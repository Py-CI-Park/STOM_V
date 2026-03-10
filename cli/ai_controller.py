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
            from utility.setting import DB_STRATEGY

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
                                    ml_n_splits: int = 5, ml_random_state: int = 42) -> dict:
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

        expression_result = generate_condition_expressions_from_analysis(
            analysis_result,
            top_n=top_n,
            feature_whitelist=feature_whitelist,
        )
        code_result = generate_conditions_from_analysis(
            analysis_result,
            top_n=top_n,
            buy_var=buy_var,
            feature_whitelist=feature_whitelist,
        )
        return {
            'status': 'ok',
            'analysis_result': analysis_result,
            'ml_analysis_result': ml_analysis_result,
            'feature_whitelist': feature_whitelist,
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
                            ml_n_splits: int = 5, ml_random_state: int = 42) -> dict:
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
            )
            if prepared.get('status') != 'ok':
                return prepared

            result = {
                'status': 'ok',
                'analysis_result': prepared['analysis_result'],
                'ml_analysis_result': prepared.get('ml_analysis_result'),
                'feature_whitelist': prepared.get('feature_whitelist'),
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
                                      ml_top_n: int = 10, ml_n_splits: int = 5, ml_random_state: int = 42) -> dict:
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
        for round_result in rounds:
            metrics = (round_result.get('test_result') or {}).get('metrics') or {}
            trade_count = metrics.get('trade_count')
            if trade_count is not None:
                trade_counts.append(float(trade_count))
        avg_trade_count = (sum(trade_counts) / len(trade_counts)) if trade_counts else None
        if min_avg_trade_count > 0 and (avg_trade_count is None or avg_trade_count < min_avg_trade_count):
            reasons.append(f'avg_trade_count<{min_avg_trade_count}')

        return {
            'status': 'ok',
            'passed': len(reasons) == 0,
            'reasons': reasons,
            'summary': {
                'round_count': round_count,
                'success_rate': success_rate,
                'mean_oos_metric': mean_oos_metric,
                'avg_trade_count': avg_trade_count,
            },
        }

    def discover_strategy(self, name: str, config_dict: dict, input_path: str = None, analysis_result: dict = None,
                          param_space: dict = None, top_n: int = 5, strategy_type: str = 'buy',
                          buy_var: str = '매수', min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                          output_code_path: str = None, walk_forward_settings: dict = None,
                          ml_analysis_result: dict = None, ml_feature_limit: int = 0,
                          ml_model_type: str = 'random_forest', ml_top_n: int = 10,
                          ml_n_splits: int = 5, ml_random_state: int = 42) -> dict:
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

    def discover_and_promote_strategy(self, name: str, config_dict: dict, input_path: str = None,
                                      analysis_result: dict = None, param_space: dict = None, top_n: int = 5,
                                      strategy_type: str = 'buy', buy_var: str = '매수',
                                      min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05,
                                      output_code_path: str = None, walk_forward_settings: dict = None,
                                      promotion_criteria: dict = None, ml_analysis_result: dict = None,
                                      ml_feature_limit: int = 0, ml_model_type: str = 'random_forest',
                                      ml_top_n: int = 10, ml_n_splits: int = 5, ml_random_state: int = 42) -> dict:
        """후보 전략을 임시 저장 후 WFO 검증을 통과한 경우에만 최종 전략으로 승격한다."""
        try:
            from cli.condition_generator import save_condition_code

            if walk_forward_settings is None:
                return {'status': 'error', 'message': 'walk_forward_settings가 필요합니다.'}

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
            )
            if prepared.get('status') != 'ok':
                return prepared

            analysis_result = prepared['analysis_result']
            ml_analysis_result = prepared.get('ml_analysis_result')
            feature_whitelist = prepared.get('feature_whitelist')
            expression_result = prepared['expression_result']
            code_result = prepared['code_result']

            temporary_name = f'__AUTO_TMP__{name}_{int(time.time() * 1000)}'
            temp_result = self.create_strategy(temporary_name, expression_result['expressions'], strategy_type)
            if temp_result.get('status') != 'ok':
                return {'status': 'error', 'message': 'temporary strategy save failed', 'temporary_result': temp_result}

            save_code_result = None
            if output_code_path and code_result.get('status') == 'ok':
                save_code_result = save_condition_code(code_result['code'], output_code_path)

            wf_result = None
            evaluation = None
            final_strategy_result = None
            promoted = False

            try:
                run_config = dict(config_dict)
                if strategy_type == 'buy':
                    run_config['buy_strategy'] = temporary_name
                else:
                    run_config['sell_strategy'] = temporary_name

                wf_result = self.walk_forward(
                    run_config,
                    param_space or {},
                    **walk_forward_settings,
                )
                evaluation = self.evaluate_walk_forward_result(
                    wf_result,
                    **(promotion_criteria or {})
                )
                if evaluation.get('status') == 'ok' and evaluation.get('passed'):
                    final_strategy_result = self.create_strategy(name, expression_result['expressions'], strategy_type)
                    promoted = final_strategy_result.get('status') == 'ok'
                else:
                    final_strategy_result = {'status': 'skipped', 'action': 'rejected'}
            finally:
                self.delete_strategy(temporary_name, strategy_type)

            return {
                'status': 'ok' if wf_result and wf_result.get('status') == 'ok' else 'error',
                'analysis_result': analysis_result,
                'ml_analysis_result': ml_analysis_result,
                'feature_whitelist': feature_whitelist,
                'expression_result': expression_result,
                'generated_code': code_result.get('code'),
                'saved_code': save_code_result,
                'temporary_strategy': temp_result,
                'walk_forward': wf_result,
                'promotion_evaluation': evaluation,
                'strategy_result': final_strategy_result,
                'promoted': promoted,
            }
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
            from utility.setting import DB_STRATEGY

            return create_and_save(DB_STRATEGY, name, conditions, strategy_type)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def delete_strategy(self, name: str, strategy_type: str = 'buy') -> dict:
        """전략을 DB에서 삭제한다."""
        try:
            from cli.strategy_generator import delete_strategy_from_db
            from utility.setting import DB_STRATEGY

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
