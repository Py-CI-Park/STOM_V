"""T0.3 측정계 프레임(niche/portfolio) 이원화 advisory 단위 테스트.

ai_strategy_loop/fitness/measurement_frame.py 계약(열거·additive 부여·advisory
경고·명예의 전당 portfolio 전용 규칙)과 cli/research_metrics.py 기본 프레임
additive 병기, dashboard/backtest_report.py 프레임 라벨 필수 표기를 검증한다.
DB/엔진/런타임 접근 없음 — 순수 dict/DataFrame/HTML 문자열 기반.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from ai_strategy_loop.dashboard.backtest_report import render_report
from ai_strategy_loop.fitness.measurement_frame import (
    DEFAULT_MEASUREMENT_FRAME,
    FRAME_NICHE_SINGLE_POSITION,
    FRAME_PORTFOLIO_MULTI_POSITION,
    HALL_OF_FAME_COMPARISON_FRAME,
    MEASUREMENT_FRAME_KEY,
    MeasurementFrame,
    VALID_MEASUREMENT_FRAMES,
    annotate_frame,
    assert_comparable,
    assert_hall_of_fame_comparable,
    frame_label,
    resolve_frame,
)
from cli.research_metrics import summarize_trade_frame


def _sample_frame():
    """세그먼트 연구 지표 계산이 기대하는 한국어 컬럼 합성 프레임."""
    return pd.DataFrame([
        {'종목명': 'A', '매수시간': 20250101090000, '매도시간': 20250101091000,
         '매수가': 1000, '수익률': 1.5, '수익금': 1500, 'R_MFE': 2.0, 'R_MAE': -0.5, '매도조건': '익절'},
        {'종목명': 'B', '매수시간': 20250102093000, '매도시간': 20250102094000,
         '매수가': 2000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -1.8, '매도조건': '손절'},
    ])


# ── (a) 열거 + 계약 상수 ─────────────────────────────────────────────────


def test_frame_enumeration_and_contract_constants():
    assert MeasurementFrame.NICHE_SINGLE_POSITION.value == "niche_single_position"
    assert MeasurementFrame.PORTFOLIO_MULTI_POSITION.value == "portfolio_multi_position"
    assert VALID_MEASUREMENT_FRAMES == (
        FRAME_NICHE_SINGLE_POSITION,
        FRAME_PORTFOLIO_MULTI_POSITION,
    )
    # 미표기 지표의 보수적 해석값은 1포지션 니치.
    assert DEFAULT_MEASUREMENT_FRAME == FRAME_NICHE_SINGLE_POSITION
    # 명예의 전당/인간 벤치마크 비교는 portfolio 프레임 전용(상수로 고정된 규칙).
    assert HALL_OF_FAME_COMPARISON_FRAME == FRAME_PORTFOLIO_MULTI_POSITION


# ── (b) annotate_frame: additive + 불변성 + 조기 실패 ────────────────────


def test_annotate_frame_is_additive_and_immutable():
    original = {"trade_count": 3}
    annotated = annotate_frame(original, FRAME_NICHE_SINGLE_POSITION)
    assert annotated == {
        "trade_count": 3,
        MEASUREMENT_FRAME_KEY: FRAME_NICHE_SINGLE_POSITION,
    }
    assert original == {"trade_count": 3}  # 원본 불변(새 dict 반환).
    assert annotated is not original


def test_annotate_frame_accepts_enum_and_overwrites_existing():
    relabeled = annotate_frame(
        {MEASUREMENT_FRAME_KEY: FRAME_NICHE_SINGLE_POSITION},
        MeasurementFrame.PORTFOLIO_MULTI_POSITION,
    )
    # 열거 멤버도 JSON-safe 평문 문자열 값으로 저장된다.
    assert relabeled[MEASUREMENT_FRAME_KEY] == FRAME_PORTFOLIO_MULTI_POSITION
    assert type(relabeled[MEASUREMENT_FRAME_KEY]) is str


@pytest.mark.parametrize("bad", ["", None, "portfolio", "NICHE_SINGLE_POSITION", 3])
def test_annotate_frame_rejects_unknown_frame(bad):
    with pytest.raises(ValueError):
        annotate_frame({}, bad)  # 오표기 조용한 영속 방지 — 조기 실패.


# ── (c) resolve_frame / frame_label ──────────────────────────────────────


def test_resolve_frame_reads_mapping_string_and_enum():
    annotated = {MEASUREMENT_FRAME_KEY: FRAME_PORTFOLIO_MULTI_POSITION}
    assert resolve_frame(annotated) == FRAME_PORTFOLIO_MULTI_POSITION
    assert resolve_frame(FRAME_NICHE_SINGLE_POSITION) == FRAME_NICHE_SINGLE_POSITION
    assert resolve_frame(MeasurementFrame.NICHE_SINGLE_POSITION) == FRAME_NICHE_SINGLE_POSITION
    assert resolve_frame({}) is None
    assert resolve_frame({MEASUREMENT_FRAME_KEY: "  "}) is None  # 공백은 미표기.
    assert resolve_frame(None, default=DEFAULT_MEASUREMENT_FRAME) == DEFAULT_MEASUREMENT_FRAME


def test_frame_label_korean_and_fallback():
    assert frame_label(FRAME_NICHE_SINGLE_POSITION) == "니치(1포지션)"
    assert frame_label(MeasurementFrame.PORTFOLIO_MULTI_POSITION) == "포트폴리오(다중보유)"
    assert frame_label("custom_frame") == "custom_frame"  # 미지 값은 원문 폴백(무예외).
    assert frame_label(None) == "측정계 미상"


# ── (d) assert_comparable: 예외 금지 advisory 경고 ───────────────────────


def test_assert_comparable_same_frame_returns_none():
    a = annotate_frame({"trade_count": 1}, FRAME_NICHE_SINGLE_POSITION)
    b = annotate_frame({"trade_count": 9}, FRAME_NICHE_SINGLE_POSITION)
    assert assert_comparable(a, b) is None
    assert assert_comparable(
        FRAME_PORTFOLIO_MULTI_POSITION, FRAME_PORTFOLIO_MULTI_POSITION
    ) is None


def test_assert_comparable_mismatch_returns_advisory_warning_without_raise():
    niche = annotate_frame({}, FRAME_NICHE_SINGLE_POSITION)
    portfolio = annotate_frame({}, FRAME_PORTFOLIO_MULTI_POSITION)
    warning = assert_comparable(niche, portfolio)
    assert warning["warning"] == "measurement_frame_mismatch"
    assert warning["authority"] == "advisory_only"  # 예외 금지 — 경고 dict 반환.
    assert warning["frame_a"] == FRAME_NICHE_SINGLE_POSITION
    assert warning["frame_b"] == FRAME_PORTFOLIO_MULTI_POSITION
    # JSON 직렬화 안전(오케스트레이터가 그대로 영수증에 병기 가능).
    text = json.dumps(warning, ensure_ascii=False)
    assert "measurement_frame_mismatch" in text


@pytest.mark.parametrize(
    ("a", "b", "code"),
    [
        ({}, {MEASUREMENT_FRAME_KEY: FRAME_NICHE_SINGLE_POSITION}, "measurement_frame_missing"),
        (None, FRAME_NICHE_SINGLE_POSITION, "measurement_frame_missing"),
        ("weird_frame", "weird_frame", "measurement_frame_unknown"),
    ],
)
def test_assert_comparable_flags_missing_or_unknown_frames(a, b, code):
    warning = assert_comparable(a, b)
    assert warning["warning"] == code
    assert warning["authority"] == "advisory_only"


# ── (e) 명예의 전당 비교는 portfolio 프레임 전용 ─────────────────────────


def test_hall_of_fame_comparison_requires_portfolio_frame():
    portfolio = annotate_frame({"cagr": 130.0}, HALL_OF_FAME_COMPARISON_FRAME)
    assert assert_hall_of_fame_comparable(portfolio) is None

    niche = annotate_frame({"cagr": 130.0}, FRAME_NICHE_SINGLE_POSITION)
    warning = assert_hall_of_fame_comparable(niche)
    assert warning["warning"] == "hall_of_fame_frame_not_portfolio"
    assert warning["frame"] == FRAME_NICHE_SINGLE_POSITION
    assert warning["required_frame"] == HALL_OF_FAME_COMPARISON_FRAME

    missing = assert_hall_of_fame_comparable({"cagr": 130.0})
    assert missing["warning"] == "hall_of_fame_frame_missing"
    assert missing["authority"] == "advisory_only"


# ── (f) research_metrics 기본 프레임 additive 병기 ───────────────────────


def test_summarize_trade_frame_carries_default_niche_frame():
    summary = summarize_trade_frame(_sample_frame())
    assert summary[MEASUREMENT_FRAME_KEY] == FRAME_NICHE_SINGLE_POSITION
    # 기존 지표 스키마 불변(additive만) — 핵심 키 유지.
    assert summary["trade_count"] == 2
    assert summary["sell_condition_counts"] == {"익절": 1, "손절": 1}


def test_summarize_trade_frame_empty_frame_still_labeled():
    summary = summarize_trade_frame(pd.DataFrame(columns=['수익률', '수익금']))
    assert summary["trade_count"] == 0
    assert summary[MEASUREMENT_FRAME_KEY] == FRAME_NICHE_SINGLE_POSITION


# ── (g) backtest_report 프레임 라벨 필수 표기 ────────────────────────────


def test_render_report_shows_default_niche_frame_label():
    html = render_report({"meta": {"title": "T"}, "metrics": {"trade_count": 1}})
    assert "측정계" in html
    assert "니치(1포지션)" in html
    assert FRAME_NICHE_SINGLE_POSITION in html  # 기계 판독용 프레임 코드 병기.


def test_render_report_shows_portfolio_frame_label_from_metrics():
    metrics = annotate_frame({"trade_count": 1}, FRAME_PORTFOLIO_MULTI_POSITION)
    html = render_report({"meta": {"title": "T"}, "metrics": metrics})
    assert "포트폴리오(다중보유)" in html
    assert FRAME_PORTFOLIO_MULTI_POSITION in html


def test_render_report_meta_frame_overrides_metrics_frame():
    metrics = annotate_frame({"trade_count": 1}, FRAME_NICHE_SINGLE_POSITION)
    payload = {
        "meta": {"title": "T", MEASUREMENT_FRAME_KEY: FRAME_PORTFOLIO_MULTI_POSITION},
        "metrics": metrics,
    }
    html = render_report(payload)
    assert "포트폴리오(다중보유)" in html  # meta 명시값 우선.
    # 입력 payload 불변(meta 복사본에만 주입).
    assert payload["meta"] == {
        "title": "T",
        MEASUREMENT_FRAME_KEY: FRAME_PORTFOLIO_MULTI_POSITION,
    }


def test_render_report_empty_payload_still_labels_frame_without_raise():
    html = render_report({})
    assert html.startswith("<!DOCTYPE html>")
    assert "니치(1포지션)" in html  # 프레임 라벨 필수 표기(기본 니치).
    # 자급자족 계약 유지(외부 리소스 0).
    assert "http://" not in html and "https://" not in html
