# -*- coding: utf-8 -*-
"""조건식 성과 원장 계약 테스트.

계약:
  1. **append-only** — 같은 후보를 다시 재면 덮어쓰지 않고 새 행을 쌓는다.
  2. 화면 기본 보기는 후보별 **최신 1행**이되, 과거 이력은 남아 있다.
  3. 알 수 없는 판정·계열은 거부한다(오타로 판정이 새로 생기는 것을 막는다).
  4. 원장이 비어 있으면 비었다고 답한다 — 후보를 지어내지 않는다.
  5. 요약은 승격(PASS) 수를 반드시 낸다 — "확정된 후보가 0" 이라는 사실이 핵심 정보다.
  6. API 는 챔피언 대비 델타를 붙이되 **원장 값을 고치지 않는다**.
"""
from __future__ import annotations

import pytest

from ai_strategy_loop.controller import strategy_ledger as sl
from ai_strategy_loop.dashboard import strategy_ledger_api as api


def _rec(candidate_id="c1", verdict="PROMISING", **kw):
    base = dict(candidate_id=candidate_id, family="exit", source="ai", lane="tick",
                verdict=verdict, recorded_at="2026-08-07T00:00:00+00:00")
    base.update(kw)
    return sl.CandidateRecord(**base)


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "ledger.db")


# ---------------------------------------------------------------------------
# 원장
# ---------------------------------------------------------------------------

def test_append_only_keeps_old_rows(db):
    sl.append(_rec("c1", "PROMISING", avg_profit_pct=0.5), db_path=db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.9), db_path=db)
    rows = sl.read_all(db_path=db)
    assert len(rows) == 2                                   # 덮어쓰지 않았다
    assert [r["verdict"] for r in rows] == ["MIXED", "PROMISING"]   # 최신 우선


def test_latest_per_candidate_picks_newest(db):
    sl.append(_rec("c1", "PROMISING", avg_profit_pct=0.5), db_path=db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.9), db_path=db)
    sl.append(_rec("c2", "REJECT"), db_path=db)
    latest = sl.latest_per_candidate(db_path=db)
    assert {r["candidate_id"] for r in latest} == {"c1", "c2"}
    c1 = next(r for r in latest if r["candidate_id"] == "c1")
    assert c1["verdict"] == "MIXED"


def test_unknown_verdict_is_refused():
    with pytest.raises(ValueError):
        _rec(verdict="GOOD")
    with pytest.raises(ValueError):
        sl.CandidateRecord(candidate_id="x", family="whatever", source="ai",
                           lane="tick", verdict="PASS", recorded_at="t")


def test_empty_ledger_is_empty_not_invented(db):
    assert sl.read_all(db_path=db) == []
    state = sl.summary(db_path=db)
    assert state["available"] is False and state["candidates"] == 0


def test_summary_reports_promoted_count(db):
    """★ '확정된 승격 후보가 0' 이라는 사실이 핵심 정보다."""
    sl.append(_rec("base", "BASELINE", avg_profit_pct=0.5), db_path=db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.9), db_path=db)
    sl.append(_rec("c2", "PROMISING", avg_profit_pct=0.6), db_path=db)
    state = sl.summary(db_path=db)
    assert state["promoted"] == 0
    assert state["verdicts"]["MIXED"] == 1
    assert state["baseline"]["candidate_id"] == "base"
    assert state["best_by_avg_profit"]["candidate_id"] == "c1"


def test_baseline_is_excluded_from_best(db):
    sl.append(_rec("base", "BASELINE", avg_profit_pct=9.9), db_path=db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.9), db_path=db)
    assert sl.summary(db_path=db)["best_by_avg_profit"]["candidate_id"] == "c1"


def test_significant_flag_round_trips(db):
    sl.append(_rec("c1", "PASS", paired_significant=True), db_path=db)
    sl.append(_rec("c2", "PROMISING", paired_significant=False), db_path=db)
    rows = {r["candidate_id"]: r for r in sl.read_all(db_path=db)}
    assert rows["c1"]["paired_significant"] == 1
    assert rows["c2"]["paired_significant"] == 0


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def test_api_adds_deltas_without_changing_stored_values(db, monkeypatch):
    monkeypatch.setattr(sl, "_DEFAULT_DB", db)
    sl.append(_rec("base", "BASELINE", avg_profit_pct=0.50, total_profit_pct=80.17,
                   cagr=56.30, mdd_pct=14.82, seed_capital=1_004_275), db_path=db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.92, total_profit_pct=71.17,
                   cagr=49.98, mdd_pct=10.48, seed_capital=1_998_220), db_path=db)

    payload = api.strategy_ledger()
    rows = {r["candidate_id"]: r for r in payload["rows"]}
    chal = rows["c1"]
    assert chal["avg_profit_pct"] == pytest.approx(0.92)          # 원값 그대로
    assert chal["delta_avg_profit_pct"] == pytest.approx(0.42)
    assert chal["delta_total_profit_pct"] == pytest.approx(71.17 - 80.17)
    assert chal["delta_mdd_pct"] == pytest.approx(10.48 - 14.82)
    assert chal["calmar"] == pytest.approx(49.98 / 10.48)
    assert chal["delta_calmar"] == pytest.approx(49.98 / 10.48 - 56.30 / 14.82)


def test_api_puts_baseline_first(db, monkeypatch):
    monkeypatch.setattr(sl, "_DEFAULT_DB", db)
    sl.append(_rec("c1", "MIXED", avg_profit_pct=0.92), db_path=db)
    sl.append(_rec("base", "BASELINE", avg_profit_pct=0.50), db_path=db)
    payload = api.strategy_ledger()
    assert payload["rows"][0]["is_baseline"] is True


def test_api_labels_every_verdict(db, monkeypatch):
    monkeypatch.setattr(sl, "_DEFAULT_DB", db)
    for i, verdict in enumerate(sl.VERDICTS):
        sl.append(_rec(f"c{i}", verdict), db_path=db)
    payload = api.strategy_ledger()
    assert set(payload["verdict_labels"]) == set(sl.VERDICTS)
    assert all(r["verdict_label"] for r in payload["rows"])


def test_api_reading_rules_warn_about_capital(db, monkeypatch):
    monkeypatch.setattr(sl, "_DEFAULT_DB", db)
    sl.append(_rec("c1", "MIXED"), db_path=db)
    rules = api.strategy_ledger()["reading_rules"]
    assert any("총수익률" in r for r in rules)
    assert any("챔피언" in r for r in rules)
