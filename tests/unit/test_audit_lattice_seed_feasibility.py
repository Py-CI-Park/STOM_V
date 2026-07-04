# -*- coding: utf-8 -*-
"""Tests for lattice sample feasibility audit."""

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "ai_strategy_loop" / "scripts" / "audit_lattice_seed_feasibility.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_lattice_seed_feasibility", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_audit_links_no_trade_result_to_gate_summary():
    mod = _load_module()
    seeds = [
        {
            "condition_id": "lattice_v1:tick_0900_small_low:momentum_breakout",
            "cell_id": "tick_0900_small_low",
            "family": "momentum_breakout",
            "params": {"high_mult": 0.995, "take_profit": 2.0, "stop_loss": 2.0},
        }
    ]
    rows = [
        {
            "buy_name": "LAT_lattice_v1:tick_0900_small_low:momentum_breakout_B",
            "status": "error",
            "reason": (
                "[lattice_v1:tick_0900_small_low:momentum_breakout] "
                "backtest failed: warm backtest non-success: status=success csv=no"
            ),
            "trade_count": 0,
        }
    ]

    audit = mod.build_audit(seeds, rows)

    assert audit["sample_count"] == 1
    assert audit["status_counts"] == {"no_trades": 1}
    sample = audit["samples"][0]
    assert sample["condition_id"] == "lattice_v1:tick_0900_small_low:momentum_breakout"
    assert sample["runtime_status"] == "no_trades"
    assert [gate["gate"] for gate in sample["gates"]] == [
        "universe_filter",
        "time_window",
        "market_cap_tier",
        "regime_filter",
        "family_trigger",
        "exit_rule",
    ]
    assert audit["decision"]["threshold_relaxation_needed"] is True
    assert "family_trigger" in audit["decision"]["primary_relaxation_targets"]
