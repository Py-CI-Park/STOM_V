#!/usr/bin/env python3
"""Independent verifier for the CL-D0 source read receipt.

Recomputes sha256/line_count for every listed source from disk using the
same bytes-based logic as the receipt builder, and asserts structural
invariants (required source set, role counts, read_scope, scope string).

Exit code 0 only when all checks pass (all_pass == True in the report).
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_RECEIPT_PATH = (
    REPO_ROOT
    / "docs/research/condition_research/generated_conditions/lattice_v3_design_20260709"
    / "source_read_receipt_v3_design_20260709.json"
)
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / ".omo/evidence/task-1-ai-condition-loop-canonical-rebuild-20260711"
    / "verification.json"
)

# Hard-coded canonical set. Do NOT read this from the receipt itself.
REQUIRED_SOURCES = [
    "docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md",
    "docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md",
    "docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_review.md",
    "docs/update_log/2026-07-09_lattice_v2_closeout_or_new_design_handoff.md",
    "docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_closeout_or_new_design_decision_20260709.json",
    "docs/research/condition_research/generated_conditions/lattice_v2_to_plan_d_conditional_20260708/v2_corrected_sell_risk_clause_audit_20260709.md",
    "docs/update_log/2026-07-09_lattice_v2_closeout_context_matrix.md",
    "docs/update_log/2026-07-08_condition_research_full_result_and_analysis.md",
    "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_official_full_warm64_288_export_summary_20260705.json",
    "docs/research/condition_research/research_runs/seed_lattice_20260702/p5_min_official_full_warm64_288_export_summary_20260705.json",
    "docs/research/condition_research/research_runs/seed_lattice_20260702/p6_lattice_go_no_go_hold_20260705.json",
    "docs/AGENT_HANDOFF.md",
    "docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md",
    "utility/ai_agent/strategy.txt",
    "utility/ai_agent/rules.txt",
    "AGENTS.md",
    "docs/AGENTS.md",
]

CANONICAL_SCOPE = "design_only_no_generation_no_db_no_replay_no_oos_no_plan_d_no_portfolio_no_export_live"

FORBIDDEN_TOKENS = {
    "generation",
    "db",
    "replay",
    "oos",
    "plan_d",
    "portfolio",
    "export",
    "live",
}


def file_stats(p: Path):
    data = p.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    line_count = data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return sha256, line_count


def check_scope(scope_value: str, errors: list):
    if scope_value == CANONICAL_SCOPE:
        return
    # Strip every "no_<token>" occurrence; whatever remains is inspected for
    # bare forbidden capability tokens.
    stripped = scope_value
    for token in FORBIDDEN_TOKENS:
        stripped = stripped.replace(f"no_{token}", "")
    remaining_tokens = [t for t in stripped.split("_") if t]
    leaked = [t for t in remaining_tokens if t in FORBIDDEN_TOKENS]
    if leaked:
        errors.append({
            "code": "forbidden_scope",
            "detail": f"scope '{scope_value}' contains enabled forbidden token(s): {sorted(set(leaked))}",
        })
    else:
        errors.append({
            "code": "scope_mismatch",
            "detail": f"scope '{scope_value}' does not equal canonical string '{CANONICAL_SCOPE}'",
        })


def main():
    parser = argparse.ArgumentParser(description="Verify CL-D0 source read receipt")
    parser.add_argument("--receipt", default=str(DEFAULT_RECEIPT_PATH), help="Path to receipt JSON to verify")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Path to write the verification report JSON")
    args = parser.parse_args()

    receipt_path = Path(args.receipt)
    report_path = Path(args.report)

    errors = []
    checked_sources = 0

    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append({"code": "receipt_unreadable", "detail": f"{receipt_path}: {exc}"})
        receipt = {}

    sources = receipt.get("sources", [])
    receipt_paths_by_role = {}
    receipt_paths_seen = set()

    for src in sources:
        rel_path = src.get("path")
        role = src.get("role")
        read_scope = src.get("read_scope")
        recorded_sha = src.get("sha256")
        recorded_lc = src.get("line_count")

        receipt_paths_seen.add(rel_path)
        receipt_paths_by_role.setdefault(role, []).append(rel_path)

        if read_scope != "full_document":
            errors.append({
                "code": "read_scope_incomplete",
                "detail": f"{rel_path}: read_scope={read_scope!r} (expected 'full_document')",
            })

        abs_path = REPO_ROOT / rel_path if rel_path else None
        if abs_path is None or not abs_path.exists():
            errors.append({"code": "missing_source", "detail": f"{rel_path}: file not found on disk"})
            continue

        checked_sources += 1
        actual_sha, actual_lc = file_stats(abs_path)

        if actual_sha != recorded_sha:
            errors.append({
                "code": "sha_mismatch",
                "detail": f"{rel_path}: recorded sha256={recorded_sha} actual={actual_sha}",
            })
        if actual_lc != recorded_lc:
            errors.append({
                "code": "line_count_mismatch",
                "detail": f"{rel_path}: recorded line_count={recorded_lc} actual={actual_lc}",
            })

    # Completeness: every required path must be present in the receipt.
    for req in REQUIRED_SOURCES:
        if req not in receipt_paths_seen:
            errors.append({"code": "missing_source", "detail": f"{req}: required source absent from receipt"})

    # Role authority counts.
    goal_authority_count = len(receipt_paths_by_role.get("goal_authority", []))
    execution_contract_count = len(receipt_paths_by_role.get("execution_contract", []))
    if goal_authority_count != 1:
        errors.append({
            "code": "role_authority_count",
            "detail": f"goal_authority count={goal_authority_count} (expected exactly 1)",
        })
    if execution_contract_count != 1:
        errors.append({
            "code": "role_authority_count",
            "detail": f"execution_contract count={execution_contract_count} (expected exactly 1)",
        })

    # Scope assertion.
    scope_value = receipt.get("scope")
    check_scope(scope_value, errors)

    all_pass = len(errors) == 0

    report = {
        "all_pass": all_pass,
        "errors": errors,
        "checked_sources": checked_sources,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
