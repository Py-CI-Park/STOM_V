"""Read-only research documentation and index-comparison routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path
from typing import Final, TypedDict

from fastapi import APIRouter

from ai_strategy_loop.dashboard import research_index
from ai_strategy_loop.dashboard import research_records as records
from ai_strategy_loop.dashboard.analysis_snapshot import analysis_router
from ai_strategy_loop.dashboard.history_api import history_router


class ResearchDocSummary(TypedDict):
    id: str
    title: str
    category: str
    updated_at: str
    size: int


class ResearchDocsResponse(TypedDict):
    docs: list[ResearchDocSummary]
    count: int


class ResearchDocResponse(TypedDict, total=False):
    id: str
    title: str
    category: str
    updated_at: str
    size: int
    available: bool
    markdown: str
    error: str


class IndexCompareResponse(TypedDict):
    available: bool
    reason: str
    run_id: str
    network_used: bool
    source: str


@dataclass(frozen=True, slots=True)
class DocRoot:
    category: str
    rel_path: str


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DOC_ROOTS: Final[tuple[DocRoot, ...]] = (
    DocRoot(category="condition_research", rel_path="docs/research/condition_research"),
    DocRoot(category="good_results", rel_path="docs/reference/STOM_Good_Results"),
)
_SELECTED_UPDATE_LOGS: Final[tuple[str, ...]] = (
    "docs/update_log/2026-06-02_analysis_capability_audit.md",
    "docs/update_log/2026-06-02_band_generator_design.md",
    "docs/update_log/2026-06-02_dashboard_batch_resume_context.md",
    "docs/update_log/2026-06-03_tick_program_complete_handoff.md",
)

router = APIRouter()
router.include_router(analysis_router)
router.include_router(history_router)


def _repo_path(rel_path: str) -> Path:
    return (REPO_ROOT / rel_path).resolve()


def _relative_id(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def _title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _updated_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _category_for(path: Path, default: str) -> str:
    rel = _relative_id(path)
    if rel.startswith("docs/research/condition_research/wiki/"):
        return "wiki"
    return default


def _summary_for(path: Path, category: str) -> ResearchDocSummary:
    markdown = path.read_text(encoding="utf-8", errors="replace")
    return {
        "id": _relative_id(path),
        "title": _title_from_markdown(markdown, path.stem.replace("_", " ")),
        "category": _category_for(path, category),
        "updated_at": _updated_at(path),
        "size": len(markdown),
    }


def _iter_allowed_docs() -> list[tuple[Path, str]]:
    docs: list[tuple[Path, str]] = []
    for root in _DOC_ROOTS:
        root_path = _repo_path(root.rel_path)
        if root_path.is_dir():
            docs.extend((path, root.category) for path in root_path.rglob("*.md") if path.is_file())
    for rel_path in _SELECTED_UPDATE_LOGS:
        path = _repo_path(rel_path)
        if path.is_file():
            docs.append((path, "update_log"))
    return docs


def _doc_index() -> dict[str, tuple[Path, ResearchDocSummary]]:
    rows: dict[str, tuple[Path, ResearchDocSummary]] = {}
    for path, category in _iter_allowed_docs():
        summary = _summary_for(path, category)
        rows[summary["id"]] = (path, summary)
    return rows


@router.get("/research_docs")
def research_docs() -> ResearchDocsResponse:
    docs = [item[1] for item in _doc_index().values()]
    docs.sort(key=lambda row: (row["category"], row["id"]))
    return {"docs": docs, "count": len(docs)}


@router.get("/research_doc")
def research_doc(id: str = "") -> ResearchDocResponse:
    found = _doc_index().get(id)
    if found is None:
        return {"available": False, "error": "doc_not_allowed", "id": id}
    path, summary = found
    markdown = path.read_text(encoding="utf-8", errors="replace")
    return {**summary, "available": True, "markdown": markdown, "size": len(markdown)}


@router.get("/research_records")
def research_records():
    return records.list_research_records()


@router.get("/research_records/detail")
def research_record_detail(campaign: str = ""):
    return records.research_record_detail(campaign)


@router.get("/research_index")
def research_index_route():
    return research_index.list_research_index()


@router.get("/research_index/detail")
def research_index_detail(id: str = ""):
    return research_index.research_index_detail(id)


@router.get("/index_compare")
def index_compare(run_id: str = "") -> IndexCompareResponse:
    return {
        "available": False,
        "reason": "local_index_source_not_found",
        "run_id": run_id,
        "network_used": False,
        "source": "local",
    }

# ===========================================================================
# P4 연구 카탈로그(research_assets.db) — SELECT-only 읽기 전용 조회(재계산·쓰기 금지).
#   DB 는 scripts/build_research_catalog.py 가 생성(gitignore). 부재/오류는 500 아닌 error envelope.
#   sqlite 는 URI mode=ro 로만 연다(원본 무변형). 계약: 2026-07-12_dashboard_data_contract.md.
# ===========================================================================
# V5.7: 정본 경로는 STOM_RESEARCH_ASSETS_DB env 로 지정(무설정 시 legacy 비정본 경로 폴백).
_CATALOG_DB: Final[Path] = Path(
    os.environ.get("STOM_RESEARCH_ASSETS_DB")
    or (REPO_ROOT / "legacy_non_authoritative_catalogs" / "research_assets.db")
)
_CATALOG_TABLES: Final[tuple[str, ...]] = (
    "assets", "judgments", "clauses", "strategies", "cells", "ledger_mirror",
)


def _catalog_conn() -> "sqlite3.Connection | None":
    if not _CATALOG_DB.is_file():
        return None
    try:
        return sqlite3.connect(f"file:{_CATALOG_DB.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


def _catalog_unavailable(reason: str) -> dict:
    return {"available": False, "reason": reason, "db": "research_assets.db",
            "hint": "python scripts/build_research_catalog.py"}


@router.get("/research/summary")
def research_catalog_summary() -> dict:
    if not _CATALOG_DB.is_file():
        return _catalog_unavailable("catalog DB missing or unreadable")
    # V5.7: 서버 COUNT(*) 집계 제거 — 카운트는 빌드 영수증(provenance)에서 읽는다(무재집계).
    receipt = _CATALOG_DB.parent / "research_assets_build_receipt.json"
    counts: dict = {t: None for t in _CATALOG_TABLES}
    generated_at = None
    if receipt.is_file():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            table_counts = data.get("table_counts") or {}
            counts = {t: table_counts.get(t) for t in _CATALOG_TABLES}
            generated_at = data.get("generated_at")
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    try:
        st = _CATALOG_DB.stat()
        mtime, size = int(st.st_mtime), st.st_size
    except OSError:
        mtime, size = None, None
    # authoritative=false: 현 카탈로그는 비정본 preview(정본 승격은 봉인 계약 통과 후).
    return {"available": True, "db": _CATALOG_DB.name, "authoritative": False,
            "mtime": mtime, "size_bytes": size, "generated_at": generated_at, "counts": counts}


@router.get("/research/assets")
def research_catalog_assets(limit: int = 200) -> dict:
    conn = _catalog_conn()
    if conn is None:
        return _catalog_unavailable("catalog DB missing or unreadable")
    lim = max(1, min(500, int(limit) if str(limit).lstrip("-").isdigit() else 200))
    try:
        cur = conn.execute(
            "SELECT asset_id, kind, path, status_tag, window, seal_doc, summary, "
            "exists_on_disk FROM assets ORDER BY kind, asset_id LIMIT ?", (lim,))
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"available": True, "count": len(rows), "assets": rows}
    except sqlite3.Error as exc:
        return _catalog_unavailable(f"query failed: {exc}")
    finally:
        conn.close()


@router.get("/research/judgments")
def research_catalog_judgments() -> dict:
    conn = _catalog_conn()
    if conn is None:
        return _catalog_unavailable("catalog DB missing or unreadable")
    try:
        cur = conn.execute(
            "SELECT series, verdict, key_metrics_json, n_ledger_rows, report_path, "
            "note FROM judgments ORDER BY series")
        cols = [c[0] for c in cur.description]
        out: list = []
        for r in cur.fetchall():
            row = dict(zip(cols, r))
            raw = row.pop("key_metrics_json", None)
            try:
                row["key_metrics"] = json.loads(raw) if raw else {}
            except (json.JSONDecodeError, TypeError):
                row["key_metrics"] = {}
                row["key_metrics_error"] = True
            out.append(row)
        return {"available": True, "count": len(out), "judgments": out}
    except sqlite3.Error as exc:
        return _catalog_unavailable(f"query failed: {exc}")
    finally:
        conn.close()

@router.get("/research/clauses")
def research_catalog_clauses(limit: int = 200) -> dict:
    # V5.7: 절실험실 뷰용 SELECT-only. 무재집계·읽기 전용.
    conn = _catalog_conn()
    if conn is None:
        return _catalog_unavailable("catalog DB missing or unreadable")
    lim = max(1, min(500, int(limit) if str(limit).lstrip("-").isdigit() else 200))
    try:
        cur = conn.execute("SELECT * FROM clauses ORDER BY rowid LIMIT ?", (lim,))
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"available": True, "count": len(rows), "clauses": rows}
    except sqlite3.Error as exc:
        return _catalog_unavailable(f"query failed: {exc}")
    finally:
        conn.close()


@router.get("/research/cells")
def research_catalog_cells(limit: int = 200) -> dict:
    # V5.7: 표본/출구은행 뷰용 SELECT-only. 무재집계·읽기 전용.
    conn = _catalog_conn()
    if conn is None:
        return _catalog_unavailable("catalog DB missing or unreadable")
    lim = max(1, min(500, int(limit) if str(limit).lstrip("-").isdigit() else 200))
    try:
        cur = conn.execute("SELECT * FROM cells ORDER BY rowid LIMIT ?", (lim,))
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"available": True, "count": len(rows), "cells": rows}
    except sqlite3.Error as exc:
        return _catalog_unavailable(f"query failed: {exc}")
    finally:
        conn.close()
