"""Governed read-only dashboard index across research records, docs, logs, and registry rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

from ai_strategy_loop.dashboard import research_records

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
IndexKind = Literal["campaign", "doc", "update_log", "registry"]
Canonicality = Literal["canonical", "derived", "historical", "stale", "reference", "candidate"]
SourceAuthority = Literal[
    "raw_campaign",
    "curated_doc",
    "selected_update_log",
    "registry_entry",
    "historical_planning_context",
]

CANONICALITY_VALUES: Final[tuple[str, ...]] = (
    "canonical",
    "derived",
    "historical",
    "stale",
    "reference",
    "candidate",
)
SOURCE_AUTHORITY_VALUES: Final[tuple[str, ...]] = (
    "raw_campaign",
    "curated_doc",
    "selected_update_log",
    "registry_entry",
    "historical_planning_context",
)


class ResearchIndexError(TypedDict):
    source_path: str
    reason: str


class ResearchIndexRow(TypedDict):
    id: str
    kind: IndexKind
    source_path: str
    title: str
    updated_at: str
    canonicality: Canonicality
    source_authority: SourceAuthority
    detail_available: bool
    tags: list[str]
    related_ids: list[str]
    summary: str


class ResearchIndexResponse(TypedDict):
    count: int
    records: list[ResearchIndexRow]
    errors: list[ResearchIndexError]
    cache: dict[str, JsonValue]


class ResearchIndexDetailResponse(TypedDict, total=False):
    available: bool
    reason: str
    row: ResearchIndexRow
    markdown: str
    campaign: JsonObject
    registry_entry: JsonObject


@dataclass(frozen=True, slots=True)
class _SourceFile:
    path: Path
    rel_path: str


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT: Final[Path] = REPO_ROOT / ".omo" / "evidence" / "tmap-walkforward"
REGISTRY_JSON: Final[str] = ".omo/evidence/stom-reorg-20260618/research-registry.json"
SOURCE_INVENTORY: Final[str] = ".omo/evidence/stom-reorg-20260618/research-source-inventory.md"
DOC_ROOTS: Final[tuple[tuple[str, str], ...]] = (
    ("condition_research", "docs/research/condition_research"),
    ("good_results", "docs/reference/STOM_Good_Results"),
)
UPDATE_LOG_ROOT: Final[str] = "docs/update_log"
_SAFE_NAMESPACE = re.compile(r"^(campaign|doc|update_log|registry):(.{1,240})$")
_CACHE: dict[str, tuple[tuple[tuple[str, int, int], ...], ResearchIndexResponse]] = {}


def _repo_path(repo_root: Path, rel_path: str) -> Path:
    return (repo_root / rel_path).resolve()


def _relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _safe_rel(value: str) -> bool:
    return bool(value) and not value.startswith(("/", "\\")) and ".." not in Path(value).parts


def _iso_from_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _iso_from_epoch(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _title_from_markdown(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _as_object(value: JsonValue | None) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _as_list(value: JsonValue | None) -> list[JsonValue]:
    return value if isinstance(value, list) else []


def _as_text(value: JsonValue | None, fallback: str = "") -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return fallback


def _source_signature(paths: list[_SourceFile]) -> tuple[tuple[str, int, int], ...]:
    signature: list[tuple[str, int, int]] = []
    for source in sorted(paths, key=lambda item: item.rel_path):
        try:
            stat = source.path.stat()
        except OSError:
            continue
        signature.append((source.rel_path, int(stat.st_mtime_ns), int(stat.st_size)))
    return tuple(signature)


def _doc_sources(repo_root: Path) -> list[tuple[_SourceFile, str, str]]:
    rows: list[tuple[_SourceFile, str, str]] = []
    for category, rel_root in DOC_ROOTS:
        root = _repo_path(repo_root, rel_root)
        if root.is_dir():
            for path in sorted(root.rglob("*.md")):
                if path.is_file():
                    rel = _relative(repo_root, path)
                    doc_category = "wiki" if rel.startswith("docs/research/condition_research/wiki/") else category
                    rows.append((_SourceFile(path, rel), "doc", doc_category))
    update_root = _repo_path(repo_root, UPDATE_LOG_ROOT)
    if update_root.is_dir():
        for path in sorted(update_root.glob("*.md")):
            if path.is_file():
                rows.append((_SourceFile(path, _relative(repo_root, path)), "update_log", "update_log"))
    return rows


def _registry_source(repo_root: Path) -> _SourceFile | None:
    path = _repo_path(repo_root, REGISTRY_JSON)
    if path.is_file():
        return _SourceFile(path, REGISTRY_JSON)
    return None


def _source_inventory(repo_root: Path) -> _SourceFile | None:
    path = _repo_path(repo_root, SOURCE_INVENTORY)
    if path.is_file():
        return _SourceFile(path, SOURCE_INVENTORY)
    return None


def _campaign_source_files(repo_root: Path, evidence_root: Path) -> list[_SourceFile]:
    if not evidence_root.is_dir():
        return []
    patterns = ("*_summary.json", "*.jsonl", "*_pairs.json", "*_run.log", "*_log.txt")
    rows: list[_SourceFile] = []
    for pattern in patterns:
        for path in sorted(evidence_root.glob(pattern)):
            if path.is_file():
                rel = _relative(repo_root, path) if path.resolve().is_relative_to(repo_root.resolve()) else str(path)
                rows.append(_SourceFile(path, rel))
    return rows


def _collect_sources(repo_root: Path, evidence_root: Path) -> list[_SourceFile]:
    sources = [source for source, _, _ in _doc_sources(repo_root)]
    sources.extend(_campaign_source_files(repo_root, evidence_root))
    registry = _registry_source(repo_root)
    if registry is not None:
        sources.append(registry)
    source_inventory = _source_inventory(repo_root)
    if source_inventory is not None:
        sources.append(source_inventory)
    return sources


def _row(
    *,
    id: str,
    kind: IndexKind,
    source_path: str,
    title: str,
    updated_at: str,
    canonicality: Canonicality,
    source_authority: SourceAuthority,
    detail_available: bool = True,
    tags: list[str] | None = None,
    related_ids: list[str] | None = None,
    summary: str = "",
) -> ResearchIndexRow:
    return {
        "id": id,
        "kind": kind,
        "source_path": source_path,
        "title": title,
        "updated_at": updated_at,
        "canonicality": canonicality,
        "source_authority": source_authority,
        "detail_available": detail_available,
        "tags": sorted(set(tags or [])),
        "related_ids": sorted(set(related_ids or [])),
        "summary": summary,
    }


def _campaign_rows(repo_root: Path, evidence_root: Path) -> tuple[list[ResearchIndexRow], list[ResearchIndexError]]:
    response = research_records.list_research_records(evidence_root)
    rows: list[ResearchIndexRow] = []
    errors: list[ResearchIndexError] = [
        {"source_path": item["file"], "reason": item["reason"]} for item in response["errors"]
    ]
    root = Path(response["root"])
    for campaign in response["campaigns"]:
        artifacts = campaign["artifacts"]
        rel_source = ""
        for key in ("summary", "jsonl", "run_log"):
            value = artifacts.get(key)  # type: ignore[arg-type]
            if isinstance(value, str) and value:
                rel_source = _relative(repo_root, root / value)
                break
        if not rel_source:
            rel_source = _relative(repo_root, root) if root.exists() else str(root)
        best = campaign.get("best", {})
        title = str(best.get("label") or campaign["name"])
        rows.append(_row(
            id=f"campaign:{campaign['name']}",
            kind="campaign",
            source_path=rel_source,
            title=title,
            updated_at=_iso_from_epoch(float(campaign["updated_at"] or 0.0)),
            canonicality="derived",
            source_authority="raw_campaign",
            tags=["campaign", "evidence", *(key for key, value in artifacts.items() if value)],
            related_ids=[],
            summary=f"{campaign['candidate_count']} candidates; artifacts={artifacts}",
        ))
    return rows, errors


def _doc_rows(repo_root: Path) -> list[ResearchIndexRow]:
    rows: list[ResearchIndexRow] = []
    for source, kind_text, category in _doc_sources(repo_root):
        try:
            markdown = source.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        kind: IndexKind = "update_log" if kind_text == "update_log" else "doc"
        row_id = f"{kind}:{source.rel_path}"
        source_authority: SourceAuthority = "selected_update_log" if kind == "update_log" else "curated_doc"
        canonicality: Canonicality = "historical" if kind == "update_log" else "reference"
        rows.append(_row(
            id=row_id,
            kind=kind,
            source_path=source.rel_path,
            title=_title_from_markdown(markdown, source.path.stem.replace("_", " ")),
            updated_at=_iso_from_mtime(source.path),
            canonicality=canonicality,
            source_authority=source_authority,
            tags=[category, kind],
            related_ids=[],
            summary=markdown[:240].replace("\n", " "),
        ))
    return rows


def _registry_rows(repo_root: Path) -> tuple[list[ResearchIndexRow], list[ResearchIndexError]]:
    source = _registry_source(repo_root)
    if source is None:
        return [], []
    try:
        data = json.loads(source.path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        return [], [{"source_path": source.rel_path, "reason": exc.__class__.__name__}]
    rows: list[ResearchIndexRow] = []
    source_updated = _iso_from_mtime(source.path)
    for item in _as_list(_as_object(data).get("campaigns")):
        row = _as_object(item)
        campaign_id = _as_text(row.get("campaign_id"))
        if not campaign_id:
            continue
        related = [f"campaign:{row['dashboard_record']}"] if isinstance(row.get("dashboard_record"), str) and row.get("dashboard_record") else []
        related.extend(_related_source_ids(row.get("source_files")))
        rows.append(_row(
            id=f"registry:campaign:{campaign_id}",
            kind="registry",
            source_path=source.rel_path,
            title=_as_text(row.get("display_alias"), campaign_id),
            updated_at=source_updated,
            canonicality="canonical" if row.get("status") == "canonical_current_baseline" else "derived",
            source_authority="registry_entry",
            tags=["registry", "campaign", _as_text(row.get("evidence_type")), _as_text(row.get("status"))],
            related_ids=related,
            summary=_as_text(row.get("next_action")),
        ))
    for item in _as_list(_as_object(data).get("candidates")):
        row = _as_object(item)
        machine_name = _as_text(row.get("machine_name"))
        if not machine_name:
            continue
        related = [f"campaign:{row['related_dashboard_record']}"] if isinstance(row.get("related_dashboard_record"), str) and row.get("related_dashboard_record") else []
        related.extend(_related_source_ids(row.get("source_files")))
        rows.append(_row(
            id=f"registry:{machine_name}",
            kind="registry",
            source_path=source.rel_path,
            title=_as_text(row.get("display_alias"), machine_name),
            updated_at=source_updated,
            canonicality="candidate",
            source_authority="registry_entry",
            tags=["registry", "candidate", _as_text(row.get("candidate_family")), _as_text(row.get("evidence_type")), _as_text(row.get("oos_status")), _as_text(row.get("promotion_status"))],
            related_ids=related,
            summary=_as_text(row.get("next_action")),
        ))
    inventory = _source_inventory(repo_root)
    if inventory is not None:
        rows.append(_row(
            id="registry:source-inventory",
            kind="registry",
            source_path=inventory.rel_path,
            title="Research source inventory",
            updated_at=_iso_from_mtime(inventory.path),
            canonicality="historical",
            source_authority="historical_planning_context",
            tags=["registry", "source_inventory", "historical"],
            related_ids=[],
            summary="Allowlisted context document; not raw performance evidence.",
        ))
    return rows, []


def _related_source_ids(value: JsonValue | None) -> list[str]:
    related: list[str] = []
    for item in _as_list(value):
        if not isinstance(item, str) or not _safe_rel(item):
            continue
        if item.startswith("docs/update_log/"):
            related.append(f"update_log:{item}")
        elif item.startswith("docs/"):
            related.append(f"doc:{item}")
    return related


def _normalize_rows(rows: list[ResearchIndexRow]) -> list[ResearchIndexRow]:
    seen: set[str] = set()
    out: list[ResearchIndexRow] = []
    for row in sorted(rows, key=lambda item: (item["updated_at"], item["id"]), reverse=True):
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        out.append(row)
    return out


def list_research_index(repo_root: Path | None = None, evidence_root: Path | None = None) -> ResearchIndexResponse:
    root = (repo_root or REPO_ROOT).resolve()
    evidence = (evidence_root or (root / ".omo" / "evidence" / "tmap-walkforward")).resolve()
    sources = _collect_sources(root, evidence)
    signature = _source_signature(sources)
    cache_key = f"{root}|{evidence}"
    cached = _CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        response = cached[1]
        return {**response, "cache": {"hit": True, "sources": len(signature)}}

    rows: list[ResearchIndexRow] = []
    errors: list[ResearchIndexError] = []
    campaign_rows, campaign_errors = _campaign_rows(root, evidence)
    registry_rows, registry_errors = _registry_rows(root)
    rows.extend(campaign_rows)
    rows.extend(_doc_rows(root))
    rows.extend(registry_rows)
    errors.extend(campaign_errors)
    errors.extend(registry_errors)
    response: ResearchIndexResponse = {
        "count": len(_normalize_rows(rows)),
        "records": _normalize_rows(rows),
        "errors": errors,
        "cache": {"hit": False, "sources": len(signature)},
    }
    _CACHE[cache_key] = (signature, response)
    return response


def research_index_detail(id: str, repo_root: Path | None = None, evidence_root: Path | None = None) -> ResearchIndexDetailResponse:
    root = (repo_root or REPO_ROOT).resolve()
    evidence = (evidence_root or (root / ".omo" / "evidence" / "tmap-walkforward")).resolve()
    match = _SAFE_NAMESPACE.fullmatch(id)
    if match is None:
        return {"available": False, "reason": "invalid_id"}
    namespace, payload = match.groups()
    if not _safe_rel(payload) and namespace in {"doc", "update_log"}:
        return {"available": False, "reason": "invalid_id"}
    index = list_research_index(root, evidence)
    row = next((item for item in index["records"] if item["id"] == id), None)
    if row is None:
        return {"available": False, "reason": "missing_id"}
    if not row["detail_available"]:
        return {"available": False, "reason": "detail_unavailable", "row": row}
    if namespace == "campaign":
        detail = research_records.research_record_detail(payload, evidence)
        return {"available": bool(detail.get("available")), "row": row, "campaign": _as_object(detail.get("campaign"))}
    if namespace in {"doc", "update_log"}:
        path = _repo_path(root, row["source_path"])
        if not path.is_file() or not path.resolve().is_relative_to(root):
            return {"available": False, "reason": "disallowed_path", "row": row}
        markdown = path.read_text(encoding="utf-8", errors="replace")
        return {"available": True, "row": row, "markdown": markdown}
    if namespace == "registry":
        entry = _registry_entry(payload, root)
        return {"available": entry is not None, "row": row, "registry_entry": entry or {}}
    return {"available": False, "reason": "invalid_id"}


def _registry_entry(payload: str, repo_root: Path) -> JsonObject | None:
    source = _registry_source(repo_root)
    if source is None:
        return None
    try:
        data = _as_object(json.loads(source.path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if payload.startswith("campaign:"):
        campaign_id = payload.split(":", 1)[1]
        for item in _as_list(data.get("campaigns")):
            row = _as_object(item)
            if row.get("campaign_id") == campaign_id:
                return row
        return None
    if payload == "source-inventory":
        return {"source_path": SOURCE_INVENTORY, "note": "historical planning context"}
    for item in _as_list(data.get("candidates")):
        row = _as_object(item)
        if row.get("machine_name") == payload:
            return row
    return None
