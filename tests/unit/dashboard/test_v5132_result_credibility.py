"""v5.13.2 — 결과 신뢰도 결함 회귀 테스트(2026-07-29 사용자 지적분).

고정하는 실측 결함:
  ① 보유시간 단위: 엔진(backengine_base.py:909-911)은 tick 백테에서 보유시간을 **초**,
     min 백테에서 **분**으로 쓴다. 대시보드가 항상 '분'으로 읽어 tick 결과의 보유시간이
     60배 부풀었다(실측: 1726 → "1726분", 실제 28.8분 — 30분 최대 보유와 모순).
  ② tick/min 구분: 결과에서 타임프레임을 알 수 없었다 → 시각 자릿수로 판별한다.
  ③ 수익률 의미: total_profit_pct(거래별 수익률 단순 합)가 '총수익률'로 표기돼
     명예의 전당의 자본 대비 수익률(32.71%)과 2배 어긋났다(65.36%).
  ④ 몬테카를로: 셔플(순열)만 있어 최종손익 분포가 항상 한 점으로 수렴했다.
  ⑤ GPT 로그인: POST /gpt_auth/login_start 가 보안 분류표에 없어 항상 403.
"""

from __future__ import annotations

import csv

import pytest

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard.security_capabilities import (
    DEFAULT_ON_CAPABILITIES,
    HTTP_CAPABILITIES,
    Capability,
)

_COLS = [
    analysis.COL_NAME, analysis.COL_BUY_TIME, analysis.COL_SELL_TIME,
    analysis.COL_HOLD_MIN, analysis.COL_PROFIT_PCT, analysis.COL_PROFIT_KRW,
]


def _write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(_COLS)
        w.writerows(rows)
    return str(path)


def _tick_csv(tmp_path):
    """tick 결과: 시각 14자리(YYYYMMDDHHMMSS), 보유시간은 초."""
    return _write_csv(tmp_path / "tick.csv", [
        # 09:04:03 → 09:07:31 = 208초
        ["삼성전자", "20250103090403", "20250103090731", 208, 4.59, 229983],
        # 09:05:56 → 09:30:00 = 1444초
        ["SG글로벌", "20250103090556", "20250103093000", 1444, 0.32, 16166],
    ])


def _min_csv(tmp_path):
    """min 결과: 시각 12자리(YYYYMMDDHHMM), 보유시간은 분."""
    return _write_csv(tmp_path / "min.csv", [
        # 10:00 → 15:18 = 318분
        ["에코프로", "202504071000", "202504071518", 318, 1.20, 50000],
        ["한미반도체", "202504081000", "202504081100", 60, -0.40, -20000],
    ])


# ---------------------------------------------------------------- ① 보유시간 단위
def test_tick_hold_column_is_seconds_not_minutes(tmp_path):
    trades = analysis.load_trades_csv(_tick_csv(tmp_path))
    assert [t["hold_sec"] for t in trades] == [208.0, 1444.0]
    # 1444초 = 24.07분 — '1444분'으로 부풀지 않아야 한다.
    assert trades[1]["hold_min"] == pytest.approx(1444 / 60.0)


def test_min_hold_column_is_minutes(tmp_path):
    trades = analysis.load_trades_csv(_min_csv(tmp_path))
    assert [t["hold_min"] for t in trades] == [318.0, 60.0]
    assert trades[0]["hold_sec"] == pytest.approx(318 * 60.0)


def test_tick_summary_max_hold_stays_within_thirty_minutes(tmp_path):
    """초기 30분 tick 전략의 최장 보유가 30분을 넘지 않아야 한다(실측 회귀)."""
    summary = analysis.summary_metrics(analysis.load_trades_csv(_tick_csv(tmp_path)))
    assert summary["max_hold_sec"] == 1444.0
    assert summary["max_hold_sec"] / 60.0 < 30.0


# ------------------------------------------------------------------ ② tick/min
@pytest.mark.parametrize("sell_time,expected", [
    ("20250103090731", "tick"),
    ("202504071518", "min"),
    ("", "unknown"),
    ("abcd", "unknown"),
])
def test_detect_timeframe_from_time_digits(sell_time, expected):
    assert analysis.detect_timeframe(sell_time) == expected


def test_summary_and_peek_expose_timeframe(tmp_path):
    tick, minute = _tick_csv(tmp_path), _min_csv(tmp_path)
    assert analysis.summary_metrics(analysis.load_trades_csv(tick))["timeframe"] == "tick"
    assert analysis.summary_metrics(analysis.load_trades_csv(minute))["timeframe"] == "min"
    # peek 는 전체 파싱 없이 첫 행만 읽는다(세대 목록 배지용).
    assert analysis.peek_timeframe_csv(tick) == "tick"
    assert analysis.peek_timeframe_csv(minute) == "min"
    assert analysis.peek_timeframe_csv(None) == "unknown"


def test_hold_histogram_unit_follows_timeframe(tmp_path):
    assert analysis.pnl_distribution(analysis.load_trades_csv(_tick_csv(tmp_path)))["hold_unit"] == "sec"
    assert analysis.pnl_distribution(analysis.load_trades_csv(_min_csv(tmp_path)))["hold_unit"] == "min"


# ------------------------------------------------------------------ ③ 수익률 의미
def test_sum_trade_return_is_named_separately(tmp_path):
    """거래별 수익률의 단순 합은 자본 대비 수익률이 아니다 — 별도 키로 노출."""
    summary = analysis.summary_metrics(analysis.load_trades_csv(_tick_csv(tmp_path)))
    assert summary["sum_trade_return_pct"] == pytest.approx(4.59 + 0.32)
    # 하위호환 키는 남되 같은 값(소비측이 이름으로 의미를 구분한다).
    assert summary["total_profit_pct"] == pytest.approx(summary["sum_trade_return_pct"])


def test_summary_exposes_period_span_for_annualization(tmp_path):
    summary = analysis.summary_metrics(analysis.load_trades_csv(_min_csv(tmp_path)))
    assert summary["period_start"] == 20250407
    assert summary["period_end"] == 20250408
    assert summary["calendar_days"] == 2


def test_annualize_refuses_short_windows():
    from ai_strategy_loop.dashboard.backtest_api import _annualize_pct

    assert _annualize_pct(30.0, 5) is None       # 기간 5일 — 연환산 과장 방지
    assert _annualize_pct(None, 365) is None
    assert _annualize_pct(-150.0, 365) is None   # 원금 전손 이상 — 정의 불가
    assert _annualize_pct(10.0, 365) == pytest.approx(10.0, abs=0.01)


# ------------------------------------------------------------------ ④ 몬테카를로
def test_shuffle_final_is_degenerate_and_flagged(tmp_path):
    """셔플은 날의 집합이 보존돼 최종손익이 항상 같다 — 버그가 아니라 성질이므로 표시한다."""
    trades = analysis.load_trades_csv(_min_csv(tmp_path))
    mc = analysis.monte_carlo(trades, n=200, seed=1, method="shuffle")
    assert mc["method"] == "shuffle"
    assert mc["final_degenerate"] is True
    assert mc["final"]["p5"] == pytest.approx(mc["final"]["p95"])
    assert mc["method_note"]


def test_bootstrap_final_has_real_spread():
    """복원추출은 최종손익도 분포를 가진다(팬이 끝에서 닫히지 않는다)."""
    trades = [{"day": 20250400 + i, "profit_krw": (100.0 if i % 2 else -60.0),
               "profit_pct": 1.0, "hold_sec": 60.0, "hold_min": 1.0,
               "name": "x", "buy_time": "", "sell_time": "", "timeframe": "min"}
              for i in range(1, 21)]
    mc = analysis.monte_carlo(trades, n=800, seed=3, method="bootstrap")
    assert mc["method"] == "bootstrap"
    assert mc["final_degenerate"] is False
    assert mc["final"]["p95"] > mc["final"]["p5"]


# ------------------------------------------------------------------ ⑤ GPT 로그인
def test_login_start_is_classified_so_it_cannot_403_as_unclassified():
    """미분류 mutation 은 security.authorize_http 가 무조건 403 한다(로그인 무반응 원인)."""
    assert ("POST", "/gpt_auth/login_start") in HTTP_CAPABILITIES
    assert HTTP_CAPABILITIES[("POST", "/gpt_auth/login_start")] is Capability.PROVIDER_LOGIN


def test_provider_login_is_enabled_by_default():
    """루프백 바인드 + Origin 일치 + 세션 쿠키가 이미 걸려 있고, 서버는 비밀번호를 보지 않는다.
    기본 OFF 로 두면 설정 탭 로그인 버튼이 항상 403 이라 기능 자체가 죽는다."""
    assert Capability.PROVIDER_LOGIN in DEFAULT_ON_CAPABILITIES
