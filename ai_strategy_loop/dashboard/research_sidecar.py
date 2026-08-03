"""QSP7 sidecar 연구 원장(P4) — 분석을 재시작 후에도 살아남게 하는 SQLite.

원칙:
  - 공식 CSV 는 불변 영수증으로 남고, 이 DB 는 언제든 재구축 가능한 인덱스다.
  - 멱등 ingest: artifact 는 (csv_sha256, row_count) 기본키 — 같은 CSV 를 몇 번
    넣어도 중복 0. analysis 는 analysis_id 로 upsert.
  - schema_version 을 meta 에 기록해 migration 기준점을 만든다.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from ai_strategy_loop.autopsy.trade_path_analysis_models import (
    AnalysisTotals,
    EpisodeSummary,
    ExcludedTrade,
    TradePathAnalysis,
)
from ai_strategy_loop.autopsy.trade_path_models import RunSource, Timeframe, TradeResultRow


SCHEMA_VERSION: Final = 1

_SCHEMA: Final = (
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS artifacts ("
    " csv_sha256 TEXT NOT NULL, row_count INTEGER NOT NULL,"
    " csv_path TEXT NOT NULL, lane TEXT NOT NULL, first_seen TEXT NOT NULL,"
    " PRIMARY KEY (csv_sha256, row_count))",
    "CREATE TABLE IF NOT EXISTS analyses ("
    " analysis_id TEXT PRIMARY KEY, lane TEXT NOT NULL,"
    " csv_sha256 TEXT NOT NULL, row_count INTEGER NOT NULL,"
    " source_json TEXT NOT NULL, totals_json TEXT NOT NULL,"
    " episodes_json TEXT NOT NULL, exclusions_json TEXT NOT NULL,"
    " rows_json TEXT NOT NULL,"
    " decision_horizons TEXT NOT NULL, continuation_horizons TEXT NOT NULL,"
    " created_at TEXT NOT NULL)",
)


def default_sidecar_path() -> Path:
    override = os.environ.get("STOM_QSP7_SIDECAR_DB")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[1] / "state" / "qsp7_research.db"


class ResearchSidecar:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_sidecar_path()
        self._lock = threading.RLock()
        self._initialised = False

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        if not self._initialised:
            for statement in _SCHEMA:
                connection.execute(statement)
            connection.execute(
                "INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )
            connection.commit()
            self._initialised = True
        return connection

    # ------------------------------------------------------------------ ingest
    def ingest_analysis(self, result: TradePathAnalysis) -> dict[str, object]:
        lane = result.source.timeframe.value
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            inserted = connection.execute(
                "INSERT OR IGNORE INTO artifacts VALUES (?, ?, ?, ?, ?)",
                (result.source.csv_sha256, len(result.rows),
                 result.source.csv_path, lane, now),
            ).rowcount
            connection.execute(
                "INSERT OR REPLACE INTO analyses VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    result.analysis_id, lane,
                    result.source.csv_sha256, len(result.rows),
                    json.dumps(asdict(result.source), ensure_ascii=False),
                    json.dumps(asdict(result.totals), ensure_ascii=False),
                    json.dumps([asdict(row) for row in result.episodes], ensure_ascii=False),
                    json.dumps([asdict(row) for row in result.exclusions], ensure_ascii=False),
                    json.dumps([asdict(row) for row in result.rows], ensure_ascii=False),
                    json.dumps(list(result.decision_horizons)),
                    json.dumps(list(result.continuation_horizons)),
                    now,
                ),
            )
        return {"artifact_inserted": bool(inserted), "analysis_id": result.analysis_id}

    # ------------------------------------------------------------------ load
    def load_analysis(self, analysis_id: str) -> TradePathAnalysis | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT source_json, totals_json, episodes_json, exclusions_json,"
                " rows_json, decision_horizons, continuation_horizons"
                " FROM analyses WHERE analysis_id = ?",
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        source_data = json.loads(row[0])
        source_data["timeframe"] = Timeframe(source_data["timeframe"])
        return TradePathAnalysis(
            analysis_id=analysis_id,
            source=RunSource(**source_data),
            rows=tuple(TradeResultRow(**item) for item in json.loads(row[4])),
            episodes=tuple(EpisodeSummary(**item) for item in json.loads(row[2])),
            exclusions=tuple(ExcludedTrade(**item) for item in json.loads(row[3])),
            totals=AnalysisTotals(**json.loads(row[1])),
            decision_horizons=tuple(json.loads(row[5])),
            continuation_horizons=tuple(json.loads(row[6])),
        )

    # ------------------------------------------------------------------ browse
    def list_analyses(self, limit: int = 50, lane: str = "") -> list[dict[str, object]]:
        query = (
            "SELECT analysis_id, lane, csv_sha256, row_count, totals_json, created_at"
            " FROM analyses"
            + (" WHERE lane = ?" if lane else "")
            + " ORDER BY created_at DESC LIMIT ?"
        )
        parameters = (lane, max(1, min(limit, 500))) if lane else (max(1, min(limit, 500)),)
        with self._lock, self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [
            {
                "analysis_id": item[0], "lane": item[1], "csv_sha256": item[2],
                "row_count": item[3], "totals": json.loads(item[4]), "created_at": item[5],
            }
            for item in rows
        ]

    def list_artifacts(self, limit: int = 50) -> list[dict[str, object]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT csv_sha256, row_count, csv_path, lane, first_seen"
                " FROM artifacts ORDER BY first_seen DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        return [
            {"csv_sha256": item[0], "row_count": item[1], "csv_path": item[2],
             "lane": item[3], "first_seen": item[4]}
            for item in rows
        ]

    def counts(self) -> dict[str, int]:
        with self._lock, self._connect() as connection:
            artifacts = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
            analyses = connection.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        return {"artifacts": int(artifacts), "analyses": int(analyses)}

    def rebuild_hash(self) -> str:
        """정렬된 canonical dump 의 SHA256 — 재구축 검증 기준."""
        with self._lock, self._connect() as connection:
            artifacts = connection.execute(
                "SELECT csv_sha256, row_count, lane FROM artifacts ORDER BY csv_sha256, row_count"
            ).fetchall()
            analyses = connection.execute(
                "SELECT analysis_id, csv_sha256, row_count, totals_json"
                " FROM analyses ORDER BY analysis_id"
            ).fetchall()
        canonical = json.dumps({"artifacts": artifacts, "analyses": analyses}, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
