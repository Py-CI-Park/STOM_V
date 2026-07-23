"""LoopState readonly=True 모드 테스트 (PR3 — 대시보드 read 경로 안전성).

readonly=True 계약:
  - mode=ro URI 로만 열어 보호된 loop_runs.db 에 어떤 쓰기도 하지 않는다.
  - 쓰기 시도(record_generation 등)는 sqlite 가 거부한다(읽기 전용 강제).
  - 스키마 마이그레이션/디렉토리 생성을 스킵한다(스키마 미변경).
  - 읽기(get_generations/get_run/list_runs)는 정상 동작한다.
기본(readonly=False)은 종전 동작 불변(WAL/마이그레이션 수행).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


def _seed(db: Path) -> None:
    """일반(쓰기) LoopState 로 run+세대 1줄을 영속한다."""
    st = LoopState(db_path=str(db), snapshot_dir=str(db.parent / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id="runRO")
        st.record_generation("runRO", 0, buy_name="b", sell_name="s", status="ok",
                             score=1.0, gate_passed=True, csv_path=None, trade_count=42)
    finally:
        st.close()


def test_readonly_reads_existing_data(tmp_path: Path):
    db = tmp_path / "loop_runs.db"
    _seed(db)
    st = LoopState(db_path=str(db), readonly=True)
    try:
        assert st.readonly is True
        gens = st.get_generations("runRO")
        assert len(gens) == 1
        assert gens[0]["trade_count"] == 42
        assert st.get_run("runRO") is not None
        assert any(r["run_id"] == "runRO" for r in st.list_runs())
    finally:
        st.close()


def test_readonly_write_attempt_fails(tmp_path: Path):
    db = tmp_path / "loop_runs.db"
    _seed(db)
    st = LoopState(db_path=str(db), readonly=True)
    try:
        # 읽기 전용 DB 에 쓰기 시도 → sqlite 가 거부(OperationalError).
        with pytest.raises(sqlite3.OperationalError):
            st.record_generation("runRO", 1, buy_name="b2", sell_name="s2",
                                 status="ok", score=2.0, gate_passed=False,
                                 csv_path=None, trade_count=7)
    finally:
        st.close()


def test_readonly_does_not_mutate_schema_or_create_files(tmp_path: Path):
    db = tmp_path / "loop_runs.db"
    _seed(db)
    # 쓰기 모드가 만든 WAL/스냅샷을 정리해 readonly 가 새로 만들지 않음을 본다.
    schema_before = _schema_fingerprint(db)

    snaps_dir = tmp_path / "ro_snaps"        # 존재하지 않는 스냅샷 디렉토리.
    st = LoopState(db_path=str(db), snapshot_dir=str(snaps_dir), readonly=True)
    try:
        st.get_generations("runRO")          # 읽기만.
    finally:
        st.close()

    # readonly 는 스냅샷 디렉토리를 mkdir 하지 않는다(쓰기 경로 스킵).
    assert not snaps_dir.exists()
    # 스키마(테이블/컬럼)는 그대로(마이그레이션 미수행).
    assert _schema_fingerprint(db) == schema_before


def test_readonly_missing_db_raises_on_open(tmp_path: Path):
    # mode=ro 는 없는 파일을 만들지 않는다 — 열기 시점에 OperationalError.
    #   (호출측 backtest_api 는 try/except 로 흡수해 빈 목록/None 을 돌린다.)
    missing = tmp_path / "nope.db"
    with pytest.raises(sqlite3.OperationalError):
        LoopState(db_path=str(missing), readonly=True)
    assert not missing.exists()              # 열기 실패가 파일을 만들지 않음.


def test_default_mode_unchanged(tmp_path: Path):
    # readonly 미지정(기본 False) → 종전대로 쓰기 가능 + 스키마 마이그레이션 수행.
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db))
    try:
        assert st.readonly is False
        assert st.get_schema_version() >= 1   # 마이그레이션이 버전을 기록했다.
        st.start_run(LoopConfig(), run_id="rw")
        st.record_generation("rw", 0, buy_name="b", sell_name="s", status="ok",
                             score=1.0, gate_passed=True, csv_path=None, trade_count=3)
        assert st.get_generations("rw")[0]["trade_count"] == 3
    finally:
        st.close()


def _schema_fingerprint(db: Path) -> set:
    """generations 테이블 컬럼 집합(스키마 변경 감지용)."""
    con = sqlite3.connect(str(db))
    try:
        cols = {row[1] for row in con.execute("PRAGMA table_info(generations)")}
    finally:
        con.close()
    return cols


def test_dashboard_read_helpers_never_open_default_writable_loop_state() -> None:
    app_source = (
        Path(PROJECT_ROOT)
        / "ai_strategy_loop"
        / "dashboard"
        / "app.py"
    ).read_text(encoding="utf-8")
    assert "LoopState()" not in app_source
    assert "LoopState(readonly=True)" in app_source
