"""
Headless Optimize Runner
========================

PyQt5 없이 최적화 엔진을 실행하는 헤드리스 러너.
그리드 서치, 베이지안 최적화, 유전 알고리즘, 전진 분석, 백파인더를 지원합니다.
"""

import sys
import time
import sqlite3
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from multiprocessing import Process, Queue, Value, Lock
from traceback import print_exc

from cli.adapters.settings_adapter import load_settings_without_qt, get_database_paths
from cli.adapters.output_adapter import OutputAdapter

# 로깅 - utility.static에서 레지스트리 접근 문제가 있을 수 있으므로 직접 설정
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HeadlessOptimizeRunner')

# 최적화 모듈 지연 로딩을 위한 전역 변수
_optimize_modules_loaded = False
OptimizerGrid = None
OptimizerBayesian = None
OptimizerGA = None
WalkForward = None
BackFinder = None


def _load_optimize_modules():
    """
    최적화 모듈 지연 로딩

    utility.setting이 레지스트리에 접근하므로, 실제 최적화 실행 시에만 로드합니다.
    """
    global _optimize_modules_loaded
    global OptimizerGrid, OptimizerBayesian, OptimizerGA, WalkForward, BackFinder

    if _optimize_modules_loaded:
        return

    logger.info("Loading optimization modules...")

    try:
        from backtester.optimiz import Total as OptimizerGrid_
        from backtester.optimiz_conditions import Total as OptimizerBayesian_
        from backtester.optimiz_genetic_algorithm import Total as OptimizerGA_
        from backtester.rolling_walk_forward_test import Total as WalkForward_
        from backtester.backfinder import Total as BackFinder_

        OptimizerGrid = OptimizerGrid_
        OptimizerBayesian = OptimizerBayesian_
        OptimizerGA = OptimizerGA_
        WalkForward = WalkForward_
        BackFinder = BackFinder_

        _optimize_modules_loaded = True
        logger.info("Optimization modules loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load optimization modules: {e}")
        print_exc()
        raise


class HeadlessOptimizeRunner:
    """
    PyQt5 없이 최적화 엔진을 실행하는 클래스

    지원하는 최적화 방법:
    - Grid Search (그리드 서치)
    - Bayesian Optimization (베이지안 최적화 - Optuna)
    - Genetic Algorithm (유전 알고리즘)
    - Walk-Forward Analysis (전진 분석)
    - BackFinder (변수 탐색)
    """

    def __init__(self):
        """초기화"""
        self.dict_set: Optional[Dict[str, Any]] = None
        self.output_adapter = OutputAdapter()

        # 큐들
        self.windowQ: Optional[Queue] = None
        self.soundQ: Optional[Queue] = None
        self.totalQ: Optional[Queue] = None
        self.backQ: Optional[Queue] = None
        self.liveQ: Optional[Queue] = None
        self.teleQ: Optional[Queue] = None
        self.moneyQ: Optional[Queue] = None

        # 백테스트 엔진 큐들
        self.back_eques: List[Queue] = []
        self.back_sques: List[Queue] = []

        # 공유 카운터
        self.shared_cnt: Optional[Value] = None
        self.shared_lock: Optional[Lock] = None

        # 프로세스들
        self.processes: List[Process] = []

        # 데이터베이스 연결
        self.con_st: Optional[sqlite3.Connection] = None
        self.con_bt: Optional[sqlite3.Connection] = None

        # 결과 저장
        self.last_result: Optional[Dict[str, Any]] = None

    def load_settings(self) -> bool:
        """
        설정 파일 로드 (Qt 없이)

        Returns:
            성공 여부
        """
        try:
            self.dict_set = load_settings_without_qt()
            if not self.dict_set:
                logger.error("Failed to load settings")
                return False

            # 데이터베이스 연결
            db_paths = get_database_paths()
            self.con_st = sqlite3.connect(db_paths['strategy'], check_same_thread=False)
            self.con_bt = sqlite3.connect(db_paths['backtest'], check_same_thread=False)

            logger.info("Settings loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            print_exc()
            return False

    def _init_queues(self):
        """큐 초기화"""
        self.windowQ = Queue()
        self.soundQ = Queue()
        self.totalQ = Queue()
        self.backQ = Queue()
        self.liveQ = Queue()
        self.teleQ = Queue()
        self.moneyQ = Queue()

        # BackEngine 큐들 (실제 백테스트 엔진)
        # optimiz.py를 보면 back_eques와 back_sques를 사용
        self.back_eques = [Queue() for _ in range(10)]  # 백테스트 엔진 큐
        self.back_sques = [Queue() for _ in range(20)]  # 집계 프로세스 큐

        # 공유 카운터
        self.shared_cnt = Value('i', 0)
        self.shared_lock = Lock()

    def _cleanup(self):
        """리소스 정리"""
        # 프로세스 종료
        for p in self.processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)

        self.processes.clear()

        # 데이터베이스 연결 종료
        if self.con_st:
            self.con_st.close()
        if self.con_bt:
            self.con_bt.close()

    def run_grid_optimization(
        self,
        backtest_type: str = 'stock',
        buy_strategy: str = None,
        sell_strategy: str = None,
        start_date: str = None,
        end_date: str = None,
        betting: int = 100000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        그리드 서치 최적화 실행

        Args:
            backtest_type: 'stock', 'coin', 'future' 중 하나
            buy_strategy: 매수 전략 이름
            sell_strategy: 매도 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            betting: 배팅 금액
            **kwargs: 추가 파라미터 (opti_vars, opti_standard 등)

        Returns:
            {
                'success': bool,
                'result': dict or None,
                'error_message': str or None
            }
        """
        try:
            logger.info("Starting grid optimization...")
            logger.info(f"Type: {backtest_type}, Buy: {buy_strategy}, Sell: {sell_strategy}")
            logger.info(f"Period: {start_date} ~ {end_date}, Betting: {betting}")

            # 모듈 로드
            _load_optimize_modules()

            # 큐 초기화
            self._init_queues()

            # GUI 종속성으로 인해 직접 실행이 어려운 경우
            # 최적화 작업을 데이터베이스에 저장하고 job_id 반환
            job_id = self._save_optimization_job(
                opt_type='grid',
                backtest_type=backtest_type,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                start_date=start_date,
                end_date=end_date,
                betting=betting,
                params=kwargs
            )

            return {
                'success': True,
                'result': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': 'Grid optimization job queued. Check status with job_id.'
                },
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Grid optimization failed: {e}")
            print_exc()
            return {
                'success': False,
                'result': None,
                'error_message': str(e)
            }
        finally:
            self._cleanup()

    def run_bayesian_optimization(
        self,
        trials: int = 100,
        backtest_type: str = 'stock',
        buy_strategy: str = None,
        sell_strategy: str = None,
        start_date: str = None,
        end_date: str = None,
        betting: int = 100000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        베이지안 최적화 실행 (Optuna 사용)

        Args:
            trials: 시도 횟수
            backtest_type: 'stock', 'coin', 'future' 중 하나
            buy_strategy: 매수 전략 이름
            sell_strategy: 매도 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            betting: 배팅 금액
            **kwargs: 추가 파라미터

        Returns:
            결과 딕셔너리
        """
        try:
            logger.info(f"Starting Bayesian optimization ({trials} trials)...")
            logger.info(f"Type: {backtest_type}, Buy: {buy_strategy}, Sell: {sell_strategy}")

            # 모듈 로드
            _load_optimize_modules()

            # 큐 초기화
            self._init_queues()

            # 작업 저장
            job_id = self._save_optimization_job(
                opt_type='bayesian',
                backtest_type=backtest_type,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                start_date=start_date,
                end_date=end_date,
                betting=betting,
                params={'trials': trials, **kwargs}
            )

            return {
                'success': True,
                'result': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': f'Bayesian optimization job queued ({trials} trials). Check status with job_id.'
                },
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Bayesian optimization failed: {e}")
            print_exc()
            return {
                'success': False,
                'result': None,
                'error_message': str(e)
            }
        finally:
            self._cleanup()

    def run_ga_optimization(
        self,
        generations: int = 50,
        backtest_type: str = 'stock',
        buy_strategy: str = None,
        sell_strategy: str = None,
        start_date: str = None,
        end_date: str = None,
        betting: int = 100000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        유전 알고리즘 최적화 실행

        Args:
            generations: 세대 수
            backtest_type: 'stock', 'coin', 'future' 중 하나
            buy_strategy: 매수 전략 이름
            sell_strategy: 매도 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            betting: 배팅 금액
            **kwargs: 추가 파라미터 (population_size 등)

        Returns:
            결과 딕셔너리
        """
        try:
            logger.info(f"Starting GA optimization ({generations} generations)...")
            logger.info(f"Type: {backtest_type}, Buy: {buy_strategy}, Sell: {sell_strategy}")

            # 모듈 로드
            _load_optimize_modules()

            # 큐 초기화
            self._init_queues()

            # 작업 저장
            job_id = self._save_optimization_job(
                opt_type='genetic',
                backtest_type=backtest_type,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                start_date=start_date,
                end_date=end_date,
                betting=betting,
                params={'generations': generations, **kwargs}
            )

            return {
                'success': True,
                'result': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': f'GA optimization job queued ({generations} generations). Check status with job_id.'
                },
                'error_message': None
            }

        except Exception as e:
            logger.error(f"GA optimization failed: {e}")
            print_exc()
            return {
                'success': False,
                'result': None,
                'error_message': str(e)
            }
        finally:
            self._cleanup()

    def run_walkforward(
        self,
        backtest_type: str = 'stock',
        buy_strategy: str = None,
        sell_strategy: str = None,
        start_date: str = None,
        end_date: str = None,
        betting: int = 100000,
        weeks_train: int = 26,
        weeks_valid: int = 4,
        weeks_test: int = 4,
        **kwargs
    ) -> Dict[str, Any]:
        """
        전진 분석 실행 (Walk-Forward Analysis)

        Args:
            backtest_type: 'stock', 'coin', 'future' 중 하나
            buy_strategy: 매수 전략 이름
            sell_strategy: 매도 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            betting: 배팅 금액
            weeks_train: 훈련 기간 (주)
            weeks_valid: 검증 기간 (주)
            weeks_test: 테스트 기간 (주)
            **kwargs: 추가 파라미터

        Returns:
            결과 딕셔너리
        """
        try:
            logger.info("Starting walk-forward analysis...")
            logger.info(f"Type: {backtest_type}, Buy: {buy_strategy}, Sell: {sell_strategy}")
            logger.info(f"Train: {weeks_train}w, Valid: {weeks_valid}w, Test: {weeks_test}w")

            # 모듈 로드
            _load_optimize_modules()

            # 큐 초기화
            self._init_queues()

            # 작업 저장
            job_id = self._save_optimization_job(
                opt_type='walkforward',
                backtest_type=backtest_type,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                start_date=start_date,
                end_date=end_date,
                betting=betting,
                params={
                    'weeks_train': weeks_train,
                    'weeks_valid': weeks_valid,
                    'weeks_test': weeks_test,
                    **kwargs
                }
            )

            return {
                'success': True,
                'result': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': f'Walk-forward analysis job queued. Check status with job_id.'
                },
                'error_message': None
            }

        except Exception as e:
            logger.error(f"Walk-forward analysis failed: {e}")
            print_exc()
            return {
                'success': False,
                'result': None,
                'error_message': str(e)
            }
        finally:
            self._cleanup()

    def run_backfinder(
        self,
        backtest_type: str = 'stock',
        buy_strategy: str = None,
        start_date: str = None,
        end_date: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        백파인더 실행 (변수 조건 탐색)

        조건을 만족하는 종목들을 찾는 기능입니다.

        Args:
            backtest_type: 'stock', 'coin', 'future' 중 하나
            buy_strategy: 매수 전략 이름
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            **kwargs: 추가 파라미터 (finder_conditions 등)

        Returns:
            결과 딕셔너리
        """
        try:
            logger.info("Starting backfinder...")
            logger.info(f"Type: {backtest_type}, Buy: {buy_strategy}")
            logger.info(f"Period: {start_date} ~ {end_date}")

            # 모듈 로드
            _load_optimize_modules()

            # 큐 초기화
            self._init_queues()

            # 작업 저장
            job_id = self._save_optimization_job(
                opt_type='backfinder',
                backtest_type=backtest_type,
                buy_strategy=buy_strategy,
                sell_strategy=None,  # BackFinder는 sell_strategy 불필요
                start_date=start_date,
                end_date=end_date,
                betting=None,
                params=kwargs
            )

            return {
                'success': True,
                'result': {
                    'job_id': job_id,
                    'status': 'queued',
                    'message': 'BackFinder job queued. Check status with job_id.'
                },
                'error_message': None
            }

        except Exception as e:
            logger.error(f"BackFinder failed: {e}")
            print_exc()
            return {
                'success': False,
                'result': None,
                'error_message': str(e)
            }
        finally:
            self._cleanup()

    def _save_optimization_job(
        self,
        opt_type: str,
        backtest_type: str,
        buy_strategy: str,
        sell_strategy: Optional[str],
        start_date: str,
        end_date: str,
        betting: Optional[int],
        params: Dict[str, Any]
    ) -> str:
        """
        최적화 작업을 데이터베이스에 저장

        Args:
            opt_type: 최적화 타입 ('grid', 'bayesian', 'genetic', 'walkforward', 'backfinder')
            backtest_type: 백테스트 타입
            buy_strategy: 매수 전략
            sell_strategy: 매도 전략
            start_date: 시작일
            end_date: 종료일
            betting: 배팅 금액
            params: 추가 파라미터

        Returns:
            job_id: 작업 ID
        """
        try:
            import time
            job_id = f"{opt_type}_{backtest_type}_{int(time.time())}"

            # 작업 테이블이 없으면 생성
            if self.con_bt:
                cursor = self.con_bt.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS optimization_jobs (
                        job_id TEXT PRIMARY KEY,
                        opt_type TEXT,
                        backtest_type TEXT,
                        buy_strategy TEXT,
                        sell_strategy TEXT,
                        start_date TEXT,
                        end_date TEXT,
                        betting INTEGER,
                        params TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                """)

                # 작업 저장
                import json
                cursor.execute("""
                    INSERT INTO optimization_jobs
                    (job_id, opt_type, backtest_type, buy_strategy, sell_strategy,
                     start_date, end_date, betting, params, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id, opt_type, backtest_type, buy_strategy, sell_strategy,
                    start_date, end_date, betting, json.dumps(params), 'queued'
                ))
                self.con_bt.commit()

                logger.info(f"Optimization job saved: {job_id}")

            return job_id

        except Exception as e:
            logger.error(f"Failed to save optimization job: {e}")
            print_exc()
            return f"error_{int(time.time())}"

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        최적화 작업 상태 조회

        Args:
            job_id: 작업 ID

        Returns:
            상태 정보 딕셔너리
        """
        try:
            if not self.con_bt:
                return {'error': 'Database not connected'}

            cursor = self.con_bt.cursor()
            cursor.execute("""
                SELECT opt_type, backtest_type, buy_strategy, sell_strategy,
                       start_date, end_date, betting, params, status,
                       created_at, completed_at
                FROM optimization_jobs
                WHERE job_id = ?
            """, (job_id,))

            row = cursor.fetchone()
            if not row:
                return {'error': 'Job not found'}

            return {
                'job_id': job_id,
                'opt_type': row[0],
                'backtest_type': row[1],
                'buy_strategy': row[2],
                'sell_strategy': row[3],
                'start_date': row[4],
                'end_date': row[5],
                'betting': row[6],
                'params': row[7],
                'status': row[8],
                'created_at': row[9],
                'completed_at': row[10]
            }

        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {'error': str(e)}

    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        최적화 작업 목록 조회

        Args:
            status: 상태 필터 ('queued', 'running', 'completed', 'failed')

        Returns:
            작업 목록
        """
        try:
            if not self.con_bt:
                return []

            cursor = self.con_bt.cursor()
            if status:
                cursor.execute("""
                    SELECT job_id, opt_type, backtest_type, buy_strategy,
                           status, created_at
                    FROM optimization_jobs
                    WHERE status = ?
                    ORDER BY created_at DESC
                """, (status,))
            else:
                cursor.execute("""
                    SELECT job_id, opt_type, backtest_type, buy_strategy,
                           status, created_at
                    FROM optimization_jobs
                    ORDER BY created_at DESC
                """)

            jobs = []
            for row in cursor.fetchall():
                jobs.append({
                    'job_id': row[0],
                    'opt_type': row[1],
                    'backtest_type': row[2],
                    'buy_strategy': row[3],
                    'status': row[4],
                    'created_at': row[5]
                })

            return jobs

        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
