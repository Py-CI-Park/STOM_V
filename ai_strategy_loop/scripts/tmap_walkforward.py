"""TMAP G4 — 전진분석(walk-forward) 정책 드라이버 (시나리오 D의 판정 도구).

"어떤 고정 전략도 영원하지 않다"(시드 연도별 쇠퇴 실측)를 받아들이면 검증 대상은
전략이 아니라 **재적합 정책**이다: fit 창에서 경향성 지도를 갱신해 θ*를 고르고,
직후 eval 창에서 θ*의 성과만 누적한다 — "이 정책으로 운용했으면 벌었을 돈".

정책 v1(사전선언, 보수적): fit 창 스윕에서 plateau_score 최고 슬롯의 고원 중심값
**한 개만** 기본값에서 변경(coordinate policy). 베이스라인(θ=기본값)도 같은 eval
창에서 평가해 정책의 부가가치를 분리한다.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.tmap_walkforward \
      --template seed_902905 --config-json <base.json> --run-prefix wf_seed \
      --windows "20230101-20231231:20240101-20240630,20240101-20241231:20250101-20250630" \
      [--params cap_max,prev_ratio_min,window_end] [--out <aggregate.json>]

창 형식: "fitStart-fitEnd:evalStart-evalEnd" 쉼표 연결.
분석/연구 전용 — 동결/OOS 규율을 대체하지 않는다(advisory; 정책 성과의 추정).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_windows(spec: str) -> List[Dict[str, int]]:
    """'20230101-20231231:20240101-20240630,...' → [{fit_start,...}] (순수 — 테스트 대상)."""
    windows: List[Dict[str, int]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        fit_part, _, eval_part = chunk.partition(":")
        f0, _, f1 = fit_part.partition("-")
        e0, _, e1 = eval_part.partition("-")
        windows.append({
            "fit_start": int(f0), "fit_end": int(f1),
            "eval_start": int(e0), "eval_end": int(e1),
        })
    return windows


def select_theta(summary: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """정책 v1: plateau_score 최고 슬롯의 고원 중심값 1개 변경 (순수 — 테스트 대상).

    적격 조건: plateau 존재 + 고원 평균손익 > max(베이스라인 손익, 0) +
    positive_ratio >= 0.5(이웃 절반 이상 흑자 — 고원다움).

    [N9 교정 2026-06-11] 비교 기준을 베이스라인 단독에서 max(베이스라인, 0)으로
    강화. 종전엔 베이스라인이 적자인 fit창(시드 쇠퇴 구간)에서 '덜 나쁜' 적자
    고원(-50만 > -300만)이 개선으로 통과해 정책 θ로 선택될 수 있었다 — 약세장
    에서 손실 전략을 알파로 오인하는 함정. 절대 흑자가 없으면 베이스라인 유지.
    Returns: (theta or None, 근거 dict).
    """
    base = (summary.get("baseline") or {})
    base_profit = float(base.get("profit") or 0.0)
    best_name, best_m, best_score = None, None, 0.0
    for name, m in (summary.get("params") or {}).items():
        plateau = m.get("plateau")
        if not plateau:
            continue
        if (m.get("positive_ratio") or 0.0) < 0.5:
            continue
        if plateau["mean_profit"] <= max(base_profit, 0.0):
            continue
        score = m.get("plateau_score") or 0.0
        if score > best_score:
            best_name, best_m, best_score = name, m, score
    if best_name is None:
        return None, {"reason": "no qualifying plateau — fallback to baseline", "baseline_profit": base_profit}
    center = best_m["plateau"]["center_value"]
    return (
        {best_name: center},
        {"param": best_name, "value": center, "plateau_score": best_score,
         "plateau": best_m["plateau"], "baseline_profit": base_profit},
    )


def _run(cmd: List[str]) -> int:
    print("[WF] $", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


def _window_config(base_config: Dict[str, Any], start: int, end: int, path: Path) -> Path:
    cfg = dict(base_config)
    cfg["bt_full_start"] = start
    cfg["bt_full_end"] = end
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--config-json", required=True)
    ap.add_argument("--run-prefix", required=True)
    ap.add_argument("--windows", required=True)
    ap.add_argument("--params", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    import ai_strategy_loop.bootstrap  # noqa: F401,PLC0415
    from ai_strategy_loop.tmap.tendency import summarize_tendency  # noqa: PLC0415
    from ai_strategy_loop.tmap.template import load_template  # noqa: PLC0415

    template = load_template(args.template)
    base_config = json.loads(Path(args.config_json).read_text(encoding="utf-8"))
    windows = parse_windows(args.windows)
    workdir = Path(".omo/evidence/tmap-walkforward") / args.run_prefix
    workdir.mkdir(parents=True, exist_ok=True)

    aggregate: Dict[str, Any] = {"template": template.name, "windows": [],
                                 "policy_total": 0.0, "baseline_total": 0.0}
    for i, w in enumerate(windows):
        tag = f"{args.run_prefix}_w{i}"
        # 1) fit 창 스윕 → 경향성 지도.
        fit_cfg = _window_config(base_config, w["fit_start"], w["fit_end"], workdir / f"w{i}_fit.json")
        sweep_run = f"{tag}_fit_sweep"
        cmd = [sys.executable, "-m", "ai_strategy_loop.scripts.tmap_sweep",
               "--template", args.template, "--config-json", str(fit_cfg),
               "--run-id", sweep_run,
               "--manifest-out", str(workdir / f"w{i}_manifest.json")]
        if args.params:
            cmd += ["--params", args.params]
        if _run(cmd) != 0:
            aggregate["windows"].append({**w, "status": "sweep_failed"})
            continue
        summary = summarize_tendency(sweep_run)
        theta, basis = select_theta(summary)

        # 2) eval 창에서 정책 θ*와 베이스라인을 같은 배치로 평가.
        from ai_strategy_loop.tmap.template import render, strategy_names, validate_rendered  # noqa: PLC0415
        from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
        import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415

        db = str(bootstrap.LOOP_DB_STRATEGY)
        pairs = []
        for label, th in (("POLICY", theta or {}), ("BASELINE", {})):
            buy_code, sell_code = render(template, th)
            if validate_rendered(buy_code, sell_code, template.timeframe):
                continue
            bn, sn = strategy_names(template, 900 + i * 2 + (0 if label == "POLICY" else 1))
            save_strategy_to_db(db, bn, buy_code, "buy")
            save_strategy_to_db(db, sn, sell_code, "sell")
            pairs.append({"label": f"WF_{label}", "buy": bn, "sell": sn})
        pairs_path = workdir / f"w{i}_pairs.json"
        pairs_path.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
        eval_cfg = _window_config(base_config, w["eval_start"], w["eval_end"], workdir / f"w{i}_eval.json")
        eval_run = f"{tag}_eval"
        if _run([sys.executable, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
                 "--pairs-json", str(pairs_path), "--config-json", str(eval_cfg),
                 "--run-id", eval_run]) != 0:
            aggregate["windows"].append({**w, "status": "eval_failed", "theta": theta})
            continue

        # 3) eval 결과 집계.
        import sqlite3  # noqa: PLC0415
        from ai_strategy_loop.controller import state as _S  # noqa: PLC0415
        con = sqlite3.connect(str(_S.LOOP_RUNS_DB))
        try:
            rows = {r[0]: {"profit": r[1] or 0.0, "trades": r[2] or 0}
                    for r in con.execute(
                        "SELECT strategy_gist, profit, trade_count FROM generations"
                        " WHERE run_id=?", (eval_run,)).fetchall()}
        finally:
            con.close()
        policy = rows.get("WF_POLICY", {"profit": 0.0, "trades": 0})
        baseline = rows.get("WF_BASELINE", {"profit": 0.0, "trades": 0})
        aggregate["policy_total"] += policy["profit"]
        aggregate["baseline_total"] += baseline["profit"]
        aggregate["windows"].append({
            **w, "status": "ok", "theta": theta, "theta_basis": basis,
            "policy": policy, "baseline": baseline,
        })
        print(f"[WF] w{i} policy={policy['profit']:,.0f} baseline={baseline['profit']:,.0f} "
              f"theta={theta}", flush=True)

    out_path = Path(args.out) if args.out else workdir / "aggregate.json"
    out_path.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[WF] TOTAL policy={aggregate['policy_total']:,.0f} "
          f"baseline={aggregate['baseline_total']:,.0f} -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
