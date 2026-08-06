"""매도 축 격자 실행기 (W3) — 사전 고정 격자를 전셀 보고한다.

사용:
    python -m ai_strategy_loop.labeling.run_exit_axis --out-name design_v3

규율:
  - 격자는 `exit_axis.default_grid()` 로 **사전 고정**이며 전셀을 보고한다.
    좋은 셀만 골라 보고하는 순간 그게 선택 편의다.
  - 진입은 무필터(집행 우주 전체)로 고정한다 — 이번 라운드가 재는 것은
    **청산 축의 여지**이지 진입 조건이 아니다. 두 축을 동시에 흔들면
    어느 쪽이 효과를 냈는지 영구히 알 수 없다.
  - 결과에는 exactness(정확/근사)를 그대로 실어 보낸다.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

from ai_strategy_loop.labeling.exit_axis import default_grid, evaluate_grid
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.trailing import TRAILING_GRID
from ai_strategy_loop.labeling.run_p3 import RULES, _load

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--warmup", type=int, default=60)
    args = parser.parse_args()

    lane = LANES[args.lane]
    hits = sorted({c for rule in RULES for c in rule[2:]})
    envelopes = [f"mfe_{h}" for h in (30, 60, 120, 300, 600)]
    horizons = [f"frA_{h}" for h in lane.horizons] + [f"frB_{h}" for h in lane.horizons]
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    trail_cols = [f"trail_{a:g}_{g:g}" for a, g in TRAILING_GRID]

    t0 = time.time()
    frame = _load(args.out_name, base + hits + envelopes + horizons + trail_cols,
                  args.warmup)
    frame = frame.reset_index(drop=True)
    print(f"집행 우주 {len(frame):,}행 · 로딩 {time.time()-t0:.0f}s", flush=True)

    grid = default_grid()
    rows = evaluate_grid(frame, grid)
    print(f"격자 {len(grid)}셀 전수 평가 · {time.time()-t0:.0f}s", flush=True)

    for row in sorted(rows, key=lambda r: -(r.get("day_mean_pct") or -9e9)):
        if not row.get("available"):
            print(f"  [불가] {row['rule']} — {row.get('reason')}", flush=True)
            continue
        print(
            f"  {row['rule']:<34} [{row['exactness']:<11}] "
            f"n={row['n']:>7,} 일평균={row.get('day_mean_pct', float('nan')):+.4f}% "
            f"흑자일={row.get('day_positive_ratio', float('nan')):.3f}",
            flush=True,
        )

    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_exit_axis_grid.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "lane": lane.name,
            "universe_rows": int(len(frame)),
            "note": "사전 고정 격자 전셀 보고 · 진입 무필터(청산 축만 흔든다)",
            "cells": rows,
        }, handle, ensure_ascii=False, indent=1)
    print(f"저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
