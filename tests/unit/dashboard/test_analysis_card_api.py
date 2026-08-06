# -*- coding: utf-8 -*-
"""페이지 25 분석 카드 API 계약 테스트.

계약:
  1. 완료된 job 의 거래 CSV → 카드(v2) 반환, 권한 키는 research_analysis_card_only.
  2. 미완료/없는 job 은 카드를 만들지 않는다 (불완전 산출물을 근거로 삼지 않음).
  3. 같은 job 재요청은 캐시로 응답한다 (같은 결과를 두 번 계산하지 않음).
  4. 손실 거래 목록은 수익률 오름차순 상위 N 건이다.
"""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from ai_strategy_loop.dashboard import analysis_card_api as api


@pytest.fixture(autouse=True)
def _clear_cache():
    api._card_cache.clear()
    yield
    api._card_cache.clear()


def _write_trades(tmp_path):
    csv_path = tmp_path / "trades.csv"
    pd.DataFrame({
        "일자": [20250403] * 6,
        "종목명": [f"종목{i}" for i in range(6)],
        "종목코드": [f"00000{i}" for i in range(6)],
        "매수시간": [90100 + i for i in range(6)],
        "매도시간": [90300 + i for i in range(6)],
        "수익률": [1.2, -2.5, 0.7, -3.1, 2.0, -0.4],
        "수익금": [12000, -25000, 7000, -31000, 20000, -4000],
        "보유시간": [120, 140, 90, 200, 110, 80],
        "매도조건": ["익절", "손절", "익절", "손절", "익절", "손절"],
        "B_체결강도평균": [130.0, 95.0, 128.0, 88.0, 140.0, 101.0],
        "B_등락율각도": [22.0, 4.0, 19.0, 2.0, 25.0, 6.0],
    }).to_csv(csv_path, index=False, encoding="utf-8-sig")
    return csv_path


def _patch_source(monkeypatch, csv_path, *, ok=True, reason="backtest_result_not_ready"):
    def fake_resolve(job_id, **_kwargs):
        if not ok:
            raise ValueError(reason)
        source = SimpleNamespace(
            run_id=job_id, csv_path=str(csv_path), csv_sha256="deadbeef",
            timeframe=SimpleNamespace(value="tick"),
            strategy_buy="buy", strategy_sell="sell",
            strategy_buy_name="테스트매수", strategy_sell_name="테스트매도",
        )
        return SimpleNamespace(source=source)
    monkeypatch.setattr(api, "resolve_job_source", fake_resolve)


def test_card_returns_research_only_authority(tmp_path, monkeypatch):
    _patch_source(monkeypatch, _write_trades(tmp_path))
    payload = api.analysis_card(job_id="job-1")

    assert payload["available"] is True
    assert payload["authority"] == "research_analysis_card_only"
    assert payload["trade_count"] == 6
    assert isinstance(payload["card"], dict)
    # 승격/실전 권한 키가 카드에 실려 나가지 않는다
    assert "can_promote" not in payload["card"]


def test_incomplete_job_makes_no_card(tmp_path, monkeypatch):
    _patch_source(monkeypatch, tmp_path / "none.csv", ok=False)
    payload = api.analysis_card(job_id="job-fail")

    assert payload["available"] is False
    assert payload["reason"] == "backtest_result_not_ready"
    assert "card" not in payload


def test_second_request_is_cached(tmp_path, monkeypatch):
    _patch_source(monkeypatch, _write_trades(tmp_path))
    first = api.analysis_card(job_id="job-1")
    second = api.analysis_card(job_id="job-1")

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["card"] == first["card"]


def test_losers_are_worst_returns_first(tmp_path, monkeypatch):
    _patch_source(monkeypatch, _write_trades(tmp_path))
    payload = api.analysis_card_losers(job_id="job-1", limit=3)

    assert payload["available"] is True
    returns = [row["수익률"] for row in payload["rows"]]
    assert returns == sorted(returns)          # 최악부터
    assert returns[0] == pytest.approx(-3.1)
    assert len(payload["rows"]) == 3


def test_losers_limit_is_bounded(tmp_path, monkeypatch):
    _patch_source(monkeypatch, _write_trades(tmp_path))
    payload = api.analysis_card_losers(job_id="job-1", limit=10_000)
    assert len(payload["rows"]) == 6           # 있는 만큼만, 상한 초과 요청도 안전
