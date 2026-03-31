
import numpy as np
from traceback import format_exc
from utility.setting_base import ui_num
from trade.upbit.upbit_strategy_tick import UpbitStrategyTick
from utility.static import now, now_utc, GetUpbitHogaunit, GetUpbitPgSgSp, dt_ymdhms, GetIndicator


class UpbitStrategyMin(UpbitStrategyTick):
    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)

    # noinspection PyUnusedLocal
    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
            분봉시가, 분봉고가, 분봉저가, \
            분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 틱수신시간, 전략연산 = data

        시분초 = int(str(체결시간)[8:] + '00')
        rw = 평균값계산틱수 = self.dict_set['코인평균값계산틱수']
        순매수금액 = 분당매수금액 - 분당매도금액
        self.hoga_unit = 호가단위 = GetUpbitHogaunit(현재가)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        if 전략연산:
            new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
            new_data_tick[:self.base_cnt] = data[:self.base_cnt]

            pre_data = self.dict_data.get(종목코드)
            if pre_data is not None:
                self.dict_data[종목코드] = np.concatenate([pre_data, [new_data_tick]])
            else:
                self.dict_data[종목코드] = np.array([new_data_tick])

            self.arry_code = self.dict_data[종목코드]
            self.tick_count = 데이터길이 = len(self.arry_code)
            self.code, self.index, self.indexn = 종목코드, 체결시간, 데이터길이 - 1

            if 데이터길이 >= 평균값계산틱수:
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self.GetParameterArea(rw)

            indicator_list = GetIndicator(
                self.arry_code[:, self.dict_findex['현재가']],
                self.arry_code[:, self.dict_findex['분봉고가']],
                self.arry_code[:, self.dict_findex['분봉저가']],
                self.arry_code[:, self.dict_findex['분당거래대금']],
                self.indi_settings
            )
            self.arry_code[-1, self.area_cnt:self.data_cnt] = indicator_list

            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, \
                PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = indicator_list

            high_low = self.high_low.get(종목코드)
            if high_low:
                if 분봉고가 >= high_low[0]:
                    high_low[0] = 분봉고가
                    high_low[1] = self.indexn
                if 분봉저가 <= high_low[2]:
                    high_low[2] = 분봉저가
                    high_low[3] = self.indexn
            else:
                self.high_low[종목코드] = [분봉고가, self.indexn, 분봉저가, self.indexn]

            if self.dict_condition:
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    try:
                        exec(v)
                    except:
                        self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 경과틱수 연산오류'))

            if 데이터길이 >= 평균값계산틱수 and self.fm_list:
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

            if 데이터길이 >= 평균값계산틱수:
                jg_data = self.dict_jg.get(종목코드)
                if jg_data:
                    if 종목코드 not in self.dict_buy_num:
                        self.dict_buy_num[종목코드] = self.indexn
                    # ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                    _, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = jg_data.values()
                    _, 수익금, 수익률 = GetUpbitPgSgSp(매입금액, 보유수량 * 현재가)
                    profit_data = self.dict_profit.get(종목코드)
                    if profit_data:
                        if 수익률 > profit_data[0]:
                            profit_data[0] = 수익률
                        elif 수익률 < profit_data[1]:
                            profit_data[1] = 수익률
                        최고수익률, 최저수익률 = profit_data
                    else:
                        self.dict_profit[종목코드] = [수익률, 수익률]
                        최고수익률 = 최저수익률 = 수익률
                    보유시간 = int((now_utc() - dt_ymdhms(매수시간)).total_seconds() / 60)
                    매수틱번호 = self.dict_buy_num[종목코드]
                else:
                    매수틱번호, 수익금, 수익률, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = 0, 0, 0, 0, 0, 0, 0, now_utc(), 0, 0, 0

                self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

                BBT = not self.dict_set['코인매수금지시간'] or not (self.dict_set['코인매수금지시작시간'] < 시분초 < self.dict_set['코인매수금지종료시간'])
                BLK = not self.dict_set['코인매수금지블랙리스트'] or 종목코드 not in self.dict_set['코인블랙리스트']
                C20 = not self.dict_set['코인매수금지200원이하'] or 현재가 > 200
                NIB = 종목코드 not in self.dict_signal['매수']
                NIS = 종목코드 not in self.dict_signal['매도']

                A = 관심종목 and NIB and 매수가 == 0
                B = self.dict_set['코인매수분할시그널']
                C = NIB and 매수가 != 0 and 분할매수횟수 < self.dict_set['코인매수분할횟수']
                D = NIB and self.dict_set['코인매도취소매수시그널'] and not NIS

                if BBT and BLK and C20 and (A or (B and C) or C or D):
                    self.info_for_signal = D, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    if A or (B and C) or D:
                        매수 = True
                        if self.buystrategy is not None:
                            try:
                                exec(self.buystrategy)
                            except:
                                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매수전략'))
                    elif C:
                        매수 = False
                        분할매수기준수익률 = round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set[
                            '코인매수분할고정수익률'] else 수익률
                        if self.dict_set['코인매수분할하방'] and 분할매수기준수익률 < -self.dict_set['코인매수분할하방수익률']:
                            매수 = True
                        elif self.dict_set['코인매수분할상방'] and 분할매수기준수익률 > self.dict_set['코인매수분할상방수익률']:
                            매수 = True

                        if 매수:
                            self.Buy()

                SBT = not self.dict_set['코인매도금지시간'] or not (self.dict_set['코인매도금지시작시간'] < 시분초 < self.dict_set['코인매도금지종료시간'])
                SCC = self.dict_set['코인매수분할횟수'] == 1 or not self.dict_set['코인매도금지매수횟수'] or 분할매수횟수 > self.dict_set[
                    '코인매도금지매수횟수값']
                NIB = 종목코드 not in self.dict_signal['매수']

                A = NIB and NIS and SCC and 매수가 != 0 and self.dict_set['코인매도분할횟수'] == 1
                B = self.dict_set['코인매도분할시그널']
                C = NIB and NIS and SCC and 매수가 != 0 and 분할매도횟수 < self.dict_set['코인매도분할횟수']
                D = NIS and self.dict_set['코인매수취소매도시그널'] and not NIB
                E = NIB and NIS and 매수가 != 0 and self.dict_set['코인매도익절수익률청산'] and 수익률 > self.dict_set['코인매도익절수익률']
                F = NIB and NIS and 매수가 != 0 and self.dict_set['코인매도익절수익금청산'] and 수익금 > self.dict_set['코인매도익절수익금']
                G = NIB and NIS and 매수가 != 0 and self.dict_set['코인매도손절수익률청산'] and 수익률 < -self.dict_set['코인매도손절수익률']
                H = NIB and NIS and 매수가 != 0 and self.dict_set['코인매도손절수익금청산'] and 수익금 < -self.dict_set['코인매도손절수익금']

                if SBT and (A or (B and C) or C or D or E or F or G or H):
                    강제청산 = E or F or G or H
                    전량매도 = A or 강제청산
                    self.info_for_signal = D, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    매도 = False
                    if A or (B and C) or D:
                        if self.sellstrategy is not None:
                            try:
                                exec(self.sellstrategy)
                            except:
                                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매도전략'))

                    elif C or 강제청산:
                        if C:
                            if self.dict_set['코인매도분할하방'] and 수익률 < -self.dict_set['코인매도분할하방수익률'] * (분할매도횟수 + 1):
                                매도 = True
                            elif self.dict_set['코인매도분할상방'] and 수익률 > self.dict_set['코인매도분할상방수익률'] * (분할매도횟수 + 1):
                                매도 = True
                        elif 강제청산:
                            매도 = True

                        if 매도:
                            self.Sell()

        else:
            pre_data = self.dict_data.get(종목코드)
            if pre_data is None:
                pre_data = np.empty((0, self.data_cnt + self.fm_tcnt), dtype=np.float64)
            self.tick_count = 데이터길이 = len(pre_data) + 1
            self.indexn = 데이터길이 - 1

        if 관심종목:
            # ['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']
            self.dict_gj[종목코드] = {
                '종목명': 종목코드,
                'per': 등락율,
                'hlp': 고저평균대비등락율,
                'lhp': 저가대비고가등락율,
                'ch': 체결강도,
                'tm': 분당거래대금,
                'dm': 당일거래대금,
                'bm': 당일매수금액,
                'sm': 당일매도금액
            }

        if self.chart_code == 종목코드 and 데이터길이 >= 평균값계산틱수:
            if not 전략연산:
                new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
                new_data_tick[:self.base_cnt] = data[:self.base_cnt]
                self.arry_code = np.concatenate([pre_data, [new_data_tick]])
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self.GetParameterArea(rw)
                self.arry_code[-1, self.area_cnt:self.data_cnt] = GetIndicator(
                    self.arry_code[:, self.dict_findex['현재가']],
                    self.arry_code[:, self.dict_findex['분봉고가']],
                    self.arry_code[:, self.dict_findex['분봉저가']],
                    self.arry_code[:, self.dict_findex['분당거래대금']],
                    self.indi_settings
                )
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

            self.windowQ.put((ui_num['실시간차트'], 종목코드, self.arry_code))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.windowQ.put((ui_num['타임로그'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))
