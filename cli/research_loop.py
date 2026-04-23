"""One-shot research loop for improving an existing buy strategy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path

from cli.analyzer import analyze_result_csv
from cli.condition_generator import generate_condition_expressions_from_analysis
from cli.paths import DB_STRATEGY
from cli.research_iteration_v2 import build_v2_candidate_pool, candidate_from_expression
from cli.research_iteration_v3 import build_v3_candidate_pool, parse_best_expression_conditions
from cli.research_compare import (
    INSTRUMENT_COLUMNS,
    OPTIONAL_KEY_COLUMNS,
    REQUIRED_KEY_COLUMNS,
    compare_trade_sets,
)
from cli.research_metrics import NUMERIC_COLUMNS, normalize_trade_frame
from cli.research_promotion import evaluate_research_candidate
from cli.research_retention import (
    annotate_candidate_retention,
    apply_retention_penalty,
    select_retention_aware_candidates,
)
from cli.research_report import build_research_report
from cli.strategy_generator import delete_strategy_from_db, generate_buy_filter_strategy, save_strategy_to_db
from cli.strategy_loader import load_strategy_from_db


_TRADE_COLUMN_ALIASES = {
    '종목코드': INSTRUMENT_COLUMNS[0],
    '종목명': INSTRUMENT_COLUMNS[1],
    '매수시간': REQUIRED_KEY_COLUMNS[0],
    '매도시간': NUMERIC_COLUMNS[1],
    '매수가': OPTIONAL_KEY_COLUMNS[0],
    '매도가': NUMERIC_COLUMNS[3],
    '수익률': NUMERIC_COLUMNS[5],
    '수익금': NUMERIC_COLUMNS[6],
}

_CLEANUP_SAFE_FAILURE_PHASES = {
    'candidate_backtest',
    'candidate_backtest_timeout',
    'candidate_csv_missing',
    'comparison',
}
_RETENTION_METADATA_KEYS = (
    'retention_estimate',
    'retention_filter_passed',
    'retention_fallback_used',
)

@dataclass
class ResearchLoopConfig:
    name: str = 'AutoResearch'
    baseline_csv: str | None = None
    score_reference_csv: str | None = None
    base_buy_strategy: str = ''
    sell_strategy: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: object = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    top_n: int = 5
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    run_candidate: bool = True
    run_candidates: bool = False
    candidate_count: int = 5
    candidate_name_prefix: str | None = None
    cleanup_best_candidate: bool = False
    keep_loser_candidates: bool = False
    candidate_start_date: int | None = None
    candidate_end_date: int | None = None
    candidate_timeout: int | None = None
    candidate_plan_only: bool = False
    keep_failed_candidate: bool = False
    min_estimated_retention: float = 0.40
    allow_retention_fallback: bool = True
    use_retention_penalty: bool = True
    candidate_pool_multiplier: int = 3
    iteration_v2_mode: str = ''
    iteration_v2_best_candidate: str = ''
    iteration_v2_best_expression: str = ''
    iteration_v2_primary_feature: str = 'B_시가총액'
    iteration_v2_secondary_features: str = ''
    iteration_v2_include_secondary_only: bool = True
    iteration_v2_max_secondary_only: int = 1
    iteration_v2_duplicate_retention_tolerance: float = 0.02


def _base_config_dict(config: ResearchLoopConfig) -> dict:
    """Build the backtest config for the existing baseline strategy."""
    return {
        'buy_strategy': config.base_buy_strategy,
        'sell_strategy': config.sell_strategy,
        'start_date': config.start_date,
        'end_date': config.end_date,
        'is_tick': config.is_tick,
        'betting': config.betting,
        'avg_time': config.avg_time,
        'start_time': config.start_time,
        'end_time': config.end_time,
        'engine_count': config.engine_count,
    }


def _candidate_config_dict(config: ResearchLoopConfig, strategy_name: str | None = None) -> dict:
    candidate = _base_config_dict(config)
    candidate['buy_strategy'] = strategy_name or config.name
    candidate['start_date'] = _candidate_start_date(config)
    candidate['end_date'] = _candidate_end_date(config)
    if config.candidate_timeout is not None:
        candidate['timeout'] = config.candidate_timeout
    return candidate


def _candidate_start_date(config: ResearchLoopConfig) -> int:
    return config.start_date if config.candidate_start_date is None else config.candidate_start_date


def _candidate_end_date(config: ResearchLoopConfig) -> int:
    return config.end_date if config.candidate_end_date is None else config.candidate_end_date


def _candidate_name_prefix(config: ResearchLoopConfig) -> str:
    return config.candidate_name_prefix or config.name


def _candidate_pool_size(config: ResearchLoopConfig) -> int:
    return max(config.top_n, config.candidate_count * config.candidate_pool_multiplier)


def _split_csv_values(value: str | None) -> list[str]:
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def _effective_top_n(config: ResearchLoopConfig) -> int:
    return _candidate_pool_size(config) if config.run_candidates else config.top_n


def _build_iteration_plan(config: ResearchLoopConfig) -> dict:
    return {
        'candidate_count': config.candidate_count,
        'candidate_name_prefix': _candidate_name_prefix(config),
        'score_reference_csv': config.score_reference_csv,
        'effective_top_n': _effective_top_n(config),
        'candidate_pool_multiplier': config.candidate_pool_multiplier,
        'candidate_pool_size': _candidate_pool_size(config),
        'min_estimated_retention': config.min_estimated_retention,
        'allow_retention_fallback': config.allow_retention_fallback,
        'use_retention_penalty': config.use_retention_penalty,
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'cleanup_best_candidate': config.cleanup_best_candidate,
        'keep_loser_candidates': config.keep_loser_candidates,
        'keep_failed_candidate': config.keep_failed_candidate,
        'iteration_v2_mode': config.iteration_v2_mode,
        'iteration_v2_best_candidate': config.iteration_v2_best_candidate,
        'iteration_v2_best_expression': config.iteration_v2_best_expression,
        'iteration_v2_primary_feature': config.iteration_v2_primary_feature,
        'iteration_v2_secondary_features': _split_csv_values(config.iteration_v2_secondary_features),
        'iteration_v2_include_secondary_only': config.iteration_v2_include_secondary_only,
        'iteration_v2_max_secondary_only': config.iteration_v2_max_secondary_only,
        'iteration_v2_duplicate_retention_tolerance': config.iteration_v2_duplicate_retention_tolerance,
    }


def _iteration_generation_metadata(iteration_v2: dict | None, iteration_v3: dict | None) -> dict:
    metadata = {}
    if iteration_v2:
        metadata['iteration_v2'] = iteration_v2
    if iteration_v3:
        metadata['iteration_v3'] = iteration_v3
    return metadata


def _build_candidate_specs(config: ResearchLoopConfig, expression_result: dict) -> list[dict]:
    specs = []
    expressions = expression_result.get('expressions') or []
    selected = expression_result.get('selected_candidates') or []
    for index, expression in enumerate(expressions[:config.candidate_count], start=1):
        source_candidate = selected[index - 1] if index - 1 < len(selected) else None
        spec = {
            'index': index,
            'strategy_name': f'{_candidate_name_prefix(config)}__cand{index:03d}',
            'expression': expression,
            'expressions': [expression],
            'source_candidate': source_candidate,
        }
        if source_candidate:
            for key in _RETENTION_METADATA_KEYS:
                if key in source_candidate:
                    spec[key] = source_candidate[key]
        specs.append(spec)
    return specs


def _retention_candidate_diagnostics(
    candidates: list[dict],
    selected_candidates: list[dict] | None = None,
) -> list[dict]:
    selected_candidates = selected_candidates or []
    selected_by_index = {
        candidate.get('original_index'): candidate
        for candidate in selected_candidates
        if candidate.get('original_index') is not None
    }
    selected_by_expression = {
        candidate.get('expression'): candidate
        for candidate in selected_candidates
        if candidate.get('expression') is not None
    }
    diagnostics = []
    for candidate in candidates:
        selected = selected_by_index.get(candidate.get('original_index'))
        if selected is None:
            selected = selected_by_expression.get(candidate.get('expression'))
        item = {'expression': candidate.get('expression')}
        for key in (
            'original_index',
            'retention_estimate',
            'retention_filter_passed',
            'retention_fallback_used',
            'source',
            'feature',
        ):
            if key in candidate:
                item[key] = candidate[key]
        if selected is not None and 'retention_fallback_used' in selected:
            item['retention_fallback_used'] = selected['retention_fallback_used']
        diagnostics.append(item)
    return diagnostics


def _build_candidate_plan(
    config: ResearchLoopConfig,
    candidate: dict,
    strategy_name: str | None = None,
    will_save_override: bool | None = None,
) -> dict:
    """Build a stable plan describing candidate execution before side effects."""
    will_save = (
        will_save_override
        if will_save_override is not None
        else bool(config.run_candidate and not config.candidate_plan_only)
    )
    return {
        'strategy_name': strategy_name or config.name,
        'base_buy_strategy': config.base_buy_strategy,
        'sell_strategy': config.sell_strategy,
        'expression': candidate.get('expression'),
        'expressions': candidate.get('expressions', []),
        'candidate_start_date': _candidate_start_date(config),
        'candidate_end_date': _candidate_end_date(config),
        'candidate_timeout': config.candidate_timeout,
        'will_save_strategy': will_save,
        'will_run_backtest': will_save,
        'keep_failed_candidate': config.keep_failed_candidate,
    }


def _candidate_failure_phase(candidate_result: dict) -> str:
    message = str(candidate_result.get('message') or '')
    if '시간 초과' in message or 'timeout' in message.lower():
        return 'candidate_backtest_timeout'
    return 'candidate_backtest'


def _cleanup_candidate_strategy(
    config: ResearchLoopConfig,
    reason: str,
    strategy_name: str | None = None,
) -> dict:
    """Delete failed candidate strategy unless the user requested preservation."""
    candidate_name = strategy_name or config.name
    if config.keep_failed_candidate:
        return {
            'attempted': False,
            'reason': 'keep_failed_candidate',
            'strategy_name': candidate_name,
        }
    try:
        result = delete_strategy_from_db(DB_STRATEGY, candidate_name, 'buy')
    except Exception as e:
        return {
            'attempted': True,
            'reason': reason,
            'strategy_name': candidate_name,
            'status': 'error',
            'message': str(e),
        }
    return {
        'attempted': True,
        'reason': reason,
        'strategy_name': candidate_name,
        'status': result.get('status'),
        'message': result.get('message'),
        'action': result.get('action'),
    }


def _error(phase: str, message: str, **extra) -> dict:
    return {'status': 'error', 'phase': phase, 'message': message, **extra}


def validate_research_iteration_config(config: ResearchLoopConfig) -> dict:
    if config.candidate_plan_only and config.run_candidates:
        return _error(
            'candidate_plan_only_iteration_conflict',
            'candidate_plan_only cannot be used with run_candidates',
        )
    if config.run_candidates and config.candidate_count < 1:
        return _error(
            'invalid_candidate_count',
            'candidate_count must be greater than or equal to 1',
        )
    if config.run_candidates and not 0 <= config.min_estimated_retention <= 1:
        return _error(
            'invalid_min_estimated_retention',
            'min_estimated_retention must be between 0 and 1',
        )
    if config.run_candidates and config.candidate_pool_multiplier < 1:
        return _error(
            'invalid_candidate_pool_multiplier',
            'candidate_pool_multiplier must be greater than or equal to 1',
        )
    allowed_iteration_modes = {'best_feature_mix', 'best_feature_mix_v3'}
    if config.run_candidates and config.iteration_v2_mode and config.iteration_v2_mode not in allowed_iteration_modes:
        return _error(
            'invalid_iteration_v2_mode',
            'iteration_v2_mode must be empty, best_feature_mix, or best_feature_mix_v3',
        )
    if config.run_candidates and config.iteration_v2_max_secondary_only < 0:
        return _error(
            'invalid_iteration_v2_max_secondary_only',
            'iteration_v2_max_secondary_only must be greater than or equal to 0',
        )
    if config.run_candidates and config.iteration_v2_mode and not config.iteration_v2_best_expression:
        return _error(
            'missing_iteration_v2_best_expression',
            'iteration_v2_best_expression is required when iteration_v2_mode is set',
        )
    if config.run_candidates and config.iteration_v2_mode == 'best_feature_mix_v3':
        trade_amount_feature = (
            (build_v3_candidate_pool.__kwdefaults__ or {}).get('trade_amount_feature')
            or 'B_당일거래대금'
        )
        try:
            parse_best_expression_conditions(
                config.iteration_v2_best_expression,
                primary_feature=config.iteration_v2_primary_feature,
                trade_amount_feature=trade_amount_feature,
            )
        except ValueError:
            return _error(
                'invalid_iteration_v2_best_expression',
                'best_feature_mix_v3 iteration_v2_best_expression must contain exactly two parseable conditions',
            )
    if config.run_candidate and config.run_candidates:
        return _error(
            'run_candidate_and_run_candidates_conflict',
            'run_candidate and run_candidates cannot both be true',
        )
    return {'status': 'ok'}


def _csv_path_from_run(result: dict) -> str | None:
    csv_path = result.get('csv_path') or result.get('output_csv')
    if csv_path:
        return csv_path
    metrics = result.get('metrics') or {}
    return metrics.get('csv_path')


def _trade_frame_for_compare(csv_path: str):
    frame = normalize_trade_frame(csv_path)
    aliases = {
        source: target
        for source, target in _TRADE_COLUMN_ALIASES.items()
        if source in frame.columns and target not in frame.columns
    }
    if aliases:
        frame = frame.rename(columns=aliases)
        frame = normalize_trade_frame(frame)
    return frame


def _score_reference_csv(config: ResearchLoopConfig) -> str | None:
    return config.score_reference_csv or None


def _build_reference_evaluation(config: ResearchLoopConfig, candidate_csv: str) -> dict:
    reference_csv = _score_reference_csv(config)
    if not reference_csv:
        return {}
    if not Path(reference_csv).exists():
        return {
            'score_reference_csv': reference_csv,
            'reference_error': {
                'phase': 'score_reference_csv_missing',
                'message': f'score_reference_csv does not exist: {reference_csv}',
                'score_reference_csv': reference_csv,
            },
        }
    reference_comparison = compare_trade_sets(
        _trade_frame_for_compare(reference_csv),
        _trade_frame_for_compare(candidate_csv),
    )
    reference_promotion = evaluate_research_candidate(reference_comparison)
    return {
        'score_reference_csv': reference_csv,
        'reference_comparison': reference_comparison,
        'reference_promotion': reference_promotion,
    }


def _build_result(config: ResearchLoopConfig, result: dict) -> dict:
    result['report'] = build_research_report(result, strategy_name=config.name)
    return result


def _first_expression(expression_result: dict) -> str | None:
    expressions = expression_result.get('expressions') or []
    return expressions[0] if expressions else None


def _is_strategy_not_found(result: dict) -> bool:
    message = str(result.get('message') or '').lower()
    not_found_markers = (
        'not found',
        'strategy not found',
        '전략 없음',
        '전략이 없습니다',
        '전략이 db에 없습니다',
        '전략을 찾을 수 없습니다',
        '테이블에 없습니다',
    )
    return any(marker in message for marker in not_found_markers)


def _format_candidate_reason(candidate: object) -> str:
    if isinstance(candidate, dict):
        parts = []
        for key in ('source', 'label', 'feature', 'count'):
            value = candidate.get(key)
            if value not in (None, ''):
                parts.append(f'{key}={value}')
        if parts:
            return ' | '.join(parts)
    if candidate not in (None, ''):
        return str(candidate)
    return ''


def _candidate_reason(expression_result: dict) -> str:
    selected_candidates = expression_result.get('selected_candidates') or []
    if selected_candidates:
        reason = _format_candidate_reason(selected_candidates[0])
        if reason:
            return reason
    reason = _format_candidate_reason(expression_result.get('analysis_candidate'))
    if reason:
        return reason
    expression = _first_expression(expression_result)
    if expression:
        return f'analysis_candidate={expression}'
    return 'analysis_candidate=unavailable'


def _candidate_from_spec(spec: dict) -> dict:
    source_candidate = spec.get('source_candidate')
    return {
        'expression': spec.get('expression'),
        'expressions': spec.get('expressions') or [],
        'reason': _format_candidate_reason(source_candidate)
        or f"analysis_candidate={spec.get('expression')}",
        'candidate_count': 1,
        'selected_candidates': [source_candidate] if source_candidate else [],
    }


def _candidate_item_error(spec: dict, phase: str, message: str, **extra) -> dict:
    item = {
        'index': spec.get('index'),
        'strategy_name': spec.get('strategy_name'),
        'expression': spec.get('expression'),
        'status': 'error',
        'phase': phase,
        'message': message,
        'rank': None,
        'rank_score': None,
        'selected_as_best': False,
    }
    for key in _RETENTION_METADATA_KEYS:
        if key in spec:
            item[key] = spec[key]
    item.update(extra)
    return item


def _prepare_candidate_strategy(
    config: ResearchLoopConfig,
    expressions: list[str],
    strategy_name: str | None = None,
) -> dict:
    candidate_name = strategy_name or config.name
    if not config.base_buy_strategy:
        return _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
        )
    if candidate_name == config.base_buy_strategy:
        return _error(
            'candidate_name_conflict',
            'name must differ from base_buy_strategy to preserve the base strategy',
        )

    base_result = load_strategy_from_db(DB_STRATEGY, config.base_buy_strategy, 'buy')
    if base_result.get('status') != 'ok':
        return _error(
            'base_strategy_load',
            base_result.get('message', 'failed to load base_buy_strategy'),
            base_strategy_result=base_result,
        )

    candidate_name_result = load_strategy_from_db(DB_STRATEGY, candidate_name, 'buy')
    if candidate_name_result.get('status') == 'ok':
        return _error(
            'candidate_name_conflict',
            f"candidate buy strategy '{candidate_name}' already exists",
            candidate_strategy_result=candidate_name_result,
        )
    if not _is_strategy_not_found(candidate_name_result):
        return _error(
            'candidate_name_lookup',
            candidate_name_result.get('message', 'failed to check candidate buy strategy name'),
            candidate_strategy_result=candidate_name_result,
        )

    strategy_result = generate_buy_filter_strategy(
        candidate_name,
        base_result.get('code', ''),
        expressions,
    )
    if strategy_result.get('status') != 'ok':
        return _error(
            'filter_generation',
            strategy_result.get('message', 'failed to generate filtered buy strategy'),
            strategy_result=strategy_result,
        )

    save_result = save_strategy_to_db(
        DB_STRATEGY,
        candidate_name,
        strategy_result.get('code', ''),
        'buy',
    )
    if save_result.get('status') != 'ok':
        return _error(
            'candidate_strategy_save',
            save_result.get('message', 'failed to save candidate buy strategy'),
            strategy_result=save_result,
        )

    return {
        'status': 'ok',
        'base_strategy_result': base_result,
        'generated_strategy': strategy_result,
        'strategy_result': save_result,
    }


def _execute_candidate_spec(
    config: ResearchLoopConfig,
    spec: dict,
    controller,
    baseline_csv: str,
) -> dict:
    strategy_name = spec['strategy_name']
    candidate = _candidate_from_spec(spec)
    candidate_plan = _build_candidate_plan(
        config,
        candidate,
        strategy_name=strategy_name,
        will_save_override=True,
    )

    strategy_flow = _prepare_candidate_strategy(
        config,
        spec['expressions'],
        strategy_name=strategy_name,
    )
    if strategy_flow.get('status') != 'ok':
        return _candidate_item_error(
            spec,
            strategy_flow.get('phase', 'candidate_strategy'),
            strategy_flow.get('message', 'failed to prepare candidate strategy'),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=_candidate_not_created_cleanup(strategy_name),
            strategy_flow=strategy_flow,
        )
    candidate['strategy_result'] = strategy_flow['strategy_result']
    candidate['generated_strategy'] = strategy_flow['generated_strategy']

    candidate_result = controller.run(_candidate_config_dict(config, strategy_name=strategy_name))
    if candidate_result.get('status') not in ('ok', 'success'):
        phase = _candidate_failure_phase(candidate_result)
        cleanup = _cleanup_candidate_strategy(config, phase, strategy_name=strategy_name)
        return _candidate_item_error(
            spec,
            phase,
            candidate_result.get('message', 'candidate run failed'),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_result=candidate_result,
        )

    candidate_csv = _csv_path_from_run(candidate_result)
    if not candidate_csv:
        cleanup = _cleanup_candidate_strategy(
            config,
            'candidate_csv_missing',
            strategy_name=strategy_name,
        )
        return _candidate_item_error(
            spec,
            'candidate_csv_missing',
            'candidate run did not return csv_path',
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_result=candidate_result,
        )
    if not Path(candidate_csv).exists():
        cleanup = _cleanup_candidate_strategy(
            config,
            'candidate_csv_missing',
            strategy_name=strategy_name,
        )
        return _candidate_item_error(
            spec,
            'candidate_csv_missing',
            f'candidate csv_path does not exist: {candidate_csv}',
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_csv=candidate_csv,
            candidate_result=candidate_result,
        )

    try:
        comparison = compare_trade_sets(
            _trade_frame_for_compare(baseline_csv),
            _trade_frame_for_compare(candidate_csv),
        )
        promotion = evaluate_research_candidate(comparison)
        reference_evaluation = _build_reference_evaluation(config, candidate_csv)
    except Exception as e:
        cleanup = _cleanup_candidate_strategy(config, 'comparison', strategy_name=strategy_name)
        return _candidate_item_error(
            spec,
            'comparison',
            str(e),
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            candidate_csv=candidate_csv,
            candidate_result=candidate_result,
        )

    return {
        'index': spec.get('index'),
        'strategy_name': strategy_name,
        'expression': spec.get('expression'),
        **{
            key: spec[key]
            for key in _RETENTION_METADATA_KEYS
            if key in spec
        },
        'status': 'ok',
        'phase': 'candidate_evaluated',
        'candidate': candidate,
        'candidate_plan': candidate_plan,
        'candidate_csv': candidate_csv,
        'candidate_result': candidate_result,
        'comparison': comparison,
        'promotion': promotion,
        **reference_evaluation,
        'rank': None,
        'rank_score': None,
        'selected_as_best': False,
        'cleanup': None,
    }


def _numeric_value(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        normalized = float(value)
        if not math.isfinite(normalized):
            return default
        return normalized
    except (TypeError, ValueError):
        return default


def _rank_score(candidate: dict) -> dict:
    incremental_promotion = candidate.get('promotion') or {}
    incremental_comparison = candidate.get('comparison') or {}
    reference_promotion = candidate.get('reference_promotion') or {}
    reference_comparison = candidate.get('reference_comparison') or {}
    use_reference = bool(reference_promotion and reference_comparison)
    promotion = reference_promotion if use_reference else incremental_promotion
    comparison = reference_comparison if use_reference else incremental_comparison
    candidate_summary = comparison.get('candidate_summary') or {}
    score = {
        'promotion_passed': promotion.get('passed') is True,
        'promotion_score': _numeric_value(promotion.get('score')),
        'trade_count': _numeric_value(candidate_summary.get('trade_count')),
        'trade_count_retention': _numeric_value(comparison.get('trade_count_retention')),
        'date_concentration': _numeric_value(
            candidate_summary.get('date_concentration'),
            default=float('inf'),
        ),
        'symbol_concentration': _numeric_value(
            candidate_summary.get('symbol_concentration'),
            default=float('inf'),
        ),
    }
    if use_reference:
        score['score_basis'] = 'reference'
        score['incremental_promotion_score'] = _numeric_value(incremental_promotion.get('score'))
        score['reference_promotion_score'] = _numeric_value(reference_promotion.get('score'))
    return score


def _rank_key(candidate: dict) -> tuple:
    score = candidate.get('rank_score') or _rank_score(candidate)
    passed_rank = 0 if score['promotion_passed'] else 1
    score_value = score.get('adjusted_score', score['promotion_score'])
    return (
        passed_rank,
        -score_value,
        -score['trade_count'],
        -score['trade_count_retention'],
        score['date_concentration'],
        score['symbol_concentration'],
        int(candidate.get('index') or 0),
    )


def _rank_candidate_results(
    candidates: list[dict],
    config: ResearchLoopConfig | None = None,
) -> tuple[list[dict], dict | None]:
    ranked_candidates = [dict(candidate) for candidate in candidates]
    for candidate in ranked_candidates:
        rank_score = _rank_score(candidate)
        if config is not None and config.use_retention_penalty:
            rank_score = apply_retention_penalty(
                rank_score,
                config.min_estimated_retention,
            )
        candidate['rank'] = None
        candidate['rank_score'] = rank_score
        candidate['selected_as_best'] = False

    eligible_indexes = [
        index
        for index, candidate in enumerate(ranked_candidates)
        if candidate.get('status') == 'ok'
    ]
    ordered_indexes = sorted(
        eligible_indexes,
        key=lambda index: _rank_key(ranked_candidates[index]),
    )

    best_candidate = None
    for rank, candidate_index in enumerate(ordered_indexes, start=1):
        candidate = ranked_candidates[candidate_index]
        candidate['rank'] = rank
        candidate['selected_as_best'] = rank == 1
        if rank == 1:
            best_candidate = candidate

    return ranked_candidates, best_candidate


def _cleanup_candidate_by_name(strategy_name: str, reason: str) -> dict:
    try:
        result = delete_strategy_from_db(DB_STRATEGY, strategy_name, 'buy')
    except Exception as e:
        return {
            'attempted': True,
            'reason': reason,
            'strategy_name': strategy_name,
            'status': 'error',
            'message': str(e),
        }
    return {
        'attempted': True,
        'reason': reason,
        'strategy_name': strategy_name,
        'status': result.get('status'),
        'message': result.get('message'),
        'action': result.get('action'),
    }


def _candidate_not_created_cleanup(strategy_name: str, reason: str = 'candidate_not_created') -> dict:
    return {
        'attempted': False,
        'reason': reason,
        'strategy_name': strategy_name,
    }


def _cleanup_summary(candidates: list[dict]) -> dict:
    summary = {
        'attempted_count': 0,
        'deleted_count': 0,
        'kept_count': 0,
        'failed_count': 0,
        'items': [],
    }
    for candidate in candidates:
        cleanup = candidate.get('cleanup') or {}
        summary['items'].append(cleanup)
        if cleanup.get('attempted') is True:
            summary['attempted_count'] += 1
            if cleanup.get('status') == 'error':
                summary['failed_count'] += 1
            elif cleanup.get('action') == 'deleted' or str(cleanup.get('reason', '')).endswith('_deleted'):
                summary['deleted_count'] += 1
        elif cleanup:
            summary['kept_count'] += 1
    return summary


def _apply_iteration_cleanup(config: ResearchLoopConfig, candidates: list[dict]) -> tuple[list[dict], dict]:
    updated_candidates = []
    for candidate in candidates:
        updated = dict(candidate)
        existing_cleanup = updated.get('cleanup')
        if existing_cleanup is not None:
            preserved = dict(existing_cleanup)
            preserved['existing'] = True
            updated['cleanup'] = preserved
            updated_candidates.append(updated)
            continue

        strategy_name = updated.get('strategy_name')
        is_best = updated.get('selected_as_best') is True
        is_failed = updated.get('status') != 'ok'

        if is_best and not config.cleanup_best_candidate:
            updated['cleanup'] = {
                'attempted': False,
                'reason': 'best_candidate_kept',
                'strategy_name': strategy_name,
            }
        elif is_best:
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'best_candidate_deleted',
            )
        elif is_failed and (
            updated.get('phase') in _CLEANUP_SAFE_FAILURE_PHASES
            or updated.get('cleanup_safe') is True
        ):
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'failed_candidate_deleted',
            )
        elif is_failed:
            updated['cleanup'] = _candidate_not_created_cleanup(strategy_name)
        elif config.keep_loser_candidates:
            updated['cleanup'] = {
                'attempted': False,
                'reason': 'loser_candidate_kept',
                'strategy_name': strategy_name,
            }
        else:
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'loser_candidate_deleted',
            )
        updated_candidates.append(updated)

    return updated_candidates, _cleanup_summary(updated_candidates)


def run_research_once(config: ResearchLoopConfig, controller) -> dict:
    """Run one analyze-generate-compare research iteration."""
    validation = validate_research_iteration_config(config)
    if validation.get('status') != 'ok':
        return validation

    baseline_result = None
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        baseline_result = controller.run(_base_config_dict(config))
        if baseline_result.get('status') not in ('ok', 'success'):
            return _error('baseline_run', baseline_result.get('message', 'baseline run failed'), run_result=baseline_result)
        baseline_csv = _csv_path_from_run(baseline_result)
        if not baseline_csv:
            return _error('baseline_run', 'baseline run did not return csv_path', run_result=baseline_result)

    analysis_result = analyze_result_csv(
        baseline_csv,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
    )
    if analysis_result.get('status') != 'ok':
        return _error(
            'analysis',
            analysis_result.get('message', 'analysis failed'),
            baseline_csv=baseline_csv,
            analysis_result=analysis_result,
        )

    expression_result = generate_condition_expressions_from_analysis(
        analysis_result,
        top_n=config.top_n,
    )
    expressions = expression_result.get('expressions') or []
    if expression_result.get('status') != 'ok' or not expressions:
        return _error(
            'no_expressions',
            expression_result.get('message', 'no candidate expressions generated'),
            baseline_csv=baseline_csv,
            analysis_result=analysis_result,
            expression_result=expression_result,
        )

    candidate = {
        'expression': _first_expression(expression_result),
        'expressions': expressions,
        'reason': _candidate_reason(expression_result),
        'candidate_count': expression_result.get('candidate_count', len(expressions)),
        'selected_candidates': expression_result.get('selected_candidates', []),
    }
    candidate_plan = _build_candidate_plan(config, candidate)

    if config.candidate_plan_only:
        return _build_result(config, {
            'status': 'ok',
            'phase': 'candidate_plan',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'candidate_csv': None,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
            'comparison': None,
            'promotion': None,
        })

    if config.run_candidate and not config.base_buy_strategy:
        return _build_result(config, _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            candidate=candidate,
            candidate_plan=candidate_plan,
        ))

    if not config.run_candidate:
        return _build_result(config, {
            'status': 'ok',
            'strategy_name': config.name,
            'config': asdict(config),
            'baseline_csv': baseline_csv,
            'candidate_csv': None,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
            'comparison': None,
            'promotion': None,
        })

    strategy_flow = _prepare_candidate_strategy(config, expressions)
    if strategy_flow.get('status') != 'ok':
        return _build_result(config, {
            **strategy_flow,
            'baseline_csv': baseline_csv,
            'baseline_result': baseline_result,
            'analysis_result': analysis_result,
            'expression_result': expression_result,
            'candidate': candidate,
            'candidate_plan': candidate_plan,
        })
    candidate['strategy_result'] = strategy_flow['strategy_result']
    candidate['generated_strategy'] = strategy_flow['generated_strategy']

    candidate_result = controller.run(_candidate_config_dict(config))
    if candidate_result.get('status') not in ('ok', 'success'):
        phase = _candidate_failure_phase(candidate_result)
        cleanup = _cleanup_candidate_strategy(config, phase)
        return _build_result(config, _error(
            phase,
            candidate_result.get('message', 'candidate run failed'),
            baseline_csv=baseline_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))
    candidate_csv = _csv_path_from_run(candidate_result)
    if not candidate_csv:
        cleanup = _cleanup_candidate_strategy(config, 'candidate_csv_missing')
        return _build_result(config, _error(
            'candidate_csv_missing',
            'candidate run did not return csv_path',
            baseline_csv=baseline_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))
    if not Path(candidate_csv).exists():
        cleanup = _cleanup_candidate_strategy(config, 'candidate_csv_missing')
        return _build_result(config, _error(
            'candidate_csv_missing',
            f'candidate csv_path does not exist: {candidate_csv}',
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))

    try:
        comparison = compare_trade_sets(
            _trade_frame_for_compare(baseline_csv),
            _trade_frame_for_compare(candidate_csv),
        )
        promotion = evaluate_research_candidate(comparison)
    except Exception as e:
        cleanup = _cleanup_candidate_strategy(config, 'comparison')
        return _build_result(config, _error(
            'comparison',
            str(e),
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
            candidate_plan=candidate_plan,
            cleanup=cleanup,
            run_result=candidate_result,
        ))

    return _build_result(config, {
        'status': 'ok',
        'strategy_name': config.name,
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'candidate_csv': candidate_csv,
        'baseline_result': baseline_result,
        'candidate_result': candidate_result,
        'analysis_result': analysis_result,
        'expression_result': expression_result,
        'candidate': candidate,
        'candidate_plan': candidate_plan,
        'comparison': comparison,
        'promotion': promotion,
    })


def run_research_iteration(config: ResearchLoopConfig, controller) -> dict:
    """Run one baseline analysis and evaluate multiple candidate expressions."""
    validation = validate_research_iteration_config(config)
    if validation.get('status') != 'ok':
        return validation
    config = replace(config, run_candidate=False, run_candidates=True)

    baseline_result = None
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        baseline_result = controller.run(_base_config_dict(config))
        if baseline_result.get('status') not in ('ok', 'success'):
            return _build_result(config, _error(
                'baseline_run',
                baseline_result.get('message', 'baseline run failed'),
                strategy_name=config.name,
                config=asdict(config),
                run_result=baseline_result,
            ))
        baseline_csv = _csv_path_from_run(baseline_result)
        if not baseline_csv:
            return _build_result(config, _error(
                'baseline_run',
                'baseline run did not return csv_path',
                strategy_name=config.name,
                config=asdict(config),
                run_result=baseline_result,
            ))

    analysis_result = analyze_result_csv(
        baseline_csv,
        min_samples=config.min_samples,
        quantiles=config.quantiles,
        alpha=config.alpha,
    )
    if analysis_result.get('status') != 'ok':
        return _build_result(config, _error(
            'analysis',
            analysis_result.get('message', 'analysis failed'),
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
        ))

    iteration_plan = _build_iteration_plan(config)
    expression_result = generate_condition_expressions_from_analysis(
        analysis_result,
        top_n=iteration_plan['effective_top_n'],
    )
    expressions = expression_result.get('expressions') or []
    if expression_result.get('status') != 'ok' or not expressions:
        return _build_result(config, _error(
            'no_expressions',
            expression_result.get('message', 'no candidate expressions generated'),
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
        ))
    if len(expressions) < config.candidate_count:
        return _build_result(config, _error(
            'insufficient_expressions',
            f"candidate_count={config.candidate_count} requested but only {len(expressions)} expressions generated",
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
            requested_candidate_count=config.candidate_count,
            expression_count=len(expressions),
        ))

    source_candidates = expression_result.get('selected_candidates') or []
    expression_candidates = []
    for index, expression in enumerate(expressions):
        source_candidate = (
            dict(source_candidates[index])
            if index < len(source_candidates) and isinstance(source_candidates[index], dict)
            else {}
        )
        source_candidate['expression'] = expression
        source_candidate['original_index'] = index
        expression_candidates.append(source_candidate)
    iteration_v2 = None
    iteration_v3 = None
    if config.iteration_v2_mode == 'best_feature_mix':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
            'source_candidate': candidate_from_expression(
                config.iteration_v2_best_expression,
                feature=config.iteration_v2_primary_feature,
            ),
        }
        iteration_v2 = build_v2_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            include_secondary_only=config.iteration_v2_include_secondary_only,
            max_secondary_only=config.iteration_v2_max_secondary_only,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v2.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v2': iteration_v2,
        }
        expressions = expression_result['expressions']
    elif config.iteration_v2_mode == 'best_feature_mix_v3':
        best_context = {
            'strategy_name': config.iteration_v2_best_candidate,
            'expression': config.iteration_v2_best_expression,
        }
        iteration_v3 = build_v3_candidate_pool(
            expression_candidates,
            best_context=best_context,
            primary_feature=config.iteration_v2_primary_feature,
            secondary_features=_split_csv_values(config.iteration_v2_secondary_features),
            min_estimated_retention=config.min_estimated_retention,
            retention_tolerance=config.iteration_v2_duplicate_retention_tolerance,
        )
        expression_candidates = iteration_v3.get('candidates') or []
        expression_result = {
            **expression_result,
            'selected_candidates': expression_candidates,
            'expressions': [candidate['expression'] for candidate in expression_candidates],
            'candidate_count': len(expression_candidates),
            'iteration_v3': iteration_v3,
        }
        expressions = expression_result['expressions']
    baseline_frame = _trade_frame_for_compare(baseline_csv)
    annotated_candidates = annotate_candidate_retention(
        expression_candidates,
        baseline_frame,
        min_retention=config.min_estimated_retention,
    )
    selected_candidates, retention_selection = select_retention_aware_candidates(
        annotated_candidates,
        candidate_count=config.candidate_count,
        allow_fallback=config.allow_retention_fallback,
        min_retention=config.min_estimated_retention,
    )
    retention_candidates = _retention_candidate_diagnostics(
        annotated_candidates,
        selected_candidates,
    )
    retention_selection = {
        **retention_selection,
        'retention_candidates': retention_candidates,
    }
    expression_result = {
        **expression_result,
        'selected_candidates': selected_candidates,
        'retention_selection': retention_selection,
        'retention_candidates': retention_candidates,
    }
    if retention_selection.get('status') != 'ok':
        return _build_result(config, _error(
            retention_selection.get('phase', 'insufficient_retention_candidates'),
            retention_selection.get('message', 'insufficient retention-aware candidates'),
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
            **_iteration_generation_metadata(iteration_v2, iteration_v3),
            retention_selection=retention_selection,
            retention_candidates=retention_candidates,
        ))
    if len(selected_candidates) < config.candidate_count:
        return _build_result(config, _error(
            'insufficient_retention_candidates',
            (
                f"candidate_count={config.candidate_count} requested but only "
                f"{len(selected_candidates)} candidates selected after retention filtering"
            ),
            strategy_name=config.name,
            config=asdict(config),
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
            analysis_result=analysis_result,
            expression_result=expression_result,
            iteration_plan=iteration_plan,
            **_iteration_generation_metadata(iteration_v2, iteration_v3),
            retention_selection=retention_selection,
            retention_candidates=retention_candidates,
            requested_candidate_count=config.candidate_count,
            selected_candidate_count=len(selected_candidates),
        ))
    expression_result = {
        **expression_result,
        'expressions': [candidate['expression'] for candidate in selected_candidates],
        'selected_candidates': selected_candidates,
    }

    specs = _build_candidate_specs(config, expression_result)
    candidates = [
        _execute_candidate_spec(config, spec, controller, baseline_csv)
        for spec in specs
    ]
    ranked_candidates, best_candidate = _rank_candidate_results(candidates, config)
    ranked_candidates, cleanup_summary = _apply_iteration_cleanup(config, ranked_candidates)
    best_candidate = next(
        (
            candidate
            for candidate in ranked_candidates
            if candidate.get('selected_as_best') is True
        ),
        None,
    )

    has_best_candidate = best_candidate is not None
    return _build_result(config, {
        'status': 'ok' if has_best_candidate else 'error',
        'phase': 'candidates_evaluated' if has_best_candidate else 'candidate_iteration',
        'message': None if has_best_candidate else 'no candidate evaluated successfully',
        'strategy_name': config.name,
        'config': asdict(config),
        'baseline_csv': baseline_csv,
        'baseline_result': baseline_result,
        'analysis_result': analysis_result,
        'expression_result': expression_result,
        'iteration_plan': iteration_plan,
        **_iteration_generation_metadata(iteration_v2, iteration_v3),
        'retention_selection': retention_selection,
        'retention_candidates': retention_candidates,
        'candidate_specs': specs,
        'candidates': ranked_candidates,
        'best_candidate': best_candidate,
        'cleanup_summary': cleanup_summary,
    })
