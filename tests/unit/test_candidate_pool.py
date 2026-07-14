"""Contract tests for CL-R06 bounded candidate-pool selector (todo 12)."""

from __future__ import annotations

import random

import pytest

from ai_strategy_loop.controller.candidate_pool import (
    apply_coverage_quota_before_selection,
    check_run_wide_duplicate,
    fresh_seed_plan,
    new_run_wide_dedup_archive,
    register_run_wide_fingerprints,
    select_official_candidate,
    select_official_candidate_v2,
)
from cli.condition_fingerprint import ast_fingerprint
from cli.condition_generator import build_approved_b_registry

TIMEFRAME = 'min'
METHODOLOGY_VERSION = 'v1'

_FULL_PROVENANCE = {
    'estimator': 'bucket',
    'parameters': {'k': 1},
    'fit_role': 'train',
    'period': '2024-01..2024-06',
    'row_count': 500,
    'row_signature': 'sig-abc',
    'dataset_sha': 'a' * 64,
    'fold_id': 'fold-1',
    'source_receipt': 'receipt-1',
}

_PARTIAL_PROVENANCE = {
    'estimator': 'bucket',
    'fit_role': 'train',
}


def _proposal(
    candidate_id: str,
    *,
    lane: str,
    family: str,
    expression: str,
    novelty: float = 0.0,
    provenance: dict | None = _FULL_PROVENANCE,
) -> dict:
    return {
        'candidate_id': candidate_id,
        'lane': lane,
        'family': family,
        'expression': expression,
        'novelty': novelty,
        'threshold_provenance': provenance,
    }


def _base_round() -> list[dict]:
    return [
        _proposal(
            'repair-a', lane='repair', family='momentum', expression='체결강도 > 100', novelty=0.2,
        ),
        _proposal(
            'repair-b', lane='repair', family='volatility', expression='등락율 < 5', novelty=0.3,
        ),
        _proposal(
            'discovery-a', lane='discovery', family='momentum',
            expression='체결강도 >= 1.0', novelty=0.7,
        ),
        _proposal(
            'discovery-b', lane='discovery', family='breadth',
            expression='등락율 < -3', novelty=0.9, provenance=_PARTIAL_PROVENANCE,
        ),
    ]


def test_four_distinct_valid_proposals_select_exactly_one_deterministic_winner():
    proposals = _base_round()
    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['pool_blockers'] == []
    assert result['selected'] is not None
    assert len(result['rejected']) == 3
    # discovery-b has full-provenance-tier fallback but highest novelty; the
    # winner is decided by validity -> provenance completeness -> novelty ->
    # candidate_id. discovery-a has full provenance + is valid + is next
    # highest novelty among fully-provenanced candidates.
    assert result['selected']['candidate_id'] == 'discovery-a'
    rejected_ids = {entry['candidate']['candidate_id'] for entry in result['rejected']}
    assert rejected_ids == {'repair-a', 'repair-b', 'discovery-b'}
    for entry in result['rejected']:
        assert entry['reasons']


def test_shuffled_input_yields_identical_selection():
    proposals = _base_round()
    baseline = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    rng = random.Random(12345)
    for _ in range(5):
        shuffled = list(proposals)
        rng.shuffle(shuffled)
        result = select_official_candidate(
            shuffled, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        )
        assert result['selected'] == baseline['selected']
        assert result['pool_blockers'] == baseline['pool_blockers']
        assert {e['candidate']['candidate_id'] for e in result['rejected']} == (
            {e['candidate']['candidate_id'] for e in baseline['rejected']}
        )


def test_whitespace_and_and_reordered_duplicate_blocks_pool_with_no_selection():
    proposals = _base_round()
    # discovery-b becomes a semantic duplicate of repair-a via whitespace +
    # parenthesization (ast_fingerprint collapses these to the same hash).
    proposals[3] = _proposal(
        'discovery-b', lane='discovery', family='breadth',
        expression='  ( 체결강도  >  100 ) ', novelty=0.9,
    )

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert any(blocker.startswith('semantic_duplicate:') for blocker in result['pool_blockers'])
    assert len(result['rejected']) == 4
    for entry in result['rejected']:
        assert any(r.startswith('semantic_duplicate:') for r in entry['reasons'])


def test_and_reordered_duplicate_expression_also_blocks():
    proposals = _base_round()
    proposals[0] = _proposal(
        'repair-a', lane='repair', family='momentum',
        expression='체결강도 > 100 and 등락율 < 5', novelty=0.2,
    )
    proposals[1] = _proposal(
        'repair-b', lane='repair', family='volatility',
        # same boolean expression, AND operands reordered -> same fingerprint.
        expression='등락율 < 5 and 체결강도 > 100', novelty=0.3,
    )

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert any(blocker.startswith('semantic_duplicate:') for blocker in result['pool_blockers'])


def test_third_same_family_candidate_triggers_family_quota_blocker():
    proposals = _base_round()
    # discovery-b's family becomes 'momentum', matching repair-a and
    # discovery-a: 3 momentum candidates > MAX_PER_FAMILY (2).
    proposals[3] = _proposal(
        'discovery-b', lane='discovery', family='momentum',
        expression='등락율 < -3', novelty=0.9,
    )

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert 'family_over_quota:momentum' in result['pool_blockers']


@pytest.mark.parametrize('proposal_count', [3, 5])
def test_wrong_proposal_count_blocks_pool_with_no_selection(proposal_count):
    base = _base_round()
    proposals = base[:proposal_count] if proposal_count < 4 else base + [
        _proposal('extra', lane='discovery', family='breadth', expression='체결강도 > 200', novelty=0.1),
    ]

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert any(b.startswith('wrong_proposal_count:') for b in result['pool_blockers'])


def test_wrong_lane_mix_blocks_pool_with_no_selection():
    proposals = _base_round()
    # 3 repair / 1 discovery instead of 2/2.
    proposals[3] = _proposal(
        'discovery-b-turned-repair', lane='repair', family='breadth',
        expression='등락율 < -3', novelty=0.9,
    )

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert any(b.startswith('wrong_lane_count:') for b in result['pool_blockers'])


def test_selector_performs_zero_evaluator_or_provider_calls(monkeypatch):
    """The selector is pure: it must never touch network/db/provider modules."""

    calls: list[str] = []

    def _forbidden(*_args, **_kwargs):
        calls.append('called')
        raise AssertionError('candidate_pool must not call evaluator/provider code')

    monkeypatch.setattr('socket.socket.connect', _forbidden, raising=False)

    proposals = _base_round()
    select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    # Also exercise a blocked round to confirm no side calls happen there either.
    select_official_candidate(
        proposals[:3], timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert calls == []


def test_all_structurally_invalid_round_blocks_selection_with_no_promotion():
    """G003 CL-R06 review fix: if every proposal in the round is structurally
    invalid, the pool must NOT promote the top-ranked (least-bad) invalid
    candidate — selected stays None and a dedicated blocker is reported, so
    zero official quota is spent on an invalid round."""
    proposals = _base_round()
    for proposal in proposals:
        # empty expression is never structurally valid (validate_b_only never
        # even runs — _is_structurally_valid short-circuits on blank input)
        # and never produces a fingerprint, so no semantic-duplicate blocker
        # is spuriously triggered alongside it.
        proposal['expression'] = ''

    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['selected'] is None
    assert 'no_structurally_valid_candidate' in result['pool_blockers']
    assert len(result['rejected']) == 4
    for entry in result['rejected']:
        assert 'no_structurally_valid_candidate' in entry['reasons']
        assert 'not_structurally_valid' in entry['reasons']


def test_normal_valid_round_still_selects_exactly_one_official_candidate():
    """Sanity companion to the all-invalid case: an ordinary valid round is
    unaffected by the G003 fix and still promotes exactly one candidate."""
    proposals = _base_round()
    result = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )

    assert result['pool_blockers'] == []
    assert result['selected'] is not None
    assert 'no_structurally_valid_candidate' not in result['pool_blockers']
    assert len(result['rejected']) == 3
# ===================================================================
# DR-04 -- final-owner lifecycle (select_official_candidate_v2 wrapper).
#   select_official_candidate itself (tested exhaustively above) stays
#   UNCHANGED; these tests exercise the additive pre-selection pipeline only.
# ===================================================================


def test_v2_with_no_extra_params_matches_v1_exactly():
    """Bullet 1 -- final-owner wiring default-OFF-equivalent: with none of the
    optional DR-04 params supplied, select_official_candidate_v2 must select
    the same official candidate as the unchanged select_official_candidate."""
    proposals = _base_round()
    v1 = select_official_candidate(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    v2 = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    assert v2['selected'] == v1['selected']
    assert v2['rejected'] == v1['rejected']
    assert v2['pool_blockers'] == v1['pool_blockers']
    assert v2['ai_performance_excluded_ids'] == []
    assert v2['seed_plan'] is None


def test_v2_fresh_seed_plan_reads_no_body_and_earns_zero_credit():
    """Bullet 3 -- fresh SeedPlan carries body_consumed=False and zero credit."""
    plan = fresh_seed_plan()
    assert plan.mode == 'fresh'
    assert plan.body_consumed is False
    assert plan.buy_body is None
    assert plan.sell_body is None
    assert plan.seed_credit == 0

    result = select_official_candidate_v2(
        _base_round(), timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        seed_plan=plan,
    )
    assert result['seed_plan']['mode'] == 'fresh'
    assert result['seed_plan']['body_consumed'] is False
    assert result['seed_plan']['seed_credit'] == 0


def test_v2_coverage_quota_applied_before_selection():
    """Bullet 5 -- coverage quotas trim the round BEFORE select_official_candidate
    runs, so a 3-in-one-bucket discovery over-quota still yields a valid
    (2 repair + 2 discovery) round instead of a wrong_proposal_count blocker."""
    proposals = _base_round()
    # two repair + THREE discovery sharing one coverage bucket (over quota=2).
    extra_discovery = dict(proposals[2])
    extra_discovery['candidate_id'] = 'discovery-c'
    extra_discovery['expression'] = '체결강도 >= 2.0'
    for entry in (proposals[2], proposals[3], extra_discovery):
        entry['coverage_bucket_keys'] = ['bucket_x']
    proposals.append(extra_discovery)

    kept, reasons = apply_coverage_quota_before_selection(proposals)
    assert len(kept) == 4
    assert any(r.startswith('coverage_bucket_over_quota:bucket_x') for r in reasons)

    result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    assert any(b.startswith('coverage_bucket_over_quota:bucket_x') for b in result['pool_blockers'])
    # the trimmed round is still a valid 2/2 shape, so selection still happens.
    assert result['selected'] is not None


def test_v2_run_wide_ast_duplicate_rejected_before_evaluation_budget():
    """Bullet 4 -- a run-wide AST duplicate must be rejected BEFORE it can
    consume evaluation budget: it never reaches select_official_candidate."""
    proposals = _base_round()
    archive = new_run_wide_dedup_archive()
    dup_fp = ast_fingerprint(
        proposals[0]['expression'], timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    register_run_wide_fingerprints(archive, ast_fingerprint=dup_fp)
    # confirm the pure checker itself flags it (no mutation).
    assert check_run_wide_duplicate(archive, ast_fingerprint=dup_fp) == [
        f'run_wide_ast_duplicate:{dup_fp}'
    ]

    result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        run_wide_archive=archive,
    )
    # removing one proposal breaks the required 2/2 lane shape -> no selection,
    # and the round-level blocker list carries the run-wide duplicate reason.
    assert result['selected'] is None
    assert any('run_wide_ast_duplicate' in b for b in result['pool_blockers'])


def test_v2_run_wide_rowset_duplicate_rejected_before_evaluation_budget():
    """Bullet 4 -- run-wide ROWSET duplicates are rejected the same way as AST."""
    proposals = _base_round()
    proposals[1]['rowset_fingerprint'] = 'rowset-abc'
    archive = new_run_wide_dedup_archive()
    register_run_wide_fingerprints(archive, rowset_fingerprint='rowset-abc')

    result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        run_wide_archive=archive,
    )
    assert result['selected'] is None
    assert any('run_wide_rowset_duplicate:rowset-abc' in b for b in result['pool_blockers'])


def test_v2_run_wide_archive_persists_winner_across_rounds():
    """Bullet 4 -- the archive is genuinely run-wide: once a round's winner is
    registered, an IDENTICAL later round (same fingerprint) is rejected too."""
    archive = new_run_wide_dedup_archive()
    first = select_official_candidate_v2(
        _base_round(), timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        run_wide_archive=archive,
    )
    assert first['selected'] is not None

    second = select_official_candidate_v2(
        _base_round(), timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        run_wide_archive=archive,
    )
    assert second['selected'] is None
    assert any('run_wide_ast_duplicate' in b for b in second['pool_blockers'])


def test_v2_approved_b_registry_reconciliation_rejects_unregistered_b_feature():
    """Bullet 8 -- only approved B_* features are admitted; a B_-prefixed name
    absent from the registry is rejected by identity, independent of the
    plain B-only variable-scope guard."""
    proposals = _base_round()
    proposals[3]['expression'] = 'B_unregistered_feature > 1'
    registry = build_approved_b_registry(['B_registered_feature'], timeframe=TIMEFRAME)

    result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        approved_b_registry=registry,
    )
    assert result['selected'] is None
    assert any(
        'registry_rejected_variable:B_unregistered_feature' in b for b in result['pool_blockers']
    )

    # the same expression is admitted once the feature is actually registered.
    ok_registry = build_approved_b_registry(['B_unregistered_feature'], timeframe=TIMEFRAME)
    ok_result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
        approved_b_registry=ok_registry,
    )
    assert not any(
        'registry_rejected_variable' in b for b in ok_result['pool_blockers']
    )


def test_v2_fallback_control_origin_excluded_from_ai_performance_accounting():
    """Bullet 7 -- fallback/control-origin candidates are tracked separately
    and never counted as AI-performance-eligible, without corrupting the
    round shape (they are NOT removed from the pool)."""
    proposals = _base_round()
    proposals[0]['origin'] = 'control'
    proposals[1]['source'] = 'diagnostic_deterministic_candidate_fallback'

    result = select_official_candidate_v2(
        proposals, timeframe=TIMEFRAME, methodology_version=METHODOLOGY_VERSION,
    )
    assert set(result['ai_performance_excluded_ids']) == {'repair-a', 'repair-b'}
    # the round shape (2 repair + 2 discovery) is untouched -- selection still runs.
    assert result['selected'] is not None
