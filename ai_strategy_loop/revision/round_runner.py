"""다후보 라운드 러너 (QSP1 P3) — 1회 호출 = 1라운드(재개 가능·감사 가능).

사용자 방법론: "하나의 조건식이 아니라 여러 후보를 생성하여 모두 평가·분석하여
개선해 나가는 방식" + "한번 개선으로 항상 좋아질 수는 없다 — 여러 개가 복합적으로".

라운드 절차(전 단계가 기존 공식 부품 재사용 — 사설 채점 금지):
  1) base 매수식 + 직전 라벨 CSV → proposer 로 N개 수정 명세(서로 다른 리프/변수 축).
  2) 각 명세: apply → intent_gate → PASS 만 loop_strategies.db 등록(INSERT-only).
  3) 공식 배치(claude_candidate_batch_eval) 로 base+후보 전부 평가.
  4) 세대 행(공식 채점)에서 객관값을 뽑아 베스트 선택 + 교훈(무효 축) 합성.
  5) convergence.judge 로 계속/수렴/발산 판정.
  6) 라운드 기록 JSON 저장(rounds/) — 대시보드 라운드 보드가 읽는다.

CLI:
  python -m ai_strategy_loop.revision.round_runner \
      --base-buy QSP1_M_HIER_900_1500_B --base-sell QSP1_M_HIER_900_1500_S \
      --config docs/research/quant_scoring_pipeline/config_qsp1_min_1mo.json \
      --tag qsp1min1mo --round 1 --n 3
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
ROUNDS_DIR = REPO / "docs" / "research" / "quant_scoring_pipeline" / "rounds"
LOOP_DB = REPO / "ai_strategy_loop" / "state" / "loop_strategies.db"
PY = sys.executable


def _read_rounds(tag: str) -> List[Dict[str, Any]]:
    out = []
    if ROUNDS_DIR.exists():
        for p in sorted(ROUNDS_DIR.glob(f"{tag}_r*.json")):
            if p.name.endswith("_pairs.json"):  # 배치 입력(리스트) — 라운드 기록 아님.
                continue
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(doc, dict) and "round" in doc:
                out.append(doc)
    return sorted(out, key=lambda r: r.get("round", 0))


def _register_buy(name: str, code: str) -> None:
    con = sqlite3.connect(LOOP_DB)
    try:
        if con.execute('SELECT 1 FROM stockbuy WHERE "index"=?', (name,)).fetchone():
            con.execute('DELETE FROM stockbuy WHERE "index"=?', (name,))  # 같은 라운드 재실행 허용
        con.execute('INSERT INTO stockbuy ("index","전략코드") VALUES (?,?)', (name, code))
        con.commit()
    finally:
        con.close()


def _load_code(name: str) -> Optional[str]:
    from ai_strategy_loop.controller.strategy_preflight import load_loop_strategy_code

    return load_loop_strategy_code("buy", name)


def _gen_rows(run_id: str) -> List[Dict[str, Any]]:
    from ai_strategy_loop.controller.state import LoopState

    st = LoopState(readonly=True)
    try:
        return list(st.get_generations(run_id))
    finally:
        st.close()


def _objective(rows: List[Dict[str, Any]]) -> None:
    """행마다 objective 주입: 게이트 통과가 하나라도 있으면 score, 아니면 총손익."""
    any_gate = any(bool(r.get("gate_passed")) for r in rows)
    for r in rows:
        r["objective"] = float(r.get("score", 0) or 0) if any_gate else float(r.get("profit", 0) or 0)


def run_round(base_buy: str, base_sell: str, config_path: str, tag: str,
              round_no: int, n_cand: int) -> Dict[str, Any]:
    from ai_strategy_loop.autopsy import label_dataset as lds
    from ai_strategy_loop.revision import intent_gate as gate
    from ai_strategy_loop.revision import proposer
    from ai_strategy_loop.revision.convergence import RoundStat, judge

    ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    prev = _read_rounds(tag)
    # 라벨 CSV: 직전 라운드 베스트의 CSV. 첫 라운드는 base 의 기준 CSV(직전 평가 run).
    if prev:
        label_csv = prev[-1]["best"]["csv_path"]
        base_code_name = prev[-1]["best"]["buy_name"]
        seed_trades = int(prev[0]["base"]["trade_count"])
    else:
        base_run = json.loads(Path(config_path).with_suffix(".baseline.json").read_text(encoding="utf-8")) \
            if Path(config_path).with_suffix(".baseline.json").exists() else None
        if not base_run:
            raise SystemExit("첫 라운드에는 <config>.baseline.json({run_id}) 이 필요합니다 — base 평가 run 지정")
        rows = _gen_rows(base_run["run_id"])
        base_row = next(r for r in rows if r.get("buy_name") == base_buy)
        label_csv = str(base_row["csv_path"])
        base_code_name = base_buy
        seed_trades = int(base_row.get("trade_count", 0) or 0)

    base_code = _load_code(base_code_name)
    if not base_code:
        raise SystemExit(f"base 매수식 로드 실패: {base_code_name}")

    ds = lds.build(str(REPO / label_csv) if not os.path.isabs(str(label_csv)) else str(label_csv))
    # P3.1(F-R3-1) 교훈 환류 — 이전 라운드들에서 base 대비 |Δ| 가 미미했던(사실상 무효)
    #   (축, 리프) 조합은 재제안하지 않는다. 임계: base objective 의 1% 또는 10만원 중 큰 값.
    exclude_axes: List[tuple] = []
    for rec in prev:
        base_obj = abs(float((rec.get("base") or {}).get("objective") or 0.0))
        thresh = max(base_obj * 0.01, 100_000.0)
        for lesson in rec.get("lessons", []):
            if abs(float(lesson.get("delta_vs_base") or 0.0)) < thresh:
                exclude_axes.append((lesson.get("axis"), lesson.get("leaf")))
    specs = proposer.propose(ds, base_code, base_code_name, top_k=n_cand,
                             exclude_axes=exclude_axes)
    print(f"[ROUND{round_no}] base={base_code_name} 라벨={label_csv} 제안={len(specs)}"
          f" (무효 축 제외 {len(set(exclude_axes))})", flush=True)

    # 후보 생성·게이트·등록.
    pairs: List[Dict[str, str]] = [{"label": f"r{round_no}_base", "buy": base_code_name, "sell": base_sell}]
    cand_meta: List[Dict[str, Any]] = []
    for i, spec in enumerate(specs, 1):
        new_code, reason = proposer.apply(spec, base_code)
        if not new_code:
            cand_meta.append({"cand": i, "spec": spec, "status": "apply_fail", "reason": reason})
            continue
        gres = gate.verify(base_code, new_code, [spec])
        if not gres.ok:
            cand_meta.append({"cand": i, "spec": spec, "status": "gate_fail", "reason": gres.reason})
            print(f"[ROUND{round_no}] C{i} GATE FAIL — {gres.reason}", flush=True)
            continue
        name = f"QSP1{tag.upper()}_R{round_no}C{i}_B"
        _register_buy(name, new_code)
        pairs.append({"label": f"r{round_no}_c{i}", "buy": name, "sell": base_sell})
        cand_meta.append({"cand": i, "spec": spec, "status": "registered",
                          "buy_name": name, "gate": "PASS"})
        print(f"[ROUND{round_no}] C{i} 등록 {name} — {spec['change']}", flush=True)

    # 공식 배치 실행(동기).
    pairs_path = ROUNDS_DIR / f"{tag}_r{round_no}_pairs.json"
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    run_id = f"{time.strftime('%Y%m%d-%H%M')}_{tag}-r{round_no}"
    cmd = [PY, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
           "--pairs-json", str(pairs_path), "--config-json", config_path, "--run-id", run_id]
    env = dict(os.environ, STOM_ALLOW_MINIMAL_SETTING="1", PYTHONUTF8="1")
    print(f"[ROUND{round_no}] 배치 {run_id} ({len(pairs)}쌍)…", flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True,
                          timeout=60 * 60)
    tail = "\n".join((proc.stdout or "").splitlines()[-12:])
    print(tail, flush=True)

    rows = _gen_rows(run_id)
    _objective(rows)
    by_label: Dict[str, Dict[str, Any]] = {}
    for r, p in zip(rows, pairs):
        by_label[p["label"]] = {**r, "pair_label": p["label"], "buy_name": p["buy"]}
    ok_rows = [v for v in by_label.values() if v.get("status") == "ok"]
    if not ok_rows:
        raise SystemExit(f"라운드 전멸 — run {run_id} 에 ok 세대 없음")
    best = max(ok_rows, key=lambda r: r["objective"])
    base_row = by_label.get(f"r{round_no}_base")

    # 교훈 합성: 베스트가 아닌 후보의 (feature, 리프) 축과 성적.
    lessons = []
    for v in ok_rows:
        if v is best:
            continue
        meta = next((m for m in cand_meta if m.get("buy_name") == v.get("buy_name")), None)
        if meta:
            lessons.append({
                "axis": meta["spec"]["feature"], "leaf": meta["spec"]["leaf_label"],
                "objective": v["objective"], "delta_vs_base": v["objective"] - (base_row or {}).get("objective", 0.0),
            })

    history = [RoundStat(r["round"], r["best"]["objective"], r["best"]["trade_count"]) for r in prev]
    history.append(RoundStat(round_no, best["objective"], int(best.get("trade_count", 0) or 0)))
    seed_n = seed_trades if prev else int((base_row or {}).get("trade_count", seed_trades) or seed_trades)
    verdict = judge(history, seed_trades=seed_n)

    record = {
        "tag": tag, "round": round_no, "run_id": run_id,
        "base": {"buy_name": base_code_name,
                 "objective": (base_row or {}).get("objective"),
                 "trade_count": (base_row or {}).get("trade_count"),
                 "csv_path": (base_row or {}).get("csv_path")},
        "candidates": cand_meta,
        "results": [{k: v.get(k) for k in ("pair_label", "buy_name", "objective", "score",
                                           "profit", "mdd", "trade_count", "gate_passed", "csv_path")}
                    for v in by_label.values()],
        "best": {k: best.get(k) for k in ("pair_label", "buy_name", "objective", "score",
                                          "profit", "mdd", "trade_count", "csv_path")},
        "lessons": lessons,
        "judgment": {"state": verdict.state, "reason": verdict.reason,
                     "improvement_pct": verdict.improvement_pct},
        "seed_trades": seed_n,
    }
    out_path = ROUNDS_DIR / f"{tag}_r{round_no}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ROUND{round_no}] best={record['best']['buy_name']} obj={record['best']['objective']:,.0f} "
          f"judgment={verdict.state} — {verdict.reason}", flush=True)
    print(f"[ROUND{round_no}] 기록 {out_path}", flush=True)
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-buy", required=True)
    ap.add_argument("--base-sell", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()
    run_round(args.base_buy, args.base_sell, args.config, args.tag, args.round, args.n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
