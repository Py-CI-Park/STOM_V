
import numpy as np
from utility.static import GetIndicator
from backtester.backengine_binance_tick import BackEngineBinanceTick


class BackEngineBinanceMin(BackEngineBinanceTick):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 분봉시가, 분봉고가, 분봉저가, 분당거래대금, \
            고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, \
            매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, \
            매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목 = self.dict_arry[self.indexn, 1:self.data_cnt]

        호가단위 = (매도호가5 - 매도호가4, 매도호가4 - 매도호가3, 매도호가3 - 매도호가2, 매수호가2 - 매수호가3, 매수호가3 - 매수호가4, 매수호가4 - 매수호가5)
        self.hoga_unit = 호가단위 = min(x for x in 호가단위 if x > 0)
        저가대비고가등락율, 순매수금액 = np.round((고가 / 저가 - 1) * 100, 2), int((분당매수수량 - 분당매도수량) * 현재가 / 1_000_000)
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:] + '00')

        self.bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

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

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                        exec(self.buystg)
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
                        포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
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

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
                        포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
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

            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False
            if not self.trade_info[vturn][vkey]['보유중']:
                if not 관심종목: return
                self.SetBuyCount(vturn, vkey, 현재가, 저가대비고가등락율, 순매수금액, 당일거래대금)
                exec(self.buystg)
            else:
                수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가)
                포지션 = 'LONG' if self.trade_info[vturn][vkey]['보유중'] == 1 else 'SHORT'
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)
