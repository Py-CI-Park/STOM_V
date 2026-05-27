
from trade.base_strategy import BaseStrategy
from utility.static_method.static_datetime import now, dt_ymdhms
from utility.static_method.static_numba import get_profit_future_long, get_profit_future_short


class FutureStrategy(BaseStrategy):
    """선물 전략 클래스입니다.
    BaseStrategy를 상속받아 선물 시장 전략을 실행합니다."""
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _get_hogaunit(self, 종목코드):
        """호가 단위를 반환합니다."""
        return self.dict_info[종목코드]['호가단위']

    def _get_profit_long(self, 매입금액, 보유금액):
        """롱 수익을 계산합니다."""
        return get_profit_future_long(매입금액, 보유금액)

    def _get_profit_short(self, 매입금액, 보유금액):
        """숏 수익을 계산합니다."""
        return get_profit_future_short(매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다."""
        return (now() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        """보유 시간(분)을 계산합니다."""
        return int((now() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다."""
        return int(betting * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다."""
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다."""
        소숫점자리수 = self.dict_info[self.code]['소숫점자리수']
        return round(거래금액 / 주문수량, 소숫점자리수) if 주문수량 != 0 else 0
