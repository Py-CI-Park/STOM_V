"""ANA-05 — Canonical AnalysisBundle v3 불변 artifact 저장소 + 읽기 카탈로그.

저장 원칙:
- 루트는 ``ai_strategy_loop/state/analysis_artifacts/`` (런타임 영역, git 제외).
  ``STOM_ANALYSIS_ARTIFACT_ROOT`` 환경변수로 재지정 가능(시험 격리용).
- 번들은 ``<root>/<content_sha256>/bundle.json`` 에 content-addressed 로 둔다.
  같은 해시면 같은 내용 — 기존 파일을 덮어쓰지 않는다.
- ``analysis_catalog.sqlite`` 는 (job_id, source_sha256) → content_sha256 조회용
  읽기 카탈로그다. 소비자는 카탈로그를 읽기만 하고, 쓰기는 store 경로뿐이다.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Final

from ai_strategy_loop.dashboard.analysis_bundle_artifacts import canonical_json
from ai_strategy_loop.dashboard.analysis_bundle_models import (
    AnalysisBundleV3,
)

_CATALOG_NAME: Final = "analysis_catalog.sqlite"


def artifact_root() -> Path:
    override = os.environ.get("STOM_ANALYSIS_ARTIFACT_ROOT")
    if override:
        return Path(override)
    return (
        Path(__file__).resolve().parent.parent
        / "state"
        / "analysis_artifacts"
    )


def _catalog_path(root: Path) -> Path:
    return root / _CATALOG_NAME


def _connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_catalog_path(root))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS bundles ("
        "  job_id TEXT NOT NULL,"
        "  source_sha256 TEXT NOT NULL,"
        "  content_sha256 TEXT NOT NULL,"
        "  stored_at REAL NOT NULL,"
        "  PRIMARY KEY (job_id, source_sha256)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS cards ("
        "  job_id TEXT NOT NULL,"
        "  card_sha256 TEXT NOT NULL,"
        "  stored_at REAL NOT NULL,"
        "  PRIMARY KEY (job_id, card_sha256)"
        ")"
    )
    return conn


def store_bundle(bundle: AnalysisBundleV3, root: Path | None = None) -> Path:
    """번들을 content-addressed 로 보존하고 카탈로그에 색인한다(멱등)."""
    root = root or artifact_root()
    bundle_dir = root / bundle.content_sha256
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / "bundle.json"
    if not bundle_path.exists():
        tmp = bundle_dir / ".bundle.json.tmp"
        tmp.write_text(
            canonical_json(bundle.model_dump(mode="json", by_alias=True)),
            encoding="utf-8",
        )
        tmp.replace(bundle_path)
    import time

    with _connect(root) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO bundles"
            " (job_id, source_sha256, content_sha256, stored_at)"
            " VALUES (?, ?, ?, ?)",
            (
                bundle.identity.job_id,
                bundle.identity.source_sha256,
                bundle.content_sha256,
                time.time(),
            ),
        )
    return bundle_path


def load_bundle_by_sha(
    content_sha256: str, root: Path | None = None
) -> AnalysisBundleV3 | None:
    """content hash 로 번들을 읽는다. 파일이 없거나 해시 불일치면 None."""
    root = root or artifact_root()
    path = root / content_sha256 / "bundle.json"
    if not path.is_file():
        return None
    try:
        return AnalysisBundleV3.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except ValueError:
        return None


def lookup_bundle(
    job_id: str, source_sha256: str, root: Path | None = None
) -> AnalysisBundleV3 | None:
    """카탈로그에서 (job_id, source_sha256) → content_sha256 를 찾아 번들을 읽는다."""
    root = root or artifact_root()
    catalog = _catalog_path(root)
    if not catalog.is_file():
        return None
    try:
        with sqlite3.connect(f"file:{catalog}?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT content_sha256 FROM bundles"
                " WHERE job_id = ? AND source_sha256 = ?",
                (job_id, source_sha256),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return load_bundle_by_sha(row[0], root)


def latest_bundle_sha_for_job(job_id: str, root: Path | None = None) -> str | None:
    """해당 job 의 가장 최근 보존 번들 해시 — 카드/화면의 bundle 링크용."""
    root = root or artifact_root()
    catalog = _catalog_path(root)
    if not catalog.is_file():
        return None
    try:
        with sqlite3.connect(f"file:{catalog}?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT content_sha256 FROM bundles WHERE job_id = ?"
                " ORDER BY stored_at DESC LIMIT 1",
                (job_id,),
            ).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def store_card(job_id: str, card_sha256: str, card_json: str,
               root: Path | None = None) -> Path:
    """Analysis Card v3 를 content-addressed 로 보존한다(멱등·덮어쓰기 없음)."""
    root = root or artifact_root()
    card_dir = root / card_sha256
    card_dir.mkdir(parents=True, exist_ok=True)
    card_path = card_dir / "card.json"
    if not card_path.exists():
        tmp = card_dir / ".card.json.tmp"
        tmp.write_text(card_json, encoding="utf-8")
        tmp.replace(card_path)
    import time

    with _connect(root) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO cards (job_id, card_sha256, stored_at)"
            " VALUES (?, ?, ?)",
            (job_id, card_sha256, time.time()),
        )
    return card_path


def load_card_by_sha(card_sha256: str, root: Path | None = None) -> str | None:
    """content hash 로 카드 JSON 문자열을 읽는다(없으면 None)."""
    root = root or artifact_root()
    path = root / card_sha256 / "card.json"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None
