"""stats_map.db 스키마·적재·요약 지문 — 사전등록 §5 저장 스키마 정합.

테이블: cells_l0 / cells_l1(동일 컬럼) / corr_matrix / build_receipts.
빌드는 결정론이며 summary_sha(전 셀+corr의 정준 직렬화 sha256)가 재현성
게이트의 대조 지문이다. .db 자체는 커밋 금지(.gitignore *.db) — 스키마·영수증·
요약만 커밋한다.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Dict, List, Optional, Sequence

# 셀 축 키 + 라벨 8종 + 보조 — cells_l0/cells_l1 공통 컬럼(순서 봉인).
CELL_COLUMNS: Sequence[str] = (
    "axis_set", "map_type", "time_label", "time_b", "updown_q", "mktcap_b", "h",
    "n", "n_candidates", "censor_rate", "insufficient",
    "p_net_ge0", "p_net_ge1", "mean_net", "median_net", "q25_net", "q75_net",
    "ci_low", "ci_high",
    "year2022_mean", "year2022_sign", "year2023_mean", "year2023_sign",
    "winrate", "payoff", "mfe_mean", "mae_mean",
)
_CELL_DDL_TYPES = {
    "axis_set": "TEXT", "map_type": "TEXT", "time_label": "INTEGER",
    "time_b": "INTEGER", "updown_q": "INTEGER", "mktcap_b": "INTEGER",
    "h": "INTEGER", "n": "INTEGER", "n_candidates": "INTEGER",
    "insufficient": "INTEGER", "year2022_sign": "INTEGER",
    "year2023_sign": "INTEGER",
}
_CORR_COLUMNS = ("map_type", "kind", "var1", "var2", "value", "n")


def _cell_ddl(table: str) -> str:
    cols = ", ".join(f'"{c}" {_CELL_DDL_TYPES.get(c, "REAL")}' for c in CELL_COLUMNS)
    return f"CREATE TABLE {table} ({cols})"


def create_schema(conn: sqlite3.Connection) -> None:
    """4개 테이블을 새로 만든다(기존 동명 테이블은 교체)."""
    for table in ("cells_l0", "cells_l1"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute(_cell_ddl(table))
    conn.execute("DROP TABLE IF EXISTS corr_matrix")
    conn.execute(
        "CREATE TABLE corr_matrix ("
        '"map_type" TEXT, "kind" TEXT, "var1" TEXT, "var2" TEXT,'
        ' "value" REAL, "n" INTEGER)')
    conn.execute("DROP TABLE IF EXISTS build_receipts")
    conn.execute(
        "CREATE TABLE build_receipts ("
        '"build_id" TEXT, "date_start" TEXT, "date_end" TEXT,'
        ' "input_files" INTEGER, "row_count" INTEGER, "n_l0" INTEGER,'
        ' "n_l1" INTEGER, "param_sha" TEXT, "summary_sha" TEXT,'
        ' "created_at" TEXT)')
    conn.commit()


def insert_cells(conn: sqlite3.Connection, table: str,
                 rows: List[Dict[str, object]]) -> None:
    """셀 행 목록을 cells_l0/cells_l1에 적재한다(컬럼 순서 봉인)."""
    placeholders = ", ".join("?" for _ in CELL_COLUMNS)
    conn.executemany(
        f"INSERT INTO {table} VALUES ({placeholders})",
        [tuple(row.get(c) for c in CELL_COLUMNS) for row in rows])
    conn.commit()


def insert_corr(conn: sqlite3.Connection, map_type: str,
                rows: List[Dict[str, object]]) -> None:
    """corr_matrix 행을 적재한다."""
    conn.executemany(
        "INSERT INTO corr_matrix VALUES (?, ?, ?, ?, ?, ?)",
        [(map_type, r["kind"], r["var1"], r["var2"], r["value"], r["n"])
         for r in rows])
    conn.commit()


def insert_receipt(conn: sqlite3.Connection, receipt: Dict[str, object]) -> None:
    """build_receipts 1행 적재."""
    cols = ("build_id", "date_start", "date_end", "input_files", "row_count",
            "n_l0", "n_l1", "param_sha", "summary_sha", "created_at")
    conn.execute(
        f"INSERT INTO build_receipts VALUES ({', '.join('?' for _ in cols)})",
        tuple(receipt.get(c) for c in cols))
    conn.commit()


def _round(value: object) -> object:
    """요약 지문용 반올림 — float은 10자리, 그 외는 원값(None 포함)."""
    return round(value, 10) if isinstance(value, float) else value


def summary_sha(cell_rows: Dict[str, List[Dict[str, object]]],
                corr_rows: List[Dict[str, object]]) -> str:
    """전 셀+corr의 정준 직렬화 sha256(재현성 게이트 대조 지문)."""
    payload = {
        "cells": {
            table: sorted(
                [[_round(r.get(c)) for c in CELL_COLUMNS] for r in rows])
            for table, rows in cell_rows.items()
        },
        "corr": sorted([[r["kind"], r["var1"], r["var2"], _round(r["value"]),
                         r["n"]] for r in corr_rows]),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
