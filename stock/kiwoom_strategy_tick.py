
import os
import sys
import math
import time
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DB_STRATEGY, DICT_SET, ui_num, dict_order_ratio, DB_STOCK_TICK, DB_STOCK_MIN, indicator, \
    list_stock_tick, list_stock_min
# noinspection PyUnresolvedReferences
from utility.static import now, timedelta_sec, GetKiwoomPgSgSp, GetHogaunit, get_buy_indi_stg, \
    str_ymdhms, dt_ymdhms, get_logger, get_angle_cf, get_ema_list, dt_ymdhm


class KiwoomStrategyTick:
    def __init__(self, gubun, qlist):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs
                0            1             2            3
        """
        self.gubun            = gubun
        self.mgzservQ         = qlist[0]
        self.straderQ         = qlist[2]
        self.sstgQs           = qlist[3]
        self.sstgQ            = qlist[3][self.gubun]
        self.dict_set         = DICT_SET
        self.logger           = get_logger(self.__class__.__name__)

        self.code             = None
        self.name             = None
        self.buystrategy      = None
        self.sellstrategy     = None
        self.chart_code       = None
        self.arry_code        = None
        self.info_for_signal  = None

        self.vars             = {}
        self.dict_data        = {}
        self.dict_signal_num  = {}
        self.dict_buy_num     = {}
        self.dict_condition   = {}
        self.dict_cond_indexn = {}
        self.dict_findex      = {}
        self.shogainfo        = {}
        self.bhogainfo        = {}
        self.dict_profit      = {}
        self.high_low         = {}
        self.dict_gj          = {}
        self.dict_jg          = {}
        self.indicator        = indicator
        self.indi_settings    = []
        self.dict_signal      = {
            '매수': [],
            '매도': []
        }

        self.tuple_kosd       = ()
        self.tick_count       = 0
        self.index            = 0
        self.indexn           = 0
        self.indexb           = 0
        self.jgrv_count       = 0
        self.int_tujagm       = 0
        self.market_gubun     = 1
        self.ma_round_unit    = 3
        self.hoga_unit        = 0
        self.profit           = 0
        self.hold_time        = 0

        self.is_tick          = self.dict_set['주식타임프레임']
        self.avg_list         = [self.dict_set['주식평균값계산틱수']]
        self.sma_list         = get_ema_list(self.is_tick)
        self.data_cnt         = len(list_stock_tick) if self.is_tick else len(list_stock_min)
        self.dict_findex      = {name: i for i, name in enumerate(list_stock_tick if self.is_tick else list_stock_min)}
        self.vitime_cnt       = self.dict_findex['VI해제시간']
        self.base_cnt         = self.dict_findex['관심종목'] + 1
        self.area_cnt         = self.dict_findex['전일비각도' if self.market_gubun == 1 else '당일거래대금각도'] + 1
        self.angle_pct_cf     = get_angle_cf(self.market_gubun, self.is_tick, 0)
        self.angle_dtm_cf     = get_angle_cf(self.market_gubun, self.is_tick, 1)

        if self.gubun == 0 and self.dict_set['전략연산프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.UpdateStringategy()
        self.Mainloop()

    def UpdateStringategy(self):
        con  = sqlite3.connect(DB_STRATEGY)
        dfb  = pd.read_sql('SELECT * FROM stockbuy', con).set_index('index')
        dfs  = pd.read_sql('SELECT * FROM stocksell', con).set_index('index')
        dfob = pd.read_sql('SELECT * FROM stockoptibuy', con).set_index('index')
        dfos = pd.read_sql('SELECT * FROM stockoptisell', con).set_index('index')
        con.close()

        buytxt = ''
        if self.dict_set['주식매수전략'] in dfb.index:
            buytxt = dfb['전략코드'][self.dict_set['주식매수전략']]
        elif self.dict_set['주식매수전략'] in dfob.index:
            buytxt = dfob['전략코드'][self.dict_set['주식매수전략']]
            vars_text = dfob['변수값'][self.dict_set['주식매수전략']]
            if vars_text != '':
                vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                self.vars = {i: var for i, var in enumerate(vars_list)}

        self.SetBuyStg(buytxt)

        if self.dict_set['주식매도전략'] in dfs.index:
            self.sellstrategy = compile(dfs['전략코드'][self.dict_set['주식매도전략']], '<string>', 'exec')
        elif self.dict_set['주식매도전략'] in dfos.index:
            self.sellstrategy = compile(dfos['전략코드'][self.dict_set['주식매도전략']], '<string>', 'exec')

        if self.dict_set['주식경과틱수설정']:
            def compile_condition(x):
                return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')
            text_list  = self.dict_set['주식경과틱수설정'].split(';')
            half_cnt   = int(len(text_list) / 2)
            key_list   = text_list[:half_cnt]
            value_text_list = text_list[half_cnt:]
            value_comp_list = [compile_condition(x) for x in value_text_list]
            self.dict_condition = dict(zip(key_list, value_comp_list))

        self.UpdateStraegyGlobals()

    def SetBuyStg(self, buytxt):
        self.buystrategy, indistg = get_buy_indi_stg(buytxt)
        if indistg is not None:
            try:
                exec(indistg)
            except:
                pass
            else:
                self.logger.info(self.indicator)
        self.indi_settings = list(self.indicator.values())

    def Mainloop(self):
        if self.gubun == 7:
            self.mgzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 전략연산 시작')))
            self.logger.info('전략연산 시작 완료')
        while True:
            data = self.sstgQ.get()
            if data.__class__ == list:
                self.Strategy(data)
            elif data.__class__ == tuple:
                self.UpdateTuple(data)
            elif data.__class__ == str:
                self.UpdateString(data)

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.dict_jg = data
            self.jgrv_count += 1
            if self.jgrv_count == 2:
                self.jgrv_count = 0
                self.PutGsjmAndDeleteHilo()
        elif gubun == '관심목록':
            self.dict_gj = {k: v for k, v in self.dict_gj.items() if k in data}
        elif gubun in ('매수완료', '매수취소'):
            if data in self.dict_signal['매수']:
                self.dict_signal['매수'].remove(data)
            if gubun == '매수완료':
                self.dict_buy_num[data] = self.dict_signal_num.get(data, len(self.dict_data[data]) - 1)
        elif gubun in ('매도완료', '매도취소'):
            if data in self.dict_signal['매도']:
                self.dict_signal['매도'].remove(data)
        elif gubun == '매수주문':
            if data not in self.dict_signal['매수']:
                self.dict_signal['매수'].append(data)
        elif gubun == '매도주문':
            if data not in self.dict_signal['매도']:
                self.dict_signal['매도'].append(data)
        elif gubun == '매수전략':
            self.SetBuyStg(data)
        elif gubun == '매도전략':
            self.sellstrategy = compile(data, '<string>', 'exec')
        elif gubun == '종목당투자금':
            self.int_tujagm = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
            self.UpdateStringategy()
        elif gubun == '코스닥목록':
            self.tuple_kosd = data
        elif gubun == '데이터저장':
            self.SaveData(data)

    def UpdateString(self, data):
        if data == '매수전략중지':
            self.buystrategy = None
            self.mgzservQ.put(('tele', '주식 매수전략 중지 완료'))
        elif data == '매도전략중지':
            self.sellstrategy = None
            self.mgzservQ.put(('tele', '주식 매도전략 중지 완료'))
        elif data == '프로파일링결과':
            if self.gubun == 0:
                self.pr.print_stats(sort='cumulative')
        elif data == '프로세스종료':
            time.sleep(5)
            self.mgzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 전략연산 종료')))

    # noinspection PyUnusedLocal
    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, \
            매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data

        시분초 = int(str(체결시간)[8:])
        rw = 평균값계산틱수 = self.dict_set['주식평균값계산틱수']
        순매수금액 = 초당매수금액 - 초당매도금액
        self.hoga_unit = 호가단위 = GetHogaunit(종목코드 in self.tuple_kosd, 현재가, 체결시간)

        shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.shogainfo = shogainfo[:self.dict_set['주식매수시장가잔량범위']]
        self.bhogainfo = bhogainfo[:self.dict_set['주식매도시장가잔량범위']]

        new_data_tick = np.zeros(self.data_cnt, dtype=np.float64)
        new_data = data[:self.base_cnt]
        new_data[self.vitime_cnt] = int(str_ymdhms(VI해제시간))
        new_data_tick[:self.base_cnt] = new_data

        pre_data = self.dict_data.get(종목코드)
        if pre_data is not None:
            self.dict_data[종목코드] = np.concatenate([pre_data, np.array([new_data_tick])])
        else:
            self.dict_data[종목코드] = np.array([new_data_tick])

        self.arry_code = self.dict_data[종목코드]
        self.tick_count = 데이터길이 = len(self.arry_code)
        self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

        if 데이터길이 >= 평균값계산틱수: self.arry_code[-1, self.base_cnt:] = self.GetParameterArea(rw)

        high_low = self.high_low.get(종목코드)
        if high_low:
            if 현재가 >= high_low[0]:
                high_low[0] = 현재가
                high_low[1] = self.indexn
            if 현재가 <= high_low[2]:
                high_low[2] = 현재가
                high_low[3] = self.indexn
        else:
            self.high_low[종목코드] = [현재가, self.indexn, 현재가, self.indexn]

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                try:
                    exec(v)
                except:
                    print_exc()
                    self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - 경과틱수 연산오류')))

        if 데이터길이 >= 평균값계산틱수 and not (매수잔량5 == 0 and 매도잔량5 == 0):
            jg_data = self.dict_jg.get(종목코드)
            if jg_data:
                if 종목코드 not in self.dict_buy_num:
                    self.dict_buy_num[종목코드] = self.indexn
                # ['종목명', '매수가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                _, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = jg_data.values()
                _, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 보유수량 * 현재가)
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
                보유시간 = (now() - dt_ymdhms(매수시간)).total_seconds()
                매수틱번호 = self.dict_buy_num[종목코드]
            else:
                매수틱번호, 수익금, 수익률, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = 0, 0, 0, 0, 0, 0, 0, now(), 0, 0, 0

            self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

            BBT = not self.dict_set['주식매수금지시간'] or not (self.dict_set['주식매수금지시작시간'] < 시분초 < self.dict_set['주식매수금지종료시간'])
            BLK = not self.dict_set['주식매수금지블랙리스트'] or 종목코드 not in self.dict_set['주식블랙리스트']
            NIB = 종목코드 not in self.dict_signal['매수']
            NIS = 종목코드 not in self.dict_signal['매도']

            A = 관심종목 and NIB and 매수가 == 0
            B = self.dict_set['주식매수분할시그널']
            C = NIB and 매수가 != 0 and 분할매수횟수 < self.dict_set['주식매수분할횟수']
            D = NIB and self.dict_set['주식매도취소매수시그널'] and not NIS

            if BBT and BLK and (A or (B and C) or C or D):
                self.info_for_signal = D, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                if A or (B and C) or D:
                    매수 = True
                    if self.buystrategy is not None:
                        try:
                            exec(self.buystrategy)
                        except:
                            print_exc()
                            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - BuyStrategy')))
                elif C:
                    매수 = False
                    분할매수기준수익률 = np.round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['주식매수분할고정수익률'] else 수익률
                    if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                        매수 = True
                    elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                        매수 = True

                    if 매수:
                        self.Buy()

            SBT = not self.dict_set['주식매도금지시간'] or not (self.dict_set['주식매도금지시작시간'] < 시분초 < self.dict_set['주식매도금지종료시간'])
            SCC = self.dict_set['주식매수분할횟수'] == 1 or not self.dict_set['주식매도금지매수횟수'] or 분할매수횟수 > self.dict_set['주식매도금지매수횟수값']
            NIB = 종목코드 not in self.dict_signal['매수']

            A = NIB and NIS and SCC and 매수가 != 0 and self.dict_set['주식매도분할횟수'] == 1
            B = self.dict_set['주식매도분할시그널']
            C = NIB and NIS and SCC and 매수가 != 0 and 분할매도횟수 < self.dict_set['주식매도분할횟수']
            D = NIS and self.dict_set['주식매수취소매도시그널'] and not NIB
            E = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
            F = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']

            if SBT and (A or (B and C) or C or D or E or F):
                강제청산 = E or F
                전량매도 = A or 강제청산
                self.info_for_signal = D, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                매도 = False
                if A or (B and C) or D:
                    if self.sellstrategy is not None:
                        try:
                            exec(self.sellstrategy)
                        except:
                            print_exc()
                            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - SellStrategy')))
                elif C or 강제청산:
                    if C:
                        if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                            매도 = True
                        elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                            매도 = True
                    else:
                        매도 = True

                    if 매도:
                        self.Sell()

        if 관심종목:
            # ['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']
            self.dict_gj[종목코드] = {
                '종목명': 종목명,
                'per': 등락율,
                'hlp': 고저평균대비등락율,
                'lhp': 저가대비고가등락율,
                'ch': 체결강도,
                'tm': 초당거래대금,
                'dm': 당일거래대금,
                'bm': 당일매수금액,
                'sm': 당일매도금액
            }

        if self.chart_code == 종목코드 and 데이터길이 >= 평균값계산틱수:
            self.mgzservQ.put(('window', (ui_num['실시간차트'], 종목명, self.arry_code[-1800:, :])))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))

    def GetParameterArea(self, rw):
        if self.is_tick:
            return [
                self._이동평균(self.sma_list[0], calc=True), self._이동평균(self.sma_list[1], calc=True),
                self._이동평균(self.sma_list[2], calc=True), self._이동평균(self.sma_list[3], calc=True),
                self._이동평균(self.sma_list[4], calc=True), self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True),
                self._체결강도평균(rw, calc=True), self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True),
                self._최고초당매수수량(rw, calc=True), self._최고초당매도수량(rw, calc=True), self._누적초당매수수량(rw, calc=True),
                self._누적초당매도수량(rw, calc=True), self._초당거래대금평균(rw, calc=True), self._등락율각도(rw, calc=True),
                self._당일거래대금각도(rw, calc=True), self._전일비각도(rw, calc=True)
            ]
        else:
            return [
                self._이동평균(self.sma_list[0], calc=True), self._이동평균(self.sma_list[1], calc=True),
                self._이동평균(self.sma_list[2], calc=True), self._이동평균(self.sma_list[3], calc=True),
                self._이동평균(self.sma_list[4], calc=True), self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True),
                self._최고분봉고가(rw, calc=True), self._최저분봉저가(rw, calc=True), self._체결강도평균(rw, calc=True),
                self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True), self._최고분당매수수량(rw, calc=True),
                self._최고분당매도수량(rw, calc=True), self._누적분당매수수량(rw, calc=True), self._누적분당매도수량(rw, calc=True),
                self._분당거래대금평균(rw, calc=True), self._등락율각도(rw, calc=True), self._당일거래대금각도(rw, calc=True),
                self._전일비각도(rw, calc=True)
            ]

    def Buy(self):
        취소시그널, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1 = self.info_for_signal
        if 취소시그널:
            매수수량 = 0
        else:
            매수수량 = self.GetBuyCount(분할매수횟수, 매수가, 현재가, 저가대비고가등락율)

        if '지정가' in self.dict_set['주식매수주문구분']:
            기준가격 = 현재가
            if self.dict_set['주식매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.dict_signal['매수'].append(self.code)
            self.dict_signal_num[self.code] = self.indexn
            self.straderQ.put(('매수', self.code, self.name, 기준가격, 매수수량, now(), False))
        else:
            매수금액 = 0
            미체결수량 = 매수수량
            for 매도호가, 매도잔량 in self.shogainfo:
                if 미체결수량 - 매도잔량 <= 0:
                    매수금액 += 매도호가 * 미체결수량
                    미체결수량 -= 매도잔량
                    break
                else:
                    매수금액 += 매도호가 * 매도잔량
                    미체결수량 -= 매도잔량
            if 미체결수량 <= 0:
                예상체결가 = int(np.round(매수금액 / 매수수량)) if 매수수량 != 0 else 0
                self.dict_signal['매수'].append(self.code)
                self.dict_signal_num[self.code] = self.indexn
                self.straderQ.put(('매수', self.code, self.name, 예상체결가, 매수수량, now(), False))

    def GetBuyCount(self, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율):
        if self.dict_set['주식비중조절'][0] == 0:
            betting = self.int_tujagm
        else:
            if self.dict_set['주식비중조절'][0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.dict_set['주식비중조절'][0] == 2:
                비중조절기준 = self._거래대금평균대비비율(30)
            elif self.dict_set['주식비중조절'][0] == 3:
                비중조절기준 = self._등락율각도(30)
            else:
                비중조절기준 = self._당일거래대금각도(30)

            if 비중조절기준 < self.dict_set['주식비중조절'][1]:
                betting = self.int_tujagm * self.dict_set['주식비중조절'][5]
            elif 비중조절기준 < self.dict_set['주식비중조절'][2]:
                betting = self.int_tujagm * self.dict_set['주식비중조절'][6]
            elif 비중조절기준 < self.dict_set['주식비중조절'][3]:
                betting = self.int_tujagm * self.dict_set['주식비중조절'][7]
            elif 비중조절기준 < self.dict_set['주식비중조절'][4]:
                betting = self.int_tujagm * self.dict_set['주식비중조절'][8]
            else:
                betting = self.int_tujagm * self.dict_set['주식비중조절'][9]

        oc_ratio = dict_order_ratio[self.dict_set['주식매수분할방법']][self.dict_set['주식매수분할횟수']][분할매수횟수]
        매수수량 = int(betting / (현재가 if 매수가 == 0 else 매수가) * oc_ratio / 100)
        return 매수수량

    def Sell(self):
        취소시그널, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1 = self.info_for_signal
        if 취소시그널:
            매도수량 = 0
        elif 전량매도:
            매도수량 = 보유수량
        else:
            매도수량 = self.GetSellCount(분할매도횟수, 보유수량, 매수가, 저가대비고가등락율)

        if '지정가' in self.dict_set['주식매도주문구분'] and not 강제청산:
            기준가격 = 현재가
            if self.dict_set['주식매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.dict_signal['매도'].append(self.code)
            self.straderQ.put(('매도', self.code, self.name, 기준가격, 매도수량, now(), False))
        else:
            매도금액 = 0
            미체결수량 = 매도수량
            for 매수호가, 매수잔량 in self.bhogainfo:
                if 미체결수량 - 매수잔량 <= 0:
                    매도금액 += 매수호가 * 미체결수량
                    미체결수량 -= 매수잔량
                    break
                else:
                    매도금액 += 매수호가 * 매수잔량
                    미체결수량 -= 매수잔량
            if 미체결수량 <= 0:
                예상체결가 = int(np.round(매도금액 / 매도수량)) if 매도수량 != 0 else 0
                self.dict_signal['매도'].append(self.code)
                self.straderQ.put(('매도', self.code, self.name, 예상체결가, 매도수량, now(), True if 강제청산 else False))

    def GetSellCount(self, 분할매도횟수, 보유수량, 매수가, 저가대비고가등락율):
        if self.dict_set['주식매도분할횟수'] == 1:
            return 보유수량
        else:
            if self.dict_set['주식비중조절'][0] == 0:
                betting = self.int_tujagm
            else:
                if self.dict_set['주식비중조절'][0] == 1:
                    비중조절기준 = 저가대비고가등락율
                elif self.dict_set['주식비중조절'][0] == 2:
                    비중조절기준 = self._거래대금평균대비비율(30)
                elif self.dict_set['주식비중조절'][0] == 3:
                    비중조절기준 = self._등락율각도(30)
                else:
                    비중조절기준 = self._당일거래대금각도(30)

                if 비중조절기준 < self.dict_set['주식비중조절'][1]:
                    betting = self.int_tujagm * self.dict_set['주식비중조절'][5]
                elif 비중조절기준 < self.dict_set['주식비중조절'][2]:
                    betting = self.int_tujagm * self.dict_set['주식비중조절'][6]
                elif 비중조절기준 < self.dict_set['주식비중조절'][3]:
                    betting = self.int_tujagm * self.dict_set['주식비중조절'][7]
                elif 비중조절기준 < self.dict_set['주식비중조절'][4]:
                    betting = self.int_tujagm * self.dict_set['주식비중조절'][8]
                else:
                    betting = self.int_tujagm * self.dict_set['주식비중조절'][9]

            oc_ratio = dict_order_ratio[self.dict_set['주식매도분할방법']][self.dict_set['주식매도분할횟수']][분할매도횟수]
            매도수량 = int(betting / 매수가 * oc_ratio / 100)
            if 매도수량 > 보유수량 or 분할매도횟수 + 1 == self.dict_set['주식매도분할횟수']: 매도수량 = 보유수량
            return 매도수량

    def PutGsjmAndDeleteHilo(self):
        if self.dict_gj:
            self.dict_gj = dict(sorted(self.dict_gj.items(), key=lambda x: x[1]['dm'], reverse=True))
            df_gj = pd.DataFrame.from_dict(self.dict_gj, orient='index')
            self.mgzservQ.put(('window', (ui_num[f'S관심종목'], self.gubun, df_gj)))
        if self.dict_profit:
            self.dict_profit = {k: v for k, v in self.dict_profit.items() if k in self.dict_jg}

    def SaveData(self, codes):
        for code in self.dict_data.copy():
            if code not in codes:
                del self.dict_data[code]

        last = len(self.dict_data)
        columns_ = list_stock_tick[:self.base_cnt] if self.dict_set['주식타임프레임'] else list_stock_min[:self.base_cnt]
        con = sqlite3.connect(DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN)
        if last > 0:
            start = now()
            cllen = len(columns_)
            for i, code in enumerate(self.dict_data):
                df = pd.DataFrame(self.dict_data[code][:, :cllen], columns=columns_)
                df['index'] = df['index'].astype('int64')
                df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                text = f'시스템 명령 실행 알림 - 전략연산 프로세스 데이터 저장 중 ... [{self.gubun + 1}]{i + 1}/{last}'
                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], text)))
            save_time = (now() - start).total_seconds()
            text = f'시스템 명령 실행 알림 - 데이터 저장 쓰기소요시간은 [{save_time:.6f}]초입니다.'
            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], text)))
        con.close()

        if self.gubun != 7:
            self.sstgQs[self.gubun + 1].put(('데이터저장', codes))
        else:
            self.logger.info('데이터 저장 완료')
            self.sstgQs[self.gubun].put('프로세스종료')

    def _fi(self, factor_name):
        return self.dict_findex[factor_name]

    def _now(self):
        return dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))

    def _Parameter_Previous(self, cidx, pre):
        if pre < self.tick_count:
            ridx = self.indexn - pre if pre != -1 else self.indexb
            return self.arry_code[ridx, cidx]
        return 0

    def _현재가N(self, pre):
        return self._Parameter_Previous(self._fi('현재가'), pre)

    def _시가N(self, pre):
        return self._Parameter_Previous(self._fi('시가'), pre)

    def _고가N(self, pre):
        return self._Parameter_Previous(self._fi('고가'), pre)

    def _저가N(self, pre):
        return self._Parameter_Previous(self._fi('저가'), pre)

    def _등락율N(self, pre):
        return self._Parameter_Previous(self._fi('등락율'), pre)

    def _당일거래대금N(self, pre):
        return self._Parameter_Previous(self._fi('당일거래대금'), pre)

    def _체결강도N(self, pre):
        return self._Parameter_Previous(self._fi('체결강도'), pre)

    def _초당매수수량N(self, pre):
        return self._Parameter_Previous(self._fi('초당매수수량'), pre)

    def _초당매도수량N(self, pre):
        return self._Parameter_Previous(self._fi('초당매도수량'), pre)

    def _거래대금증감N(self, pre):
        return self._Parameter_Previous(self._fi('거래대금증감'), pre)

    def _전일비N(self, pre):
        return self._Parameter_Previous(self._fi('전일비'), pre)

    def _회전율N(self, pre):
        return self._Parameter_Previous(self._fi('회전율'), pre)

    def _전일동시간비N(self, pre):
        return self._Parameter_Previous(self._fi('전일동시간비'), pre)

    def _시가총액N(self, pre):
        return self._Parameter_Previous(self._fi('시가총액'), pre)

    def _라운드피겨위5호가이내N(self, pre):
        return self._Parameter_Previous(self._fi('라운드피겨위5호가이내'), pre)

    def _VI해제시간N(self, pre):
        return self._Parameter_Previous(self._fi('VI해제시간'), pre)

    def _VI가격N(self, pre):
        return self._Parameter_Previous(self._fi('VI가격'), pre)

    def _VI호가단위N(self, pre):
        return self._Parameter_Previous(self._fi('VI호가단위'), pre)

    def _초당거래대금N(self, pre):
        return self._Parameter_Previous(self._fi('초당거래대금'), pre)

    def _고저평균대비등락율N(self, pre):
        return self._Parameter_Previous(self._fi('고저평균대비등락율'), pre)

    def _저가대비고가등락율N(self, pre):
        return self._Parameter_Previous(self._fi('저가대비고가등락율'), pre)

    def _초당매수금액N(self, pre):
        return self._Parameter_Previous(self._fi('초당매수금액'), pre)

    def _초당매도금액N(self, pre):
        return self._Parameter_Previous(self._fi('초당매도금액'), pre)

    def _당일매수금액N(self, pre):
        return self._Parameter_Previous(self._fi('당일매수금액'), pre)

    def _최고매수금액N(self, pre):
        return self._Parameter_Previous(self._fi('최고매수금액'), pre)

    def _최고매수가격N(self, pre):
        return self._Parameter_Previous(self._fi('최고매수가격'), pre)

    def _당일매도금액N(self, pre):
        return self._Parameter_Previous(self._fi('당일매도금액'), pre)

    def _최고매도금액N(self, pre):
        return self._Parameter_Previous(self._fi('최고매도금액'), pre)

    def _최고매도가격N(self, pre):
        return self._Parameter_Previous(self._fi('최고매도가격'), pre)

    def _매도호가5N(self, pre):
        return self._Parameter_Previous(self._fi('매도호가5'), pre)

    def _매도호가4N(self, pre):
        return self._Parameter_Previous(self._fi('매도호가4'), pre)

    def _매도호가3N(self, pre):
        return self._Parameter_Previous(self._fi('매도호가3'), pre)

    def _매도호가2N(self, pre):
        return self._Parameter_Previous(self._fi('매도호가2'), pre)

    def _매도호가1N(self, pre):
        return self._Parameter_Previous(self._fi('매도호가1'), pre)

    def _매수호가1N(self, pre):
        return self._Parameter_Previous(self._fi('매수호가1'), pre)

    def _매수호가2N(self, pre):
        return self._Parameter_Previous(self._fi('매수호가2'), pre)

    def _매수호가3N(self, pre):
        return self._Parameter_Previous(self._fi('매수호가3'), pre)

    def _매수호가4N(self, pre):
        return self._Parameter_Previous(self._fi('매수호가4'), pre)

    def _매수호가5N(self, pre):
        return self._Parameter_Previous(self._fi('매수호가5'), pre)

    def _매도잔량5N(self, pre):
        return self._Parameter_Previous(self._fi('매도잔량5'), pre)

    def _매도잔량4N(self, pre):
        return self._Parameter_Previous(self._fi('매도잔량4'), pre)

    def _매도잔량3N(self, pre):
        return self._Parameter_Previous(self._fi('매도잔량3'), pre)

    def _매도잔량2N(self, pre):
        return self._Parameter_Previous(self._fi('매도잔량2'), pre)

    def _매도잔량1N(self, pre):
        return self._Parameter_Previous(self._fi('매도잔량1'), pre)

    def _매수잔량1N(self, pre):
        return self._Parameter_Previous(self._fi('매수잔량1'), pre)

    def _매수잔량2N(self, pre):
        return self._Parameter_Previous(self._fi('매수잔량2'), pre)

    def _매수잔량3N(self, pre):
        return self._Parameter_Previous(self._fi('매수잔량3'), pre)

    def _매수잔량4N(self, pre):
        return self._Parameter_Previous(self._fi('매수잔량4'), pre)

    def _매수잔량5N(self, pre):
        return self._Parameter_Previous(self._fi('매수잔량5'), pre)

    def _매도총잔량N(self, pre):
        return self._Parameter_Previous(self._fi('매도총잔량'), pre)

    def _매수총잔량N(self, pre):
        return self._Parameter_Previous(self._fi('매수총잔량'), pre)

    def _매도수5호가잔량합N(self, pre):
        return self._Parameter_Previous(self._fi('매도수5호가잔량합'), pre)

    def _관심종목N(self, pre):
        return self._Parameter_Previous(self._fi('관심종목'), pre)

    def _분봉시가N(self, pre):
        return self._Parameter_Previous(self._fi('분봉시가'), pre)

    def _분봉고가N(self, pre):
        return self._Parameter_Previous(self._fi('분봉고가'), pre)

    def _분봉저가N(self, pre):
        return self._Parameter_Previous(self._fi('분봉저가'), pre)

    def _최고분봉고가(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고분봉고가'), self._fi('분봉고가'), tick, pre, np.max, calc=calc)

    def _최저분봉저가(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최저분봉저가'), self._fi('분봉저가'), tick, pre, np.min, calc=calc)

    def _분당매수수량N(self, pre):
        return self._Parameter_Previous(self._fi('분당매수수량'), pre)

    def _분당매도수량N(self, pre):
        return self._Parameter_Previous(self._fi('분당매도수량'), pre)

    def _분당거래대금N(self, pre):
        return self._Parameter_Previous(self._fi('분당거래대금'), pre)

    def _분당매수금액N(self, pre):
        return self._Parameter_Previous(self._fi('분당매수금액'), pre)

    def _분당매도금액N(self, pre):
        return self._Parameter_Previous(self._fi('분당매도금액'), pre)

    def _최고분당매수수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고분당매수수량'), self._fi('분당매수수량'), tick, pre, np.max, calc=calc)

    def _최고분당매도수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고분당매도수량'), self._fi('분당매도수량'), tick, pre, np.max, calc=calc)

    def _누적분당매수수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('누적분당매수수량'), self._fi('분당매수수량'), tick, pre, np.sum, calc=calc)

    def _누적분당매도수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('누적분당매도수량'), self._fi('분당매도수량'), tick, pre, np.sum, calc=calc)

    def _분당거래대금평균(self, tick, pre=0, calc=False):
        return int(self._Parameter_Area(self._fi('분당거래대금평균'), self._fi('분당거래대금'), tick, pre, np.mean, calc=calc))

    def _get_column_index(self, cidx):
        return cidx

    def _get_double_index(self, tick):
        return self.indexn + 1 - tick, self.indexn + 1

    def _get_double_pre_index(self, tick, pre):
        sidx = self.indexn + 1 - tick - pre if pre != -1 else self.indexb + 1 - tick
        eidx = self.indexn + 1 - pre if pre != -1 else self.indexb + 1
        return sidx, eidx

    def _get_angle_double_pre_index(self, tick, pre):
        sidx = self.indexn - tick - pre if pre != -1 else self.indexb - tick
        eidx = self.indexn - pre if pre != -1 else self.indexb
        return sidx, eidx

    def _이동평균(self, tick, pre=0, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.sma_list:
                return self._Parameter_Previous(self._fi(f'이동평균{tick}'), pre)
            else:
                sidx, eidx = self._get_double_pre_index(tick, pre)
                return np.round(self.arry_code[sidx:eidx, self._fi('현재가')].mean(), self.ma_round_unit)
        return 0

    def _Parameter_Area(self, cidx, fidx, tick, pre, func, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.avg_list:
                return self._Parameter_Previous(self._get_column_index(cidx), pre)
            else:
                sidx, eidx = self._get_double_pre_index(tick, pre)
                return func(self.arry_code[sidx:eidx, fidx])
        return 0

    def _Parameter_Angle(self, cidx, fidx, tick, pre, cf, calc=False):
        if tick + pre <= self.tick_count:
            if not calc and tick in self.avg_list:
                return self._Parameter_Previous(self._get_column_index(cidx), pre)
            else:
                sidx, eidx = self._get_angle_double_pre_index(tick, pre)
                diff = self.arry_code[eidx, fidx] - self.arry_code[sidx, fidx]
                return np.round(math.atan2(diff * cf, tick) / (2 * math.pi) * 360, 2)
        return 0

    def _최고현재가(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고현재가'), self._fi('현재가'), tick, pre, np.max, calc=calc)

    def _최저현재가(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최저현재가'), self._fi('현재가'), tick, pre, np.min, calc=calc)

    def _체결강도평균(self, tick, pre=0, calc=False):
        return np.round(self._Parameter_Area(self._fi('체결강도평균'), self._fi('체결강도'), tick, pre, np.mean, calc=calc), 3)

    def _최고체결강도(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고체결강도'), self._fi('체결강도'), tick, pre, np.max, calc=calc)

    def _최저체결강도(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최저체결강도'), self._fi('체결강도'), tick, pre, np.min, calc=calc)

    def _최고초당매수수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고초당매수수량'), self._fi('초당매수수량'), tick, pre, np.max, calc=calc)

    def _최고초당매도수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('최고초당매도수량'), self._fi('초당매도수량'), tick, pre, np.max, calc=calc)

    def _누적초당매수수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('누적초당매수수량'), self._fi('초당매수수량'), tick, pre, np.sum, calc=calc)

    def _누적초당매도수량(self, tick, pre=0, calc=False):
        return self._Parameter_Area(self._fi('누적초당매도수량'), self._fi('초당매도수량'), tick, pre, np.sum, calc=calc)

    def _초당거래대금평균(self, tick, pre=0, calc=False):
        return int(self._Parameter_Area(self._fi('초당거래대금평균'), self._fi('초당거래대금'), tick, pre, np.mean, calc=calc))

    def _등락율각도(self, tick, pre=0, calc=False):
        return self._Parameter_Angle(self._fi('등락율각도'), self._fi('등락율'), tick, pre, self.angle_pct_cf, calc=calc)

    def _당일거래대금각도(self, tick, pre=0, calc=False):
        return self._Parameter_Angle(self._fi('당일거래대금각도'), self._fi('당일거래대금'), tick, pre, self.angle_dtm_cf, calc=calc)

    def _전일비각도(self, tick, pre=0, calc=False):
        return self._Parameter_Angle(self._fi('전일비각도'), self._fi('전일비'), tick, pre, 1, calc=calc)

    def _경과틱수(self, 조건명):
        if self.code in self.dict_cond_indexn and \
                조건명 in self.dict_cond_indexn[self.code] and self.dict_cond_indexn[self.code][조건명] != 0:
            return self.indexn - self.dict_cond_indexn[self.code][조건명]
        return 0

    def _이평지지(self, tick1, tick2=30, per=0.5, cnt=10):
        if tick1 + tick2 <= self.tick_count and tick1 in self.sma_list:
            sidx, eidx = self._get_double_index(tick2)
            arry_close = self.arry_code[sidx:eidx, self._fi('현재가')]
            arry_sma = self.arry_code[sidx:eidx, self._fi(f'이동평균{tick1}')]
            deviation = np.abs(arry_close - arry_sma) / arry_sma * 100
            return np.sum(deviation <= per) >= cnt
        return 0

    def _시가지지(self, tick, per=0.5, cnt=10):
        if tick <= self.tick_count:
            sidx, eidx = self._get_double_index(tick)
            arry_close = self.arry_code[sidx:eidx, self._fi('현재가')]
            deviation = np.abs(arry_close - self._시가N(0)) / self._시가N(0) * 100
            return np.sum(deviation <= per) >= cnt
        return 0

    def _변동성(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            if self.is_tick:
                arry_close = self.arry_code[sidx:eidx, self._fi('현재가')]
                volatility = np.std(arry_close) / np.mean(arry_close) * 100
            else:
                arry_high  = self.arry_code[sidx:eidx, self._fi('분봉고가')]
                arry_low   = self.arry_code[sidx:eidx, self._fi('분봉저가')]
                volatility = np.std(arry_high - arry_low) / np.mean(arry_high - arry_low) * 100
            return volatility
        return 0

    def _구간저가대비현재가등락율(self, tick):
        if tick <= self.tick_count:
            if self.is_tick:
                return (self._현재가N(0) / self._최저현재가(tick) - 1) * 100
            else:
                return (self._현재가N(0) / self._최저분봉저가(tick) - 1) * 100
        return 0

    def _구간고가대비현재가등락율(self, tick):
        if tick <= self.tick_count:
            if self.is_tick:
                return (self._현재가N(0) / self._최고현재가(tick) - 1) * 100
            else:
                return (self._현재가N(0) / self._최고분봉고가(tick) - 1) * 100
        return 0

    def _거래대금평균대비비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            if self.is_tick:
                money_unit = self._초당거래대금N(pre)
                money_avg  = self._초당거래대금평균(tick, pre)
            else:
                money_unit = self._분당거래대금N(pre)
                money_avg  = self._분당거래대금평균(tick, pre)
            return money_unit / money_avg if money_avg > 0 else 0
        return 0

    # noinspection PyTypeChecker
    def _체결강도평균대비비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            return self._체결강도N(pre) / self._체결강도평균(tick, pre)
        return 0

    def _구간호가총잔량비율(self, tick, pre=0):
        if tick + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            sum_bids = self.arry_code[sidx:eidx, self._fi('매수총잔량')].sum()
            sum_asks = self.arry_code[sidx:eidx, self._fi('매도총잔량')].sum()
            total_cnt = sum_bids + sum_asks
            return sum_bids / total_cnt if total_cnt != 0 else 0
        return 0

    def _매수수량변동성(self, tick, pre=0):
        if tick * 2 + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            cur_avg_buys = self.arry_code[sidx:eidx, self._fi('초당매수수량' if self.is_tick else '분당매수수량')].sum()
            pre_avg_buys = self.arry_code[sidx - tick:eidx - tick, self._fi('초당매수수량' if self.is_tick else '분당매수수량')].sum()
            return cur_avg_buys / pre_avg_buys if pre_avg_buys != 0 else 0
        return 0

    def _매도수량변동성(self, tick, pre=0):
        if tick * 2 + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            cur_arry_sells = self.arry_code[sidx:eidx, self._fi('초당매도수량' if self.is_tick else '분당매도수량')].sum()
            pre_arry_sells = self.arry_code[sidx - tick:eidx - tick, self._fi('초당매도수량' if self.is_tick else '분당매도수량')].sum()
            return cur_arry_sells / pre_arry_sells if pre_arry_sells != 0 else 0
        return 0

    def _횡보감지(self, tick, per=0.5, pre=0):
        if tick + pre <= self.tick_count:
            return self._변동성(tick, pre) <= per
        return 0

    def _고가미갱신지속틱수(self):
        return self.indexn - self.high_low[self.code][1]

    def _저가미갱신지속틱수(self):
        return self.indexn - self.high_low[self.code][3]

    def _고점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[self.code][1]
        diff_pct  = (self._현재가N(0) / self.high_low[self.code][0] - 1) * 100
        return np.round(math.atan2(diff_pct * cf, diff_tick) / (2 * math.pi) * 360, 2)

    def _저점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[self.code][3]
        diff_pct  = (self._현재가N(0) / self.high_low[self.code][2] - 1) * 100
        return np.round(math.atan2(diff_pct * cf, diff_tick) / (2 * math.pi) * 360, 2)

    def _연속상승(self, tick):
        if 1 < tick < self.tick_count:
            for cc in range(0, tick):
                if self._현재가N(cc) < self._현재가N(cc + 1):
                    return False
            return True
        return False

    def _연속하락(self, tick):
        if 1 < tick < self.tick_count:
            for cc in range(1, tick):
                if self._현재가N(cc) > self._현재가N(cc + 1):
                    return False
            return True
        return False

    def _호가갭발생(self, hogagap, pre=0):
        if pre < self.tick_count:
            if pre == 0:
                hoga_spread = (self._매도호가1N(0) - self._매수호가1N(0)) / self.hoga_unit
            else:
                hoga_spread = (self._매도호가1N(pre) - self._매수호가1N(pre)) / self.hoga_unit
            return hoga_spread >= hogagap
        return False

    def _변동성급증(self, tick, ratio=2):
        prev_volatility = self._변동성(tick, tick)
        if prev_volatility > 0:
            return self._변동성(tick) / prev_volatility >= ratio
        return False

    def _변동성급감(self, tick, ratio=0.5):
        prev_volatility = self._변동성(tick, tick)
        if prev_volatility > 0:
            if ratio == 0: return False
            return self._변동성(tick) / prev_volatility <= ratio
        return False

    def _가격급등(self, tick, per=1.0):
        return self._구간저가대비현재가등락율(tick) >= per

    def _가격급락(self, tick, per=1.0):
        return self._구간고가대비현재가등락율(tick) <= -per

    def _거래대금급증(self, tick, ratio=3):
        return self._거래대금평균대비비율(tick) >= ratio

    def _거래대금급감(self, tick, ratio=0.5):
        return self._거래대금평균대비비율(tick) <= ratio

    def _체결강도급등(self, tick, ratio=1.1):
        return self._체결강도평균대비비율(tick) >= ratio

    def _체결강도급락(self, tick, ratio=0.9):
        return self._체결강도평균대비비율(tick) <= ratio

    def _호가상승압력(self, tick, ratio=0.7):
        return self._구간호가총잔량비율(tick) >= ratio

    def _호가하락압력(self, tick, ratio=0.3):
        return self._구간호가총잔량비율(tick) <= ratio

    def _매수수량급증(self, tick, ratio=3):
        return self._매수수량변동성(tick) >= ratio

    def _매수수량급감(self, tick, ratio=0.5):
        return self._매수수량변동성(tick) <= ratio

    def _매도수량급증(self, tick, ratio=3):
        return self._매도수량변동성(tick) >= ratio

    def _매도수량급감(self, tick, ratio=0.5):
        return self._매도수량변동성(tick) <= ratio

    def _이평돌파(self, tick, per=1.0):
        sma = self._이동평균(tick)
        if sma == 0: return False
        return self._최저현재가(tick) < sma and (self._현재가N(0) / sma - 1) * 100 >= per

    def _이평이탈(self, tick, per=1.0):
        sma = self._이동평균(tick)
        if sma == 0: return False
        return self._최고현재가(tick) > sma and (self._현재가N(0) / sma - 1) * 100 <= -per

    def _시가돌파(self, tick, per=1.0):
        return self._최저현재가(tick) < self._시가N(0) and (self._현재가N(0) / self._시가N(0) - 1) * 100 >= per

    def _시가이탈(self, tick, per=1.0):
        return self._최고현재가(tick) > self._시가N(0) and (self._현재가N(0) / self._시가N(0) - 1) * 100 <= -per

    def _이평지지후이평돌파(self, tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
        return self._이평지지(tick1, tick2, per1, cnt) and self._이평돌파(tick1, per2)

    def _이평지지후이평이탈(self, tick1, tick2=30, per1=0.5, cnt=10, per2=1.0):
        return self._이평지지(tick1, tick2, per1, cnt) and self._이평이탈(tick1, per2)

    def _횡보후가격급등(self, tick1, per1=0.5, tick2=10, per2=1.0):
        return self._횡보감지(tick1, per1, tick2) and self._가격급등(tick2, per2)

    def _횡보후가격급락(self, tick1, per1=0.5, tick2=10, per2=1.0):
        return self._횡보감지(tick1, per1, tick2) and self._가격급락(tick2, per2)

    def _횡보후연속상승(self, tick1, per1=0.5, tick2=5):
        return self._횡보감지(tick1, per1, tick2) and self._연속상승(tick2)

    def _횡보후연속하락(self, tick1, per1=0.5, tick2=5):
        return self._횡보감지(tick1, per1, tick2) and self._연속하락(tick2)

    def _연속상승및가격급등(self, tick1, tick2=10, per=1.0):
        return self._연속상승(tick1) and self._가격급등(tick2, per)

    def _연속하락및가격급락(self, tick1, tick2=10, per=1.0):
        return self._연속하락(tick1) and self._가격급락(tick2, per)

    def _거래대금급증및연속상승(self, tick1, ratio=2, tick2=5):
        return self._거래대금급증(tick1, ratio) and self._연속상승(tick2)

    def _거래대금급감및연속하락(self, tick1, ratio=2, tick2=5):
        return self._거래대금급감(tick1, ratio) and self._연속하락(tick2)

    def _호가상승압력및매수수량급증(self, tick, ratio1=0.7, ratio2=3):
        return self._호가상승압력(tick, ratio1) and self._매수수량급증(tick, ratio2)

    def _호가하락압력및매도수량급증(self, tick, ratio=0.3, ratio2=3):
        return self._호가하락압력(tick, ratio) and self._매도수량급증(tick, ratio2)

    def _매수수량급증및가격급등(self, tick, ratio=3, tick2=10, per=1.0):
        return self._매수수량급증(tick, ratio) and self._가격급등(tick2, per)

    def _매도수량급증후가격급락(self, tick, ratio=3, tick2=10, per=1.0):
        return self._매도수량급증(tick, ratio) and self._가격급락(tick2, per)

    def _변동성급증및구간최고가갱신(self, tick, ratio=2):
        return self._변동성급증(tick, ratio) and self._현재가N(0) > self._최고현재가(tick, 1)

    def _변동성급감및구간최저가갱신(self, tick, ratio=0.5):
        return self._변동성급감(tick, ratio) and self._현재가N(0) < self._최저현재가(tick, 1)

    def _거래대금급증및구간최고가갱신(self, tick, ratio=2):
        return self._거래대금급증(tick, ratio) and self._현재가N(0) > self._최고현재가(tick, 1)

    def _거래대금급감후구간최저가갱신(self, tick, ratio=0.5):
        return self._거래대금급감(tick, ratio) and self._현재가N(0) < self._최저현재가(tick, 1)

    def _거래대금급증및가격급등(self, tick1, ratio=2, tick2=10, per=1.0):
        return self._거래대금급증(tick1, ratio) and self._가격급등(tick2, per)

    def _거래대금급감및가격급락(self, tick1, ratio=0.5, tick2=10, per=1.0):
        return self._거래대금급감(tick1, ratio) and self._가격급락(tick2, per)

    def _체결강도급등및호가상승압력(self, tick1, ratio1=1.1, tick2=10, ratio2=0.7):
        return self._체결강도급등(tick1, ratio1) and self._호가상승압력(tick2, ratio2)

    def _체결강도급락및호가하락압력(self, tick1, ratio1=0.9, tick2=10, ratio2=0.3):
        return self._체결강도급락(tick1, ratio1) and self._호가하락압력(tick2, ratio2)

    def _시가근접황보후시가돌파(self, tick, per1=0.5, cnt=10, per2=1.0):
        return self._시가지지(tick, per1, cnt) and self._시가돌파(tick, per2)

    def _시가근접황보후시가이탈(self, tick, per1=0.5, cnt=10, per2=1.0):
        return self._시가지지(tick, per1, cnt) and self._시가이탈(tick, per2)

    def _저가갱신후가격급등(self, tick, per=2):
        return self.indexn - self.high_low[self.code][3] <= tick and self._가격급등(tick, per)

    def _고가갱신후가격급락(self, tick, per=2):
        return self.indexn - self.high_low[self.code][1] <= tick and self._가격급락(tick, per)

    def _횡보상태장기보유(self, tick, per=0.5, time_=600):
        return self._횡보감지(tick, per) and self.hold_time >= time_

    def _변동성급증_역추세매도(self, tick, ratio=3, reversal_per=2.0):
        cur_vol = self._변동성(tick)
        pre_vol = self._변동성(tick, tick)
        if cur_vol >= pre_vol * ratio:
            return self._구간고가대비현재가등락율(tick) <= -reversal_per
        return False

    def _장기보유종목_동적익절청산(self, tick, time_=600, minper=0.3, multi=1):
        if tick <= self.tick_count:
            cur_vol = self._변동성(tick)
            min_profit = max(minper, cur_vol * multi)
            hold_time = max(time_, cur_vol * time_ * multi)
            if self.profit > min_profit and self.hold_time > hold_time:
                return True
        return False

    def _거래대금비율기반_동적청산(self, tick, ratio1=0.3, ratio2=3):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self._거래대금급감(tick, ratio1)
            else:
                return self._거래대금급증(tick, ratio2)
        return False

    def _호가압력기반_동적청산(self, tick, buy_pressure=0.8, sell_pressure=0.2):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self._호가하락압력(tick, sell_pressure)
            else:
                return self._호가상승압력(tick, buy_pressure)
        return False

    def _이평기반_동적청산(self, short, long=60, deviation1=0.5, deviation2=1.0):
        if short <= self.tick_count and long <= self.tick_count:
            short_ma = self._이동평균(short)
            long_ma = self._이동평균(long)
            if short_ma == 0: return False
            if self.profit > 0:
                deviation_pct = abs(self._현재가N(0) - short_ma) / short_ma * 100
                return self._현재가N(0) < short_ma and deviation_pct >= deviation1
            else:
                deviation_pct = abs(self._현재가N(0) - long_ma) / long_ma * 100
                return self._현재가N(0) < long_ma and deviation_pct >= deviation2
        return False

    def _변동성기반_동적청산(self, tick, ratio1=3, ratio2=1.5):
        if tick <= self.tick_count:
            if self.profit > 0:
                return self.profit >= self._변동성(tick) * ratio1
            else:
                return self.profit <= -self._변동성(tick) * ratio2
        return False

    def _변동성급증기반_동적청산(self, tick, multi=2, ratio1=3, ratio2=1.5):
        cur_vol = self._변동성(tick)
        avg_vol = self._변동성(tick, tick)
        if cur_vol > avg_vol * multi:
            if self.profit > 0:
                return self.profit >= cur_vol * ratio1
            else:
                return self.profit <= -cur_vol * ratio2
        return False

    def _AD_N(self, pre):
        return self._Parameter_Previous(self._fi('AD'), pre)

    def _ADOSC_N(self, pre):
        return self._Parameter_Previous(self._fi('ADOSC'), pre)

    def _ADXR_N(self, pre):
        return self._Parameter_Previous(self._fi('ADXR'), pre)

    def _APO_N(self, pre):
        return self._Parameter_Previous(self._fi('APO'), pre)

    def _AROOND_N(self, pre):
        return self._Parameter_Previous(self._fi('AROOND'), pre)

    def _AROONU_N(self, pre):
        return self._Parameter_Previous(self._fi('AROONU'), pre)

    def _ATR_N(self, pre):
        return self._Parameter_Previous(self._fi('ATR'), pre)

    def _BBU_N(self, pre):
        return self._Parameter_Previous(self._fi('BBU'), pre)

    def _BBM_N(self, pre):
        return self._Parameter_Previous(self._fi('BBM'), pre)

    def _BBL_N(self, pre):
        return self._Parameter_Previous(self._fi('BBL'), pre)

    def _CCI_N(self, pre):
        return self._Parameter_Previous(self._fi('CCI'), pre)

    def _DIM_N(self, pre):
        return self._Parameter_Previous(self._fi('DIM'), pre)

    def _DIP_N(self, pre):
        return self._Parameter_Previous(self._fi('DIP'), pre)

    def _MACD_N(self, pre):
        return self._Parameter_Previous(self._fi('MACD'), pre)

    def _MACDS_N(self, pre):
        return self._Parameter_Previous(self._fi('MACDS'), pre)

    def _MACDH_N(self, pre):
        return self._Parameter_Previous(self._fi('MACDH'), pre)

    def _MFI_N(self, pre):
        return self._Parameter_Previous(self._fi('MFI'), pre)

    def _MOM_N(self, pre):
        return self._Parameter_Previous(self._fi('MOM'), pre)

    def _OBV_N(self, pre):
        return self._Parameter_Previous(self._fi('OBV'), pre)

    def _PPO_N(self, pre):
        return self._Parameter_Previous(self._fi('PPO'), pre)

    def _ROC_N(self, pre):
        return self._Parameter_Previous(self._fi('ROC'), pre)

    def _RSI_N(self, pre):
        return self._Parameter_Previous(self._fi('RSI'), pre)

    def _SAR_N(self, pre):
        return self._Parameter_Previous(self._fi('SAR'), pre)

    def _STOCHSK_N(self, pre):
        return self._Parameter_Previous(self._fi('STOCHSK'), pre)

    def _STOCHSD_N(self, pre):
        return self._Parameter_Previous(self._fi('STOCHSD'), pre)

    def _STOCHFK_N(self, pre):
        return self._Parameter_Previous(self._fi('STOCHFK'), pre)

    def _STOCHFD_N(self, pre):
        return self._Parameter_Previous(self._fi('STOCHFD'), pre)

    def _WILLR_N(self, pre):
        return self._Parameter_Previous(self._fi('WILLR'), pre)

    def UpdateStraegyGlobals(self):
        dict_add_func = {
            '현재가N': self._현재가N,
            '시가N': self._시가N,
            '고가N': self._고가N,
            '저가N': self._저가N,
            '등락율N': self._등락율N,
            '당일거래대금N': self._당일거래대금N,
            '체결강도N': self._체결강도N,

            '고저평균대비등락율N': self._고저평균대비등락율N,
            '저가대비고가등락율N': self._저가대비고가등락율N,
            '초당매수금액N': self._초당매수금액N,
            '초당매도금액N': self._초당매도금액N,
            '당일매수금액N': self._당일매수금액N,
            '최고매수금액N': self._최고매수금액N,
            '최고매수가격N': self._최고매수가격N,
            '당일매도금액N': self._당일매도금액N,
            '최고매도금액N': self._최고매도금액N,
            '최고매도가격N': self._최고매도가격N,

            '초당매수수량N': self._초당매수수량N,
            '초당매도수량N': self._초당매도수량N,
            '초당거래대금N': self._초당거래대금N,
            '최고초당매수수량': self._최고초당매수수량,
            '최고초당매도수량': self._최고초당매도수량,
            '누적초당매수수량': self._누적초당매수수량,
            '누적초당매도수량': self._누적초당매도수량,
            '초당거래대금평균': self._초당거래대금평균,

            '분봉시가N': self._분봉시가N,
            '분봉고가N': self._분봉고가N,
            '분봉저가N': self._분봉저가N,
            '분당매수수량N': self._분당매수수량N,
            '분당매도수량N': self._분당매도수량N,
            '분당거래대금N': self._분당거래대금N,
            '분당매수금액N': self._분당매수금액N,
            '분당매도금액N': self._분당매도금액N,
            '최고분봉고가': self._최고분봉고가,
            '최저분봉저가': self._최저분봉저가,
            '최고분당매수수량': self._최고분당매수수량,
            '최고분당매도수량': self._최고분당매도수량,
            '누적분당매수수량': self._누적분당매수수량,
            '누적분당매도수량': self._누적분당매도수량,
            '분당거래대금평균': self._분당거래대금평균,

            '거래대금증감N': self._거래대금증감N,
            '전일비N': self._전일비N,
            '회전율N': self._회전율N,
            '전일동시간비N': self._전일동시간비N,
            '시가총액N': self._시가총액N,
            '라운드피겨위5호가이내N': self._라운드피겨위5호가이내N,
            'VI해제시간N': self._VI해제시간N,
            'VI가격N': self._VI가격N,
            'VI호가단위N': self._VI호가단위N,
            '전일비각도': self._전일비각도,

            '매도호가5N': self._매도호가5N,
            '매도호가4N': self._매도호가4N,
            '매도호가3N': self._매도호가3N,
            '매도호가2N': self._매도호가2N,
            '매도호가1N': self._매도호가1N,
            '매수호가1N': self._매수호가1N,
            '매수호가2N': self._매수호가2N,
            '매수호가3N': self._매수호가3N,
            '매수호가4N': self._매수호가4N,
            '매수호가5N': self._매수호가5N,
            '매도잔량5N': self._매도잔량5N,
            '매도잔량4N': self._매도잔량4N,
            '매도잔량3N': self._매도잔량3N,
            '매도잔량2N': self._매도잔량2N,
            '매도잔량1N': self._매도잔량1N,
            '매수잔량1N': self._매수잔량1N,
            '매수잔량2N': self._매수잔량2N,
            '매수잔량3N': self._매수잔량3N,
            '매수잔량4N': self._매수잔량4N,
            '매수잔량5N': self._매수잔량5N,
            '매도총잔량N': self._매도총잔량N,
            '매수총잔량N': self._매수총잔량N,
            '매도수5호가잔량합N': self._매도수5호가잔량합N,
            '관심종목N': self._관심종목N,

            '이동평균': self._이동평균,
            '최고현재가': self._최고현재가,
            '최저현재가': self._최저현재가,
            '체결강도평균': self._체결강도평균,
            '최고체결강도': self._최고체결강도,
            '최저체결강도': self._최저체결강도,
            '등락율각도': self._등락율각도,
            '당일거래대금각도': self._당일거래대금각도,
            '경과틱수': self._경과틱수,

            '이평지지': self._이평지지,
            '시가지지': self._시가지지,
            '변동성': self._변동성,
            '구간저가대비현재가등락율': self._구간저가대비현재가등락율,
            '구간고가대비현재가등락율': self._구간고가대비현재가등락율,
            '거래대금평균대비비율': self._거래대금평균대비비율,
            '체결강도평균대비비율': self._체결강도평균대비비율,
            '구간호가총잔량비율': self._구간호가총잔량비율,
            '매수수량변동성': self._매수수량변동성,
            '매도수량변동성': self._매도수량변동성,
            '횡보감지': self._횡보감지,
            '고가미갱신지속틱수': lambda: self._고가미갱신지속틱수(),
            '저가미갱신지속틱수': lambda: self._저가미갱신지속틱수(),
            '고점기준등락율각도': self._고점기준등락율각도,
            '저점기준등락율각도': self._저점기준등락율각도,
            '연속상승': self._연속상승,
            '연속하락': self._연속하락,
            '호가갭발생': self._호가갭발생,
            '변동성급증': self._변동성급증,
            '변동성급감': self._변동성급감,
            '가격급등': self._가격급등,
            '가격급락': self._가격급락,
            '거래대금급증': self._거래대금급증,
            '거래대금급감': self._거래대금급감,
            '체결강도급등': self._체결강도급등,
            '체결강도급락': self._체결강도급락,
            '호가상승압력': self._호가상승압력,
            '호가하락압력': self._호가하락압력,
            '매수수량급증': self._매수수량급증,
            '매수수량급감': self._매수수량급감,
            '매도수량급증': self._매도수량급증,
            '매도수량급감': self._매도수량급감,
            '이평돌파': self._이평돌파,
            '이평이탈': self._이평이탈,
            '시가돌파': self._시가돌파,
            '시가이탈': self._시가이탈,

            '이평지지후이평돌파': self._이평지지후이평돌파,
            '이평지지후이평이탈': self._이평지지후이평이탈,
            '횡보후가격급등': self._횡보후가격급등,
            '횡보후가격급락': self._횡보후가격급락,
            '횡보후연속상승': self._횡보후연속상승,
            '횡보후연속하락': self._횡보후연속하락,
            '연속상승및가격급등': self._연속상승및가격급등,
            '연속하락및가격급락': self._연속하락및가격급락,
            '거래대금급증및연속상승': self._거래대금급증및연속상승,
            '거래대금급감및연속하락': self._거래대금급감및연속하락,
            '호가상승압력및매수수량급증': self._호가상승압력및매수수량급증,
            '호가하락압력및매도수량급증': self._호가하락압력및매도수량급증,
            '매수수량급증및가격급등': self._매수수량급증및가격급등,
            '매도수량급증후가격급락': self._매도수량급증후가격급락,
            '변동성급증및구간최고가갱신': self._변동성급증및구간최고가갱신,
            '변동성급감및구간최저가갱신': self._변동성급감및구간최저가갱신,
            '거래대금급증및구간최고가갱신': self._거래대금급증및구간최고가갱신,
            '거래대금급감후구간최저가갱신': self._거래대금급감후구간최저가갱신,
            '거래대금급증및가격급등': self._거래대금급증및가격급등,
            '거래대금급감및가격급락': self._거래대금급감및가격급락,
            '체결강도급등및호가상승압력': self._체결강도급등및호가상승압력,
            '체결강도급락및호가하락압력': self._체결강도급락및호가하락압력,
            '시가근접황보후시가돌파': self._시가근접황보후시가돌파,
            '시가근접황보후시가이탈': self._시가근접황보후시가이탈,
            '저가갱신후가격급등': self._저가갱신후가격급등,
            '고가갱신후가격급락': self._고가갱신후가격급락,
            '횡보상태장기보유': self._횡보상태장기보유,
            '변동성급증_역추세매도': self._변동성급증_역추세매도,
            '장기보유종목_동적익절청산': self._장기보유종목_동적익절청산,
            '거래대금비율기반_동적청산': self._거래대금비율기반_동적청산,
            '호가압력기반_동적청산': self._호가압력기반_동적청산,
            '이평기반_동적청산': self._이평기반_동적청산,
            '변동성기반_동적청산': self._변동성기반_동적청산,
            '변동성급증기반_동적청산': self._변동성급증기반_동적청산,

            'AD_N': self._AD_N,
            'ADOSC_N': self._ADOSC_N,
            'ADXR_N': self._ADXR_N,
            'APO_N': self._APO_N,
            'AROOND_N': self._AROOND_N,
            'AROONU_N': self._AROONU_N,
            'ATR_N': self._ATR_N,
            'BBU_N': self._BBU_N,
            'BBM_N': self._BBM_N,
            'BBL_N': self._BBL_N,
            'CCI_N': self._CCI_N,
            'DIM_N': self._DIM_N,
            'DIP_N': self._DIP_N,
            'MACD_N': self._MACD_N,
            'MACDS_N': self._MACDS_N,
            'MACDH_N': self._MACDH_N,
            'MFI_N': self._MFI_N,
            'MOM_N': self._MOM_N,
            'OBV_N': self._OBV_N,
            'PPO_N': self._PPO_N,
            'ROC_N': self._ROC_N,
            'RSI_N': self._RSI_N,
            'SAR_N': self._SAR_N,
            'STOCHSK_N': self._STOCHSK_N,
            'STOCHSD_N': self._STOCHSD_N,
            'STOCHFK_N': self._STOCHFK_N,
            'STOCHFD_N': self._STOCHFD_N,
            'WILLR_': self._WILLR_N
        }
        self.UpdateGlobalsFunc(dict_add_func)

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)
