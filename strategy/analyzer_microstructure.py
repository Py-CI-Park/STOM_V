
import numpy as np
from numba import njit
from collections import defaultdict
from typing import Dict, List, Tuple


@njit(cache=True, fastmath=True, parallel=True)
def _calc_analyze_price_levels(quantities: np.ndarray, multiplier: float, min_occurrences: int):
    """가격 레벨별 분석 (Numba JIT 최적화) - 튜플 대신 배열 반환"""
    n_rows, n_cols = quantities.shape
    if n_rows < 3:
        return np.empty((0, 5), dtype=np.float64)

    # 5개 레벨 각각 계산
    total_qtys = np.zeros(n_cols, dtype=np.float64)
    occurrences = np.zeros(n_cols, dtype=np.int32)
    max_qtys = np.zeros(n_cols, np.float64)

    for col in range(n_cols):
        max_val = 0.0
        for row in range(n_rows):
            val = quantities[row, col]
            total_qtys[col] += val
            if val > 0:
                occurrences[col] += 1
            if val > max_val:
                max_val = val
        max_qtys[col] = max_val

    # 의심스러운 패턴 탐지
    suspicious_count = 0
    for col in range(n_cols):
        if occurrences[col] > 0:
            avg_qty = total_qtys[col] / occurrences[col]
            if occurrences[col] >= min_occurrences and max_qtys[col] > avg_qty * multiplier:
                suspicious_count += 1

    if suspicious_count == 0:
        return np.empty((0, 5), dtype=np.float64)

    # 결과 배열 생성
    result = np.empty((suspicious_count, 5), dtype=np.float64)
    idx = 0
    for col in range(n_cols):
        if occurrences[col] > 0:
            avg_qty = total_qtys[col] / occurrences[col]
            if occurrences[col] >= min_occurrences and max_qtys[col] > avg_qty * multiplier:
                score = min(max_qtys[col] / (avg_qty + 1e-8) / 3.0, 10.0)
                result[idx, 0] = float(col)
                result[idx, 1] = avg_qty
                result[idx, 2] = max_qtys[col]
                result[idx, 3] = float(occurrences[col])
                result[idx, 4] = score
                idx += 1

    return result


# noinspection PyUnresolvedReferences
@njit(cache=True, fastmath=True)
def _calc_detect_large_order_changes(quantities: np.ndarray, prices: np.ndarray, threshold: float):
    """대량 주문 변화 감지 (Numba JIT 최적화) - 배열 반환"""
    n_rows, n_cols = quantities.shape
    if n_rows < 2:
        return np.empty((0, 6), dtype=np.float64)

    prev_n = n_rows - 1
    change_count = 0
    max_change_ratio = 0.0

    for row in range(prev_n):
        for col in range(n_cols):
            prev_qty = quantities[row, col]
            curr_qty = quantities[row + 1, col]
            max_qty = max(prev_qty, curr_qty)

            if max_qty > 0:
                change_ratio = abs(curr_qty - prev_qty) / max_qty
                if change_ratio > max_change_ratio:
                    max_change_ratio = change_ratio
                if change_ratio > threshold:
                    change_count += 1

    # 너무 많으면 샘플링
    if change_count > 50:
        result = np.empty((1, 6), dtype=np.float64)
        result[0, 0] = 0.0  # level
        result[0, 1] = 0.0  # price
        result[0, 2] = 0.0  # prev_qty
        result[0, 3] = 0.0  # curr_qty
        result[0, 4] = 0.0  # change_amount
        result[0, 5] = max_change_ratio
        return result

    if change_count == 0:
        return np.empty((0, 6), dtype=np.float64)

    # 결과 배열 생성
    idx = 0
    result = np.empty((change_count, 6), dtype=np.float64)

    for row in range(prev_n):
        for col in range(n_cols):
            prev_qty = quantities[row, col]
            curr_qty = quantities[row + 1, col]
            max_qty = max(prev_qty, curr_qty)

            if max_qty > 0:
                change_ratio = abs(curr_qty - prev_qty) / max_qty
                if change_ratio > threshold:
                    result[idx, 0] = float(col)
                    result[idx, 1] = prices[row + 1, col]
                    result[idx, 2] = prev_qty
                    result[idx, 3] = curr_qty
                    result[idx, 4] = abs(curr_qty - prev_qty)
                    result[idx, 5] = change_ratio
                    idx += 1

    return result


@njit(cache=True, fastmath=True)
def _calc_layering_confidence(levels: np.ndarray):
    """레이어링 신뢰도 계산 (Numba JIT) - levels: (N, 5) 배열"""
    n = levels.shape[0]
    if n == 0:
        return 0.0

    max_suspicion = 0.0
    sum_suspicion = 0.0
    max_occurrences = 0.0

    for i in range(n):
        suspicion = levels[i, 4]
        occurrences = levels[i, 3]
        if suspicion > max_suspicion:
            max_suspicion = suspicion
        sum_suspicion += suspicion
        if occurrences > max_occurrences:
            max_occurrences = occurrences

    avg_suspicion = sum_suspicion / n
    occurrence_weight = min(max_occurrences / 10.0, 1.0)
    confidence = (max_suspicion * 0.7 + avg_suspicion * 0.3) * occurrence_weight

    if confidence > 1.0:
        return 1.0
    return confidence


@njit(cache=True, fastmath=True)
def _calc_spoofing_confidence(changes: np.ndarray):
    """스푸핑 신뢰도 계산 (Numba JIT) - changes: (N, 6) 배열"""
    n = changes.shape[0]
    if n == 0:
        return 0.0

    max_change_ratio = 0.0
    sum_change_ratio = 0.0

    for i in range(n):
        ratio = changes[i, 5]
        if ratio > max_change_ratio:
            max_change_ratio = ratio
        sum_change_ratio += ratio

    avg_change_ratio = sum_change_ratio / n
    change_count_weight = min(n / 5.0, 1.0)
    confidence = (max_change_ratio * 0.7 + avg_change_ratio * 0.3) * change_count_weight

    if confidence > 1.0:
        return 1.0
    return confidence


@njit(cache=True, fastmath=True)
def _calc_detect_iceberg(qtys: np.ndarray, prices: np.ndarray, depletion_threshold: float,
                         price_stable_threshold: float, min_pattern_count: int):
    """아이스버그 주문 탐지 (Numba JIT) - 결과: (N, 6) 배열 (side_idx, level, avg_price, max_count, total_depletion, confidence)"""
    n_rows, n_cols = qtys.shape
    if n_rows < 5:
        return np.empty((0, 6), dtype=np.float64)

    # 최대 20개 결과 저장 가능
    result_count = 0
    max_results = 20
    results = np.empty((max_results, 6), dtype=np.float64)

    for level in range(n_cols):
        # 소진 패턴 탐지
        depletion_indices_list = []
        prev_qty = qtys[0, level]

        for row in range(1, n_rows):
            curr_qty = qtys[row, level]
            qty_change = curr_qty - prev_qty
            price_change = abs(prices[row, level] - prices[row - 1, level])

            # 소진 조건: 수량 감소 > 30% and 가격 안정
            if qty_change < -prev_qty * depletion_threshold and price_change < price_stable_threshold:
                depletion_indices_list.append(row - 1)  # 이전 인덱스 기준
            prev_qty = curr_qty

        depletion_count = len(depletion_indices_list)
        if depletion_count < min_pattern_count:
            continue

        # 연속 그룹 분리 및 최대 길이 계산
        if depletion_count == 0:
            continue

        max_pattern_count = 1
        current_group = 1

        for i in range(1, depletion_count):
            if depletion_indices_list[i] == depletion_indices_list[i - 1] + 1:
                current_group += 1
                if current_group > max_pattern_count:
                    max_pattern_count = current_group
            else:
                current_group = 1

        if max_pattern_count < min_pattern_count:
            continue

        # 총 소진량 계산
        total_depletion = 0.0
        initial_qty = qtys[0, level]

        for idx in depletion_indices_list:
            if idx + 1 < n_rows:
                qty_change = qtys[idx, level] - qtys[idx + 1, level]
                if qty_change > 0:
                    total_depletion += qty_change

        if total_depletion <= initial_qty * 2:
            continue

        # 결과 저장
        if result_count < max_results:
            avg_price = (prices[0, level] + prices[-1, level]) / 2.0
            # 0으로 나누기 방지
            depletion_denom = initial_qty * 3.0 if initial_qty > 0 else 1.0
            confidence = min(max_pattern_count / 5.0, 1.0) * min(total_depletion / depletion_denom, 1.0)
            results[result_count, 0] = 0.0  # side_idx (ask=0, bid=1, 외부에서 설정)
            results[result_count, 1] = float(level)
            results[result_count, 2] = avg_price
            results[result_count, 3] = float(max_pattern_count)
            results[result_count, 4] = total_depletion
            results[result_count, 5] = min(confidence, 1.0)
            result_count += 1

    return results[:result_count]


@njit(cache=True, fastmath=True)
def _calc_detect_stop_hunt(prices: np.ndarray, volumes: np.ndarray, price_threshold: float, vol_threshold: float):
    """스탑로스 털기 패턴 감지 (Numba JIT) - 결과: (N, 6) 배열 (direction, price, change, vol, confidence, idx)"""
    n = len(prices)
    if n < 20:
        return np.empty((0, 6), dtype=np.float64)

    # 평균 거래량 계산
    avg_volume = 0.0
    for i in range(n - 1):
        avg_volume += volumes[i]
    avg_volume = avg_volume / (n - 1) + 1e-8

    # 최대 50개 결과 저장
    result_count = 0
    max_results = 50
    results = np.empty((max_results, 6), dtype=np.float64)

    for i in range(3, n - 4):
        # 가격 변화율
        price_change = (prices[i + 1] - prices[i]) / (prices[i] + 1e-10) * 100.0
        volume_spike = volumes[i + 1] / avg_volume

        # 조건 체크
        if abs(price_change) > price_threshold and volume_spike > vol_threshold:
            # before_trend 계산 (i-3 ~ i)
            before_sum = 0.0
            for j in range(i - 3, i):
                before_sum += (prices[j + 1] - prices[j]) / (prices[j] + 1e-10) * 100.0
            before_trend = before_sum / 3.0

            # after_trend 계산 (i+1 ~ i+4)
            after_sum = 0.0
            for j in range(i + 1, min(i + 4, n - 1)):
                after_sum += (prices[j + 1] - prices[j]) / (prices[j] + 1e-10) * 100.0
            after_trend = after_sum / 3.0

            # reversal 조건
            is_reversal = (before_trend * after_trend < 0) or (abs(after_trend) < abs(before_trend) * 0.3)

            if is_reversal and result_count < max_results:
                direction = 1 if price_change > 0 else -1
                confidence = min(abs(price_change), 1.0) * min(volume_spike / 5.0, 1.0)

                results[result_count, 0] = float(direction)
                results[result_count, 1] = prices[i + 1]
                results[result_count, 2] = price_change
                results[result_count, 3] = volume_spike
                results[result_count, 4] = confidence
                results[result_count, 5] = float(i)
                result_count += 1

    return results[:result_count]


@njit(cache=True, fastmath=True)
def _calc_detect_pump_dump(prices: np.ndarray, volumes: np.ndarray, price_threshold: float,
                           vol_threshold: float, window: int):
    """펌프 앤 덤프 탐지 (Numba JIT) - 결과: (N, 3) 배열 (price_change, volume_spike, confidence)"""
    n = len(prices)
    if n < window + 2:
        return np.empty((0, 3), dtype=np.float64)

    # 이동평균 계산 (window 기반)
    ma_prices = np.zeros(n - window, dtype=np.float64)
    for i in range(n - window):
        sum_price = 0.0
        for j in range(window):
            sum_price += prices[i + j]
        ma_prices[i] = sum_price / window

    # 평균 거래량
    avg_volume = 0.0
    for i in range(n - 1):
        avg_volume += volumes[i]
    avg_volume = avg_volume / (n - 1) + 1e-8

    # 최대 30개 결과 저장
    result_count = 0
    max_results = 30
    results = np.empty((max_results, 3), dtype=np.float64)

    for i in range(len(ma_prices) - 1):
        price_change = (ma_prices[i + 1] - ma_prices[i]) / (ma_prices[i] + 1e-10) * 100.0
        actual_idx = i + window
        volume_spike = volumes[actual_idx] / avg_volume

        # 조건 체크
        if abs(price_change) > price_threshold and volume_spike > vol_threshold and result_count < max_results:
            price_score = min(abs(price_change) / 0.1, 1.0)
            vol_score = min(volume_spike / 5.0, 1.0)
            confidence = (price_score + vol_score) / 2.0

            results[result_count, 0] = price_change
            results[result_count, 1] = volume_spike
            results[result_count, 2] = confidence
            result_count += 1

    return results[:result_count]


class HistoryBuffer:
    """전처리 데이터 히스토리용 numpy ring buffer

    스칼라값과 5단계 호가 데이터를 효율적으로 저장
    """

    __slots__ = ['maxlen', 'ptr', 'count', 'curr_price', 'imbalance', 
                 'ask_prices', 'bid_prices', 'ask_qtys', 'bid_qtys',
                 'buy_volume', 'sell_volume', 'total_volume', 'weighted_depth_ratio']

    def __init__(self, maxlen: int):
        self.maxlen = maxlen
        self.ptr = 0
        self.count = 0

        # 스칼라 데이터용 배열
        self.curr_price = np.zeros(maxlen, dtype=np.float64)
        self.imbalance = np.zeros(maxlen, dtype=np.float64)
        self.buy_volume = np.zeros(maxlen, dtype=np.float64)
        self.sell_volume = np.zeros(maxlen, dtype=np.float64)
        self.total_volume = np.zeros(maxlen, dtype=np.float64)
        self.weighted_depth_ratio = np.zeros(maxlen, dtype=np.float64)

        # 5단계 호가 데이터용 배열 (maxlen x 5)
        self.ask_prices = np.zeros((maxlen, 5), dtype=np.float64)
        self.bid_prices = np.zeros((maxlen, 5), dtype=np.float64)
        self.ask_qtys = np.zeros((maxlen, 5), dtype=np.float64)
        self.bid_qtys = np.zeros((maxlen, 5), dtype=np.float64)

    def append(self, curr_price: float, imbalance: float, buy_volume: float, sell_volume: float,
               total_volume: float, weighted_depth_ratio: float, ask_prices: np.ndarray, bid_prices: np.ndarray,
               ask_qtys: np.ndarray, bid_qtys: np.ndarray):
        """데이터를 추가합니다.
        Args:
            curr_price: 현재가
            imbalance: 불균형
            buy_volume: 매수 수량
            sell_volume: 매도 수량
            ask_prices: 매도 호가 가격 배열
            bid_prices: 매수 호가 가격 배열
            ask_qtys: 매도 호가 수량 배열
            bid_qtys: 매수 호가 수량 배열
            total_volume: 총 수량
            weighted_depth_ratio: 가중 깊이 비율
        """
        idx = self.ptr

        self.curr_price[idx] = curr_price
        self.imbalance[idx] = imbalance
        self.buy_volume[idx] = buy_volume
        self.sell_volume[idx] = sell_volume
        self.total_volume[idx] = total_volume
        self.weighted_depth_ratio[idx] = weighted_depth_ratio

        self.ask_prices[idx] = ask_prices
        self.bid_prices[idx] = bid_prices
        self.ask_qtys[idx] = ask_qtys
        self.bid_qtys[idx] = bid_qtys

        self.ptr = (self.ptr + 1) % self.maxlen
        if self.count < self.maxlen:
            self.count += 1

    def get_prices_array(self) -> np.ndarray:
        """가격 배열을 반환합니다.
        Returns:
            가격 배열
        """
        if self.count < self.maxlen:
            return self.curr_price[:self.count]
        return np.concatenate([self.curr_price[self.ptr:], self.curr_price[:self.ptr]])

    def get_volumes_array(self) -> np.ndarray:
        """수량 배열을 반환합니다.
        Returns:
            수량 배열
        """
        if self.count < self.maxlen:
            return self.total_volume[:self.count]
        return np.concatenate([self.total_volume[self.ptr:], self.total_volume[:self.ptr]])

    def get_qtys_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """호가 수량 배열들을 반환합니다.
        Returns:
            (매도 호가 수량 배열, 매수 호가 수량 배열) 튜플
        """
        if self.count < self.maxlen:
            return self.ask_qtys[:self.count], self.bid_qtys[:self.count]
        ask = np.concatenate([self.ask_qtys[self.ptr:], self.ask_qtys[:self.ptr]], axis=0)
        bid = np.concatenate([self.bid_qtys[self.ptr:], self.bid_qtys[:self.ptr]], axis=0)
        return ask, bid

    def get_prices_arrays(self) -> Tuple[np.ndarray, np.ndarray]:
        """호가 가격 배열들을 반환합니다.
        Returns:
            (매도 호가 가격 배열, 매수 호가 가격 배열) 튜플
        """
        if self.count < self.maxlen:
            return self.ask_prices[:self.count], self.bid_prices[:self.count]
        ask = np.concatenate([self.ask_prices[self.ptr:], self.ask_prices[:self.ptr]], axis=0)
        bid = np.concatenate([self.bid_prices[self.ptr:], self.bid_prices[:self.ptr]], axis=0)
        return ask, bid

    def get_imbalance_array(self) -> np.ndarray:
        """불균형 배열을 반환합니다.
        Returns:
            불균형 배열
        """
        if self.count < self.maxlen:
            return self.imbalance[:self.count]
        return np.concatenate([self.imbalance[self.ptr:], self.imbalance[:self.ptr]])

    def __len__(self) -> int:
        """현재 길이를 반환합니다.
        Returns:
            현재 길이
        """
        return self.count


class AnalyzerMicrostructure:
    """시장 미시구조 분석기 클래스입니다.
    호가 데이터를 분석하여 시장 조작 패턴을 탐지합니다.
    """
    def __init__(self, market_type: str, columns: list, data_cnt: int = 1800, history_cnt: int = 30):
        # 기본 설정
        self._price_risk_cache = {}
        self.market_type = market_type
        self.columns = columns
        self.data_cnt = data_cnt
        self.history_cnt = history_cnt
        self.curr_data = None
        self.data_results = []

        # 데이터 타입별 파라미터 설정
        self._setup_parameters()

        # 칼럼 설정
        self._setup_columns()

        # 분석 히스토리 버퍼
        self.data_history = defaultdict(lambda: HistoryBuffer(self.history_cnt))

        # 상수 캐싱 (반복 생성 회피)
        self._depth_weights = np.array([0.35, 0.25, 0.20, 0.12, 0.08])  # 1~5단계 가중치
        self._log_depth_rate_threshold = np.log(self.params['depth_rate_threshold'])

    def _setup_parameters(self):
        """분석 파라미터를 설정합니다."""
        # 주식 1초 스냅샷 파라미터 (고빈도, 저지연, 변동성 적음)
        if self.market_type == 'stock':
            self.params = {
                'layering_multiplier': 6.0,         # 6배 이상 (높은 신뢰도)
                'layering_occurrences': 3,          # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.8,      # 80% 변화 (높은 임계값)
                'pump_price_threshold': 0.06,       # 6% 가격 변동
                'imbalance_threshold': 0.25,        # 25% 불균형
                'volume_rate_threshold': 3.0,      # 3배 거래량 급증
                'concentration_threshold': 0.6,     # 60% 집중도
                'depth_rate_threshold': 2.0,       # 깊이 비율 2.0
                'pressure_threshold': 0.7,          # 압력 레벨 0.7
            }
        # 코인 1초 스냅샷 파라미터 (고빈도, 고변동성, 24시간)
        elif self.market_type == 'coin':
            self.params = {
                'layering_multiplier': 4.5,         # 4.5배 이상
                'layering_occurrences': 3,          # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.7,      # 70% 변화
                'pump_price_threshold': 0.10,       # 10% 가격 변동 (코인은 변동성 큼)
                'imbalance_threshold': 0.20,        # 20% 불균형
                'volume_rate_threshold': 3.5,      # 3.5배 거래량 급증
                'concentration_threshold': 0.55,    # 55% 집중도
                'depth_rate_threshold': 1.6,       # 깊이 비율 1.6
                'pressure_threshold': 0.65          # 압력 레벨 0.65
            }
        # 해외선물 1초 스냅샷 파라미터 (고빈도, 중간변동성, 24시간+레버리지)
        elif self.market_type == 'future':
            self.params = {
                'layering_multiplier': 5.0,         # 5배 이상 (높은 신뢰도)
                'layering_occurrences': 3,          # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.75,     # 75% 변화 (높은 임계값)
                'pump_price_threshold': 0.07,       # 7% 가격 변동 (레버리지 고려)
                'imbalance_threshold': 0.22,        # 22% 불균형
                'volume_rate_threshold': 3.2,      # 3.2배 거래량 급증
                'concentration_threshold': 0.58,    # 58% 집중도
                'depth_rate_threshold': 1.8,       # 깊이 비율 1.8
                'pressure_threshold': 0.68          # 압력 레벨 0.68
            }

    def _setup_columns(self):
        """컬럼을 설정합니다."""
        # 칼럼 인덱스 매핑 (빠른 접근용)
        col_index = {col: idx for idx, col in enumerate(self.columns)}
        self.idx_curr_price = col_index.get('현재가', 0)
        self.idx_buy_vol    = col_index.get('초당매수수량', 0)
        self.idx_sell_vol   = col_index.get('초당매도수량', 0)
        self.idx_ask_price  = [col_index.get(f'매도호가{i}', 0) for i in range(1, 6)]
        self.idx_ask_qty    = [col_index.get(f'매도잔량{i}', 0) for i in range(1, 6)]
        self.idx_bid_price  = [col_index.get(f'매수호가{i}', 0) for i in range(1, 6)]
        self.idx_bid_qty    = [col_index.get(f'매수잔량{i}', 0) for i in range(1, 6)]

    def update_data(self, code: str, tick_data: np.ndarray):
        """데이터를 업데이트합니다.
        Args:
            code: 종목 코드
            tick_data: 틱 데이터
        """
        self._calculate_processed_data(code, tick_data)

    def get_signal(self, buy_cf: float, sell_cf: float) -> Tuple[str, float, float]:
        """시그널을 반환합니다.
        Args:
            buy_cf: 매수 신뢰도
            sell_cf: 매도 신뢰도
        Returns:
            (시그널, 리스크, 신뢰도) 튜플
        """
        total_risk = self._analyze_risk()
        signal, confidence = self._analyze_signal(buy_cf, sell_cf)
        return signal, confidence, total_risk

    def _calculate_processed_data(self, code: str, tick_data: np.ndarray):
        """전처리 데이터를 계산합니다.
        Args:
            code: 종목 코드
            tick_data: 틱 데이터
        """
        if len(tick_data) < self.history_cnt:
            return

        recent_data  = tick_data[-self.history_cnt:]
        curr_price   = recent_data[-1, self.idx_curr_price]
        buy_volume   = recent_data[-1, self.idx_buy_vol]
        sell_volume  = recent_data[-1, self.idx_sell_vol]
        total_volume = buy_volume + sell_volume

        # 벡터화된 호가 데이터 추출 (리스트-배열 변환 제거)
        ask_prices   = recent_data[-1, self.idx_ask_price]
        ask_qtys     = recent_data[-1, self.idx_ask_qty]
        bid_prices   = recent_data[-1, self.idx_bid_price]
        bid_qtys     = recent_data[-1, self.idx_bid_qty]

        # 깊이 비율, 불균형, VWAP 계산 (벡터화 연산)
        total_ask_qty = np.sum(ask_qtys)
        total_bid_qty = np.sum(bid_qtys)
        # noinspection PyUnresolvedReferences
        depth_ratio   = total_bid_qty / total_ask_qty if total_ask_qty > 0 else 1
        # noinspection PyUnresolvedReferences
        total_qty     = total_bid_qty + total_ask_qty
        # noinspection PyUnresolvedReferences
        imbalance     = (total_bid_qty - total_ask_qty) / total_qty if total_qty > 0 else 0.0

        # 깊이별 가중치 계산 (벡터화 연산)
        weighted_ask_qty = np.dot(ask_qtys, self._depth_weights)
        weighted_bid_qty = np.dot(bid_qtys, self._depth_weights)
        weighted_depth_ratio = weighted_bid_qty / weighted_ask_qty if weighted_ask_qty > 0 else 1

        # 스프레드 트렌드 및 불균형 트렌드 계산 (HistoryBuffer 직접 사용)
        hist_buffer = self.data_history[code]
        hist_buffer.append(
            curr_price, imbalance, buy_volume, sell_volume, total_volume,
            weighted_depth_ratio, ask_prices, bid_prices, ask_qtys, bid_qtys
        )
        if len(hist_buffer) < self.history_cnt:
            return

        # HistoryBuffer에서 imbalance 배열 직접 가져와 트렌드 계산
        imbalances = hist_buffer.get_imbalance_array()[-self.history_cnt:]

        # 단순 선형 추정: (후반부 평균 - 전반부 평균) / (구간 길이 / 2)
        half = self.history_cnt // 2
        first_half_avg  = np.mean(imbalances[:half])
        second_half_avg = np.mean(imbalances[half:])
        imbalance_trend = (second_half_avg - first_half_avg) / half

        # 집중도 점수, 압력 레벨 계산 (벡터화 연산)
        if total_ask_qty > 0:
            ask_concentration = np.sum((ask_qtys / total_ask_qty) ** 2)
        else:
            ask_concentration = 0.0

        if total_bid_qty > 0:
            bid_concentration = np.sum((bid_qtys / total_bid_qty) ** 2)
        else:
            bid_concentration = 0.0

        # noinspection PyUnresolvedReferences
        concentration_score = (bid_concentration + ask_concentration) / 2
        pressure_level      = (imbalance + concentration_score) / 2

        # 각종 조작 패턴 감지 (HistoryBuffer 직접 사용)
        layering     = self._detect_layering(hist_buffer)                                       # 레이어링 감지
        pump_dump    = self._detect_pump_dump(hist_buffer)                                      # 펌프앤덤프 감지
        iceberg      = self._detect_iceberg(hist_buffer)                                        # 아이스버그 감지
        stop_hunt    = self._detect_stop_hunt(hist_buffer)                                      # 스탑헌트 감지
        overall_risk = self._calculate_overall_risk(layering, pump_dump, iceberg, stop_hunt)    # 리스크 평가

        # 최신 데이터 저장 (전략 클래스들에서 참조)
        self.curr_data = {
            'curr_price': curr_price,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_ask_qty': total_ask_qty,
            'total_bid_qty': total_bid_qty,
            'depth_ratio': depth_ratio,
            'weighted_depth_ratio': weighted_depth_ratio,
            'imbalance': imbalance,
            'ask_concentration': ask_concentration,
            'bid_concentration': bid_concentration,
            'imbalance_trend': imbalance_trend,
            'pressure_level': pressure_level,
            'layering': layering,
            'pump_dump': pump_dump,
            'iceberg': iceberg,
            'stop_hunt': stop_hunt,
            'overall_risk': overall_risk
        }

    def _detect_layering(self, hist_buffer: HistoryBuffer) -> List[Tuple]:
        """레이어링을 탐지합니다.
        Args:
            hist_buffer: 히스토리 버퍼
        Returns:
            시그널 리스트
        """
        n = len(hist_buffer)
        if n < 10:
            return []

        # 최근 30개만 사용
        if n > 30:
            n = 30

        # numpy 배열 직접 가져오기
        ask_qtys, bid_qtys = hist_buffer.get_qtys_arrays()
        ask_prices, bid_prices = hist_buffer.get_prices_arrays()

        # 최근 n개만 슬라이싱
        ask_qtys, bid_qtys = ask_qtys[-n:], bid_qtys[-n:]
        ask_prices, bid_prices = ask_prices[-n:], bid_prices[-n:]

        layering_signals = []

        # Numba 함수용 파라미터 준비 (딕셔너리 접근 최소화)
        multiplier = self.params['layering_multiplier']
        min_occurrences = self.params['layering_occurrences']
        threshold = self.params['order_change_threshold']

        # 양쪽을 한번에 처리
        for side_idx, qtys, prices in [(0, ask_qtys, ask_prices), (1, bid_qtys, bid_prices)]:
            if qtys.shape[0] < 3:
                continue

            suspicious_levels_arr = _calc_analyze_price_levels(qtys, multiplier, min_occurrences)
            large_order_changes_arr = _calc_detect_large_order_changes(qtys, prices, threshold)

            # 빠른 조건 체크 (배열 크기로)
            has_suspicious = suspicious_levels_arr.shape[0] > 0
            has_changes = large_order_changes_arr.shape[0] > 0

            if not has_suspicious and not has_changes:
                continue

            # confidence 계산
            if has_suspicious and has_changes:
                layering_conf = _calc_layering_confidence(suspicious_levels_arr)
                spoofing_conf = _calc_spoofing_confidence(large_order_changes_arr)
                combined_confidence = min((layering_conf + spoofing_conf) / 2 * 1.2, 1.0)
            elif has_suspicious:
                combined_confidence = _calc_layering_confidence(suspicious_levels_arr)
            else:
                combined_confidence = _calc_spoofing_confidence(large_order_changes_arr)

            # lightweight 튜플 반환
            layering_signals.append((
                side_idx,
                suspicious_levels_arr.shape[0],
                large_order_changes_arr.shape[0],
                round(combined_confidence, 2)
            ))

        return layering_signals

    def _detect_pump_dump(self, hist_buffer: HistoryBuffer) -> List[Tuple]:
        """펌프 앤 덤프를 탐지합니다.
        Args:
            hist_buffer: 히스토리 버퍼
        Returns:
            시그널 리스트
        """
        prices = hist_buffer.get_prices_array()
        volumes = hist_buffer.get_volumes_array()
        n = len(prices)

        if n < 20:
            return []

        # Numba 함수용 파라미터
        price_threshold = self.params['pump_price_threshold']
        vol_threshold = self.params['volume_rate_threshold']
        window = 5

        results = _calc_detect_pump_dump(prices, volumes, price_threshold, vol_threshold, window)

        # 결과 변환
        pump_dump_signals = []
        for i in range(results.shape[0]):
            pump_dump_signals.append((
                round(float(results[i, 0]), 2),  # price_change
                round(float(results[i, 1]), 2),  # volume_spike
                round(float(results[i, 2]), 2)   # confidence
            ))

        return pump_dump_signals

    def _detect_iceberg(self, hist_buffer: HistoryBuffer) -> List[Tuple]:
        """아이스버그 주문을 탐지합니다.
        Args:
            hist_buffer: 히스토리 버퍼
        Returns:
            시그널 리스트
        """
        n = len(hist_buffer)
        if n < 10:
            return []

        # numpy 배열 직접 가져오기
        ask_qtys, bid_qtys = hist_buffer.get_qtys_arrays()
        ask_prices, bid_prices = hist_buffer.get_prices_arrays()

        # 최근 30개만 사용
        if n > 30:
            ask_qtys, bid_qtys = ask_qtys[-30:], bid_qtys[-30:]
            ask_prices, bid_prices = ask_prices[-30:], bid_prices[-30:]
            n = 30

        if n < 10:
            return []

        iceberg_signals = []
        # 매도/매수 각각 Numba 함수 호출
        for side_idx, (qtys, prices) in enumerate([(ask_qtys, ask_prices), (bid_qtys, bid_prices)]):
            if qtys.shape[0] < 5:
                continue

            side = 'ask' if side_idx == 0 else 'bid'
            results = _calc_detect_iceberg(qtys, prices, 0.3, 0.01, 3)

            # 결과 변환 (side 정보 추가)
            for i in range(results.shape[0]):
                iceberg_signals.append((
                    side,
                    int(results[i, 1]),  # level
                    float(results[i, 2]),  # avg_price
                    int(results[i, 3]),  # max_pattern_count
                    float(results[i, 4]),  # total_depletion
                    round(float(results[i, 5]), 2)  # confidence
                ))

        return iceberg_signals

    def _detect_stop_hunt(self, hist_buffer: HistoryBuffer) -> List[Tuple]:
        """스탑 헌팅을 탐지합니다.
        Args:
            hist_buffer: 히스토리 버퍼
        Returns:
            시그널 리스트
        """
        prices = hist_buffer.get_prices_array()
        volumes = hist_buffer.get_volumes_array()
        n = len(prices)

        if n < 20:
            return []

        results = _calc_detect_stop_hunt(prices, volumes, 0.5, 2.5)

        # 결과 변환
        stop_hunt_signals = []
        for i in range(results.shape[0]):
            stop_hunt_signals.append((
                int(results[i, 0]),  # direction
                float(results[i, 1]),  # price
                round(float(results[i, 2]), 2),  # change
                round(float(results[i, 3]), 2),  # vol
                round(float(results[i, 4]), 2),  # confidence
                int(results[i, 5])  # idx
            ))

        return stop_hunt_signals

    def _calculate_overall_risk(self, layering_signals, pump_dump_signals, iceberg_signals, stop_hunt_signals) -> Dict:
        """전체 리스크를 계산합니다.
        Args:
            layering_signals: 레이어링 시그널
            pump_dump_signals: 펌프 앤 덤프 시그널
            iceberg_signals: 아이스버그 시그널
            stop_hunt_signals: 스탑 헌팅 시그널
        Returns:
            리스크 딕셔너리
        """
        total_signals = len(layering_signals) + len(pump_dump_signals) + len(iceberg_signals) + len(stop_hunt_signals)

        # 모든 신호의 confidence 추출 (모두 튜플 형식)
        all_confidences = (
            [s[3] for s in layering_signals] +      # 튜플: (side, levels_count, changes_count, confidence)
            [s[2] for s in pump_dump_signals] +     # 튜플: (price_change, volume_spike, confidence)
            [s[5] for s in iceberg_signals] +       # 튜플: (side, level, price, count, volume, confidence)
            [s[4] for s in stop_hunt_signals]       # 튜플: (direction, price, change, vol, confidence, idx)
        )

        # 빈 리스트 처리
        max_confidence = max(all_confidences) if all_confidences else 0.0

        # 리스크 레벨 결정
        if total_signals == 0:
            risk_level = 'LOW'
        elif total_signals <= 2 and max_confidence < 0.8 and len(stop_hunt_signals) == 0:
            risk_level = 'MEDIUM'
        elif len(stop_hunt_signals) > 0 and max_confidence > 0.7:
            risk_level = 'HIGH'
        else:
            risk_level = 'HIGH'

        return {
            'risk_level': risk_level,
            'total_signals': total_signals,
            'max_confidence': max_confidence,
            'iceberg_count': len(iceberg_signals),
            'stop_hunt_count': len(stop_hunt_signals)
        }

    def _analyze_risk(self):
        """리스크를 분석합니다.
        Returns:
            리스크 딕셔너리
        """
        if self.curr_data is None:
            return 1.0

        # 고위험 상황이면 보류
        if self.curr_data['overall_risk']['risk_level'] == 'HIGH':
            self.curr_data['total_risk'] = 1.0

        market_risk = self._calculate_market_risk()                     # 시장 리스크
        manipulation_risk = self._calculate_manipulation_risk()         # 조작 리스크
        liquidity_risk = self._calculate_liquidity_risk()               # 유동성 리스크
        total_risk = round((market_risk + manipulation_risk + liquidity_risk) / 3, 2)

        self.curr_data['total_risk'] = total_risk

        return total_risk

    def _analyze_signal(self, buy_cf, sell_cf):
        """시그널을 분석합니다.
        Args:
            buy_cf: 매수 신뢰도
            sell_cf: 매도 신뢰도
        Returns:
            시그널 딕셔너리
        """
        if self.curr_data is None:
            return 'hold', 0.0

        final_signal = self._analyze_order_flow(buy_cf, sell_cf)  # 주문 흐름 분석
        confidence = self._calculate_confidence(final_signal, self.curr_data['total_risk'])  # 신뢰도

        return final_signal, confidence

    def _calculate_market_risk(self) -> float:
        """시장 리스크를 계산합니다.
        Returns:
            시장 리스크
        """

        # 불균형 리스크 (절대값이 클수록 위험)
        imbalance_risk = abs(self.curr_data['imbalance'])

        # 깊이 리스크 (깊이 비율이 임계값에서 멀어질수록 위험)
        depth_risk = min(abs(1 - self.curr_data['depth_ratio']) / self.params['depth_rate_threshold'], 1.0)

        return (imbalance_risk + depth_risk) / 2

    def _calculate_manipulation_risk(self) -> float:
        """조작 리스크를 계산합니다.
        Returns:
            조작 리스크
        """
        risk_level = self.curr_data['overall_risk']['risk_level']
        total_signals = self.curr_data['overall_risk']['total_signals']

        # 리스크 레벨별 기본 리스크
        base_risk = {
            'LOW': 0.1,
            'MEDIUM': 0.5,
            'HIGH': 0.9
        }.get(risk_level, 0.5)

        # 신호 개수에 따른 추가 리스크
        signal_risk = min(total_signals / 8.0, 1.0)
        return (base_risk + signal_risk) / 2

    def _calculate_liquidity_risk(self) -> float:
        """유동성 리스크를 계산합니다.
        Returns:
            유동성 리스크
        """
        # 총 깊이 계산
        curr_price = self.curr_data['curr_price']
        total_depth = (self.curr_data['total_bid_qty'] + self.curr_data['total_ask_qty']) * curr_price

        # 깊이가 5억 이하이면 리스크 증가
        depth_risk = max(0, 1 - total_depth / 500_000_000)

        # 평균 집중도 계산
        avg_concentration = (self.curr_data['bid_concentration'] + self.curr_data['ask_concentration']) / 2

        # 집중도가 임계값 이상이면 리스크 증가
        concentration_risk = min(avg_concentration / self.params['concentration_threshold'], 1.0)

        return (depth_risk + concentration_risk) / 2

    def _analyze_order_flow(self, buy_cf, sell_cf) -> str:
        """주문 흐름을 분석합니다.
        Args:
            buy_cf: 매수 신뢰도
            sell_cf: 매도 신뢰도
        Returns:
            시그널
        """
        # 시장 지표 추출
        imbalance = self.curr_data['imbalance']
        imbalance_trend = self.curr_data['imbalance_trend']
        depth_ratio = self.curr_data['depth_ratio']
        bid_concentration = self.curr_data['bid_concentration']
        ask_concentration = self.curr_data['ask_concentration']
        log_depth_ratio = np.log(depth_ratio) / self._log_depth_rate_threshold if depth_ratio > 0 else 0
        weighted_depth_ratio = self.curr_data['weighted_depth_ratio']

        # 매수 흐름 강도 계산 (연속적인 0.0~1.0 값)
        buy_flow_strength = (
            # 불균형: 매수 우세일수록 높은 값 (0.0~0.30)
            min(1.0, max(0.0, imbalance + 1.0) / 2.0) * 0.30 +
            # 불균형 추세: 매수 추세일수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, imbalance_trend / (self.params['imbalance_threshold'] * 0.1))) * 0.20 +
            # 깊이 비율: 매수 깊이가 깊을수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, log_depth_ratio)) * 0.20 +
            # 가중 깊이 비율: 중요한 신규 지표 (0.0~0.15)
            min(1.0, weighted_depth_ratio) * 0.15 +
            # 집중도: 매수 집중도가 높을수록 높은 값 (0.0~0.15)
            min(1.0, max(0.0, bid_concentration / self.params['concentration_threshold'])) * 0.15
        )

        # 매도 흐름 강도 계산 (연속적인 0.0~1.0 값)
        sell_flow_strength = (
            # 불균형: 매도 우세일수록 높은 값 (0.0~0.30)
            min(1.0, max(0.0, 1.0 - imbalance) / 2.0) * 0.30 +
            # 불균형 추세: 매도 추세일수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, -imbalance_trend / (self.params['imbalance_threshold'] * 0.1))) * 0.20 +
            # 깊이 비율: 매도 깊이가 깊을수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, -log_depth_ratio)) * 0.20 +
            # 가중 깊이 비율: 중요한 신규 지표 (0.0~0.15)
            min(1.0, max(0.0, 1.0 - weighted_depth_ratio)) * 0.15 +
            # 집중도: 매도 집중도가 높을수록 높은 값 (0.0~0.15)
            min(1.0, max(0.0, ask_concentration / self.params['concentration_threshold'])) * 0.15
        )

        # 최종 신호 결정
        if buy_flow_strength > sell_flow_strength + buy_cf:
            return 'buy'
        elif sell_flow_strength > buy_flow_strength + sell_cf:
            return 'sell'
        else:
            return 'hold'

    def _calculate_confidence(self, signal: str, total_risk: float) -> float:
        """신뢰도를 계산합니다.
        Args:
            signal: 시그널
            total_risk: 전체 리스크
        Returns:
            신뢰도
        """
        # 시장 상태에서 주요 지표 추출
        imbalance = abs(self.curr_data['imbalance'])
        imbalance_trend = self.curr_data['imbalance_trend']
        depth_ratio = self.curr_data['depth_ratio']
        pressure_level = self.curr_data['pressure_level']
        weighted_depth_ratio = self.curr_data['weighted_depth_ratio']

        signal_adjustments = {'buy': 1.0, 'sell': 1.0, 'hold': 0.1}
        base_confidence = signal_adjustments[signal] * 0.15
        imbalance_confidence = min(max(0.01, imbalance), 1.0) * 0.15

        if signal == 'buy':
            trend_confidence = min(max(0.01, imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * 0.15
            depth_confidence = min(max(0.01, depth_ratio * (self.params['depth_rate_threshold'] * 0.1)), 1.0) * 0.15
        else:
            trend_confidence = min(max(0.01, -imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * 0.15
            depth_confidence = min(max(0.01, 1 - depth_ratio * (self.params['depth_rate_threshold'] * 0.1)), 1.0) * 0.15

        pressure_confidence = min(max(0.01, pressure_level * (1 / self.params['pressure_threshold'])), 1.0) * 0.15
        risk_confidence = min(max(0.01, 1 - total_risk), 1.0) * 0.15

        if signal == 'buy':
            weighted_depth_confidence = min(max(0.01, weighted_depth_ratio), 1.0) * 0.10
        else:
            weighted_depth_confidence = min(max(0.01, 1.0 - weighted_depth_ratio), 1.0) * 0.10

        final_confidence = (base_confidence + pressure_confidence + imbalance_confidence + 
                            trend_confidence + depth_confidence + weighted_depth_confidence + risk_confidence)

        final_confidence = round(final_confidence, 2)

        return final_confidence

    def clear_code_data(self, code):
        """종목 데이터를 삭제합니다.
        Args:
            code: 종목 코드
        """
        self.curr_data = None
        if code in self.data_history:
            del self.data_history[code]

    def clear_data(self):
        """모든 데이터를 삭제합니다."""
        self.curr_data = None
        self.data_history = defaultdict(lambda: HistoryBuffer(self.history_cnt))
