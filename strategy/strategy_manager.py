
import logging
import numpy as np
from typing import Dict, List, Tuple
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
# 주식 분봉 데이터 칼럼
list_stock_min = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '거래대금증감', '전일비', '회전율', '전일동시간비', '시가총액', '라운드피겨위5호가이내', 'VI해제시간', 'VI가격', 'VI호가단위',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]
# 코인 틱 데이터 칼럼
list_coin_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]
# 코인 분봉 데이터 칼럼
list_coin_min = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]


class StrategyManager:
    """
    전략 데이터 관리 매니저
    
    Features:
    - 종목코드별 데이터 관리 (1차원 배열 실시간 처리)
    - 슬라이딩 윈도우 데이터 버퍼링
    - 전처리 데이터 자동 계산 및 캐싱
    - 4개 전략 클래스용 데이터 제공 (ManipulationDetector, OrderBookAnalyzer, MicrostructureAnalyzer, TargetPriceManager)
    """
    def __init__(self, market_type: str = 'stock', data_type: str = 'tick', data_cnt: int = 1800, history_cnt: int = 30):
        """
        초기화
        
        Args:
            market_type: 'stock' 또는 'coin' (시장 종류)
            data_type: 'tick' 또는 'min' (데이터 타입)
            data_cnt: 종목별 최대 히스토리 저장 크기 (슬라이딩 윈도우)
            history_cnt: 전처리 데이터 히스토리 크기
        """
        # 기본 설정
        self.logger       = logging.getLogger(__name__)
        self.market_type  = market_type  # 시장 종류
        self.data_type    = data_type    # 데이터 타입
        self.data_cnt     = data_cnt     # 데이터 버퍼 크기
        self.history_cnt  = history_cnt  # 히스토리 크기
        self.curr_data    = None         # 현재 데이터
        
        # 종목코드별 데이터 저장소
        self.data_buffers = defaultdict(lambda: deque(maxlen=data_cnt))  # 실시간 데이터 버퍼
        self.data_history = defaultdict(lambda: deque(maxlen=history_cnt))  # 전처리 데이터 히스토리
        
        # 전처리 데이터 저장소 (종목코드별)
        self.processed_data = defaultdict(dict)  # 계산된 지표들
        self.manipulation_data = defaultdict(dict)  # 조작 감지 데이터
        self.orderbook_data = defaultdict(dict)  # 호가 분석 데이터
        self.microstructure_data = defaultdict(dict)  # 미시구조 데이터
        self.target_price_data = defaultdict(dict)  # 목표가 데이터
        
        # 계산 캐시 (성능 최적화용)
        self._calculation_cache = defaultdict(dict)
        
        # 칼럼 설정
        self._setup_columns()
    
    def _setup_columns(self):
        """
        시장 및 데이터 타입에 따른 칼럼 설정
        """
        # 시장 종류에 따라 칼럼 목록 선택
        if self.market_type == 'stock':
            if self.data_type == 'tick':
                self.columns = list_stock_tick  # 주식 틱 데이터
            else:  # min
                self.columns = list_stock_min   # 주식 분봉 데이터
        else:  # coin or future
            if self.data_type == 'tick':
                self.columns = list_coin_tick  # 코인 틱 데이터
            else:  # min
                self.columns = list_coin_min   # 코인 분봉 데이터
        
        # 칼럼 인덱스 매핑 (빠른 접근용)
        self.col_index = {col: idx for idx, col in enumerate(self.columns)}
    
    def get_signal_date(self, code: str, data: np.ndarray) -> Tuple[str, float]:
        """
        종목별 신호 생성 (메인 진입점)
        
        Args:
            code: 종목코드
            data: 1차원 numpy 배열 (실시간 데이터)
            
        Returns:
            Tuple[str, float]: (신호타입, 신뢰도)
        """
        # 종목코드별 데이터 버퍼에 실시간 데이터 추가
        self.data_buffers[code].append(data)
        
        # 해당 종목 전처리 데이터 계산
        self._calculate_processed_data(code)
        # 시그널 및 신뢰도 계산
        signal, confidence = self._analyze_signal(code)
        return signal, confidence
    
    def _calculate_processed_data(self, code: str):
        """
        종목코드별 전처리 데이터 계산
        
        Args:
            code: 종목코드
        """
        buffer = self.data_buffers[code]
        if len(buffer) < 20:  # 최소 20개 데이터 필요
            return
        
        # 넘파이 배열로 변환 (성능 최적화)
        recent_data = np.array(list(buffer))
        curr_price  = recent_data[-1, self.col_index['현재가']]
        
        # 거래량 관련 계산 (데이터 타입에 따라 다름)
        if self.data_type == 'tick':
            buy_volume   = recent_data[:, self.col_index['초당매수수량']]
            sell_volume  = recent_data[:, self.col_index['초당매도수량']]
        else:
            buy_volume   = recent_data[:, self.col_index['분당매수수량']]
            sell_volume  = recent_data[:, self.col_index['분당매도수량']]
        
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
        spread_pct = (spread / best_bid) * 100 if best_bid > 0 else 0.9995  # 0으로 나누기 방지
        spread_score = min(spread_pct / 1.0, 1.0)
        
        # 깊이 비율, 불균형, VWAP 계산
        total_ask_qty = sum(ask_qtys)
        total_bid_qty = sum(bid_qtys)
        depth_ratio = total_bid_qty / total_ask_qty if total_ask_qty > 0 else 1
        total_qty = total_bid_qty + total_ask_qty
        imbalance = (total_bid_qty - total_ask_qty) / total_qty if total_qty > 0 else 0
        
        # 집중도 점수, 압력 레벨 계산
        ask_concentration = sum((aq / total_ask_qty) ** 2 if total_ask_qty > 0 else 0 for aq in ask_qtys)
        bid_concentration = sum((bq / total_bid_qty) ** 2 if total_bid_qty > 0 else 0 for bq in bid_qtys)
        concentration_score = (bid_concentration + ask_concentration) / 2
        pressure_level = (imbalance + spread_score + concentration_score) / 3
        
        # 히스토리 데이터 저장 (슬라이딩 윈도우)
        self.data_history[code].append({
            'curr_price': curr_price,
            'spread': spread,
            'imbalance': imbalance,
            'ask_prices': ask_prices,
            'bid_prices': bid_prices,
            'ask_qtys': ask_qtys,
            'bid_qtys': bid_qtys,
            'total_volume': buy_volume[-1] + sell_volume[-1],
        })
        # 스프레드 트렌드 및 불균형 트렌드 계산
        data_history = list(self.data_history[code])
        if len(data_history) < self.history_cnt:
            spread_trend = 0
            imbalance_trend = 0
        else:
            # 최근 히스토리 기준 선형 회귀 분석
            spread_trend = np.polyfit(range(self.history_cnt), [d['spread'] for d in data_history], 1)[0]
            imbalance_trend = np.polyfit(range(self.history_cnt), [d['imbalance'] for d in data_history], 1)[0]
        
        # 호가 압력 시그널 생성
        liquidity_signal = self._generate_liquidity_signal(imbalance, spread_trend, imbalance_trend)
        
        # 각종 조작 패턴 감지
        layering = self._detect_layering(code)                              # 레이어링 감지
        pump_dump = self._detect_pump_dump(code)                            # 펌프앤덤프 감지
        overall_risk = self._calculate_overall_risk(layering, pump_dump)    # 종합 리스크 평가
        
        # 최신 데이터 저장 (전략 클래스들에서 참조)
        self.curr_data = {
            'curr_price': curr_price,
            'total_ask_qty': total_ask_qty,
            'total_bid_qty': total_bid_qty,
            'spread': spread,
            'spread_pct': spread_pct,
            'depth_ratio': depth_ratio,
            'imbalance': imbalance,
            'ask_concentration': ask_concentration,
            'bid_concentration': bid_concentration,
            'pressure_level': pressure_level,
            'spread_trend': spread_trend,
            'imbalance_trend': imbalance_trend,
            'liquidity_signal': liquidity_signal,
            'layering': layering,
            'pump_dump': pump_dump,
            'overall_risk': overall_risk
        }
    
    def _generate_liquidity_signal(self, imbalance: float, spread_trend: float, imbalance_trend: float) -> str:
        """
        호가 유동성 신호 생성
        
        Args:
            imbalance: 매수/매도 불균형 (-1~1)
            spread_trend: 스프레드 트렌드
            imbalance_trend: 불균형 트렌드
            
        Returns:
            str: 유동성 신호 (STRONG_BUY, STRONG_SELL, WEAK_BUY, WEAK_SELL, HOLD)
        """
        # 강한 매수 신호: 매수 우세, 스프레드 축소, 불균형 증가
        if imbalance > 0.25 and spread_trend < -0.15 and imbalance_trend > 0.03:
            return 'STRONG_BUY'
        # 강한 매도 신호: 매도 우세, 스프레드 축소, 불균형 감소
        elif imbalance < -0.25 and spread_trend < -0.15 and imbalance_trend < -0.03:
            return 'STRONG_SELL'
        # 약한 매수 신호: 매수 우세
        elif imbalance > 0.08:
            return 'WEAK_BUY'
        # 약한 매도 신호: 매도 우세
        elif imbalance < -0.08:
            return 'WEAK_SELL'
        # 중립 신호 (보류)
        return 'NEUTRAL'

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
        if len(self.data_history[code]) < self.data_cnt:
            return layering_signals
        
        data_history = list(self.data_history[code])
        
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
            
            # 평균보다 2.5배 이상 큰 주문이 2번 이상 반복되면 의심
            if max_qty > avg_qty * 2.5 and analysis['occurrences'] >= 2:
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
        
        # 데이터가 3개 미만이면 분석 불가
        if len(data_history) < 3:
            return changes
        
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
                
                # 주문량이 40% 이상 변화하고, 주문량이 0보다 큰 경우
                if max(prev_qty, curr_qty) > 0 and qty_change / max(prev_qty, curr_qty) > 0.4:
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
        if not levels: 
            return 0.0
        
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
        if not changes: 
            return 0.0
        
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
        if len(date_history) < self.data_cnt:
            return pump_dump_signals
        
        prices = np.array([d['curr_price'] for d in date_history])
        
        # 가격 변화율 계산 (%)
        price_changes = np.diff(prices) / (prices[:-1] + 1e-10) * 100
        
        # 거래량 급증 감지
        volume_spikes = self._detect_volume_spikes(code)
        
        # 각 시점별 펌프 앤 덤프 패턴 확인
        for i in range(len(price_changes)):
            # 가격 변동이 임계값을 초과하고 거래량이 급증한 경우
            if abs(price_changes[i]) > 0.03 and i < len(volume_spikes) and volume_spikes[i] > 2.5:
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
        avg_volume = np.mean(volumes)
        
        for i, volume in enumerate(volumes):
            # 평균 대비 거래량 비율 계산
            # noinspection PyTypeChecker
            spike_ratio = volume / (avg_volume + 1e-8)
            spikes.append(spike_ratio)
        
        return spikes

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
            before = prices[index - window:index]  # 이전 10개
            after = prices[index:index + window]  # 이후 10개
            
            # 이후 평균가가 이전 평균가보다 2% 이상 하락하고,
            # 현재가가 이전 평균가보다 2% 이상 상승한 경우
            # noinspection PyTypeChecker
            if np.mean(after) < np.mean(before) * 0.98 and prices[index] > np.mean(before) * 1.02:
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

    def _analyze_signal(self, code: str):
        """
        최종 신호 분석
        
        Args:
            code: 종목 코드
            
        Returns:
            Tuple[str, float]: (신호, 신뢰도)
        """
        buffer = self.data_buffers[code]
        if len(buffer) < 30:
            return 'HOLD', 0.0
        
        # 고위험 상황이면 보류
        if self.curr_data['overall_risk']['risk_level'] == 'HIGH':
            return 'HOLD', 0.0
        
        market_risk       = self._calculate_market_risk()                           # 시장 리스크
        manipulation_risk = self._calculate_manipulation_risk()                     # 조작 리스크
        liquidity_risk    = self._calculate_liquidity_risk()                        # 유동성 리스크
        total_risk        = (market_risk + manipulation_risk + liquidity_risk) / 3  # 총 리스크 (평균)
        
        flow_signal       = self._analyze_order_flow()                              # 주문 흐름 분석
        final_signal      = self._analyze_final_signals(flow_signal)                # 신호 융합
        confidence        = self._calculate_confidence(final_signal, total_risk)    # 신뢰도
        
        return final_signal, confidence

    def _calculate_market_risk(self) -> float:
        """
        시장 리스크 계산
        
        Returns:
            float: 시장 리스크 (0.0 - 1.0)
        """
        # 스프레드 리스크 (0.8% 이상이면 위험)
        spread_risk = min(self.curr_data['spread_pct'] / 0.8, 1.0)
        # 불균형 리스크 (절대값이 클수록 위험)
        imbalance_risk = abs(self.curr_data['imbalance'])
        # 깊이 리스크 (깊이 비율이 1에서 멀어질수록 위험)
        depth_risk = min(abs(1 - self.curr_data['depth_ratio']) / 1.5, 1.0)
        
        return (spread_risk + imbalance_risk + depth_risk) / 3

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
        # 집중도가 높을수록 리스크 증가
        concentration_risk = avg_concentration
        return (depth_risk + concentration_risk) / 2

    def _analyze_order_flow(self) -> str:
        """주문 흐름 분석
        Returns:
            str: 주문 흐름 신호 ('STRONG_BUY', 'WEAK_BUY', 'NEUTRAL', 'WEAK_SELL', 'STRONG_SELL')
        """
        # 시장 지표 추출
        imbalance = self.curr_data['imbalance']                     # 매수/매도 불균형
        depth_ratio = self.curr_data['depth_ratio']                 # 깊이 비율
        spread_pct = self.curr_data['spread_pct']                   # 스프레드 비율
        bid_concentration = self.curr_data['bid_concentration']     # 매수 집중도
        ask_concentration = self.curr_data['ask_concentration']     # 매도 집중도
        # 매수 흐름 강도 계산 (가중치 합산)
        buy_flow_strength = (
            (imbalance > 0) * 0.4 +             # 매수 우세 시 0.4
            (depth_ratio > 1.5) * 0.3 +         # 매수 깊이가 깊을 시 0.3
            (spread_pct < 0.1) * 0.2 +          # 스프레드가 좁을 시 0.2
            (bid_concentration > 0.5) * 0.1     # 매수 집중도가 높을 시 0.1
        )
        # 매도 흐름 강도 계산
        sell_flow_strength = (
            (imbalance < 0) * 0.4 +             # 매도 우세 시 0.4
            (depth_ratio < 0.5) * 0.3 +         # 매도 깊이가 깊을 시 0.3
            (spread_pct < 0.1) * 0.2 +          # 스프레드가 좆을 시 0.2
            (ask_concentration > 0.5) * 0.1     # 매도 집중도가 높을 시 0.1
        )
        
        # 최종 신호 결정
        if buy_flow_strength > sell_flow_strength + 0.2:
            return 'STRONG_BUY'
        elif sell_flow_strength > buy_flow_strength + 0.2:
            return 'STRONG_SELL'
        elif buy_flow_strength > sell_flow_strength:
            return 'WEAK_BUY'
        elif sell_flow_strength > buy_flow_strength:
            return 'WEAK_SELL'
        else:
            return 'NEUTRAL'

    def _analyze_final_signals(self, flow_signal: str) -> str:
        """
        신호 융합
        유동성 신호와 주문 흐름 신호를 결합하여 최종 신호 생성
        
        Args:
            flow_signal: 주문 흐름 신호
        Returns:
            str: 융합된 신호 ('BUY', 'SELL', 'HOLD')
        """
        # 신호별 가중치 설정
        liquidity_weight = 0.6  # 유동성 신호 가중치
        flow_weight = 0.4       # 주문 흐름 신호 가중치
        
        # 신호를 수치로 변환
        signal_scores = {
            'STRONG_BUY': 2, 'BUY': 1, 'WEAK_BUY': 0.5,
            'STRONG_SELL': -2, 'SELL': -1, 'WEAK_SELL': -0.5,
            'NEUTRAL': 0, 'HOLD': 0
        }
        
        # 각 신호를 수치로 변환
        liquidity_score = signal_scores.get(self.curr_data['liquidity_signal'], 0)
        flow_score = signal_scores.get(flow_signal, 0)
        
        # 가중치 적용하여 융합 점수 계산
        fused_score = liquidity_score * liquidity_weight + flow_score * flow_weight
        
        # 최종 신호 결정
        if fused_score >= 0.4:
            return 'BUY'
        elif fused_score <= -0.4:
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
        pressure_confidence = min(max(0.01, pressure_level * 3), 1.0) * 0.2         # 압력 신뢰도
        imbalance_confidence = min(max(0.01, imbalance), 1.0) * 0.2                 # 불균형 신뢰도

        # 디버그
        """
        if signal == 'BUY':
            print(f"{'-' * 50} {signal} {pressure_level * 3:.3f} {imbalance:.3f} {imbalance_trend * 20:.3f} {depth_ratio * 0.2:.3f} {1 - total_risk:.3f}")
        elif signal == 'SELL':
            print(f"{'-' * 50} {signal} {pressure_level * 3:.3f} {imbalance:.3f} {-imbalance_trend * 20:.3f} {1 - depth_ratio * 0.2:.3f} {1 - total_risk:.3f}")
        """

        # 매수/매도 신호에 따른 추세 신뢰도 계산
        if signal == 'BUY':
            trend_confidence = min(max(0.01, imbalance_trend * 20), 1.0) * 0.1      # 매수 추세 신뢰도
            depth_confidence = min(max(0.01, depth_ratio * 0.2), 1.0) * 0.1         # 깊이 신뢰도
        else:
            trend_confidence = min(max(0.01, -imbalance_trend * 20), 1.0) * 0.1     # 매도 추세 신뢰도
            depth_confidence = min(max(0.01, 1 - depth_ratio * 0.2), 1.0) * 0.1     # 깊이 신뢰도
        
        risk_confidence = min(max(0.01, 1 - total_risk), 1.0) * 0.2                 # 리스크 신뢰도
        
        # 최종 신뢰도 계산 (모든 요소 결합)
        final_confidence = base_confidence + pressure_confidence + imbalance_confidence + \
            trend_confidence + depth_confidence + risk_confidence
        final_confidence = np.round(final_confidence, 2)                            # 소수점 2자리 반올림
        final_confidence = min(max(final_confidence, 0.1), 1.0)                     # 0.1-1.0 범위로 제한
        
        return final_confidence
    
    def clear_data(self):
        """데이터 초기화"""
        self.data_buffers = defaultdict(lambda: deque(maxlen=self.data_cnt))
        self.data_history = defaultdict(lambda: deque(maxlen=self.history_cnt))
