"""W5-a min 레인 최초 판독 — 155일치 라벨을 한 번도 읽지 않았다.

배경: `min_design_v2`(545MB · 155일)는 QSP10 에서 만들어졌지만 그 뒤 모든 라운드가
tick 레인만 봤다. "만들어 두고 안 쓴 자산"은 연구 자산이 아니라 **미결 부채**다.
이 러너가 그 부채를 갚는다.

## 무엇을 재는가

tick 과 **같은 자**로 잰다 — 같은 집행 우주, 같은 청산 규칙군, 같은 정확도 분류.
그래야 "min 이 tick 보다 나은가"라는 질문에 답할 수 있다.

  1. 기저 — 무필터 우주에서 각 청산 규칙의 건당 기대값
  2. 표현력 — min 라벨이 어떤 규칙군을 표현할 수 있는가(v2 는 트레일링 실현값이 없다)
  3. 대조 — tick 무필터 기저와 나란히

## 판독 규율

- **기저가 음수인 것은 결함이 아니라 사실이다.** 왕복비용을 넘는 무조건적 우위는
  존재하지 않는다. 기저를 알아야 조건이 만든 초과분을 잴 수 있다.
- 상한(미래 참조) 셀은 천장으로만 읽는다.
- min 은 시간 단위가 분이다. tick 의 초 지평과 숫자를 직접 비교하지 않는다.

사용:
    python -m ai_strategy_loop.labeling.run_min_lane_read --out-name min_design_v2
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.exit_axis import ExitRule, evaluate
from ai_strategy_loop.labeling.lanes import BARRIERS_DOWN, BARRIERS_UP, LANES
from ai_strategy_loop.labeling.run_p3 import _load
from ai_strategy_loop.labeling.trailing import TRAILING_GRID

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def min_grid(lane) -> list[ExitRule]:
    """min 레인 청산 격자 — 지평은 레인 체크포인트(분)를 그대로 쓴다.

    tick 격자를 그대로 베끼지 않는 이유: 지평 600 은 tick 에서 10분이지만
    min 에서는 600분(하루보다 길다)이다. 단위를 섞으면 표가 거짓말을 한다.
    """
    rules: list[ExitRule] = []
    for horizon in lane.checkpoints:
        rules.append(ExitRule("time_stop", horizon=horizon))
        rules.append(ExitRule("mfe_capture", horizon=horizon))
    for tp in BARRIERS_UP:
        for sl in BARRIERS_DOWN:
            rules.append(ExitRule("barrier", horizon=lane.barrier_horizon,
                                  tp_pct=tp, sl_pct=sl))
    for arm, give in TRAILING_GRID:
        rules.append(ExitRule("trailing_exact", arm_pct=arm, give_pct=give))
        rules.append(ExitRule("trailing", horizon=lane.barrier_horizon,
                              arm_pct=arm, give_pct=give))
    return rules


def _day_stats(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> dict:
    if values.size == 0:
        return {"n": 0, "expectancy_pct": float("nan"), "day_mean_pct": float("nan"),
                "day_positive_ratio": float("nan"), "days": 0}
    counts = np.bincount(day_codes, minlength=n_days)
    sums = np.bincount(day_codes, weights=values, minlength=n_days)
    active = counts > 0
    daily = sums[active] / counts[active]
    return {"n": int(values.size), "expectancy_pct": float(values.mean()),
            "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean()), "days": int(len(daily))}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="min_design_v2")
    parser.add_argument("--warmup", type=int, default=5,
                        help="min 레인 워밍업(분). tick 의 60초와 다른 단위다")
    parser.add_argument("--sample-days", type=int, default=0,
                        help="0 이면 전부. 연기 시험용으로 앞 N 일만 읽는다")
    args = parser.parse_args()

    lane = LANES["min"]
    rules = min_grid(lane)

    envelopes = [f"mfe_{h}" for h in lane.checkpoints]
    horizons = [f"frA_{h}" for h in lane.horizons] + [f"frB_{h}" for h in lane.horizons]
    hits = [f"hit_up_{t:g}" for t in BARRIERS_UP] + [f"hit_dn_{s:g}" for s in BARRIERS_DOWN]
    trail_cols = [f"trail_{a:g}_{g:g}" for a, g in TRAILING_GRID]
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]

    t0 = time.time()
    frame = _load(args.out_name, base + hits + envelopes + horizons + trail_cols,
                  args.warmup)
    if args.sample_days:
        days = sorted(frame["일자"].unique())[:args.sample_days]
        frame = frame[frame["일자"].isin(days)]
    frame = frame.reset_index(drop=True)
    print(f"min 집행 우주 {len(frame):,}행 · 로딩 {time.time()-t0:.0f}s", flush=True)

    present = set(frame.columns)
    missing_trailing = [c for c in trail_cols if c not in present]
    if missing_trailing:
        print(f"[표현력] 트레일링 실현값 열 없음({len(missing_trailing)}개) — "
              f"라벨 v4 재빌드가 필요하다. 정확 트레일링 셀은 건너뛴다.", flush=True)

    day_codes = pd.factorize(frame["일자"].to_numpy())[0]
    n_days = int(day_codes.max() + 1) if day_codes.size else 0

    cells = []
    for rule in rules:
        try:
            values = evaluate(frame, rule)
        except (KeyError, ValueError) as exc:
            cells.append({"rule": rule.label, "family": rule.family,
                          "exactness": rule.exactness, "available": False,
                          "reason": str(exc)[:120]})
            continue
        stats = _day_stats(values, day_codes, n_days)
        cells.append({"rule": rule.label, "family": rule.family,
                      "exactness": rule.exactness, "available": True, **stats})

    judgeable = [c for c in cells if c.get("available")
                 and c["exactness"] in ("exact", "lower_bound")]
    positives = [c for c in judgeable if c["expectancy_pct"] > 0]

    print(f"\n=== min 레인 기저 (무필터 · {n_days}일) ===", flush=True)
    ranked = sorted((c for c in cells if c.get("available")),
                    key=lambda c: -c["expectancy_pct"])
    for cell in ranked[:16]:
        mark = "★" if cell in positives else " "
        print(f" {mark}{cell['rule']:<34} [{cell['exactness']:<11}] "
              f"n={cell['n']:>8,} 건당={cell['expectancy_pct']:+.4f}% "
              f"일평균={cell['day_mean_pct']:+.4f}% 흑자일={cell['day_positive_ratio']:.3f}",
              flush=True)

    print(f"\n판정 가능 셀 {len(judgeable)}개 중 양수 {len(positives)}개.", flush=True)
    if not positives:
        print("무필터 기저는 전부 음수다 — 정상이다(왕복비용). 조건이 만드는 "
              "초과분을 여기서부터 재면 된다.", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_min_lane_read.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "lane": "min",
            "out_name": args.out_name,
            "universe_rows": int(len(frame)),
            "days": n_days,
            "warmup_minutes": args.warmup,
            "trailing_available": not missing_trailing,
            "cells": cells,
            "judgeable_count": len(judgeable),
            "positive_count": len(positives),
            "note": ("무필터 기저다. 음수가 정상이며, 조건이 만든 초과분을 재는 "
                     "기준선으로 쓴다. min 지평은 분 단위라 tick 초 지평과 "
                     "직접 비교하지 않는다."),
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
