
from backtest.backengine_base import BackEngineBase
from utility.static_method.static import get_profit_stock, get_hogaunit_stock
# noinspection PyUnresolvedReferences
from utility.static_method.static import timedelta_sec


class BackEngineStock(BackEngineBase):
    """국내 주식 백테스트 엔진 클래스입니다.
    BackEngineBase를 상속받아 국내 주식 시장 특화 로직을 구현합니다.
    """
    def _get_hogaunit(self, 주문가격):
        """호가 단위를 반환합니다.
        Args:
            주문가격: 주문 가격
        Returns:
            호가 단위
        """
        return get_hogaunit_stock(주문가격)

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
        return int(betting / 현재가)

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다.
        Args:
            거래금액 (int): 거래 금액
            주문수량 (int): 주문 수량
        Returns:
            int: 주문 가격
        """
        return int(거래금액 / 주문수량 + 0.5)

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        """수익 정보를 계산합니다.
        Args:
            현재가 (int): 현재가
            매수가 (int): 매수가
            보유수량 (int): 보유 수량
        Returns:
            tuple: (시가총액, 평가금액, 수익금, 수익률)
        """
        시가총액 = int(self.arry_code[self.indexn, self.dict_findex['시가총액']])
        평가금액, 수익금, 수익률 = get_profit_stock(보유수량 * 매수가, 보유수량 * 현재가, self.is_etfn)
        return 시가총액, 평가금액, 수익금, 수익률
