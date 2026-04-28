"""Markdown report rendering for Wide v2 optimizer runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _format_markdown_value(value: Any) -> str:
    if value is None:
        return ''
    return str(value).replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def _bullet(key: str, value: Any) -> str:
    return f'- {key}={_format_markdown_value(value)}'


def _round_rows(result: dict[str, Any]) -> list[str]:
    rows = [
        '| round | status | source_candidate | round_best | expression |',
        '| --- | --- | --- | --- | --- |',
    ]
    for item in result.get('rounds') or []:
        best = item.get('round_best_candidate') or {}
        rows.append(
            '| {round_index} | {status} | {source_candidate} | {best_name} | {expression} |'.format(
                round_index=_format_markdown_value(item.get('round_index')),
                status=_format_markdown_value(item.get('status')),
                source_candidate=_format_markdown_value(item.get('source_candidate')),
                best_name=_format_markdown_value(best.get('strategy_name')),
                expression=_format_markdown_value(best.get('expression')),
            )
        )
    return rows


def _round_best_rows(result: dict[str, Any]) -> list[str]:
    rows = [
        '| round | strategy_name | expression |',
        '| --- | --- | --- |',
    ]
    for item in result.get('rounds') or []:
        best = item.get('round_best_candidate') or {}
        rows.append(
            '| {round_index} | {strategy_name} | {expression} |'.format(
                round_index=_format_markdown_value(item.get('round_index')),
                strategy_name=_format_markdown_value(best.get('strategy_name')),
                expression=_format_markdown_value(best.get('expression')),
            )
        )
    return rows


def _leaderboard_rows(result: dict[str, Any]) -> list[str]:
    rows = [
        '| round | candidate | strategy | adjusted_score | promotion_passed | global_best |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for item in result.get('leaderboard') or []:
        rows.append(
            '| {round_index} | {candidate_index} | {strategy_name} | {adjusted_score} | {promotion_passed} | {global_best} |'.format(
                round_index=_format_markdown_value(item.get('round_index')),
                candidate_index=_format_markdown_value(item.get('candidate_index')),
                strategy_name=_format_markdown_value(item.get('strategy_name')),
                adjusted_score=_format_markdown_value(item.get('adjusted_score')),
                promotion_passed=_format_markdown_value(item.get('promotion_passed')),
                global_best=_format_markdown_value(item.get('selected_as_global_best')),
            )
        )
    return rows


def _recovery_lines(result: dict[str, Any]) -> list[str]:
    recovery_family_counts = result.get('recovery_family_counts') or {}
    return [
        '## V5 recovery',
        '',
        _bullet('initial_v4_candidate_count', result.get('initial_v4_candidate_count')),
        _bullet('recovery_attempted', result.get('recovery_attempted')),
        _bullet('recovery_reason', result.get('recovery_reason')),
        _bullet('recovery_family_counts', recovery_family_counts),
        _bullet('final_candidate_pool_count', result.get('final_candidate_pool_count')),
        _bullet('eligible_count', result.get('eligible_count')),
        _bullet('execution_count', result.get('execution_count')),
        _bullet('planned_execution_count', result.get('planned_execution_count')),
        '',
    ]


def _next_seed_lines(result: dict[str, Any]) -> list[str]:
    return [
        '## Next seed selection',
        '',
        _bullet('next_seed_selection_status', result.get('next_seed_selection_status')),
        _bullet('next_seed_strategy_name', result.get('next_seed_strategy_name')),
        _bullet('next_seed_expression', result.get('next_seed_expression')),
        _bullet(
            'rejected_round_best_seed_strategy_name',
            result.get('rejected_round_best_seed_strategy_name'),
        ),
        _bullet(
            'rejected_round_best_seed_expression',
            result.get('rejected_round_best_seed_expression'),
        ),
        _bullet(
            'rejected_round_best_seed_reason',
            result.get('rejected_round_best_seed_reason'),
        ),
        '',
    ]


def _report_write_failure(path: Path, error: OSError) -> dict[str, Any]:
    return {
        'failure_phase': 'optimizer_report_output_write_failure',
        'failure_message': f'optimizer report write failed: {error}',
        'output_path': str(path),
        'exception_type': type(error).__name__,
    }


def render_optimizer_summary_markdown(result: dict[str, Any]) -> str:
    final_best = result.get('final_best_candidate') or {}
    initial_seed = result.get('initial_seed') or {}
    wfo_candidate = result.get('wfo_candidate') or {}
    lines = [
        '# Wide v2 optimizer summary',
        '',
        '## Run configuration',
        '',
        _bullet('run_id', result.get('run_id')),
        _bullet('status', result.get('status')),
        _bullet('iteration_v2_mode', initial_seed.get('iteration_v2_mode')),
        _bullet('iteration_v2_primary_feature', initial_seed.get('iteration_v2_primary_feature')),
        _bullet(
            'iteration_v2_trade_amount_feature',
            initial_seed.get('iteration_v2_trade_amount_feature'),
        ),
        '',
        '## Initial baseline',
        '',
        _bullet('base_buy_strategy', initial_seed.get('base_buy_strategy')),
        _bullet('source_baseline', initial_seed.get('source_baseline')),
        _bullet('seed_candidate', initial_seed.get('seed_candidate')),
        _bullet('seed_expression', initial_seed.get('seed_expression')),
        '',
        '## Round count',
        '',
        _bullet('completed_round_count', result.get('completed_round_count')),
        '',
        '## Round summary',
        '',
        'round-by-round summary',
        '',
        *_round_rows(result),
        '',
        '## Round best candidates',
        '',
        *_round_best_rows(result),
        '',
        '## Global leaderboard top candidates',
        '',
        *_leaderboard_rows(result),
        '',
        *_recovery_lines(result),
        *_next_seed_lines(result),
        '## Stop reason',
        '',
        _bullet('stop_reason', result.get('stop_reason')),
        _bullet('failed_round', result.get('failed_round')),
        _bullet('failure_phase', result.get('failure_phase')),
        _bullet('failure_message', result.get('failure_message')),
        _bullet('requested_candidate_count', result.get('requested_candidate_count')),
        _bullet('selected_candidate_count', result.get('selected_candidate_count')),
        '',
        '## Final best candidate',
        '',
        'final_best_candidate',
        '',
        _bullet('strategy_name', final_best.get('strategy_name')),
        _bullet('expression', final_best.get('expression')),
        _bullet('adjusted_score', final_best.get('adjusted_score')),
        '',
        '## WFO handoff',
        '',
        'WFO was not run inside the optimizer loop.',
        'The final candidate is a WFO candidate, not a live-trading approval.',
        '',
        'WFO handoff candidate',
        '',
        _bullet('strategy_name', wfo_candidate.get('strategy_name')),
        _bullet('expression', wfo_candidate.get('expression')),
        '',
        'next command for WFO validation plan',
        '',
        _bullet('next_command', wfo_candidate.get('next_command')),
        '',
    ]
    return '\n'.join(lines)


def write_optimizer_report(
    result: dict[str, Any],
    report_path: str | None,
    *,
    errors: list[dict[str, Any]] | None = None,
) -> str | None:
    if not report_path:
        return None
    path = Path(report_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_optimizer_summary_markdown(result), encoding='utf-8')
    except OSError as error:
        if errors is not None:
            errors.append(_report_write_failure(path, error))
            return None
        raise
    return str(path)
