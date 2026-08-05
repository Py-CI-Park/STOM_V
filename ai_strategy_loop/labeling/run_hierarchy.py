"""QSP12 계층 구조 탐색 실행기 — 분기별 수렴 후 결합 판정.

사용:
    python -m ai_strategy_loop.labeling.run_hierarchy --out-name design_v3
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

from ai_strategy_loop.labeling.hierarchy import search
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load


_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    # Windows 콘솔(cp949)에서 유니코드가 깨져 죽는 것을 막는다. **임포트 시점이
    #   아니라 실행 시점에** 바꾼다 — 모듈 임포트가 전역 stdout 을 갈아치우면
    #   그 모듈을 불러 쓰는 다른 스크립트의 출력이 끊긴다(실측 결함).
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--min-rows", type=int, default=800)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--objective", choices=("pooled", "day_mean"), default="day_mean")
    args = parser.parse_args()

    lane = LANES[args.lane]
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    hits = sorted({c for rule in RULES for c in rule[2:]})

    t0 = time.time()
    frame = _load(args.out_name, base + hits + variables, args.warmup)
    frame = frame.reset_index(drop=True)      # 위치 색인을 쓰므로 인덱스를 정규화한다
    available = [v for v in variables if v in frame.columns]
    print(f"집행 우주 {len(frame):,}행 · 변수 {len(available)}종 · {time.time()-t0:.0f}s",
          flush=True)

    report = {"lane": lane.name, "objective": args.objective,
              "rows": int(len(frame)), "rules": []}
    for tp_pct, sl_pct, tp, sl in RULES:
        if tp not in frame.columns or sl not in frame.columns:
            continue
        outcome = search(frame, variables=available, tp_pct=tp_pct, sl_pct=sl_pct,
                         tp=tp, sl=sl, horizon=lane.barrier_horizon,
                         timeout_label=timeout_label, min_rows=args.min_rows,
                         max_depth=args.max_depth, objective=args.objective)
        combined = outcome.combined
        record = {
            "rule": f"TP{tp_pct}/SL{sl_pct}",
            "branches": [{"name": b.name, "spec": b.mask_spec, "clauses": b.clauses,
                          "rows": b.rows, "stats": b.stats} for b in outcome.branches],
            "combined": combined,
        }
        report["rules"].append(record)
        print(f"{record['rule']}: 분기 {combined['branches']}개 · n={combined['rows']:,} · "
              f"일수 {combined['days']} · 기대값 {combined['expectancy_pct']:+.4f}% · "
              f"일평균 {combined['day_mean_pct']:+.4f}% · "
              f"양수일 {combined['day_positive_ratio']*100:.1f}% · "
              f"p={combined['p_value']:.4f} · {time.time()-t0:.0f}s", flush=True)

    # 게이트는 **일평균과 합계 둘 다 양수**를 요구한다. 일평균만 양수면 "거래가 적은 날은
    #   좋고 많은 날은 나쁘다"는 뜻이라, 실제로 모든 신호를 체결하는 운용에서는 손실이다
    #   (TP5/SL3 실측: 일평균 +0.3842% 인데 합계 −0.0311%).
    passing = [r for r in report["rules"]
               if r["combined"]["day_mean_pct"] > 0
               and r["combined"]["expectancy_pct"] > 0
               and r["combined"]["p_value"] < 0.05]
    report["gate_passed"] = bool(passing)
    report["passing_rules"] = [r["rule"] for r in passing]
    path = os.path.join(_LABEL_ROOT, args.out_name, "_hierarchy_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=float)
    print(json.dumps({"gate": report["gate_passed"], "passing": report["passing_rules"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
