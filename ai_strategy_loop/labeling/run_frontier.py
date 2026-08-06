"""QSP10 프런티어 실행기 — 배리어 규칙별로 '유의한 흑자 구역'을 규모대별로 찾는다.

탐욕 수렴이 표본 하한까지 밀고 내려가는 편향을 보완한다. 결과가 비면 "이 우주에
이 규칙으로 잡을 흑자 구역은 없다"가 근거 있는 결론이 된다.
"""

from __future__ import annotations

import argparse
import json
import os
import time

from ai_strategy_loop.labeling.frontier import scan
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v2")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--buckets", type=int, default=20)
    args = parser.parse_args()

    lane = LANES[args.lane]
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    hits = sorted({c for rule in RULES for c in rule[2:]})

    t0 = time.time()
    frame = _load(args.out_name, base + hits + variables, args.warmup)
    available = [v for v in variables if v in frame.columns]
    print(f"집행 우주 {len(frame):,}행 · 변수 {len(available)}종 · {time.time()-t0:.0f}s", flush=True)

    report = {"lane": lane.name, "rows": int(len(frame)), "rules": []}
    for tp_pct, sl_pct, tp, sl in RULES:
        if tp not in frame.columns or sl not in frame.columns:
            continue
        result = scan(frame, variables=available, buckets=args.buckets,
                      tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                      horizon=lane.barrier_horizon, timeout_label=timeout_label)
        result["rule"] = f"TP{tp_pct}/SL{sl_pct}"
        report["rules"].append(result)
        print(f"{result['rule']}: 흑자 구역 {result['regions']} · FDR 생존 {result['survivors']} · "
              f"프런티어 {len(result['frontier'])}밴드 · {time.time()-t0:.0f}s", flush=True)
        for row in result["frontier"]:
            print(f"   [{row['band']}] {row['description']} · n={row['n']:,} "
                  f"(하루 {row['per_day']}) · 승률 {row['win_rate']:.3f}/{row['breakeven']:.3f} · "
                  f"기대값 {row['expectancy_pct']:+.4f}% · q={row['q_value']:.4f}", flush=True)

    report["gate_any_positive_region"] = any(r["frontier"] for r in report["rules"])
    path = os.path.join(_LABEL_ROOT, args.out_name, "_frontier_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=float)
    print(json.dumps({"gate": report["gate_any_positive_region"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
