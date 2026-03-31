
import os
import sys
import time
import sqlite3
import numpy as np
import pandas as pd
from copy import deepcopy
from traceback import format_exc
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from trade.risk_analyzer import RiskAnalyzer
from trade.strategy_base import StrategyBase
from trade.formula_manager import get_formula_data
from trade.microstructure_analyzer import MicrostructureAnalyzer
from utility.setting_base import DB_STRATEGY, ui_num, dict_order_ratio, DB_STOCK_TICK, DB_STOCK_MIN, indicator, \
    list_stock_tick, list_stock_min
# noinspection PyUnresolvedReferences
from utility.static import now, timedelta_sec, GetKiwoomPgSgSp, GetHogaunit, get_buy_indi_stg, \
    str_ymdhms, dt_ymdhms, get_angle_cf, get_ema_list, error_decorator, set_builtin_print, get_profile_text


class KiwoomStrategyTick(StrategyBase):
    def __init__(self, gubun, qlist, dict_set):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs
                0            1             2            3
        """
        super().__init__()
        self.gubun            = gubun
        self.mgzservQ         = qlist[0]
        self.straderQ         = qlist[2]
        self.sstgQs           = qlist[3]
        self.sstgQ            = qlist[3][self.gubun]
        self.dict_set         = dict_set
        self.indicator        = indicator

        self.buystrategy      = None
        self.sellstrategy     = None
        self.chart_code       = None
        self.info_for_signal  = None

        self.dict_data        = {}
        self.dict_signal_num  = {}
        self.dict_buy_num     = {}
        self.dict_profit      = {}
        self.dict_gj          = {}
        self.dict_jg          = {}
        self.indi_settings    = []
        self.tuple_kosd       = ()
        self.dict_signal      = {
            '매수': [],
            '매도': []
        }

        self.jgrv_count       = 0
        self.int_tujagm       = 0
        self.비중조절기준        = 0

        self.market_gubun     = 1
        self.ma_round_unit    = 3
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
        self.buy_hj_limit     = self.dict_set['주식매수시장가잔량범위']
        self.sell_hj_limit    = self.dict_set['주식매도시장가잔량범위']

        if self.is_tick:
            self.dict_findex['초당매도수금액'] = self.dict_findex['초당매수금액']
            self.dict_findex['누적초당매도수수량'] = self.dict_findex['누적초당매수수량']
        else:
            self.dict_findex['분당매도수금액'] = self.dict_findex['분당매수금액']
            self.dict_findex['누적분당매도수수량'] = self.dict_findex['누적분당매수수량']

        self.dict_findex['당일매도수금액'] = self.dict_findex['당일매수금액']
        self.dict_findex['최고매도수금액'] = self.dict_findex['최고매수금액']
        self.dict_findex['최고매도수가격'] = self.dict_findex['최고매수가격']
        self.dict_findex['호가총잔량'] = self.dict_findex['매수총잔량']
        self.dict_findex['매도수호가잔량1'] = self.dict_findex['매수잔량1']

        if self.dict_set['전략연산프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.ms_analyzer = MicrostructureAnalyzer('stock')
        self.rk_analyzer = RiskAnalyzer('stock')

        set_builtin_print(False, self.mgzservQ)
        self.SetFormulaData()
        self.UpdateStringategy()
        self.Mainloop()

    def SetFormulaData(self):
        self.fm_list, dict_fm, self.fm_tcnt = get_formula_data(False, self.data_cnt)
        self.mgzservQ.put(('window', (ui_num['사용자수식'], deepcopy(self.fm_list), dict_fm, self.fm_tcnt)))
        if self.fm_list:
            for fm in self.fm_list:
                fm[8] = compile(fm[-2], '<string>', 'exec')

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

        self.SetGlobalsFunc()

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)

    def SetBuyStg(self, buytxt):
        self.buystrategy, indistg = get_buy_indi_stg(buytxt)
        if indistg is not None:
            try:
                exec(indistg)
            except:
                self.mgzservQ.put(('window', (ui_num['시스템로그'], f'{format_exc()}오류 알림 - {indistg}')))
            else:
                self.mgzservQ.put(('window', (ui_num['기본로그'], f'{self.indicator}')))
        self.indi_settings = list(self.indicator.values())

    def Mainloop(self):
        if self.gubun == 7:
            self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 전략연산 시작')))
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
                self.mgzservQ.put(('window', (ui_num['시스템로그'], get_profile_text(self.pr))))
        elif data == '프로세스종료':
            time.sleep(5)
            self.mgzservQ.put(('window', (ui_num['기본로그'], '시스템 명령 실행 알림 - 전략연산 종료')))

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

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
        new_data = data[:self.base_cnt]
        new_data[self.vitime_cnt] = int(str_ymdhms(VI해제시간))
        new_data_tick[:self.base_cnt] = new_data

        pre_data = self.dict_data.get(종목코드)
        if pre_data is not None:
            self.dict_data[종목코드] = np.concatenate([pre_data, [new_data_tick]])
        else:
            self.dict_data[종목코드] = np.array([new_data_tick])

        self.arry_code = self.dict_data[종목코드]
        self.tick_count = 데이터길이 = len(self.arry_code)
        self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

        리스크점수 = 0
        if 데이터길이 >= 평균값계산틱수:
            self.arry_code[-1, self.base_cnt:self.data_cnt] = self.GetParameterArea(rw)

            if self.dict_set['시장미시구조분석']:
                self.ms_analyzer.update_data(self.code, self.arry_code)
            if self.dict_set['시장리스크분석']:
                리스크점수 = self.rk_analyzer.get_risk_score(self.arry_code)

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
                exec(v)

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
                        price = self.arry_code[self.indexn, self.dict_findex[fname]]
                        self.arry_code[self.indexn, col_idx] = price

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
                        exec(self.buystrategy)

                elif C:
                    매수 = False
                    분할매수기준수익률 = round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['주식매수분할고정수익률'] else 수익률
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
            E = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도익절수익률청산'] and 수익률 > self.dict_set['주식매도익절수익률']
            F = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도익절수익금청산'] and 수익금 > self.dict_set['주식매도익절수익금']
            G = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
            H = NIB and NIS and 매수가 != 0 and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']

            if SBT and (A or (B and C) or C or D or E or F or G or H):
                강제청산 = E or F or G or H
                전량매도 = A or 강제청산
                self.info_for_signal = D, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                매도 = False
                if A or (B and C) or D:
                    if self.sellstrategy is not None:
                        exec(self.sellstrategy)

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
            self.mgzservQ.put(('window', (ui_num['실시간차트'], 종목코드, self.arry_code[-1800:, :])))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.mgzservQ.put(('window', (ui_num['타임로그'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))

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
            주문수량 = 0
        else:
            주문수량 = self.GetBuyCount(분할매수횟수, 매수가, 현재가, 저가대비고가등락율)

        if '지정가' in self.dict_set['주식매수주문구분']:
            기준가격 = 현재가
            if self.dict_set['주식매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.dict_signal['매수'].append(self.code)
            self.dict_signal_num[self.code] = self.indexn
            self.straderQ.put(('매수', self.code, self.name, 기준가격, 주문수량, now(), False))
        else:
            호가배열 = self.shogainfo[:self.buy_hj_limit]
            잔량배열 = self.shreminfo[:self.buy_hj_limit]
            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                예상체결가 = int(거래금액 / 주문수량 + 0.5) if 주문수량 != 0 else 0
                self.dict_signal['매수'].append(self.code)
                self.dict_signal_num[self.code] = self.indexn
                self.straderQ.put(('매수', self.code, self.name, 예상체결가, 주문수량, now(), False))

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
            elif self.dict_set['주식비중조절'][0] == 4:
                비중조절기준 = self._당일거래대금각도(30)
            else:
                비중조절기준 = self.비중조절기준

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
            주문수량 = 0
        elif 전량매도:
            주문수량 = 보유수량
        else:
            주문수량 = self.GetSellCount(분할매도횟수, 보유수량)

        if '지정가' in self.dict_set['주식매도주문구분'] and not 강제청산:
            기준가격 = 현재가
            if self.dict_set['주식매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1
            if self.dict_set['주식매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1
            self.dict_signal['매도'].append(self.code)
            self.straderQ.put(('매도', self.code, self.name, 기준가격, 주문수량, now(), False))
        else:
            호가배열 = self.bhogainfo[:self.sell_hj_limit]
            잔량배열 = self.bhreminfo[:self.sell_hj_limit]
            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                예상체결가 = int(거래금액 / 주문수량 + 0.5) if 주문수량 != 0 else 0
                self.dict_signal['매도'].append(self.code)
                self.straderQ.put(('매도', self.code, self.name, 예상체결가, 주문수량, now(), True if 강제청산 else False))

    def GetSellCount(self, 분할매도횟수, 보유수량):
        if self.dict_set['주식매도분할횟수'] == 1:
            return 보유수량
        else:
            dict_ratio = dict_order_ratio[self.dict_set['주식매도분할방법']][self.dict_set['주식매도분할횟수']]
            oc_ratio = dict_ratio[분할매도횟수]
            if 분할매도횟수 == 0:
                매도수량 = int(보유수량 * oc_ratio / 100)
            else:
                보유비율 = sum(비율 for 횟수, 비율 in dict_ratio.items() if 횟수 >= 분할매도횟수)
                매도수량 = int(보유수량 / 보유비율 * oc_ratio)

            if 매도수량 > 보유수량 or 분할매도횟수 + 1 == self.dict_set['주식매도분할횟수']:
                매도수량 = 보유수량

            return 매도수량

    def PutGsjmAndDeleteHilo(self):
        if self.dict_gj:
            self.dict_gj = dict(sorted(self.dict_gj.items(), key=lambda x: x[1]['dm'], reverse=True))
            df_gj = pd.DataFrame.from_dict(self.dict_gj, orient='index')
            self.mgzservQ.put(('window', (ui_num['S관심종목'], self.gubun, df_gj)))
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
                self.mgzservQ.put(('window', (ui_num['기본로그'], f'시스템 명령 실행 알림 - 전략연산 프로세스 데이터 저장 중 ... [{self.gubun + 1}]{i + 1}/{last}')))
            save_time = (now() - start).total_seconds()
            self.mgzservQ.put(('window', (ui_num['기본로그'], f'시스템 명령 실행 알림 - 데이터 저장 쓰기소요시간은 [{save_time:.6f}]초입니다.')))
        con.close()

        if self.gubun != 7:
            self.sstgQs[self.gubun + 1].put(('데이터저장', codes))
        else:
            self.sstgQs[self.gubun].put('프로세스종료')
