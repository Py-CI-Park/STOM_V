from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import GATES  # noqa: E402
from scripts.summarize_v3k_gui_sidecar_first_gate_blockers import (  # noqa: E402
    build_blocker_snapshot,
)

REMAINING_GATE_STATUS_SUMMARY_VERSION = "V3K_REMAINING_GATE_STATUS_SUMMARY_V1"
OBJECTIVE = "V3 features + Kiwoom retained"
LS_EXCLUSION = "LS Securities REST/TR/REAL direct dependency excluded"


@dataclass(frozen=True)
class GateStatus:
    order: int
    gate: str
    risk: str
    status: str
    ack_env: str
    ack_present: bool
    phrase: str
    executable: bool
    blocked_reason: str


@dataclass(frozen=True)
class RemainingGateStatusSummary:
    summary_version: str
    objective: str
    ls_exclusion: str
    implementation_lane: str
    actual_gate_execution_progress: str
    safe_staged_progress: str
    next_gate: str
    next_phrase: str
    review_only: bool
    creates_user_ack: bool
    creates_artifacts: bool
    executes_runtime: bool
    gates: tuple[GateStatus, ...]


def _gate_status(gate: dict[str, object]) -> GateStatus:
    ack_env = str(gate["ack_env"])
    ack_present = os.environ.get(ack_env) == "1"
    return GateStatus(
        order=int(gate["order"]),
        gate=str(gate["gate"]),
        risk=str(gate["risk"]),
        status=str(gate["status"]),
        ack_env=ack_env,
        ack_present=ack_present,
        phrase=str(gate["phrase"]),
        executable=False,
        blocked_reason=f"{ack_env} absent" if not ack_present else "approval environment present but execution remains policy-gated",
    )


def build_remaining_gate_status_summary() -> RemainingGateStatusSummary:
    first = build_blocker_snapshot()
    return RemainingGateStatusSummary(
        summary_version=REMAINING_GATE_STATUS_SUMMARY_VERSION,
        objective=OBJECTIVE,
        ls_exclusion=LS_EXCLUSION,
        implementation_lane="STOM_Version_2U_C",
        actual_gate_execution_progress=first.actual_gate_execution_progress,
        safe_staged_progress=first.safe_staged_progress,
        next_gate=first.gate,
        next_phrase=first.accepted_phrase,
        review_only=True,
        creates_user_ack=False,
        creates_artifacts=False,
        executes_runtime=False,
        gates=tuple(_gate_status(gate) for gate in GATES),
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the remaining V3K approval gate status without side effects."
    )
    parser.add_argument(
        "--format",
        choices=("json", "text", "markdown"),
        default="json",
        help="Output format (default: json).",
    )
    return parser.parse_args(argv)


def _print_text(summary: RemainingGateStatusSummary) -> None:
    print(f"summary_version={summary.summary_version}")
    print(f"objective={summary.objective}")
    print(f"actual_gate_execution_progress={summary.actual_gate_execution_progress}")
    print(f"safe_staged_progress={summary.safe_staged_progress}")
    print(f"next_gate={summary.next_gate}")
    print(f"next_phrase={summary.next_phrase}")
    for gate in summary.gates:
        print(
            "gate="
            f"{gate.order}|{gate.gate}|{gate.status}|{gate.ack_env}|"
            f"ack_present={str(gate.ack_present).lower()}|executable={str(gate.executable).lower()}"
        )


def _print_markdown(summary: RemainingGateStatusSummary) -> None:
    print("| Order | Gate | Status | Executable |")
    print("| ---: | --- | --- | --- |")
    for gate in summary.gates:
        print(f"| {gate.order} | `{gate.gate}` | `{gate.status}` | `{str(gate.executable).lower()}` |")
    print()
    print(f"- actual_gate_execution_progress: `{summary.actual_gate_execution_progress}`")
    print(f"- safe_staged_progress: `{summary.safe_staged_progress}`")
    print(f"- next_phrase: `{summary.next_phrase}`")


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    summary = build_remaining_gate_status_summary()
    if args.format == "json":
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, sort_keys=True))
    elif args.format == "markdown":
        _print_markdown(summary)
    else:
        _print_text(summary)


if __name__ == "__main__":
    main()

