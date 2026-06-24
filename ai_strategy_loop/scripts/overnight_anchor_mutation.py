"""밤샘 앵커 변이 발굴 (LLM 0회 — 콜드 생성 아님).

검증된 앵커(seed_902905 등)에서 출발해 라운드마다:
  ① propose_mutations로 단일축 이웃 변이(시간·시총·익절·트레일…) 생성
  ② render → materialize_candidate(DB 등록) → pairs-json
  ③ claude_candidate_batch_eval로 일괄 재백테(P0b 게이트 = 발굴 config의 mdd/daily)
  ④ loop_runs.db에서 결과 조회 → gate=True 채택 → 최선(profit max)을 다음 앵커로(hill-climb)
  ⑤ 마감시각(--deadline-hhmm)까지 반복. 동일 θ 재평가 방지(dedup).

엔진/CLI/backtest_graph 무수정 — 기존 mutator·materialize·batch_eval만 조립한다.
정직지표: gate=True(발굴 게이트 통과) 후보 수. 채택 = 진짜 재백테 통과분만(사후슬라이스 차단).
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

import ai_strategy_loop.bootstrap as bootstrap
from ai_strategy_loop.controller import state as _state
from ai_strategy_loop.tmap.mutator import propose_mutations
from ai_strategy_loop.tmap.refine_gate import materialize_candidate
from ai_strategy_loop.tmap.template import load_template, render

_REPO = Path(__file__).resolve().parents[2]


def _theta_sig(theta: Dict[str, Any]) -> str:
    return json.dumps({k: theta[k] for k in sorted(theta)}, ensure_ascii=False)


def _deadline_epoch(hhmm: str) -> float:
    """'08:00' → 다음 도래하는 그 시각의 epoch(오늘 지났으면 내일). 시스템 시계 사용."""
    hh, mm = (int(x) for x in hhmm.split(":"))
    now = time.localtime()
    target = time.struct_time((now.tm_year, now.tm_mon, now.tm_mday, hh, mm, 0,
                               now.tm_wday, now.tm_yday, now.tm_isdst))
    ep = time.mktime(target)
    if ep <= time.time():
        ep += 24 * 3600
    return ep


def _query_round(run_id: str) -> List[Dict[str, Any]]:
    """batch_eval가 loop_runs.db에 남긴 이 라운드 결과를 읽는다(label=strategy_gist)."""
    try:
        con = sqlite3.connect(str(_state.LOOP_RUNS_DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT strategy_gist, gate_passed, profit, mdd, trade_count, daily_avg_trades, score"
                " FROM generations WHERE run_id=?", (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return []
    return [dict(r) for r in rows]


def _log(out_jsonl: Path, obj: Dict[str, Any]) -> None:
    with open(out_jsonl, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="밤샘 앵커 변이 발굴(LLM 0회).")
    ap.add_argument("--template", default="seed_902905")
    ap.add_argument("--config-json", required=True, help="발굴 게이트 config(mdd/daily).")
    ap.add_argument("--run-prefix", default="ovn_anchor")
    ap.add_argument("--out", required=True, help="라운드 결과 jsonl 경로.")
    ap.add_argument("--deadline-hhmm", default="08:00")
    ap.add_argument("--max-per-param", type=int, default=2)
    ap.add_argument("--max-rounds", type=int, default=0, help="0=무제한(마감까지).")
    ap.add_argument("--round-timeout", type=int, default=5400, help="라운드당 batch_eval 타임아웃(초).")
    ap.add_argument("--dry-run", action="store_true", help="변이·재료화·pairs만, 백테 미실행.")
    args = ap.parse_args(argv)

    out_jsonl = Path(args.out)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    template = load_template(args.template)
    anchor: Dict[str, Any] = dict(template.defaults())
    deadline = _deadline_epoch(args.deadline_hhmm)
    seen: set = set()
    best_overall: Optional[Dict[str, Any]] = None
    adopted_total = 0
    round_no = 0

    print(f"[OVN] 시작 — anchor={args.template} 마감={args.deadline_hhmm} "
          f"(남은 {(deadline - time.time())/3600:.1f}h) config={args.config_json}", flush=True)
    _log(out_jsonl, {"event": "start", "template": args.template, "deadline_hhmm": args.deadline_hhmm,
                     "ts": time.time(), "config": args.config_json})

    while time.time() < deadline:
        if args.max_rounds and round_no >= args.max_rounds:
            print(f"[OVN] max-rounds {args.max_rounds} 도달 — 종료", flush=True)
            break
        round_no += 1
        muts = propose_mutations(template, anchor, max_per_param=args.max_per_param)
        fresh = [m for m in muts if _theta_sig(m["theta"]) not in seen]
        if not fresh:
            print(f"[OVN] r{round_no}: 새 변이 없음(앵커 수렴) — max_per_param 확대 시도", flush=True)
            muts = propose_mutations(template, anchor, max_per_param=args.max_per_param + 2)
            fresh = [m for m in muts if _theta_sig(m["theta"]) not in seen]
            if not fresh:
                print("[OVN] 탐색 고갈 — 종료", flush=True)
                break

        label2theta: Dict[str, Dict[str, Any]] = {}
        pairs: List[Dict[str, str]] = []
        for i, m in enumerate(fresh):
            label = f"r{round_no}_{i}_{m['param']}={m['value']}"
            try:
                buy, sell = render(template, m["theta"])
                bn, sn = materialize_candidate(label, buy, sell, template.timeframe)
            except Exception as exc:  # noqa: BLE001 - 재료화 실패 후보는 건너뜀.
                continue
            seen.add(_theta_sig(m["theta"]))
            label2theta[label] = m["theta"]
            pairs.append({"label": label, "buy": bn, "sell": sn})

        run_id = f"{args.run_prefix}_r{round_no}"
        pairs_path = out_jsonl.parent / f"{run_id}_pairs.json"
        pairs_path.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
        print(f"[OVN] r{round_no}: 변이 {len(pairs)}개 재료화 → 재백테", flush=True)

        if args.dry_run:
            _log(out_jsonl, {"event": "round_dry", "round": round_no, "candidates": len(pairs),
                             "pairs_path": str(pairs_path), "ts": time.time()})
            print(f"[OVN] (dry-run) r{round_no} pairs={len(pairs)} — 백테 생략", flush=True)
            if args.max_rounds and round_no >= args.max_rounds:
                break
            continue

        remain = int(deadline - time.time())
        if remain < 600:
            print("[OVN] 마감 임박 — 라운드 미시작", flush=True)
            break
        try:
            subprocess.run(
                [sys.executable, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
                 "--pairs-json", str(pairs_path), "--config-json", args.config_json, "--run-id", run_id],
                cwd=str(_REPO), env=dict(os.environ, PYTHONUTF8="1"),
                timeout=min(args.round_timeout, remain), check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"[OVN] r{round_no} batch 타임아웃", flush=True)

        results = _query_round(run_id)
        passers = [r for r in results if r.get("gate_passed") and float(r.get("profit") or 0) > 0]
        # 채택분 로그.
        for r in results:
            _log(out_jsonl, {"event": "cand", "round": round_no, "label": r.get("strategy_gist"),
                             "gate": bool(r.get("gate_passed")), "profit": r.get("profit"),
                             "mdd": r.get("mdd"), "trades": r.get("trade_count"),
                             "daily": r.get("daily_avg_trades"),
                             "theta": label2theta.get(r.get("strategy_gist") or ""), "ts": time.time()})
        adopted_total += len(passers)

        # hill-climb: 통과분 있으면 최고 profit을 새 앵커로. 없으면 최고 profit(미통과)로 소프트 이동(탐색).
        pool = passers if passers else [r for r in results if r.get("profit") is not None]
        moved = False
        if pool:
            best = max(pool, key=lambda r: float(r.get("profit") or -1e18))
            bt = label2theta.get(best.get("strategy_gist") or "")
            if bt:
                anchor = dict(template.defaults()); anchor.update(bt)
                moved = True
                if best.get("gate_passed") and (best_overall is None or
                        float(best["profit"]) > float(best_overall["profit"])):
                    best_overall = {"label": best.get("strategy_gist"), "profit": best.get("profit"),
                                    "mdd": best.get("mdd"), "theta": bt}
        print(f"[OVN] r{round_no} 완료 — 통과 {len(passers)}/{len(results)} "
              f"누적채택 {adopted_total} 앵커이동={moved} "
              f"best_overall={best_overall['profit'] if best_overall else None}", flush=True)
        _log(out_jsonl, {"event": "round_done", "round": round_no, "passers": len(passers),
                         "evaluated": len(results), "adopted_total": adopted_total,
                         "best_overall": best_overall, "ts": time.time()})

    summary = {"rounds": round_no, "adopted_total": adopted_total, "best_overall": best_overall,
               "finished_ts": time.time()}
    (out_jsonl.parent / f"{args.run_prefix}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OVN] 종료 — 라운드 {round_no} 누적채택 {adopted_total} "
          f"best_overall={best_overall}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
