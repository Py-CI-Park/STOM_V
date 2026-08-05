"""지도 적정성 검증 — 사용자 902/905 조건을 지도 위에 그대로 얹어 본다.

가장 정보량이 큰 질문: **흑자가 증명된 전략을 우리 지도가 볼 수 있는가?**

- 볼 수 있다(일평균 양수) → 지도·특징 공간은 충분하고, 탐색이 아직 못 찾은 것이다.
- 볼 수 없다(음수) → 지도 자체가 현실과 어긋난다(우주·라벨·특징 어딘가). 탐색을 더
  돌릴 이유가 없고 지도를 고쳐야 한다.

902 조건 중 `당일거래대금각도(30)` 은 엔진 정의를 확정하지 못해 제외했다(§QSP11).
그 외는 실코드 그대로 옮긴다.
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
from scipy import stats

from ai_strategy_loop.labeling.frontier import row_values
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import MIN_VARIABLES, RULES, TICK_VARIABLES, _load

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")


def _mask_902(frame: pd.DataFrame) -> pd.Series:
    """`Tick_B_902_905_Study_2` 의 09:00~09:02 분기(당일거래대금각도만 제외)."""
    return (
        (frame["시분초"] < 90200)
        & (frame["현재가"] > 1000) & (frame["현재가"] <= 50000)
        & (frame["등락율"] > 1.0) & (frame["등락율"] <= 8.0)
        & (frame["고저평균대비등락율"] > 0)
        & (frame["라운드피겨위5호가이내"] == 0)
        & (frame["시가총액"] < 3000)
        & (frame["시가등락율"] >= 2.0) & (frame["시가등락율"] < 4.0)
        & (frame["시가대비등락율"] >= 0.5) & (frame["시가대비등락율"] < 6.0)
        & (frame["초당순매수금액"] > 1) & (frame["초당순매수금액"] < 1000)
        & (frame["일중위치"] > 0.8)
        & (frame["전일비"] > 0) & (frame["전일동시간비"] > 0)
        & (frame["회전율"] > 2)
        & (frame["당일거래대금"] > 500)
        & (frame["초당거래대금배율_30"] > 3.0)
        & (frame["매수흐름_매도잔량비"] > 0.20)
        & (frame["잔량비"] > 0.10) & (frame["잔량비"] < 2.0)
        & (frame["체결강도"] >= 50) & (frame["체결강도"] <= 300)
    )


def _mask_905(frame: pd.DataFrame) -> pd.Series:
    """09:02~09:05 분기 — 같은 골격, 다른 임계."""
    return (
        (frame["시분초"] >= 90200) & (frame["시분초"] < 90500)
        & (frame["현재가"] > 1000) & (frame["현재가"] <= 30000)
        & (frame["등락율"] > 2.0) & (frame["등락율"] <= 15.0)
        & (frame["고저평균대비등락율"] > 0)
        & (frame["라운드피겨위5호가이내"] == 0)
        & (frame["초당거래대금직전비"] > 1.0)
        & (frame["시가총액"] < 3000)
        & (frame["시가등락율"] >= 0.0) & (frame["시가등락율"] < 8.0)
        & (frame["시가대비등락율"] >= 3.0) & (frame["시가대비등락율"] < 8.0)
        & (frame["초당순매수금액"] > 1) & (frame["초당순매수금액"] < 1000)
        & (frame["일중위치"] > 0.8)
        & (frame["전일비"] > 5) & (frame["전일동시간비"] > 0)
        & (frame["회전율"] > 1.5)
        & (frame["당일거래대금"] > 5000)
        & (frame["초당거래대금배율_30"] > 2.0)
        & (frame["매수흐름_매도잔량비"] > 0.30)
        & (frame["체결강도"] >= 50) & (frame["체결강도"] <= 300)
    )


def _evaluate(frame: pd.DataFrame, mask: np.ndarray, values: np.ndarray,
              day_codes: np.ndarray, n_days: int, label: str) -> dict:
    count = int(mask.sum())
    if count == 0:
        print(f"{label}: 0건 — 지도에서 이 조건에 걸리는 시점이 없다")
        return {"label": label, "rows": 0}
    picked = values[mask]
    codes = day_codes[mask]
    counts = np.bincount(codes, minlength=n_days)
    sums = np.bincount(codes, weights=picked, minlength=n_days)
    active = counts > 0
    daily = sums[active] / counts[active]
    t_stat, p_two = stats.ttest_1samp(daily, 0.0) if len(daily) >= 20 else (0.0, 1.0)
    result = {
        "label": label, "rows": count, "days": int(len(daily)),
        "per_day": round(count / max(n_days, 1), 2),
        "expectancy_pct": float(picked.mean()),
        "day_mean_pct": float(daily.mean()),
        "day_positive_ratio": float((daily > 0).mean()),
        "p_value": float(p_two / 2 if t_stat > 0 else 1.0),
    }
    print(f"{label}: n={count:,} (하루 {result['per_day']}) · 일수 {result['days']} · "
          f"기대값 {result['expectancy_pct']:+.4f}% · 일평균 {result['day_mean_pct']:+.4f}% · "
          f"양수일 {result['day_positive_ratio']*100:.1f}% · p={result['p_value']:.4f}",
          flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=sorted(LANES), default="tick")
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--warmup", type=int, default=60)
    args = parser.parse_args()

    lane = LANES[args.lane]
    variables = TICK_VARIABLES if lane.name == "tick" else MIN_VARIABLES
    timeout_label = f"frA_{lane.path_window}"
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            "라운드피겨위5호가이내", timeout_label,
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    hits = sorted({c for rule in RULES for c in rule[2:]})

    t0 = time.time()
    frame = _load(args.out_name, base + hits + variables, args.warmup).reset_index(drop=True)
    print(f"집행 우주 {len(frame):,}행 · {time.time()-t0:.0f}s\n", flush=True)

    day_codes, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    mask_902 = _mask_902(frame).to_numpy()
    mask_905 = _mask_905(frame).to_numpy()
    both = mask_902 | mask_905

    report = {"lane": lane.name, "rows": int(len(frame)), "rules": []}
    for tp_pct, sl_pct, tp, sl in RULES:
        if tp not in frame.columns:
            continue
        values = row_values(frame, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                            horizon=lane.barrier_horizon, timeout_label=timeout_label)
        print(f"--- TP{tp_pct}/SL{sl_pct} (우주 전체 {values.mean():+.4f}%) ---")
        entry = {"rule": f"TP{tp_pct}/SL{sl_pct}",
                 "universe_expectancy_pct": float(values.mean()),
                 "results": [
                     _evaluate(frame, mask_902, values, day_codes, n_days, "902(09:00~02)"),
                     _evaluate(frame, mask_905, values, day_codes, n_days, "905(09:02~05)"),
                     _evaluate(frame, both, values, day_codes, n_days, "902+905 합집합"),
                 ]}
        report["rules"].append(entry)
        print(flush=True)

    path = os.path.join(_LABEL_ROOT, args.out_name, "_human_strategy_report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=float)
    print("saved:", os.path.abspath(path))


if __name__ == "__main__":
    main()
