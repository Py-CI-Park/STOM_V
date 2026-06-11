"""M7 (2026-06-11) — 조건식 연구 파이프라인 1-커맨드 (체크포인트 재개).

2026-06-11에 수동으로 이은 체인(스윕→θ*→재평가→동결→OOS)을 한 명령으로
재현한다. 세션 중단(오늘 실제 2회 발생)에도 state JSON 체크포인트로 완료
단계를 스킵하고 이어간다. **새 평가 로직 0** — 기존 공식 도구를 순서대로
호출하는 오케스트레이션만 한다(스윕 단계는 tmap_sweep --resume라 자체
재개도 된다).

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.research_pipeline \
      --template seed_902905 \
      --config-json .omo/evidence/claude-condition-research-20260610/train-config.json \
      --prefix pipe_20260612 [--params cap_max,take_hard] [--from-stage freeze]

단계: sweep → theta_star → reeval → freeze(+V1 자동) → oos2022 → oos2026.
슬리피지(V5)·플라시보(V2)·카드(V6)는 결과 해석이 필요해 의도적으로 수동 단계로
남긴다(자동화는 측정까지 — 판단은 사람/에이전트).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EVID_RESEARCH = REPO_ROOT / ".omo/evidence/claude-condition-research-20260610"
EVID_TMAP = REPO_ROOT / ".omo/evidence/tmap-walkforward"

STAGES = ["sweep", "theta_star", "reeval", "freeze", "oos2022", "oos2026",
          "placebo", "slippage"]  # P-B(2026-06-12): V2·V5 자동화 — 카드 입력 완성.


def pending_stages(state: Dict[str, str], from_stage: str = "") -> List[str]:
    """완료(done) 단계를 스킵한 실행 목록. from_stage부터는 강제 재실행.

    순수 함수 — 테스트 대상. from_stage가 STAGES에 없으면 ValueError.
    """
    if from_stage and from_stage not in STAGES:
        raise ValueError(f"unknown stage: {from_stage} (choices: {STAGES})")
    start = STAGES.index(from_stage) if from_stage else None
    out = []
    for i, stage in enumerate(STAGES):
        if start is not None and i >= start:
            out.append(stage)  # 강제 재실행 구간.
        elif state.get(stage) != "done":
            out.append(stage)
    return out


def build_stage_command(
    stage: str, *, template: str, config_json: str, prefix: str, params: str = ""
) -> Optional[List[str]]:
    """단계별 서브프로세스 명령(순수 함수 — 테스트 대상). 미지원 단계는 None."""
    py = sys.executable
    sweep_run = f"{prefix}_sweep"
    reeval_run = f"{prefix}_reeval"
    if stage == "sweep":
        cmd = [py, "-m", "ai_strategy_loop.scripts.tmap_sweep",
               "--template", template, "--config-json", config_json,
               "--run-id", sweep_run, "--resume",
               "--manifest-out", str(EVID_TMAP / f"{prefix}_sweep_manifest.json")]
        if params:
            cmd += ["--params", params]
        return cmd
    if stage == "theta_star":
        return [py, str(EVID_TMAP / "gen_theta_star_batch.py"), sweep_run]
    if stage == "reeval":
        return [py, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
                "--pairs-json", str(EVID_TMAP / "pairs-theta-star.json"),
                "--config-json", config_json, "--run-id", reeval_run]
    if stage == "freeze":
        return [py, str(EVID_RESEARCH / "select_and_freeze.py"), reeval_run,
                f"--trial-runs={sweep_run}"]
    if stage == "oos2022":
        # gen_oos_configs는 동결 아티팩트를 읽어 pairs/config를 만든다 — freeze 후.
        return [py, str(EVID_RESEARCH / "gen_oos_configs.py")]
    if stage == "oos2026":
        return None  # oos2022 단계에서 두 해 배치를 함께 실행한다(아래 run_stage).
    return None


def _run(cmd: List[str]) -> int:
    print("[PIPE] $", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.call([str(c) for c in cmd], cwd=str(REPO_ROOT))


def _selected_candidate() -> Optional[Dict[str, Any]]:
    """동결 아티팩트에서 선택 후보를 읽는다(없으면 None — 스테이지 건너뜀)."""
    try:
        with open(EVID_RESEARCH / "p5-selected-candidate.json", encoding="utf-8") as fh:
            return json.load(fh).get("selected_candidate")
    except Exception:  # noqa: BLE001
        return None


def placebo_pairs(placebo_prefix: str, sell_name: str,
                  rates=(2, 5, 10), shifts=(0, 1)) -> List[Dict[str, str]]:
    """P-B — 플라시보 페어 구성(gen_placebo_strategy 명명 규약과 정합).

    순수 함수 — 테스트 대상. 같은 매도식 + 무작위 진입 buys.
    """
    pairs = []
    for rate in rates:
        for shift in shifts:
            buy = (f"{placebo_prefix}_R{rate}_B" if shift == 0
                   else f"{placebo_prefix}_R{rate}_S{shift}_B")
            pairs.append({"label": f"PLACEBO R{rate} S{shift}",
                          "buy": buy, "sell": sell_name})
    return pairs


def _run_placebo_stage(prefix: str, config_json: str, workdir: Path) -> int:
    """V2 자동화: 무작위 진입 생성 → 동일 매도 배치 → 분포 위치 산출(C1)."""
    cand = _selected_candidate()
    if not cand or not cand.get("sell_name"):
        print("[PIPE] placebo: 동결 후보 없음 — 건너뜀", flush=True)
        return 0
    pfx = f"PLB_{prefix[-12:]}"
    rc = _run([sys.executable, "-m", "ai_strategy_loop.scripts.gen_placebo_strategy",
               "--prefix", pfx, "--rates", "2,5,10", "--shifts", "0,1"])
    if rc != 0:
        return rc
    pairs = placebo_pairs(pfx, cand["sell_name"])
    pairs_path = workdir / "pairs-placebo.json"
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    run_id = f"{prefix}_placebo"
    rc = _run([sys.executable, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
               "--pairs-json", str(pairs_path), "--config-json", config_json,
               "--run-id", run_id])
    if rc != 0:
        return rc
    from ai_strategy_loop.controller.state import LOOP_RUNS_DB  # noqa: PLC0415
    from ai_strategy_loop.fitness.placebo_check import (  # noqa: PLC0415
        placebo_position,
        placebo_profits_from_run,
    )

    rows = placebo_profits_from_run(run_id, str(LOOP_RUNS_DB))
    position = placebo_position(float(cand.get("profit") or 0.0),
                                [r["profit"] for r in rows])
    (workdir / "placebo_position.json").write_text(
        json.dumps({"candidate": cand.get("buy_name"), "samples": rows,
                    "position": position}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[PIPE] placebo: {position.get('interpretation') if position else '표본 부족'}",
          flush=True)
    return 0


def _run_slippage_stage(prefix: str, workdir: Path) -> int:
    """V5 자동화: 동결 후보의 train+OOS CSV 수집 → 슬리피지 스트레스 리포트."""
    cand = _selected_candidate()
    if not cand or not cand.get("buy_name"):
        print("[PIPE] slippage: 동결 후보 없음 — 건너뜀", flush=True)
        return 0
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.controller.state import LOOP_RUNS_DB  # noqa: PLC0415

    csvs: List[str] = []
    try:
        con = sqlite3.connect(str(LOOP_RUNS_DB))
        try:
            for rid in (f"{prefix}_reeval", f"{prefix}_oos_2022", f"{prefix}_oos_2026"):
                row = con.execute(
                    "SELECT csv_path FROM generations WHERE run_id=? AND buy_name=?"
                    " AND status='ok' AND csv_path IS NOT NULL LIMIT 1",
                    (rid, cand["buy_name"]),
                ).fetchone()
                if row and row[0]:
                    csvs.append(row[0])
        finally:
            con.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[PIPE] slippage: CSV 조회 실패 {exc} — 건너뜀", flush=True)
        return 0
    if not csvs:
        print("[PIPE] slippage: 후보 CSV 없음 — 건너뜀", flush=True)
        return 0
    cmd = [sys.executable, "-m", "ai_strategy_loop.scripts.slippage_stress_report",
           "--ticks", "0,1,2", "--fee-bps", "0,5",
           "--out", str(workdir / "slippage_stress.json")]
    for c in csvs:
        cmd += ["--csv", c]
    return _run(cmd)


def run_stage(stage: str, *, template: str, config_json: str, prefix: str,
              params: str = "") -> int:
    """단계 실행. oos는 config 1회+연도 배치, placebo/slippage는 P-B 자동화."""
    workdir = REPO_ROOT / ".omo/evidence/pipeline" / prefix
    workdir.mkdir(parents=True, exist_ok=True)
    if stage == "placebo":
        return _run_placebo_stage(prefix, config_json, workdir)
    if stage == "slippage":
        return _run_slippage_stage(prefix, workdir)
    if stage in ("oos2022", "oos2026"):
        year = stage[-4:]
        if stage == "oos2022":  # config 생성은 한 번만(동결 아티팩트 기반).
            rc = _run(build_stage_command("oos2022", template=template,
                                          config_json=config_json, prefix=prefix))
            if rc != 0:
                return rc
        return _run([sys.executable, "-m",
                     "ai_strategy_loop.scripts.claude_candidate_batch_eval",
                     "--pairs-json", str(EVID_RESEARCH / "pairs-oos.json"),
                     "--config-json", str(EVID_RESEARCH / f"oos-{year}-config.json"),
                     "--run-id", f"{prefix}_oos_{year}"])
    cmd = build_stage_command(stage, template=template, config_json=config_json,
                              prefix=prefix, params=params)
    if cmd is None:
        return 0
    return _run(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--config-json", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--params", default="")
    ap.add_argument("--from-stage", default="")
    args = ap.parse_args()

    state_dir = REPO_ROOT / ".omo/evidence/pipeline" / args.prefix
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    state: Dict[str, str] = (
        json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    )

    todo = pending_stages(state, args.from_stage)
    skipped = [s for s in STAGES if s not in todo]
    if skipped:
        print(f"[PIPE] skip(완료): {skipped}", flush=True)
    for stage in todo:
        t0 = time.time()
        rc = run_stage(stage, template=args.template, config_json=args.config_json,
                       prefix=args.prefix, params=args.params)
        state[stage] = "done" if rc == 0 else f"failed rc={rc}"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        print(f"[PIPE] {stage}: {state[stage]} ({time.time()-t0:.0f}s)", flush=True)
        if rc != 0:
            print(f"[PIPE] 중단 — 재개: 같은 명령 재실행(완료 단계 자동 스킵)", flush=True)
            return rc
    print("[PIPE] 전 단계 완료 — 수동 단계: 슬리피지(V5)·플라시보(V2)·결정 카드(V6)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
