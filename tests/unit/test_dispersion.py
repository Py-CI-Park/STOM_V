"""Track B 1차 — 다종목 분산 기반 고빈도 유도 토글 단위 테스트.

검증:
  (A) build_messages 프롬프트 분산 토글(dispersion_prompt_enabled):
      - OFF(기본): seed-refine 저빈도 압력 문구가 byte 보존된다(회귀).
      - ON: 그 문구가 사라지고 "분산"·"과발화" 취지 문구가 들어간다.
      - target_daily_trades: 주입 시 산식 문구 존재, None이면 부재.
  (B) _dispersion_term 수학: None→None, 6/6→1.0, 3/6→0.5, 12/6→1.0(clamp).
  (C) compute_graded_fitness 분산 토글(dispersion_enabled):
      - OFF(기본): 기존과 동일 graded(회귀).
      - ON + max_hold_count: 게이트-실패 graded에 분산항 반영(값 달라짐).
      - 게이트-통과 graded 불변, compute_fitness(하드게이트) 불변.

OFF=기존동작 보존이 핵심 — 모든 신규 동작은 토글 뒤에만 있다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.brain.prompt import build_messages
from ai_strategy_loop.fitness.score import (
    compute_fitness,
    compute_graded_fitness,
    _dispersion_term,
)

# base_code(seed-refine) 경로를 타게 하는 더미 출발점 전략(내용 무관).
_BASE_BUY = "매수 = False\nif 등락율 > 3:\n    매수 = True\nif 매수:\n    self.Buy()"

# 저빈도 압력 문장의 byte-보존 회귀 마커(OFF에서 반드시 존재해야 한다).
_LOWFREQ_MARKER_1 = "늘리지 말고 유지하거나 줄여라"
_LOWFREQ_MARKER_2 = "현재 전략의 거래 수준을 넘지 않게 하라"

_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


# ============================================================
# (A) build_messages 프롬프트 분산 토글
# ============================================================

def test_dispersion_prompt_off_preserves_lowfreq_phrases():
    """OFF(기본): seed-refine 저빈도 압력 문구가 byte 보존된다(회귀)."""
    messages = build_messages("buy", timeframe="min", base_code=_BASE_BUY)
    user = _user_text(messages)
    assert _LOWFREQ_MARKER_1 in user
    assert _LOWFREQ_MARKER_2 in user
    # 분산 취지 문구는 OFF에서 없어야 한다.
    assert "분산 진입" not in user
    assert "과발화" not in user


def test_dispersion_prompt_on_replaces_lowfreq_with_dispersion():
    """ON: 저빈도 압력 문구가 사라지고 분산·과발화 취지 문구가 들어간다."""
    messages = build_messages(
        "buy", timeframe="min", base_code=_BASE_BUY,
        dispersion_prompt_enabled=True,
    )
    user = _user_text(messages)
    # 저빈도 압력 문구 부재.
    assert _LOWFREQ_MARKER_1 not in user
    assert _LOWFREQ_MARKER_2 not in user
    # 분산매매 취지 문구 존재.
    assert "분산 진입" in user
    assert "분산매매" in user
    assert "과발화" in user
    # 유동성 게이트 보존 경고가 들어가야 한다(흑자 핵심).
    assert "유동성 게이트" in user
    # 거래 빈도 블록 뒤 단일 종목 과발화 억제 한 줄.
    assert "항상참 임계" in user


def test_dispersion_prompt_on_no_basecode_is_safe():
    """ON이어도 base_code 없는 fresh 경로는 안전하게 동작한다(seed-refine 블록 미진입)."""
    messages = build_messages("buy", timeframe="min", dispersion_prompt_enabled=True)
    user = _user_text(messages)
    # fresh 경로엔 seed-refine 블록이 없으므로 direction_line/mdd_line 치환이 없다.
    # 단, 거래 빈도 블록 뒤 과발화 억제 한 줄은 (dispersion ON이라) 추가된다.
    assert "항상참 임계" in user
    assert any(m["role"] == "system" for m in messages)


def test_dispersion_prompt_sell_path_unaffected():
    """매도 경로는 dispersion_prompt_enabled와 무관하게 동일하다(분산은 매수 의미)."""
    off = _user_text(build_messages("sell", timeframe="min", base_code=_BASE_BUY))
    on = _user_text(build_messages(
        "sell", timeframe="min", base_code=_BASE_BUY,
        dispersion_prompt_enabled=True,
    ))
    assert off == on


def test_target_daily_trades_formula_present_when_given():
    """target_daily_trades 주입 시 산식 문구 존재, None이면 부재."""
    with_target = _user_text(build_messages(
        "buy", timeframe="min", target_daily_trades=15.0,
    ))
    assert "일평균 15회" in with_target
    assert "6~12종목" in with_target

    without_target = _user_text(build_messages("buy", timeframe="min"))
    # None이면 산식이 붙지 않는다.
    assert "일평균 15회" not in without_target
    assert "종목당 일평균 1.5~2회" not in without_target


# ============================================================
# (B) _dispersion_term 수학
# ============================================================

def test_dispersion_term_none_when_no_hold_count():
    """max_hold_count가 None이면 None(무영향)."""
    assert _dispersion_term(None, 6.0) is None


def test_dispersion_term_values():
    """6/6→1.0, 3/6→0.5, 12/6→1.0(clamp)."""
    assert _dispersion_term(6.0, 6.0) == 1.0
    assert _dispersion_term(3.0, 6.0) == 0.5
    assert _dispersion_term(12.0, 6.0) == 1.0  # clamp 상한


def test_dispersion_term_min_hold_symbols_fallback():
    """min_hold_symbols<=0이면 기본(6.0)으로 폴백한다."""
    # 0/폴백6 → 3/6=0.5
    assert _dispersion_term(3.0, 0.0) == 0.5


# ============================================================
# (C) compute_graded_fitness 분산 토글
# ============================================================

def _config():
    """min_trades=30, mdd_cap=25 — graded 테스트 기준 게이트."""
    return LoopConfig(min_trades=30, mdd_cap=25.0)


def _metrics(cagr, mdd, trades, profit, max_hold_count=None):
    m = {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }
    if max_hold_count is not None:
        m["max_hold_count"] = max_hold_count
    return m


def test_graded_off_is_identical_regression():
    """dispersion_enabled=False(기본)면 기존과 graded가 완전 동일하다(회귀)."""
    cfg = _config()
    # max_hold_count가 있어도 OFF면 무시되어야 한다.
    m = _metrics(30.0, 60.0, 50, 1_000_000, max_hold_count=10)
    default_call = compute_graded_fitness(m, _STEADY, cfg)
    off_call = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=False)
    assert default_call.graded == off_call.graded
    # OFF면 dispersion_term 노출값이 무영향 기본(1.0).
    assert default_call.dispersion_term == 1.0


def test_graded_on_gate_failed_reflects_dispersion():
    """ON + max_hold_count: 게이트-실패 graded에 분산항이 반영되어 값이 달라진다."""
    cfg = _config()
    # 수익 + 거래충분이지만 MDD 60 > cap 25 → 게이트 실패.
    m_low = _metrics(30.0, 60.0, 50, 1_000_000, max_hold_count=1)   # 거의 분산 안 됨
    m_high = _metrics(30.0, 60.0, 50, 1_000_000, max_hold_count=12)  # 잘 분산됨

    off = compute_graded_fitness(m_high, _STEADY, cfg, dispersion_enabled=False)
    on_low = compute_graded_fitness(
        m_low, _STEADY, cfg, dispersion_enabled=True, min_hold_symbols=6.0
    )
    on_high = compute_graded_fitness(
        m_high, _STEADY, cfg, dispersion_enabled=True, min_hold_symbols=6.0
    )

    assert on_low.gate_passed is False
    assert on_high.gate_passed is False
    # 분산이 잘 된 전략이 분산 안 된 전략보다 graded가 높다(동시보유 보상).
    assert on_high.graded > on_low.graded
    # ON이 OFF와 graded가 달라진다(분산항이 base 평균에 가산됨).
    assert on_high.graded != off.graded
    # dispersion_term 노출값: 1/6→0.1667, 12/6→1.0(clamp).
    assert on_high.dispersion_term == 1.0
    assert abs(on_low.dispersion_term - (1.0 / 6.0)) < 1e-9
    assert on_high.max_hold_count == 12.0


def test_graded_on_no_hold_count_no_effect():
    """ON이어도 metrics에 max_hold_count가 없으면 graded는 OFF와 동일(하위호환)."""
    cfg = _config()
    m = _metrics(30.0, 60.0, 50, 1_000_000)  # max_hold_count 키 없음
    off = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=False)
    on = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=True)
    assert on.graded == off.graded
    assert on.dispersion_term == 1.0


def test_graded_on_gate_passed_unchanged():
    """게이트-통과 graded는 dispersion 토글과 무관하게 불변이다."""
    cfg = _config()
    # 통과: 거래 50>=30, MDD 10<=25, 수익>0.
    m = _metrics(30.0, 10.0, 50, 1_000_000, max_hold_count=12)
    off = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=False)
    on = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=True)
    assert off.gate_passed is True and on.gate_passed is True
    # 통과 분기 graded는 1.0+term(objective)로, 분산항이 끼지 않으므로 동일.
    assert on.graded == off.graded


def test_hard_gate_unchanged_by_dispersion():
    """compute_fitness(하드게이트)는 dispersion과 전혀 무관하다(시그니처/결과 불변)."""
    cfg = _config()
    m = _metrics(30.0, 10.0, 50, 1_000_000, max_hold_count=12)
    fit = compute_fitness(m, _STEADY, cfg)
    # 하드게이트는 max_hold_count를 보지 않는다 — 통과 여부는 빈도/MDD/수익만.
    assert fit.gate_passed is True
    assert fit.score > 0.0


# ============================================================
# (D) max_hold_count 저장/표시값은 토글 무관 raw(정보 손실 수정)
# ============================================================

def test_max_hold_count_stored_raw_when_dispersion_off():
    """버그 수정: dispersion OFF여도 GradedResult.max_hold_count에 엔진 실측 raw를 싣는다.

    엔진은 동시보유 피크(max_hold_count)를 항상 계산하지만, 기존 코드는 이 값을
    dispersion_enabled=True일 때만 GradedResult에 실어, OFF(기본)인 모든 run이 실측
    동시보유를 0.0으로 버렸다(정보 손실). 저장/표시용 필드는 토글과 무관하게 raw를
    싣고, 점수 가산용 dispersion_term만 게이트(enabled)를 유지한다.
    """
    cfg = _config()
    m = _metrics(30.0, 10.0, 50, 1_000_000, max_hold_count=2)
    # OFF(명시) + 기본 호출 모두 — 표시값은 실측 2.0, dispersion_term은 중립 1.0.
    off = compute_graded_fitness(m, _STEADY, cfg, dispersion_enabled=False)
    default = compute_graded_fitness(m, _STEADY, cfg)
    assert off.max_hold_count == 2.0            # 토글 OFF여도 실측값 보존.
    assert default.max_hold_count == 2.0        # 기본 호출도 동일.
    assert off.dispersion_term == 1.0           # 점수 가산항은 게이트로 중립.
    assert default.dispersion_term == 1.0


def test_max_hold_count_raw_does_not_change_graded():
    """불변식: max_hold_count raw 노출은 graded 점수를 byte-동일하게 둔다.

    graded는 dispersion_term만 사용하고 max_hold_count 필드는 직접 쓰지 않는다.
    OFF에서 dispersion_term은 항상 중립(None→1.0이지만 base 평균에 미가산)이므로,
    max_hold_count 키가 있든(2) 없든 graded는 동일해야 한다.
    """
    cfg = _config()
    # 게이트-실패 분기(MDD 초과)에서도 max_hold_count 유무가 graded에 영향 없음.
    m_with = _metrics(30.0, 60.0, 50, 1_000_000, max_hold_count=2)
    m_without = _metrics(30.0, 60.0, 50, 1_000_000)  # 키 없음.
    g_with = compute_graded_fitness(m_with, _STEADY, cfg, dispersion_enabled=False)
    g_without = compute_graded_fitness(m_without, _STEADY, cfg, dispersion_enabled=False)
    assert g_with.graded == g_without.graded     # graded byte-동일.
    # 표시값만 갈린다: raw 있으면 2.0, 없으면 0.0(폴백).
    assert g_with.max_hold_count == 2.0
    assert g_without.max_hold_count == 0.0


def test_max_hold_count_none_falls_back_to_zero():
    """metrics에 max_hold_count 키가 없으면 표시값은 0.0 폴백(하위호환)."""
    cfg = _config()
    m = _metrics(30.0, 10.0, 50, 1_000_000)  # 키 없음.
    g = compute_graded_fitness(m, _STEADY, cfg)
    assert g.max_hold_count == 0.0
