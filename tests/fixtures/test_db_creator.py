"""
STOM CLI Test Fixtures - Database Creator
==========================================

테스트용 데이터베이스 생성 유틸리티
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .sample_strategies import (
    SAMPLE_STRATEGIES_METADATA,
    SAMPLE_BACKTEST_RESULTS,
    SAMPLE_TRADES
)


class DatabaseCreator:
    """테스트용 데이터베이스 생성 클래스 (pytest 수집 방지를 위해 Test 접두사 제거)"""

    def __init__(self, base_dir: Path):
        """
        Args:
            base_dir: 데이터베이스 파일을 생성할 기본 디렉토리
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_strategy_db(self, with_data: bool = False) -> Path:
        """
        전략 데이터베이스 생성

        Args:
            with_data: True면 샘플 데이터 포함

        Returns:
            생성된 DB 파일 경로
        """
        db_path = self.base_dir / "strategy.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 모든 전략 테이블 생성
        tables = [
            'stockbuy', 'stocksell', 'coinbuy', 'coinsell',
            'futurebuy', 'futuresell', 'stockoptibuy', 'stockoptisell',
            'coinoptibuy', 'coinoptisell', 'futureoptibuy', 'futureoptisell',
            'stockvars', 'coinvars', 'futurevars',
            'stockoptivars', 'coinoptivars', 'futureoptivars',
            'stockbuyconds', 'stocksellconds', 'coinbuyconds', 'coinsellconds',
            'futurebuyconds', 'futuresellconds', 'schedule'
        ]

        for table in tables:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    name TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        if with_data:
            self._insert_sample_strategies(cursor)

        conn.commit()
        conn.close()
        return db_path

    def create_backtest_db(self, with_data: bool = False) -> Path:
        """
        백테스트 데이터베이스 생성

        Args:
            with_data: True면 샘플 데이터 포함

        Returns:
            생성된 DB 파일 경로
        """
        db_path = self.base_dir / "backtest.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        if with_data:
            self._insert_sample_backtest_results(cursor)

        conn.commit()
        conn.close()
        return db_path

    def create_tradelist_db(self, with_data: bool = False) -> Path:
        """
        거래내역 데이터베이스 생성

        Args:
            with_data: True면 샘플 데이터 포함

        Returns:
            생성된 DB 파일 경로
        """
        db_path = self.base_dir / "tradelist.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                trade_time TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        if with_data:
            self._insert_sample_trades(cursor)

        conn.commit()
        conn.close()
        return db_path

    def create_setting_db(self) -> Path:
        """
        설정 데이터베이스 생성 (기본 스키마만)

        Returns:
            생성된 DB 파일 경로
        """
        db_path = self.base_dir / "setting.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 기본 설정 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS main (
                `index` TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                `index` TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin (
                `index` TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS back (
                `index` TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        conn.close()
        return db_path

    def create_all_databases(self, with_data: bool = False) -> Dict[str, Path]:
        """
        모든 테스트용 데이터베이스 생성

        Args:
            with_data: True면 샘플 데이터 포함

        Returns:
            DB 이름 -> 경로 매핑
        """
        return {
            'strategy': self.create_strategy_db(with_data),
            'backtest': self.create_backtest_db(with_data),
            'tradelist': self.create_tradelist_db(with_data),
            'setting': self.create_setting_db(),
        }

    def _insert_sample_strategies(self, cursor: sqlite3.Cursor) -> None:
        """샘플 전략 데이터 삽입"""
        for strategy in SAMPLE_STRATEGIES_METADATA:
            table = f"{strategy['type']}{strategy['buy_sell']}"
            cursor.execute(
                f"INSERT OR REPLACE INTO {table} (name, code) VALUES (?, ?)",
                (strategy['name'], strategy['code'])
            )

    def _insert_sample_backtest_results(self, cursor: sqlite3.Cursor) -> None:
        """샘플 백테스트 결과 삽입"""
        for result in SAMPLE_BACKTEST_RESULTS:
            cursor.execute("""
                INSERT INTO backtest_results
                (strategy_name, start_date, end_date, total_return,
                 sharpe_ratio, max_drawdown, win_rate, total_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result['strategy_name'],
                result['start_date'],
                result['end_date'],
                result['total_return'],
                result['sharpe_ratio'],
                result['max_drawdown'],
                result.get('win_rate'),
                result.get('total_trades')
            ))

    def _insert_sample_trades(self, cursor: sqlite3.Cursor) -> None:
        """샘플 거래 데이터 삽입"""
        for trade in SAMPLE_TRADES:
            cursor.execute("""
                INSERT INTO trades
                (symbol, trade_date, trade_time, side, quantity, price)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trade['symbol'],
                trade['trade_date'],
                trade['trade_time'],
                trade['side'],
                trade['quantity'],
                trade['price']
            ))


def create_test_databases(base_dir: Path, with_data: bool = True) -> Dict[str, Path]:
    """
    테스트용 데이터베이스 일괄 생성 헬퍼 함수

    Args:
        base_dir: 데이터베이스 파일을 생성할 디렉토리
        with_data: True면 샘플 데이터 포함

    Returns:
        DB 이름 -> 경로 매핑
    """
    creator = DatabaseCreator(base_dir)
    return creator.create_all_databases(with_data)


def verify_database_schema(db_path: Path, expected_tables: List[str]) -> bool:
    """
    데이터베이스 스키마 검증

    Args:
        db_path: 검증할 DB 파일 경로
        expected_tables: 존재해야 하는 테이블 목록

    Returns:
        모든 테이블이 존재하면 True
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    actual_tables = {row[0] for row in cursor.fetchall()}

    conn.close()

    return all(table in actual_tables for table in expected_tables)
