"""S7 — 진입 절 단위 제거 A/B: 빈도를 올릴 곳은 어디인가.

## 문제

챔피언은 하루 **0.433건**만 산다(361건 / DB 833거래일). 열흘 중 엿새는 거래가
아예 없다. 표본이 늘 모자란 근본 원인이다.

절은 34개다. 어느 절이 수익을 만들고 어느 절이 거래만 막는지 모른다.

## 왜 엔진이 아니라 지도인가

절 32개 × 엔진 1런(확장 구간 약 9분) = **5시간**. 게다가 그 32번의 시도 자체가
선택 편의를 만든다(QSP13 실측: 후보 28→58 셀에 편의 ×1.90).

지도는 챔피언 진입 위에서 트레일링을 **그대로 시뮬레이션**한다(`trailing.py` 는
근사가 아니라 계산이다). 32셀이 초 단위로 끝나고, 격자를 실행 전에 고정하므로
전셀 보고가 가능하다(헌법 5항).

지도에서 "빈도는 늘고 건당은 안 떨어지는" 절만 골라 **엔진으로 확인**한다.

## 게이트

| 판정 | 조건 | 뜻 |
|---|---|---|
| **완화 후보** | 진입 증가 + 건당 ≥ 기준선 | 빈도를 공짜로 얻는다 |
| 값 지불 | 진입 증가 + 건당 < 기준선 | 빈도를 기대값으로 샀다 — 폐기 |
| 무효 | 진입 변화 없음 | 다른 절이 이미 막고 있다 |

**빈도를 위해 기대값을 팔지 않는다**(로드맵 §3 단계 4 게이트).

사용:
    python -m ai_strategy_loop.labeling.run_entry_ablation --out-name design_v4
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

from ai_strategy_loop.labeling import champion_clauses as cc
from ai_strategy_loop.labeling.entries import entry_positions
from ai_strategy_loop.labeling.exit_axis import ExitRule, evaluate
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import _load

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 평가용 청산 — 챔피언 진입을 재현한 셀 중 최고(엔진에서도 확정된 B3).
DEFAULT_ARM, DEFAULT_GIVE = 5.0, 2.0


def _stats(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> dict:
    if values.size == 0:
        return {"entries": 0, "days": 0, "entries_per_day": 0.0,
                "expectancy_pct": None, "day_mean_pct": None,
                "day_positive_ratio": None}
    counts = np.bincount(day_codes, minlength=n_days)
    sums = np.bincount(day_codes, weights=values, minlength=n_days)
    active = counts > 0
    daily = sums[active] / counts[active]
    return {"entries": int(values.size), "days": int(active.sum()),
            "entries_per_day": float(values.size / max(n_days, 1)),
            "expectancy_pct": float(values.mean()),
            "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean())}


def _verdict(base: dict, cell: dict, *, tolerance: float) -> str:
    if cell["entries"] <= base["entries"]:
        return "무효"
    if cell["expectancy_pct"] is None or base["expectancy_pct"] is None:
        return "무효"
    # 기대값을 팔지 않는다. 허용 오차는 표본 잡음만 인정한다.
    if cell["expectancy_pct"] >= base["expectancy_pct"] - tolerance:
        return "완화 후보"
    return "값 지불"


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--arm", type=float, default=DEFAULT_ARM)
    parser.add_argument("--give", type=float, default=DEFAULT_GIVE)
    parser.add_argument("--tolerance", type=float, default=0.0,
                        help="건당 허용 하락(%%p). 기본 0 — 기대값을 팔지 않는다")
    parser.add_argument("--tag", default="")
    args = parser.parse_args()

    lane = LANES["tick"]
    trail_col = f"trail_{args.arm:g}_{args.give:g}"
    columns = (["일자", "종목코드", "시분초", "경과", "spread_pct",
                "flag_no_trade", "flag_limit_up", "flag_vi_near"]
               + sorted(cc.required_columns()) + [trail_col])

    t0 = time.time()
    frame = _load(args.out_name, columns, args.warmup).reset_index(drop=True)
    print(f"집행 우주 {len(frame):,}행 · 로딩 {time.time() - t0:.0f}s", flush=True)

    # `trailing_exact` 는 라벨 v4 의 실현값 열을 그대로 읽는다 — 근사가 아니라
    #   경로 시뮬레이션 결과다(하한 계열 `trailing` 과 혼동하면 안 된다).
    rule = ExitRule(family="trailing_exact", horizon=lane.barrier_horizon,
                    arm_pct=args.arm, give_pct=args.give)

    all_days = pd.factorize(frame["일자"].to_numpy())[0]
    n_days = int(all_days.max() + 1) if all_days.size else 0

    def measure(drop: str | None) -> dict:
        mask = cc.champion_mask(frame, drop=drop).to_numpy()
        positions = entry_positions(frame, mask, horizon=lane.barrier_horizon)
        if positions.size == 0:
            return {"entries": 0, "days": 0, "entries_per_day": 0.0,
                    "expectancy_pct": None, "day_mean_pct": None,
                    "day_positive_ratio": None}
        subset = frame.iloc[positions].reset_index(drop=True)
        values = evaluate(subset, rule)
        codes = pd.factorize(subset["일자"].to_numpy())[0]
        return _stats(values, codes, int(codes.max() + 1))

    base = measure(None)
    print(f"\n=== 기준선(챔피언 34절) ===")
    print(f" 진입 {base['entries']:,}건 · 거래일 {base['days']:,} · "
          f"일평균 {base['entries_per_day']:.3f}건 · 건당 {base['expectancy_pct']:+.4f}%",
          flush=True)
    print(f" 우주 거래일 {n_days:,} · 청산 trailing({args.arm:g}/{args.give:g})\n", flush=True)

    rows = []
    for key in cc.DROPPABLE:
        cell = measure(key)
        verdict = _verdict(base, cell, tolerance=args.tolerance)
        rows.append({
            "clause": key, "label": cc.clause_by_key(key).label,
            **cell,
            "entry_gain": cell["entries"] - base["entries"],
            "entry_gain_ratio": (cell["entries"] / base["entries"]
                                 if base["entries"] else None),
            "expectancy_delta_pct": (cell["expectancy_pct"] - base["expectancy_pct"]
                                     if cell["expectancy_pct"] is not None else None),
            "verdict": verdict,
        })

    rows.sort(key=lambda r: (-(r["expectancy_delta_pct"] or -9e9), -r["entry_gain"]))
    print(f"{'절':<22}{'설명':<28}{'진입':>7}{'배':>6}{'건당':>10}{'Δ건당':>10}  판정")
    print("-" * 96)
    for row in rows:
        ratio = f"{row['entry_gain_ratio']:.2f}" if row["entry_gain_ratio"] else "—"
        exp = f"{row['expectancy_pct']:+.4f}%" if row["expectancy_pct"] is not None else "—"
        delta = f"{row['expectancy_delta_pct']:+.4f}" if row["expectancy_delta_pct"] is not None else "—"
        print(f"{row['clause']:<22}{row['label'][:27]:<28}{row['entries']:>7,}"
              f"{ratio:>6}{exp:>10}{delta:>10}  {row['verdict']}")

    relax = [r for r in rows if r["verdict"] == "완화 후보"]
    print(f"\n완화 후보 {len(relax)}개 / 값 지불 "
          f"{sum(1 for r in rows if r['verdict'] == '값 지불')}개 / 무효 "
          f"{sum(1 for r in rows if r['verdict'] == '무효')}개")
    if relax:
        best = max(relax, key=lambda r: r["entry_gain"])
        print(f"\n★ 최대 빈도 이득: {best['clause']} ({best['label']}) — "
              f"진입 {base['entries']:,} → {best['entries']:,} "
              f"({best['entry_gain_ratio']:.2f}배), 건당 {best['expectancy_delta_pct']:+.4f}%p")
        print("  → 엔진으로 확인할 대상이다. 지도에서 통과했다고 채택하지 않는다.")
    else:
        print("\n어떤 절도 공짜로 빼지 못한다 — 빈도는 기대값을 팔아야만 오른다.")

    out_path = os.path.join(_LABEL_ROOT, args.out_name, f"_entry_ablation{args.tag}.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "lane": lane.name, "out_name": args.out_name,
            "exit_rule": f"trailing({args.arm:g}/{args.give:g})",
            "tolerance_pct": args.tolerance,
            "universe_days": n_days,
            "baseline": base, "clauses": rows,
            "relax_candidates": [r["clause"] for r in relax],
            "note": ("지도 축 제거 A/B. 빈도를 위해 기대값을 팔지 않는다. "
                     "완화 후보는 엔진으로 확인해야 채택 대상이 된다."),
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
