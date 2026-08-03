"""QSP7 trade-path REST vertical slice over isolated official-like artifacts."""

from __future__ import annotations

import csv
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import trade_path_jobs, trade_path_official_api, trade_path_source
from ai_strategy_loop.dashboard.trade_path_api import trade_path_router
from ai_strategy_loop.dashboard.trade_path_jobs import TradePathCoordinator
from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger


class _FakeJobManager:
    def __init__(
        self, baseline: Path, candidate: Path, *, end_time: int | None = 90300,
        candidate_timeframe: str = "tick",
    ) -> None:
        self._paths = {"baseline": baseline, "candidate": candidate}
        self._end_time = end_time
        self._candidate_timeframe = candidate_timeframe

    def get(self, job_id: str, log_tail: int = 0):
        del log_tail
        path = self._paths.get(job_id)
        if path is None:
            return {"available": False}
        spec = {
            "buy": "매수A", "sell": "매도A",
            "start": 20250102, "end": 20250102,
            "timeframe": self._candidate_timeframe if job_id == "candidate" else "tick",
            "buy_code": "매수 = True",
            "sell_code": (
                "매도 = False\n"
                "if 보유시간 >= 30 and 수익률 <= -2:\n"
                "    매도 = True\n"
                "if 매도:\n"
                "    self.Sell()"
            ),
        }
        if self._end_time is not None:
            spec["end_time"] = self._end_time
        return {
            "available": True,
            "status": "success",
            "csv_path": str(path),
            "spec": spec,
            "metrics": {"total_profit_krw": -31_740},
        }

    def result_csv_path(self, job_id: str):
        path = self._paths.get(job_id)
        return str(path) if path is not None else None


def _market_fixture(root: Path) -> None:
    root.mkdir()
    with sqlite3.connect(root / "stock_tick_20250102.db") as connection:
        connection.execute(
            'CREATE TABLE "005930" ("index" INTEGER, "현재가" REAL, "체결강도" REAL, '
            '"초당매수수량" REAL, "초당매도수량" REAL, "매수총잔량" REAL, "매도총잔량" REAL)'
        )
        connection.executemany(
            'INSERT INTO "005930" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                (20250102090000, 1000, 100, 10, 8, 100, 90),
                (20250102090100, 970, 85, 4, 15, 70, 150),
                (20250102090200, 1020, 120, 18, 6, 160, 80),
                (20250102090300, 1040, 125, 20, 5, 180, 70),
            ],
        )
    with sqlite3.connect(root / "code_info.db") as connection:
        connection.execute('CREATE TABLE stockinfo ("index" TEXT, "종목명" TEXT)')
        connection.execute('INSERT INTO stockinfo VALUES ("005930", "삼성전자")')


def _csv(path: Path, *, sell_time: str = "20250102090100", sell_price: int = 970,
         profit: int = -31_740, reason: str = "손절") -> None:
    fields = ["종목명", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
              "매수금액", "매도금액", "수익률", "수익금", "매도조건", "추가매수시간"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"종목명": "삼성전자", "매수시간": "20250102090000",
                         "매도시간": sell_time, "보유시간": "60", "매수가": "1000",
                         "매도가": str(sell_price), "매수금액": "1000000",
                         "매도금액": str(1_000_000 + profit), "수익률": "-3.17",
                         "수익금": str(profit), "매도조건": reason, "추가매수시간": "[]"})


def test_trade_path_api_runs_analysis_counterfactual_and_official_pair(
    monkeypatch, tmp_path: Path,
) -> None:
    # Given: 공식 결과 형식 CSV 두 개와 read-only로 조회할 일일 tick DB.
    database = tmp_path / "database"
    _market_fixture(database)
    baseline, candidate = tmp_path / "baseline.csv", tmp_path / "candidate.csv"
    _csv(baseline)
    _csv(candidate, sell_time="20250102090200", sell_price=1020, profit=17_864, reason="익절")
    manager = _FakeJobManager(baseline, candidate)
    ledger_path = tmp_path / "trade-path-ledger.jsonl"
    monkeypatch.setattr(
        trade_path_jobs,
        "_COORDINATOR",
        TradePathCoordinator(ledger=TradePathLedger(ledger_path)),
    )
    monkeypatch.setattr(trade_path_source, "get_job_manager", lambda: manager)
    monkeypatch.setattr(trade_path_official_api, "get_job_manager", lambda: manager)
    monkeypatch.setenv("STOM_TRADE_PATH_DATABASE_DIR", str(database))
    monkeypatch.setenv("STOM_TRADE_PATH_CODE_INFO_DB", str(database / "code_info.db"))
    app = FastAPI()
    app.include_router(trade_path_router)
    client = TestClient(app)

    # When: preflight 후 백그라운드 분석을 시작하고 완료까지 조회한다.
    preflight = client.get("/bt/trade-path/preflight", params={"job_id": "baseline"}).json()
    started = client.post("/bt/trade-path/jobs", json={"job_id": "baseline"}).json()
    analysis_id = started["analysis_id"]
    deadline = time.time() + 5
    state = started
    while state["status"] not in ("success", "error") and time.time() < deadline:
        time.sleep(0.02)
        state = client.get(f"/bt/trade-path/jobs/{analysis_id}").json()

    # Then: 진단→자문→정본 권위가 서로 섞이지 않고 전 구간이 연결된다.
    assert preflight["available"] is True
    assert preflight["counterfactual_limit"] == "forced_liquidation_boundary"
    assert preflight["forced_liquidation_time"] == 90300
    assert preflight["boundary_source"] == "job_spec_end_time"
    assert state["status"] == "success"
    summary = client.get("/bt/trade-path/summary", params={"analysis_id": analysis_id}).json()
    assert summary["summary"]["analyzed_count"] == 1
    trades = client.get("/bt/trade-path/trades", params={"analysis_id": analysis_id}).json()
    trade_key = trades["trades"][0]["trade_key"]
    detail = client.get(
        f"/bt/trade-path/trade/{trade_key}", params={"analysis_id": analysis_id},
    ).json()
    assert detail["episode"]["market_path"][-1]["timestamp"] == 20250102090300
    sell_trace = client.get("/bt/trade-path/sell-dsl-trace", params={
        "analysis_id": analysis_id, "trade_key": trade_key,
    }).json()
    assert sell_trace["authority"] == "advisory"
    assert sell_trace["timeframe"] == "tick"
    assert sell_trace["replay"]["status"] == "supported", sell_trace
    assert sell_trace["replay"]["exit_timestamp"] == 20250102090100
    assert sell_trace["data_quality"]["bounded_at"] == 20250102090300

    advisory = client.post("/bt/trade-path/counterfactual", json={
        "analysis_id": analysis_id,
        "policy": {"name": "회복 익절", "rules": [{"rule_id": "take_profit",
                    "after_seconds": 90, "clauses": [{"field": "net_return_pct",
                    "operator": ">=", "value": 1.5}]}]},
    }).json()
    assert advisory["authority"] == "advisory"
    assert advisory["outcomes"][0]["exit_timestamp"] == 20250102090200
    proposals = client.post("/bt/trade-path/proposals", json={"analysis_id": analysis_id}).json()
    assert proposals["saved"] is False
    assert proposals["proposals"]
    report = client.get("/bt/trade-path/report", params={"analysis_id": analysis_id})
    assert report.status_code == 200
    assert report.headers["x-stom-authority"] == "diagnostic"
    assert "전체청산 이후 가격은 조회하지 않음" in report.text

    official = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "baseline", "candidate_job_id": "candidate",
    }).json()
    assert official["authority"] == "official"
    assert official["pair"]["delta_profit_krw"] == 49_604
    gate = client.post("/bt/trade-path/promotion-gate", json={
        "design_baseline_job_id": "baseline", "design_candidate_job_id": "candidate",
        "oos_baseline_job_id": "baseline", "oos_candidate_job_id": "candidate",
    }).json()
    assert gate["verdict"] == "blocked"
    assert "design_oos_period_overlap" in gate["blockers"]
    history = client.get("/bt/trade-path/history").json()
    assert {row["event"] for row in history["records"]} >= {
        "analysis_success",
        "counterfactual_completed",
        "proposals_generated",
        "official_pair_compared",
    }
    assert all(row["schema_version"] == "stom-trade-path-ledger-v1" for row in history["records"])


def test_candidate_run_attribution_round_trips_by_lane(monkeypatch, tmp_path: Path) -> None:
    # Given: 격리 코디네이터와 라우터만 올린 앱(P1-4 귀속 계약).
    ledger_path = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(
        trade_path_jobs,
        "_COORDINATOR",
        TradePathCoordinator(ledger=TradePathLedger(ledger_path)),
    )
    app = FastAPI()
    app.include_router(trade_path_router)
    client = TestClient(app)

    # When: min 후보의 설계 job 과 tick 기준선 job 을 귀속한다.
    first = client.post("/bt/trade-path/candidate-runs", json={
        "candidate_id": "delay_stop_with_breakdown", "lane": "min", "role": "design",
        "job_id": "job-min-1", "sell_name": "QSP7_min_손실방어_x", "family": "손실 방어",
    }).json()
    client.post("/bt/trade-path/candidate-runs", json={
        "candidate_id": "baseline", "lane": "tick", "role": "design",
        "job_id": "job-tick-1", "sell_name": "ResearchTest_Tick_S",
    })

    # Then: 레인 필터가 교차 오염 없이 동작하고 원장에 official 로 남는다.
    assert first["available"] is True and first["authority"] == "official"
    min_runs = client.get("/bt/trade-path/candidate-runs", params={"lane": "min"}).json()["runs"]
    assert [row["job_id"] for row in min_runs] == ["job-min-1"]
    all_runs = client.get("/bt/trade-path/candidate-runs").json()["runs"]
    assert len(all_runs) == 2
    ledger_text = ledger_path.read_text(encoding="utf-8")
    assert "candidate_run_attributed" in ledger_text

    # And: 허용되지 않은 role/lane 은 검증 단계에서 거부된다.
    bad = client.post("/bt/trade-path/candidate-runs", json={
        "candidate_id": "x", "lane": "hour", "role": "design",
        "job_id": "j", "sell_name": "s",
    })
    assert bad.status_code == 422


def test_main_app_registers_trade_path_router() -> None:
    from ai_strategy_loop.dashboard.app import create_app

    paths = {route.path for route in create_app().routes}
    assert "/bt/trade-path/preflight" in paths
    assert "/bt/trade-path/report" in paths
    assert "/bt/trade-path/sell-dsl-trace" in paths
    assert "/bt/trade-path/promotion-gate" in paths


def test_official_pair_rejects_incompatible_timeframes(
    monkeypatch, tmp_path: Path,
) -> None:
    baseline, candidate = tmp_path / "baseline.csv", tmp_path / "candidate.csv"
    _csv(baseline)
    _csv(candidate)
    manager = _FakeJobManager(baseline, candidate, candidate_timeframe="min")
    monkeypatch.setattr(trade_path_official_api, "get_job_manager", lambda: manager)
    app = FastAPI()
    app.include_router(trade_path_router)
    client = TestClient(app)

    response = client.post("/bt/trade-path/official-pair", json={
        "baseline_job_id": "baseline", "candidate_job_id": "candidate",
    }).json()

    assert response["available"] is False
    assert response["reason"] == "incompatible_official_pair"
    assert response["mismatches"] == ["timeframe"]


def test_preflight_rejects_boundary_before_any_actual_exit(
    monkeypatch, tmp_path: Path,
) -> None:
    database = tmp_path / "database"
    _market_fixture(database)
    baseline, candidate = tmp_path / "baseline.csv", tmp_path / "candidate.csv"
    _csv(baseline, sell_time="20250102151800", reason="전략종료청산")
    _csv(candidate)
    manager = _FakeJobManager(baseline, candidate, end_time=None)
    monkeypatch.setattr(trade_path_source, "get_job_manager", lambda: manager)
    monkeypatch.setenv("STOM_TRADE_PATH_DATABASE_DIR", str(database))
    monkeypatch.setenv("STOM_TRADE_PATH_CODE_INFO_DB", str(database / "code_info.db"))
    app = FastAPI()
    app.include_router(trade_path_router)
    client = TestClient(app)

    response = client.get(
        "/bt/trade-path/preflight",
        params={"job_id": "baseline", "forced_liquidation_time": 93000},
    ).json()

    assert response["available"] is False
    assert response["reason"] == "actual_exit_after_forced_liquidation"
    assert response["exit_after_boundary_count"] == 1


def test_preflight_infers_legacy_boundary_from_latest_actual_exit(
    monkeypatch, tmp_path: Path,
) -> None:
    database = tmp_path / "database"
    _market_fixture(database)
    baseline, candidate = tmp_path / "baseline.csv", tmp_path / "candidate.csv"
    _csv(baseline, sell_time="20250102151800", reason="전략종료청산")
    _csv(candidate)
    manager = _FakeJobManager(baseline, candidate, end_time=None)
    monkeypatch.setattr(trade_path_source, "get_job_manager", lambda: manager)
    monkeypatch.setenv("STOM_TRADE_PATH_DATABASE_DIR", str(database))
    monkeypatch.setenv("STOM_TRADE_PATH_CODE_INFO_DB", str(database / "code_info.db"))
    app = FastAPI()
    app.include_router(trade_path_router)
    client = TestClient(app)

    response = client.get(
        "/bt/trade-path/preflight", params={"job_id": "baseline"},
    ).json()

    assert response["available"] is True
    assert response["forced_liquidation_time"] == 151800
    assert response["boundary_source"] == "legacy_csv_latest_exit"
    assert response["boundary_confidence"] == "conservative"
