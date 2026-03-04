"""
실시간 변동성 분석 및 예측 시스템
GARCH 모델 기반 변동성 예측 및 트레이딩 신호 생성
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from arch import arch_model
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class RealTimeVolatilityAnalyzer:
    """
    실시간 변동성 분석 및 예측 시스템
    
    기능:
    - GARCH 모델 기반 변동성 예측
    - 변동성 클러스터링
    - 변동성 레징 시스템
    - 변동성 기반 리스크 관리
    """
    
    def __init__(self, window_size: int = 100, garch_p: int = 1, garch_q: int = 1):
        """
        초기화
        
        Args:
            window_size: 데이터 윈도우 크기
            garch_p: GARCH(p,q) 모델의 p 파라미터
            garch_q: GARCH(p,q) 모델의 q 파라미터
        """
        self.window_size = window_size
        self.garch_p = garch_p
        self.garch_q = garch_q
        self.volatility_history = []
        self.price_history = []
        self.volatility_forecasts = []
        self.current_volatility = 0.0
        self.volatility_regime = 'normal'
        
    def calculate_historical_volatility(self, prices: np.ndarray, 
                                 method: str = 'std') -> float:
        """
        역사적 변동성 계산
        
        Args:
            prices: 가격 데이터
            method: 계산 방법 ('std', 'parkinson', 'garman_klass')
            
        Returns:
            변동성 값
        """
        returns = np.diff(np.log(prices))
        
        if method == 'std':
            return np.std(returns) * np.sqrt(252)
        elif method == 'parkinson':
            # Parkinson 변동성 추정기
            log_hl = np.log(prices[1:] / prices[:-1])
            return np.sqrt(0.361 * np.mean(log_hl**2)) * np.sqrt(252)
        elif method == 'garman_klass':
            # Garman-Klass 변동성 추정기
            log_hl = np.log(prices[1:] / prices[:-1])
            return np.sqrt(0.5 * np.mean(log_hl**2) - 0.39 * np.mean(log_hl)) * np.sqrt(252)
        else:
            return np.std(returns) * np.sqrt(252)
    
    def fit_garch_model(self, returns: np.ndarray) -> Tuple[float, float, float]:
        """
        GARCH 모델 적합
        
        Args:
            returns: 수익률 데이터
            
        Returns:
            (omega, alpha, beta) GARCH 파라미터
        """
        try:
            model = arch_model(returns, vol='Garch', p=self.garch_p, q=self.garch_q)
            result = model.fit(disp='off')
            
            omega = result.params['omega']
            alpha = result.params['alpha[1]']
            beta = result.params['beta[1]']
            
            return omega, alpha, beta
        except:
            # 기본값 반환
            return 0.0001, 0.1, 0.85
    
    def forecast_volatility(self, returns: np.ndarray, 
                        horizon: int = 5) -> List[float]:
        """
        변동성 예측
        
        Args:
            returns: 수익률 데이터
            horizon: 예측 기간
            
        Returns:
            예측된 변동성 리스트
        """
        omega, alpha, beta = self.fit_garch_model(returns)
        
        # 현재 변동성
        current_var = np.var(returns[-self.window_size:])
        
        # 미래 변동성 예측
        forecasts = []
        var_t = current_var
        
        for _ in range(horizon):
            var_t_plus_1 = omega + alpha * returns[-1]**2 + beta * var_t
            forecasts.append(np.sqrt(var_t_plus_1) * np.sqrt(252))
            var_t = var_t_plus_1
        
        return forecasts
    
    def classify_volatility_regime(self, volatility: float, 
                              history: List[float]) -> str:
        """
        변동성 레징 분류
        
        Args:
            volatility: 현재 변동성
            history: 변동성 히스토리
            
        Returns:
            변동성 레징 ('low', 'normal', 'high', 'extreme')
        """
        if len(history) < 10:
            return 'normal'
        
        # 변동성 퍼센타일 계산
        percentiles = np.percentile(history, [25, 75, 90])
        
        if volatility < percentiles[0]:
            return 'low'
        elif volatility < percentiles[1]:
            return 'normal'
        elif volatility < percentiles[2]:
            return 'high'
        else:
            return 'extreme'
    
    def calculate_volatility_target_position(self, current_price: float, 
                                      target_volatility: float,
                                      current_volatility: float) -> float:
        """
        변동성 타겟 포지션 크기 계산
        
        Args:
            current_price: 현재 가격
            target_volatility: 목표 변동성
            current_volatility: 현재 변동성
            
        Returns:
            포지션 크기 조정 비율
        """
        if current_volatility == 0:
            return 1.0
        
        # 변동성 타겟 비율
        vol_ratio = target_volatility / current_volatility
        
        # 포지션 크기 조정 (최대 2배까지 허용)
        position_adjustment = min(max(vol_ratio, 0.5), 2.0)
        
        return position_adjustment
    
    def detect_volatility_spike(self, current_vol: float, 
                            historical_vols: List[float],
                            threshold: float = 2.0) -> bool:
        """
        변동성 스파이크 감지
        
        Args:
            current_vol: 현재 변동성
            historical_vols: 역사적 변동성
            threshold: 스파이크 임계값 (배수)
            
        Returns:
            스파이크 발생 여부
        """
        if len(historical_vols) < 20:
            return False
        
        # 최근 20일 평균 변동성
        avg_vol = np.mean(historical_vols[-20:])
        
        return current_vol > avg_vol * threshold
    
    def update_volatility(self, new_price: float) -> Dict:
        """
        새로운 가격으로 변동성 업데이트
        
        Args:
            new_price: 새로운 가격
            
        Returns:
            업데이트된 변동성 정보
        """
        self.price_history.append(new_price)
        
        # 윈도우 크기 유지
        if len(self.price_history) > self.window_size:
            self.price_history = self.price_history[-self.window_size:]
        
        if len(self.price_history) < 2:
            return {'current_volatility': 0, 'regime': 'normal'}
        
        # 현재 변동성 계산
        current_vol = self.calculate_historical_volatility(
            np.array(self.price_history), method='std'
        )
        
        self.current_volatility = current_vol
        self.volatility_history.append(current_vol)
        
        # 변동성 레징 업데이트
        self.volatility_regime = self.classify_volatility_regime(
            current_vol, self.volatility_history
        )
        
        # 변동성 예측
        if len(self.price_history) >= 50:
            returns = np.diff(np.log(self.price_history))
            forecasts = self.forecast_volatility(returns, horizon=5)
            self.volatility_forecasts = forecasts
        
        return {
            'current_volatility': current_vol,
            'regime': self.volatility_regime,
            'forecasts': self.volatility_forecasts,
            'spike_detected': self.detect_volatility_spike(
                current_vol, self.volatility_history
            )
        }
    
    def generate_trading_signals(self, volatility_info: Dict) -> Dict:
        """
        변동성 기반 트레이딩 신호 생성
        
        Args:
            volatility_info: 변동성 정보
            
        Returns:
            트레이딩 신호
        """
        regime = volatility_info.get('regime', 'normal')
        current_vol = volatility_info.get('current_volatility', 0)
        spike_detected = volatility_info.get('spike_detected', False)
        
        signals = {
            'reduce_position': False,
            'increase_position': False,
            'hedge_position': False,
            'volatility_breakout': False
        }
        
        # 변동성 레징에 따른 신호
        if regime == 'extreme':
            signals['reduce_position'] = True
            signals['hedge_position'] = True
        elif regime == 'high':
            signals['reduce_position'] = True
        elif regime == 'low':
            signals['increase_position'] = True
        
        # 변동성 스파이크 신호
        if spike_detected:
            signals['volatility_breakout'] = True
        
        return signals


class VolatilityRiskManager:
    """
    변동성 기반 리스크 관리 시스템
    """
    
    def __init__(self, max_volatility: float = 0.3, 
                 var_confidence: float = 0.05):
        """
        초기화
        
        Args:
            max_volatility: 최대 허용 변동성
            var_confidence: VaR 신뢰수준
        """
        self.max_volatility = max_volatility
        self.var_confidence = var_confidence
        
    def calculate_var(self, returns: np.ndarray, 
                    portfolio_value: float) -> float:
        """
        Value at Risk 계산
        
        Args:
            returns: 포트폴리오 수익률
            portfolio_value: 포트폴리오 가치
            
        Returns:
            VaR 값
        """
        var_percentile = (1 - self.var_confidence) * 100
        return np.percentile(returns, var_percentile) * portfolio_value
    
    def calculate_position_limits(self, current_volatility: float,
                            portfolio_value: float) -> Dict:
        """
        변동성 기반 포지션 한도 계산
        
        Args:
            current_volatility: 현재 변동성
            portfolio_value: 포트폴리오 가치
            
        Returns:
            포지션 한도 정보
        """
        # 변동성이 0인 경우 기본값 사용
        if current_volatility == 0:
            current_volatility = 0.01  # 최소 변동성
        
        # 변동성 조정 포지션 크기
        vol_adjusted_size = portfolio_value * (self.max_volatility / current_volatility)
        
        # 최대/최소 포지션 크기
        max_position = portfolio_value * 2.0
        min_position = portfolio_value * 0.1
        
        return {
            'recommended_size': min(max(vol_adjusted_size, min_position), max_position),
            'max_size': max_position,
            'min_size': min_position,
            'volatility_ratio': current_volatility / self.max_volatility
        }


def test_volatility_analyzer():
    """
    변동성 분석기 테스트
    """
    # 샘플 데이터 생성
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    
    # 변동성이 변하는 가격 데이터 생성
    prices = []
    base_price = 100
    
    for i in range(200):
        # 변동성 레징 시뮬레이션
        if i < 50:
            vol = 0.01  # 낮은 변동성
        elif i < 100:
            vol = 0.02  # 정상 변동성
        elif i < 150:
            vol = 0.04  # 높은 변동성
        else:
            vol = 0.08  # 극단적 변동성
        
        daily_return = np.random.normal(0, vol)
        base_price *= (1 + daily_return)
        prices.append(base_price)
    
    prices = np.array(prices)
    
    # 변동성 분석기 초기화
    analyzer = RealTimeVolatilityAnalyzer(window_size=50)
    risk_manager = VolatilityRiskManager()
    
    print("실시간 변동성 분석 테스트")
    print("=" * 50)
    
    # 실시간 분석 시뮬레이션
    for i, price in enumerate(prices[50:], 50):
        vol_info = analyzer.update_volatility(price)
        signals = analyzer.generate_trading_signals(vol_info)
        
        # 리스크 관리
        position_limits = risk_manager.calculate_position_limits(
            vol_info['current_volatility'], 1000000
        )
        
        if i % 20 == 0:  # 20일 간격으로 출력
            print(f"\n일자: {dates[i].strftime('%Y-%m-%d')}")
            print(f"가격: {price:.2f}")
            print(f"현재 변동성: {vol_info['current_volatility']:.2%}")
            print(f"변동성 레징: {vol_info['regime']}")
            print(f"변동성 스파이크: {vol_info['spike_detected']}")
            
            if vol_info['forecasts']:
                print(f"5일 예측 변동성: {vol_info['forecasts'][0]:.2%}")
            
            print("트레이딩 신호:")
            for signal, active in signals.items():
                if active:
                    print(f"  - {signal}: 활성화")
            
            print(f"권장 포지션 크기: {position_limits['recommended_size']:,.0f}")
            print(f"변동성 비율: {position_limits['volatility_ratio']:.2f}")
    
    print("\n" + "=" * 50)
    print("최종 변동성 통계:")
    print(f"평균 변동성: {np.mean(analyzer.volatility_history):.2%}")
    print(f"최고 변동성: {np.max(analyzer.volatility_history):.2%}")
    print(f"최저 변동성: {np.min(analyzer.volatility_history):.2%}")


if __name__ == "__main__":
    test_volatility_analyzer()
