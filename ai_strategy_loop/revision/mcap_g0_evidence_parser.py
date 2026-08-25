"""Strict JSON-boundary parsing for G0 Truth and Analysis Bundle payloads."""

from __future__ import annotations

import json

from pydantic import ValidationError

from ai_strategy_loop.controller.research_truth_models import ResearchTruth
from ai_strategy_loop.dashboard.analysis_bundle_models import AnalysisBundleV2
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue


def unavailable_reason(payload: dict[str, JsonValue]) -> str | None:
    value = payload.get("reason")
    return value if isinstance(value, str) else None


def parse_truth_payload(payload: dict[str, JsonValue]) -> ResearchTruth | None:
    if payload.get("truth_available") is not True:
        return None
    try:
        return ResearchTruth.model_validate_json(
            json.dumps(payload.get("truth"), ensure_ascii=False)
        )
    except ValidationError:
        return None


def parse_bundle_payload(payload: dict[str, JsonValue]) -> AnalysisBundleV2 | None:
    if payload.get("bundle_available") is not True:
        return None
    try:
        return AnalysisBundleV2.model_validate_json(
            json.dumps(payload.get("bundle"), ensure_ascii=False)
        )
    except ValidationError:
        return None
