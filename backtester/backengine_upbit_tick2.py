
import numpy as np
from backtester.back_static import get_trade_info
from backtester.backengine_upbit_tick import BackEngineUpbitTick
from utility.setting import dict_order_ratio
from utility.static import timedelta_sec, GetUpbitPgSgSp, dt_ymdhms, dt_ymdhm, GetUpbitHogaunit


class BackEngineUpbitTick2(BackEngineUpbitTick):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율, 매도총잔량, \
            매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, 매도수5호가잔량합, \
            관심종목 = self.dict_arry[self.indexn, 1:self.data_cnt]

        저가대비고가등락율, 순매수금액 = np.round((고가 / 저가 - 1) * 100, 2), int((초당매수수량 - 초당매도수량) * 현재가 / 1_000_000)
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:])
        self.hoga_unit = 호가단위 = GetUpbitHogaunit(현재가)

        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.buy_hj_limit]
        self.shogainfo = shogainfo[:self.sell_hj_limit]

        if not self.high_low:
            self.high_low = [현재가, 현재가, self.indexn, self.indexn]
        else:
            if 현재가 > self.high_low[0]:
                self.high_low[0] = 현재가
                self.high_low[2] = self.indexn
            if 현재가 < self.high_low[1]:
                self.high_low[1] = 현재가
                self.high_low[3] = self.indexn

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

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
                    수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey)
                    if gubun is None: continue

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

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey)
                    if gubun is None: continue

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

            gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey)
            if gubun is None: return

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

    def GetSellInfo(self, vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간):
        self.indexb = 매수틱번호
        수익금, 수익률, 보유시간 = 0, 0, 0
        if self.trade_info[vturn][vkey]['보유중']:
            _, 수익금, 수익률 = GetUpbitPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
            if 수익률 > 최고수익률:
                self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
            elif 수익률 < 최저수익률:
                self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
            now_time = self._now()
            보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        return 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def CheckBuyOrSell(self, 보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, vturn, vkey, 분봉저가=None, 분봉고가=None):
        gubun = None
        if self.dict_set['코인매수주문구분'] == '시장가':
            if not 보유중:
                gubun = '매수'
            elif 매수분할횟수 < self.dict_set['코인매수분할횟수']:
                gubun = '매수매도'
            else:
                gubun = '매도'
        elif self.dict_set['코인매수주문구분'] == '지정가':
            관심종목1 = self._관심종목N(1)
            if not 보유중:
                if 매수호가 == 0:
                    gubun = '매수'
                else:
                    관심이탈 = not 관심종목 and 관심종목1
                    self.CheckBuy(vturn, vkey, 현재가, 관심이탈, 분봉저가)
                    return gubun
            elif 매수분할횟수 < self.dict_set['코인매수분할횟수']:
                if 매수호가 == 0 and 매도호가 == 0:
                    if self.dict_set['코인매도금지매수횟수'] and 매수분할횟수 < self.dict_set['코인매도금지매수횟수값']:
                        gubun = '매수'
                    else:
                        gubun = '매수매도'
                elif 매수호가 != 0:
                    관심이탈 = not 관심종목 and 관심종목1
                    self.CheckBuy(vturn, vkey, 현재가, 관심이탈, 분봉저가)
                    return gubun
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self.CheckSell(vturn, vkey, 현재가, 관심진입, 분봉고가)
                    return gubun
            else:
                if 매도호가 == 0:
                    gubun = '매도'
                else:
                    관심진입 = 관심종목 and not 관심종목1
                    self.CheckSell(vturn, vkey, 현재가, 관심진입, 분봉고가)
                    return gubun
        return gubun

    def CancelBuyOrder(self, 현재가, vturn, vkey):
        cancel = False
        now_time = self._now()
        거래횟수, 손절횟수, 직전거래시간, 손절매도시간 = self.day_info[vturn][vkey].values()
        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['코인매수금지거래횟수'] and self.dict_set['코인매수금지거래횟수값'] <= 거래횟수:
            cancel = True
        elif self.dict_set['코인매수금지손절횟수'] and self.dict_set['코인매수금지손절횟수값'] <= 손절횟수:
            cancel = True
        elif self.dict_set['코인매수금지시간'] and self.dict_set['코인매수금지시작시간'] < hms < self.dict_set['코인매수금지종료시간']:
            cancel = True
        elif self.dict_set['코인매수금지간격'] and now_time <= 직전거래시간:
            cancel = True
        elif self.dict_set['코인매수금지손절간격'] and now_time <= 손절매도시간:
            cancel = True
        elif self.dict_set['코인매수금지200원이하'] and 현재가 <= 200:
            cancel = True
        return cancel

    def SetBuyCount3(self, vturn, vkey, 보유중, 매수가, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매수분할횟수, 매도호가1, 매수호가1, 호가단위):
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = 순매수금액
            elif self.set_weight[0] == 3:
                비중조절기준 = 당일거래대금
            else:
                비중조절기준 = self._등락율각도(30)

            if 비중조절기준 < self.set_weight[1]:
                betting = self.betting * self.set_weight[5]
            elif 비중조절기준 < self.set_weight[2]:
                betting = self.betting * self.set_weight[6]
            elif 비중조절기준 < self.set_weight[3]:
                betting = self.betting * self.set_weight[7]
            elif 비중조절기준 < self.set_weight[4]:
                betting = self.betting * self.set_weight[8]
            else:
                betting = self.betting * self.set_weight[9]

        oc_ratio = dict_order_ratio[self.dict_set['코인매수분할방법']][self.dict_set['코인매수분할횟수']][매수분할횟수]
        self.trade_info[vturn][vkey]['주문수량'] = np.round(betting / (현재가 if not 보유중 else 매수가) * oc_ratio / 100, 8)

        if self.dict_set['코인매수주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['코인매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['코인매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.trade_info[vturn][vkey]['매수호가_'] = 기준가격 + 호가단위 * self.dict_set['코인매수지정가호가번호']

    def CheckDividBuy(self, 현재가, 추가매수가, 수익률, vturn, vkey):
        분할매수기준수익률 = (현재가 / 추가매수가 - 1) * 100 if self.dict_set['코인매수분할고정수익률'] else 수익률
        if self.dict_set['코인매수분할하방'] and 분할매수기준수익률 < -self.dict_set['코인매수분할하방수익률']:
            self.Buy(vturn, vkey)
            return True
        elif self.dict_set['코인매수분할상방'] and 분할매수기준수익률 > self.dict_set['코인매수분할상방수익률']:
            self.Buy(vturn, vkey)
            return True
        return False

    def CheckSonjeol(self, 수익률, 수익금, vturn, vkey):
        if (self.dict_set['코인매도손절수익률청산'] and 수익률 < -self.dict_set['코인매도손절수익률']) or \
                (self.dict_set['코인매도손절수익금청산'] and 수익금 < -self.dict_set['코인매도손절수익금'] * 10000):
            origin_sell_gubun = self.dict_set['코인매도주문구분']
            self.dict_set['코인매도주문구분'] = '시장가'
            self.trade_info[vturn][vkey]['주문수량'] = self.trade_info[vturn][vkey]['보유수량']
            self.Sell(vturn, vkey, 200)
            self.dict_set['코인매도주문구분'] = origin_sell_gubun
            return True
        return False

    def CancelSellOrder(self, 매수분할횟수, vturn, vkey):
        cancel = False
        if self.dict_set['코인매도주문구분'] == '시장가':
            if 매수분할횟수 != self.trade_info[vturn][vkey]['매수분할횟수']:
                cancel = True
                return cancel
        elif self.trade_info[vturn][vkey]['매수호가'] != 0:
            cancel = True
            return cancel

        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['코인매도금지시간'] and self.dict_set['코인매도금지시작시간'] < hms < self.dict_set['코인매도금지종료시간']:
            cancel = True
        elif self.dict_set['코인매도금지간격'] and self._now() <= self.day_info[vturn][vkey]['직전거래시간']:
            cancel = True
        elif self.dict_set['코인매수분할횟수'] > 1 and self.dict_set['코인매도금지매수횟수'] and 매수분할횟수 <= self.dict_set['코인매도금지매수횟수값']:
            cancel = True
        return cancel

    def SetSellCount2(self, vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매도분할횟수, 매도호가1, 매수호가1, 호가단위):
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = 순매수금액
            elif self.set_weight[0] == 3:
                비중조절기준 = 당일거래대금
            else:
                비중조절기준 = self._등락율각도(30)

            if 비중조절기준 < self.set_weight[1]:
                betting = self.betting * self.set_weight[5]
            elif 비중조절기준 < self.set_weight[2]:
                betting = self.betting * self.set_weight[6]
            elif 비중조절기준 < self.set_weight[3]:
                betting = self.betting * self.set_weight[7]
            elif 비중조절기준 < self.set_weight[4]:
                betting = self.betting * self.set_weight[8]
            else:
                betting = self.betting * self.set_weight[9]

        oc_ratio = dict_order_ratio[self.dict_set['코인매도분할방법']][self.dict_set['코인매도분할횟수']][매도분할횟수]
        self.trade_info[vturn][vkey]['주문수량'] = np.round(betting / self.trade_info[vturn][vkey]['매수가'] * oc_ratio / 100, 8)
        if self.trade_info[vturn][vkey]['주문수량'] > 보유수량 or 매도분할횟수 + 1 == self.dict_set['코인매도분할횟수']:
            self.trade_info[vturn][vkey]['주문수량'] = 보유수량

        if self.dict_set['코인매도주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['코인매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['코인매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.trade_info[vturn][vkey]['매도호가_'] = 기준가격 + 호가단위 * self.dict_set['코인매도지정가호가번호']

    def CheckDividSell(self, 수익률, 매도분할횟수, vturn, vkey):
        if self.dict_set['코인매도분할하방'] and 수익률 < -self.dict_set['코인매도분할하방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100)
            return False
        elif self.dict_set['코인매도분할상방'] and 수익률 > self.dict_set['코인매도분할상방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100)
            return False
        return True

    def Buy(self, vturn, vkey, gubun=None):
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        if 주문수량 > 0:
            if self.dict_set['코인매수주문구분'] == '시장가':
                매수금액 = 0
                for 매도호가, 매도잔량 in self.bhogainfo:
                    if 미체결수량 - 매도잔량 <= 0:
                        매수금액 += 매도호가 * 미체결수량
                        미체결수량 -= 매도잔량
                        break
                    else:
                        매수금액 += 매도호가 * 매도잔량
                        미체결수량 -= 매도잔량
                if 미체결수량 <= 0:
                    직전매수가 = self.trade_info[vturn][vkey]['매수가']
                    직전보유수량 = self.trade_info[vturn][vkey]['보유수량']
                    추가매수가 = np.round(매수금액 / 주문수량, 4)
                    보유수량 = 직전보유수량 + 주문수량
                    매수가 = np.round((직전매수가 * 직전보유수량 + 매수금액) / 보유수량, 4)
                    self.trade_info[vturn][vkey]['매수가'] = 매수가
                    self.trade_info[vturn][vkey]['보유수량'] = 보유수량
                    self.trade_info[vturn][vkey]['추가매수가'] = 추가매수가
                    self.UpdateBuyInfo(vturn, vkey, True if 직전매수가 == 0 else False)
            elif self.dict_set['코인매수주문구분'] == '지정가':
                self.trade_info[vturn][vkey]['매수호가'] = self.trade_info[vturn][vkey]['매수호가_']
                self.trade_info[vturn][vkey]['매수호가단위'] = \
                    self.dict_arry[self.indexn, 16] - self.dict_arry[self.indexn, 17]
                self.trade_info[vturn][vkey]['매수주문취소시간'] = \
                    timedelta_sec(self.dict_set['코인매수취소시간초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))

    def CheckBuy(self, vturn, vkey, 현재가, 관심이탈, 분봉저가):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, _, 주문수량, 보유수량, _, _, _, _, _, 매수호가, _, _, _, _, \
            매수호가단위, _, _, _, _, _, 매수주문취소시간, _ = self.trade_info[vturn][vkey].values()

        if self.dict_set['코인매수취소관심이탈'] and 관심이탈:
            self.trade_info[vturn][vkey]['매수호가'] = 0
        elif self.dict_set['코인매수취소시간'] and (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매수주문취소시간:
            self.trade_info[vturn][vkey]['매수호가'] = 0
        elif self.trade_info[vturn][vkey]['매수정정횟수'] < self.dict_set['코인매수정정횟수'] and \
                현재가 >= 매수호가 + 매수호가단위 * self.dict_set['코인매수정정호가차이']:
            self.trade_info[vturn][vkey]['매수호가'] = 현재가 - 매수호가단위 * self.dict_set['코인매수정정호가']
            self.trade_info[vturn][vkey]['매수정정횟수'] += 1
            self.trade_info[vturn][vkey]['매수호가단위'] = \
                self.dict_arry[self.indexn, 16] - self.dict_arry[self.indexn, 17]
        elif (분봉저가 is None and 현재가 < 매수호가) or (분봉저가 is not None and 분봉저가 < 매수호가):
            직전매수금액 = 매수가 * 보유수량
            매수금액 = 매수호가 * 주문수량
            총수량 = 보유수량 + 주문수량
            평단가 = int(np.round((직전매수금액 + 매수금액) / 총수량))
            self.trade_info[vturn][vkey]['매수가'] = 평단가
            self.trade_info[vturn][vkey]['보유수량'] = 총수량
            self.trade_info[vturn][vkey]['추가매수가'] = 매수호가
            self.UpdateBuyInfo(vturn, vkey, True if 매수가 == 0 else False)

    def UpdateBuyInfo(self, vturn, vkey, firstbuy):
        datetimefromindex = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
        self.trade_info[vturn][vkey]['보유중'] = 1
        self.trade_info[vturn][vkey]['매수호가'] = 0
        self.trade_info[vturn][vkey]['매수정정횟수'] = 0
        self.day_info[vturn][vkey]['직전거래시간'] = timedelta_sec(self.dict_set['코인매수금지간격초'], datetimefromindex)
        if firstbuy:
            self.trade_info[vturn][vkey]['매수틱번호'] = self.indexn
            self.trade_info[vturn][vkey]['매수시간'] = datetimefromindex
            self.trade_info[vturn][vkey]['추가매수시간'] = []
            self.trade_info[vturn][vkey]['매수분할횟수'] = 0
        text = f"{self.index};{self.trade_info[vturn][vkey]['추가매수가']}"
        self.trade_info[vturn][vkey]['추가매수시간'].append(text)
        self.trade_info[vturn][vkey]['매수분할횟수'] += 1

    def Sell(self, vturn, vkey, sell_cond, gubun=None):
        if self.dict_set['코인매도주문구분'] == '시장가':
            매도금액 = 0
            주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
            for 매수호가, 매수잔량 in self.shogainfo:
                if 미체결수량 - 매수잔량 <= 0:
                    매도금액 += 매수호가 * 미체결수량
                    미체결수량 -= 매수잔량
                    break
                else:
                    매도금액 += 매수호가 * 매수잔량
                    미체결수량 -= 매수잔량
            if 미체결수량 <= 0:
                self.trade_info[vturn][vkey]['매도가'] = np.round(매도금액 / 주문수량, 4)
                self.sell_cond = sell_cond
                self.CalculationEyun(vturn, vkey)
        elif self.dict_set['코인매도주문구분'] == '지정가':
            self.sell_cond = sell_cond
            self.trade_info[vturn][vkey]['매도호가'] = self.trade_info[vturn][vkey]['매도호가_']
            self.trade_info[vturn][vkey]['매도호가단위'] = \
                self.dict_arry[self.indexn, 16] - self.dict_arry[self.indexn, 17]
            self.trade_info[vturn][vkey]['매도주문취소시간'] = \
                timedelta_sec(self.dict_set['코인매도취소시간초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))

    def CheckSell(self, vturn, vkey, 현재가, 관심진입, 분봉고가):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
        """
        _, _, _, _, _, _, _, _, _, _, _, 매도호가, _, _, _, _, \
            매도호가단위, _, 매도정정횟수, _, _, _, 매도주문취소시간 = self.trade_info[vturn][vkey].values()

        if self.dict_set['코인매도취소관심진입'] and 관심진입:
            self.trade_info[vturn][vkey]['매도호가'] = 0
        elif self.dict_set['코인매도취소시간'] and (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매도주문취소시간:
            self.trade_info[vturn][vkey]['매도호가'] = 0
        elif 매도정정횟수 < self.dict_set['코인매도정정횟수'] and 현재가 <= 매도호가 - 매도호가단위 * self.dict_set['코인매도정정호가차이']:
            self.trade_info[vturn][vkey]['매도호가'] = 현재가 + 매도호가단위 * self.dict_set['코인매도정정호가']
            self.trade_info[vturn][vkey]['매도정정횟수'] += 1
            self.trade_info[vturn][vkey]['매도호가단위'] = \
                self.dict_arry[self.indexn, 16] - self.dict_arry[self.indexn, 17]
        elif (분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가):
            self.trade_info[vturn][vkey]['매도가'] = 매도호가
            self.CalculationEyun(vturn, vkey)

    def CalculationEyun(self, vturn, vkey):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, 매도가, 주문수량, 보유수량, _, _, 매수틱번호, 매수시간, 추가매수시간 = list(self.trade_info[vturn][vkey].values())[:10]
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        더미 = 0
        매수시간, 매도시간, 매입금액 = int(self.dict_arry[매수틱번호, 0]), self.index, 주문수량 * 매수가
        평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 주문수량 * 매도가)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '^'.join(추가매수시간), 보유수량 - 주문수량 == 0
        data = ('백테결과', self.name, 더미, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        if 수익률 < 0:
            self.day_info[vturn][vkey]['손절횟수'] += 1
            self.day_info[vturn][vkey]['손절매도시간'] = \
                timedelta_sec(self.dict_set['코인매수금지손절간격초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))
        if 보유수량 - 주문수량 > 0:
            self.trade_info[vturn][vkey]['매도호가'] = 0
            self.trade_info[vturn][vkey]['보유수량'] -= self.trade_info[vturn][vkey]['주문수량']
            self.trade_info[vturn][vkey]['매도정정횟수'] = 0
            self.trade_info[vturn][vkey]['매도분할횟수'] += 1
        else:
            self.trade_info[vturn][vkey] = get_trade_info(2)
