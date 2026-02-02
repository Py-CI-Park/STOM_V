"""
Headless Backtest Runner
========================

PyQt5 없이 백테스트 엔진을 실행하는 헤드리스 러너.
"""

import sys
import time
from typing import Optional, Dict, Any
from multiprocessing import Process, Queue
from traceback import print_exc

from cli.adapters.settings_adapter import load_settings_without_qt, get_database_paths
from cli.adapters.queue_adapter import CLIQueueAdapter
from cli.adapters.output_adapter import OutputAdapter
from utility.static import get_logger

logger = get_logger('HeadlessBacktestRunner')


class HeadlessBacktestRunner:
    """
    PyQt5 없이 백테스트 엔진을 실행하는 클래스

    CLI 환경에서 백테스트를 실행할 수 있도록 합니다.
    """

    def __init__(self):
        """초기화"""
        self.dict_set: Optional[Dict[str, Any]] = None
        self.process: Optional[Process] = None
        self.queue_adapter = CLIQueueAdapter()
        self.output_adapter = OutputAdapter()

    def load_settings(self) -> bool:
        """설정 로드"""
        try:
            logger.info("Loading settings without Qt...")
            self.dict_set = load_settings_without_qt()
            logger.info("Settings loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            print_exc()
            return False

    def start_backtest(self,
                      backtest_type: str,
                      strategy_name: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      **kwargs) -> bool:
        """
        백테스트 시작

        Args:
            backtest_type: 백테스트 타입 ('stock', 'coin', 'future')
            strategy_name: 전략명 (None이면 현재 설정된 전략 사용)
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)
            **kwargs: 추가 파라미터

        Returns:
            성공 여부
        """
        if not self.dict_set:
            if not self.load_settings():
                return False

        try:
            logger.info(f"Starting {backtest_type} backtest...")

            # 백테스트 타입별 엔진 선택
            if backtest_type == 'stock':
                from backtester.backtest_stocks import BacktestStock
                engine_class = BacktestStock
            elif backtest_type == 'coin':
                from backtester.backtest_coin import BacktestCoin
                engine_class = BacktestCoin
            elif backtest_type == 'future':
                logger.error("Future backtest not implemented yet")
                return False
            else:
                logger.error(f"Unknown backtest type: {backtest_type}")
                return False

            # 프로세스 생성 및 실행
            self.process = Process(
                target=self._run_backtest_process,
                args=(engine_class, self.dict_set, strategy_name, start_date, end_date, kwargs)
            )
            self.process.start()

            # 프로세스 완료 대기
            self.process.join()

            if self.process.exitcode == 0:
                logger.info("Backtest completed successfully")
                return True
            else:
                logger.error(f"Backtest failed with exit code: {self.process.exitcode}")
                return False

        except Exception as e:
            logger.error(f"Failed to start backtest: {e}")
            print_exc()
            return False

    def _run_backtest_process(self,
                             engine_class,
                             dict_set: Dict[str, Any],
                             strategy_name: Optional[str],
                             start_date: Optional[str],
                             end_date: Optional[str],
                             kwargs: Dict[str, Any]):
        """
        백테스트 프로세스 실행 (프로세스 내부에서 실행됨)

        Args:
            engine_class: 백테스트 엔진 클래스
            dict_set: 설정 딕셔너리
            strategy_name: 전략명
            start_date: 시작일
            end_date: 종료일
            kwargs: 추가 파라미터
        """
        try:
            # 큐 생성
            query_queue = Queue()
            result_queue = Queue()

            # 엔진 초기화
            logger.info(f"Initializing {engine_class.__name__}...")
            engine = engine_class(
                query_queue=query_queue,
                result_queue=result_queue,
                dict_set=dict_set
            )

            # 전략명 설정
            if strategy_name:
                if hasattr(engine, 'strategy_name'):
                    engine.strategy_name = strategy_name

            # 날짜 범위 설정
            if start_date and hasattr(engine, 'start_date'):
                engine.start_date = start_date
            if end_date and hasattr(engine, 'end_date'):
                engine.end_date = end_date

            # 추가 파라미터 적용
            for key, value in kwargs.items():
                if hasattr(engine, key):
                    setattr(engine, key, value)

            # 엔진 시작
            logger.info("Starting backtest engine...")
            engine.start()

            # 결과 대기 및 출력
            timeout = kwargs.get('timeout', 3600)  # 기본 1시간 타임아웃
            start_time = time.time()

            while True:
                if not result_queue.empty():
                    result = result_queue.get()
                    self.output_adapter.output(result, title="Backtest Result")

                if not engine.is_alive():
                    logger.info("Engine process terminated")
                    break

                if time.time() - start_time > timeout:
                    logger.warning("Backtest timeout reached")
                    engine.terminate()
                    break

                time.sleep(0.1)

            # 종료 대기
            engine.join(timeout=10)
            if engine.is_alive():
                logger.warning("Forcing engine termination")
                engine.terminate()
                engine.join()

            logger.info("Backtest process completed")
            sys.exit(0)

        except Exception as e:
            logger.error(f"Error in backtest process: {e}")
            print_exc()
            sys.exit(1)

    def stop(self):
        """백테스트 중지"""
        if self.process and self.process.is_alive():
            logger.info("Stopping backtest...")
            self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                logger.warning("Force killing backtest process")
                self.process.kill()
                self.process.join()
            logger.info("Backtest stopped")
