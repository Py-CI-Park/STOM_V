
import numpy as np
from backtester.backengine_upbit_tick2 import BackEngineUpbitTick2
from utility.static import GetIndicator, GetUpbitHogaunit


class BackEngineUpbitMin2(BackEngineUpbitTick2):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, \
            분당매수수량, 분당매도수량, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, \
            고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, \
            매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, \
            매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목 = self.dict_arry[self.indexn, 1:self.data_cnt]

        저가대비고가등락율, 순매수금액 = np.round((고가 / 저가 - 1) * 100, 2), int((분당매수수량 - 분당매도수량) * 현재가 / 1_000_000)
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:] + '00')
        self.hoga_unit = 호가단위 = GetUpbitHogaunit(현재가)

        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.buy_hj_limit]
        self.shogainfo = shogainfo[:self.sell_hj_limit]

        if not self.high_low:
            self.high_low = [분봉고가, 분봉저가, self.indexn, self.indexn]
        else:
            if 분봉고가 > self.high_low[0]:
                self.high_low[0] = 분봉고가
                self.high_low[2] = self.indexn
            if 분봉저가 < self.high_low[1]:
                self.high_low[1] = 분봉저가
                self.high_low[3] = self.indexn

        start, end = self.indexn+1-self.tick_count, self.indexn+1
        self.mc = self.dict_arry[start:end, self._fi('현재가')]
        self.mh = self.dict_arry[start:end, self._fi('분봉고가')]
        self.ml = self.dict_arry[start:end, self._fi('분봉저가')]
        self.mv = self.dict_arry[start:end, self._fi('분당거래대금')]

        if self.opti_turn == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
                    수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey,
                                                분봉저가=분봉저가, 분봉고가=분봉고가)
                    if gubun is None: continue

                    if self.indistg is not None:
                        exec(self.indistg)
                    self.k = list(self.indicator.values())
                    AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, \
                        OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = GetIndicator(self.mc, self.mh, self.ml, self.mv, self.k)

                    if self.dict_condition:
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    매수, 매도 = True, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가, vturn, vkey): continue
                        self.SetBuyCount3(vturn, vkey, 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                          매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if not 보유중:
                            exec(self.buystg)
                        else:
                            if not self.CheckDividBuy(현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매수분할시그널']:
                                exec(self.buystg)

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금, vturn, vkey): continue
                        if self.CancelSellOrder(매수분할횟수, vturn, vkey): continue
                        self.SetSellCount2(vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                           매도분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if self.dict_set['코인매도분할횟수'] == 1:
                            exec(self.sellstg)
                        else:
                            if not self.CheckDividSell(수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
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

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
                    수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey,
                                                분봉저가=분봉저가, 분봉고가=분봉고가)
                    if gubun is None: continue

                    if self.indistg is not None:
                        exec(self.indistg)
                    self.k = list(self.indicator.values())
                    AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, \
                        OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = GetIndicator(self.mc, self.mh, self.ml, self.mv, self.k)

                    if self.dict_condition:
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    매수, 매도 = True, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가, vturn, vkey): continue
                        self.SetBuyCount3(vturn, vkey, 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                          매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if not 보유중:
                            if self.back_type != '조건최적화':
                                exec(self.buystg)
                            else:
                                exec(self.dict_buystg[index_])
                        else:
                            if not self.CheckDividBuy(현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매도분할시그널']:
                                if self.back_type != '조건최적화':
                                    exec(self.buystg)
                                else:
                                    exec(self.dict_buystg[index_])

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금, vturn, vkey): continue
                        if self.CancelSellOrder(매수분할횟수, vturn, vkey): continue
                        self.SetSellCount2(vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                           매도분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if self.dict_set['코인매도분할횟수'] == 1:
                            if self.back_type != '조건최적화':
                                exec(self.sellstg)
                            else:
                                exec(self.dict_sellstg[index_])
                        else:
                            if not self.CheckDividSell(수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
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

            보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                매도분할횟수, 매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
            수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
            self.profit, self.hold_time = 수익률, 보유시간

            gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey,
                                        분봉저가=분봉저가, 분봉고가=분봉고가)
            if gubun is None: return

            if self.indistg is not None:
                exec(self.indistg)
            self.k = list(self.indicator.values())
            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, \
                OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = GetIndicator(self.mc, self.mh, self.ml, self.mv, self.k)

            if self.dict_condition:
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    exec(v)

            매수, 매도 = True, False
            if '매수' in gubun:
                if not 관심종목: return
                if self.CancelBuyOrder(현재가, vturn, vkey): return
                self.SetBuyCount3(vturn, vkey, 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                  매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                if not 보유중:
                    exec(self.buystg)
                else:
                    if not self.CheckDividBuy(현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매수분할시그널']:
                        exec(self.buystg)

            if '매도' in gubun:
                if self.CheckSonjeol(수익률, 수익금, vturn, vkey): return
                if self.CancelSellOrder(매수분할횟수, vturn, vkey): return
                self.SetSellCount2(vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                   매도분할횟수, 매도호가1, 매수호가1, 호가단위)
                if self.dict_set['코인매도분할횟수'] == 1:
                    exec(self.sellstg)
                else:
                    if not self.CheckDividSell(수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
                        exec(self.sellstg)
