
import numpy as np
from backtester.back_static import get_trade_info
from backtester.backengine_future_tick import BackEngineFutureTick
from utility.setting import dict_order_ratio
from utility.static import timedelta_sec, GetFutureLongPgSgSp, GetFutureShortPgSgSp, dt_ymdhms, dt_ymdhm


class BackEngineFutureTick2(BackEngineFutureTick):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율, 매도총잔량, \
            매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, 매도수5호가잔량합, \
            관심종목 = self.dict_arry[self.indexn, 1:self.data_cnt]

        저가대비고가등락율, 순매수금액 = np.round((고가 / 저가 - 1) * 100, 2), int((초당매수수량 - 초당매도수량) * 현재가 / 1_000_000)
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:])
        self.hoga_unit = 호가단위 = self.dict_info[종목코드]['호가단위']

        self.bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

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
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, vturn, vkey)
                    if gubun is None: continue

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(self._now(), vturn, vkey): continue
                        self.SetBuyCount2(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                          매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if not 보유중:
                            exec(self.buystg)
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매수분할시그널']:
                                exec(self.buystg)

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금, vturn, vkey): continue
                        if self.CancelSellOrder(매수분할횟수, vturn, vkey): continue
                        self.SetSellCount2(vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                           매도분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if self.dict_set['코인매도분할횟수'] == 1:
                            exec(self.sellstg)
                        else:
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
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
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                        self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, vturn, vkey)
                    if gubun is None: continue

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(self._now(), vturn, vkey): continue
                        self.SetBuyCount2(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                          매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                        if not 보유중:
                            if self.back_type != '조건최적화':
                                exec(self.buystg)
                            else:
                                exec(self.dict_buystg[index_])
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매수분할시그널']:
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
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
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
                매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
            포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                self.GetSellInfo(vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간)
            self.profit, self.hold_time = 수익률, 보유시간

            gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, vturn, vkey)
            if gubun is None: return

            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False

            if '매수' in gubun:
                if not 관심종목: return
                if self.CancelBuyOrder(self._now(), vturn, vkey): return
                self.SetBuyCount2(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                  매수분할횟수, 매도호가1, 매수호가1, 호가단위)
                if not 보유중:
                    exec(self.buystg)
                else:
                    if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률, vturn, vkey) and self.dict_set['코인매수분할시그널']:
                        exec(self.buystg)

            if '매도' in gubun:
                if self.CheckSonjeol(수익률, 수익금, vturn, vkey): return
                if self.CancelSellOrder(매수분할횟수, vturn, vkey): return
                self.SetSellCount2(vturn, vkey, 보유수량, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금,
                                   매도분할횟수, 매도호가1, 매수호가1, 호가단위)
                if self.dict_set['코인매도분할횟수'] == 1:
                    exec(self.sellstg)
                else:
                    if not self.CheckDividSell(포지션, 수익률, 매도분할횟수, vturn, vkey) and self.dict_set['코인매도분할시그널']:
                        exec(self.sellstg)

    def GetSellInfo(self, vturn, vkey, 매수틱번호, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수시간):
        self.indexb = 매수틱번호
        수익금, 수익률, 보유시간, 포지션 = 0, 0, 0, None
        if self.trade_info[vturn][vkey]['보유중'] != 0:
            매입금액 = self.dict_info[self.code]['위탁증거금'] * 보유수량
            평가금액 = 매입금액 + (현재가 - 매수가) * self.dict_info[self.code]['틱가치'] * 보유수량
            if self.trade_info[vturn][vkey]['보유중'] == 1:
                _, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, self.code)
                포지션 = 'LONG'
            else:
                _, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, self.code)
                포지션 = 'SHORT'
            if 수익률 > 최고수익률:
                self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
            elif 수익률 < 최저수익률:
                self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
            now_time = self._now()
            보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        return 포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def CheckBuyOrSell(self, 보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, vturn, vkey, 분봉저가=None, 분봉고가=None):
        gubun = None
        if self.dict_set['주식매수주문구분'] == '시장가':
            if not 보유중:
                gubun = '매수'
            elif 매수분할횟수 < self.dict_set['주식매수분할횟수']:
                gubun = '매수매도'
            else:
                gubun = '매도'
        elif self.dict_set['주식매수주문구분'] == '지정가':
            if not 보유중:
                if 매수호가 == 0:
                    gubun = '매수'
                else:
                    self.CheckBuy(vturn, vkey, 현재가, 분봉저가, 분봉고가)
                    return gubun
            elif 매수분할횟수 < self.dict_set['주식매수분할횟수']:
                if 매수호가 == 0 and 매도호가 == 0:
                    if self.dict_set['주식매도금지매수횟수'] and 매수분할횟수 < self.dict_set['주식매도금지매수횟수값']:
                        gubun = '매수'
                    else:
                        gubun = '매수매도'
                elif 매수호가 != 0:
                    self.CheckBuy(vturn, vkey, 현재가, 분봉저가, 분봉고가)
                    return gubun
                else:
                    self.CheckSell(vturn, vkey, 현재가, 분봉저가, 분봉고가)
                    return gubun
            else:
                if 매도호가 == 0:
                    gubun = '매도'
                else:
                    self.CheckSell(vturn, vkey, 현재가, 분봉저가, 분봉고가)
                    return gubun
        return gubun

    def CancelBuyOrder(self, vturn, vkey):
        cancel = False
        now_time = self._now()
        거래횟수, 손절횟수, 직전거래시간, 손절매도시간 = self.day_info[vturn][vkey].values()
        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['주식매수금지거래횟수'] and self.dict_set['주식매수금지거래횟수값'] <= 거래횟수:
            cancel = True
        elif self.dict_set['주식매수금지손절횟수'] and self.dict_set['주식매수금지손절횟수값'] <= 손절횟수:
            cancel = True
        elif self.dict_set['주식매수금지시간'] and self.dict_set['주식매수금지시작시간'] < hms < self.dict_set['주식매수금지종료시간']:
            cancel = True
        elif self.dict_set['주식매수금지간격'] and now_time <= 직전거래시간:
            cancel = True
        elif self.dict_set['주식매수금지손절간격'] and now_time <= 손절매도시간:
            cancel = True
        return cancel

    def SetBuyCount2(self, vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금, 매수분할횟수, 매도호가1, 매수호가1, 호가단위):
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

        oc_ratio = dict_order_ratio[self.dict_set['주식매수분할방법']][self.dict_set['주식매수분할횟수']][매수분할횟수]
        self.trade_info[vturn][vkey]['주문수량'] = int(betting * oc_ratio / 100)

        if self.dict_set['주식매수주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['주식매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.trade_info[vturn][vkey]['매수호가_'] = 기준가격 + 호가단위 * self.dict_set['주식매수지정가호가번호']

    def CheckDividBuy(self, 포지션, 현재가, 추가매수가, 수익률, vturn, vkey):
        분할매수기준수익률 = (현재가 / 추가매수가 - 1) * 100 if self.dict_set['주식매수분할고정수익률'] else 수익률
        if 포지션 == 'LONG' and self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
            self.Buy(vturn, vkey, 'LONG')
            return True
        elif 포지션 == 'LONG' and self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
            self.Buy(vturn, vkey, 'LONG')
            return True
        elif 포지션 == 'SHORT' and self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
            self.Buy(vturn, vkey, 'SHORT')
            return True
        elif 포지션 == 'SHORT' and self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
            self.Buy(vturn, vkey, 'SHORT')
            return True
        return False

    def CheckSonjeol(self, 수익률, 수익금, vturn, vkey):
        if (self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']) or \
                (self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금'] * 10000):
            gubun = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
            origin_sell_gubun = self.dict_set['주식매도주문구분']
            self.dict_set['주식매도주문구분'] = '시장가'
            self.trade_info[vturn][vkey]['주문수량'] = self.trade_info[vturn][vkey]['보유수량']
            self.Sell(vturn, vkey, 200, gubun)
            self.dict_set['주식매도주문구분'] = origin_sell_gubun
            return True
        return False

    def CancelSellOrder(self, 매수분할횟수, vturn, vkey):
        cancel = False
        if self.dict_set['주식매도주문구분'] == '시장가':
            if 매수분할횟수 != self.trade_info[vturn][vkey]['매수분할횟수']:
                cancel = True
                return cancel
        elif self.trade_info[vturn][vkey]['매수호가'] != 0:
            cancel = True
            return cancel

        hms = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        if self.dict_set['주식매도금지시간'] and self.dict_set['주식매도금지시작시간'] < hms < self.dict_set['주식매도금지종료시간']:
            cancel = True
        elif self.dict_set['주식매도금지간격'] and self._now() <= self.day_info[vturn][vkey]['직전거래시간']:
            cancel = True
        elif self.dict_set['주식매수분할횟수'] > 1 and self.dict_set['주식매도금지매수횟수'] and 매수분할횟수 <= self.dict_set['주식매도금지매수횟수값']:
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

        oc_ratio = dict_order_ratio[self.dict_set['주식매도분할방법']][self.dict_set['주식매도분할횟수']][매도분할횟수]
        self.trade_info[vturn][vkey]['주문수량'] = int(betting * oc_ratio / 100)
        if self.trade_info[vturn][vkey]['주문수량'] > 보유수량 or 매도분할횟수 + 1 == self.dict_set['주식매도분할횟수']:
            self.trade_info[vturn][vkey]['주문수량'] = 보유수량

        if self.dict_set['주식매도주문구분'] == '지정가':
            기준가격 = 현재가
            if self.dict_set['주식매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.trade_info[vturn][vkey]['매도호가_'] = 기준가격 + 호가단위 * self.dict_set['주식매도지정가호가번호']

    def CheckDividSell(self, 포지션, 수익률, 매도분할횟수, vturn, vkey):
        if 포지션 == 'LONG' and self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100, 'LONG')
            return True
        elif 포지션 == 'LONG' and self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100, 'LONG')
            return True
        elif 포지션 == 'SHORT' and self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100, 'SHORT')
            return True
        elif 포지션 == 'SHORT' and self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (매도분할횟수 + 1):
            self.Sell(vturn, vkey, 100, 'SHORT')
            return True
        return False

    def Buy(self, vturn, vkey, gubun=None):
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        if 주문수량 > 0:
            if self.dict_set['주식매수주문구분'] == '시장가':
                매수금액 = 0
                호가정보 = self.bhogainfo if gubun == 'LONG' else self.shogainfo
                호가정보 = 호가정보[:self.buy_hj_limit]
                for 호가, 잔량 in 호가정보:
                    if 미체결수량 - 잔량 <= 0:
                        매수금액 += 호가 * 미체결수량
                        미체결수량 -= 잔량
                        break
                    else:
                        매수금액 += 호가 * 잔량
                        미체결수량 -= 잔량
                if 미체결수량 <= 0:
                    직전매수가 = self.trade_info[vturn][vkey]['매수가']
                    직전보유수량 = self.trade_info[vturn][vkey]['보유수량']
                    추가매수가 = np.round(매수금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])
                    보유수량 = 직전보유수량 + 주문수량
                    매수가 = np.round((직전매수가 * 직전보유수량 + 추가매수가 * 주문수량) / 보유수량, self.dict_info[self.code]['소숫점자리수'])
                    self.trade_info[vturn][vkey]['매수가'] = 매수가
                    self.trade_info[vturn][vkey]['보유수량'] = 보유수량
                    self.trade_info[vturn][vkey]['추가매수가'] = 추가매수가
                    self.UpdateBuyInfo(vturn, vkey, gubun, True if 직전매수가 == 0 else False)
            elif self.dict_set['주식매수주문구분'] == '지정가':
                self.trade_info[vturn][vkey]['주문포지션'] = gubun
                self.trade_info[vturn][vkey]['매수호가'] = self.trade_info[vturn][vkey]['매수호가_']
                self.trade_info[vturn][vkey]['매수호가단위'] = self.dict_arry[self.indexn, 17] - self.dict_arry[self.indexn, 18]
                self.trade_info[vturn][vkey]['매수주문취소시간'] = \
                    timedelta_sec(self.dict_set['주식매수취소시간초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))

    def CheckBuy(self, vturn, vkey, 현재가, 분봉저가, 분봉고가):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, _, 주문수량, 보유수량, _, _, _, _, _, 매수호가, _, _, _, _, \
            매수호가단위, _, _, _, _, _, 매수주문취소시간, _, 주문포지션 = self.trade_info[vturn][vkey].values()

        if self.dict_set['주식매수취소시간'] and (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매수주문취소시간:
            self.trade_info[vturn][vkey]['매수호가'] = 0
        elif 주문포지션 == 'LONG' and self.trade_info[vturn][vkey]['매수정정횟수'] < self.dict_set['주식매수정정횟수'] and \
                현재가 >= 매수호가 + 매수호가단위 * self.dict_set['주식매수정정호가차이']:
            self.trade_info[vturn][vkey]['매수호가'] = 현재가 - 매수호가단위 * self.dict_set['주식매수정정호가']
            self.trade_info[vturn][vkey]['매수정정횟수'] += 1
        elif 주문포지션 == 'SHORT' and self.trade_info[vturn][vkey]['매수정정횟수'] < self.dict_set['주식매수정정횟수'] and \
                현재가 <= 매수호가 - 매수호가단위 * self.dict_set['주식매수정정호가차이']:
            self.trade_info[vturn][vkey]['매수호가'] = 현재가 + 매수호가단위 * self.dict_set['주식매수정정호가']
            self.trade_info[vturn][vkey]['매수정정횟수'] += 1
        elif (주문포지션 == 'LONG' and ((분봉저가 is None and 현재가 < 매수호가) or (분봉저가 is not None and 분봉저가 < 매수호가))) or \
                (주문포지션 == 'SHORT' and ((분봉고가 is None and 현재가 > 매수호가) or (분봉고가 is not None and 분봉고가 > 매수호가))):
            직전매수금액 = 매수가 * 보유수량
            매수금액 = 매수호가 * 주문수량
            총수량 = 보유수량 + 주문수량
            평단가 = np.round((직전매수금액 + 매수금액) / 총수량, self.dict_info[self.code]['소숫점자리수'])
            self.trade_info[vturn][vkey]['매수가'] = 평단가
            self.trade_info[vturn][vkey]['보유수량'] = 총수량
            self.trade_info[vturn][vkey]['추가매수가'] = 매수호가
            self.UpdateBuyInfo(vturn, vkey, 주문포지션, True if 매수가 == 0 else False)

    def UpdateBuyInfo(self, vturn, vkey, gubun, firstbuy):
        datetimefromindex = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
        self.trade_info[vturn][vkey]['보유중'] = 1 if gubun == 'LONG' else 2
        self.trade_info[vturn][vkey]['매수호가'] = 0
        self.trade_info[vturn][vkey]['매수정정횟수'] = 0
        self.day_info[vturn][vkey]['직전거래시간'] = timedelta_sec(self.dict_set['주식매수금지간격초'], datetimefromindex)
        if firstbuy:
            self.trade_info[vturn][vkey]['매수틱번호'] = self.indexn
            self.trade_info[vturn][vkey]['매수시간'] = datetimefromindex
            self.trade_info[vturn][vkey]['추가매수시간'] = []
            self.trade_info[vturn][vkey]['매수분할횟수'] = 0
        text = f"{self.index};{self.trade_info[vturn][vkey]['추가매수가']}"
        self.trade_info[vturn][vkey]['추가매수시간'].append(text)
        self.trade_info[vturn][vkey]['매수분할횟수'] += 1

    def Sell(self, vturn, vkey, sell_cond, gubun=None):
        if self.dict_set['주식매도주문구분'] == '시장가':
            매도금액 = 0
            주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
            호가정보 = self.shogainfo if gubun == 'LONG' else self.bhogainfo
            호가정보 = 호가정보[:self.sell_hj_limit]
            for 호가, 잔량 in 호가정보:
                if 미체결수량 - 잔량 <= 0:
                    매도금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매도금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                self.trade_info[vturn][vkey]['매도가'] = np.round(매도금액 / 주문수량, self.dict_info[self.code]['소숫점자리수'])
                self.sell_cond = sell_cond
                self.CalculationEyun(vturn, vkey)
        elif self.dict_set['주식매도주문구분'] == '지정가':
            self.sell_cond = sell_cond
            self.trade_info[vturn][vkey]['주문포지션'] = gubun
            self.trade_info[vturn][vkey]['매도호가'] = self.trade_info[vturn][vkey]['매도호가_']
            self.trade_info[vturn][vkey]['매도호가단위'] = self.dict_arry[self.indexn, 17] - self.dict_arry[self.indexn, 18]
            self.trade_info[vturn][vkey]['매도주문취소시간'] = \
                timedelta_sec(self.dict_set['주식매도취소시간초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))

    def CheckSell(self, vturn, vkey, 현재가, 분봉저가, 분봉고가):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
        """
        보유중, _, _, _, _, _, _, _, _, _, _, 매도호가, _, _, _, _, \
            매도호가단위, _, 매도정정횟수, _, _, _, 매도주문취소시간, _ = self.trade_info[vturn][vkey].values()

        gubun = 'LONG' if 보유중 == 1 else 'SHORT'
        if self.dict_set['주식매도취소시간'] and (dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))) > 매도주문취소시간:
            self.trade_info[vturn][vkey]['매도호가'] = 0
        elif gubun == 'LONG' and 매도정정횟수 < self.dict_set['주식매도정정횟수'] and \
                현재가 <= 매도호가 - 매도호가단위 * self.dict_set['주식매도정정호가차이']:
            self.trade_info[vturn][vkey]['매도호가'] = 현재가 + 매도호가단위 * self.dict_set['주식매도정정호가']
            self.trade_info[vturn][vkey]['매도정정횟수'] += 1
        elif gubun == 'SHORT' and 매도정정횟수 < self.dict_set['주식매도정정횟수'] and \
                현재가 >= 매도호가 + 매도호가단위 * self.dict_set['주식매도정정호가차이']:
            self.trade_info[vturn][vkey]['매도호가'] = 현재가 - 매도호가단위 * self.dict_set['주식매도정정호가']
            self.trade_info[vturn][vkey]['매도정정횟수'] += 1
        elif (gubun == 'LONG' and ((분봉고가 is None and 현재가 > 매도호가) or (분봉고가 is not None and 분봉고가 > 매도호가))) or \
                (gubun == 'SHORT' and ((분봉저가 is None and 현재가 < 매도호가) or (분봉저가 is not None and 분봉저가 < 매도호가))):
            self.trade_info[vturn][vkey]['매도가'] = 매도호가
            self.CalculationEyun(vturn, vkey)

    def CalculationEyun(self, vturn, vkey):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간, 주문포지션 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, 매도가, 주문수량, 보유수량, _, _, 매수틱번호, 매수시간, 추가매수시간 = list(self.trade_info[vturn][vkey].values())[:10]
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간 = int(self.dict_arry[매수틱번호, 0]), self.index
        매입금액 = self.dict_info[self.code]['위탁증거금'] * 주문수량
        평가금액 = 매입금액 + (매도가 - 매수가) * self.dict_info[self.code]['틱가치'] * 주문수량
        if self.trade_info[vturn][vkey]['보유중'] == 1:
            포지션 = 'LONG'
            평가금액, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, self.code)
        else:
            포지션 = 'SHORT'
            평가금액, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, self.code)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '^'.join(추가매수시간), 보유수량 - 주문수량 == 0
        data = ('백테결과', self.name, 포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        if 수익률 < 0:
            self.day_info[vturn][vkey]['손절횟수'] += 1
            self.day_info[vturn][vkey]['손절매도시간'] = \
                timedelta_sec(self.dict_set['주식매수금지손절간격초'], dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index)))
        if 보유수량 - 주문수량 > 0:
            self.trade_info[vturn][vkey]['매도호가'] = 0
            self.trade_info[vturn][vkey]['보유수량'] -= self.trade_info[vturn][vkey]['주문수량']
            self.trade_info[vturn][vkey]['매도정정횟수'] = 0
            self.trade_info[vturn][vkey]['매도분할횟수'] += 1
        else:
            v = get_trade_info(2)
            v['주문포지션'] = ''
            self.trade_info[vturn][vkey] = v
