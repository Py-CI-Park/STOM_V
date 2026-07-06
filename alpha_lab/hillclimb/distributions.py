"""힐클라임 뮤테이터용 피처 경험분포 로더 — v3 캐시 샤드(43컬럼) → 정렬 배열.

alpha_lab.dataset.cache.load_shards(캐시 v3 증축 — feature_names 메타 키)를
그대로 재사용해 60일 전량(678,451표본)에서 피처별 오름차순 1차원 배열을
만든다. mutator.shift_threshold/quantile_value는 이 배열이 오름차순임을
전제로 한다(계약 — 본 모듈이 유일한 생성 지점).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Sequence, Union

import numpy as np

from alpha_lab.dataset.cache import feature_names_of, load_shards

__all__ = ["load_feature_distributions"]

PathLike = Union[str, Path]


def load_feature_distributions(
    cache_dir: PathLike, dates: Sequence[str], feature_names: Sequence[str]
) -> Dict[str, np.ndarray]:
    """지정 피처들의 오름차순 정렬 경험분포 dict를 만든다.

    dates 순서와 무관하게 값 자체만 모으므로(정렬로 순서 소거) 병합 순서는
    결과에 영향을 주지 않는다 — 결정론은 "정렬된 배열의 값 집합"에 있다.
    feature_names 중 캐시 샤드에 없는 이름은 KeyError(정직 실패 — 조용한 스킵
    금지, 호출측이 화이트리스트 오타를 즉시 알아채도록).
    """
    arrays = load_shards(cache_dir, list(dates))
    names = feature_names_of(arrays)
    index = {name: i for i, name in enumerate(names)}
    features = np.asarray(arrays["features"])
    out: Dict[str, np.ndarray] = {}
    for name in feature_names:
        if name not in index:
            raise KeyError(f"캐시 샤드에 없는 피처: {name!r} (보유: {sorted(index)})")
        col = features[:, index[name]].astype(np.float64)
        out[name] = np.sort(col)
    return out
