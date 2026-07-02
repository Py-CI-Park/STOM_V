"""T5.2 포트폴리오 조립기 단위 테스트 — 합성 시계열 수기 검증.

검증 계약:
  1. 거래행(한국어 컬럼) → 일별 손익 파생(daily_pnl_from_trades) + 드롭 정직 공시
  2. 상관 캡 초과 쌍의 성과 열위 제외 + exclusions 기록(조용한 탈락 금지)
  3. 공통 거래일 교집합 < 20일 → correlation=None + 'insufficient_overlap'
  4. 시간밴드 상보성(중첩 0 → 1.0, 동일 밴드 → 0.0, 밴드 누락 → 정직 None)
  5. 결합 MDD/총손익 수기 검증(0 기준선 포함)
  6. measurement_frame=portfolio_multi_position 라벨 필수(결과/portfolio 양쪽)
  7. 벤치마크 비교 시 프레임 advisory 경고 전파 + 상대 지표 수기 검증
DB/엔진/런타임 접근 없음 — 순수 dict/DataFrame 합성 입력만 사용한다.
"""
from __future__ import annotations

import pandas as pd
import pytest

from ai_strategy_loop.fitness.measurement_frame import (
    FRAME_PORTFOLIO_MULTI_POSITION,
    MEASUREMENT_FRAME_KEY,
    annotate_frame,
)
from ai_strategy_loop.portfolio.assembler import (
    STATUS_INSUFFICIENT_OVERLAP,
    STATUS_OK,
    STATUS_ZERO_VARIANCE,
    combine_candidates,
    compare_to_benchmark,
    daily_pnl_from_trades,
    load_reference_strategies,
)


# ---------------------------------------------------------------------------
# 합성 데이터 헬퍼
# ---------------------------------------------------------------------------

def _days(n: int) -> list[str]:
    """2024-01 내 연속 n일(YYYYMMDD 문자열, n<=28)."""
    assert n <= 28
    return [f"202401{d:02d}" for d in range(1, n + 1)]


def _series(pattern: list[float], scale: float, offset: float) -> dict[str, float]:
    """pattern 의 아핀 변환 시계열 {YYYYMMDD: scale*p + offset}."""
    days = _days(len(pattern))
    return {day: scale * p + offset for day, p in zip(days, pattern)}


# p/q 는 24일 위에서 정확히 직교(피어슨 상관 0)인 부호 패턴.
_P = [1.0, -1.0] * 12
_Q = [1.0, 1.0, -1.0, -1.0] * 6


def _abc_candidates() -> list[dict]:
    """A~B 완전 상관(1.0), A~C/B~C 상관 0, B 가 성과 열위인 3후보."""
    return [
        {"name": "A", "daily_pnl": _series(_P, 100.0, 50.0),
         "meta": {"time_band": {"start": 90000, "end": 91000, "label": "b0900"},
                  "buy_sha256": "sha-A"}},
        {"name": "B", "daily_pnl": _series(_P, 90.0, 40.0),
         "meta": {"time_band": {"start": 90000, "end": 91000, "label": "b0900"}}},
        {"name": "C", "daily_pnl": _series(_Q, 100.0, 50.0),
         "meta": {"time_band": {"start": 91000, "end": 92000, "label": "b0910"}}},
    ]


# ---------------------------------------------------------------------------
# 1. 거래행 → 일별 손익 파생
# ---------------------------------------------------------------------------

def test_daily_pnl_from_trades_aggregates_by_buy_date():
    rows = [
        {"매수시간": 20240101090001, "수익금": 100.0},
        {"매수시간": 20240101092500, "수익금": -50.0},
        {"매수시간": 20240102091000, "수익금": 200.0},
    ]
    out = daily_pnl_from_trades(rows)
    assert out["daily_pnl"] == {"20240101": 50.0, "20240102": 200.0}
    assert out["n_trades"] == 3
    assert out["n_wins"] == 2
    assert out["dropped_rows"] == 0


def test_daily_pnl_from_trades_accepts_dataframe_and_reports_drops():
    df = pd.DataFrame([
        {"매수시간": 20240101090001, "수익금": 100.0},
        {"매수시간": None, "수익금": 999.0},          # 매수시간 결측 → 드롭
        {"매수시간": 20240102091000, "수익금": None},  # 수익금 결측 → 드롭
    ])
    out = daily_pnl_from_trades(df)
    assert out["daily_pnl"] == {"20240101": 100.0}
    assert out["n_trades"] == 1
    assert out["dropped_rows"] == 2


def test_daily_pnl_from_trades_all_unparseable_raises():
    with pytest.raises(ValueError, match="집계 가능한 거래행"):
        daily_pnl_from_trades([{"매수시간": None, "수익금": None}])


# ---------------------------------------------------------------------------
# 2. 입력 계약 위반 — 정직 에러
# ---------------------------------------------------------------------------

def test_combine_empty_candidates_raises():
    with pytest.raises(ValueError, match="비어 있습니다"):
        combine_candidates([])


def test_combine_duplicate_names_raises():
    cand = {"name": "X", "daily_pnl": {"20240101": 1.0}}
    with pytest.raises(ValueError, match="중복"):
        combine_candidates([cand, dict(cand)])


def test_combine_candidate_without_series_raises():
    with pytest.raises(ValueError, match="daily_pnl 또는 trades"):
        combine_candidates([{"name": "X"}])


def test_combine_invalid_weights_string_raises():
    with pytest.raises(ValueError, match="weights"):
        combine_candidates(
            [{"name": "X", "daily_pnl": {"20240101": 1.0}}], weights="optimized",
        )


def test_combine_weights_mapping_unknown_name_raises():
    with pytest.raises(ValueError, match="미지 후보명"):
        combine_candidates(
            [{"name": "X", "daily_pnl": {"20240101": 1.0}}],
            weights={"X": 1.0, "TYPO": 2.0},
        )


# ---------------------------------------------------------------------------
# 3. 상관행렬 + 상관 캡 제외 (조용한 탈락 금지)
# ---------------------------------------------------------------------------

def test_correlation_matrix_hand_verified():
    result = combine_candidates(_abc_candidates(), correlation_cap=0.5)
    corr = result["correlation"]
    assert corr["basis"] == "common_day_intersection"
    assert corr["labels"] == ["A", "B", "C"]
    matrix = corr["matrix"]
    assert matrix[0][0] == 1.0
    assert matrix[0][1] == pytest.approx(1.0, abs=1e-9)   # A~B: 같은 패턴의 아핀 변환
    assert matrix[0][2] == pytest.approx(0.0, abs=1e-9)   # A~C: 직교 패턴
    assert matrix[1][2] == pytest.approx(0.0, abs=1e-9)
    pair_ab = next(p for p in corr["pairs"] if {p["a"], p["b"]} == {"A", "B"})
    assert pair_ab["status"] == STATUS_OK
    assert pair_ab["n_overlap_days"] == 24


def test_correlation_cap_excludes_lower_performer_with_reason():
    result = combine_candidates(_abc_candidates(), correlation_cap=0.5)
    # B(총손익 960) 가 A(1200) 에 밀려 제외 — 사유 레코드 필수.
    assert result["selected"] == ["A", "C"]
    assert len(result["exclusions"]) == 1
    exclusion = result["exclusions"][0]
    assert exclusion["name"] == "B"
    assert exclusion["reason"] == "correlation_cap_exceeded"
    assert exclusion["kept"] == "A"
    assert exclusion["correlation"] == pytest.approx(1.0, abs=1e-9)
    assert exclusion["correlation_cap"] == 0.5
    assert exclusion["loser_total_profit"] == pytest.approx(960.0)
    assert exclusion["kept_total_profit"] == pytest.approx(1200.0)


def test_high_cap_keeps_everyone_no_exclusions():
    result = combine_candidates(_abc_candidates(), correlation_cap=1.1)
    assert result["selected"] == ["A", "B", "C"]
    assert result["exclusions"] == []


# ---------------------------------------------------------------------------
# 4. 표본 부족 / 무분산 — 추측 금지 정직 라벨
# ---------------------------------------------------------------------------

def test_insufficient_overlap_labeled_and_never_excluded():
    days = _days(5)  # 5일 < 기본 20일 하한
    result = combine_candidates([
        {"name": "A", "daily_pnl": {d: v for d, v in zip(days, [1.0, 2.0, 3.0, 4.0, 5.0])}},
        {"name": "B", "daily_pnl": {d: v for d, v in zip(days, [1.0, 2.0, 3.0, 4.0, 5.0])}},
    ], correlation_cap=0.5)
    pair = result["correlation"]["pairs"][0]
    assert pair["status"] == STATUS_INSUFFICIENT_OVERLAP
    assert pair["correlation"] is None
    assert pair["n_overlap_days"] == 5
    # 동일 시계열이라도 표본 부족이면 상관을 추측하지 않고 제외 근거로도 안 쓴다.
    assert result["selected"] == ["A", "B"]
    assert result["exclusions"] == []


def test_zero_variance_labeled_and_never_excluded():
    days = _days(24)
    result = combine_candidates([
        {"name": "FLAT", "daily_pnl": {d: 10.0 for d in days}},
        {"name": "MOVE", "daily_pnl": _series(_P, 100.0, 0.0)},
    ], correlation_cap=0.5)
    pair = result["correlation"]["pairs"][0]
    assert pair["status"] == STATUS_ZERO_VARIANCE
    assert pair["correlation"] is None
    assert result["exclusions"] == []


# ---------------------------------------------------------------------------
# 5. 시간밴드 상보성
# ---------------------------------------------------------------------------

def test_complementarity_disjoint_bands_scores_one():
    result = combine_candidates(_abc_candidates(), correlation_cap=0.5)
    comp = result["complementarity"]
    # 선택 [A(0900~0910), C(0910~0920)] — 반열림 구간이라 중첩 0 → 상보성 1.0.
    assert comp["status"] == STATUS_OK
    assert comp["score"] == pytest.approx(1.0)
    assert comp["pairs"][0]["overlap_ratio"] == pytest.approx(0.0)


def test_complementarity_identical_bands_scores_zero():
    days = _days(5)
    band = {"time_band": {"start": 90000, "end": 93000}}
    result = combine_candidates([
        {"name": "A", "daily_pnl": {d: 1.0 for d in days}, "meta": band},
        {"name": "B", "daily_pnl": {d: 2.0 for d in days}, "meta": band},
    ])
    assert result["complementarity"]["score"] == pytest.approx(0.0)


def test_complementarity_missing_band_is_honest_none():
    days = _days(5)
    result = combine_candidates([
        {"name": "A", "daily_pnl": {d: 1.0 for d in days},
         "meta": {"time_band": {"start": 90000, "end": 93000}}},
        {"name": "NOBAND", "daily_pnl": {d: 2.0 for d in days}},
    ])
    comp = result["complementarity"]
    assert comp["score"] is None
    assert comp["status"] == "missing_time_band"
    assert comp["missing"] == ["NOBAND"]


# ---------------------------------------------------------------------------
# 6. 결합 곡선 지표 — 수기 검증
# ---------------------------------------------------------------------------

def test_combined_mdd_and_profit_hand_verified():
    # A: +100, -300, +500 / B: +200, -100, +100 (equal=명목 1.0 합산)
    # 결합 일별 [300, -400, 600] → 누적 [300, -100, 500]
    # peak 300 → trough -100 → MDD 400. 총손익 500. 흑자일 2/3.
    result = combine_candidates([
        {"name": "A", "daily_pnl": {"20240101": 100.0, "20240102": -300.0, "20240103": 500.0}},
        {"name": "B", "daily_pnl": {"20240101": 200.0, "20240102": -100.0, "20240103": 100.0}},
    ], capital_base=1_000_000)
    port = result["portfolio"]
    assert port["total_profit"] == pytest.approx(500.0)
    assert port["mdd_money"] == pytest.approx(400.0)
    assert port["mdd_pct"] == pytest.approx(0.04)          # 400 / 1_000_000 * 100
    assert port["total_return_pct"] == pytest.approx(0.05)  # 500 / 1_000_000 * 100
    assert port["daily_curve"]["cum"] == [300.0, -100.0, 500.0]
    assert port["positive_day_ratio"] == pytest.approx(2.0 / 3.0)


def test_mdd_counts_initial_drawdown_from_zero_baseline():
    # 원금 기준선 0 에서 출발: 첫날 -100 도 MDD 로 센다.
    result = combine_candidates(
        [{"name": "A", "daily_pnl": {"20240101": -100.0, "20240102": 50.0}}],
    )
    assert result["portfolio"]["mdd_money"] == pytest.approx(100.0)


def test_union_days_fill_missing_with_zero():
    result = combine_candidates([
        {"name": "A", "daily_pnl": {"20240101": 100.0}},
        {"name": "B", "daily_pnl": {"20240102": -40.0}},
    ])
    port = result["portfolio"]
    assert port["daily_curve"]["days"] == ["20240101", "20240102"]
    assert port["daily_curve"]["daily"] == [100.0, -40.0]
    assert port["total_profit"] == pytest.approx(60.0)


def test_missing_capital_base_yields_honest_none_pct():
    result = combine_candidates(
        [{"name": "A", "daily_pnl": {"20240101": 100.0, "20240102": -30.0}}],
    )
    port = result["portfolio"]
    assert port["mdd_pct"] is None
    assert port["total_return_pct"] is None
    assert port["metric_notes"]["mdd_pct"] == "missing_capital_base"
    assert port["metric_notes"]["total_return_pct"] == "missing_capital_base"


def test_trade_stats_from_trades_and_meta_counts():
    trades_a = [
        {"매수시간": 20240101090001, "수익금": 100.0},
        {"매수시간": 20240101090500, "수익금": -50.0},
        {"매수시간": 20240102090001, "수익금": 200.0},
    ]
    result = combine_candidates([
        {"name": "A", "trades": trades_a},
        {"name": "B", "daily_pnl": {"20240101": 30.0, "20240102": -10.0},
         "n_trades": 2, "n_wins": 1},
    ])
    port = result["portfolio"]
    # 총 5거래 / 2거래일 = 2.5, 승 3/5 = 60%
    assert port["daily_avg_trades"] == pytest.approx(2.5)
    assert port["win_rate_pct"] == pytest.approx(60.0)


def test_trade_stats_unavailable_is_honest_none():
    result = combine_candidates([
        {"name": "A", "daily_pnl": {"20240101": 100.0}},  # 거래 통계 없음
    ])
    port = result["portfolio"]
    assert port["daily_avg_trades"] is None
    assert port["win_rate_pct"] is None
    assert port["metric_notes"]["daily_avg_trades"] == "trade_stats_unavailable"


def test_weights_mapping_scales_daily_pnl():
    result = combine_candidates([
        {"name": "A", "daily_pnl": {"20240101": 100.0}},
        {"name": "B", "daily_pnl": {"20240101": 100.0}},
    ], weights={"A": 2.0, "B": 1.0})
    assert result["portfolio"]["total_profit"] == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# 7. measurement_frame 라벨 필수
# ---------------------------------------------------------------------------

def test_frame_label_present_on_result_and_portfolio():
    result = combine_candidates(_abc_candidates())
    assert result[MEASUREMENT_FRAME_KEY] == FRAME_PORTFOLIO_MULTI_POSITION
    assert result["portfolio"][MEASUREMENT_FRAME_KEY] == FRAME_PORTFOLIO_MULTI_POSITION
    assert result["authority"] == "advisory_only"


# ---------------------------------------------------------------------------
# 8. 벤치마크 비교 — advisory 경고 전파 + 상대 지표 수기 검증
# ---------------------------------------------------------------------------

_REF_SINGLE = {
    "id": "#X",
    "profit_krw": 500_000,
    "total_return_pct": 100.0,
    "mdd_pct": 4.0,
    "daily_avg_trades": 20.0,
    "win_rate_pct": 40.0,
}


def _portfolio_metrics_annotated() -> dict:
    return annotate_frame({
        "total_profit": 1_000_000,
        "total_return_pct": 50.0,
        "mdd_pct": 2.0,
        "daily_avg_trades": 10.0,
        "win_rate_pct": 50.0,
    }, FRAME_PORTFOLIO_MULTI_POSITION)


def test_compare_ratios_hand_verified():
    report = compare_to_benchmark(_portfolio_metrics_annotated(), _REF_SINGLE)
    assert report["frame_warning"] is None
    row = report["rows"][0]
    assert row["reference_id"] == "#X"
    assert row["profit_multiple_krw"] == pytest.approx(2.0)
    assert row["return_multiple"] == pytest.approx(0.5)
    assert row["mdd_pct_ratio"] == pytest.approx(0.5)
    # TPI 유사: (50/2) / (100/4) = 25/25 = 1.0
    assert row["tpi_like_ratio"] == pytest.approx(1.0)
    assert row["daily_avg_trades_ratio"] == pytest.approx(0.5)
    assert row["win_rate_ratio"] == pytest.approx(1.25)
    assert row["missing_inputs"] == []


def test_compare_without_frame_propagates_advisory_warning():
    metrics = {"total_profit": 1_000_000, "total_return_pct": 50.0, "mdd_pct": 2.0}
    report = compare_to_benchmark(metrics, _REF_SINGLE)
    warning = report["frame_warning"]
    assert warning is not None
    assert warning["warning"] == "hall_of_fame_frame_missing"
    assert warning["authority"] == "advisory_only"
    # 경고는 전파하되 비교 자체는 막지 않는다(advisory).
    assert report["rows"][0]["profit_multiple_krw"] == pytest.approx(2.0)


def test_compare_niche_frame_propagates_not_portfolio_warning():
    metrics = annotate_frame({"total_return_pct": 50.0}, "niche_single_position")
    report = compare_to_benchmark(metrics, _REF_SINGLE)
    assert report["frame_warning"]["warning"] == "hall_of_fame_frame_not_portfolio"


def test_compare_with_strategies_list_and_median_summary():
    reference = {
        "_meta": {"kind": "human_benchmark"},
        "strategies": [
            dict(_REF_SINGLE),
            {**_REF_SINGLE, "id": "#Y", "total_return_pct": 200.0, "mdd_pct": 2.0},
        ],
    }
    report = compare_to_benchmark(_portfolio_metrics_annotated(), reference)
    assert report["reference_kind"] == "human_benchmark"
    assert report["reference_count"] == 2
    # return_multiple: [0.5, 0.25] → 중앙값 0.375
    assert report["summary"]["median_return_multiple"] == pytest.approx(0.375)


def test_compare_missing_inputs_are_listed_not_guessed():
    metrics = annotate_frame({"total_profit": 100.0}, FRAME_PORTFOLIO_MULTI_POSITION)
    row = compare_to_benchmark(metrics, _REF_SINGLE)["rows"][0]
    assert row["return_multiple"] is None
    assert "return_multiple" in row["missing_inputs"]
    assert "mdd_pct_ratio" in row["missing_inputs"]


def test_combine_result_feeds_compare_without_frame_warning():
    combined = combine_candidates(_abc_candidates(), capital_base=1_000_000)
    report = compare_to_benchmark(combined["portfolio"], _REF_SINGLE)
    assert report["frame_warning"] is None


# ---------------------------------------------------------------------------
# 9. reference_strategies.json 로드
# ---------------------------------------------------------------------------

def test_load_reference_strategies_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="reference_strategies.json"):
        load_reference_strategies(tmp_path / "absent.json")


def test_load_reference_strategies_default_file_loads():
    payload = load_reference_strategies()
    strategies = payload["strategies"]
    assert isinstance(strategies, list) and len(strategies) >= 1
    first = strategies[0]
    assert "annual_return_pct" in first and "mdd_pct" in first
