import math

import pandas as pd

from cli.research_retention import (
    annotate_candidate_retention,
    apply_retention_penalty,
    estimate_candidate_retention,
    retention_penalty,
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
