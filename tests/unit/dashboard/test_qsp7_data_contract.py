"""QSP7 official artifact and data-contract regression tests."""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from backtest.back_static import (
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
)
from ai_strategy_loop.dashboard.backtest_jobs import (
    BacktestJobSpec,
    default_command_builder,
)
from ai_strategy_loop.dashboard.backtest_api import BacktestRunPayload
from ai_strategy_loop.dashboard.trade_contract import build_trade_artifact_contract
from ai_strategy_loop.dashboard import trade_contract_api
from ai_strategy_loop.dashboard.trade_path_api import trade_path_router
from fastapi.encoders import jsonable_encoder


BASE_COLUMNS = (
    "종목명", "시가총액", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
    "매수금액", "매도금액", "수익률", "수익금", "수익금합계", "매도조건", "추가매수시간",
)


def test_official_job_preserves_intraday_boundary_in_command() -> None:
    """Given a declared session, the official command must preserve both times."""
    spec = BacktestJobSpec(
        buy="매수A",
        sell="매도A",
        start=20250102,
        end=20250131,
        timeframe="tick",
        start_time=90000,
        end_time=93000,
    )

    command = default_command_builder(spec)

    assert command[command.index("--start-time") + 1] == "90000"
    assert command[command.index("--end-time") + 1] == "93000"


def test_backtest_request_accepts_explicit_tick_session_boundary() -> None:
    """Given a tick request, the validated payload must retain its session."""
    payload = BacktestRunPayload.model_validate({
        "buy": "매수A",
        "sell": "매도A",
        "start": 20250102,
        "end": 20250131,
        "timeframe": "tick",
        "start_time": 90000,
        "end_time": 93000,
    })

    assert payload.start_time == 90000
    assert payload.end_time == 93000


def test_contract_distinguishes_missing_zero_only_and_available_columns(
    tmp_path: Path,
) -> None:
    """Given a modern CSV, the profile must not confuse zero-only with missing."""
    csv_path = tmp_path / "official.csv"
    columns = [
        *BASE_COLUMNS,
        *TRADE_RESULT_B_COLUMNS,
        *TRADE_RESULT_S_COLUMNS,
        *TRADE_RESULT_R_COLUMNS,
    ]
    row = {column: "0" for column in columns}
    row.update({
        "종목명": "삼성전자",
        "매수시간": "20250102090000",
        "매도시간": "20250102090100",
        "B_현재가": "1000",
        "S_현재가": "970",
        "R_MFE": "1.5",
    })
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)

    contract = build_trade_artifact_contract(
        csv_path=csv_path,
        job_id="job-1",
        spec={
            "buy": "매수A",
            "sell": "매도A",
            "buy_code": "매수 = True",
            "sell_code": "매도 = False",
            "timeframe": "tick",
            "start_time": 90000,
            "end_time": 93000,
        },
    )
    payload = asdict(contract)

    assert payload["artifact"]["schema_variant"] == "modern_54"
    assert payload["artifact"]["row_count"] == 1
    assert len(payload["artifact"]["sha256"]) == 64
    assert payload["boundary"] == {
        "start_time": 90000,
        "forced_liquidation_time": 93000,
        "source": "job_spec_end_time",
        "confidence": "official",
    }
    availability = {row["name"]: row["status"] for row in payload["columns"]}
    assert availability["B_현재가"] == "available"
    assert availability["B_분봉시가"] == "zero_only"
    assert availability["B_RSI"] == "zero_only"
    assert payload["cost_policy"]["round_trip_rate_pct"] == 0.21
    assert payload["strategy"]["buy_sha256"] != payload["strategy"]["sell_sha256"]


def test_data_contract_api_exposes_profile_for_completed_job(
    monkeypatch, tmp_path: Path,
) -> None:
    """Given a completed job, the endpoint must expose its immutable profile."""
    csv_path = tmp_path / "official.csv"
    csv_path.write_text(
        "종목명,매수시간,매도시간,B_현재가\n삼성전자,20250102090000,20250102090100,1000\n",
        encoding="utf-8-sig",
    )

    class FakeManager:
        def get(self, job_id: str, log_tail: int = 0):
            assert job_id == "job-1"
            assert log_tail == 0
            return {
                "available": True,
                "status": "success",
                "csv_path": str(csv_path),
                "spec": {"timeframe": "tick", "start_time": 90000, "end_time": 93000},
            }

    monkeypatch.setattr(trade_contract_api, "get_job_manager", lambda: FakeManager())

    response = jsonable_encoder(trade_contract_api.data_contract(job_id="job-1"))

    assert response["available"] is True
    assert response["contract"]["artifact"]["row_count"] == 1
    assert response["contract"]["boundary"]["forced_liquidation_time"] == 93000


def test_legacy_contract_uses_latest_actual_exit_as_conservative_boundary(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "legacy.csv"
    csv_path.write_text(
        "종목명,매수시간,매도시간\n삼성전자,202501020900,202501021519\n",
        encoding="utf-8-sig",
    )

    contract = build_trade_artifact_contract(
        csv_path=csv_path, job_id="legacy", spec={"timeframe": "min"},
    )

    assert contract.boundary.forced_liquidation_time == 151900
    assert contract.boundary.source == "legacy_csv_latest_exit"
    assert contract.boundary.confidence == "conservative"


def test_trade_path_router_registers_data_contract_page_api() -> None:
    paths = {route.path for route in trade_path_router.routes}

    assert "/bt/trade-path/data-contract" in paths
