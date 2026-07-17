"""B-트랙 가지 판정 — 무결성 → 가지/anchor 발화 mean L3·CI·등급·FDR·3분법 (봉인본 §4·§5·§6·§14-F4).

- 무결성: 은행(0b6268e0)·d1 비트(4df57b77) 지문 대조(pair_gate.check_integrity 재사용).
- 가지 발화 = §3 비트 AND(라벨 온셋 862,932 위). anchor = 902 ∨ 905(서로소 — 계수 합 assert).
- mean L3·day_block 단일군 부트스트랩 CI(seed 20260715·n_boot 400, o4lab 재사용·드리프트 금지)·
  양측 p·연도별 mean·MDE(clause_lab.judge._mde_from_ci 재사용).
- 표본 등급: 정식(n≥2,000∧연도≥400) / 관찰(100≤n<2,000) / insufficient(n<100).
- FDR q=0.10, 분모 = 정식 가지 + anchor 1. 관찰/insufficient 제외(열거).
- **anchor 3분법(§14-F4)**: (a) 재현 = mean≥+0.10∧CI하한>0∧연도동부호 / (b) 프레임 갭 = CI 상한<0 /
  (c) 미결 = 그 외(검정력 부족 — 프레임 판정 유보). 2분법의 검정력 오분류 방지.

엔진 0회. L3 재사용만. 엔진 실측 갭(A_2022 +0.82%/101·A_2023 +0.57%/197)은 판정과 병기.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

import numpy as np

from alpha_lab.btrack.branches import BRANCHES, TIME_GATE, branch_bit_cols
from alpha_lab.clause_lab.judge import _mde_from_ci
from alpha_lab.clause_lab.pair_gate import check_integrity
from alpha_lab.o4lab.judge_o4 import day_block_mean_bootstrap
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

__all__ = [
    "EFFECT_FLOOR_PP", "FDR_Q", "FORMAL_N", "FORMAL_YEAR", "N_BOOT", "OBS_N",
    "POOL_MEAN_PP", "SANITY_BAND_PP", "SEED", "YEARS",
    "anchor_verdict", "branch_fire_mask", "judge_branches", "judge_unit",
    "load_engine_reference", "sample_tier",
]

N_BOOT = 400
SEED = 20260715               # §14-F6.
FDR_Q = 0.10
EFFECT_FLOOR_PP = 0.10        # §6.
FORMAL_N = 2000               # 정식 등급 하한(§5·§14-F1).
FORMAL_YEAR = 400
OBS_N = 100                   # 관찰 등급 하한.
POOL_MEAN_PP = -1.008         # 서지 풀 평균(§4·d1 #22) — sanity 기준.
SANITY_BAND_PP = 0.02
YEARS: Tuple[int, ...] = (2022, 2023)


def branch_fire_mask(bit_arrays: Mapping[str, np.ndarray], nums: Tuple[int, ...]) -> np.ndarray:
    """가지 발화 = 절 비트의 논리곱(전 절 만족). bit_arrays 는 라벨 온셋 위 bool 배열."""
    cols = branch_bit_cols(nums)
    fire = np.ones_like(bit_arrays[cols[0]], dtype=bool)
    for c in cols:
        fire &= bit_arrays[c].astype(bool)
    return fire


def sample_tier(n: int, yc: Mapping[int, int]) -> str:
    """발화 계수 → 표본 등급(§5·§14-F1). 정식 = n≥2,000 ∧ 연도별 각 ≥400."""
    if n >= FORMAL_N and all(yc[yr] >= FORMAL_YEAR for yr in YEARS):
        return "formal"
    if n >= OBS_N:
        return "observational"
    return "insufficient"


def judge_unit(name: str, fire: np.ndarray, net_pp: np.ndarray,
               days: np.ndarray, years: np.ndarray,
               *, n_boot: int = N_BOOT, seed: int = SEED) -> Dict[str, object]:
    """가지/anchor 1개 — 발화 mean L3·CI·p·MDE·연도별 mean·등급(분류/FDR은 judge_branches)."""
    n = int(fire.sum())
    yc = {int(yr): int((fire & (years == yr)).sum()) for yr in YEARS}
    tier = sample_tier(n, yc)
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
    return {
        "name": name, "n_fire": n, "year_counts": yc, "tier": tier,
        "mean_net_pp": round(mean, 6) if np.isfinite(mean) else None,
        "ci_low_pp": round(boot["ci_low"], 6) if np.isfinite(boot["ci_low"]) else None,
        "ci_high_pp": round(boot["ci_high"], 6) if np.isfinite(boot["ci_high"]) else None,
        "p_one_sided": round(boot["p_one"], 6), "p_two_sided": round(boot["p_two"], 6),
        "mde_pp": round(mde, 6) if np.isfinite(mde) else None,
        "year_mean": year_mean, "both_year_positive": bool(both_pos),
        "n_boot": n_boot, "seed": seed,
    }


def anchor_verdict(r: Mapping[str, object]) -> str:
    """§14-F4 3분법 — (a) reproduce / (b) frame_gap / (c) undetermined."""
    mean, cl, ch = r["mean_net_pp"], r["ci_low_pp"], r["ci_high_pp"]
    if mean is None or cl is None or ch is None:
        return "undetermined"
    if mean >= EFFECT_FLOOR_PP and cl > 0 and r["both_year_positive"]:
        return "reproduce"            # (a) 오프라인이 챔피언 깊은 양(+) 재현.
    if ch < 0:
        return "frame_gap"            # (b) 명확한 음 — 프레임 갭 확정.
    return "undetermined"             # (c) CI 0 걸침 — 검정력 부족, 프레임 판정 유보.


def _classify_branch(r: Mapping[str, object], fdr_survive: bool) -> str:
    """가지 분류(§6) — 정식 양(+)/관찰 양(+)/음(−)/none."""
    mean, cl, ch = r["mean_net_pp"], r["ci_low_pp"], r["ci_high_pp"]
    if mean is None or cl is None:
        return "insufficient"
    if r["tier"] == "formal":
        if fdr_survive and mean >= EFFECT_FLOOR_PP and cl > 0 and r["both_year_positive"]:
            return "positive_formal"
        if ch is not None and ch < 0:
            return "negative"
        return "none"
    if r["tier"] == "observational":
        if mean > 0 and cl > 0 and r["both_year_positive"]:
            return "positive_observational"   # 보고만·채택 불가.
        if ch is not None and ch < 0:
            return "negative_observational"
        return "none_observational"
    return "insufficient"


def load_engine_reference(live_dir) -> Dict[str, object]:
    """B1 엔진 런(A_2022·A_2023)에서 거래수·평균수익%·승률 — 프레임 갭 서술 기준선."""
    out: Dict[str, object] = {}
    for yr, fname in ((2022, "A_2022.json"), (2023, "A_2023.json")):
        p = Path(live_dir) / fname
        if not p.exists():
            out[yr] = None
            continue
        m = json.loads(p.read_text(encoding="utf-8")).get("metrics", {})
        out[yr] = {"trade_count": m.get("trade_count"),
                   "avg_profit_pct": m.get("avg_profit_pct"),
                   "win_rate": m.get("win_rate")}
    return out


def judge_branches(
    bit_arrays: Mapping[str, np.ndarray], net_pp: np.ndarray, days: np.ndarray,
    years: np.ndarray, *, engine_ref: Optional[Mapping] = None,
    n_boot: int = N_BOOT, seed: int = SEED, fdr_q: float = FDR_Q,
) -> Dict[str, object]:
    """전 가지 + anchor 판정 + 등급 + FDR(정식+anchor) + 3분법 + sanity + 엔진 갭(§4·§6·§14-F4)."""
    f902 = branch_fire_mask(bit_arrays, BRANCHES["902"])
    f905 = branch_fire_mask(bit_arrays, BRANCHES["905"])
    n_disjoint = int((f902 & f905).sum())
    if n_disjoint != 0:
        raise ValueError(f"902·905 발화 비서로소({n_disjoint}) — 시간게이트 상호배타 위반(kill)")
    anchor = f902 | f905

    units = {
        "902": judge_unit("902", f902, net_pp, days, years, n_boot=n_boot, seed=seed),
        "905": judge_unit("905", f905, net_pp, days, years, n_boot=n_boot, seed=seed),
        "anchor": judge_unit("anchor", anchor, net_pp, days, years, n_boot=n_boot, seed=seed),
    }
    # anchor 계수 = 서로소 합(서술 검증).
    units["anchor"]["disjoint_sum_check"] = bool(
        units["anchor"]["n_fire"] == units["902"]["n_fire"] + units["905"]["n_fire"])

    # FDR 세트 = anchor + 정식 등급 가지(§8).
    formal_branches = [b for b in ("902", "905") if units[b]["tier"] == "formal"]
    fdr_names = ["anchor"] + formal_branches
    pvals = [float(units[n]["p_two_sided"]) for n in fdr_names]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    for i, n in enumerate(fdr_names):
        units[n]["fdr_survive"] = bool(survive[i])
    for b in ("902", "905"):
        units[b].setdefault("fdr_survive", False)
        units[b]["classification"] = _classify_branch(units[b], units[b]["fdr_survive"])

    verdict = anchor_verdict(units["anchor"])
    units["anchor"]["frame_verdict"] = verdict

    # sanity anchor(§7-5): 전 유닛 |mean − 서지풀 −1.008|<0.02 무차별 수렴.
    devs = [abs(units[n]["mean_net_pp"] - POOL_MEAN_PP) for n in ("902", "905", "anchor")
            if units[n]["mean_net_pp"] is not None]
    sanity_trip = bool(devs and max(devs) < SANITY_BAND_PP)

    # 엔진 갭(§4 한계 3): 오프라인 연도별 mean vs 엔진 avg_profit_pct.
    gap = {}
    if engine_ref:
        for yr in YEARS:
            eng = engine_ref.get(yr) or engine_ref.get(str(yr))
            off = units["anchor"]["year_mean"][int(yr)]["mean_pp"]
            if eng and eng.get("avg_profit_pct") is not None and off is not None:
                gap[int(yr)] = {"engine_avg_pct": eng["avg_profit_pct"],
                                "engine_trades": eng.get("trade_count"),
                                "offline_anchor_mean_pp": off,
                                "gap_pp": round(eng["avg_profit_pct"] - off, 6)}
            else:
                gap[int(yr)] = {"engine_avg_pct": (eng or {}).get("avg_profit_pct"),
                                "offline_anchor_mean_pp": off, "gap_pp": None}

    positive_formal = [b for b in ("902", "905")
                       if units[b]["classification"] == "positive_formal"]
    positive_obs = [b for b in ("902", "905")
                    if units[b]["classification"] == "positive_observational"]
    return {
        "units": units,
        "fdr_denominator": len(fdr_names), "fdr_q": fdr_q, "fdr_names": fdr_names,
        "formal_branches": formal_branches,
        "anchor_frame_verdict": verdict,
        "positive_formal_branches": positive_formal,
        "positive_observational_branches": positive_obs,
        "n_positive_formal": len(positive_formal),
        "pool_mean_pp_ref": POOL_MEAN_PP, "sanity_anchor_tripped": sanity_trip,
        "engine_gap": gap,
        # §7 kill-1: 프레임 갭 확정 ∧ 정식 양(+) 0.
        "kill1_frame_gap": bool(verdict == "frame_gap" and len(positive_formal) == 0),
    }
