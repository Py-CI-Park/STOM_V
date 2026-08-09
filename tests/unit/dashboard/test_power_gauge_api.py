# -*- coding: utf-8 -*-
"""페이지 31 API 계약 테스트.

계약:
  1. 거래 빈도의 분모는 **DB 실거래일**이다 — 달력 일수도, 거래가 난 날도 아니다.
  2. 합격선 기록이 없으면 빈도를 지어내지 않는다.
  3. 부족분은 '며칠'로 환산된다 — 계획을 세울 수 있는 단위여야 한다.
  4. 판독 규칙은 항상 실려 나간다(화면이 숫자만 보여주면 오독한다).
"""
from __future__ import annotations

import pandas as pd
import pytest

from ai_strategy_loop.dashboard import power_gauge_api as api

#: 실제 영업일 축 — 존재하지 않는 날짜(20240332 같은)로 분모를 만들면
#: 구간 필터가 통과해 버려 테스트가 코드보다 먼저 틀린다.
DB_DAYS = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range("2024-03-04", "2025-08-22")]


def _row(cid, verdict, **kw):
    base = {"candidate_id": cid, "sell_name": cid, "verdict": verdict,
            "trades": None, "period_start": 20240304, "period_end": 20250822,
            "paired_pairs": None, "paired_mean_diff_pct": None,
            "paired_ci_low": None, "paired_ci_high": None}
    base.update(kw)
    return base


@pytest.fixture()
def wired(monkeypatch):
    """원장과 DB 날짜 목록을 고정한다 — 실제 파일 시스템에 의존하지 않는다."""
    def _install(rows):
        monkeypatch.setattr(api.ledger, "latest_per_candidate", lambda: rows)
        monkeypatch.setattr(api.standing, "db_days", lambda lane: DB_DAYS)
        return DB_DAYS

    return _install


def test_trade_rate_divides_by_db_trading_days(wired):
    """★ 분모는 DB 실거래일 — 거래가 난 날만 세면 빈도가 과대평가된다."""
    days = wired([_row("champ", "BASELINE", trades=161)])
    rate = api.power_gauge_view()["trade_rate"]
    assert rate["db_trading_days"] == len(days)
    assert rate["trades_per_day"] == pytest.approx(161 / len(days))
    # 실측 감각 확인: 0.5건/일 근방이지 1.39건/일(거래일만 센 값)이 아니다.
    assert 0.3 < rate["trades_per_day"] < 0.7


def test_missing_baseline_reports_instead_of_inventing(wired):
    wired([_row("c1", "MIXED", paired_pairs=160, paired_mean_diff_pct=0.3,
                paired_ci_low=-0.09, paired_ci_high=0.69)])
    payload = api.power_gauge_view()
    assert payload["trade_rate"]["available"] is False
    assert payload["trade_rate"]["reason"]
    # 빈도를 모르면 '며칠'은 못 내지만 '몇 짝'은 낸다.
    gauge = payload["gauges"][0]
    assert gauge["extra_days_needed"] is None
    assert gauge["extra_pairs_needed"] > 0


def test_shortfall_is_converted_to_trading_days(wired):
    days = wired([
        _row("champ", "BASELINE", trades=161),
        _row("c1", "MIXED", paired_pairs=160, paired_mean_diff_pct=0.3,
             paired_ci_low=-0.09, paired_ci_high=0.69),
    ])
    payload = api.power_gauge_view()
    gauge = next(g for g in payload["gauges"] if g["candidate_id"] == "c1")
    rate = 161 / len(days)
    assert gauge["extra_days_needed"] == pytest.approx(gauge["extra_pairs_needed"] / rate)
    assert payload["days_to_finish_round"] == pytest.approx(gauge["extra_days_needed"])


def test_period_filters_the_day_axis(wired):
    """구간 밖 거래일은 분모에 들어가지 않는다."""
    wired([_row("champ", "BASELINE", trades=100,
                period_start=20240310, period_end=20240320)])
    rate = api.power_gauge_view()["trade_rate"]
    expected = sum(1 for d in DB_DAYS if 20240310 <= d <= 20240320)
    assert rate["db_trading_days"] == expected < len(DB_DAYS)
    assert rate["period"] == [20240310, 20240320]


def test_reading_rules_always_ship(wired):
    wired([_row("champ", "BASELINE", trades=161)])
    rules = api.power_gauge_view()["reading_rules"]
    assert any("MDE" in r for r in rules)
    assert any("검정력" in r for r in rules)


def test_empty_ledger_is_empty(wired):
    wired([])
    payload = api.power_gauge_view()
    assert payload["available"] is False and payload["candidates"] == 0
