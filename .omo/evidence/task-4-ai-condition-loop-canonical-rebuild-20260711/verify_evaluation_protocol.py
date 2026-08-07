#!/usr/bin/env python3
"""Independent verifier for the CL-D3 evaluation protocol + next command.

Runs a deterministic state-machine self-test (valid CL-D0..D4 path ends at the
awaiting_CL_R01_R06_approval stop; D2->R07, receipt-only R08, and UPDATE/DELETE
transitions fail closed), then asserts the protocol document contains the
required elements and the next-command fenced blocks are design-scope only.
Exit 0 only when all checks pass.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN = REPO_ROOT / "docs/research/condition_research/generated_conditions/lattice_v3_design_20260709"
DEFAULT_PROTOCOL = GEN / "lattice_v3_evaluation_protocol_20260709.md"
DEFAULT_NEXTCMD = GEN / "lattice_v3_next_command_20260709.md"
DEFAULT_REPORT = (
    REPO_ROOT
    / ".omo/evidence/task-4-ai-condition-loop-canonical-rebuild-20260711"
    / "verification.json"
)

P1 = "I approve CL-R01-R06 code integration only"
P2 = "I approve CL-R07 bounded mini-loop only"
P3 = "I approve CL-R08 bounded min performance only"
P4 = "I approve CL-R09 sealed OOS/WF only"
P5 = "I approve CL-R10 benchmark promotion review only"
APPROVAL_PHRASES = [P1, P2, P3, P4, P5]

ORDER = ["CL-D0", "CL-D1", "CL-D2", "CL-D3", "CL-D4"] + [f"CL-R{n:02d}" for n in range(1, 11)]
APPROVAL_FOR = {
    "CL-R01": P1, "CL-R02": P1, "CL-R03": P1, "CL-R04": P1, "CL-R05": P1, "CL-R06": P1,
    "CL-R07": P2, "CL-R08": P3, "CL-R09": P4, "CL-R10": P5,
}


def validate(target, completed, approvals, event):
    if event in ("UPDATE", "DELETE"):
        return ("reject", "evidence_mutation_forbidden")
    idx = ORDER.index(target)
    if idx > 0 and ORDER[idx - 1] not in completed:
        return ("reject", "out_of_order")
    need = APPROVAL_FOR.get(target)
    if need is not None and need not in approvals:
        return ("reject", "authority_missing")
    return ("allow", None)


def run_state_machine_tests():
    """Return (tests:list, ok:bool)."""
    tests = []
    ok = True

    # 1. Valid CL-D0..D4 path (no approvals), then stop at awaiting R01-R06.
    completed = set()
    for phase in ["CL-D0", "CL-D1", "CL-D2", "CL-D3", "CL-D4"]:
        verdict, code = validate(phase, completed, set(), "INSERT")
        passed = verdict == "allow"
        ok = ok and passed
        tests.append({"name": f"design_path_{phase}", "expected": "allow", "got": verdict, "pass": passed})
        completed.add(phase)
    # After D4, R01 must be blocked without approval -> stop state proven.
    verdict, code = validate("CL-R01", completed, set(), "INSERT")
    passed = verdict == "reject" and code == "authority_missing"
    ok = ok and passed
    tests.append({"name": "stop_at_awaiting_CL_R01_R06_approval", "expected": "reject/authority_missing", "got": f"{verdict}/{code}", "pass": passed})

    # 2. D2 -> R07 out of order.
    verdict, code = validate("CL-R07", {"CL-D0", "CL-D1", "CL-D2"}, {P1, P2}, "INSERT")
    passed = verdict == "reject" and code == "out_of_order"
    ok = ok and passed
    tests.append({"name": "d2_to_r07_out_of_order", "expected": "reject/out_of_order", "got": f"{verdict}/{code}", "pass": passed})

    # 3. Receipt-only R08 (predecessor complete, approval missing).
    completed_r07 = set(ORDER[:ORDER.index("CL-R07") + 1])
    verdict, code = validate("CL-R08", completed_r07, {P1, P2}, "INSERT")
    passed = verdict == "reject" and code == "authority_missing"
    ok = ok and passed
    tests.append({"name": "receipt_only_r08_authority_missing", "expected": "reject/authority_missing", "got": f"{verdict}/{code}", "pass": passed})

    # 4. UPDATE/DELETE evidence event forbidden.
    verdict, code = validate("CL-R02", set(ORDER), set(APPROVAL_PHRASES), "UPDATE")
    passed = verdict == "reject" and code == "evidence_mutation_forbidden"
    ok = ok and passed
    tests.append({"name": "update_delete_forbidden", "expected": "reject/evidence_mutation_forbidden", "got": f"{verdict}/{code}", "pass": passed})

    return tests, ok


def fenced_blocks(text):
    parts = text.split("```")
    return [parts[i] for i in range(1, len(parts), 2)]


FORBIDDEN_IN_FENCE = ["insert into", "replay", "oos", "benchmark", "code integration", "run_backtest", "apply"]


def main():
    parser = argparse.ArgumentParser(description="Verify CL-D3 evaluation protocol + next command")
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--nextcmd", default=str(DEFAULT_NEXTCMD))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    errors = []

    # State machine self-tests.
    tests, sm_ok = run_state_machine_tests()
    if not sm_ok:
        for t in tests:
            if not t["pass"]:
                errors.append({"code": "state_machine_logic", "detail": f"{t['name']}: expected {t['expected']} got {t['got']}"})

    # Protocol document checks.
    try:
        proto = Path(args.protocol).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "protocol_unreadable", "detail": str(exc)})
        proto = ""
    for pid in ORDER:
        if pid not in proto:
            errors.append({"code": "missing_phase", "detail": f"phase id absent from protocol: {pid}"})
    for phrase in APPROVAL_PHRASES:
        if phrase not in proto:
            errors.append({"code": "missing_approval_phrase", "detail": f"approval phrase absent: {phrase!r}"})
    for token in ["INSERT-only", "evidence does not grant authority", "evidence_mutation_forbidden",
                   "UPDATE", "DELETE", "OOS custodian", "cohort manifest",
                   "dashboard cannot reinterpret evidence", "awaiting_CL_R01_R06_approval"]:
        if token not in proto:
            errors.append({"code": "missing_protocol_element", "detail": f"required element absent: {token!r}"})

    # Next-command document checks.
    try:
        nextcmd = Path(args.nextcmd).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "nextcmd_unreadable", "detail": str(exc)})
        nextcmd = ""
    if "$start-work" not in nextcmd:
        errors.append({"code": "missing_next_command", "detail": "no design-only $start-work command found"})
    if not ("hard stop" in nextcmd or "정지" in nextcmd) or "CL-D4" not in nextcmd:
        errors.append({"code": "missing_stop_rule", "detail": "next command lacks explicit CL-D4 hard-stop rule"})
    for block in fenced_blocks(nextcmd):
        low = block.lower()
        for bad in FORBIDDEN_IN_FENCE:
            if bad in low:
                errors.append({"code": "next_command_scope_violation", "detail": f"fenced command block contains forbidden execution token {bad!r}"})

    all_pass = len(errors) == 0
    report = {
        "all_pass": all_pass,
        "errors": errors,
        "state_machine_tests": tests,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
