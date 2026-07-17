"""O-3 돌파 온셋 판정 — 변형×모집단 단독 절대 EV 검정 (봉인본 §7·§8·§10, judge_d9 미러).

D9(전이 vs 서지 paired 차)와 달리 O-3는 **단독 모집단 절대 EV** 검정이다(§7):
각 자격 (변형×모집단)에 대해 라벨된 온셋의 L3 실현 net 평균이 양의 실질 문턱을
넘는가를 판정한다. paired 차 부트스트랩이 아니라 **단독 평균 일자블록 부트스트랩**
(stats_common.day_block_bootstrap stat="mean", seed 20260710·n_boot 400, F7-③).

판정(전 조건 동시 — §7):
- strong(양EV): BH-FDR(q=0.10, 분모=자격 변형×모집단 수) 생존 ∧ mean_net ≥ +0.10%p
  ∧ 일자블록 CI 하한 > 0 ∧ 연도(2022·2023) 동부호(+).
- 약신호: mean_net > 0 ∧ 연도 동부호(+)이나 strong 미충족 — 보고만.
- 변형 kill: mean_net CI 상한 < 0(부정 지도).
- insufficient: 표본 하한(n≥2,000 ∧ 연도 각 ≥400) 미달 — 판정 금지·분모 제외.
- MDE 병기(미검출 vs 효과 없음). sanity anchor: 전 자격 |mean − 서지풀 −1.01%p|<0.02
  수렴 시 파이프라인 결함 의심.

효과 하한·MDE·약신호 대역 상수는 D1 clause_lab.judge 를 재사용(드리프트 금지).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Sequence

import numpy as np

from alpha_lab.clause_lab.judge import EFFECT_FLOOR_PP, WEAK_LOW_PP, _mde_from_ci
from alpha_lab.stats_common import bh_fdr, day_block_bootstrap

logger = logging.getLogger(__name__)

__all__ = [
    "FDR_Q", "FLOOR_TOTAL", "FLOOR_YEAR", "N_BOOT", "POPULATIONS", "SEED",
    "SURGE_POOL_MEAN_PP", "YEARS", "judge_all_o3", "judge_unit",
]

SEED = 20260710               # F7-③ — O-1G 연속성(D5 20260712 와 다름, O-3 봉인값).
N_BOOT = 400                  # §7 일자블록 부트스트랩.
FDR_Q = 0.10                  # §8 BH-FDR.
FLOOR_TOTAL = 2000            # §5 변형×모집단 표본 하한(라벨된 온셋).
FLOOR_YEAR = 400              # §5 연도별 하한.
YEARS = (2022, 2023)
POPULATIONS = ("all", "surge_nonoverlap")   # §5·F2 판정 2모집단.
SURGE_POOL_MEAN_PP = -1.01    # 서지 온셋 풀 L3 평균(%p) — sanity anchor 기준(§10-5).
_SANITY_DELTA_PP = 0.02       # sanity anchor 문턱(%p).


def judge_unit(
    name: str, net_pp: np.ndarray, day: np.ndarray, year: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, object]:
    """한 (변형×모집단)의 단독 절대 EV 진단 — mean·CI·p·MDE·연도부호·표본 하한.

    net_pp/day/year 는 해당 단위의 **라벨된 온셋**(net_pp = l3_net×100). FDR 생존은
    judge_all_o3 가 일괄. 표본 하한(§5)은 라벨된 n 기준(호가 무효는 이미 제외).
    """
    n = int(net_pp.size)
    yr_counts = {yr: int((year == yr).sum()) for yr in YEARS}
    floor_pass = n >= FLOOR_TOTAL and all(yr_counts[yr] >= FLOOR_YEAR for yr in YEARS)
    mean = float(net_pp.mean()) if n else float("nan")

    mask = np.ones(n, dtype=bool)
    boot = day_block_bootstrap(np.asarray(day, dtype=np.int64),
                               np.asarray(net_pp, dtype=np.float64), mask,
                               n_boot=n_boot, seed=seed, stat="mean")
    ci_low, ci_high, p_one = boot["ci_low"], boot["ci_high"], boot["p_one_sided"]
    p_two = float(min(1.0, 2.0 * min(p_one, 1.0 - p_one)))
    mde = _mde_from_ci(ci_low, ci_high)

    year_mean = {}
    for yr in YEARS:
        vals = net_pp[year == yr]
        mv = float(vals.mean()) if vals.size else float("nan")
        year_mean[yr] = {"mean_pp": round(mv, 6) if np.isfinite(mv) else None,
                         "sign": int(np.sign(mv)) if np.isfinite(mv) else 0,
                         "n": int(vals.size)}
    both_pos = all(year_mean[yr]["sign"] == 1 for yr in YEARS)
    both_neg = all(year_mean[yr]["sign"] == -1 for yr in YEARS)

    return {
        "unit": name, "n_labeled": n, "year_counts": yr_counts,
        "floor_total": FLOOR_TOTAL, "floor_year": FLOOR_YEAR,
        "floor_pass": bool(floor_pass),
        "mean_net_pp": round(mean, 6) if np.isfinite(mean) else None,
        "ci_low_pp": round(ci_low, 6) if np.isfinite(ci_low) else None,
        "ci_high_pp": round(ci_high, 6) if np.isfinite(ci_high) else None,
        "p_one_sided": round(p_one, 6), "p_two_sided": round(p_two, 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_mean": year_mean,
        "both_year_positive": bool(both_pos), "both_year_negative": bool(both_neg),
        "n_boot": n_boot, "seed": seed,
    }


def _classify(r: Mapping[str, object]) -> str:
    """단독 EV 분류(§7) — insufficient/kill/strong/weak/none 우선순위."""
    if not r["floor_pass"]:
        return "insufficient"
    m = r["mean_net_pp"]
    cl, ch = r["ci_low_pp"], r["ci_high_pp"]
    if ch is not None and ch < 0.0:
        return "variant_kill"                      # §7 CI 상한<0 = 부정 지도.
    if m is None:
        return "none"
    if (r["fdr_survive"] and m >= EFFECT_FLOOR_PP and cl is not None and cl > 0.0
            and r["both_year_positive"]):
        return "strong"                            # §7 양EV(전 조건 동시).
    if m > 0.0 and r["both_year_positive"]:
        return "weak_signal"                       # §7 약신호(보고만).
    return "none"


def judge_all_o3(
    units: Mapping[str, Mapping[str, np.ndarray]],
    *, n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """자격 (변형×모집단) 단위 전체 판정 + BH-FDR(분모=하한 통과 자격 수) + sanity.

    units[name] = {"net_pp", "day", "year"} (라벨된 온셋). name = f"{variant}:{population}".
    분모는 §5 표본 하한 통과 단위 수(사후 확정 — 자기채점 아님, 하한은 L3 분포 전 결정).
    """
    per: Dict[str, Dict[str, object]] = {}
    for name, u in units.items():
        per[name] = judge_unit(name, u["net_pp"], u["day"], u["year"],
                               n_boot=n_boot, seed=seed)

    # BH-FDR 분모 = 표본 하한 통과 자격 단위(§8, 상한 10). 미달은 분모 제외.
    floor_names = [n for n in units if per[n]["floor_pass"]]
    insufficient = [n for n in units if not per[n]["floor_pass"]]
    pvals = [float(per[n]["p_two_sided"]) for n in floor_names]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    surv_map = {floor_names[i]: bool(survive[i]) for i in range(len(floor_names))}
    for n in units:
        per[n]["fdr_survive"] = bool(surv_map.get(n, False))
        per[n]["classification"] = _classify(per[n])

    strong = [n for n in floor_names if per[n]["classification"] == "strong"]
    weak = [n for n in floor_names if per[n]["classification"] == "weak_signal"]
    kills = [n for n in floor_names if per[n]["classification"] == "variant_kill"]

    # sanity anchor(§10-5): 전 자격 단위 |mean − 서지풀 −1.01%p| < 0.02 → 결함 의심.
    devs = [abs(per[n]["mean_net_pp"] - SURGE_POOL_MEAN_PP) for n in floor_names
            if per[n]["mean_net_pp"] is not None]
    sanity_trip = bool(devs and max(devs) < _SANITY_DELTA_PP)

    # kill-1(§10): 전 자격 단위 CI 상한 < 0 = "돌파도 시초 음의 지형을 못 뒤집음".
    all_ci_high_neg = bool(floor_names and all(
        per[n]["ci_high_pp"] is not None and per[n]["ci_high_pp"] < 0.0
        for n in floor_names))

    return {
        "per_unit": per,
        "units": list(units.keys()),
        "floor_pass_units": floor_names,
        "insufficient_units": insufficient,
        "fdr_denominator": len(floor_names),
        "fdr_q": fdr_q,
        "strong_units": strong,
        "weak_signal_units": weak,
        "variant_kill_units": kills,
        "n_strong": len(strong),
        "n_weak_signal": len(weak),
        "sanity_anchor_tripped": sanity_trip,
        # §10-4: strong≥1 = 통과(kill 아님). kill-1 = 자격 전무 CI상한<0.
        "kill1_all_ci_high_negative": all_ci_high_neg,
        "no_positive_ev": bool(len(strong) == 0),
    }


def unit_name(variant: str, population: str) -> str:
    """(변형, 모집단) → 판정 단위 키 — 'P20:all' 형식."""
    return f"{variant}:{population}"


def split_qualified_units(
    variant: np.ndarray, net_pp: np.ndarray, day: np.ndarray, year: np.ndarray,
    labeled: np.ndarray, surge_nonoverlap: np.ndarray,
    *, variants: Sequence[str], populations: Sequence[str] = POPULATIONS,
) -> Dict[str, Dict[str, np.ndarray]]:
    """은행 배열 → 변형×모집단 판정 단위 dict(라벨된 온셋만, net_pp = l3_net×100).

    surge_nonoverlap = 해당 온셋이 ±30초 내 서지 온셋 부재(모집단 'surge_nonoverlap' 성원).
    """
    lab = np.asarray(labeled, dtype=bool)
    units: Dict[str, Dict[str, np.ndarray]] = {}
    for v in variants:
        v_mask = (variant == v) & lab
        for pop in populations:
            mask = v_mask & surge_nonoverlap if pop == "surge_nonoverlap" else v_mask
            units[unit_name(v, pop)] = {
                "net_pp": np.asarray(net_pp)[mask].astype(np.float64),
                "day": np.asarray(day)[mask].astype(np.int64),
                "year": np.asarray(year)[mask].astype(np.int64),
            }
    return units
