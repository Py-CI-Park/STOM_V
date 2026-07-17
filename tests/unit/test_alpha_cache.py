"""alpha_lab.dataset.cache 단위 테스트 — npz 샤드 캐시 (알파 랩 F3).

검증(계약):
- to_arrays: schema npz 계약 dtype(features float32 (n,25), L1_*/L2 int8,
  t0 int64, code '<U6', date int32), ALL_FEATURES 컬럼 순서, float32 다운캐스트,
  라벨 키 자동 식별(비기본 지평 포함), 키 불일치/6자 초과 code 거부,
  빈 입력 스키마 보존(라벨은 기본 LABEL_COLUMNS).
- write_shard/read_shard: '{date}.npz' 경로·디렉토리 자동 생성, 키 정렬 순서
  기록, 무손실 왕복. 결정성은 배열·dtype 동일성 기준
  (zip 바이트 비교 금지 — 아카이브 타임스탬프 비결정).
- load_shards: dates 순서 concatenate 병합, 빈 dates → {}, 누락 파일 →
  FileNotFoundError, 샤드 간 키 불일치 → ValueError.
"""
from __future__ import annotations

import numpy as np
import pytest

from alpha_lab.dataset.cache import load_shards, read_shard, to_arrays, write_shard
from alpha_lab.dataset.schema import ALL_FEATURES, LABEL_COLUMNS

META_KEYS = ("date", "code", "t0")
DEFAULT_KEYS = {"features", *META_KEYS, *LABEL_COLUMNS}


def _make_sample(
    *,
    date: int = 20240103,
    code: str = "000100",
    t0: int = 20240103090501,
    base: float = 1.0,
    horizons=(60, 180, 300),
) -> dict:
    """stream_samples 방출 dict 미러 — 삽입 순서(meta→25피처→L1_*→L2) 동일."""
    sample = {"date": date, "code": code, "t0": t0}
    for i, name in enumerate(ALL_FEATURES):
        sample[name] = base + 0.5 * i
    for j, h in enumerate(horizons):
        sample[f"L1_{h}"] = (int(base) + j) % 2
    sample["L2"] = (-1, 0, 1)[int(base) % 3]
    return sample


def _make_samples(n: int, **kwargs) -> list:
    return [
        _make_sample(base=float(k), t0=20240103090501 + 5 * k, **kwargs)
        for k in range(n)
    ]


# ---------------------------------------------------------------- to_arrays


def test_to_arrays_dtypes_and_shapes():
    arrays = to_arrays(_make_samples(3))
    assert set(arrays) == DEFAULT_KEYS
    assert arrays["features"].shape == (3, len(ALL_FEATURES))
    assert arrays["features"].dtype == np.float32
    assert arrays["date"].dtype == np.int32
    assert arrays["t0"].dtype == np.int64
    assert arrays["code"].dtype == np.dtype("<U6")
    for name in LABEL_COLUMNS:
        assert arrays[name].dtype == np.int8
        assert arrays[name].shape == (3,)


def test_to_arrays_feature_order_follows_all_features():
    sample = _make_sample()
    for i, name in enumerate(ALL_FEATURES):
        sample[name] = float(i)  # 피처 i → 값 i (순서 판별용)
    arrays = to_arrays([sample])
    assert np.array_equal(
        arrays["features"][0], np.arange(len(ALL_FEATURES), dtype=np.float32)
    )


def test_to_arrays_float32_downcast_exact():
    sample = _make_sample()
    sample[ALL_FEATURES[0]] = 0.1  # float32로 정확 표현 불가한 값
    arrays = to_arrays([sample])
    stored = arrays["features"][0, 0]
    assert stored == np.float32(0.1)
    assert float(stored) != 0.1  # float64 원본과는 다르다(다운캐스트 증거)


def test_to_arrays_meta_and_label_values():
    samples = [
        _make_sample(date=20240103, code="000100", t0=20240103090501, base=0.0),
        _make_sample(date=20240104, code="123456", t0=20240104091001, base=2.0),
    ]
    arrays = to_arrays(samples)
    assert arrays["date"].tolist() == [20240103, 20240104]
    assert arrays["code"].tolist() == ["000100", "123456"]
    assert arrays["t0"].tolist() == [20240103090501, 20240104091001]
    for name in LABEL_COLUMNS:
        assert arrays[name].tolist() == [samples[0][name], samples[1][name]]


def test_to_arrays_custom_horizon_label_keys():
    arrays = to_arrays(_make_samples(2, horizons=(30,)))
    assert set(arrays) == {"features", *META_KEYS, "L1_30", "L2"}
    assert arrays["L1_30"].dtype == np.int8


def test_to_arrays_empty_preserves_schema():
    arrays = to_arrays([])
    assert set(arrays) == DEFAULT_KEYS
    assert arrays["features"].shape == (0, len(ALL_FEATURES))
    assert arrays["features"].dtype == np.float32
    assert arrays["date"].dtype == np.int32
    assert arrays["t0"].dtype == np.int64
    assert arrays["code"].dtype == np.dtype("<U6")
    for name in LABEL_COLUMNS:
        assert arrays[name].shape == (0,)
        assert arrays[name].dtype == np.int8


def test_to_arrays_accepts_generator_input():
    arrays = to_arrays(iter(_make_samples(4)))
    assert arrays["features"].shape[0] == 4


def test_to_arrays_inconsistent_keys_raises():
    good = _make_sample(base=0.0)
    bad = _make_sample(base=1.0)
    del bad["L2"]
    with pytest.raises(ValueError):
        to_arrays([good, bad])


def test_to_arrays_code_longer_than_6_raises():
    sample = _make_sample()
    sample["code"] = "1234567"  # '<U6' 무언 절단은 데이터 파손 — 거부해야 한다
    with pytest.raises(ValueError):
        to_arrays([sample])


# ------------------------------------------------- write_shard / read_shard


def test_write_read_roundtrip(tmp_path):
    arrays = to_arrays(_make_samples(4))
    cache_dir = tmp_path / "shards"  # 미존재 디렉토리 → 자동 생성 확인
    path = write_shard(cache_dir, "20240103", arrays)
    assert path.name == "20240103.npz"
    assert path.parent == cache_dir
    assert path.exists()
    loaded = read_shard(path)
    assert set(loaded) == set(arrays)
    for key, arr in arrays.items():
        assert loaded[key].dtype == arr.dtype
        assert np.array_equal(loaded[key], arr)


def test_write_shard_sorted_key_order(tmp_path):
    path = write_shard(tmp_path, "20240103", to_arrays(_make_samples(2)))
    loaded = read_shard(path)
    assert list(loaded) == sorted(loaded)  # 기록 키 순서 = 정렬 순서(봉인)


def test_write_shard_deterministic_arrays(tmp_path):
    """결정성은 왕복 배열·dtype 동일성 기준(zip 바이트 비교 금지)."""
    arrays = to_arrays(_make_samples(3))
    loaded_a = read_shard(write_shard(tmp_path / "a", "20240103", arrays))
    loaded_b = read_shard(write_shard(tmp_path / "b", "20240103", arrays))
    assert set(loaded_a) == set(loaded_b)
    for key in loaded_a:
        assert loaded_a[key].dtype == loaded_b[key].dtype
        assert np.array_equal(loaded_a[key], loaded_b[key])


def test_empty_arrays_roundtrip(tmp_path):
    arrays = to_arrays([])
    loaded = read_shard(write_shard(tmp_path, "20240105", arrays))
    assert loaded["features"].shape == (0, len(ALL_FEATURES))
    for key, arr in arrays.items():
        assert loaded[key].dtype == arr.dtype
        assert loaded[key].shape == arr.shape


# ---------------------------------------------------------------- load_shards


def test_load_shards_merges_in_date_order(tmp_path):
    write_shard(tmp_path, "20240103", to_arrays(_make_samples(2, date=20240103)))
    write_shard(tmp_path, "20240104", to_arrays(_make_samples(3, date=20240104)))
    merged = load_shards(tmp_path, ["20240103", "20240104"])
    assert set(merged) == DEFAULT_KEYS
    assert merged["features"].shape == (5, len(ALL_FEATURES))
    assert merged["features"].dtype == np.float32
    assert merged["date"].tolist() == [20240103] * 2 + [20240104] * 3
    assert merged["code"].dtype == np.dtype("<U6")
    assert merged["t0"].dtype == np.int64
    for name in LABEL_COLUMNS:
        assert merged[name].dtype == np.int8
        assert merged[name].shape == (5,)


def test_load_shards_single_date_equals_read_shard(tmp_path):
    arrays = to_arrays(_make_samples(2))
    path = write_shard(tmp_path, "20240103", arrays)
    merged = load_shards(tmp_path, ["20240103"])
    single = read_shard(path)
    assert set(merged) == set(single)
    for key in merged:
        assert np.array_equal(merged[key], single[key])
        assert merged[key].dtype == single[key].dtype


def test_load_shards_empty_dates_returns_empty_dict(tmp_path):
    assert load_shards(tmp_path, []) == {}


def test_load_shards_with_empty_shard_concatenates(tmp_path):
    write_shard(tmp_path, "20240103", to_arrays([]))
    write_shard(tmp_path, "20240104", to_arrays(_make_samples(2, date=20240104)))
    merged = load_shards(tmp_path, ["20240103", "20240104"])
    assert merged["features"].shape == (2, len(ALL_FEATURES))
    assert merged["date"].tolist() == [20240104, 20240104]


def test_load_shards_missing_file_raises(tmp_path):
    write_shard(tmp_path, "20240103", to_arrays(_make_samples(1)))
    with pytest.raises(FileNotFoundError):
        load_shards(tmp_path, ["20240103", "20240199"])


def test_load_shards_mismatched_keys_raises(tmp_path):
    write_shard(tmp_path, "20240103", to_arrays(_make_samples(1)))
    write_shard(tmp_path, "20240104", to_arrays(_make_samples(1, horizons=(30,))))
    with pytest.raises(ValueError):
        load_shards(tmp_path, ["20240103", "20240104"])
