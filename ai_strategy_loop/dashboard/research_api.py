"""Read-only research documentation and index-comparison routes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, TypedDict

from fastapi import APIRouter

from ai_strategy_loop.dashboard import research_index
from ai_strategy_loop.dashboard import research_records as records
from ai_strategy_loop.dashboard.analysis_snapshot import analysis_router


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
