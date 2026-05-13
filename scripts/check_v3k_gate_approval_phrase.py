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

FIRST_GATE = RECOMMENDED_APPROVAL_ORDER_FIRST
FIRST_GATE_RECORD = next(gate for gate in GATES if gate["gate"] == FIRST_GATE)
FIRST_GATE_PHRASE = str(FIRST_GATE_RECORD["phrase"])

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

    if normalized == FIRST_GATE_PHRASE:
        return ApprovalPhraseVerdict(
            accepted=True,
            status="accepted-review-only-first-gate",
            gate=FIRST_GATE,
            reason="exact first gate phrase matched; execution still needs preflight and USER_ACK handling",
        )

    for gate in GATES:
        if normalized == gate["phrase"]:
            return ApprovalPhraseVerdict(
                accepted=False,
                status="rejected-out-of-order-gate",
                gate=str(gate["gate"]),
                reason=f"gate {gate['gate']} is not the current first approval gate",
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
