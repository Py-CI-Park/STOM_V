from __future__ import annotations

from ai_strategy_loop.dashboard.backtest_terminal_classification import (
    JsonValue,
    is_verified_no_trades_payload,
)


def test_no_trades_requires_exact_engine_receipt() -> None:
    payload: dict[str, JsonValue] = {
        "status": "error",
        "message": "backtest completed without metrics",
        "metrics": None,
        "backtest_process_diagnostics": {
            "event_count": 2,
            "last_checkpoint": "total_report_no_trades",
            "last_by_source": {"BackTest": "total_report_no_trades"},
        },
    }

    assert is_verified_no_trades_payload(2, payload) is True


def test_generic_no_metrics_message_is_not_no_trades() -> None:
    payload: dict[str, JsonValue] = {
        "status": "error",
        "message": "backtest completed without metrics",
        "metrics": None,
    }

    assert is_verified_no_trades_payload(2, payload) is False


def test_strategy_exception_overrides_no_trades_receipt() -> None:
    payload: dict[str, JsonValue] = {
        "status": "error",
        "message": "backtest completed without metrics",
        "metrics": None,
        "backtest_process_diagnostics": {
            "event_count": 3,
            "last_checkpoint": "total_report_no_trades",
            "last_by_source": {"BackEngine:0": "engine_strategy_exception"},
            "last_detail_by_source": {
                "BackEngine:0": {
                    "error": "TypeError: list indices must be integers or slices, not str"
                }
            },
        },
    }

    assert is_verified_no_trades_payload(2, payload) is False


def test_data_timeout_is_not_no_trades() -> None:
    payload: dict[str, JsonValue] = {
        "status": "error",
        "message": "engine_data_response_timeout",
        "metrics": None,
        "backtest_process_diagnostics": {
            "event_count": 2,
            "last_checkpoint": "total_report_no_trades",
        },
    }

    assert is_verified_no_trades_payload(2, payload) is False


def test_conflicting_payload_status_is_not_no_trades() -> None:
    payload: dict[str, JsonValue] = {
        "status": "success",
        "metrics": None,
        "backtest_process_diagnostics": {
            "event_count": 2,
            "last_checkpoint": "total_report_no_trades",
        },
    }

    assert is_verified_no_trades_payload(2, payload) is False
