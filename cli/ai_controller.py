"""AI 백테스트 컨트롤러 — 통합 파사드.

AI가 하나의 인터페이스로 전체 백테스트 파이프라인을 제어한다.
모든 메서드는 dict를 반환하며, 예외를 throw하지 않는다.

주의:
- 현재는 `stom_backtest.py` 의 공식 서브커맨드가 아니라 Python API 성격의 모듈이다.
- shipped CLI 범위와 혼동하지 않도록 문서/계획서에서 library-only 로 구분한다.
"""

import os
import sys
import time
import json
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.config import BacktestConfig, list_strategies, validate
from cli.engine_tuner import recommend_engine_count, get_system_info


class AIBacktestController:
    """AI 자동 백테스트 컨트롤러.

    사용법::

        controller = AIBacktestController()
        strategies = controller.list_strategies()
        result = controller.run({
            'buy_strategy': 'Min_B_Study_251227',
            'sell_strategy': 'Min_S_Study_251227',
            'start_date': 20250407,
            'end_date': 20250409,
            'is_tick': False,
            'engine_count': 2,
        })
        history = controller.get_history(limit=5)
        best = controller.get_best('tpi')
    """

    def __init__(self, history_db_path=None):
        self._history_db = history_db_path

    def _init_history(self):
        """히스토리 DB를 초기화하고 경로를 반환한다."""
        try:
            from cli.history import init_history_db
            return init_history_db(self._history_db)
        except Exception:
            return None

    def list_strategies(self) -> dict:
        """사용 가능한 전략 목록을 반환한다."""
        try:
            stgs = list_strategies()
            return {'status': 'ok', 'strategies': stgs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def analyze_strategy(self, name: str, strategy_type: str = 'buy') -> dict:
        """전략을 AST 분석하고 타임프레임을 감지한다."""
        try:
            from cli.strategy_loader import load_strategy_from_db
            from cli.timeframe_detector import detect_timeframe
            from cli.paths import DB_STRATEGY

            loader_result = load_strategy_from_db(DB_STRATEGY, name, strategy_type)
            if loader_result['status'] != 'ok':
                return loader_result

            code = loader_result.get('code', '')
            timeframe = detect_timeframe(name, code)

            return {
                'status': 'ok',
                'name': name,
                'type': strategy_type,
                'timeframe': timeframe,
                'var_refs': loader_result.get('var_refs', []),
                'functions': loader_result.get('functions', []),
                'warnings': loader_result.get('warnings', []),
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _prepare_strategy_candidate(self, name: str, analysis_result: dict = None, input_path: str = None,
                                    top_n: int = 5, strategy_type: str = 'buy', buy_var: str = '매수',
                                    min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                                    ml_analysis_result: dict = None, ml_feature_limit: int = 0,
                                    ml_model_type: str = 'random_forest', ml_top_n: int = 10,
                                    ml_n_splits: int = 5, ml_random_state: int = 42,
                                    ml_weight: float = 0.0) -> dict:
        from cli.analyzer import analyze_result_csv
        from cli.condition_generator import (
            generate_condition_expressions_from_analysis,
            generate_conditions_from_analysis,
        )

        if strategy_type != 'buy':
            return {'status': 'error', 'message': '현재 자동 조건식 탐색은 buy 전략 생성만 지원합니다.'}

        if analysis_result is None:
            if not input_path:
                return {'status': 'error', 'message': 'analysis_result 또는 input_path가 필요합니다.'}
            analysis_result = analyze_result_csv(
                input_path,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
            )
        if analysis_result.get('status') != 'ok':
            return analysis_result

        feature_whitelist = None
        feature_importance_map = None
        if ml_feature_limit > 0:
            if ml_analysis_result is None:
                if not input_path:
                    return {'status': 'error', 'message': 'ML feature filtering에는 input_path 또는 ml_analysis_result가 필요합니다.'}
                ml_analysis_result = self.analyze_results_ml(
                    input_path,
                    model_type=ml_model_type,
                    top_n=ml_top_n,
                    n_splits=ml_n_splits,
                    random_state=ml_random_state,
                )
            if ml_analysis_result.get('status') != 'ok':
                return ml_analysis_result
            feature_whitelist = [
                item['feature']
                for item in (ml_analysis_result.get('top_features') or [])[:ml_feature_limit]
            ]
        if ml_analysis_result is not None:
            feature_importance_map = ml_analysis_result.get('feature_importance_map') or {
                item['feature']: item['importance']
                for item in (ml_analysis_result.get('top_features') or [])
            }

        expression_result = generate_condition_expressions_from_analysis(
            analysis_result,
            top_n=top_n,
            feature_whitelist=feature_whitelist,
            feature_importance_map=feature_importance_map,
            ml_weight=ml_weight,
        )
        code_result = generate_conditions_from_analysis(
            analysis_result,
            top_n=top_n,
            buy_var=buy_var,
            feature_whitelist=feature_whitelist,
            feature_importance_map=feature_importance_map,
            ml_weight=ml_weight,
        )
        return {
            'status': 'ok',
            'analysis_result': analysis_result,
            'ml_analysis_result': ml_analysis_result,
            'feature_whitelist': feature_whitelist,
            'feature_importance_map': feature_importance_map,
            'expression_result': expression_result,
            'code_result': code_result,
        }

    def analyze_results(self, input_path: str, min_samples: int = 30, quantiles: int = 10,
                        alpha: float = 0.05, output_path: str = None) -> dict:
        """백테스트 상세 CSV를 분석해 조건 후보를 추출한다."""
        try:
            from cli.analyzer import analyze_result_csv, save_analysis

            result = analyze_result_csv(
                input_path,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
            )
            if output_path and result.get('status') == 'ok':
                save_result = save_analysis(result, output_path)
                result['saved'] = save_result
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def analyze_results_ml(self, input_path: str, model_type: str = 'random_forest',
                           top_n: int = 10, n_splits: int = 5, random_state: int = 42,
                           output_path: str = None) -> dict:
        """ML 기반으로 B_* feature importance를 분석한다."""
        try:
            from cli.ml_factor_model import analyze_results_ml, save_ml_analysis

            result = analyze_results_ml(
                input_path,
                model_type=model_type,
                top_n=top_n,
                n_splits=n_splits,
                random_state=random_state,
            )
            if output_path and result.get('status') == 'ok':
                result['saved'] = save_ml_analysis(result, output_path)
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def generate_conditions(self, analysis_result: dict = None, input_path: str = None,
                            top_n: int = 5, buy_var: str = '매수', output_path: str = None,
                            min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                            ml_analysis_result: dict = None, ml_feature_limit: int = 0,
                            ml_model_type: str = 'random_forest', ml_top_n: int = 10,
                            ml_n_splits: int = 5, ml_random_state: int = 42,
                            ml_weight: float = 0.0) -> dict:
        """분석 결과 또는 CSV 입력으로부터 자동 필터 조건 코드를 생성한다."""
        try:
            from cli.condition_generator import save_condition_code

            prepared = self._prepare_strategy_candidate(
                name='__preview__',
                analysis_result=analysis_result,
                input_path=input_path,
                top_n=top_n,
                strategy_type='buy',
                buy_var=buy_var,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
                ml_analysis_result=ml_analysis_result,
                ml_feature_limit=ml_feature_limit,
                ml_model_type=ml_model_type,
                ml_top_n=ml_top_n,
                ml_n_splits=ml_n_splits,
                ml_random_state=ml_random_state,
                ml_weight=ml_weight,
            )
            if prepared.get('status') != 'ok':
                return prepared

            result = {
                'status': 'ok',
                'analysis_result': prepared['analysis_result'],
                'ml_analysis_result': prepared.get('ml_analysis_result'),
                'feature_whitelist': prepared.get('feature_whitelist'),
                'feature_importance_map': prepared.get('feature_importance_map'),
                'selected_candidates': prepared['code_result'].get('selected_candidates', []),
                'code': prepared['code_result']['code'],
                'candidate_count': prepared['code_result']['candidate_count'],
            }
            if output_path and result.get('status') == 'ok':
                save_result = save_condition_code(result['code'], output_path)
                result['saved'] = save_result
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_strategy_from_analysis(self, name: str, analysis_result: dict = None, input_path: str = None,
                                      top_n: int = 5, strategy_type: str = 'buy', buy_var: str = '매수',
                                      min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                                      output_code_path: str = None, ml_analysis_result: dict = None,
                                      ml_feature_limit: int = 0, ml_model_type: str = 'random_forest',
                                      ml_top_n: int = 10, ml_n_splits: int = 5, ml_random_state: int = 42,
                                      ml_weight: float = 0.0) -> dict:
        """분석 결과로부터 전략 코드를 생성하고 strategy.db에 저장한다."""
        try:
            from cli.condition_generator import save_condition_code

            prepared = self._prepare_strategy_candidate(
                name=name,
                analysis_result=analysis_result,
                input_path=input_path,
                top_n=top_n,
                strategy_type=strategy_type,
                buy_var=buy_var,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
                ml_analysis_result=ml_analysis_result,
                ml_feature_limit=ml_feature_limit,
                ml_model_type=ml_model_type,
                ml_top_n=ml_top_n,
                ml_n_splits=ml_n_splits,
                ml_random_state=ml_random_state,
                ml_weight=ml_weight,
            )
            if prepared.get('status') != 'ok':
                return prepared

            analysis_result = prepared['analysis_result']
            ml_analysis_result = prepared.get('ml_analysis_result')
            feature_whitelist = prepared.get('feature_whitelist')
            expression_result = prepared['expression_result']
            code_result = prepared['code_result']
            strategy_result = self.create_strategy(name, expression_result['expressions'], strategy_type)

            response = {
                'status': strategy_result.get('status', 'error'),
                'analysis_result': analysis_result,
                'ml_analysis_result': ml_analysis_result,
                'feature_whitelist': feature_whitelist,
                'feature_importance_map': prepared.get('feature_importance_map'),
                'expression_result': expression_result,
                'generated_code': code_result.get('code'),
                'strategy_result': strategy_result,
            }
            if output_code_path and code_result.get('status') == 'ok':
                response['saved_code'] = save_condition_code(code_result['code'], output_code_path)
            return response
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def evaluate_walk_forward_result(self, walk_forward_result: dict, min_rounds: int = 1,
                                     min_success_rate: float = 0.6, min_mean_oos_metric: float = 0.0,
                                     min_avg_trade_count: float = 0.0) -> dict:
        if walk_forward_result.get('status') != 'ok':
            return {'status': 'error', 'passed': False, 'reasons': ['walk_forward_failed']}

        summary = walk_forward_result.get('summary') or {}
        rounds = walk_forward_result.get('rounds') or []
        reasons = []

        round_count = int(summary.get('round_count', len(rounds)))
        success_rate = float(summary.get('success_rate', 0.0) or 0.0)
        mean_oos_metric = summary.get('mean_oos_metric')

        if round_count < min_rounds:
            reasons.append(f'round_count<{min_rounds}')
        if success_rate < min_success_rate:
            reasons.append(f'success_rate<{min_success_rate}')
        if mean_oos_metric is None or float(mean_oos_metric) < min_mean_oos_metric:
            reasons.append(f'mean_oos_metric<{min_mean_oos_metric}')

        trade_counts = []
        inferred_zero_trade_rounds = 0
        for round_result in rounds:
            test_result = round_result.get('test_result') or {}
            metrics = test_result.get('metrics') or {}
            trade_count = metrics.get('trade_count')
            if trade_count is None and test_result.get('status') == 'success':
                message = str(test_result.get('message', '') or '')
                if not metrics or '결과 테이블이 비어있습니다' in message:
                    inferred_zero_trade_rounds += 1
                    trade_count = 0.0
            if trade_count is not None:
                trade_counts.append(float(trade_count))
        avg_trade_count = (sum(trade_counts) / len(trade_counts)) if trade_counts else None
        zero_trade_rounds = int(summary.get('zero_trade_rounds', 0) or 0)
        if inferred_zero_trade_rounds:
            zero_trade_rounds = max(zero_trade_rounds, inferred_zero_trade_rounds)
        if trade_counts:
            zero_trade_rounds = max(zero_trade_rounds, sum(1 for trade_count in trade_counts if trade_count <= 0))
        if min_avg_trade_count > 0 and (avg_trade_count is None or avg_trade_count < min_avg_trade_count):
            reasons.append(f'avg_trade_count<{min_avg_trade_count}')
        if round_count > 0 and zero_trade_rounds >= round_count:
            reasons.append('all_rounds_no_trades')

        return {
            'status': 'ok',
            'passed': len(reasons) == 0,
            'reasons': reasons,
            'criteria': {
                'min_rounds': min_rounds,
                'min_success_rate': min_success_rate,
                'min_mean_oos_metric': min_mean_oos_metric,
                'min_avg_trade_count': min_avg_trade_count,
            },
            'summary': {
                'round_count': round_count,
                'success_rate': success_rate,
                'mean_oos_metric': mean_oos_metric,
                'avg_trade_count': avg_trade_count,
                'zero_trade_rounds': zero_trade_rounds,
                'trade_count_rounds': len(trade_counts),
            },
        }

    def discover_strategy(self, name: str, config_dict: dict, input_path: str = None, analysis_result: dict = None,
                          param_space: dict = None, top_n: int = 5, strategy_type: str = 'buy',
                          buy_var: str = '매수', min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                          output_code_path: str = None, walk_forward_settings: dict = None,
                          ml_analysis_result: dict = None, ml_feature_limit: int = 0,
                          ml_model_type: str = 'random_forest', ml_top_n: int = 10,
                          ml_n_splits: int = 5, ml_random_state: int = 42,
                          ml_weight: float = 0.0) -> dict:
        """분석 → 조건 생성 → 전략 저장 → (선택) WFO 검증을 한 번에 수행한다."""
        try:
            strategy_flow = self.create_strategy_from_analysis(
                name=name,
                analysis_result=analysis_result,
                input_path=input_path,
                top_n=top_n,
                strategy_type=strategy_type,
                buy_var=buy_var,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
                output_code_path=output_code_path,
                ml_analysis_result=ml_analysis_result,
                ml_feature_limit=ml_feature_limit,
                ml_model_type=ml_model_type,
                ml_top_n=ml_top_n,
                ml_n_splits=ml_n_splits,
                ml_random_state=ml_random_state,
                ml_weight=ml_weight,
            )
            if strategy_flow.get('status') != 'ok':
                return strategy_flow

            response = {
                'status': 'ok',
                'strategy_flow': strategy_flow,
            }

            if walk_forward_settings is not None:
                config_dict = dict(config_dict)
                if strategy_type == 'buy':
                    config_dict['buy_strategy'] = name
                else:
                    config_dict['sell_strategy'] = name

                wf_result = self.walk_forward(
                    config_dict,
                    param_space or {},
                    **walk_forward_settings,
                )
                response['walk_forward'] = wf_result
                if wf_result.get('status') != 'ok':
                    response['status'] = 'error'

            return response
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def _save_generated_strategy(self, strategy_name, expressions, strategy_type, base_buy_strategy):
        """전략 코드를 생성하여 DB에 저장한다. base_buy_strategy가 있으면 합성 전략을 생성한다."""
        from cli.strategy_generator import save_strategy_to_db, generate_buy_filter_strategy
        from cli.strategy_loader import load_strategy_from_db
        from cli.paths import DB_STRATEGY

        if strategy_type == 'buy' and base_buy_strategy:
            base_loaded = load_strategy_from_db(DB_STRATEGY, base_buy_strategy, 'buy')
            if base_loaded.get('status') != 'ok':
                return {'status': 'error', 'message': 'base buy strategy load failed', 'base_result': base_loaded}
            composed = generate_buy_filter_strategy(strategy_name, base_loaded['code'], expressions)
            if composed.get('status') != 'ok':
                return composed
            saved = save_strategy_to_db(DB_STRATEGY, strategy_name, composed['code'], strategy_type)
            saved['code'] = composed['code']
            return saved
        return self.create_strategy(strategy_name, expressions, strategy_type)

    def _execute_wfo_loop(self, *, name, config_dict, analysis_result, input_path, param_space,
                          walk_forward_settings, strategy_type, buy_var, base_buy_strategy,
                          top_n, min_samples, quantiles, alpha,
                          ml_analysis_result, ml_feature_limit, ml_model_type,
                          ml_top_n, ml_n_splits, ml_random_state, ml_weight,
                          eval_criteria, promotion_preset, criteria_mode,
                          auto_relax, max_relax_steps):
        """WFO 루프를 실행하고 auto-relax 재시도를 관리한다.

        임시 전략을 DB에 저장 → WFO 실행 → 평가 → 승격/거절 판정.
        auto_relax가 True이면 zero-trade 시 top_n을 줄여 재시도한다.
        """
        current_top_n = max(int(top_n), 1)
        max_attempts = max_relax_steps + 1 if auto_relax else 1
        auto_relax_history = []
        auto_relax_failed = False

        wf_result = None
        evaluation = None
        final_strategy_result = None
        promoted = False
        temp_result = None
        feature_whitelist = None
        feature_importance_map = None
        expression_result = None
        code_result = None

        for step in range(max_attempts):
            prepared = self._prepare_strategy_candidate(
                name=name,
                analysis_result=analysis_result,
                input_path=input_path,
                top_n=current_top_n,
                strategy_type=strategy_type,
                buy_var=buy_var,
                min_samples=min_samples,
                quantiles=quantiles,
                alpha=alpha,
                ml_analysis_result=ml_analysis_result,
                ml_feature_limit=ml_feature_limit,
                ml_model_type=ml_model_type,
                ml_top_n=ml_top_n,
                ml_n_splits=ml_n_splits,
                ml_random_state=ml_random_state,
                ml_weight=ml_weight,
            )
            if prepared.get('status') != 'ok':
                return prepared

            analysis_result = prepared['analysis_result']
            ml_analysis_result = prepared.get('ml_analysis_result')
            feature_whitelist = prepared.get('feature_whitelist')
            feature_importance_map = prepared.get('feature_importance_map')
            expression_result = prepared['expression_result']
            code_result = prepared['code_result']

            temporary_name = f'__AUTO_TMP__{name}_{int(time.time() * 1000)}_{step}'
            temp_result = self._save_generated_strategy(temporary_name, expression_result['expressions'],
                                                        strategy_type, base_buy_strategy)
            if temp_result.get('status') != 'ok':
                return {'status': 'error', 'message': 'temporary strategy save failed', 'temporary_result': temp_result}

            try:
                run_config = dict(config_dict)
                if strategy_type == 'buy':
                    run_config['buy_strategy'] = temporary_name
                else:
                    run_config['sell_strategy'] = temporary_name

                wf_result = self.walk_forward(run_config, param_space or {}, **walk_forward_settings)
                evaluation = self.evaluate_walk_forward_result(
                    wf_result,
                    min_rounds=eval_criteria['min_rounds'],
                    min_success_rate=eval_criteria['min_success_rate'],
                    min_mean_oos_metric=eval_criteria['min_mean_oos_metric'],
                    min_avg_trade_count=eval_criteria['min_avg_trade_count'],
                )
                evaluation['preset'] = promotion_preset
                evaluation['criteria'] = eval_criteria
                evaluation['criteria_mode'] = criteria_mode

                summary = (evaluation.get('summary') or {}).copy()
                total_rounds = int(summary.get('round_count', 0) or 0)
                zero_trade_rounds = int(summary.get('zero_trade_rounds', 0) or 0)
                if auto_relax:
                    auto_relax_history.append({
                        'step': step, 'top_n': current_top_n,
                        'zero_trade_rounds': zero_trade_rounds, 'total_rounds': total_rounds,
                    })

                should_relax = (
                    auto_relax and
                    evaluation.get('status') == 'ok' and
                    'all_rounds_no_trades' in (evaluation.get('reasons') or []) and
                    current_top_n > 1 and
                    step < max_attempts - 1
                )
                if should_relax:
                    current_top_n = max(1, current_top_n - 1)
                    continue

                if auto_relax and evaluation.get('status') == 'ok' and \
                        'all_rounds_no_trades' in (evaluation.get('reasons') or []) and current_top_n <= 1:
                    auto_relax_failed = True

                if evaluation.get('status') == 'ok' and evaluation.get('passed'):
                    final_strategy_result = self._save_generated_strategy(name, expression_result['expressions'],
                                                                          strategy_type, base_buy_strategy)
                    promoted = final_strategy_result.get('status') == 'ok'
                else:
                    final_strategy_result = {'status': 'skipped', 'action': 'rejected'}
                break
            finally:
                self.delete_strategy(temporary_name, strategy_type)

        return {
            'analysis_result': analysis_result,
            'ml_analysis_result': ml_analysis_result,
            'feature_whitelist': feature_whitelist,
            'feature_importance_map': feature_importance_map,
            'expression_result': expression_result,
            'code_result': code_result,
            'wf_result': wf_result,
            'evaluation': evaluation,
            'final_strategy_result': final_strategy_result,
            'promoted': promoted,
            'temp_result': temp_result,
            'auto_relax_history': auto_relax_history,
            'auto_relax_failed': auto_relax_failed,
        }

    def _build_discovery_response(self, loop_result, *, name, criteria_mode, auto_relax,
                                  output_code_path, report_json_path, report_md_path):
        """WFO 루프 결과를 최종 응답 dict로 조립하고 리포트를 저장한다."""
        from cli.condition_generator import save_condition_code
        from cli.discovery_report import build_discovery_report, save_discovery_report_json, save_discovery_report_markdown

        wf_result = loop_result.get('wf_result')
        final_strategy_result = loop_result.get('final_strategy_result')
        temp_result = loop_result.get('temp_result')
        code_result = loop_result.get('code_result')

        generated_code = None
        if final_strategy_result and final_strategy_result.get('code'):
            generated_code = final_strategy_result.get('code')
        elif temp_result and temp_result.get('code'):
            generated_code = temp_result.get('code')
        elif code_result:
            generated_code = code_result.get('code')

        save_code_result = None
        if output_code_path and generated_code:
            save_code_result = save_condition_code(generated_code, output_code_path)

        response = {
            'status': 'ok' if wf_result and wf_result.get('status') == 'ok' else 'error',
            'analysis_result': loop_result.get('analysis_result'),
            'ml_analysis_result': loop_result.get('ml_analysis_result'),
            'feature_whitelist': loop_result.get('feature_whitelist'),
            'feature_importance_map': loop_result.get('feature_importance_map'),
            'expression_result': loop_result.get('expression_result'),
            'generated_code': generated_code,
            'saved_code': save_code_result,
            'temporary_strategy': temp_result,
            'walk_forward': wf_result,
            'promotion_evaluation': loop_result.get('evaluation'),
            'strategy_result': final_strategy_result,
            'promoted': loop_result.get('promoted', False),
            'criteria_mode': criteria_mode,
        }
        if auto_relax:
            response['auto_relax_history'] = loop_result.get('auto_relax_history', [])
            if loop_result.get('auto_relax_failed'):
                response['auto_relax_failed'] = True

        report = build_discovery_report(response, strategy_name=name)
        response['report'] = report
        if report_json_path:
            response['saved_report_json'] = save_discovery_report_json(report, report_json_path)
        if report_md_path:
            response['saved_report_md'] = save_discovery_report_markdown(report, report_md_path)
        return response

    def discover_and_promote_strategy(self, name: str, config_dict: dict, input_path: str = None,
                                      analysis_result: dict = None, param_space: dict = None, top_n: int = 5,
                                      strategy_type: str = 'buy', buy_var: str = '매수',
                                      min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                                      output_code_path: str = None, walk_forward_settings: dict = None,
                                      promotion_criteria: dict = None, ml_analysis_result: dict = None,
                                      ml_feature_limit: int = 0, ml_model_type: str = 'random_forest',
                                      ml_top_n: int = 10, ml_n_splits: int = 5, ml_random_state: int = 42,
                                      ml_weight: float = 0.0, promotion_preset: str = 'balanced', report_json_path: str = None,
                                      report_md_path: str = None, auto_relax: bool = False,
                                      max_relax_steps: int = 3,
                                      discovery_config=None) -> dict:
        """후보 전략을 임시 저장 후 WFO 검증을 통과한 경우에만 최종 전략으로 승격한다.

        discovery_config가 주어지면 개별 파라미터보다 우선 적용된다.
        """
        if discovery_config is not None:
            a = discovery_config.analysis
            m = discovery_config.ml
            p = discovery_config.promotion
            o = discovery_config.output
            top_n = a.top_n
            min_samples = a.min_samples
            quantiles = a.quantiles
            alpha = a.alpha
            buy_var = a.buy_var
            strategy_type = a.strategy_type
            ml_feature_limit = m.feature_limit
            ml_model_type = m.model_type
            ml_top_n = m.top_n
            ml_n_splits = m.n_splits
            ml_random_state = m.random_state
            ml_weight = m.weight
            promotion_preset = p.preset
            promotion_criteria = p.criteria
            auto_relax = p.auto_relax
            max_relax_steps = p.max_relax_steps
            output_code_path = o.code_path if output_code_path is None else output_code_path
            report_json_path = o.report_json_path if report_json_path is None else report_json_path
            report_md_path = o.report_md_path if report_md_path is None else report_md_path
        try:
            from cli.promotion import resolve_promotion_criteria

            if walk_forward_settings is None:
                return {'status': 'error', 'message': 'walk_forward_settings가 필요합니다.'}

            resolved_criteria = resolve_promotion_criteria(promotion_preset, promotion_criteria)
            eval_criteria = dict(resolved_criteria)
            criteria_mode = 'strict'
            if auto_relax and promotion_criteria is None:
                eval_criteria['min_avg_trade_count'] = 0.0
                criteria_mode = 'relaxed'
            elif promotion_criteria is not None:
                preset_original = resolve_promotion_criteria(promotion_preset)
                for key in ('min_rounds', 'min_success_rate', 'min_mean_oos_metric', 'min_avg_trade_count'):
                    if eval_criteria.get(key, preset_original.get(key)) < preset_original.get(key, 0):
                        criteria_mode = 'relaxed'
                        break
            base_buy_strategy = config_dict.get('base_buy_strategy') if strategy_type == 'buy' else None

            loop_result = self._execute_wfo_loop(
                name=name, config_dict=config_dict,
                analysis_result=analysis_result, input_path=input_path,
                param_space=param_space, walk_forward_settings=walk_forward_settings,
                strategy_type=strategy_type, buy_var=buy_var,
                base_buy_strategy=base_buy_strategy,
                top_n=top_n, min_samples=min_samples, quantiles=quantiles, alpha=alpha,
                ml_analysis_result=ml_analysis_result, ml_feature_limit=ml_feature_limit,
                ml_model_type=ml_model_type, ml_top_n=ml_top_n,
                ml_n_splits=ml_n_splits, ml_random_state=ml_random_state, ml_weight=ml_weight,
                eval_criteria=eval_criteria, promotion_preset=promotion_preset,
                criteria_mode=criteria_mode,
                auto_relax=auto_relax, max_relax_steps=max_relax_steps,
            )
            if loop_result.get('status') == 'error':
                return loop_result

            return self._build_discovery_response(
                loop_result, name=name, criteria_mode=criteria_mode, auto_relax=auto_relax,
                output_code_path=output_code_path,
                report_json_path=report_json_path, report_md_path=report_md_path,
            )
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_discovery_history(self, limit: int = 20, promoted_only: bool = False) -> dict:
        """auto-discovery 실행 히스토리를 조회한다."""
        try:
            from cli.history import get_discovery_runs, init_history_db
            init_history_db(self._history_db)
            runs = get_discovery_runs(limit, promoted_only, self._history_db)
            return {'status': 'ok', 'total': len(runs), 'runs': runs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def compare_discovery_history(self, discovery_ids: list[int]) -> dict:
        """여러 discovery run을 비교한다."""
        try:
            from cli.history import compare_discovery_runs, init_history_db
            init_history_db(self._history_db)
            result = compare_discovery_runs(discovery_ids, self._history_db)
            return {'status': 'ok', **result}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def auto_discover_batch(self, batch_path: str = None, common: dict = None,
                             runs: list = None) -> dict:
        """여러 auto-discovery 파이프라인을 배치로 순차 실행한다.

        Args:
            batch_path: 배치 설정 JSON 파일 경로.
            common: 공통 설정 dict.
            runs: 개별 실행 오버라이드 리스트.

        Returns:
            배치 결과 dict (status, total, promoted, results).
        """
        try:
            from cli.auto_discovery import run_batch
            return run_batch(batch_path=batch_path, common=common, runs=runs,
                             controller=self)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def auto_discover(self, config=None, **kwargs) -> dict:
        """DB 전략명으로 백테스트 → 분석 → WFO 검증 → 승격 전체 파이프라인을 실행한다.

        Args:
            config: AutoDiscoveryConfig 인스턴스. None이면 kwargs로 생성.
            **kwargs: AutoDiscoveryConfig 필드값.

        Returns:
            파이프라인 결과 dict (status, promoted, strategy_name, csv_path 등).
        """
        try:
            from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

            if config is None:
                config = AutoDiscoveryConfig(**kwargs)
            result = AutoDiscoveryEngine.run(config, controller=self)

            # 히스토리 DB에 저장
            try:
                from cli.history import save_discovery_run, init_history_db
                init_history_db(self._history_db)
                discovery_id = save_discovery_run(config, result, self._history_db)
                result = {**result, 'discovery_id': discovery_id}
            except Exception:
                pass

            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def run(self, config_dict: dict) -> dict:
        """백테스트를 실행하고 결과를 히스토리에 저장한다."""
        try:
            from cli.runner import run_backtest
            from cli.timeframe_detector import validate_timeframe_match

            config = BacktestConfig(**{
                k: v for k, v in config_dict.items()
                if k in {f.name for f in BacktestConfig.__dataclass_fields__.values()}
            })

            # 타임프레임 검증
            tf_check = validate_timeframe_match(config)
            if tf_check['status'] != 'ok':
                return tf_check

            # 설정 검증
            errors = validate(config)
            if errors:
                return {'status': 'error', 'message': '; '.join(errors)}

            start_time = time.time()
            result = run_backtest(config)
            duration = time.time() - start_time

            # 히스토리 저장
            try:
                from cli.history import save_run, init_history_db
                init_history_db(self._history_db)
                run_id = save_run(config, result, duration, self._history_db)
                result = {**result, 'run_id': run_id, 'duration': round(duration, 2)}
            except Exception:
                result = {**result, 'duration': round(duration, 2)}

            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def dry_run(self, config_dict: dict) -> dict:
        """설정 검증만 수행한다 (실행 없음)."""
        try:
            from cli.timeframe_detector import validate_timeframe_match

            config = BacktestConfig(**{
                k: v for k, v in config_dict.items()
                if k in {f.name for f in BacktestConfig.__dataclass_fields__.values()}
            })

            tf_check = validate_timeframe_match(config)
            if tf_check['status'] != 'ok':
                return tf_check

            errors = validate(config)
            if errors:
                return {'status': 'error', 'message': '; '.join(errors), 'errors': errors}

            return {
                'status': 'ok',
                'message': '설정 검증 통과',
                'config': asdict(config),
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def sweep(self, config_dict: dict, param_space: dict,
              on_progress=None) -> dict:
        """파라미터 스윕을 실행한다."""
        try:
            from cli.sweep import run_sweep

            config = BacktestConfig(**{
                k: v for k, v in config_dict.items()
                if k in {f.name for f in BacktestConfig.__dataclass_fields__.values()}
            })

            results = run_sweep(config, param_space, on_progress)
            return {
                'status': 'ok',
                'total': len(results),
                'results': results,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def optimize(self, config_dict: dict, param_space: dict,
                 objective: str = 'tpi', method: str = 'grid',
                 maximize: bool = True, max_iter: int = 10,
                 on_progress=None) -> dict:
        """파라미터 최적화를 실행한다."""
        try:
            from cli.optimizer import optimize as run_optimize

            config = BacktestConfig(**{
                k: v for k, v in config_dict.items()
                if k in {f.name for f in BacktestConfig.__dataclass_fields__.values()}
            })

            save_fn = None
            try:
                from cli.history import save_run, init_history_db
                init_history_db(self._history_db)
                save_fn = lambda cfg, res, dur: save_run(cfg, res, dur, self._history_db)
            except Exception:
                pass

            return run_optimize(
                config, param_space,
                objective=objective,
                method=method,
                maximize=maximize,
                max_iter=max_iter,
                save_fn=save_fn,
                on_progress=on_progress,
            )
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def walk_forward(self, config_dict: dict, param_space: dict,
                     train_window_days: int, test_window_days: int,
                     step_days: int = None, purge_days: int = 0, embargo_days: int = 0,
                     objective: str = 'tpi', method: str = 'grid',
                     maximize: bool = True, max_iter: int = 10,
                     on_progress=None, output_path: str = None) -> dict:
        """Walk-Forward Optimization을 실행한다."""
        try:
            from cli.wfo import run_walk_forward, save_walk_forward_report

            config = BacktestConfig(**{
                k: v for k, v in config_dict.items()
                if k in {f.name for f in BacktestConfig.__dataclass_fields__.values()}
            })

            result = run_walk_forward(
                config,
                param_space,
                train_window_days=train_window_days,
                test_window_days=test_window_days,
                step_days=step_days,
                purge_days=purge_days,
                embargo_days=embargo_days,
                objective=objective,
                method=method,
                maximize=maximize,
                max_iter=max_iter,
                on_progress=on_progress,
            )
            if output_path and result.get('status') == 'ok':
                result['saved'] = save_walk_forward_report(result, output_path)
            return result
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def create_strategy(self, name: str, conditions: list,
                        strategy_type: str = 'buy') -> dict:
        """전략 코드를 생성하고 DB에 저장한다."""
        try:
            from cli.strategy_generator import create_and_save
            from cli.paths import DB_STRATEGY

            return create_and_save(DB_STRATEGY, name, conditions, strategy_type)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_strategy(self, name: str, strategy_type: str = 'buy') -> dict:
        """전략을 DB에서 삭제한다."""
        try:
            from cli.strategy_generator import delete_strategy_from_db
            from cli.paths import DB_STRATEGY

            return delete_strategy_from_db(DB_STRATEGY, name, strategy_type)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_history(self, limit: int = 20, strategy: str = None,
                    status: str = None) -> dict:
        """실행 히스토리를 조회한다."""
        try:
            from cli.history import get_runs, init_history_db
            init_history_db(self._history_db)

            runs = get_runs(limit, strategy, status, self._history_db)
            return {'status': 'ok', 'total': len(runs), 'runs': runs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_best(self, metric: str = 'tpi', order: str = 'desc',
                 limit: int = 1) -> dict:
        """특정 지표 기준 최고 성능 런을 조회한다."""
        try:
            from cli.history import get_best_run, init_history_db
            init_history_db(self._history_db)

            runs = get_best_run(metric, order, limit, self._history_db)
            return {'status': 'ok', 'total': len(runs), 'runs': runs}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def compare(self, run_ids: list) -> dict:
        """실행 결과를 비교한다."""
        try:
            from cli.history import compare_runs, init_history_db
            init_history_db(self._history_db)

            return compare_runs(run_ids, self._history_db)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def system_info(self) -> dict:
        """시스템 정보와 추천 엔진 수를 반환한다."""
        try:
            info = get_system_info()
            recommended = recommend_engine_count()
            return {
                'status': 'ok',
                'system': info,
                'recommended_engines': recommended,
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
