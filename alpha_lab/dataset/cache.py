"""npz 샤드 캐시 — stream_samples 표본 dict → 일 단위 컬럼 배열 직렬화.

npz 저장 계약(schema.py 모듈 docstring과 동일 — 봉인):
    features : float32 (n, 25) — ALL_FEATURES 순서 그대로
    L1_* / L2 : int8 (L1은 {0,1}, L2는 {-1,0,1})
    t0   : int64  (int YYYYMMDDHHMMSS)
    code : '<U6'  (6자리 종목코드 문자열)
    date : int32  (int YYYYMMDD)

샤드 파일명은 '{date}.npz'이고 np.savez_compressed로 키를 정렬 순서로
기록한다. 외부 의존(pyarrow 등) 없이 npz만 사용한다(연구 규율).
결정성 비교는 왕복 배열·dtype 동일성 기준이다(zip 컨테이너 바이트는
아카이브 타임스탬프 때문에 비결정 — 비교 기준으로 쓰지 않는다).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Union

import numpy as np

from alpha_lab.dataset.schema import ALL_FEATURES, LABEL_COLUMNS, META_COLUMNS

__all__ = ["load_shards", "read_shard", "to_arrays", "write_shard"]

logger = logging.getLogger(__name__)

_CODE_DTYPE = np.dtype("<U6")
_FEATURE_SET = frozenset(ALL_FEATURES)
_META_SET = frozenset(META_COLUMNS)

PathLike = Union[str, Path]


def _empty_arrays() -> Dict[str, np.ndarray]:
    """표본 0건일 때 스키마 보존 빈 배열(라벨 키는 기본 LABEL_COLUMNS)."""
    arrays: Dict[str, np.ndarray] = {
        "features": np.empty((0, len(ALL_FEATURES)), dtype=np.float32),
        "date": np.empty(0, dtype=np.int32),
        "code": np.empty(0, dtype=_CODE_DTYPE),
        "t0": np.empty(0, dtype=np.int64),
    }
    for name in LABEL_COLUMNS:
        arrays[name] = np.empty(0, dtype=np.int8)
    return arrays


def _code_array(codes: List[object]) -> np.ndarray:
    """code 목록 → '<U6'. 6자 초과는 무언 절단(데이터 파손) 대신 거부."""
    arr = np.asarray(codes)
    if arr.dtype.kind != "U" or arr.dtype.itemsize > _CODE_DTYPE.itemsize:
        raise ValueError(f"code는 6자 이하 문자열이어야 한다: dtype={arr.dtype}")
    return arr.astype(_CODE_DTYPE)


def to_arrays(samples: Iterable[Mapping[str, object]]) -> Dict[str, np.ndarray]:
    """표본 dict 스트림 → 컬럼 배열 dict (npz 저장 계약 dtype 강제).

    라벨 키는 첫 표본에서 메타·피처를 제외한 나머지(삽입 순서 유지)로
    식별한다 — stream_samples 기본 지평이면 schema.LABEL_COLUMNS와 일치하고,
    비기본 지평(L1_30 등)도 그대로 통과한다. 모든 표본은 첫 표본과 동일한
    키 집합이어야 하며 다르면 ValueError. 빈 입력은 스키마 보존 빈 배열.
    """
    rows = list(samples)
    if not rows:
        return _empty_arrays()
    first_keys = rows[0].keys()
    label_keys = [k for k in first_keys if k not in _META_SET and k not in _FEATURE_SET]
    features = np.empty((len(rows), len(ALL_FEATURES)), dtype=np.float32)
    for i, row in enumerate(rows):
        if row.keys() != first_keys:
            raise ValueError(f"표본 {i}의 키 집합이 첫 표본과 다르다")
        features[i, :] = [float(row[name]) for name in ALL_FEATURES]
    arrays: Dict[str, np.ndarray] = {
        "features": features,
        "date": np.asarray([row["date"] for row in rows], dtype=np.int32),
        "code": _code_array([row["code"] for row in rows]),
        "t0": np.asarray([row["t0"] for row in rows], dtype=np.int64),
    }
    for name in label_keys:
        arrays[name] = np.asarray([row[name] for row in rows], dtype=np.int8)
    return arrays


def write_shard(
    cache_dir: PathLike, date: str, arrays: Mapping[str, np.ndarray]
) -> Path:
    """arrays를 '{cache_dir}/{date}.npz'로 기록하고 경로를 반환한다.

    키는 정렬 순서로 기록(np.savez_compressed)하며 디렉토리는 자동 생성한다.
    """
    out_dir = Path(cache_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date}.npz"
    ordered = {key: np.asarray(arrays[key]) for key in sorted(arrays)}
    np.savez_compressed(path, **ordered)
    logger.debug("write_shard %s keys=%s", path, list(ordered))
    return path


def read_shard(path: PathLike) -> Dict[str, np.ndarray]:
    """npz 샤드 → {키: 배열} dict. 저장된 키 순서를 유지하고 메모리로 실체화."""
    with np.load(Path(path), allow_pickle=False) as npz:
        return {key: npz[key] for key in npz.files}


def load_shards(cache_dir: PathLike, dates: Sequence[str]) -> Dict[str, np.ndarray]:
    """여러 일자 샤드를 dates 순서로 읽어 키별 np.concatenate 병합.

    빈 dates → {}. 샤드 파일 누락 → FileNotFoundError,
    샤드 간 키 집합 불일치 → ValueError.
    """
    root = Path(cache_dir)
    shards: List[Dict[str, np.ndarray]] = []
    for date in dates:
        path = root / f"{date}.npz"
        if not path.exists():
            raise FileNotFoundError(f"샤드 없음: {path}")
        shards.append(read_shard(path))
    if not shards:
        return {}
    for i, shard in enumerate(shards[1:], start=1):
        if shard.keys() != shards[0].keys():
            raise ValueError(
                f"샤드 키 불일치: {dates[i]}({sorted(shard)}) vs "
                f"{dates[0]}({sorted(shards[0])})"
            )
    merged = {
        key: np.concatenate([shard[key] for shard in shards], axis=0)
        for key in shards[0]
    }
    logger.debug("load_shards %d개 샤드 병합 keys=%s", len(shards), list(merged))
    return merged
