"""공용 통계 유틸 — 레인 A(규칙 채굴)·레인 C(이벤트 스터디) 공용 단일 원본.

이 모듈이 유일 원본이다 — 레인별 중복 구현 금지(사전등록 규율).

- lift: 부분집합 양성률 / 전체 양성률 배율.
- day_block_bootstrap: 일(day) 블록 복원 재표집 부트스트랩. 표본 단위가 아닌
  '일 단위'로 재표집해 일중 상관을 보존한다. stat='lift'|'mean'.
- bh_fdr: Benjamini–Hochberg step-up FDR 통제(입력 순서 정렬 생존 마스크).

구현 노트: 부트스트랩 통계(lift·mean)는 합계의 비(ratio-of-sums)라서
일별 (Σy·mask, Σmask, Σy, n) 집계를 한 번 만든 뒤 일 인덱스 행렬로
벡터화 계산한다 — 재표집 표본을 실제로 이어붙이는 방식과 수학적으로 동일.
"""
from __future__ import annotations

import logging
from typing import Dict, Sequence, Tuple

import numpy as np

__all__ = ["bh_fdr", "day_block_bootstrap", "lift"]

logger = logging.getLogger(__name__)

_STATS = ("lift", "mean")
_CI_PERCENTILES = (2.5, 97.5)  # 95% 백분위 CI


def lift(positives: float, n: float, base_rate: float) -> float:
    """부분집합 양성률(positives/n)을 전체 양성률(base_rate)로 나눈 배율.

    n<=0 또는 base_rate<=0이면 정의 불가 → nan.
    """
    if n <= 0 or base_rate <= 0:
        return float("nan")
    return (float(positives) / float(n)) / float(base_rate)


def _per_day_aggregates(
    day_ids: np.ndarray, y: np.ndarray, mask: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """일별 (mask 내 y합, mask 내 표본수, 전체 y합, 전체 표본수) 벡터."""
    _, inv = np.unique(day_ids, return_inverse=True)
    n_days = int(inv.max()) + 1
    w_mask = mask.astype(np.float64)
    msum = np.bincount(inv, weights=y * w_mask, minlength=n_days)
    mcnt = np.bincount(inv, weights=w_mask, minlength=n_days)
    asum = np.bincount(inv, weights=y, minlength=n_days)
    acnt = np.bincount(inv, minlength=n_days).astype(np.float64)
    return msum, mcnt, asum, acnt


def _ratio_stat(msum, mcnt, asum, acnt, stat: str) -> np.ndarray:
    """합계(스칼라 또는 벡터) → 통계값. 정의 불가 원소는 nan.

    'mean' = msum/mcnt (mask 내 y 평균), 'lift' = (msum/mcnt)/(asum/acnt).
    mcnt==0(재표본에 mask 표본 없음), asum<=0(전체 양성 0) → nan.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        sub = np.asarray(msum, dtype=np.float64) / np.asarray(mcnt, dtype=np.float64)
        if stat == "mean":
            out = sub
        else:  # 'lift'
            out = sub * (
                np.asarray(acnt, dtype=np.float64) / np.asarray(asum, dtype=np.float64)
            )
    out = np.asarray(out, dtype=np.float64)
    return np.where(np.isfinite(out), out, np.nan)


def _summarize(point: float, reps: np.ndarray, stat: str) -> Dict[str, float]:
    """반복 통계 → {point, ci_low, ci_high, p_one_sided}.

    CI는 95% 백분위. p_one_sided는 '효과 없음' 방향(lift<=1 또는 mean<=0)
    반복 비율. nan 반복은 제외하고, 유효 반복 0이면 CI nan·p 1.0(보수).
    """
    valid = reps[np.isfinite(reps)]
    if valid.size == 0:
        return {
            "point": point,
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "p_one_sided": 1.0,
        }
    ci_low, ci_high = np.percentile(valid, _CI_PERCENTILES)
    null_edge = 1.0 if stat == "lift" else 0.0
    return {
        "point": point,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "p_one_sided": float(np.mean(valid <= null_edge)),
    }


def _validate_bootstrap_inputs(
    day_arr: np.ndarray, y_arr: np.ndarray, mask_arr: np.ndarray, n_boot: int, stat: str
) -> None:
    if day_arr.ndim != 1 or not (day_arr.shape == y_arr.shape == mask_arr.shape):
        raise ValueError("day_ids/y/mask는 같은 길이의 1차원 배열이어야 한다")
    if stat not in _STATS:
        raise ValueError(f"stat은 {_STATS} 중 하나여야 한다: {stat!r}")
    if n_boot < 1:
        raise ValueError(f"n_boot는 1 이상이어야 한다: {n_boot}")


def day_block_bootstrap(
    day_ids: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int,
    stat: str = "lift",
) -> Dict[str, float]:
    """일 블록 복원 재표집 부트스트랩 → {point, ci_low, ci_high, p_one_sided}.

    고유 일수를 D라 할 때 매 반복 D개 일을 복원 추출하고, 뽑힌 일들의 표본을
    그대로 이어붙인 재표본에서 통계를 계산한다(일중 상관 보존).
    stat='lift': mask 내 양성률 / 전체 양성률 — 분자·분모 모두 재표본 기준.
    stat='mean': mask 내 y 평균. point는 전체 표본 동일 산식 값.
    CI는 95% 백분위(2.5/97.5), p_one_sided는 효과 없음 방향(lift<=1 또는
    mean<=0) 반복 비율. seed는 필수 키워드(재현성 규율).
    """
    day_arr = np.asarray(day_ids)
    y_arr = np.asarray(y, dtype=np.float64)
    mask_arr = np.asarray(mask, dtype=bool)
    _validate_bootstrap_inputs(day_arr, y_arr, mask_arr, n_boot, stat)
    if day_arr.size == 0:
        return _summarize(float("nan"), np.full(n_boot, np.nan), stat)
    msum, mcnt, asum, acnt = _per_day_aggregates(day_arr, y_arr, mask_arr)
    point = float(_ratio_stat(msum.sum(), mcnt.sum(), asum.sum(), acnt.sum(), stat))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, msum.shape[0], size=(n_boot, msum.shape[0]))
    reps = _ratio_stat(
        msum[idx].sum(axis=1),
        mcnt[idx].sum(axis=1),
        asum[idx].sum(axis=1),
        acnt[idx].sum(axis=1),
        stat,
    )
    logger.debug(
        "day_block_bootstrap stat=%s days=%d n=%d n_boot=%d",
        stat, msum.shape[0], day_arr.size, n_boot,
    )
    return _summarize(point, reps, stat)


def bh_fdr(pvals: Sequence[float], q: float = 0.05) -> np.ndarray:
    """Benjamini–Hochberg step-up FDR — 입력 순서 정렬 기각(생존) bool 마스크.

    m개 p값을 오름차순 정렬해 p(k) <= (k/m)*q 를 만족하는 최대 k를 찾고
    정렬 기준 최소 k개를 기각(True)한다. 만족하는 k가 없으면 전부 False.
    p값은 [0,1] 유한값이어야 하며 아니면 ValueError.
    """
    p = np.asarray(pvals, dtype=np.float64)
    if p.ndim != 1:
        raise ValueError("pvals는 1차원 시퀀스여야 한다")
    m = p.size
    if m == 0:
        return np.zeros(0, dtype=bool)
    if np.any(~np.isfinite(p)) or np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("p값은 [0,1] 범위의 유한값이어야 한다")
    order = np.argsort(p, kind="stable")
    passed = p[order] <= (np.arange(1, m + 1) / m) * q
    if not passed.any():
        return np.zeros(m, dtype=bool)
    k = int(np.nonzero(passed)[0].max())  # 마지막 통과 순위(0-based)
    reject = np.zeros(m, dtype=bool)
    reject[order[: k + 1]] = True
    return reject
