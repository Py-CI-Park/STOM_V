"""SQ02 — versioned 지표 정의 레지스트리/projection 회귀 시험."""

from __future__ import annotations

import json

import pytest

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import metric_definitions as md


def _trade(day: int, profit: float, pct: float = 1.0,
           buy_time: str = "090000") -> dict:
    return {
        "day": day,
        "profit_krw": profit,
        "profit_pct": pct,
        "buy_time": buy_time,
        "sell_time": "091000",
        "hold_seconds": 600.0,
        "timeframe": "min",
    }


TRADES = [
    _trade(20240102, 10_000.0, 1.0),
    _trade(20240103, -4_000.0, -0.4),
    _trade(20240104, 7_500.0, 0.75),
    _trade(20240105, 0.0, 0.0),
    _trade(20240108, 12_000.0, 1.2),
    _trade(20240109, -3_000.0, -0.3),
    _trade(20240110, 5_000.0, 0.5),
]

SUMMARY = analysis.summary_metrics([dict(t) for t in TRADES])
PROJ = md.project_summary(SUMMARY)


def test_registry_covers_every_summary_key():
    missing = set(SUMMARY) - set(md.METRIC_DEFINITIONS)
    assert not missing, f"정의 없는 summary 키: {sorted(missing)}"


def test_projection_covers_all_summary_keys():
    assert set(PROJ["metrics"]) == set(md.METRIC_DEFINITIONS) - {
        "return_on_capital_pct", "mdd_on_capital_pct", "capital_krw",
        "return_krw", "annual_return_pct", "score", "gate_passed", "status",
    }
    assert PROJ["definitions_version"] == md.DEFINITIONS_VERSION


def test_projection_values_equal_summary():
    for key, entry in PROJ["metrics"].items():
        assert entry["value"] == SUMMARY[key], key


def test_projection_has_unit_and_def_version():
    for key, entry in PROJ["metrics"].items():
        assert entry["unit"] == md.METRIC_DEFINITIONS[key].unit
        assert entry["def"] == md.DEFINITIONS_VERSION


def test_populated_summary_marks_complete():
    assert PROJ["metrics"]["win_rate"]["state"] == md.STATE_COMPLETE
    assert PROJ["metrics"]["max_drawdown_pct"]["state"] == md.STATE_COMPLETE


def test_empty_trades_marks_missing_not_zero():
    empty = analysis.summary_metrics([])
    proj = md.project_summary(empty)
    assert empty["win_rate"] == 0.0  # 원본 값은 유지.
    for key, entry in proj["metrics"].items():
        assert entry["state"] == md.STATE_MISSING, key
        assert entry["reason"] in ("no_trades", "value_absent")


def test_missingness_distinguishes_empty_from_zero_profit():
    zero_profit = analysis.summary_metrics([_trade(20240102, 0.0, 0.0)])
    proj = md.project_summary(zero_profit)
    # 실제 거래가 있으므로 trade_count 는 complete, 0인 값도 complete 로 남는다.
    assert proj["metrics"]["trade_count"]["state"] == md.STATE_COMPLETE
    assert proj["metrics"]["total_profit_krw"]["state"] == md.STATE_COMPLETE
    assert proj["metrics"]["total_profit_krw"]["value"] == 0.0


def test_degraded_sharpe_when_insufficient_days():
    one_day = analysis.summary_metrics([_trade(20240102, 100.0)])
    proj = md.project_summary(one_day)
    assert proj["metrics"]["sharpe"]["state"] == md.STATE_DEGRADED
    assert proj["metrics"]["sharpe"]["reason"] == "trading_days_lt_2"


def test_degraded_calmar_when_no_drawdown():
    only_wins = analysis.summary_metrics([_trade(20240102, 100.0),
                                          _trade(20240103, 200.0)])
    proj = md.project_summary(only_wins)
    assert proj["metrics"]["calmar"]["state"] == md.STATE_DEGRADED


def test_projection_does_not_mutate_input():
    before = dict(SUMMARY)
    md.project_summary(SUMMARY)
    assert SUMMARY == before


def test_context_projection_dual_definitions():
    ctx = {
        "return_on_capital_pct": 32.71, "sum_trade_return_pct": 65.36,
        "annual_return_pct": None, "mdd_on_capital_pct": 2.16,
        "capital_krw": 3_000_000.0, "return_krw": 981_300.0,
        "calendar_days": 45, "trading_days": 30,
    }
    proj = md.project_result_context(ctx)
    m = proj["metrics"]
    # 두 수익률/두 MDD 정의가 같은 이름으로 섞이지 않는다(v5.13.2 계약).
    assert m["return_on_capital_pct"]["value"] == 32.71
    assert m["sum_trade_return_pct"]["value"] == 65.36
    assert m["mdd_on_capital_pct"]["value"] == 2.16
    assert m["annual_return_pct"]["state"] == md.STATE_MISSING


def test_context_projection_missing_capital():
    proj = md.project_result_context({"return_on_capital_pct": 10.0})
    assert proj["metrics"]["capital_krw"]["state"] == md.STATE_MISSING


def test_catalog_serializable_and_lists_states():
    cat = md.definitions_catalog()
    blob = json.dumps(cat, ensure_ascii=False)
    assert md.DEFINITIONS_VERSION in blob
    assert cat["cost_model"] == "none"
    assert set(cat["states"]) == {"complete", "missing", "degraded"}
    # 필수 도메인 커버 — 수익률/MDD/자본/비용/기간/결측.
    for key in ("sum_trade_return_pct", "return_on_capital_pct",
                "max_drawdown_pct", "mdd_on_capital_pct", "capital_krw",
                "total_profit_krw", "calendar_days", "sharpe"):
        assert key in cat["metrics"], key


def test_cost_model_is_explicitly_none():
    for defn in md.METRIC_DEFINITIONS.values():
        assert defn.cost_model == "none"


def test_registry_fingerprint_stable_and_sealed():
    fp = md.registry_fingerprint()
    assert fp == md.registry_fingerprint()  # 결정적.
    # 봉인 지문 — 정의 변경은 새 version 발행이지 in-place 수정이 아니다.
    # v1 레지스트리의 고정 지문:
    assert fp == EXPECTED_REGISTRY_SHA256


def test_annualize_definition_caveat_recorded():
    defn = md.METRIC_DEFINITIONS["annual_return_pct"]
    assert "20" in defn.formula and defn.missing_policy == "undefined"


def test_hold_seconds_is_canonical_unit():
    assert md.METRIC_DEFINITIONS["avg_hold_sec"].unit == "sec"
    assert md.METRIC_DEFINITIONS["avg_hold_min"].basis == "derived"


EXPECTED_REGISTRY_SHA256 = "d7ab1d7510fc6a177fcded2bcf8404b7e5e631996476f201888f212049ba45d9"


def test_summary_golden_regression():
    """정의별 회귀 — 고정 fixture 의 핵심 지표 golden."""
    assert SUMMARY["trade_count"] == 7
    assert SUMMARY["win_count"] == 4
    assert SUMMARY["loss_count"] == 2
    assert SUMMARY["total_profit_krw"] == pytest.approx(27_500.0)
    assert SUMMARY["sum_trade_return_pct"] == pytest.approx(2.75)
    # peak-to-trough: 10k→6k(-4k) → dd 4000; 이후 13.5k→10.5k(-3k). max 4000.
    assert SUMMARY["max_drawdown_krw"] == pytest.approx(4_000.0)
    assert SUMMARY["max_consecutive_wins"] == 1
    assert SUMMARY["max_consecutive_losses"] == 1
    assert SUMMARY["trading_days"] == 7


# ---------------------------------------------------------------------------
# API 배선 — projection 이 실제 응답에 실리는지.
# ---------------------------------------------------------------------------
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import backtest_api as api
from tests.unit.dashboard.trade_quality_fixtures import official_pair


def _manager(path, status="success", trade_count=1):
    class Manager:
        def get(self, job_id, log_tail=0):
            return {
                "available": True, "status": status,
                "csv_path": str(path),
                "metrics": {"trade_count": trade_count},
            }
    return Manager


def _client(monkeypatch, tmp_path, status="success", trade_count=1):
    header, row = official_pair()
    path = tmp_path / "src.csv"
    path.write_text(header + row, encoding="utf-8")
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", _manager(path, status, trade_count))
    app = FastAPI()
    app.include_router(api.backtest_router)
    return TestClient(app)


def test_compare_side_carries_metric_projection(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        res = client.get("/bt/compare", params={"job_a": "a1", "job_b": "b2"}).json()
    assert res["a"]["metric_projection"]["definitions_version"] == md.DEFINITIONS_VERSION
    assert res["a"]["metric_projection"]["metrics"]["trade_count"]["value"] == 1
    assert res["b"]["admitted"] is True


def test_compare_blocked_side_has_no_projection(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path, status="error") as client:
        res = client.get("/bt/compare", params={"job_a": "a1", "job_b": "b2"}).json()
    assert res["a"]["admitted"] is False
    assert res["a"]["metric_projection"] is None


def test_individual_summary_carries_projection(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        res = client.get("/bt/analysis/summary", params={"job_id": "j1"}).json()
    assert res["metric_projection"]["definitions_version"] == md.DEFINITIONS_VERSION
    assert res["definitions_version"] == md.DEFINITIONS_VERSION
    assert res["summary"]["trade_count"] == 1


def test_individual_non_summary_has_no_projection(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        res = client.get("/bt/analysis/equity", params={"job_id": "j1"}).json()
    assert "metric_projection" not in res


def test_overlay_member_carries_projection(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        res = client.get("/bt/overlay", params={"job_ids": "a1,b2"}).json()
    members = res.get("series") or []
    assert members and members[0]["metric_projection"]["definitions_version"] == md.DEFINITIONS_VERSION
