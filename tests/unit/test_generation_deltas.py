"""P1b — 부모 대비 숫자 델타 영속화 단위 테스트 (state.py + loop.py).

검증(백테/루프 실행 없음, tmp DB):
  - SCHEMA_VERSION >= 8(P1b 도입), generations에 d_graded..d_uptrend_r2 7컬럼 존재.
  - _build_parent_diff_and_deltas: 부모 1회 조회로 NL diff + 숫자 델타(정확값) 반환.
  - record_generation: d_* 전달 시 행에 숫자 저장; 부모 없는 세대는 d_* NULL.
  - diff_from_parent NL 문자열이 기존 포맷과 byte-identical(회귀 가드).
  - 구버전 DB(d_* 컬럼 없음) 열면 마이그레이션으로 컬럼 추가됨.
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402

_DELTA_COLS = (
    "d_graded", "d_mdd", "d_trades", "d_profit",
    "d_daily_trades", "d_calmar", "d_uptrend_r2",
)


def _cols(st, table="generations"):
    return {row[1] for row in st._con.execute(f"PRAGMA table_info({table})")}


def _row(st, rid, gen_no):
    r = st._con.execute(
        "SELECT * FROM generations WHERE run_id = ? AND gen_no = ?", (rid, gen_no)
    ).fetchone()
    return dict(r) if r is not None else None


class TestSchema:
    def test_schema_version_at_least_8(self):
        # P1b는 v8에서 d_* 델타 컬럼을 도입했다. 이후 마이그레이션(P2a v9 등)으로
        #   버전이 올라가도 d_* 컬럼 계약은 유지된다 — 정확 버전 대신 하한으로 가드한다.
        assert S.SCHEMA_VERSION >= 8

    def test_delta_columns_present(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "sv.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            cols = _cols(st)
            for c in _DELTA_COLS:
                assert c in cols, f"누락 컬럼: {c}"
            assert st.get_schema_version() == S.SCHEMA_VERSION
            assert st.get_schema_version() >= 8
        finally:
            st.close()


class TestBuildDeltas:
    def test_deltas_none_when_no_parent(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "nd.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            st.start_run(LoopConfig(), run_id="r")
            nl, deltas = L._build_parent_diff_and_deltas(
                st, "r", None,
                graded=1.0, mdd=10.0, trade_count=40, profit=1.0,
                daily_avg_trades=1.0, calmar=2.0, uptrend_r2=0.5,
            )
            assert nl is None
            assert deltas is None
        finally:
            st.close()

    def test_deltas_exact_values(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "ev.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "ev"
            st.start_run(LoopConfig(), run_id=rid)
            # 부모(gen0) — 시드급 기준값.
            st.record_generation(
                rid, 0, buy_name="b0", sell_name="s0", status="ok",
                score=2.7703, mdd=17.76, trade_count=307, profit=8266552.0,
                daily_avg_trades=0.42, calmar=3.19, uptrend_r2=0.90,
                gate_passed=True,
            )
            # 자식(gen1, parent_gen=0) — 부모 대비 델타를 계산할 현재 지표.
            nl, deltas = L._build_parent_diff_and_deltas(
                st, rid, 0,
                graded=1.96, mdd=18.23, trade_count=350, profit=4820000.0,
                daily_avg_trades=0.55, calmar=1.82, uptrend_r2=0.725,
            )
            assert nl is not None
            assert deltas is not None
            # 자식 mdd 18.23 - 부모 17.76 = +0.47 (부동소수 근사).
            assert abs(deltas["d_mdd"] - 0.47) < 1e-6
            assert abs(deltas["d_graded"] - (1.96 - 2.7703)) < 1e-9
            assert abs(deltas["d_trades"] - (350 - 307)) < 1e-9
            assert abs(deltas["d_profit"] - (4820000.0 - 8266552.0)) < 1e-3
            assert abs(deltas["d_daily_trades"] - (0.55 - 0.42)) < 1e-9
            assert abs(deltas["d_calmar"] - (1.82 - 3.19)) < 1e-9
            assert abs(deltas["d_uptrend_r2"] - (0.725 - 0.90)) < 1e-9
        finally:
            st.close()


class TestRecordPersistence:
    def test_record_stores_numeric_deltas(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "rp.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "rp"
            st.start_run(LoopConfig(), run_id=rid)
            st.record_generation(
                rid, 1, buy_name="b1", sell_name="s1", status="ok",
                score=1.96, parent_gen=0,
                d_graded=-0.81, d_mdd=0.47, d_trades=43.0, d_profit=-3446552.0,
                d_daily_trades=0.13, d_calmar=-1.37, d_uptrend_r2=-0.175,
            )
            row = _row(st, rid, 1)
            assert row is not None
            assert abs(row["d_graded"] - (-0.81)) < 1e-9
            assert abs(row["d_mdd"] - 0.47) < 1e-9
            assert abs(row["d_trades"] - 43.0) < 1e-9
            assert abs(row["d_profit"] - (-3446552.0)) < 1e-3
            assert abs(row["d_daily_trades"] - 0.13) < 1e-9
            assert abs(row["d_calmar"] - (-1.37)) < 1e-9
            assert abs(row["d_uptrend_r2"] - (-0.175)) < 1e-9
        finally:
            st.close()

    def test_parentless_generation_has_null_deltas(self, tmp_path):
        st = LoopState(db_path=str(tmp_path / "nn.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "nn"
            st.start_run(LoopConfig(), run_id=rid)
            # 부모 없는 세대(시드/gen0): d_* 미전달 → NULL이어야 한다(하위호환).
            st.record_generation(
                rid, 0, buy_name="b0", sell_name="s0", status="ok",
                score=2.77, parent_gen=None,
            )
            row = _row(st, rid, 0)
            assert row is not None
            for c in _DELTA_COLS:
                assert row[c] is None, f"{c} 는 부모 없으면 NULL이어야 한다 (got {row[c]!r})"
        finally:
            st.close()


class TestNLByteIdentical:
    def test_nl_format_unchanged(self, tmp_path):
        """diff_from_parent NL 문자열이 기존 포맷과 정확히 동일(byte-identical 회귀 가드)."""
        st = LoopState(db_path=str(tmp_path / "nl.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "nl"
            st.start_run(LoopConfig(), run_id=rid)
            # 부모 gen1: score=1.4, mdd=11.0, trade_count=38, profit=160000.0.
            st.record_generation(
                rid, 1, buy_name="b1", sell_name="s1", status="ok",
                score=1.4, mdd=11.0, trade_count=38, profit=160000.0,
                daily_avg_trades=0.0, calmar=0.0, uptrend_r2=0.0,
            )
            # 자식 graded 1.6 / mdd 9.0 / 거래 36 / 손익 200000 — 알려진 입력.
            nl, _ = L._build_parent_diff_and_deltas(
                st, rid, 1,
                graded=1.6, mdd=9.0, trade_count=36, profit=200000.0,
                daily_avg_trades=0.0, calmar=0.0, uptrend_r2=0.0,
            )
            # 기존 _format ( {sign}{d:.4g} ) 로 산출되는 정확 문자열.
            assert nl == "gen1 대비: graded +0.2 MDD -2 거래 -2 손익 +4e+04"
        finally:
            st.close()

    def test_build_parent_diff_matches_combined(self, tmp_path):
        """기존 _build_parent_diff(단독)와 통합 함수의 NL이 동일해야 한다."""
        st = LoopState(db_path=str(tmp_path / "cmp.db"), snapshot_dir=str(tmp_path / "s"))
        try:
            rid = "cmp"
            st.start_run(LoopConfig(), run_id=rid)
            st.record_generation(
                rid, 0, buy_name="b0", sell_name="s0", status="ok",
                score=1.0, mdd=15.0, trade_count=40, profit=100000.0,
            )
            old_nl = L._build_parent_diff(st, rid, 0, 1.6, 9.0, 36, 200000.0)
            new_nl, _ = L._build_parent_diff_and_deltas(
                st, rid, 0,
                graded=1.6, mdd=9.0, trade_count=36, profit=200000.0,
                daily_avg_trades=0.0, calmar=0.0, uptrend_r2=0.0,
            )
            assert old_nl == new_nl
        finally:
            st.close()


class TestMigration:
    def test_legacy_db_gains_delta_columns(self, tmp_path):
        """구버전 DB(d_* 컬럼 없는 generations)를 열면 마이그레이션으로 컬럼이 추가된다."""
        db = str(tmp_path / "legacy.db")
        # v7 이전 형태에 가까운 최소 generations 테이블(델타 컬럼 없음)을 직접 생성.
        con = sqlite3.connect(db)
        con.execute(
            "CREATE TABLE generations ("
            " run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT, status TEXT,"
            " score REAL, created_at REAL, PRIMARY KEY (run_id, gen_no))"
        )
        con.commit()
        con.close()
        # 마이그레이션 전: 델타 컬럼 부재 확인.
        con = sqlite3.connect(db)
        pre = {r[1] for r in con.execute("PRAGMA table_info(generations)")}
        con.close()
        for c in _DELTA_COLS:
            assert c not in pre

        # LoopState 열기 → _migrate_schema가 멱등 ADD COLUMN 한다.
        st = LoopState(db_path=db, snapshot_dir=str(tmp_path / "s"))
        try:
            cols = _cols(st)
            for c in _DELTA_COLS:
                assert c in cols, f"마이그레이션 후 {c} 컬럼이 있어야 한다"
            assert st.get_schema_version() == S.SCHEMA_VERSION
            assert st.get_schema_version() >= 8
        finally:
            st.close()
