"""EV 채택기 — preregistration_v3 봉인 adoption_ev 게이트 그대로 (v3 P1).

봉인 기준(preregistration_v3.json sha 50d3d38a — adoption_ev):
- primary: 일블록 부트스트랩 CI_low(mean L3_net) > 0 (n_boot 1000, seed 20260707)
- per_year: 발견창 전 연도(2023·2024) 각각 EV > 0
- support_min: 1000, fdr_q: 0.05 (BH step-up)
- transition_rate_per_day [5,60] 예산은 transition.measure_transition_ev 소관
  (채택 후보의 전이 재측정 단계에서 별도 판정).

RC-0 처방: v1/v2의 lift(적중률 배수) 채택을 폐기하고 경제성(EV = mean
L3_net)의 CI 하한을 채택 기준 그 자체로 삼는다.

재사용 규율(재구현 금지): 마스크 재구성은 alpha_lab.mining.stats.rule_mask,
부트스트랩·FDR은 alpha_lab.stats_common(day_block_bootstrap/bh_fdr)만 쓴다.
리프 i의 부트스트랩 시드는 seed+i — evaluate_leaves와 동일 관례.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence

import numpy as np

from alpha_lab.mining.stats import rule_mask
from alpha_lab.stats_common import bh_fdr, day_block_bootstrap

__all__ = [
    "SEALED_FDR_Q",
    "SEALED_N_BOOT",
    "SEALED_SEED",
    "SEALED_SUPPORT_MIN",
    "adopt_by_ev",
]

logger = logging.getLogger(__name__)

# preregistration_v3.adoption_ev 봉인값 — 함수 기본 인자와 단일 원천.
SEALED_N_BOOT = 1000
SEALED_SEED = 20260707
SEALED_SUPPORT_MIN = 1000
SEALED_FDR_Q = 0.05


def _validate_inputs(
    X: np.ndarray,
    y: np.ndarray,
    day_ids: np.ndarray,
    per_year_masks: Dict[int, np.ndarray],
) -> Dict[int, np.ndarray]:
    if X.ndim != 2:
        raise ValueError(f"X는 2차원 배열이어야 한다: shape={X.shape}")
    if not (X.shape[0] == y.shape[0] == day_ids.shape[0]):
        raise ValueError("X/y_net/day_ids 표본수가 서로 다르다")
    if not per_year_masks:
        raise ValueError("per_year_masks는 최소 1개 연도가 필요하다")
    validated: Dict[int, np.ndarray] = {}
    for year, year_mask in per_year_masks.items():
        ym = np.asarray(year_mask, dtype=bool)
        if ym.ndim != 1 or ym.shape[0] != X.shape[0]:
            raise ValueError(
                f"연도 {year} 마스크 길이({ym.shape})가 표본수({X.shape[0]})와 다르다"
            )
        validated[year] = ym
    return validated


def _per_year_ev(
    y: np.ndarray, mask: np.ndarray, per_year_masks: Dict[int, np.ndarray]
) -> Dict[int, float]:
    """연도별 EV = 그 연도 ∩ 리프 표본의 y_net 평균. 표본 0이면 nan."""
    out: Dict[int, float] = {}
    for year, ym in per_year_masks.items():
        sub = mask & ym
        count = int(sub.sum())
        out[year] = float(y[sub].mean()) if count else float("nan")
    return out


def adopt_by_ev(
    leaves: Sequence[dict],
    X: np.ndarray,
    y_net: np.ndarray,
    day_ids: np.ndarray,
    *,
    n_boot: int = SEALED_N_BOOT,
    seed: int = SEALED_SEED,
    support_min: int = SEALED_SUPPORT_MIN,
    fdr_q: float = SEALED_FDR_Q,
    per_year_masks: Dict[int, np.ndarray],
) -> List[dict]:
    """봉인 adoption_ev 게이트 — 리프별 EV 평가 dict를 새로 만들어 반환한다.

    리프마다 rule_mask로 표본 마스크를 재구성하고
    day_block_bootstrap(stat='mean', seed+i)으로 EV 점추정·95% CI·단측 p를
    얻은 뒤, 전체 리프 p에 bh_fdr(fdr_q)를 적용한다. 채택(adopted)은 봉인
    4게이트 동시 충족이다:
        fdr_survivor ∧ ci_low > 0 ∧ support_eval >= support_min
        ∧ 전 연도 per_year_ev > 0 (nan은 보수적으로 탈락)

    반환 dict(원본 리프 불변, 키 부착):
        ev, ci_low, ci_high, p, support_eval(평가 표본 기준 마스크 크기),
        per_year_ev({연도: EV}), fdr_survivor, adopted.
    y_net은 연속 실현손익(L3_net %) — (0/1) 라벨이 아니라 mean 통계다.
    """
    X_arr = np.asarray(X, dtype=np.float32)
    y_arr = np.asarray(y_net, dtype=np.float64)
    day_arr = np.asarray(day_ids)
    year_masks = _validate_inputs(X_arr, y_arr, day_arr, per_year_masks)
    evaluated: List[dict] = []
    for i, leaf in enumerate(leaves):
        mask = rule_mask(X_arr, leaf)
        boot = day_block_bootstrap(
            day_arr, y_arr, mask, n_boot=n_boot, seed=seed + i, stat="mean"
        )
        evaluated.append(
            {
                **leaf,
                "ev": float(boot["point"]),
                "ci_low": float(boot["ci_low"]),
                "ci_high": float(boot["ci_high"]),
                "p": float(boot["p_one_sided"]),
                "support_eval": int(mask.sum()),
                "per_year_ev": _per_year_ev(y_arr, mask, year_masks),
            }
        )
    survivors = (
        bh_fdr([item["p"] for item in evaluated], fdr_q)
        if evaluated
        else np.zeros(0, dtype=bool)
    )
    results: List[dict] = []
    n_adopted = 0
    for item, survived in zip(evaluated, survivors):
        per_year = item["per_year_ev"]
        adopted = bool(
            survived
            and item["ci_low"] > 0.0  # nan > 0 은 False — 보수적.
            and item["support_eval"] >= int(support_min)
            and all(value > 0.0 for value in per_year.values())
        )
        n_adopted += int(adopted)
        results.append({**item, "fdr_survivor": bool(survived), "adopted": adopted})
    logger.info(
        "adopt_by_ev leaves=%d n=%d n_boot=%d seed=%d support_min=%d "
        "fdr_q=%.3f years=%s fdr_survivors=%d adopted=%d",
        len(results), X_arr.shape[0], n_boot, seed, support_min, fdr_q,
        sorted(year_masks), int(np.asarray(survivors).sum()), n_adopted,
    )
    return results
