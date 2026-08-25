from __future__ import annotations

import json

from ai_strategy_loop.dashboard.backtest_cli_json import parse_cli_json


def test_pretty_cli_json_is_recovered_after_runtime_warnings() -> None:
    # Given
    payload = {
        "status": "error",
        "message": "backtest completed without metrics",
        "metrics": None,
        "backtest_process_diagnostics": {
            "event_count": 204,
            "last_checkpoint": "total_report_no_trades",
            "last_by_source": {"BackTest": "total_report_no_trades"},
        },
    }
    stdout = "\n".join(
        (
            "2026-08-26 | WARNING | Setting : minimal mode",
            '[CLI_DIAG] {"source":"BackTest","checkpoint":"completed"}',
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
    )

    # When
    parsed = parse_cli_json(stdout)

    # Then
    assert parsed == payload
