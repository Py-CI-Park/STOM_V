
import numpy as np
from backtester.backengine_base import BackEngineBase
from utility.static import GetFutureLongPgSgSp, GetFutureShortPgSgSp


class BackEngineFutureTick(BackEngineBase):
    def Strategy(self):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        순매수금액 = 초당매수금액 - 초당매도금액
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:])
        호가빼기데이터 = (매도호가5 - 매도호가4, 매도호가4 - 매도호가3, 매도호가3 - 매도호가2, 매수호가2 - 매수호가3, 매수호가3 - 매수호가4, 매수호가4 - 매수호가5)
        # noinspection PyUnusedLocal
        self.hoga_unit = 호가단위 = self.GetHogaunit(호가빼기데이터)

        self.shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        self.UpdateHighLow(현재가)

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(v)

        if self.opti_turn == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    self.vturn, self.vkey = vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

                    # noinspection PyUnusedLocal
                    BUY_LONG, SELL_SHORT = True, True
                    # noinspection PyUnusedLocal
                    SELL_LONG, BUY_SHORT = False, False
                    if not 보유중:
                        if not 관심종목: continue
                        self.info_for_order = 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금
                        exec(self.buystg)
                    else:
                        포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                        self.profit, self.hold_time = 수익률, 보유시간
                        exec(self.sellstg)

        elif self.opti_turn == 3:
            for vturn in self.trade_info:
                for vkey in self.trade_info[vturn]:
                    index_ = vturn * 20 + vkey
                    if self.back_type != '조건최적화':
                        self.vars = self.vars_lists[index_]
                        if vturn != 0:
                            if self.tick_count < self.vars[0]:
                                return
                        else:
                            if self.tick_count < self.vars[0]:
                                continue
                    elif self.tick_count < self.avgtime:
                        return

                    self.vturn, self.vkey = vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

                    # noinspection PyUnusedLocal
                    BUY_LONG, SELL_SHORT = True, True
                    # noinspection PyUnusedLocal
                    SELL_LONG, BUY_SHORT = False, False
                    if not 보유중:
                        if not 관심종목: continue
                        self.info_for_order = 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                        self.profit, self.hold_time = 수익률, 보유시간
                        if self.back_type != '조건최적화':
                            exec(self.sellstg)
                        else:
                            exec(self.dict_sellstg[index_])
        else:
            vturn, vkey = 0, 0
            if self.back_type in ('최적화', '전진분석'):
                if self.tick_count < self.vars[0]:
                    return
            else:
                if self.tick_count < self.avgtime:
                    return

            self.vturn, self.vkey = vturn, vkey
            self.curr_trade_info = self.trade_info[vturn][vkey]
            보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

            # noinspection PyUnusedLocal
            BUY_LONG, SELL_SHORT = True, True
            # noinspection PyUnusedLocal
            SELL_LONG, BUY_SHORT = False, False
            if not 보유중:
                if not 관심종목: return
                self.info_for_order = 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금
                exec(self.buystg)
            else:
                포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)

    def UpdateMarketGubun(self):
        self.market_gubun = 2

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)

    # noinspection PyUnusedLocal
    def GetHogaunit(self, 호가빼기데이터):
        return self.dict_info[self.code]['호가단위']

    def GetOrderCount(self, betting, 현재가, 보유중, 매수가, oc_ratio):
        return int(betting)

    def GetBuyPrice(self, 매수금액, 주문수량):
        return np.round(매수금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])

    def GetSellPrice(self, 매도금액, 주문수량):
        return np.round(매도금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])

    def GetLastSellPrice(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = np.round(매도금액 / 보유수량, self.dict_info[self.code]['소숫점자리수'])
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = np.round(매도금액 / (보유수량 - 미체결수량), self.dict_info[self.code]['소숫점자리수'])
        return 매도가

    def GetProfitInfo(self, 현재가, 매수가, 보유수량):
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 보유수량
        평가금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[self.code]['틱가치'] * 보유수량
        if self.curr_trade_info['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, self.code)
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, self.code)
        return 포지션, 평가금액, 수익금, 수익률
