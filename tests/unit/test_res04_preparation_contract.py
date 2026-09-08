"""Preparation validation never submits research or opens a market database."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ai_strategy_loop.revision import res04_preparation_contract as contract

if TYPE_CHECKING:
    from pathlib import Path


def payload() -> str:
    """Return a synthetic plan, not market data or execution authority."""
    return json.dumps(
        {
            "schema_version": "stom.res04.preparation.v1",
            "authority": "PREPARATION_ONLY_NO_EXECUTION",
            "source": {
                "path": "synthetic.db",
                "bytes": 123,
                "sha256": "a" * 64,
                "hash_mode": "full_sha256",
                "role": "DEVELOPMENT_PREVIOUSLY_EXPOSED",
            },
            "candidate_manifest_sha256": "b" * 64,
            "candidate_ids": [f"candidate_{i}" for i in range(7)],
            "folds": [
                {
                    "id": f"F{i}",
                    "start": f"202{i}-04-01",
                    "end_exclusive": f"202{i}-05-01",
                }
                for i in range(2, 6)
            ],
            "seed": 20260907,
            "window_start": "09:00:00",
            "window_end_exclusive": "09:30:00",
            "timezone": "Asia/Seoul",
            "max_gap_seconds": 1,
            "min_total_episodes": 200,
            "min_episodes_per_fold": 20,
            "min_distinct_days": 20,
            "min_distinct_symbols": 10,
            "primary_hypothesis": "E1",
            "secondary_hypothesis": "R1_DESCRIPTIVE_ONLY",
            "initial_true_policy": "LEFT_CENSOR",
            "gap_policy": "CENSOR_NOT_FALSE",
            "duplicate_policy": "REJECT",
            "nonfinite_policy": "REJECT",
            "selection_policy": "NO_PNL_SELECTION",
            "cost_policy": "NOT_APPLICABLE_NO_ECONOMIC_METRICS",
            "execution_policy": "SEPARATE_APPROVAL_REQUIRED",
        },
    )


def test_valid_preparation_does_not_grant_execution() -> None:
    # Given / When: a complete synthetic preparation contract.
    plan = contract.Res04Preparation.model_validate_json(payload())
    # Then: the only authority is non-executing preparation.
    assert plan.authority == "PREPARATION_ONLY_NO_EXECUTION"


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('"seed": 20260907', '"seed": null'),
        ('"seed": 20260907', '"seed": true'),
        ('"full_sha256"', '"sampled_v1"'),
        ('"DEVELOPMENT_PREVIOUSLY_EXPOSED"', '"FROZEN_OOS"'),
        ('"2025-05-01"', '"2026-01-02"'),
        ('"2022-04-01"', '"2022-02-30"'),
        ('"candidate_6"', '"candidate_5"'),
        ('"F5"', '"F4"'),
        ('"2025-04-01"', '"2024-04-01"'),
        ('"09:30:00"', '"08:30:00"'),
        ('"max_gap_seconds": 1', '"max_gap_seconds": 0'),
        ('"PREPARATION_ONLY_NO_EXECUTION"', '"SEALED_FOR_EXECUTION"'),
        ('"09:00:00"', '"09:00:00+09:00"'),
        ('"2022-04-01"', '"2022-05-01"'),
        ('"2022-04-01"', '"2022-06-01"'),
        ('"min_total_episodes": 200', '"min_total_episodes": -1'),
        ('"min_distinct_days": 20', '"min_distinct_days": false'),
        ('"bytes": 123', '"bytes": 0'),
        ('"candidate_5", "candidate_6"', '"candidate_5"'),
    ],
)
def test_unsafe_plan_rejected(old: str, new: str) -> None:
    # Given: one invalid boundary field.
    raw = payload().replace(old, new)
    # When / Then: parsing rejects rather than defaults or promotes it.
    with pytest.raises(ValidationError):
        contract.Res04Preparation.model_validate_json(raw)


def test_extra_execution_field_rejected() -> None:
    # Given: a caller tries to smuggle execution permission.
    raw = payload()[:-1] + ', "approved_for_execution": true}'
    # When / Then: unknown authority fields are forbidden.
    with pytest.raises(ValidationError):
        contract.Res04Preparation.model_validate_json(raw)


def test_load_validates_exact_bytes(tmp_path: Path) -> None:
    # Given: a fixture file with independently calculated identity.
    path = tmp_path / "plan.json"
    raw = payload().encode()
    path.write_bytes(raw)
    # When: the public file boundary loads a real file.
    plan = contract.load_preparation(path, hashlib.sha256(raw).hexdigest())
    # Then: parsing does not need/open the nonexistent synthetic.db.
    assert plan.source.path == "synthetic.db"


def test_tampered_file_rejected(tmp_path: Path) -> None:
    # Given: valid JSON but a mismatched expected identity.
    path = tmp_path / "plan.json"
    path.write_text(payload(), encoding="utf-8")
    # When / Then: integrity failure blocks parsing.
    with pytest.raises(ValueError, match="PREPARATION_HASH_MISMATCH"):
        contract.load_preparation(path, "0" * 64)


def test_oversized_file_rejected(tmp_path: Path) -> None:
    # Given: a document larger than the bounded preparation input.
    path = tmp_path / "large.json"
    path.write_bytes(b" " * 65537)
    # When / Then: bounded reader refuses it.
    with pytest.raises(ValueError, match="PREPARATION_RESOURCE_LIMIT"):
        contract.load_preparation(path, "0" * 64)
