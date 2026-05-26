
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

VOLUME_SPIKE_DB = f'{DB_PATH}/volume_spike.db'

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
def _calculate_ma_volume(volume_data: np.ndarray, analysis_period: int) -> np.ndarray:
    """이동평균 거래량 계산 (numba 최적화)"""
    n = len(volume_data)
    ma_volume = np.zeros(n, dtype=np.float64)
    for i in prange(analysis_period - 1, n):
        ma_volume[i] = np.mean(volume_data[i + 1 - analysis_period:i + 1])
    return ma_volume


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_spike_score_array(close_price: np.ndarray, dates: np.ndarray, indices: np.ndarray,
                                 analysis_period: int, rate_threshold: float) -> np.ndarray:
    """거래량 급증 점수 배열 계산 (numba 최적화)"""
    max_scores = len(indices)
    scores = np.zeros(max_scores, dtype=np.float64)
    for i in prange(max_scores):
        idx = indices[i]
        if idx + analysis_period < len(close_price) and dates[idx] == dates[idx + analysis_period]:
            entry_price = close_price[idx]
            exit_max_price = close_price[idx + 1:idx + 1 + analysis_period].max()
            exit_min_price = close_price[idx + 1:idx + 1 + analysis_period].min()
            if abs(exit_max_price - entry_price) >= abs(exit_min_price - entry_price):
                exit_price = exit_max_price
            else:
                exit_price = exit_min_price
            price_change = (exit_price / entry_price - 1) * 100
            score = price_change / rate_threshold * 100
            score = max(-100.0, min(100.0, score))
            scores[i] = score
    return scores[scores != 0.0]


class AnalyzerVolumeSpike:
    """메인 거래량 급증 패턴 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, is_tick: bool,
                 realtime: bool = False, min_samples: int = 20):
        self.spike_database = VolumeSpikeDatabase(market_info['전략구분'], is_tick)
        self.analysis_period, self.rate_threshold = self.spike_database.load_spike_setting(market_gubun)

        self.backtest_db = market_info['백테디비'][is_tick]
        self.factor_list = market_info['팩터목록'][is_tick]
        self.is_tick     = is_tick
        self.min_samples = min_samples
        self.idx_close   = self.factor_list.index('현재가')
        self.idx_volume  = self.factor_list.index('초당거래대금') if is_tick else self.factor_list.index('분당거래대금')
        self.spike_scores: dict[str, dict[float, dict[str, float]]] = {}

        if realtime:
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

    def analyze_current_spike(self, code: str, code_data: np.ndarray) -> Tuple[float, float]:
        """실시간 거래량 분석 및 학습된 점수 반환"""
        volume_spike_score = confidence_score = 0.0

        spike_scores = self.spike_scores.get(code)
        if spike_scores and len(code_data) >= self.analysis_period:
            volume_data = code_data[:, self.idx_volume]
            current_ma_volume = np.mean(volume_data[-self.analysis_period:])
            current_volume = volume_data[-1]

            if current_ma_volume > 0:
                spike_level   = current_volume / current_ma_volume
                rounded_level = round(spike_level * 2) / 2
                score_data = spike_scores.get(rounded_level)
                if score_data:
                    volume_spike_score = score_data['avg_score']
                    confidence_score   = score_data['confidence_score']

        return volume_spike_score, confidence_score

    def analyze_batch_data(self, code: str, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석합니다."""
        date = int(str(code_data[0, 0])[:8])
        self.load_spike_code_scores(code, date)

        n = len(code_data)
        results = np.zeros((n, 2))

        for i in range(self.analysis_period, n):
            window_data = code_data[:i]
            results[i] = list(self.analyze_current_spike(code, window_data))

        return results

    def train_all_codes(self, ui):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}
        with sqlite3.connect(self.spike_database.db_path) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.spike_database.table_name} '
                    f'WHERE code = ? and setting_hash = ?',
                    (code, self.spike_database.setting_hash)
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
                    i, code_chunk, self.backtest_db, self.idx_close, self.idx_volume,
                    self.analysis_period, self.rate_threshold, self.min_samples,
                    existing_dates_dict, self.is_tick, self.spike_database.setting_hash
                )
                for i, code_chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        columns = [
            'code', 'spike_level', 'avg_score', 'max_score', 'min_score', 'std_score',
            'sample_count', 'confidence_score', 'setting_hash', 'last_update'
        ]
        for i, result in enumerate(results):
            if result:
                df = pd.DataFrame(result, columns=columns)
                self.spike_database.save_spike_scores(df)
                total_processed += 1
                ui.windowQ.put((UI_NUM['학습로그'], f'학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]'))

        if total_processed > 0:
            pass_time = now() - start
            ui.windowQ.put((
                UI_NUM['학습로그'],
                f'학습 데이터 저장 완료, {self.spike_database.db_path} -> {self.spike_database.table_name}'
            ))
            ui.windowQ.put((UI_NUM['학습로그'], f'거래량분석 학습 완료, 소요시간[{pass_time}]'))
        else:
            ui.windowQ.put((UI_NUM['학습로그'], '이미 모든 데이터가 학습되어 있습니다.'))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str, idx_close: int, idx_volume: int,
                          analysis_period: int, rate_threshold: int, min_samples: int,
                          existing_dates_dict: Dict[str, set], is_tick: bool, setting_hash: str) -> List[Any]:
        """단일 종목 청크 학습 (멀티프로세싱용)"""
        global window_queue

        all_spike_scores = []
        last = len(code_chunk)

        for k, code in enumerate(code_chunk):
            try:
                with sqlite3.connect(backtest_db) as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'SELECT * FROM "{code}"')
                    results = cursor.fetchall()
                    historical_data = np.array(results)

                datetime_data = historical_data[:, 0]
                all_dates = datetime_data // 1000000 if is_tick else datetime_data // 10000
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

                    dates          = date_data[:, 0] // 1000000 if is_tick else date_data[:, 0] // 10000
                    close_price    = date_data[:, idx_close]
                    volume_data    = date_data[:, idx_volume]
                    ma_volume_data = _calculate_ma_volume(volume_data, analysis_period)

                    groups = {}
                    for idx, (volume, ma_volume) in enumerate(zip(volume_data, ma_volume_data)):
                        if ma_volume > 0.0:
                            level = volume / ma_volume
                            rounded_level = round(level * 2) / 2
                            if rounded_level not in groups:
                                groups[rounded_level] = []
                            groups[rounded_level].append(idx)

                    for level, indices in groups.items():
                        if len(indices) >= min_samples:
                            indices_array = np.array(indices)
                            scores = _calculate_spike_score_array(close_price, dates, indices_array,
                                                                  analysis_period, rate_threshold)

                            if len(scores) >= min_samples:
                                std_scores    = scores.std()
                                sample_factor = min(len(scores) / 100.0, 1.0)
                                std_factor    = max(1.0 - std_scores / 100.0, 0.0)
                                confidence    = (sample_factor + std_factor) / 2.0

                                spike_scores = [
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
                                all_spike_scores.append(spike_scores)

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f'[{i:02d}][{code}] 거래량분석 학습 중 ... [{k+1:02d}/{last:02d}]'))
            except Exception:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['시스템로그'], format_exc()))

        return all_spike_scores


class VolumeSpikeDatabase:
    """거래량 급증 점수 데이터베이스 관리 클래스"""
    def __init__(self, strategy_gubun: str, is_tick: bool):
        self.table_name   = f"{strategy_gubun}_volume_spike_{'tick' if is_tick else 'min'}"
        self.is_tick      = is_tick
        self.db_path      = VOLUME_SPIKE_DB
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS spike_setting (
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
                    spike_level REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    min_score REAL NOT NULL,
                    std_score REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, spike_level, setting_hash, last_update)
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

    def get_spike_all_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """종목의 전체 급증 점수 조회 (최신 날짜 기준)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT spike_level, avg_score, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash))
            results = cursor.fetchall()

            spike_scores = {}
            for result in results:
                spike_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }
            return spike_scores

    def get_spike_code_scores(self, code: str, backtest_date: int) -> Dict[str, Dict[str, float]]:
        """백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 급증 점수 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT spike_level, avg_score, confidence_score 
                FROM {self.table_name} 
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update < ?)
            ''', (code, self.setting_hash, code, self.setting_hash, backtest_date))
            results = cursor.fetchall()

            spike_scores = {}
            for result in results:
                spike_scores[result[0]] = {
                    'avg_score': result[1],
                    'confidence_score': result[2]
                }
            return spike_scores

    def save_spike_scores(self, df: pd.DataFrame):
        """종목별 급증 점수 저장"""
        with sqlite3.connect(self.db_path) as conn:
            df.to_sql(self.table_name, conn, if_exists='append', index=False, chunksize=2000)

    def load_spike_setting(self, market: int) -> tuple:
        """마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        is_tick: 틱 데이터 여부 (기본값 False)
        return: (analysis_period, rate_threshold) 튜플, 데이터가 없으면 (30, 3.0, 20) 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT analysis_period, rate_threshold 
                FROM spike_setting 
                WHERE market = ? AND is_tick = ?
            ''', (market, 1 if self.is_tick else 0)
            )
            result = cursor.fetchone()
            if result:
                analysis_period, rate_threshold = result
            else:
                analysis_period, rate_threshold = 10, 3
                self.save_spike_setting(market, analysis_period, rate_threshold)

            self.setting_hash = _calculate_setting_hash(analysis_period, rate_threshold)
            return analysis_period, rate_threshold

    def save_spike_setting(self, market: int, analysis_period: int, rate_threshold: int):
        """마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석 기간 분
        rate_threshold: 등락율 임계값
        is_tick: 틱 데이터 여부 (기본값 False)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                INSERT OR REPLACE INTO spike_setting 
                (market, is_tick, analysis_period, rate_threshold) 
                VALUES (?, ?, ?, ?)
            ''', (market, 1 if self.is_tick else 0, analysis_period, rate_threshold)
            )
            conn.commit()


def spike_setting_load(ui):
    """세개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolumeSpikeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period, rate_threshold = database.load_spike_setting(ui.market_gubun)
    ui.vsp_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vsp_comboBoxxx_02.setCurrentText(str(rate_threshold))


def spike_setting_save(ui):
    """세개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    from ui.etcetera.etc import send_analyzer_setting_change
    analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    database = VolumeSpikeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    database.save_spike_setting(ui.market_gubun, analysis_period, rate_threshold)
    send_analyzer_setting_change(ui)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def spike_train(ui):
    """급증 패턴 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vsp_comboBoxxx_01.currentText())
    _rate_threshold  = int(ui.vsp_comboBoxxx_02.currentText())
    database = VolumeSpikeDatabase(ui.market_info['전략구분'], ui.dict_set['타임프레임'])
    analysis_period, rate_threshold = database.load_spike_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    ui.windowQ.put((UI_NUM['학습로그'], '거래량분석 학습을 시작합니다.'))
    _spike_train(ui)


@thread_decorator
def _spike_train(ui):
    """스레드로 급증 패턴 학습을 시작한다."""
    ui.learn_running = True
    vs_analyzer = AnalyzerVolumeSpike(ui.market_gubun, ui.market_info, ui.dict_set['타임프레임'])
    vs_analyzer.train_all_codes(ui)
    ui.learn_running = False
