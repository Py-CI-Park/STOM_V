"""Run-local SQLite ledger for native research checkpoints and resume."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def trial_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class NativeSidecar:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_schema(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS native_runs (
                    run_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL,
                    authority TEXT NOT NULL, tool TEXT NOT NULL, created_at TEXT NOT NULL,
                    status TEXT NOT NULL, config_sha256 TEXT NOT NULL,
                    data_fingerprints_json TEXT NOT NULL,
                    operational_fingerprints_before_json TEXT NOT NULL,
                    operational_fingerprints_after_json TEXT
                );
                CREATE TABLE IF NOT EXISTS native_trials (
                    trial_hash TEXT PRIMARY KEY, run_id TEXT NOT NULL, phase TEXT NOT NULL,
                    family_id TEXT NOT NULL, band_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL, params_json TEXT NOT NULL, resume_key TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL, timeout_kind TEXT, metrics_json TEXT,
                    started_at TEXT, ended_at TEXT
                );
                CREATE TABLE IF NOT EXISTS native_checkpoints (
                    run_id TEXT NOT NULL, trial_hash TEXT NOT NULL, seq INTEGER NOT NULL,
                    checkpoint TEXT NOT NULL, detail_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, trial_hash, seq)
                );
                CREATE TABLE IF NOT EXISTS native_artifacts (
                    artifact_sha256 TEXT PRIMARY KEY, run_id TEXT NOT NULL, trial_hash TEXT,
                    kind TEXT NOT NULL, path TEXT NOT NULL, row_count INTEGER, table_name TEXT
                );
                CREATE TABLE IF NOT EXISTS source_snapshots (
                    source_sha256 TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, code TEXT NOT NULL
                );
                """
            )

    def record_trial(self, *, run_id: str, phase: str, family_id: str, band_id: str,
                     candidate_id: str, source_sha256: str, parameters: dict[str, Any],
                     resume_key: str, status: str) -> str:
        payload = {
            "run_id": run_id, "phase": phase, "family_id": family_id, "band_id": band_id,
            "candidate_id": candidate_id, "source_sha256": source_sha256,
            "parameters": parameters, "resume_key": resume_key,
        }
        digest = trial_hash(payload)
        with self.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO native_trials
                (trial_hash, run_id, phase, family_id, band_id, candidate_id, source_sha256,
                 params_json, resume_key, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (digest, run_id, phase, family_id, band_id, candidate_id, source_sha256,
                 canonical_json(parameters), resume_key, status),
            )
        return digest

    def completed_trial_hashes(self) -> set[str]:
        terminal = ("engine_success", "evidence_recovered")
        with self.connect() as connection:
            return {row[0] for row in connection.execute(
                "SELECT trial_hash FROM native_trials WHERE status IN (?, ?)", terminal
            )}

    def is_resume_complete(self, resume_key: str) -> bool:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT status FROM native_trials WHERE resume_key = ?", (resume_key,)
            ).fetchone()
        return bool(row and row[0] in {"engine_success", "evidence_recovered"})
