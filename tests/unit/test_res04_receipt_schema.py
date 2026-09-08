"""Structural schema probes only; these are not actual Stage F receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final, Literal, assert_never

import pytest
from jsonschema import Draft202012Validator

PATH: Final = (
    Path(__file__).resolve().parents[2]
    / "docs/research/quant_scoring_pipeline/planning"
    / "2026-09-08_res04p_expected_receipt.schema.json"
)


def fixture_json() -> str:
    """Use synthetic count/hash placeholders exclusively inside structural tests."""
    schema = json.loads(PATH.read_text(encoding="utf-8"))
    props = schema["properties"]
    candidate_ids = schema["$defs"]["CandidateFeasibility"]["properties"]["candidate"][
        "enum"
    ]
    fold_ids = [
        item["contains"]["properties"]["fold"]["const"]
        for item in schema["$defs"]["CandidateFeasibility"]["allOf"][0]["then"][
            "properties"
        ]["per_fold"]["allOf"]
    ]
    reports = [
        {
            "candidate": key,
            "status": "NORMAL_STOP",
            "reason": "INSUFFICIENT_ONSET_SAMPLE",
            "coverage_authority": "RELATIVE_TO_DECLARED_INVENTORY_ONLY",
            "execution_policy": "SEPARATE_APPROVAL_REQUIRED",
            "inventory_sha256": "0" * 64,
            "preparation_sha256": "0" * 64,
            "input_receipt_sha256": "0" * 64,
            "candidate_definition_sha256": "0" * 64,
            "expected_slices": 4,
            "received_slices": 4,
            "total_onsets": 8,
            "onset_days": 4,
            "onset_symbols": 1,
            "per_fold": [{"fold": f, "onsets": 2} for f in fold_ids],
        }
        for key in candidate_ids
    ]
    value = {
        "schema": props["schema"]["const"],
        "definition_sha256": "0" * 64,
        "raw_source_sha256": props["raw_source_sha256"]["const"],
        "candidate_manifest_sha256": props["candidate_manifest_sha256"]["const"],
        "implementation_identity": props["implementation_identity"]["const"],
        "inventory_sha256": "0" * 64,
        "event_output_sha256": "0" * 64,
        "execution_authority": "OUTCOME_FREE_NO_ECONOMIC_APPROVAL",
        "program_decision": "NORMAL_STOP",
        "source_binding": [{"kind": "BOUND_EVENT_STREAM_MANIFEST", "sha256": "0" * 64}],
        "overlap_reports": [{"kind": "OVERLAP_MANIFEST", "sha256": "0" * 64}],
        "expected_vs_received_inventory": {
            "expected_slices": 28,
            "received_slices": 28,
            "missing_scope_keys": [],
            "unexpected_scope_keys": [],
        },
        "candidate_sample_reports": reports,
        "coverage_and_errors": {"excluded_expected_slices": 0, "errors": []},
        "elapsed_and_resource_usage": {
            "elapsed_milliseconds": 1,
            "workers": 1,
            "bytes_read": 0,
            "budget_exceeded": False,
        },
        "stop_reason": "INSUFFICIENT_ONSET_SAMPLE",
    }
    return json.dumps(value, allow_nan=False)


def test_exact_schema_and_structural_fixture() -> None:
    # Given / When / Then: validate schema and a synthetic well-shaped STOP receipt.
    schema = json.loads(PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(fixture_json()))


@pytest.mark.parametrize(
    "change",
    [
        "missing_candidate",
        "duplicate_candidate",
        "unknown_candidate",
        "incomplete_candidate",
        "missing_source",
        "budget",
        "deadline",
        "execution",
        "profit",
    ],
)
def test_malformed_success_receipts_rejected(
    change: Literal[
        "missing_candidate",
        "duplicate_candidate",
        "unknown_candidate",
        "incomplete_candidate",
        "missing_source",
        "budget",
        "deadline",
        "execution",
        "profit",
    ],
) -> None:
    # Given: a synthetic receipt; mutate one condition without executing research.
    value = json.loads(fixture_json())
    match change:
        case "missing_candidate":
            value["candidate_sample_reports"].pop()
        case "duplicate_candidate":
            value["candidate_sample_reports"][-1] = value["candidate_sample_reports"][0]
        case "unknown_candidate":
            value["candidate_sample_reports"][0]["candidate"] = "UNKNOWN"
        case "incomplete_candidate":
            value["candidate_sample_reports"][0]["status"] = "INCOMPLETE"
        case "missing_source":
            value["source_binding"] = []
        case "budget":
            value["elapsed_and_resource_usage"]["budget_exceeded"] = True
        case "deadline":
            value["elapsed_and_resource_usage"]["elapsed_milliseconds"] = 1800001
        case "execution":
            value["execution_authority"] = "ECONOMIC_APPROVED"
        case "profit":
            value["pnl"] = 100
        case unreachable:
            assert_never(unreachable)
    # When / Then: do not accept a numerical success shape with invalid context.
    schema = json.loads(PATH.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value))
