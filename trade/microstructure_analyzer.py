
import os
import sys
import numpy as np
from typing import Dict, List, Tuple
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except:
    pass
from utility.setting_base import list_stock_tick, list_coin_tick


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

    def append(self, data: dict):
        """데이터 추가"""
        idx = self.ptr

        self.curr_price[idx] = data['curr_price']
        self.imbalance[idx] = data['imbalance']
        self.buy_volume[idx] = data['buy_volume']
        self.sell_volume[idx] = data['sell_volume']
        self.total_volume[idx] = data['total_volume']
        self.weighted_depth_ratio[idx] = data['weighted_depth_ratio']

        self.ask_prices[idx] = data['ask_prices']
        self.bid_prices[idx] = data['bid_prices']
        self.ask_qtys[idx] = data['ask_qtys']
        self.bid_qtys[idx] = data['bid_qtys']

        self.ptr = (self.ptr + 1) % self.maxlen
        if self.count < self.maxlen:
            self.count += 1

    def get_recent(self, n: int):
        """최근 n개 데이터를 딕셔너리 리스트로 반환 (최적화 버전)"""
        if n > self.count:
            n = self.count

        if n == 0:
            return []

        # 인덱스 계산 (벡터화)
        indices = np.arange(n)
        buffer_indices = (self.ptr - n + indices) % self.maxlen

        # numpy 배열 슬라이싱으로 한번에 데이터 추출
        curr_prices = self.curr_price[buffer_indices]
        imbalances = self.imbalance[buffer_indices]
        ask_prices_data = self.ask_prices[buffer_indices]
        bid_prices_data = self.bid_prices[buffer_indices]
        ask_qtys_data = self.ask_qtys[buffer_indices]
        bid_qtys_data = self.bid_qtys[buffer_indices]
        buy_volumes = self.buy_volume[buffer_indices]
        sell_volumes = self.sell_volume[buffer_indices]
        total_volumes = self.total_volume[buffer_indices]
        weighted_depth_ratios = self.weighted_depth_ratio[buffer_indices]

        # 결과 생성 (tolist() 호출 최소화)
        result = []
        for i in range(n):
            result.append({
                'curr_price': curr_prices[i],
                'imbalance': imbalances[i],
                'ask_prices': ask_prices_data[i].tolist(),
                'bid_prices': bid_prices_data[i].tolist(),
                'ask_qtys': ask_qtys_data[i].tolist(),
                'bid_qtys': bid_qtys_data[i].tolist(),
                'buy_volume': buy_volumes[i],
                'sell_volume': sell_volumes[i],
                'total_volume': total_volumes[i],
                'weighted_depth_ratio': weighted_depth_ratios[i]
            })
        return result

    def get_all(self):
        """모든 데이터 반환"""
        return self.get_recent(self.count)

    def get_prices_array(self) -> np.ndarray:
        """가격 배열 직접 반환 (펌프덤프용)"""
        if self.count < self.maxlen:
            return self.curr_price[:self.count]
        # 순환 래핑된 경우 순서 재정렬
        return np.concatenate([
            self.curr_price[self.ptr:],
            self.curr_price[:self.ptr]
        ])

    def get_volumes_array(self) -> np.ndarray:
        """거래량 배열 직접 반환 (패턴 분석용)"""
        if self.count < self.maxlen:
            return self.total_volume[:self.count]
        return np.concatenate([
            self.total_volume[self.ptr:],
            self.total_volume[:self.ptr]
        ])

    def __len__(self) -> int:
        return self.count


class DataBuffer:
    """numpy 기반 고정 크기 링 버퍼"""

    __slots__ = ['data', 'ptr', 'count', 'maxlen', 'n_cols']

    def __init__(self, maxlen: int, n_cols: int):
        self.maxlen = maxlen
        self.n_cols = n_cols
        self.data = np.zeros((maxlen, n_cols), dtype=np.float64)
        self.ptr = 0    # 다음 쓰기 위치
        self.count = 0  # 실제 데이터 개수

    def append(self, value: np.ndarray):
        """데이터 추가 (링 버퍼)"""
        self.data[self.ptr] = value
        self.ptr = (self.ptr + 1) % self.maxlen
        if self.count < self.maxlen:
            self.count += 1

    def get_recent(self, n: int) -> np.ndarray:
        """최근 n개 데이터 뷰 반환 (복사 없음)"""
        if n > self.count:
            n = self.count

        # 순환 래핑 고려하여 최근 데이터 위치 계산
        start = (self.ptr - n) % self.maxlen
        end = (self.ptr - 1) % self.maxlen

        if start <= end:
            return self.data[start:end+1]
        else:
            # 순환 래핑 경우: 두 구간 합침
            return np.concatenate([self.data[start:], self.data[:end+1]], axis=0)

    def get_all(self) -> np.ndarray:
        """모든 데이터 반환 (최신순)"""
        return self.get_recent(self.count)

    def __len__(self) -> int:
        return self.count


class MicrostructureAnalyzer:
    def __init__(self, market_type: str = 'stock', data_cnt: int = 1800, history_cnt: int = 30):
        """
        초기화

        Args:
            market_type: 'stock', 'coin', 'future' (시장 종류)
            data_cnt: 종목별 최대 히스토리 저장 크기 (슬라이딩 윈도우)
            history_cnt: 전처리 데이터 히스토리 크기
        """
        # 기본 설정
        self.market_type = market_type
        self.data_cnt = data_cnt
        self.history_cnt = history_cnt
        self.curr_data = None
        self.data_results = []

        # 데이터 타입별 파라미터 설정
        self._setup_parameters()

        # 칼럼 설정
        self._setup_columns()

        # 종목코드별 데이터 저장소 (Ring Buffer로 변경)
        self.data_buffers: Dict[str, DataBuffer] = {}
        self.data_history: Dict[str, HistoryBuffer] = {}

        # 상수 캐싱 (반복 생성 회피)
        self._depth_weights = np.array([0.35, 0.25, 0.20, 0.12, 0.08])  # 1~5단계 가중치
        self._log_depth_ratio_threshold = np.log(self.params['depth_ratio_threshold'])
        self._depth_weights_reshaped = self._depth_weights.reshape(1, 5)  # 브로드캐스팅용

    def _setup_parameters(self):
        """
        시장 종류와 데이터 타입에 따른 파라미터 설정
        주식/코인/해외선물 × 1초스냅샷
        """
        # 주식 1초 스냅샷 파라미터 (고빈도, 저지연, 변동성 적음)
        if self.market_type == 'stock':
            self.params = {
                'layering_multiplier': 6.0,         # 6배 이상 (높은 신뢰도)
                'layering_occurrences': 3,          # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.8,      # 80% 변화 (높은 임계값)
                'pump_price_threshold': 0.06,       # 6% 가격 변동
                'imbalance_threshold': 0.25,        # 25% 불균형
                'volume_spike_threshold': 3.0,      # 3배 거래량 급증
                'concentration_threshold': 0.6,     # 60% 집중도
                'depth_ratio_threshold': 2.0,       # 깊이 비율 2.0
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
                'volume_spike_threshold': 3.5,      # 3.5배 거래량 급증
                'concentration_threshold': 0.55,    # 55% 집중도
                'depth_ratio_threshold': 1.6,       # 깊이 비율 1.6
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
                'volume_spike_threshold': 3.2,      # 3.2배 거래량 급증
                'concentration_threshold': 0.58,    # 58% 집중도
                'depth_ratio_threshold': 1.8,       # 깊이 비율 1.8
                'pressure_threshold': 0.68          # 압력 레벨 0.68
            }

    def _setup_columns(self):
        """
        시장 및 데이터 타입에 따른 칼럼 설정
        """
        # 시장 종류에 따라 칼럼 목록 선택
        if self.market_type == 'stock':
            self.columns = list_stock_tick
        else:
            self.columns = list_coin_tick

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
        """
        데이터 전처리, 시장구조분석

        Args:
            code: 종목코드
            tick_data: 1차원 numpy 배열 (실시간 데이터)
        """
        # 종목코드별 Ring Buffer 생성 (최초 접근 시)
        if code not in self.data_buffers:
            self.data_buffers[code] = DataBuffer(self.data_cnt, len(tick_data))
        
        # Ring Buffer에 실시간 데이터 추가
        self.data_buffers[code].append(tick_data)
        
        # 데이터 전처리, 시장구조분석
        self._calculate_processed_data(code)

    def get_signal(self, code: str, buy_cf: float, sell_cf: float) -> Tuple[str, float, float]:
        """
        리스크분석, 신호 생성

        Args:
            code: 종목코드
            buy_cf: 매수 신호 생성용 계수
            sell_cf: 매도 신호 생성용 계수

        Returns:
            Tuple[str, float, float]: (신호타입, 신뢰도, 리스크)
        """
        # 리스크분석
        total_risk = self._analyze_risk(code)
        # 시그널 및 신뢰도 계산
        signal, confidence = self._analyze_signal(buy_cf, sell_cf)
        return signal, confidence, total_risk

    def _calculate_processed_data(self, code: str):
        """
        데이터 전처리, 시장구조분석 (Ring Buffer 최적화 버전)

        Args:
            code: 종목코드
        """
        ring_buffer = self.data_buffers[code]
        if len(ring_buffer) < self.history_cnt:
            return

        # Ring Buffer에서 최근 데이터 뷰 가져오기 (복사 없음)
        recent_data = ring_buffer.get_recent(self.history_cnt)
        curr_price  = recent_data[-1, self.idx_curr_price]

        # 거래량 관련 계산 (캐싱된 인덱스 사용)
        buy_volume   = recent_data[-1, self.idx_buy_vol]
        sell_volume  = recent_data[-1, self.idx_sell_vol]
        total_volume = buy_volume + sell_volume

        # 마지막 호가 데이터 추출 (5단계 호가) - 캐싱된 인덱스 사용
        ask_prices = [recent_data[-1, idx] for idx in self.idx_ask_price]
        ask_qtys   = [recent_data[-1, idx] for idx in self.idx_ask_qty]
        bid_prices = [recent_data[-1, idx] for idx in self.idx_bid_price]
        bid_qtys   = [recent_data[-1, idx] for idx in self.idx_bid_qty]

        # 깊이 비율, 불균형, VWAP 계산
        total_ask_qty = sum(ask_qtys)
        total_bid_qty = sum(bid_qtys)
        depth_ratio   = total_bid_qty / total_ask_qty if total_ask_qty > 0 else 1
        total_qty     = total_bid_qty + total_ask_qty
        imbalance     = (total_bid_qty - total_ask_qty) / total_qty if total_qty > 0 else 0.0

        # 깊이별 가중치 계산 (벡터화 연산)
        ask_qtys_array = np.array(ask_qtys)
        bid_qtys_array = np.array(bid_qtys)
        weighted_ask_qty = np.dot(ask_qtys_array, self._depth_weights)
        weighted_bid_qty = np.dot(bid_qtys_array, self._depth_weights)
        weighted_depth_ratio = weighted_bid_qty / weighted_ask_qty if weighted_ask_qty > 0 else 1

        # 히스토리 데이터 저장 (DataHistoryBuffer 사용)
        if code not in self.data_history:
            self.data_history[code] = HistoryBuffer(self.history_cnt)
        
        self.data_history[code].append({
            'curr_price': curr_price,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': total_volume,
            'ask_prices': ask_prices,
            'bid_prices': bid_prices,
            'ask_qtys': ask_qtys,
            'bid_qtys': bid_qtys,
            'imbalance': imbalance,
            'weighted_depth_ratio': weighted_depth_ratio
        })

        # 스프레드 트렌드 및 불균형 트렌드 계산
        hist_buffer = self.data_history[code]
        if len(hist_buffer) < self.history_cnt:
            return

        # DataHistoryBuffer에서 최근 데이터 가져오기
        data_history = hist_buffer.get_recent(self.history_cnt)

        # 최근 히스토리 기준 이동평균 트렌드 계산 (polyfit 대체)
        imbalances = [d['imbalance'] for d in data_history]
        # 단순 선형 추정: (후반부 평균 - 전반부 평균) / (구간 길이 / 2)
        half = self.history_cnt // 2
        first_half_avg  = sum(imbalances[:half]) / half
        second_half_avg = sum(imbalances[half:]) / (self.history_cnt - half)
        imbalance_trend = (second_half_avg - first_half_avg) / half

        # 집중도 점수, 압력 레벨 계산
        ask_concentration   = sum((aq / total_ask_qty) ** 2 if total_ask_qty > 0 else 0 for aq in ask_qtys)
        bid_concentration   = sum((bq / total_bid_qty) ** 2 if total_bid_qty > 0 else 0 for bq in bid_qtys)
        concentration_score = (bid_concentration + ask_concentration) / 2
        pressure_level      = (imbalance + concentration_score) / 2

        # 각종 조작 패턴 감지 (data_history 공유)
        layering     = self._detect_layering(data_history)                      # 레이어링 감지
        # 펌프앤덤프 감지 - numpy 배열 직접 사용
        pump_dump    = self._detect_pump_dump(hist_buffer)                      # 펌프앤덤프 감지
        overall_risk = self._calculate_overall_risk(layering, pump_dump)        # 리스크 평가

        # 실제 체결 데이터 분석 (data_history 공유)
        # 거래량 패턴 분석 - numpy 배열 직접 사용
        volume_pattern = self._analyze_volume_pattern(hist_buffer)              # 거래량 패턴 분석
        trade_ratio    = self._calculate_trade_ratio(buy_volume, sell_volume)   # 매수/매도 체결 비율

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
            'overall_risk': overall_risk,
            'volume_pattern': volume_pattern,
            'trade_ratio': trade_ratio
        }

    def _detect_layering(self, data_history: list) -> List[Dict]:
        """
        레이어링 조작 감지
        레이어링: 특정 가격대에 여러 호가를 걸어놓고
        시장 참여자들에게 위신호를 주는 조작 행위
            
        Returns:
            List[Dict]: 감지된 레이어링 신호 목록
        """
        layering_signals = []

        # 매도호가와 매수호가 각각 분석
        for side in ['ask', 'bid']:  # ask: 매도, bid: 매수
            suspicious_levels = self._analyze_price_levels(data_history, side)
            large_order_changes = self._detect_large_order_changes(data_history, side)

            # 의심스러운 패턴이 있는 경우
            if suspicious_levels or large_order_changes:
                # 레이어링 신뢰도 계산
                layering_confidence = self._calculate_layering_confidence(suspicious_levels)
                # 스푸핑 신뢰도 계산
                spoofing_confidence = self._calculate_spoofing_confidence_from_changes(large_order_changes)

                # 두 신뢰도 결합 (둘 다 감지되면 가중치 증가)
                combined_confidence = max(layering_confidence, spoofing_confidence)
                if suspicious_levels and large_order_changes:
                    combined_confidence = min((layering_confidence + spoofing_confidence) / 2 * 1.2, 1.0)

                layering_signals.append({
                    'type': 'layering',
                    'side': side,
                    'levels': suspicious_levels,
                    'large_changes': large_order_changes,
                    'confidence': combined_confidence
                })

        return layering_signals

    def _analyze_price_levels(self, data_history: List, side: str) -> List[Dict]:
        """
        가격 레벨별 분석 (벡터화 최적화 버전)
        특정 가격에 반복적으로 대량 주문이 있는지 분석
        호가는 5단계로 고정되어 있어 리스트 인덱스로 최적화

        Args:
            data_history: 호가 데이터 목록
            side: 'ask'(매도) 또는 'bid'(매수)
        Returns:
            List[Dict]: 의심스러운 가격 레벨 목록
        """
        if not data_history:
            return []

        # numpy 배열로 데이터 변환 (벡터화 연산용)
        n = len(data_history)
        quantities_matrix = np.zeros((n, 5), dtype=np.float64)

        # 데이터를 numpy 배열로 한번에 변환
        for i, data in enumerate(data_history):
            qtys = data['ask_qtys'] if side == 'ask' else data['bid_qtys']
            quantities_matrix[i] = qtys

        # 벡터화 연산으로 통계 계산
        total_qtys = np.sum(quantities_matrix, axis=0)
        occurrences = np.sum(quantities_matrix > 0, axis=0)
        avg_qtys = np.divide(total_qtys, occurrences, out=np.zeros_like(total_qtys), where=occurrences > 0)
        max_qtys = np.max(quantities_matrix, axis=0)

        # 의심스러운 패턴 탐지 (벡터화)
        multiplier = self.params['layering_multiplier']
        min_occurrences = self.params['layering_occurrences']

        suspicious_mask = (occurrences >= min_occurrences) & (max_qtys > avg_qtys * multiplier)

        suspicious_levels = []
        for level in range(5):
            if suspicious_mask[level]:
                suspicious_levels.append({
                    'level': level,
                    'avg_quantity': avg_qtys[level],
                    'max_quantity': max_qtys[level],
                    'occurrences': int(occurrences[level]),
                    'suspicion_score': min(max_qtys[level] / (avg_qtys[level] + 1e-8) / 3, 10.0)
                })

        return suspicious_levels

    def _detect_large_order_changes(self, data_history: List, side: str) -> List[Dict]:
        """
        대량 주문 변화 감지 (벡터화 최적화 버전)
        주문량이 갑자기 크게 변하는 경우를 감지 (스푸핑의 특징)

        Args:
            data_history: 호가 데이터 목록
            side: 'ask'(매도) 또는 'bid'(매수)

        Returns:
            List[Dict]: 대량 주문 변화 목록
        """
        if len(data_history) < 2:
            return []

        changes = []
        threshold = self.params['order_change_threshold']

        # numpy 배열로 데이터 변환 (벡터화 연산용)
        n = len(data_history)
        quantities_matrix = np.zeros((n, 5), dtype=np.float64)
        prices_matrix = np.zeros((n, 5), dtype=np.float64)

        for i, data in enumerate(data_history):
            if side == 'ask':
                quantities_matrix[i] = data['ask_qtys']
                prices_matrix[i] = data['ask_prices']
            else:
                quantities_matrix[i] = data['bid_qtys']
                prices_matrix[i] = data['bid_prices']

        # 벡터화 연산으로 변화량 계산
        prev_quantities = quantities_matrix[:-1]
        curr_quantities = quantities_matrix[1:]
        curr_prices = prices_matrix[1:]

        # 변화량 계산 (벡터화)
        qty_changes = np.abs(curr_quantities - prev_quantities)
        max_qtys = np.maximum(prev_quantities, curr_quantities)

        # 임계값 초과 여부 마스크 (0이 아닌 값만 고려)
        valid_mask = max_qtys > 0
        change_ratio_mask = (qty_changes / max_qtys) > threshold
        significant_changes = valid_mask & change_ratio_mask

        # 결과 생성
        for i in range(n - 1):
            for level in range(5):
                if significant_changes[i, level]:
                    changes.append({
                        'level': level,
                        'price': curr_prices[i, level],
                        'prev_quantity': prev_quantities[i, level],
                        'curr_quantity': curr_quantities[i, level],
                        'change_amount': qty_changes[i, level],
                        'change_ratio': qty_changes[i, level] / max_qtys[i, level]
                    })

        return changes

    def _calculate_layering_confidence(self, levels: List[Dict]) -> float:
        """
        레이어링 신뢰도 계산

        Args:
            levels: 의심스러운 가격 레벨 목록

        Returns:
            float: 레이어링 신뢰도 (0.0 - 1.0)
        """
        if not levels: return 0.0

        max_suspicion_score = max(level['suspicion_score'] for level in levels)
        avg_suspicion_score = sum(level['suspicion_score'] for level in levels) / len(levels)
        max_occurrences = max(level['occurrences'] for level in levels)
        occurrence_weight = min(max_occurrences / 10.0, 1.0)

        confidence = (max_suspicion_score * 0.7 + avg_suspicion_score * 0.3) * occurrence_weight
        return min(confidence, 1.0)

    def _calculate_spoofing_confidence_from_changes(self, changes: List[Dict]) -> float:
        """
        변동 기반 스푸핑 신뢰도 계산

        Args:
            changes: 대량 주문 변화 목록

        Returns:
            float: 스푸핑 신뢰도 (0.0 - 1.0)
        """
        if not changes: return 0.0

        max_change_ratio = max(change['change_ratio'] for change in changes)
        avg_change_ratio = sum(change['change_ratio'] for change in changes) / len(changes)
        change_count_weight = min(len(changes) / 5.0, 1.0)
        confidence = (max_change_ratio * 0.7 + avg_change_ratio * 0.3) * change_count_weight
        return min(confidence, 1.0)

    def _detect_pump_dump(self, hist_buffer: HistoryBuffer) -> List[Dict]:
        """
        펌프 앤 덤프 탐지 (DataHistoryBuffer 최적화 버전)
        펌프 앤 덤프: 가격을 인위적으로 끌어올린 후 대량 매도하는 조작

        Args:
            hist_buffer: DataHistoryBuffer 인스턴스

        Returns:
            List[Dict]: 감지된 펌프 앤 덤프 신호 목록
        """
        pump_dump_signals = []

        # numpy 배열 직접 가져오기 (리스트컴프리헨션 제거)
        prices = hist_buffer.get_prices_array()
        volumes = hist_buffer.get_volumes_array()
        n = len(prices)
        
        if n < 2:
            return pump_dump_signals

        # 가격 변화율 계산 (%) - 벡터화
        price_changes = np.diff(prices) / (prices[:-1] + 1e-10) * 100

        # 거래량 급증 감지 (벡터화)
        avg_volume = np.mean(volumes)
        # noinspection PyTypeChecker
        volume_spikes = volumes / (avg_volume + 1e-8)

        # 각 시점별 펌프 앤 덤프 패턴 확인
        threshold = self.params['pump_price_threshold']
        vol_threshold = self.params['volume_spike_threshold']

        for i in range(len(price_changes)):
            # 가격 변동이 임계값을 초과하고 거래량이 급증한 경우
            if abs(price_changes[i]) > threshold and volume_spikes[i] > vol_threshold:
                # 펌프 앤 덤프 패턴이 맞는지 확인
                if self._is_pump_dump_pattern(prices, i):
                    pump_dump_signals.append({
                        'type': 'pump_dump',
                        'price_change': price_changes[i],
                        'volume_spike': volume_spikes[i],
                        'confidence': self._calculate_pump_confidence(price_changes[i], volume_spikes[i])
                    })

        return pump_dump_signals

    def _is_pump_dump_pattern(self, prices: np.ndarray, index: int) -> bool:
        """
        펌프 앤 덤프 패턴 확인

        Args:
            prices: 가격 배열
            index: 확인할 인덱스

        Returns:
            bool: 펌프 앤 덤프 패턴이면 True
        """
        # 데이터가 충분하지 않으면 판단 불가
        if index < 10:
            return False

        window = 10
        if index + window < len(prices):
            before = prices[index - window:index]   # 이전 10개
            after = prices[index:index + window]    # 이후 10개

            # 평균 한 번만 계산
            before_mean = np.mean(before)
            # 이후 평균가가 이전 평균가보다 2% 이상 하락하고,
            # 현재가가 이전 평균가보다 2% 이상 상승한 경우
            # noinspection PyTypeChecker
            if np.mean(after) < before_mean * 0.98 and prices[index] > before_mean * 1.02:
                return True

        return False

    def _calculate_pump_confidence(self, price_change: float, volume_spike: float) -> float:
        """
        펌프 앤 덤프 신뢰도 계산

        Args:
            price_change: 가격 변화율 (%)
            volume_spike: 거래량 급증 비율

        Returns:
            float: 펌프 앤 덤프 신뢰도 (0.0 - 1.0)
        """
        price_score = min(abs(price_change) / 0.1, 1.0)
        volume_score = min(volume_spike / 5.0, 1.0)
        return (price_score + volume_score) / 2.0

    def _calculate_overall_risk(self, layering_signals, pump_dump_signals) -> Dict:
        """
        종합 리스크 평가 (최적화 버전)

        Args:
            layering_signals: 레이어링 신호 목록
            pump_dump_signals: 펌프 앤 덤프 신호 목록

        Returns:
            Dict: 종합 리스크 정보
        """
        # 총 신호 개수 및 최고 신뢰도 한 번에 계산
        total_signals = len(layering_signals) + len(pump_dump_signals)
        max_confidence = 0.0

        # 레이어링 신호에서 최대 신뢰도 검색
        for signal in layering_signals:
            conf = signal.get('confidence', 0)
            if conf > max_confidence:
                max_confidence = conf

        # 펌프덤프 신호에서 최대 신뢰도 검색
        for signal in pump_dump_signals:
            conf = signal.get('confidence', 0)
            if conf > max_confidence:
                max_confidence = conf

        # 리스크 레벨 결정
        if total_signals == 0:
            risk_level = 'LOW'
        elif total_signals <= 2 and max_confidence < 0.8:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'

        return {
            'risk_level': risk_level,
            'total_signals': total_signals,
            'max_confidence': max_confidence
        }

    def _analyze_volume_pattern(self, hist_buffer: HistoryBuffer) -> Dict:
        """
        거래량 패턴 분석 (DataHistoryBuffer 최적화 버전)
        시간에 따른 거래량 변화 패턴을 분석하여 이상 징후 감지

        Args:
            hist_buffer: DataHistoryBuffer 인스턴스

        Returns:
            Dict: 거래량 패턴 정보
        """
        # numpy 배열 직접 가져오기
        volumes = hist_buffer.get_volumes_array()
        n = len(volumes)
        
        if n < 10:
            return {'pattern': 'insufficient_data', 'volatility': 0, 'trend': 0}

        # 거래량 변동성 계산 (벡터화)
        mean_vol = np.mean(volumes)
        # noinspection PyTypeChecker
        volume_volatility = np.std(volumes) / (mean_vol + 1e-8)

        # 거래량 트렌드 계산 (이동평균 차이로 polyfit 대체)
        half = n // 2
        first_half_avg = np.mean(volumes[:half])
        second_half_avg = np.mean(volumes[half:])
        # noinspection PyTypeChecker
        volume_trend = (second_half_avg - first_half_avg) / half

        # 패턴 분류
        # noinspection PyTypeChecker
        if volume_volatility > 2.0:
            pattern = 'high_volatility'
        elif abs(volume_trend) > mean_vol * 0.1:
            pattern = 'strong_trend'
        else:
            pattern = 'stable'

        return {
            'pattern': pattern,
            'volatility': volume_volatility,
            'trend': volume_trend,
            'avg_volume': mean_vol,
            'current_volume': volumes[-1]
        }

    def _calculate_trade_ratio(self, buy_volume, sell_volume) -> Dict:
        """
        매수/매도 체결 비율 분석
        실제 체결된 거래의 매수/매도 비율을 계산

        Returns:
            Dict: 체결 비율 정보
        """
        # 실제 체결 데이터 사용 (초당 매수/매도 수량)
        total_volume = buy_volume + sell_volume

        if total_volume == 0:
            return {'buy_ratio': 0.5, 'sell_ratio': 0.5, 'dominance': 'neutral'}

        buy_ratio = buy_volume / total_volume
        sell_ratio = sell_volume / total_volume

        # 우세도 판단
        if buy_ratio > 0.6:
            dominance = 'buy_dominant'
        elif sell_ratio > 0.6:
            dominance = 'sell_dominant'
        else:
            dominance = 'balanced'

        return {
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'dominance': dominance,
            'total_volume': total_volume
        }

    def _analyze_risk(self, code: str):
        """리스크 분석"""
        if self.curr_data is None:
            return 1.0

        # 고위험 상황이면 보류
        if self.curr_data['overall_risk']['risk_level'] == 'HIGH':
            self.curr_data['total_risk'] = 1.0

        market_risk = self._calculate_market_risk()                     # 시장 리스크
        manipulation_risk = self._calculate_manipulation_risk()         # 조작 리스크
        liquidity_risk = self._calculate_liquidity_risk()               # 유동성 리스크
        price_risk = self._calculate_price_risk(code)                   # 가격 기반 리스크 (VaR 등)
        total_risk = round((market_risk + manipulation_risk + liquidity_risk + price_risk) / 4, 2)

        self.curr_data['total_risk'] = total_risk

        return total_risk

    def _analyze_signal(self, buy_cf, sell_cf):
        """최종 신호 분석"""
        if self.curr_data is None:
            return 'hold', 0.0

        final_signal = self._analyze_order_flow(buy_cf, sell_cf)  # 주문 흐름 분석
        confidence = self._calculate_confidence(final_signal, self.curr_data['total_risk'])  # 신뢰도

        return final_signal, confidence

    def _calculate_market_risk(self) -> float:
        """
        시장 리스크 계산

        Returns:
            float: 시장 리스크 (0.0 - 1.0)
        """

        # 불균형 리스크 (절대값이 클수록 위험)
        imbalance_risk = abs(self.curr_data['imbalance'])

        # 깊이 리스크 (깊이 비율이 임계값에서 멀어질수록 위험)
        depth_risk = min(abs(1 - self.curr_data['depth_ratio']) / self.params['depth_ratio_threshold'], 1.0)

        return (imbalance_risk + depth_risk) / 2

    def _calculate_manipulation_risk(self) -> float:
        """
        조작 리스크 계산

        Returns:
            float: 조작 리스크 (0.0 - 1.0)
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
        """유동성 리스크 계산

        Returns:
            float: 유동성 리스크 (0.0 - 1.0)
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

    def _calculate_price_risk(self, code: str) -> float:
        """
        가격 기반 리스크 계산 (VaR, Sharpe Ratio, Max Drawdown)

        Args:
            code: 종목 코드

        Returns:
            float: 가격 기반 리스크 (0.0 - 1.0)
        """
        # Ring Buffer에서 모든 데이터 가져오기
        ring_buffer = self.data_buffers.get(code)
        if ring_buffer is None or len(ring_buffer) < 2:
            return 0.3

        prices = ring_buffer.get_all()[:, self.idx_curr_price]

        # 수익률 계산
        returns = self._calculate_returns(prices)
        if len(returns) == 0:
            return 0.3

        # VaR 계산 (95% 신뢰수준)
        var_95 = self._calculate_var_historical(returns, 0.95)
        # Sharpe Ratio 계산
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        # Max Drawdown 계산
        max_dd, _, _ = self._calculate_max_drawdown(prices)
        # 각 지표를 0-1 스케일로 정규화하여 리스크 점수 계산
        # noinspection PyTypeChecker
        var_risk = min(var_95 / 0.05, 1.0)
        sharpe_risk = max(0, min(1, (2 - sharpe_ratio) / 4))
        # noinspection PyTypeChecker
        dd_risk = min(max_dd / 0.2, 1.0)
        # 세 가지 리스크 지표의 평균
        price_risk = (var_risk + sharpe_risk + dd_risk) / 3

        return price_risk

    def _calculate_returns(self, prices: np.ndarray) -> np.ndarray:
        """가격 데이터로부터 수익률 계산 (numpy 기반)"""
        if len(prices) < 2:
            return np.array([])
        return np.diff(prices) / prices[:-1]

    def _calculate_var_historical(self, returns: np.ndarray, confidence: float = 0.95):
        """VaR 계산"""
        return -np.percentile(returns, (1 - confidence) * 100)

    def _calculate_sharpe_ratio(self, returns: np.ndarray, annualize: bool = True):
        """Sharpe Ratio 계산"""
        if len(returns) == 0:
            return 0.0
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1) if len(returns) > 1 else 0.0
        if std_return == 0:
            return 0.0
        # noinspection PyTypeChecker
        sharpe = (mean_return - 0.02 / 250) / std_return
        if annualize:
            sharpe *= np.sqrt(250)
        return sharpe

    def _calculate_max_drawdown(self, prices: np.ndarray):
        """최대낙폭 계산"""
        if len(prices) == 0:
            return 0.0, 0, 0
        # 누적 최대값 계산 (벡터화)
        cummax = np.maximum.accumulate(prices)
        drawdown = (cummax - prices) / cummax
        max_dd = np.max(drawdown)
        # 최대 낙폭 끝점 찾기
        end_idx = np.argmax(drawdown)
        # 시작점 찾기 (벡터화)
        # noinspection PyTypeChecker
        start_idx = np.argmax(prices[:end_idx + 1]) if end_idx >= 0 else 0
        return max_dd, start_idx, end_idx

    def _analyze_order_flow(self, buy_cf, sell_cf) -> str:
        """주문 흐름 분석

        Returns:
            str: 주문 흐름 신호 ('buy', 'sell', 'hold')
        """
        # 시장 지표 추출
        imbalance = self.curr_data['imbalance']
        imbalance_trend = self.curr_data['imbalance_trend']
        depth_ratio = self.curr_data['depth_ratio']
        bid_concentration = self.curr_data['bid_concentration']
        ask_concentration = self.curr_data['ask_concentration']
        log_depth_ratio = np.log(depth_ratio) / self._log_depth_ratio_threshold if depth_ratio > 0 else 0
        weighted_depth_ratio = self.curr_data['weighted_depth_ratio']
        volume_pattern = self.curr_data['volume_pattern']
        trade_ratio = self.curr_data['trade_ratio']

        # 매수 흐름 강도 계산 (연속적인 0.0~1.0 값)
        buy_flow_strength = (
            # 불균형: 매수 우세일수록 높은 값 (0.0~0.30)
            min(1.0, max(0.0, imbalance + 1.0) / 2.0) * 0.30 +
            # 불균형 추세: 매수 추세일수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, imbalance_trend / (self.params['imbalance_threshold'] * 0.1))) * 0.20 +
            # 깊이 비율: 매수 깊이가 깊을수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, log_depth_ratio)) * 0.20 +
            # 가중 깊이 비율: 중요한 신규 지표 (0.0~0.10)
            min(1.0, weighted_depth_ratio) * 0.10 +
            # 집중도: 매수 집중도가 높을수록 높은 값 (0.0~0.10)
            min(1.0, max(0.0, bid_concentration / self.params['concentration_threshold'])) * 0.10 +
            # 거래량 패턴: 안정성 지표 (0.0~0.03)
            (0.03 if volume_pattern['pattern'] == 'stable' else 0.01) +
            # 체결 비율: 실제 거래 반영 (0.0~0.07)
            (0.07 if trade_ratio['dominance'] == 'buy_dominant' else 0)
        )

        # 매도 흐름 강도 계산 (연속적인 0.0~1.0 값)
        sell_flow_strength = (
            # 불균형: 매도 우세일수록 높은 값 (0.0~0.30)
            min(1.0, max(0.0, 1.0 - imbalance) / 2.0) * 0.30 +
            # 불균형 추세: 매도 추세일수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, -imbalance_trend / (self.params['imbalance_threshold'] * 0.1))) * 0.20 +
            # 깊이 비율: 매도 깊이가 깊을수록 높은 값 (0.0~0.20)
            min(1.0, max(0.0, -log_depth_ratio)) * 0.20 +
            # 가중 깊이 비율: 중요한 신규 지표 (0.0~0.10)
            min(1.0, max(0.0, 1.0 - weighted_depth_ratio)) * 0.10 +
            # 집중도: 매도 집중도가 높을수록 높은 값 (0.0~0.10)
            min(1.0, max(0.0, ask_concentration / self.params['concentration_threshold'])) * 0.10 +
            # 거래량 패턴: 안정성 지표 (0.0~0.03)
            (0.03 if volume_pattern['pattern'] == 'stable' else 0.01) +
            # 체결 비율: 실제 거래 반영 (0.0~0.07)
            (0.07 if trade_ratio['dominance'] == 'sell_dominant' else 0)
        )

        # 최종 신호 결정
        if buy_flow_strength > sell_flow_strength + buy_cf:
            return 'buy'
        elif sell_flow_strength > buy_flow_strength + sell_cf:
            return 'sell'
        else:
            return 'hold'

    def _calculate_confidence(self, signal: str, total_risk: float) -> float:
        """
        신호 신뢰도 계산

        Args:
            signal: 매매 신호
            total_risk: 총리스크

        Returns:
            float: 신호 신뢰도 (0.1 - 1.0)
        """
        # 시장 상태에서 주요 지표 추출
        imbalance = abs(self.curr_data['imbalance'])
        imbalance_trend = self.curr_data['imbalance_trend']
        depth_ratio = self.curr_data['depth_ratio']
        pressure_level = self.curr_data['pressure_level']
        weighted_depth_ratio = self.curr_data['weighted_depth_ratio']
        volume_pattern = self.curr_data['volume_pattern']
        trade_ratio = self.curr_data['trade_ratio']

        signal_adjustments = {'buy': 1.0, 'sell': 1.0, 'hold': 0.1}
        base_confidence = signal_adjustments[signal] * 0.20
        imbalance_confidence = min(max(0.01, imbalance), 1.0) * 0.20

        if signal == 'buy':
            trend_confidence = min(max(0.01, imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * 0.10
            depth_confidence = min(max(0.01, depth_ratio * (self.params['depth_ratio_threshold'] * 0.1)), 1.0) * 0.10
        else:
            trend_confidence = min(max(0.01, -imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * 0.10
            depth_confidence = min(max(0.01, 1 - depth_ratio * (self.params['depth_ratio_threshold'] * 0.1)), 1.0) * 0.10

        pressure_confidence = min(max(0.01, pressure_level * (1 / self.params['pressure_threshold'])), 1.0) * 0.10
        risk_confidence = min(max(0.01, 1 - total_risk), 1.0) * 0.10

        if signal == 'buy':
            weighted_depth_confidence = min(max(0.01, weighted_depth_ratio), 1.0) * 0.10
        else:
            weighted_depth_confidence = min(max(0.01, 1.0 - weighted_depth_ratio), 1.0) * 0.10

        if volume_pattern['pattern'] == 'stable':
            volume_confidence = 0.05
        elif volume_pattern['pattern'] == 'high_volatility':
            volume_confidence = 0.01
        else:
            volume_confidence = 0.03

        dominance = trade_ratio['dominance']
        if (dominance == 'buy_dominant' and signal == 'buy') or (dominance == 'sell_dominant' and signal == 'sell'):
            trade_ratio_confidence = 0.05
        else:
            trade_ratio_confidence = 0.01

        final_confidence = (base_confidence + pressure_confidence + imbalance_confidence + 
                            trend_confidence + depth_confidence + weighted_depth_confidence +
                            volume_confidence + trade_ratio_confidence + risk_confidence)

        final_confidence = round(final_confidence, 2)

        return final_confidence

    def clear_code_data(self, code):
        """종목 데이터 초기화"""
        self.curr_data = None
        if code in self.data_buffers:
            del self.data_buffers[code]
        if code in self.data_history:
            del self.data_history[code]

    def clear_data(self):
        """전체 데이터 초기화"""
        self.curr_data = None
        self.data_buffers = {}
        self.data_history = {}
