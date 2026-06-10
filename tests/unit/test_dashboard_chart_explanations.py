"""Static UX contract tests for chart explanations and engine progress."""

from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_charts_define_metric_help_strip_with_required_meanings() -> None:
    src = _read_front("chart.jsx")

    assert "function MetricHelpStrip(" in src
    for text in (
        "graded_score = weighted fitness",
        "hard gate = target score plus MDD/trade rules",
        "payoff_ratio = avg win / abs(avg loss)",
        "Calmar = return divided by MDD",
        "uptrend_r2 = cumulative equity trend fit",
        "edge_ratio = segment edge density",
        "peak_holdings=0 can mean no overlap buy/sell timing data",
    ):
        assert text in src


def test_major_charts_render_metric_help_strip() -> None:
    src = _read_front("chart.jsx")

    for fn in ("FitnessChart", "ProfitChart", "EquityOverlayChart", "BacktestDetailChart"):
        body = src[src.find(f"function {fn}(") :]
        body = body[: body.find("\nfunction ", 20) if "\nfunction " in body[20:] else len(body)]
        assert "<MetricHelpStrip" in body


def test_equity_overlay_has_twelve_winner_colors_and_subdued_nonwinners() -> None:
    src = _read_front("chart.jsx")
    palette = src[src.find("const _EQ_WINNER_COLORS"): src.find("function EquityOverlayChart")]

    assert len(re.findall(r'"#[0-9a-fA-F]{6}"', palette)) >= 12
    assert "stroke=\"rgba(255,255,255,0.10)\"" in src


def test_engine_panel_exposes_progress_eta_config_and_logs() -> None:
    src = _read_front("engine.jsx")

    for text in (
        "Overall Progress",
        "Elapsed",
        "Remaining",
        "ETA",
        "Timeout",
        "Deadline",
        "Engine Config",
        "min/tick",
        "Period",
        "bt_full_start",
        "bt_full_end",
        "bt_warm_run_timeout",
        "Recent Logs",
    ):
        assert text in src
