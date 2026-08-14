"""사용자 브레인스토밍 아이디어 실증 — 시초 첫 2/5/10분 한정 진입·소수 종목·높은 손익비.

설계 원칙 (QSP13 교훈 반영):
  - **탐색·최적화 없음.** 사전 고정 격자(시간창 7 × 필터 2 × 배리어 6 = 84셀)만 평가한다.
    셀을 고른 뒤 보고하는 것이 아니라 84셀 전부를 보고한다 — 선택 편의 원천 차단.
  - 필터 임계는 튜닝하지 않는다. 902/905 실전 조건의 3.0 을 그대로 쓴다(사전 고정).
  - 진입 단위 교정(entries) 적용 — 엔진과 같은 단위로 센다.

사용:
    python -m ai_strategy_loop.labeling.run_idea_scan --out-name design_v3
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

from ai_strategy_loop.labeling.entries import entry_positions
from ai_strategy_loop.labeling.frontier import row_values
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import RULES, _load
from scipy import stats

#: 시간창(HHMMSS, [시작, 끝)) — 사전 고정. 워밍업 60틱 탓에 실질 시작은 09:01 부근.
WINDOWS = (
    ("전체(09:01~30)", 90100, 93000),
    ("누적 ~2분", 90100, 90200),
    ("누적 ~5분", 90100, 90500),
    ("누적 ~10분", 90100, 91000),
    ("구간 2~5분", 90200, 90500),
    ("구간 5~10분", 90500, 91000),
    ("구간 10~30분", 91000, 93000),
)

#: 소수-종목 필터 — 902/905 가 실전에서 쓰는 급증 임계(3.0)를 그대로. 튜닝 금지.
FILTER_COLUMN = "초당거래대금배율_30"
FILTER_THRESHOLD = 3.0


def _day_metrics(values: np.ndarray, day_codes: np.ndarray) -> dict:
    frame = pd.DataFrame({"v": values, "d": day_codes})
    daily = frame.groupby("d")["v"].mean().to_numpy()
    if len(daily) < 2:
        return {"days": int(len(daily)), "day_mean_pct": float("nan"),
                "day_positive_ratio": float("nan"), "p_one_sided": 1.0}
    t_stat, p_two = stats.ttest_1samp(daily, 0.0)
    return {
        "days": int(len(daily)),
        "day_mean_pct": float(daily.mean()),
        "day_positive_ratio": float((daily > 0).mean()),
        "p_one_sided": float(p_two / 2 if t_stat > 0 else 1.0),
    }


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v3")
    parser.add_argument("--warmup", type=int, default=60)
    args = parser.parse_args()

    lane = LANES["tick"]
    timeout_label = f"frA_{lane.path_window}"
    horizon = lane.barrier_horizon
    hits = sorted({c for rule in RULES for c in rule[2:]})
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "현재가", "spread_pct",
            timeout_label, "flag_no_trade", "flag_limit_up", "flag_vi_near"]

    t0 = time.time()
    frame = _load(args.out_name, base + hits + [FILTER_COLUMN], args.warmup)
    frame = frame.reset_index(drop=True)
    clock = frame["시분초"].to_numpy()
    day_all = frame["일자"].to_numpy()
    n_days_total = int(pd.unique(day_all).size)
    surge = frame[FILTER_COLUMN].to_numpy(dtype=np.float64)
    print(f"집행 우주 {len(frame):,}행 · {n_days_total}일 · 로딩 {time.time()-t0:.0f}s", flush=True)

    # 배리어 6규칙의 행별 수익률을 한 번만 벡터화
    returns = {
        (tp_pct, sl_pct): row_values(frame, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                                     horizon=horizon, timeout_label=timeout_label)
        for tp_pct, sl_pct, tp, sl in RULES
    }

    cells = []
    for win_name, start, end in WINDOWS:
        window_mask = (clock >= start) & (clock < end)
        for filter_name, mask in (
            ("무필터", window_mask),
            (f"배율≥{FILTER_THRESHOLD}", window_mask & (surge >= FILTER_THRESHOLD)),
        ):
            t1 = time.time()
            positions = entry_positions(frame, mask, horizon=horizon)
            if positions.size == 0:
                continue
            day_codes = pd.factorize(day_all[positions])[0]
            for (tp_pct, sl_pct), values_all in returns.items():
                values = values_all[positions]
                cell = {
                    "window": win_name, "filter": filter_name,
                    "rule": f"TP+{tp_pct:g}/SL-{sl_pct:g}",
                    "rr": round(tp_pct / sl_pct, 2),
                    "n_entries": int(positions.size),
                    "per_day": round(positions.size / n_days_total, 2),
                    "expectancy_pct": float(np.mean(values)),
                    **_day_metrics(values, day_codes),
                }
                cells.append(cell)
            print(f"{win_name} · {filter_name}: 진입 {positions.size:,} "
                  f"({time.time()-t1:.0f}s)", flush=True)

    out = {"universe_rows": int(len(frame)), "n_days": n_days_total,
           "horizon": horizon, "timeout_label": timeout_label,
           "filter": {"column": FILTER_COLUMN, "threshold": FILTER_THRESHOLD},
           "note": "사전 고정 84셀 전수 보고 — 탐색·튜닝 없음(선택 편의 차단)",
           "cells": cells}
    out_path = os.path.join(os.path.dirname(__file__), "..", "state", "labels",
                            args.out_name, "_idea_scan.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"저장: {os.path.abspath(out_path)} · 셀 {len(cells)}개 · 총 {time.time()-t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()
