"""cli.wide_seed_trial_planner 단위 테스트 (G004)."""

from __future__ import annotations

import pytest

from cli.condition_history_schema import (
    ExitProfileReceiptV1,
    SeedBoundaryIntentReceiptV1,
)
from cli.wide_seed_trial_planner import (
    CELLS_PER_LANE,
    MAX_ATTEMPTS,
    MAX_UNIQUE_TRIALS,
    RETRY_LIMIT_PER_TRIAL,
    TestedCellLedgerV1,
    TrialSpecV1,
    append_ledger_entry,
    assert_no_cartesian,
    build_default_plan,
    compute_trial_id,
    read_ledger,
    validate_plan,
)


def _receipts() -> tuple[str, str]:
    boundary = SeedBoundaryIntentReceiptV1.frozen_default().sha256
    exit_ = ExitProfileReceiptV1.frozen_default().sha256
    return boundary, exit_


def test_build_default_plan_returns_exactly_two_specs() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)

    assert len(specs) == MAX_UNIQUE_TRIALS == 2
    lanes = {spec.lane for spec in specs}
    assert lanes == {"tick", "min"}
    for spec in specs:
        assert spec.role == "unified_wide"
        assert spec.dataset_scope == "full_available_history"
        assert spec.result_role == "exploratory_full_history"
        assert len(spec.cell_metadata) == CELLS_PER_LANE


def test_build_default_plan_is_deterministic() -> None:
    boundary_sha, exit_sha = _receipts()
    specs_a = build_default_plan(boundary_sha, exit_sha)
    specs_b = build_default_plan(boundary_sha, exit_sha)

    assert [s.trial_id for s in specs_a] == [s.trial_id for s in specs_b]


def test_compute_trial_id_changes_with_boundary_sha() -> None:
    id_a = compute_trial_id("tick", "buy", "sell", "sha_a")
    id_b = compute_trial_id("tick", "buy", "sell", "sha_b")
    id_same = compute_trial_id("tick", "buy", "sell", "sha_a")

    assert id_a != id_b
    assert id_a == id_same


def test_validate_plan_accepts_default_plan() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    validate_plan(specs)  # 예외 없이 통과해야 한다.


def test_validate_plan_rejects_third_trial() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    extra = TrialSpecV1(
        trial_id="trial_extra_0000000000000000",
        lane="tick",
        buy_name="X",
        sell_name="Y",
        role="unified_wide",
        cell_metadata=specs[0].cell_metadata,
        dataset_scope="full_available_history",
        result_role="exploratory_full_history",
    )

    with pytest.raises(ValueError):
        validate_plan([*specs, extra])


def test_validate_plan_rejects_duplicate_trial_id() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    duplicate = TrialSpecV1(
        trial_id=specs[0].trial_id,
        lane=specs[0].lane,
        buy_name=specs[0].buy_name,
        sell_name=specs[0].sell_name,
        role=specs[0].role,
        cell_metadata=specs[0].cell_metadata,
        dataset_scope=specs[0].dataset_scope,
        result_role=specs[0].result_role,
    )

    with pytest.raises(ValueError):
        validate_plan([specs[0], duplicate])


def test_validate_plan_rejects_wrong_cell_count() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    bad = TrialSpecV1(
        trial_id=specs[0].trial_id,
        lane=specs[0].lane,
        buy_name=specs[0].buy_name,
        sell_name=specs[0].sell_name,
        role=specs[0].role,
        cell_metadata=specs[0].cell_metadata[:11],
        dataset_scope=specs[0].dataset_scope,
        result_role=specs[0].result_role,
    )

    with pytest.raises(ValueError):
        validate_plan([bad])


def test_assert_no_cartesian_passes_for_default_plan() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    assert_no_cartesian(specs)  # 예외 없이 통과해야 한다.


def test_assert_no_cartesian_rejects_oversized_plan() -> None:
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)
    with pytest.raises(ValueError):
        assert_no_cartesian([*specs, specs[0], specs[1]])


def test_attempts_and_retry_budget_constants() -> None:
    assert MAX_UNIQUE_TRIALS == 2
    assert MAX_ATTEMPTS == 4
    assert RETRY_LIMIT_PER_TRIAL == 1
    assert MAX_UNIQUE_TRIALS * (1 + RETRY_LIMIT_PER_TRIAL) == MAX_ATTEMPTS


def test_ledger_append_and_read_roundtrip(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    boundary_sha, exit_sha = _receipts()
    specs = build_default_plan(boundary_sha, exit_sha)

    written = []
    for spec in specs:
        entry = TestedCellLedgerV1(
            event="planned",
            trial_id=spec.trial_id,
            spec_hash=spec.trial_id,
        )
        written.append(append_ledger_entry(ledger_path, entry))

    written.append(
        append_ledger_entry(
            ledger_path,
            {
                "event": "executed",
                "trial_id": specs[0].trial_id,
                "spec_hash": specs[0].trial_id,
            },
        )
    )

    read_back = read_ledger(ledger_path)

    assert len(read_back) == 3
    assert [r["event"] for r in read_back] == ["planned", "planned", "executed"]
    assert all(r["timestamp"] for r in read_back)
    assert read_back == written


def test_ledger_read_missing_file_returns_empty_list(tmp_path) -> None:
    missing = tmp_path / "does_not_exist.jsonl"
    assert read_ledger(missing) == []


def test_append_ledger_entry_rejects_unknown_event(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError):
        append_ledger_entry(
            ledger_path,
            {"event": "bogus", "trial_id": "t1", "spec_hash": "h1"},
        )


def test_append_ledger_entry_rejects_missing_required_key(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError):
        append_ledger_entry(ledger_path, {"event": "planned", "trial_id": "t1"})
