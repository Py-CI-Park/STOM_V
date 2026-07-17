"""리프 통계 평가·채택 게이트 — stats_common 재사용 (P1 레인 A 모듈 4).

통계 원식은 alpha_lab.stats_common(day_block_bootstrap/bh_fdr/lift)만 쓴다
— 레인별 중복 구현 금지 규율.

evaluate_leaves: 리프 규칙로 표본 마스크를 재구성해 일 블록 부트스트랩
(stat='lift', 리프 i는 seed+i)으로 95% CI와 단측 p를 얻고, 전체 리프 p에
BH-FDR(q)를 적용해 생존 마스크를 만든다. 원본 리프 dict는 변경하지 않고
{ci_low, ci_high, p, fdr_survivor}를 부착한 새 dict 리스트를 반환한다.
adopt 단계용 내부 키도 함께 부착한다(직렬화 시 '_' 접두 키는 제외할 것):
  _idx[np.ndarray]      리프 마스크 표본 인덱스
  _pos_idx[np.ndarray]  리프 내 양성(y==1) 표본 인덱스
  _pos_all[np.ndarray]  전체 양성 표본 인덱스(전 리프 공유 참조)
  _n[int]               평가 표본수(연도 마스크 길이 검증용)

adopt: FDR 생존 ∧ lift>=lift_min ∧ support>=support_min ∧ 발견창 전 연도
각각 lift>per_year_lift_gt '동시' 충족 리프만 반환(설계서 봉인 기준).
채택 리프에는 {per_year_lift: {연도: lift}}를 부착한 새 dict를 담는다.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence

import numpy as np

from alpha_lab.stats_common import bh_fdr, day_block_bootstrap
from alpha_lab.stats_common import lift as _lift

__all__ = ["adopt", "evaluate_leaves", "rule_mask"]

logger = logging.getLogger(__name__)

_ADOPT_REQUIRED = ("fdr_survivor", "lift", "support", "_idx", "_pos_idx", "_pos_all", "_n")


def rule_mask(X: np.ndarray, leaf: dict) -> np.ndarray:
    """리프 rule×rule_cols conjunction을 X 표본 bool 마스크로 재구성.

    공개 API — evaluate_leaves 내부와 교차창 점검(alpha_crosscheck)이 같은
    구현을 공유한다(마스크 재구성 중복 구현 금지).
    """
    cols = leaf.get("rule_cols")
    if cols is None or len(cols) != len(leaf["rule"]):
        raise ValueError("리프에 rule_cols가 없거나 rule과 길이가 다르다 — mine_rules 산출물이 아니다")
    mask = np.ones(X.shape[0], dtype=bool)
    for col, (_, op, thr) in zip(cols, leaf["rule"]):
        if op not in ("<=", ">"):
            raise ValueError(f"지원하지 않는 연산자: {op!r}")
        vals = X[:, int(col)]
        mask &= (vals <= thr) if op == "<=" else (vals > thr)
    return mask


_rule_mask = rule_mask  # 기존 내부명 호환 별칭.


def _validate_eval_inputs(X: np.ndarray, y: np.ndarray, day_ids: np.ndarray) -> None:
    if X.ndim != 2:
        raise ValueError(f"X는 2차원 배열이어야 한다: shape={X.shape}")
    if not (X.shape[0] == y.shape[0] == day_ids.shape[0]):
        raise ValueError("X/y/day_ids 표본수가 서로 다르다")


def evaluate_leaves(
    leaves: Sequence[dict],
    X: np.ndarray,
    y: np.ndarray,
    day_ids: np.ndarray,
    *,
    n_boot: int,
    seed: int,
    q: float,
) -> List[dict]:
    """리프별 일 블록 부트스트랩 lift CI·p + BH-FDR 생존 부착(새 dict 반환)."""
    X_arr = np.asarray(X, dtype=np.float32)
    y_pos = (np.asarray(y) == 1).astype(np.float64)
    day_arr = np.asarray(day_ids)
    _validate_eval_inputs(X_arr, y_pos, day_arr)
    pos_all = np.flatnonzero(y_pos > 0.0)
    enriched: List[dict] = []
    for i, leaf in enumerate(leaves):
        mask = _rule_mask(X_arr, leaf)
        boot = day_block_bootstrap(
            day_arr, y_pos, mask, n_boot=n_boot, seed=seed + i, stat="lift"
        )
        enriched.append(
            {
                **leaf,
                "ci_low": boot["ci_low"],
                "ci_high": boot["ci_high"],
                "p": boot["p_one_sided"],
                "_idx": np.flatnonzero(mask),
                "_pos_idx": np.flatnonzero(mask & (y_pos > 0.0)),
                "_pos_all": pos_all,
                "_n": int(X_arr.shape[0]),
            }
        )
    survivors = (
        bh_fdr([leaf["p"] for leaf in enriched], q)
        if enriched
        else np.zeros(0, dtype=bool)
    )
    logger.info(
        "evaluate_leaves leaves=%d n=%d n_boot=%d q=%.3f fdr_survivors=%d",
        len(enriched), X_arr.shape[0], n_boot, q, int(survivors.sum()),
    )
    return [
        {**leaf, "fdr_survivor": bool(s)} for leaf, s in zip(enriched, survivors)
    ]


def _per_year_lifts(leaf: dict, per_year_masks: Dict[int, np.ndarray]) -> Dict[int, float]:
    """연도별 lift — 분자(리프 내 양성률)·분모(그 연도 전체 양성률) 모두 연도 한정."""
    out: Dict[int, float] = {}
    for year, year_mask in per_year_masks.items():
        ym = np.asarray(year_mask, dtype=bool)
        if ym.ndim != 1 or ym.shape[0] != leaf["_n"]:
            raise ValueError(
                f"연도 {year} 마스크 길이({ym.shape})가 평가 표본수({leaf['_n']})와 다르다"
            )
        support_y = float(ym[leaf["_idx"]].sum())
        positives_y = float(ym[leaf["_pos_idx"]].sum())
        n_y = float(ym.sum())
        base_y = float(ym[leaf["_pos_all"]].sum()) / n_y if n_y > 0 else 0.0
        out[year] = float(_lift(positives_y, support_y, base_y))
    return out


def adopt(
    leaves: Sequence[dict],
    *,
    lift_min: float = 1.5,
    support_min: int = 2000,
    per_year_masks: Dict[int, np.ndarray],
    per_year_lift_gt: float = 1.0,
) -> List[dict]:
    """봉인 채택 게이트 — FDR 생존 ∧ lift ∧ support ∧ 전 연도 lift 동시 충족.

    per_year_masks는 {연도: 표본 bool 마스크}(evaluate_leaves와 같은 표본축).
    연도 lift가 nan(그 연도 support 0 등)이면 비교가 False가 되어 보수적으로
    탈락한다. evaluate_leaves를 거치지 않은 리프는 ValueError.
    """
    if not per_year_masks:
        raise ValueError("per_year_masks는 최소 1개 연도가 필요하다")
    adopted: List[dict] = []
    for leaf in leaves:
        missing = [k for k in _ADOPT_REQUIRED if k not in leaf]
        if missing:
            raise ValueError(f"evaluate_leaves 미적용 리프(누락 키 {missing}) — 평가를 먼저 수행하라")
        if not leaf["fdr_survivor"]:
            continue
        if not (leaf["lift"] >= lift_min and leaf["support"] >= support_min):
            continue
        per_year = _per_year_lifts(leaf, per_year_masks)
        if all(v > per_year_lift_gt for v in per_year.values()):
            adopted.append({**leaf, "per_year_lift": per_year})
    logger.info(
        "adopt %d/%d (lift>=%.2f, support>=%d, 연도 %d개 lift>%.2f)",
        len(adopted), len(leaves), lift_min, support_min,
        len(per_year_masks), per_year_lift_gt,
    )
    return adopted
