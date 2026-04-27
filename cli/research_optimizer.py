"""Coordinator for multi-round Wide v2 research optimization."""

from __future__ import annotations

from dataclasses import fields
import json
from pathlib import Path
from typing import Any, Callable

from cli.research_iteration_v3 import parse_best_expression_conditions
from cli.research_loop import ResearchLoopConfig, run_research_iteration
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


def _write_json(path: str, payload: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(json_safe_value(payload), ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _seed_from_previous(round_result: dict[str, Any], fallback_candidate: str) -> tuple[str, str] | None:
    best_candidate = round_result.get('best_candidate')
    if not isinstance(best_candidate, dict):
        return None

    strategy_name = str(best_candidate.get('strategy_name') or fallback_candidate or '').strip()
    expression = str(best_candidate.get('expression') or '').strip()
    if not strategy_name or not expression:
        return None
    return strategy_name, expression


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

    phase = result.get('phase')
    if phase == 'invalid_iteration_v2_best_expression':
        return 'invalid_seed_expression'
    if phase in _INSUFFICIENT_CANDIDATE_PHASES:
        return 'insufficient_candidates'
    if phase in _RUNTIME_FAILURE_PHASES:
        return 'runtime_failure'
    return 'research_error'


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

    if not _validate_seed_expression(config, current_expression):
        status = 'error'
        stop_reason = 'invalid_seed_expression'
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

            next_seed = _seed_from_previous(round_result, current_candidate)
            if next_seed is None or not _validate_seed_expression(config, next_seed[1]):
                status = 'error'
                stop_reason = 'invalid_seed_expression'
                break

            current_candidate, current_expression = next_seed

    final_best_candidate = select_global_best_candidate(leaderboard)
    leaderboard = mark_global_best(leaderboard, final_best_candidate)
    final_best_round_candidate = _final_best_round_candidate(final_best_candidate, round_results)
    result = {
        'status': status,
        'run_id': config.run_id,
        'stop_reason': stop_reason,
        'completed_round_count': completed_round_count,
        'rounds': rounds,
        'leaderboard': leaderboard,
        'final_best_candidate': final_best_candidate,
        'final_best_leaderboard_entry': final_best_candidate,
        'final_best_round_candidate': final_best_round_candidate,
        'wfo_candidate': _wfo_candidate(config, final_best_candidate),
        'summary_output_path': summary_output_path,
        'leaderboard_output_path': leaderboard_output_path,
        'report_path': config.report_path,
    }
    result = json_safe_value(result)

    if summary_output_path:
        _write_json(summary_output_path, result)
    if leaderboard_output_path:
        _write_json(leaderboard_output_path, leaderboard)

    return result
