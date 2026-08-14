"""소수-종목 아이디어의 정면 실증 — 일별 횡단면 상위 K 선별 (사전 고정 24셀).

임계 필터("배율 ≥ 3.0")와 달리, 인간이 실제로 하는 "오늘 가장 강한 놈만 골라 산다"는
**횡단면 순위** 구조다. QSP10~13 의 행 단위 임계 탐색은 이 구조를 한 번도 시험하지 않았다.

설계 (선택 편의 차단):
  - 순위 키 = 초당거래대금배율_30 (902/905 실전 신호 — 사전 고정, 튜닝 금지)
  - K ∈ {1, 3} · 창 ∈ {~2분, ~5분} · 배리어 6규칙 = 24셀 전수 보고
  - 진입 = 창 안에서 배율 ≥ 3.0 이 처음 성립한 초 (종목당 1회, 일별 상위 K 종목만)

사용:
    python -m ai_strategy_loop.labeling.run_idea_topk --out-name design_v3
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

from ai_strategy_loop.labeling.frontier import row_values
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import RULES, _load
from scipy import stats

WINDOWS = (("~2분", 90100, 90200), ("~5분", 90100, 90500))
TOP_KS = (1, 3)
RANK_COLUMN = "초당거래대금배율_30"
TRIGGER = 3.0


def _day_metrics(values: np.ndarray, day_codes: np.ndarray) -> dict:
    daily = pd.DataFrame({"v": values, "d": day_codes}).groupby("d")["v"].mean().to_numpy()
    if len(daily) < 2:
        return {"days": int(len(daily)), "day_mean_pct": float("nan"),
                "day_positive_ratio": float("nan"), "p_one_sided": 1.0}
    t_stat, p_two = stats.ttest_1samp(daily, 0.0)
    return {"days": int(len(daily)), "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean()),
            "p_one_sided": float(p_two / 2 if t_stat > 0 else 1.0)}


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
    frame = _load(args.out_name, base + hits + [RANK_COLUMN], args.warmup)
    frame = frame.reset_index(drop=True)
    clock = frame["시분초"].to_numpy()
    surge = frame[RANK_COLUMN].to_numpy(dtype=np.float64)
    print(f"우주 {len(frame):,}행 · 로딩 {time.time()-t0:.0f}s", flush=True)

    returns = {(tp_pct, sl_pct): row_values(frame, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp,
                                            sl=sl, horizon=horizon, timeout_label=timeout_label)
               for tp_pct, sl_pct, tp, sl in RULES}

    cells = []
    for win_name, start, end in WINDOWS:
        # 창 안에서 배율 트리거가 처음 성립한 초 — (일자, 종목) 당 1행
        mask = (clock >= start) & (clock < end) & (surge >= TRIGGER)
        idx = np.flatnonzero(mask)
        sub = pd.DataFrame({
            "row": idx,
            "일자": frame["일자"].to_numpy()[idx],
            "종목코드": frame["종목코드"].to_numpy()[idx],
            "시분초": clock[idx],
            "surge": surge[idx],
        }).sort_values(["일자", "종목코드", "시분초"])
        first = sub.groupby(["일자", "종목코드"], as_index=False).first()
        for k in TOP_KS:
            picked = (first.sort_values(["일자", "surge"], ascending=[True, False])
                      .groupby("일자").head(k))
            positions = picked["row"].to_numpy()
            day_codes = pd.factorize(picked["일자"].to_numpy())[0]
            for (tp_pct, sl_pct), values_all in returns.items():
                values = values_all[positions]
                cells.append({
                    "window": win_name, "top_k": k,
                    "rule": f"TP+{tp_pct:g}/SL-{sl_pct:g}", "rr": round(tp_pct / sl_pct, 2),
                    "n_entries": int(len(positions)),
                    "expectancy_pct": float(np.mean(values)),
                    **_day_metrics(values, day_codes),
                })
            print(f"{win_name} top{k}: 진입 {len(positions):,}", flush=True)

    out = {"rank_column": RANK_COLUMN, "trigger": TRIGGER,
           "note": "사전 고정 24셀 전수 보고 — 횡단면 상위 K, 탐색·튜닝 없음",
           "cells": cells}
    out_path = os.path.join(os.path.dirname(__file__), "..", "state", "labels",
                            args.out_name, "_idea_topk.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
