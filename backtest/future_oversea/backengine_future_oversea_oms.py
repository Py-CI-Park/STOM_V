
from backtest.future.backengine_future_oms import BackEngineFutureOms
from utility.static_method.static import get_profit_future_os_long, get_profit_future_os_short


class BackEngineFutureOverseaOms(BackEngineFutureOms):
    """해외 선물 OMS 백테스트 엔진 클래스입니다.
    BackEngineFutureOms를 상속받아 해외 선물 시장 특화 OMS 로직을 구현합니다.
    """
    def _get_hogaunit(self, 종목코드):
        """호가 단위를 반환합니다.
        Args:
            종목코드: 종목 코드
        Returns:
            호가 단위
        """
        return self.dict_info[종목코드]['호가단위']

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다.
        Args:
            betting: 배팅 금액
            현재가: 현재가
            매수가: 매수가
            oc_ratio: 분할 비율
        Returns:
            매수 수량
        """
        return int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다.
        Args:
            보유수량: 보유 수량
            보유비율: 보유 비율
            oc_ratio: 분할 비율
        Returns:
            매도 수량
        """
        return int(보유수량 / 보유비율 * oc_ratio)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다.
        Args:
            거래금액 (float): 거래 금액
            주문수량 (int): 주문 수량
        Returns:
            float: 주문 가격
        """
        return round(거래금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        """수익 정보를 계산합니다.
        Args:
            현재가 (float): 현재가
            매수가 (float): 매수가
            보유수량 (int): 보유 수량
        Returns:
            tuple: (포지션, 평가금액, 수익금, 수익률)
        """
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 보유수량
        보유금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[self.code]['틱가치'] * 보유수량
        mini = self.code.startswith('M') or self.code.startswith('SIL')
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = get_profit_future_os_long(mini, 매입금액, 보유금액)
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = get_profit_future_os_short(mini, 매입금액, 보유금액)
        return 포지션, 평가금액, 수익금, 수익률
