"""P3 — generations 스키마 마이그레이션 단위 테스트 (멱등 ALTER + schema_version).

검증:
  - 새 DB는 처음부터 schema_version==SCHEMA_VERSION + 신규 컬럼(parent_gen,
    diff_from_parent) 보유.
  - 구버전 DB(신규 컬럼 없는 generations)를 열면 누락 컬럼만 멱등 ALTER로 추가되고
    기존 행이 보존된다(하위호환).
  - record_generation이 parent_gen/diff_from_parent를 저장하고 읽힌다.
  - 같은 DB를 두 번 열어도(멱등) 에러 없이 동작한다.

실DB/백테 미사용: tmp 경로 SQLite만 쓴다.
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.state import SCHEMA_VERSION, LoopState  # noqa: E402


def _cols(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def _make_legacy_db(path):
    """신규 컬럼(parent_gen/diff_from_parent)이 없는 구버전 generations DB를 만든다.

    mdd/profit/strategy_gist도 없는 더 오래된 형태로 만들어, 멱등 ALTER가 전부
    보강하는지(v1+v2) 본다. 기존 행 1개를 넣어 보존을 확인한다.
    """
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT,
            status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL
        );
        CREATE TABLE generations (
            run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT,
            status TEXT, score REAL, calmar REAL, uptrend_r2 REAL,
            gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER,
            created_at REAL, PRIMARY KEY (run_id, gen_no)
        );
        """
    )
    con.execute(
        "INSERT INTO runs (run_id, started_at, status) VALUES ('legacy_run', 1.0, 'complete')"
    )
    con.execute(
        "INSERT INTO generations "
        "(run_id, gen_no, buy_name, sell_name, status, score, gate_passed, "
        " trade_count, created_at) "
        "VALUES ('legacy_run', 0, 'b0', 's0', 'ok', 1.1, 1, 40, 1.0)"
    )
    con.commit()
    con.close()


class TestNewDbSchema:
    def test_new_db_has_schema_version_and_new_columns(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "new.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            assert st.get_schema_version() == SCHEMA_VERSION
            cols = _cols(st._con, "generations")
            assert "parent_gen" in cols
            assert "diff_from_parent" in cols
            # v1 컬럼도 존재.
            assert {"mdd", "profit", "strategy_gist"}.issubset(cols)
        finally:
            st.close()


class TestLegacyMigration:
    def test_legacy_db_columns_added_and_rows_preserved(self, tmp_path):
        db = str(tmp_path / "legacy.db")
        _make_legacy_db(db)
        # 마이그레이션 전: 신규 컬럼 없음.
        con = sqlite3.connect(db)
        before = _cols(con, "generations")
        con.close()
        assert "parent_gen" not in before
        assert "mdd" not in before

        # 열면 멱등 ALTER가 누락 컬럼을 전부 추가한다.
        st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        try:
            after = _cols(st._con, "generations")
            assert {"mdd", "profit", "strategy_gist", "parent_gen", "diff_from_parent"}.issubset(after)
            assert st.get_schema_version() == SCHEMA_VERSION
            # 기존 행 보존(legacy_run gen0).
            gens = st.get_generations("legacy_run")
            assert len(gens) == 1
            assert gens[0]["gen_no"] == 0
            assert gens[0]["score"] == 1.1
            # 새 컬럼은 NULL 기본.
            assert gens[0]["parent_gen"] is None
            assert gens[0]["diff_from_parent"] is None
        finally:
            st.close()

    def test_reopen_is_idempotent(self, tmp_path):
        db = str(tmp_path / "legacy2.db")
        _make_legacy_db(db)
        # 두 번 연속 열어도 ALTER 중복 에러 없이 동작.
        st1 = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        st1.close()
        st2 = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        try:
            assert st2.get_schema_version() == SCHEMA_VERSION
        finally:
            st2.close()


class TestRecordParentDiff:
    def test_record_and_read_parent_gen_and_diff(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "rec.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = st.start_run(LoopConfig(provider="openrouter"))
            # 부모 세대(루트, parent None).
            st.record_generation(
                rid, 0, buy_name="b0", sell_name="s0", status="ok",
                score=1.0, gate_passed=True, trade_count=40, mdd=15.0, profit=100000.0,
            )
            # 자식 세대(parent_gen=0 + diff).
            st.record_generation(
                rid, 1, buy_name="b1", sell_name="s1", status="ok",
                score=1.3, gate_passed=True, trade_count=38, mdd=12.0, profit=160000.0,
                parent_gen=0, diff_from_parent="gen0 대비: graded +0.3 MDD -3 거래 -2",
            )
            gens = {g["gen_no"]: g for g in st.get_generations(rid)}
        finally:
            st.close()

        assert gens[0]["parent_gen"] is None
        assert gens[1]["parent_gen"] == 0
        assert "graded +0.3" in gens[1]["diff_from_parent"]

    def test_get_all_generations_spans_multiple_runs(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "multi.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            r1 = st.start_run(LoopConfig(), run_id="r1")
            r2 = st.start_run(LoopConfig(), run_id="r2")
            st.record_generation(r1, 0, buy_name="b", sell_name="s", status="ok",
                                 score=1.0, gate_passed=True, trade_count=40)
            st.record_generation(r2, 0, buy_name="b", sell_name="s", status="ok",
                                 score=1.2, gate_passed=True, trade_count=50)
            all_gens = st.get_all_generations()
            runs = st.list_runs()
        finally:
            st.close()
        assert len(all_gens) == 2
        assert {g["run_id"] for g in all_gens} == {"r1", "r2"}
        assert len(runs) == 2
