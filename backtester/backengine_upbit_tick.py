
import numpy as np
from backtester.back_static import get_trade_info
from backtester.backengine_kiwoom_tick import BackEngineKiwoomTick
from utility.static import GetUpbitPgSgSp, dt_ymdhms, dt_ymdhm, GetUpbitHogaunit


class BackEngineUpbitTick(BackEngineKiwoomTick):
    def UpdateMarketGubun(self):
        self.market_gubun = 3

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

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                        exec(self.buystg)
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
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

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
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

            매수, 매도 = True, False
            if not self.trade_info[vturn][vkey]['보유중']:
                if not 관심종목: return
                self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                exec(self.buystg)
            else:
                수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)

    def SetBuyCount(self, vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금):
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

        self.trade_info[vturn][vkey]['주문수량'] = np.round(betting / 현재가, 8)

    def Buy(self, vturn, vkey, gubun=None):
        매수금액 = 0
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        if 주문수량 > 0:
            for 매도호가, 매도잔량 in self.bhogainfo:
                if 미체결수량 - 매도잔량 <= 0:
                    매수금액 += 매도호가 * 미체결수량
                    미체결수량 -= 매도잔량
                    break
                else:
                    매수금액 += 매도호가 * 매도잔량
                    미체결수량 -= 매도잔량
            if 미체결수량 <= 0:
                self.trade_info[vturn][vkey] = {
                    '보유중': 1,
                    '매수가': np.round(매수금액 / 주문수량, 4),
                    '매도가': 0,
                    '주문수량': 0,
                    '보유수량': 주문수량,
                    '최고수익률': 0.,
                    '최저수익률': 0.,
                    '매수틱번호': self.indexn,
                    '매수시간': dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                }

    def SetSellCount(self, vturn, vkey, 현재가):
        _, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        _, _, 수익률 = GetUpbitPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
        if 수익률 > 최고수익률:   self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
        now_time = self._now()
        보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        self.indexb = 매수틱번호
        self.trade_info[vturn][vkey]['주문수량'] = 보유수량
        return 수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호

    def Sell(self, vturn, vkey, sell_cond, gubun=None):
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

    def LastSell(self):
        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
            self.dict_arry[self.indexn, self.hoga_sidex:self.hoga_eidex]

        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        shogainfo = shogainfo[:self.sell_hj_limit]

        for vturn in self.trade_info:
            for vkey in self.trade_info[vturn]:
                if self.trade_info[vturn][vkey]['보유중']:
                    매도금액 = 0
                    보유수량 = 미체결수량 = self.trade_info[vturn][vkey]['보유수량']
                    for 매수호가, 매수잔량 in shogainfo:
                        if 미체결수량 - 매수잔량 <= 0:
                            매도금액 += 매수호가 * 미체결수량
                            미체결수량 -= 매수잔량
                            break
                        else:
                            매도금액 += 매수호가 * 매수잔량
                            미체결수량 -= 매수잔량
                    if 미체결수량 <= 0:
                        self.trade_info[vturn][vkey]['매도가'] = np.round(매도금액 / 보유수량, 4)
                    elif 매도금액 == 0:
                        self.trade_info[vturn][vkey]['매도가'] = self.dict_arry[self.indexn, 1]
                    else:
                        self.trade_info[vturn][vkey]['매도가'] = np.round(매도금액 / (보유수량 - 미체결수량), 4)

                    self.trade_info[vturn][vkey]['주문수량'] = 보유수량
                    self.sell_cond = 0
                    self.CalculationEyun(vturn, vkey)

    def CalculationEyun(self, vturn, vkey):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        더미 = 0
        매수시간, 매도시간, 매입금액 = int(self.dict_arry[매수틱번호, 0]), self.index, 주문수량 * 매수가
        평가금액, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 주문수량 * 매도가)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True
        data = ('백테결과', self.name, 더미, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[vturn][vkey] = get_trade_info(1)
