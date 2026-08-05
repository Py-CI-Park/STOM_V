"""날 차원 실행기 — 아침 정보로 유리한 날을 고를 수 있는지 실측한다.

사용:
    python -m ai_strategy_loop.labeling.run_day_dimension --feature-end 90500 --entry-start 90500
"""

from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

from ai_strategy_loop.labeling.day_dimension import day_table, rank_day_features
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v2")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--feature-end", type=int, default=90500)
    parser.add_argument("--entry-start", type=int, default=90500)
    parser.add_argument("--rule", default="TP2.0/SL1.0")
    args = parser.parse_args()

    lane = LANES[args.lane]
    tp_pct = float(args.rule.split("/")[0].removeprefix("TP"))
    sl_pct = float(args.rule.split("/")[1].removeprefix("SL"))
    tp_col, sl_col = next((t, s) for a, b, t, s in RULES
                          if abs(a - tp_pct) < 1e-9 and abs(b - sl_pct) < 1e-9)
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]

    t0 = time.time()
    frame = _load(args.out_name, base + [tp_col, sl_col] + variables, args.warmup)
    print(f"집행 우주 {len(frame):,}행 · {time.time()-t0:.0f}s", flush=True)

    rule = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp_col, sl=sl_col,
                horizon=lane.barrier_horizon, timeout_label=timeout_label)
    table = day_table(frame, feature_end=args.feature_end, entry_start=args.entry_start, **rule)
    values = table["기대값"].to_numpy()
    print(f"\n날 {len(table)}일 · 일평균 기대값 {values.mean():+.4f}% · "
          f"중앙값 {np.median(values):+.4f}% · 양수 일 {(values > 0).sum()}/{len(values)} "
          f"({(values > 0).mean()*100:.1f}%)", flush=True)

    ranked = rank_day_features(table, buckets=5)
    print("\n=== 아침 특징별 그날 성적 (상위분위 − 하위분위) ===")
    print(ranked.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))

    payload = {
        "rule": args.rule, "feature_end": args.feature_end, "entry_start": args.entry_start,
        "days": int(len(table)), "day_mean_pct": float(values.mean()),
        "day_positive_ratio": float((values > 0).mean()),
        "features": ranked.to_dict(orient="records"),
        "significant": ranked[(ranked["p"] < 0.05) & (ranked["차이"] > 0)]["특징"].tolist(),
    }
    path = os.path.join(_LABEL_ROOT, args.out_name, "_day_dimension_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=float)
    print(f"\n유의한 아침 특징: {payload['significant'] or '없음'}")
    print("saved:", os.path.abspath(path))


if __name__ == "__main__":
    main()
