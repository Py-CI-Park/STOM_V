"""Read-only index over local research and backtest evidence files."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import NotRequired, TypedDict

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ResearchRecordError(TypedDict):
    file: str
    reason: str


class CandidateRecord(TypedDict, total=False):
    label: str
    event: str
    round: int
    gate: bool
    profit: float
    mdd: float
    trades: int
    daily: float
    ts: float


class CampaignArtifacts(TypedDict):
    summary: str | None
    jsonl: str | None
    run_log: str | None
    pairs: list[str]


class CampaignRecord(TypedDict):
    name: str
    updated_at: float
    summary: dict[str, JsonValue]
    best: dict[str, JsonValue]
    candidates: list[CandidateRecord]
    candidate_count: int
    artifacts: CampaignArtifacts


class ResearchRecordsResponse(TypedDict):
    root: str
    count: int
    campaigns: list[CampaignRecord]
    errors: list[ResearchRecordError]


class ResearchRecordDetailResponse(TypedDict):
    available: bool
    reason: NotRequired[str]
    campaign: NotRequired[CampaignRecord]


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = REPO_ROOT / ".omo" / "evidence" / "tmap-walkforward"
_SAFE_CAMPAIGN = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")
_RECORD_CACHE_LIMIT = 8
_RECORD_CACHE_LOCK = RLock()
_RECORD_CACHE: OrderedDict[str, tuple[tuple[tuple[str, int, int], ...], ResearchRecordsResponse, dict[str, CampaignRecord]]] = OrderedDict()


def _empty_artifacts() -> CampaignArtifacts:
    return {"summary": None, "jsonl": None, "run_log": None, "pairs": []}


def _empty_campaign(name: str) -> CampaignRecord:
    return {
        "name": name,
        "updated_at": 0.0,
        "summary": {},
        "best": {},
        "candidates": [],
        "candidate_count": 0,
        "artifacts": _empty_artifacts(),
    }


def _campaign_from_pairs(path: Path) -> str:
    match = re.match(r"(.+)_r\d+_pairs$", path.stem)
    if match is not None:
        return match.group(1)
    return path.stem


def _campaign_from_log(path: Path) -> str:
    stem = path.stem
    if stem.endswith("_run"):
        return stem[:-4]
    if stem.endswith("_log"):
        return stem[:-4]
    return stem


def _safe_campaign_name(name: str) -> bool:
    return bool(_SAFE_CAMPAIGN.fullmatch(name)) and ".." not in name


def _read_json(path: Path, errors: list[ResearchRecordError]) -> JsonValue | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append({"file": path.name, "reason": f"json:{exc.msg}"})
    except OSError as exc:
        errors.append({"file": path.name, "reason": f"io:{exc.strerror or exc.__class__.__name__}"})
    except UnicodeError as exc:
        errors.append({"file": path.name, "reason": f"encoding:{exc.__class__.__name__}"})
    return None


def _as_dict(value: JsonValue | None) -> dict[str, JsonValue]:
    if isinstance(value, dict):
        return value
    return {}


def _as_float(value: JsonValue | None) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _as_int(value: JsonValue | None) -> int | None:
    num = _as_float(value)
    if num is None:
        return None
    return int(num)


def _candidate_from(raw: dict[str, JsonValue]) -> CandidateRecord | None:
    if raw.get("event") != "cand":
        return None
    label = raw.get("label")
    if not isinstance(label, str) or not label:
        return None
    out: CandidateRecord = {"label": label, "event": "cand"}
    round_no = _as_int(raw.get("round"))
    profit = _as_float(raw.get("profit"))
    mdd = _as_float(raw.get("mdd"))
    trades = _as_int(raw.get("trades"))
    daily = _as_float(raw.get("daily"))
    ts = _as_float(raw.get("ts"))
    if round_no is not None:
        out["round"] = round_no
    if isinstance(raw.get("gate"), bool):
        out["gate"] = bool(raw["gate"])
    if profit is not None:
        out["profit"] = profit
    if mdd is not None:
        out["mdd"] = mdd
    if trades is not None:
        out["trades"] = trades
    if daily is not None:
        out["daily"] = daily
    if ts is not None:
        out["ts"] = ts
    return out


def _load_candidates(path: Path, errors: list[ResearchRecordError]) -> list[CandidateRecord]:
    rows: list[CandidateRecord] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append({"file": path.name, "reason": f"io:{exc.strerror or exc.__class__.__name__}"})
        return rows
    except UnicodeError as exc:
        errors.append({"file": path.name, "reason": f"encoding:{exc.__class__.__name__}"})
        return rows
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append({"file": path.name, "reason": f"line{idx}:json:{exc.msg}"})
            continue
        candidate = _candidate_from(_as_dict(parsed))
        if candidate is not None:
            rows.append(candidate)
    rows.sort(key=lambda row: float(row.get("profit", 0.0)), reverse=True)
    return rows
def _record_source_paths(evidence: Path) -> dict[str, list[Path]]:
    return {
        "summaries": sorted(evidence.glob("*_summary.json")),
        "jsonl": sorted(evidence.glob("*.jsonl")),
        "pairs": sorted(evidence.glob("*_pairs.json")),
        "logs": sorted(list(evidence.glob("*_run.log")) + list(evidence.glob("*_log.txt"))),
    }


def _record_source_signature(paths: dict[str, list[Path]]) -> tuple[tuple[str, int, int], ...]:
    signature: list[tuple[str, int, int]] = []
    for group in ("summaries", "jsonl", "pairs", "logs"):
        for path in paths[group]:
            try:
                stat = path.stat()
            except OSError:
                continue
            signature.append((path.name, stat.st_mtime_ns, stat.st_size))
    return tuple(signature)


def _build_research_records(
    evidence: Path,
    paths: dict[str, list[Path]],
) -> tuple[ResearchRecordsResponse, dict[str, CampaignRecord]]:
    campaigns: dict[str, CampaignRecord] = {}
    errors: list[ResearchRecordError] = []
    for summary_path in paths["summaries"]:
        name = summary_path.stem.removesuffix("_summary")
        data = _as_dict(_read_json(summary_path, errors))
        if not data:
            continue
        campaign = campaigns.setdefault(name, _empty_campaign(name))
        campaign["summary"] = data
        campaign["best"] = _as_dict(data.get("best_overall"))
        campaign["artifacts"]["summary"] = summary_path.name
        campaign["updated_at"] = max(campaign["updated_at"], summary_path.stat().st_mtime)

    for jsonl_path in paths["jsonl"]:
        name = jsonl_path.stem
        candidates = _load_candidates(jsonl_path, errors)
        if not candidates and name not in campaigns:
            continue
        campaign = campaigns.setdefault(name, _empty_campaign(name))
        campaign["candidates"] = candidates
        campaign["candidate_count"] = len(candidates)
        campaign["artifacts"]["jsonl"] = jsonl_path.name
        campaign["updated_at"] = max(campaign["updated_at"], jsonl_path.stat().st_mtime)

    for pairs_path in paths["pairs"]:
        name = _campaign_from_pairs(pairs_path)
        campaign = campaigns.get(name)
        if campaign is None:
            continue
        campaign["artifacts"]["pairs"].append(pairs_path.name)
        campaign["updated_at"] = max(campaign["updated_at"], pairs_path.stat().st_mtime)

    for log_path in paths["logs"]:
        name = _campaign_from_log(log_path)
        campaign = campaigns.get(name)
        if campaign is None:
            continue
        campaign["artifacts"]["run_log"] = log_path.name
        campaign["updated_at"] = max(campaign["updated_at"], log_path.stat().st_mtime)

    items = list(campaigns.values())
    items.sort(key=lambda row: (row["updated_at"], row["name"]), reverse=True)
    response: ResearchRecordsResponse = {
        "root": str(evidence), "count": len(items), "campaigns": items, "errors": errors,
    }
    return response, {item["name"]: item for item in items}


def _cached_research_records(
    root: Path | None,
) -> tuple[ResearchRecordsResponse, dict[str, CampaignRecord]]:
    evidence = root if root is not None else EVIDENCE_ROOT
    if not evidence.is_dir():
        return {"root": str(evidence), "count": 0, "campaigns": [], "errors": []}, {}
    cache_key = str(evidence.resolve())
    with _RECORD_CACHE_LOCK:
        paths = _record_source_paths(evidence)
        signature = _record_source_signature(paths)
        cached = _RECORD_CACHE.get(cache_key)
        if cached is not None and cached[0] == signature:
            _RECORD_CACHE.move_to_end(cache_key)
            return cached[1], cached[2]
        response, by_campaign = _build_research_records(evidence, paths)
        _RECORD_CACHE[cache_key] = (signature, response, by_campaign)
        _RECORD_CACHE.move_to_end(cache_key)
        while len(_RECORD_CACHE) > _RECORD_CACHE_LIMIT:
            _RECORD_CACHE.popitem(last=False)
        return response, by_campaign




def list_research_records(root: Path | None = None) -> ResearchRecordsResponse:
    """Return a source-signature cached, read-only campaign listing."""
    return _cached_research_records(root)[0]


def research_record_detail(campaign: str, root: Path | None = None) -> ResearchRecordDetailResponse:
    if not _safe_campaign_name(campaign):
        return {"available": False, "reason": "invalid_campaign"}
    item = _cached_research_records(root)[1].get(campaign)
    if item is None:
        return {"available": False, "reason": "missing_campaign"}
    return {"available": True, "campaign": item}
