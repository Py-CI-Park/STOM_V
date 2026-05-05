
import random
import sqlite3
import hashlib
import numpy as np
import pandas as pd
from numba import njit, prange
from traceback import format_exc
from PyQt5.QtWidgets import QMessageBox
from typing import Tuple, List, Dict, Any
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static_decorator import thread_decorator
from utility.static_method.static_datetime import now, dt_ymd, str_ymd, timedelta_day

VOLATILITY_STOP_TAKE_DB = f'{DB_PATH}/volatility_stop_take.db'

window_queue = None


def init_worker(wndowQ):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = wndowQ


def _calculate_setting_hash(*args) -> str:
    """설정값들을 MD5 해시로 변환"""
    hash_input = '_'.join(map(str, args))
    return hashlib.md5(hash_input.encode()).hexdigest()


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_volatility_change_rate(prices: np.ndarray, analysis_period: int) -> np.ndarray:
    """변동성 변화율 계산 (이전기간 대비 최근기간 변동성 변화, Numba 최적화)
    period: 각 기간의 길이 (이전=period, 최근=period, 총 2*period 필요)
    """
    n = len(prices)
    change_rates = np.zeros(n, dtype=np.float64)
    for i in prange(2 * analysis_period, n):
        prev_window   = prices[i + 1 - 2 * analysis_period:i + 1 - analysis_period]
        prev_mean     = np.mean(prev_window)
        prev_std      = np.std(prev_window)
        prev_vol      = prev_std / prev_mean * 100 if prev_mean > 0 else 0.0
        recent_window = prices[i + 1 - analysis_period:i + 1]
        recent_mean   = np.mean(recent_window)
        recent_std    = np.std(recent_window)
        recent_vol    = recent_std / recent_mean * 100 if recent_mean > 0 else 0.0
        if prev_vol > 0:
            change_rates[i] = recent_vol / prev_vol
    return change_rates


@njit(cache=True, fastmath=True)
def _calculate_volatility_change_rate_last(prices: np.ndarray, analysis_period: int) -> float:
    """변동성 변화율 마지막 값만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    prev_window   = prices[n - 2 * analysis_period:n - analysis_period]
    prev_mean     = np.mean(prev_window)
    prev_std      = np.std(prev_window)
    prev_vol      = prev_std / prev_mean * 100 if prev_mean > 0 else 0.0
    recent_window = prices[n - analysis_period:n]
    recent_mean   = np.mean(recent_window)
    recent_std    = np.std(recent_window)
    recent_vol    = recent_std / recent_mean * 100 if recent_mean > 0 else 0.0
    if prev_vol > 0:
        return recent_vol / prev_vol
    return 0.0


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_realized_volatility_change_rate(prices: np.ndarray, analysis_period: int) -> np.ndarray:
    """실현 변동성 변화율 계산 (이전기간 대비 최근기간, Numba 최적화)"""
    n = len(prices)
    log_returns = np.zeros(n, dtype=np.float64)
    for i in prange(1, n):
        log_returns[i] = np.log(prices[i] / prices[i - 1])
    change_rates = np.zeros(n, dtype=np.float64)
    for i in prange(2 * analysis_period, n):
        period_sqrt = np.sqrt(analysis_period)
        prev_std    = np.std(log_returns[i + 1 - 2 * analysis_period:i + 1 - analysis_period])
        prev_vol    = prev_std * period_sqrt * 100
        recent_std  = np.std(log_returns[i + 1 - analysis_period:i + 1])
        recent_vol  = recent_std * period_sqrt * 100
        if prev_vol > 0:
            change_rates[i] = recent_vol / prev_vol
    return change_rates


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_realized_volatility_change_rate_last(prices: np.ndarray, analysis_period: int) -> float:
    """실현 변동성 변화율 마지막 값만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    log_returns = np.zeros(2 * analysis_period, dtype=np.float64)
    for i in prange(2 * analysis_period):
        idx = n - 2 * analysis_period + i
        log_returns[i] = np.log(prices[idx] / prices[idx - 1])
    period_sqrt = np.sqrt(analysis_period)
    prev_std    = np.std(log_returns[:analysis_period])
    prev_vol    = prev_std * period_sqrt * 100
    recent_std  = np.std(log_returns[analysis_period:])
    recent_vol  = recent_std * period_sqrt * 100
    if prev_vol > 0:
        return recent_vol / prev_vol
    return 0.0


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_absolute_change_rate_change(prices: np.ndarray, analysis_period: int) -> np.ndarray:
    """절대 변화율 기반 변동성 변화율 계산 (이전기간 대비 최근기간, Numba 최적화)"""
    n = len(prices)
    abs_changes = np.zeros(n, dtype=np.float64)
    for i in prange(1, n):
        abs_changes[i] = abs(prices[i] / prices[i - 1] - 1) * 100
    change_rates = np.zeros(n, dtype=np.float64)
    for i in prange(2 * analysis_period, n):
        prev_vol   = np.mean(abs_changes[i + 1 - 2 * analysis_period:i + 1 - analysis_period])
        recent_vol = np.mean(abs_changes[i + 1 - analysis_period:i + 1])
        if prev_vol > 0:
            change_rates[i] = recent_vol / prev_vol
    return change_rates


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_absolute_change_rate_change_last(prices: np.ndarray, analysis_period: int) -> float:
    """절대 변화율 기반 변동성 변화율 마지막 값만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    abs_changes = np.zeros(2 * analysis_period, dtype=np.float64)
    for i in prange(2 * analysis_period):
        idx = n - 2 * analysis_period + i
        abs_changes[i] = abs(prices[idx] / prices[idx - 1] - 1) * 100
    prev_vol   = np.mean(abs_changes[:analysis_period])
    recent_vol = np.mean(abs_changes[analysis_period:])
    if prev_vol > 0:
        return recent_vol / prev_vol
    return 0.0


@njit(cache=True, fastmath=True, parallel=True)
def _simulate_stop_take(prices: np.ndarray, dates: np.ndarray, stop_loss_pct: float,
                        take_profit_pct: float, analysis_period: int, check_step: int):
    """손절/익절 시뮬레이션 (Numba 최적화)"""
    n = len(prices)
    returns = np.zeros(n, dtype=np.float64)
    total_iterations = (n - analysis_period - analysis_period + check_step - 1) // check_step
    for idx in prange(total_iterations):
        i = analysis_period + idx * check_step
        entry_price = prices[i]
        sl_price    = entry_price * (1 - stop_loss_pct / 100)
        tp_price    = entry_price * (1 + take_profit_pct / 100)
        for j in range(i + 1, min(i + 1 + analysis_period, n)):
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


class AnalyzerVolatilityStopTake:
    """변손익분석 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, is_tick: bool,
                 realtime: bool = False, min_samples: int = 20):
        """초기화
        market_gubun: 마켓 구분 번호
        market_info: 마켓 정보 딕셔너리
        is_tick: 틱 데이터 여부
        realtime: 실시간 모드 여부
        min_samples: 최소 샘플 수 (기본값 20)
        """
        self.volatility_database = VolatilityStopTakeDatabase(market_info['전략구분'], is_tick)
        self.analysis_period = self.volatility_database.load_volatility_stop_take_setting(market_gubun, is_tick)
        self.backtest_db = market_info['백테디비'][is_tick]
        self.factor_list = market_info['팩터목록'][is_tick]
        self.is_tick     = is_tick
        self.min_samples = min_samples
        self.idx_close   = self.factor_list.index('현재가')
        self.volatility_data: dict[str, dict[int, dict[str, float]]] = {}

        if realtime:
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

    def analyze_current_volatility(self, code: str, code_data: np.ndarray) -> Tuple[float, float, float, float]:
        """실시간 변동성 변화율 분석 및 학습된 손절/익절 반환
        code: 종목코드
        code_data: 코드 데이터 2차원 어레이
        return: (에상수익률, 익절수익률, 손절수익률, 변손익신뢰도)
        """
        estimated_return = take_profit_pct = stop_loss_pct = confidence_score = 0.0

        len_min    = self.analysis_period * 2 + 1
        group_data = self.volatility_data.get(code)
        if group_data and len(code_data) >= len_min:
            close_price    = code_data[-len_min:, self.idx_close]
            vol_std_change = _calculate_volatility_change_rate_last(close_price, self.analysis_period)
            vol_abs_change = _calculate_absolute_change_rate_change_last(close_price, self.analysis_period)
            vol_rv_change  = _calculate_realized_volatility_change_rate_last(close_price, self.analysis_period)
            vol_cur_change = vol_std_change * 0.4 + vol_rv_change * 0.4 + vol_abs_change * 0.2
            rounded_rate   = round(vol_cur_change * 2) / 2

            score_data = group_data.get(rounded_rate)
            if score_data:
                estimated_return = score_data['avg_return']
                take_profit_pct  = score_data['level_take']
                stop_loss_pct    = -score_data['level_stop']
                confidence_score = score_data['confidence_score']

        return estimated_return, take_profit_pct, stop_loss_pct, confidence_score

    def analyze_batch_data(self, code: str, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석
        code: 종목코드
        code_data: 코드 데이터 2차원 어레이
        return: (N, 4) 형태 - 에상수익률, 익절수익률, 손절수익률, 변손익신뢰도
        """
        date = int(str(code_data[0, 0])[:8])
        self.load_volatility_code_data(code, date)

        n = len(code_data)
        start_idx = self.analysis_period * 2 + 1
        results = np.zeros((n, 4))

        for i in range(start_idx, n):
            window_data = code_data[:i]
            results[i] = list(self.analyze_current_volatility(code, window_data))

        return results

    def train_all_codes(self, ui):
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
        len_code_list = len(code_list)
        if len_code_list <= multi:
            code_chunks = [[code] for code in code_list]
        else:
            code_chunks = []
            for i in range(multi):
                code_chunks.append([code for j, code in enumerate(code_list) if j % multi == i])

        start = now()
        ui.windowQ.put((UI_NUM['학습로그'], (start, len_code_list)))
        actual_processes = min(multi, len(code_chunks))
        with Pool(processes=actual_processes, initializer=init_worker, initargs=(ui.windowQ,)) as pool:
            args = [
                (
                    i, code_chunk, self.backtest_db, self.idx_close, self.analysis_period,
                    self.min_samples, existing_dates_dict, self.is_tick,
                    self.volatility_database.setting_hash
                )
                for i, code_chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_single_chunk, args)

        total_processed = 0
        columns = [
            'code', 'volatility_level', 'level_stop', 'level_take', 'avg_return', 'max_return', 'min_return',
            'std_return', 'win_rate', 'sample_count', 'confidence_score', 'setting_hash', 'last_update'
        ]
        for i, result in enumerate(results):
            if result:
                df = pd.DataFrame(result, columns=columns)
                self.volatility_database.save_volatility_scores(df)
                total_processed += 1
                ui.windowQ.put((UI_NUM['학습로그'], f'학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]'))

        if total_processed > 0:
            pass_time = now() - start
            ui.windowQ.put((
                UI_NUM['학습로그'],
                f'학습 데이터 저장 완료, {self.volatility_database.db_path} -> {self.volatility_database.table_name}'
            ))
            ui.windowQ.put((UI_NUM['학습로그'], f'변손익분석 학습 완료, 소요시간[{pass_time}]'))
        else:
            ui.windowQ.put((UI_NUM['학습로그'], '이미 모든 데이터가 학습되어 있습니다'))

    @staticmethod
    def _train_single_chunk(i: int, code_chunk: List[str], backtest_db: str, idx_close: int, analysis_period: int,
                            min_samples: int, existing_dates_dict: Dict[str, set], is_tick: bool,
                            setting_hash: str) -> List[Any]:
        """단일 종목 청크 학습 (멀티프로세싱용)"""
        global window_queue

        all_volatility_scores = []
        last = len(code_chunk)

        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                if len(historical_data) < analysis_period * 3:
                    continue

                all_dates = historical_data[:, 0] // 1000000 if is_tick else historical_data[:, 0] // 10000
                target_dates = np.unique(all_dates)
                target_dates.sort()
                existing_dates = existing_dates_dict.get(code, set())

                for target_date in target_dates:
                    if target_date in existing_dates:
                        continue

                    start_date = float(str_ymd(timedelta_day(-30, dt_ymd(str(int(target_date))))))
                    mask = (start_date <= all_dates) & (all_dates <= target_date)
                    date_data = historical_data[mask]

                    if len(date_data) < analysis_period * 3:
                        continue

                    dates          = date_data[:, 0] // 1000000 if is_tick else date_data[:, 0] // 10000
                    date_prices    = date_data[:, idx_close]
                    vol_std_change = _calculate_volatility_change_rate(date_prices, analysis_period)
                    vol_abs_change = _calculate_absolute_change_rate_change(date_prices, analysis_period)
                    vol_rv_change  = _calculate_realized_volatility_change_rate(date_prices, analysis_period)
                    change_rates   = vol_std_change * 0.4 + vol_rv_change * 0.4 + vol_abs_change * 0.2

                    groups = {}
                    for idx, rate in enumerate(change_rates):
                        if rate != 0.0:
                            rounded_level = round(rate * 2) / 2
                            if rounded_level not in groups:
                                groups[rounded_level] = []
                            groups[rounded_level].append(idx)

                    for level, indices in groups.items():
                        if len(indices) >= min_samples:
                            check_step      = 60 if is_tick else 10
                            stop_mult_range = np.linspace(0.5, 10.0, 20)
                            take_mult_range = np.linspace(0.5, 10.0, 20)
                            best_return     = -float('inf')

                            best_params = None
                            for stop_mult in stop_mult_range:
                                for take_mult in take_mult_range:
                                    returns = _simulate_stop_take(date_prices, dates, stop_mult, take_mult,
                                                                  analysis_period, check_step)

                                    if len(returns) > 0:
                                        total_return = returns.sum()
                                        if total_return > best_return:
                                            best_return = total_return
                                            best_params = (stop_mult, take_mult)

                            if best_params:
                                stop_mult, take_mult = best_params
                                scores = _simulate_stop_take(date_prices, dates, stop_mult, take_mult,
                                                             analysis_period, check_step)
                                len_scores    = len(scores)
                                std_scores    = scores.std()
                                sample_factor = min(len_scores / 100.0, 1.0)
                                std_factor    = max(1.0 - std_scores / 5.0, 0.0)
                                confidence    = (sample_factor + std_factor) / 2.0
                                # noinspection PyUnresolvedReferences
                                win_rate = (scores > 0).mean() * 100

                                volatility_scores = [
                                    code,
                                    level,
                                    round(stop_mult, 2),
                                    round(take_mult, 2),
                                    round(scores.mean(), 2),
                                    round(scores.max(), 2),
                                    round(scores.min(), 2),
                                    round(std_scores, 2),
                                    round(win_rate, 2),
                                    len_scores,
                                    round(confidence, 2),
                                    setting_hash,
                                    target_date
                                ]
                                all_volatility_scores.append(volatility_scores)

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 변손익분석 학습 중 ... [{k+1:02d}/{last:02d}]'))
            except Exception:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['시스템로그'], format_exc()))

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
                    analysis_period INTEGER NOT NULL,
                    PRIMARY KEY (market, is_tick)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    volatility_level REAL NOT NULL,
                    level_stop REAL NOT NULL,
                    level_take REAL NOT NULL,
                    avg_return REAL NOT NULL,
                    max_return REAL NOT NULL,
                    min_return REAL NOT NULL,
                    std_return REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, volatility_level, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> list:
        """모든 종목코드 목록 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT DISTINCT code 
                FROM {self.table_name} 
                WHERE setting_hash = ?
            ''', (self.setting_hash,)
            )
            results = cursor.fetchall()
            return [row[0] for row in results]

    def get_volatility_all_scores(self, code: str) -> dict:
        """종목의 모든 변동성 변화율 그룹 데이터 로드"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, level_stop, level_take, avg_return, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash)
            )
            results = cursor.fetchall()
            scores = {}
            for row in results:
                scores[row[0]] = {
                    'level_stop': row[1],
                    'level_take': row[2],
                    'avg_return': row[3],
                    'confidence_score': row[4]
                }
            return scores

    def get_volatility_code_scores(self, code: str, backtest_date: int) -> dict:
        """백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 변동성 변화율 점수 조회
        code: 종목코드
        backtest_date: 백테스트 기준 날짜 (YYYYMMDD)
        return: 변동성 변화율 그룹별 점수 딕셔너리
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, level_stop, level_take, avg_return, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update <= ?)
            ''', (code, self.setting_hash, code, self.setting_hash, backtest_date)
            )
            results = cursor.fetchall()
            scores = {}
            for row in results:
                scores[row[0]] = {
                    'level_stop': row[1],
                    'level_take': row[2],
                    'avg_return': row[3],
                    'confidence_score': row[4]
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
        return: analysis_period, 데이터가 없으면 60 반환
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT analysis_period 
                FROM volatility_stop_take_setting 
                WHERE market = ? AND is_tick = ?
            ''', (market, 1 if is_tick else 0)
            )
            result = cursor.fetchone()
            if result:
                self.setting_hash = _calculate_setting_hash(result[0])
                return result[0]
            else:
                analysis_period = 10
                self.save_volatility_stop_take_setting(market, is_tick, analysis_period)
                self.setting_hash = _calculate_setting_hash(analysis_period)
                return analysis_period

    def save_volatility_stop_take_setting(self, market: int, is_tick: bool, analysis_period: int):
        """설정값 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR REPLACE INTO volatility_stop_take_setting 
                (market, is_tick, analysis_period) 
                VALUES (?, ?, ?)
            ''', (market, 1 if is_tick else 0, analysis_period)
            )
            conn.commit()


def volatility_stop_take_setting_load(ui):
    """콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period = database.load_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'])
    ui.vst_comboBoxxx_01.setCurrentText(str(analysis_period))


def volatility_stop_take_setting_save(ui):
    """콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    from ui.etcetera.etc import send_analyzer_setting_change
    analysis_period = int(ui.vst_comboBoxxx_01.currentText())
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    database.save_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'], analysis_period)
    send_analyzer_setting_change(ui)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def volatility_stop_take_train(ui):
    """변동성 손절/익절 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vst_comboBoxxx_01.currentText())
    database = VolatilityStopTakeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period = database.load_volatility_stop_take_setting(ui.market_gubun, ui.dict_set['타임프레임'])

    if _analysis_period != analysis_period:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    ui.windowQ.put((UI_NUM['학습로그'], '변손익분석 학습을 시작합니다.'))
    _volatility_stop_take_train(ui)


@thread_decorator
def _volatility_stop_take_train(ui):
    """스레드로 변동성 손절/익절 학습을 시작한다."""
    ui.learn_running = True
    vst_analyzer = AnalyzerVolatilityStopTake(ui.market_gubun, ui.market_info, ui.dict_set['타임프레임'])
    vst_analyzer.train_all_codes(ui)
    ui.learn_running = False
