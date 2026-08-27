"""Read-only HTTP surface for deterministic AnalysisBundle v2 payloads."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

from fastapi import APIRouter
from pydantic import ConfigDict, TypeAdapter, ValidationError

from ai_strategy_loop.controller.research_truth_models import ResearchTruth
from ai_strategy_loop.dashboard.analysis_bundle_builder import (
    AnalysisBundleBuildError,
    build_legacy_job_analysis_bundle,
)
from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_api import (
    build_truth_payload,
    configured_jobs_dir,
)

analysis_bundle_router = APIRouter(
    prefix="/analysis-bundle",
    tags=["analysis-bundle"],
)

_API_SCHEMA: Final = "stom.analysis_bundle.api.v1"
_JOB_ID_RE: Final = re.compile(r"^[0-9A-Za-z가-힣_.-]{1,160}$")
_JSON_OBJECT = TypeAdapter(
    dict[str, JsonValue],
    config=ConfigDict(strict=True),
)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _base(job_id: str) -> dict[str, JsonValue]:
    return {
        "schema": _API_SCHEMA,
        "job_id": job_id,
        "bundle_available": False,
        "bundle": None,
        "content_sha256": None,
        "persistence": "none",
    }


def _unavailable(job_id: str, reason: str) -> dict[str, JsonValue]:
    payload = _base(job_id)
    payload["reason"] = reason
    return payload


def _record(job_id: str) -> dict[str, JsonValue]:
    raw = get_job_manager().get(job_id, log_tail=50)
    try:
        return _JSON_OBJECT.validate_python(raw)
    except ValidationError:
        return {"available": False, "job_id": job_id}


def _resolved_csv(record: dict[str, JsonValue]) -> Path | None:
    raw = record.get("csv_path")
    if not isinstance(raw, str) or not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(REPO_ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        return None
    return resolved if resolved.is_file() else None


def build_analysis_bundle_payload(
    job_id: str,
    record: dict[str, JsonValue],
    jobs_dir: Path,
) -> dict[str, JsonValue]:
    truth_payload = build_truth_payload(job_id, record, jobs_dir)
    if truth_payload.get("truth_available") is not True:
        reason = truth_payload.get("reason")
        return _unavailable(
            job_id,
            reason if isinstance(reason, str) else "truth_unavailable",
        )
    truth_value = truth_payload.get("truth")
    try:
        truth = ResearchTruth.model_validate_json(
            json.dumps(truth_value, ensure_ascii=False)
        )
        bundle = build_legacy_job_analysis_bundle(
            record,
            truth,
            _resolved_csv(record),
        )
    except (ValidationError, AnalysisBundleBuildError) as exc:
        return _unavailable(job_id, str(exc))
    payload = _base(job_id)
    payload["bundle_available"] = True
    payload["bundle"] = _JSON_OBJECT.validate_python(
        bundle.model_dump(mode="json", by_alias=True)
    )
    payload["content_sha256"] = bundle.content_sha256
    return payload


def current_analysis_bundle_payload(job_id: str) -> dict[str, JsonValue]:
    if _JOB_ID_RE.fullmatch(job_id) is None:
        return _unavailable(job_id, "invalid_job_id")
    return build_analysis_bundle_payload(
        job_id,
        _record(job_id),
        configured_jobs_dir(),
    )


@analysis_bundle_router.get("/job")
def analysis_bundle_job(job_id: str) -> dict[str, JsonValue]:
    return current_analysis_bundle_payload(job_id)
