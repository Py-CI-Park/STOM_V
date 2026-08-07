#!/usr/bin/env python3
"""Independent verifier for the CL-D4 durable master plan / handoff / pointers.

- Cold-start check: every path in the handoff 'referenced paths' fenced block
  must resolve on disk.
- Audit check: the ambiguous P/T primary-label rows are gone and the canonical
  CL-ID mapping is present.
- Supersession banners present in the two legacy handoffs.
- All CL-D deliverables + master plan + handoffs exist.
Exit 0 only when all checks pass.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN = "docs/research/condition_research/generated_conditions/lattice_v3_design_20260709"
DEFAULT_HANDOFF = REPO_ROOT / "docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md"
DEFAULT_AUDIT = REPO_ROOT / "docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md"
DEFAULT_AGENT_HANDOFF = REPO_ROOT / "docs/AGENT_HANDOFF.md"
DEFAULT_CROSSAGENT = REPO_ROOT / "docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md"
DEFAULT_REPORT = REPO_ROOT / ".omo/evidence/task-5-ai-condition-loop-canonical-rebuild-20260711/verification.json"

AMBIGUOUS_ROWS = [
    "| P1 / T0 |", "| P2 / T1 |", "| P3 / T2 |", "| P4 / T3 |", "| P5 / T4 |",
]
CANONICAL_TOKENS = ["CL-D0", "CL-D1", "CL-D2", "CL-D3", "CL-D4", "CL-R01", "CL-R07", "CL-R10", "정본 ID 매핑"]

DELIVERABLES = [
    f"{GEN}/source_read_receipt_v3_design_20260709.json",
    f"{GEN}/lattice_v3_failure_lesson_matrix_20260709.md",
    f"{GEN}/lattice_v3_design_spec_20260709.md",
    f"{GEN}/lattice_v3_evaluation_protocol_20260709.md",
    f"{GEN}/lattice_v3_next_command_20260709.md",
    "docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md",
    "docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md",
    "docs/update_log/2026-07-09_lattice_v3_design_only_handoff.md",
]

NEW_HANDOFF_REF = "docs/update_log/2026-07-11_ai_condition_loop_canonical_rebuild_handoff.md"
SUPERSEDE_MARK = "[최신 정본 우선]"


def first_fenced_block(text):
    parts = text.split("```")
    return parts[1] if len(parts) >= 3 else ""


def main():
    parser = argparse.ArgumentParser(description="Verify CL-D4 handoff/master-plan/pointers")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    parser.add_argument("--audit", default=str(DEFAULT_AUDIT))
    parser.add_argument("--agent-handoff", default=str(DEFAULT_AGENT_HANDOFF))
    parser.add_argument("--crossagent", default=str(DEFAULT_CROSSAGENT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    errors = []

    # 1. Cold-start referenced-path resolution.
    try:
        handoff = Path(args.handoff).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "handoff_unreadable", "detail": str(exc)})
        handoff = ""
    ref_block = first_fenced_block(handoff)
    ref_paths = [ln.strip() for ln in ref_block.splitlines() if ln.strip()]
    if not ref_paths:
        errors.append({"code": "no_referenced_paths", "detail": "handoff has no referenced-path block"})
    for rel in ref_paths:
        if not (REPO_ROOT / rel).exists():
            errors.append({"code": "unresolved_reference", "detail": f"handoff references missing path: {rel}"})

    # 2. Audit ambiguity removed + canonical mapping present.
    try:
        audit = Path(args.audit).read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "audit_unreadable", "detail": str(exc)})
        audit = ""
    for row in AMBIGUOUS_ROWS:
        if row in audit:
            errors.append({"code": "ambiguous_pt_row", "detail": f"audit still contains ambiguous primary-label row: {row!r}"})
    for tok in CANONICAL_TOKENS:
        if tok not in audit:
            errors.append({"code": "missing_canonical_mapping", "detail": f"audit missing canonical token: {tok!r}"})

    # 3. Supersession banners in legacy handoffs.
    for label, path in [("agent_handoff", args.agent_handoff), ("crossagent", args.crossagent)]:
        try:
            body = Path(path).read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover
            errors.append({"code": "legacy_handoff_unreadable", "detail": f"{label}: {exc}"})
            continue
        if SUPERSEDE_MARK not in body or NEW_HANDOFF_REF not in body:
            errors.append({"code": "missing_supersession_banner", "detail": f"{label} lacks latest-first banner or new-handoff reference"})

    # 4. All deliverables exist.
    for rel in DELIVERABLES:
        if not (REPO_ROOT / rel).exists():
            errors.append({"code": "missing_deliverable", "detail": f"deliverable absent: {rel}"})

    all_pass = len(errors) == 0
    report = {
        "all_pass": all_pass,
        "errors": errors,
        "referenced_paths_checked": len(ref_paths),
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
