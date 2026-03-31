
import numpy as np
from backtest.backengine_base import BackEngineBase
from utility.static import GetKiwoomPgSgSp, dt_ymdhms, GetHogaunit
# noinspection PyUnresolvedReferences
from utility.static import timedelta_sec


class BackEngineKiwoomTick(BackEngineBase):
    # noinspection PyUnusedLocal
    def Strategy(self):
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, \
            매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        if self.dict_set['시장미시구조분석']:
            self.ms_analyzer.update_data(self.code, self.arry_code[self.indexn, :])

        VI해제시간, 순매수금액 = dt_ymdhms(str(int(VI해제시간))), 초당매수금액 - 초당매도금액
        종목명, 종목코드, 데이터길이, 체결시간, 시분초 = self.name, self.code, self.tick_count, self.index, int(str(self.index)[8:])
        self.hoga_unit = 호가단위 = GetHogaunit(self.dict_kosd.get(종목코드, False), 현재가, 체결시간)

        self.shogainfo = np.array([매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5])
        self.shreminfo = np.array([매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5])
        self.bhogainfo = np.array([매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5])
        self.bhreminfo = np.array([매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5])

        self.UpdateHighLow(현재가)

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
                        price = self.arry_code[self.indexn, self.dict_findex[fname]]
                        self.arry_code[self.indexn, col_idx] = price

        if self.opti_kind == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

                    매수, 매도 = True, False
                    if not 보유중:
                        if not 관심종목: continue
                        exec(self.buystg)
                    else:
                        포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                        self.profit, self.hold_time = 수익률, 보유시간
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

                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

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

            self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
            self.curr_trade_info = self.trade_info[vturn][vkey]
            보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

            매수, 매도 = True, False
            if not 보유중:
                if not 관심종목: return
                exec(self.buystg)
            else:
                포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = self.GetHoldInfo(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)

    def UpdateMarketGubun(self):
        self.market_gubun = 1

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)

    def GetOrderCount(self, betting, 현재가, 보유중, 매수가, oc_ratio):
        return int(betting / 현재가)

    def GetBuyPrice(self, 매수금액, 주문수량):
        return int(매수금액 / 주문수량 + 0.5)

    def GetSellPrice(self, 매도금액, 주문수량):
        return int(매도금액 / 주문수량 + 0.5)

    def GetLastSellPrice(self, 매도금액, 보유수량, 미체결수량):
        if 미체결수량 <= 0:
            매도가 = int(매도금액 / 보유수량 + 0.5)
        elif 매도금액 == 0:
            매도가 = self.arry_code[self.indexn, 1]
        else:
            매도가 = int(매도금액 / (보유수량 - 미체결수량) + 0.5)
        return 매도가

    def GetProfitInfo(self, 현재가, 매수가, 보유수량):
        시가총액 = int(self.arry_code[self.indexn, self.dict_findex['시가총액']])
        평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
        return 시가총액, 평가금액, 수익금, 수익률
