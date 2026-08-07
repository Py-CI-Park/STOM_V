#!/usr/bin/env python3
"""Independent static verifier for the CL-D1 failure lesson matrix.

Asserts the eight evidence families, the seven per-family fields, the three
mandatory conclusion tokens, the literal V2 count string, and the absence of
any go/hold reinterpretation. Exit 0 only when all checks pass.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_MATRIX_PATH = (
    REPO_ROOT
    / "docs/research/condition_research/generated_conditions/lattice_v3_design_20260709"
    / "lattice_v3_failure_lesson_matrix_20260709.md"
)
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / ".omo/evidence/task-2-ai-condition-loop-canonical-rebuild-20260711"
    / "verification.json"
)

# Recognizable substrings, one per required evidence family.
FAMILY_LABELS = [
    "tick 288",
    "min 288",
    "576",
    "repair composite",
    "Plan D",
    "V2",
    "sell/risk",
    "batch",
]

# Seven per-family column fields; each should appear once per family (>= 8).
FIELD_LABELS = [
    "engine/profile/process",
    "gate threshold",
    "entry structure",
    "exit/risk",
    "data leakage",
    "reusable asset",
    "forbidden inference",
]

MANDATORY_CONCLUSIONS = [
    "gate_relaxation_is_not_sufficient",
    "v2_sell_risk_table_superseded_but_decision_unchanged",
    "provider_batch_is_not_autonomous_learning",
]

V2_COUNT = "8/7/1/0/0/8"

# Regex patterns flagging an illegal go/hold/survivor reinterpretation (a
# positive integer assigned to go/hold/survivor). `\bgo` never matches the
# "go" inside "no_go", so correct statements like "no_go 576" are not flagged.
REINTERPRETATION_PATTERNS = [
    r"\bgo\s+[1-9]",
    r"\bhold\s+[1-9]",
    r"\bsurvivors?\s+[1-9]",
    r"생존\s*[1-9]",
]

# Correct negative-count statements that MUST be present.
REQUIRED_NEGATIVE_STATEMENTS = ["no_go 576", "go 0", "hold 0"]

EXPECTED_FAMILY_COUNT = 8


def main():
    parser = argparse.ArgumentParser(description="Verify CL-D1 failure lesson matrix")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    report_path = Path(args.report)
    errors = []

    try:
        text = matrix_path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "matrix_unreadable", "detail": f"{matrix_path}: {exc}"})
        text = ""

    lower = text.lower()

    # 1. Family section count via the '## Family ' anchor.
    family_sections = len(re.findall(r"(?m)^## Family ", text))
    if family_sections != EXPECTED_FAMILY_COUNT:
        errors.append({
            "code": "missing_family",
            "detail": f"found {family_sections} '## Family ' sections (expected {EXPECTED_FAMILY_COUNT})",
        })

    # 2. Family label substrings.
    for label in FAMILY_LABELS:
        if label.lower() not in lower:
            errors.append({"code": "missing_family_label", "detail": f"family label absent: {label!r}"})

    # 3. Mandatory conclusion tokens (verbatim).
    for token in MANDATORY_CONCLUSIONS:
        if token not in text:
            errors.append({"code": "missing_conclusion", "detail": f"conclusion token absent: {token}"})

    # 4. V2 literal count string.
    if V2_COUNT not in text:
        errors.append({"code": "v2_count_mismatch", "detail": f"literal V2 count {V2_COUNT!r} absent"})

    # 5. Seven per-family fields, each >= EXPECTED_FAMILY_COUNT occurrences.
    for field in FIELD_LABELS:
        n = lower.count(field.lower())
        if n < EXPECTED_FAMILY_COUNT:
            errors.append({
                "code": "missing_field",
                "detail": f"field {field!r} appears {n} times (expected >= {EXPECTED_FAMILY_COUNT})",
            })

    # 6. No go/hold/survivor reinterpretation; correct negatives present.
    for pat in REINTERPRETATION_PATTERNS:
        m = re.search(pat, lower)
        if m:
            errors.append({"code": "go_hold_reinterpretation", "detail": f"forbidden reinterpretation match {pat!r}: {m.group(0)!r}"})
    for good in REQUIRED_NEGATIVE_STATEMENTS:
        if good.lower() not in lower:
            errors.append({"code": "go_hold_reinterpretation", "detail": f"required negative-count statement absent: {good!r}"})

    all_pass = len(errors) == 0
    report = {
        "all_pass": all_pass,
        "errors": errors,
        "family_sections": family_sections,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
