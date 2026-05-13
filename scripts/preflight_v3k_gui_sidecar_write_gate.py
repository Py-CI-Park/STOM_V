from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import (  # noqa: E402
    FIRST_GATE,
    FIRST_GATE_PHRASE,
    evaluate_approval_phrase,
)
from scripts.preview_v3k_gui_sidecar_default_payload import (  # noqa: E402
    assert_default_off_payload,
    build_default_off_payload,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_DIR,
    V3K_GUI_SIDECAR_FILE,
)

GUI_SIDECAR_PREFLIGHT_VERSION = "V3K_GUI_SIDECAR_FIRST_GATE_PREFLIGHT_V1"
USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"
WRITER_SCRIPT = "scripts/write_v3k_gui_sidecar_from_preview.py"
ROLLBACK_SCRIPT = "scripts/rollback_v3k_gui_sidecar.py"

FORBIDDEN_ARTIFACT_PATHS = (
    V3K_GUI_SIDECAR_DIR,
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
)

REQUIRED_REVIEW_DOCS = (
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_approval_execution_packet.md",
    "docs/update_log/2026-05-13_v3k_gui_sidecar_write_readiness_audit.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_preapproval_completion_audit.md",
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
)


@dataclass(frozen=True)
class GuiSidecarGatePreflightReport:
    preflight_version: str
    gate: str
    phrase_status: str
    phrase_accepted: bool
    ready_for_execution: bool
    review_only: bool
    blocked_reasons: tuple[str, ...]
    target: str = V3K_GUI_SIDECAR_FILE
    creates_user_ack: bool = False
    creates_sidecar_artifact: bool = False
    executes_runtime: bool = False


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _artifact_status() -> str:
    return _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)


def _validate_review_docs() -> tuple[str, ...]:
    missing = [path for path in REQUIRED_REVIEW_DOCS if not (ROOT / path).is_file()]
    if missing:
        return tuple(f"missing review document: {path}" for path in missing)
    return ()


def _blocked_reasons(phrase: str | None) -> tuple[str, ...]:
    reasons: list[str] = []
    reasons.extend(_validate_review_docs())

    if not phrase:
        reasons.append("approval phrase not provided")
    else:
        verdict = evaluate_approval_phrase(phrase)
        if not verdict.accepted:
            reasons.append(f"approval phrase rejected: {verdict.status}")

    if os.environ.get(USER_ACK_ENV) != "1":
        reasons.append(f"{USER_ACK_ENV}=1 absent")

    if not (ROOT / WRITER_SCRIPT).is_file():
        reasons.append("actual GUI sidecar writer intentionally absent")

    if not (ROOT / ROLLBACK_SCRIPT).is_file():
        reasons.append("actual GUI sidecar rollback script intentionally absent")

    if (ROOT / V3K_GUI_SIDECAR_FILE).exists():
        reasons.append("actual GUI sidecar file already exists")

    if (ROOT / V3K_GUI_SIDECAR_DIR).exists():
        reasons.append("actual GUI sidecar directory already exists")

    status = _artifact_status()
    if status:
        reasons.append("forbidden artifact status is not clean")

    payload = build_default_off_payload()
    try:
        assert_default_off_payload(payload)
    except AssertionError as exc:
        reasons.append(f"default-OFF preview payload invalid: {exc}")

    return tuple(reasons)


def build_preflight_report(phrase: str | None = None) -> GuiSidecarGatePreflightReport:
    before = _artifact_status()
    verdict = evaluate_approval_phrase(phrase or "")
    reasons = _blocked_reasons(phrase)
    after = _artifact_status()
    if before != after:
        reasons = (*reasons, "preflight changed forbidden artifact status")

    phrase_status = "missing"
    phrase_accepted = False
    if phrase:
        phrase_status = verdict.status
        phrase_accepted = verdict.accepted

    return GuiSidecarGatePreflightReport(
        preflight_version=GUI_SIDECAR_PREFLIGHT_VERSION,
        gate=FIRST_GATE,
        phrase_status=phrase_status,
        phrase_accepted=phrase_accepted,
        ready_for_execution=not reasons,
        review_only=True,
        blocked_reasons=reasons,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review-only preflight for the first V3K GUI sidecar write gate."
    )
    parser.add_argument(
        "--phrase",
        help="Optional candidate approval phrase. This script never creates USER_ACK or artifacts.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format (default: json).",
    )
    parser.add_argument(
        "--expect-blocked",
        action="store_true",
        help="Exit non-zero if the preflight is unexpectedly ready for execution.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    report = build_preflight_report(args.phrase)
    if args.format == "json":
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"preflight_version={report.preflight_version}")
        print(f"gate={report.gate}")
        print(f"phrase_status={report.phrase_status}")
        print(f"phrase_accepted={str(report.phrase_accepted).lower()}")
        print(f"ready_for_execution={str(report.ready_for_execution).lower()}")
        for reason in report.blocked_reasons:
            print(f"blocked={reason}")

    if args.expect_blocked and report.ready_for_execution:
        raise SystemExit("preflight unexpectedly ready for execution")


if __name__ == "__main__":
    main()
