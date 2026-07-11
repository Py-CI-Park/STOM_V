"""Canonical CL phase contract and fail-closed approval guard (CL-R01).

Design refs:
- CL-D2 lattice_v3_design_spec_20260709.md §4 (phase IDs + aliases), §16
  (exact approval phrases).
- CL-D3 lattice_v3_evaluation_protocol_20260709.md §2 (transition table),
  §2.1 (CL-R01..R06 sub-phases), §9 (failure transitions).

Core invariant: **evidence does not grant authority**. A valid receipt from
the immediate predecessor phase is a necessary condition to move forward,
but it never substitutes for the exact approval phrase a CL-R phase
requires. Evidence-only or paraphrased approval must fail closed.

This module is PURE: no filesystem/DB/network access happens at import
time or inside any of the core validation functions. The one I/O helper,
``load_approvals_from_intake``, is opt-in and must be called explicitly by
a caller that already decided to read an intake file; core validation
(``validate_transition`` and friends) always take approvals as an explicit
``set[str]`` argument.
"""
from __future__ import annotations

import enum
import json
from pathlib import Path

__all__ = [
    "CLPhase",
    "PhaseState",
    "PHASE_ORDER",
    "LEGACY_ALIAS",
    "APPROVAL_FOR",
    "PERMITTED_MUTATIONS",
    "CODE_EVIDENCE_MUTATION_FORBIDDEN",
    "CODE_WRONG_ALIAS",
    "CODE_OUT_OF_ORDER",
    "CODE_AUTHORITY_MISSING",
    "EXECUTION_KIND_FIXED_BATCH",
    "EXECUTION_KIND_RUN_LOOP",
    "MUTATION_EVENT_KINDS",
    "resolve_alias",
    "evidence_valid",
    "authority_valid",
    "validate_transition",
    "canonical_phase_owner_ok",
    "default_phase_status",
    "load_approvals_from_intake",
]


class CLPhase(enum.Enum):
    """The 15 canonical CL lattice phases, in execution order."""

    CL_D0 = "CL-D0"
    CL_D1 = "CL-D1"
    CL_D2 = "CL-D2"
    CL_D3 = "CL-D3"
    CL_D4 = "CL-D4"
    CL_R01 = "CL-R01"
    CL_R02 = "CL-R02"
    CL_R03 = "CL-R03"
    CL_R04 = "CL-R04"
    CL_R05 = "CL-R05"
    CL_R06 = "CL-R06"
    CL_R07 = "CL-R07"
    CL_R08 = "CL-R08"
    CL_R09 = "CL-R09"
    CL_R10 = "CL-R10"


class PhaseState(enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    TERMINAL = "TERMINAL"


# Transition failure codes (CL-D3 §2 / §9).
CODE_EVIDENCE_MUTATION_FORBIDDEN = "evidence_mutation_forbidden"
CODE_WRONG_ALIAS = "wrong_alias"
CODE_OUT_OF_ORDER = "out_of_order"
CODE_AUTHORITY_MISSING = "authority_missing"

# Evidence events are append-only INSERT-only; UPDATE/DELETE are forbidden.
MUTATION_EVENT_KINDS = frozenset({"UPDATE", "DELETE"})

# Execution origin kinds for canonical_phase_owner_ok.
EXECUTION_KIND_FIXED_BATCH = "fixed_batch"
EXECUTION_KIND_RUN_LOOP = "run_loop"

PHASE_ORDER: tuple[CLPhase, ...] = tuple(CLPhase)

# Legacy alias table (CL-D2 §4). P0 = audit, deliberately absent (no phase).
LEGACY_ALIAS: dict[str, CLPhase] = {
    "T0": CLPhase.CL_D0,
    "T1": CLPhase.CL_D1,
    "T2": CLPhase.CL_D2,
    "T3": CLPhase.CL_D3,
    "T4": CLPhase.CL_D4,
    "P1": CLPhase.CL_D0,
    "P2": CLPhase.CL_D1,
    "P3": CLPhase.CL_D2,
    "P4": CLPhase.CL_D3,
    "P5": CLPhase.CL_D4,
    "P6": CLPhase.CL_R01,
    "P9": CLPhase.CL_R07,
    "P10": CLPhase.CL_R08,
    "P11": CLPhase.CL_R10,
}

# Exact approval phrases (CL-D2 §16). Literal, case-sensitive; paraphrase
# invalid. CL-D0..CL-D4 (design phases) intentionally absent -> no approval
# required.
_APPROVAL_CODE_INTEGRATION = "I approve CL-R01-R06 code integration only"

APPROVAL_FOR: dict[CLPhase, str] = {
    CLPhase.CL_R01: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R02: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R03: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R04: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R05: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R06: _APPROVAL_CODE_INTEGRATION,
    CLPhase.CL_R07: "I approve CL-R07 bounded mini-loop only",
    CLPhase.CL_R08: "I approve CL-R08 bounded min performance only",
    CLPhase.CL_R09: "I approve CL-R09 sealed OOS/WF only",
    CLPhase.CL_R10: "I approve CL-R10 benchmark promotion review only",
}

_DESIGN_MUTATIONS: tuple[str, ...] = ("doc", "receipt")
_CODE_MUTATIONS: tuple[str, ...] = ("code", "evidence_insert")

PERMITTED_MUTATIONS: dict[CLPhase, tuple[str, ...]] = {
    phase: (_DESIGN_MUTATIONS if phase not in APPROVAL_FOR else _CODE_MUTATIONS)
    for phase in PHASE_ORDER
}


def resolve_alias(label: str) -> CLPhase | None:
    """Resolve a canonical phase id or legacy alias to a ``CLPhase``.

    Unknown labels (including ``P0`` which denotes audit, not a phase)
    return ``None``, which drives the ``wrong_alias`` failure code.
    """
    if isinstance(label, CLPhase):
        return label
    if not isinstance(label, str):
        return None
    if label in LEGACY_ALIAS:
        return LEGACY_ALIAS[label]
    try:
        return CLPhase(label)
    except ValueError:
        return None


def _predecessor(phase: CLPhase) -> CLPhase | None:
    idx = PHASE_ORDER.index(phase)
    if idx == 0:
        return None
    return PHASE_ORDER[idx - 1]


def evidence_valid(target: CLPhase, completed_receipts: set) -> bool:
    """True iff the immediate predecessor's receipt is present.

    CL-D0 has no predecessor, so it is always valid regardless of the
    (possibly empty) receipt set. Every other phase requires its exact
    immediate predecessor phase to be present in ``completed_receipts``;
    an empty set is therefore False for any phase past CL-D0.
    """
    predecessor = _predecessor(target)
    if predecessor is None:
        return True
    return predecessor in completed_receipts


def authority_valid(target: CLPhase, approvals: set) -> bool:
    """True iff the target's exact approval phrase is present.

    Design phases (CL-D0..CL-D4) require no approval and are always True.
    CL-R phases require exact, case-sensitive, non-substring membership of
    the required phrase in ``approvals``; an empty set is always False for
    CL-R phases. Neither this nor ``evidence_valid`` default to True for
    CL-R phases -- both must be independently satisfied.
    """
    required_phrase = APPROVAL_FOR.get(target)
    if required_phrase is None:
        return True
    return required_phrase in approvals


def validate_transition(
    target,
    completed_receipts: set,
    approvals: set,
    event_kind: str,
) -> tuple[str, str | None]:
    """Validate a proposed transition into ``target``.

    ``target`` may be a ``CLPhase`` or a canonical/legacy alias string.

    Check order (CL-D3 §9):
      1. ``evidence_mutation_forbidden`` -- event_kind is UPDATE/DELETE.
      2. ``wrong_alias`` -- target does not resolve to a known CLPhase.
      3. ``out_of_order`` -- immediate predecessor receipt missing.
      4. ``authority_missing`` -- CL-R target's exact phrase absent.

    Returns ``("allow", None)`` or ``("reject", <code>)``.
    """
    if event_kind in MUTATION_EVENT_KINDS:
        return ("reject", CODE_EVIDENCE_MUTATION_FORBIDDEN)

    resolved = resolve_alias(target) if not isinstance(target, CLPhase) else target
    if resolved is None:
        return ("reject", CODE_WRONG_ALIAS)

    if not evidence_valid(resolved, completed_receipts):
        return ("reject", CODE_OUT_OF_ORDER)

    if not authority_valid(resolved, approvals):
        return ("reject", CODE_AUTHORITY_MISSING)

    return ("allow", None)


def canonical_phase_owner_ok(execution_kind: str) -> bool:
    """True only for ``run_loop`` origin.

    ``fixed_batch`` execution may record evidence but can never advance
    canonical phase lineage.
    """
    return execution_kind == EXECUTION_KIND_RUN_LOOP


def default_phase_status() -> tuple[CLPhase, PhaseState]:
    """Return the canonical default phase/state: CL-D4 AWAITING_APPROVAL.

    No side effects; this is a pure constant lookup reflecting the CL-D3
    §2 stop state at the end of the design chain.
    """
    return (CLPhase.CL_D4, PhaseState.AWAITING_APPROVAL)


def load_approvals_from_intake(path) -> set:
    """Read an intake JSON file's ``exact_approval_phrase`` into a set.

    This is the only function in this module that performs I/O, and it is
    never called at import time or from any core validation function.
    Callers that need to feed approvals from an intake receipt must call
    this explicitly and pass the resulting set into ``validate_transition``
    / ``authority_valid``.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    phrase = data.get("exact_approval_phrase")
    if not phrase:
        return set()
    return {phrase}
