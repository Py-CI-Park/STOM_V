"""Fail-closed D3 screen gate and conditional D4 admission decision."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


def decide_d3_screen(screen: Mapping[str, Any]) -> dict[str, Any]:
    if screen.get("schema") != "stom.d3_mcap_engine_screen.v1":
        raise ValueError("D3 screen schema mismatch")
    rows = list(screen.get("rows") or [])
    if screen.get("verdict") != "D3_SCREEN_COMPLETED" or len(rows) != 40:
        raise ValueError("D3 official screen is incomplete")
    if any(not row.get("source_snapshot_match") for row in rows):
        raise ValueError("D3 source snapshot mismatch")
    statuses = Counter(str(row.get("status")) for row in rows)
    advanced = [row for row in rows if bool((row.get("screen") or {}).get("advance"))]
    cells: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = f"{row['family_id']}:{row['band_id']}"
        cell = cells.setdefault(key, {"attempted": 0, "metrics": 0, "no_trades": 0, "advanced": 0})
        cell["attempted"] += 1
        cell["metrics"] += int(isinstance(row.get("metrics"), dict))
        cell["no_trades"] += int(row.get("status") == "no_trades")
        cell["advanced"] += int(bool((row.get("screen") or {}).get("advance")))
    if advanced:
        verdict = "D3_FOLDS_REQUIRED"
        controls = "PENDING_AFTER_FOLDS"
        bayesian = "PENDING_AFTER_FOLDS"
        d4 = "BLOCKED_PENDING_D3_FOLDS_CONTROLS_BAYESIAN"
    else:
        verdict = "NO_EVENT_QUALIFIED_D3_CANDIDATE"
        controls = "NOT_ENTERED_NO_EVENT_QUALIFIED_CANDIDATE"
        bayesian = "APPROVE_0_OF_0"
        d4 = "GATE_NOT_ENTERED"
    return {
        "schema": "stom.d3_screen_decision.v1",
        "authority": "existing_db_development_no_oos_no_adoption",
        "can_adopt": False,
        "screen_manifest_sha256": screen.get("manifest_sha256"),
        "attempted": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "metrics_count": sum(isinstance(row.get("metrics"), dict) for row in rows),
        "advanced_count": len(advanced),
        "advanced": [row["candidate_id"] for row in advanced],
        "cells": dict(sorted(cells.items())),
        "controls": controls,
        "bayesian": bayesian,
        "d4_bo": d4,
        "verdict": verdict,
    }
