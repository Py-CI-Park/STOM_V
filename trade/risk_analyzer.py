
import numpy as np
try:
    from numba import jit

    @jit(nopython=True, cache=True, fastmath=True)
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """RSI 계산 (Numba JIT 최적화)"""
        n = len(prices)
        if n < period + 1:
            return 50.0

        deltas = np.zeros(n - 1, dtype=np.float64)
        for i in range(n - 1):
            deltas[i] = prices[i + 1] - prices[i]

        gains = np.zeros(n - 1, dtype=np.float64)
        losses = np.zeros(n - 1, dtype=np.float64)
        for i in range(n - 1):
            if deltas[i] > 0:
                gains[i] = deltas[i]
            else:
                losses[i] = -deltas[i]

        avg_gain = 0.0
        avg_loss = 0.0
        for i in range(n - 1 - period, n - 1):
            avg_gain += gains[i]
            avg_loss += losses[i]
        avg_gain /= period
        avg_loss /= period

        if avg_loss == 0.0:
            return 100.0
        elif avg_gain == 0.0:
            return 0.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
            return rsi


    @jit(nopython=True, cache=True, fastmath=True)
    def _calculate_volatility(prices: np.ndarray, window: int = 20) -> float:
        """변동성 계산 (Numba JIT 최적화)"""
        n = len(prices)
        if n < window:
            return 0.0

        returns = np.zeros(n - window, dtype=np.float64)
        for i in range(n - window):
            if prices[i + window - 1] != 0:
                returns[i] = (prices[i + window] - prices[i + window - 1]) / prices[i + window - 1]

        mean_return = 0.0
        for i in range(n - window):
            mean_return += returns[i]
        mean_return /= (n - window)

        variance = 0.0
        for i in range(n - window):
            diff = returns[i] - mean_return
            variance += diff * diff
        variance /= (n - window)

        volatility = np.sqrt(variance) * np.sqrt(252.0) * 100.0
        return volatility
except:
    def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
        """RSI 계산 (Fallback 버전)"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0
        elif avg_gain == 0:
            return 0.0
        else:
            # noinspection PyTypeChecker
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi


    def _calculate_volatility(prices: np.ndarray, window: int = 20) -> float:
        """변동성 계산 (Fallback 버전)"""
        if len(prices) < window:
            return 0.0
        recent_prices = prices[-window:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        volatility = np.std(returns) * np.sqrt(252) * 100
        return volatility


class RiskAnalyzer:
    def __init__(self, market_type: str = 'stock'):
        """market_type: 'stock', 'coin', 'future'"""
        self.market_type = market_type
        self._setup_analysis_parameters()
        self._setup_columns()

    def _setup_columns(self):
        """
        시장 및 데이터 타입에 따른 칼럼 설정
        """
        # 시장 종류에 따라 칼럼 목록 선택
        if self.market_type == 'stock':
            from utility.setting_base import list_stock_tick
            self.columns = list_stock_tick
        else:
            from utility.setting_base import list_coin_tick
            self.columns = list_coin_tick

        # 칼럼 인덱스 매핑 (빠른 접근용)
        col_index = {col: idx for idx, col in enumerate(self.columns)}
        self.idx_curr_price = col_index.get('현재가', 1)
        self.idx_volume = col_index.get('당일거래대금', 6)
        self.idx_chegyeol_strength = col_index.get('체결강도', 7)
        self.idx_buy_vol = col_index.get('초당매수수량', 8)
        self.idx_sell_vol = col_index.get('초당매도수량', 9)
        self.idx_trade_amount = col_index.get('초당거래대금', 10)
        self.idx_high_low_ratio = col_index.get('고저평균대비등락율', 11)
        self.idx_low_high_ratio = col_index.get('저가대비고가등락율', 12)
        self.idx_buy_amount = col_index.get('초당매수금액', 13)
        self.idx_sell_amount = col_index.get('초당매도금액', 14)
        self.idx_day_buy_amount = col_index.get('당일매수금액', 15)
        self.idx_max_buy_amount = col_index.get('최고매수금액', 16)
        self.idx_max_buy_price = col_index.get('최고매수가격', 17)
        self.idx_day_sell_amount = col_index.get('당일매도금액', 18)
        self.idx_max_sell_amount = col_index.get('최고매도금액', 19)
        self.idx_max_sell_price = col_index.get('최고매도가격', 20)
        self.idx_max_price = col_index.get('최고현재가', 30)
        self.idx_min_price = col_index.get('최저현재가', 31)
        self.idx_chegyeol_avg = col_index.get('체결강도평균', 33)
        self.idx_max_strength = col_index.get('최고체결강도', 34)
        self.idx_min_strength = col_index.get('최저체결강도', 35)
        self.idx_max_buy_vol = col_index.get('최고초당매수수량', 36)
        self.idx_max_sell_vol = col_index.get('최고초당매도수량', 37)
        self.idx_change_angle = col_index.get('등락율각도', 43)
        self.idx_volume_angle = col_index.get('당일거래대금각도', 44)

    def _setup_analysis_parameters(self):
        """시장 종류별 분석 파라미터 설정"""
        if self.market_type == 'stock':
            self.params = {
                'rsi_overbought': 70,               # 과매수 RSI
                'rsi_oversold': 30,                 # 과매도 RSI
                'volatility_threshold': 3.0,        # 변동성 임계값
            }
        elif self.market_type == 'coin':
            self.params = {
                'rsi_overbought': 75,               # 코인은 더 높은 과매수 기준
                'rsi_oversold': 25,                 # 코인은 더 낮은 과매도 기준
                'volatility_threshold': 5.0,        # 코인은 더 높은 변동성 허용
            }
        else:
            self.params = {
                'rsi_overbought': 72,
                'rsi_oversold': 28,
                'volatility_threshold': 4.0,
            }

    def get_risk_score(self, arry_code: np.ndarray) -> float:
        """리스크점수 계산"""
        try:
            analysis = self._analyze_market_data(arry_code)
            risk_score = self._calculate_risk_score(analysis)
            return risk_score
        except:
            return 0.0

    def _analyze_market_data(self, arry_code: np.ndarray) -> dict:
        """시장 데이터 분석"""
        current_prices = arry_code[:, self.idx_curr_price]    # 현재가
        volumes = arry_code[:, self.idx_volume]           # 거래대금

        rsi = _calculate_rsi(current_prices)
        volatility = _calculate_volatility(current_prices)
        trend = self._analyze_trend(current_prices)
        momentum = self._calculate_momentum(current_prices)
        volume_trend = self._analyze_volume_trend(volumes)
        chegyeol_strength = self._analyze_chegyeol_strength(arry_code)
        suyang_imbalance = self._analyze_suyang_imbalance(arry_code)
        price_position = self._analyze_price_position(arry_code)
        angle_analysis = self._analyze_angle_trend(arry_code)

        return {
            'rsi': rsi,
            'volatility': volatility,
            'trend': trend,
            'momentum': momentum,
            'volume_trend': volume_trend,
            'chegyeol_strength': chegyeol_strength,
            'suyang_imbalance': suyang_imbalance,
            'price_position': price_position,
            'angle_analysis': angle_analysis
        }

    def _analyze_trend(self, prices: np.ndarray) -> dict:
        """추세 분석"""
        short_ma = np.mean(prices[-5:])
        medium_ma = np.mean(prices[-10:])
        long_ma = np.mean(prices[-20:])
        current_price = prices[-1]

        if current_price > short_ma > medium_ma > long_ma:
            direction = 'strong_uptrend'
        elif current_price > short_ma > medium_ma:
            direction = 'uptrend'
        elif current_price < short_ma < medium_ma < long_ma:
            direction = 'strong_downtrend'
        elif current_price < short_ma < medium_ma:
            direction = 'downtrend'
        else:
            direction = 'neutral'

        x = np.arange(len(prices))
        # noinspection PyTypeChecker
        slope = np.polyfit(x, prices, 1)[0] / np.mean(prices) * 100
        strength = abs(slope)

        return {
            'direction': direction,
            'strength': strength,
            'momentum': slope,
            'short_ma': short_ma,
            'medium_ma': medium_ma,
            'long_ma': long_ma
        }

    def _calculate_momentum(self, prices: np.ndarray) -> dict:
        """모멘텀 분석"""
        short_momentum = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        medium_momentum = (prices[-1] - prices[-10]) / prices[-10] * 100 if len(prices) >= 10 else 0

        if short_momentum > 2 and medium_momentum > 1:
            momentum_trend = 'bullish'
        elif short_momentum < -2 and medium_momentum < -1:
            momentum_trend = 'bearish'
        else:
            momentum_trend = 'neutral'

        return {
            'short_momentum': short_momentum,
            'medium_momentum': medium_momentum,
            'momentum_trend': momentum_trend
        }

    def _analyze_chegyeol_strength(self, arry_code: np.ndarray) -> dict:
        """체결강도 분석"""
        chegyeol_strength = arry_code[:, self.idx_chegyeol_strength]    # 체결강도
        chegyeol_avg = arry_code[:, self.idx_chegyeol_avg]              # 체결강도평균
        max_strength = arry_code[:, self.idx_max_strength]              # 최고체결강도
        min_strength = arry_code[:, self.idx_min_strength]              # 최저체결강도

        current_strength = chegyeol_strength[-1]
        avg_strength = chegyeol_avg[-1]

        if current_strength > avg_strength * 2:
            trend = 'spike'
        elif current_strength < avg_strength * 0.5:
            trend = 'weak'
        else:
            trend = 'normal'
        
        return {
            'current_strength': current_strength,
            'avg_strength': avg_strength,
            'max_strength': max_strength[-1],
            'min_strength': min_strength[-1],
            'trend': trend,
            'deviation': abs(current_strength - avg_strength) / avg_strength if avg_strength > 0 else 0
        }
    
    def _analyze_suyang_imbalance(self, arry_code: np.ndarray) -> dict:
        """수량 불균형 분석"""
        buy_suyang = arry_code[:, self.idx_buy_vol]   # 초당매수수량
        sell_suyang = arry_code[:, self.idx_sell_vol]  # 초당매도수량

        current_buy = buy_suyang[-1]
        current_sell = sell_suyang[-1]

        total = current_buy + current_sell
        if total > 0:
            buy_ratio = current_buy / total
            sell_ratio = current_sell / total
            imbalance = abs(buy_ratio - 0.5) * 2
        else:
            buy_ratio = sell_ratio = 0.5
            imbalance = 0

        if buy_ratio > 0.7:
            direction = 'buy_dominant'
        elif sell_ratio > 0.7:
            direction = 'sell_dominant'
        else:
            direction = 'balanced'
        
        return {
            'buy_ratio': buy_ratio,
            'sell_ratio': sell_ratio,
            'imbalance': imbalance,
            'direction': direction,
            'current_buy': current_buy,
            'current_sell': current_sell
        }
    
    def _analyze_price_position(self, arry_code: np.ndarray) -> dict:
        """가격 위치 분석"""
        current_price = arry_code[-1, self.idx_curr_price]
        high_low_avg_ratio = arry_code[:, self.idx_high_low_ratio]  # 고저평균대비등락율
        low_high_ratio = arry_code[:, self.idx_low_high_ratio]      # 저가대비고가등락율
        max_price = arry_code[:, self.idx_max_price]                # 최고현재가
        min_price = arry_code[:, self.idx_min_price]                # 최저현재가

        current_high_low = high_low_avg_ratio[-1]
        current_low_high = low_high_ratio[-1]

        if abs(current_high_low) > 5:
            position = 'extreme'
        elif abs(current_high_low) > 2:
            position = 'far'
        elif abs(current_high_low) > 1:
            position = 'moderate'
        else:
            position = 'normal'

        max_current = max_price[-1]
        min_current = min_price[-1]
        if max_current != min_current:
            price_range_position = (current_price - min_current) / (max_current - min_current)
        else:
            price_range_position = 0.5

        return {
            'position': position,
            'high_low_ratio': current_high_low,
            'low_high_ratio': current_low_high,
            'price_range_position': price_range_position,
            'max_price': max_current,
            'min_price': min_current
        }

    def _analyze_angle_trend(self, arry_code: np.ndarray) -> dict:
        """각도 추세 분석"""
        change_angle = arry_code[:, self.idx_change_angle]    # 등락율각도
        volume_angle = arry_code[:, self.idx_volume_angle]    # 당일거래대금각도

        current_change_angle = change_angle[-1]
        current_volume_angle = volume_angle[-1]

        if current_change_angle > 45:
            change_trend = 'strong_uptrend'
        elif current_change_angle > 15:
            change_trend = 'uptrend'
        elif current_change_angle < -45:
            change_trend = 'strong_downtrend'
        elif current_change_angle < -15:
            change_trend = 'downtrend'
        else:
            change_trend = 'sideways'

        return {
            'change_angle': current_change_angle,
            'volume_angle': current_volume_angle,
            'change_trend': change_trend,
            'angle_strength': abs(current_change_angle)
        }

    def _analyze_volume_trend(self, volumes: np.ndarray) -> dict:
        """거래량 추세 분석"""
        recent_avg = np.mean(volumes[-5:])
        previous_avg = np.mean(volumes[-10:-5]) if len(volumes) >= 10 else recent_avg
        # noinspection PyTypeChecker
        volume_change = (recent_avg - previous_avg) / previous_avg * 100 if previous_avg > 0 else 0
        # noinspection PyTypeChecker
        spike = recent_avg > previous_avg * 2

        if volume_change > 30:
            trend = 'increasing'
        elif volume_change < -30:
            trend = 'decreasing'
        else:
            trend = 'normal'

        return {
            'trend': trend,
            'spike': spike,
            'change_percent': volume_change,
            'recent_avg': recent_avg,
            'previous_avg': previous_avg
        }

    def _calculate_risk_score(self, analysis: dict) -> float:
        """리스크 점수 계산 (0-100) - 모든 분석 요소 적극 반영"""
        rsi = analysis.get('rsi', 50)
        volatility = analysis.get('volatility', 0)
        trend = analysis.get('trend', {})
        momentum = analysis.get('momentum', {})
        volume_trend = analysis.get('volume_trend', {})
        chegyeol_strength = analysis.get('chegyeol_strength', {})
        suyang_imbalance = analysis.get('suyang_imbalance', {})
        price_position = analysis.get('price_position', {})
        angle_analysis = analysis.get('angle_analysis', {})

        # 1. RSI 리스크 (0-15점)
        rsi_risk = 0
        if rsi > self.params['rsi_overbought']:
            rsi_risk = (rsi - self.params['rsi_overbought']) / (100 - self.params['rsi_overbought']) * 15
        elif rsi < self.params['rsi_oversold']:
            rsi_risk = (self.params['rsi_oversold'] - rsi) / self.params['rsi_oversold'] * 12

        # 2. 변동성 리스크 (0-15점)
        volatility_risk = min(volatility / self.params['volatility_threshold'] * 15, 15)

        # 3. 추세 리스크 (0-15점)
        trend_risk = 0
        direction = trend.get('direction', 'neutral')
        strength = trend.get('strength', 0)

        if direction == 'strong_downtrend':
            trend_risk = 15
        elif direction == 'downtrend':
            trend_risk = 12
        elif direction == 'neutral' and strength > 1.0:
            trend_risk = 8
        elif direction == 'uptrend':
            trend_risk = 3

        # 4. 모멘텀 리스크 (0-10점)
        momentum_risk = 0
        momentum_trend = momentum.get('momentum_trend', 'neutral')
        short_momentum = momentum.get('short_momentum', 0)
        medium_momentum = momentum.get('medium_momentum', 0)

        if momentum_trend == 'bearish':
            momentum_risk = 10
        elif momentum_trend == 'neutral':
            if short_momentum < -3 or medium_momentum < -2:
                momentum_risk = 7
            elif short_momentum < -1 or medium_momentum < -0.5:
                momentum_risk = 4

        # 5. 거래량 리스크 (0-8점)
        volume_risk = 0
        volume_change = volume_trend.get('change_percent', 0)
        spike = volume_trend.get('spike', False)

        if spike:
            volume_risk = 8
        elif abs(volume_change) > 50:
            volume_risk = 6
        elif volume_change < -30:
            volume_risk = 4

        # 6. 체결강도 리스크 (0-12점)
        chegyeol_risk = 0
        strength_trend = chegyeol_strength.get('trend', 'normal')
        deviation = chegyeol_strength.get('deviation', 0)

        if strength_trend == 'spike':
            chegyeol_risk = 12
        elif strength_trend == 'weak':
            chegyeol_risk = 8
        elif deviation > 1.0:
            chegyeol_risk = 6

        # 7. 수량 불균형 리스크 (0-10점)
        suyang_risk = 0
        imbalance_direction = suyang_imbalance.get('direction', 'balanced')
        imbalance = suyang_imbalance.get('imbalance', 0)

        if imbalance_direction == 'sell_dominant':
            suyang_risk = min(imbalance * 20, 10)
        elif imbalance_direction == 'buy_dominant':
            suyang_risk = min(imbalance * 10, 5)

        # 8. 가격 위치 리스크 (0-8점)
        price_risk = 0
        price_pos = price_position.get('position', 'normal')
        range_pos = price_position.get('price_range_position', 0.5)

        if price_pos == 'extreme':
            price_risk = 8
        elif price_pos == 'far':
            price_risk = 6
        elif price_pos == 'moderate':
            price_risk = 3

        # 극단적 위치 추가 리스크
        if range_pos > 0.9 or range_pos < 0.1:
            price_risk = min(price_risk + 4, 8)

        # 9. 각도 추세 리스크 (0-7점)
        angle_risk = 0
        angle_trend = angle_analysis.get('change_trend', 'sideways')

        if angle_trend == 'strong_downtrend':
            angle_risk = 7
        elif angle_trend == 'downtrend':
            angle_risk = 5
        elif angle_trend == 'strong_uptrend':
            angle_risk = 2  # 급등도 리스크

        # 총 리스크 점수 계산 (0-100점)
        total_risk = (rsi_risk + volatility_risk + trend_risk + momentum_risk + 
                      volume_risk + chegyeol_risk + suyang_risk + price_risk + angle_risk)
        
        return round(min(total_risk, 100.0), 2)
