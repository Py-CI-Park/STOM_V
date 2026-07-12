"""D1 2절 교호작용 — DiD 판정 (봉인본 §6·§7·§8·§14).

자격 짝별 2×2 차이-속-차이(DiD):
    I = μ11 − μ10 − μ01 + μ00 = Δ_AB − Δ_A − Δ_B   (셀 μ00 기준)
셀 순서 = a*2 + b → 00·01·10·11. I > 0 시너지 / I < 0 간섭(§6.1).

- CI = 일자블록 부트스트랩(437일 복원추출, 재표집마다 4셀 평균→I, n_boot 400,
  seed 20260713 §14). 양측 p, SE_boot, MDE = D1 동일 산식(judge._mde_from_ci).
- 연도별 I(2022·2023) — 연도 동부호 판정용.
- 판정(§7): 시너지·간섭·약대역·미검출(검출력)·무검출(가산적합). 미검출(표본 희소)은
  자격 게이트(pair_gate)에서 이미 배제.
- BH-FDR q=0.10, 분모 = 자격 짝 수(§14-F3). 족-짝 계상(§8, 상한 22).

부트스트랩·MDE·FDR 인프라는 D1 judge.py 재사용(드리프트 금지). 엔진 0회.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

from alpha_lab.clause_lab.judge import EFFECT_FLOOR_PP, WEAK_LOW_PP, _mde_from_ci
from alpha_lab.clause_lab.pair_gate import (
    FAMILY_PAIR_CAP, YEARS, family_pair_key, pair_id,
)
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

__all__ = [
    "FDR_Q", "N_BOOT", "SANITY_FLAT_PP", "SEED",
    "day_block_did_bootstrap", "judge_all_pairs", "judge_pair",
]

N_BOOT = 400
SEED = 20260713               # §14 확인① — D1(20260712)와 구분.
FDR_Q = 0.10
SANITY_FLAT_PP = 0.005        # §10 sanity anchor — 전 짝 |I|<0.005%p 완전 평탄이면 결함 의심.


def _cell_ids(bit_a: np.ndarray, bit_b: np.ndarray) -> np.ndarray:
    """4셀 인덱스 — cell = a*2 + b (00=0·01=1·10=2·11=3)."""
    return bit_a.astype(np.int64) * 2 + bit_b.astype(np.int64)


def _cell_means(net_pp: np.ndarray, cell: np.ndarray) -> np.ndarray:
    """셀별 평균 [μ00, μ01, μ10, μ11] — 빈 셀은 nan."""
    mu = np.full(4, np.nan)
    for c in range(4):
        m = cell == c
        if m.any():
            mu[c] = float(net_pp[m].mean())
    return mu


def _interaction(mu: np.ndarray) -> float:
    """I = μ11 − μ10 − μ01 + μ00 = mu[3] − mu[2] − mu[1] + mu[0]."""
    return float(mu[3] - mu[2] - mu[1] + mu[0])


def _per_day_cell(
    day_ids: np.ndarray, y: np.ndarray, cell: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, int]:
    """일별 4셀 (합, 수) — [n_days, 4]. 부트스트랩 재표집의 사전 집계."""
    _, inv = np.unique(day_ids, return_inverse=True)
    nd = int(inv.max()) + 1
    sums = np.zeros((nd, 4), dtype=np.float64)
    cnts = np.zeros((nd, 4), dtype=np.float64)
    for c in range(4):
        m = cell == c
        sums[:, c] = np.bincount(inv[m], weights=y[m], minlength=nd)
        cnts[:, c] = np.bincount(inv[m], minlength=nd)
    return sums, cnts, nd


def _I_from_sums(sums: np.ndarray, cnts: np.ndarray) -> np.ndarray:
    """합/수 → I(벡터화). 마지막 축 크기 4(셀). 빈 셀 재표본은 nan."""
    with np.errstate(divide="ignore", invalid="ignore"):
        mu = sums / cnts
    return mu[..., 3] - mu[..., 2] - mu[..., 1] + mu[..., 0]


def day_block_did_bootstrap(
    day_ids: np.ndarray, net_pp: np.ndarray, bit_a: np.ndarray, bit_b: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, float]:
    """일 블록 복원 DiD 부트스트랩 → {point, ci_low, ci_high, se, p_one, p_two, n_valid}.

    일(437) 복원추출, 재표집마다 4셀 평균으로 I 재계산(일내 상관 보존). CI=백분위
    2.5/97.5, p_one=P(I*≤0), 양측 p_two. SE = 재표본 표준편차.
    """
    cell = _cell_ids(bit_a, bit_b)
    if day_ids.size == 0:
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "se": float("nan"),
                "p_one": 1.0, "p_two": 1.0, "n_valid": 0}
    sums, cnts, nd = _per_day_cell(day_ids, net_pp.astype(np.float64), cell)
    point = float(_I_from_sums(sums.sum(0), cnts.sum(0)))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nd, size=(n_boot, nd))
    reps = _I_from_sums(sums[idx].sum(axis=1), cnts[idx].sum(axis=1))
    valid = reps[np.isfinite(reps)]
    if valid.size == 0:
        return {"point": point, "ci_low": float("nan"), "ci_high": float("nan"),
                "se": float("nan"), "p_one": 1.0, "p_two": 1.0, "n_valid": 0}
    ci_low, ci_high = np.percentile(valid, [2.5, 97.5])
    se = float(valid.std(ddof=1)) if valid.size > 1 else float("nan")
    p_one = float(np.mean(valid <= 0.0))
    p_two = float(min(1.0, 2.0 * min(p_one, 1.0 - p_one)))
    return {"point": point, "ci_low": float(ci_low), "ci_high": float(ci_high),
            "se": se, "p_one": p_one, "p_two": p_two, "n_valid": int(valid.size)}


def judge_pair(
    a: int, b: int, net_pp: np.ndarray, days: np.ndarray, years: np.ndarray,
    bit_a: np.ndarray, bit_b: np.ndarray, *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, object]:
    """짝 (a,b) 1개 DiD 판정 — μ 4셀·Δ·I·CI·p·MDE·연도별 I (FDR/분류는 judge_all)."""
    cell = _cell_ids(bit_a, bit_b)
    mu = _cell_means(net_pp, cell)
    counts = np.array([int((cell == c).sum()) for c in range(4)])
    I = _interaction(mu)
    boot = day_block_did_bootstrap(days, net_pp, bit_a, bit_b, n_boot=n_boot, seed=seed)
    mde = _mde_from_ci(boot["ci_low"], boot["ci_high"])

    year_I = {}
    for yr in YEARS:
        m = years == yr
        muy = _cell_means(net_pp[m], cell[m])
        Iy = _interaction(muy) if np.all(np.isfinite(muy)) else float("nan")
        year_I[yr] = {"I_pp": round(Iy, 6) if np.isfinite(Iy) else None,
                      "sign": int(np.sign(Iy)) if np.isfinite(Iy) else 0}
    both_pos = all(year_I[yr]["sign"] == 1 for yr in YEARS)
    both_neg = all(year_I[yr]["sign"] == -1 for yr in YEARS)

    return {
        "pair_id": pair_id(a, b), "a": a, "b": b,
        "family_pair": family_pair_key(a, b),
        "cell_counts": [int(x) for x in counts], "cell_order": "00,01,10,11",
        "mu_pp": [round(float(m), 6) if np.isfinite(m) else None for m in mu],
        "delta_A_pp": round(float(mu[2] - mu[0]), 6),   # μ10 − μ00.
        "delta_B_pp": round(float(mu[1] - mu[0]), 6),   # μ01 − μ00.
        "delta_AB_pp": round(float(mu[3] - mu[0]), 6),  # μ11 − μ00.
        "I_pp": round(I, 6),
        "ci_low_pp": round(boot["ci_low"], 6) if np.isfinite(boot["ci_low"]) else None,
        "ci_high_pp": round(boot["ci_high"], 6) if np.isfinite(boot["ci_high"]) else None,
        "se_pp": round(boot["se"], 6) if np.isfinite(boot["se"]) else None,
        "p_two_sided": round(boot["p_two"], 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_I": year_I, "both_year_positive": bool(both_pos),
        "both_year_negative": bool(both_neg),
        "n_boot": n_boot, "seed": seed,
    }


def _classify(r: Mapping[str, object], fdr_survive: bool) -> str:
    """§7 분류 — 시너지/간섭/약대역/미검출(검출력)/무검출(가산적합)."""
    I = r["I_pp"]
    cl, ch, mde = r["ci_low_pp"], r["ci_high_pp"], r["mde_pp"]
    if I is None:
        return "undetermined"
    if (fdr_survive and I >= EFFECT_FLOOR_PP and cl is not None and cl > 0
            and r["both_year_positive"]):
        return "synergy"
    if (fdr_survive and I <= -EFFECT_FLOOR_PP and ch is not None and ch < 0
            and r["both_year_negative"]):
        return "interference"
    if (WEAK_LOW_PP <= abs(I) < EFFECT_FLOOR_PP and cl is not None and ch is not None
            and (cl > 0 or ch < 0)):
        return "weak_signal"
    if mde is not None and mde > EFFECT_FLOOR_PP:
        return "undetected_power"       # "효과 없음" 주장 금지.
    return "no_detect_additive"         # MDE ≤ 0.10 — 가산 모형 적합 주장 가능.


def _family_pair_count(per_pair: Mapping[str, Mapping]) -> Dict[str, object]:
    """족-짝 발견 계상(§8) — 족-짝 내 생존 절-짝 동부호 시 1건. 상한 22."""
    fam: Dict[str, List[Mapping]] = {}
    for r in per_pair.values():
        fam.setdefault(r["family_pair"], []).append(r)
    result: Dict[str, object] = {}
    for key, members in fam.items():
        distinct = [m for m in members
                    if m["classification"] in ("synergy", "interference")]
        signs = {int(np.sign(m["I_pp"])) for m in distinct if m["I_pp"] is not None}
        same_sign = len(signs) == 1
        syn = any(m["classification"] == "synergy" for m in distinct) and same_sign and signs == {1}
        itf = any(m["classification"] == "interference" for m in distinct) and same_sign and signs == {-1}
        result[key] = {
            "n_member_pairs": len(members),
            "member_pairs": [m["pair_id"] for m in members],
            "synergy_family": bool(syn), "interference_family": bool(itf),
        }
    return result


def judge_all_pairs(
    qualified: Sequence[Tuple[int, int]],
    net_pp: np.ndarray, days: np.ndarray, years: np.ndarray,
    bits: Mapping[int, np.ndarray],
    *, n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """자격 짝 전체 DiD 판정 + BH-FDR(분모=자격 짝 수) + 분류 + 족-짝 계상 + sanity.

    qualified = [(a, b), ...] 자격 짝. bits[n] = 라벨된 온셋 만족 bool 배열(net_pp 순서).
    """
    per: Dict[str, Dict[str, object]] = {}
    for a, b in qualified:
        r = judge_pair(a, b, net_pp, days, years, bits[a], bits[b],
                       n_boot=n_boot, seed=seed)
        per[r["pair_id"]] = r

    ordered = list(per.keys())
    pvals = [float(per[k]["p_two_sided"]) for k in ordered]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    for i, k in enumerate(ordered):
        per[k]["fdr_survive"] = bool(survive[i])
        per[k]["classification"] = _classify(per[k], per[k]["fdr_survive"])

    synergy = [k for k in ordered if per[k]["classification"] == "synergy"]
    interference = [k for k in ordered if per[k]["classification"] == "interference"]
    weak = [k for k in ordered if per[k]["classification"] == "weak_signal"]
    undetected_power = [k for k in ordered if per[k]["classification"] == "undetected_power"]
    no_detect = [k for k in ordered if per[k]["classification"] == "no_detect_additive"]

    fam = _family_pair_count(per)
    n_syn_fam = sum(1 for r in fam.values() if r["synergy_family"])
    n_itf_fam = sum(1 for r in fam.values() if r["interference_family"])

    abs_I = [abs(per[k]["I_pp"]) for k in ordered if per[k]["I_pp"] is not None]
    sanity_trip = bool(abs_I and max(abs_I) < SANITY_FLAT_PP)

    return {
        "per_pair": per,
        "n_qualified": len(qualified),
        "fdr_denominator": len(qualified),
        "fdr_q": fdr_q,
        "synergy_pairs": synergy, "interference_pairs": interference,
        "weak_signal_pairs": weak, "undetected_power_pairs": undetected_power,
        "no_detect_additive_pairs": no_detect,
        "family_pairs": fam, "family_pair_cap": FAMILY_PAIR_CAP,
        "n_synergy_families": n_syn_fam, "n_interference_families": n_itf_fam,
        "sanity_anchor_tripped": sanity_trip,
        # §10 kill-1: 자격 짝 중 시너지·간섭 0 → "검정한 2절 짝에서 초가산 구조 미검출".
        "kill1_no_interaction_detected": bool(len(synergy) == 0 and len(interference) == 0),
    }
