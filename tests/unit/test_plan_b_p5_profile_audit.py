# -*- coding: utf-8 -*-
"""Regression tests for Plan B P5 official profile audit."""

from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from pathlib import Path

import pytest

from ai_strategy_loop.scripts import plan_b_p5_profile_audit as audit


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_market_db(path: Path, table: str, indices: list[str]) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute(f'CREATE TABLE "{table}" ("index" TEXT, value REAL)')
        con.executemany(f'INSERT INTO "{table}" ("index", value) VALUES (?, 1.0)', [(x,) for x in indices])
        con.commit()
    finally:
        con.close()


def _make_strategy_db(path: Path, pairs: list[dict[str, str]]) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, code TEXT)')
        con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, code TEXT)')
        con.executemany('INSERT INTO stockbuy ("index", code) VALUES (?, "")', [(p["buy"],) for p in pairs])
        con.executemany('INSERT INTO stocksell ("index", code) VALUES (?, "")', [(p["sell"],) for p in pairs])
        con.commit()
    finally:
        con.close()


def test_inspect_sqlite_index_range_filters_short_tokens(tmp_path: Path):
    db = tmp_path / "market.db"
    _make_market_db(db, "000001", ["20", "20220323090000", "20260227093000"])

    result = audit.inspect_sqlite_index_range(db, min_len=14)

    assert result["min_index"] == "20220323090000"
    assert result["max_index"] == "20260227093000"
    assert result["start_date"] == 20220323
    assert result["end_date"] == 20260227
    assert result["temporal_row_count"] == 2


def test_inspect_sqlite_index_range_rejects_invalid_extreme_datetime(tmp_path: Path):
    db = tmp_path / "market.db"
    _make_market_db(db, "000001", ["20220323090000", "99999999999999"])

    with pytest.raises(ValueError):
        audit.inspect_sqlite_index_range(db, min_len=14)


def test_official_configs_align_configured_and_effective_gate_values():
    tick_cfg, min_cfg = audit.build_official_configs(
        tick_base={"min_daily_trades": 0.3, "mdd_cap": 35, "bt_timeframe": "tick"},
        min_base={"min_daily_trades": 0.3, "mdd_cap": 35, "bt_timeframe": "min"},
        tick_range={"start_date": 20220323, "end_date": 20260227},
        min_range={"start_date": 20250407, "end_date": 20260227},
    )

    tick_profile = audit.effective_profile(tick_cfg)
    min_profile = audit.effective_profile(min_cfg)

    assert tick_profile["configured"]["min_daily_trades"] == 0.5
    assert tick_profile["effective"]["min_daily_trades"] == 0.5
    assert tick_profile["effective"]["mdd_cap"] == 35.0
    assert tick_profile["warm_backtest_config"]["engine_count"] == 64
    assert tick_profile["warm_backtest_config"]["start_date"] == 20220323
    assert tick_profile["warm_backtest_config"]["end_date"] == 20260227
    assert tick_profile["warm_backtest_config"]["start_time"] == 90000
    assert tick_profile["warm_backtest_config"]["end_time"] == 92800
    assert min_profile["warm_backtest_config"]["start_date"] == 20250407
    assert min_profile["warm_backtest_config"]["end_time"] == 151900


def test_chunk_protocol_restarts_warm_engine_every_48_pairs():
    protocol = audit.build_chunk_protocol(288)

    assert protocol["chunk_size"] == 48
    assert protocol["chunk_count"] == 6
    assert all(chunk["warm_engine_restart_before_chunk"] for chunk in protocol["chunks"])
    assert protocol["chunks"][0]["start_index_inclusive"] == 0
    assert protocol["chunks"][-1]["end_index_exclusive"] == 288


def test_chunk_protocol_rejects_out_of_policy_chunk_sizes():
    for chunk_size in (0, 39, 61):
        with pytest.raises(ValueError, match="chunk_size must be 40..60"):
            audit.build_chunk_protocol(288, chunk_size=chunk_size)


def test_run_audit_writes_configs_receipt_and_preflight_plan(tmp_path: Path):
    run_dir = tmp_path / "run"
    tick_db = tmp_path / "tick.db"
    min_db = tmp_path / "min.db"
    strategy_db = tmp_path / "strategies.db"
    _make_market_db(tick_db, "000001", ["20", "20220323090000", "20260227093000"])
    _make_market_db(min_db, "000001", ["202504070900", "202602271519"])
    pairs = [
        {"label": f"pair{i}", "buy": f"LAT_pair{i}_B", "sell": f"LAT_pair{i}_S"}
        for i in range(4)
    ]
    min_pair_rows = [
        {"label": f"min_pair{i}", "buy": f"LAT_min_pair{i}_B", "sell": f"LAT_min_pair{i}_S"}
        for i in range(4)
    ]
    _make_strategy_db(strategy_db, pairs + min_pair_rows)
    tick_config = run_dir / "tick.json"
    min_config = run_dir / "min.json"
    tick_pairs = run_dir / "pairs_tick.json"
    min_pairs = run_dir / "pairs_min.json"
    _write_json(tick_config, {"bt_timeframe": "tick", "min_daily_trades": 0.3, "mdd_cap": 35})
    _write_json(min_config, {"bt_timeframe": "min", "min_daily_trades": 0.3, "mdd_cap": 35})
    _write_json(tick_pairs, pairs)
    _write_json(min_pairs, min_pair_rows)

    receipt = audit.run_audit(Namespace(
        run_dir=str(run_dir),
        tick_config=str(tick_config),
        min_config=str(min_config),
        tick_pairs=str(tick_pairs),
        min_pairs=str(min_pairs),
        tick_db=str(tick_db),
        min_db=str(min_db),
        strategy_db=str(strategy_db),
        stamp="20990101",
    ))

    tick_official = run_dir / "smoke_config_tick_official_full_warm64_20990101.json"
    min_official = run_dir / "smoke_config_min_official_full_warm64_20990101.json"
    receipt_path = run_dir / "p5_profile_audit_official_full_warm64_20990101.json"
    preflight_plan = run_dir / "p5_preflight_plan_official_full_warm64_20990101.md"
    assert tick_official.is_file()
    assert min_official.is_file()
    assert receipt_path.is_file()
    assert preflight_plan.is_file()
    assert receipt["receipt_path"].endswith("p5_profile_audit_official_full_warm64_20990101.json")
    loaded_tick = json.loads(tick_official.read_text(encoding="utf-8"))
    assert loaded_tick["bt_full_start"] == 20220323
    assert loaded_tick["bt_warm_engine_count"] == 64
    assert receipt["gate_policy_audit"]["verdict"] == "corrected_config_to_effective_policy_floor"
    assert receipt["preflight"]["full_run_allowed_by_this_receipt"] is False
    assert receipt["strategy_db_audit"]["tables"]["stockbuy"]["missing_count"] == 0
    assert "lat_preflight_tick_official_full_warm64_20990101" in preflight_plan.read_text(encoding="utf-8")
