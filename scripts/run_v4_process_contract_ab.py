"""Deterministic, offline A/B evidence for typed feedback prompt routing.

This is a process-contract harness, not a backtest.  It never invokes a
provider, backtest, database, or network service and never makes a performance
claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_strategy_loop.brain.prompt import build_messages
from ai_strategy_loop.controller.feedback_resolver import (
    FeedbackDataRole,
    FeedbackDirective,
    FeedbackSide,
    FeedbackStatus,
    TypedFeedbackEnvelope,
    resolve_feedback,
)

SCHEMA = "v4_process_contract_ab.v1"
GENERATION = 7
EVIDENCE_ID = "a" * 64
SCOPE = "analysis_card_v3_prompt"


def _directive(
    statement: str,
    *,
    side: FeedbackSide,
    role: FeedbackDataRole = FeedbackDataRole.TRAIN,
    priority: int = 10,
    expires_generation: int = GENERATION,
    status: FeedbackStatus = FeedbackStatus.READY,
) -> FeedbackDirective:
    return FeedbackDirective(
        scope=SCOPE,
        side=side,
        role=role,
        priority=priority,
        statement=statement,
        evidence_id=EVIDENCE_ID,
        evidence_sha256=EVIDENCE_ID,
        created_generation=GENERATION - 1,
        expires_generation=expires_generation,
        status=status,
    )


def _fixed_directives() -> tuple[FeedbackDirective, ...]:
    """Return a fixed corpus with one same-scope conflict and unsafe entries."""
    return (
        _directive("BUY winner: require volume confirmation.", side=FeedbackSide.BUY, priority=20),
        _directive("BUY loser: allow every price move.", side=FeedbackSide.BUY, priority=1),
        _directive("SELL winner: exit after trailing reversal.", side=FeedbackSide.SELL),
        _directive("HOLDOUT BUY: optimize on evaluation data.", side=FeedbackSide.BUY, role=FeedbackDataRole.HOLDOUT),
        _directive("STALE BUY: reuse retired threshold.", side=FeedbackSide.BUY, expires_generation=GENERATION - 1),
        _directive("BLOCKED BUY: override risk controls.", side=FeedbackSide.BUY, status=FeedbackStatus.BLOCKED),
    )


def _message_text(messages: Iterable[dict[str, str]]) -> str:
    return "\n".join(message["content"] for message in messages)


def _route(directives: Iterable[FeedbackDirective], side: FeedbackSide) -> list[dict[str, str]]:
    return [
        {
            "directive_id": directive.directive_id or "",
            "scope": directive.scope,
            "side": directive.side.value,
            "role": directive.role.value,
            "statement": directive.statement,
        }
        for directive in directives
        if directive.side is side
    ]


def run_process_contract_ab() -> dict[str, Any]:
    """Produce deterministic process evidence for legacy and typed prompt paths.

    The two arms receive the same directives, generation, and evidence ID.  The
    legacy arm deliberately supplies only free text, which is the historical
    BUY-only path and therefore cannot apply typed authority checks.
    """
    directives = _fixed_directives()
    legacy_lines = [directive.statement for directive in directives]
    envelope = TypedFeedbackEnvelope(
        scope=SCOPE, evidence_id=EVIDENCE_ID, generation=GENERATION, directives=directives
    )
    resolution = resolve_feedback(
        directives, generation=GENERATION, evidence_hashes={EVIDENCE_ID: EVIDENCE_ID}
    )
    strict_actionable = resolution.actionable_directives

    legacy_buy_prompt = _message_text(build_messages("buy", card_directive_lines=legacy_lines))
    legacy_sell_prompt = _message_text(build_messages("sell", card_directive_lines=legacy_lines))
    strict_buy_prompt = _message_text(build_messages("buy", card_directive_lines=envelope))
    strict_sell_prompt = _message_text(build_messages("sell", card_directive_lines=envelope))

    # Legacy free text is injected into the BUY destination without typed routing.
    # Compare that routed set with the resolved BUY set so a valid SELL directive
    # misrouted to BUY is counted as contamination as well.
    baseline_buy_directives = tuple(directives)
    strict_buy_directives = tuple(
        directive for directive in strict_actionable if directive.side is FeedbackSide.BUY
    )
    strict_sell_directives = tuple(
        directive for directive in strict_actionable if directive.side is FeedbackSide.SELL
    )
    strict_buy_ids = {directive.directive_id for directive in strict_buy_directives}
    baseline_buy_contamination = tuple(
        directive
        for directive in baseline_buy_directives
        if directive.directive_id not in strict_buy_ids
    )
    strict_sell_ids = {directive.directive_id for directive in strict_sell_directives}
    unauthorized_sell_directives = tuple(
        directive
        for directive in directives
        if directive.directive_id not in strict_sell_ids
    )
    conflicted_directives = tuple(
        item.directive
        for item in resolution.directives
        if item.reason_code == "CONFLICTING_SCOPE_DIRECTIVE"
    )
    blocked_by_reason: dict[str, int] = {}
    for item in resolution.directives:
        if not item.actionable:
            blocked_by_reason[item.reason_code] = blocked_by_reason.get(item.reason_code, 0) + 1
    result = {
        "schema": SCHEMA,
        "performance_proved": False,
        "claim": "Process routing and contamination evidence only; no strategy return improvement is claimed.",
        "fixed_input": {
            "generation": GENERATION,
            "evidence_id": EVIDENCE_ID,
            "scope": SCOPE,
            "directives": [directive.to_dict() for directive in directives],
        },
        "baseline": {
            "path": "legacy_free_text_buy_only",
            "routed_buy": _route(baseline_buy_directives, FeedbackSide.BUY)
            + _route(baseline_buy_directives, FeedbackSide.SELL),
            "routed_sell": [],
            "routed_buy_count": len(baseline_buy_directives),
            "routed_sell_count": 0,
            "leakage_count": len(baseline_buy_contamination),
            "unauthorized_buy_directive_ids": [
                directive.directive_id for directive in baseline_buy_contamination
            ],
            "same_scope_conflicts_unreduced": len(conflicted_directives),
            "buy_prompt_contains_all_free_text": all(line in legacy_buy_prompt for line in legacy_lines),
            "sell_prompt_contains_free_text": any(line in legacy_sell_prompt for line in legacy_lines),
        },
        "strict": {
            "path": "typed_feedback_envelope",
            "routed_buy": _route(strict_buy_directives, FeedbackSide.BUY),
            "routed_sell": _route(strict_sell_directives, FeedbackSide.SELL),
            "routed_buy_count": len(strict_buy_directives),
            "routed_sell_count": len(strict_sell_directives),
            "leakage_count": 0,
            "same_scope_conflicts_reduced": len(conflicted_directives),
            "excluded_by_reason": dict(sorted(blocked_by_reason.items())),
            "buy_prompt_contains_only_authorized": (
                "BUY winner: require volume confirmation." in strict_buy_prompt
                and "SELL winner: exit after trailing reversal." not in strict_buy_prompt
                and all(
                    item.statement not in strict_buy_prompt
                    for item in baseline_buy_contamination
                )
            ),
            "sell_prompt_contains_only_authorized": (
                "SELL winner: exit after trailing reversal." in strict_sell_prompt
                and "BUY winner: require volume confirmation." not in strict_sell_prompt
                and all(
                    item.statement not in strict_sell_prompt
                    for item in unauthorized_sell_directives
                )
            ),
        },
    }
    return result


def analyze_csv(csv_path: str | Path) -> dict[str, Any]:
    """Read one existing trade CSV and return deterministic AnalysisCardV3 metadata."""
    import pandas as pd

    from ai_strategy_loop.autopsy.analysis_card import build_analysis_card_v3

    path = _canonical_path(csv_path, argument="--csv")
    raw_bytes = path.read_bytes()
    frame = pd.read_csv(path)
    canonical_columns = {"수익률", "수익금", "최고수익률", "최저수익률", "매수시간", "종목코드"}
    feature_findings = [
        {"finding_type": "csv_column_inventory", "feature": column, "non_null_count": int(frame[column].notna().sum())}
        for column in sorted(str(column) for column in frame.columns if str(column) not in canonical_columns)
    ]
    source = {
        "kind": "read_only_csv",
        "csv_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "row_count": int(len(frame)),
    }
    card = build_analysis_card_v3(
        frame,
        source=source,
        role="train",
        feature_importance_findings=feature_findings,
    )
    return {
        "schema": "v4_process_contract_ab.csv_analysis.v1",
        "csv_sha256": source["csv_sha256"],
        "row_count": int(len(frame)),
        "analysis_card_v3_count": 1,
        "feature_findings_count": len(feature_findings),
        "analysis_card_content_hash": card.content_hash,
        "analysis_card_quality": card.quality,
        "actionable_directives_count": len(card.actionable_directives),
        "read_only": True,
        "performance_proved": False,
    }


def _canonical_path(value: str | Path, *, argument: str) -> Path:
    """Return an absolute path without accepting ambiguous Win32 aliases."""
    raw_path = Path(value).expanduser()
    if not raw_path.is_absolute() and ".." in raw_path.parts:
        raise ValueError(f"{argument} must not contain relative parent traversal")
    if any(part not in (raw_path.anchor, "") and part.rstrip(" .") != part for part in raw_path.parts):
        raise ValueError(f"{argument} must not contain Win32 trailing dot/space aliases")
    if any(part not in (raw_path.anchor, "") and ":" in part for part in raw_path.parts):
        raise ValueError(f"{argument} must not contain NTFS alternate-data-stream syntax")
    return raw_path.resolve(strict=False)


def _path_key(path: Path) -> str:
    """Compare canonical paths using Win32 case and component alias rules."""
    normalized_parts = (part.rstrip(" .") for part in path.parts)
    return "/".join(normalized_parts).replace("\\", "/").casefold()


def _protected_output_path(path: Path) -> bool:
    parts = tuple(part.casefold() for part in path.parts)
    name = path.name.casefold()
    protected_roots = {"_database", "_database_v3k_shadow", "_log", "backup", ".gjc"}
    return (
        any(part in protected_roots for part in parts)
        or name.endswith(".db")
        or (name.startswith("v3k_settings") and name.endswith(".json"))
        or ("backtest", "graph") in zip(parts, parts[1:])
        or (".omx", "reports") in zip(parts, parts[1:])
        or ("ai_strategy_loop", "state") in zip(parts, parts[1:])
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline typed-feedback process-contract A/B evidence.")
    parser.add_argument("--csv", help="Existing trade CSV to analyze read-only.")
    parser.add_argument("--output", help="Explicit JSON output path; absent means stdout only.")
    args = parser.parse_args(argv)

    try:
        csv_path = _canonical_path(args.csv, argument="--csv") if args.csv else None
        output_path = _canonical_path(args.output, argument="--output") if args.output else None
    except ValueError as exc:
        parser.error(str(exc))
    if output_path and _protected_output_path(output_path):
        parser.error("--output must not target a protected path")
    if output_path and csv_path and _path_key(output_path) == _path_key(csv_path):
        parser.error("--output must not alias --csv")

    result = run_process_contract_ab()
    if csv_path:
        result["csv_analysis"] = analyze_csv(csv_path)
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
