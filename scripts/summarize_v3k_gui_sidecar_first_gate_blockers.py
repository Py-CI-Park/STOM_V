from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import FIRST_GATE, FIRST_GATE_PHRASE  # noqa: E402
from scripts.preflight_v3k_gui_sidecar_write_gate import (  # noqa: E402
    USER_ACK_ENV,
    build_preflight_report,
)

BLOCKER_SNAPSHOT_VERSION = "V3K_GUI_SIDECAR_FIRST_GATE_BLOCKER_SNAPSHOT_V1"


@dataclass(frozen=True)
class FirstGateBlockerSnapshot:
    snapshot_version: str
    gate: str
    accepted_phrase: str
    ready_for_execution: bool
    actual_gate_execution_progress: str
    safe_staged_progress: str
    blockers: tuple[str, ...]
    next_clearance_conditions: tuple[str, ...]
    review_only: bool = True
    creates_user_ack: bool = False
    creates_sidecar_artifact: bool = False
    executes_runtime: bool = False


def build_blocker_snapshot() -> FirstGateBlockerSnapshot:
    report = build_preflight_report(FIRST_GATE_PHRASE)
    next_clearance_conditions = (
        f"explicit one-gate approval phrase remains exact: {FIRST_GATE_PHRASE}",
        f"{USER_ACK_ENV}=1 or equivalent approved update_log record",
        "approved isolated writer implementation",
        "approved rollback script and owner acceptance",
        "default-OFF payload checksum and schema acceptance",
        "green pre-execution V3K audit suite",
        "post-write audit and artifact policy confirmation",
    )
    return FirstGateBlockerSnapshot(
        snapshot_version=BLOCKER_SNAPSHOT_VERSION,
        gate=FIRST_GATE,
        accepted_phrase=FIRST_GATE_PHRASE,
        ready_for_execution=report.ready_for_execution,
        actual_gate_execution_progress="0/6",
        safe_staged_progress="about 96%",
        blockers=report.blocked_reasons,
        next_clearance_conditions=next_clearance_conditions,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the current blockers for the first V3K GUI sidecar gate."
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format (default: json).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    snapshot = build_blocker_snapshot()
    if args.format == "json":
        print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(f"snapshot_version={snapshot.snapshot_version}")
    print(f"gate={snapshot.gate}")
    print(f"ready_for_execution={str(snapshot.ready_for_execution).lower()}")
    print(f"actual_gate_execution_progress={snapshot.actual_gate_execution_progress}")
    print(f"safe_staged_progress={snapshot.safe_staged_progress}")
    for blocker in snapshot.blockers:
        print(f"blocker={blocker}")
    for condition in snapshot.next_clearance_conditions:
        print(f"next_clearance={condition}")


if __name__ == "__main__":
    main()
