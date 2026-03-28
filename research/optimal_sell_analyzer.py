
import numpy as np
from typing import Dict, List
from collections import deque
from utility.setting_base import list_stock_tick, list_coin_tick


class OptimalSellAnalyzer:
    """
    종목별 최적 매도 타이밍 분석기

    어떤 매수전략으로 매수하더라도 해당 종목의 데이터를 기반으로
    최적의 매도 타이밍을 찾아내는 분석기
    """

    def __init__(self, market_type: str = 'stock', history_size: int = 1800):
        """
        초기화

        Args:
            market_type: 'stock', 'coin', 'future'
            history_size: 히스토리 데이터 저장 크기
        """
        self.market_type  = market_type
        self.history_size = history_size

        # 데이터 저장소
        self.data_buffers = {}  # 종목별 데이터 버퍼

        # 시장 종류별 칼럼 설정
        self.columns = list_stock_tick if market_type == 'stock' else list_coin_tick
        self.col_index = {col: idx for idx, col in enumerate(self.columns)}

        # 분석 파라미터
        self.params = self._setup_analysis_params()

        # 신호 가중치
        self.signal_weights = {
            'technical': 0.25,      # 기술적 분석
            'momentum': 0.20,       # 모멘텀
            'volume': 0.20,         # 거래량
            'volatility': 0.15,     # 변동성
            'pattern': 0.10,        # 패턴 인식
            'microstructure': 0.10  # 마이크로스트럭처
        }

    def _setup_analysis_params(self) -> Dict:
        """시장 종류별 분석 파라미터 설정"""
        if self.market_type == 'stock':
            return {
                'rsi_period': 14,
                'rsi_overbought': 70,
                'rsi_oversold': 30,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 20,
                'bb_std': 2.0,
                'volume_spike_threshold': 3.0,
                'price_change_threshold': 0.02,  # 2%
                'momentum_period': 10,
                'volatility_period': 20,
                'resistance_lookback': 50
            }
        elif self.market_type == 'coin':
            return {
                'rsi_period': 14,
                'rsi_overbought': 75,
                'rsi_oversold': 25,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 20,
                'bb_std': 2.5,
                'volume_spike_threshold': 4.0,
                'price_change_threshold': 0.03,  # 3%
                'momentum_period': 8,
                'volatility_period': 15,
                'resistance_lookback': 30
            }
        else:  # future
            return {
                'rsi_period': 14,
                'rsi_overbought': 72,
                'rsi_oversold': 28,
                'macd_fast': 12,
                'macd_slow': 26,
                'macd_signal': 9,
                'bb_period': 20,
                'bb_std': 2.2,
                'volume_spike_threshold': 3.5,
                'price_change_threshold': 0.025,  # 2.5%
                'momentum_period': 9,
                'volatility_period': 18,
                'resistance_lookback': 40
            }

    def update_data(self, symbol: str, tick_data: np.ndarray):
        """
        틱 데이터 업데이트

        Args:
            symbol: 종목코드
            tick_data: 틱 데이터 1차원 배열
        """
        if symbol not in self.data_buffers:
            self.data_buffers[symbol] = deque(maxlen=self.history_size)

        self.data_buffers[symbol].append(tick_data)

    def analyze_sell_timing(self, symbol: str, entry_price: float, entry_time: int) -> Dict:
        """
        최적 매도 타이밍 분석

        Args:
            symbol: 종목코드
            entry_price: 매수 진입가
            entry_time: 매수 진입 시간

        Returns:
            Dict: 매도 타이밍 분석 결과
        """
        if symbol not in self.data_buffers or len(self.data_buffers[symbol]) < 50:
            return self._get_insufficient_data_result()

        # 데이터 준비
        data_array = np.array(list(self.data_buffers[symbol]))
        current_price = data_array[-1, self.col_index['현재가']]

        # 각 분석기 실행
        technical_signals = self.analyze_technical_signals(data_array)
        momentum_signals = self.analyze_momentum_signals(data_array)
        volume_signals = self.analyze_volume_signals(data_array)
        volatility_signals = self.analyze_volatility_signals(data_array)
        pattern_signals = self.analyze_pattern_signals(data_array)
        microstructure_signals = self.analyze_microstructure_signals(data_array)

        # 종합 매도 점수 계산
        all_signals = {
            'technical': technical_signals,
            'momentum': momentum_signals,
            'volume': volume_signals,
            'volatility': volatility_signals,
            'pattern': pattern_signals,
            'microstructure': microstructure_signals
        }

        sell_score = self.calculate_sell_score(all_signals)

        # 최적 매도 가격 계산
        optimal_price = self.calculate_optimal_sell_price(
            current_price, entry_price, sell_score, all_signals
        )

        # 시간 민감도 분석
        time_sensitivity = self.analyze_time_sensitivity(data_array, entry_time)

        return {
            'symbol': symbol,
            'current_price': current_price,
            'entry_price': entry_price,
            'profit_loss_pct': ((current_price - entry_price) / entry_price) * 100,
            'sell_score': sell_score,
            'signals': all_signals,
            'recommendation': self.get_sell_recommendation(sell_score),
            'optimal_sell_price': optimal_price,
            'time_sensitivity': time_sensitivity,
            'risk_level': self.assess_risk_level(all_signals),
            'confidence': self.calculate_confidence(all_signals)
        }

    def analyze_technical_signals(self, data_array: np.ndarray) -> Dict:
        """기술적 분석 시그널"""
        prices = data_array[:, self.col_index['현재가']]

        signals = {}

        # RSI 과매수 확인
        rsi = self.calculate_rsi(prices, self.params['rsi_period'])
        current_rsi = rsi[-1]
        signals['rsi_overbought'] = {
            'signal': current_rsi >= self.params['rsi_overbought'],
            'strength': min(1.0, (current_rsi - self.params['rsi_overbought']) / 30),
            'value': current_rsi
        }

        # 볼린저밴드 상단 돌파
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(
            prices, self.params['bb_period'], self.params['bb_std']
        )
        current_price = prices[-1]
        signals['bollinger_upper'] = {
            'signal': current_price >= bb_upper[-1],
            'strength': min(1.0, (current_price - bb_upper[-1]) / bb_upper[-1] * 100),
            'penetration_pct': ((current_price - bb_upper[-1]) / bb_upper[-1]) * 100
        }

        # MACD 다이버전스
        macd_line, signal_line = self.calculate_macd(
            prices, self.params['macd_fast'], self.params['macd_slow'], self.params['macd_signal']
        )
        signals['macd_divergence'] = self.detect_macd_divergence(prices, macd_line)

        # 저항선 접근
        resistance_levels = self.find_resistance_levels(prices, self.params['resistance_lookback'])
        signals['resistance_approach'] = self.check_resistance_approach(current_price, resistance_levels)

        return signals

    def analyze_momentum_signals(self, data_array: np.ndarray) -> Dict:
        """모멘텀 분석 시그널"""
        prices = data_array[:, self.col_index['현재가']]

        signals = {}

        # 가속도 감소
        momentum = self.calculate_momentum(prices, self.params['momentum_period'])
        acceleration = np.diff(momentum)
        # noinspection PyTypeChecker
        signals['acceleration_decrease'] = {
            'signal': len(acceleration) > 0 > acceleration[-1],
            'strength': min(1.0, abs(acceleration[-1]) / np.std(acceleration) if np.std(acceleration) > 0 else 0),
            'trend': 'decreasing' if len(acceleration) > 0 > acceleration[-1] else 'increasing'
        }

        # 추세 전환
        short_ma = self.calculate_sma(prices, 10)
        long_ma = self.calculate_sma(prices, 30)
        signals['trend_reversal'] = {
            'signal': len(short_ma) > 1 and len(long_ma) > 1 and short_ma[-1] < long_ma[-1] and short_ma[-2] >= long_ma[-2],
            'strength': min(1.0, abs(short_ma[-1] - long_ma[-1]) / long_ma[-1] * 100),
            'short_ma': short_ma[-1] if len(short_ma) > 0 else 0,
            'long_ma': long_ma[-1] if len(long_ma) > 0 else 0
        }

        # 모멘텀 다이버전스
        signals['momentum_divergence'] = self.detect_momentum_divergence(prices, momentum)

        return signals

    def analyze_volume_signals(self, data_array: np.ndarray) -> Dict:
        """거래량 분석 시그널"""
        buy_volumes = data_array[:, self.col_index['초당매수수량']]
        sell_volumes = data_array[:, self.col_index['초당매도수량']]
        total_volumes = buy_volumes + sell_volumes

        signals = {}

        # 거래량 급증 후 감소
        avg_volume = np.mean(total_volumes)
        current_volume = total_volumes[-1]
        # noinspection PyTypeChecker
        volume_spike = current_volume / avg_volume if avg_volume > 0 else 1

        # 이전 거래량과 비교
        if len(total_volumes) > 1:
            volume_trend = (total_volumes[-1] - total_volumes[-2]) / total_volumes[-2] if total_volumes[-2] > 0 else 0
        else:
            volume_trend = 0

        signals['volume_exhaustion'] = {
            'signal': volume_spike > self.params['volume_spike_threshold'] and volume_trend < -0.1,
            'strength': min(1.0, volume_spike / self.params['volume_spike_threshold']),
            'spike_ratio': volume_spike,
            'trend': volume_trend
        }

        # 매수/매도 압력 변화
        buy_pressure = np.sum(buy_volumes[-5:]) / (np.sum(buy_volumes[-5:]) + np.sum(sell_volumes[-5:]) + 1e-10)
        sell_pressure = np.sum(sell_volumes[-5:]) / (np.sum(buy_volumes[-5:]) + np.sum(sell_volumes[-5:]) + 1e-10)

        signals['pressure_shift'] = {
            'signal': sell_pressure > buy_pressure * 1.2,  # 매도 압력이 매수 압력보다 20% 이상 높음
            'strength': min(1.0, (sell_pressure - buy_pressure) / buy_pressure) if buy_pressure > 0 else 0,
            'buy_pressure': buy_pressure,
            'sell_pressure': sell_pressure
        }

        return signals
    
    def analyze_volatility_signals(self, data_array: np.ndarray) -> Dict:
        """변동성 분석 시그널"""
        prices = data_array[:, self.col_index['현재가']]

        signals = {}

        # 변동성 팽창
        volatility = self.calculate_volatility(prices, self.params['volatility_period'])
        if len(volatility) > 1:
            volatility_change = (volatility[-1] - volatility[-2]) / volatility[-2] if volatility[-2] > 0 else 0
        else:
            volatility_change = 0

        signals['volatility_expansion'] = {
            'signal': volatility_change > 0.2,  # 변동성이 20% 이상 증가
            'strength': min(1.0, volatility_change / 0.5),
            'current_volatility': volatility[-1] if len(volatility) > 0 else 0,
            'change_pct': volatility_change * 100
        }

        # 변동성 수축 (가격 안정화)
        signals['volatility_contraction'] = {
            'signal': volatility_change < -0.1,  # 변동성이 10% 이상 감소
            'strength': min(1.0, abs(volatility_change) / 0.3),
            'contraction_pct': abs(volatility_change) * 100
        }

        return signals

    def analyze_pattern_signals(self, data_array: np.ndarray) -> Dict:
        """패턴 인식 시그널"""
        prices = data_array[:, self.col_index['현재가']]

        signals = {
            'double_top': self.detect_double_top(prices),           # 더빙 패턴 (상승 후 하락)
            'head_shoulders': self.detect_head_shoulders(prices),   # 헤드앤숄더 패턴
            'rising_wedge': self.detect_rising_wedge(prices)        # 상승 쐐기판 패턴
        }

        return signals

    def analyze_microstructure_signals(self, data_array: np.ndarray) -> Dict:
        """마이크로스트럭처 분석 시그널"""
        signals = {}

        # 호가 불균형
        total_bid_qty = sum(data_array[-1, self.col_index[f'매수잔량{i}']] for i in range(1, 6))
        total_ask_qty = sum(data_array[-1, self.col_index[f'매도잔량{i}']] for i in range(1, 6))
        total_qty = total_bid_qty + total_ask_qty

        if total_qty > 0:
            imbalance = (total_bid_qty - total_ask_qty) / total_qty
        else:
            imbalance = 0

        signals['order_imbalance'] = {
            'signal': imbalance < -0.2,  # 매도 잔량이 매수 잔량보다 20% 이상 많음
            'strength': min(1.0, abs(imbalance) / 0.5),
            'imbalance_value': imbalance,
            'bid_qty': total_bid_qty,
            'ask_qty': total_ask_qty
        }

        # 스프레드 확대
        best_bid = data_array[-1, self.col_index['매수호가1']]
        best_ask = data_array[-1, self.col_index['매도호가1']]
        current_price = data_array[-1, self.col_index['현재가']]

        if current_price > 0:
            spread_pct = (best_ask - best_bid) / current_price * 100
        else:
            spread_pct = 0

        # 평균 스프레드 계산
        spreads = []
        for i in range(max(0, len(data_array) - 50), len(data_array)):
            bid = data_array[i, self.col_index['매수호가1']]
            ask = data_array[i, self.col_index['매도호가1']]
            price = data_array[i, self.col_index['현재가']]
            if price > 0:
                spreads.append((ask - bid) / price * 100)

        avg_spread = np.mean(spreads) if spreads else 0

        signals['spread_widening'] = {
            'signal': spread_pct > avg_spread * 1.5,  # 스프레드가 평균보다 50% 이상 넓음
            'strength': min(1.0, spread_pct / (avg_spread * 2) if avg_spread > 0 else 0),
            'current_spread': spread_pct,
            'avg_spread': avg_spread
        }

        return signals

    def calculate_sell_score(self, all_signals: Dict) -> float:
        """종합 매도 점수 계산 (0.0 - 1.0)"""
        total_score = 0.0
        total_weight = 0.0

        for signal_type, signals in all_signals.items():
            weight = self.signal_weights.get(signal_type, 0.1)
            signal_score = self.calculate_signal_score(signals)

            total_score += signal_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0

    def calculate_signal_score(self, signals: Dict) -> float:
        """개별 시그널 그룹의 점수 계산"""
        if not signals:
            return 0.0

        total_strength = 0.0
        signal_count = 0

        for signal_name, signal_data in signals.items():
            if isinstance(signal_data, dict) and 'signal' in signal_data:
                if signal_data['signal']:
                    total_strength += signal_data.get('strength', 0.5)
                    signal_count += 1

        return total_strength / max(signal_count, 1)

    def get_sell_recommendation(self, sell_score: float) -> str:
        """매도 추천 단계"""
        if sell_score >= 0.8:
            return 'STRONG_SELL'
        elif sell_score >= 0.6:
            return 'SELL'
        elif sell_score >= 0.4:
            return 'CONSIDER_SELL'
        elif sell_score >= 0.2:
            return 'HOLD'
        else:
            return 'HOLD_STRONG'

    def calculate_optimal_sell_price(self, current_price: float, entry_price: float,
                                     sell_score: float, all_signals: Dict) -> Dict:
        """최적 매도 가격 계산"""
        # 기본 예상 가격 (현재가 기준)
        base_price = current_price

        # 기술적 저항선 고려
        technical_price = self.get_technical_target_price(all_signals['technical'], current_price)

        # 리스크 고려 가격 조정
        risk_adjustment = self.calculate_risk_adjustment(sell_score)

        # 최종 최적 가격
        optimal_price = base_price * (1 + risk_adjustment)

        # 가격 범위 제안
        price_range = {
            'conservative': base_price * (1 + risk_adjustment * 0.5),
            'moderate': optimal_price,
            'aggressive': base_price * (1 + risk_adjustment * 1.5)
        }

        return {
            'optimal_price': optimal_price,
            'price_range': price_range,
            'technical_target': technical_price,
            'risk_adjustment': risk_adjustment,
            'upside_potential': ((optimal_price - entry_price) / entry_price) * 100
        }

    def analyze_time_sensitivity(self, data_array: np.ndarray, entry_time: int) -> Dict:
        """시간 민감도 분석"""
        # 보유 기간 분석
        current_time = len(data_array)  # 단순화된 시간 계산
        holding_period = current_time - entry_time

        return {
            'holding_period': holding_period,
            'time_pressure': self.calculate_time_pressure(holding_period)
        }

    def assess_risk_level(self, all_signals: Dict) -> str:
        """리스크 레벨 평가"""
        high_risk_signals = 0
        total_signals = 0

        for signal_type, signals in all_signals.items():
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict) and 'signal' in signal_data:
                    total_signals += 1
                    if signal_data['signal'] and signal_data.get('strength', 0) > 0.7:
                        high_risk_signals += 1

        if total_signals == 0:
            return 'LOW'

        high_risk_ratio = high_risk_signals / total_signals

        if high_risk_ratio >= 0.6:
            return 'HIGH'
        elif high_risk_ratio >= 0.3:
            return 'MEDIUM'
        else:
            return 'LOW'

    def calculate_confidence(self, all_signals: Dict) -> float:
        """분석 신뢰도 계산"""
        total_confidence = 0.0
        signal_count = 0
        active_signals = 0

        for signal_type, signals in all_signals.items():
            for signal_name, signal_data in signals.items():
                if isinstance(signal_data, dict):
                    signal_count += 1
                    # 신호 강도와 일관성으로 신뢰도 계산
                    strength = max(0.0, signal_data.get('strength', 0))  # 음수 방지
                    consistency = self.calculate_signal_consistency(signal_data)
                    
                    # 활성 신호에 가중치 부여
                    if signal_data.get('signal', False):
                        active_signals += 1
                        total_confidence += (strength + consistency) / 2 * 1.2  # 20% 가중치
                    else:
                        total_confidence += (strength + consistency) / 2

        # 기본 신뢰도 보정 (데이터가 있다는 것 자체로 최소 신뢰도 부여)
        base_confidence = 0.3
        if signal_count > 0:
            avg_confidence = total_confidence / signal_count
            # 활성 신호 비율에 따른 추가 보정
            active_ratio = active_signals / signal_count
            confidence = base_confidence + avg_confidence * 0.4 + active_ratio * 0.3
        else:
            confidence = 0.0

        return max(0.0, min(1.0, confidence))  # 0-1 범위 제한

    # 보조 계산 함수들
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI 계산"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')

        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std: float = 2.0):
        """볼린저밴드 계산"""
        sma = self.calculate_sma(prices, period)
        rolling_std = self.calculate_rolling_std(prices, period)

        upper = sma + (rolling_std * std)
        lower = sma - (rolling_std * std)

        return upper, sma, lower

    def calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """단순이동평균 계산"""
        return np.convolve(prices, np.ones(period)/period, mode='valid')

    def calculate_rolling_std(self, prices: np.ndarray, period: int) -> np.ndarray:
        """이동표준편차 계산"""
        result = []
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            result.append(np.std(window))
        return np.array(result)

    def calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD 계산"""
        ema_fast = self.calculate_ema(prices, fast)
        ema_slow = self.calculate_ema(prices, slow)

        macd_line = ema_fast[len(ema_slow) - len(ema_fast):] - ema_slow
        signal_line = self.calculate_ema(macd_line, signal)

        return macd_line, signal_line

    def calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """지수이동평균 계산"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]

        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]

        return ema

    def calculate_momentum(self, prices: np.ndarray, period: int = 10) -> np.ndarray:
        """모멘텀 계산"""
        return np.diff(prices, n=period) if len(prices) > period else np.array([])

    def calculate_volatility(self, prices: np.ndarray, period: int = 20) -> np.ndarray:
        """변동성 계산"""
        returns = np.diff(prices) / prices[:-1]
        return self.calculate_rolling_std(returns, period) if len(returns) >= period else np.array([])

    def find_resistance_levels(self, prices: np.ndarray, lookback: int = 50) -> List[float]:
        """저항선 찾기"""
        if len(prices) < lookback:
            return []

        recent_prices = prices[-lookback:]
        resistance_levels = []

        # 로컬 최대값 찾기
        for i in range(1, len(recent_prices) - 1):
            if recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i+1]:
                resistance_levels.append(recent_prices[i])

        return sorted(resistance_levels, reverse=True)[:3]  # 상위 3개 저항선

    def check_resistance_approach(self, current_price: float, resistance_levels: List[float]) -> Dict:
        """저항선 접근 확인"""
        if not resistance_levels:
            return {'signal': False, 'strength': 0, 'nearest_resistance': None}

        nearest_resistance = resistance_levels[0]
        distance_pct = (nearest_resistance - current_price) / current_price * 100

        return {
            'signal': distance_pct < 2.0,  # 2% 이내 접근
            'strength': min(1.0, (2.0 - distance_pct) / 2.0) if distance_pct < 2.0 else 0,
            'nearest_resistance': nearest_resistance,
            'distance_pct': distance_pct
        }

    def detect_macd_divergence(self, prices: np.ndarray, macd_line: np.ndarray) -> Dict:
        """MACD 다이버전스 감지"""
        # 단순화된 다이버전스 감지
        if len(prices) < 20 or len(macd_line) < 20:
            return {'signal': False, 'strength': 0, 'type': None}

        price_trend = prices[-1] - prices[-10]
        macd_trend = macd_line[-1] - macd_line[-10]

        # 가격 상승 but MACD 하락 (베어리시 다이버전스)
        bearish_divergence = price_trend > 0 > macd_trend

        # noinspection PyTypeChecker
        return {
            'signal': bearish_divergence,
            'strength': min(1.0, abs(macd_trend) / (np.std(macd_line) + 1e-10)),
            'type': 'bearish' if bearish_divergence else None
        }

    def detect_momentum_divergence(self, prices: np.ndarray, momentum: np.ndarray) -> Dict:
        """모멘텀 다이버전스 감지"""
        if len(prices) < 20 or len(momentum) < 10:
            return {'signal': False, 'strength': 0, 'type': None}

        price_trend = prices[-1] - prices[-10]
        momentum_trend = momentum[-1] - momentum[-5] if len(momentum) > 5 else 0

        bearish_divergence = price_trend > 0 > momentum_trend

        # noinspection PyTypeChecker
        return {
            'signal': bearish_divergence,
            'strength': min(1.0, abs(momentum_trend) / (np.std(momentum) + 1e-10)),
            'type': 'bearish' if bearish_divergence else None
        }

    def detect_double_top(self, prices: np.ndarray) -> Dict:
        """더블탑 패턴 감지"""
        if len(prices) < 20:
            return {'signal': False, 'strength': 0}

        # 단순화된 더블탑 감지
        recent_prices = prices[-20:]

        # 두 개의 고점 찾기
        peaks = []
        for i in range(1, len(recent_prices) - 1):
            if recent_prices[i] > recent_prices[i-1] and recent_prices[i] > recent_prices[i+1]:
                peaks.append((i, recent_prices[i]))

        if len(peaks) >= 2:
            # 첫 두 개 고점이 비슷한 높이인지 확인
            peak1, peak2 = peaks[0], peaks[1]
            height_diff = abs(peak1[1] - peak2[1]) / peak1[1]

            if height_diff < 0.02:  # 2% 이내 차이
                return {
                    'signal': True,
                    'strength': 1.0 - height_diff / 0.02,
                    'peak1_price': peak1[1],
                    'peak2_price': peak2[1]
                }

        return {'signal': False, 'strength': 0}
    
    def detect_head_shoulders(self, prices: np.ndarray) -> Dict:
        """헤드앤숄더 패턴 감지"""
        # 단순화된 헤드앤숄더 감지
        if len(prices) < 30:
            return {'signal': False, 'strength': 0}

        # 실제 구현은 더 복잡하지만 여기서는 단순화
        return {'signal': False, 'strength': 0}

    def detect_rising_wedge(self, prices: np.ndarray) -> Dict:
        """상승 쐐기판 패턴 감지"""
        # 단순화된 상승 쐐기판 감지
        if len(prices) < 20:
            return {'signal': False, 'strength': 0}

        return {'signal': False, 'strength': 0}

    def get_technical_target_price(self, technical_signals: Dict, current_price: float) -> float:
        """기술적 분석 기반 목표가"""
        target_prices = []

        # 저항선 고려
        if 'resistance_approach' in technical_signals:
            resistance = technical_signals['resistance_approach']
            if resistance['nearest_resistance']:
                target_prices.append(resistance['nearest_resistance'])

        # 볼린저밴드 상단 고려
        if 'bollinger_upper' in technical_signals:
            bb_upper = technical_signals['bollinger_upper']
            if bb_upper['signal']:
                target_prices.append(current_price * (1 + bb_upper['penetration_pct'] / 100))

        return np.mean(target_prices) if target_prices else current_price

    def calculate_risk_adjustment(self, sell_score: float) -> float:
        """리스크 기반 가격 조정"""
        # 매도 점수가 높을수록 더 보수적인 가격 조정
        if sell_score >= 0.8:
            return 0.01  # 1% 상향 조정
        elif sell_score >= 0.6:
            return 0.005  # 0.5% 상향 조정
        else:
            return 0

    def calculate_time_pressure(self, holding_period: int) -> float:
        """시간 압박 계산"""
        # 보유 기간이 길수록 압박 증가
        return min(1.0, holding_period / 1000)

    def calculate_signal_consistency(self, signal_data: Dict) -> float:
        """시그널 일관성 계산"""
        # 시그널이 활성화되어 있으면 일관성 높음, 아니면 낮음
        if signal_data.get('signal', False):
            # 활성 신호는 기본 0.7 + strength의 30% 가중치
            return min(1.0, 0.7 + signal_data.get('strength', 0) * 0.3)
        else:
            # 비활성 신호도 일정 수준의 일관성 인정 (데이터가 있다는 것 자체)
            return 0.3

    def _get_insufficient_data_result(self) -> Dict:
        """데이터 부족 시 결과"""
        return {
            'sell_score': 0.0,
            'recommendation': 'INSUFFICIENT_DATA',
            'confidence': 0.0,
            'risk_level': 'UNKNOWN',
            'message': '분석에 필요한 데이터가 부족합니다'
        }
