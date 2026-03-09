
from backtest.backengine_kiwoom_tick import BackEngineKiwoomTick
from utility.static import dt_ymdhms, GetIndicator, GetHogaunit, GetUvilower5


class BackEngineKiwoomMin(BackEngineKiwoomTick):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
            거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위, \
            분봉시가, 분봉고가, 분봉저가, \
            분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        VI해제시간, VI아래5호가 = dt_ymdhms(str(int(VI해제시간))), GetUvilower5(VI가격, VI호가단위, self.index)
        순매수금액 = 분당매수금액 - 분당매도금액
        수익률 = 매수금액 = 매수가격 = 매수수량 = 매도수량 = 0
        강제청산 = False
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:] + '00')
        self.hoga_unit = 호가단위 = GetHogaunit(self.dict_kosd.get(종목코드, False), 현재가, 체결시간)

        self.shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        self.UpdateHighLow(분봉고가, 분봉저가)

        start, end = self.indexn+1-self.tick_count, self.indexn+1
        arry_indi = self.arry_code[start:end, :]
        self.mc = arry_indi[:, self.dict_findex['현재가']]
        self.mh = arry_indi[:, self.dict_findex['분봉고가']]
        self.ml = arry_indi[:, self.dict_findex['분봉저가']]
        self.mv = arry_indi[:, self.dict_findex['분당거래대금']]

        if self.opti_turn == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

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
                    if not 보유중:
                        if not 관심종목: continue
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

                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

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
                    if not 보유중:
                        if not 관심종목: continue
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

            self.curr_trade_info = self.trade_info[vturn][vkey]
            self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
            보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

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
            if not 보유중:
                if not 관심종목: return
                exec(self.buystg)
            else:
                포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)
