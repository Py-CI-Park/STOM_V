
import logging
from typing import Dict, List, Tuple
from utility.lazy_imports import get_np
from collections import defaultdict, deque

# 데이터 칼럼 정의
# 주식 틱 데이터 칼럼
list_stock_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]
# 코인, 해외선물 틱 데이터 칼럼
list_coin_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]


class MicrostructureAnalyzer:
    def __init__(self, market_type: str = 'stock', data_cnt: int = 1800, history_cnt: int = 30, test_mode=False):
        """
        초기화

        Args:
            market_type: 'stock', 'coin', 'future' (시장 종류)
            data_cnt: 종목별 최대 히스토리 저장 크기 (슬라이딩 윈도우)
            history_cnt: 전처리 데이터 히스토리 크기
            test_mode: 테스트모드
        """
        # 기본 설정
        self.logger       = logging.getLogger(__name__)
        self.market_type  = market_type
        self.data_cnt     = data_cnt
        self.history_cnt  = history_cnt
        self.curr_data    = None
        self.test_mode    = test_mode
        self.data_results = []

        # 종목코드별 데이터 저장소
        self.data_buffers = defaultdict(lambda: deque(maxlen=data_cnt))     # 실시간 데이터 버퍼
        self.data_history = defaultdict(lambda: deque(maxlen=history_cnt))  # 전처리 데이터 히스토리

        # 데이터 타입별 파라미터 설정
        self._setup_parameters()
        
        # 칼럼 설정
        self._setup_columns()

    def _setup_parameters(self):
        """
        시장 종류와 데이터 타입에 따른 파라미터 설정
        주식/코인/해외선물 × 1초스냅샷/1분봉 6가지 조합
        """
        # 주식 1초 스냅샷 파라미터 (고빈도, 저지연, 변동성 적음)
        if self.market_type == 'stock':
            self.params = {
                'layering_multiplier': 6.0,        # 6배 이상 (높은 신뢰도)
                'layering_occurrences': 3,         # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.8,     # 80% 변화 (높은 임계값)
                'pump_price_threshold': 0.06,      # 6% 가격 변동
                'pump_volume_threshold': 5.0,      # 5배 거래량 급증
                'imbalance_threshold': 0.25,       # 25% 불균형
                'volume_spike_threshold': 3.0,     # 3배 거래량 급증
                'concentration_threshold': 0.6,    # 60% 집중도
                'depth_ratio_threshold': 2.0,      # 깊이 비율 2.0
                'pressure_threshold': 0.7,         # 압력 레벨 0.7
                'trend_weight': 0.15,              # 추세 가중치
                'liquidity_weight': 0.65,          # 유동성 가중치
                'flow_weight': 0.35,               # 주문 흐름 가중치
                
                # 기술적 분석 파라미터
                'ema_short': 12,                    # 단기 EMA 기간
                'ema_long': 26,                     # 장기 EMA 기간
                'rsi_period': 14,                   # RSI 기간
                'rsi_overbought': 70,               # RSI 과매수선
                'rsi_oversold': 30,                 # RSI 과매도선
                'macd_signal': 9,                   # MACD 시그널 기간
                'bb_period': 20,                    # 볼린저밴드 기간
                'bb_std': 2.0                       # 볼린저밴드 표준편차
            }
        # 코인 1초 스냅샷 파라미터 (고빈도, 고변동성, 24시간)
        elif self.market_type == 'coin':
            self.params = {
                'layering_multiplier': 4.5,        # 4.5배 이상
                'layering_occurrences': 3,         # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.7,     # 70% 변화
                'pump_price_threshold': 0.10,      # 10% 가격 변동 (코인은 변동성 큼)
                'pump_volume_threshold': 4.0,      # 4배 거래량 급증
                'imbalance_threshold': 0.20,       # 20% 불균형
                'volume_spike_threshold': 3.5,     # 3.5배 거래량 급증
                'concentration_threshold': 0.55,   # 55% 집중도
                'depth_ratio_threshold': 1.6,      # 깊이 비율 1.6
                'pressure_threshold': 0.65,        # 압력 레벨 0.65
                'trend_weight': 0.20,              # 추세 가중치
                'liquidity_weight': 0.60,          # 유동성 가중치
                'flow_weight': 0.40                # 주문 흐름 가중치
            }
        # 해외선물 1초 스냅샷 파라미터 (고빈도, 중간변동성, 24시간+레버리지)
        elif self.market_type == 'future':
            self.params = {
                'layering_multiplier': 5.0,        # 5배 이상 (높은 신뢰도)
                'layering_occurrences': 3,         # 3회 이상 반복 (30개 중 10%)
                'order_change_threshold': 0.75,    # 75% 변화 (높은 임계값)
                'pump_price_threshold': 0.07,      # 7% 가격 변동 (레버리지 고려)
                'pump_volume_threshold': 4.5,      # 4.5배 거래량 급증
                'imbalance_threshold': 0.22,       # 22% 불균형
                'volume_spike_threshold': 3.2,     # 3.2배 거래량 급증
                'concentration_threshold': 0.58,   # 58% 집중도
                'depth_ratio_threshold': 1.8,      # 깊이 비율 1.8
                'pressure_threshold': 0.68,        # 압력 레벨 0.68
                'trend_weight': 0.18,              # 추세 가중치
                'liquidity_weight': 0.62,          # 유동성 가중치
                'flow_weight': 0.38                # 주문 흐름 가중치
            }

    def _setup_columns(self):
        """
        시장 및 데이터 타입에 따른 칼럼 설정
        """
        # 시장 종류에 따라 칼럼 목록 선택
        if self.market_type == 'stock':
            self.columns = list_stock_tick  # 주식 틱 데이터
        else:  # coin or future
            self.columns = list_coin_tick   # 코인, 해외선물 틱 데이터

        # 칼럼 인덱스 매핑 (빠른 접근용)
        self.col_index = {col: idx for idx, col in enumerate(self.columns)}

    def update_data(self, code: str, data: get_np().ndarray):
        """
        데이터 전처리, 시장구조분석, 리스크분석

        Args:
            code: 종목코드
            data: 1차원 numpy 배열 (실시간 데이터)

        Returns:
            Tuple[str, float]: (신호타입, 신뢰도)
        """
        # 종목코드별 데이터 버퍼에 실시간 데이터 추가
        self.data_buffers[code].append(data)
        # 데이터 전처리, 시장구조분석
        self._calculate_processed_data(code)
        # 리스크분석
        self._analyze_risk()

    def get_signal(self, buy_cf: float, sell_cf: float) -> Tuple[str, float]:
        """종목별 신호 생성"""
        # 시그널 및 신뢰도 계산
        signal, confidence = self._analyze_signal(buy_cf, sell_cf)

        return signal, confidence

    def _calculate_processed_data(self, code: str):
        """
        종목코드별 전처리 데이터 계산

        Args:
            code: 종목코드
        """
        data_buffers = list(self.data_buffers[code])
        if len(data_buffers) < self.history_cnt:
            return

        # 넘파이 배열로 변환 (성능 최적화)
        recent_data = get_np().array(data_buffers)
        curr_price  = recent_data[-1, self.col_index['현재가']]

        # 거래량 관련 계산 (데이터 타입에 따라 다름)
        total_volume = recent_data[-1, self.col_index['초당매수수량']] + recent_data[-1, self.col_index['초당매도수량']]

        # 마지막 호가 데이터 추출 (5단계 호가)
        ask_prices = []
        bid_prices = []
        ask_qtys = []
        bid_qtys = []
        for i in range(1, 6):
            ask_prices.append(recent_data[-1, self.col_index[f'매도호가{i}']])
            ask_qtys.append(recent_data[-1, self.col_index[f'매도잔량{i}']])
            bid_prices.append(recent_data[-1, self.col_index[f'매수호가{i}']])
            bid_qtys.append(recent_data[-1, self.col_index[f'매수잔량{i}']])

        # 스프레드 관련 계산
        best_ask = ask_prices[0]
        best_bid = bid_prices[0]
        spread = best_ask - best_bid

        # 깊이 비율, 불균형, VWAP 계산
        total_ask_qty = sum(ask_qtys)
        total_bid_qty = sum(bid_qtys)
        depth_ratio = total_bid_qty / total_ask_qty if total_ask_qty > 0 else 1
        total_qty = total_bid_qty + total_ask_qty
        imbalance = (total_bid_qty - total_ask_qty) / total_qty if total_qty > 0 else 0.0

        # 집중도 점수, 압력 레벨 계산
        ask_concentration = sum((aq / total_ask_qty) ** 2 if total_ask_qty > 0 else 0 for aq in ask_qtys)
        bid_concentration = sum((bq / total_bid_qty) ** 2 if total_bid_qty > 0 else 0 for bq in bid_qtys)
        concentration_score = (bid_concentration + ask_concentration) / 2
        pressure_level = (imbalance + concentration_score) / 2

        # 히스토리 데이터 저장 (슬라이딩 윈도우)
        self.data_history[code].append({
            'curr_price': curr_price,
            'spread': spread,
            'imbalance': imbalance,
            'ask_prices': ask_prices,
            'bid_prices': bid_prices,
            'ask_qtys': ask_qtys,
            'bid_qtys': bid_qtys,
            'total_volume': total_volume
        })

        # 스프레드 트렌드 및 불균형 트렌드 계산
        data_history = list(self.data_history[code])
        if len(data_history) < self.history_cnt:
            imbalance_trend = 0
        else:
            # 최근 히스토리 기준 선형 회귀 분석
            imbalance_trend = get_np().polyfit(range(self.history_cnt), [d['imbalance'] for d in data_history], 1)[0]

        # 각종 조작 패턴 감지
        layering = self._detect_layering(code)                              # 레이어링 감지
        pump_dump = self._detect_pump_dump(code)                            # 펌프앤덤프 감지
        overall_risk = self._calculate_overall_risk(layering, pump_dump)    # 종합 리스크 평가

        # 호가 압력 시그널 생성
        liquidity_signal = self._generate_liquidity_signal(imbalance, imbalance_trend)

        # 최신 데이터 저장 (전략 클래스들에서 참조)
        self.curr_data = {
            'curr_price': curr_price,
            'total_ask_qty': total_ask_qty,
            'total_bid_qty': total_bid_qty,
            'spread': spread,
            'depth_ratio': depth_ratio,
            'imbalance': imbalance,
            'ask_concentration': ask_concentration,
            'bid_concentration': bid_concentration,
            'pressure_level': pressure_level,
            'imbalance_trend': imbalance_trend,
            'layering': layering,
            'pump_dump': pump_dump,
            'overall_risk': overall_risk,
            'liquidity_signal': liquidity_signal
        }

    def _detect_layering(self, code: str) -> List[Dict]:
        """
        레이어링 조작 감지

        레이어링: 특정 가격대에 여러 호가를 걸어놓고
        시장 참여자들에게 위신호를 주는 조작 행위

        Args:
            code: 종목 코드
            
        Returns:
            List[Dict]: 감지된 레이어링 신호 목록
        """
        layering_signals = []

        # 데이터가 충분하지 않으면 분석 불가
        data_history = list(self.data_history[code])
        if len(data_history) < self.history_cnt:
            return layering_signals

        # 매도호가와 매수호가 각각 분석
        for side in ['ask', 'bid']:  # ask: 매도, bid: 매수
            suspicious_levels   = self._analyze_price_levels(data_history, side)
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
        가격 레벨별 분석
        특정 가격에 반복적으로 대량 주문이 있는지 분석

        Args:
            data_history: 호가 데이터 목록
            side: 'ask'(매도) 또는 'bid'(매수)
        Returns:
            List[Dict]: 의심스러운 가격 레벨 목록
        """
        level_analysis = {}

        # 각 호가 데이터 분석
        for data in data_history:
            # 매도/매수별 가격과 수량 추출
            if side == 'ask':
                prices = data['ask_prices']
                quantities = data['ask_qtys']
            else:
                prices = data['bid_prices']
                quantities = data['bid_qtys']

            # 가격별 수량 누적 분석
            for price, qty in zip(prices, quantities):
                if qty > 0:
                    if price not in level_analysis:
                        level_analysis[price] = {
                            'total_quantity': 0,
                            'occurrences': 0,
                            'quantities': []
                        }
                    level_analysis[price]['total_quantity'] += qty
                    level_analysis[price]['occurrences'] += 1
                    level_analysis[price]['quantities'].append(qty)

        # 의심스러운 패턴 탐지
        suspicious_levels = []
        for price, analysis in level_analysis.items():
            avg_qty = analysis['total_quantity'] / analysis['occurrences']
            max_qty = max(analysis['quantities'])

            # 평균보다 지정배수 이상 큰 주문이 지정횟수 이상 반복되면 의심
            if max_qty > avg_qty * self.params['layering_multiplier'] and \
                    analysis['occurrences'] >= self.params['layering_occurrences']:
                suspicious_levels.append({
                    'price': price,
                    'avg_quantity': avg_qty,
                    'max_quantity': max_qty,
                    'occurrences': analysis['occurrences'],
                    'suspicion_score': min(max_qty / (avg_qty + 1e-8) / 3, 10.0)
                })

        return suspicious_levels

    def _detect_large_order_changes(self, data_history: List, side: str) -> List[Dict]:
        """
        대량 주문 변화 감지
        주문량이 갑자기 크게 변하는 경우를 감지 (스푸핑의 특징)

        Args:
            data_history: 호가 데이터 목록
            side: 'ask'(매도) 또는 'bid'(매수)

        Returns:
            List[Dict]: 대량 주문 변화 목록
        """
        changes = []

        # 연속된 호가 데이터 비교
        for i in range(1, len(data_history)):
            prev_data = data_history[i-1]
            curr_data = data_history[i]

            # 매도/매수별 수량 추출
            if side == 'ask':
                prev_quantities = prev_data['ask_qtys']  # 이전 매도잔량
                curr_quantities = curr_data['ask_qtys']  # 현재 매도잔량
                prices = curr_data['ask_prices']         # 매도호가
            else:
                prev_quantities = prev_data['bid_qtys']  # 이전 매수잔량
                curr_quantities = curr_data['bid_qtys']  # 현재 매수잔량
                prices = curr_data['bid_prices']         # 매수호가

            # 각 호가 레벨별 변화량 계산
            for level, (prev_qty, curr_qty, price) in enumerate(zip(prev_quantities, curr_quantities, prices)):
                qty_change = abs(curr_qty - prev_qty)

                # 주문량이 지정 비율 이상 변화하고, 주문량이 0보다 큰 경우
                if max(prev_qty, curr_qty) > 0 and \
                        qty_change / max(prev_qty, curr_qty) > self.params['order_change_threshold']:
                    changes.append({
                        'level': level,
                        'price': price,
                        'prev_quantity': prev_qty,
                        'curr_quantity': curr_qty,
                        'change_amount': qty_change,
                        'change_ratio': qty_change / max(prev_qty, curr_qty)
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
        max_occurrences     = max(level['occurrences'] for level in levels)
        occurrence_weight   = min(max_occurrences / 10.0, 1.0)

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

        max_change_ratio    = max(change['change_ratio'] for change in changes)
        avg_change_ratio    = sum(change['change_ratio'] for change in changes) / len(changes)
        change_count_weight = min(len(changes) / 5.0, 1.0)
        confidence = (max_change_ratio * 0.7 + avg_change_ratio * 0.3) * change_count_weight
        return min(confidence, 1.0)

    def _detect_pump_dump(self, code: str) -> List[Dict]:
        """
        펌프 앤 덤프 탐지
        펌프 앤 덤프: 가격을 인위적으로 끌어올린 후 대량 매도하는 조작

        Args:
            code: 종목 코드

        Returns:
            List[Dict]: 감지된 펌프 앤 덤프 신호 목록
        """
        pump_dump_signals = []

        # 데이터가 충분하지 않으면 분석 불가
        date_history = list(self.data_history[code])
        if len(date_history) < self.history_cnt:
            return pump_dump_signals

        prices = get_np().array([d['curr_price'] for d in date_history])

        # 가격 변화율 계산 (%)
        price_changes = get_np().diff(prices) / (prices[:-1] + 1e-10) * 100

        # 거래량 급증 감지
        volume_spikes = self._detect_volume_spikes(code)

        # 각 시점별 펌프 앤 덤프 패턴 확인
        for i in range(len(price_changes)):
            # 가격 변동이 임계값을 초과하고 거래량이 급증한 경우
            if abs(price_changes[i]) > self.params['pump_price_threshold'] and \
                    i < len(volume_spikes) and volume_spikes[i] > self.params['volume_spike_threshold']:
                # 펌프 앤 덤프 패턴이 맞는지 확인
                if self._is_pump_dump_pattern(prices, i):
                    pump_dump_signals.append({
                        'type': 'pump_dump',
                        'price_change': price_changes[i],
                        'volume_spike': volume_spikes[i],
                        'confidence': self._calculate_pump_confidence(price_changes[i], volume_spikes[i])
                    })

        return pump_dump_signals

    def _detect_volume_spikes(self, code: str) -> List[float]:
        """
        거래량 급증 감지

        Args:
            code: 종목 코드

        Returns:
            List[float]: 각 시점별 거래량 급증 비율
        """
        volumes = [v['total_volume'] for v in self.data_history[code]]
        spikes = []

        # 평균 거래량 계산
        avg_volume = get_np().mean(volumes)
        for i, volume in enumerate(volumes):
            # 평균 대비 거래량 비율 계산
            # noinspection PyTypeChecker
            spike_ratio = volume / (avg_volume + 1e-8)
            spikes.append(spike_ratio)

        return spikes

    def _is_pump_dump_pattern(self, prices: get_np().ndarray, index: int) -> bool:
        """
        펌프 앤 덤프 패턴 확인

        Args:
            prices: 가격 배열
            index: 확인할 인덱스

        Returns:
            bool: 펌프 앤 덤프 패턴이면 True
        """
        # 데이터가 충분하지 않으면 판단 불가
        if index < 10: return False

        window = 10
        if index + window < len(prices):
            before = prices[index - window:index]  # 이전 10개
            after = prices[index:index + window]   # 이후 10개

            # 이후 평균가가 이전 평균가보다 2% 이상 하락하고,
            # 현재가가 이전 평균가보다 2% 이상 상승한 경우
            # noinspection PyTypeChecker
            if get_np().mean(after) < get_np().mean(before) * 0.98 and prices[index] > get_np().mean(before) * 1.02:
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
        종합 리스크 평가

        Args:
            layering_signals: 레이어링 신호 목록
            pump_dump_signals: 펌프 앤 덤프 신호 목록

        Returns:
            Dict: 종합 리스크 정보
        """
        all_signals = {
            'layering': layering_signals,
            'pump_dump': pump_dump_signals
        }

        # 총 신호 개수 계산
        total_signals = sum(len(signals) for signals in all_signals.values() if isinstance(signals, list))

        # 최고 신뢰도 찾기
        max_confidence = 0
        for signals in all_signals.values():
            if isinstance(signals, list):
                for signal in signals:
                    if 'confidence' in signal:
                        max_confidence = max(max_confidence, signal['confidence'])

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

    def _generate_liquidity_signal(self, imbalance: float, imbalance_trend: float) -> str:
        """
        호가 유동성 신호 생성

        Args:
            imbalance: 매수/매도 불균형 (-1~1)
            imbalance_trend: 불균형 트렌드

        Returns:
            str: 유동성 신호 (STRONG_BUY, STRONG_SELL, WEAK_BUY, WEAK_SELL, HOLD)
        """
        # 강한 매수 신호: 매수 우세, 스프레드 축소, 불균형 증가
        if imbalance > self.params['imbalance_threshold'] and imbalance_trend > self.params['imbalance_threshold'] * 0.12:
            return 'STRONG_BUY'
        # 강한 매도 신호: 매도 우세, 스프레드 축소, 불균형 감소
        elif imbalance < -self.params['imbalance_threshold'] and imbalance_trend < -self.params['imbalance_threshold'] * 0.12:
            return 'STRONG_SELL'
        # 약한 매수 신호: 매수 우세
        elif imbalance > self.params['imbalance_threshold'] * 0.32:
            return 'WEAK_BUY'
        # 약한 매도 신호: 매도 우세
        elif imbalance < -self.params['imbalance_threshold'] * 0.32:
            return 'WEAK_SELL'
        # 중립 신호 (보류)
        return 'NEUTRAL'

    def _analyze_risk(self):
        """리스크 분석"""
        if self.curr_data is None:
            return

        # 고위험 상황이면 보류
        if self.curr_data['overall_risk']['risk_level'] == 'HIGH':
            self.curr_data['total_risk'] = None

        market_risk       = self._calculate_market_risk()                               # 시장 리스크
        manipulation_risk = self._calculate_manipulation_risk()                         # 조작 리스크
        liquidity_risk    = self._calculate_liquidity_risk()                            # 유동성 리스크
        total_risk        = (market_risk + manipulation_risk + liquidity_risk) / 3      # 총 리스크 (평균)

        self.curr_data['total_risk'] = total_risk

    def _analyze_signal(self, buy_cf, sell_cf):
        """최종 신호 분석"""
        if self.curr_data is None:
            return 'HOLD', 0.0

        final_signal = self._analyze_order_flow(buy_cf, sell_cf)                                # 주문 흐름 분석
        confidence   = self._calculate_confidence(final_signal, self.curr_data['total_risk'])   # 신뢰도

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
        depth_risk = max(0, 1 - total_depth / 1_000_000_000)

        # 평균 집중도 계산
        avg_concentration = (self.curr_data['bid_concentration'] + self.curr_data['ask_concentration']) / 2

        # 집중도가 임계값 이상이면 리스크 증가
        concentration_risk = min(avg_concentration / self.params['concentration_threshold'], 1.0)

        return (depth_risk + concentration_risk) / 2

    def _analyze_order_flow(self, buy_cf, sell_cf) -> str:
        """주문 흐름 분석

        Returns:
            str: 주문 흐름 신호 ('STRONG_BUY', 'WEAK_BUY', 'NEUTRAL', 'WEAK_SELL', 'STRONG_SELL')
        """
        # 시장 지표 추출
        imbalance         = self.curr_data['imbalance']
        depth_ratio       = self.curr_data['depth_ratio']
        bid_concentration = self.curr_data['bid_concentration']
        ask_concentration = self.curr_data['ask_concentration']
        log_depth_ratio   = get_np().log(self.params['depth_ratio_threshold'])
        log_depth_ratio   = get_np().log(depth_ratio) / log_depth_ratio if depth_ratio > 0 else 0

        # 매수 흐름 강도 계산 (연속적인 0.0~1.0 값)
        buy_flow_strength = (
            # 불균형: 매수 우세일수록 높은 값 (0.0~0.4)
            min(1.0, max(0.0, imbalance + 1.0) / 2.0) * 0.4 +
            # 깊이 비율: 매수 깊이가 깊을수록 높은 값 (0.0~0.3) - 로그 스케일로 정규화
            min(1.0, max(0.0, log_depth_ratio)) * 0.3 +
            # 집중도: 매수 집중도가 높을수록 높은 값 (0.0~0.3)
            min(1.0, max(0.0, bid_concentration / self.params['concentration_threshold'])) * 0.3
        )

        # 매도 흐름 강도 계산 (연속적인 0.0~1.0 값)
        sell_flow_strength = (
            # 불균형: 매도 우세일수록 높은 값 (0.0~0.4)
            min(1.0, max(0.0, 1.0 - imbalance) / 2.0) * 0.4 +
            # 깊이 비율: 매도 깊이가 깊을수록 높은 값 (0.0~0.3) - 로그 스케일로 정규화
            min(1.0, max(0.0, -log_depth_ratio)) * 0.3 +
            # 집중도: 매도 집중도가 높을수록 높은 값 (0.0~0.3)
            min(1.0, max(0.0, ask_concentration / self.params['concentration_threshold'])) * 0.3
        )

        if self.test_mode:
            self.data_results.append([buy_flow_strength, sell_flow_strength, None])

        # 최종 신호 결정
        if buy_flow_strength > sell_flow_strength + buy_cf:
            return 'BUY'
        elif sell_flow_strength > buy_flow_strength + sell_cf:
            return 'SELL'
        else:
            return 'HOLD'

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
        pressure_level    = self.curr_data['pressure_level']                        # 압력 수준
        imbalance         = abs(self.curr_data['imbalance'])                        # 불균형 절대값
        imbalance_trend   = self.curr_data['imbalance_trend']                       # 불균형 추세
        depth_ratio       = self.curr_data['depth_ratio']                           # 깊이 비율

        # 신호별 기본 조정값
        signal_adjustments = {'BUY': 1.0, 'SELL': 1.0, 'HOLD': 0.1}
        base_confidence = signal_adjustments.get(signal, 0) * 0.2                   # 기본 신뢰도

        # 각 요소별 신뢰도 계산
        pressure_confidence = min(max(0.01, pressure_level * (1 / self.params['pressure_threshold'])), 1.0) * 0.2  # 압력 신뢰도
        imbalance_confidence = min(max(0.01, imbalance), 1.0) * 0.2                 # 불균형 신뢰도

        # 매수/매도 신호에 따른 추세 신뢰도 계산
        if signal == 'BUY':
            trend_confidence = min(max(0.01, imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * self.params['trend_weight']   # 매수 추세 신뢰도
            depth_confidence = min(max(0.01, depth_ratio * (self.params['depth_ratio_threshold'] * 0.1)), 1.0) * self.params['trend_weight']            # 깊이 신뢰도
        else:
            trend_confidence = min(max(0.01, -imbalance_trend * (1 / (self.params['imbalance_threshold'] * 0.05))), 1.0) * self.params['trend_weight']  # 매도 추세 신뢰도
            depth_confidence = min(max(0.01, 1 - depth_ratio * (self.params['depth_ratio_threshold'] * 0.1)), 1.0) * self.params['trend_weight']        # 깊이 신뢰도

        risk_confidence = min(max(0.01, 1 - total_risk), 1.0) * 0.2                 # 리스크 신뢰도

        final_confidence = base_confidence + pressure_confidence + imbalance_confidence + \
            trend_confidence + depth_confidence + risk_confidence
        final_confidence = round(final_confidence, 2)                            # 소수점 2자리 반올림
        # noinspection PyTypeChecker
        final_confidence = min(max(final_confidence, 0.1), 1.0)                     # 0.1-1.0 범위로 제한

        if self.test_mode:
            self.data_results[-1][2] = final_confidence

        return final_confidence

    def clear_data(self):
        """데이터 초기화"""
        self.curr_data    = None
        self.data_buffers = defaultdict(lambda: deque(maxlen=self.data_cnt))
        self.data_history = defaultdict(lambda: deque(maxlen=self.history_cnt))
