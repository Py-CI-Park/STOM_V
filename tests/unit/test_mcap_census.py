from __future__ import annotations

from pathlib import Path
import sqlite3

from ai_strategy_loop.labeling.mcap_census import CensusConfig, scan_mcap_census
from ai_strategy_loop.revision.mcap_bands import band_for_value, mcap_band_case_sql, validate_full_partition


def _make_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    connection.executemany('INSERT INTO moneytop VALUES (?, ?)', [
        (20250102090000, "000001;000002"), (20250102103000, "000001;000002")
    ])
    columns = '"index" INTEGER, "시가총액" REAL, "당일거래대금" REAL, "초당거래대금" REAL, "체결강도" REAL'
    for code, cap in (("000001", 2999), ("000002", 3000), ("000003", 5000), ("000004", 10000)):
        connection.execute(f'CREATE TABLE "{code}" ({columns})')
        connection.executemany(f'INSERT INTO "{code}" VALUES (?, ?, ?, ?, ?)', [
            (20250102090000, cap, 100, 10, 101),
            (20250102093000, cap, 200, 20, 102),
            (20250103090000, cap, 300, 30, 103),
        ])
    connection.execute('CREATE TABLE metadata (key TEXT)')
    connection.commit()
    connection.close()


def test_market_cap_bands_are_complete_non_overlapping_and_boundary_exact():
    assert [band_for_value(value) for value in (2999.9, 3000, 4999.9, 5000, 9999.9, 10000)] == [
        "MCAP_A_LT3000", "MCAP_B_3000_5000", "MCAP_B_3000_5000",
        "MCAP_C_5000_10000", "MCAP_C_5000_10000", "MCAP_D_GE10000",
    ]
    assert band_for_value(None) is None
    assert band_for_value(-1) is None
    counts = validate_full_partition([2999, 3000, 5000, 10000, None])
    assert counts == {
        "MCAP_A_LT3000": 1, "MCAP_B_3000_5000": 1,
        "MCAP_C_5000_10000": 1, "MCAP_D_GE10000": 1, "INVALID": 1,
    }
    assert "WHEN \"시가총액\" < 3000" in mcap_band_case_sql()


def test_census_uses_stock_table_window_not_wider_moneytop_window(tmp_path):
    path = tmp_path / "stock_tick_back.db"
    _make_db(path)
    result = scan_mcap_census(CensusConfig(str(path), "stock_tick", min_days=2, min_symbols=1))
    assert result["moneytop_scope"]["max_time"] == "103000"
    assert result["stock_table_scope"]["max_time"] == "093000"
    assert result["stock_table_scope"]["scanned_tables"] == 4
    assert result["stock_table_scope"]["skipped_tables"] == 1
    bands = {row["band_id"]: row for row in result["bands"]}
    assert all(row["rows"] == 3 for row in bands.values())
    assert all(row["days"] == 2 for row in bands.values())
    assert all(row["symbols"] == 1 for row in bands.values())
    assert all(row["verdict"] == "CENSUS_PASS" for row in bands.values())
    assert not Path(str(path) + "-wal").exists()
    assert not Path(str(path) + "-shm").exists()


def test_census_marks_band_insufficient_before_strategy_search(tmp_path):
    path = tmp_path / "stock_tick_back.db"
    _make_db(path)
    result = scan_mcap_census(CensusConfig(str(path), "stock_tick", min_days=120, min_symbols=30))
    assert {row["verdict"] for row in result["bands"]} == {"INSUFFICIENT_SAMPLE"}
    assert result["authority"] == "existing_db_development_no_oos_no_adoption"
    assert result["can_adopt"] is False
