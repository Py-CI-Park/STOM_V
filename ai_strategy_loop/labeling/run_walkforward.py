"""QSP13 워크포워드 실행기 — 표본 밖 성능의 정직한 추정치를 낸다.

사용:
    python -m ai_strategy_loop.labeling.run_walkforward --out-name design_v3
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

from ai_strategy_loop.labeling import walkforward
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--min-rows", type=int, default=400)
    parser.add_argument("--max-depth", type=int, default=4)
    args = parser.parse_args()

    lane = LANES[args.lane]
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    hits = sorted({c for rule in RULES for c in rule[2:]})

    t0 = time.time()
    frame = _load(args.out_name, base + hits + variables, args.warmup).reset_index(drop=True)
    available = [v for v in variables if v in frame.columns]
    print(f"집행 우주 {len(frame):,}행 · 변수 {len(available)}종 · {time.time()-t0:.0f}s",
          flush=True)

    report = {"lane": lane.name, "folds": args.folds, "rules": []}
    for tp_pct, sl_pct, tp, sl in RULES:
        if tp not in frame.columns or sl not in frame.columns:
            continue
        outcome = walkforward.run(frame, variables=available, tp_pct=tp_pct, sl_pct=sl_pct,
                                  tp=tp, sl=sl, horizon=lane.barrier_horizon,
                                  timeout_label=timeout_label, n_folds=args.folds,
                                  min_rows=args.min_rows, max_depth=args.max_depth)
        summary = outcome.summary
        report["rules"].append({
            "rule": f"TP{tp_pct}/SL{sl_pct}", "summary": summary,
            "folds": [{"index": f.index, "train": f.train, "valid": f.valid,
                       "train_stats": f.train_stats, "valid_stats": f.valid_stats,
                       "branches": len(f.branches)} for f in outcome.folds],
        })
        if summary.get("folds"):
            print(f"TP{tp_pct}/SL{sl_pct}: 폴드 {summary['folds']} · "
                  f"학습 {summary.get('train_day_mean_pct', float('nan')):+.4f}% → "
                  f"**표본밖 {summary['oos_day_mean_pct']:+.4f}%** · "
                  f"양수 폴드 {summary['oos_positive_folds']}/{summary['folds']} · "
                  f"p={summary.get('p_value', 1.0):.4f} · "
                  f"{'PASS' if summary['passed'] else 'FAIL'} · {time.time()-t0:.0f}s",
                  flush=True)
        else:
            print(f"TP{tp_pct}/SL{sl_pct}: 폴드 0 (후보 없음) · {time.time()-t0:.0f}s", flush=True)

    passing = [r["rule"] for r in report["rules"] if r["summary"].get("passed")]
    report["gate_passed"] = bool(passing)
    report["passing_rules"] = passing
    path = os.path.join(_LABEL_ROOT, args.out_name, "_walkforward_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=float)
    print(json.dumps({"gate": report["gate_passed"], "passing": passing}, ensure_ascii=False))


if __name__ == "__main__":
    main()
