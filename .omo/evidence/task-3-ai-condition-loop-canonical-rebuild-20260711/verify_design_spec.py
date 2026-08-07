#!/usr/bin/env python3
"""Independent verifier for the CL-D2 sole canonical design specification.

Asserts required sections, exactly one SOLE-CANONICAL declaration, the full
phase-alias set (CL-D0..D4 + CL-R01..R10), the five exact approval phrases,
key numeric budgets, and the absence of generated-body / DB-apply / replay
instructions; plus a repo scan proving no second active canonical spec.
Exit 0 only when all checks pass.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SPEC_PATH = (
    REPO_ROOT
    / "docs/research/condition_research/generated_conditions/lattice_v3_design_20260709"
    / "lattice_v3_design_spec_20260709.md"
)
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / ".omo/evidence/task-3-ai-condition-loop-canonical-rebuild-20260711"
    / "verification.json"
)
GENERATED_DIR = REPO_ROOT / "docs/research/condition_research/generated_conditions"

REQUIRED_HEADINGS = [
    "목표와 비목표",
    "권한 위계",
    "용어집",
    "정본 단계 ID",
    "단일 실행 소유권",
    "허용 입력과 제외 입력",
    "증거 스키마",
    "불변 ID와 hash 규칙",
    "append-only 저장 규칙",
    "min/tick lane 정책",
    "semantic identity",
    "2x2 기여도",
    "수치 예산",
    "봉인 OOS 정책",
    "인간 비교 가능성 정책",
    "go/no-go 표",
]

CANONICAL_PHRASE = "SOLE CANONICAL design specification"

PHASE_IDS = ["CL-D0", "CL-D1", "CL-D2", "CL-D3", "CL-D4"] + [f"CL-R{n:02d}" for n in range(1, 11)]

APPROVAL_PHRASES = [
    "I approve CL-R01-R06 code integration only",
    "I approve CL-R07 bounded mini-loop only",
    "I approve CL-R08 bounded min performance only",
    "I approve CL-R09 sealed OOS/WF only",
    "I approve CL-R10 benchmark promotion review only",
]

BUDGET_TOKENS = [
    "max 9 official evaluations",
    "max 3 provider pack calls",
    "120-minute wall cap",
    "max 11 official evaluations",
    "4-hour cap",
]

# Tokens that would indicate a generated body, DB apply, or replay instruction.
FORBIDDEN_BODY = ["buy_code", "sell_code", "INSERT INTO", "run_backtest("]


def main():
    parser = argparse.ArgumentParser(description="Verify CL-D2 canonical design spec")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    spec_path = Path(args.spec)
    report_path = Path(args.report)
    errors = []

    try:
        text = spec_path.read_text(encoding="utf-8")
    except Exception as exc:  # pragma: no cover
        errors.append({"code": "spec_unreadable", "detail": f"{spec_path}: {exc}"})
        text = ""

    # 1. Required sections.
    for h in REQUIRED_HEADINGS:
        if h not in text:
            errors.append({"code": "missing_section", "detail": f"required section absent: {h!r}"})

    # 2. Exactly one sole-canonical declaration.
    n_canonical = text.count(CANONICAL_PHRASE)
    if n_canonical != 1:
        errors.append({"code": "canonical_declaration", "detail": f"{CANONICAL_PHRASE!r} appears {n_canonical} times (expected exactly 1)"})

    # 3. Full phase-alias set.
    for pid in PHASE_IDS:
        if pid not in text:
            errors.append({"code": "missing_phase_alias", "detail": f"phase id absent: {pid}"})

    # 4. Exact approval phrases.
    for phrase in APPROVAL_PHRASES:
        if phrase not in text:
            errors.append({"code": "missing_approval_phrase", "detail": f"approval phrase absent: {phrase!r}"})

    # 5. Numeric budgets.
    for tok in BUDGET_TOKENS:
        if tok not in text:
            errors.append({"code": "missing_budget", "detail": f"budget token absent: {tok!r}"})

    # 6. No generated body / DB apply / replay instruction.
    for tok in FORBIDDEN_BODY:
        if tok in text:
            errors.append({"code": "forbidden_body", "detail": f"forbidden body/DB/replay token present: {tok!r}"})

    # 7. Repo scan: exactly one canonical spec in the generated-conditions tree.
    canonical_files = []
    if GENERATED_DIR.exists():
        for md in GENERATED_DIR.rglob("*.md"):
            try:
                if CANONICAL_PHRASE in md.read_text(encoding="utf-8"):
                    canonical_files.append(str(md.relative_to(REPO_ROOT)).replace("\\", "/"))
            except Exception:
                continue
    if len(canonical_files) != 1:
        errors.append({"code": "duplicate_canonical", "detail": f"generated_conditions declares SOLE CANONICAL in {len(canonical_files)} files: {canonical_files}"})

    all_pass = len(errors) == 0
    report = {
        "all_pass": all_pass,
        "errors": errors,
        "canonical_declaration_count": n_canonical,
        "canonical_files": canonical_files,
        "checked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
