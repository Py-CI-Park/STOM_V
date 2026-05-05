
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

VOLUME_SPIKE_DB = f'{DB_PATH}/volume_spike.db'

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
def calculate_ma_volume(volume_data: np.ndarray, analysis_period: int) -> np.ndarray:
    """이동평균 거래량 계산 (numba 최적화)"""
    ma_volume = np.zeros(len(volume_data))
    for idx in range(analysis_period, len(volume_data)):
        ma_volume[idx] = np.mean(volume_data[idx-analysis_period:idx])
    return ma_volume


@njit(cache=True, fastmath=True)
def calculate_spike_indices(volume_data: np.ndarray, ma_volume: np.ndarray,
                            ratio_threshold: float, analysis_period: int) -> np.ndarray:
    """거래량 급증 인덱스 계산 (numba 최적화)"""
    spike_indices = []
    for idx in range(analysis_period, len(volume_data)):
        if ma_volume[idx] > 0:
            multiplier = volume_data[idx] / ma_volume[idx]
            if multiplier >= ratio_threshold:
                spike_indices.append(idx)
    return np.array(spike_indices)


@njit(cache=True, fastmath=True)
def calculate_spike_score_array(close_price: np.ndarray, indices: np.ndarray,
                                analysis_period: int, rate_threshold: float) -> np.ndarray:
    """거래량 급증 점수 배열 계산 (numba 최적화)"""
    scores = []
    for idx in indices:
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
        else:
            scores.append(0.0)
    return np.array(scores)


class AnalyzerVolumeSpike:
    """메인 거래량 급증 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, backtest: bool = False, min_samples: int = 20):
        """
        초기화
        market_gubun: 마켓 구분 번호
        market_info: 마켓 정보 딕셔너리
        min_samples: 최소 샘플 수 (기본값 20)
        """
        self.spike_database = VolumeSpikeDatabase(market_info['전략구분'])
        self.analysis_period, self.rate_threshold, self.ratio_threshold = \
            self.spike_database.load_spike_setting(market_gubun)

        self.backtest_db  = market_info['백테디비'][0]
        self.factor_list  = market_info['팩터목록'][0]
        self.min_samples  = min_samples
        self.idx_close    = self.factor_list.index('현재가')
        self.idx_volume   = self.factor_list.index('분당거래대금')
        self.spike_scores = {}

        if not backtest:
            self._load_spike_all_scores()

    def _load_spike_all_scores(self):
        """데이터베이스에서 모든 종목의 급증 점수 로드"""
        all_codes = self.spike_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.spike_scores[code] = self.spike_database.get_spike_all_scores(code)

    def load_spike_code_scores(self, code: str, date: int):
        """데이터베이스에서 종목코드의 급증 점수 로드"""
        self.spike_scores[code] = self.spike_database.get_spike_code_scores(code, date)

    def analyze_current_spike(self, code: str, realtime_data: np.ndarray) -> Tuple[float, float]:
        """
        실시간 거래량 분석 및 학습된 점수 반환
        code: 종목코드
        realtime_data: 실시간 1분봉 데이터
        return: 거래량점수, 거래량신뢰도
        """
        spike_score, confidence = 0.0, 0.0

        if len(realtime_data) >= self.analysis_period:
            volume_data    = realtime_data[:, self.idx_volume]
            ma_volume = np.zeros(len(volume_data))
            for idx in range(self.analysis_period, len(volume_data)):
                ma_volume[idx] = np.mean(volume_data[idx-self.analysis_period:idx])
            current_volume = volume_data[-1]

            if ma_volume[-1] > 0:
                spike_multiplier = current_volume / ma_volume[-1]
                if spike_multiplier >= self.ratio_threshold:
                    rounded_multiplier = round(spike_multiplier * 2) / 2
                    if code in self.spike_scores and rounded_multiplier in self.spike_scores[code]:
                        score_data  = self.spike_scores[code][rounded_multiplier]
                        spike_score = score_data['avg_score']
                        confidence  = score_data['confidence_score']

        return spike_score, confidence

    def train_all_codes(self, windowQ):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.spike_database.table_name} WHERE code = ?',
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
                    i, chunk, self.backtest_db, self.idx_close, self.idx_volume, self.analysis_period,
                    self.rate_threshold, self.ratio_threshold, self.min_samples, existing_dates_dict
                )
                for i, chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            code_count = 0
            for code, date_scores in chunk_results.items():
                for date, spike_scores in date_scores.items():
                    self.spike_database.save_spike_scores(code, spike_scores, date)
                    code_count += 1
                    total_processed += 1

            if code_count > 0:
                windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]"))

        if total_processed > 0:
            windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
            windowQ.put((UI_NUM['학습로그'], f"{VOLUME_SPIKE_DB} -> {self.spike_database.table_name}"))
            windowQ.put((UI_NUM['학습로그'], f"거래량분석 학습 완료 [{total_processed}]"))
        else:
            windowQ.put((UI_NUM['학습로그'], "이미 모든 데이터가 학습되어 있습니다."))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str,
                          idx_close: int, idx_volume: int,
                          analysis_period: int, rate_threshold: int, ratio_threshold: int,
                          min_samples: int, existing_dates_dict: Dict[str, set]) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db: 백테디비 경로
        idx_close: 현재가 인덱스
        idx_volume: 분당거래대금 인덱스
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        ratio_threshold: 급증 임계값
        min_samples: 최소 샘플 수
        existing_dates_dict: 종목별 기존 저장 날짜 딕셔너리 {code: set(dates)}
        return: 종목별 급증 점수 딕셔너리 {code: spike_scores}
        """
        global window_queue

        all_spike_scores = {}
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

                    close_price   = date_data[:, idx_close]
                    volume_data   = date_data[:, idx_volume]
                    ma_volume     = calculate_ma_volume(volume_data, analysis_period)
                    spike_indices = calculate_spike_indices(volume_data, ma_volume, ratio_threshold, analysis_period)

                    spike_groups = {}
                    for idx in spike_indices:
                        multiplier = volume_data[idx] / ma_volume[idx]
                        rounded_multiplier = round(multiplier * 2) / 2
                        if rounded_multiplier not in spike_groups:
                            spike_groups[rounded_multiplier] = []
                        spike_groups[rounded_multiplier].append(idx)

                    spike_scores = {}
                    for multiplier, indices in spike_groups.items():
                        if len(indices) >= min_samples:
                            indices_array = np.array(indices)
                            scores = calculate_spike_score_array(close_price, indices_array,
                                                                 analysis_period, rate_threshold)
                            valid_scores = scores[scores != 0.0]

                            if len(valid_scores) >= min_samples:
                                sample_factor = min(len(valid_scores) / 100.0, 1.0)
                                std_factor    = max(1.0 - float(np.std(valid_scores)) / 50.0, 0.0)
                                confidence    = (sample_factor + std_factor) / 2.0
                                spike_scores[multiplier] = {
                                    'avg_score': round(float(np.mean(valid_scores)), 2),
                                    'max_score': round(float(np.max(valid_scores)), 2),
                                    'min_score': round(float(np.min(valid_scores)), 2),
                                    'std_score': round(float(np.std(valid_scores)), 2),
                                    'sample_count': len(valid_scores),
                                    'confidence_score': round(confidence, 2)
                                }

                    if spike_scores:
                        if code not in all_spike_scores:
                            all_spike_scores[code] = {}
                        all_spike_scores[code][target_date] = spike_scores

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 거래량분석 학습 중 ... [{k+1:02d}/{last:02d}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 거래량분석 학습 실패 - {e}"))

        return all_spike_scores


class VolumeSpikeDatabase:
    """거래량 급증 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str):
        self.table_name   = f'{strategy_gubun}_volume_spike'
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS spike_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold INTEGER NOT NULL,
                    ratio_threshold INTEGER NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    spike_multiplier REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, spike_multiplier, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """
        데이터베이스에 저장된 전체 종목코드 조회
        return: 종목코드 리스트
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_spike_all_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """
        종목의 전체 급증 점수 조회 (최신 날짜 기준)
        code: 종목코드
        return: 급증 강도별 점수 딕셔너리
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT spike_multiplier, avg_score, max_score, min_score, std_score, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash))
            results = cursor.fetchall()

            spike_scores = {}
            for result in results:
                spike_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
            return spike_scores

    def get_spike_code_scores(self, code: str, backtest_date: int) -> Dict[str, Dict[str, float]]:
        """
        백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 급증 점수 조회
        code: 종목코드
        backtest_date: 백테스트 기준 날짜 (YYYYMMDD)
        return: 급증 강도별 점수 딕셔너리
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT spike_multiplier, avg_score, max_score, min_score, std_score, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update < ?)
            ''', (code, self.setting_hash, code, self.setting_hash, backtest_date))
            results = cursor.fetchall()

            spike_scores = {}
            for result in results:
                spike_scores[result[0]] = {
                    'avg_score': result[1],
                    'max_score': result[2],
                    'min_score': result[3],
                    'std_score': result[4],
                    'sample_count': result[5],
                    'confidence_score': result[6]
                }
            return spike_scores

    def save_spike_scores(self, code: str, spike_scores: Dict[str, Dict[str, float]], date: int):
        """
        종목별 급증 점수 저장
        code: 종목코드
        spike_scores: 급증 강도별 점수 딕셔너리
        date: 학습 날짜
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()

            data = [
                (
                    code,
                    spike_multiplier,
                    scores['avg_score'],
                    scores['max_score'],
                    scores['min_score'],
                    scores['std_score'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    self.setting_hash,
                    date
                )
                for spike_multiplier, scores in spike_scores.items()
            ]

            cursor.executemany(f'''
                INSERT OR REPLACE INTO {self.table_name} 
                (code, spike_multiplier, avg_score, max_score, min_score, std_score, sample_count,
                confidence_score, setting_hash, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)

            conn.commit()

    def load_spike_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (analysis_period, rate_threshold, ratio_threshold) 튜플, 데이터가 없으면 (30, 3.0, 20) 반환
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, rate_threshold, ratio_threshold FROM spike_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if not result:
                result = 30, 5, 3

            self.setting_hash = calculate_setting_hash(*result)
            return result

    def save_spike_setting(self, market: int, analysis_period: int, rate_threshold: float, ratio_threshold: int):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        ratio_threshold: 급증 임계값
        """
        with sqlite3.connect(VOLUME_SPIKE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO spike_setting (market, analysis_period, rate_threshold, ratio_threshold) '
                'VALUES (?, ?, ?, ?)',
                (market, analysis_period, rate_threshold, ratio_threshold)
            )
            conn.commit()


def spike_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolumeSpikeDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, ratio_threshold = database.load_spike_setting(ui.market_gubun)
    ui.vsp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vsp_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vsp_comboBoxxx_03.setCurrentText(str(ratio_threshold))


def spike_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    ratio_threshold = int(ui.vsp_comboBoxxx_03.currentText())
    database = VolumeSpikeDatabase(ui.market_info['전략구분'])
    database.save_spike_setting(ui.market_gubun, analysis_period, rate_threshold, ratio_threshold)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def spike_train(ui):
    """급증 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 급증 패턴 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    _ratio_threshold = int(ui.vsp_comboBoxxx_03.currentText())
    database = VolumeSpikeDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, ratio_threshold = database.load_spike_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _ratio_threshold != ratio_threshold:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _spike_train(ui)


@thread_decorator
def _spike_train(ui):
    """스레드로 급증 패턴 학습을 시작한다."""
    ui.learn_running = True
    vs_analyzer = AnalyzerVolumeSpike(ui.market_gubun, ui.market_info)
    vs_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
