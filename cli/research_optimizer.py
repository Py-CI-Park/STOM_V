"""Coordinator for multi-round Wide v2 research optimization."""

from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
from typing import Any, Callable

from cli.research_iteration_v3 import parse_best_expression_conditions
from cli.research_loop import ResearchLoopConfig, run_research_iteration
from cli.research_optimizer_report import write_optimizer_report
from cli.research_optimizer_state import (
    WideV2OptimizerConfig,
    build_leaderboard_entries,
    compute_improvement,
    default_leaderboard_output_path,
    default_summary_output_path,
    json_safe_value,
    mark_global_best,
    round_runtime_output_path,
    select_global_best_candidate,
)

ResearchRunner = Callable[[ResearchLoopConfig, Any], dict[str, Any]]

_INSUFFICIENT_CANDIDATE_PHASES = {
    'insufficient_expressions',
    'insufficient_retention_candidates',
    'no_expressions',
}

_RUNTIME_FAILURE_PHASES = {
    'analysis',
    'baseline_run',
    'candidate_backtest',
    'candidate_backtest_timeout',
    'candidate_csv_missing',
    'candidate_iteration',
    'candidate_iteration_runtime_failure',
    'comparison',
    'runtime_output_write_failure',
}

_ROUND_FAILURE_METADATA_KEYS = (
    'requested_candidate_count',
    'selected_candidate_count',
    'initial_v4_candidate_count',
    'recovery_attempted',
    'recovery_reason',
    'recovery_family_counts',
    'final_candidate_pool_count',
    'eligible_count',
    'execution_count',
    'planned_execution_count',
)


def _output_write_failure(path: Path, phase: str, error: OSError) -> dict[str, Any]:
    return json_safe_value(
        {
            'failure_phase': phase,
            'failure_message': f'optimizer output write failed: {error}',
            'output_path': str(path),
            'exception_type': type(error).__name__,
        }
    )


def _write_json(path: str, payload: Any, *, failure_phase: str) -> dict[str, Any] | None:
    output = Path(path)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(json_safe_value(payload), ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    except OSError as error:
        return _output_write_failure(output, failure_phase, error)
    return None


def _candidate_seed_tuple(candidate: Any, fallback_candidate: str) -> tuple[str, str] | None:
    if not isinstance(candidate, dict):
        return None

    strategy_name = str(candidate.get('strategy_name') or fallback_candidate or '').strip()
    expression = str(candidate.get('expression') or '').strip()
    if not strategy_name or not expression:
        return None
    return strategy_name, expression


def _seed_candidate_rank_key(candidate: dict[str, Any]) -> tuple[int, int, int]:
    rank = candidate.get('rank')
    try:
        rank_value = int(rank)
    except (TypeError, ValueError):
        rank_value = 999999

    index = candidate.get('index')
    try:
        index_value = int(index)
    except (TypeError, ValueError):
        index_value = 999999

    selected_penalty = 0 if candidate.get('selected_as_best') is True else 1
    return rank_value, selected_penalty, index_value


def _validate_seed_expression(config: WideV2OptimizerConfig, expression: str) -> bool:
    if not config.iteration_v2_mode:
        return True
    if not expression:
        return False
    if config.iteration_v2_mode == 'best_feature_mix':
        return True
    try:
        parse_best_expression_conditions(
            expression,
            primary_feature=config.iteration_v2_primary_feature,
            trade_amount_feature=config.iteration_v2_trade_amount_feature,
        )
    except ValueError:
        return False
    return True


def _seed_from_ranked_candidates(
    config: WideV2OptimizerConfig,
    round_result: dict[str, Any],
    fallback_candidate: str,
) -> dict[str, Any]:
    best_candidate = round_result.get('best_candidate')
    rejected_strategy_name = None
    rejected_expression = None
    rejected_reason = None
    best_seed = _candidate_seed_tuple(best_candidate, fallback_candidate)
    if best_seed is not None:
        if _validate_seed_expression(config, best_seed[1]):
            return json_safe_value(
                {
                    'strategy_name': best_seed[0],
                    'expression': best_seed[1],
                    'selection_status': 'round_best',
                    'rejected_round_best_seed_strategy_name': None,
                    'rejected_round_best_seed_expression': None,
                    'rejected_round_best_seed_reason': None,
                }
            )
        rejected_strategy_name = best_seed[0]
        rejected_expression = best_seed[1]
        rejected_reason = 'invalid_seed_expression'

    candidates = [
        candidate
        for candidate in round_result.get('candidates') or []
        if isinstance(candidate, dict)
    ]
    candidates.sort(key=_seed_candidate_rank_key)
    seen: set[tuple[str, str]] = set()
    if best_seed is not None:
        seen.add(best_seed)

    for candidate in candidates:
        seed = _candidate_seed_tuple(candidate, fallback_candidate)
        if seed is None or seed in seen:
            continue
        seen.add(seed)
        if _validate_seed_expression(config, seed[1]):
            return json_safe_value(
                {
                    'strategy_name': seed[0],
                    'expression': seed[1],
                    'selection_status': 'compatible_fallback',
                    'rejected_round_best_seed_strategy_name': rejected_strategy_name,
                    'rejected_round_best_seed_expression': rejected_expression,
                    'rejected_round_best_seed_reason': rejected_reason,
                }
            )

    return json_safe_value(
        {
            'strategy_name': None,
            'expression': None,
            'selection_status': 'not_found',
            'rejected_round_best_seed_strategy_name': rejected_strategy_name,
            'rejected_round_best_seed_expression': rejected_expression,
            'rejected_round_best_seed_reason': rejected_reason,
        }
    )


def _next_seed_round_metadata(seed_selection: dict[str, Any]) -> dict[str, Any]:
    return {
        'next_seed_selection_status': seed_selection.get('selection_status'),
        'next_seed_strategy_name': seed_selection.get('strategy_name'),
        'next_seed_expression': seed_selection.get('expression'),
        'rejected_round_best_seed_strategy_name': seed_selection.get(
            'rejected_round_best_seed_strategy_name'
        ),
        'rejected_round_best_seed_expression': seed_selection.get(
            'rejected_round_best_seed_expression'
        ),
        'rejected_round_best_seed_reason': seed_selection.get(
            'rejected_round_best_seed_reason'
        ),
    }


def _next_seed_result_metadata(seed_selection: dict[str, Any] | None) -> dict[str, Any]:
    if not seed_selection:
        return {
            'next_seed_selection_status': None,
            'next_seed_strategy_name': None,
            'next_seed_expression': None,
            'rejected_round_best_seed_strategy_name': None,
            'rejected_round_best_seed_expression': None,
            'rejected_round_best_seed_reason': None,
        }
    return _next_seed_round_metadata(seed_selection)


def build_round_research_config(
    config: WideV2OptimizerConfig,
    *,
    round_index: int,
    source_candidate: str,
    seed_expression: str,
) -> ResearchLoopConfig:
    allowed_fields = {field.name for field in fields(ResearchLoopConfig)}
    config_dict = {
        field_name: getattr(config, field_name)
        for field_name in allowed_fields
        if hasattr(config, field_name)
    }
    config_dict.update(
        run_candidate=False,
        run_candidates=True,
        candidate_name_prefix=f'{config.name}__round{round_index:03d}',
        iteration_v2_best_candidate=source_candidate,
        iteration_v2_best_expression=seed_expression,
        runtime_output_path=round_runtime_output_path(config, round_index),
    )
    return ResearchLoopConfig(**config_dict)


def _failure_stop_reason(result: dict[str, Any]) -> str:
    actual_rowset_selection = result.get('actual_rowset_selection') or {}
    if actual_rowset_selection.get('row_set_identity_status') == 'duplicate_only':
        return 'duplicate_rowset_only'
    if actual_rowset_selection.get('status') == 'shortfall':
        return 'insufficient_candidates'
    if (
        actual_rowset_selection.get('status') == 'not_run'
        and actual_rowset_selection.get('reason') == 'insufficient_successful_candidates'
    ):
        return 'insufficient_candidates'

    phase = result.get('phase')
    if phase == 'invalid_iteration_v2_best_expression':
        return 'invalid_seed_expression'
    if phase in _INSUFFICIENT_CANDIDATE_PHASES:
        return 'insufficient_candidates'
    if phase in _RUNTIME_FAILURE_PHASES:
        return 'runtime_failure'
    return 'research_error'


def _actual_rowset_stop_reason(result: dict[str, Any]) -> str | None:
    actual_rowset_selection = result.get('actual_rowset_selection') or {}
    if not isinstance(actual_rowset_selection, dict):
        return None
    if actual_rowset_selection.get('row_set_identity_status') == 'duplicate_only':
        return 'duplicate_rowset_only'
    if actual_rowset_selection.get('status') == 'shortfall':
        return 'insufficient_candidates'
    if (
        actual_rowset_selection.get('status') == 'not_run'
        and actual_rowset_selection.get('reason') == 'insufficient_successful_candidates'
    ):
        return 'insufficient_candidates'
    return None


def _selected_candidate_count(actual_rowset_selection: dict[str, Any]) -> Any:
    if actual_rowset_selection.get('selected_count') is not None:
        return actual_rowset_selection.get('selected_count')
    return actual_rowset_selection.get('successful_candidate_count')


def _failure_metadata(
    *,
    failed_round: int | None = None,
    failure_phase: Any = None,
    failure_message: Any = None,
    actual_rowset_selection: dict[str, Any] | None = None,
    round_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actual_selection = actual_rowset_selection or {}
    round_payload = round_result or {}
    metadata = {
        'failed_round': failed_round,
        'failure_phase': failure_phase,
        'failure_message': failure_message,
        'requested_candidate_count': (
            actual_selection.get('requested_count')
            if actual_selection.get('requested_count') is not None
            else round_payload.get('requested_candidate_count')
        ),
        'selected_candidate_count': (
            _selected_candidate_count(actual_selection)
            if actual_selection
            else round_payload.get('selected_candidate_count')
        ),
    }
    for key in _ROUND_FAILURE_METADATA_KEYS:
        if key in {'requested_candidate_count', 'selected_candidate_count'}:
            continue
        if key in round_payload:
            metadata[key] = round_payload.get(key)
    return json_safe_value(metadata)


def _actual_rowset_failure_message(stop_reason: str, actual_rowset_selection: dict[str, Any]) -> str:
    if stop_reason == 'duplicate_rowset_only':
        return 'actual row-set selection produced duplicate-only candidates'
    reason = actual_rowset_selection.get('reason')
    if reason:
        return f'actual row-set selection did not produce enough candidates: {reason}'
    return 'actual row-set selection did not produce enough candidates'


def _apply_output_write_failures(
    result: dict[str, Any],
    output_write_failures: list[dict[str, Any]],
) -> None:
    result['output_write_failures'] = json_safe_value(output_write_failures)
    if not output_write_failures:
        return

    first_failure = output_write_failures[0]
    if result.get('status') == 'ok':
        result['status'] = 'error'
        result['stop_reason'] = 'runtime_failure'
        result['failure_phase'] = first_failure.get('failure_phase')
        result['failure_message'] = first_failure.get('failure_message')
    else:
        if not result.get('failure_phase'):
            result['failure_phase'] = first_failure.get('failure_phase')
        if not result.get('failure_message'):
            result['failure_message'] = first_failure.get('failure_message')


def _final_best_round_candidate(
    final_best_entry: dict[str, Any] | None,
    round_results: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    if final_best_entry is None:
        return None

    round_index = int(final_best_entry.get('round_index') or 0)
    round_result = round_results.get(round_index) or {}
    candidates = round_result.get('candidates') or []
    target_index = int(final_best_entry.get('candidate_index') or 0)
    target_name = final_best_entry.get('strategy_name')

    for candidate in candidates:
        if (
            int(candidate.get('index') or 0) == target_index
            and candidate.get('strategy_name') == target_name
        ):
            return json_safe_value(dict(candidate))

    best_candidate = round_result.get('best_candidate')
    if isinstance(best_candidate, dict) and best_candidate.get('strategy_name') == target_name:
        return json_safe_value(dict(best_candidate))
    return None


def _wfo_candidate(
    config: WideV2OptimizerConfig,
    final_best_entry: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if final_best_entry is None:
        return None

    strategy_name = final_best_entry.get('strategy_name')
    expression = final_best_entry.get('expression')
    return json_safe_value(
        {
            'strategy_name': strategy_name,
            'expression': expression,
            'source_round': final_best_entry.get('round_index'),
            'source_candidate': final_best_entry.get('source_candidate'),
            'reason_selected': 'global_best_leaderboard_entry',
            'next_command': (
                f'$writing-plans {config.name} optimizer winner '
                f'{strategy_name} WFO handoff plan 작성'
            ),
        }
    )


def _initial_seed_metadata(config: WideV2OptimizerConfig) -> dict[str, Any]:
    effective_seed_candidate = config.seed_candidate or config.base_buy_strategy
    return json_safe_value(
        {
            'base_buy_strategy': config.base_buy_strategy,
            'source_baseline': config.base_buy_strategy,
            'seed_candidate': effective_seed_candidate,
            'seed_expression': config.seed_expression,
            'iteration_v2_mode': config.iteration_v2_mode,
            'iteration_v2_primary_feature': config.iteration_v2_primary_feature,
            'iteration_v2_trade_amount_feature': config.iteration_v2_trade_amount_feature,
        }
    )


def run_wide_v2_optimizer(
    config: WideV2OptimizerConfig,
    controller,
    *,
    research_runner: ResearchRunner = run_research_iteration,
) -> dict[str, Any]:
    rounds: list[dict[str, Any]] = []
    leaderboard: list[dict[str, Any]] = []
    round_results: dict[int, dict[str, Any]] = {}
    summary_output_path = default_summary_output_path(config)
    leaderboard_output_path = default_leaderboard_output_path(config)

    current_candidate = config.seed_candidate or config.base_buy_strategy
    current_expression = config.seed_expression
    completed_round_count = 0
    no_improvement_streak = 0
    stop_reason = 'max_rounds_reached'
    status = 'ok'
    failure_metadata = _failure_metadata()
    last_next_seed_selection: dict[str, Any] | None = None

    if not _validate_seed_expression(config, current_expression):
        status = 'error'
        stop_reason = 'invalid_seed_expression'
        failure_metadata = _failure_metadata(
            failed_round=1,
            failure_phase='invalid_seed_expression',
            failure_message='initial seed expression is invalid',
        )
    else:
        for round_index in range(1, max(int(config.max_rounds), 0) + 1):
            round_config = build_round_research_config(
                config,
                round_index=round_index,
                source_candidate=current_candidate,
                seed_expression=current_expression,
            )
            round_result = research_runner(round_config, controller)
            round_state = {
                'round_index': round_index,
                'status': round_result.get('status'),
                'phase': round_result.get('phase'),
                'candidate_name_prefix': round_config.candidate_name_prefix,
                'source_candidate': current_candidate,
                'seed_expression': current_expression,
                'runtime_json_path': round_config.runtime_output_path,
                'round_best_candidate': round_result.get('best_candidate'),
            }

            if round_result.get('status') != 'ok':
                round_state['failure_message'] = round_result.get('message')
                rounds.append(json_safe_value(round_state))
                status = 'error'
                stop_reason = _failure_stop_reason(round_result)
                failure_metadata = _failure_metadata(
                    failed_round=round_index,
                    failure_phase=round_result.get('phase'),
                    failure_message=round_result.get('message'),
                    actual_rowset_selection=round_result.get('actual_rowset_selection'),
                    round_result=round_result,
                )
                break

            rowset_stop_reason = _actual_rowset_stop_reason(round_result)
            if rowset_stop_reason is not None:
                actual_rowset_selection = round_result.get('actual_rowset_selection') or {}
                round_state['failure_message'] = _actual_rowset_failure_message(
                    rowset_stop_reason,
                    actual_rowset_selection,
                )
                rounds.append(json_safe_value(round_state))
                status = 'error'
                stop_reason = rowset_stop_reason
                failure_metadata = _failure_metadata(
                    failed_round=round_index,
                    failure_phase='actual_rowset_selection',
                    failure_message=round_state['failure_message'],
                    actual_rowset_selection=actual_rowset_selection,
                    round_result=round_result,
                )
                break

            round_results[round_index] = round_result
            rounds.append(json_safe_value(round_state))
            completed_round_count = round_index

            prior_global_best = select_global_best_candidate(leaderboard)
            leaderboard.extend(
                build_leaderboard_entries(
                    run_id=config.run_id,
                    round_index=round_index,
                    round_result=round_result,
                    source_baseline=config.base_buy_strategy,
                    source_candidate=current_candidate,
                    runtime_json_path=round_config.runtime_output_path,
                )
            )
            current_global_best = select_global_best_candidate(leaderboard)
            leaderboard = mark_global_best(leaderboard, current_global_best)

            if prior_global_best is not None:
                improvement = compute_improvement(current_global_best, prior_global_best)
                if improvement is None or improvement < config.min_improvement:
                    no_improvement_streak += 1
                else:
                    no_improvement_streak = 0

            if round_index >= config.max_rounds:
                stop_reason = 'max_rounds_reached'
                break

            if prior_global_best is not None and no_improvement_streak >= config.stop_after_no_improvement:
                stop_reason = 'no_improvement_streak_reached'
                break

            seed_selection = _seed_from_ranked_candidates(
                config,
                round_result,
                current_candidate,
            )
            round_state.update(_next_seed_round_metadata(seed_selection))
            if rounds:
                rounds[-1] = json_safe_value(round_state)
            last_next_seed_selection = seed_selection
            if seed_selection.get('selection_status') == 'not_found':
                status = 'error'
                stop_reason = 'invalid_seed_expression'
                failure_metadata = {
                    **_failure_metadata(
                        failed_round=round_index + 1,
                        failure_phase='invalid_seed_expression',
                        failure_message='next seed expression is invalid',
                    ),
                    **_next_seed_round_metadata(seed_selection),
                }
                break

            current_candidate = str(seed_selection.get('strategy_name') or '')
            current_expression = str(seed_selection.get('expression') or '')

    final_best_candidate = select_global_best_candidate(leaderboard)
    leaderboard = mark_global_best(leaderboard, final_best_candidate)
    final_best_round_candidate = _final_best_round_candidate(final_best_candidate, round_results)
    result = {
        'status': status,
        'run_id': config.run_id,
        'stop_reason': stop_reason,
        **failure_metadata,
        **_next_seed_result_metadata(last_next_seed_selection),
        'completed_round_count': completed_round_count,
        'initial_seed': _initial_seed_metadata(config),
        'rounds': rounds,
        'leaderboard': leaderboard,
        'final_best_candidate': final_best_candidate,
        'final_best_leaderboard_entry': final_best_candidate,
        'final_best_round_candidate': final_best_round_candidate,
        'wfo_candidate': _wfo_candidate(config, final_best_candidate),
        'summary_output_path': summary_output_path,
        'leaderboard_output_path': leaderboard_output_path,
        'report_path': config.report_path,
        'output_write_failures': [],
    }
    result = json_safe_value(result)

    output_write_failures: list[dict[str, Any]] = []
    if leaderboard_output_path:
        leaderboard_error = _write_json(
            leaderboard_output_path,
            leaderboard,
            failure_phase='optimizer_leaderboard_output_write_failure',
        )
        if leaderboard_error is not None:
            output_write_failures.append(leaderboard_error)
            _apply_output_write_failures(result, output_write_failures)

    report_errors: list[dict[str, Any]] = []
    report_path = write_optimizer_report(result, config.report_path, errors=report_errors)
    result['report_path'] = report_path
    if report_errors:
        output_write_failures.extend(report_errors)
        _apply_output_write_failures(result, output_write_failures)

    if summary_output_path:
        summary_error = _write_json(
            summary_output_path,
            result,
            failure_phase='optimizer_summary_output_write_failure',
        )
        if summary_error is not None:
            output_write_failures.append(summary_error)
            _apply_output_write_failures(result, output_write_failures)

    return result
