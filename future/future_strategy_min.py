
import os
import sys
import numpy as np
from traceback import print_exc
from future_strategy_tick import FutureStrategyTick
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, now_cme, GetFutureLongPgSgSp, GetFutureShortPgSgSp, dt_ymdhms, GetIndicator


class FutureStrategyMin(FutureStrategyTick):
    # noinspection PyUnusedLocal
    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 분봉시가, 분봉고가, 분봉저가, \
            분당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, \
            매수호가2, 매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, \
            매수잔량3, 매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data

        시분초 = int(str(체결시간)[8:] + '00')
        평균값계산틱수 = self.dict_set['주식평균값계산틱수']
        저가대비고가등락율 = np.round((고가 / 저가 - 1) * 100, 2)
        순매수금액 = int((분당매수수량 - 분당매도수량) * 현재가 / 1_000_000)
        self.hoga_unit = 호가단위 = self.dict_info[종목코드]['호가단위']

        self.bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        rw = 평균값계산틱수
        new_data_tick = np.zeros(self.data_cnt, dtype=np.float64)

        if 전략연산:
            new_data = [
                체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도,
                분당매수수량, 분당매도수량,
                분봉시가, 분봉고가, 분봉저가, 분당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량,
                매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4,
                매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5,
                매도수5호가잔량합, 관심종목
            ]
            index1 = len(new_data)
            new_data_tick[:index1] = new_data

            if 종목코드 not in self.dict_data:
                self.dict_data[종목코드] = np.array([new_data_tick])
            else:
                self.dict_data[종목코드] = np.concatenate([self.dict_data[종목코드], np.array([new_data_tick])])

            self.dict_arry = self.dict_data[종목코드]

            self.tick_count = 데이터길이 = len(self.dict_data[종목코드]) + 1
            self.code, self.index, self.indexn = 종목코드, 체결시간, 데이터길이 - 1

            new_data = [
                self._이동평균(5, calc=True), self._이동평균(10, calc=True), self._이동평균(20, calc=True), self._이동평균(60, calc=True), self._이동평균(120, calc=True),
                self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True), self._최고분봉고가(rw, calc=True), self._최저분봉저가(rw, calc=True),
                self._체결강도평균(rw, calc=True), self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True), self._최고분당매수수량(rw, calc=True),
                self._최고분당매도수량(rw, calc=True), self._누적분당매수수량(rw, calc=True), self._누적분당매도수량(rw, calc=True), self._분당거래대금평균(rw, calc=True),
                self._등락율각도(rw, calc=True), self._당일거래대금각도(rw, calc=True)
            ]
            index2 = index1 + len(new_data)
            self.dict_data[종목코드][-1, index1:index2] = new_data

            high_low = self.high_low.get(종목코드)
            if high_low is None:
                self.high_low[종목코드] = [분봉고가, 분봉저가, self.indexn, self.indexn]
            else:
                if 분봉고가 > high_low[0]:
                    high_low[0] = 분봉고가
                    high_low[2] = self.indexn
                if 분봉저가 < high_low[1]:
                    high_low[1] = 분봉저가
                    high_low[3] = self.indexn

            k  = list(self.indicator.values())
            mc = self.dict_data[종목코드][:, self._fi('현재가')]
            mh = self.dict_data[종목코드][:, self._fi('분봉고가')]
            ml = self.dict_data[종목코드][:, self._fi('분봉저가')]
            mv = self.dict_data[종목코드][:, self._fi('분당거래대금')]
            indicator_list = GetIndicator(mc, mh, ml, mv, k)
            self.dict_data[종목코드][-1, index2:] = indicator_list

            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, \
                PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = indicator_list

            if self.dict_condition:
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    try:
                        exec(v)
                    except:
                        print_exc()
                        self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - 경과틱수 연산오류')))

            if 데이터길이 >= 평균값계산틱수:
                if 종목코드 in self.dict_jg:
                    if 종목코드 not in self.dict_buy_num:
                        self.dict_buy_num[종목코드] = self.indexn
                    # ['종목명', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                    _, 포지션, 매입가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = self.dict_jg[종목코드].values()
                    평가금액 = 매입금액 + (현재가 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                    if 포지션 == 'LONG':
                        _, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                    else:
                        _, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                    if 종목코드 not in self.dict_profit:
                        self.dict_profit[종목코드] = [수익률, 수익률]
                    else:
                        if 수익률 > self.dict_profit[종목코드][0]:
                            self.dict_profit[종목코드][0] = 수익률
                        elif 수익률 < self.dict_profit[종목코드][1]:
                            self.dict_profit[종목코드][1] = 수익률
                    최고수익률, 최저수익률 = self.dict_profit[종목코드]
                    보유시간 = int((now_cme() - dt_ymdhms(매수시간)).total_seconds() / 60)
                    매수틱번호 = self.dict_buy_num[종목코드]
                else:
                    포지션, 매수틱번호, 수익금, 수익률, 매입가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = None, 0, 0, 0, 0, 0, 0, 0, now_cme(), 0, 0, 0
                self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호
    
                BBT  = not self.dict_set['주식매수금지시간'] or not (self.dict_set['주식매수금지시작시간'] < 시분초 < self.dict_set['주식매수금지종료시간'])
                BLK  = not self.dict_set['주식매수금지블랙리스트'] or 종목코드 not in self.dict_set['해선블랙리스트']
                NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
                NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
                NISL = 종목코드 not in self.dict_signal['SELL_LONG']
                NIBS = 종목코드 not in self.dict_signal['BUY_SHORT']
                A    = NIBL and 포지션 is None
                B    = NISS and 포지션 is None
                C    = self.dict_set['주식매수분할시그널']
                D    = NIBL and 포지션 == 'LONG' and 분할매수횟수 < self.dict_set['주식매수분할횟수']
                E    = NISS and 포지션 == 'SHORT' and 분할매수횟수 < self.dict_set['주식매수분할횟수']
                F    = NIBL and self.dict_set['주식매도취소매수시그널'] and not NISL
                G    = NISS and self.dict_set['주식매도취소매수시그널'] and not NIBS
    
                if BBT and BLK and (A or B or (C and D) or (C and E) or D or E or F or G):
                    매수수량 = 0
                    if not (F or G):
                        매수수량 = self.SetBuyCount(분할매수횟수, 저가대비고가등락율, 순매수금액, 당일거래대금)
    
                    if A or B or (C and (D or E)) or F or G:
                        BUY_LONG, SELL_SHORT = True, True
                        if self.buystrategy is not None:
                            try:
                                exec(self.buystrategy)
                            except:
                                print_exc()
                                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - BuyStrategy')))
                    elif D or E:
                        BUY_LONG, SELL_SHORT = False, False
                        분할매수기준수익률 = np.round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['주식매수분할고정수익률'] else 수익률
                        if D:
                            if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                                BUY_LONG   = True
                            elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                                BUY_LONG   = True
                        elif E:
                            if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                                SELL_SHORT = True
                            elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                                SELL_SHORT = True
    
                        if BUY_LONG or SELL_SHORT:
                            self.Buy(종목코드, 종목명, BUY_LONG, 현재가, 매도호가1, 매수호가1, 매수수량, 데이터길이)
    
                SBT  = not self.dict_set['주식매도금지시간'] or not (self.dict_set['주식매도금지시작시간'] < 시분초 < self.dict_set['주식매도금지종료시간'])
                SCC  = self.dict_set['주식매수분할횟수'] == 1 or not self.dict_set['주식매도금지매수횟수'] or 분할매수횟수 > self.dict_set['주식매도금지매수횟수값']
                NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
                NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
                GJCS = 수익금 / self.dict_info[종목코드]['위탁증거금'] * 100 <= -30
    
                A    = NIBL and NISL and SCC and 포지션 == 'LONG' and self.dict_set['주식매도분할횟수'] == 1
                B    = NISS and NIBS and SCC and 포지션 == 'SHORT' and self.dict_set['주식매도분할횟수'] == 1
                C    = self.dict_set['주식매도분할시그널']
                D    = NIBL and NISL and SCC and 포지션 == 'LONG' and 분할매도횟수 < self.dict_set['주식매도분할횟수']
                E    = NISS and NIBS and SCC and 포지션 == 'SHORT' and 분할매도횟수 < self.dict_set['주식매도분할횟수']
                F    = NISL and self.dict_set['주식매수취소매도시그널'] and not NIBL
                G    = NIBS and self.dict_set['주식매수취소매도시그널'] and not NISS
                H    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
                J    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
                K    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']
                L    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']
                M    = NIBL and NISL and 포지션 == 'LONG' and GJCS
                N    = NISS and NIBS and 포지션 == 'SHORT' and GJCS
    
                if SBT and (A or B or (C and D) or (C and E) or D or E or F or G or H or J or K or L or M or N):
                    SELL_LONG, BUY_SHORT = False, False
                    매도수량 = 0
                    강제청산 = H or J or K or L or M or N
    
                    if A or B or H or J or K or L or M or N:
                        매도수량 = 보유수량
                    elif not (F or G):
                        매도수량 = self.SetSellCount(분할매도횟수, 보유수량, 저가대비고가등락율, 순매수금액, 당일거래대금)
    
                    if A or B or (C and (D or E)) or F or G:
                        if self.sellstrategy is not None:
                            try:
                                exec(self.sellstrategy)
                            except:
                                print_exc()
                                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - SellStrategy')))
                    elif D or E or H or J or K or L or M or N:
                        if H or K or M:
                            SELL_LONG = True
                        elif J or L or N:
                            BUY_SHORT = True
                        elif D:
                            if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                                SELL_LONG = True
                            elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                                SELL_LONG = True
                        elif E:
                            if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                                BUY_SHORT = True
                            elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                                BUY_SHORT = True
    
                        if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):
                            self.Sell(종목코드, 종목명, SELL_LONG, 현재가, 매도호가1, 매수호가1, 매도수량, 강제청산)

            if 관심종목:
                # ['종목명', 'per', 'hlp', 'sm', 'sma', 'dm', 'ch', 'cha', 'chh']
                self.dict_gj[종목코드] = {
                    '종목명': 종목명,
                    'per': 등락율,
                    'hlp': 고저평균대비등락율,
                    'sm': 분당거래대금,
                    'sma': self._분당거래대금평균(rw),
                    'dm': 당일거래대금,
                    'ch': 체결강도,
                    'cha': self._체결강도평균(rw),
                    'chh': self._최고체결강도(rw)
                }
        else:
            데이터길이 = len(self.dict_data[종목코드])

        if self.chart_code == 종목코드 and 데이터길이 >= 평균값계산틱수:
            if not 전략연산:
                new_data = [
                    체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도,
                    분당매수수량, 분당매도수량,
                    분봉시가, 분봉고가, 분봉저가, 분당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량,
                    매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
                    매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5,
                    매도수5호가잔량합, 관심종목
                ]
                index1 = len(new_data)
                new_data_tick[:index1] = new_data
                self.dict_arry = np.concatenate([self.dict_data[종목코드], np.array([new_data_tick])])

                new_data = [
                    self._이동평균(5, calc=True), self._이동평균(10, calc=True), self._이동평균(20, calc=True), self._이동평균(60, calc=True),
                    self._이동평균(120, calc=True), self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True), self._최고분봉고가(rw, calc=True),
                    self._최저분봉저가(rw, calc=True), self._체결강도평균(rw, calc=True), self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True),
                    self._최고분당매수수량(rw, calc=True), self._최고분당매도수량(rw, calc=True), self._누적분당매수수량(rw, calc=True), self._누적분당매도수량(rw, calc=True),
                    self._분당거래대금평균(rw, calc=True), self._등락율각도(rw, calc=True), self._당일거래대금각도(rw, calc=True)
                ]
                index2 = index1 + len(new_data)
                self.dict_arry[-1, index1:index2] = new_data

                k = list(self.indicator.values())
                mc = self.dict_arry[:, self._fi('현재가')]
                mh = self.dict_arry[:, self._fi('분봉고가')]
                ml = self.dict_arry[:, self._fi('분봉저가')]
                mv = self.dict_arry[:, self._fi('분당거래대금')]
                self.dict_arry[-1, index2:] = GetIndicator(mc, mh, ml, mv, k)

            self.mgzservQ.put(('window', (ui_num['실시간차트'], 종목명, self.dict_data[종목코드] if 전략연산 else self.dict_arry)))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
