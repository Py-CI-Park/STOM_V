
import os
import talib
import random
import sqlite3
import numpy as np
from typing import Dict, List
from PyQt5.QtWidgets import QMessageBox
from multiprocessing import Pool, cpu_count
from utility.static_method.static import now, thread_decorator
from utility.settings.setting_base import ui_num
from ui.create_widget.set_text import famous_saying


PATTERN_DB = './_database/pattern_analysis.db'
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


def init_worker(q):
    """Pool worker 프로세스 초기화 함수: 윈도우 큐를 전역 변수로 설정"""
    global window_queue
    window_queue = q


class AnalyzerPattern:
    """메인 패턴 분석 통합 클래스"""
    def __init__(self, market_info: dict, minute: int = 30, pct: int = 5):
        self.market_info      = market_info
        self.strategy_type    = market_info['전략구분']
        self.backtest_db_path = market_info['백테디비'][0]
        self.minute           = minute
        self.pct              = pct
        self.pattern_database = PatternDatabase(self.strategy_type)
        self.pattern_realtime = PatternRealtime(market_info)

    def analyze_patterns(self, code: str, realtime_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        실시간 패턴 분석 수행
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
        :return: 탐지된 패턴과 학습된 점수
        """
        return self.pattern_realtime.analyze_patterns(code, realtime_data)

    def train_all_codes(self, windowQ):
        """
        전체 종목 패턴 학습 수행 (종목 기반 멀티프로세싱)
        """
        code_list = self.get_code_list()
        num_processes = cpu_count()
        code_chunks = self._split_codes(code_list, num_processes)

        with Pool(processes=num_processes, initializer=init_worker, initargs=(windowQ,)) as pool:
            args = [(i, chunk, self.backtest_db_path, self.market_info, self.minute, self.pct)
                    for i, chunk in enumerate(code_chunks)]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            for code, pattern_scores in chunk_results.items():
                self.pattern_database.save_pattern_scores(code, pattern_scores)
                total_processed += 1
            windowQ.put((ui_num['패턴학습'], f"학습 데이터 저장 중 ... [{i+1}/{num_processes}]"))

        windowQ.put((ui_num['패턴학습'], "학습 데이터 저장 완료"))
        windowQ.put((ui_num['패턴학습'], f"{PATTERN_DB} -> {self.pattern_database.table_name}"))
        windowQ.put((ui_num['패턴학습'], f"전체 종목 패턴 학습 완료 [{total_processed}]"))

    def get_code_list(self) -> List[str]:
        """
        백테 디비에서 종목코드 목록 추출
        :return: 종목코드 리스트
        """
        with sqlite3.connect(self.backtest_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]
            return code_list

    def _split_codes(self, code_list: List[str], num_chunks: int) -> List[List[str]]:
        """
        종목 리스트를 CPU수만큼 분할
        :param code_list: 종목코드 리스트
        :param num_chunks: 분할할 청크 수 (CPU 코어 수)
        :return: 분할된 종목코드 청크 리스트
        """
        chunk_size = len(code_list) // num_chunks
        chunks = []
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(code_list)
            chunks.append(code_list[start:end])
        return chunks

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db_path: str,
                          market_info: dict, minute: int, pct: int) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        :param code_chunk: 종목코드 청크
        :param backtest_db_path: 백테디비 경로
        :param market_info: 마켓 정보 딕셔너리
        :param minute: 분봉 설정
        :param pct: 퍼센트 설정
        :return: 종목별 패턴 점수 딕셔너리 {code: pattern_scores}
        """
        global window_queue
        pattern_learning = PatternLearning(market_info, minute, pct)
        all_pattern_scores = {}
        last = len(code_chunk)
        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)
                pattern_scores = pattern_learning.train_patterns(historical_data)
                if pattern_scores:
                    all_pattern_scores[code] = pattern_scores
                # noinspection PyUnresolvedReferences
                window_queue.put((ui_num['패턴학습'], f"[{i}][{code}] 패턴 학습 중 ... [{k+1}/{last}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((ui_num['패턴학습'], f"[{i}][{code}] 패턴 학습 실패 - {e}"))
        return all_pattern_scores


class PatternLearning:
    """과거데이터 기반 패턴 점수 학습 모듈"""
    def __init__(self, market_info: dict, minute: int, pct: int):
        self.market_info      = market_info
        self.strategy_type    = market_info['전략구분']
        self.minute           = minute
        self.pct              = pct
        factor_list           = market_info['팩터목록'][0]
        self.idx_open         = factor_list.index('분봉시가')
        self.idx_high         = factor_list.index('분봉고가')
        self.idx_low          = factor_list.index('분봉저가')
        self.idx_close        = factor_list.index('현재가')
        self.num_processes    = os.cpu_count()
        self.pattern_database = PatternDatabase(self.strategy_type)

    def train_patterns(self, historical_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        종목별 과거데이터로 패턴 점수 학습 (순차 처리)
        :param historical_data: 과거 1분봉 데이터 (2차원 numpy 어레이) 칼럼순서는 self.market_info['팩터목록'][0]에 따름
        :return: 패턴별 점수 딕셔너리
        """
        open_price     = historical_data[:, self.idx_open]
        high_price     = historical_data[:, self.idx_high]
        low_price      = historical_data[:, self.idx_low]
        close_price    = historical_data[:, self.idx_close]
        datetime_data  = historical_data[:, 0]

        pattern_scores = {}
        for pattern_name in PATTERN_FUNCTIONS:
            pattern_func      = getattr(talib, pattern_name)
            pattern_result    = pattern_func(open_price, high_price, low_price, close_price)
            detection_indices = np.where(pattern_result != 0)[0]

            scores = []
            for idx in detection_indices:
                if idx + self.minute < len(close_price):
                    entry_date = int(datetime_data[idx] // 10000)
                    exit_date = int(datetime_data[idx + self.minute] // 10000)
                    if entry_date == exit_date:
                        entry_price = close_price[idx]
                        exit_max_price = close_price[idx:idx + self.minute].max()
                        exit_min_price = close_price[idx:idx + self.minute].min()
                        if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                            exit_price = exit_max_price
                        else:
                            exit_price = exit_min_price

                        price_change = (exit_price - entry_price) / entry_price * 100
                        score = self._calculate_score(price_change)
                        scores.append(score)

            if len(scores) >= 10:
                pattern_scores[pattern_name] = {
                    'avg_score': float(np.mean(scores)),
                    'max_score': float(np.max(scores)),
                    'min_score': float(np.min(scores)),
                    'std_score': float(np.std(scores)),
                    'sample_count': len(scores)
                }

        return pattern_scores

    def _calculate_score(self, price_change_percent: float) -> float:
        """가격변화율을 기반으로 점수 계산"""
        score = (price_change_percent / self.pct) * 100
        return max(-100.0, min(100.0, score))


class PatternRealtime:
    """실시간 패턴인식 및 학습된 점수 반환 모듈"""
    def __init__(self, market_info: dict):
        self.market_info      = market_info
        self.strategy_type    = market_info['전략구분']
        factor_list           = market_info['팩터목록'][0]
        self.idx_open         = factor_list.index('분봉시가')
        self.idx_high         = factor_list.index('분봉고가')
        self.idx_low          = factor_list.index('분봉저가')
        self.idx_close        = factor_list.index('현재가')
        self.pattern_database = PatternDatabase(self.strategy_type)
        self.pattern_scores   = {}
        self._load_pattern_scores()

    def _load_pattern_scores(self):
        """데이터베이스에서 모든 종목의 패턴 점수를 미리 로드"""
        all_codes = self.pattern_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.pattern_scores[code] = self.pattern_database.get_all_pattern_scores(code)
            return True
        return False

    def analyze_patterns(self, code: str, realtime_data: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        실시간 데이터에서 패턴 탐지 및 학습된 점수 반환
        :param code: 종목코드
        :param realtime_data: 실시간 1분봉 데이터 (2차원 numpy 어레이)
                            칼럼순서는 self.market_info['팩터목록'][0]에 따름
        :return: 탐지된 패턴과 학습된 점수
        """
        pattern_score, reliability = 0, 0

        realtime_data = realtime_data[-5:]
        open_price    = realtime_data[:, self.idx_open]
        high_price    = realtime_data[:, self.idx_high]
        low_price     = realtime_data[:, self.idx_low]
        close_price   = realtime_data[:, self.idx_close]

        for pattern_name in PATTERN_FUNCTIONS:
            pattern_func = getattr(talib, pattern_name)
            pattern_result = pattern_func(open_price, high_price, low_price, close_price)

            if pattern_result[-1] != 0:
                learned_score = self.pattern_scores.get(code, {}).get(pattern_name)
                if learned_score:
                    pattern_score = learned_score['avg_score']
                    reliability = self._calculate_reliability(learned_score)

        return pattern_score, reliability

    def _calculate_reliability(self, score_data: Dict[str, float]) -> float:
        """
        점수 데이터의 신뢰도 계산
        :param score_data: 학습된 점수 데이터
        :return: 신뢰도 (0 ~ 1)
        """
        sample_factor = min(score_data['sample_count'] / 100.0, 1.0)
        std_factor = max(1.0 - score_data['std_score'] / 50.0, 0.0)
        return (sample_factor + std_factor) / 2.0


class PatternDatabase:
    """패턴 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_type: str):
        self.strategy_type = strategy_type
        self.table_name    = f'{strategy_type}_pattern_score'
        self._ensure_db_directory()
        self._initialize_tables()

    def _ensure_db_directory(self):
        """데이터베이스 디렉토리 생성"""
        db_dir = os.path.dirname(PATTERN_DB)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS pattern_setting (
                    market INTEGER NOT NULL,
                    minute INTEGER NOT NULL,
                    pct INTEGER NOT NULL,
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
                    last_update TEXT NOT NULL,
                    PRIMARY KEY (code, pattern_name)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        :return: 종목코드 리스트
        """
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_all_pattern_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """
        종목의 전체 패턴 점수 조회
        :param code: 종목코드
        :return: 패턴별 점수 딕셔너리
        """
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT pattern_name, avg_score, max_score, min_score, std_score, sample_count
                FROM {self.table_name}
                WHERE code = ?
            ''', (code,))
            results = cursor.fetchall()

            pattern_scores = {}
            for result in results:
                pattern_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5]
                }
            return pattern_scores

    def save_pattern_scores(self, code: str, pattern_scores: Dict[str, Dict[str, float]]):
        """
        종목별 패턴 점수 저장
        :param code: 종목코드
        :param pattern_scores: 패턴별 점수 딕셔너리
        """
        current_date = now().strftime('%Y-%m-%d')

        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            for pattern_name, scores in pattern_scores.items():
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {self.table_name} 
                    (code, pattern_name, avg_score, max_score, min_score, std_score, sample_count, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    pattern_name,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    current_date
                ))
            conn.commit()

    def delete_all_pattern_scores(self, code: str):
        """
        종목의 전체 패턴 점수 삭제
        :param code: 종목코드
        """
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'DELETE FROM {self.table_name} WHERE code = ?', (code,))
            conn.commit()

    def load_pattern_setting(self, market: int) -> tuple:
        """
        마켓번호로 패턴 설정값 불러오기
        :param market: 마켓번호 (1~9)
        :return: (minute, pct) 튜플, 데이터가 없으면 (30, 10) 반환
        """
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT minute, pct FROM pattern_setting WHERE market = ?', (market,))
            result = cursor.fetchone()
            if result:
                return result
            return 30, 10

    def save_pattern_setting(self, market: int, minute: int, pct: int):
        """
        마켓번호로 패턴 설정값 저장
        :param market: 마켓번호 (1~9)
        :param minute: 분봉설정
        :param pct: 퍼센트설정
        """
        with sqlite3.connect(PATTERN_DB) as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO pattern_setting (market, minute, pct) VALUES (?, ?, ?)',
                           (market, minute, pct))
            conn.commit()


def pattern_setting_load(ui):
    pattern_database = PatternDatabase(ui.market_info['전략구분'])
    minute, pct = pattern_database.load_pattern_setting(ui.market_gubun)
    ui.ptn_comboBoxxx_01.setCurrentText(str(minute))
    ui.ptn_comboBoxxx_02.setCurrentText(str(pct))


def pattern_setting_save(ui):
    minute = int(ui.ptn_comboBoxxx_01.currentText())
    pct = int(ui.ptn_comboBoxxx_02.currentText())
    pattern_database = PatternDatabase(ui.market_info['전략구분'])
    pattern_database.save_pattern_setting(ui.market_gubun, minute, pct)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def pattern_train(ui):
    if ui.pattern_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 패턴학습이 진행중입니다.\n')
        return
    _pattern_train(ui)


@thread_decorator
def _pattern_train(ui):
    ui.pattern_running = True
    minute = int(ui.ptn_comboBoxxx_01.currentText())
    pct = int(ui.ptn_comboBoxxx_02.currentText())
    pt_analyzer = AnalyzerPattern(ui.market_info, minute, pct)
    pt_analyzer.train_all_codes(ui.windowQ)
    ui.pattern_running = False
