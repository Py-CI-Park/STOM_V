
import numpy as np
from numba import njit, prange


@njit(cache=True, fastmath=True)
def _calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """RSI 계산 (Numba JIT 최적화) - 마지막 period개만 계산"""
    n = len(prices)
    if n < period + 1:
        return 50.0
    avg_gain = 0.0
    avg_loss = 0.0
    start_idx = n - period - 1
    for i in range(period):
        delta = prices[start_idx + i + 1] - prices[start_idx + i]
        if delta > 0:
            avg_gain += delta
        else:
            avg_loss += -delta
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


@njit(cache=True, fastmath=True, parallel=True)
def _calculate_volatility(prices: np.ndarray, window: int = 20) -> float:
    """변동성 계산 (Numba JIT 최적화)"""
    n = len(prices)
    if n <= window:
        return 0.0
    returns = np.zeros(n - window, dtype=np.float64)
    for i in prange(n - window):
        future1_price = prices[i + window]
        future2_price = prices[i + window - 1]
        returns[i] = (future1_price / future2_price - 1)
    mean_return = np.mean(returns)
    variance    = np.sum((returns - mean_return) ** 2) / (n - window)
    volatility  = np.sqrt(variance) * np.sqrt(250.0) * 100.0
    return volatility


class AnalyzerRisk:
    """리스크 분석을 수행하는 클래스입니다.
    RSI, 변동성 등 리스크 관련 지표를 계산합니다."""
    def __init__(self, market_type: str, dict_findex: dict):
        self.market_type = market_type
        self.dict_findex = dict_findex
        self._setup_columns()
        self._setup_analysis_parameters()

    def _setup_columns(self):
        """시장 및 데이터 타입에 따른 칼럼 설정"""
        self.is_tick = '초당매수수량' in self.dict_findex
        self.idx_curr_price        = self.dict_findex['현재가']
        self.idx_volume            = self.dict_findex['당일거래대금']
        self.idx_chegyeol_strength = self.dict_findex['체결강도']
        if self.is_tick:
            self.idx_buy_vol       = self.dict_findex['초당매수수량']
            self.idx_sell_vol      = self.dict_findex['초당매도수량']
        else:
            self.idx_buy_vol       = self.dict_findex['분당매수수량']
            self.idx_sell_vol      = self.dict_findex['분당매도수량']
        self.idx_high_low_ratio    = self.dict_findex['고저평균대비등락율']
        self.idx_max_price         = self.dict_findex['최고현재가']
        self.idx_min_price         = self.dict_findex['최저현재가']
        self.idx_chegyeol_avg      = self.dict_findex['체결강도평균']
        self.idx_change_angle      = self.dict_findex['등락율각도']

    def _setup_analysis_parameters(self):
        """분석 파라미터를 설정합니다.
        시장 종류별 및 틱봉/분봉별 분석 파라미터 설정"""
        if self.market_type == 'stock':
            if self.is_tick:
                self.params = {
                    # RSI 파라미터
                    'rsi_overbought': 70,                       # 과매수 RSI
                    'rsi_oversold': 30,                         # 과매도 RSI
                    'volatility_threshold': 3.0,                # 변동성 임계값
                    # 추세 분석 기간
                    'trend_short_period': 5,                    # 단기 이동평균 기간
                    'trend_medium_period': 10,                  # 중기 이동평균 기간
                    'trend_long_period': 20,                    # 장기 이동평균 기간
                    # 모멘텀 임계값
                    'momentum_strong_bullish_short': 2.0,       # 강세 상승 단기 모멘텀
                    'momentum_strong_bullish_medium': 1.0,      # 강세 상승 중기 모멘텀
                    'momentum_strong_bearish_short': -2.0,      # 강세 하락 단기 모멘텀
                    'momentum_strong_bearish_medium': -1.0,     # 강세 하락 중기 모멘텀
                    'momentum_moderate_bearish_short': -1.0,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.5,   # 중간 약세 기준
                    # 체결강도 배수
                    'strength_spike_multiplier': 2.0,           # 스파이크 기준 배수
                    'strength_weak_multiplier': 0.5,            # 약세 기준 배수
                    # 수량 불균형 비율
                    'imbalance_dominant_ratio': 0.7,            # 우세 비율 기준
                    # 가격 위치 퍼센트
                    'price_extreme_threshold': 5.0,             # 극단적 위치 기준 (%)
                    'price_far_threshold': 2.0,                 # 먼 위치 기준 (%)
                    'price_moderate_threshold': 1.0,            # 중간 위치 기준 (%)
                    # 각도 추세 임계값
                    'angle_strong_uptrend': 45,                 # 강한 상승 각도
                    'angle_uptrend': 15,                        # 상승 각도
                    'angle_strong_downtrend': -45,              # 강한 하락 각도
                    'angle_downtrend': -15,                     # 하락 각도
                    # 거래량 변동
                    'volume_increase_threshold': 30,            # 거래량 증가 기준 (%)
                    'volume_decrease_threshold': -30,           # 거래량 감소 기준 (%)
                    'volume_spike_multiplier': 2.0,             # 거래량 스파이크 배수
                    'volume_large_change': 50                   # 큰 변동 기준 (%)
                }
            else:  # 분봉 (더 보수적)
                self.params = {
                    # RSI 파라미터
                    'rsi_overbought': 72,                       # 과매수 RSI
                    'rsi_oversold': 28,                         # 과매도 RSI
                    'volatility_threshold': 2.5,                # 변동성 임계값
                    # 추세 분석 기간 (더 길게)
                    'trend_short_period': 3,                    # 단기 이동평균 기간
                    'trend_medium_period': 5,                   # 중기 이동평균 기간
                    'trend_long_period': 10,                    # 장기 이동평균 기간
                    # 모멘텀 임계값 (더 보수적)
                    'momentum_strong_bullish_short': 1.5,       # 강세 상승 단기 모멘텀
                    'momentum_strong_bullish_medium': 0.8,      # 강세 상승 중기 모멘텀
                    'momentum_strong_bearish_short': -1.5,      # 강세 하락 단기 모멘텀
                    'momentum_strong_bearish_medium': -0.8,     # 강세 하락 중기 모멘텀
                    'momentum_moderate_bearish_short': -0.8,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.4,   # 중간 약세 기준
                    # 체결강도 배수 (더 보수적)
                    'strength_spike_multiplier': 1.8,           # 스파이크 기준 배수
                    'strength_weak_multiplier': 0.6,            # 약세 기준 배수
                    # 수량 불균형 비율 (더 보수적)
                    'imbalance_dominant_ratio': 0.75,           # 우세 비율 기준
                    # 가격 위치 퍼센트 (더 보수적)
                    'price_extreme_threshold': 6.0,             # 극단적 위치 기준 (%)
                    'price_far_threshold': 2.5,                 # 먼 위치 기준 (%)
                    'price_moderate_threshold': 1.2,            # 중간 위치 기준 (%)
                    # 각도 추세 임계값 (더 보수적)
                    'angle_strong_uptrend': 50,                 # 강한 상승 각도
                    'angle_uptrend': 20,                        # 상승 각도
                    'angle_strong_downtrend': -50,              # 강한 하락 각도
                    'angle_downtrend': -20,                     # 하락 각도
                    # 거래량 변동 (더 보수적)
                    'volume_increase_threshold': 25,            # 거래량 증가 기준 (%)
                    'volume_decrease_threshold': -25,           # 거래량 감소 기준 (%)
                    'volume_spike_multiplier': 1.8,             # 거래량 스파이크 배수
                    'volume_large_change': 40                   # 큰 변동 기준 (%)
                }
        elif self.market_type == 'coin':
            if self.is_tick:
                self.params = {
                    # 코인은 더 높은 변동성과 빠른 움직임 특성 반영
                    'rsi_overbought': 75,                       # 코인은 더 높은 과매수 기준
                    'rsi_oversold': 25,                         # 코인은 더 낮은 과매도 기준
                    'volatility_threshold': 5.0,                # 코인은 더 높은 변동성 허용
                    # 추세 분석 기간 (더 짧게)
                    'trend_short_period': 3,                    # 더 짧은 단기 기간
                    'trend_medium_period': 8,                   # 더 짧은 중기 기간
                    'trend_long_period': 15,                    # 더 짧은 장기 기간
                    # 모멘텀 임계값 (더 민감하게)
                    'momentum_strong_bullish_short': 1.5,       # 더 낮은 기준
                    'momentum_strong_bullish_medium': 0.8,      # 더 낮은 기준
                    'momentum_strong_bearish_short': -1.5,      # 더 높은 기준
                    'momentum_strong_bearish_medium': -0.8,     # 더 높은 기준
                    'momentum_moderate_bearish_short': -0.8,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.4,   # 중간 약세 기준
                    # 체결강도 배수 (더 변동성 크게)
                    'strength_spike_multiplier': 2.5,           # 더 큰 스파이크 기준
                    'strength_weak_multiplier': 0.4,            # 더 낮은 약세 기준
                    # 수량 불균형 비율 (더 극단적)
                    'imbalance_dominant_ratio': 0.75,           # 더 높은 우세 기준
                    # 가격 위치 퍼센트 (더 넓은 범위)
                    'price_extreme_threshold': 8.0,             # 더 넓은 극단 기준
                    'price_far_threshold': 3.0,                 # 더 넓은 먼 기준
                    'price_moderate_threshold': 1.5,            # 더 넓은 중간 기준
                    # 각도 추세 임계값 (더 민감하게)
                    'angle_strong_uptrend': 35,                 # 더 낮은 강상승 기준
                    'angle_uptrend': 12,                        # 더 낮은 상승 기준
                    'angle_strong_downtrend': -35,              # 더 높은 강하락 기준
                    'angle_downtrend': -12,                     # 더 높은 하락 기준
                    # 거래량 변동 (더 변동성 크게)
                    'volume_increase_threshold': 40,            # 더 높은 증가 기준
                    'volume_decrease_threshold': -40,           # 더 낮은 감소 기준
                    'volume_spike_multiplier': 2.2,             # 더 큰 스파이크 기준
                    'volume_large_change': 60                   # 더 큰 변동 기준
                }
            else:  # 분봉 (더 보수적)
                self.params = {
                    # 코인 분봉은 보수적 기준
                    'rsi_overbought': 77,                       # 더 높은 과매수 기준
                    'rsi_oversold': 23,                         # 더 낮은 과매도 기준
                    'volatility_threshold': 4.0,                # 중간 변동성 허용
                    # 추세 분석 기간 (중간 수준)
                    'trend_short_period': 2,                    # 중간 단기 기간
                    'trend_medium_period': 5,                   # 중간 중기 기간
                    'trend_long_period': 10,                    # 중간 장기 기간
                    # 모멘텀 임계값 (보수적)
                    'momentum_strong_bullish_short': 1.2,       # 더 낮은 기준
                    'momentum_strong_bullish_medium': 0.6,      # 더 낮은 기준
                    'momentum_strong_bearish_short': -1.2,      # 더 높은 기준
                    'momentum_strong_bearish_medium': -0.6,     # 더 높은 기준
                    'momentum_moderate_bearish_short': -0.6,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.3,   # 중간 약세 기준
                    # 체결강도 배수 (보수적)
                    'strength_spike_multiplier': 2.0,           # 중간 스파이크 기준
                    'strength_weak_multiplier': 0.5,            # 중간 약세 기준
                    # 수량 불균형 비율 (보수적)
                    'imbalance_dominant_ratio': 0.78,           # 더 높은 우세 기준
                    # 가격 위치 퍼센트 (보수적)
                    'price_extreme_threshold': 9.0,             # 더 넓은 극단 기준
                    'price_far_threshold': 3.5,                 # 더 넓은 먼 기준
                    'price_moderate_threshold': 1.8,            # 더 넓은 중간 기준
                    # 각도 추세 임계값 (보수적)
                    'angle_strong_uptrend': 40,                 # 중간 강상승 기준
                    'angle_uptrend': 15,                        # 중간 상승 기준
                    'angle_strong_downtrend': -40,              # 중간 강하락 기준
                    'angle_downtrend': -15,                     # 중간 하락 기준
                    # 거래량 변동 (보수적)
                    'volume_increase_threshold': 35,            # 중간 증가 기준
                    'volume_decrease_threshold': -35,           # 중간 감소 기준
                    'volume_spike_multiplier': 2.0,             # 중간 스파이크 기준
                    'volume_large_change': 50                   # 중간 변동 기준
                }
        else:  # future
            if self.is_tick:
                self.params = {
                    # 선물은 레버리지로 인한 보수적 기준
                    'rsi_overbought': 72,                       # 중간 수준
                    'rsi_oversold': 28,                         # 중간 수준
                    'volatility_threshold': 4.0,                # 중간 변동성
                    # 추세 분석 기간 (중간 수준)
                    'trend_short_period': 4,                    # 중간 단기 기간
                    'trend_medium_period': 9,                   # 중간 중기 기간
                    'trend_long_period': 18,                    # 중간 장기 기간
                    # 모멘텀 임계값 (보수적)
                    'momentum_strong_bullish_short': 1.8,       # 중간 기준
                    'momentum_strong_bullish_medium': 0.9,      # 중간 기준
                    'momentum_strong_bearish_short': -1.8,      # 중간 기준
                    'momentum_strong_bearish_medium': -0.9,     # 중간 기준
                    'momentum_moderate_bearish_short': -0.9,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.45,  # 중간 약세 기준
                    # 체결강도 배수 (중간 수준)
                    'strength_spike_multiplier': 2.2,           # 중간 스파이크 기준
                    'strength_weak_multiplier': 0.45,           # 중간 약세 기준
                    # 수량 불균형 비율 (보수적)
                    'imbalance_dominant_ratio': 0.72,           # 중간 우세 기준
                    # 가격 위치 퍼센트 (보수적)
                    'price_extreme_threshold': 6.0,             # 중간 극단 기준
                    'price_far_threshold': 2.5,                 # 중간 먼 기준
                    'price_moderate_threshold': 1.2,            # 중간 중간 기준
                    # 각도 추세 임계값 (보수적)
                    'angle_strong_uptrend': 40,                 # 중간 강상승 기준
                    'angle_uptrend': 13,                        # 중간 상승 기준
                    'angle_strong_downtrend': -40,              # 중간 강하락 기준
                    'angle_downtrend': -13,                     # 중간 하락 기준
                    # 거래량 변동 (보수적)
                    'volume_increase_threshold': 35,            # 중간 증가 기준
                    'volume_decrease_threshold': -35,           # 중간 감소 기준
                    'volume_spike_multiplier': 2.1,             # 중간 스파이크 기준
                    'volume_large_change': 55                   # 중간 변동 기준
                }
            else:  # 분봉 (더 보수적)
                self.params = {
                    # 선물 분봉은 더 보수적 기준
                    'rsi_overbought': 74,                       # 더 높은 과매수 기준
                    'rsi_oversold': 26,                         # 더 낮은 과매도 기준
                    'volatility_threshold': 3.5,                # 더 낮은 변동성
                    # 추세 분석 기간 (더 길게)
                    'trend_short_period': 3,                    # 더 긴 단기 기간
                    'trend_medium_period': 6,                   # 더 긴 중기 기간
                    'trend_long_period': 12,                    # 더 긴 장기 기간
                    # 모멘텀 임계값 (더 보수적)
                    'momentum_strong_bullish_short': 1.5,       # 더 낮은 기준
                    'momentum_strong_bullish_medium': 0.7,      # 더 낮은 기준
                    'momentum_strong_bearish_short': -1.5,      # 더 높은 기준
                    'momentum_strong_bearish_medium': -0.7,     # 더 높은 기준
                    'momentum_moderate_bearish_short': -0.7,    # 중간 약세 기준
                    'momentum_moderate_bearish_medium': -0.35,  # 중간 약세 기준
                    # 체결강도 배수 (더 보수적)
                    'strength_spike_multiplier': 2.0,           # 더 낮은 스파이크 기준
                    'strength_weak_multiplier': 0.5,            # 더 높은 약세 기준
                    # 수량 불균형 비율 (더 보수적)
                    'imbalance_dominant_ratio': 0.75,           # 더 높은 우세 기준
                    # 가격 위치 퍼센트 (더 보수적)
                    'price_extreme_threshold': 7.0,             # 더 넓은 극단 기준
                    'price_far_threshold': 3.0,                 # 더 넓은 먼 기준
                    'price_moderate_threshold': 1.5,            # 더 넓은 중간 기준
                    # 각도 추세 임계값 (더 보수적)
                    'angle_strong_uptrend': 45,                 # 더 높은 강상승 기준
                    'angle_uptrend': 15,                        # 더 높은 상승 기준
                    'angle_strong_downtrend': -45,              # 더 낮은 강하락 기준
                    'angle_downtrend': -15,                     # 더 낮은 하락 기준
                    # 거래량 변동 (더 보수적)
                    'volume_increase_threshold': 30,            # 더 낮은 증가 기준
                    'volume_decrease_threshold': -30,           # 더 높은 감소 기준
                    'volume_spike_multiplier': 2.0,             # 더 낮은 스파이크 기준
                    'volume_large_change': 45                   # 더 낮은 변동 기준
                }

    def get_risk_score(self, code_data: np.ndarray) -> float:
        """리스크 점수를 반환합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            리스크 점수
        """
        analysis = self._analyze_market_data(code_data)
        risk_score = self._calculate_risk_score(analysis)
        return risk_score

    def analyze_batch_data(self, code_data: np.ndarray) -> np.ndarray:
        """2차원 어레이 데이터 전체를 일괄 분석하여 리스크 점수를 반환합니다.
        Args:
            code_data: 코드 데이터 2차원 어레이
        Returns:
            (N) 형태의 1차원 어레이 - 리스크점수
        """
        n = len(code_data)
        start_idx = 20
        results = np.zeros(n)  # [리스크 점수]

        for i in range(start_idx, n):
            window_data = code_data[:i]  # 0부터 i까지의 데이터 사용
            risk_score = self.get_risk_score(window_data)
            results[i] = risk_score

        return results

    def _analyze_market_data(self, code_data: np.ndarray) -> dict:
        """시장 데이터를 분석합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            분석 결과 딕셔너리
        """
        current_prices    = code_data[:, self.idx_curr_price]   # 현재가
        volumes           = code_data[:, self.idx_volume]       # 거래대금
        rsi               = _calculate_rsi(current_prices)
        volatility        = _calculate_volatility(current_prices)
        trend             = self._analyze_trend(current_prices)
        momentum          = self._calculate_momentum(current_prices)
        volume_trend      = self._analyze_volume_trend(volumes)
        chegyeol_strength = self._analyze_chegyeol_strength(code_data)
        suyang_imbalance  = self._analyze_suyang_imbalance(code_data)
        price_position    = self._analyze_price_position(code_data)
        angle_analysis    = self._analyze_angle_trend(code_data)

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
        """추세를 분석합니다.
        Args:
            prices: 가격 배열
        Returns:
            추세 분석 결과 딕셔너리
        """
        short_period  = self.params['trend_short_period']
        medium_period = self.params['trend_medium_period']
        long_period   = self.params['trend_long_period']

        short_ma  = np.mean(prices[-short_period:]) if len(prices) >= short_period else prices[-1]
        medium_ma = np.mean(prices[-medium_period:]) if len(prices) >= medium_period else prices[-1]
        long_ma   = np.mean(prices[-long_period:]) if len(prices) >= long_period else prices[-1]
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

        prices_clean = prices[~np.isnan(prices) & ~np.isinf(prices)]

        if len(prices_clean) < 2 or np.all(prices_clean == prices_clean[0]):
            strength = 1e-10
        else:
            try:
                x = np.arange(len(prices_clean))
                mean_price = np.mean(prices_clean)
                if mean_price == 0:
                    strength = 1e-10
                else:
                    slope = np.polyfit(x, prices_clean, 1)[0] / mean_price * 100
                    strength = abs(slope)
            except (np.linalg.LinAlgError, ValueError, ZeroDivisionError):
                strength = 1e-10

        return {
            'direction': direction,
            'strength': strength
        }

    def _calculate_momentum(self, prices: np.ndarray) -> dict:
        """모멘텀을 계산합니다.
        Args:
            prices: 가격 배열
        Returns:
            모멘텀 결과 딕셔너리
        """
        strong_bullish_short  = self.params['momentum_strong_bullish_short']
        strong_bullish_medium = self.params['momentum_strong_bullish_medium']
        strong_bearish_short  = self.params['momentum_strong_bearish_short']
        strong_bearish_medium = self.params['momentum_strong_bearish_medium']

        short_momentum  = (prices[-1] - prices[-5]) / prices[-5] * 100 if len(prices) >= 5 else 0
        medium_momentum = (prices[-1] - prices[-10]) / prices[-10] * 100 if len(prices) >= 10 else 0

        if short_momentum > strong_bullish_short and medium_momentum > strong_bullish_medium:
            momentum_trend = 'bullish'
        elif short_momentum < strong_bearish_short and medium_momentum < strong_bearish_medium:
            momentum_trend = 'bearish'
        else:
            momentum_trend = 'neutral'

        return {
            'short_momentum': short_momentum,
            'medium_momentum': medium_momentum,
            'momentum_trend': momentum_trend
        }

    def _analyze_chegyeol_strength(self, code_data: np.ndarray) -> dict:
        """체결 강도를 분석합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            체결 강도 분석 결과 딕셔너리
        """
        curr_strength = code_data[-1, self.idx_chegyeol_strength]   # 체결강도
        avg_strength  = code_data[-1, self.idx_chegyeol_avg]        # 체결강도평균

        if curr_strength > avg_strength * self.params['strength_spike_multiplier']:
            trend = 'spike'
        elif curr_strength < avg_strength * self.params['strength_weak_multiplier']:
            trend = 'weak'
        else:
            trend = 'normal'

        return {
            'trend': trend,
            'deviation': abs(curr_strength - avg_strength) / avg_strength if avg_strength > 0 else 0
        }

    def _analyze_suyang_imbalance(self, code_data: np.ndarray) -> dict:
        """수급 불균형을 분석합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            수급 불균형 분석 결과 딕셔너리
        """
        current_buy  = code_data[-1, self.idx_buy_vol]   # 초당매수수량
        current_sell = code_data[-1, self.idx_sell_vol]  # 초당매도수량

        total = current_buy + current_sell
        if total > 0:
            buy_ratio  = current_buy / total
            sell_ratio = current_sell / total
            imbalance  = abs(buy_ratio - 0.5) * 2
        else:
            buy_ratio  = sell_ratio = 0.5
            imbalance  = 0

        if buy_ratio > self.params['imbalance_dominant_ratio']:
            direction = 'buy_dominant'
        elif sell_ratio > self.params['imbalance_dominant_ratio']:
            direction = 'sell_dominant'
        else:
            direction = 'balanced'

        return {
            'imbalance': imbalance,
            'direction': direction
        }

    def _analyze_price_position(self, code_data: np.ndarray) -> dict:
        """가격 위치를 분석합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            가격 위치 분석 결과 딕셔너리
        """
        current_price    = code_data[-1, self.idx_curr_price]
        current_high_low = code_data[-1, self.idx_high_low_ratio]   # 고저평균대비등락율
        max_price        = code_data[-1, self.idx_max_price]        # 최고현재가
        min_price        = code_data[-1, self.idx_min_price]        # 최저현재가

        if abs(current_high_low) > self.params['price_extreme_threshold']:
            position = 'extreme'
        elif abs(current_high_low) > self.params['price_far_threshold']:
            position = 'far'
        elif abs(current_high_low) > self.params['price_moderate_threshold']:
            position = 'moderate'
        else:
            position = 'normal'

        max_current = max_price
        min_current = min_price
        if max_current != min_current:
            price_range_position = (current_price - min_current) / (max_current - min_current)
        else:
            price_range_position = 0.5

        return {
            'position': position,
            'price_range_position': price_range_position
        }

    def _analyze_angle_trend(self, code_data: np.ndarray) -> dict:
        """각도 추세를 분석합니다.
        Args:
            code_data: 코드 데이터 배열
        Returns:
            각도 추세 분석 결과 딕셔너리
        """
        change_angle = code_data[-1, self.idx_change_angle]    # 등락율각도

        if change_angle > self.params['angle_strong_uptrend']:
            change_trend = 'strong_uptrend'
        elif change_angle > self.params['angle_uptrend']:
            change_trend = 'uptrend'
        elif change_angle < self.params['angle_strong_downtrend']:
            change_trend = 'strong_downtrend'
        elif change_angle < self.params['angle_downtrend']:
            change_trend = 'downtrend'
        else:
            change_trend = 'sideways'

        return {
            'change_trend': change_trend
        }

    def _analyze_volume_trend(self, volumes: np.ndarray) -> dict:
        """거래량 추세를 분석합니다.
        Args:
            volumes: 거래량 배열
        Returns:
            거래량 추세 분석 결과 딕셔너리
        """
        recent_avg    = np.mean(volumes[-5:])
        previous_avg  = np.mean(volumes[-10:-5]) if len(volumes) >= 10 else recent_avg
        volume_change = (recent_avg - previous_avg) / previous_avg * 100 if previous_avg > 0 else 0

        spike = recent_avg > previous_avg * self.params['volume_spike_multiplier']

        return {
            'spike': spike,
            'change_percent': volume_change
        }

    def _calculate_risk_score(self, analysis: dict) -> float:
        """리스크 점수를 계산합니다.
        Args:
            analysis: 분석 결과 딕셔너리
        Returns:
            리스크 점수
        """
        rsi               = analysis.get('rsi', 50)
        volatility        = analysis.get('volatility', 0)
        trend             = analysis.get('trend', {})
        momentum          = analysis.get('momentum', {})
        volume_trend      = analysis.get('volume_trend', {})
        chegyeol_strength = analysis.get('chegyeol_strength', {})
        suyang_imbalance  = analysis.get('suyang_imbalance', {})
        price_position    = analysis.get('price_position', {})
        angle_analysis    = analysis.get('angle_analysis', {})

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
        momentum_risk   = 0
        momentum_trend  = momentum.get('momentum_trend', 'neutral')
        short_momentum  = momentum.get('short_momentum', 0)
        medium_momentum = momentum.get('medium_momentum', 0)

        strong_bearish_short    = self.params['momentum_strong_bearish_short']
        strong_bearish_medium   = self.params['momentum_strong_bearish_medium']
        moderate_bearish_short  = self.params['momentum_moderate_bearish_short']
        moderate_bearish_medium = self.params['momentum_moderate_bearish_medium']

        if momentum_trend == 'bearish':
            momentum_risk = 10
        elif momentum_trend == 'neutral':
            if short_momentum < strong_bearish_short or medium_momentum < strong_bearish_medium:
                momentum_risk = 7
            elif short_momentum < moderate_bearish_short or medium_momentum < moderate_bearish_medium:
                momentum_risk = 4

        # 5. 거래량 리스크 (0-8점)
        volume_risk = 0
        volume_change = volume_trend.get('change_percent', 0)
        spike = volume_trend.get('spike', False)

        if spike:
            volume_risk = 8
        elif abs(volume_change) > self.params['volume_large_change']:
            volume_risk = 6
        elif volume_change < self.params['volume_decrease_threshold']:
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
