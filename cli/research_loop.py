"""One-shot research loop for improving an existing buy strategy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from cli.analyzer import analyze_result_csv
from cli.condition_generator import generate_condition_expressions_from_analysis
from cli.paths import DB_STRATEGY
from cli.promotion import resolve_promotion_criteria
from cli.research_compare import (
    INSTRUMENT_COLUMNS,
    OPTIONAL_KEY_COLUMNS,
    REQUIRED_KEY_COLUMNS,
    compare_trade_sets,
)
from cli.research_metrics import NUMERIC_COLUMNS, normalize_trade_frame
from cli.research_promotion import evaluate_research_candidate
from cli.research_report import build_research_report
from cli.strategy_generator import generate_buy_filter_strategy, save_strategy_to_db
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


@dataclass
class ResearchLoopConfig:
    name: str = 'AutoResearch'
    baseline_csv: str | None = None
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
    run_wfo: bool = False
    train_window_days: int | None = None
    test_window_days: int | None = None
    step_days: int | None = None
    purge_days: int = 0
    embargo_days: int = 0
    objective: str = 'tpi'
    wfo_method: str = 'grid'
    wfo_max_iter: int = 10
    promotion_preset: str = 'balanced'
    promotion_criteria: dict | None = None
    param_space: dict = field(default_factory=dict)


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


def _candidate_config_dict(config: ResearchLoopConfig) -> dict:
    candidate = _base_config_dict(config)
    candidate['buy_strategy'] = config.name
    return candidate


def _error(phase: str, message: str, **extra) -> dict:
    return {'status': 'error', 'phase': phase, 'message': message, **extra}


def _validate_wfo_config(config: ResearchLoopConfig) -> dict | None:
    """Return a structured error when WFO settings are incomplete."""
    if not config.run_wfo:
        return None
    if not config.run_candidate:
        return _error('wfo_config', 'run_wfo requires run_candidate=True')
    if config.train_window_days is None or config.test_window_days is None:
        return _error('wfo_config', 'run_wfo requires train_window_days and test_window_days')
    return None


def _wfo_settings_dict(config: ResearchLoopConfig) -> dict:
    """Build keyword arguments for controller.walk_forward()."""
    return {
        'train_window_days': config.train_window_days,
        'test_window_days': config.test_window_days,
        'step_days': config.step_days,
        'purge_days': config.purge_days,
        'embargo_days': config.embargo_days,
        'objective': config.objective,
        'method': config.wfo_method,
        'max_iter': config.wfo_max_iter,
    }


def _wfo_eval_criteria(config: ResearchLoopConfig) -> dict:
    """Resolve WFO promotion criteria from existing presets."""
    criteria = resolve_promotion_criteria(config.promotion_preset, config.promotion_criteria)
    return {
        'min_rounds': criteria['min_rounds'],
        'min_success_rate': criteria['min_success_rate'],
        'min_mean_oos_metric': criteria['min_mean_oos_metric'],
        'min_avg_trade_count': criteria['min_avg_trade_count'],
    }


def _combined_evaluation(research_promotion: dict | None, wfo_evaluation: dict | None, run_wfo: bool) -> dict:
    """Combine CSV-comparison and WFO pass/fail evidence."""
    research_passed = bool((research_promotion or {}).get('passed'))
    wfo_passed = bool((wfo_evaluation or {}).get('passed')) if run_wfo else None
    reasons = []
    for reason in (research_promotion or {}).get('reasons') or []:
        reasons.append(f'research:{reason}')
    if run_wfo:
        for reason in (wfo_evaluation or {}).get('reasons') or []:
            reasons.append(f'wfo:{reason}')
    passed = research_passed and (wfo_passed if run_wfo else True)
    if not passed and not reasons:
        if not research_passed:
            reasons.append('research:not_passed')
        if run_wfo and not wfo_passed:
            reasons.append('wfo:not_passed')
    return {
        'mode': 'research_plus_wfo' if run_wfo else 'research_only',
        'passed': passed,
        'research_passed': research_passed,
        'wfo_passed': wfo_passed,
        'reasons': reasons,
    }


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


def _prepare_candidate_strategy(config: ResearchLoopConfig, expressions: list[str]) -> dict:
    if not config.base_buy_strategy:
        return _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
        )
    if config.name == config.base_buy_strategy:
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

    candidate_name_result = load_strategy_from_db(DB_STRATEGY, config.name, 'buy')
    if candidate_name_result.get('status') == 'ok':
        return _error(
            'candidate_name_conflict',
            f"candidate buy strategy '{config.name}' already exists",
            candidate_strategy_result=candidate_name_result,
        )
    if not _is_strategy_not_found(candidate_name_result):
        return _error(
            'candidate_name_lookup',
            candidate_name_result.get('message', 'failed to check candidate buy strategy name'),
            candidate_strategy_result=candidate_name_result,
        )

    strategy_result = generate_buy_filter_strategy(
        config.name,
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
        config.name,
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


def run_research_once(config: ResearchLoopConfig, controller) -> dict:
    """Run one analyze-generate-compare research iteration."""
    baseline_result = None
    baseline_csv = config.baseline_csv
    if not baseline_csv:
        baseline_result = controller.run(_base_config_dict(config))
        if baseline_result.get('status') not in ('ok', 'success'):
            return _error('baseline_run', baseline_result.get('message', 'baseline run failed'), run_result=baseline_result)
        baseline_csv = _csv_path_from_run(baseline_result)
        if not baseline_csv:
            return _error('baseline_run', 'baseline run did not return csv_path', run_result=baseline_result)

    wfo_config_error = _validate_wfo_config(config)
    if wfo_config_error is not None:
        return {**wfo_config_error, 'baseline_csv': baseline_csv, 'baseline_result': baseline_result}

    if config.run_candidate and not config.base_buy_strategy:
        return _error(
            'candidate_strategy',
            'base_buy_strategy is required when run_candidate is True',
            baseline_csv=baseline_csv,
            baseline_result=baseline_result,
        )

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
            'comparison': None,
            'promotion': None,
        })

    strategy_flow = _prepare_candidate_strategy(config, expressions)
    if strategy_flow.get('status') != 'ok':
        return {**strategy_flow, 'baseline_csv': baseline_csv}
    candidate['strategy_result'] = strategy_flow['strategy_result']
    candidate['generated_strategy'] = strategy_flow['generated_strategy']

    candidate_result = controller.run(_candidate_config_dict(config))
    if candidate_result.get('status') not in ('ok', 'success'):
        return _error(
            'candidate_backtest',
            candidate_result.get('message', 'candidate run failed'),
            baseline_csv=baseline_csv,
            candidate=candidate,
            run_result=candidate_result,
        )
    candidate_csv = _csv_path_from_run(candidate_result)
    if not candidate_csv:
        return _error(
            'candidate_csv_missing',
            'candidate run did not return csv_path',
            baseline_csv=baseline_csv,
            candidate=candidate,
            run_result=candidate_result,
        )
    if not Path(candidate_csv).exists():
        return _error(
            'candidate_csv_missing',
            f'candidate csv_path does not exist: {candidate_csv}',
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
            run_result=candidate_result,
        )

    try:
        comparison = compare_trade_sets(
            _trade_frame_for_compare(baseline_csv),
            _trade_frame_for_compare(candidate_csv),
        )
        promotion = evaluate_research_candidate(comparison)
    except Exception as e:
        return _error(
            'comparison',
            str(e),
            baseline_csv=baseline_csv,
            candidate_csv=candidate_csv,
            candidate=candidate,
        )

    wfo_result = None
    wfo_evaluation = None
    if config.run_wfo:
        wfo_config = _candidate_config_dict(config)
        wfo_result = controller.walk_forward(wfo_config, config.param_space, **_wfo_settings_dict(config))
        if wfo_result.get('status') != 'ok':
            return _error(
                'wfo_execution',
                wfo_result.get('message', 'WFO execution failed'),
                baseline_csv=baseline_csv,
                candidate_csv=candidate_csv,
                candidate=candidate,
                wfo_result=wfo_result,
            )
        wfo_evaluation = controller.evaluate_walk_forward_result(wfo_result, **_wfo_eval_criteria(config))
        if wfo_evaluation.get('status') != 'ok':
            return _error(
                'wfo_evaluation',
                wfo_evaluation.get('message', 'WFO evaluation failed'),
                baseline_csv=baseline_csv,
                candidate_csv=candidate_csv,
                candidate=candidate,
                wfo_result=wfo_result,
                wfo_evaluation=wfo_evaluation,
            )
    combined = _combined_evaluation(promotion, wfo_evaluation, config.run_wfo)

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
        'comparison': comparison,
        'promotion': promotion,
        'wfo_result': wfo_result,
        'wfo_evaluation': wfo_evaluation,
        'combined_evaluation': combined,
    })
