"""v3uc_db_compatibility_check.py 단위 테스트.

mock sqlite로 PK 진단·자동 추가·extra DB 분석 함수 검증.
실 _database/는 건드리지 않는다.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "v3uc_db_compatibility_check.py"


pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("v3uc_db_compat", str(_SCRIPT))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _make_mock_db_no_pk(path: Path) -> None:
    """V2 시절 schema 시뮬 — PK 없는 종목 테이블."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE "025950" ("index" INTEGER, "현재가" REAL, "시가" REAL)')
    cur.execute('INSERT INTO "025950" VALUES (202504071234, 10000.0, 9950.0)')
    cur.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    cur.execute('INSERT INTO moneytop VALUES (1, "test")')
    con.commit()
    con.close()


def _make_mock_db_with_pk(path: Path) -> None:
    """V3.08+ schema 시뮬 — PK 있음."""
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE "025950" ("index" INTEGER PRIMARY KEY, "현재가" REAL)')
    cur.execute('INSERT INTO "025950" VALUES (202504071234, 10000.0)')
    con.commit()
    con.close()


def test_table_has_pk_detection(mod, tmp_path) -> None:
    no_pk = tmp_path / "stock_min_20990101.db"
    with_pk = tmp_path / "stock_min_20990102.db"
    _make_mock_db_no_pk(no_pk)
    _make_mock_db_with_pk(with_pk)

    con1 = sqlite3.connect(str(no_pk))
    assert mod.table_has_pk(con1, "025950") is False
    con1.close()

    con2 = sqlite3.connect(str(with_pk))
    assert mod.table_has_pk(con2, "025950") is True
    con2.close()


def test_scan_db_counts(mod, tmp_path) -> None:
    db = tmp_path / "stock_min_20990101.db"
    _make_mock_db_no_pk(db)
    result = mod.scan_db(db)
    assert result["table_count"] == 2  # 025950 + moneytop
    assert result["tables_without_pk"] == 2
    assert result["tables_with_pk"] == 0
    assert "025950" in result["missing_pk_examples"]


def test_is_stock_data_db_classification(mod, tmp_path) -> None:
    stock = tmp_path / "stock_min_20990101.db"
    coin = tmp_path / "coin_tick_20990101.db"
    extra = tmp_path / "setting.db"
    backtest = tmp_path / "backtest.db"
    for p in (stock, coin, extra, backtest):
        p.touch()
    assert mod.is_stock_data_db(stock) is True
    assert mod.is_stock_data_db(coin) is True
    assert mod.is_stock_data_db(extra) is False
    assert mod.is_stock_data_db(backtest) is False


def test_add_pk_to_db_dry_run(mod, tmp_path) -> None:
    db = tmp_path / "stock_min_20990101.db"
    _make_mock_db_no_pk(db)
    result = mod.add_pk_to_db(db, dry_run=True)
    assert result["processed"] == 1  # 025950만 처리 (moneytop은 skip)
    assert result["dry_run"] is True
    # dry-run이므로 실제 변경 없음 — 재스캔 시 여전히 PK 없음
    rescan = mod.scan_db(db)
    assert rescan["tables_without_pk"] == 2  # 025950 + moneytop


def test_add_pk_to_db_live(mod, tmp_path) -> None:
    db = tmp_path / "stock_min_20990101.db"
    _make_mock_db_no_pk(db)
    result = mod.add_pk_to_db(db, dry_run=False)
    assert result["processed"] == 1
    assert result["errors"] == []
    # live 후 재스캔 — 025950은 PK 있음, moneytop은 skip되어 여전히 없음
    rescan = mod.scan_db(db)
    assert rescan["tables_with_pk"] == 1
    assert rescan["tables_without_pk"] == 1
    # 데이터 보존 검증
    con = sqlite3.connect(str(db))
    rows = list(con.execute('SELECT * FROM "025950"'))
    assert len(rows) == 1
    assert rows[0][0] == 202504071234
    con.close()


def test_analyze_extra_db(mod, tmp_path) -> None:
    db = tmp_path / "setting.db"
    con = sqlite3.connect(str(db))
    con.execute('CREATE TABLE account ("index" INTEGER, "access_key" TEXT, "secret_key" TEXT)')
    con.execute('CREATE TABLE tele ("index" INTEGER PRIMARY KEY, "bot_token" TEXT, "chatingid" TEXT)')
    con.commit()
    con.close()
    summary = mod.analyze_extra_db(db)
    assert "account" in summary["tables"]
    assert "tele" in summary["tables"]
    assert summary["tables"]["account"]["has_pk"] is False
    assert summary["tables"]["tele"]["has_pk"] is True


def test_main_scan_command_exits_with_warn_on_missing_pk(mod, tmp_path, capsys) -> None:
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    _make_mock_db_no_pk(db_dir / "stock_min_20990101.db")
    exit_code = mod.main(["--db-dir", str(db_dir), "scan"])
    captured = capsys.readouterr()
    assert exit_code == 1  # warn 시 1 반환
    assert "WARN" in captured.out
