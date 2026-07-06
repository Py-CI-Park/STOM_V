"""alpha_lab.mining.transition 단위 테스트 — 전이 샘플러 (v3 P1).

검증(계약):
- FALSE→TRUE 전이(onset)만 추출: 상태 지속 구간은 1회 — 그리드(상태 참)
  카운트와 전이 카운트가 실제로 다름을 확인(RC-2 처방의 근거 측정).
- 종목-일 시계열 경계 이월 금지: 앞 시리즈 끝이 TRUE여도 다음 시리즈 첫 행이
  TRUE면 새 onset. 비연속(흩어진) series_ids는 ValueError(정렬 요구).
- 입력 두 형태 지원: rows(dict 시퀀스)+절 목록, X(ndarray)+리프 dict
  (alpha_lab.mining.stats.rule_mask 재사용 — 마스크 재구성 중복 구현 금지).
- measure_transition_ev: 심은 양EV 포켓 회수(양성 대조 — ci_low>0, p=0),
  일평균 전이율 산식(전이수/전체 고유 일수)과 봉인 예산 [5,60] 판정,
  stats_common.day_block_bootstrap(stat='mean') 직접 호출과 수치 동치.
"""
from __future__ import annotations

import numpy as np
import pytest

from alpha_lab.mining.stats import rule_mask
from alpha_lab.mining.transition import (
    TRANSITION_RATE_BUDGET,
    extract_transitions,
    measure_transition_ev,
    series_ids_from,
    state_mask,
    transition_mask,
)
from alpha_lab.stats_common import day_block_bootstrap

# ---------------------------------------------------------------- 합성 데이터

N_DAYS = 30
CODES = ("001470", "900250")
ROWS_PER_SERIES = 100
RUN_LEN = 5      # 시리즈 내 TRUE 연속 구간 길이
RUN_PERIOD = 20  # 구간 주기 → 시리즈당 onset 5회, 상태 TRUE 25행


def _planted_pocket():
    """전이≠그리드가 명확한 결정적 합성: (일×종목) 시리즈마다 TRUE 런 5개.

    x0: 상태 TRUE 행에서 1.0, 아니면 0.0 → 규칙 'x0 > 0.5'.
    y: 상태 TRUE 행 +1.0, 아니면 -1.0 (onset 부분집합 EV = +1.0 결정적).
    반환: X(float32 2열), y, day_ids, series_ids, 기대 전이수.
    """
    n_series = N_DAYS * len(CODES)
    n = n_series * ROWS_PER_SERIES
    offsets = np.arange(ROWS_PER_SERIES)
    state_one = (offsets % RUN_PERIOD) < RUN_LEN
    state = np.tile(state_one, n_series)
    x0 = state.astype(np.float64)
    X = np.column_stack([x0, np.zeros(n)]).astype(np.float32)
    y = np.where(state, 1.0, -1.0)
    day_ids = np.repeat(np.arange(N_DAYS), len(CODES) * ROWS_PER_SERIES)
    dates = np.repeat(20230601 + np.arange(N_DAYS), len(CODES) * ROWS_PER_SERIES)
    codes = np.tile(np.repeat(np.asarray(CODES), ROWS_PER_SERIES), N_DAYS)
    series_ids = series_ids_from(dates, codes)
    onsets_per_series = int(np.count_nonzero(np.diff(state_one.astype(int)) == 1))
    onsets_per_series += int(state_one[0])
    return X, y, day_ids, series_ids, n_series * onsets_per_series


LEAF = {"rule": [("x0", ">", 0.5)], "rule_cols": [0]}


# ------------------------------------------------------------ transition_mask


def test_transition_mask_counts_onsets_only():
    """상태 지속 구간은 시작 1회만 onset — [F,T,T,T,F,T,T] → 인덱스 1, 5."""
    mask = np.array([False, True, True, True, False, True, True])
    onsets = transition_mask(mask)
    assert onsets.dtype == bool
    assert np.flatnonzero(onsets).tolist() == [1, 5]


def test_transition_mask_series_boundary_resets_state():
    """시리즈 경계에서 이전 상태 이월 금지 — 다음 시리즈 첫 TRUE는 새 onset."""
    mask = np.array([True, True, True, False, True])
    sids = np.array(["a", "a", "b", "b", "b"])
    assert np.flatnonzero(transition_mask(mask, sids)).tolist() == [0, 2, 4]
    # 같은 마스크를 단일 시리즈로 보면 인덱스 2는 지속 구간(onset 아님).
    assert np.flatnonzero(transition_mask(mask)).tolist() == [0, 4]


def test_transition_mask_rejects_non_contiguous_series():
    """같은 시리즈가 흩어져 있으면(정렬 안 됨) ValueError."""
    mask = np.array([True, True, True])
    with pytest.raises(ValueError):
        transition_mask(mask, np.array(["a", "b", "a"]))


def test_transition_mask_empty_and_shape_validation():
    assert transition_mask(np.zeros(0, dtype=bool)).size == 0
    with pytest.raises(ValueError):
        transition_mask(np.zeros((2, 2), dtype=bool))
    with pytest.raises(ValueError):
        transition_mask(np.array([True, False]), np.array(["a"]))


# ---------------------------------------------------------------- state_mask


def test_state_mask_rows_clause_list():
    """rows(dict)+절 목록 — 이름으로 평가, <=/> 두 연산자."""
    rows = [{"체결강도": v, "등락율": 1.0} for v in (100.0, 200.0, 210.0, 90.0, 180.0)]
    mask = state_mask(rows, [("체결강도", ">", 150.0)])
    assert mask.tolist() == [False, True, True, False, True]
    both = state_mask(rows, [("체결강도", ">", 150.0), ("등락율", "<=", 1.0)])
    assert both.tolist() == [False, True, True, False, True]


def test_state_mask_rows_missing_feature_or_bad_op_rejected():
    rows = [{"체결강도": 1.0}]
    with pytest.raises(ValueError):
        state_mask(rows, [("없는피처", ">", 0.0)])
    with pytest.raises(ValueError):
        state_mask(rows, [("체결강도", ">=", 0.0)])


def test_state_mask_ndarray_leaf_matches_rule_mask():
    """ndarray+리프 dict 경로는 rule_mask 재사용 — 결과 동치."""
    rng = np.random.default_rng(3)
    X = rng.uniform(-1.0, 1.0, size=(50, 3)).astype(np.float32)
    leaf = {"rule": [("f0", ">", 0.2), ("f2", "<=", 0.5)], "rule_cols": [0, 2]}
    assert np.array_equal(state_mask(X, leaf), rule_mask(X, leaf))


def test_state_mask_ndarray_int_clauses_and_rejects_names():
    X = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    mask = state_mask(X, [(0, ">", 0.5), (1, "<=", 0.5)])
    assert mask.tolist() == [False, True, False]
    with pytest.raises(ValueError):
        state_mask(X, [("이름절", ">", 0.5)])  # ndarray에는 열 인덱스 필요


# ------------------------------------------------------- extract_transitions


def test_extract_transitions_rows_and_ndarray_agree():
    """rows 경로와 ndarray+리프 경로가 같은 onset 인덱스를 낸다."""
    X, _, _, series_ids, expected = _planted_pocket()
    idx_nd = extract_transitions(X, LEAF, series_ids=series_ids)
    rows = [{"x0": float(v)} for v in X[:, 0]]
    idx_rows = extract_transitions(
        rows, [("x0", ">", 0.5)], series_ids=series_ids
    )
    assert np.array_equal(idx_nd, idx_rows)
    assert idx_nd.size == expected


def test_extract_transitions_fewer_than_grid_state_count():
    """전이 카운트 < 그리드(상태 TRUE) 카운트 — RC-2 괴리의 직접 측정."""
    X, _, _, series_ids, expected = _planted_pocket()
    state = state_mask(X, LEAF)
    onsets = extract_transitions(X, LEAF, series_ids=series_ids)
    assert onsets.size == expected
    assert int(state.sum()) == expected * RUN_LEN  # 지속 발화 5배
    assert onsets.size < int(state.sum())


# ----------------------------------------------------- measure_transition_ev


def test_measure_transition_ev_positive_control():
    """양성 대조: 심은 양EV 포켓을 전이 기준으로 회수 — ci_low>0, 예산 내."""
    X, y, day_ids, series_ids, expected = _planted_pocket()
    result = measure_transition_ev(
        X, LEAF, y, day_ids, series_ids=series_ids, n_boot=400, seed=20260707
    )
    assert result["n_transitions"] == expected
    assert result["n_state_true"] == expected * RUN_LEN
    assert result["n_days"] == N_DAYS
    # 일평균 전이율 = 전이수/고유 일수 = 2종목×5런 = 10.0 → 봉인 예산 [5,60] 내.
    assert result["transitions_per_day"] == pytest.approx(10.0)
    assert result["rate_budget"] == list(TRANSITION_RATE_BUDGET)
    assert result["rate_in_budget"] is True
    assert result["ev"] == pytest.approx(1.0)
    assert result["ci_low"] > 0.0
    assert result["p"] == 0.0


def test_measure_transition_ev_matches_direct_bootstrap():
    """ev/ci/p는 동일 onset 마스크의 day_block_bootstrap 직접 호출과 동치."""
    X, _, day_ids, series_ids, _ = _planted_pocket()
    rng = np.random.default_rng(9)
    y = rng.normal(0.1, 1.0, X.shape[0])
    result = measure_transition_ev(
        X, LEAF, y, day_ids, series_ids=series_ids, n_boot=300, seed=123
    )
    onset = transition_mask(state_mask(X, LEAF), series_ids)
    direct = day_block_bootstrap(
        day_ids, y, onset, n_boot=300, seed=123, stat="mean"
    )
    assert result["ev"] == direct["point"]
    assert result["ci_low"] == direct["ci_low"]
    assert result["ci_high"] == direct["ci_high"]
    assert result["p"] == direct["p_one_sided"]


def test_measure_transition_ev_rate_budget_out():
    """일평균 전이율이 예산 밖(1/일 < 5)이면 rate_in_budget=False."""
    n_days, per_day = 10, 50
    n = n_days * per_day
    day_ids = np.repeat(np.arange(n_days), per_day)
    x0 = np.zeros(n)
    x0[np.arange(n_days) * per_day] = 1.0  # 일 1회 onset
    X = x0.reshape(-1, 1).astype(np.float32)
    y = np.ones(n)
    result = measure_transition_ev(
        X, {"rule": [("x0", ">", 0.5)], "rule_cols": [0]}, y, day_ids,
        n_boot=100, seed=1,
    )
    assert result["n_transitions"] == n_days
    assert result["transitions_per_day"] == pytest.approx(1.0)
    assert result["rate_in_budget"] is False


def test_measure_transition_ev_validates_lengths():
    X, y, day_ids, series_ids, _ = _planted_pocket()
    with pytest.raises(ValueError):
        measure_transition_ev(
            X, LEAF, y[:-1], day_ids, series_ids=series_ids, n_boot=10, seed=1
        )
    with pytest.raises(ValueError):
        measure_transition_ev(
            X, LEAF, y, day_ids[:-1], series_ids=series_ids, n_boot=10, seed=1
        )


def test_series_ids_from_pairs_date_and_code():
    sids = series_ids_from([20230601, 20230601, 20230602], ["000001", "000002", "000001"])
    assert sids.tolist() == ["20230601:000001", "20230601:000002", "20230602:000001"]
