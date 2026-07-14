"""B-ext 판정 — 무결성·신규비트 패리티 → 가지/합동 anchor mean L3·등급·FDR·3분법·층화 (봉인본 §6·§7·§14).

- 무결성: 은행(0b6268e0)·d1 비트(4df57b77) 지문(pair_gate) + ext 비트 행수·키 정합.
- 신규비트 패리티: 온셋 100 × ext 절 — 벡터(numpy &/~) vs 독립 스칼라(Python 연쇄비교/not) 100% 일치.
- 가지 발화 = 재사용(bit_N) + 신규(ext_id) AND. 합동 anchor = 챔피언 902/905(branches) + 전 측정 가지
  발화 합집합(dedup, §14-F4 insufficient 포함).
- mean L3·day_block 부트스트랩(seed 20260716)·등급(judge_b)·FDR(정식+anchor)·3분법(judge_b.anchor_verdict)·
  가문 족 2층·층화 mean(가문/비가문·전략별, §7)·sanity.

부트스트랩·등급·3분법은 judge_b 재사용(드리프트 금지). 엔진 0회.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.btrack import judge_b
from alpha_lab.btrack.branches import BRANCH_902_NUMS, BRANCH_905_NUMS, branch_bit_cols
from alpha_lab.btrack.ext_parse import compile_clause
from alpha_lab.clause_lab.gate import sample_onset_namespace
from alpha_lab.stats_common import bh_fdr

logger = logging.getLogger(__name__)

SEED = 20260716               # §14-F6.
N_BOOT = 400
FDR_Q = 0.10

__all__ = ["SEED", "ext_parity_gate", "judge_ext"]


def _mask_and(bit_arrays: Mapping[str, np.ndarray], cols: Sequence[str]) -> np.ndarray:
    fire = np.ones_like(next(iter(bit_arrays.values())), dtype=bool)
    for c in cols:
        fire &= bit_arrays[c].astype(bool)
    return fire


def ext_parity_gate(db_dir, days: Sequence[str], new_bit_defs: Mapping[str, Tuple[str, bool]],
                    *, sample: int = 100, seed: int = SEED) -> Dict[str, object]:
    """신규 비트 벡터(numpy) vs 독립 스칼라(Python 연쇄비교/not) 100% 일치(§5 패리티)."""
    onset_ns, _ = sample_onset_namespace(db_dir, days, max(sample, 300))
    total = int(onset_ns["현재가"].shape[0])
    n = int(min(sample, total))
    rng = np.random.default_rng(seed)
    sel = np.sort(rng.choice(total, size=n, replace=False)) if total > n else np.arange(total)
    preds = {bid: compile_clause(canon, negated=bool(neg)) for bid, (canon, neg) in new_bit_defs.items()}
    per_bit: Dict[str, int] = {bid: 0 for bid in new_bit_defs}
    mism: List[dict] = []
    for bid, (canon, negated) in new_bit_defs.items():
        ci = preds[bid]
        vec = ci.predicate(onset_ns)
        for i in sel.tolist():
            env = {k: float(onset_ns[k][i]) for k in ci.symbols if k in onset_ns}
            sval = ci.scalar_eval(env)   # 독립 스칼라(연쇄비교/분모>0/not).
            if bool(vec[i]) == sval:
                per_bit[bid] += 1
            elif len(mism) < 20:
                mism.append({"bit": bid, "onset_row": int(i), "canon": canon,
                             "vec": bool(vec[i]), "scalar": sval})
    n_eval = len(sel)
    agree = sum(per_bit.values())
    n_pairs = n_eval * len(new_bit_defs)
    return {"kind": "b_ext_new_bit_parity", "n_onsets": n_eval, "n_bits": len(new_bit_defs),
            "n_pairs": n_pairs, "n_agree": agree,
            "agreement_pct": (100.0 * agree / n_pairs) if n_pairs else 100.0,
            "mismatches": mism, "pass": bool(n_pairs == 0 or agree == n_pairs)}


def judge_ext(branches: Sequence[Mapping[str, object]], bit_arrays: Mapping[str, np.ndarray],
              net_pp: np.ndarray, days: np.ndarray, years: np.ndarray,
              *, engine_ref: Optional[Mapping] = None, n_boot: int = N_BOOT,
              seed: int = SEED, fdr_q: float = FDR_Q) -> Dict[str, object]:
    """전 측정 가지 + 합동 anchor 판정 (§6·§7·§14-F4).

    branches = [{"id","strategy","bit_cols","is_family"}...] (측정가능 분기, ext_select 유래).
    """
    # 챔피언 902/905 발화(branches.py 재사용).
    champ902 = _mask_and(bit_arrays, branch_bit_cols(BRANCH_902_NUMS))
    champ905 = _mask_and(bit_arrays, branch_bit_cols(BRANCH_905_NUMS))

    per: Dict[str, Dict[str, object]] = {}
    fires: Dict[str, np.ndarray] = {}
    union = champ902 | champ905
    for br in branches:
        bid = str(br["id"])
        fire = _mask_and(bit_arrays, list(br["bit_cols"]))
        fires[bid] = fire
        union = union | fire
        u = judge_b.judge_unit(bid, fire, net_pp, days, years, n_boot=n_boot, seed=seed)
        u["strategy"] = br["strategy"]
        u["is_family"] = bool(br["is_family"])
        per[bid] = u

    # 챔피언 두 가지도 유닛으로(기존 114 포함).
    for name, fire in (("champ_902", champ902), ("champ_905", champ905)):
        u = judge_b.judge_unit(name, fire, net_pp, days, years, n_boot=n_boot, seed=seed)
        u["strategy"] = "ALP_V4_RR8_12"
        u["is_family"] = True
        per[name] = u
        fires[name] = fire

    anchor = judge_b.judge_unit("anchor", union, net_pp, days, years, n_boot=n_boot, seed=seed)
    verdict = judge_b.anchor_verdict(anchor)
    anchor["frame_verdict"] = verdict

    # FDR: 정식 등급 가지 + anchor.
    formal = [k for k in per if per[k]["tier"] == "formal"]
    fdr_names = ["anchor"] + formal
    pvals = [float(anchor["p_two_sided"])] + [float(per[k]["p_two_sided"]) for k in formal]
    survive = bh_fdr(pvals, q=fdr_q) if pvals else np.zeros(0, dtype=bool)
    anchor["fdr_survive"] = bool(survive[0]) if len(survive) else False
    for i, k in enumerate(formal):
        per[k]["fdr_survive"] = bool(survive[i + 1])
    for k in per:
        per[k].setdefault("fdr_survive", False)
        per[k]["classification"] = judge_b._classify_branch(per[k], per[k]["fdr_survive"])

    # 층화 mean(§7): 가문/비가문·전략별.
    def _union_mean(keys: Sequence[str]) -> Dict[str, object]:
        if not keys:
            return {"n": 0, "mean_pp": None}
        m = np.zeros_like(union, dtype=bool)
        for k in keys:
            m = m | fires[k]
        n = int(m.sum())
        return {"n": n, "mean_pp": round(float(net_pp[m].mean()), 6) if n else None}

    fam_keys = [k for k in per if per[k]["is_family"]]
    nonfam_keys = [k for k in per if not per[k]["is_family"]]
    strat_keys: Dict[str, List[str]] = {}
    for k in per:
        strat_keys.setdefault(str(per[k]["strategy"]), []).append(k)
    stratified = {
        "family": _union_mean(fam_keys), "nonfamily": _union_mean(nonfam_keys),
        "per_strategy": {s: _union_mean(ks) for s, ks in strat_keys.items()},
    }

    # 가문 족 2층 계상(§14-F5): 전략내 임계변형 가지 = 1족(전략 단위) · 902/905 동일-시분초 초족.
    fam_pos = {}
    for s, ks in strat_keys.items():
        surv = [k for k in ks if per[k]["classification"] == "positive_formal"]
        obs = [k for k in ks if per[k]["classification"] == "positive_observational"]
        fam_pos[s] = {"n_positive_formal": len(surv), "n_positive_observational": len(obs)}

    devs = [abs(per[k]["mean_net_pp"] - judge_b.POOL_MEAN_PP) for k in per
            if per[k]["mean_net_pp"] is not None]
    sanity_trip = bool(devs and max(devs) < judge_b.SANITY_BAND_PP)

    gap = {}
    if engine_ref:
        for yr in (2022, 2023):
            eng = engine_ref.get(yr) or engine_ref.get(str(yr))
            off = anchor["year_mean"][int(yr)]["mean_pp"]
            gap[int(yr)] = {"engine_avg_pct": (eng or {}).get("avg_profit_pct"),
                            "engine_trades": (eng or {}).get("trade_count"),
                            "offline_anchor_mean_pp": off,
                            "gap_pp": (round((eng or {}).get("avg_profit_pct") - off, 6)
                                       if eng and (eng or {}).get("avg_profit_pct") is not None
                                       and off is not None else None)}

    pos_formal = [k for k in per if per[k]["classification"] == "positive_formal"]
    pos_obs = [k for k in per if per[k]["classification"] == "positive_observational"]
    return {
        "units": per, "anchor": anchor, "anchor_frame_verdict": verdict,
        "fdr_denominator": len(fdr_names), "fdr_names": fdr_names, "formal_branches": formal,
        "positive_formal": pos_formal, "positive_observational": pos_obs,
        "n_positive_formal": len(pos_formal), "n_positive_observational": len(pos_obs),
        "stratified_mean": stratified, "family_positive_by_strategy": fam_pos,
        "engine_gap": gap, "pool_mean_pp_ref": judge_b.POOL_MEAN_PP,
        "sanity_anchor_tripped": sanity_trip,
        "kill1_frame_gap": bool(verdict == "frame_gap" and len(pos_formal) == 0),
        "b3_coordinates": pos_formal + pos_obs,   # B-3 OR 조립 좌표(정식+관찰 양+).
    }
