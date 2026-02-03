"""
Headless Trade Runner
=====================

PyQt5 없이 실시간 트레이딩을 실행하는 헤드리스 러너.
실제 Trade 아키텍처와 동일한 구조를 사용합니다.
"""

import sys
import time
import sqlite3
import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime
from traceback import print_exc

from cli.adapters.settings_adapter import load_settings_without_qt

# 로깅 - utility.static에서 레지스트리 접근 문제가 있을 수 있으므로 직접 설정
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('HeadlessTradeRunner')

# 데이터베이스 경로 상수 (utility.setting 대신 직접 정의)
DB_TRADELIST = './_database/tradelist.db'
DB_STOCK_BACK = './_database/stock_tick_back.db'
DB_COIN_BACK = './_database/coin_tick_back.db'


class HeadlessTradeRunner:
    """
    PyQt5 없이 실시간 트레이딩을 실행하는 클래스

    현재는 거래 상태 모니터링, 포지션 조회, 주문 관리 등의 기능을 제공합니다.
    실제 거래 시작/중지는 브로커 연결이 필요하므로 플레이스홀더로 구현되어 있습니다.
    """

    def __init__(self):
        """초기화"""
        self.dict_set: Optional[Dict[str, Any]] = None
        self.trading_active: Dict[str, bool] = {
            'stock': False,
            'coin': False,
            'future': False
        }
        self.start_times: Dict[str, Optional[float]] = {
            'stock': None,
            'coin': None,
            'future': None
        }

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

    def start_trading(self, trade_type: str, **kwargs) -> bool:
        """
        트레이딩 시작

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')
            **kwargs: 추가 파라미터
                - buy_strategy: 매수 전략명
                - sell_strategy: 매도 전략명
                - betting: 배팅금액
                - 기타 전략별 파라미터

        Returns:
            성공 여부

        Note:
            현재는 플레이스홀더 구현입니다.
            실제 거래 시작은 브로커 연결(Kiwoom API, Upbit API 등)이 필요합니다.
        """
        if not self.dict_set:
            if not self.load_settings():
                return False

        try:
            # 타입 검증
            if trade_type not in ['stock', 'coin', 'future']:
                logger.error(f"Unknown trade type: {trade_type}")
                return False

            # 이미 실행 중인지 확인
            if self.trading_active[trade_type]:
                logger.warning(f"{trade_type} trading is already active")
                return False

            # 플레이스홀더 구현
            logger.info(f"Starting {trade_type} trading...")
            logger.info(f"Parameters: {kwargs}")

            # TODO: 실제 브로커 연결 및 트레이딩 프로세스 시작
            # - Kiwoom API 연결 (주식)
            # - Upbit/Binance API 연결 (코인)
            # - 전략 로딩 및 실행
            # - 주문 관리 프로세스 시작

            logger.warning("Trading start is a placeholder - broker connection not implemented")
            logger.info(f"Would start {trade_type} trading with:")
            logger.info(f"  - Buy strategy: {kwargs.get('buy_strategy', 'N/A')}")
            logger.info(f"  - Sell strategy: {kwargs.get('sell_strategy', 'N/A')}")
            logger.info(f"  - Betting: {kwargs.get('betting', 'N/A')}")

            # 상태 업데이트
            self.trading_active[trade_type] = True
            self.start_times[trade_type] = time.time()

            return True

        except Exception as e:
            logger.error(f"Failed to start trading: {e}")
            print_exc()
            return False

    def stop_trading(self, trade_type: str = None) -> bool:
        """
        트레이딩 중지

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')
                       None이면 모든 거래 중지

        Returns:
            성공 여부
        """
        try:
            if trade_type:
                types_to_stop = [trade_type]
            else:
                types_to_stop = ['stock', 'coin', 'future']

            stopped_any = False
            for ttype in types_to_stop:
                if self.trading_active[ttype]:
                    logger.info(f"Stopping {ttype} trading...")

                    # TODO: 실제 트레이딩 프로세스 중지
                    # - 진행 중인 주문 취소
                    # - 포지션 정리 (선택적)
                    # - API 연결 종료

                    logger.warning("Trading stop is a placeholder - broker disconnection not implemented")

                    self.trading_active[ttype] = False
                    self.start_times[ttype] = None
                    stopped_any = True

            if not stopped_any:
                logger.info("No active trading to stop")

            return True

        except Exception as e:
            logger.error(f"Failed to stop trading: {e}")
            print_exc()
            return False

    def get_status(self) -> dict:
        """
        현재 트레이딩 상태 조회

        Returns:
            상태 정보 딕셔너리
        """
        try:
            status = {}

            for trade_type in ['stock', 'coin', 'future']:
                if self.trading_active[trade_type]:
                    elapsed = time.time() - self.start_times[trade_type]
                    hours, remainder = divmod(int(elapsed), 3600)
                    minutes, seconds = divmod(remainder, 60)

                    status[trade_type] = {
                        'active': True,
                        'start_time': datetime.fromtimestamp(self.start_times[trade_type]).strftime('%Y-%m-%d %H:%M:%S'),
                        'elapsed': f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                        'elapsed_seconds': int(elapsed)
                    }
                else:
                    status[trade_type] = {
                        'active': False,
                        'start_time': None,
                        'elapsed': None,
                        'elapsed_seconds': 0
                    }

            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            print_exc()
            return {}

    def get_positions(self, trade_type: str) -> pd.DataFrame:
        """
        현재 포지션 조회

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')

        Returns:
            포지션 DataFrame
        """
        try:
            # 타입별 테이블명 매핑
            table_map = {
                'stock': 'chegeollist',
                'coin': 'chegeollist',
                'future': 'chegeollist'
            }

            table = table_map.get(trade_type)
            if not table:
                logger.error(f"Unknown trade type: {trade_type}")
                return pd.DataFrame()

            # tradelist.db에서 체결 내역 조회
            con = sqlite3.connect(DB_TRADELIST)

            # 테이블 존재 확인
            cursor = con.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                logger.info(f"Table '{table}' does not exist in tradelist.db")
                con.close()
                return pd.DataFrame()

            # 포지션 조회 (미청산 포지션만)
            query = f"""
                SELECT
                    종목코드,
                    종목명,
                    SUM(수량) as 보유수량,
                    AVG(체결가) as 평균단가,
                    SUM(수량 * 체결가) as 매수금액,
                    체결시간
                FROM {table}
                WHERE 주문구분 LIKE '%매수%'
                GROUP BY 종목코드
                HAVING SUM(수량) > 0
                ORDER BY 체결시간 DESC
            """

            df = pd.read_sql(query, con)
            con.close()

            if df.empty:
                logger.info(f"No active positions for {trade_type}")
            else:
                logger.info(f"Found {len(df)} active positions for {trade_type}")

            return df

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            print_exc()
            return pd.DataFrame()

    def close_position(self, trade_type: str, code: str = None, close_all: bool = False) -> bool:
        """
        포지션 청산

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')
            code: 종목코드 (특정 종목만 청산할 경우)
            close_all: 전체 청산 여부

        Returns:
            성공 여부

        Note:
            현재는 플레이스홀더 구현입니다.
            실제 청산은 브로커 API를 통한 매도 주문이 필요합니다.
        """
        try:
            if not self.trading_active[trade_type]:
                logger.warning(f"{trade_type} trading is not active")
                return False

            # 현재 포지션 조회
            positions = self.get_positions(trade_type)

            if positions.empty:
                logger.info("No positions to close")
                return True

            # 청산 대상 필터링
            if close_all:
                targets = positions
                logger.info(f"Closing all {len(targets)} positions for {trade_type}")
            elif code:
                targets = positions[positions['종목코드'] == code]
                if targets.empty:
                    logger.warning(f"Code {code} not found in positions")
                    return False
                logger.info(f"Closing position for {code}")
            else:
                logger.error("Either code or close_all must be specified")
                return False

            # TODO: 실제 매도 주문 실행
            for _, row in targets.iterrows():
                logger.warning(f"Would close position: {row['종목코드']} {row['종목명']} x{row['보유수량']}")
                logger.warning("Position closing is a placeholder - order submission not implemented")

            return True

        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            print_exc()
            return False

    def get_orders(self, trade_type: str) -> pd.DataFrame:
        """
        미체결 주문 조회

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')

        Returns:
            미체결 주문 DataFrame
        """
        try:
            # tradelist.db에서 주문 내역 조회
            con = sqlite3.connect(DB_TRADELIST)

            # 테이블 존재 확인
            cursor = con.cursor()
            table = 'jumunlist'
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                logger.info(f"Table '{table}' does not exist in tradelist.db")
                con.close()
                return pd.DataFrame()

            # 미체결 주문 조회
            query = f"""
                SELECT
                    주문번호,
                    종목코드,
                    종목명,
                    주문구분,
                    주문가격,
                    주문수량,
                    미체결수량,
                    주문시간,
                    주문상태
                FROM {table}
                WHERE 미체결수량 > 0
                ORDER BY 주문시간 DESC
            """

            df = pd.read_sql(query, con)
            con.close()

            if df.empty:
                logger.info(f"No pending orders for {trade_type}")
            else:
                logger.info(f"Found {len(df)} pending orders for {trade_type}")

            return df

        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            print_exc()
            return pd.DataFrame()

    def cancel_order(self, trade_type: str, order_id: str = None, cancel_all: bool = False) -> bool:
        """
        주문 취소

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')
            order_id: 주문번호 (특정 주문만 취소할 경우)
            cancel_all: 전체 취소 여부

        Returns:
            성공 여부

        Note:
            현재는 플레이스홀더 구현입니다.
            실제 취소는 브로커 API를 통한 취소 요청이 필요합니다.
        """
        try:
            if not self.trading_active[trade_type]:
                logger.warning(f"{trade_type} trading is not active")
                return False

            # 현재 미체결 주문 조회
            orders = self.get_orders(trade_type)

            if orders.empty:
                logger.info("No pending orders to cancel")
                return True

            # 취소 대상 필터링
            if cancel_all:
                targets = orders
                logger.info(f"Cancelling all {len(targets)} orders for {trade_type}")
            elif order_id:
                targets = orders[orders['주문번호'] == order_id]
                if targets.empty:
                    logger.warning(f"Order {order_id} not found")
                    return False
                logger.info(f"Cancelling order {order_id}")
            else:
                logger.error("Either order_id or cancel_all must be specified")
                return False

            # TODO: 실제 주문 취소 실행
            for _, row in targets.iterrows():
                logger.warning(f"Would cancel order: {row['주문번호']} {row['종목코드']} {row['주문구분']} x{row['미체결수량']}")
                logger.warning("Order cancellation is a placeholder - cancel request not implemented")

            return True

        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            print_exc()
            return False

    def get_trade_history(self, trade_type: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        거래 내역 조회

        Args:
            trade_type: 거래 타입 ('stock', 'coin', 'future')
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            거래 내역 DataFrame
        """
        try:
            # tradelist.db에서 체결 내역 조회
            con = sqlite3.connect(DB_TRADELIST)

            # 테이블 존재 확인
            cursor = con.cursor()
            table = 'chegeollist'
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                logger.info(f"Table '{table}' does not exist in tradelist.db")
                con.close()
                return pd.DataFrame()

            # 거래 내역 조회
            query = f"""
                SELECT
                    체결시간,
                    종목코드,
                    종목명,
                    주문구분,
                    체결가,
                    수량,
                    체결금액,
                    수수료,
                    세금
                FROM {table}
                ORDER BY 체결시간 DESC
            """

            # 날짜 필터 추가
            if start_date or end_date:
                conditions = []
                if start_date:
                    conditions.append(f"체결시간 >= '{start_date}'")
                if end_date:
                    conditions.append(f"체결시간 <= '{end_date}'")
                query = query.replace("ORDER BY", f"WHERE {' AND '.join(conditions)} ORDER BY")

            df = pd.read_sql(query, con)
            con.close()

            if df.empty:
                logger.info(f"No trade history found for {trade_type}")
            else:
                logger.info(f"Found {len(df)} trades for {trade_type}")

            return df

        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            print_exc()
            return pd.DataFrame()
