import dataclasses
import hashlib

import pytest

from ai_strategy_loop.controller.feedback_resolver import (
    REASON_EVIDENCE_HASH_MISMATCH,
    REASON_EVIDENCE_MISSING,
    REASON_SCOPE_CONFLICT,
    REASON_STALE,
    FeedbackDataRole,
    FeedbackDirective,
    FeedbackSide,
    FeedbackStatus,
    resolve_feedback,
)


EVIDENCE_ID = "analysis-card-1"
EVIDENCE_HASH = hashlib.sha256(b"analysis-card-1").hexdigest()


def directive(**overrides):
    values = {
        "scope": "entry-quality",
        "side": FeedbackSide.BUY,
        "role": FeedbackDataRole.TRAIN,
        "priority": 10,
        "statement": "Prefer confirmed volume expansion.",
        "evidence_id": EVIDENCE_ID,
        "evidence_sha256": EVIDENCE_HASH,
        "created_generation": 3,
        "expires_generation": 5,
    }
    values.update(overrides)
    return FeedbackDirective(**values)


def resolve(items, generation=4, evidence_hashes=None):
    return resolve_feedback(
        items,
        generation=generation,
        evidence_hashes={EVIDENCE_ID: EVIDENCE_HASH} if evidence_hashes is None else evidence_hashes,
    )


def test_stale_directive_is_removed_from_actionable_results():
    result = resolve([directive(expires_generation=3)])

    assert result.actionable_directives == ()
    assert result.directives[0].status is FeedbackStatus.STALE
    assert result.directives[0].reason_code == REASON_STALE


def test_same_scope_side_conflict_selects_highest_priority_deterministically():
    lower = directive(priority=1, statement="Prefer a trend filter.")
    higher = directive(priority=20, statement="Prefer confirmation.")

    result = resolve([lower, higher])

    assert result.actionable_directives == (higher,)
    blocked = next(item for item in result.directives if item.directive == lower)
    assert blocked.status is FeedbackStatus.BLOCKED
    assert blocked.reason_code == REASON_SCOPE_CONFLICT


def test_scope_and_side_are_independent_conflict_dimensions():
    entry_buy = directive(scope="entry", side=FeedbackSide.BUY)
    exit_buy = directive(scope="exit", side=FeedbackSide.BUY)
    entry_sell = directive(scope="entry", side=FeedbackSide.SELL)

    result = resolve([entry_sell, exit_buy, entry_buy])

    assert set(result.actionable_directives) == {entry_buy, exit_buy, entry_sell}


def test_missing_and_mismatched_evidence_are_blocked():
    missing = directive(evidence_id="missing")
    mismatch = directive(statement="Different evidence.")

    result = resolve([missing, mismatch], evidence_hashes={EVIDENCE_ID: "0" * 64})

    by_directive = {item.directive.directive_id: item for item in result.directives}
    assert by_directive[missing.directive_id].reason_code == REASON_EVIDENCE_MISSING
    assert by_directive[mismatch.directive_id].reason_code == REASON_EVIDENCE_HASH_MISMATCH
    assert result.actionable_directives == ()


def test_holdout_is_always_descriptive_even_with_matching_evidence():
    holdout = directive(role=FeedbackDataRole.HOLDOUT)

    result = resolve([holdout])

    assert result.actionable_directives == ()
    assert result.directives[0].status is FeedbackStatus.DESCRIPTIVE_ONLY


def test_duplicates_are_removed_and_output_order_is_stable():
    alpha = directive(scope="alpha", priority=3, statement="Alpha.")
    beta = directive(scope="beta", priority=3, statement="Beta.")

    first = resolve([beta, alpha, alpha])
    second = resolve([alpha, beta])

    assert first == second
    assert first.actionable_directives == (alpha, beta)


def test_contract_is_frozen_and_ids_are_content_addressed():
    item = directive()

    with pytest.raises(dataclasses.FrozenInstanceError):
        item.priority = 12
    assert item.directive_id == directive().directive_id
