import math

import pandas as pd

from cli.research_retention import (
    annotate_candidate_retention,
    apply_retention_penalty,
    estimate_candidate_retention,
    retention_penalty,
    select_retention_aware_candidates,
)


EVALUATION_TOTAL = '\uD3C9\uAC00\uCD1D\uC561'
TURNOVER = '\uD68C\uC804\uC728'
CHANGE_RATE = '\uB4F1\uB77D\uC728'
MISSING_COLUMN = '\uC5C6\uB294\uCEEC\uB7FC'


def _frame():
    return pd.DataFrame([
        {EVALUATION_TOTAL: 1000, TURNOVER: 5.0, CHANGE_RATE: 1.0},
        {EVALUATION_TOTAL: 2000, TURNOVER: 12.0, CHANGE_RATE: 3.0},
        {EVALUATION_TOTAL: 3000, TURNOVER: 20.0, CHANGE_RATE: 5.0},
        {EVALUATION_TOTAL: 4000, TURNOVER: 30.0, CHANGE_RATE: 7.0},
        {EVALUATION_TOTAL: 5000, TURNOVER: 40.0, CHANGE_RATE: 9.0},
    ])


def test_estimate_candidate_retention_counts_removed_and_kept_rows():
    result = estimate_candidate_retention(_frame(), f'{EVALUATION_TOTAL} <= 4000')

    assert result['baseline_trade_count'] == 5
    assert result['estimated_removed_count'] == 4
    assert result['estimated_kept_count'] == 1
    assert result['estimated_retention'] == 0.2
    assert result['evaluation_error'] is None


def test_estimate_candidate_retention_accepts_b_prefixed_csv_columns():
    frame = pd.DataFrame([
        {f'B_{TURNOVER}': 5.0},
        {f'B_{TURNOVER}': 12.0},
        {f'B_{TURNOVER}': 20.0},
    ])

    result = estimate_candidate_retention(frame, f'{TURNOVER} > 10')

    assert result['baseline_trade_count'] == 3
    assert result['estimated_removed_count'] == 2
    assert result['estimated_kept_count'] == 1
    assert result['estimated_retention'] == 1 / 3
    assert result['evaluation_error'] is None


def test_estimate_candidate_retention_marks_eval_errors_as_low_retention():
    result = estimate_candidate_retention(_frame(), f'{MISSING_COLUMN} > 0')

    assert result['baseline_trade_count'] == 5
    assert result['estimated_removed_count'] == 5
    assert result['estimated_kept_count'] == 0
    assert result['estimated_retention'] == 0.0
    assert result['evaluation_error']


def test_estimate_candidate_retention_rejects_numeric_series_masks():
    frame = pd.DataFrame([{'x': 0}, {'x': 0}, {'x': 0}])

    result = estimate_candidate_retention(frame, 'x')

    assert result['baseline_trade_count'] == 3
    assert result['estimated_removed_count'] == 3
    assert result['estimated_kept_count'] == 0
    assert result['estimated_retention'] == 0.0
    assert result['evaluation_error'] == 'expression did not return a boolean row mask'


def test_estimate_candidate_retention_handles_empty_frame():
    result = estimate_candidate_retention(
        pd.DataFrame(columns=[TURNOVER]),
        f'{TURNOVER} > 10',
    )

    assert result['baseline_trade_count'] == 0
    assert result['estimated_removed_count'] == 0
    assert result['estimated_kept_count'] == 0
    assert result['estimated_retention'] == 0.0
    assert result['evaluation_error'] is None


def test_annotate_candidate_retention_marks_pass_fail():
    candidates = [
        {'expression': f'{EVALUATION_TOTAL} <= 2000'},
        {'expression': f'{TURNOVER} > 10'},
        {'expression': f'{MISSING_COLUMN} > 0'},
    ]

    annotated = annotate_candidate_retention(candidates, _frame(), min_retention=0.4)

    assert annotated[0]['retention_estimate']['estimated_retention'] == 0.6
    assert annotated[0]['retention_filter_passed'] is True
    assert annotated[1]['retention_estimate']['estimated_retention'] == 0.2
    assert annotated[1]['retention_filter_passed'] is False
    assert annotated[2]['retention_estimate']['evaluation_error']
    assert annotated[2]['retention_filter_passed'] is False


def test_annotate_candidate_retention_fails_numeric_series_masks():
    frame = pd.DataFrame([{'x': 0}, {'x': 0}, {'x': 0}])

    annotated = annotate_candidate_retention(
        [{'expression': 'x'}],
        frame,
        min_retention=0.4,
    )

    assert annotated[0]['retention_estimate']['estimated_retention'] == 0.0
    assert annotated[0]['retention_estimate']['evaluation_error']
    assert annotated[0]['retention_filter_passed'] is False


def test_retention_penalty_scales_below_threshold():
    assert retention_penalty(0.4, 0.4) == 1.0
    assert retention_penalty(0.2, 0.4) == 0.5
    assert retention_penalty(-1.0, 0.4) == 0.0
    assert retention_penalty(float('nan'), 0.4) == 0.0
    assert retention_penalty(0.2, 0.0) == 1.0
    assert retention_penalty(0.2, float('inf')) == 1.0


def test_apply_retention_penalty_adds_adjusted_score():
    result = apply_retention_penalty(
        {'promotion_score': 100.0, 'trade_count_retention': 0.2},
        min_retention=0.4,
    )

    assert result['retention_penalty'] == 0.5
    assert result['adjusted_score'] == 50.0


def test_apply_retention_penalty_handles_non_finite_scores():
    result = apply_retention_penalty(
        {'promotion_score': math.inf, 'trade_count_retention': 'bad'},
        min_retention=0.4,
    )

    assert result['promotion_score'] == 0.0
    assert result['trade_count_retention'] == 0.0
    assert result['retention_penalty'] == 0.0
    assert result['adjusted_score'] == 0.0


def test_select_retention_aware_candidates_prefers_passed_candidates():
    candidates = [
        {
            'expression': 'A',
            'combined_score': 100,
            'retention_estimate': {'estimated_retention': 0.2},
            'retention_filter_passed': False,
        },
        {
            'expression': 'B',
            'combined_score': 10,
            'retention_estimate': {'estimated_retention': 0.7},
            'retention_filter_passed': True,
        },
        {
            'expression': 'C',
            'combined_score': 20,
            'retention_estimate': {'estimated_retention': 0.6},
            'retention_filter_passed': True,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=2,
        allow_fallback=True,
        min_retention=0.4,
    )

    assert [item['expression'] for item in selected] == ['B', 'C']
    assert summary['status'] == 'ok'
    assert summary['phase'] == 'retention_candidates_selected'
    assert summary['pool_count'] == 3
    assert summary['passed_count'] == 2
    assert summary['fallback_count'] == 0
    assert summary['selected_count'] == 2
    assert summary['min_estimated_retention'] == 0.4
    assert summary['allow_retention_fallback'] is True


def test_select_retention_aware_candidates_uses_fallback_when_needed():
    candidates = [
        {
            'expression': 'A',
            'combined_score': 100,
            'retention_estimate': {'estimated_retention': 0.2},
            'retention_filter_passed': False,
        },
        {
            'expression': 'B',
            'combined_score': 10,
            'retention_estimate': {'estimated_retention': 0.7},
            'retention_filter_passed': True,
        },
        {
            'expression': 'C',
            'combined_score': 20,
            'retention_estimate': {'estimated_retention': 0.3},
            'retention_filter_passed': False,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=3,
        allow_fallback=True,
        min_retention=0.4,
    )

    assert [item['expression'] for item in selected] == ['B', 'C', 'A']
    assert selected[0]['retention_fallback_used'] is False
    assert selected[1]['retention_fallback_used'] is True
    assert selected[2]['retention_fallback_used'] is True
    assert summary['fallback_count'] == 2
    assert summary['selected_count'] == 3


def test_select_retention_aware_candidates_blocks_when_fallback_disabled():
    candidates = [
        {
            'expression': 'A',
            'retention_estimate': {'estimated_retention': 0.2},
            'retention_filter_passed': False,
        },
        {
            'expression': 'B',
            'retention_estimate': {'estimated_retention': 0.7},
            'retention_filter_passed': True,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=2,
        allow_fallback=False,
        min_retention=0.4,
    )

    assert selected == []
    assert summary['status'] == 'error'
    assert summary['phase'] == 'insufficient_retention_candidates'
    assert summary['pool_count'] == 2
    assert summary['passed_count'] == 1
    assert summary['fallback_count'] == 0
    assert summary['selected_count'] == 0
    assert summary['min_estimated_retention'] == 0.4
    assert summary['allow_retention_fallback'] is False


def test_select_retention_aware_candidates_does_not_fallback_eval_errors():
    candidates = [
        {
            'expression': 'A',
            'retention_estimate': {'estimated_retention': 0.7, 'evaluation_error': None},
            'retention_filter_passed': True,
        },
        {
            'expression': 'B',
            'retention_estimate': {'estimated_retention': 0.0, 'evaluation_error': 'missing column'},
            'retention_filter_passed': False,
        },
        {
            'expression': 'C',
            'retention_estimate': {'estimated_retention': 0.3, 'evaluation_error': None},
            'retention_filter_passed': False,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=2,
        allow_fallback=True,
        min_retention=0.4,
    )

    assert [item['expression'] for item in selected] == ['A', 'C']
    assert summary['fallback_count'] == 1


def test_select_retention_aware_candidates_never_selects_eval_errors():
    candidates = [
        {
            'expression': 'A',
            'retention_estimate': {'estimated_retention': 0.7, 'evaluation_error': 'bad mask'},
            'retention_filter_passed': True,
        },
        {
            'expression': 'B',
            'retention_estimate': {'estimated_retention': 0.6, 'evaluation_error': None},
            'retention_filter_passed': True,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=1,
        allow_fallback=True,
        min_retention=0.4,
    )

    assert [item['expression'] for item in selected] == ['B']
    assert summary['passed_count'] == 1


def test_select_retention_aware_candidates_sorts_score_after_retention():
    candidates = [
        {
            'expression': 'A',
            'combined_score': 10,
            'retention_estimate': {'estimated_retention': 0.8},
            'retention_filter_passed': True,
        },
        {
            'expression': 'B',
            'combined_score': 20,
            'retention_estimate': {'estimated_retention': 0.8},
            'retention_filter_passed': True,
        },
        {
            'expression': 'C',
            'score': 30,
            'retention_estimate': {'estimated_retention': 0.2},
            'retention_filter_passed': False,
        },
        {
            'expression': 'D',
            'base_score': 40,
            'retention_estimate': {'estimated_retention': 0.2},
            'retention_filter_passed': False,
        },
    ]

    selected, summary = select_retention_aware_candidates(
        candidates,
        candidate_count=4,
        allow_fallback=True,
        min_retention=0.4,
    )

    assert [item['expression'] for item in selected] == ['B', 'A', 'D', 'C']
    assert summary['fallback_count'] == 2
