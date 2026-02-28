
import numpy as np
from backtester.backengine_base_oms import BackEngineBaseOms
from utility.static import GetUpbitHogaunit, GetUpbitPgSgSp


class BackEngineUpbitTick2(BackEngineBaseOms):
    def Strategy(self):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        순매수금액 = 초당매수금액 - 초당매도금액
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:])
        # noinspection PyUnusedLocal
        self.hoga_unit = 호가단위 = GetUpbitHogaunit(현재가)

        shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.shogainfo = shogainfo[:self.buy_hj_limit]
        self.bhogainfo = bhogainfo[:self.sell_hj_limit]

        if self.high_low:
            if 고가 >= self.high_low[0]:
                self.high_low[0] = 고가
                self.high_low[1] = self.indexn
            if 저가 <= self.high_low[1]:
                self.high_low[2] = 저가
                self.high_low[3] = self.indexn
        else:
            self.high_low = [고가, self.indexn, 저가, self.indexn]

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
                    self.curr_day_info = self.day_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                    self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                                매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션)
                    if gubun is None: continue

                    # noinspection PyUnusedLocal
                    매수, 매도 = True, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가): continue
                        if not 보유중:
                            exec(self.buystg)
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['코인매수분할시그널']:
                                exec(self.buystg)

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금): continue
                        if self.CancelSellOrder(현재가, 매수분할횟수): continue
                        if self.dict_set['코인매도분할횟수'] == 1:
                            exec(self.sellstg)
                        else:
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set['코인매도분할시그널']:
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
                    self.curr_day_info = self.day_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                    self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                                매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션)
                    if gubun is None: continue

                    # noinspection PyUnusedLocal
                    매수, 매도 = True, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가): continue
                        if not 보유중:
                            if self.back_type != '조건최적화':
                                exec(self.buystg)
                            else:
                                exec(self.dict_buystg[index_])
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['코인매도분할시그널']:
                                if self.back_type != '조건최적화':
                                    exec(self.buystg)
                                else:
                                    exec(self.dict_buystg[index_])

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금): continue
                        if self.CancelSellOrder(현재가, 매수분할횟수): continue
                        if self.dict_set['코인매도분할횟수'] == 1:
                            if self.back_type != '조건최적화':
                                exec(self.sellstg)
                            else:
                                exec(self.dict_sellstg[index_])
                        else:
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set['코인매도분할시그널']:
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
            self.curr_day_info = self.day_info[vturn][vkey]

            보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
            포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
            self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수
            self.profit, self.hold_time = 수익률, 보유시간

            gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                        매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션)
            if gubun is None: return

            # noinspection PyUnusedLocal
            매수, 매도 = True, False
            if '매수' in gubun:
                if not 관심종목: return
                if self.CancelBuyOrder(현재가): return
                if not 보유중:
                    exec(self.buystg)
                else:
                    if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set['코인매수분할시그널']:
                        exec(self.buystg)

            if '매도' in gubun:
                if self.CheckSonjeol(수익률, 수익금): return
                if self.CancelSellOrder(현재가, 매수분할횟수): return
                if self.dict_set['코인매도분할횟수'] == 1:
                    exec(self.sellstg)
                else:
                    if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set['코인매도분할시그널']:
                        exec(self.sellstg)

    def UpdateMarketGubun(self):
        self.market_gubun = 3

    def UpdateGlobalsFunc(self, dict_update_func):
        globals().update(dict_update_func)

    def GetAddBuyPrice(self, 매수금액, 주문수량):
        return np.round(매수금액 / 주문수량, 4)

    def GetBuyPrice(self, 직전매수가, 직전보유수량, 매수금액, 보유수량):
        return np.round((직전매수가 * 직전보유수량 + 매수금액) / 보유수량, 4)

    def GetOrderCount(self, betting, 현재가, 보유중, 매수가, oc_ratio):
        return np.round(betting / (현재가 if not 보유중 else 매수가) * oc_ratio / 100, 8)

    def GetProfitInfo(self, 현재가, 매수가, 보유수량):
        시가총액 = 0
        평가금액, 수익금, 수익률 = GetUpbitPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
        return 시가총액, 평가금액, 수익금, 수익률

    def GetSellPrice(self, 매도금액, 주문수량):
        return np.round(매도금액 / 주문수량, 4)

    def GetLastSellPrice(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = np.round(매도금액 / 보유수량, 4)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = np.round(매도금액 / (보유수량 - 미체결수량), 4)
        return 매도가
