#!/usr/bin/env python
"""Verify the CL-R01 canonical phase contract & fail-closed approval guard.

Runs the assertions enumerated in the CL-R01 task (todo 6 of
`.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md`) against
`ai_strategy_loop.controller.phase_contract` and writes a verification
receipt to
`.omo/evidence/task-6-ai-condition-loop-canonical-rebuild-20260711/verification.json`.

Exit code 0 iff every check passes; non-zero otherwise. This script does
not open a DB, run a backtest, or enable any runtime feature; it only
imports the pure phase_contract module and calls its pure functions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ai_strategy_loop.controller import phase_contract as pc  # noqa: E402

EVIDENCE_DIR = REPO_ROOT / ".omo" / "evidence" / "task-6-ai-condition-loop-canonical-rebuild-20260711"
EVIDENCE_PATH = EVIDENCE_DIR / "verification.json"

CODE_PHRASE = "I approve CL-R01-R06 code integration only"


def _all_receipts_through(phase: pc.CLPhase) -> set:
    idx = pc.PHASE_ORDER.index(phase)
    return set(pc.PHASE_ORDER[: idx + 1])


def run_checks() -> list[dict]:
    checks: list[dict] = []

    def record(name: str, expected, got):
        checks.append(
            {
                "name": name,
                "expected": repr(expected),
                "got": repr(got),
                "pass": expected == got,
            }
        )

    # 1. CL-D0->CL-D4 each validate 'allow' with empty approvals as
    #    predecessor receipts accrue.
    completed: set = set()
    for phase in (pc.CLPhase.CL_D0, pc.CLPhase.CL_D1, pc.CLPhase.CL_D2,
                  pc.CLPhase.CL_D3, pc.CLPhase.CL_D4):
        result = pc.validate_transition(phase, completed, set(), "INSERT")
        record(f"1_cl_d_chain_allows[{phase.value}]", ("allow", None), result)
        completed.add(phase)

    # 2. After CL-D4 receipt, CL-R01 with empty approvals -> authority_missing.
    completed_d4 = _all_receipts_through(pc.CLPhase.CL_D4)
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed_d4, set(), "INSERT")
    record("2_cl_r01_empty_approvals_authority_missing",
           ("reject", pc.CODE_AUTHORITY_MISSING), result)

    # 3. CL-R01 with exact phrase -> allow; CL-R07 with same phrase -> reject.
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed_d4, {CODE_PHRASE}, "INSERT")
    record("3a_cl_r01_exact_phrase_allow", ("allow", None), result)

    completed_r06 = _all_receipts_through(pc.CLPhase.CL_R06)
    result = pc.validate_transition(pc.CLPhase.CL_R07, completed_r06, {CODE_PHRASE}, "INSERT")
    record("3b_cl_r07_wrong_phrase_authority_missing",
           ("reject", pc.CODE_AUTHORITY_MISSING), result)

    # 4. Paraphrases -> authority_missing.
    for label, phrase in (
        ("approve_only", "approve CL-R01-R06"),
        ("approve_all", "I approve all"),
        ("lowercase", "i approve cl-r01-r06 code integration only"),
    ):
        result = pc.validate_transition(pc.CLPhase.CL_R01, completed_d4, {phrase}, "INSERT")
        record(f"4_paraphrase_rejected[{label}]",
               ("reject", pc.CODE_AUTHORITY_MISSING), result)

    # 5. Receipt-only (predecessor complete, approvals empty) -> authority_missing.
    result = pc.validate_transition(pc.CLPhase.CL_R01, completed_d4, set(), "INSERT")
    record("5_receipt_only_authority_missing",
           ("reject", pc.CODE_AUTHORITY_MISSING), result)

    # 6. Unknown alias -> wrong_alias.
    for label in ("P99", "CL-R99"):
        result = pc.validate_transition(label, set(), set(), "INSERT")
        record(f"6_unknown_alias_wrong_alias[{label}]",
               ("reject", pc.CODE_WRONG_ALIAS), result)

    # 7. Out-of-order CL-R03 with {CL-D0..CL-D4, CL-R01} -> out_of_order.
    completed_skip = _all_receipts_through(pc.CLPhase.CL_D4) | {pc.CLPhase.CL_R01}
    result = pc.validate_transition(pc.CLPhase.CL_R03, completed_skip, set(), "INSERT")
    record("7_out_of_order", ("reject", pc.CODE_OUT_OF_ORDER), result)

    # 8. UPDATE and DELETE events -> evidence_mutation_forbidden.
    completed_d3 = _all_receipts_through(pc.CLPhase.CL_D3)
    for event_kind in ("UPDATE", "DELETE"):
        result = pc.validate_transition(pc.CLPhase.CL_D4, completed_d3, set(), event_kind)
        record(f"8_mutation_forbidden[{event_kind}]",
               ("reject", pc.CODE_EVIDENCE_MUTATION_FORBIDDEN), result)

    # 9. default_phase_status; canonical_phase_owner_ok.
    result = pc.default_phase_status()
    record("9a_default_phase_status",
           (pc.CLPhase.CL_D4, pc.PhaseState.AWAITING_APPROVAL), result)

    result = pc.canonical_phase_owner_ok(pc.EXECUTION_KIND_FIXED_BATCH)
    record("9b_fixed_batch_owner_false", False, result)

    result = pc.canonical_phase_owner_ok(pc.EXECUTION_KIND_RUN_LOOP)
    record("9c_run_loop_owner_true", True, result)

    return checks


def main() -> int:
    errors: list[str] = []
    try:
        checks = run_checks()
    except Exception as exc:  # pragma: no cover - defensive, reported in receipt
        checks = []
        errors.append(f"{type(exc).__name__}: {exc}")

    all_pass = bool(checks) and all(c["pass"] for c in checks) and not errors

    payload = {
        "all_pass": all_pass,
        "checks": checks,
        "errors": errors,
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
