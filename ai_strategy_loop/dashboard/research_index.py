"""Governed read-only dashboard index across research records, docs, logs, and registry rows."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict, cast

from ai_strategy_loop.dashboard import research_records

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]
IndexKind = Literal["campaign", "doc", "update_log", "registry", "hof", "loop_run", "decision", "evidence"]
Canonicality = Literal["canonical", "derived", "historical", "stale", "reference", "candidate"]
SourceAuthority = Literal[
    "raw_campaign",
    "curated_doc",
    "selected_update_log",
    "registry_entry",
    "historical_planning_context",
    "hall_of_fame",
    "loop_runs_db",
    "decision_log",
    "evidence_artifact",
]
TraceStatus = Literal["linked", "unlinked", "unknown"]

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
    "hall_of_fame",
    "loop_runs_db",
    "decision_log",
    "evidence_artifact",
)
TRACE_STATUS_VALUES: Final[tuple[str, ...]] = ("linked", "unlinked", "unknown")


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
    trace_status: TraceStatus
    exact_link: str
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
REFERENCE_STRATEGIES_JSON: Final[str] = "ai_strategy_loop/dashboard/reference_strategies.json"
DECISIONS_JSONL: Final[str] = ".omo/evidence/decisions.jsonl"
LOOP_RUNS_DB: Final[str] = "ai_strategy_loop/state/loop_runs.db"
EVIDENCE_ROOT_REL: Final[str] = ".omo/evidence"
EVIDENCE_ARTIFACT_SUFFIXES: Final[tuple[str, ...]] = (".json", ".jsonl", ".md", ".txt")
_SAFE_NAMESPACE = re.compile(r"^(campaign|doc|update_log|registry|hof|loop_run|decision|evidence):(.{1,240})$")
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


def _static_governance_sources(repo_root: Path) -> list[_SourceFile]:
    rows: list[_SourceFile] = []
    for rel_path in (REFERENCE_STRATEGIES_JSON, DECISIONS_JSONL, LOOP_RUNS_DB):
        path = _repo_path(repo_root, rel_path)
        if path.is_file():
            rows.append(_SourceFile(path, rel_path))
    return rows


def _evidence_artifact_sources(repo_root: Path) -> list[_SourceFile]:
    root = _repo_path(repo_root, EVIDENCE_ROOT_REL)
    if not root.is_dir():
        return []
    rows: list[_SourceFile] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in EVIDENCE_ARTIFACT_SUFFIXES:
            try:
                rel = _relative(repo_root, path)
            except ValueError:
                continue
            rows.append(_SourceFile(path, rel))
    return rows


def _collect_sources(repo_root: Path, evidence_root: Path) -> list[_SourceFile]:
    sources = [source for source, _, _ in _doc_sources(repo_root)]
    sources.extend(_campaign_source_files(repo_root, evidence_root))
    sources.extend(_evidence_artifact_sources(repo_root))
    sources.extend(_static_governance_sources(repo_root))
    registry = _registry_source(repo_root)
    if registry is not None:
        sources.append(registry)
    source_inventory = _source_inventory(repo_root)
    if source_inventory is not None:
        sources.append(source_inventory)
    return _dedupe_sources(sources)


def _dedupe_sources(sources: list[_SourceFile]) -> list[_SourceFile]:
    seen: set[str] = set()
    out: list[_SourceFile] = []
    for source in sources:
        if source.rel_path in seen:
            continue
        seen.add(source.rel_path)
        out.append(source)
    return out


def _trace_status(kind: IndexKind, related_ids: list[str]) -> TraceStatus:
    if related_ids:
        return "linked"
    if kind in {"campaign", "registry", "loop_run", "decision", "evidence"}:
        return "unlinked"
    return "unknown"


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
    trace_status: TraceStatus | None = None,
) -> ResearchIndexRow:
    related = sorted(set(related_ids or []))
    resolved_trace = trace_status or _trace_status(kind, related)
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
        "related_ids": related,
        "trace_status": resolved_trace,
        "exact_link": f"research-index://{id}",
        "summary": summary,
    }


def _campaign_rows(repo_root: Path, evidence_root: Path) -> tuple[list[ResearchIndexRow], list[ResearchIndexError]]:
    response = research_records.list_research_records(evidence_root)
    rows: list[ResearchIndexRow] = []
    errors: list[ResearchIndexError] = [
        {"source_path": item["file"], "reason": item["reason"]} for item in response["errors"]
    ]
    root = evidence_root.resolve()
    for campaign in response["campaigns"]:
        artifacts = campaign["artifacts"]
        rel_source = ""
        for key in ("summary", "jsonl", "run_log"):
            value = artifacts.get(key)  # type: ignore[arg-type]
            if isinstance(value, str) and _safe_rel(value):
                artifact_path = (root / value).resolve()
                if artifact_path.is_relative_to(root):
                    try:
                        rel_source = _relative(repo_root, artifact_path)
                    except ValueError:
                        pass
                if rel_source:
                    break
        if not rel_source:
            try:
                rel_source = _relative(repo_root, root)
            except ValueError:
                rel_source = response["root"]
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


def _summary_from_file(path: Path, max_chars: int = 240) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            keys = ", ".join(str(key) for key in list(parsed.keys())[:8])
            return f"JSON object keys: {keys}" if keys else "JSON object"
        if isinstance(parsed, list):
            return f"JSON list rows: {len(parsed)}"
    first_lines = " ".join(line.strip() for line in text.splitlines()[:4] if line.strip())
    return (first_lines or text[:max_chars]).replace("\n", " ")[:max_chars]


def _hof_rows(repo_root: Path) -> list[ResearchIndexRow]:
    rows: list[ResearchIndexRow] = []
    path = _repo_path(repo_root, REFERENCE_STRATEGIES_JSON)
    if path.is_file():
        summary = _summary_from_file(path)
        rows.append(_row(
            id="hof:reference-strategies",
            kind="hof",
            source_path=REFERENCE_STRATEGIES_JSON,
            title="Hall of Fame reference strategies",
            updated_at=_iso_from_mtime(path),
            canonicality="reference",
            source_authority="hall_of_fame",
            tags=["hof", "reference_strategies"],
            related_ids=[],
            summary=summary,
        ))
    db_path = _repo_path(repo_root, LOOP_RUNS_DB)
    if db_path.is_file():
        rows.append(_row(
            id="hof:loop-runs-ai",
            kind="hof",
            source_path=LOOP_RUNS_DB,
            title="Hall of Fame AI candidates from loop_runs.db",
            updated_at=_iso_from_mtime(db_path),
            canonicality="derived",
            source_authority="hall_of_fame",
            tags=["hof", "ai", "loop_runs"],
            related_ids=["loop_run:loop_runs.db"],
            summary="AI Hall of Fame rows are projected from loop_runs.db gate-passed generations.",
        ))
    return rows


def _loop_run_rows(repo_root: Path) -> tuple[list[ResearchIndexRow], list[ResearchIndexError]]:
    db_path = _repo_path(repo_root, LOOP_RUNS_DB)
    if not db_path.is_file():
        return [], []
    rows: list[ResearchIndexRow] = []
    errors: list[ResearchIndexError] = []
    try:
        from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

        state = LoopState(readonly=True)
        try:
            runs = state.list_runs()
            generations = state.get_all_generations()
        finally:
            state.close()
    except Exception as exc:  # noqa: BLE001 - DB absent/schema drift must not break index.
        return [], [{"source_path": LOOP_RUNS_DB, "reason": exc.__class__.__name__}]
    if not runs:
        rows.append(_row(
            id="loop_run:loop_runs.db",
            kind="loop_run",
            source_path=LOOP_RUNS_DB,
            title="loop_runs.db (0 runs)",
            updated_at=_iso_from_mtime(db_path),
            canonicality="historical",
            source_authority="loop_runs_db",
            tags=["loop_runs", "db", "empty"],
            related_ids=[],
            summary="loop_runs.db exists but has no run rows in this worktree.",
        ))
        return rows, errors
    gen_counts: dict[str, int] = {}
    for generation in generations:
        run_id = _as_text(generation.get("run_id"))
        if run_id:
            gen_counts[run_id] = gen_counts.get(run_id, 0) + 1
    for run in runs:
        run_id = _as_text(run.get("run_id"))
        if not run_id:
            continue
        started = float(run.get("started_at") or 0.0)
        rows.append(_row(
            id=f"loop_run:{run_id}",
            kind="loop_run",
            source_path=LOOP_RUNS_DB,
            title=f"Loop run {run_id}",
            updated_at=_iso_from_epoch(started or db_path.stat().st_mtime),
            canonicality="historical",
            source_authority="loop_runs_db",
            tags=["loop_runs", _as_text(run.get("status")), f"gens:{gen_counts.get(run_id, 0)}"],
            related_ids=[],
            summary=f"status={run.get('status')}; generations={gen_counts.get(run_id, 0)}; best_gen={run.get('best_gen')}; best_score={run.get('best_score')}",
        ))
    return rows, errors


def _decision_rows(repo_root: Path) -> tuple[list[ResearchIndexRow], list[ResearchIndexError]]:
    path = _repo_path(repo_root, DECISIONS_JSONL)
    if not path.is_file():
        return [], []
    rows: list[ResearchIndexRow] = []
    errors: list[ResearchIndexError] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [], [{"source_path": DECISIONS_JSONL, "reason": exc.__class__.__name__}]
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            payload = {"raw": stripped}
        item = _as_object(payload)
        title = (
            _as_text(item.get("title"))
            or _as_text(item.get("decision"))
            or _as_text(item.get("action"))
            or f"Decision {idx}"
        )
        timestamp = _as_text(item.get("ts")) or _as_text(item.get("timestamp")) or _as_text(item.get("created_at"))
        rows.append(_row(
            id=f"decision:{idx}",
            kind="decision",
            source_path=DECISIONS_JSONL,
            title=title,
            updated_at=timestamp if timestamp else _iso_from_mtime(path),
            canonicality="historical",
            source_authority="decision_log",
            tags=["decision", "append_only"],
            related_ids=_related_source_ids(item.get("source_files")),
            summary=stripped[:240],
        ))
    if not rows:
        rows.append(_row(
            id="decision:decisions.jsonl",
            kind="decision",
            source_path=DECISIONS_JSONL,
            title="Decisions log (empty)",
            updated_at=_iso_from_mtime(path),
            canonicality="historical",
            source_authority="decision_log",
            tags=["decision", "append_only", "empty"],
            related_ids=[],
            summary="Append-only decisions log exists but has no records.",
        ))
    return rows, errors


def _evidence_artifact_rows(repo_root: Path) -> list[ResearchIndexRow]:
    rows: list[ResearchIndexRow] = []
    for source in _evidence_artifact_sources(repo_root):
        if source.rel_path in {REGISTRY_JSON, SOURCE_INVENTORY, DECISIONS_JSONL}:
            continue
        summary = _summary_from_file(source.path)
        tags = ["evidence", source.path.suffix.lower().lstrip("."), source.path.parent.name]
        rows.append(_row(
            id=f"evidence:{source.rel_path}",
            kind="evidence",
            source_path=source.rel_path,
            title=source.path.stem.replace("_", " ").replace("-", " "),
            updated_at=_iso_from_mtime(source.path),
            canonicality="derived" if source.path.suffix.lower() in {".json", ".jsonl"} else "historical",
            source_authority="evidence_artifact",
            tags=tags,
            related_ids=[],
            summary=summary,
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
        elif item.startswith(".omo/evidence/"):
            related.append(f"evidence:{item}")
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


def _resolve_row_links(rows: list[ResearchIndexRow]) -> list[ResearchIndexRow]:
    valid_ids = {row["id"] for row in rows}
    resolved: list[ResearchIndexRow] = []
    for row in rows:
        related = [item for item in row["related_ids"] if item in valid_ids and item != row["id"]]
        if related == row["related_ids"] and row["trace_status"] == _trace_status(row["kind"], related):
            resolved.append(row)
            continue
        resolved_row: ResearchIndexRow = {
            **row,
            "related_ids": related,
            "trace_status": _trace_status(row["kind"], related),
        }
        resolved.append(resolved_row)
    return resolved


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
    loop_rows, loop_errors = _loop_run_rows(root)
    decision_rows, decision_errors = _decision_rows(root)
    rows.extend(campaign_rows)
    rows.extend(_doc_rows(root))
    rows.extend(_evidence_artifact_rows(root))
    rows.extend(_hof_rows(root))
    rows.extend(loop_rows)
    rows.extend(decision_rows)
    rows.extend(registry_rows)
    rows = _resolve_row_links(rows)
    errors.extend(campaign_errors)
    errors.extend(registry_errors)
    errors.extend(loop_errors)
    errors.extend(decision_errors)
    response: ResearchIndexResponse = {
        "count": len(_normalize_rows(rows)),
        "records": _normalize_rows(rows),
        "errors": errors,
        "cache": {"hit": False, "sources": len(signature)},
    }
    _CACHE[cache_key] = (signature, response)
    return response

def _redact_markdown_absolute_paths(markdown: str) -> str:
    """Apply the shared absolute-path redactor to path tokens in markdown text."""
    chunks: list[str] = []
    cursor = 0
    token_boundaries = " \t\r\n([{\"'`="
    trailing_punctuation = ".,;:!?)]}>`"
    while cursor < len(markdown):
        path_start = next(
            (
                index
                for index in range(cursor, len(markdown))
                if (index == 0 or markdown[index - 1] in token_boundaries)
                and research_records._ABSOLUTE_PATH.match(markdown[index:])
            ),
            None,
        )
        if path_start is None:
            chunks.append(markdown[cursor:])
            break
        chunks.append(markdown[cursor:path_start])
        token_end = path_start
        while token_end < len(markdown) and not markdown[token_end].isspace():
            token_end += 1
        path_end = token_end
        while path_end > path_start and markdown[path_end - 1] in trailing_punctuation:
            path_end -= 1
        redacted = research_records._redact_absolute_paths(markdown[path_start:path_end])
        chunks.append(redacted if isinstance(redacted, str) else markdown[path_start:path_end])
        chunks.append(markdown[path_end:token_end])
        cursor = token_end
    return "".join(chunks)


def _serialize_detail_response(response: ResearchIndexDetailResponse) -> ResearchIndexDetailResponse:
    """Redact absolute paths from all detail payloads without mutating their sources."""
    serialized = cast(ResearchIndexDetailResponse, research_records._redact_absolute_paths(response))
    markdown = serialized.get("markdown")
    if isinstance(markdown, str):
        serialized["markdown"] = _redact_markdown_absolute_paths(markdown)
    return serialized




def research_index_detail(id: str, repo_root: Path | None = None, evidence_root: Path | None = None) -> ResearchIndexDetailResponse:
    root = (repo_root or REPO_ROOT).resolve()
    evidence = (evidence_root or (root / ".omo" / "evidence" / "tmap-walkforward")).resolve()
    match = _SAFE_NAMESPACE.fullmatch(id)
    if match is None:
        return _serialize_detail_response({"available": False, "reason": "invalid_id"})
    namespace, payload = match.groups()
    if not _safe_rel(payload) and namespace in {"doc", "update_log", "evidence"}:
        return _serialize_detail_response({"available": False, "reason": "invalid_id"})
    index = list_research_index(root, evidence)
    row = next((item for item in index["records"] if item["id"] == id), None)
    if row is None:
        return _serialize_detail_response({"available": False, "reason": "missing_id"})
    if not row["detail_available"]:
        return _serialize_detail_response({"available": False, "reason": "detail_unavailable", "row": row})
    if namespace == "campaign":
        detail = research_records.research_record_detail(payload, evidence)
        return _serialize_detail_response(
            {"available": bool(detail.get("available")), "row": row, "campaign": _as_object(detail.get("campaign"))}
        )
    if namespace in {"doc", "update_log", "evidence"}:
        path = _repo_path(root, row["source_path"])
        if not path.is_file() or not path.resolve().is_relative_to(root):
            return _serialize_detail_response({"available": False, "reason": "disallowed_path", "row": row})
        markdown = path.read_text(encoding="utf-8", errors="replace")
        return _serialize_detail_response({"available": True, "row": row, "markdown": markdown})
    if namespace == "registry":
        entry = _registry_entry(payload, root)
        return _serialize_detail_response({"available": entry is not None, "row": row, "registry_entry": entry or {}})
    if namespace == "hof":
        entry = _hof_entry(payload, root)
        return _serialize_detail_response({"available": entry is not None, "row": row, "registry_entry": entry or {}})
    if namespace == "loop_run":
        entry = _loop_run_entry(payload, root)
        return _serialize_detail_response({"available": entry is not None, "row": row, "registry_entry": entry or {}})
    if namespace == "decision":
        entry = _decision_entry(payload, root)
        return _serialize_detail_response({"available": entry is not None, "row": row, "registry_entry": entry or {}})
    return _serialize_detail_response({"available": False, "reason": "invalid_id"})


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


def _hof_entry(payload: str, repo_root: Path) -> JsonObject | None:
    if payload == "reference-strategies":
        path = _repo_path(repo_root, REFERENCE_STRATEGIES_JSON)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            data = []
        return {
            "source_path": REFERENCE_STRATEGIES_JSON,
            "kind": "reference_strategies",
            "row_count": len(data) if isinstance(data, list) else None,
            "items": data if isinstance(data, list) else [],
        }
    if payload == "loop-runs-ai":
        return {
            "source_path": LOOP_RUNS_DB,
            "kind": "loop_runs_hof_projection",
            "note": "AI Hall of Fame rows are derived from read-only loop_runs.db gate-passed generations.",
        }
    return None


def _loop_run_entry(payload: str, repo_root: Path) -> JsonObject | None:
    if payload == "loop_runs.db":
        path = _repo_path(repo_root, LOOP_RUNS_DB)
        return {"source_path": LOOP_RUNS_DB, "exists": path.is_file(), "note": "loop_runs.db summary row"}
    try:
        from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

        state = LoopState(readonly=True)
        try:
            row = state.get_run(payload)
            generations = state.get_generations(payload) if row is not None else []
        finally:
            state.close()
    except Exception:  # noqa: BLE001
        return None
    if row is None:
        return None
    return {"run": row, "generations": generations}


def _decision_entry(payload: str, repo_root: Path) -> JsonObject | None:
    path = _repo_path(repo_root, DECISIONS_JSONL)
    if not path.is_file():
        return None
    try:
        idx = int(payload)
        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    except (OSError, ValueError):
        return {"source_path": DECISIONS_JSONL, "note": "decisions.jsonl summary row"} if payload == "decisions.jsonl" else None
    if idx < 1 or idx > len(lines):
        return None
    try:
        parsed = json.loads(lines[idx - 1])
    except json.JSONDecodeError:
        parsed = {"raw": lines[idx - 1]}
    return _as_object(parsed)
