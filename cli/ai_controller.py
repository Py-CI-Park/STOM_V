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

    def generate_conditions(self, analysis_result: dict = None, input_path: str = None,
                            top_n: int = 5, buy_var: str = '매수', output_path: str = None,
                            min_samples: int = 30, quantiles: int = 10, alpha: float = 0.05) -> dict:
        """분석 결과 또는 CSV 입력으로부터 자동 필터 조건 코드를 생성한다."""
        try:
            from cli.analyzer import analyze_result_csv
            from cli.condition_generator import generate_conditions_from_analysis, save_condition_code

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

            result = generate_conditions_from_analysis(
                analysis_result,
                top_n=top_n,
                buy_var=buy_var,
            )
            if output_path and result.get('status') == 'ok':
                save_result = save_condition_code(result['code'], output_path)
                result['saved'] = save_result
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
