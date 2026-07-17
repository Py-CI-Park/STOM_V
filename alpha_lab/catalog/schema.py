"""research_assets 카탈로그 스키마 — 테이블 6종 DDL (WBS v3 P0, 계획 §3).

원칙(계획 §3): 원본 파일이 정본이고 이 DB는 카탈로그+요약 계층이다.
.db 자체는 커밋 금지(run 디렉토리 .gitignore) — 스키마·빌더·빌드 영수증만
커밋한다. 언제든 `python scripts/build_research_catalog.py`로 재생성 가능.

테이블 6종:
  assets        자산 레지스트리(지위 딱지·재생성 명령 컬럼 — 계획 §5-2)
  judgments     판정 카드(GA 경로 산출물 플래그 — 계획 §5-4)
  clauses       D1 절별 전 수치 + W5 어휘 유형
  strategies    W2 랭킹 + API 호환 + 원문 sha
  cells         S-v1/O-1G 셀 통합 union — label_tag 딱지 컬럼 NOT NULL 필수
  ledger_mirror n_trials 장부 미러(조회용)
"""
from __future__ import annotations

import sqlite3
from typing import Dict, Tuple

# 테이블 6종(계획 §3 표 순서). 이 외 테이블은 만들지 않는다.
TABLES: Tuple[str, ...] = (
    "assets", "judgments", "clauses", "strategies", "cells", "ledger_mirror",
)

_DDL: Tuple[str, ...] = (
    # 자산 레지스트리 — 계획 §1 관계표의 기계가독 사본.
    # status_tag = 지위 딱지(예: '함정 설명 전용', 'RR8_12 출구 조건부').
    # regen_cmd = 재생성 명령(§5-2 — git 제외 자산 유실 대비).
    """
    CREATE TABLE IF NOT EXISTS assets (
        asset_id        TEXT PRIMARY KEY,
        kind            TEXT NOT NULL,
        path            TEXT NOT NULL,
        produced_commit TEXT,
        seal_doc        TEXT,
        window          TEXT,
        status_tag      TEXT NOT NULL,
        regen_cmd       TEXT,
        summary         TEXT,
        exists_on_disk  INTEGER NOT NULL DEFAULT 0,
        sha256          TEXT,
        size_bytes      INTEGER,
        mtime_utc       TEXT
    )
    """,
    # 판정 카드 — 확정 판정(번복 금지)의 조회용 요약.
    # ga_path_flag = GA/최적화 경로 산출물 경고(엔진 dict 공유 버그 — 계획 §5-4).
    """
    CREATE TABLE IF NOT EXISTS judgments (
        series           TEXT PRIMARY KEY,
        verdict          TEXT NOT NULL,
        key_metrics_json TEXT NOT NULL,
        ledger_rows      TEXT,
        n_ledger_rows    INTEGER NOT NULL DEFAULT 0,
        report_path      TEXT,
        source_path      TEXT,
        produced_commit  TEXT,
        ga_path_flag     INTEGER NOT NULL DEFAULT 0,
        note             TEXT
    )
    """,
    # D1 절별 전 수치 — d1_clause_ablation_summary.json judgment.per_clause 미러.
    # w5_category = W5 어휘 유형(cat), classification = load_bearing 등 분류.
    """
    CREATE TABLE IF NOT EXISTS clauses (
        clause_num         INTEGER PRIMARY KEY,
        text               TEXT NOT NULL,
        family             TEXT,
        w5_category        TEXT,
        tier               TEXT,
        n_sat              INTEGER,
        n_unsat            INTEGER,
        delta_pp           REAL,
        ci_low_pp          REAL,
        ci_high_pp         REAL,
        mde_pp             REAL,
        p_one_sided        REAL,
        p_two_sided        REAL,
        both_year_positive INTEGER,
        both_year_negative INTEGER,
        floor_pass         INTEGER,
        fdr_survive        INTEGER,
        classification     TEXT NOT NULL,
        year_delta_json    TEXT,
        extra_json         TEXT
    )
    """,
    # W2 전략 랭킹 + API 호환 + 원문 sha(있는 경우만 — w2 json에는 sha 부재,
    # B1 등록 영수증·D1 요약에서 보강). human_hall_of_fame은 외부 벤치마크
    # (원문 없음 확정·절 파싱 금지) — status_tag로 표시.
    """
    CREATE TABLE IF NOT EXISTS strategies (
        name               TEXT PRIMARY KEY,
        source_section     TEXT NOT NULL,
        family             TEXT,
        rank_by_total      INTEGER,
        total_return_pct   REAL,
        annual_return_pct  REAL,
        monthly_return_pct REAL,
        mdd_pct            REAL,
        win_rate           REAL,
        payoff             REAL,
        trades             INTEGER,
        api_compat         TEXT,
        source_sha256      TEXT,
        lineage            TEXT,
        rank_metrics_json  TEXT NOT NULL,
        status_tag         TEXT
    )
    """,
    # S-v1(h300)·V2-A(L3)·O-1G 셀 통합 union.
    # label_tag NOT NULL 필수 — '함정 설명 전용' 등 지위 딱지 없는 셀 적재 금지.
    """
    CREATE TABLE IF NOT EXISTS cells (
        cell_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        source         TEXT NOT NULL,
        source_path    TEXT NOT NULL,
        label_kind     TEXT,
        label_tag      TEXT NOT NULL,
        axis_set       TEXT,
        map_type       TEXT,
        time_label     INTEGER,
        time_b         INTEGER,
        updown_q       INTEGER,
        mktcap_b       INTEGER,
        gap_b          INTEGER,
        gap_label      TEXT,
        win            INTEGER,
        win_label      TEXT,
        exit_kind      TEXT,
        h              INTEGER,
        n              INTEGER,
        n_candidates   INTEGER,
        censor_rate    REAL,
        exclusion_rate REAL,
        insufficient   INTEGER,
        mean_net       REAL,
        median_net     REAL,
        q25_net        REAL,
        q75_net        REAL,
        p_net_ge0      REAL,
        p_net_ge1      REAL,
        ci_low         REAL,
        ci_high        REAL,
        winrate        REAL,
        payoff         REAL,
        mfe_mean       REAL,
        mae_mean       REAL,
        year2022_mean  REAL,
        year2022_sign  INTEGER,
        year2023_mean  REAL,
        year2023_sign  INTEGER,
        extra_json     TEXT
    )
    """,
    # n_trials 장부 미러 — row_num = jsonl 1-기반 행 번호(원장 행 번호 참조 키).
    """
    CREATE TABLE IF NOT EXISTS ledger_mirror (
        row_num    INTEGER PRIMARY KEY,
        ts         TEXT,
        series     TEXT,
        window     TEXT,
        trial_type TEXT,
        target     TEXT,
        result     TEXT,
        session    TEXT,
        raw_json   TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_cells_source ON cells(source)",
    "CREATE INDEX IF NOT EXISTS idx_cells_label ON cells(label_kind, label_tag)",
    "CREATE INDEX IF NOT EXISTS idx_ledger_series ON ledger_mirror(series)",
)


def create_schema(con: sqlite3.Connection) -> None:
    """테이블 6종+인덱스를 생성한다(멱등 — IF NOT EXISTS)."""
    for ddl in _DDL:
        con.execute(ddl)
    con.commit()


def reset_tables(con: sqlite3.Connection) -> None:
    """전 테이블 행을 비운다(재빌드 멱등성 — cell_id 시퀀스 포함 초기화)."""
    for t in TABLES:
        con.execute(f"DELETE FROM {t}")
    # AUTOINCREMENT 시퀀스 초기화(첫 삽입 전에는 sqlite_sequence 자체가 없다).
    try:
        con.execute("DELETE FROM sqlite_sequence WHERE name='cells'")
    except sqlite3.OperationalError:
        pass
    con.commit()


def table_counts(con: sqlite3.Connection) -> Dict[str, int]:
    """테이블별 행 수(영수증·검증용)."""
    return {
        t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in TABLES
    }
