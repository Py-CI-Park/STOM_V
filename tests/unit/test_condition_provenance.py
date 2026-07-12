"""Contract tests for CL-R04 sub-slice 9b: threshold provenance + B-only
enforcement toggle.

Covers:
  - cli/analyzer.py: optional `provenance_context` kwarg attaches a
    well-formed `threshold_provenance` dict to produced candidates, and is
    fully backward compatible when omitted.
  - cli/condition_generator.py: `enforce_approved_b_only` (default False)
    gates whether `non_approved_variable` is a hard ingestion blocker, while
    `b_variable_approval` provenance is always recorded on valid candidates.
"""

from __future__ import annotations

import pandas as pd
import pytest

from cli.analyzer import (
    analyze_market_cap_segments,
    analyze_ttest_candidates,
    generate_quantile_candidates,
)
from cli.condition_generator import validate_multi_hypothesis_candidate_pack


def _sample_result_frame():
    rows = []
    for index in range(60):
        if index < 20:
            market_cap = 100_000_000_000
            pct = 0.5 + index * 0.05
            ret = -1.0
        elif index < 40:
            market_cap = 800_000_000_000
            pct = 2.0 + (index - 20) * 0.05
            ret = 0.5
        else:
            market_cap = 2_000_000_000_000
            pct = 3.5 + (index - 40) * 0.05
            ret = 1.5
        rows.append({
            '종목명': f'종목{index}',
            '수익률': ret,
            'B_등락율': pct,
            'B_시가총액': market_cap,
            'B_체결강도': 90 + index,
        })
    return pd.DataFrame(rows)


def _provenance_context(**overrides):
    context = dict(
        fit_role='train',
        period='2026-01',
        dataset_sha='a' * 64,
        fold_id='fold-1',
        source_receipt='receipt-1',
    )
    context.update(overrides)
    return context


# ---------------------------------------------------------------------------
# analyzer.py: provenance_context is additive / opt-in
# ---------------------------------------------------------------------------


def test_generate_quantile_candidates_without_context_has_no_provenance():
    df = _sample_result_frame()
    with_context = generate_quantile_candidates(df, min_samples=10, quantiles=4)
    without_context = generate_quantile_candidates(
        df, min_samples=10, quantiles=4, provenance_context=None,
    )
    assert with_context == without_context
    assert with_context
    for candidate in with_context:
        assert 'threshold_provenance' not in candidate


def test_generate_quantile_candidates_with_context_attaches_provenance():
    df = _sample_result_frame()
    candidates = generate_quantile_candidates(
        df, min_samples=10, quantiles=4, provenance_context=_provenance_context(),
    )
    assert candidates
    for candidate in candidates:
        provenance = candidate['threshold_provenance']
        assert provenance['estimator'] == 'quantile'
        assert provenance['parameters'] == {'quantiles': 4}
        assert provenance['row_count'] == candidate['count']
        assert provenance['dataset_sha'] == 'a' * 64
        assert provenance['fit_role'] == 'train'
        assert provenance['fold_id'] == 'fold-1'
        assert provenance['source_receipt'] == 'receipt-1'
        assert candidate['feature'] in provenance['row_signature']


def test_generate_quantile_candidates_rejects_forbidden_fit_role():
    df = _sample_result_frame()
    for fit_role in ('full_baseline', 'oos', 'validation'):
        with pytest.raises(ValueError):
            generate_quantile_candidates(
                df, min_samples=10, quantiles=4,
                provenance_context=_provenance_context(fit_role=fit_role),
            )


def test_analyze_ttest_candidates_without_context_has_no_provenance():
    df = _sample_result_frame()
    with_context = analyze_ttest_candidates(df, min_samples=10)
    without_context = analyze_ttest_candidates(df, min_samples=10, provenance_context=None)
    assert with_context == without_context
    for candidate in with_context:
        assert 'threshold_provenance' not in candidate


def test_analyze_ttest_candidates_with_context_attaches_provenance():
    df = _sample_result_frame()
    candidates = analyze_ttest_candidates(
        df, min_samples=10, alpha=0.05, provenance_context=_provenance_context(),
    )
    assert candidates
    for candidate in candidates:
        provenance = candidate['threshold_provenance']
        assert provenance['estimator'] == 'median_ttest'
        assert provenance['parameters'] == {'alpha': 0.05}
        assert provenance['row_count'] == candidate['count']
        assert provenance['dataset_sha'] == 'a' * 64


def test_analyze_ttest_candidates_rejects_forbidden_fit_role():
    df = _sample_result_frame()
    with pytest.raises(ValueError):
        analyze_ttest_candidates(
            df, min_samples=10, provenance_context=_provenance_context(fit_role='oos'),
        )


def test_analyze_market_cap_segments_without_context_has_no_provenance():
    df = _sample_result_frame()
    with_context = analyze_market_cap_segments(df, min_samples=10)
    without_context = analyze_market_cap_segments(df, min_samples=10, provenance_context=None)
    assert with_context == without_context
    for candidate in with_context['candidates']:
        assert 'threshold_provenance' not in candidate


def test_analyze_market_cap_segments_with_context_attaches_provenance():
    df = _sample_result_frame()
    result = analyze_market_cap_segments(
        df, min_samples=10, provenance_context=_provenance_context(),
    )
    assert result['candidates']
    for candidate in result['candidates']:
        provenance = candidate['threshold_provenance']
        assert provenance['estimator'] == 'bucket'
        assert 'buckets' in provenance['parameters']
        assert provenance['row_count'] == candidate['count']
        assert provenance['dataset_sha'] == 'a' * 64


def test_analyze_market_cap_segments_rejects_forbidden_fit_role():
    df = _sample_result_frame()
    with pytest.raises(ValueError):
        analyze_market_cap_segments(
            df, min_samples=10,
            provenance_context=_provenance_context(fit_role='full_baseline'),
        )


# ---------------------------------------------------------------------------
# condition_generator.py: enforce_approved_b_only default-off toggle
# ---------------------------------------------------------------------------


def _pack_with_variable_candidates():
    return {
        'schema_version': 1,
        'candidate_pack_id': 'provenance-pack',
        'parents': {
            'buy': {'id': 'buy-parent', 'code': 'if 체결강도 > 90:\n    매수 = True'},
            'sell': {'id': 'sell-parent', 'code': 'if 수익률 < -1:\n    매도 = True'},
        },
        'candidates': [
            {
                'hypothesis_id': 'approved',
                'lane': 'repair',
                'expression': '체결강도 > 100',
                'intended_hypothesis': 'conservative repair',
                'mutation_axis': 'entry_strength',
                'expected_effect': 'reduce weak entries',
                'risk_note': 'may reduce trades',
                'parent_buy_id': 'buy-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'unapproved',
                'lane': 'discovery',
                'expression': '거래대금 > 1000',
                'intended_hypothesis': 'discover liquidity regime',
                'mutation_axis': 'liquidity_regime',
                'expected_effect': 'find new coverage',
                'risk_note': 'may overtrade liquid names',
                'coverage_bucket_keys': ['liquidity-midday'],
                'novelty': {'coverage_regime': 'midday-liquidity'},
                'novelty_rationale': 'new market segment and feature family',
            },
        ],
    }


def _by_hypothesis_id(items, hypothesis_id):
    for item in items:
        candidate = item.get('candidate', item)
        if candidate.get('hypothesis_id') == hypothesis_id:
            return item
    raise AssertionError(f'{hypothesis_id} not found')


def test_default_off_does_not_block_unapproved_variable_but_records_provenance():
    pack = _pack_with_variable_candidates()
    validation = validate_multi_hypothesis_candidate_pack(pack)

    approved = _by_hypothesis_id(validation['valid_candidates'], 'approved')
    unapproved = _by_hypothesis_id(validation['valid_candidates'], 'unapproved')

    assert approved['b_variable_approval']['approved'] is True
    assert approved['b_variable_approval']['unknown_names'] == []

    assert unapproved['b_variable_approval']['approved'] is False
    assert unapproved['b_variable_approval']['unknown_names'] == ['거래대금']
    assert unapproved['b_variable_approval']['timeframe']


def test_enforce_on_blocks_unapproved_variable_candidate():
    pack = _pack_with_variable_candidates()
    validation = validate_multi_hypothesis_candidate_pack(pack, enforce_approved_b_only=True)

    valid_ids = {c['hypothesis_id'] for c in validation['valid_candidates']}
    assert 'unapproved' not in valid_ids
    assert 'approved' in valid_ids

    invalid = _by_hypothesis_id(validation['invalid_candidates'], 'unapproved')
    assert any(r.startswith('non_approved_variable:거래대금') for r in invalid['failure_reasons'])

    approved = _by_hypothesis_id(validation['valid_candidates'], 'approved')
    assert approved['b_variable_approval']['approved'] is True


def test_enforce_toggle_does_not_affect_other_hard_blockers():
    pack = _pack_with_variable_candidates()
    pack['candidates'].append({
        'hypothesis_id': 'leaky',
        'lane': 'discovery',
        'expression': 'S_보유시간 > 10',
        'intended_hypothesis': 'leak probe',
        'mutation_axis': 'leak_probe',
        'expected_effect': 'should never validate',
        'risk_note': 'diagnostic leakage probe',
        'coverage_bucket_keys': ['leak-probe'],
        'novelty': {'feature_family': 'leak-probe'},
        'novelty_rationale': 'leak probe',
    })
    off = validate_multi_hypothesis_candidate_pack(pack)
    on = validate_multi_hypothesis_candidate_pack(pack, enforce_approved_b_only=True)

    off_leaky = _by_hypothesis_id(off['invalid_candidates'], 'leaky')
    on_leaky = _by_hypothesis_id(on['invalid_candidates'], 'leaky')
    assert 'leaky_result_variable:S_보유시간' in off_leaky['failure_reasons']
    assert 'leaky_result_variable:S_보유시간' in on_leaky['failure_reasons']
