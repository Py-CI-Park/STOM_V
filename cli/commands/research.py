"""Discovery research command parser and handler wiring."""

from __future__ import annotations

import json
from typing import Any


ITERATION_V2_MODE_CHOICES = [
    'best_feature_mix',
    'best_feature_mix_v3',
    'best_feature_mix_v4',
    'best_feature_mix_v5',
]


def add_research_parser(disc_sub):
    disc_research = disc_sub.add_parser('research', help='run one discovery research iteration')
    disc_research.add_argument('name', help='strategy name to create')
    disc_research.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
    disc_research.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
    disc_research.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
    disc_research.add_argument('--sell', required=True, help='existing sell strategy name')
    disc_research.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
    disc_research.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
    disc_research.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_research.add_argument('--betting', default='1')
    disc_research.add_argument('--avg-time', type=int, default=60)
    disc_research.add_argument('--start-time', type=int, default=90000)
    disc_research.add_argument('--end-time', type=int, default=152800)
    disc_research.add_argument('--engines', type=int, default=4)
    disc_research.add_argument('--top-n', type=int, default=1)
    disc_research.add_argument('--min-samples', type=int, default=30)
    disc_research.add_argument('--quantiles', type=int, default=10)
    disc_research.add_argument('--alpha', type=float, default=0.05)
    candidate_mode = disc_research.add_mutually_exclusive_group()
    candidate_mode.add_argument('--run-candidate', action='store_true', default=False)
    candidate_mode.add_argument('--run-candidates', action='store_true', default=False)
    disc_research.add_argument('--candidate-count', type=int, default=5)
    disc_research.add_argument('--candidate-name-prefix')
    disc_research.add_argument('--cleanup-best-candidate', action='store_true', default=False)
    disc_research.add_argument('--keep-loser-candidates', action='store_true', default=False)
    disc_research.add_argument('--min-estimated-retention', type=float, default=0.4)
    disc_research.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
    disc_research.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
    disc_research.add_argument('--candidate-pool-multiplier', type=int, default=3)
    disc_research.add_argument('--candidate-start', type=int)
    disc_research.add_argument('--candidate-end', type=int)
    disc_research.add_argument('--candidate-timeout', type=int)
    disc_research.add_argument('--candidate-plan-only', action='store_true', default=False)
    disc_research.add_argument('--keep-failed-candidate', action='store_true', default=False)
    disc_research.add_argument('--runtime-output', dest='runtime_output_path')
    disc_research.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
    disc_research.add_argument(
        '--iteration-v2-mode',
        choices=ITERATION_V2_MODE_CHOICES,
        default='',
    )
    disc_research.add_argument('--iteration-v2-best-candidate', default='')
    disc_research.add_argument('--iteration-v2-best-expression', default='')
    disc_research.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
    disc_research.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
    disc_research.add_argument('--iteration-v2-secondary-features', default='')
    disc_research.add_argument(
        '--no-iteration-v2-secondary-only',
        dest='iteration_v2_include_secondary_only',
        action='store_false',
        default=True,
    )
    disc_research.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
    disc_research.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
    return disc_research


def add_optimize_wide_v2_parser(disc_sub):
    disc_optimize_v2 = disc_sub.add_parser('optimize-wide-v2', help='run Wide v2 multi-round backtest optimizer')
    disc_optimize_v2.add_argument('--name', required=True, help='optimizer run id')
    disc_optimize_v2.add_argument('--input', '-i', dest='input_file', help='baseline CSV file')
    disc_optimize_v2.add_argument('--score-reference-csv', help='root baseline CSV for cumulative score comparison')
    disc_optimize_v2.add_argument('--base-buy-strategy', required=True, help='existing buy strategy name')
    disc_optimize_v2.add_argument('--sell', required=True, help='existing sell strategy name')
    disc_optimize_v2.add_argument('--seed-candidate', default='', help='initial seed strategy name')
    disc_optimize_v2.add_argument('--seed-expression', default='', help='initial seed expression for v5 candidate generation')
    disc_optimize_v2.add_argument('--start', type=int, required=True, help='start date YYYYMMDD')
    disc_optimize_v2.add_argument('--end', type=int, required=True, help='end date YYYYMMDD')
    disc_optimize_v2.add_argument('--timeframe', choices=['tick', 'min'], default='tick')
    disc_optimize_v2.add_argument('--betting', default='1')
    disc_optimize_v2.add_argument('--avg-time', type=int, default=60)
    disc_optimize_v2.add_argument('--start-time', type=int, default=90000)
    disc_optimize_v2.add_argument('--end-time', type=int, default=152800)
    disc_optimize_v2.add_argument('--engines', type=int, default=4)
    disc_optimize_v2.add_argument('--top-n', type=int, default=1)
    disc_optimize_v2.add_argument('--min-samples', type=int, default=30)
    disc_optimize_v2.add_argument('--quantiles', type=int, default=10)
    disc_optimize_v2.add_argument('--alpha', type=float, default=0.05)
    disc_optimize_v2.add_argument('--candidate-count', type=int, default=10)
    disc_optimize_v2.add_argument('--candidate-timeout', type=int)
    disc_optimize_v2.add_argument('--cleanup-best-candidate', action='store_true', default=False)
    disc_optimize_v2.add_argument('--keep-loser-candidates', action='store_true', default=False)
    disc_optimize_v2.add_argument('--keep-failed-candidate', action='store_true', default=False)
    disc_optimize_v2.add_argument('--min-estimated-retention', type=float, default=0.4)
    disc_optimize_v2.add_argument('--no-retention-fallback', dest='allow_retention_fallback', action='store_false', default=True)
    disc_optimize_v2.add_argument('--no-retention-penalty', dest='use_retention_penalty', action='store_false', default=True)
    disc_optimize_v2.add_argument('--candidate-pool-multiplier', type=int, default=3)
    disc_optimize_v2.add_argument(
        '--iteration-v2-mode',
        choices=ITERATION_V2_MODE_CHOICES,
        default='best_feature_mix_v5',
    )
    disc_optimize_v2.add_argument('--iteration-v2-primary-feature', default='B_시가총액')
    disc_optimize_v2.add_argument('--iteration-v2-trade-amount-feature', default='B_당일거래대금')
    disc_optimize_v2.add_argument('--iteration-v2-secondary-features', default='')
    disc_optimize_v2.add_argument(
        '--no-iteration-v2-secondary-only',
        dest='iteration_v2_include_secondary_only',
        action='store_false',
        default=True,
    )
    disc_optimize_v2.add_argument('--iteration-v2-max-secondary-only', type=int, default=1)
    disc_optimize_v2.add_argument('--iteration-v2-duplicate-retention-tolerance', type=float, default=0.02)
    disc_optimize_v2.add_argument('--max-rounds', type=int, default=3)
    disc_optimize_v2.add_argument('--min-improvement', type=float, default=0.01)
    disc_optimize_v2.add_argument('--stop-after-no-improvement', type=int, default=2)
    disc_optimize_v2.add_argument('--max-consecutive-candidate-failures', type=int, default=3)
    disc_optimize_v2.add_argument('--runtime-output', dest='runtime_output_path')
    disc_optimize_v2.add_argument('--leaderboard-output', dest='leaderboard_output_path')
    disc_optimize_v2.add_argument('--summary-output', dest='summary_output_path')
    disc_optimize_v2.add_argument('--report-path')
    return disc_optimize_v2


def build_research_strategy_payload(parsed) -> dict[str, Any]:
    return {
        'name': parsed.name,
        'baseline_csv': getattr(parsed, 'input_file', None),
        'score_reference_csv': parsed.score_reference_csv,
        'base_buy_strategy': parsed.base_buy_strategy,
        'sell_strategy': parsed.sell,
        'start_date': parsed.start,
        'end_date': parsed.end,
        'is_tick': parsed.timeframe == 'tick',
        'betting': parsed.betting,
        'avg_time': parsed.avg_time,
        'start_time': parsed.start_time,
        'end_time': parsed.end_time,
        'engine_count': parsed.engines,
        'top_n': parsed.top_n,
        'min_samples': parsed.min_samples,
        'quantiles': parsed.quantiles,
        'alpha': parsed.alpha,
        'run_candidate': parsed.run_candidate,
        'run_candidates': parsed.run_candidates,
        'candidate_count': parsed.candidate_count,
        'candidate_name_prefix': parsed.candidate_name_prefix,
        'cleanup_best_candidate': parsed.cleanup_best_candidate,
        'keep_loser_candidates': parsed.keep_loser_candidates,
        'min_estimated_retention': parsed.min_estimated_retention,
        'allow_retention_fallback': parsed.allow_retention_fallback,
        'use_retention_penalty': parsed.use_retention_penalty,
        'candidate_pool_multiplier': parsed.candidate_pool_multiplier,
        'candidate_start_date': parsed.candidate_start,
        'candidate_end_date': parsed.candidate_end,
        'candidate_timeout': parsed.candidate_timeout,
        'candidate_plan_only': parsed.candidate_plan_only,
        'keep_failed_candidate': parsed.keep_failed_candidate,
        'runtime_output_path': parsed.runtime_output_path,
        'max_consecutive_candidate_failures': parsed.max_consecutive_candidate_failures,
        'iteration_v2_mode': parsed.iteration_v2_mode,
        'iteration_v2_best_candidate': parsed.iteration_v2_best_candidate,
        'iteration_v2_best_expression': parsed.iteration_v2_best_expression,
        'iteration_v2_primary_feature': parsed.iteration_v2_primary_feature,
        'iteration_v2_trade_amount_feature': parsed.iteration_v2_trade_amount_feature,
        'iteration_v2_secondary_features': parsed.iteration_v2_secondary_features,
        'iteration_v2_include_secondary_only': parsed.iteration_v2_include_secondary_only,
        'iteration_v2_max_secondary_only': parsed.iteration_v2_max_secondary_only,
        'iteration_v2_duplicate_retention_tolerance': parsed.iteration_v2_duplicate_retention_tolerance,
    }


def build_wide_v2_optimizer_config(parsed):
    from cli.research_optimizer_state import WideV2OptimizerConfig

    return WideV2OptimizerConfig(
        name=parsed.name,
        baseline_csv=getattr(parsed, 'input_file', None),
        score_reference_csv=parsed.score_reference_csv,
        base_buy_strategy=parsed.base_buy_strategy,
        sell_strategy=parsed.sell,
        seed_candidate=parsed.seed_candidate,
        seed_expression=parsed.seed_expression,
        start_date=parsed.start,
        end_date=parsed.end,
        is_tick=parsed.timeframe == 'tick',
        betting=parsed.betting,
        avg_time=parsed.avg_time,
        start_time=parsed.start_time,
        end_time=parsed.end_time,
        engine_count=parsed.engines,
        top_n=parsed.top_n,
        min_samples=parsed.min_samples,
        quantiles=parsed.quantiles,
        alpha=parsed.alpha,
        candidate_count=parsed.candidate_count,
        candidate_timeout=parsed.candidate_timeout,
        cleanup_best_candidate=parsed.cleanup_best_candidate,
        keep_loser_candidates=parsed.keep_loser_candidates,
        keep_failed_candidate=parsed.keep_failed_candidate,
        min_estimated_retention=parsed.min_estimated_retention,
        allow_retention_fallback=parsed.allow_retention_fallback,
        use_retention_penalty=parsed.use_retention_penalty,
        candidate_pool_multiplier=parsed.candidate_pool_multiplier,
        iteration_v2_mode=parsed.iteration_v2_mode,
        iteration_v2_primary_feature=parsed.iteration_v2_primary_feature,
        iteration_v2_trade_amount_feature=parsed.iteration_v2_trade_amount_feature,
        iteration_v2_secondary_features=parsed.iteration_v2_secondary_features,
        iteration_v2_include_secondary_only=parsed.iteration_v2_include_secondary_only,
        iteration_v2_max_secondary_only=parsed.iteration_v2_max_secondary_only,
        iteration_v2_duplicate_retention_tolerance=parsed.iteration_v2_duplicate_retention_tolerance,
        max_rounds=parsed.max_rounds,
        min_improvement=parsed.min_improvement,
        stop_after_no_improvement=parsed.stop_after_no_improvement,
        max_consecutive_candidate_failures=parsed.max_consecutive_candidate_failures,
        runtime_output_path=parsed.runtime_output_path,
        leaderboard_output_path=parsed.leaderboard_output_path,
        summary_output_path=parsed.summary_output_path,
        report_path=parsed.report_path,
    )


def _controller_or_default(controller):
    if controller is not None:
        return controller
    from cli.ai_controller import AIBacktestController

    return AIBacktestController()


def handle_research(parsed, controller=None) -> int:
    controller = _controller_or_default(controller)
    result = controller.research_strategy_once(build_research_strategy_payload(parsed))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('status') == 'ok' else 1


def handle_optimize_wide_v2(parsed, controller=None) -> int:
    from cli.research_optimizer import run_wide_v2_optimizer

    controller = _controller_or_default(controller)
    result = run_wide_v2_optimizer(build_wide_v2_optimizer_config(parsed), controller)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get('status') == 'ok' else 1
