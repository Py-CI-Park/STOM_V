"""결정트리 기반 규칙 채굴 — 리프 전수 추출 (P1 레인 A 모듈 4).

mine_rules는 sklearn DecisionTreeClassifier(random_state=seed+k)를 피처
서브셋별로 학습하고 '모든' 리프를 루트→리프 경로의
(피처명, '<=' | '>', 임계값) conjunction 규칙으로 반환한다. 양성 리프만
고르지 않는다 — 반환 리프 수 전체가 n_trials 원장에 정직 합산되어야
하기 때문(사전등록 규율). lift 산식은 alpha_lab.stats_common.lift 재사용.

리프 dict 계약(봉인 키 + 부속 키):
  rule[list[(name, op, thr)]], support[int], positives[int], lift[float],
  subset_id[int], leaf_id[int](트리 node id, 서브셋 내 유일),
  rule_cols[list[int]](rule과 평행한 X 전역 열 인덱스 — evaluate_leaves가
  피처명 재해석 없이 마스크를 재구성하는 데 사용).

트리 학습 목표는 (y == 1) 이진화 값이다 — L1(0/1)과 L2(-1/0/1) 라벨 모두
'양성(=1)' 리프 탐색으로 해석이 일치한다. 임계값은 원값 그대로 반환하며
소수 1자리 반올림 봉인은 번역(translate) 단계 소관이다.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from alpha_lab.stats_common import lift as _lift

__all__ = ["mine_rules"]

logger = logging.getLogger(__name__)

_NO_CHILD = -1  # sklearn tree_.children_* 의 리프 표식


def _validate_inputs(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
    subsets: List[List[int]],
    min_samples_leaf: int,
) -> None:
    """형상·서브셋·파라미터 검증 — 위반 시 ValueError."""
    if X.ndim != 2 or X.shape[0] == 0:
        raise ValueError(f"X는 비어있지 않은 2차원 배열이어야 한다: shape={X.shape}")
    if y.ndim != 1 or y.shape[0] != X.shape[0]:
        raise ValueError(f"y는 X 행수({X.shape[0]})와 같은 1차원 배열이어야 한다")
    if len(feature_names) != X.shape[1]:
        raise ValueError(
            f"feature_names 길이({len(feature_names)})가 X 열수({X.shape[1]})와 다르다"
        )
    if min_samples_leaf < 1:
        raise ValueError(f"min_samples_leaf는 1 이상이어야 한다: {min_samples_leaf}")
    for k, cols in enumerate(subsets):
        if len(cols) == 0:
            raise ValueError(f"feature_subsets[{k}]가 비어 있다")
        bad = [c for c in cols if not 0 <= int(c) < X.shape[1]]
        if bad:
            raise ValueError(f"feature_subsets[{k}] 열 인덱스 범위 밖: {bad}")


def _leaf_paths(tree) -> Dict[int, List[Tuple[int, str, float]]]:
    """리프 node_id → 루트→리프 경로 [(로컬 피처, op, 임계값)] — 좌→우 DFS."""
    paths: Dict[int, List[Tuple[int, str, float]]] = {}
    stack: List[Tuple[int, List[Tuple[int, str, float]]]] = [(0, [])]
    while stack:
        node, path = stack.pop()
        if tree.children_left[node] == _NO_CHILD:
            paths[node] = path
            continue
        feat = int(tree.feature[node])
        thr = float(tree.threshold[node])
        stack.append((int(tree.children_right[node]), path + [(feat, ">", thr)]))
        stack.append((int(tree.children_left[node]), path + [(feat, "<=", thr)]))
    return paths


def _leaf_counts(clf, X_sub: np.ndarray, pos: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """리프별 (support, positives) — clf.apply 기반이라 sklearn 버전 무관."""
    leaf_of = clf.apply(X_sub)
    n_nodes = clf.tree_.node_count
    support = np.bincount(leaf_of, minlength=n_nodes)
    positives = np.bincount(leaf_of, weights=pos, minlength=n_nodes)
    return support, positives


def _mine_subset(
    X: np.ndarray,
    pos: np.ndarray,
    cols: List[int],
    feature_names: Sequence[str],
    subset_id: int,
    *,
    max_depth: int,
    min_samples_leaf: int,
    random_state: int,
    base_rate: float,
) -> List[dict]:
    """서브셋 하나에 트리 1개 학습 → 리프 전수를 규칙 dict로 변환."""
    X_sub = X[:, cols]
    clf = DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=random_state,
    )
    clf.fit(X_sub, pos)
    support, positives = _leaf_counts(clf, X_sub, pos)
    leaves = []
    for leaf_id, path in _leaf_paths(clf.tree_).items():
        sup = int(support[leaf_id])
        posi = int(positives[leaf_id])
        leaves.append(
            {
                "rule": [
                    (str(feature_names[cols[f]]), op, thr) for f, op, thr in path
                ],
                "support": sup,
                "positives": posi,
                "lift": float(_lift(posi, sup, base_rate)),
                "subset_id": int(subset_id),
                "leaf_id": int(leaf_id),
                "rule_cols": [int(cols[f]) for f, _, _ in path],
            }
        )
    return leaves


def mine_rules(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: Sequence[str],
    *,
    max_depth: int = 4,
    min_samples_leaf: int = 2000,
    seed: int = 20260705,
    feature_subsets: List[List[int]] | None = None,
) -> List[dict]:
    """피처 서브셋별 결정트리에서 리프 전수를 규칙 후보로 채굴한다.

    feature_subsets가 None이면 전 피처 단일 서브셋 1개. 서브셋 k의 트리는
    random_state=seed+k 로 고정한다(재현성). 반환 리스트 순서는
    (서브셋 순서, 트리 좌→우 DFS)로 결정적이다.
    """
    X_arr = np.asarray(X, dtype=np.float32)
    y_arr = np.asarray(y)
    subsets = (
        [list(range(X_arr.shape[1]))]
        if feature_subsets is None
        else [[int(c) for c in cols] for cols in feature_subsets]
    )
    _validate_inputs(X_arr, y_arr, feature_names, subsets, min_samples_leaf)
    pos = (y_arr == 1).astype(np.float64)
    base_rate = float(pos.mean())
    leaves: List[dict] = []
    for k, cols in enumerate(subsets):
        subset_leaves = _mine_subset(
            X_arr,
            pos,
            cols,
            feature_names,
            k,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=seed + k,
            base_rate=base_rate,
        )
        leaves.extend(subset_leaves)
        logger.info(
            "mine_rules subset=%d cols=%d leaves=%d (n=%d, base_rate=%.5f)",
            k, len(cols), len(subset_leaves), X_arr.shape[0], base_rate,
        )
    return leaves
