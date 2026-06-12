"""tests/unit/test_db_audit.py — db_audit.py 단위 테스트 (합성 DB만 사용).

실 DB에 접근하지 않는다. tmp_path SQLite로 모든 시나리오를 재현한다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List

import pytest

from ai_strategy_loop.scripts.db_audit import (
    audit_day_coverage,
    audit_runs_db,
    load_tick_days,
)


# ---------------------------------------------------------------------------
# audit_day_coverage
# ---------------------------------------------------------------------------

class TestAuditDayCoverage:
    def test_empty_list(self):
        result = audit_day_coverage([], today="20260101")
        assert result["n_days"] == 0
        assert result["first"] is None
        assert result["last"] is None
        assert result["freshness_days"] is None
        assert result["weekday_gaps"]["total"] == 0

    def test_continuous_weekdays_no_gap(self):
        # 2026-06-08(월)~2026-06-12(금) 5일 연속 평일
        days = ["20260608", "20260609", "20260610", "20260611", "20260612"]
        result = audit_day_coverage(days, today="20260612")
        assert result["n_days"] == 5
        assert result["first"] == "20260608"
        assert result["last"] == "20260612"
        assert result["freshness_days"] == 0
        assert result["weekday_gaps"]["total"] == 0

    def test_one_missing_weekday_detected(self):
        # 2026-06-08(월), 2026-06-10(수), 2026-06-11(목) — 화(09) 빠짐
        days = ["20260608", "20260610", "20260611"]
        result = audit_day_coverage(days, today="20260620")
        assert result["weekday_gaps"]["total"] == 1
        assert "20260609" in result["weekday_gaps"]["sample"]

    def test_freshness_days_calculated_correctly(self):
        # last = 20260601, today = 20260610 → 9일 전
        days = ["20260601"]
        result = audit_day_coverage(days, today="20260610")
        assert result["freshness_days"] == 9

    def test_weekend_not_counted_as_gap(self):
        # 2026-06-05(금) → 2026-06-08(월) : 토·일 사이 — 갭 없어야
        days = ["20260605", "20260608"]
        result = audit_day_coverage(days, today="20260608")
        assert result["weekday_gaps"]["total"] == 0

    def test_sample_capped_at_10(self):
        # 20개 갭이 있어도 sample은 최대 10개
        # 2026-01-05(월)~2026-01-06(화) 사이에 대량 갭 만들기
        # 2026-01-02(금)와 2026-01-30(금) 만 포함 → 사이 평일 다 빠짐
        days = ["20260102", "20260130"]
        result = audit_day_coverage(days, today="20260130")
        assert result["weekday_gaps"]["total"] > 10
        assert len(result["weekday_gaps"]["sample"]) == 10

    def test_duplicates_handled(self):
        days = ["20260608", "20260608", "20260609"]
        result = audit_day_coverage(days, today="20260609")
        assert result["n_days"] == 2

    def test_note_present(self):
        result = audit_day_coverage(["20260601"], today="20260601")
        assert "휴장일" in result["note"]


# ---------------------------------------------------------------------------
# load_tick_days
# ---------------------------------------------------------------------------

class TestLoadTickDays:
    def _make_moneytop(self, tmp_path: Path, indices: List[int]) -> sqlite3.Connection:
        """소형 moneytop 모사 테이블 생성."""
        db_path = tmp_path / "tick_test.db"
        con = sqlite3.connect(str(db_path))
        con.execute(
            "CREATE TABLE moneytop ([index] INTEGER, 거래대금순위 TEXT)"
        )
        con.executemany(
            "INSERT INTO moneytop VALUES (?, ?)",
            [(idx, "000660;005930") for idx in indices],
        )
        con.commit()
        return con

    def test_basic_day_extraction(self, tmp_path):
        # 20220323 090000 ~ 090002 → 일자 20220323 하나
        indices = [20220323090000, 20220323090001, 20220323090002]
        con = self._make_moneytop(tmp_path, indices)
        days = load_tick_days(con)
        con.close()
        assert days == ["20220323"]

    def test_multiple_days(self, tmp_path):
        indices = [
            20220323090000,
            20220324090000,
            20220325090000,
        ]
        con = self._make_moneytop(tmp_path, indices)
        days = load_tick_days(con)
        con.close()
        assert days == ["20220323", "20220324", "20220325"]

    def test_deduplication(self, tmp_path):
        # 같은 날 여러 분봉 → 일자 1개
        indices = [20220323090000, 20220323090100, 20220323090200]
        con = self._make_moneytop(tmp_path, indices)
        days = load_tick_days(con)
        con.close()
        assert len(days) == 1

    def test_sorted_ascending(self, tmp_path):
        indices = [20220325090000, 20220323090000, 20220324090000]
        con = self._make_moneytop(tmp_path, indices)
        days = load_tick_days(con)
        con.close()
        assert days == sorted(days)

    def test_empty_table(self, tmp_path):
        con = self._make_moneytop(tmp_path, [])
        days = load_tick_days(con)
        con.close()
        assert days == []


# ---------------------------------------------------------------------------
# audit_runs_db
# ---------------------------------------------------------------------------

class TestAuditRunsDb:
    def _make_runs_db(self, tmp_path: Path) -> sqlite3.Connection:
        """최소 runs·generations 테이블 생성."""
        db_path = tmp_path / "runs_test.db"
        con = sqlite3.connect(str(db_path))
        con.execute(
            """CREATE TABLE runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT,
                status TEXT,
                finished_at TEXT
            )"""
        )
        con.execute(
            """CREATE TABLE generations (
                run_id TEXT,
                gen_no INTEGER,
                status TEXT,
                csv_path TEXT
            )"""
        )
        return con

    def test_empty_db(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        result = audit_runs_db(con, file_exists=lambda p: True)
        con.close()
        assert result["run_count"] == 0
        assert result["gen_count"] == 0
        assert result["oldest_run_id"] is None
        assert result["newest_run_id"] is None
        assert result["orphan_csvs"]["total"] == 0

    def test_status_counts(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.execute("INSERT INTO runs VALUES ('r1', '2026-01-01', 'ok', '2026-01-01')")
        con.execute("INSERT INTO runs VALUES ('r2', '2026-01-02', 'ok', '2026-01-02')")
        con.executemany(
            "INSERT INTO generations VALUES (?, ?, ?, ?)",
            [
                ("r1", 1, "ok", None),
                ("r1", 2, "ok", None),
                ("r2", 1, "error", None),
            ],
        )
        con.commit()
        result = audit_runs_db(con, file_exists=lambda p: True)
        con.close()
        assert result["status_counts"]["ok"] == 2
        assert result["status_counts"]["error"] == 1

    def test_orphan_csv_detection(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.execute("INSERT INTO runs VALUES ('r1', '2026-01-01', 'ok', '2026-01-01')")
        con.executemany(
            "INSERT INTO generations VALUES (?, ?, ?, ?)",
            [
                ("r1", 1, "ok", "exists.csv"),
                ("r1", 2, "ok", "missing.csv"),
                ("r1", 3, "ok", "also_missing.csv"),
            ],
        )
        con.commit()

        existing = {"exists.csv"}
        result = audit_runs_db(con, file_exists=lambda p: p in existing)
        con.close()

        assert result["orphan_csvs"]["total"] == 2
        assert "missing.csv" in result["orphan_csvs"]["sample"]
        assert "also_missing.csv" in result["orphan_csvs"]["sample"]

    def test_no_orphan_when_all_exist(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.execute("INSERT INTO runs VALUES ('r1', '2026-01-01', 'ok', '2026-01-01')")
        con.execute("INSERT INTO generations VALUES ('r1', 1, 'ok', 'real.csv')")
        con.commit()
        result = audit_runs_db(con, file_exists=lambda p: True)
        con.close()
        assert result["orphan_csvs"]["total"] == 0

    def test_null_csv_path_not_orphan(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.execute("INSERT INTO runs VALUES ('r1', '2026-01-01', 'ok', '2026-01-01')")
        con.execute("INSERT INTO generations VALUES ('r1', 1, 'ok', NULL)")
        con.commit()
        result = audit_runs_db(con, file_exists=lambda p: False)
        con.close()
        assert result["orphan_csvs"]["total"] == 0

    def test_oldest_newest_run_id(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.executemany(
            "INSERT INTO runs VALUES (?, ?, ?, ?)",
            [
                ("r_old", "2026-01-01", "ok", "2026-01-01"),
                ("r_mid", "2026-03-15", "ok", "2026-03-15"),
                ("r_new", "2026-06-01", "ok", "2026-06-01"),
            ],
        )
        con.commit()
        result = audit_runs_db(con, file_exists=lambda p: True)
        con.close()
        assert result["oldest_run_id"] == "r_old"
        assert result["newest_run_id"] == "r_new"

    def test_orphan_sample_capped_at_5(self, tmp_path):
        con = self._make_runs_db(tmp_path)
        con.execute("INSERT INTO runs VALUES ('r1', '2026-01-01', 'ok', '2026-01-01')")
        rows = [("r1", i, "ok", f"missing_{i}.csv") for i in range(10)]
        con.executemany("INSERT INTO generations VALUES (?, ?, ?, ?)", rows)
        con.commit()
        result = audit_runs_db(con, file_exists=lambda p: False)
        con.close()
        assert result["orphan_csvs"]["total"] == 10
        assert len(result["orphan_csvs"]["sample"]) == 5
