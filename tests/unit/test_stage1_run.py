"""cli.stage1_run 단위 테스트 (G005) -- 순수 헬퍼만 다룬다. 백테스트 실행 없음."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.stage1_run import (
    DEFAULT_ENGINE_COUNT,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_WARM_ENGINE_COUNT,
    DEFAULT_WARM_MIN_END_TIME,
    DEFAULT_WARM_MIN_START_TIME,
    REQUIRED_TRADE_COLUMNS,
    _ledger_record,
    _parse_cli_json,
    _reject_forbidden_write_target,
    build_command,
    build_sealed_env,
    build_warm_command,
    build_warm_config_payload,
    build_warm_pairs_payload,
)
from cli.wide_seed_trial_planner import LEDGER_EVENTS, TrialSpecV1


def _spec(lane: str = "min") -> TrialSpecV1:
    return TrialSpecV1(
        trial_id=f"trial_{lane}_deadbeefcafef00d",
        lane=lane,
        buy_name="WSEED_V1_Min_B",
        sell_name="WSEED_V1_Min_S",
        role="unified_wide",
        cell_metadata=tuple({"ordinal": i} for i in range(12)),
        dataset_scope="full_available_history",
        result_role="exploratory_full_history",
    )


# ---------------------------------------------------------------------------
# _reject_forbidden_write_target
# ---------------------------------------------------------------------------


def test_reject_forbidden_write_target_rejects_database_segment() -> None:
    with pytest.raises(ValueError):
        _reject_forbidden_write_target(r"C:\System_Trading\STOM\STOM_V.wt-dev\_database\backtest.db")


def test_reject_forbidden_write_target_allows_worktree_local_path() -> None:
    _reject_forbidden_write_target("backtest/temp/stage1_backtest.db")  # 예외 없어야 함


# ---------------------------------------------------------------------------
# build_sealed_env
# ---------------------------------------------------------------------------


def test_build_sealed_env_points_min_db_to_read_only_data_dir() -> None:
    env = build_sealed_env(
        data_dir=r"C:\System_Trading\STOM\STOM_V.wt-dev\_database",
        strategy_db="ai_strategy_loop/state/loop_strategies.db",
        writable_dir="backtest/temp",
        base_env={},
    )

    assert env["STOM_CLI_DB_STOCK_BACK_MIN"] == (
        r"C:\System_Trading\STOM\STOM_V.wt-dev\_database\stock_min_back.db"
    )
    assert env["STOM_ALLOW_MINIMAL_SETTING"] == "1"
    assert env["STOM_CLI_DB_STRATEGY"] == "ai_strategy_loop/state/loop_strategies.db"
    assert env["STOM_CLI_DB_SETTING"] == str(Path("backtest/temp/stage1_setting.db"))
    assert env["STOM_CLI_DB_BACKTEST"] == str(Path("backtest/temp/stage1_backtest.db"))


def test_build_sealed_env_rejects_writable_dir_under_database() -> None:
    with pytest.raises(ValueError):
        build_sealed_env(
            data_dir=r"C:\wt-dev\_database",
            strategy_db="ai_strategy_loop/state/loop_strategies.db",
            writable_dir=r"C:\wt-dev\_database\temp",
            base_env={},
        )


def test_build_sealed_env_rejects_strategy_db_under_database() -> None:
    with pytest.raises(ValueError):
        build_sealed_env(
            data_dir=r"C:\wt-dev\_database",
            strategy_db=r"C:\wt-dev\_database\strategy.db",
            writable_dir="backtest/temp",
            base_env={},
        )


# ---------------------------------------------------------------------------
# build_command
# ---------------------------------------------------------------------------


def test_build_command_uses_min_timeframe_and_official_entrypoint() -> None:
    cmd = build_command(_spec("min"), start_date=20250407, end_date=20260227)

    assert cmd[1].endswith("stom_backtest.py")
    assert "--buy" in cmd and "WSEED_V1_Min_B" in cmd
    assert "--sell" in cmd and "WSEED_V1_Min_S" in cmd
    assert "--start" in cmd and "20250407" in cmd
    assert "--end" in cmd and "20260227" in cmd
    assert "--timeframe" in cmd and "min" in cmd
    assert "--engines" in cmd and str(DEFAULT_ENGINE_COUNT) in cmd
    assert "--timeout" in cmd and str(DEFAULT_TIMEOUT_SEC) in cmd
    assert "--format" in cmd and "json" in cmd
    assert "--quiet" in cmd


def test_build_command_rejects_unknown_lane() -> None:
    bad_spec = _spec("min")
    object.__setattr__(bad_spec, "lane", "hour")
    with pytest.raises(ValueError):
        build_command(bad_spec, start_date=20250407, end_date=20260227)


# ---------------------------------------------------------------------------
# _ledger_record -- 원장 이벤트 shape
# ---------------------------------------------------------------------------


def test_ledger_record_executed_shape() -> None:
    spec = _spec("min")
    record = _ledger_record("executed", spec, {"csv_path": "backtest/csv/x.csv", "trade_count": 3})
    as_dict = record.to_dict()

    assert as_dict["event"] == "executed"
    assert as_dict["event"] in LEDGER_EVENTS
    assert as_dict["trial_id"] == spec.trial_id
    assert as_dict["spec_hash"] == spec.trial_id
    assert as_dict["detail"]["csv_path"] == "backtest/csv/x.csv"
    assert as_dict["timestamp"] is None  # append_ledger_entry가 채움, 여기선 미확정


def test_ledger_record_failed_shape() -> None:
    spec = _spec("min")
    record = _ledger_record("failed", spec, {"reason": "timeout"})
    as_dict = record.to_dict()

    assert as_dict["event"] == "failed"
    assert as_dict["detail"]["reason"] == "timeout"


# ---------------------------------------------------------------------------
# _parse_cli_json
# ---------------------------------------------------------------------------


def test_parse_cli_json_plain() -> None:
    assert _parse_cli_json('{"status": "success", "csv_path": "x.csv"}') == {
        "status": "success", "csv_path": "x.csv",
    }


def test_parse_cli_json_extracts_embedded_object() -> None:
    noisy = 'some warning line\n{"status": "success"}\ntrailing noise'
    assert _parse_cli_json(noisy) == {"status": "success"}


def test_parse_cli_json_empty_or_unparseable_returns_empty_dict() -> None:
    assert _parse_cli_json("") == {}
    assert _parse_cli_json("not json at all") == {}


# ---------------------------------------------------------------------------
# 상수 계약
# ---------------------------------------------------------------------------


def test_required_trade_columns_include_buy_time_and_market_cap() -> None:
    assert "매수시간" in REQUIRED_TRADE_COLUMNS
    assert "시가총액" in REQUIRED_TRADE_COLUMNS


# ---------------------------------------------------------------------------
# build_warm_pairs_payload / build_warm_config_payload / build_warm_command
# ---------------------------------------------------------------------------


def test_build_warm_pairs_payload_uses_trial_id_as_label() -> None:
    spec = _spec("min")
    pairs = build_warm_pairs_payload(spec)

    assert pairs == [{"label": spec.trial_id, "buy": "WSEED_V1_Min_B", "sell": "WSEED_V1_Min_S"}]


def test_build_warm_config_payload_opens_full_session_for_min_lane() -> None:
    config = build_warm_config_payload(start_date=20250407, end_date=20260227)

    assert config["bt_timeframe"] == "min"
    assert config["bt_full_start"] == 20250407
    assert config["bt_full_end"] == 20260227
    assert config["bt_warm_engine_count"] == DEFAULT_WARM_ENGINE_COUNT
    assert config["bt_universe_start_time"] == DEFAULT_WARM_MIN_START_TIME
    assert config["full_session_enabled"] is True
    assert config["bt_min_universe_end_time"] == DEFAULT_WARM_MIN_END_TIME
    assert config["max_generations"] == 1


def test_build_warm_config_payload_accepts_custom_engine_count_and_window() -> None:
    config = build_warm_config_payload(
        start_date=20250407, end_date=20250410, engine_count=8,
        start_time=90000, end_time=93000,
    )

    assert config["bt_warm_engine_count"] == 8
    assert config["bt_universe_start_time"] == 90000
    assert config["bt_min_universe_end_time"] == 93000


def test_build_warm_command_appends_fail_fast_flag_by_default() -> None:
    cmd = build_warm_command(
        pairs_json_path="pairs.json", config_json_path="config.json", run_id="run1",
    )

    assert cmd[-1] == "--fail-fast-timeout"
    assert "--pairs-json" in cmd and "pairs.json" in cmd
    assert "--config-json" in cmd and "config.json" in cmd
    assert "--run-id" in cmd and "run1" in cmd


def test_build_warm_command_can_omit_fail_fast_flag() -> None:
    cmd = build_warm_command(
        pairs_json_path="pairs.json", config_json_path="config.json", run_id="run1",
        fail_fast_timeout=False,
    )

    assert "--fail-fast-timeout" not in cmd
