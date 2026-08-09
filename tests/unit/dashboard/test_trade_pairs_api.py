# -*- coding: utf-8 -*-
"""페이지 34 API 계약 테스트.

계약:
  1. `backtest.db` 는 **읽기 전용**으로만 연다.
  2. **진입 계열 후보는 목록에 없다** — 진입이 다르면 짝이 성립하지 않는다.
  3. 합격선이 없으면 없다고 답한다. 조용히 아무 후보나 기준선으로 삼지 않는다.
  4. limit 은 상한이 있다 — 300건을 다 뿌리면 아무도 안 읽는다.
  5. 판독 규칙은 항상 실려 나간다.
"""
from __future__ import annotations

import inspect

import pandas as pd
import pytest

from ai_strategy_loop.dashboard import trade_pairs_api as api


def _ledger_rows():
    return [
        {"candidate_id": "B::champ", "sell_name": "Tick_S_902_905", "family": "exit",
         "verdict": "BASELINE", "job_id": "j-champ", "buy_name": "Tick_B_902_905",
         "trades": 361, "avg_profit_pct": 0.67},
        {"candidate_id": "B::t240", "sell_name": "W6_S_TURN_TIME_STOP_240", "family": "exit",
         "verdict": "PROMISING", "job_id": "j-240", "buy_name": "Tick_B_902_905",
         "trades": 352, "avg_profit_pct": 0.90},
        {"candidate_id": "R::relax", "sell_name": "W7_B_RELAX_902_회전율", "family": "entry",
         "verdict": "PROMISING", "job_id": "j-relax", "buy_name": "W7_B_RELAX_902_회전율",
         "trades": 500, "avg_profit_pct": 0.60},
    ]


def _frame(profits, holds, reasons):
    n = len(profits)
    return pd.DataFrame({
        "매수시간": [f"2024030109{i:04d}" for i in range(n)],
        "종목명": [f"S{i}" for i in range(n)],
        "수익률": profits, "수익금": [p * 1000 for p in profits],
        "보유시간": holds, "매도조건": reasons,
    })


@pytest.fixture()
def wired(monkeypatch):
    monkeypatch.setattr(api.ledger, "latest_per_candidate", _ledger_rows)
    monkeypatch.setattr(api, "_tables", lambda db: ["t_champ", "t_240"])
    monkeypatch.setattr(api, "resolve_table",
                        lambda tables, buy, job: {"j-champ": "t_champ",
                                                  "j-240": "t_240"}.get(job))
    frames = {
        "t_champ": _frame([1.0, 2.0, 3.0], [400.0] * 3, ["챔피언"] * 3),
        "t_240": _frame([2.0, 1.0, 3.0], [240.0] * 3, ["시간손절", "시간손절", "트레일링"]),
    }
    monkeypatch.setattr(api, "_load", lambda t: frames[t])
    return frames


# ---------------------------------------------------------------------------
# 안전 · 목록
# ---------------------------------------------------------------------------

def test_database_is_opened_read_only():
    assert "mode=ro" in inspect.getsource(api._load)


def test_entry_family_is_excluded_from_the_picker(wired):
    """★ 진입이 다르면 짝이 성립하지 않는다 — 고를 수 없어야 한다."""
    ids = {c["candidate_id"] for c in api.trade_pairs()["candidates"]}
    assert ids == {"B::t240"}
    assert "R::relax" not in ids


def test_baseline_is_excluded_from_the_picker(wired):
    assert all(c["candidate_id"] != "B::champ" for c in api.trade_pairs()["candidates"])


def test_missing_baseline_is_reported(monkeypatch):
    monkeypatch.setattr(api.ledger, "latest_per_candidate",
                        lambda: [r for r in _ledger_rows() if r["verdict"] != "BASELINE"])
    payload = api.trade_pairs(candidate="B::t240")
    assert payload["available"] is False and "합격선" in payload["reason"]


def test_no_candidate_selected_is_reported(wired):
    payload = api.trade_pairs()
    assert payload["available"] is False and "후보" in payload["reason"]
    assert payload["candidates"]                     # 고를 목록은 준다


def test_unknown_candidate_is_reported(wired):
    payload = api.trade_pairs(candidate="없는것")
    assert payload["available"] is False and "없는것" in payload["reason"]


# ---------------------------------------------------------------------------
# 분석
# ---------------------------------------------------------------------------

def test_pairs_and_exit_reasons_are_returned(wired):
    payload = api.trade_pairs(candidate="B::t240")
    assert payload["available"] is True and payload["pairs"] == 3
    assert payload["candidate_label"] == "W6_S_TURN_TIME_STOP_240"
    assert payload["baseline_label"] == "Tick_S_902_905"
    reasons = {r["매도조건"]: r for r in payload["exit_reasons"]}
    assert reasons["시간손절"]["건수"] == 2
    assert reasons["시간손절"]["합계차이"] == pytest.approx(0.0)   # +1.0, -1.0


def test_limit_is_clamped(wired):
    assert api.trade_pairs(candidate="B::t240", limit=99999)["available"] is True
    assert api.trade_pairs(candidate="B::t240", limit=0)["available"] is True


def test_reading_rules_always_ship(wired):
    rules = api.trade_pairs(candidate="B::t240")["reading_rules"]
    assert any("청산 사유" in r for r in rules)
    assert any("진입 계열" in r for r in rules)
