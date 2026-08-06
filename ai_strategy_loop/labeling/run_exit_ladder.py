"""매도 축 검증 사다리 — 엔진에 올리기 **전에** 설계 구간에서 거를 수 있는 것들.

엔진 런은 팔 하나에 수 분~수십 분이고, 홀드아웃은 한 번뿐인 카드다. 과최적이거나
국면에 기댄 청산 규칙을 거기서 태우면 안 된다. 아래 셋은 전부 지도 위에서 답이 난다.

| 단 | 무엇을 잡나 | 정확도 |
|---|---|---|
| ① 격자 고원 | 이웃 셀(arm±/give±)에서도 살아남는가 — 절벽이면 과최적 | 정확 |
| ② 비용 스트레스 | 왕복 비용이 1.5배여도 흑자인가 | **근사**(정책 고정) |
| ③ 국면 절단 | 기간을 나눠도 일관되는가 | 정확 |

## ② 가 근사인 이유 — 숨기지 않는다

라벨의 트레일링 실현값은 비용이 **이미 반영된** 값이다. 비용을 올리면 무장 시점이
늦어져 청산 시점 자체가 달라질 수 있는데, 라벨만으로는 그 재시뮬레이션을 할 수 없다.
그래서 이 단은 **"같은 청산이 일어났다면"** 을 가정하고 값만 내린다. 답하는 질문은
"규칙이 비용에 얼마나 여유가 있나"이지 "비용이 오르면 규칙이 어떻게 바뀌나"가 아니다.

정확히 재려면 라벨을 비용 1.5배로 다시 구워야 한다(`label_spec.COST_*`).

사용:
    python -m ai_strategy_loop.labeling.run_exit_ladder --out-name design_v4 \\
        --rule "trailing(arm+5/give2)"
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.entries import entry_positions
from ai_strategy_loop.labeling.exit_axis import ExitRule, evaluate
from ai_strategy_loop.labeling.lanes import LANES
from ai_strategy_loop.labeling.run_p3 import RULES, _load
from ai_strategy_loop.labeling.trailing import resolve_grid
from ai_strategy_loop.labeling.run_reproduction_gate import _champion_columns
from ai_strategy_loop.labeling.verify_human_strategy import _mask_902, _mask_905

_LABEL_ROOT = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 비용 스트레스 배수. 1.5 = 슬리피지·체결 열위를 절반 더 얹는다.
COST_STRESS = 1.5

#: 국면 절단 조각 수 — 4분할이면 조각당 약 3~4개월(355 거래일 기준).
REGIME_SEGMENTS = 4

#: 고원 판정 — 이웃 셀 중 이 비율 이상이 양수여야 "고원"이다.
PLATEAU_MIN_POSITIVE_RATIO = 0.6

_RULE = re.compile(r"^trailing\(arm\+([0-9.]+)/give([0-9.]+)\)$")


def _stats(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> dict:
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


def neighbours(arm: float, give: float,
               grid: tuple[tuple[float, float], ...]) -> list[tuple[float, float]]:
    """격자에서 (arm, give) 의 이웃 — 한 칸 옆(대각 포함, 자기 자신 제외)."""
    arms = sorted({a for a, _ in grid})
    gives = sorted({g for _, g in grid})
    if arm not in arms or give not in gives:
        return []
    ai, gi = arms.index(arm), gives.index(give)
    out = []
    for da in (-1, 0, 1):
        for dg in (-1, 0, 1):
            if da == dg == 0:
                continue
            a, g = ai + da, gi + dg
            if 0 <= a < len(arms) and 0 <= g < len(gives):
                pair = (arms[a], gives[g])
                if pair in grid:
                    out.append(pair)
    return out


def cost_stress_shift(multiplier: float = COST_STRESS) -> float:
    """비용 배수 → 순수익률(%)에 더할 값(음수).

    왕복 비용을 `multiplier` 배로 올렸을 때 같은 체결에서 잃는 %p.
    """
    base = (1 - spec.COST_OUT) / (1 + spec.COST_IN)
    stressed = (1 - spec.COST_OUT * multiplier) / (1 + spec.COST_IN * multiplier)
    return (stressed - base) * 100.0


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-name", default="design_v4")
    parser.add_argument("--rule", default="trailing(arm+5/give2)")
    parser.add_argument("--grid", default="default")
    parser.add_argument("--warmup", type=int, default=60)
    parser.add_argument("--segments", type=int, default=REGIME_SEGMENTS)
    args = parser.parse_args()

    match = _RULE.match(args.rule)
    if match is None:
        raise SystemExit(f"트레일링 규칙만 지원한다: {args.rule}")
    arm, give = float(match.group(1)), float(match.group(2))
    grid = resolve_grid(args.grid)
    lane = LANES["tick"]

    peers = neighbours(arm, give, grid)
    cells = [(arm, give)] + peers
    trail_cols = [f"trail_{a:g}_{g:g}" for a, g in cells]

    hits = sorted({c for rule in RULES for c in rule[2:]})
    envelopes = [f"mfe_{h}" for h in (30, 60, 120, 300, 600)]
    horizons = [f"frA_{h}" for h in lane.horizons] + [f"frB_{h}" for h in lane.horizons]
    base = ["일자", "종목코드", "시분초", "경과", "관심종목", "spread_pct",
            "flag_no_trade", "flag_limit_up", "flag_vi_near"]
    variables = sorted(_champion_columns())

    t0 = time.time()
    frame = _load(args.out_name, base + hits + envelopes + horizons + variables + trail_cols,
                  args.warmup).reset_index(drop=True)
    print(f"집행 우주 {len(frame):,}행 · 로딩 {time.time()-t0:.0f}s", flush=True)

    missing = [c for c in trail_cols if c not in frame.columns]
    if f"trail_{arm:g}_{give:g}" in missing:
        raise SystemExit(f"대상 셀 열이 없다: trail_{arm:g}_{give:g} — 라벨 재빌드 필요")

    mask = (_mask_902(frame) | _mask_905(frame)).to_numpy()
    positions = entry_positions(frame, mask, horizon=lane.barrier_horizon)
    subset = frame.iloc[positions].reset_index(drop=True)
    day_codes, day_values = pd.factorize(subset["일자"].to_numpy())
    n_days = int(day_codes.max() + 1) if day_codes.size else 0
    print(f"챔피언 진입 {positions.size:,}건 · {n_days}일", flush=True)

    values = evaluate(subset, ExitRule("trailing_exact", arm_pct=arm, give_pct=give))
    headline = _stats(values, day_codes, n_days)
    print(f"\n대상 {args.rule}: 건당 {headline['expectancy_pct']:+.4f}% · "
          f"일평균 {headline['day_mean_pct']:+.4f}%", flush=True)

    # ── ① 격자 고원 ────────────────────────────────────────────────────────
    plateau_rows = []
    for a, g in peers:
        column = f"trail_{a:g}_{g:g}"
        if column not in frame.columns:
            plateau_rows.append({"cell": f"arm+{a:g}/give{g:g}", "available": False})
            continue
        peer_values = evaluate(subset, ExitRule("trailing_exact", arm_pct=a, give_pct=g))
        plateau_rows.append({"cell": f"arm+{a:g}/give{g:g}", "available": True,
                             **_stats(peer_values, day_codes, n_days)})
    usable = [r for r in plateau_rows if r.get("available")]
    positive = [r for r in usable if r["expectancy_pct"] > 0]
    ratio = len(positive) / len(usable) if usable else 0.0
    plateau_pass = bool(usable) and ratio >= PLATEAU_MIN_POSITIVE_RATIO

    print(f"\n=== ① 격자 고원 ({'PASS' if plateau_pass else 'FAIL' if usable else 'N/A'}) ===",
          flush=True)
    print(f"이웃 {len(usable)}셀 중 양수 {len(positive)}셀 ({ratio:.0%}) · "
          f"기준 {PLATEAU_MIN_POSITIVE_RATIO:.0%}", flush=True)
    for row in plateau_rows:
        if row.get("available"):
            print(f"  {row['cell']:<22} 건당={row['expectancy_pct']:+.4f}%", flush=True)
        else:
            print(f"  {row['cell']:<22} (격자에 없음 — 넓은 격자 라벨 필요)", flush=True)

    # ── ② 비용 스트레스 ────────────────────────────────────────────────────
    shift = cost_stress_shift()
    stressed = _stats(values + shift, day_codes, n_days)
    cost_pass = stressed["expectancy_pct"] > 0
    print(f"\n=== ② 비용 스트레스 ×{COST_STRESS} ({'PASS' if cost_pass else 'FAIL'}) ===",
          flush=True)
    print(f"차감 {shift:+.4f}%p → 건당 {stressed['expectancy_pct']:+.4f}% · "
          f"일평균 {stressed['day_mean_pct']:+.4f}%", flush=True)
    print("  [근사] 청산 시점을 고정한 채 값만 내렸다 — 무장 지연은 반영되지 않는다.",
          flush=True)

    # ── ③ 국면 절단 ────────────────────────────────────────────────────────
    order = np.argsort(day_values)
    ranked = {day: rank for rank, day in enumerate(day_values[order])}
    day_rank = np.array([ranked[d] for d in day_values])[day_codes]
    edges = np.linspace(0, n_days, args.segments + 1).astype(int)
    segments = []
    for index in range(args.segments):
        low, high = edges[index], edges[index + 1]
        pick = (day_rank >= low) & (day_rank < high)
        if not pick.any():
            continue
        seg_days = day_codes[pick]
        remap = {code: i for i, code in enumerate(sorted(set(seg_days.tolist())))}
        seg_codes = np.array([remap[c] for c in seg_days])
        segments.append({
            "segment": index + 1,
            "day_from": int(day_values[order][low]),
            "day_to": int(day_values[order][min(high, n_days) - 1]),
            **_stats(values[pick], seg_codes, len(remap)),
        })
    seg_positive = sum(1 for s in segments if s["day_mean_pct"] > 0)
    regime_pass = bool(segments) and seg_positive == len(segments)

    print(f"\n=== ③ 국면 절단 ({'PASS' if regime_pass else 'FAIL'}) ===", flush=True)
    print(f"{len(segments)}조각 중 양수 {seg_positive}조각 (전부여야 통과)", flush=True)
    for seg in segments:
        print(f"  {seg['segment']}: {seg['day_from']}~{seg['day_to']} "
              f"({seg['days']}일 {seg['n']}건) 일평균={seg['day_mean_pct']:+.4f}%", flush=True)

    verdict = "PASS" if (plateau_pass and cost_pass and regime_pass) else "FAIL"
    print(f"\n=== 사다리 종합: {verdict} ===", flush=True)
    if verdict == "FAIL":
        print("  통과하지 못한 단이 있다 — 엔진 승격·사람 보고 대상이 아니다.", flush=True)

    out_path = os.path.join(_LABEL_ROOT, args.out_name,
                            f"_exit_ladder_{arm:g}_{give:g}.json".replace(".", "p", 0))
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({
            "rule": args.rule, "grid": args.grid, "entry": "champion_902_905_fixed",
            "headline": headline,
            "plateau": {"rows": plateau_rows, "positive_ratio": ratio,
                        "minimum_ratio": PLATEAU_MIN_POSITIVE_RATIO,
                        "verdict": "PASS" if plateau_pass else ("FAIL" if usable else "N/A")},
            "cost_stress": {"multiplier": COST_STRESS, "shift_pct": shift,
                            "exactness": "approx_policy_fixed",
                            "stats": stressed, "verdict": "PASS" if cost_pass else "FAIL"},
            "regime": {"segments": segments, "positive": seg_positive,
                       "verdict": "PASS" if regime_pass else "FAIL"},
            "verdict": verdict,
            "note": ("비용 스트레스는 청산 시점을 고정한 근사다. 정확히 재려면 "
                     "비용을 올려 라벨을 다시 구워야 한다."),
        }, handle, ensure_ascii=False, indent=1, default=float)
    print(f"\n저장: {os.path.abspath(out_path)} · 총 {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
