"""Contract TDD tests for CL-R01 canonical phase contract & fail-closed approval guard.

Covers: ai_strategy_loop/controller/phase_contract.py
Design refs: CL-D2 lattice_v3_design_spec_20260709.md §4/§16
             CL-D3 lattice_v3_evaluation_protocol_20260709.md §2/§2.1/§9
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_strategy_loop.controller import phase_contract as pc


# ---------------------------------------------------------------------------
# CLPhase / PhaseState enums
# ---------------------------------------------------------------------------


def test_cl_phase_has_exactly_15_members_in_order():
    assert [p.value for p in pc.PHASE_ORDER] == [
        "CL-D0", "CL-D1", "CL-D2", "CL-D3", "CL-D4",
        "CL-R01", "CL-R02", "CL-R03", "CL-R04", "CL-R05", "CL-R06",
        "CL-R07", "CL-R08", "CL-R09", "CL-R10",
    ]
    assert len(pc.CLPhase) == 15
    assert tuple(pc.CLPhase) == pc.PHASE_ORDER


def test_phase_state_members():
    expected = {
        "NOT_STARTED", "IN_PROGRESS", "COMPLETE",
        "AWAITING_APPROVAL", "BLOCKED", "TERMINAL",
    }
    assert {s.name for s in pc.PhaseState} == expected


def test_transition_codes_are_strings():
    for code in (
        pc.CODE_EVIDENCE_MUTATION_FORBIDDEN,
        pc.CODE_WRONG_ALIAS,
        pc.CODE_OUT_OF_ORDER,
        pc.CODE_AUTHORITY_MISSING,
    ):
        assert isinstance(code, str) and code


# ---------------------------------------------------------------------------
# Legacy alias resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,expected",
    [
        ("T0", pc.CLPhase.CL_D0),
        ("T1", pc.CLPhase.CL_D1),
        ("T2", pc.CLPhase.CL_D2),
        ("T3", pc.CLPhase.CL_D3),
        ("T4", pc.CLPhase.CL_D4),
        ("P1", pc.CLPhase.CL_D0),
        ("P2", pc.CLPhase.CL_D1),
        ("P3", pc.CLPhase.CL_D2),
        ("P4", pc.CLPhase.CL_D3),
        ("P5", pc.CLPhase.CL_D4),
        ("P6", pc.CLPhase.CL_R01),
        ("P9", pc.CLPhase.CL_R07),
        ("P10", pc.CLPhase.CL_R08),
        ("P11", pc.CLPhase.CL_R10),
        ("CL-D0", pc.CLPhase.CL_D0),
        ("CL-R10", pc.CLPhase.CL_R10),
    ],
)
def test_resolve_alias_known(label, expected):
    assert pc.resolve_alias(label) is expected


@pytest.mark.parametrize("label", ["P99", "CL-R99", "T9", "", "cl-d0", "bogus"])
def test_resolve_alias_unknown_returns_none(label):
    assert pc.resolve_alias(label) is None


def test_p0_is_audit_not_a_phase():
    assert pc.resolve_alias("P0") is None


# ---------------------------------------------------------------------------
# APPROVAL_FOR
# ---------------------------------------------------------------------------


def test_approval_for_cl_r_phases_only():
    for phase in (
        pc.CLPhase.CL_D0, pc.CLPhase.CL_D1, pc.CLPhase.CL_D2,
        pc.CLPhase.CL_D3, pc.CLPhase.CL_D4,
    ):
        assert phase not in pc.APPROVAL_FOR

    for phase in (
        pc.CLPhase.CL_R01, pc.CLPhase.CL_R02, pc.CLPhase.CL_R03,
        pc.CLPhase.CL_R04, pc.CLPhase.CL_R05, pc.CLPhase.CL_R06,
    ):
        assert pc.APPROVAL_FOR[phase] == "I approve CL-R01-R06 code integration only"

    assert pc.APPROVAL_FOR[pc.CLPhase.CL_R07] == "I approve CL-R07 bounded mini-loop only"
    assert pc.APPROVAL_FOR[pc.CLPhase.CL_R08] == "I approve CL-R08 bounded min performance only"
    assert pc.APPROVAL_FOR[pc.CLPhase.CL_R09] == "I approve CL-R09 sealed OOS/WF only"
    assert pc.APPROVAL_FOR[pc.CLPhase.CL_R10] == "I approve CL-R10 benchmark promotion review only"


# ---------------------------------------------------------------------------
# PERMITTED_MUTATIONS
# ---------------------------------------------------------------------------


def test_permitted_mutations_design_vs_code():
    for phase in (
        pc.CLPhase.CL_D0, pc.CLPhase.CL_D1, pc.CLPhase.CL_D2,
        pc.CLPhase.CL_D3, pc.CLPhase.CL_D4,
    ):
        assert pc.PERMITTED_MUTATIONS[phase] == ("doc", "receipt")

    for phase in (
        pc.CLPhase.CL_R01, pc.CLPhase.CL_R02, pc.CLPhase.CL_R03,
        pc.CLPhase.CL_R04, pc.CLPhase.CL_R05, pc.CLPhase.CL_R06,
        pc.CLPhase.CL_R07, pc.CLPhase.CL_R08, pc.CLPhase.CL_R09,
        pc.CLPhase.CL_R10,
    ):
        assert pc.PERMITTED_MUTATIONS[phase] == ("code", "evidence_insert")

    assert set(pc.PERMITTED_MUTATIONS) == set(pc.CLPhase)


# ---------------------------------------------------------------------------
# evidence_valid
# ---------------------------------------------------------------------------


def test_evidence_valid_cl_d0_no_predecessor():
    assert pc.evidence_valid(pc.CLPhase.CL_D0, set()) is True


def test_evidence_valid_empty_set_false_past_first():
    assert pc.evidence_valid(pc.CLPhase.CL_D1, set()) is False
    assert pc.evidence_valid(pc.CLPhase.CL_R01, set()) is False
    assert pc.evidence_valid(pc.CLPhase.CL_R10, set()) is False


def test_evidence_valid_immediate_predecessor_present():
    assert pc.evidence_valid(pc.CLPhase.CL_D1, {pc.CLPhase.CL_D0}) is True
    assert pc.evidence_valid(pc.CLPhase.CL_R01, {pc.CLPhase.CL_D4}) is True


def test_evidence_valid_non_immediate_predecessor_insufficient():
    # CL-D0 receipt alone does not satisfy CL-D2's predecessor requirement (CL-D1)
    assert pc.evidence_valid(pc.CLPhase.CL_D2, {pc.CLPhase.CL_D0}) is False


# ---------------------------------------------------------------------------
# authority_valid
# ---------------------------------------------------------------------------


def test_authority_valid_design_phases_always_true():
    for phase in (
        pc.CLPhase.CL_D0, pc.CLPhase.CL_D1, pc.CLPhase.CL_D2,
        pc.CLPhase.CL_D3, pc.CLPhase.CL_D4,
    ):
        assert pc.authority_valid(phase, set()) is True


def test_authority_valid_cl_r_empty_approvals_false():
    assert pc.authority_valid(pc.CLPhase.CL_R01, set()) is False


def test_authority_valid_exact_phrase_true():
    assert pc.authority_valid(
        pc.CLPhase.CL_R01, {"I approve CL-R01-R06 code integration only"}
    ) is True


def test_authority_valid_case_sensitive():
    assert pc.authority_valid(
        pc.CLPhase.CL_R01, {"i approve cl-r01-r06 code integration only"}
    ) is False


@pytest.mark.parametrize(
    "phrase",
    [
        "approve CL-R01-R06",
        "I approve all",
        "I approve CL-R01-R06 code integration only ",  # trailing space
        " I approve CL-R01-R06 code integration only",  # leading space
        "I approve CL-R01-R06 code integration only extra",
        "I approve CL-R07 bounded mini-loop only",  # wrong phase's phrase
    ],
)
def test_authority_valid_substring_paraphrase_rejected(phrase):
    assert pc.authority_valid(pc.CLPhase.CL_R01, {phrase}) is False


def test_authority_valid_wrong_phase_phrase_not_shared():
    assert pc.authority_valid(
        pc.CLPhase.CL_R07, {"I approve CL-R01-R06 code integration only"}
    ) is False


# ---------------------------------------------------------------------------
# validate_transition
# ---------------------------------------------------------------------------


def _all_receipts_through(phase: pc.CLPhase) -> set:
    idx = pc.PHASE_ORDER.index(phase)
    return set(pc.PHASE_ORDER[: idx + 1])


def test_validate_transition_cl_d_chain_allows_without_approval():
    completed: set = set()
    for phase in (pc.CLPhase.CL_D0, pc.CLPhase.CL_D1, pc.CLPhase.CL_D2,
                  pc.CLPhase.CL_D3, pc.CLPhase.CL_D4):
        result = pc.validate_transition(phase, completed, set(), "INSERT")
        assert result == ("allow", None), (phase, result)
        completed.add(phase)


def test_validate_transition_cl_r01_after_cl_d4_receipt_empty_approvals_authority_missing():
    completed = _all_receipts_through(pc.CLPhase.CL_D4)
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed, set(), "INSERT")
    assert result == ("reject", pc.CODE_AUTHORITY_MISSING)


def test_validate_transition_cl_r01_with_exact_phrase_allows():
    completed = _all_receipts_through(pc.CLPhase.CL_D4)
    approvals = {"I approve CL-R01-R06 code integration only"}
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed, approvals, "INSERT")
    assert result == ("allow", None)


def test_validate_transition_cl_r07_with_cl_r01_phrase_rejected():
    completed = _all_receipts_through(pc.CLPhase.CL_R06)
    approvals = {"I approve CL-R01-R06 code integration only"}
    result = pc.validate_transition(pc.CLPhase.CL_R07, completed, approvals, "INSERT")
    assert result == ("reject", pc.CODE_AUTHORITY_MISSING)


@pytest.mark.parametrize(
    "phrase",
    [
        "approve CL-R01-R06",
        "I approve all",
        "i approve cl-r01-r06 code integration only",
    ],
)
def test_validate_transition_paraphrase_rejected(phrase):
    completed = _all_receipts_through(pc.CLPhase.CL_D4)
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed, {phrase}, "INSERT")
    assert result == ("reject", pc.CODE_AUTHORITY_MISSING)


def test_validate_transition_receipt_only_no_approval_rejected():
    completed = _all_receipts_through(pc.CLPhase.CL_D4)
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed, set(), "INSERT")
    assert result == ("reject", pc.CODE_AUTHORITY_MISSING)


@pytest.mark.parametrize("label", ["P99", "CL-R99"])
def test_validate_transition_unknown_alias_wrong_alias(label):
    result = pc.validate_transition(label, set(), set(), "INSERT")
    assert result == ("reject", pc.CODE_WRONG_ALIAS)


def test_validate_transition_out_of_order():
    completed = _all_receipts_through(pc.CLPhase.CL_D4) | {pc.CLPhase.CL_R01}
    result = pc.validate_transition(pc.CLPhase.CL_R03, completed, set(), "INSERT")
    assert result == ("reject", pc.CODE_OUT_OF_ORDER)


@pytest.mark.parametrize("event_kind", ["UPDATE", "DELETE"])
def test_validate_transition_mutation_forbidden(event_kind):
    completed = _all_receipts_through(pc.CLPhase.CL_D3)
    result = pc.validate_transition(pc.CLPhase.CL_D4, completed, set(), event_kind)
    assert result == ("reject", pc.CODE_EVIDENCE_MUTATION_FORBIDDEN)


def test_validate_transition_mutation_forbidden_checked_before_other_codes():
    # Even with unknown alias AND mutation event, mutation code wins (order: mutation, alias, order, authority)
    result = pc.validate_transition("P99", set(), set(), "DELETE")
    assert result == ("reject", pc.CODE_EVIDENCE_MUTATION_FORBIDDEN)


def test_validate_transition_wrong_alias_checked_before_out_of_order_and_authority():
    result = pc.validate_transition("P99", set(), set(), "INSERT")
    assert result == ("reject", pc.CODE_WRONG_ALIAS)


def test_validate_transition_out_of_order_checked_before_authority():
    # target resolvable, predecessor missing entirely -> out_of_order not authority_missing
    result = pc.validate_transition(pc.CLPhase.CL_R01, set(), set(), "INSERT")
    assert result == ("reject", pc.CODE_OUT_OF_ORDER)


def test_validate_transition_accepts_alias_string_target():
    completed = _all_receipts_through(pc.CLPhase.CL_D3)
    result = pc.validate_transition("T4", completed, set(), "INSERT")
    assert result == ("allow", None)


# ---------------------------------------------------------------------------
# canonical_phase_owner_ok
# ---------------------------------------------------------------------------


def test_canonical_phase_owner_ok_run_loop_true():
    assert pc.canonical_phase_owner_ok(pc.EXECUTION_KIND_RUN_LOOP) is True


def test_canonical_phase_owner_ok_fixed_batch_false():
    assert pc.canonical_phase_owner_ok(pc.EXECUTION_KIND_FIXED_BATCH) is False


def test_canonical_phase_owner_ok_unknown_kind_false():
    assert pc.canonical_phase_owner_ok("something_else") is False


# ---------------------------------------------------------------------------
# default_phase_status
# ---------------------------------------------------------------------------


def test_default_phase_status():
    assert pc.default_phase_status() == (pc.CLPhase.CL_D4, pc.PhaseState.AWAITING_APPROVAL)


# ---------------------------------------------------------------------------
# load_approvals_from_intake (no import-time side effects; explicit call only)
# ---------------------------------------------------------------------------


def test_load_approvals_from_intake_reads_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intake.json"
        path.write_text(
            json.dumps({"exact_approval_phrase": "I approve CL-R01-R06 code integration only"}),
            encoding="utf-8",
        )
        result = pc.load_approvals_from_intake(path)
        assert result == {"I approve CL-R01-R06 code integration only"}


def test_load_approvals_from_intake_missing_key_returns_empty_set():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intake.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        assert pc.load_approvals_from_intake(path) == set()


def test_module_has_no_import_time_side_effects(tmp_path):
    # Re-importing must not touch filesystem beyond normal python import machinery.
    # This is a structural guarantee check: the module must not define any
    # module-level call to load_approvals_from_intake or similar I/O.
    import inspect

    source = inspect.getsource(pc)
    # crude guard: load_approvals_from_intake must only appear in its own def line
    # and not be invoked unconditionally at module scope.
    lines = source.splitlines()
    call_lines = [
        ln for ln in lines
        if "load_approvals_from_intake(" in ln and not ln.strip().startswith("def ")
    ]
    for ln in call_lines:
        assert ln.startswith("    ") or ln.strip().startswith(("#", '"""', "'''")), ln
