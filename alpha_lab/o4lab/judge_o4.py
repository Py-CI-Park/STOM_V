"""O-4 후보 판정 — 자격(L3 미접촉) → 발화 mean L3·일자블록 CI·FDR·겹침·분류 (봉인본 §6·§7·§8·§14).

순서 봉인(§6):
  [3] qualify_candidates — 발화 n≥2,000 ∧ 연도별 ≥400. **L3 컬럼 미접촉**(비트+연도만, 자기채점 차단).
  [4] judge_candidate     — 발화 집합 mean L3_net·day_block_mean_bootstrap CI(seed 20260714)·p·MDE·연도평균.
      FDR q=0.10(양측 p, 분모=자격 후보 수).
  [5] 겹침                — champion_and_mask(bit_1~39 플랫 AND, §14-F8 하한 프록시)와 발화 교차율.
  [6] 분류                — 생존/아류/약신호/양EV증거0 + 족 계상(§8) + sanity anchor.

부트스트랩·MDE·FDR 인프라는 D1 judge.py 재사용(드리프트 금지). 엔진 0회.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

from alpha_lab.clause_lab.judge import _mde_from_ci
from alpha_lab.o4lab.grammar import CANDIDATES, CHAMPION_AND_BITS, Candidate, families
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

__all__ = [
    "EFFECT_FLOOR_PP", "FDR_Q", "FLOOR_N", "FLOOR_YEAR", "N_BOOT", "OVERLAP_CAP",
    "OVERLAP_PROXY_TAG", "POOL_MEAN_PP", "SANITY_BAND_PP", "SEED", "WEAK_LOW_PP", "YEARS",
    "champion_and_mask", "day_block_mean_bootstrap", "candidate_fire_mask",
    "judge_all_candidates", "judge_candidate", "qualify_candidates",
]

N_BOOT = 400
SEED = 20260714               # §14-F12.
FDR_Q = 0.10                  # §6.
EFFECT_FLOOR_PP = 0.10        # 효과크기 floor(§6·§9-F9) — mean>0(비용 넘김)만은 기각.
WEAK_LOW_PP = 0.05            # 약신호 하단(§6).
FLOOR_N = 2000                # 발화 표본 하한(§6·§10-F10).
FLOOR_YEAR = 400              # 연도별 발화 하한(§6).
OVERLAP_CAP = 0.50            # 아류 차단 상한(§7).
POOL_MEAN_PP = -1.008         # 서지 풀 평균(§0·§10-6, d1 #22 mean_sat −1.007796) — sanity 기준.
SANITY_BAND_PP = 0.02         # sanity anchor 밴드(§10-6).
YEARS: Tuple[int, ...] = (2022, 2023)

# §14-F8 강제 인쇄 딱지 — 39절 AND 프록시의 하한 성격.
OVERLAP_PROXY_TAG = (
    "챔피언 발동 프록시 = 39절 플랫 AND(bit_1~39). RR8_12 병합 다분기(CNF)·엔진 상태 변수"
    "(경과틱수·warmup·1일1진입·순매수금액 타이밍) 미포함 → 발화 **과소추정** → 본 겹침률은 "
    "참 겹침의 **하한**이다(구별로 보여도 실제 더 겹칠 수 있음). 실측 보완은 A-5 엔진 겹침(§14-F3)."
)


def candidate_fire_mask(cand: Candidate, bit_arrays: Mapping[str, np.ndarray]) -> np.ndarray:
    """후보 발화 = 선택 비트의 논리곱(전 비트 만족). bit_arrays 는 라벨 온셋 위 bool 배열."""
    fire = np.ones_like(next(iter(bit_arrays.values())), dtype=bool)
    for b in cand.bits:
        fire &= bit_arrays[b].astype(bool)
    return fire


def champion_and_mask(bit_arrays: Mapping[str, np.ndarray]) -> np.ndarray:
    """챔피언 발동 프록시 = 39절 플랫 AND(§7·§14-F8) — 발화 하한 프록시."""
    mask = np.ones_like(next(iter(bit_arrays.values())), dtype=bool)
    for b in CHAMPION_AND_BITS:
        mask &= bit_arrays[b].astype(bool)
    return mask


def qualify_candidates(
    bit_arrays: Mapping[str, np.ndarray], days: np.ndarray,
    candidates: Sequence[Candidate] = CANDIDATES,
) -> Dict[str, object]:
    """[3] 자격 — 발화 n·연도별 계수·표본 하한. **L3 미접촉**(bit_arrays·days 만).

    호출부는 bit_arrays 에 L3 파생을 넣지 않아야 한다(방어 assert). 자격 확정 후 분모 변경 금지.
    """
    forbidden = {"l3_net", "l3_labeled", "l3_clause", "l3_exit"}
    assert not (forbidden & set(bit_arrays)), "자격 게이트가 L3 컬럼을 참조했다(§6 순서 위반)"
    years = (np.asarray(days) // 10000).astype(np.int64)
    per: Dict[str, object] = {}
    qualified: List[str] = []
    for c in candidates:
        fire = candidate_fire_mask(c, bit_arrays)
        n = int(fire.sum())
        yc = {int(yr): int((fire & (years == yr)).sum()) for yr in YEARS}
        floor = bool(n >= FLOOR_N and all(yc[yr] >= FLOOR_YEAR for yr in YEARS))
        per[c.cid] = {"cid": c.cid, "family": c.family, "bits": list(c.bits),
                      "n_fire": n, "year_counts": yc, "floor_pass": floor}
        if floor:
            qualified.append(c.cid)
    return {
        "kind": "o4_qualification",
        "n_candidates": len(candidates), "n_qualified": len(qualified),
        "fdr_denominator": len(qualified), "qualified_cids": qualified,
        "floor_n": FLOOR_N, "floor_year": FLOOR_YEAR, "per_candidate": per,
    }


def day_block_mean_bootstrap(
    day_ids: np.ndarray, y: np.ndarray, *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, float]:
    """단일군 발화 평균 일자블록 부트스트랩 → {point, ci_low, ci_high, p_one, p_two}.

    일 복원추출, 재표집마다 mean = Σ(y|재표집 일) / Σ(count|재표집 일)(합의 비 — 일내 상관 보존).
    CI=95% 백분위, p_one=P(mean*≤0). judge.day_block_diff_bootstrap 의 단일군 판본.
    """
    day_arr = np.asarray(day_ids)
    y_arr = np.asarray(y, dtype=np.float64)
    if day_arr.size == 0:
        return {"point": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "p_one": 1.0, "p_two": 1.0}
    _, inv = np.unique(day_arr, return_inverse=True)
    nd = int(inv.max()) + 1
    dsum = np.bincount(inv, weights=y_arr, minlength=nd)
    dcnt = np.bincount(inv, minlength=nd).astype(np.float64)
    point = float(dsum.sum() / dcnt.sum())
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nd, size=(n_boot, nd))
    with np.errstate(divide="ignore", invalid="ignore"):
        reps = dsum[idx].sum(1) / dcnt[idx].sum(1)
    valid = reps[np.isfinite(reps)]
    if valid.size == 0:
        return {"point": point, "ci_low": float("nan"), "ci_high": float("nan"),
                "p_one": 1.0, "p_two": 1.0}
    lo, hi = np.percentile(valid, [2.5, 97.5])
    p_one = float(np.mean(valid <= 0.0))
    p_two = float(min(1.0, 2.0 * min(p_one, 1.0 - p_one)))
    return {"point": point, "ci_low": float(lo), "ci_high": float(hi),
            "p_one": p_one, "p_two": p_two}


def judge_candidate(
    cand: Candidate, bit_arrays: Mapping[str, np.ndarray], net_pp: np.ndarray,
    days: np.ndarray, years: np.ndarray, champ_fire: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED,
) -> Dict[str, object]:
    """[4][5] 후보 1개 — 발화 mean L3·CI·p·MDE·연도평균·겹침(FDR/분류는 judge_all)."""
    fire = candidate_fire_mask(cand, bit_arrays)
    n = int(fire.sum())
    mean = float(net_pp[fire].mean()) if n else float("nan")
    boot = day_block_mean_bootstrap(days[fire], net_pp[fire], n_boot=n_boot, seed=seed)
    mde = _mde_from_ci(boot["ci_low"], boot["ci_high"])

    year_mean = {}
    for yr in YEARS:
        m = fire & (years == yr)
        mv = float(net_pp[m].mean()) if int(m.sum()) else float("nan")
        year_mean[int(yr)] = {"mean_pp": round(mv, 6) if np.isfinite(mv) else None,
                              "sign": int(np.sign(mv)) if np.isfinite(mv) else 0,
                              "n": int(m.sum())}
    both_pos = all(year_mean[int(yr)]["sign"] == 1 for yr in YEARS)

    n_ov = int((fire & champ_fire).sum())
    overlap = float(n_ov / n) if n else float("nan")
    return {
        "cid": cand.cid, "family": cand.family, "bits": list(cand.bits),
        "n_fire": n, "mean_net_pp": round(mean, 6) if np.isfinite(mean) else None,
        "ci_low_pp": round(boot["ci_low"], 6) if np.isfinite(boot["ci_low"]) else None,
        "ci_high_pp": round(boot["ci_high"], 6) if np.isfinite(boot["ci_high"]) else None,
        "p_one_sided": round(boot["p_one"], 6), "p_two_sided": round(boot["p_two"], 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_mean": year_mean, "both_year_positive": bool(both_pos),
        "n_champ_overlap": n_ov,
        "overlap_rate": round(overlap, 6) if np.isfinite(overlap) else None,
        "n_boot": n_boot, "seed": seed,
    }


def _classify(r: Mapping[str, object]) -> str:
    """§6 분류 — 생존/아류/약신호/양EV증거0. fdr_survive 는 judge_all 이 주입 후 호출."""
    mean = r["mean_net_pp"]
    cl = r["ci_low_pp"]
    surv = r["fdr_survive"]
    ov = r["overlap_rate"]
    if mean is None or cl is None:
        return "insufficient"
    if surv and mean >= EFFECT_FLOOR_PP and cl > 0 and r["both_year_positive"]:
        if ov is not None and ov <= OVERLAP_CAP:
            return "survive"
        return "derivative"            # 아류(겹침 초과) — kill 아님(§7).
    if WEAK_LOW_PP <= mean < EFFECT_FLOOR_PP and cl > 0 and r["both_year_positive"]:
        return "weak_signal"
    return "no_positive_ev"            # 양EV 증거 0(§10 kill-1 재료).


def judge_all_candidates(
    qualification: Mapping[str, object], bit_arrays: Mapping[str, np.ndarray],
    net_pp: np.ndarray, days: np.ndarray, years: np.ndarray,
    *, n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """자격 후보 전체 판정 + BH-FDR(분모=자격 후보) + 겹침 분류 + 족 계상 + sanity(§6·§7·§8)."""
    champ_fire = champion_and_mask(bit_arrays)
    by_cid = {c.cid: c for c in CANDIDATES}
    qualified = list(qualification["qualified_cids"])

    per: Dict[str, Dict[str, object]] = {}
    for cid in qualified:
        per[cid] = judge_candidate(by_cid[cid], bit_arrays, net_pp, days, years,
                                   champ_fire, n_boot=n_boot, seed=seed)

    pvals = [float(per[cid]["p_two_sided"]) for cid in qualified]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    for i, cid in enumerate(qualified):
        per[cid]["fdr_survive"] = bool(survive[i])
        per[cid]["classification"] = _classify(per[cid])

    surv = [c for c in qualified if per[c]["classification"] == "survive"]
    deriv = [c for c in qualified if per[c]["classification"] == "derivative"]
    weak = [c for c in qualified if per[c]["classification"] == "weak_signal"]
    no_ev = [c for c in qualified if per[c]["classification"] == "no_positive_ev"]

    # 족 계상(§8) — 임계만 다른 후보 = 1족. 족 내 ≥1 생존 ∧ 동부호(+) → 그 족 1건.
    fam_members = families()
    fam_result: Dict[str, object] = {}
    for fam, cids in fam_members.items():
        elig = [c for c in cids if c in qualified]
        if not elig:
            continue
        surv_here = [c for c in elig if per[c]["classification"] == "survive"]
        signs = {int(np.sign(per[c]["mean_net_pp"])) for c in elig
                 if per[c]["mean_net_pp"] is not None}
        fam_result[fam] = {
            "eligible": elig, "n_survive": len(surv_here),
            "survive_family": bool(surv_here and signs == {1}),
        }
    survive_families = [f for f, r in fam_result.items() if r["survive_family"]]

    # sanity anchor(§10-6): 전 자격 후보 |mean − 서지풀 −1.008|<0.02 → 무차별 수렴 의심.
    devs = [abs(per[c]["mean_net_pp"] - POOL_MEAN_PP) for c in qualified
            if per[c]["mean_net_pp"] is not None]
    sanity_trip = bool(devs and max(devs) < SANITY_BAND_PP)

    return {
        "per_candidate": per,
        "n_qualified": len(qualified), "fdr_denominator": len(qualified), "fdr_q": fdr_q,
        "survive_cids": surv, "derivative_cids": deriv,
        "weak_signal_cids": weak, "no_positive_ev_cids": no_ev,
        "n_survive": len(surv), "n_derivative": len(deriv),
        "family_result": fam_result, "survive_families": survive_families,
        "n_survive_families": len(survive_families),
        "overlap_cap": OVERLAP_CAP, "overlap_proxy_tag": OVERLAP_PROXY_TAG,
        "pool_mean_pp_ref": POOL_MEAN_PP,
        "sanity_anchor_tripped": sanity_trip,
        # §10 kill-1: 생존(겹침 통과 양EV) 0 → "가산 조합으로 음의 지형 못 뒤집음".
        "kill1_no_survivor": bool(len(surv) == 0),
        # 아류만 생존(§10-4): 생존 0 이나 겹침 전이면 양EV였을 후보(아류)만 존재.
        "only_derivative": bool(len(surv) == 0 and len(deriv) > 0),
    }
