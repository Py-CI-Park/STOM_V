"""매도 축 워크포워드 (W4) — 청산 규칙 선택이 표본 밖에서 유지되는가.

W3 재현 게이트를 통과했으므로 탐색이 허가됐다. 다만 QSP13 이 증명한 대로,
**설계 구간 성적은 그대로 믿을 수 없다**. 그래서 첫 시료부터 워크포워드로 잰다.

설계:
  진입 = 챔피언 902/905 고정(탐색하지 않는다 — 이번 라운드는 청산 축만 흔든다)
  청산 = exit_axis 격자 (정확/하한 계열만 후보. 상한은 미래 참조라 제외)
  분할 = 학습[1..k] → 검증[k+1] 앞으로만. 검증은 항상 학습보다 뒤.
  선택 = 학습 구간 일평균 최대 셀 1개
  판정 = 그 셀의 **검증 구간** 일평균. 폴드 과반 양수 + 평균 양수 → PASS

선택 편의:
  후보가 수백만이 아니라 **수십 셀**이다. 그래도 0 은 아니므로 폴드별 학습-검증
  간극을 함께 보고한다(그 간극이 이 규모 탐색의 편의 크기다).

사용:
    python -m ai_strategy_loop.labeling.run_exit_walkforward --out-name design_v4
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
from ai_strategy_loop.labeling.exit_axis import default_grid, evaluate
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import RULES, _load
from ai_strategy_loop.labeling.run_reproduction_gate import _champion_columns
from ai_strategy_loop.labeling.trailing import TRAILING_GRID
from ai_strategy_loop.labeling.verify_human_strategy import _mask_902, _mask_905
from ai_strategy_loop.labeling.walkforward import MIN_TRAIN_DAYS, MIN_VALID_DAYS, make_folds

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: QSP13 실측 선택 편의(%p) — 수백만 조합 기준. 수십 셀이면 훨씬 작지만
#:   보수적으로 함께 표기해 "차감해도 양수인가"를 볼 수 있게 한다.
SELECTION_BIAS_PCT = 0.6225


def _day_mean(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> float:
    if values.size == 0:
        return float("nan")
    counts = np.bincount(day_codes, minlength=n_days)
    sums = np.bincount(day_codes, weights=values, minlength=n_days)
    active = counts > 0
    if not active.any():
        return float("nan")
    return float((sums[active] / counts[active]).mean())


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args()

    lane = LANES["tick"]
    hits = sorted({c for rule in RULES for c in rule[2:]})
    envelopes = [f"mfe_{h}" for h in (30, 60, 120, 300, 600)]
    horizons = [f"frA_{h}" for h in lane.horizons] + [f"frB_{h}" for h in lane.horizons]
    trail_cols = [f"trail_{a:g}_{g:g}" for a, g in TRAILING_GRID]
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "spread_pct",
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]

    t0 = time.time()
    frame = _load(args.out_name,
                  base + hits + envelopes + horizons + sorted(_champion_columns()) + trail_cols,
                  args.warmup).reset_index(drop=True)
    mask = (_mask_902(frame) | _mask_905(frame)).to_numpy()
    positions = entry_positions(frame, mask, horizon=lane.barrier_horizon)
    subset = frame.iloc[positions].reset_index(drop=True)
    print(f"챔피언 진입 {positions.size:,}건 · 로딩 {time.time()-t0:.0f}s", flush=True)

    days = np.sort(pd.unique(subset["일자"].to_numpy()))
    folds = make_folds(days, n_folds=args.folds, min_train_days=MIN_TRAIN_DAYS)
    if not folds:
        print(f"[불가] 폴드를 만들 수 없다 — 거래일 {len(days)}일 "
              f"(최소 {MIN_TRAIN_DAYS + MIN_VALID_DAYS}일 필요)", flush=True)
        return

    # 판정 가능한 셀만 후보로 둔다 — 상한(미래 참조)은 선택지에서 제외.
    candidates = []
    for rule in default_grid():
        if rule.exactness == "upper_bound":
            continue
        try:
            candidates.append((rule, evaluate(subset, rule)))
        except (KeyError, ValueError):
            continue
    print(f"후보 셀 {len(candidates)}개 · 폴드 {len(folds)}개 · 거래일 {len(days)}일", flush=True)

    day_of_row = subset["일자"].to_numpy()
    results = []
    for index, (train_idx, valid_idx) in enumerate(folds, start=1):
        train_days = set(days[train_idx].tolist())
        valid_days = set(days[valid_idx].tolist())
        train_rows = np.isin(day_of_row, list(train_days))
        valid_rows = np.isin(day_of_row, list(valid_days))
        tr_codes = pd.factorize(day_of_row[train_rows])[0]
        va_codes = pd.factorize(day_of_row[valid_rows])[0]
        n_tr = int(tr_codes.max() + 1) if tr_codes.size else 0
        n_va = int(va_codes.max() + 1) if va_codes.size else 0

        scored = [
            (rule, _day_mean(values[train_rows], tr_codes, n_tr))
            for rule, values in candidates
        ]
        scored = [(r, s) for r, s in scored if not np.isnan(s)]
        if not scored or n_va == 0:
            continue
        best_rule, train_score = max(scored, key=lambda item: item[1])
        best_values = next(v for r, v in candidates if r is best_rule)
        valid_score = _day_mean(best_values[valid_rows], va_codes, n_va)

        results.append({
            "fold": index,
            "train_days": len(train_days), "valid_days": len(valid_days),
            "chosen": best_rule.label, "exactness": best_rule.exactness,
            "train_day_mean_pct": train_score,
            "valid_day_mean_pct": valid_score,
            "gap_pct": train_score - valid_score,
        })
        print(f"  폴드 {index}: 선택={best_rule.label:<32} "
              f"학습={train_score:+.4f}% → 표본밖={valid_score:+.4f}% "
              f"(간극 {train_score - valid_score:+.4f}%p)", flush=True)

    if not results:
        print("[불가] 유효 폴드가 없다.", flush=True)
        return

    valid_scores = np.array([r["valid_day_mean_pct"] for r in results], dtype=np.float64)
    positive = int((valid_scores > 0).sum())
    mean_valid = float(np.nanmean(valid_scores))
    mean_gap = float(np.nanmean([r["gap_pct"] for r in results]))
    verdict = "PASS" if (mean_valid > 0 and positive * 2 > len(results)) else "FAIL"

    print(f"\n=== 매도 축 워크포워드: {verdict} ===", flush=True)
    print(f" 표본 밖 일평균 = {mean_valid:+.4f}% · 양수 폴드 {positive}/{len(results)}", flush=True)
    print(f" 학습-표본밖 간극(이 규모 탐색의 편의) = {mean_gap:+.4f}%p", flush=True)
    print(f" QSP13 대규모 편의({SELECTION_BIAS_PCT}%p) 차감 시 = "
          f"{mean_valid - SELECTION_BIAS_PCT:+.4f}%", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name, "_exit_walkforward.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "verdict": verdict, "entry": "champion_902_905_fixed",
            "candidates": len(candidates), "folds": results,
            "mean_valid_day_mean_pct": mean_valid,
            "positive_folds": positive,
            "mean_train_valid_gap_pct": mean_gap,
            "selection_bias_pct_large_scale": SELECTION_BIAS_PCT,
            "note": "상한(미래 참조) 셀은 후보에서 제외했다. 진입은 고정(청산 축만 흔듦).",
        }, handle, ensure_ascii=False, indent=1)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
