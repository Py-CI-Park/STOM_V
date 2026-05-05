
import random
import sqlite3
import hashlib
import numpy as np
from numba import njit
from typing import Dict, List, Tuple
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import UI_NUM, DB_PATH
from utility.static_method.static import thread_decorator

VOLATILITY_PATTERN_DB = f'{DB_PATH}/volatility_pattern.db'

window_queue = None


def calculate_setting_hash(*args) -> str:
    """설정값들을 MD5 해시로 변환"""
    hash_input = '_'.join(map(str, args))
    return hashlib.md5(hash_input.encode()).hexdigest()


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


@njit(cache=True, fastmath=True)
def calculate_atr(close_price: np.ndarray, high_price: np.ndarray, low_price: np.ndarray,
                  analysis_period: int) -> np.ndarray:
    """ATR 계산 (numba 최적화)"""
    tr1 = high_price[1:] - low_price[1:]
    tr2 = np.abs(high_price[1:] - close_price[:-1])
    tr3 = np.abs(low_price[1:] - close_price[:-1])
    tr = np.maximum(tr1, tr2, tr3)
    atr = np.zeros(len(close_price))
    for idx in range(analysis_period, len(close_price)):
        atr[idx] = np.mean(tr[idx-analysis_period:idx])
    return atr


@njit(cache=True, fastmath=True)
def classify_volatility_levels(volatility_data: np.ndarray, level_boundaries: np.ndarray,
                               num_levels: int) -> np.ndarray:
    """변동성 레벨 분류 (numba 최적화)"""
    levels = np.zeros(len(volatility_data), dtype=np.int32)
    for idx in range(len(volatility_data)):
        if volatility_data[idx] > 0:
            for level in range(num_levels):
                if level_boundaries[level] <= volatility_data[idx] < level_boundaries[level + 1]:
                    levels[idx] = level
                    break
            if volatility_data[idx] >= level_boundaries[-1]:
                levels[idx] = num_levels - 1
    return levels


@njit(cache=True, fastmath=True)
def calculate_volatility_scores(close_price: np.ndarray, level_indices: np.ndarray,
                                analysis_period: int, rate_threshold: float) -> np.ndarray:
    """변동성 점수 계산 (numba 최적화)"""
    scores = []
    for idx in level_indices:
        if idx + analysis_period < len(close_price):
            entry_price = close_price[idx]
            exit_max_price = close_price[idx:idx + analysis_period].max()
            exit_min_price = close_price[idx:idx + analysis_period].min()
            if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                exit_price = exit_max_price
            else:
                exit_price = exit_min_price
            price_change = (exit_price - entry_price) / entry_price * 100
            score = price_change / rate_threshold * 100
            score = max(-100.0, min(100.0, score))
            scores.append(score)
    return np.array(scores)


class AnalyzerVolatilityPattern:
    """메인 변동성 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, backtest: bool = False, min_samples: int = 20):
        """
        초기화
        market_gubun: 마켓 구분 번호
        market_info: 마켓 정보 딕셔너리
        min_samples: 최소 샘플 수 (기본값 20)
        """
        self.volatility_database = VolatilityPatternDatabase(market_info['전략구분'])
        self.analysis_period, self.rate_threshold, self.num_levels = \
            self.volatility_database.load_volatility_setting(market_gubun)

        self.backtest_db       = market_info['백테디비'][0]
        self.factor_list       = market_info['팩터목록'][0]
        self.min_samples       = min_samples
        self.idx_close         = self.factor_list.index('현재가')
        self.idx_high          = self.factor_list.index('분봉고가')
        self.idx_low           = self.factor_list.index('분봉저가')
        self.volatility_scores = {}
        self.level_boundaries  = {}

        if not backtest:
            self._load_volatility_all_scores()

    def _load_volatility_all_scores(self):
        """데이터베이스에서 모든 종목의 변동성 점수 로드"""
        all_codes = self.volatility_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volatility_scores[code], self.level_boundaries[code] = \
                    self.volatility_database.get_volatility_all_scores(code)

    def load_volatility_code_scores(self, code: str, date: int):
        """데이터베이스에서 종목코드의 변동성 점수 로드"""
        self.volatility_scores[code], self.level_boundaries[code] = \
            self.volatility_database.get_volatility_code_scores(code, date)

    def analyze_current_volatility(self, code: str, realtime_data: np.ndarray) -> Tuple[float, float]:
        """
        실시간 변동성 분석 및 학습된 점수 반환
        code: 종목코드
        realtime_data: 실시간 1분봉 데이터
        return: 변동성점수, 변동성신뢰도
        """
        volatility_score, confidence = 0.0, 0.0

        if len(realtime_data) >= self.analysis_period:
            close_price = realtime_data[:, self.idx_close]
            high_price  = realtime_data[:, self.idx_high]
            low_price   = realtime_data[:, self.idx_low]

            tr1 = high_price[1:] - low_price[1:]
            tr2 = np.abs(high_price[1:] - close_price[:-1])
            tr3 = np.abs(low_price[1:] - close_price[:-1])
            tr  = np.maximum(tr1, tr2, tr3)
            atr = np.zeros(len(close_price))
            for idx in range(self.analysis_period, len(close_price)):
                atr[idx] = np.mean(tr[idx-self.analysis_period:idx])
            volatility_data  = atr
            volatility_value = volatility_data[-1]

            if code in self.level_boundaries:
                boundaries = self.level_boundaries[code]
                volatility_level = 0
                for level in range(len(boundaries) - 1):
                    if boundaries[level] <= volatility_value < boundaries[level + 1]:
                        volatility_level = level
                        break
                if volatility_value >= boundaries[-1]:
                    volatility_level = len(boundaries) - 2

                if code in self.volatility_scores and volatility_level in self.volatility_scores[code]:
                    score_data       = self.volatility_scores[code][volatility_level]
                    volatility_score = score_data['avg_score']
                    confidence       = score_data['confidence_score']

        return volatility_score, confidence

    def train_all_codes(self, windowQ):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.volatility_database.table_name} WHERE code = ?',
                    (code,)
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
                    i, chunk, self.backtest_db, self.idx_close, self.idx_high, self.idx_low, self.analysis_period,
                    self.rate_threshold, self.num_levels, self.min_samples, existing_dates_dict
                )
                for i, chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            code_count = 0
            for code, date_scores in chunk_results.items():
                for date, (volatility_scores, level_boundaries) in date_scores.items():
                    self.volatility_database.save_volatility_scores(code, volatility_scores, level_boundaries, date)
                    code_count += 1
                    total_processed += 1

            if code_count > 0:
                windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]"))

        if total_processed > 0:
            windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
            windowQ.put((UI_NUM['학습로그'], f"{VOLATILITY_PATTERN_DB} -> {self.volatility_database.table_name}"))
            windowQ.put((UI_NUM['학습로그'], f"변동성분석 학습 완료 [{total_processed}]"))
        else:
            windowQ.put((UI_NUM['학습로그'], "이미 모든 데이터가 학습되어 있습니다."))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str,
                          idx_close: int, idx_high: int, idx_low: int,
                          analysis_period: int, rate_threshold: int, num_levels: int,
                          min_samples: int, existing_dates_dict: Dict[str, set]) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db: 백테디비 경로
        idx_close: 현재가 인덱스
        idx_high: 분봉고가 인덱스
        idx_low: 분봉저가 인덱스
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        num_levels: 변동성 레벨 수
        min_samples: 최소 샘플 수
        existing_dates_dict: 종목별 기존 저장 날짜 딕셔너리 {code: set(dates)}
        return: 종목별 변동성 점수 딕셔너리 {code: volatility_scores}
        """
        global window_queue

        all_volatility_scores = {}
        last = len(code_chunk)

        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                datetime_data = historical_data[:, 0]
                dates = datetime_data // 10000
                target_dates = np.unique(dates)
                target_dates.sort()
                existing_dates = existing_dates_dict.get(code, set())

                for target_date in target_dates:
                    if target_date in existing_dates:
                        continue

                    mask = dates <= target_date
                    date_data = historical_data[mask]

                    if len(date_data) < analysis_period * 2:
                        continue

                    close_price = date_data[:, idx_close]
                    high_price  = date_data[:, idx_high]
                    low_price   = date_data[:, idx_low]

                    volatility_data = calculate_atr(close_price, high_price, low_price, analysis_period)
                    valid_data      = volatility_data[volatility_data > 0]

                    if len(valid_data) < num_levels:
                        level_boundaries = np.linspace(0, 1, num_levels + 1)
                    else:
                        percentiles      = np.linspace(0, 100, num_levels + 1)
                        level_boundaries = np.percentile(valid_data, percentiles)

                    levels = classify_volatility_levels(volatility_data, level_boundaries, num_levels)

                    level_scores = {}
                    for level in range(num_levels):
                        level_indices = np.where(levels == level)[0]
                        if len(level_indices) >= min_samples:
                            scores = calculate_volatility_scores(close_price, level_indices,
                                                                 analysis_period, rate_threshold)

                            if len(scores) >= min_samples:
                                sample_factor = min(len(scores) / 100.0, 1.0)
                                std_factor    = max(1.0 - float(np.std(scores)) / 50.0, 0.0)
                                confidence    = (sample_factor + std_factor) / 2.0
                                level_scores[level] = {
                                    'avg_score': round(float(np.mean(scores)), 2),
                                    'max_score': round(float(np.max(scores)), 2),
                                    'min_score': round(float(np.min(scores)), 2),
                                    'std_score': round(float(np.std(scores)), 2),
                                    'sample_count': len(scores),
                                    'confidence_score': round(confidence, 2)
                                }

                    if level_scores:
                        if code not in all_volatility_scores:
                            all_volatility_scores[code] = {}
                        all_volatility_scores[code][target_date] = (level_scores, level_boundaries)

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 변동성분석 학습 중 ... [{k+1:02d}/{last:02d}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 변동성분석 학습 실패 - {e}"))

        return all_volatility_scores


class VolatilityPatternDatabase:
    """변동성 패턴 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str):
        self.table_name   = f'{strategy_gubun}_volatility_pattern'
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS volatility_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    num_levels INTEGER NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    volatility_level INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    level_boundaries TEXT NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, volatility_level, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        return: 종목코드 리스트
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_volatility_all_scores(self, code: str) -> Tuple[Dict[int, Dict[str, float]], np.ndarray]:
        """
        종목의 전체 변동성 점수 조회 (최신 날짜 기준)
        code: 종목코드
        return: (변동성 레벨별 점수 딕셔너리, 레벨 경계 배열)
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, avg_score, max_score, min_score, std_score, sample_count,
                confidence_score, level_boundaries
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash))
            results = cursor.fetchall()

            volatility_scores = {}
            level_boundaries = None
            for result in results:
                volatility_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
                level_boundaries = np.array(list(map(float, result[7].split(','))))

            return volatility_scores, level_boundaries

    def get_volatility_code_scores(self, code: str, date: int) -> \
            Tuple[Dict[int, Dict[str, float]], np.ndarray]:
        """
        백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 변동성 점수 조회
        code: 종목코드
        date: 백테스트 기준 날짜 (YYYYMMDD)
        return: (변동성 레벨별 점수 딕셔너리, 레벨 경계 배열)
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT volatility_level, avg_score, max_score, min_score, std_score, sample_count,
                confidence_score, level_boundaries
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update < ?)
            ''', (code, self.setting_hash, code, self.setting_hash, date))
            results = cursor.fetchall()

            volatility_scores = {}
            level_boundaries = None
            for result in results:
                volatility_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
                level_boundaries = np.array(list(map(float, result[7].split(','))))

            return volatility_scores, level_boundaries

    def save_volatility_scores(self, code: str, volatility_scores: Dict[int, Dict[str, float]],
                               level_boundaries: np.ndarray, date: int):
        """
        종목별 변동성 점수 저장
        code: 종목코드
        volatility_scores: 변동성 레벨별 점수 딕셔너리
        level_boundaries: 레벨 경계 배열
        date: 학습 날짜
        """
        boundaries_str = ','.join(map(str, level_boundaries))

        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()

            data = [
                (
                    code,
                    volatility_level,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    boundaries_str,
                    self.setting_hash,
                    date
                )
                for volatility_level, scores in volatility_scores.items()
            ]

            cursor.executemany(f'''
                INSERT OR REPLACE INTO {self.table_name} 
                (code, volatility_level, avg_score, max_score, min_score, std_score, sample_count,
                confidence_score, level_boundaries, setting_hash, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)

            conn.commit()

    def load_volatility_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (analysis_period, rate_threshold, num_levels) 튜플, 데이터가 없으면 ('std', 20, 10) 반환
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, rate_threshold, num_levels FROM volatility_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if not result:
                result = 30, 5, 5

            self.setting_hash = calculate_setting_hash(*result)
            return result

    def save_volatility_setting(self, market: int, analysis_period: int, rate_threshold: str, num_levels: int):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        num_levels: 변동성 레벨 수
        """
        with sqlite3.connect(VOLATILITY_PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO volatility_setting '
                '(market, analysis_period, rate_threshold, num_levels) VALUES (?, ?, ?, ?)',
                (market, analysis_period, rate_threshold, num_levels)
            )
            conn.commit()


def volatility_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, num_levels = database.load_volatility_setting(ui.market_gubun)
    ui.vlp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vlp_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vlp_comboBoxxx_03.setCurrentText(str(num_levels))


def volatility_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period = int(ui.vlp_comboBoxxx_01.currentText())
    rate_threshold  = int(ui.vlp_comboBoxxx_02.currentText())
    num_levels      = int(ui.vlp_comboBoxxx_03.currentText())
    database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    database.save_volatility_setting(ui.market_gubun, analysis_period, rate_threshold, num_levels)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def volatility_train(ui):
    """변동성 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 변동성 패턴 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vlp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vlp_comboBoxxx_02.currentText())
    _num_levels      = int(ui.vlp_comboBoxxx_03.currentText())
    database = VolatilityPatternDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, num_levels = database.load_volatility_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _num_levels != num_levels:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _volatility_train(ui)


@thread_decorator
def _volatility_train(ui):
    """스레드로 변동성 패턴 학습을 시작한다."""
    ui.learn_running = True
    vp_analyzer = AnalyzerVolatilityPattern(ui.market_gubun, ui.market_info)
    vp_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
