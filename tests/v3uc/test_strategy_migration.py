"""v3uc_strategy_migration.py 단위 테스트.

mock sqlite로 V2 → V3 매핑·migrate·rollback 검증.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "v3uc_strategy_migration.py"


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("v3uc_strategy_mig", str(_SCRIPT))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _make_mock_strategy_db(path: Path, *, with_v2: bool = True, with_v3_empty: bool = True) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    if with_v2:
        cur.execute('CREATE TABLE stockbuy ("index" INTEGER, "전략코드" TEXT)')
        cur.execute('INSERT INTO stockbuy VALUES (1, "전략A")')
        cur.execute('INSERT INTO stockbuy VALUES (2, "전략B")')
        cur.execute('CREATE TABLE stocksell ("index" INTEGER, "전략코드" TEXT)')
        cur.execute('INSERT INTO stocksell VALUES (1, "매도전략1")')
    if with_v3_empty:
        cur.execute('CREATE TABLE stock_buy ("index" INTEGER, "전략코드" TEXT)')
        cur.execute('CREATE TABLE stock_sell ("index" INTEGER, "전략코드" TEXT)')
    con.commit()
    con.close()


def test_table_name_mapping(mod) -> None:
    assert mod.v2_table_name("buy") == "stockbuy"
    assert mod.v2_table_name("sell") == "stocksell"
    assert mod.v3_table_name("stock", "buy") == "stock_buy"
    assert mod.v3_table_name("stock_etf", "buy") == "stock_etf_buy"
    assert mod.v3_table_name("coin", "sell") == "coin_sell"


def test_scan_with_v2_data(mod, tmp_path, capsys) -> None:
    db = tmp_path / "strategy.db"
    _make_mock_strategy_db(db)
    rc = mod.main(["--db", str(db), "scan"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "stockbuy" in out
    assert "stock_buy" in out
    assert "마이그레이션 후보" in out


def test_migrate_dry_run_no_change(mod, tmp_path, capsys) -> None:
    db = tmp_path / "strategy.db"
    _make_mock_strategy_db(db)
    # 백업 위장
    (tmp_path / "_database_backup_test").mkdir()
    # 시뮬 db 경로를 _database/strategy.db 패턴으로 위장 — 백업 검색이 db.parent.parent에서
    real_db_dir = tmp_path / "_database"
    real_db_dir.mkdir()
    real_db = real_db_dir / "strategy.db"
    _make_mock_strategy_db(real_db)
    (tmp_path / "_database_backup_test").touch()  # 백업 directory
    rc = mod.main(["--db", str(real_db), "migrate", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY" in out or "dry_run=True" in out
    # dry-run이므로 실 변경 없음
    con = sqlite3.connect(str(real_db))
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM stock_buy')
    assert cur.fetchone()[0] == 0
    con.close()


def test_migrate_live_actual_copy(mod, tmp_path, capsys) -> None:
    real_db_dir = tmp_path / "_database"
    real_db_dir.mkdir()
    real_db = real_db_dir / "strategy.db"
    _make_mock_strategy_db(real_db)
    (tmp_path / "_database_backup_test").mkdir()
    rc = mod.main(["--db", str(real_db), "migrate"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out
    con = sqlite3.connect(str(real_db))
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM stock_buy')
    assert cur.fetchone()[0] == 2  # stockbuy 2 rows 복사
    cur.execute('SELECT COUNT(*) FROM stock_sell')
    assert cur.fetchone()[0] == 1  # stocksell 1 row 복사
    con.close()


def test_migrate_refuses_without_backup(mod, tmp_path, capsys) -> None:
    real_db_dir = tmp_path / "_database"
    real_db_dir.mkdir()
    real_db = real_db_dir / "strategy.db"
    _make_mock_strategy_db(real_db)
    # 백업 디렉토리 없음
    rc = mod.main(["--db", str(real_db), "migrate"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "백업 없음" in out
