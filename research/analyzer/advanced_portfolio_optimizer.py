"""
고급 포트폴리오 최적화 및 리스크 관리 시스템
다양한 자산군의 균형 잡힌 포트폴리오 구성 및 동적 리밸런싱
"""

import warnings
import numpy as np
import pandas as pd
from typing import Dict, List
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
warnings.filterwarnings('ignore')


class AdvancedPortfolioOptimizer:
    """
    고급 포트폴리오 최적화 및 리스크 관리 시스템
    
    기능:
    - 다양한 자산군 포트폴리오 최적화
    - 동적 리밸런싱 전략
    - 리스크 패리티 및 VaR 계산
    - 샤프 비율 최적화
    - 상관관계 기반 자산 선택
    """

    def __init__(self, risk_free_rate: float = 0.02, max_weight: float = 0.3):
        """
        초기화
        
        Args:
            risk_free_rate: 무위험 이자율
            max_weight: 개별 자산 최대 비중
        """
        self.risk_free_rate = risk_free_rate
        self.max_weight = max_weight
        self.portfolio_weights = {}
        self.asset_returns = {}
        self.asset_volatilities = {}

    def calculate_portfolio_metrics(self, returns: pd.DataFrame, weights: np.ndarray) -> Dict:
        """
        포트폴리오 메트릭 계산
        
        Args:
            returns: 자산 수익률 데이터
            weights: 포트폴리오 가중치
            
        Returns:
            포트폴리오 메트릭 딕셔너리
        """
        # 포트폴리오 수익률
        portfolio_return = np.sum(returns.mean() * weights) * 252

        # 포트폴리오 변동성
        covariance_matrix = returns.cov() * 252
        portfolio_variance = np.dot(weights.T, np.dot(covariance_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)

        # 샤프 비율
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility

        # 최대 낙폭 (MDD)
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min().iloc[0] if hasattr(drawdown.min(), 'iloc') else drawdown.min()

        # VaR (Value at Risk)
        portfolio_returns = np.dot(returns, weights)
        var_95 = np.percentile(portfolio_returns, 5)

        return {
            'return': portfolio_return,
            'volatility': portfolio_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'var_95': var_95,
            'weights': weights
        }

    def optimize_portfolio(self, returns: pd.DataFrame, method: str = 'sharpe') -> Dict:
        """
        포트폴리오 최적화
        
        Args:
            returns: 자산 수익률 데이터
            method: 최적화 방법 ('sharpe', 'min_variance', 'max_return')
            
        Returns:
            최적화된 포트폴리오 메트릭
        """
        num_assets = len(returns.columns)

        # 제약 조건
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # 가중치 합 = 1
        ]

        # 가중치 범위
        bounds = tuple((0, self.max_weight) for _ in range(num_assets))

        # 초기 가중치
        initial_weights = np.array([1/num_assets] * num_assets)

        # 목적 함수
        if method == 'sharpe':
            def objective(x):
                return -self.calculate_portfolio_metrics(returns, x)['sharpe_ratio']
        elif method == 'min_variance':
            def objective(x):
                return self.calculate_portfolio_metrics(returns, x)['volatility']
        else:
            def objective(x):
                return -self.calculate_portfolio_metrics(returns, x)['return']

        # 최적화
        # noinspection PyTypeChecker
        result = minimize(
            objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'disp': False}
        )

        if result.success:
            optimal_weights = result.x
            return self.calculate_portfolio_metrics(returns, optimal_weights)
        else:
            raise ValueError("포트폴리오 최적화 실패")

    def calculate_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """
        상관관계 행렬 계산
        
        Args:
            returns: 자산 수익률 데이터
            
        Returns:
            상관관계 행렬
        """
        return returns.corr()

    def select_uncorrelated_assets(self, returns: pd.DataFrame, threshold: float = 0.7) -> List[str]:
        """
        상관관계가 낮은 자산 선택
        
        Args:
            returns: 자산 수익률 데이터
            threshold: 상관관계 임계값
            
        Returns:
            선택된 자산 리스트
        """
        correlation_matrix = self.calculate_correlation_matrix(returns)
        selected_assets = []

        for asset in correlation_matrix.columns:
            # 다른 자산들과의 평균 상관관계 계산
            correlations = correlation_matrix[asset].drop(asset)
            avg_correlation = correlations.abs().mean()

            if avg_correlation < threshold:
                selected_assets.append(asset)

        return selected_assets

    def calculate_risk_parity_weights(self, returns: pd.DataFrame) -> np.ndarray:
        """
        리스크 패리티 가중치 계산
        
        Args:
            returns: 자산 수익률 데이터
            
        Returns:
            리스크 패리티 가중치
        """
        # 공분산 행렬 계산 (Ledoit-Wolf 축소)
        cov_estimator = LedoitWolf()
        # noinspection PyUnresolvedReferences
        cov_matrix = cov_estimator.fit(returns).covariance_

        # 리스크 패리티 가중치 계산
        inv_sqrt_diag = np.diag(1 / np.sqrt(np.diag(cov_matrix)))
        risk_parity_weights = inv_sqrt_diag @ np.ones(len(returns.columns))
        risk_parity_weights = risk_parity_weights / np.sum(risk_parity_weights)

        return risk_parity_weights

    def dynamic_rebalancing(self, current_weights: Dict[str, float],
                            target_weights: Dict[str, float],
                            threshold: float = 0.05) -> Dict[str, float]:
        """
        동적 리밸런싱
        
        Args:
            current_weights: 현재 포트폴리오 가중치
            target_weights: 목표 포트폴리오 가중치
            threshold: 리밸런싱 임계값
            
        Returns:
            리밸런싱 후 가중치
        """
        rebalanced_weights = {}

        for asset in target_weights:
            current_weight = current_weights.get(asset, 0)
            target_weight = target_weights[asset]

            # 리밸런싱 필요 여부 확인
            if abs(current_weight - target_weight) > threshold:
                rebalanced_weights[asset] = target_weight
            else:
                rebalanced_weights[asset] = current_weight

        return rebalanced_weights

    def calculate_portfolio_attribution(self, returns: pd.DataFrame, weights: np.ndarray) -> Dict[str, float]:
        """
        포트폴리오 기여도 분석
        
        Args:
            returns: 자산 수익률 데이터
            weights: 포트폴리오 가중치
            
        Returns:
            자산별 기여도
        """
        portfolio_return = np.sum(returns.mean() * weights) * 252
        attribution = {}

        for i, asset in enumerate(returns.columns):
            asset_return = returns[asset].mean() * 252
            asset_contribution = asset_return * weights[i]
            attribution[asset] = asset_contribution / portfolio_return

        return attribution


class RiskManager:
    """
    리스크 관리 시스템
    """

    def __init__(self, max_portfolio_var: float = 0.02, max_drawdown: float = 0.15):
        """
        초기화
        
        Args:
            max_portfolio_var: 최대 포트폴리오 VaR
            max_drawdown: 최대 허용 낙폭
        """
        self.max_portfolio_var = max_portfolio_var
        self.max_drawdown = max_drawdown

    def calculate_position_size(self, portfolio_value: float,
                                asset_volatility: float,
                                correlation_with_portfolio: float) -> float:
        """
        리스크 기반 포지션 크기 계산
        
        Args:
            portfolio_value: 포트폴리오 가치
            asset_volatility: 자산 변동성
            correlation_with_portfolio: 포트폴리오와의 상관관계
            
        Returns:
            적정 포지션 크기
        """
        # Kelly 공식 기반 포지션 크기
        kelly_fraction = 0.25  # 보수적인 Kelly 비율

        # 리스크 조정
        risk_adjusted_size = (kelly_fraction * portfolio_value *
                              (1 - correlation_with_portfolio) / asset_volatility)

        return min(risk_adjusted_size, portfolio_value * 0.2)  # 최대 20% 제한

    def check_risk_limits(self, portfolio_metrics: Dict) -> bool:
        """
        리스크 한계 확인
        
        Args:
            portfolio_metrics: 포트폴리오 메트릭
            
        Returns:
            리스크 한계 준수 여부
        """
        # VaR 확인
        if abs(portfolio_metrics['var_95']) > self.max_portfolio_var:
            return False

        # MDD 확인
        if abs(portfolio_metrics['max_drawdown']) > self.max_drawdown:
            return False

        return True


def test_portfolio_optimizer():
    """
    포트폴리오 최적화 테스트
    """
    # 샘플 데이터 생성
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=252, freq='D')

    # 5개 자산의 수익률 데이터 생성
    assets = ['Stock_A', 'Stock_B', 'Bond_A', 'Commodity_A', 'Crypto_A']
    returns_data = {}

    for asset in assets:
        # 각 자산별 특성 반영
        if 'Stock' in asset:
            volatility = 0.2
            mean_return = 0.08
        elif 'Bond' in asset:
            volatility = 0.1
            mean_return = 0.04
        elif 'Commodity' in asset:
            volatility = 0.25
            mean_return = 0.06
        else:  # Crypto
            volatility = 0.4
            mean_return = 0.15

        daily_returns = np.random.normal(mean_return/252, volatility/np.sqrt(252), 252)
        returns_data[asset] = daily_returns

    returns_df = pd.DataFrame(returns_data, index=dates)

    # 포트폴리오 최적화
    optimizer = AdvancedPortfolioOptimizer()

    # 상관관계가 낮은 자산 선택
    selected_assets = optimizer.select_uncorrelated_assets(returns_df)
    print(f"선택된 자산: {selected_assets}")

    if selected_assets:
        selected_returns = returns_df[selected_assets]

        # 샤프 비율 최적화
        optimal_portfolio = optimizer.optimize_portfolio(selected_returns, method='sharpe')

        print("최적 포트폴리오:")
        print(f"연간 수익률: {optimal_portfolio['return']:.2%}")
        print(f"연간 변동성: {optimal_portfolio['volatility']:.2%}")
        print(f"샤프 비율: {optimal_portfolio['sharpe_ratio']:.2f}")
        print(f"최대 낙폭: {optimal_portfolio['max_drawdown']:.2%}")
        print(f"VaR(95%): {optimal_portfolio['var_95']:.2%}")

        # 가중치 출력
        weights_dict = dict(zip(selected_assets, optimal_portfolio['weights']))
        print("\n최적 가중치:")
        for asset, weight in weights_dict.items():
            print(f"{asset}: {weight:.2%}")

        # 포트폴리오 기여도 분석
        attribution = optimizer.calculate_portfolio_attribution(selected_returns, optimal_portfolio['weights'])
        print("\n포트폴리오 기여도:")
        for asset, contribution in attribution.items():
            print(f"{asset}: {contribution:.2%}")

        # 리스크 패리티 가중치 계산
        rp_weights = optimizer.calculate_risk_parity_weights(selected_returns)
        rp_weights_dict = dict(zip(selected_assets, rp_weights))
        print("\n리스크 패리티 가중치:")
        for asset, weight in rp_weights_dict.items():
            print(f"{asset}: {weight:.2%}")

        # 리스크 관리 테스트
        risk_manager = RiskManager()
        portfolio_metrics = optimal_portfolio if 'optimal_portfolio' in locals() else {}

        if portfolio_metrics:
            risk_ok = risk_manager.check_risk_limits(portfolio_metrics)
            print(f"\n리스크 한계 준수: {'예' if risk_ok else '아니오'}")


if __name__ == "__main__":
    test_portfolio_optimizer()
