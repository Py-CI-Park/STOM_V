
from backtest.backengine_future_min2 import BackEngineFutureMin2
from utility.static import GetBinanceLongPgSgSp, GetBinanceShortPgSgSp


class BackEngineBinanceMin2(BackEngineFutureMin2):
    def UpdateMarketGubun(self):
        self.market_gubun = 4

    def GetHogaunit(self, 호가빼기데이터):
        return min(x for x in 호가빼기데이터 if x > 0)

    def GetOrderCount(self, betting, 현재가, 보유중, 매수가, oc_ratio):
        return round(betting / (현재가 if not 보유중 else 매수가) * oc_ratio / 100, 8)

    def GetBuyPrice(self, 매수금액, 주문수량):
        return round(매수금액 / 주문수량, 4)

    def GetSellPrice(self, 매도금액, 주문수량):
        return round(매도금액 / 주문수량, 4)

    def GetLastSellPrice(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = round(매도금액 / 보유수량, 4)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = round(매도금액 / (보유수량 - 미체결수량), 4)
        return 매도가

    def GetProfitInfo(self, 현재가, 매수가, 보유수량):
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = GetBinanceLongPgSgSp(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['코인매수주문구분'],
                '시장가' in self.dict_set['코인매도주문구분'])
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = GetBinanceShortPgSgSp(
                보유수량 * 매수가, 보유수량 * 현재가,
                '시장가' in self.dict_set['코인매수주문구분'],
                '시장가' in self.dict_set['코인매도주문구분'])
        return 포지션, 평가금액, 수익금, 수익률
