
import random
import sqlite3
import hashlib
import numpy as np
import pandas as pd
from numba import njit, prange
from traceback import format_exc
from PyQt5.QtWidgets import QMessageBox
from typing import Dict, List, Tuple, Any
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.static_method.static_datetime import now
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static_decorator import thread_decorator

VOLATILITY_PATTERN_DB = f'{DB_PATH}/volatility_pattern.db'

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
    period: 각 기간의 길이 (이전=period, 최근=period, 총 2*period 필요)"""
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


@njit(cache=True, fastmath=True)
def _calculate_realized_volatility_change_rate_last(prices: np.ndarray, analysis_period: int) -> float:
    """실현 변동성 변화율 마지막 값만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    log_returns = np.zeros(2 * analysis_period, dtype=np.float64)
    for i in range(2 * analysis_period):
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


@njit(cache=True, fastmath=True)
def _calculate_absolute_change_rate_change_last(prices: np.ndarray, analysis_period: int) -> float:
    """절대 변화율 기반 변동성 변화율 마지막 값만 계산 (실시간용, Numba 최적화)"""
    n = len(prices)
    abs_changes = np.zeros(2 * analysis_period, dtype=np.float64)
    for i in range(2 * analysis_period):
        idx = n - 2 * analysis_period + i
        abs_changes[i] = abs(prices[idx] / prices[idx - 1] - 1) * 100
    prev_vol   = np.mean(abs_changes[:analysis_period])
    recent_vol = np.mean(abs_changes[analysis_period:])
    if prev_vol > 0:
        return recent_vol / prev_vol
    return 0.0


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_volatility_scores(prices: np.ndarray, dates: np.ndarray, indices: np.ndarray,
                                 analysis_period: int, rate_threshold: float) -> np.ndarray:
    """변동성 점수 계산 (numba 최적화)"""
    max_scores = len(indices)
    scores = np.zeros(max_scores, dtype=np.float64)
    for k in prange(max_scores):
        idx = indices[k]
        if idx + analysis_period < len(prices) and dates[idx] == dates[idx + analysis_period]:
            entry_price    = prices[idx]
            exit_max_price = prices[idx:idx + analysis_period].max()
            exit_min_price = prices[idx:idx + analysis_period].min()
            if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                exit_price = exit_max_price
            else:
                exit_price = exit_min_price
            price_change   = (exit_price / entry_price - 1) * 100
            score = price_change / rate_threshold * 100
            score = max(-100.0, min(100.0, score))
            scores[k] = score
    return scores[scores != 0.0]


class AnalyzerVolatilityPattern:
    """메인 변동성 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, is_tick: bool,
                 realtime: bool = False, min_samples: int = 20):
        self.volatility_database = VolatilityPatternDatabase(market_info['전략구분'], is_tick)
        self.analysis_period, self.rate_threshold = \
            self.volatility_database.load_volatility_setting(market_gubun)

        self.backtest_db = market_info['백테디비'][is_tick]
        self.factor_list = market_info['팩터목록'][is_tick]
        self.is_tick     = is_tick
        self.min_samples = min_samples
        self.idx_close   = self.factor_list.index('현재가')
        self.volatility_scores: dict[str, dict[int, dict[str, float]]] = {}

        if realtime:
            self._load_volatility_all_scores()

    def _load_volatility_all_scores(self):
        """데이터베이스에서 모든 종목의 변동성 점수 로드"""
        all_codes = self.volatility_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volatility_scores[code] = self.volatility_database.get_volatility_all_scores(code)

    def load_volatility_code_scores(self, code: str, date: int):
        """데이터베이스에서 종목코드의 변동성 점수 로드"""
        self.volatility_scores[code] = self.volatility_database.get_volatility_code_scores(code, date)

    def analyze_current_volatility(self, code: str, code_data: np.ndarray) -> Tuple[float, float]:
        """실시간 변동성 분석 및 학습된 점수 반환 (변동성 변화율 기반)"""
        volatility_score = confidence_score = 0.0

        len_min = self.analysis_period * 2 + 1
        group_data = self.volatility_scores.get(code)
        if group_data and len(code_data) >= len_min:
            close_price    = code_data[-len_min:, self.idx_close]
            vol_std_change = _calculate_volatility_change_rate_last(close_price, self.analysis_period)
            vol_abs_change = _calculate_absolute_change_rate_change_last(close_price, self.analysis_period)
            vol_rv_change  = _calculate_realized_volatility_change_rate_last(close_price, self.analysis_period)
            vol_cur_change = vol_std_change * 0.4 + vol_rv_change * 0.4 + vol_abs_change * 0.2
            rounded_rate   = round(vol_cur_change * 2) / 2

            score_data = group_data.get(rounded_rate)
            if score_data:
                volatility_score = score_data['avg_score']
                confidence_score = score_data['confidence_score']

        return volatility_score, confidence_score

    def analyze_batch_data(self, code: str, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석합니다."""
        date = int(str(code_data[0, 0])[:8])
        self.load_volatility_code_scores(code, date)

        n = len(code_data)
        start_idx = self.analysis_period * 2 + 1
        results = np.zeros((n, 2))

        for i in range(start_idx, n):
            window_data = code_data[:i]
            results[i] = list(self.analyze_current_volatility(code, window_data))

        return results

    def train_all_codes(self, ui):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
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
        if len_code_list == 0:
            ui.windowQ.put((UI_NUM['학습로그'], '백테DB에 데이터가 존재하지 않습니다.'))
            return
        elif len_code_list <= multi:
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
                    self.rate_threshold, self.min_samples, existing_dates_dict,
                    self.is_tick, self.volatility_database.setting_hash
                )
                for i, code_chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        columns = [
            'code', 'volatility_level', 'avg_score', 'max_score', 'min_score', 'std_score',
            'sample_count', 'confidence_score', 'setting_hash', 'last_update'
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
            ui.windowQ.put((UI_NUM['학습로그'], f'변동성분석 학습 완료, 소요시간[{pass_time}]'))
        else:
            ui.windowQ.put((UI_NUM['학습로그'], '이미 모든 데이터가 학습되어 있습니다.'))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str, idx_close: int, analysis_period: int,
                          rate_threshold: int, min_samples: int, existing_dates_dict: Dict[str, set],
                          is_tick: bool, setting_hash: str) -> List[Any]:
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

                all_dates = historical_data[:, 0] // 1000000 if is_tick else historical_data[:, 0] // 10000
                target_dates = np.unique(all_dates)
                target_dates.sort()
                existing_dates = existing_dates_dict.get(code, set())

                for target_date in target_dates:
                    if target_date in existing_dates:
                        continue

                    mask = all_dates <= target_date
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
                            indices_array = np.array(indices)
                            scores = _calculate_volatility_scores(date_prices, dates, indices_array,
                                                                  analysis_period, rate_threshold)

                            if len(scores) >= min_samples:
                                std_scores    = scores.std()
                                sample_factor = min(len(scores) / 100.0, 1.0)
                                std_factor    = max(1.0 - std_scores / 100.0, 0.0)
                                confidence    = (sample_factor + std_factor) / 2.0

                                level_scores = [
                                    code,
                                    level,
                                    round(scores.mean(), 2),
                                    round(scores.max(), 2),
                                    round(scores.min(), 2),
                                    round(std_scores, 2),
                                    len(scores),
                                    round(confidence, 2),
                                    setting_hash,
                                    target_date
                                ]
                                all_volatility_scores.append(level_scores)

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 변동성분석 학습 중 ... [{k+1:02d}/{last:02d}]'))
            except Exception:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['시스템로그'], format_exc()))

        return all_volatility_scores


class VolatilityPatternDatabase:
    """변동성 패턴 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str, is_tick: bool):
        self.table_name   = f"{strategy_gubun}_volatility_pattern_{'tick' if is_tick else 'min'}"
        self.is_tick      = is_tick
        self.db_path      = VOLATILITY_PATTERN_DB
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS volatility_setting (
                    market INTEGER NOT NULL,
                    is_tick INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    PRIMARY KEY (market, is_tick)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    volatility_level REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, volatility_level, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """데이터베이스에 저장된 전체 종목코드 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT DISTINCT code 
                FROM {self.table_name} 
                WHERE setting_hash = ?
            ''', (self.setting_hash,)
            )
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_volatility_all_scores(self, code: str) -> Dict[int, Dict[str, float]]:
        """종목의 전체 변동성 점수 조회 (최신 날짜 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, avg_score, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash)
            )
            results = cursor.fetchall()

            volatility_scores = {}
            for result in results:
                volatility_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }

            return volatility_scores

    def get_volatility_code_scores(self, code: str, date: int) -> Dict[int, Dict[str, float]]:
        """백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 변동성 점수 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, avg_score, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update <= ?)
            ''', (code, self.setting_hash, code, self.setting_hash, date)
            )
            results = cursor.fetchall()

            volatility_scores = {}
            for result in results:
                volatility_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }

            return volatility_scores

    def save_volatility_scores(self, df: pd.DataFrame):
        """종목별 변동성 점수 저장"""
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False, chunksize=2000)

    def load_volatility_setting(self, market: int) -> tuple:
        """마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        is_tick: 틱 데이터 여부 (기본값 False)
        return: (analysis_period, rate_threshold) 튜플, 데이터가 없으면 (30, 5) 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT analysis_period, rate_threshold 
                FROM volatility_setting 
                WHERE market = ? AND is_tick = ?
            ''', (market, 1 if self.is_tick else 0)
            )
            result = cursor.fetchone()
            if result:
                analysis_period, rate_threshold = result
            else:
                analysis_period, rate_threshold = 10, 3
                self.save_volatility_setting(market, analysis_period, rate_threshold)

            self.setting_hash = _calculate_setting_hash(analysis_period, rate_threshold)
            return analysis_period, rate_threshold

    def save_volatility_setting(self, market: int, analysis_period: int, rate_threshold: str):
        """마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        is_tick: 틱 데이터 여부 (기본값 False)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR REPLACE INTO volatility_setting 
                (market, is_tick, analysis_period, rate_threshold) 
                VALUES (?, ?, ?, ?)
            ''', (market, 1 if self.is_tick else 0, analysis_period, rate_threshold)
            )
            conn.commit()


def volatility_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolatilityPatternDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period, rate_threshold = database.load_volatility_setting(ui.market_gubun)
    ui.vlp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vlp_comboBoxxx_02.setCurrentText(str(rate_threshold))


def volatility_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    from ui.etcetera.etc import send_analyzer_setting_change
    analysis_period = int(ui.vlp_comboBoxxx_01.currentText())
    rate_threshold  = int(ui.vlp_comboBoxxx_02.currentText())
    database = VolatilityPatternDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    database.save_volatility_setting(ui.market_gubun, analysis_period, rate_threshold)
    send_analyzer_setting_change(ui)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def volatility_train(ui):
    """변동성 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vlp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vlp_comboBoxxx_02.currentText())
    database = VolatilityPatternDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period, rate_threshold = database.load_volatility_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    ui.windowQ.put((UI_NUM['학습로그'], '변동성분석 학습을 시작합니다.'))
    _volatility_train(ui)


@thread_decorator
def _volatility_train(ui):
    """스레드로 변동성 패턴 학습을 시작한다."""
    ui.learn_running = True
    vp_analyzer = AnalyzerVolatilityPattern(ui.market_gubun, ui.market_info, ui.dict_set['타임프레임'])
    vp_analyzer.train_all_codes(ui)
    ui.learn_running = False
