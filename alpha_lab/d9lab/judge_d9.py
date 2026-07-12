"""D9 서브모집단 대조 판정 — 전이 온셋 vs 서지 기준선 Δ (봉인본 §7·§14-1·§14-3·§14-4).

3개 서브모집단(신규진입·재진입·pooled) 각각에 대해:
- Δ = mean(L3 %p | 전이 서브모집단) − mean(L3 %p | 서지 기준선), 관측가능·라벨된 온셋 위.
- CI = 전이·서지 **동시 일자블록 차 부트스트랩**(judge.day_block_diff_bootstrap,
  n_boot 400) — 기준선을 상수 취급하지 않는다(§14-3).
- 표본 하한(전이 측, §14-4): 재진입 150/연40 · 신규진입 100/연30 · pooled 150/연40.
  미달 = inconclusive(구별 판정 불가).
- 효과크기 하한 |Δ| ≥ 0.10%p, CI 0 배제, 연도(2022·2023) 동부호 → 구별 EV.
- BH-FDR q=0.10, **분모 = 3 고정**(§14-1·§14-9, 사후 축소·확대 금지).
- 반기(H1/H2) 부호 보조 병기. MDE 병기(미검출 vs 효과 없음).
- sanity anchor: 전 서브모집단 |Δ|<0.02%p → 파이프라인 결함 의심(수동 스팟 후 kill-4).

Δ·CI·FDR·MDE 인프라는 D1 judge 를 그대로 재사용(드리프트 금지).
"""
from __future__ import annotations

import logging
from typing import Dict, Mapping, Sequence

import numpy as np

from alpha_lab.clause_lab.judge import (
    EFFECT_FLOOR_PP,
    MDE_Z,
    N_BOOT,
    SEED,
    WEAK_LOW_PP,
    _mde_from_ci,
    day_block_diff_bootstrap,
)
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

__all__ = [
    "FDR_DENOMINATOR",
    "FDR_Q",
    "SANITY_DELTA_PP",
    "SUBPOP_FLOORS",
    "SUBPOPS",
    "judge_all_d9",
    "judge_subpop",
]

FDR_Q = 0.10
FDR_DENOMINATOR = 3           # §14-1·§14-9 — 사전 고정, 사후 변경 금지.
SANITY_DELTA_PP = 0.02        # §14 sanity anchor 문턱(%p).
YEARS = (2022, 2023)
SUBPOPS = ("new", "reentry", "pooled")
# (전이 측 총 하한, 연도별 하한) — §14-4.
SUBPOP_FLOORS: Dict[str, tuple] = {
    "new": (100, 30), "reentry": (150, 40), "pooled": (150, 40),
}


def _halfyear_labels(days: np.ndarray) -> np.ndarray:
    """YYYYMMDD → 반기 라벨(YYYYH1/H2). month≤6 = H1."""
    days = np.asarray(days, dtype=np.int64)
    year = days // 10000
    month = (days // 100) % 100
    half = np.where(month <= 6, 1, 2)
    return np.array([f"{y}H{h}" for y, h in zip(year, half)])


def _subpop_transition_mask(is_reentry: np.ndarray, name: str) -> np.ndarray:
    """서브모집단 이름 → 전이 온셋 마스크(관측가능·라벨은 호출측이 이미 적용)."""
    if name == "new":
        return ~is_reentry
    if name == "reentry":
        return is_reentry
    return np.ones(is_reentry.size, dtype=bool)  # pooled.


def judge_subpop(
    name: str,
    tr_net: np.ndarray, tr_day: np.ndarray, tr_year: np.ndarray,
    sg_net: np.ndarray, sg_day: np.ndarray, sg_year: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, object]:
    """전이 서브모집단 vs 서지 기준선 1개 판정(Δ·CI·p·MDE·연도/반기 부호·표본 하한).

    tr_* = 전이 온셋(이미 해당 서브모집단·관측가능·라벨 필터), sg_* = 서지 기준선(라벨).
    net 은 %p(=l3_net×100). FDR 생존은 judge_all_d9 가 일괄.
    """
    n_tr = int(tr_net.size)
    floor_total, floor_year = SUBPOP_FLOORS[name]
    yr_counts = {yr: int((tr_year == yr).sum()) for yr in YEARS}
    floor_pass = (n_tr >= floor_total
                  and all(yr_counts[yr] >= floor_year for yr in YEARS))

    # pooled 표본: 전이(sat=1) + 서지(sat=0), 동시 일자블록 차 부트스트랩.
    net = np.concatenate([tr_net, sg_net]).astype(np.float64)
    day = np.concatenate([tr_day, sg_day]).astype(np.int64)
    sat = np.concatenate([np.ones(n_tr, bool), np.zeros(sg_net.size, bool)])
    mean_tr = float(tr_net.mean()) if n_tr else float("nan")
    mean_sg = float(sg_net.mean()) if sg_net.size else float("nan")
    delta = mean_tr - mean_sg

    boot = day_block_diff_bootstrap(day, net, sat, n_boot=n_boot, seed=seed)
    ci_low, ci_high = boot["ci_low"], boot["ci_high"]
    p_one = boot["p_one_sided"]
    p_two = float(min(1.0, 2.0 * min(p_one, 1.0 - p_one)))
    mde = _mde_from_ci(ci_low, ci_high)

    year_delta = {}
    for yr in YEARS:
        dt = tr_net[tr_year == yr]
        dg = sg_net[sg_year == yr]
        dyr = (float(dt.mean()) - float(dg.mean())) if dt.size and dg.size else float("nan")
        year_delta[yr] = {"delta_pp": round(dyr, 4) if np.isfinite(dyr) else None,
                          "sign": int(np.sign(dyr)) if np.isfinite(dyr) else 0,
                          "n_tr": int(dt.size)}
    both_pos = all(year_delta[yr]["sign"] == 1 for yr in YEARS)
    both_neg = all(year_delta[yr]["sign"] == -1 for yr in YEARS)

    # 반기 부호(보조 — 채택 조건 아님, §7).
    hy_tr = _halfyear_labels(tr_day)
    hy_sg = _halfyear_labels(sg_day)
    half_delta = {}
    for hy in (f"{y}H{h}" for y in YEARS for h in (1, 2)):
        dt = tr_net[hy_tr == hy]
        dg = sg_net[hy_sg == hy]
        dhy = (float(dt.mean()) - float(dg.mean())) if dt.size and dg.size else float("nan")
        half_delta[hy] = {"delta_pp": round(dhy, 4) if np.isfinite(dhy) else None,
                          "sign": int(np.sign(dhy)) if np.isfinite(dhy) else 0,
                          "n_tr": int(dt.size)}

    return {
        "subpop": name, "n_transition": n_tr, "n_surge": int(sg_net.size),
        "year_counts": yr_counts, "floor_total": floor_total,
        "floor_year": floor_year, "floor_pass": bool(floor_pass),
        "mean_transition_pp": round(mean_tr, 6) if np.isfinite(mean_tr) else None,
        "mean_surge_pp": round(mean_sg, 6) if np.isfinite(mean_sg) else None,
        "delta_pp": round(delta, 6) if np.isfinite(delta) else None,
        "ci_low_pp": round(ci_low, 6) if np.isfinite(ci_low) else None,
        "ci_high_pp": round(ci_high, 6) if np.isfinite(ci_high) else None,
        "p_one_sided": round(p_one, 6), "p_two_sided": round(p_two, 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_delta": year_delta, "half_delta": half_delta,
        "both_year_positive": bool(both_pos), "both_year_negative": bool(both_neg),
        "n_boot": n_boot, "seed": seed,
    }


def _classify(r: Mapping[str, object]) -> str:
    """구별 EV 분류 — floor·FDR·효과크기·CI·연도부호 동시 충족(§7)."""
    d = r["delta_pp"]
    cl, ch = r["ci_low_pp"], r["ci_high_pp"]
    if d is None or not r["floor_pass"] or not r["fdr_survive"]:
        return "inconclusive" if not r["floor_pass"] else "none"
    if (d >= EFFECT_FLOOR_PP and cl is not None and cl > 0 and r["both_year_positive"]):
        return "distinct_positive"
    if (d <= -EFFECT_FLOOR_PP and ch is not None and ch < 0 and r["both_year_negative"]):
        return "distinct_negative"
    if WEAK_LOW_PP <= abs(d) < EFFECT_FLOOR_PP and cl is not None and ch is not None \
            and (cl > 0 or ch < 0):
        return "weak_signal"
    return "none"


def judge_all_d9(
    tr: Mapping[str, np.ndarray], sg: Mapping[str, np.ndarray],
    *, n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """3개 서브모집단 판정 + BH-FDR(분모=3 고정) + sanity anchor.

    tr = 관측가능·라벨된 전이 온셋 {net_pp, day, year, is_reentry}.
    sg = 라벨된 서지 기준선 {net_pp, day, year}.
    """
    is_re = np.asarray(tr["is_reentry"], dtype=bool)
    per: Dict[str, Dict[str, object]] = {}
    for name in SUBPOPS:
        mask = _subpop_transition_mask(is_re, name)
        per[name] = judge_subpop(
            name, tr["net_pp"][mask], tr["day"][mask], tr["year"][mask],
            sg["net_pp"], sg["day"], sg["year"], n_boot=n_boot, seed=seed)

    # BH-FDR — 분모 3 고정(§14-1). 전 서브모집단 p_two 사용(floor-fail 도 계상 = 보수).
    pvals = [float(per[name]["p_two_sided"]) for name in SUBPOPS]
    survive_mask = bh_fdr(pvals, q=fdr_q)
    for i, name in enumerate(SUBPOPS):
        per[name]["fdr_survive"] = bool(survive_mask[i])
        per[name]["classification"] = _classify(per[name])

    distinct = [n for n in SUBPOPS if per[n]["classification"].startswith("distinct")]
    inconclusive = [n for n in SUBPOPS if per[n]["classification"] == "inconclusive"]
    deltas = [abs(per[n]["delta_pp"]) for n in SUBPOPS
              if per[n]["delta_pp"] is not None and per[n]["floor_pass"]]
    sanity_trip = bool(deltas and max(deltas) < SANITY_DELTA_PP)

    return {
        "per_subpop": per,
        "subpops": list(SUBPOPS),
        "fdr_denominator": FDR_DENOMINATOR,
        "fdr_q": fdr_q,
        "distinct_subpops": distinct,
        "inconclusive_subpops": inconclusive,
        "n_distinct": len(distinct),
        "sanity_anchor_tripped": sanity_trip,
        # kill-4(§10): 구별 서브모집단 0 → "서지 대비 구별 EV 없음"(정직 종결).
        "kill4_no_distinct": bool(len(distinct) == 0),
    }
