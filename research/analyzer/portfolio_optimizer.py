"""
포트폴리오 최적화 분석기 모듈
Modern Portfolio Theory 기반 포트폴리오 최적화
속도 우선: SciPy minimize 함수 사용
"""

from scipy.optimize import minimize
from typing import Dict, Tuple, Optional
from utility.lazy_imports import get_np, get_pd


class PortfolioOptimizer:
    def __init__(self, risk_free_rate: float = 0.02):
        """
        포트폴리오 최적화기 초기화
        """
        self.risk_free_rate = risk_free_rate

    def calculate_portfolio_stats(self, weights: get_np().ndarray, returns: get_np().ndarray,
                                  cov_matrix: get_np().ndarray) -> Tuple[float, float, float]:
        """
        포트폴리오 통계 계산 (속도 우선: 벡터화)
        """
        portfolio_return = get_np().dot(weights, returns)
        portfolio_volatility = get_np().sqrt(get_np().dot(weights.T, get_np().dot(cov_matrix, weights)))
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
        return portfolio_return, portfolio_volatility, sharpe_ratio

    def optimize_portfolio(self, returns: get_np().ndarray, cov_matrix: get_np().ndarray,
                           target_return: Optional[float] = None,
                           method: str = 'sharpe') -> Dict:
        """
        포트폴리오 최적화 (속도 우선: SciPy minimize)
        """
        n_assets = len(returns)
        bounds = tuple((0, 1) for _ in range(n_assets))
        constraints = [{'type': 'eq', 'fun': lambda w: get_np().sum(w) - 1}]  # 가중치 합 1

        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: get_np().dot(w, returns) - target_return
            })

        if method == 'sharpe':
            # Sharpe Ratio 최대화 (효율적 투자선 상단)
            def objective(weights):
                port_return, port_vol, _ = self.calculate_portfolio_stats(weights, returns, cov_matrix)
                return -port_return / port_vol  # 음수로 최대화

        elif method == 'min_volatility':
            # 최소 변동성
            def objective(weights):
                _, port_vol, _ = self.calculate_portfolio_stats(weights, returns, cov_matrix)
                return port_vol

        elif method == 'max_return':
            # 최대 수익률
            def objective(weights):
                port_return, _, _ = self.calculate_portfolio_stats(weights, returns, cov_matrix)
                return -port_return  # 음수로 최대화

        else:
            raise ValueError("지원하지 않는 최적화 방법")

        # 초기 가중치: 동일 비중
        initial_weights = get_np().array([1/n_assets] * n_assets)

        # 최적화 실행 (속도 우선: SLSQP 방법)
        # noinspection PyTypeChecker
        result = minimize(objective, initial_weights,
                          method='SLSQP',
                          bounds=bounds,
                          constraints=constraints)

        if result.success:
            opt_weights = result.x
            opt_return, opt_volatility, opt_sharpe = self.calculate_portfolio_stats(
                opt_weights, returns, cov_matrix
            )

            return {
                'weights': opt_weights,
                'expected_return': opt_return,
                'volatility': opt_volatility,
                'sharpe_ratio': opt_sharpe,
                'success': True
            }
        else:
            return {'success': False, 'message': result.message}

    def efficient_frontier(self, returns: get_np().ndarray, cov_matrix: get_np().ndarray,
                           num_portfolios: int = 100) -> get_pd().DataFrame:
        """
        효율적 투자선 생성 (속도 우선: 벡터화)
        """
        n_assets = len(returns)
        results = []

        # 랜덤 포트폴리오 생성
        for _ in range(num_portfolios):
            weights = get_np().random.random(n_assets)
            weights /= get_np().sum(weights)  # 정규화

            port_return, port_volatility, sharpe_ratio = self.calculate_portfolio_stats(
                weights, returns, cov_matrix
            )

            results.append({
                'Return': port_return,
                'Volatility': port_volatility,
                'Sharpe': sharpe_ratio,
                'Weights': weights
            })

        return get_pd().DataFrame(results)

    def black_litterman_adjustment(self, prior_returns: get_np().ndarray,
                                   views: Dict[int, float],  # {자산인덱스: 예상수익률}
                                   tau: float = 0.05) -> get_np().ndarray:
        """
        Black-Litterman 모델로 사전 수익률 조정
        """
        n_assets = len(prior_returns)
        omega = get_np().diag(get_np().var(prior_returns)) * tau  # 불확실성 행렬

        # 뷰 행렬 생성
        P = get_np().zeros((len(views), n_assets))
        Q = get_np().zeros(len(views))

        for i, (asset_idx, view_return) in enumerate(views.items()):
            P[i, asset_idx] = 1
            Q[i] = view_return

        # Black-Litterman 공식
        pi = prior_returns
        tau_sigma = tau * get_np().cov(prior_returns.reshape(1, -1).repeat(n_assets, axis=0))

        try:
            adjusted_returns = pi + get_np().dot(
                get_np().dot(tau_sigma, P.T),
                get_np().linalg.inv(get_np().dot(get_np().dot(P, tau_sigma), P.T) + omega)
            ).dot(Q - get_np().dot(P, pi))
        except get_np().linalg.LinAlgError:
            adjusted_returns = pi  # 역행렬 계산 실패 시 원래 값 사용

        return adjusted_returns

    def risk_parity_weights(self, cov_matrix: get_np().ndarray) -> get_np().ndarray:
        """
        리스크 패리티 가중치 계산 (각 자산의 리스크 기여도 동일)
        """
        n_assets = len(cov_matrix)
        weights = get_np().ones(n_assets) / n_assets

        def risk_contribution(_weights):
            port_vol = get_np().sqrt(get_np().dot(_weights.T, get_np().dot(cov_matrix, _weights)))
            marginal_risk = get_np().dot(cov_matrix, _weights) / port_vol
            risk_contrib = _weights * marginal_risk
            return risk_contrib

        def objective(_weights):
            risk_contrib = risk_contribution(_weights)
            return get_np().var(risk_contrib)  # 리스크 기여도 분산 최소화

        constraints = [{'type': 'eq', 'fun': lambda w: get_np().sum(w) - 1}]
        bounds = tuple((0, 1) for _ in range(n_assets))

        # noinspection PyTypeChecker
        result = minimize(objective, weights,
                          method='SLSQP',
                          bounds=bounds,
                          constraints=constraints)

        return result.x if result.success else weights

    def analyze_portfolio_allocation(self, returns: get_np().ndarray, cov_matrix: get_np().ndarray) -> Dict:
        """
        다양한 포트폴리오 할당 전략 분석
        """
        results = {'sharpe_max': self.optimize_portfolio(returns, cov_matrix, method='sharpe'),
                   'min_volatility': self.optimize_portfolio(returns, cov_matrix, method='min_volatility'),
                   'max_return': self.optimize_portfolio(returns, cov_matrix, method='max_return')}

        # 리스크 패리티
        rp_weights = self.risk_parity_weights(cov_matrix)
        rp_return, rp_vol, rp_sharpe = self.calculate_portfolio_stats(rp_weights, returns, cov_matrix)
        results['risk_parity'] = {
            'weights': rp_weights,
            'expected_return': rp_return,
            'volatility': rp_vol,
            'sharpe_ratio': rp_sharpe,
            'success': True
        }

        # 동일 가중치 (벤치마크)
        equal_weights = get_np().ones(len(returns)) / len(returns)
        eq_return, eq_vol, eq_sharpe = self.calculate_portfolio_stats(equal_weights, returns, cov_matrix)
        results['equal_weight'] = {
            'weights': equal_weights,
            'expected_return': eq_return,
            'volatility': eq_vol,
            'sharpe_ratio': eq_sharpe,
            'success': True
        }

        return results

    def portfolio_report(self, allocation_results: Dict) -> get_pd().DataFrame:
        """
        포트폴리오 최적화 리포트 생성
        """
        report_data = {}
        for strategy, result in allocation_results.items():
            if result['success']:
                report_data[strategy] = {
                    'Expected_Return': result['expected_return'],
                    'Volatility': result['volatility'],
                    'Sharpe_Ratio': result['sharpe_ratio']
                }

        df = get_pd().DataFrame.from_dict(report_data, orient='index')
        df = df.round(4)
        return df


# 예제 사용
if __name__ == "__main__":
    # 샘플 데이터 생성 (속도 테스트용)
    get_np().random.seed(42)
    _n_assets = 5
    _n_periods = 1000

    # 랜덤 수익률 생성
    _returns = get_np().random.randn(_n_assets, _n_periods) * 0.02 + 0.001
    _cov_matrix = get_np().cov(_returns)

    _optimizer = PortfolioOptimizer()

    # Sharpe 최대화 최적화
    _sharpe_opt = _optimizer.optimize_portfolio(get_np().mean(_returns, axis=1), _cov_matrix, method='sharpe')
    print("Sharpe Max Weights:", _sharpe_opt['weights'])
    print("Sharpe Max Return:", _sharpe_opt['expected_return'])

    # 리스크 패리티
    _rp_weights = _optimizer.risk_parity_weights(_cov_matrix)
    print("Risk Parity Weights:", _rp_weights)

    # 전체 분석
    _analysis = _optimizer.analyze_portfolio_allocation(get_np().mean(_returns, axis=1), _cov_matrix)
    _report = _optimizer.portfolio_report(_analysis)
    print(_report)
