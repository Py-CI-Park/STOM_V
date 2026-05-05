
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

VOLUME_PROFILE_DB = f'{DB_PATH}/volume_profile.db'

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
def calculate_volume_by_bin(close_price: np.ndarray, volume_data: np.ndarray, price_bins: np.ndarray) -> np.ndarray:
    """가격대별 거래량 계산 (numba 최적화)"""
    volume_by_bin = np.zeros(len(price_bins) - 1)
    for idx in range(len(close_price)):
        price = close_price[idx]
        volume = volume_data[idx]
        bin_idx = 0
        for i in range(len(price_bins) - 1):
            if price_bins[i] <= price < price_bins[i + 1]:
                bin_idx = i
                break
        if 0 <= bin_idx < len(volume_by_bin):
            volume_by_bin[bin_idx] += volume
    return volume_by_bin


@njit(cache=True, fastmath=True)
def calculate_node_scores(close_price: np.ndarray, node_price: float, analysis_period: int,
                          rate_threshold: float) -> tuple:
    """노드별 점수 계산 (numba 최적화)"""
    upward_penetration = 0
    downward_penetration = 0
    bounce_up = 0
    bounce_down = 0
    total_count = 0
    threshold = node_price * rate_threshold / 100
    for idx in range(len(close_price) - analysis_period):
        price = close_price[idx]
        if abs(price - node_price) / node_price * 100 <= rate_threshold:
            total_count += 1
            future_prices = close_price[idx+1:idx+1+analysis_period]
            if future_prices.max() >= node_price + threshold:
                upward_penetration += 1
            elif future_prices.min() <= node_price - threshold:
                downward_penetration += 1
            else:
                if future_prices[-1] > future_prices[0]:
                    bounce_up += 1
                else:
                    bounce_down += 1
    if total_count == 0:
        upward_strength = 0.0
        downward_strength = 0.0
        sample_count = 0
    else:
        upward_strength = (upward_penetration + bounce_up) / total_count
        downward_strength = (downward_penetration + bounce_down) / total_count
        sample_count = total_count
    return upward_strength, downward_strength, sample_count


class AnalyzerVolumeProfile:
    """메인 볼륨 프로파일 분석 통합 클래스"""
    def __init__(self, market_gubun: int, market_info: dict, backtest: bool = False, top_nodes: int = 20):
        """
        초기화
        market_gubun: 마켓 구분 번호
        market_info: 마켓 정보 딕셔너리
        top_nodes: 상위 볼륨 노드 개수 (기본값 20)
        """
        self.volume_database = VolumeProfileDatabase(market_info['전략구분'])
        self.analysis_period, self.rate_threshold, self.price_range_pct = \
            self.volume_database.load_volume_setting(market_gubun)

        self.backtest_db  = market_info['백테디비'][0]
        self.factor_list  = market_info['팩터목록'][0]
        self.top_nodes    = top_nodes
        self.idx_close    = self.factor_list.index('현재가')
        self.idx_volume   = self.factor_list.index('분당거래대금')
        self.volume_nodes = {}
        if not backtest:
            self._load_volume_all_nodes()

    def _load_volume_all_nodes(self):
        """데이터베이스에서 모든 종목의 볼륨 노드 로드"""
        all_codes = self.volume_database.get_all_codes()
        if all_codes:
            for code in all_codes:
                self.volume_nodes[code] = self.volume_database.get_volume_all_scores(code)

    def load_volume_code_nodes(self, code: str, date: int):
        """데이터베이스에서 종목코드의 볼륨 노드 로드"""
        self.volume_nodes[code] = self.volume_database.get_volume_code_scores(code, date)

    def analyze_current_price(self, code: str, current_price: float) -> Tuple[float, float]:
        """
        실시간 가격대 분석 및 학습된 점수 반환
        code: 종목코드
        current_price: 현재가 데이터
        return: 가격대점수, 가격대신뢰도
        """
        volume_profile_score, confidence_score = 0.0, 0.0

        if code in self.volume_nodes:
            nearest_node = None
            min_distance = float('inf')

            for node_price in self.volume_nodes[code].keys():
                distance = abs(current_price - node_price)
                if distance / node_price * 100 <= self.price_range_pct:
                    if distance < min_distance:
                        min_distance = distance
                        nearest_node = node_price

            if nearest_node:
                node_data = self.volume_nodes[code][nearest_node]
                volume_profile_score = node_data['avg_score']
                confidence_score = node_data['confidence_score']

        return volume_profile_score, confidence_score

    def train_all_codes(self, windowQ):
        """전체 종목 학습 수행 (종목 기반 멀티프로세싱)"""
        with sqlite3.connect(self.backtest_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            results = cursor.fetchall()
            code_list = [result[0] for result in results if result[0] != 'moneytop' and '_info' not in result[0]]

        existing_dates_dict = {}
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            for code in code_list:
                cursor.execute(
                    f'SELECT DISTINCT last_update FROM {self.volume_database.table_name} WHERE code = ?',
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
                    self.rate_threshold, self.price_range_pct, self.top_nodes, existing_dates_dict
                )
                for i, chunk in enumerate(code_chunks)
            ]
            results = pool.starmap(self._train_code_chunk, args)

        total_processed = 0
        for i, chunk_results in enumerate(results):
            code_count = 0
            for code, date_scores in chunk_results.items():
                for date, volume_scores in date_scores.items():
                    self.volume_database.save_volume_scores(code, volume_scores, date)
                    code_count += 1
                    total_processed += 1

            if code_count > 0:
                windowQ.put((UI_NUM['학습로그'], f"학습 데이터 저장 중 ... [{i+1:02d}/{actual_processes:02d}]"))

        if total_processed > 0:
            windowQ.put((UI_NUM['학습로그'], "학습 데이터 저장 완료"))
            windowQ.put((UI_NUM['학습로그'], f"{VOLUME_PROFILE_DB} -> {self.volume_database.table_name}"))
            windowQ.put((UI_NUM['학습로그'], f"가격대분석 학습 완료 [{total_processed}]"))
        else:
            windowQ.put((UI_NUM['학습로그'], "이미 모든 데이터가 학습되어 있습니다."))

    @staticmethod
    def _train_code_chunk(i: int, code_chunk: List[str], backtest_db: str,
                          idx_close: int, idx_volume: int,
                          analysis_period: int, rate_threshold: float, price_range_pct: float,
                          top_nodes: int, existing_dates_dict: Dict[str, set]) -> Dict[str, Dict[str, float]]:
        """
        종목 청크별 학습 (프로세스 내에서 실행)
        code_chunk: 종목코드 청크
        backtest_db: 백테디비 경로
        idx_close: 현재가 인덱스
        idx_volume: 분당거래대금 인덱스
        analysis_period: 분석 기간
        rate_threshold: 등락율 임계값
        price_range_pct: 가격대 분할 퍼센트
        top_nodes: 상위 볼륨 노드 개수
        existing_dates_dict: 종목별 기존 저장 날짜 딕셔너리 {code: set(dates)}
        return: 종목별 패턴 점수 딕셔너리 {code: pattern_scores}
        """
        global window_queue

        all_volume_scores = {}
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

                    close_price    = date_data[:, idx_close]
                    volume_data    = date_data[:, idx_volume]
                    min_price      = close_price.min()
                    max_price      = close_price.max()
                    bin_size       = min_price * price_range_pct / 100
                    num_bins       = int((max_price - min_price) / bin_size) + 1
                    price_bins     = np.linspace(min_price, max_price, num_bins)

                    volume_by_bin  = calculate_volume_by_bin(close_price, volume_data, price_bins)
                    bin_centers    = (price_bins[:-1] + price_bins[1:]) / 2
                    sorted_indices = np.argsort(volume_by_bin)[::-1]
                    top_indices    = sorted_indices[:top_nodes]
                    volume_nodes   = [float(bin_centers[idx]) for idx in top_indices]

                    node_scores = {}
                    for node_price in volume_nodes:
                        upward_strength, downward_strength, sample_count = \
                            calculate_node_scores(close_price, node_price, analysis_period, rate_threshold)

                        if sample_count >= 10:
                            final_score = (upward_strength - downward_strength) * 100
                            final_score = max(-100.0, min(100.0, final_score))
                            confidence_score = min(1.0, sample_count / 100) if sample_count >= 10 else 0.0
                            node_scores[node_price] = {
                                'avg_score': round(final_score, 2),
                                'upward_strength': round(upward_strength, 2),
                                'downward_strength': round(downward_strength, 2),
                                'sample_count': sample_count,
                                'confidence_score': round(confidence_score, 2)
                            }

                    if node_scores:
                        if code not in all_volume_scores:
                            all_volume_scores[code] = {}
                        all_volume_scores[code][target_date] = node_scores

                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 가격대분석 학습 중 ... [{k+1:02d}/{last:02d}]"))
            except Exception as e:
                # noinspection PyUnresolvedReferences
                window_queue.put((UI_NUM['학습로그'], f"[{i:02d}][{code}] 가격대분석 학습 실패 - {e}"))

        return all_volume_scores


class VolumeProfileDatabase:
    """볼륨 프로파일 점수 데이터베이스 관리 클래스"""

    def __init__(self, strategy_gubun: str):
        self.table_name   = f'{strategy_gubun}_volume_score'
        self.setting_hash = None
        self._initialize_tables()

    def _initialize_tables(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS volume_setting (
                    market INTEGER NOT NULL,
                    analysis_period INTEGER NOT NULL,
                    rate_threshold REAL NOT NULL,
                    price_range_pct REAL NOT NULL,
                    PRIMARY KEY (market)
                )
            ''')
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    code TEXT NOT NULL,
                    price_level REAL NOT NULL,
                    avg_score REAL NOT NULL,
                    upward_strength REAL NOT NULL,
                    downward_strength REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    confidence_score REAL NOT NULL,
                    setting_hash TEXT NOT NULL,
                    last_update INTEGER NOT NULL,
                    PRIMARY KEY (code, price_level, setting_hash, last_update)
                )
            ''')
            conn.commit()

    def get_all_codes(self) -> List[str]:
        """데이터베이스에 저장된 전체 종목코드 조회"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT DISTINCT code FROM {self.table_name}')
            results = cursor.fetchall()
            return [result[0] for result in results]

    def get_volume_all_scores(self, code: str) -> Dict[str, Dict[str, float]]:
        """종목의 전체 볼륨 프로파일 점수 조회 (최신 날짜 기준)"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT price_level, avg_score, upward_strength, downward_strength, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ?)
            ''', (code, self.setting_hash, code, self.setting_hash))
            results = cursor.fetchall()

            volume_scores = {}
            for result in results:
                volume_scores[result[0]] = {
                    'avg_score': result[1],
                    'upward_strength': result[2],
                    'downward_strength': result[3],
                    'sample_count': result[4],
                    'confidence_score': result[5]
                }
            return volume_scores

    def get_volume_code_scores(self, code: str, backtest_date: int) -> Dict[str, Dict[str, float]]:
        """
        백테스트 날짜 기준으로 해당 날짜 이전의 최신 날짜의 전체 볼륨 프로파일 점수 조회
        code: 종목코드
        backtest_date: 백테스트 기준 날짜 (YYYYMMDD)
        return: 가격대별 점수 딕셔너리
        """
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                SELECT price_level, avg_score, upward_strength, downward_strength, sample_count, confidence_score
                FROM {self.table_name}
                WHERE code = ? AND setting_hash = ? AND last_update = 
                (SELECT MAX(last_update) FROM {self.table_name} WHERE code = ? AND setting_hash = ? AND last_update < ?)
            ''', (code, self.setting_hash, code, self.setting_hash, backtest_date))
            results = cursor.fetchall()

            volume_scores = {}
            for result in results:
                volume_scores[result[0]] = {
                    'avg_score': result[1],
                    'upward_strength': result[2],
                    'downward_strength': result[3],
                    'sample_count': result[4],
                    'confidence_score': result[5]
                }
            return volume_scores

    def save_volume_scores(self, code: str, volume_scores: Dict[str, Dict[str, float]], date: int):
        """종목별 볼륨 프로파일 점수 저장"""
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()

            data = [
                (
                    code,
                    price_level,
                    scores['avg_score'],
                    scores['upward_strength'],
                    scores['downward_strength'],
                    scores['sample_count'],
                    scores['confidence_score'],
                    self.setting_hash,
                    date
                )
                for price_level, scores in volume_scores.items()
            ]

            cursor.executemany(f'''
                INSERT OR REPLACE INTO {self.table_name} 
                (code, price_level, avg_score, upward_strength, downward_strength, sample_count,
                confidence_score, setting_hash, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)

            conn.commit()

    def load_volume_setting(self, market: int) -> tuple:
        """
        마켓번호로 설정값 불러오기
        market: 마켓번호 (1~9)
        return: (price_range_pct, rate_threshold) 튜플, 데이터가 없으면 (30, 10) 반환
        """
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT analysis_period, rate_threshold, price_range_pct FROM volume_setting WHERE market = ?',
                (market,)
            )
            result = cursor.fetchone()
            if not result:
                result = 10, 0.5, 0.33

            self.setting_hash = calculate_setting_hash(*result)
            return result

    def save_volume_setting(self, market: int, analysis_period: int, rate_threshold: float, price_range_pct: float):
        """
        마켓번호로 설정값 저장
        market: 마켓번호 (1~9)
        analysis_period: 분석기간설정
        rate_threshold: 퍼센트설정
        price_range_pct: 분봉설정
        """
        with sqlite3.connect(VOLUME_PROFILE_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO volume_setting (market, analysis_period, rate_threshold, price_range_pct)'
                'VALUES (?, ?, ?, ?)',
                (market, analysis_period, rate_threshold, price_range_pct)
            )
            conn.commit()


def volume_setting_load(ui):
    """두개의 콤보박스를 현재 거래소의 설정값으로 로딩한다."""
    database = VolumeProfileDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, price_range_pct = database.load_volume_setting(ui.market_gubun)
    ui.vpf_comboBoxxx_01.setCurrentText(str(analysis_period))
    ui.vpf_comboBoxxx_02.setCurrentText(str(rate_threshold))
    ui.vpf_comboBoxxx_03.setCurrentText(str(price_range_pct))


def volume_setting_save(ui):
    """두개의 콤보박스 텍스트를 현재 거래소의 설정값으로 저장한다."""
    analysis_period = int(ui.vpf_comboBoxxx_01.currentText())
    rate_threshold  = float(ui.vpf_comboBoxxx_02.currentText())
    price_range_pct = float(ui.vpf_comboBoxxx_03.currentText())
    database = VolumeProfileDatabase(ui.market_info['전략구분'])
    database.save_volume_setting(ui.market_gubun, analysis_period, rate_threshold, price_range_pct)
    QMessageBox.information(ui.dialog_pattern, '저장완료', random.choice(famous_saying))


def volume_profile_train(ui):
    """볼륨 프로파일 학습을 시작한다. 스레드로 구동하여 UI멈춤을 방지한다."""
    if ui.learn_running:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 볼륨 프로파일 학습이 진행중입니다.\n')
        return

    _analysis_period = int(ui.vpf_comboBoxxx_01.currentText())
    _rate_threshold  = float(ui.vpf_comboBoxxx_02.currentText())
    _price_range_pct = float(ui.vpf_comboBoxxx_03.currentText())
    database = VolumeProfileDatabase(ui.market_info['전략구분'])
    analysis_period, rate_threshold, price_range_pct = database.load_volume_setting(ui.market_gubun)

    if _analysis_period != analysis_period or _rate_threshold != rate_threshold or _price_range_pct != price_range_pct:
        QMessageBox.critical(ui.dialog_pattern, '오류 알림', '현재 콤보박스 선택과 저장된 값이 다릅니다.\n저장 후 재실행하십시오.\n')
        return

    _volume_profile_train(ui)


@thread_decorator
def _volume_profile_train(ui):
    """스레드로 볼륨 프로파일 학습을 시작한다."""
    ui.learn_running = True
    vf_analyzer = AnalyzerVolumeProfile(ui.market_gubun, ui.market_info)
    vf_analyzer.train_all_codes(ui.windowQ)
    ui.learn_running = False
