
import talib
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

PATTERN_DB = f'{DB_PATH}/pattern_analysis.db'
PATTERN_FUNCTIONS = [
    'CDL2CROWS', 'CDL3BLACKCROWS', 'CDL3INSIDE', 'CDL3LINESTRIKE', 'CDL3OUTSIDE',
    'CDL3STARSINSOUTH', 'CDL3WHITESOLDIERS', 'CDLABANDONEDBABY', 'CDLADVANCEBLOCK', 'CDLBELTHOLD',
    'CDLBREAKAWAY', 'CDLCLOSINGMARUBOZU', 'CDLCONCEALBABYSWALL', 'CDLCOUNTERATTACK', 'CDLDARKCLOUDCOVER',
    'CDLDOJI', 'CDLDOJISTAR', 'CDLDRAGONFLYDOJI', 'CDLENGULFING', 'CDLEVENINGDOJISTAR',
    'CDLEVENINGSTAR', 'CDLGAPSIDESIDEWHITE', 'CDLGRAVESTONEDOJI', 'CDLHAMMER', 'CDLHANGINGMAN',
    'CDLHARAMI', 'CDLHARAMICROSS', 'CDLHIGHWAVE', 'CDLHIKKAKE', 'CDLHIKKAKEMOD',
    'CDLHOMINGPIGEON', 'CDLIDENTICAL3CROWS', 'CDLINNECK', 'CDLINVERTEDHAMMER', 'CDLKICKING',
    'CDLKICKINGBYLENGTH', 'CDLLADDERBOTTOM', 'CDLLONGLEGGEDDOJI', 'CDLLONGLINE', 'CDLMARUBOZU',
    'CDLMATCHINGLOW', 'CDLMATHOLD', 'CDLMORNINGDOJISTAR', 'CDLMORNINGSTAR', 'CDLONNECK',
    'CDLPIERCING', 'CDLRICKSHAWMAN', 'CDLRISEFALL3METHODS', 'CDLSEPARATINGLINES', 'CDLSHOOTINGSTAR',
    'CDLSHORTLINE', 'CDLSPINNINGTOP', 'CDLSTALLEDPATTERN', 'CDLSTICKSANDWICH', 'CDLTAKURI',
    'CDLTASUKIGAP', 'CDLTHRUSTING', 'CDLTRISTAR', 'CDLUNIQUE3RIVER', 'CDLUPSIDEGAP2CROWS',
    'CDLXSIDEGAP3METHODS'
]

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
def _calculate_pattern_scores(close_price: np.ndarray, dates: np.ndarray, detection_indices: np.ndarray,
                              analysis_period: int, rate_threshold: float) -> np.ndarray:
    """패턴 점수 계산 (numba 최적화)"""
    max_scores = len(detection_indices)
    scores = np.zeros(max_scores)
    for k in prange(max_scores):
        idx = detection_indices[k]
        if idx + analysis_period < len(close_price) and dates[idx] == dates[idx + analysis_period]:
            entry_price    = close_price[idx]
            exit_max_price = close_price[idx:idx + analysis_period].max()
            exit_min_price = close_price[idx:idx + analysis_period].min()
            if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                exit_price = exit_max_price
            else:
                exit_price = exit_min_price
            price_change   = (exit_price / entry_price - 1) * 100
            score = price_change / rate_threshold * 100
            score = max(-100.0, min(100.0, score))
            scores[k] = score
    return scores[scores != 0.0]


class AnalyzerCandlePattern:
    """메인 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, realtime: bool = False,
                 min_candle: int = 15, min_samples: int = 20):
        self.pattern_database = CandlePatternDatabase(market_info['전략구분'])
        self.analysis_period, self.rate_threshold = self.pattern_database.load_pattern_setting(market_gubun)

        self.backtest_db = market_info['백테디비'][0]
        self.factor_list = market_info['팩터목록'][0]
        self.min_candle  = min_candle
        self.min_samples = min_samples
        self.idx_open    = self.factor_list.index('분봉시가')
        self.idx_high    = self.factor_list.index('분봉고가')
        self.idx_low     = self.factor_list.index('분봉저가')
        self.idx_close   = self.factor_list.index('현재가')
        self.pattern_scores: dict[str, dict[str, dict[str, float]]] = {}

        if realtime:
            self._load_pattern_all_scores()

    def _load_pattern_all_scores(self):
        """데이터베이스에서 모든 종목의 패턴 점수 로드"""
        all_codes = self.pattern_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.pattern_scores[code] = self.pattern_database.get_pattern_all_scores(code)

    def load_pattern_code_scores(self, code: str, date: int):
        """데이터베이스에서 종목코드의 패턴 점수 로드"""
        self.pattern_scores[code] = self.pattern_database.get_pattern_code_scores(code, date)

    def analyze_current_patterns(self, code: str, code_data: np.ndarray) -> Tuple[float, float]:
        """실시간 패턴 분석 및 학습된 점수 반환"""
        pattern_score = confidence_score = 0.0

        pattern_scores = self.pattern_scores.get(code)
        if pattern_scores and len(code_data) >= self.min_candle:
            code_data   = code_data[-self.min_candle:]
            open_price  = code_data[:, self.idx_open]
            high_price  = code_data[:, self.idx_high]
            low_price   = code_data[:, self.idx_low]
            close_price = code_data[:, self.idx_close]

            high_avg_score = 0
            for pattern_name in PATTERN_FUNCTIONS:
                pattern_func   = getattr(talib, pattern_name)
                pattern_result = pattern_func(open_price, high_price, low_price, close_price)

                if pattern_result[-1] != 0:
                    learned_score = pattern_scores.get(pattern_name)
                    if learned_score:
                        avg_score = learned_score['avg_score']
                        if avg_score > high_avg_score:
                            pattern_score    = avg_score
                            confidence_score = learned_score['confidence_score']

        return pattern_score, confidence_score

    def analyze_batch_data(self, code: str, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석합니다."""
        date = int(str(code_data[0, 0])[:8])
        self.load_pattern_code_scores(code, date)

        n = len(code_data)
        results = np.zeros((n, 2))

        for i in range(self.min_candle - 1, n):
            window_data = code_data[:i + 1]
            results[i] = list(self.analyze_current_patterns(code, window_data))

        return results

    def train_all_codes(self, ui):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}
        with sqlite3.connect(self.pattern_database.db_path) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.pattern_database.table_name} '
                    f'WHERE code = ? and setting_hash = ?',
                    (code, self.pattern_database.setting_hash)
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
                    i, code_chunk, self.backtest_db, self.idx_open, self.idx_high,
                    self.idx_low, self.idx_close, self.analysis_period, self.rate_threshold, self.min_samples,
                    existing_dates_dict, self.pattern_database.setting_hash
                )
                for i, code_chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        columns = [
            'code', 'pattern_name', 'avg_score', 'max_score', 'min_score', 'std_score',
            'sample_count', 'confidence_score', 'setting_hash', 'last_update'
        ]
        for i, result in enumerate(results):
            if result:
                df = pd.DataFrame(result, columns=columns)
                self.pattern_database.save_pattern_scores(df)
                total_processed += 1
                ui.windowQ.put((UI_NUM['학습로그'], f'학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]'))

        if total_processed > 0:
            pass_time = now() - start
            ui.windowQ.put((
                UI_NUM['학습로그'],
                f'학습 데이터 저장 완료, {self.pattern_database.db_path} -> {self.pattern_database.table_name}'
            ))
            ui.windowQ.put((UI_NUM['학습로그'], f'캔들분석 학습 완료, 소요시간[{pass_time}]'))
        else:
            ui.windowQ.put((UI_NUM['학습로그'], '이미 모든 데이터가 학습되어 있습니다'))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str, idx_open: int, idx_high: int,
                          idx_low: int, idx_close: int, analysis_period: int, rate_threshold: int, min_samples: int,
                          existing_dates_dict: Dict[str, set], setting_hash: str) -> List[Any]:
        """단일 종목 청크 학습 (멀티프로세싱용)"""
        global window_queue

        all_pattern_scores = []
        last = len(code_chunk)

        with sqlite3.connect(backtest_db) as conn:
            cursor = conn.cursor()
            for k, code in enumerate(code_chunk):
                try:
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                    all_dates = historical_data[:, 0] // 10000
                    target_dates = np.unique(all_dates)
                    target_dates.sort()
                    existing_dates = existing_dates_dict.get(code, set())

                    for target_date in target_dates:
                        if target_date in existing_dates:
                            continue

                        mask = all_dates <= target_date
                        date_data = historical_data[mask]

                        if len(date_data) < analysis_period * 2:
                            continue

                        dates       = date_data[:, 0] // 10000
                        open_price  = date_data[:, idx_open]
                        high_price  = date_data[:, idx_high]
                        low_price   = date_data[:, idx_low]
                        close_price = date_data[:, idx_close]

                        for pattern_name in PATTERN_FUNCTIONS:
                            pattern_func      = getattr(talib, pattern_name)
                            pattern_result    = pattern_func(open_price, high_price, low_price, close_price)
                            detection_indices = np.where(pattern_result != 0)[0]

                            if len(detection_indices) >= min_samples:
                                scores = _calculate_pattern_scores(close_price, dates, detection_indices,
                                                                   analysis_period, rate_threshold)

                                if len(scores) >= min_samples:
                                    std_scores    = scores.std()
                                    sample_factor = min(len(scores) / 100.0, 1.0)
                                    std_factor    = max(1.0 - float(std_scores) / 50.0, 0.0)
                                    confidence    = (sample_factor + std_factor) / 2.0

                                    pattern_scores = [
                                        code,
                                        pattern_name,
                                        round(scores.mean(), 2),
                                        round(scores.max(), 2),
                                        round(scores.min(), 2),
                                        round(std_scores, 2),
                                        len(scores),
                                        round(confidence, 2),
                                        setting_hash,
                                        target_date
                                    ]
                                    all_pattern_scores.append(pattern_scores)

                    # noinspection PyUnresolvedReferences
                    window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 캔들분석 학습 중 ... [{k+1:02d}/{last:02d}]'))
                except Exception:
                    # noinspection PyUnresolvedReferences
                    window_queue.put((UI_NUM['시스템로그'], format_exc()))

        return all_pattern_scores


class CandlePatternDatabase:
    """패턴 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str):
        self.table_name   = f'{strategy_gubun}_pattern_score'
        self.db_path      = PATTERN_DB
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS pattern_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, pattern_name, setting_hash, last_update)
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

    def get_pattern_all_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """종목의 전체 패턴 점수 조회 (최신 날짜 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT pattern_name, avg_score, confidence_score
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash))
            results = cursor.fetchall()

            pattern_scores = {}
            for result in results:
                pattern_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }
            return pattern_scores

    def get_pattern_code_scores(self, code: str, backtest_date: int) -> Dict[str, Dict[str, float]]:
        """백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 패턴 점수 조회 """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT pattern_name, avg_score, confidence_score 
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update < ?)
            ''', (code, self.setting_hash, code, self.setting_hash, backtest_date))
            results = cursor.fetchall()

            pattern_scores = {}
            for result in results:
                pattern_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }
            return pattern_scores

    def save_pattern_scores(self, df: pd.DataFrame):
        """ 종목별 패턴 점수 저장"""
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False, chunksize=2000)

    def load_pattern_setting(self, market: int) -> tuple:
        """마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (analysis_period, rate_threshold) 튜플, 데이터가 없으면 (30, 10) 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT analysis_period, rate_threshold 
                FROM pattern_setting 
                WHERE market = ?
            ''', (market,)
            )
            result = cursor.fetchone()
            if result:
                analysis_period, rate_threshold = result
            else:
                analysis_period, rate_threshold = 10, 3
                self.save_pattern_setting(market, analysis_period, rate_threshold)

            self.setting_hash = _calculate_setting_hash(analysis_period, rate_threshold)
            return analysis_period, rate_threshold

    def save_pattern_setting(self, market: int, analysis_period: int, rate_threshold: int):
        """마켓번호로 설정값 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR REPLACE INTO pattern_setting 
                (market, analysis_period, rate_threshold)
                VALUES (?, ?, ?)
            ''', (market, analysis_period, rate_threshold)
            )
            conn.commit()


def pattern_setting_load(ui):
    """두개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = CandlePatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold = database.load_pattern_setting(ui.market_gubun)
    ui.ptn_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.ptn_comboBoxxx_02.setCurrentText(str(rate_threshold))


def pattern_setting_save(ui):
    """두개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    from ui.etcetera.etc import send_analyzer_setting_change
    analysis_period  = int(ui.ptn_comboBoxxx_01.currentText())
    rate_threshold   = int(ui.ptn_comboBoxxx_02.currentText())
    database = CandlePatternDatabase(ui.market_info['전략구분'])
    database.save_pattern_setting(ui.market_gubun, analysis_period, rate_threshold)
    send_analyzer_setting_change(ui)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def pattern_train(ui):
    """패턴학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.dict_set['타임프레임']:
        QMessageBox.critical(
            ui.dialog_pattern, '오류 알림',
            '현재 타임프레임이 1초스냅샷 상태입니다.\n캔들분석 학습은 1분봉 타임프레임만 지원합니다.\n'
        )
        return

    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.ptn_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.ptn_comboBoxxx_02.currentText())
    database = CandlePatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold = database.load_pattern_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    ui.windowQ.put((UI_NUM['학습로그'], '캔들분석 학습을 시작합니다.'))
    _pattern_train(ui)


@thread_decorator
def _pattern_train(ui):
    """스레드로 패턴학습을 시작한다."""
    ui.learn_running = True
    pt_analyzer = AnalyzerCandlePattern(ui.market_gubun, ui.market_info)
    pt_analyzer.train_all_codes(ui)
    ui.learn_running = False
