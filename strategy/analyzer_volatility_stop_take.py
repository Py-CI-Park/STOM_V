
import random
import sqlite3
import hashlib
import numpy as np
import pandas as pd
from numba import njit, prange
from typing import Tuple, List, Dict, Any
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static_decorator import thread_decorator

VOLATILITY_STOP_TAKE_DB = f'{DB_PATH}/volatility_stop_take.db'

window_queue = None


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


def _calculate_setting_hash(*args) -> str:
    """설정값들을 MD5 해시로 변환"""
    hash_input = '_'.join(map(str, args))
    return hashlib.md5(hash_input.encode()).hexdigest()


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_std_volatility(prices: np.ndarray, period: int) -> np.ndarray:
    """표준편차 기반 변동성 계산 (Numba 최적화)"""
    n = len(prices)
    volatility = np.zeros(n, dtype=np.float64)
    for i in prange(period, n):
        w    = prices[i-period:i]
        mean = np.mean(w)
        std  = np.std(w)
        volatility[i] = std / mean * 100
    return volatility


@njit(cache=True, fastmath=True)
def _calculate_std_volatility_last(prices: np.ndarray, period: int) -> float:
    """표준편차 기반 마지막 변동성만 계산 (실시간용, Numba 최적화)"""
    n    = len(prices)
    w    = prices[n-period:n]
    mean = np.mean(w)
    std  = np.std(w)
    return std / mean * 100


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_realized_volatility_tick(prices: np.ndarray, period: int) -> np.ndarray:
    """로그 수익률의 표준편차 기반 실현 변동성 (Numba 최적화)"""
    n = len(prices)
    returns = np.zeros(n-1, dtype=np.float64)
    for i in prange(1, n):
        returns[i-1] = np.log(prices[i] / prices[i-1])
    rv = np.zeros(n, dtype=np.float64)
    for i in prange(period, n):
        window = returns[i-period:i]
        rv[i] = np.std(window) * np.sqrt(period) * 100
    return rv


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_realized_volatility_tick_last(prices: np.ndarray, period: int) -> float:
    """로그 수익률 기반 마지막 실현 변동성만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    returns = np.zeros(period)
    base_idx = n - 1 - period
    for i in prange(period):
        returns[i] = np.log(prices[base_idx + i + 1] / prices[base_idx + i])
    return np.std(returns) * np.sqrt(period) * 100


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_absolute_change_rate(prices: np.ndarray, period: int) -> np.ndarray:
    """절대 변화율 기반 변동성 (Numba 최적화)"""
    n = len(prices)
    abs_changes = np.zeros(n - 1, dtype=np.float64)
    for i in prange(1, n):
        abs_changes[i - 1] = abs(prices[i] - prices[i - 1]) / prices[i - 1] * 100
    volatility = np.zeros(n, dtype=np.float64)
    for i in prange(period - 1, n):
        window = abs_changes[i - period + 1:i]
        volatility[i] = np.mean(window)
    return volatility


@njit(cache=True, fastmath=True)
def _calculate_absolute_change_rate_last(prices: np.ndarray, period: int) -> float:
    """절대 변화율 기반 마지막 변동성만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    if n < period + 1:
        return 0.0
    abs_changes = np.zeros(period)
    base_idx = n - period
    for i in range(period):
        idx = base_idx + i
        abs_changes[i] = abs(prices[idx] - prices[idx - 1]) / prices[idx - 1] * 100
    return np.mean(abs_changes)


@njit(cache=True, fastmath=True, parallel=True)
def _simulate_stop_take(prices: np.ndarray, dates: np.ndarray, stop_loss_pct: float,
                        take_profit_pct: float, start_period: int):
    """손절/익절 시뮬레이션 (Numba 최적화)"""
    n = len(prices)
    returns = np.zeros(n, dtype=np.float64)
    for i in prange(start_period, n - start_period):
        entry_price = prices[i]
        sl_price    = entry_price * (1 - stop_loss_pct / 100)
        tp_price    = entry_price * (1 + take_profit_pct / 100)
        for j in range(i + 1, min(i + 1 + start_period, n)):
            if dates[i] == dates[j]:
                if prices[j] <= sl_price:
                    returns[i] = -stop_loss_pct
                    break
                elif prices[j] >= tp_price:
                    returns[i] = take_profit_pct
                    break
            else:
                returns[i] = np.round((prices[j-1] / entry_price - 1) * 100, 2)
                break
    return returns[returns != 0.0]


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_volatility_percentiles(volatility_array: np.ndarray, group_count: int):
    """변동성 백분위값 계산 (Numba 최적화)"""
    percentiles = np.zeros(group_count, dtype=np.float64)
    step = 100.0 / group_count
    for i in prange(group_count):
        percentiles[i] = np.percentile(volatility_array, (i + 1) * step)
    return percentiles


class AnalyzerVolatilityStopTake:
    """변손익분석 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, is_tick: bool, backtest: bool = False):
        """초기화
        market_gubun: 마켓 구분 번호
        market_info: 마켓 정보 딕셔너리
        is_tick: 틱 데이터 여부
        backtest: 백테스트 모드 여부
        """
        self.volatility_database = VolatilityStopTakeDatabase(market_info['전략구분'], is_tick)
        self.start_period, self.group_count = \
            self.volatility_database.load_volatility_stop_take_setting(market_gubun, is_tick)
        self.backtest_db     = market_info['백테디비'][is_tick]
        self.factor_list     = market_info['팩터목록'][is_tick]
        self.is_tick         = is_tick
        self.idx_close       = self.factor_list.index('현재가')
        self.start_period    = 30
        self.volatility_data = {}

        if not backtest:
            self._load_volatility_all_data()

    def _load_volatility_all_data(self):
        """데이터베이스에서 모든 종목의 변동성 데이터 로드"""
        all_codes = self.volatility_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volatility_data[code] = self.volatility_database.get_volatility_all_scores(code)

    def load_volatility_code_data(self, code: str, date: int):
        """데이터베이스에서 종목코드의 변동성 데이터 로드
        code: 종목코드
        date: 일자 (YYYYMMDD 형식)
        """
        self.volatility_data[code] = self.volatility_database.get_volatility_code_scores(code, date)

    def analyze_current_volatility(self, code: str, code_data: np.ndarray) -> Tuple[float, float, float]:
        """실시간 변동성 분석 및 학습된 손절/익절 반환
        code: 종목코드
        code_data: 코드 데이터 2차원 어레이
        return: (손절%, 익절%, 변동성, 그룹번호)
        """
        estimated_return, take_profit_pct, stop_loss_pct = 0.0, 0.0, 0.0
        price_history = code_data[:, self.idx_close]
        group_data = self.volatility_data[code]

        if group_data and len(price_history) >= self.start_period:
            vol_std = _calculate_std_volatility_last(price_history, self.start_period)
            vol_abs = _calculate_absolute_change_rate_last(price_history, self.start_period)
            vol_rv  = _calculate_realized_volatility_tick_last(price_history, self.start_period)

            current_volatility = vol_std * 0.4 + vol_rv * 0.4 + vol_abs * 0.2
            for _, v in group_data.items():
                if v['volatility_min'] <= current_volatility < v['volatility_max']:
                    estimated_return = v['expected_return']
                    take_profit_pct  = v['multiplier_take']
                    stop_loss_pct    = -v['multiplier_stop']
                    break

        return estimated_return, take_profit_pct, stop_loss_pct

    def analyze_batch_data(self, code: str, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석
        code: 종목코드
        code_data: 코드 데이터 2차원 어레이
        return: (N, 3) 형태 - 손절%, 익절%
        """
        date = int(str(code_data[0, 0])[:8])
        self.load_volatility_code_data(code, date)

        n = len(code_data)
        results = np.zeros((n, 3))
        for i in range(self.start_period, n):
            window_data = code_data[i-self.start_period:i]
            results[i] = list(self.analyze_current_volatility(code, window_data))

        return results

    def train_all_codes(self, windowQ):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results   = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}

        with sqlite3.connect(self.volatility_database.db_path) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.volatility_database.table_name} '
                    f'WHERE code = ? and setting_hash = ?',
                    (code, self.volatility_database.setting_hash)
                )
                existing_dates_dict[code] = set([row[0] for row in cursor.fetchall()])

        multi = cpu_count()
        if len(code_list) <= multi:
            code_chunks = [[code] for code in code_list]
        else:
            code_chunks = []
            for i in range(multi):
                code_chunks.append([code for j, code in enumerate(code_list) if j % multi == i])

        actual_processes = min(multi, len(code_chunks))
        with Pool(processes=actual_processes, initializer=init_worker, initargs=(windowQ,)) as pool:
            args = [
                (
                    i, chunk, self.backtest_db, self.idx_close, self.start_period,
                    self.group_count, existing_dates_dict, self.is_tick, self.volatility_database.setting_hash
                )
                for i, chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_single_chunk, args)

        total_processed = 0
        columns = [
            'code', 'volatility_group', 'volatility_min', 'volatility_max', 'avg_volatility',
            'multiplier_stop', 'multiplier_take', 'expected_return', 'win_rate', 'sharpe_ratio',
            'sample_count', 'setting_hash', 'last_update'
        ]
        for i, result in enumerate(results):
            if result:
                df = pd.DataFrame(result, columns=columns)
                self.volatility_database.save_volatility_scores(df)
                total_processed += 1
                windowQ.put((UI_NUM['학습로그'], f'학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]'))

        if total_processed > 0:
            windowQ.put((UI_NUM['학습로그'], '학습 데이터 저장 완료'))
            windowQ.put((UI_NUM['학습로그'], f'{self.volatility_database.db_path} -> {self.volatility_database.table_name}'))
            windowQ.put((UI_NUM['학습로그'], '변손익분석 학습 완료'))
        else:
            windowQ.put((UI_NUM['학습로그'], '이미 모든 데이터가 학습되어 있습니다'))

    @staticmethod
    def _train_single_chunk(i: int, code_chunk: List[str], backtest_db: str, idx_close: int, start_period: int,
                            group_count: int, existing_dates_dict: Dict[str, set], is_tick: bool, setting_hash: str) -> List[Any]:
        """단일 종목 청크 학습 (멀티프로세싱용)"""
        all_volatility_scores = []
        last = len(code_chunk)

        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                if len(historical_data) < start_period * 2:
                    continue

                all_dates = historical_data[:, 0] // 1000000 if is_tick else historical_data[:, 0] // 10000
                target_dates = np.unique(all_dates)
                target_dates.sort()
                existing_dates = existing_dates_dict.get(code, set())

                for target_date in target_dates:
                    if target_date in existing_dates:
                        continue

                    mask = all_dates <= target_date
                    date_data = historical_data[mask]

                    if len(date_data) < start_period * 2:
                        continue

                    dates         = date_data[:, 0] // 1000000 if is_tick else date_data[:, 0] // 10000
                    date_prices   = date_data[:, idx_close]
                    vol_std       = _calculate_std_volatility(date_prices, start_period)
                    vol_abs       = _calculate_absolute_change_rate(date_prices, start_period)
                    vol_rv        = _calculate_realized_volatility_tick(date_prices, start_period)

                    volatility    = vol_std * 0.4 + vol_rv * 0.4 + vol_abs * 0.2
                    valid_indices = ~np.isnan(volatility)
                    volatility    = volatility[valid_indices]
                    percentiles   = _calculate_volatility_percentiles(volatility, group_count)

                    for group_idx in range(group_count):
                        vol_min = 0.0 if group_idx == 0 else percentiles[group_idx - 1]
                        vol_max = percentiles[group_idx]
                        if group_idx == group_count - 1:
                            group_indices = np.where(volatility >= vol_min)[0]
                        else:
                            group_indices = np.where((volatility >= vol_min) & (volatility < vol_max))[0]

                        if len(group_indices) < 100:
                            continue

                        stop_mult_range = np.linspace(0.5, 10.0, 20)
                        take_mult_range = np.linspace(0.5, 10.0, 20)
                        best_sharpe     = -float('inf')

                        best_params  = None
                        for stop_mult in stop_mult_range:
                            for take_mult in take_mult_range:
                                returns = _simulate_stop_take(date_prices, dates, stop_mult, take_mult, start_period)
                                if len(returns) > 0:
                                    sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
                                    if sharpe > best_sharpe:
                                        best_sharpe = sharpe
                                        best_params = (stop_mult, take_mult)

                        if best_params:
                            stop_mult, take_mult = best_params
                            returns    = _simulate_stop_take(date_prices, dates, stop_mult, take_mult, start_period)
                            avg_return = np.mean(returns)
                            # noinspection PyUnresolvedReferences
                            win_rate   = (returns > 0).mean() * 100
                            avg_vol    = np.mean(volatility[group_indices])

                            volatility_scores = [
                                code,
                                group_idx,
                                round(float(vol_min), 4),
                                round(float(vol_max), 4),
                                round(float(avg_vol), 4),
                                round(float(stop_mult), 2),
                                round(float(take_mult), 2),
                                round(float(avg_return), 4),
                                round(float(win_rate), 2),
                                round(float(best_sharpe), 4),
                                len(group_indices),
                                setting_hash,
                                target_date
                            ]
                            all_volatility_scores.append(volatility_scores)

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 변손익분석 학습 중 ... [{k+1:02d}/{last:02d}]'))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 변손익분석 학습 실패 - {e}'))

        return all_volatility_scores


class VolatilityStopTakeDatabase:
    """변손익분석 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str, is_tick: bool):
        self.table_name     = f"{strategy_gubun}_volatility_{'tick' if is_tick else 'min'}"
        self.db_path        = VOLATILITY_STOP_TAKE_DB
        self.setting_hash   = None
        self._initialize_database()

    def _initialize_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS volatility_stop_take_setting (
                    market INTEGER NOT NULL,
                    is_tick INTEGER NOT NULL,
                    start_period INTEGER NOT NULL,
                    group_count INTEGER NOT NULL,
                    PRIMARY KEY (market, is_tick)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    volatility_group INTEGER NOT NULL,
                    volatility_min REAL NOT NULL,
                    volatility_max REAL NOT NULL,
                    avg_volatility REAL NOT NULL,
                    multiplier_stop REAL NOT NULL,
                    multiplier_take REAL NOT NULL,
                    expected_return REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    sharpe_ratio REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, volatility_group, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> list:
        """모든 종목코드 목록 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT DISTINCT code FROM {self.table_name} WHERE setting_hash = ?',
                (self.setting_hash,)
            )
            results = cursor.fetchall()
            return [row[0] for row in results]

    def get_volatility_all_scores(self, code: str) -> dict:
        """종목의 모든 변동성 그룹 데이터 로드"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT volatility_group, volatility_min, volatility_max, avg_volatility, '
                f'multiplier_stop, multiplier_take, expected_return, win_rate, sharpe_ratio, sample_count '
                f'FROM {self.table_name} '
                f'WHERE code = ? AND setting_hash = ? AND last_update = '
                f'(SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?) '
                f'ORDER BY volatility_group',
                (code, self.setting_hash, code, self.setting_hash)
            )
            results = cursor.fetchall()
            scores = {}
            for row in results:
                scores[row[0]] = {
                    'volatility_min': row[1],
                    'volatility_max': row[2],
                    'avg_volatility': row[3],
                    'multiplier_stop': row[4],
                    'multiplier_take': row[5],
                    'expected_return': row[6],
                    'win_rate': row[7],
                    'sharpe_ratio': row[8],
                    'sample_count': row[9]
                }
            return scores

    def get_volatility_code_scores(self, code: str, backtest_date: int) -> dict:
        """백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 변동성 점수 조회
        code: 종목코드
        backtest_date: 백테스트 기준 날짜 (YYYYMMDD)
        return: 변동성 그룹별 점수 딕셔너리
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'SELECT volatility_group, volatility_min, volatility_max, avg_volatility, '
                f'multiplier_stop, multiplier_take, expected_return, win_rate, sharpe_ratio, sample_count '
                f'FROM {self.table_name} '
                f'WHERE code = ? AND setting_hash = ? AND last_update = '
                f'(SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update <= ?) '
                f'ORDER BY volatility_group',
                (code, self.setting_hash, code, self.setting_hash, backtest_date)
            )
            results = cursor.fetchall()
            scores = {}
            for row in results:
                scores[row[0]] = {
                    'volatility_min': row[1],
                    'volatility_max': row[2],
                    'avg_volatility': row[3],
                    'multiplier_stop': row[4],
                    'multiplier_take': row[5],
                    'expected_return': row[6],
                    'win_rate': row[7],
                    'sharpe_ratio': row[8],
                    'sample_count': row[9]
                }
            return scores

    def save_volatility_scores(self, df: pd.DataFrame):
        """종목별 변동성 점수 저장"""
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False, chunksize=2000)

    def load_volatility_stop_take_setting(self, market: int, is_tick: bool) -> tuple:
        """마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        is_tick: 틱 데이터 여부
        return: (start_period, group_count) 튜플, 데이터가 없으면 (60, 10) 반환
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT start_period, group_count '
                'FROM volatility_stop_take_setting '
                'WHERE market = ? AND is_tick = ?',
                (market, 1 if is_tick else 0)
            )
            result = cursor.fetchone()
            if result:
                self.setting_hash = _calculate_setting_hash(result[0], result[1])
                return result[0], result[1]
            else:
                start_period = 60
                group_count  = 10
                self.save_volatility_stop_take_setting(market, is_tick, start_period, group_count)
                self.setting_hash = _calculate_setting_hash(start_period, group_count)
                return start_period, group_count

    def save_volatility_stop_take_setting(self, market: int, is_tick: bool, start_period: int, group_count: int):
        """설정값 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO volatility_stop_take_setting '
                '(market, is_tick, start_period, group_count) '
                'VALUES (?, ?, ?, ?)',
                (market, 1 if is_tick else 0, start_period, group_count)
            )
            conn.commit()


def volatility_stop_take_setting_load(ui):
    """콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    start_period, group_count = database.load_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'])
    ui.vst_comboBoxxx_01.setCurrentText(str(start_period))
    ui.vst_comboBoxxx_02.setCurrentText(str(group_count))


def volatility_stop_take_setting_save(ui):
    """콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    from ui.etcetera.etc import send_analyzer_setting_change
    start_period = int(ui.vst_comboBoxxx_01.currentText())
    group_count  = int(ui.vst_comboBoxxx_02.currentText())
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    database.save_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'], start_period, group_count)
    send_analyzer_setting_change(ui)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def volatility_stop_take_train(ui):
    """변동성 손절/익절 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 변동성 손절/익절 학습이 진행중입니다.\n')
        return

    _start_period = int(ui.vst_comboBoxxx_01.currentText())
    _group_count  = int(ui.vst_comboBoxxx_02.currentText())
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    start_period, group_count = database.load_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'])

    if _start_period != start_period or _group_count != group_count:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    ui.windowQ.put((UI_NUM['학습로그'], '변손익분석 학습을 시작합니다.'))
    _volatility_stop_take_train(ui)


@thread_decorator
def _volatility_stop_take_train(ui):
    """스레드로 변동성 손절/익절 학습을 시작한다."""
    ui.learn_running = True
    vst_analyzer = AnalyzerVolatilityStopTake(ui.market_gubun, ui.market_info, ui.dict_set['타임프레임'])
    vst_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
