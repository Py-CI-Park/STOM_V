
from backtest.future.backengine_future_oms import BackEngineFutureOms
from utility.static_method.static import get_profit_coin_future_long, get_profit_coin_future_short


class BackEngineBinanceOms(BackEngineFutureOms):
    """바이낸스 OMS 백테스트 엔진 클래스입니다.
    BackEngineFutureOms를 상속받아 바이낸스 시장 특화 OMS 로직을 구현합니다.
    """

    def _get_hogaunit(self, 호가빼기데이터):
        """호가 단위를 반환합니다.
        Args:
            호가빼기데이터: 호가 빼기 데이터
        Returns:
            호가 단위
        """
        return min(x for x in 호가빼기데이터 if x > 0)

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
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100, 소숫점자리수)

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다.
        Args:
            보유수량: 보유 수량
            보유비율: 보유 비율
            oc_ratio: 분할 비율
        Returns:
            매도 수량
        """
        소숫점자리수 = self.dict_info[self.code]['수량소숫점자리수']
        return round(보유수량 / 보유비율 * oc_ratio, 소숫점자리수)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다.
        Args:
            거래금액 (float): 거래 금액
            주문수량 (float): 주문 수량
        Returns:
            float: 주문 가격
        """
        소숫점자리수 = self.dict_info[self.code]['가격소숫점자리수']
        return round(거래금액 / 주문수량, 소숫점자리수) if 주문수량 != 0 else 0.0

    def _get_last_sell_price(self, 매도금액, 보유수량, 미체결수량):
        """최종 매도 가격을 계산합니다.
        Args:
            매도금액 (float): 매도 금액
            보유수량 (float): 보유 수량
            미체결수량 (float): 미체결 수량
        Returns:
            float: 최종 매도 가격
        """
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, 4)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), 4)
        return 매도가

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        """수익 정보를 계산합니다.
        Args:
            현재가 (float): 현재가
            매수가 (float): 매수가
            보유수량 (float): 보유 수량
        Returns:
            tuple: (포지션, 평가금액, 수익금, 수익률)
        """
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = get_profit_coin_future_long(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['매수주문유형'],
                '시장가' in self.dict_set['매도주문유형'])
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = get_profit_coin_future_short(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['매수주문유형'],
                '시장가' in self.dict_set['매도주문유형'])
        return 포지션, 평가금액, 수익금, 수익률
