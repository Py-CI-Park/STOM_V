"""캐시 v3 증축 단위 테스트 — features 파생 컬럼 저장 + CLI --derived 배선.

검증(계약):
- to_arrays(extra_features=...): features (n, 25+k) float32(ALL_FEATURES 뒤에
  extra 순서대로), feature_names 메타 키 저장, 라벨 자동 식별에서 extra 제외,
  ALL_FEATURES/META 충돌·중복 extra는 ValueError.
- 하위호환(v1/v2 불변): extra_features 미지정 호출은 기존과 동일 —
  features (n,25), feature_names 키 없음.
- 왕복: write_shard→load_shards에서 feature_names는 concat 아닌 단일 사본,
  샤드 간 feature_names 불일치는 ValueError. v1형(키 없음) 샤드는 기존 병합.
- feature_names_of: 키 부재 시 ALL_FEATURES 기본, 열수 불일치 ValueError.
- CLI(alpha_dataset_v2): --derived/--annex-dir 인자 수용(기본 v3 run dir),
  _annex_passed_derived가 annex 통과 목록을 엔진 18항 순서로 결정적 반환,
  _derived_by_index가 공식 창(90000~93000) 필터 + rowid(삽입) 순 +
  compute_derived_tick(NULL→NaN→0.0 엔진 의미론)과 일치.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_lab.dataset.cache import (
    FEATURE_NAMES_KEY,
    feature_names_of,
    load_shards,
    to_arrays,
    write_shard,
)
from alpha_lab.dataset.derived import (
    AVG_WINDOW_FROZEN,
    DERIVED_TICK_FEATURES,
    SOURCE_COLUMNS,
    compute_derived_tick,
)
from alpha_lab.dataset.schema import ALL_FEATURES
from cli.alpha_dataset_v2 import (
    _annex_passed_derived,
    _derived_by_index,
    build_parser,
)

EXTRA = ["체결강도평균", "등락율각도"]
LABEL_DTYPES = {"L3_net": np.float32, "L3_pos": np.int8}


def _sample(i: int, date: int = 20230601, extra_names=EXTRA) -> dict:
    out = {"date": date, "code": "001470", "t0": date * 1_000_000 + 90001 + i}
    for name in ALL_FEATURES:
        out[name] = float(i)
    for k, name in enumerate(extra_names):
        out[name] = float(100 + 10 * k + i)
    out["L3_net"] = 0.5 * i
    out["L3_pos"] = 1
    return out


# ------------------------------------------------------------------ to_arrays


def test_to_arrays_extra_features_shapes_names_and_labels():
    rows = [_sample(i) for i in range(3)]
    arrays = to_arrays(rows, label_dtypes=LABEL_DTYPES, extra_features=EXTRA)
    assert arrays["features"].shape == (3, len(ALL_FEATURES) + len(EXTRA))
    assert arrays["features"].dtype == np.float32
    names = feature_names_of(arrays)
    assert names == list(ALL_FEATURES) + EXTRA
    # extra 값이 ALL_FEATURES 뒤 열에 순서대로 들어간다.
    col0 = len(ALL_FEATURES)
    assert arrays["features"][:, col0].tolist() == [100.0, 101.0, 102.0]
    assert arrays["features"][:, col0 + 1].tolist() == [110.0, 111.0, 112.0]
    # 라벨 자동 식별에서 extra 제외 — L3_*만 라벨.
    assert "체결강도평균" not in arrays and "등락율각도" not in arrays
    assert arrays["L3_net"].dtype == np.float32
    assert arrays["L3_pos"].dtype == np.int8


def test_to_arrays_without_extra_is_backward_compatible():
    """extra_features 미지정 — v1/v2 계약 그대로(파생 키는 라벨로 분류됨)."""
    rows = [_sample(i, extra_names=[]) for i in range(2)]
    arrays = to_arrays(rows, label_dtypes=LABEL_DTYPES)
    assert arrays["features"].shape == (2, len(ALL_FEATURES))
    assert FEATURE_NAMES_KEY not in arrays
    assert feature_names_of(arrays) == list(ALL_FEATURES)


def test_to_arrays_extra_collisions_rejected():
    rows = [_sample(0)]
    with pytest.raises(ValueError):
        to_arrays(rows, extra_features=["등락율"])  # ALL_FEATURES 충돌
    with pytest.raises(ValueError):
        to_arrays(rows, extra_features=["date"])  # META 충돌
    with pytest.raises(ValueError):
        to_arrays(rows, extra_features=["체결강도평균", "체결강도평균"])  # 중복


def test_to_arrays_empty_with_extra_keeps_schema():
    arrays = to_arrays([], extra_features=EXTRA)
    assert arrays["features"].shape == (0, len(ALL_FEATURES) + len(EXTRA))
    assert feature_names_of(arrays) == list(ALL_FEATURES) + EXTRA


# ------------------------------------------------------------- 샤드 왕복 병합


def test_load_shards_keeps_single_feature_names_copy(tmp_path):
    a = to_arrays([_sample(i, date=20230601) for i in range(2)],
                  label_dtypes=LABEL_DTYPES, extra_features=EXTRA)
    b = to_arrays([_sample(i, date=20230602) for i in range(3)],
                  label_dtypes=LABEL_DTYPES, extra_features=EXTRA)
    write_shard(tmp_path, "20230601", a)
    write_shard(tmp_path, "20230602", b)
    merged = load_shards(tmp_path, ["20230601", "20230602"])
    assert merged["features"].shape == (5, len(ALL_FEATURES) + len(EXTRA))
    assert feature_names_of(merged) == list(ALL_FEATURES) + EXTRA
    assert merged[FEATURE_NAMES_KEY].shape[0] == len(ALL_FEATURES) + len(EXTRA)


def test_load_shards_feature_names_mismatch_raises(tmp_path):
    a = to_arrays([_sample(0)], label_dtypes=LABEL_DTYPES, extra_features=EXTRA)
    rows_b = [_sample(0, date=20230602, extra_names=["체결강도평균"])]
    b = to_arrays(rows_b, label_dtypes=LABEL_DTYPES,
                  extra_features=["체결강도평균"])
    write_shard(tmp_path, "20230601", a)
    write_shard(tmp_path, "20230602", b)
    with pytest.raises(ValueError):
        load_shards(tmp_path, ["20230601", "20230602"])


def test_feature_names_of_column_count_mismatch_raises():
    arrays = to_arrays([_sample(0)], label_dtypes=LABEL_DTYPES,
                       extra_features=EXTRA)
    broken = {**arrays, "features": arrays["features"][:, :-1]}
    with pytest.raises(ValueError):
        feature_names_of(broken)


# ------------------------------------------------------------------ CLI 배선


def test_build_parser_accepts_derived_flags():
    parser = build_parser()
    args = parser.parse_args(
        ["build", "--dates", "20230601", "--derived", "--annex-dir", "X"]
    )
    assert args.derived is True and args.annex_dir == "X"
    default = parser.parse_args(["build", "--mvp"])
    assert default.derived is False
    assert "alpha_lab_v3_20260706" in default.annex_dir


def test_annex_passed_derived_engine_order_and_unknown_ignored():
    payload = {
        "passed_features": [
            {"name": "등락율각도"},
            {"name": "이동평균60"},
            {"name": "미지의피처"},
            {"name": "체결강도평균"},
        ]
    }
    names = _annex_passed_derived(payload)
    assert names == ["이동평균60", "체결강도평균", "등락율각도"]  # 엔진 18항 순서
    assert all(n in DERIVED_TICK_FEATURES for n in names)
    assert _annex_passed_derived({"passed_features": []}) == []


def _rows_fixture(n: int = 40, date: int = 20230601):
    """공식 창 밖 1행 + 창 내 n행, NULL 1개 포함 rows dict(삽입=시간 순)."""
    rows = {}
    pre = date * 1_000_000 + 85959  # 창 밖(90000 이전) — 제외 대상
    rows[pre] = {name: 1.0 for name in SOURCE_COLUMNS}
    for i in range(n):
        idx = date * 1_000_000 + 90000 + i
        row = {name: float(i + 1 + k) for k, name in enumerate(SOURCE_COLUMNS)}
        row["관심종목"] = None  # 파생 원천 외 컬럼(무시되어야 함)
        if i == 3:
            row["체결강도"] = None  # NULL → NaN → 엔진 nan_to_num 의미론
        rows[idx] = row
    return rows


def test_derived_by_index_matches_compute_derived_tick():
    rows = _rows_fixture()
    names = ["체결강도평균", "등락율각도", "누적초당매수수량"]
    got = _derived_by_index(rows, names)
    window_items = [
        (idx, row) for idx, row in rows.items()
        if 90000 <= idx % 1_000_000 <= 93000
    ]
    assert len(got) == len(window_items)  # 창 밖 행 제외
    frame = pd.DataFrame(
        {
            name: pd.to_numeric(
                pd.Series([row.get(name) for _, row in window_items],
                          dtype="object"),
                errors="coerce",
            )
            for name in SOURCE_COLUMNS
        }
    )
    expected = compute_derived_tick(frame, AVG_WINDOW_FROZEN)
    for pos, (idx, _) in enumerate(window_items):
        for name in names:
            assert got[idx][name] == expected[name].iloc[pos]
    # 워밍업(창 시작 29행)과 NULL 전파 구간은 엔진 의미론상 0.0.
    first_idx = window_items[0][0]
    assert got[first_idx]["체결강도평균"] == 0.0


def test_derived_by_index_empty_window():
    rows = {20230601085959: {name: 1.0 for name in SOURCE_COLUMNS}}
    assert _derived_by_index(rows, ["체결강도평균"]) == {}
