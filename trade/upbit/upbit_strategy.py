
from trade.base_strategy import BaseStrategy
from utility.static_method.static_numba import get_profit_coin
from utility.static_method.static_etcetera import get_hogaunit_coin
from utility.static_method.static_datetime import now_utc, dt_ymdhms


class UpbitStrategy(BaseStrategy):
    """업비트 전략 클래스입니다.
    BaseStrategy를 상속받아 업비트 시장 전략을 실행합니다."""
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _get_hogaunit(self, 주문가격):
        """호가 단위를 반환합니다."""
        return get_hogaunit_coin(주문가격)

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다."""
        return get_profit_coin(매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다."""
        return (now_utc() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        """보유 시간(분)을 계산합니다."""
        return int((now_utc() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다."""
        return round(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100, 8)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다."""
        return round(보유수량 / 보유비율 * oc_ratio, 8)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다."""
        return round(거래금액 / 주문수량, 4) if 주문수량 != 0 else 0
