"""Real production-import binding tests against isolated SQLite and sealed metadata."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_strategy_loop.revision import res04_input_binding as binding
from ai_strategy_loop.revision import res04_tick_source as source
from tests.unit.res04_binding_fixtures import MANIFEST, PREREG, PREREG_SHA, source_plan


def test_source_to_predicate_to_event_stream(tmp_path: Path) -> None:
    # Given: actual SQLite fixture and immutable production candidate manifest.
    plan = source_plan(tmp_path)
    database = Path(plan.source.path)
    before = database.read_bytes()
    request = source.SourceRequest(
        symbol="005930", session_day=date(2022, 4, 1), max_rows=100
    )
    # When: public binding uses real SQLite, manifest validator, and predicate.
    result = binding.build_bound_event_stream(
        plan,
        request,
        binding.CandidateFiles(
            manifest=MANIFEST, prereg=PREREG, prereg_sha256=PREREG_SHA
        ),
        plan.candidate_ids[0],
    )
    # Then: exact source identity/rows are bound, without write or execution grant.
    assert result.source.row_count == 90
    assert result.source.sha256 == hashlib.sha256(before).hexdigest()
    assert result.stream.source_rows == 90
    assert result.authority == "READONLY_INPUT_BINDING_NO_EXECUTION_GRANT"
    assert database.read_bytes() == before
    assert not Path(str(database) + "-wal").exists()


def test_tampered_source_rejected(tmp_path: Path) -> None:
    # Given: the source no longer matches the preparation identity.
    plan = source_plan(tmp_path)
    with Path(plan.source.path).open("ab") as handle:
        handle.write(b"tampered")
    # When / Then.
    with pytest.raises(ValueError, match="SOURCE_IDENTITY"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidefiles_block_immutable_read(tmp_path: Path, suffix: str) -> None:
    # Given: immutable mode must not silently ignore outstanding side files.
    plan = source_plan(tmp_path)
    Path(plan.source.path + suffix).write_bytes(b"pending")
    # When / Then.
    with pytest.raises(ValueError, match="SOURCE_SIDEFILE"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


def test_partial_or_missing_values_not_zero_filled(tmp_path: Path) -> None:
    # Given: NULL price would become zero in the legacy normalizer.
    plan = source_plan(tmp_path, missing=True)
    # When / Then: reject before normalization.
    with pytest.raises(ValidationError):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2022, 4, 1))
        )


def test_row_limit_not_partial_success(tmp_path: Path) -> None:
    # Given: source contains more rows than the permitted slice.
    plan = source_plan(tmp_path)
    # When / Then.
    with pytest.raises(ValueError, match="SOURCE_ROW_LIMIT"):
        source.read_tick_slice(
            plan,
            source.SourceRequest(
                symbol="005930", session_day=date(2022, 4, 1), max_rows=10
            ),
        )


def test_oos_request_rejected_before_open(tmp_path: Path) -> None:
    # Given: missing source and an OOS request; source must not be opened.
    plan = source_plan(tmp_path)
    Path(plan.source.path).unlink()
    # When / Then: scope error, not file access.
    with pytest.raises(ValueError, match="SOURCE_FOLD"):
        source.read_tick_slice(
            plan, source.SourceRequest(symbol="005930", session_day=date(2026, 1, 1))
        )


def test_tampered_manifest_rejected(tmp_path: Path) -> None:
    # Given: wrong manifest bytes without changing expected identity.
    plan = source_plan(tmp_path)
    fake = tmp_path / "manifest.json"
    fake.write_bytes(b"{}")
    # When / Then.
    with pytest.raises(ValueError, match="BINDING_FILE_HASH"):
        binding.load_candidate(
            plan,
            binding.CandidateFiles(
                manifest=fake, prereg=PREREG, prereg_sha256=PREREG_SHA
            ),
            plan.candidate_ids[0],
        )


def test_unregistered_candidate_rejected(tmp_path: Path) -> None:
    # Given: a requested candidate outside the fixed seven.
    plan = source_plan(tmp_path)
    # When / Then.
    with pytest.raises(ValueError, match="BINDING_CANDIDATE"):
        binding.load_candidate(
            plan,
            binding.CandidateFiles(
                manifest=MANIFEST, prereg=PREREG, prereg_sha256=PREREG_SHA
            ),
            "not-registered",
        )
