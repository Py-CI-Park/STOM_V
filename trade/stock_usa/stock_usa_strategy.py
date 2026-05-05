
from trade.base_strategy import BaseStrategy
from utility.static_method.static import get_profit_stock_os, now_cme, dt_ymdhms


class StockUsaStrategy(BaseStrategy):
    """미국 주식 전략 클래스입니다.
    BaseStrategy를 상속받아 미국 주식 시장 전략을 실행합니다."""
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _get_hogaunit(self, 주문가격):
        """호가 단위를 반환합니다.
        Args:
            주문가격 (float): 주문 가격
        Returns:
            float: 호가 단위
        """
        return 0.01

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다.
        Args:
            매입금액 (float): 매입 금액
            보유금액 (float): 보유 금액
        Returns:
            tuple: (평가금액, 수익금, 수익률)
        """
        return get_profit_stock_os(매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다.
        Args:
            매수시간 (datetime): 매수 시간
        Returns:
            float: 보유 시간 (초)
        """
        return (now_cme() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        """보유 시간을 분 단위로 계산합니다.
        Args:
            매수시간 (datetime): 매수 시간
        Returns:
            int: 보유 시간 (분)
        """
        return int((now_cme() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다.
        Args:
            betting (float): 배팅 금액
            현재가 (float): 현재가
            매수가 (float): 매수가
            oc_ratio (float): 분할 비율

        Returns:
            int: 매수 수량
        """
        return int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다.
        Args:
            보유수량 (int): 보유 수량
            보유비율 (float): 보유 비율
            oc_ratio (float): 분할 비율

        Returns:
            int: 매도 수량
        """
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다.
        Args:
            거래금액: 거래 금액
            주문수량: 주문 수량
        Returns:
            주문 가격
        """
        return round(거래금액 / 주문수량, 2) if 주문수량 != 0 else 0
