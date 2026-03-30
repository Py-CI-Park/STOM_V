
from utility.static import GetIndicator
from backtest.backengine_future_tick2 import BackEngineFutureTick2


class BackEngineFutureMin2(BackEngineFutureTick2):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
            분봉시가, 분봉고가, 분봉저가, \
            분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        순매수금액 = 분당매수금액 - 분당매도금액
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:] + '00')
        호가빼기데이터 = (매도호가5 - 매도호가4, 매도호가4 - 매도호가3, 매도호가3 - 매도호가2, 매수호가2 - 매수호가3, 매수호가3 - 매수호가4, 매수호가4 - 매수호가5)
        self.hoga_unit = 호가단위 = self.GetHogaunit(호가빼기데이터)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        self.UpdateHighLow(분봉고가, 분봉저가)

        start, end = self.indexn+1-self.tick_count, self.indexn+1
        arry_indi = self.arry_code[start:end, :]
        self.mc = arry_indi[:, self.dict_findex['현재가']]
        self.mh = arry_indi[:, self.dict_findex['분봉고가']]
        self.ml = arry_indi[:, self.dict_findex['분봉저가']]
        self.mv = arry_indi[:, self.dict_findex['분당거래대금']]

        if self.opti_kind == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    self.curr_day_info = self.day_info[vturn][vkey]
                    self.curr_trade_info = self.trade_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                    self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                                매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션,
                                                분봉고가=분봉고가, 분봉저가=분봉저가)
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

                    if self.fm_list:
                        for name, _, _, fname, data_type, _, _, style, stg, col_idx in self.fm_list:
                            self.check, self.line, self.up, self.down = None, None, None, None

                            exec(stg)

                            if data_type == '선:일반':
                                if self.line is not None:
                                    self.arry_code[self.indexn, col_idx] = self.line

                            elif data_type == '선:조건':
                                if self.check is not None and self.line is not None:
                                    if self.check:
                                        self.arry_code[self.indexn, col_idx] = self.line
                                    else:
                                        pre_line = self.arry_code[self.indexn - 1, col_idx]
                                        if pre_line > 0:
                                            self.arry_code[self.indexn, col_idx] = pre_line

                            elif data_type == '범위':
                                if self.check is not None and self.up is not None and self.down is not None:
                                    self.arry_code[self.indexn, col_idx] = 1.0 if self.check else 0.0
                                    self.arry_code[self.indexn, col_idx + 1] = self.up
                                    self.arry_code[self.indexn, col_idx + 2] = self.down

                            elif data_type == '화살표:일반':
                                if self.check is not None and self.check:
                                    if fname == '현재가':
                                        price = 분봉저가 if style == 6 else 분봉고가
                                    else:
                                        price = self.arry_code[self.indexn, self.dict_findex[fname]]
                                    self.arry_code[self.indexn, col_idx] = price

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가): continue
                        if not 보유중:
                            exec(self.buystg)
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set[f'{self.market_text}매수분할시그널']:
                                exec(self.buystg)

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금): continue
                        if self.CancelSellOrder(현재가, 매수분할횟수): continue
                        if self.dict_set[f'{self.market_text}매도분할횟수'] == 1:
                            exec(self.sellstg)
                        else:
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set[f'{self.market_text}매도분할시그널']:
                                exec(self.sellstg)

        elif self.opti_kind == 3:
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

                    self.curr_day_info = self.day_info[vturn][vkey]
                    self.curr_trade_info = self.trade_info[vturn][vkey]

                    보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                        매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                        매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
                    포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                    self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey
                    self.profit, self.hold_time = 수익률, 보유시간

                    gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                                매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션,
                                                분봉고가=분봉고가, 분봉저가=분봉저가)
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

                    if self.fm_list:
                        for name, _, _, fname, data_type, _, _, style, stg, col_idx in self.fm_list:
                            self.check, self.line, self.up, self.down = None, None, None, None

                            exec(stg)

                            if data_type == '선:일반':
                                if self.line is not None:
                                    self.arry_code[self.indexn, col_idx] = self.line

                            elif data_type == '선:조건':
                                if self.check is not None and self.line is not None:
                                    if self.check:
                                        self.arry_code[self.indexn, col_idx] = self.line
                                    else:
                                        pre_line = self.arry_code[self.indexn - 1, col_idx]
                                        if pre_line > 0:
                                            self.arry_code[self.indexn, col_idx] = pre_line

                            elif data_type == '범위':
                                if self.check is not None and self.up is not None and self.down is not None:
                                    self.arry_code[self.indexn, col_idx] = 1.0 if self.check else 0.0
                                    self.arry_code[self.indexn, col_idx + 1] = self.up
                                    self.arry_code[self.indexn, col_idx + 2] = self.down

                            elif data_type == '화살표:일반':
                                if self.check is not None and self.check:
                                    if fname == '현재가':
                                        price = 분봉저가 if style == 6 else 분봉고가
                                    else:
                                        price = self.arry_code[self.indexn, self.dict_findex[fname]]
                                    self.arry_code[self.indexn, col_idx] = price

                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False
                    if '매수' in gubun:
                        if not 관심종목: continue
                        if self.CancelBuyOrder(현재가): continue
                        if not 보유중:
                            if self.back_type != '조건최적화':
                                exec(self.buystg)
                            else:
                                exec(self.dict_buystg[index_])
                        else:
                            if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set[f'{self.market_text}매수분할시그널']:
                                if self.back_type != '조건최적화':
                                    exec(self.buystg)
                                else:
                                    exec(self.dict_buystg[index_])

                    if '매도' in gubun:
                        if self.CheckSonjeol(수익률, 수익금): continue
                        if self.CancelSellOrder(현재가, 매수분할횟수): continue
                        if self.dict_set[f'{self.market_text}매도분할횟수'] == 1:
                            if self.back_type != '조건최적화':
                                exec(self.sellstg)
                            else:
                                exec(self.dict_sellstg[index_])
                        else:
                            if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set[f'{self.market_text}매도분할시그널']:
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

            self.curr_day_info = self.day_info[vturn][vkey]
            self.curr_trade_info = self.trade_info[vturn][vkey]

            보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, \
                매도호가, 매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, \
                매도분할횟수, 매수주문취소시간, 매도주문취소시간, 주문포지션 = self.curr_trade_info.values()
            포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
            self.info_for_order = 보유중, 매수가, 현재가, 저가대비고가등락율, 매수분할횟수, 매도호가1, 매수호가1, 보유수량, 매도분할횟수, vturn, vkey
            self.profit, self.hold_time = 수익률, 보유시간

            gubun = self.CheckBuyOrSell(보유중, 현재가, 매수분할횟수, 매수호가, 매도호가, 관심종목, 매수가, 주문수량, 보유수량,
                                        매수호가단위, 매수주문취소시간, 매도호가단위, 매도정정횟수, 매도주문취소시간, 주문포지션,
                                        분봉고가=분봉고가, 분봉저가=분봉저가)
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

            if self.fm_list:
                for name, _, _, fname, data_type, _, _, style, stg, col_idx in self.fm_list:
                    self.check, self.line, self.up, self.down = None, None, None, None

                    exec(stg)

                    if data_type == '선:일반':
                        if self.line is not None:
                            self.arry_code[self.indexn, col_idx] = self.line

                    elif data_type == '선:조건':
                        if self.check is not None and self.line is not None:
                            if self.check:
                                self.arry_code[self.indexn, col_idx] = self.line
                            else:
                                pre_line = self.arry_code[self.indexn - 1, col_idx]
                                if pre_line > 0:
                                    self.arry_code[self.indexn, col_idx] = pre_line

                    elif data_type == '범위':
                        if self.check is not None and self.up is not None and self.down is not None:
                            self.arry_code[self.indexn, col_idx] = 1.0 if self.check else 0.0
                            self.arry_code[self.indexn, col_idx + 1] = self.up
                            self.arry_code[self.indexn, col_idx + 2] = self.down

                    elif data_type == '화살표:일반':
                        if self.check is not None and self.check:
                            if fname == '현재가':
                                price = 분봉저가 if style == 6 else 분봉고가
                            else:
                                price = self.arry_code[self.indexn, self.dict_findex[fname]]
                            self.arry_code[self.indexn, col_idx] = price

            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False
            if '매수' in gubun:
                if not 관심종목: return
                if self.CancelBuyOrder(현재가): return
                if not 보유중:
                    exec(self.buystg)
                else:
                    if not self.CheckDividBuy(포지션, 현재가, 추가매수가, 수익률) and self.dict_set[f'{self.market_text}매수분할시그널']:
                        exec(self.buystg)

            if '매도' in gubun:
                if self.CheckSonjeol(수익률, 수익금): return
                if self.CancelSellOrder(현재가, 매수분할횟수): return
                if self.dict_set[f'{self.market_text}매도분할횟수'] == 1:
                    exec(self.sellstg)
                else:
                    if not self.CheckDividSell(포지션, 수익률, 매도분할횟수) and self.dict_set[f'{self.market_text}매도분할시그널']:
                        exec(self.sellstg)

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)
