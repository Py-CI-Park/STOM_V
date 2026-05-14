from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import GATES
from scripts.audit_v3k_runtime_activation_gap import RECOMMENDED_APPROVAL_ORDER_FIRST
from strategy.v3k_analyzer_adapter import (
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file

FIRST_GATE = RECOMMENDED_APPROVAL_ORDER_FIRST
FIRST_GATE_RECORD = next(gate for gate in GATES if gate["gate"] == FIRST_GATE)
FIRST_GATE_PHRASE = str(FIRST_GATE_RECORD["phrase"])
COMPLETION_MARKERS = {
    "gui-sidecar-write-await-user-approval": "## V3K-GUI-SIDECAR-WRITE-ACTUAL-APPROVAL",
    "phase-f-f4-on-await-user-approval": "## V3K-PHASE-F-ENABLE",
    "phase-g-g3-on-await-user-approval": "## V3K-PHASE-G-ENABLE",
    "phase-h-h2-h3-live-dryrun-await-user-approval": "## V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL",
    "f1-actual-db-cutover-await-user-approval": "## V3K-F1-ACTUAL-DB-CUTOVER-APPROVAL",
    "live-order-exit-rule-consumption-await-user-approval": "## V3K-LIVE-ORDER-EXIT-ENABLE",
}

BROAD_APPROVAL_TOKENS = (
    "approve all",
    "all gates",
    "all gate",
    "approve everything",
    "turn everything on",
    "enable everything",
    "all approvals",
    "모두 승인",
    "전체 승인",
    "전부 승인",
    "모든 gate",
    "모든 게이트",
    "한번에 승인",
)


@dataclass(frozen=True)
class ApprovalPhraseVerdict:
    accepted: bool
    status: str
    gate: str | None
    reason: str
    review_only: bool = True
    creates_user_ack: bool = False
    creates_enable_registry: bool = False
    executes_runtime: bool = False


def _squash_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _registry_headings() -> set[str]:
    registry = ROOT / "docs" / "CARRY_FORWARD_REGISTRY.md"
    if not registry.is_file():
        return set()
    return {
        line.strip()
        for line in registry.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("## ")
    }


def _gate_has_completion_evidence(gate: str, headings: set[str]) -> bool:
    marker = COMPLETION_MARKERS.get(gate)
    if not marker or marker not in headings:
        return False
    if gate == "gui-sidecar-write-await-user-approval":
        return (ROOT / V3K_GUI_SIDECAR_FILE).is_file()
    if gate == "phase-f-f4-on-await-user-approval":
        sidecar = load_v3k_gui_sidecar_file(ROOT / V3K_GUI_SIDECAR_FILE)
        return sidecar.valid and sidecar.settings.get(FLAG_PHASE_F_ANALYZER_STRATEGY) is True
    if gate == "phase-g-g3-on-await-user-approval":
        sidecar = load_v3k_gui_sidecar_file(ROOT / V3K_GUI_SIDECAR_FILE)
        return sidecar.valid and sidecar.settings.get(FLAG_PHASE_G_MICROSTRUCTURE_ENGINE) is True
    return True


def completed_approval_gates() -> tuple[str, ...]:
    headings = _registry_headings()
    completed: list[str] = []
    for gate in GATES:
        gate_name = str(gate["gate"])
        if _gate_has_completion_evidence(gate_name, headings):
            completed.append(gate_name)
        else:
            break
    return tuple(completed)


def current_approval_gate_record() -> dict[str, object] | None:
    completed = set(completed_approval_gates())
    for gate in GATES:
        if str(gate["gate"]) not in completed:
            return gate
    return None


def evaluate_approval_phrase(phrase: str) -> ApprovalPhraseVerdict:
    """Evaluate a proposed V3K gate approval phrase without side effects.

    This is an intake guard only. An accepted verdict means the phrase is the
    next review-level candidate; it does not create USER_ACK, enable registry,
    sidecar artifacts, DB changes, KHOPENAPI sessions, or live wiring.
    """

    normalized = _squash_whitespace(phrase)
    lowered = normalized.lower()
    if not normalized:
        return ApprovalPhraseVerdict(
            accepted=False,
            status="rejected-empty",
            gate=None,
            reason="approval phrase is empty",
        )

    if any(token in lowered for token in BROAD_APPROVAL_TOKENS):
        return ApprovalPhraseVerdict(
            accepted=False,
            status="rejected-broad-approval",
            gate=None,
            reason="broad or multi-gate approval is not accepted",
        )

    current_gate = current_approval_gate_record()
    current_gate_name = str(current_gate["gate"]) if current_gate else None
    current_phrase = str(current_gate["phrase"]) if current_gate else None

    if current_gate and normalized == current_phrase:
        return ApprovalPhraseVerdict(
            accepted=True,
            status="accepted-review-only-current-gate",
            gate=current_gate_name,
            reason="exact current gate phrase matched; execution still needs preflight and USER_ACK handling",
        )

    for gate in GATES:
        if normalized == gate["phrase"]:
            gate_name = str(gate["gate"])
            if gate_name in completed_approval_gates():
                return ApprovalPhraseVerdict(
                    accepted=False,
                    status="rejected-already-completed-gate",
                    gate=gate_name,
                    reason=f"gate {gate_name} is already completed",
                )
            return ApprovalPhraseVerdict(
                accepted=False,
                status="rejected-out-of-order-gate",
                gate=gate_name,
                reason=f"gate {gate['gate']} is not the current approval gate",
            )

    return ApprovalPhraseVerdict(
        accepted=False,
        status="rejected-unknown-or-inexact",
        gate=None,
        reason="phrase does not exactly match the current one-gate approval phrase",
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review-only V3K one-gate approval phrase intake checker."
    )
    parser.add_argument(
        "--phrase",
        required=True,
        help="Candidate approval phrase to evaluate without side effects.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "--expect",
        choices=("accepted", "rejected"),
        help="Optional expectation; exits non-zero if the verdict differs.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    verdict = evaluate_approval_phrase(args.phrase)

    if args.format == "json":
        print(json.dumps(asdict(verdict), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={verdict.status}")
        print(f"accepted={str(verdict.accepted).lower()}")
        print(f"gate={verdict.gate or ''}")
        print(f"reason={verdict.reason}")
        print("side_effects=none")

    if args.expect == "accepted" and not verdict.accepted:
        raise SystemExit(1)
    if args.expect == "rejected" and verdict.accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
