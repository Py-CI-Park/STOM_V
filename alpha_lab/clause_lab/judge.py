"""절-단위 A/B 판정 — Δ·일자블록 CI·BH-FDR·연도 동부호·MDE·족 계상 (사전등록 §7·§8).

절 c 의 판정(전 조건 동시 충족 = load-bearing):
- Δ(c) = mean(L3net %p | 만족) − mean(L3net %p | 미만족), 라벨된 온셋 위.
- 표본 하한: 만족·미만족 각 n≥2,000 ∧ 연도별 각 ≥400(미달=inconclusive, 분모 제외 §5).
- 효과크기 하한 Δ ≥ +0.10%p(순-load-bearing 방향).
- BH-FDR q=0.10(양측 p, 분모=자격 절 수 §13-F3). 일자블록 부트스트랩(n_boot 400) CI 하한>0.
- 연도(2022·2023) 동부호. MDE 병기(미검출 vs 효과 없음, D5-R _mde_from_ci 동일 계수).
- 역생산 절: Δ≤−0.10%p ∧ FDR 생존(별도 보고). 약신호: +0.05~0.10%p ∧ CI>0.
- 족(밑변수) 계상: 족 내 ≥1 절 FDR 생존 ∧ 족 동부호 → 그 족 load-bearing 1건(§8).
- sanity anchor: 자격 절 전부 |Δ|<0.02%p → 파이프라인 결함 의심(수동 스팟 후 kill).

두 그룹 차(비-paired)라 D5-R 의 mean-of-deltas 부트스트랩 대신 두 그룹 일자블록
차 부트스트랩을 쓴다(같은 재표집 일에서 두 그룹 평균차 — 일중 상관 보존).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.clause_lab.clauses import CLAUSE_SPECS, FAMILIES, spec_by_num
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

__all__ = [
    "EFFECT_FLOOR_PP", "FDR_Q", "FLOOR_BOTH", "FLOOR_YEAR", "MDE_Z", "N_BOOT",
    "SANITY_DELTA_PP", "SEED", "WEAK_LOW_PP",
    "day_block_diff_bootstrap", "judge_all", "judge_clause",
]

N_BOOT = 400
SEED = 20260712
MDE_Z = 2.802                 # (z_0.975 + z_0.80) — 양측 5%·검정력 80% (D5-R 동일).
FLOOR_BOTH = 2000             # 만족·미만족 각 표본 하한(§5).
FLOOR_YEAR = 400              # 연도별 각 표본 하한(§5).
EFFECT_FLOOR_PP = 0.10        # 순-load-bearing 효과크기 하한(%p, §7).
WEAK_LOW_PP = 0.05            # 약신호 대역 하단(%p, §7).
FDR_Q = 0.10                  # BH-FDR q(§7).
SANITY_DELTA_PP = 0.02        # sanity anchor 문턱(%p, §13).
YEARS = (2022, 2023)


def _mde_from_ci(ci_low: float, ci_high: float) -> float:
    """부트스트랩 95% 백분위 CI 폭 → SE≈(hi−lo)/3.9199, MDE=MDE_Z×SE (D5-R 동일식)."""
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        return float("nan")
    se = (ci_high - ci_low) / (2.0 * 1.959963985)
    return MDE_Z * se


def _per_day_group_sums(
    day_ids: np.ndarray, y: np.ndarray, sat: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """일별 (만족 y합, 만족수, 미만족 y합, 미만족수) — 두 그룹 부트스트랩 집계."""
    _, inv = np.unique(day_ids, return_inverse=True)
    nd = int(inv.max()) + 1
    s = sat.astype(np.float64)
    u = 1.0 - s
    ssum = np.bincount(inv, weights=y * s, minlength=nd)
    scnt = np.bincount(inv, weights=s, minlength=nd)
    usum = np.bincount(inv, weights=y * u, minlength=nd)
    ucnt = np.bincount(inv, weights=u, minlength=nd)
    return ssum, scnt, usum, ucnt


def day_block_diff_bootstrap(
    day_ids: np.ndarray, y: np.ndarray, sat: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, float]:
    """두 그룹 일자블록 차 부트스트랩 → {point, ci_low, ci_high, p_one_sided}.

    Δ = mean(y|만족) − mean(y|미만족)(합의 비, ratio-of-sums). 매 반복 D개 일을
    복원추출해 같은 재표집 일에서 두 그룹 평균을 계산(일중 상관 보존). CI=95%
    백분위, p_one_sided = P(Δ* ≤ 0). 재표본에서 한쪽 그룹 표본 0이면 그 반복 nan(제외).
    """
    day_arr = np.asarray(day_ids)
    y_arr = np.asarray(y, dtype=np.float64)
    sat_arr = np.asarray(sat, dtype=bool)
    if day_arr.size == 0:
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "p_one_sided": 1.0}
    ssum, scnt, usum, ucnt = _per_day_group_sums(day_arr, y_arr, sat_arr)

    def stat(ss, sc, us, uc):
        with np.errstate(divide="ignore", invalid="ignore"):
            out = ss / sc - us / uc
        return np.where(np.isfinite(out), out, np.nan)

    point = float(stat(ssum.sum(), scnt.sum(), usum.sum(), ucnt.sum()))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, ssum.shape[0], size=(n_boot, ssum.shape[0]))
    reps = stat(ssum[idx].sum(1), scnt[idx].sum(1), usum[idx].sum(1), ucnt[idx].sum(1))
    valid = reps[np.isfinite(reps)]
    if valid.size == 0:
        return {"point": point, "ci_low": float("nan"),
                "ci_high": float("nan"), "p_one_sided": 1.0}
    lo, hi = np.percentile(valid, [2.5, 97.5])
    return {"point": point, "ci_low": float(lo), "ci_high": float(hi),
            "p_one_sided": float(np.mean(valid <= 0.0))}


def judge_clause(
    num: int, net_pp: np.ndarray, days: np.ndarray, years: np.ndarray,
    sat: np.ndarray, *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, object]:
    """절 c 1개의 진단 — Δ·CI·p·MDE·연도부호·표본 하한(FDR 판정은 judge_all 이 일괄)."""
    spec = spec_by_num(num)
    n_sat = int(sat.sum())
    n_unsat = int((~sat).sum())
    yr_counts = {yr: {"sat": int((sat & (years == yr)).sum()),
                      "unsat": int((~sat & (years == yr)).sum())} for yr in YEARS}
    floor_pass = (n_sat >= FLOOR_BOTH and n_unsat >= FLOOR_BOTH
                  and all(yr_counts[yr]["sat"] >= FLOOR_YEAR
                          and yr_counts[yr]["unsat"] >= FLOOR_YEAR for yr in YEARS))

    mean_sat = float(net_pp[sat].mean()) if n_sat else float("nan")
    mean_unsat = float(net_pp[~sat].mean()) if n_unsat else float("nan")
    delta = mean_sat - mean_unsat

    boot = day_block_diff_bootstrap(days, net_pp, sat, n_boot=n_boot, seed=seed)
    ci_low, ci_high = boot["ci_low"], boot["ci_high"]
    p_one = boot["p_one_sided"]
    p_two = float(min(1.0, 2.0 * min(p_one, 1.0 - p_one)))
    mde = _mde_from_ci(ci_low, ci_high)

    year_delta = {}
    for yr in YEARS:
        m = years == yr
        ds = net_pp[m & sat]
        du = net_pp[m & ~sat]
        dyr = (float(ds.mean()) - float(du.mean())) if ds.size and du.size else float("nan")
        year_delta[yr] = {"delta_pp": round(dyr, 4) if np.isfinite(dyr) else None,
                          "sign": int(np.sign(dyr)) if np.isfinite(dyr) else 0,
                          "n_sat": int(ds.size), "n_unsat": int(du.size)}
    both_year_pos = all(year_delta[yr]["sign"] == 1 for yr in YEARS)
    both_year_neg = all(year_delta[yr]["sign"] == -1 for yr in YEARS)

    return {
        "num": num, "text": spec.text, "cat": spec.cat, "tier": spec.tier,
        "family": spec.family, "polarity_note": spec.polarity_note,
        "n_sat": n_sat, "n_unsat": n_unsat, "year_counts": yr_counts,
        "floor_pass": bool(floor_pass),
        "mean_sat_pp": round(mean_sat, 6) if np.isfinite(mean_sat) else None,
        "mean_unsat_pp": round(mean_unsat, 6) if np.isfinite(mean_unsat) else None,
        "delta_pp": round(delta, 6) if np.isfinite(delta) else None,
        "ci_low_pp": round(ci_low, 6) if np.isfinite(ci_low) else None,
        "ci_high_pp": round(ci_high, 6) if np.isfinite(ci_high) else None,
        "p_one_sided": round(p_one, 6), "p_two_sided": round(p_two, 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_delta": year_delta,
        "both_year_positive": bool(both_year_pos),
        "both_year_negative": bool(both_year_neg),
        "n_boot": n_boot, "seed": seed,
    }


def judge_all(
    bits: Mapping[int, np.ndarray], net_pp: np.ndarray, days: np.ndarray,
    years: np.ndarray, qualified_nums: Sequence[int],
    *, n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """자격 절 전체 판정 + BH-FDR(양측 p, 분모=표본하한 통과 자격 절) + 족 계상 + sanity.

    bits[num] 은 라벨된 온셋에 대응하는 만족 bool 배열(net_pp/days/years 와 동일 길이·순서).
    """
    per: Dict[int, Dict[str, object]] = {}
    for num in qualified_nums:
        per[num] = judge_clause(num, net_pp, days, years, np.asarray(bits[num], dtype=bool),
                                n_boot=n_boot, seed=seed)

    # FDR 분모 = 표본 하한 통과 자격 절(§5 분모 제외).
    floor_nums = [n for n in qualified_nums if per[n]["floor_pass"]]
    inconclusive = [n for n in qualified_nums if not per[n]["floor_pass"]]
    pvals = [float(per[n]["p_two_sided"]) for n in floor_nums]
    survive_mask = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    survive = {floor_nums[i]: bool(survive_mask[i]) for i in range(len(floor_nums))}
    for n in qualified_nums:
        per[n]["fdr_survive"] = bool(survive.get(n, False))

    load_bearing, counter, weak = [], [], []
    for n in floor_nums:
        r = per[n]
        d = r["delta_pp"]
        cl, ch = r["ci_low_pp"], r["ci_high_pp"]
        surv = r["fdr_survive"]
        r["classification"] = "none"
        if d is None:
            continue
        if (surv and d >= EFFECT_FLOOR_PP and cl is not None and cl > 0
                and r["both_year_positive"]):
            r["classification"] = "load_bearing"
            load_bearing.append(n)
        elif surv and d <= -EFFECT_FLOOR_PP:
            # §7 역방향 절(별도 보고): Δ≤−0.10%p ∧ FDR 생존 — 조합 조건부/잉여 후보.
            r["classification"] = "counter_productive"
            counter.append(n)
        elif (WEAK_LOW_PP <= d < EFFECT_FLOOR_PP and cl is not None and cl > 0):
            r["classification"] = "weak_signal"
            weak.append(n)

    # 족 계상(§8) — 근접 중복 인플레 차단(발견 계상은 족 단위). 두 층 병기:
    #  · load_bearing_family: 족 내 ≥1 절이 절-단위 load-bearing(§7 하한 통과) ∧ 족 동부호
    #    → 절 #37·#38 처럼 같은 족의 load-bearing 을 1건으로 계상(주 계상).
    #  · sig_positive_family: 족 내 ≥1 절 FDR 생존 양(+) ∧ 족 동부호(약신호 포함, 넓은 층).
    family_result: Dict[str, object] = {}
    for fam, members in FAMILIES.items():
        elig = [n for n in members if n in floor_nums]
        if not elig:
            continue
        signs = [int(np.sign(per[n]["delta_pp"])) for n in elig
                 if per[n]["delta_pp"] is not None]
        any_surv = any(per[n]["fdr_survive"] for n in elig)
        has_lb = any(per[n]["classification"] == "load_bearing" for n in elig)
        has_cp = any(per[n]["classification"] == "counter_productive" for n in elig)
        same_sign = len(set(signs)) == 1 and signs and signs[0] != 0
        pos = same_sign and signs[0] == 1
        family_result[fam] = {
            "eligible_clauses": elig, "any_fdr_survive": bool(any_surv),
            "same_sign": bool(same_sign), "sign": signs[0] if same_sign else 0,
            "load_bearing_family": bool(has_lb and same_sign and pos),
            "counter_family": bool(has_cp and same_sign and not pos),
            "sig_positive_family": bool(any_surv and same_sign and pos),
        }
    lb_families = [f for f, r in family_result.items() if r["load_bearing_family"]]
    sig_pos_families = [f for f, r in family_result.items() if r["sig_positive_family"]]

    # sanity anchor: 자격 절 전부 |Δ|<0.02%p → 결함 의심.
    deltas = [abs(per[n]["delta_pp"]) for n in floor_nums if per[n]["delta_pp"] is not None]
    sanity_trip = bool(deltas and max(deltas) < SANITY_DELTA_PP)

    return {
        "per_clause": per,
        "qualified_nums": list(qualified_nums),
        "floor_pass_nums": floor_nums,
        "inconclusive_nums": inconclusive,
        "fdr_denominator": len(floor_nums),
        "fdr_q": fdr_q,
        "load_bearing_nums": load_bearing,
        "counter_productive_nums": counter,
        "weak_signal_nums": weak,
        "family_result": family_result,
        "load_bearing_families": lb_families,
        "sig_positive_families": sig_pos_families,
        "n_load_bearing": len(load_bearing),
        "n_counter_productive": len(counter),
        "n_weak_signal": len(weak),
        "sanity_anchor_tripped": sanity_trip,
        "kill1_all_zero_survivors": bool(len(load_bearing) == 0),
    }
