"""L3 재현 게이트 + R3 리플레이 triage — Δnet·CI·MDE·가문/연도 일관성·겹침률.

봉인 근거: 2026-07-12_d5r_conditional_exit_preregistration.md §6·§7·§8.

L3 게이트: 패치 반사실 청산의 순수 vs 벡터 대조(청산 시각·가격 동시 일치율
≥99.9%, 수익률오차 중앙 0.0, p99 ≤0.10%p). R3: 영향거래 Δnet 점추정·일자블록
부트스트랩 CI(n_boot 400)·MDE 병기·RR8 가문 내 방향 일관성(12→0·21)·연도 방향·
반기 부호(보조)·Family B 겹침률(≤0.50, 민감도 0.55/0.60). 표본 하한 미달 셀은
§5.1대로 채택 대상이 아니며(kill-2), 여기 산출은 §5.2 MDE 병기(미검출 vs 효과
없음 구분)를 위한 진단이다.
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Mapping, Sequence

import numpy as np

from alpha_lab.exitlab_r.patch_exit import Patch, replay_patched_vector
from alpha_lab.stats_common import day_block_bootstrap

__all__ = [
    "BOOTSTRAP_SEED",
    "N_BOOT",
    "MDE_Z",
    "run_l3_gate",
    "run_r3_candidate",
]

logger = logging.getLogger(__name__)

N_BOOT = 400                 # §7 일자블록 부트스트랩 반복.
BOOTSTRAP_SEED = 20260712    # 봉인 시드(재현성).
MDE_Z = 2.802                # (z_0.975 + z_0.80) — 양측 5%·검정력 80% MDE 계수.


# ---------------------------------------------------------------------------
# L3 재현 게이트 — 패치 청산 순수 vs 벡터.
# ---------------------------------------------------------------------------

def run_l3_gate(
    full_records: Sequence[Mapping],
    get_ctx: Callable[[str, int], object], candidates: Sequence[Patch],
    *, threshold: float = 0.999,
) -> dict:
    """후보별 패치 청산의 순수(레코드 저장분) vs 벡터 재계산 대조.

    레코드의 cand[label] 은 순수 경로 실측(pipeline). 같은 거래를 벡터 경로로
    재계산해 청산 시각·가격 **동시** 일치율(match=시각∧가격)과 수익률 오차를
    잰다. 영향거래(현직과 청산 상이)만 채점(무영향 현직은 identity 재현게이트가
    커버). 미달 시 순수 경로 유지(순수가 이 triage 의 채점 경로).
    """
    per_cand: Dict[str, dict] = {}
    match_total = total = 0
    err_all: List[float] = []
    for p in candidates:
        n = both = 0
        errs: List[float] = []
        mism: List[dict] = []
        for r in full_records:
            if r.get("status") != "ok":
                continue
            pure = r["cand"][p.label]
            if not pure["affected"]:
                continue
            ctx = get_ctx(r["code6"], r["day"])
            vec = replay_patched_vector(
                ctx, buy_time=int(r["buy_time"]), buy_price=float(r["buy_price"]),
                qty=int(r["qty"]), patch=p,
            )
            n += 1
            err = abs(vec.profit_pct - pure["pct"])
            errs.append(err)
            same = (vec.sell_time == pure["time"]
                    and abs(vec.sell_price - pure["price"]) < 1e-9)
            if same:
                both += 1
            else:
                mism.append({"code6": r["code6"], "buy_time": r["buy_time"],
                             "pure_time": pure["time"], "vec_time": vec.sell_time,
                             "pure_price": pure["price"], "vec_price": vec.sell_price,
                             "err_pp": round(err, 4)})
        arr = np.array(errs, dtype=np.float64) if errs else np.zeros(0)
        per_cand[p.label] = {
            "n_affected": n, "n_match": both,
            "match_rate": round(both / n, 6) if n else None,
            "err_median_pp": round(float(np.median(arr)), 6) if arr.size else None,
            "err_p99_pp": round(float(np.percentile(arr, 99)), 6) if arr.size else None,
            "err_max_pp": round(float(arr.max()), 6) if arr.size else None,
            "mismatches": mism[:10],
        }
        total += n
        match_total += both
        err_all.extend(errs)
    ea = np.array(err_all, dtype=np.float64) if err_all else np.zeros(0)
    overall_rate = (match_total / total) if total else 1.0
    return {
        "threshold": threshold,
        "n_pairs": total,
        "match_rate_overall": round(overall_rate, 6),
        "err_median_pp_overall": round(float(np.median(ea)), 6) if ea.size else 0.0,
        "err_p99_pp_overall": round(float(np.percentile(ea, 99)), 6) if ea.size else 0.0,
        "err_max_pp_overall": round(float(ea.max()), 6) if ea.size else 0.0,
        "gate_pass": bool(total == 0 or overall_rate >= threshold),
        "engine_used": "pure",  # 벡터는 게이트 통과 시에도 순수와 동치 — 순수 채점 유지.
        "per_candidate": per_cand,
    }


# ---------------------------------------------------------------------------
# R3 리플레이 triage — 후보 1개.
# ---------------------------------------------------------------------------

def _half(day: int) -> str:
    mm = (int(day) // 100) % 100
    return "H1" if mm <= 6 else "H2"


def _mde_from_ci(ci_low: float, ci_high: float) -> float:
    """부트스트랩 백분위 CI 폭에서 SE 근사 → MDE = MDE_Z × SE.

    95% 백분위 CI 폭 ≈ 2·1.96·SE 이므로 SE ≈ (hi−lo)/3.92.
    """
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        return float("nan")
    se = (ci_high - ci_low) / (2.0 * 1.959963985)
    return MDE_Z * se


def run_r3_candidate(
    patch: Patch, deduped: Sequence[Mapping], full_records: Sequence[Mapping],
    *, adopt_floor: float, n_boot: int = N_BOOT, seed: int = BOOTSTRAP_SEED,
) -> dict:
    """후보 1개의 진단 triage — Δnet 점추정·CI·MDE·가문/연도/반기·겹침률.

    adopt_floor = 채택 Δnet 하한(Family A +0.20%p, B +0.10%p). 표본 하한 자격은
    호출측(lower_bound_table)이 판정 — 여기 verdict 는 자격 통과 전제의 진단
    분류(pass/weak/reject)를 병기하되, 자격 미달이면 최종은 inconclusive.
    """
    lab = patch.label
    aff = [r for r in deduped if r["cand"][lab]["affected"]]
    dnet = np.array([r["cand"][lab]["dnet_pp"] for r in aff], dtype=np.float64)
    dwon = np.array([r["cand"][lab]["dwon"] for r in aff], dtype=np.float64)
    days = np.array([r["day"] for r in aff], dtype=np.int64)
    mask = np.ones(len(aff), dtype=bool)

    boot = (day_block_bootstrap(days, dnet, mask, n_boot=n_boot, seed=seed, stat="mean")
            if len(aff) else {"point": float("nan"), "ci_low": float("nan"),
                              "ci_high": float("nan"), "p_one_sided": 1.0})
    mean_dnet = float(dnet.mean()) if dnet.size else float("nan")
    sum_dwon = int(dwon.sum()) if dwon.size else 0
    mde = _mde_from_ci(boot["ci_low"], boot["ci_high"])

    # 연도 방향.
    year_dir = {}
    for yr in (2022, 2023):
        d = dnet[days // 10000 == yr]
        year_dir[yr] = {"n": int(d.size),
                        "mean_dnet": round(float(d.mean()), 4) if d.size else None,
                        "sign": int(np.sign(d.mean())) if d.size else 0}
    # 반기 부호(보조).
    half_dir = {}
    for yr in (2022, 2023):
        for h in ("H1", "H2"):
            d = np.array([r["cand"][lab]["dnet_pp"] for r in aff
                          if r["year"] == yr and _half(r["day"]) == h])
            half_dir[f"{yr}{h}"] = {"n": int(d.size),
                                    "mean_dnet": round(float(d.mean()), 4) if d.size else None,
                                    "sign": int(np.sign(d.mean())) if d.size else 0}

    # RR8 가문 내 일관성 — 챔피언별 자기 영향거래 평균 Δnet 부호(비-dedup).
    champ_dir = {}
    for champ in ("RR8_12", "RR8_0", "RR8_21"):
        d = np.array([r["cand"][lab]["dnet_pp"] for r in full_records
                      if r.get("status") == "ok" and r["champ"] == champ
                      and r["cand"][lab]["affected"]])
        champ_dir[champ] = {"n": int(d.size),
                            "mean_dnet": round(float(d.mean()), 4) if d.size else None,
                            "sign": int(np.sign(d.mean())) if d.size else 0}
    base_sign = champ_dir["RR8_12"]["sign"]
    agree = sum(1 for c in ("RR8_12", "RR8_0", "RR8_21")
                if champ_dir[c]["sign"] == base_sign and base_sign != 0)
    family_consistent = bool(base_sign != 0 and agree >= 2)

    # Family B 겹침률(§8) — |B 발동| / |보유≥T 도달| (deduped).
    overlap = None
    if patch.family == "B":
        b_fired = sum(1 for r in deduped if r["cand"][lab]["b_fired"])
        denom = sum(1 for r in deduped if r["per_T"][int(patch.T)]["held"] == 1)
        ov = (b_fired / denom) if denom else float("nan")
        overlap = {
            "b_fired": b_fired, "held_ge_T": denom,
            "overlap_rate": round(float(ov), 4) if np.isfinite(ov) else None,
            "le_0.50": bool(ov <= 0.50), "le_0.55": bool(ov <= 0.55),
            "le_0.60": bool(ov <= 0.60),
            "kill4_fires": bool(np.isfinite(ov) and ov > 0.55),
        }

    ci_low = boot["ci_low"]
    both_year_same = (year_dir[2022]["sign"] == year_dir[2023]["sign"] != 0)
    # 진단 분류(자격 통과 전제) — 실제 채택은 하한 자격이 지배.
    if np.isfinite(ci_low) and ci_low > 0 and mean_dnet >= adopt_floor \
            and both_year_same and family_consistent \
            and (overlap is None or overlap["overlap_rate"] is None or overlap["le_0.50"]):
        diag = "pass_if_qualified"
    elif np.isfinite(mean_dnet) and 0.05 <= mean_dnet < adopt_floor \
            and np.isfinite(ci_low) and ci_low > 0:
        diag = "weak_signal"
    else:
        diag = "reject"

    return {
        "candidate": lab, "family": patch.family, "adopt_floor": adopt_floor,
        "n_affected": len(aff),
        "mean_dnet_pp": round(mean_dnet, 4) if np.isfinite(mean_dnet) else None,
        "sum_dwon_krw": sum_dwon,
        "ci_low_pp": round(float(boot["ci_low"]), 4) if np.isfinite(boot["ci_low"]) else None,
        "ci_high_pp": round(float(boot["ci_high"]), 4) if np.isfinite(boot["ci_high"]) else None,
        "p_one_sided": round(float(boot["p_one_sided"]), 4),
        "mde_pp": round(float(mde), 4) if np.isfinite(mde) else None,
        "n_boot": n_boot, "seed": seed,
        "year_direction": year_dir, "both_year_same_sign": bool(both_year_same),
        "half_year_sign": half_dir,
        "family_consistency": {"per_champion": champ_dir, "base_sign": base_sign,
                               "agree": agree, "consistent_2of3": family_consistent},
        "overlap": overlap,
        "diagnostic_class": diag,
    }
