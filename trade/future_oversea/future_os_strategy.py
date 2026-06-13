
from trade.base_strategy import BaseStrategy
from utility.static_method.static_datetime import now_cme, dt_ymdhms
from utility.static_method.static_numba import get_profit_future_os_long, get_profit_future_os_short


class FutureOsStrategy(BaseStrategy):
    """해외 선물 전략 클래스입니다.
    BaseStrategy를 상속받아 해외 선물 시장 전략을 실행합니다."""
    def __init__(self, gubun, qlist, dict_set, market_info):
        super().__init__(gubun, qlist, dict_set, market_info)

    def _get_hogaunit(self, 종목코드):
        """호가 단위를 반환합니다."""
        return self.dict_info[종목코드]['호가단위']

    def _get_profit_long(self, 매입금액, 보유금액, 종목코드=None):
        """롱 수익을 계산합니다."""
        mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
        return get_profit_future_os_long(mini, 매입금액, 보유금액)

    def _get_profit_short(self, 매입금액, 보유금액, 종목코드=None):
        """숏 수익을 계산합니다."""
        mini = 종목코드.startswith('M') or 종목코드.startswith('SIL')
        return get_profit_future_os_short(mini, 매입금액, 보유금액)

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다."""
        return (now_cme() - dt_ymdhms(매수시간)).total_seconds()

    def _get_hold_time_min(self, 매수시간):
        """보유 시간(분)을 계산합니다."""
        return int((now_cme() - dt_ymdhms(매수시간)).total_seconds() / 60)

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다."""
        return int(betting * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다."""
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_buy_price(self, 종목코드, 주문구분, 주문가격):
        """매수 주문 가격을 반환합니다."""
        매수지정가호가번호 = self.dict_set['매수지정가호가번호']
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매수지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'BUY_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

    def _get_order_sell_price(self, 종목코드, 주문구분, 주문가격):
        """매도 주문 가격을 반환합니다."""
        매도지정가호가번호 = self.dict_set['매도지정가호가번호']
        소숫점자리수 = self.dict_info[종목코드]['소숫점자리수']
        호가차이 = self.dict_info[종목코드]['호가단위'] * 매도지정가호가번호
        return round(주문가격 + 호가차이, 소숫점자리수) if 주문구분 == 'SELL_LONG' else round(주문가격 - 호가차이, 소숫점자리수)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다."""
        소숫점자리수 = self.dict_info[self.code]['소숫점자리수']
        return round(거래금액 / 주문수량, 소숫점자리수)
