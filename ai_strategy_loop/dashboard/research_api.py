"""Read-only research documentation and index-comparison routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Final, Literal, TypedDict

from fastapi import APIRouter

from ai_strategy_loop.dashboard import research_index
from ai_strategy_loop.dashboard import research_records as records
from ai_strategy_loop.dashboard.analysis_snapshot import analysis_router
from ai_strategy_loop.dashboard.history_api import history_router


WikiDocsStatus = Literal["ok", "invalid_limit", "invalid_cursor", "invalid_q", "invalid_tag", "invalid_category"]


class ResearchDocChronologyEntry(TypedDict, total=False):
    date: str
    label: str
    status: str
    id: str


class ResearchDocSummary(TypedDict, total=False):
    id: str
    title: str
    category: str
    updated_at: str
    size: int
    source_sha256: str
    source_bytes: int
    tags: list[str]
    related_ids: list[str]
    chronology: list[ResearchDocChronologyEntry]
    history: list[ResearchDocChronologyEntry]
    trust: str
    standard_template_status: str
    metadata_status: str
    metadata_source: str
    stale: bool


class ResearchDocsResponse(TypedDict, total=False):
    docs: list[ResearchDocSummary]
    count: int
    total_count: int
    next_cursor: str | None
    limit: int
    cursor: str
    available: bool
    status: WikiDocsStatus
    error: WikiDocsStatus


class ResearchDocResponse(TypedDict, total=False):
    id: str
    title: str
    category: str
    updated_at: str
    size: int
    source_sha256: str
    source_bytes: int
    tags: list[str]
    related_ids: list[str]
    chronology: list[ResearchDocChronologyEntry]
    history: list[ResearchDocChronologyEntry]
    trust: str
    standard_template_status: str
    metadata_status: str
    metadata_source: str
    stale: bool
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
_DOCS_MAX_LIMIT: Final[int] = 1000
_DOCS_DEFAULT_LIMIT: Final[int] = 1000
_FILTER_TEXT_MAX: Final[int] = 120
_TAG_TEXT_MAX: Final[int] = 48
_CATEGORY_TEXT_MAX: Final[int] = 48
_HISTORY_LIMIT: Final[int] = 50
_WIKI_INDEX_FILES: Final[tuple[str, ...]] = (
    "docs/research/condition_research/wiki/_wiki_index.json",
    "docs/research/condition_research/wiki/wiki_index.json",
)

router = APIRouter()
_DOC_INDEX_CACHE_TTL_SECONDS: Final[float] = 30.0
_doc_index_cache_lock = threading.Lock()
_doc_index_cache_key: tuple[object, ...] | None = None
_doc_index_cache_at = 0.0
_doc_index_cache: dict[str, tuple[Path, ResearchDocSummary]] | None = None
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


def _read_doc_source(path: Path) -> tuple[bytes, str]:
    raw_bytes = path.read_bytes()
    decoded = raw_bytes.decode("utf-8", errors="replace")
    return raw_bytes, decoded.replace("\r\n", "\n").replace("\r", "\n")


def _source_sha256(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def _clean_text(value: Any, max_len: int) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = " ".join(value.replace("\x00", " ").split())
    if not stripped:
        return None
    return stripped[:max_len]


def _normalize_tags(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else [value]
    tags: set[str] = set()
    for item in raw_items:
        cleaned = _clean_text(item, _TAG_TEXT_MAX)
        if cleaned:
            tags.add(cleaned.casefold())
    return sorted(tags)


def _normalize_doc_ids(value: Any, allowed_ids: set[str], self_id: str = "") -> list[str]:
    raw_items = value if isinstance(value, list) else [value]
    ids: set[str] = set()
    for item in raw_items:
        if not isinstance(item, str):
            continue
        candidate = item.strip()
        if candidate in allowed_ids and candidate != self_id:
            ids.add(candidate)
    return sorted(ids)


def _normalize_chronology(value: Any, allowed_ids: set[str]) -> list[ResearchDocChronologyEntry]:
    if not isinstance(value, list):
        return []
    rows: list[ResearchDocChronologyEntry] = []
    for item in value[:_HISTORY_LIMIT]:
        if isinstance(item, str):
            label = _clean_text(item, 160)
            if label:
                rows.append({"label": label})
            continue
        if not isinstance(item, dict):
            continue
        row: ResearchDocChronologyEntry = {}
        date = _clean_text(item.get("date") or item.get("at") or item.get("updated_at"), 64)
        label = _clean_text(item.get("label") or item.get("title") or item.get("event"), 160)
        status = _clean_text(item.get("status"), 64)
        doc_id = item.get("id") or item.get("doc_id") or item.get("related_id")
        if date:
            row["date"] = date
        if label:
            row["label"] = label
        if status:
            row["status"] = status
        if isinstance(doc_id, str) and doc_id.strip() in allowed_ids:
            row["id"] = doc_id.strip()
        if row:
            rows.append(row)
    return rows


def _standard_template_status(payload: dict[str, Any]) -> str:
    value: Any = payload.get("standard_template_status", payload.get("template_status"))
    if value is None:
        standard_template = payload.get("standard_template")
        if isinstance(standard_template, dict):
            value = standard_template.get("status")
        elif isinstance(standard_template, bool):
            value = "standard" if standard_template else "nonstandard"
    return _clean_text(value, 64) or "unknown"


def _trust_status(payload: dict[str, Any]) -> str:
    value: Any = payload.get("trust")
    if isinstance(value, dict):
        value = value.get("level") or value.get("status")
    return _clean_text(value, 64) or "unknown"


def _wiki_sidecar_paths(path: Path) -> tuple[Path, ...]:
    return (
        path.with_name(f"{path.name}.wiki.json"),
        path.with_suffix(".wiki.json"),
    )


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _load_wiki_index_metadata(allowed_ids: set[str]) -> dict[str, tuple[dict[str, Any], str]]:
    metadata: dict[str, tuple[dict[str, Any], str]] = {}
    for rel_path in _WIKI_INDEX_FILES:
        path = _repo_path(rel_path)
        if not path.is_file():
            continue
        payload = _read_json_object(path)
        if payload is None:
            continue
        source = _relative_id(path)
        docs = payload.get("docs") or payload.get("items") or payload.get("records")
        if isinstance(docs, dict):
            for doc_id, item in docs.items():
                if isinstance(doc_id, str) and doc_id in allowed_ids and isinstance(item, dict):
                    metadata[doc_id] = (item, source)
        elif isinstance(docs, list):
            for item in docs:
                if not isinstance(item, dict):
                    continue
                doc_id = item.get("id") or item.get("doc_id")
                if isinstance(doc_id, str) and doc_id in allowed_ids:
                    metadata[doc_id] = (item, source)
    return metadata


def _load_wiki_sidecar(path: Path, doc_id: str) -> tuple[dict[str, Any] | None, str, str]:
    for sidecar in _wiki_sidecar_paths(path):
        if not sidecar.is_file():
            continue
        source = _relative_id(sidecar)
        payload = _read_json_object(sidecar)
        if payload is None:
            return None, "invalid_sidecar", source
        declared_id = payload.get("id") or payload.get("doc_id")
        if isinstance(declared_id, str) and declared_id.strip() and declared_id.strip() != doc_id:
            return None, "invalid_sidecar", source
        return payload, "ok", source
    return None, "missing_sidecar", ""


def _metadata_for(
    path: Path,
    doc_id: str,
    raw_bytes: bytes,
    allowed_ids: set[str],
    index_metadata: tuple[dict[str, Any], str] | None,
) -> dict[str, object]:
    payload: dict[str, Any] = {}
    metadata_status = "missing_sidecar"
    metadata_source = "none"
    if index_metadata is not None:
        payload.update(index_metadata[0])
        metadata_source = index_metadata[1]
        metadata_status = "ok"

    sidecar_payload, sidecar_status, sidecar_source = _load_wiki_sidecar(path, doc_id)
    if sidecar_status == "invalid_sidecar":
        payload = {}
        metadata_source = sidecar_source
        metadata_status = "invalid_sidecar"
    elif sidecar_payload is not None:
        payload.update(sidecar_payload)
        metadata_source = sidecar_source
        metadata_status = "ok"

    raw_sha = _source_sha256(raw_bytes)
    declared_sha = _clean_text(payload.get("source_sha256"), 80)
    stale = bool(declared_sha and declared_sha.casefold() != raw_sha.casefold())
    if stale and metadata_status == "ok":
        metadata_status = "stale_sidecar"

    chronology = _normalize_chronology(payload.get("chronology", payload.get("history")), allowed_ids)
    return {
        "source_sha256": raw_sha,
        "source_bytes": len(raw_bytes),
        "tags": _normalize_tags(payload.get("tags")),
        "related_ids": _normalize_doc_ids(payload.get("related_ids", payload.get("related")), allowed_ids, doc_id),
        "chronology": chronology,
        "history": chronology,
        "trust": _trust_status(payload),
        "standard_template_status": _standard_template_status(payload),
        "metadata_status": metadata_status,
        "metadata_source": metadata_source,
        "stale": stale,
    }


def _summary_for(
    path: Path,
    category: str,
    allowed_ids: set[str] | None = None,
    index_metadata: tuple[dict[str, Any], str] | None = None,
) -> ResearchDocSummary:
    doc_id = _relative_id(path)
    raw_bytes, markdown = _read_doc_source(path)
    title = research_index.serialize_research_doc_markdown(
        _title_from_markdown(markdown, path.stem.replace("_", " "))
    )
    return {
        "id": doc_id,
        "title": title,
        "category": _category_for(path, category),
        "updated_at": _updated_at(path),
        "size": len(markdown),
        **_metadata_for(path, doc_id, raw_bytes, allowed_ids or set(), index_metadata),
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


def _doc_index_key() -> tuple[object, ...]:
    return (
        str(REPO_ROOT.resolve()),
        tuple((root.category, root.rel_path) for root in _DOC_ROOTS),
        _SELECTED_UPDATE_LOGS,
        _WIKI_INDEX_FILES,
    )


def _build_doc_index() -> dict[str, tuple[Path, ResearchDocSummary]]:
    entries: list[tuple[Path, str, str]] = []
    for path, category in _iter_allowed_docs():
        try:
            entries.append((path, category, _relative_id(path)))
        except ValueError:
            continue
    allowed_ids = {doc_id for _path, _category, doc_id in entries}
    index_metadata = _load_wiki_index_metadata(allowed_ids)
    rows: dict[str, tuple[Path, ResearchDocSummary]] = {}
    for path, category, doc_id in entries:
        summary = _summary_for(path, category, allowed_ids, index_metadata.get(doc_id))
        rows[doc_id] = (path, summary)
    return rows


def _doc_index() -> dict[str, tuple[Path, ResearchDocSummary]]:
    global _doc_index_cache, _doc_index_cache_at, _doc_index_cache_key

    key = _doc_index_key()
    now = time.monotonic()
    with _doc_index_cache_lock:
        if (
            _doc_index_cache is not None
            and _doc_index_cache_key == key
            and now - _doc_index_cache_at < _DOC_INDEX_CACHE_TTL_SECONDS
        ):
            return _doc_index_cache

        rows = _build_doc_index()
        _doc_index_cache = rows
        _doc_index_cache_key = key
        _doc_index_cache_at = time.monotonic()
        return rows


def _parse_limit(value: Any) -> tuple[int, WikiDocsStatus | None]:
    if value in (None, ""):
        return _DOCS_DEFAULT_LIMIT, None
    try:
        limit = int(str(value))
    except (TypeError, ValueError):
        return _DOCS_DEFAULT_LIMIT, "invalid_limit"
    if limit < 1 or limit > _DOCS_MAX_LIMIT:
        return _DOCS_DEFAULT_LIMIT, "invalid_limit"
    return limit, None


def _parse_cursor(value: Any) -> tuple[int, WikiDocsStatus | None]:
    if value in (None, ""):
        return 0, None
    try:
        cursor = int(str(value))
    except (TypeError, ValueError):
        return 0, "invalid_cursor"
    if cursor < 0:
        return 0, "invalid_cursor"
    return cursor, None


def _normalize_filter(value: Any, max_len: int, error: WikiDocsStatus) -> tuple[str, WikiDocsStatus | None]:
    if value in (None, ""):
        return "", None
    text = str(value).strip()
    if "\x00" in text or len(text) > max_len:
        return "", error
    return text, None


def _docs_error(status: WikiDocsStatus) -> ResearchDocsResponse:
    return {
        "available": False,
        "status": status,
        "error": status,
        "docs": [],
        "count": 0,
        "total_count": 0,
        "limit": 0,
        "cursor": "0",
        "next_cursor": None,
    }


def _matches_q(row: ResearchDocSummary, q: str) -> bool:
    if not q:
        return True
    chronology = row.get("chronology") or []
    haystack = [
        row.get("id", ""),
        row.get("title", ""),
        row.get("category", ""),
        row.get("trust", ""),
        row.get("standard_template_status", ""),
        row.get("metadata_status", ""),
        row.get("source_sha256", ""),
        *(row.get("tags") or []),
        *(row.get("related_ids") or []),
        *(item.get("label", "") for item in chronology),
    ]
    return q.casefold() in "\n".join(str(item) for item in haystack).casefold()


def _filter_docs(
    docs: list[ResearchDocSummary],
    q: str,
    tag: str,
    category: str,
) -> list[ResearchDocSummary]:
    tag_key = tag.casefold()
    category_key = category.casefold()
    filtered: list[ResearchDocSummary] = []
    for row in docs:
        if category_key and row.get("category", "").casefold() != category_key:
            continue
        if tag_key and tag_key not in {item.casefold() for item in row.get("tags", [])}:
            continue
        if not _matches_q(row, q):
            continue
        filtered.append(row)
    return filtered


@router.get("/research_docs")
def research_docs(
    q: str = "",
    tag: str = "",
    category: str = "",
    limit: str = "",
    cursor: str = "",
) -> ResearchDocsResponse:
    resolved_limit, limit_error = _parse_limit(limit)
    if limit_error:
        return _docs_error(limit_error)
    resolved_cursor, cursor_error = _parse_cursor(cursor)
    if cursor_error:
        return _docs_error(cursor_error)
    q_filter, q_error = _normalize_filter(q, _FILTER_TEXT_MAX, "invalid_q")
    if q_error:
        return _docs_error(q_error)
    tag_filter, tag_error = _normalize_filter(tag, _TAG_TEXT_MAX, "invalid_tag")
    if tag_error:
        return _docs_error(tag_error)
    category_filter, category_error = _normalize_filter(category, _CATEGORY_TEXT_MAX, "invalid_category")
    if category_error:
        return _docs_error(category_error)

    docs = [item[1] for item in _doc_index().values()]
    docs.sort(key=lambda row: (row.get("category", ""), row.get("id", "")))
    filtered = _filter_docs(docs, q_filter, tag_filter, category_filter)
    page = filtered[resolved_cursor:resolved_cursor + resolved_limit]
    next_offset = resolved_cursor + resolved_limit
    return {
        "available": True,
        "status": "ok",
        "docs": page,
        "count": len(page),
        "total_count": len(filtered),
        "limit": resolved_limit,
        "cursor": str(resolved_cursor),
        "next_cursor": str(next_offset) if next_offset < len(filtered) else None,
    }


@router.get("/research_doc")
def research_doc(id: str = "") -> ResearchDocResponse:
    found = _doc_index().get(id)
    if found is None:
        return {"available": False, "error": "doc_not_allowed", "id": id}
    path, summary = found
    raw_bytes, markdown = _read_doc_source(path)
    return {
        **summary,
        "available": True,
        "markdown": research_index.serialize_research_doc_markdown(markdown),
        "size": len(markdown),
        "source_sha256": _source_sha256(raw_bytes),
        "source_bytes": len(raw_bytes),
    }


@router.get("/research_records")
def research_records():
    return records.list_research_records()


@router.get("/research_records/detail")
def research_record_detail(campaign: str = ""):
    return records.research_record_detail(campaign)


@router.get("/research_index")
def research_index_route():
    return research_index.serialize_research_index_response(research_index.list_research_index())

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
_CATALOG_DB: Final[Path] = REPO_ROOT / "legacy_non_authoritative_catalogs" / "research_assets.db"
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
    conn = _catalog_conn()
    if conn is None:
        return _catalog_unavailable("catalog DB missing or unreadable")
    try:
        counts: dict = {}
        for table in _CATALOG_TABLES:
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608 — 고정 테이블명
            except sqlite3.Error:
                counts[table] = None
        st = _CATALOG_DB.stat()
        return {"available": True, "db": "research_assets.db",
                "mtime": int(st.st_mtime), "size_bytes": st.st_size, "counts": counts}
    finally:
        conn.close()


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
