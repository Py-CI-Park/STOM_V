from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

PY_COMPILE_TARGETS = (
    "strategy/v3k_analyzer_adapter.py",
    "strategy/v3k_microstructure_engine.py",
    "scripts/backtest_v3k_phase_g_parity.py",
    "scripts/benchmark_v3k_phase_g_engine.py",
    "scripts/audit_v3k_phase_g_ls_excise.py",
    "scripts/smoke_v3k_phase_g_engine_unit.py",
    "scripts/audit_v3k_runtime_activation_gap.py",
    "scripts/audit_v3k_verify_1a.py",
    "scripts/audit_v3k_verify_1b_closure.py",
    "scripts/audit_v3k_gui_sidecar_write_readiness.py",
    "scripts/audit_v3k_remaining_approval_gates.py",
    "scripts/preview_v3k_gui_sidecar_default_payload.py",
    "scripts/audit_v3k_gui_sidecar_approval_template.py",
    "scripts/audit_v3k_gui_sidecar_preapproval_completion.py",
    "scripts/audit_v3k_remaining_gate_approval_matrix.py",
    "scripts/run_v3k_audit_suite.py",
    "scripts/summarize_v3k_phase_g_evidence.py",
)

ARTIFACT_GUARD_PATHS = (
    "_v3k_sidecar",
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
)


@dataclass(frozen=True)
class AuditStep:
    name: str
    command: tuple[str, ...]
    description: str


def _python(*args: str) -> tuple[str, ...]:
    return (sys.executable, *args)


def build_steps(base_ref: str) -> tuple[AuditStep, ...]:
    """Return the canonical V3K audit sequence for 2U_C.

    V3K_AUDIT_RUNNER_POLICY: this repo-tracked runner is the approved M2
    local execution surface. It does not install `.git/hooks`, does not edit
    external CI, and does not turn on Phase F/G/H runtime features.
    """

    return (
        AuditStep(
            "py_compile",
            _python("-m", "py_compile", *PY_COMPILE_TARGETS),
            "Compile V3K adapter, Phase G proof, audits, and this runner.",
        ),
        AuditStep(
            "phase_g_parity",
            _python("scripts/backtest_v3k_phase_g_parity.py"),
            "Run synthetic/caller-owned Phase G parity proof.",
        ),
        AuditStep(
            "phase_g_benchmark",
            _python("scripts/benchmark_v3k_phase_g_engine.py"),
            "Run synthetic Phase G benchmark proof.",
        ),
        AuditStep(
            "phase_g_evidence_summary",
            _python("scripts/summarize_v3k_phase_g_evidence.py", "--format", "json"),
            "Print commit-safe Phase G evidence summary and hash raw local reports without committing them.",
        ),
        AuditStep(
            "phase_g_ls_excise",
            _python("scripts/audit_v3k_phase_g_ls_excise.py"),
            "Ensure Phase G staging has no LS/broker runtime dependency marker.",
        ),
        AuditStep(
            "phase_g_unit_smoke",
            _python("scripts/smoke_v3k_phase_g_engine_unit.py"),
            "Check Phase G engine default-OFF/unit behavior.",
        ),
        AuditStep(
            "runtime_activation_gap",
            _python("scripts/audit_v3k_runtime_activation_gap.py"),
            "Check remaining activation gates and next-candidate matrix.",
        ),
        AuditStep(
            "gui_sidecar_write_readiness",
            _python("scripts/audit_v3k_gui_sidecar_write_readiness.py"),
            "Check GUI sidecar write readiness remains blocked before approval.",
        ),
        AuditStep(
            "remaining_approval_gate_blocker",
            _python("scripts/audit_v3k_remaining_approval_gates.py"),
            "Check all remaining approval gates stay blocked before explicit approval.",
        ),
        AuditStep(
            "gui_sidecar_payload_preview",
            _python("scripts/preview_v3k_gui_sidecar_default_payload.py", "--format", "json"),
            "Preview the first GUI sidecar default-OFF payload without writing artifacts.",
        ),
        AuditStep(
            "gui_sidecar_approval_template",
            _python("scripts/audit_v3k_gui_sidecar_approval_template.py"),
            "Check the GUI sidecar write approval template exists while writer remains blocked.",
        ),
        AuditStep(
            "gui_sidecar_preapproval_completion",
            _python("scripts/audit_v3k_gui_sidecar_preapproval_completion.py"),
            "Check the first GUI sidecar gate is review-ready but still execution-blocked.",
        ),
        AuditStep(
            "remaining_gate_approval_matrix",
            _python("scripts/audit_v3k_remaining_gate_approval_matrix.py"),
            "Check all six remaining gate approval phrases exist while every gate stays blocked.",
        ),
        AuditStep(
            "verify_1a",
            _python("scripts/audit_v3k_verify_1a.py", "--base", base_ref),
            "Check OFF regression, Kiwoom untouched, LS excise, artifact guard.",
        ),
        AuditStep(
            "verify_1b_closure",
            _python("scripts/audit_v3k_verify_1b_closure.py"),
            "Check V3K closure docs/code/script inventory and default-OFF contract.",
        ),
        AuditStep(
            "nonrelease_sync",
            _python("scripts/verify_nonrelease_sync.py"),
            "Check 2U_C nonrelease sync guardrails.",
        ),
        AuditStep(
            "diff_check",
            ("git", "diff", "--check"),
            "Reject whitespace errors in the current diff.",
        ),
        AuditStep(
            "artifact_status",
            ("git", "status", "--short", "--", *ARTIFACT_GUARD_PATHS),
            "Ensure DB/runtime/sidecar/report artifacts are not staged or modified.",
        ),
    )


def _format_command(command: Sequence[str]) -> str:
    return " ".join(command)


def run_step(step: AuditStep) -> None:
    print(f"[V3K audit] START {step.name}: {step.description}")
    print(f"[V3K audit] CMD   {_format_command(step.command)}")
    result = subprocess.run(
        step.command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(
            result.stderr,
            end="" if result.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )
    if result.returncode != 0:
        raise SystemExit(f"[V3K audit] FAIL {step.name}: exit {result.returncode}")
    if step.name == "artifact_status" and result.stdout.strip():
        raise SystemExit(
            "[V3K audit] FAIL artifact_status: forbidden artifact status is not clean"
        )
    print(f"[V3K audit] PASS  {step.name}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the repo-tracked V3K audit suite for STOM_Version_2U_C."
    )
    parser.add_argument(
        "--base",
        default="57496d24",
        help="Base ref passed to audit_v3k_verify_1a.py (default: 57496d24).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the audit steps without running them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    steps = build_steps(args.base)
    if args.list:
        for step in steps:
            print(f"{step.name}: {_format_command(step.command)}")
        return

    for step in steps:
        run_step(step)
    print(f"[V3K audit] PASS all {len(steps)} steps")


if __name__ == "__main__":
    main()
