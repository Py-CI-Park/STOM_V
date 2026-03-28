"""
리스크분석기 모듈
VaR, Sharpe Ratio, 최대낙폭 등 리스크 지표 계산
속도 우선: NumPy 벡터화 연산 사용
"""

from typing import Dict
from scipy.stats import norm
from utility.lazy_imports import get_np, get_pd


class RiskAnalyzer:
    def __init__(self):
        """
        리스크분석기 초기화
        """
        self.confidence_levels = [0.95, 0.99]  # 신뢰수준
        self.risk_free_rate = 0.02  # 무위험 수익률 (연간)

    def calculate_returns(self, prices: get_np().ndarray) -> get_np().ndarray:
        """
        가격 데이터로부터 수익률 계산 (속도 우선: 벡터화)
        """
        return get_np().diff(prices) / prices[:-1]

    def calculate_var_historical(self, returns: get_np().ndarray, confidence: float = 0.95):
        """
        역사적 VaR 계산 (속도 우선: get_np().percentile)
        """
        return -get_np().percentile(returns, (1 - confidence) * 100)

    def calculate_var_parametric(self, returns: get_np().ndarray, confidence: float = 0.95):
        """
        정규분포 가정 VaR 계산 (속도 우선: 벡터화 통계)
        """
        mean_return = get_np().mean(returns)
        std_return = get_np().std(returns, ddof=1)
        z_score = norm.ppf(1 - confidence)
        # noinspection PyTypeChecker
        return -(mean_return + z_score * std_return)

    def calculate_sharpe_ratio(self, returns: get_np().ndarray, annualize: bool = True):
        """
        Sharpe Ratio 계산 (속도 우선: 벡터화)
        """
        mean_return = get_np().mean(returns)
        std_return = get_np().std(returns, ddof=1)
        if std_return == 0:
            return 0
        # noinspection PyTypeChecker
        sharpe = (mean_return - self.risk_free_rate / 252) / std_return  # 일별 조정
        return sharpe * get_np().sqrt(252) if annualize else sharpe

    def calculate_max_drawdown(self, prices: get_np().ndarray):
        """
        최대낙폭 계산 (속도 우선: 누적 최대값 사용)
        """
        cumulative = get_np().maximum.accumulate(prices)
        drawdown = (prices - cumulative) / cumulative
        max_dd = get_np().min(drawdown)
        end_idx = get_np().argmin(drawdown)
        # noinspection PyTypeChecker
        start_idx = get_np().argmax(prices[:end_idx + 1])
        return -max_dd, start_idx, end_idx

    def calculate_volatility(self, returns: get_np().ndarray, annualize: bool = True) -> float:
        """
        변동성 계산 (속도 우선: get_np().std)
        """
        vol = get_np().std(returns, ddof=1)
        return vol * get_np().sqrt(252) if annualize else vol

    def calculate_sortino_ratio(self, returns: get_np().ndarray, annualize: bool = True) -> float:
        """
        Sortino Ratio 계산 (하방 변동성만 고려)
        """
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0:
            return get_np().inf
        downside_std = get_np().std(downside_returns, ddof=1)
        mean_return = get_np().mean(returns)
        # noinspection PyTypeChecker
        sortino = (mean_return - self.risk_free_rate / 252) / downside_std
        return sortino * get_np().sqrt(252) if annualize else sortino

    def analyze_portfolio_risk(self, prices_dict: Dict[str, get_np().ndarray]) -> Dict:
        """
        포트폴리오 리스크 분석 (속도 우선: 행렬 연산)
        """
        codes = list(prices_dict.keys())
        returns_matrix = get_np().array([self.calculate_returns(prices) for prices in prices_dict.values()])

        # 공분산 행렬 (속도 우선: get_np().cov)
        cov_matrix = get_np().cov(returns_matrix)

        # 상관 행렬
        corr_matrix = get_np().corrcoef(returns_matrix)

        # 포트폴리오 리스크 지표 계산
        results = {}
        for i, code in enumerate(codes):
            returns = returns_matrix[i]
            results[code] = {
                'VaR_95_Historical': self.calculate_var_historical(returns, 0.95),
                'VaR_99_Historical': self.calculate_var_historical(returns, 0.99),
                'VaR_95_Parametric': self.calculate_var_parametric(returns, 0.95),
                'Sharpe_Ratio': self.calculate_sharpe_ratio(returns),
                'Sortino_Ratio': self.calculate_sortino_ratio(returns),
                'Max_Drawdown': self.calculate_max_drawdown(prices_dict[code])[0],
                'Volatility': self.calculate_volatility(returns),
                'Mean_Return': get_np().mean(returns),
                'Skewness': self.calculate_skewness(returns),
                'Kurtosis': self.calculate_kurtosis(returns)
            }

        results['Portfolio_Cov_Matrix'] = cov_matrix
        results['Portfolio_Corr_Matrix'] = corr_matrix

        return results

    def calculate_skewness(self, returns: get_np().ndarray):
        """
        왜도 계산 (속도 우선: np 함수)
        """
        return get_np().mean(((returns - get_np().mean(returns)) / get_np().std(returns, ddof=1)) ** 3)

    def calculate_kurtosis(self, returns: get_np().ndarray) -> float:
        """
        첨도 계산 (속도 우선: np 함수)
        """
        # noinspection PyTypeChecker
        return get_np().mean(((returns - get_np().mean(returns)) / get_np().std(returns, ddof=1)) ** 4) - 3

    def risk_report(self, analysis_results: Dict) -> get_pd().DataFrame:
        """
        리스크 분석 리포트 생성
        """
        individual_results = {k: v for k, v in analysis_results.items() if isinstance(v, dict)}
        df = get_pd().DataFrame.from_dict(individual_results, orient='index')
        df = df.round(4)
        return df


# 예제 사용
if __name__ == "__main__":
    # 샘플 데이터 생성 (속도 테스트용)
    get_np().random.seed(42)
    sample_prices = get_np().random.randn(1000).cumsum() + 100  # 랜덤 가격 데이터

    analyzer = RiskAnalyzer()
    _returns = analyzer.calculate_returns(sample_prices)

    print("VaR (95%):", analyzer.calculate_var_historical(_returns, 0.95))
    print("Sharpe Ratio:", analyzer.calculate_sharpe_ratio(_returns))
    print("Max Drawdown:", analyzer.calculate_max_drawdown(sample_prices)[0])

    # 포트폴리오 분석 예제
    _prices_dict = {
        'Stock1': sample_prices,
        'Stock2': sample_prices * 1.1 + get_np().random.randn(1000) * 0.5
    }
    portfolio_risk = analyzer.analyze_portfolio_risk(_prices_dict)
    report = analyzer.risk_report(portfolio_risk)
    print(report.head())
