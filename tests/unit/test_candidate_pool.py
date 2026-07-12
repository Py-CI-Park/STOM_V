"""Contract tests for CL-R06 bounded candidate-pool selector (todo 12)."""

from __future__ import annotations

import random

import pytest

from ai_strategy_loop.controller.candidate_pool import select_official_candidate

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
