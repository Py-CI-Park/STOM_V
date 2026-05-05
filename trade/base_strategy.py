
import time
import sqlite3
import numpy as np
import pandas as pd
from copy import deepcopy
from traceback import format_exc
from trade.analyzer_risk import AnalyzerRisk
from trade.stg_globals_func import StgGlobalsFunc
from trade.manager_formula import get_formula_data
from trade.analyzer_pattern import AnalyzerPattern
from trade.analyzer_microstruc import AnalyzerMicrostructure
from utility.settings.setting_base import indicator, DB_SETTING
from utility.settings.setting_base import DB_STRATEGY, ui_num, dict_order_ratio
# noinspection PyUnusedImports
from utility.static_method.static import now, timedelta_sec, str_ymdhms, get_ema_list, set_builtin_print, \
    get_indicator


class BaseStrategy(StgGlobalsFunc):
    """실시간 전략 연산을 담당하는 기본 클래스입니다.
    매수/매도 전략을 컴파일하고, 보조지표를 설정하며,
    실시간 데이터를 기반으로 전략을 실행합니다.
    """

    def __init__(self, gubun, qlist, dict_set, market_info):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ
           0        1       2      3       4      5      6      7       8        9       10     11
        """
        super().__init__()
        self.gubun           = gubun
        self.windowQ         = qlist[0]
        self.teleQ           = qlist[3]
        self.traderQ         = qlist[9]
        self.stgQs           = qlist[10]
        self.stgQ            = qlist[10][self.gubun]
        self.dict_set        = dict_set
        self.indicator       = indicator
        self.market_gubun    = market_info[0]
        self.market_info     = market_info[1]
        self.is_etfn         = self.market_gubun in (2, 3)

        self.is_running      = True
        self.buystrategy     = None
        self.sellstrategy    = None
        self.chart_code      = None
        self.arry_code       = None
        self.info_for_buy    = None
        self.info_for_sell   = None

        self.dict_data: dict[str, list] = {}
        self.dict_gj: dict[str, dict[str, int | float]] = {}
        self.dict_jg: dict[str, dict[str, int | float]] = {}
        self.dict_profit: dict[str, list] = {}

        if self.market_gubun < 6:
            self.dict_signal = {
                '매수': [],
                '매도': []
            }
        else:
            self.dict_signal = {
                'BUY_LONG': [],
                'SELL_SHORT': [],
                'SELL_LONG': [],
                'BUY_SHORT': []
            }

        self.dict_info       = {}
        self.dict_buy_num    = {}
        self.dict_signal_num = {}
        self.indi_settings   = []
        self.black_list      = []

        self.jgrv_count      = 0
        self.int_tujagm      = 0
        self.비중조절기준       = 0
        self.vitime_cnt      = 0

        self.avg_list        = [self.dict_set['평균값계산틱수']]
        self.rolling_window  = self.dict_set['평균값계산틱수']

        self.is_tick         = self.dict_set['타임프레임']
        self.buy_hj_limit    = self.dict_set['매수시장가잔량범위']
        self.sell_hj_limit   = self.dict_set['매도시장가잔량범위']
        self.set_weight      = self.dict_set['비중조절']
        self.sma_list        = get_ema_list(self.is_tick)

        self.ma_round_unit   = self.market_info['반올림단위']
        angle_cf             = self.market_info['각도계수'][self.is_tick]
        self.angle_pct_cf    = angle_cf[0]
        self.angle_dtm_cf    = angle_cf[1]
        factor_list          = self.market_info['팩터목록'][self.is_tick]
        self.dict_findex     = {factor: i for i, factor in enumerate(factor_list)}
        self.data_cnt        = self.market_info['팩터개수'][self.is_tick]

        self.base_cnt        = self.dict_findex['관심종목'] + 1
        self.area_cnt        = self.dict_findex['당일거래대금각도'] + 1
        if self.market_gubun < 4:
            self.vitime_cnt  = self.dict_findex['VI해제시간']

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

        self.ms_analyzer = AnalyzerMicrostructure(self.market_info['마켓구분'], factor_list)
        self.rk_analyzer = AnalyzerRisk(self.market_info['마켓구분'], factor_list)
        self.pt_analyzer = AnalyzerPattern(self.market_info)

        set_builtin_print(self.windowQ)
        self._set_formula_data()
        self._set_strategy_and_blacklist()
        self._main_loop()

    def _set_formula_data(self):
        """공식 데이터를 설정합니다."""
        self.fm_list, dict_fm, self.fm_tcnt = get_formula_data(False, self.data_cnt)
        self.windowQ.put((ui_num['사용자수식'], deepcopy(self.fm_list), dict_fm, self.fm_tcnt))
        if self.fm_list:
            for fm in self.fm_list:
                fm[8] = compile(fm[-2], '<string>', 'exec')

    def _set_strategy_and_blacklist(self):
        """전략과 블랙리스트를 설정합니다."""
        first_name               = self.market_info['전략구분']
        table_name_stg_buy       = f"{first_name}_buy"
        table_name_stg_sell      = f"{first_name}_sell"
        table_name_stg_optibuy   = f"{first_name}_optibuy"
        table_name_stg_optisell  = f"{first_name}_optisell"
        table_name_stg_passticks = f"{first_name}_passticks"
        con  = sqlite3.connect(DB_STRATEGY)
        dfb  = pd.read_sql(f'SELECT * FROM {table_name_stg_buy}', con).set_index('index')
        dfs  = pd.read_sql(f'SELECT * FROM {table_name_stg_sell}', con).set_index('index')
        dfob = pd.read_sql(f'SELECT * FROM {table_name_stg_optibuy}', con).set_index('index')
        dfos = pd.read_sql(f'SELECT * FROM {table_name_stg_optisell}', con).set_index('index')
        dfpt = pd.read_sql(f'SELECT * FROM {table_name_stg_passticks}', con).set_index('index')
        con.close()

        self._set_strategy(dfs, dfos, dfb, dfob)
        if len(dfpt) > 0:
            self._set_passticks(dfpt)

        con  = sqlite3.connect(DB_SETTING)
        dfbl = pd.read_sql('SELECT * FROM strategy', con).set_index('index')
        con.close()

        blacklist = dfbl['블랙리스트'][0]
        if blacklist != '':
            self.black_list = blacklist.split(';')

        self.set_globals_func()

    def _update_globals_func(self, dict_add_func):
        """전역 함수를 업데이트합니다.
        Args:
            dict_add_func (dict): 추가할 전역 함수 딕셔너리
        """
        globals().update(dict_add_func)

    def _set_strategy(self, dfs, dfos, dfb, dfob):
        """전략을 설정합니다.
        Args:
            dfs: 매수 전략
            dfos: 매도 전략
            dfb: 매수 블랙리스트
            dfob: 매도 블랙리스트
        """
        if self.dict_set['매도전략'] in dfs.index:
            self.sellstrategy = compile(dfs['전략코드'][self.dict_set['매도전략']], '<string>', 'exec')
        elif self.dict_set['매도전략'] in dfos.index:
            self.sellstrategy = compile(dfos['전략코드'][self.dict_set['매도전략']], '<string>', 'exec')

        buytxt = ''
        if self.dict_set['매수전략'] in dfb.index:
            buytxt = dfb['전략코드'][self.dict_set['매수전략']]
        elif self.dict_set['매수전략'] in dfob.index:
            buytxt = dfob['전략코드'][self.dict_set['매수전략']]
            vars_text = dfob['변수값'][self.dict_set['매수전략']]
            if vars_text != '':
                vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                self.vars = {i: var for i, var in enumerate(vars_list)}

        self._set_buy_strategy(buytxt)

    def _set_buy_strategy(self, buytxt):
        """매수 전략을 설정합니다.
        Args:
            buytxt: 매수 전략 텍스트
        """
        self.buystrategy, indistg = self.get_buy_indi_stg(buytxt)
        if indistg is not None:
            try:
                exec(indistg)
            except Exception:
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - indistg'))
        self.indi_settings = list(self.indicator.values())

    def get_buy_indi_stg(self, buytxt):
        """매수 지표 전략을 반환합니다.
        Args:
            buytxt: 매수 전략 텍스트
        Returns:
            지표 전략 텍스트
        """
        lines   = [line for line in buytxt.split('\n') if line and line[0] != '#']
        buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
        indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
        if buystg:
            try:
                buystg = compile(buystg, '<string>', 'exec')
            except Exception:
                buystg = None
        else:
            buystg = None
        if indistg:
            try:
                indistg = compile(indistg, '<string>', 'exec')
            except Exception:
                indistg = None
        else:
            indistg = None
        return buystg, indistg

    def _set_passticks(self, dfpt):
        """패스 틱을 설정합니다.
        Args:
            dfpt: 패스 틱 데이터프레임
        """
        def compile_condition(x):
            return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')

        name_list = list(dfpt.index)
        stg_list  = dfpt['전략코드'].to_list()
        stg_list  = [compile_condition(x) for x in stg_list]
        self.dict_condition = dict(zip(name_list, stg_list))

    def _main_loop(self):
        """메인 루프를 실행합니다."""
        self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 전략 연산 시작"))
        while self.is_running:
            try:
                data = self.stgQ.get()
                if data.__class__ == list:
                    if self.market_gubun < 6:
                        if self.is_tick:
                            self._strategy_tick(data)
                        else:
                            self._strategy_min(data)
                    else:
                        if self.is_tick:
                            self._strategy_future_tick(data)
                        else:
                            self._strategy_future_min(data)
                elif data.__class__ == tuple:
                    self._update_tuple(data)
                elif data.__class__ == str:
                    self._update_string(data)
            except Exception:
                from traceback import format_exc
                self.windowQ.put((ui_num['시스템로그'], format_exc()))

        import sys
        time.sleep(1)
        sys.exit()

    def _update_tuple(self, data):
        """튜플을 업데이트합니다.
        Args:
            data: 데이터
        """
        gubun, data = data
        if gubun == '잔고목록':
            self.dict_jg = data
            self.jgrv_count += 1
            if self.jgrv_count == 2:
                self.jgrv_count = 0
                self._put_gsjm_and_delete_profit()
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
        elif '_COMPLETE' in gubun:
            gubun = gubun.replace('_COMPLETE', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
            if gubun in ('BUY_LONG', 'SELL_SHORT'):
                self.dict_buy_num[data] = self.dict_signal_num.get(data, len(self.dict_data[data]) - 1)
        elif '_CANCEL' in gubun:
            gubun = gubun.replace('_CANCEL', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
        elif '_MANUAL' in gubun:
            gubun = gubun.replace('_MANUAL', '')
            if data not in self.dict_signal[gubun]:
                self.dict_signal[gubun].append(data)
        elif gubun == '관심목록':
            self.dict_gj = {k: v for k, v in self.dict_gj.items() if k in data}
        elif gubun == '매수전략':
            self._set_buy_strategy(data)
        elif gubun == '매도전략':
            self.sellstrategy = compile(data, '<string>', 'exec')
        elif gubun == '종목당투자금':
            self.int_tujagm = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
            self._set_strategy_and_blacklist()
        elif gubun == '종목정보':
            self.dict_info = data
        elif gubun == '데이터저장':
            self._save_data(data)

    def _update_string(self, data):
        """문자열을 업데이트합니다.
        Args:
            data: 데이터
        """
        if data == '매수전략중지':
            self.buystrategy = None
            self.teleQ.put('매수전략 중지 완료')
        elif data == '매도전략중지':
            self.sellstrategy = None
            self.teleQ.put('매도전략 중지 완료')
        elif data == '프로세스종료':
            self.is_running = False
            self.windowQ.put((ui_num['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 전략연산 종료"))

    # noinspection PyUnusedLocal
    def _strategy_tick(self, data):
        """틱 전략을 실행합니다.
        Args:
            data: 데이터
        """
        if self.market_gubun < 4:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                VI해제시간, VI가격, VI호가단위, \
                초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data
            data[self.vitime_cnt] = int(str_ymdhms(VI해제시간))
        elif self.market_gubun == 4:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data
        else:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data

        시분초, 순매수금액 = int(str(체결시간)[8:]), 초당매수금액 - 초당매도금액
        self.hoga_unit = 호가단위 = self._get_hogaunit(현재가)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
        new_data_tick[:self.base_cnt] = data[:self.base_cnt]

        pre_data = self.dict_data.get(종목코드)
        if pre_data is not None:
            self.dict_data[종목코드] = np.concatenate([pre_data, [new_data_tick]])
        else:
            self.dict_data[종목코드] = np.array([new_data_tick])

        self.arry_code = self.dict_data[종목코드]
        self.tick_count = 데이터길이 = len(self.arry_code)
        self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

        리스크점수 = 0
        if 데이터길이 >= self.rolling_window:
            self.arry_code[-1, self.base_cnt:self.data_cnt] = self._get_parameter_area(self.rolling_window)

            if self.dict_set['시장미시구조분석']:
                self.ms_analyzer.update_data(self.code, self.arry_code)
            if self.dict_set['시장리스크분석']:
                리스크점수 = self.rk_analyzer.get_risk_score(self.arry_code)

        self._update_high_low(종목코드, 현재가)

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(v)

        if 데이터길이 >= self.rolling_window and self.fm_list:
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

        if 데이터길이 >= self.rolling_window:
            jg_data = self.dict_jg.get(종목코드)
            if jg_data:
                if 종목코드 not in self.dict_buy_num:
                    self.dict_buy_num[종목코드] = self.indexn
                _, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = jg_data.values()
                _, 수익금, 수익률 = self._get_profit(매입금액, 보유수량 * 현재가)
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
                보유시간 = self._get_hold_time(매수시간)
                매수틱번호 = self.dict_buy_num[종목코드]
            else:
                매수틱번호, 수익금, 수익률, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, \
                    최고수익률, 최저수익률 = 0, 0, 0, 0, 0, 0, 0, now(), 0, 0, 0

            self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

            BBT = not self.dict_set['매수금지시간'] or \
                not (self.dict_set['매수금지시작시간'] < 시분초 < self.dict_set['매수금지종료시간'])
            BLK = not self.dict_set['매수금지블랙리스트'] or 종목명 not in self.black_list
            NIB = 종목코드 not in self.dict_signal['매수']
            NIS = 종목코드 not in self.dict_signal['매도']

            A = 관심종목 and NIB and 매수가 == 0
            B = self.dict_set['매수분할시그널']
            C = NIB and 매수가 != 0 and 분할매수횟수 < self.dict_set['매수분할횟수']
            D = NIB and self.dict_set['매도취소매수시그널'] and not NIS

            if BBT and BLK and (A or (B and C) or C or D):
                self.info_for_buy = D, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                if A or (B and C) or D:
                    매수 = True
                    if self.buystrategy is not None:
                        exec(self.buystrategy)

                elif C:
                    매수 = False
                    분할매수기준수익률 = \
                        round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['매수분할고정수익률'] else 수익률
                    if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                        매수 = True
                    elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                        매수 = True

                    if 매수:
                        self.Buy()

            SBT = not self.dict_set['매도금지시간'] or \
                not (self.dict_set['매도금지시작시간'] < 시분초 < self.dict_set['매도금지종료시간'])
            SCC = self.dict_set['매수분할횟수'] == 1 or \
                not self.dict_set['매도금지매수횟수'] or 분할매수횟수 > self.dict_set['매도금지매수횟수값']
            NIB = 종목코드 not in self.dict_signal['매수']

            A = NIB and NIS and SCC and 매수가 != 0 and self.dict_set['매도분할횟수'] == 1
            B = self.dict_set['매도분할시그널']
            C = NIB and NIS and SCC and 매수가 != 0 and 분할매도횟수 < self.dict_set['매도분할횟수']
            D = NIS and self.dict_set['매수취소매도시그널'] and not NIB
            E = NIB and NIS and 매수가 != 0 and self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
            F = NIB and NIS and 매수가 != 0 and self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
            G = NIB and NIS and 매수가 != 0 and self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
            H = NIB and NIS and 매수가 != 0 and self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']

            if SBT and (A or (B and C) or C or D or E or F or G or H):
                강제청산 = E or F or G or H
                전량매도 = A or 강제청산
                self.info_for_sell = D, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                매도 = False
                if A or (B and C) or D:
                    if self.sellstrategy is not None:
                        exec(self.sellstrategy)

                elif C or 강제청산:
                    if C:
                        if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                            매도 = True
                        elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
                            매도 = True
                    elif 강제청산:
                        매도 = True

                    if 매도:
                        self.Sell()

        if 관심종목:
            """['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']"""
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

        if self.chart_code == 종목코드 and 데이터길이 >= self.rolling_window:
            self.windowQ.put((ui_num['실시간차트'], 종목코드, self.arry_code))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.windowQ.put((ui_num['타임로그'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))

    # noinspection PyUnusedLocal
    def _strategy_min(self, data):
        """분봉 전략을 실행합니다.
        Args:
            data: 데이터
        """
        if self.market_gubun < 4:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                VI해제시간, VI가격, VI호가단위, 분봉시가, 분봉고가, 분봉저가, \
                분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data
            data[self.vitime_cnt] = int(str_ymdhms(VI해제시간))
        elif self.market_gubun == 4:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                분봉시가, 분봉고가, 분봉저가, \
                분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data
        else:
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                분봉시가, 분봉고가, 분봉저가, \
                분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data

        시분초, 순매수금액 = int(str(체결시간)[8:] + '00'), 분당매수금액 - 분당매도금액
        self.hoga_unit = 호가단위 = self._get_hogaunit(현재가)

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
            self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

            if 데이터길이 >= self.rolling_window:
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self._get_parameter_area(self.rolling_window)

            패턴점수, 패턴신뢰도 = 0, 0
            if self.dict_set['패턴인식분석'] and 데이터길이 >= 5:
                패턴점수, 패턴신뢰도 = self.pt_analyzer.analyze_patterns(self.code, self.arry_code)

            indicator_list = get_indicator(
                self.arry_code[:, self.dict_findex['현재가']],
                self.arry_code[:, self.dict_findex['분봉고가']],
                self.arry_code[:, self.dict_findex['분봉저가']],
                self.arry_code[:, self.dict_findex['분당거래대금']],
                self.indi_settings
            )
            self.arry_code[-1, self.area_cnt:self.data_cnt] = indicator_list

            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, \
                OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = indicator_list

            self._update_high_low(종목코드, 분봉고가, 분봉저가)

            if self.dict_condition:
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    exec(v)

            if 데이터길이 >= self.rolling_window and self.fm_list:
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

            if 데이터길이 >= self.rolling_window:
                jg_data = self.dict_jg.get(종목코드)
                if jg_data:
                    if 종목코드 not in self.dict_buy_num:
                        self.dict_buy_num[종목코드] = self.indexn
                    _, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = jg_data.values()
                    _, 수익금, 수익률 = self._get_profit(매입금액, 보유수량 * 현재가)
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
                    보유시간 = self._get_hold_time_min(매수시간)
                    매수틱번호 = self.dict_buy_num[종목코드]
                else:
                    매수틱번호, 수익금, 수익률, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, \
                        최고수익률, 최저수익률 = 0, 0, 0, 0, 0, 0, 0, now(), 0, 0, 0

                self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

                BBT = not self.dict_set['매수금지시간'] or \
                    not (self.dict_set['매수금지시작시간'] < 시분초 < self.dict_set['매수금지종료시간'])
                BLK = not self.dict_set['매수금지블랙리스트'] or 종목명 not in self.black_list
                NIB = 종목코드 not in self.dict_signal['매수']
                NIS = 종목코드 not in self.dict_signal['매도']

                A = 관심종목 and NIB and 매수가 == 0
                B = self.dict_set['매수분할시그널']
                C = NIB and 매수가 != 0 and 분할매수횟수 < self.dict_set['매수분할횟수']
                D = NIB and self.dict_set['매도취소매수시그널'] and not NIS

                if BBT and BLK and (A or (B and C) or C or D):
                    self.info_for_signal = D, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    if A or (B and C) or D:
                        매수 = True
                        if self.buystrategy is not None:
                            exec(self.buystrategy)

                    elif C:
                        매수 = False
                        분할매수기준수익률 = round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set[
                            '매수분할고정수익률'] else 수익률
                        if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                            매수 = True
                        elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                            매수 = True

                        if 매수:
                            self.Buy()

                SBT = not self.dict_set['매도금지시간'] or \
                    not (self.dict_set['매도금지시작시간'] < 시분초 < self.dict_set['매도금지종료시간'])
                SCC = self.dict_set['매수분할횟수'] == 1 or \
                    not self.dict_set['매도금지매수횟수'] or 분할매수횟수 > self.dict_set['매도금지매수횟수값']
                NIB = 종목코드 not in self.dict_signal['매수']

                A = NIB and NIS and SCC and 매수가 != 0 and self.dict_set['매도분할횟수'] == 1
                B = self.dict_set['매도분할시그널']
                C = NIB and NIS and SCC and 매수가 != 0 and 분할매도횟수 < self.dict_set['매도분할횟수']
                D = NIS and self.dict_set['매수취소매도시그널'] and not NIB
                E = NIB and NIS and 매수가 != 0 and \
                    self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
                F = NIB and NIS and 매수가 != 0 and \
                    self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']

                if SBT and (A or (B and C) or C or D or E or F):
                    강제청산 = E or F
                    전량매도 = A or 강제청산
                    self.info_for_signal = \
                        D, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    매도 = False
                    if A or (B and C) or D:
                        if self.sellstrategy is not None:
                            exec(self.sellstrategy)

                    elif C or 강제청산:
                        if C:
                            if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                                매도 = True
                            elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
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
            """['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']"""
            self.dict_gj[종목코드] = {
                '종목명': 종목명,
                'per': 등락율,
                'hlp': 고저평균대비등락율,
                'lhp': 저가대비고가등락율,
                'ch': 체결강도,
                'tm': 분당거래대금,
                'dm': 당일거래대금,
                'bm': 당일매수금액,
                'sm': 당일매도금액
            }

        if self.chart_code == 종목코드 and 데이터길이 >= self.rolling_window:
            if not 전략연산:
                new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
                new_data_tick[:self.base_cnt] = data[:self.base_cnt]
                self.arry_code = np.concatenate([pre_data, [new_data_tick]])
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self._get_parameter_area(self.rolling_window)
                self.arry_code[-1, self.area_cnt:self.data_cnt] = get_indicator(
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

    # noinspection PyUnusedLocal
    def _strategy_future_tick(self, data):
        """선물 틱 전략을 실행합니다.
        Args:
            data: 데이터
        """
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
            초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
            당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data

        시분초, 순매수금액 = int(str(체결시간)[8:]), 초당매수금액 - 초당매도금액
        self.hoga_unit = 호가단위 = self._get_hogaunit(종목코드)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
        new_data_tick[:self.base_cnt] = data[:self.base_cnt]

        pre_data = self.dict_data.get(종목코드)
        if pre_data is not None:
            self.dict_data[종목코드] = np.concatenate([pre_data, [new_data_tick]])
        else:
            self.dict_data[종목코드] = np.array([new_data_tick])

        self.arry_code = self.dict_data[종목코드]
        self.tick_count = 데이터길이 = len(self.arry_code)
        self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

        리스크점수 = 0
        if 데이터길이 >= self.rolling_window:
            self.arry_code[-1, self.base_cnt:self.data_cnt] = self._get_parameter_area(self.rolling_window)

            if self.dict_set['시장미시구조분석']:
                self.ms_analyzer.update_data(self.code, self.arry_code)
            if self.dict_set['시장리스크분석']:
                리스크점수 = self.rk_analyzer.get_risk_score(self.arry_code)

        self._update_high_low(종목코드, 현재가)

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(v)

        if 데이터길이 >= self.rolling_window and self.fm_list:
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

        if 데이터길이 >= self.rolling_window:
            jg_data = self.dict_jg.get(종목코드)
            if jg_data:
                if 종목코드 not in self.dict_buy_num:
                    self.dict_buy_num[종목코드] = self.indexn
                _, 포지션, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 레버리지 = jg_data.values()
                if 포지션 == 'LONG':
                    _, 수익금, 수익률 = self._get_profit_long(매입금액, 보유수량 * 현재가)
                else:
                    _, 수익금, 수익률 = self._get_profit_short(매입금액, 보유수량 * 현재가)
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
                보유시간 = self._get_hold_time(매수시간)
                매수틱번호 = self.dict_buy_num[종목코드]
            else:
                포지션, 매수틱번호, 수익금, 수익률, 레버리지, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, \
                    최고수익률, 최저수익률 = None, 0, 0, 0, 1, 0, 0, 0, 0, now(), 0, 0, 0

            self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

            BBT  = not self.dict_set['매수금지시간'] or \
                not (self.dict_set['매수금지시작시간'] < 시분초 < self.dict_set['매수금지종료시간'])
            BLK  = not self.dict_set['매수금지블랙리스트'] or 종목명 not in self.black_list
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
            NISL = 종목코드 not in self.dict_signal['SELL_LONG']
            NIBS = 종목코드 not in self.dict_signal['BUY_SHORT']
            A    = 관심종목 and NIBL and 포지션 is None
            B    = 관심종목 and NISS and 포지션 is None
            C    = self.dict_set['매수분할시그널']
            D    = NIBL and 포지션 == 'LONG' and 분할매수횟수 < self.dict_set['매수분할횟수']
            E    = NISS and 포지션 == 'SHORT' and 분할매수횟수 < self.dict_set['매수분할횟수']
            F    = NIBL and self.dict_set['매도취소매수시그널'] and not NISL
            G    = NISS and self.dict_set['매도취소매수시그널'] and not NIBS

            if BBT and BLK and (A or B or (C and D) or (C and E) or D or E or F or G):
                self.info_for_buy = F or G, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                if A or B or (C and (D or E)) or F or G:
                    BUY_LONG, SELL_SHORT = True, True
                    if self.buystrategy is not None:
                        exec(self.buystrategy)

                elif D or E:
                    BUY_LONG, SELL_SHORT = False, False
                    분할매수기준수익률 = \
                        round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['매수분할고정수익률'] else 수익률
                    if D:
                        if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                            BUY_LONG   = True
                        elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                            BUY_LONG   = True
                    elif E:
                        if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                            SELL_SHORT = True
                        elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                            SELL_SHORT = True

                    if BUY_LONG or SELL_SHORT:
                        self.Buy(BUY_LONG)

            SBT  = not self.dict_set['매도금지시간'] or \
                not (self.dict_set['매도금지시작시간'] < 시분초 < self.dict_set['매도금지종료시간'])
            SCC  = self.dict_set['매수분할횟수'] == 1 or \
                not self.dict_set['매도금지매수횟수'] or 분할매수횟수 > self.dict_set['매도금지매수횟수값']
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']

            A = NIBL and NISL and SCC and 포지션 == 'LONG' and self.dict_set['매도분할횟수'] == 1
            B = NISS and NIBS and SCC and 포지션 == 'SHORT' and self.dict_set['매도분할횟수'] == 1
            C = self.dict_set['매도분할시그널']
            D = NIBL and NISL and SCC and 포지션 == 'LONG' and 분할매도횟수 < self.dict_set['매도분할횟수']
            E = NISS and NIBS and SCC and 포지션 == 'SHORT' and 분할매도횟수 < self.dict_set['매도분할횟수']
            F = NISL and self.dict_set['매수취소매도시그널'] and not NIBL
            G = NIBS and self.dict_set['매수취소매도시그널'] and not NISS
            H = NIBL and NISL and 포지션 == 'LONG' and \
                self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
            J = NISS and NIBS and 포지션 == 'SHORT' and \
                self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
            K = NIBL and NISL and 포지션 == 'LONG' and \
                self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
            L = NISS and NIBS and 포지션 == 'SHORT' and \
                self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
            M = NIBL and NISL and 포지션 == 'LONG' and \
                self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
            N = NISS and NIBS and 포지션 == 'SHORT' and \
                self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
            P = NIBL and NISL and 포지션 == 'LONG' and \
                self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']
            Q = NISS and NIBS and 포지션 == 'SHORT' and \
                self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']
            R = NIBL and NISL and 포지션 == 'LONG' and 수익률 * 레버리지 < -90
            S = NISS and NIBS and 포지션 == 'SHORT' and 수익률 * 레버리지 < -90

            if SBT and (A or B or (C and D) or (C and E) or D or E or F or G or H or J or K or L or M or N or P or Q or R or S):
                강제청산 = H or J or K or L or M or N or P or Q or R or S
                전량매도 = A or B or 강제청산
                self.info_for_sell = \
                    F or G, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                SELL_LONG, BUY_SHORT = False, False
                if A or B or (C and D) or (C and E) or F or G:
                    if self.sellstrategy is not None:
                        exec(self.sellstrategy)

                elif D or E or 강제청산:
                    if H or K or M or P or R:
                        SELL_LONG = True
                    elif J or L or N or Q or S:
                        BUY_SHORT = True
                    elif D:
                        if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                        elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                    elif E:
                        if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True
                        elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True

                    if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):
                        self.Sell(SELL_LONG)

        if 관심종목:
            """['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']"""
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

        if self.chart_code == 종목코드 and 데이터길이 >= self.rolling_window:
            self.windowQ.put((ui_num['실시간차트'], 종목코드, self.arry_code))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.windowQ.put((ui_num['타임로그'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))

    # noinspection PyUnusedLocal
    def _strategy_future_min(self, data):
        """선물 분봉 전략을 실행합니다.
        Args:
            data: 데이터
        """
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
            분봉시가, 분봉고가, 분봉저가, \
            분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
            당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
            매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간, 전략연산 = data

        시분초, 순매수금액 = int(str(체결시간)[8:] + '00'), 분당매수금액 - 분당매도금액
        self.hoga_unit = 호가단위 = self._get_hogaunit(종목코드)

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
            self.code, self.name, self.index, self.indexn = 종목코드, 종목명, 체결시간, 데이터길이 - 1

            if 데이터길이 >= self.rolling_window:
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self._get_parameter_area(self.rolling_window)

            패턴점수, 패턴신뢰도 = 0, 0
            if self.dict_set['패턴인식분석'] and 데이터길이 >= 5:
                패턴점수, 패턴신뢰도 = self.pt_analyzer.analyze_patterns(self.code, self.arry_code)

            indicator_list = get_indicator(
                self.arry_code[:, self.dict_findex['현재가']],
                self.arry_code[:, self.dict_findex['분봉고가']],
                self.arry_code[:, self.dict_findex['분봉저가']],
                self.arry_code[:, self.dict_findex['분당거래대금']],
                self.indi_settings
            )
            self.arry_code[-1, self.area_cnt:self.data_cnt] = indicator_list

            AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, \
                OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = indicator_list

            self._update_high_low(종목코드, 분봉고가, 분봉저가)

            if self.dict_condition:
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    try:
                        exec(v)
                    except Exception:
                        self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 경과틱수 연산오류'))

            if 데이터길이 >= self.rolling_window and self.fm_list:
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

            if 데이터길이 >= self.rolling_window:
                jg_data = self.dict_jg.get(종목코드)
                if jg_data:
                    if 종목코드 not in self.dict_buy_num:
                        self.dict_buy_num[종목코드] = self.indexn
                    _, 포지션, 매수가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 레버리지 = jg_data.values()
                    if 포지션 == 'LONG':
                        _, 수익금, 수익률 = self._get_profit_long(매입금액, 보유수량 * 현재가)
                    else:
                        _, 수익금, 수익률 = self._get_profit_short(매입금액, 보유수량 * 현재가)
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
                    보유시간 = self._get_hold_time_min(매수시간)
                    매수틱번호 = self.dict_buy_num[종목코드]
                else:
                    포지션, 매수틱번호, 수익금, 수익률, 레버리지, 매수가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, \
                        최고수익률, 최저수익률 = None, 0, 0, 0, 1, 0, 0, 0, 0, now(), 0, 0, 0

                self.profit, self.hold_time, self.indexb = 수익률, 보유시간, 매수틱번호

                BBT  = not self.dict_set['매수금지시간'] or \
                    not (self.dict_set['매수금지시작시간'] < 시분초 < self.dict_set['매수금지종료시간'])
                BLK  = not self.dict_set['매수금지블랙리스트'] or 종목명 not in self.black_list
                NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
                NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
                NISL = 종목코드 not in self.dict_signal['SELL_LONG']
                NIBS = 종목코드 not in self.dict_signal['BUY_SHORT']
                A    = 관심종목 and NIBL and 포지션 is None
                B    = 관심종목 and NISS and 포지션 is None
                C    = self.dict_set['매수분할시그널']
                D    = NIBL and 포지션 == 'LONG' and 분할매수횟수 < self.dict_set['매수분할횟수']
                E    = NISS and 포지션 == 'SHORT' and 분할매수횟수 < self.dict_set['매수분할횟수']
                F    = NIBL and self.dict_set['매도취소매수시그널'] and not NISL
                G    = NISS and self.dict_set['매도취소매수시그널'] and not NIBS

                if BBT and BLK and (A or B or (C and D) or (C and E) or D or E or F or G):
                    self.info_for_buy = F or G, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    if A or B or (C and (D or E)) or F or G:
                        BUY_LONG, SELL_SHORT = True, True
                        if self.buystrategy is not None:
                            try:
                                exec(self.buystrategy)
                            except Exception:
                                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매수전략'))
                    elif D or E:
                        BUY_LONG, SELL_SHORT = False, False
                        분할매수기준수익률 = \
                            round((현재가 / self._현재가N(-1) - 1) * 100, 2) if self.dict_set['매수분할고정수익률'] else 수익률
                        if D:
                            if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                                BUY_LONG   = True
                            elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                                BUY_LONG   = True
                        elif E:
                            if self.dict_set['매수분할하방'] and 분할매수기준수익률 < -self.dict_set['매수분할하방수익률']:
                                SELL_SHORT = True
                            elif self.dict_set['매수분할상방'] and 분할매수기준수익률 > self.dict_set['매수분할상방수익률']:
                                SELL_SHORT = True

                        if BUY_LONG or SELL_SHORT:
                            self.Buy(BUY_LONG)

                SBT  = not self.dict_set['매도금지시간'] or \
                    not (self.dict_set['매도금지시작시간'] < 시분초 < self.dict_set['매도금지종료시간'])
                SCC  = self.dict_set['매수분할횟수'] == 1 or \
                    not self.dict_set['매도금지매수횟수'] or 분할매수횟수 > self.dict_set['매도금지매수횟수값']
                NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
                NISS = 종목코드 not in self.dict_signal['SELL_SHORT']

                A = NIBL and NISL and SCC and 포지션 == 'LONG' and self.dict_set['매도분할횟수'] == 1
                B = NISS and NIBS and SCC and 포지션 == 'SHORT' and self.dict_set['매도분할횟수'] == 1
                C = self.dict_set['매도분할시그널']
                D = NIBL and NISL and SCC and 포지션 == 'LONG' and 분할매도횟수 < self.dict_set['매도분할횟수']
                E = NISS and NIBS and SCC and 포지션 == 'SHORT' and 분할매도횟수 < self.dict_set['매도분할횟수']
                F = NISL and self.dict_set['매수취소매도시그널'] and not NIBL
                G = NIBS and self.dict_set['매수취소매도시그널'] and not NISS
                H = NIBL and NISL and 포지션 == 'LONG' and \
                    self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
                J = NISS and NIBS and 포지션 == 'SHORT' and \
                    self.dict_set['매도익절수익률청산'] and 수익률 > self.dict_set['매도익절수익률']
                K = NIBL and NISL and 포지션 == 'LONG' and \
                    self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
                L = NISS and NIBS and 포지션 == 'SHORT' and \
                    self.dict_set['매도익절수익금청산'] and 수익금 > self.dict_set['매도익절수익금']
                M = NIBL and NISL and 포지션 == 'LONG' and \
                    self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
                N = NISS and NIBS and 포지션 == 'SHORT' and \
                    self.dict_set['매도손절수익률청산'] and 수익률 < -self.dict_set['매도손절수익률']
                P = NIBL and NISL and 포지션 == 'LONG' and \
                    self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']
                Q = NISS and NIBS and 포지션 == 'SHORT' and \
                    self.dict_set['매도손절수익금청산'] and 수익금 < -self.dict_set['매도손절수익금']
                R = NIBL and NISL and 포지션 == 'LONG' and 수익률 * 레버리지 < -90
                S = NISS and NIBS and 포지션 == 'SHORT' and 수익률 * 레버리지 < -90

                if SBT and (A or B or (C and D) or (C and E) or D or E or F or G or H or J or K or L or M or N or P or Q or R or S):
                    강제청산 = H or J or K or L or M or N or P or Q or R or S
                    전량매도 = A or B or 강제청산
                    self.info_for_sell = \
                        F or G, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1

                    SELL_LONG, BUY_SHORT = False, False
                    if A or B or (C and D) or (C and E) or F or G:
                        if self.sellstrategy is not None:
                            try:
                                exec(self.sellstrategy)
                            except Exception:
                                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매도전략'))

                    elif D or E or 강제청산:
                        if H or K or M or P or R:
                            SELL_LONG = True
                        elif J or L or N or Q or S:
                            BUY_SHORT = True
                        elif D:
                            if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                                SELL_LONG = True
                            elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
                                SELL_LONG = True
                        elif E:
                            if self.dict_set['매도분할하방'] and 수익률 < -self.dict_set['매도분할하방수익률'] * (분할매도횟수 + 1):
                                BUY_SHORT = True
                            elif self.dict_set['매도분할상방'] and 수익률 > self.dict_set['매도분할상방수익률'] * (분할매도횟수 + 1):
                                BUY_SHORT = True

                        if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):
                            self.Sell(SELL_LONG)

        else:
            pre_data = self.dict_data.get(종목코드)
            if pre_data is None:
                pre_data = np.empty((0, self.data_cnt + self.fm_tcnt), dtype=np.float64)
            self.tick_count = 데이터길이 = len(pre_data) + 1
            self.indexn = 데이터길이 - 1

        if 관심종목:
            """['종목명', 'per', 'hlp', 'lhp', 'ch', 'tm', 'dm', 'bm', 'sm']"""
            self.dict_gj[종목코드] = {
                '종목명': 종목명,
                'per': 등락율,
                'hlp': 고저평균대비등락율,
                'lhp': 저가대비고가등락율,
                'ch': 체결강도,
                'tm': 분당거래대금,
                'dm': 당일거래대금,
                'bm': 당일매수금액,
                'sm': 당일매도금액
            }

        if self.chart_code == 종목코드 and 데이터길이 >= self.rolling_window:
            if not 전략연산:
                new_data_tick = np.zeros(self.data_cnt + self.fm_tcnt, dtype=np.float64)
                new_data_tick[:self.base_cnt] = data[:self.base_cnt]
                self.arry_code = np.concatenate([pre_data, [new_data_tick]])
                self.arry_code[-1, self.base_cnt:self.area_cnt] = self._get_parameter_area(self.rolling_window)
                self.arry_code[-1, self.area_cnt:self.data_cnt] = get_indicator(
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

    def _get_parameter_area(self, rw):
        """구간연산 팩터의 값을 계산합니다.
        Args:
            rw: 롤링윈도우
        Returns:
            구간연산 팩터 리스트
        """
        if self.is_tick:
            return [
                self._이동평균(self.sma_list[0], calc=True), self._이동평균(self.sma_list[1], calc=True),
                self._이동평균(self.sma_list[2], calc=True), self._이동평균(self.sma_list[3], calc=True),
                self._이동평균(self.sma_list[4], calc=True), self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True),
                self._체결강도평균(rw, calc=True), self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True),
                self._최고초당매수수량(rw, calc=True), self._최고초당매도수량(rw, calc=True), self._누적초당매수수량(rw, calc=True),
                self._누적초당매도수량(rw, calc=True), self._초당거래대금평균(rw, calc=True), self._등락율각도(rw, calc=True),
                self._당일거래대금각도(rw, calc=True)
            ]
        else:
            return [
                self._이동평균(self.sma_list[0], calc=True), self._이동평균(self.sma_list[1], calc=True),
                self._이동평균(self.sma_list[2], calc=True), self._이동평균(self.sma_list[3], calc=True),
                self._이동평균(self.sma_list[4], calc=True), self._최고현재가(rw, calc=True), self._최저현재가(rw, calc=True),
                self._최고분봉고가(rw, calc=True), self._최저분봉저가(rw, calc=True), self._체결강도평균(rw, calc=True),
                self._최고체결강도(rw, calc=True), self._최저체결강도(rw, calc=True), self._최고분당매수수량(rw, calc=True),
                self._최고분당매도수량(rw, calc=True), self._누적분당매수수량(rw, calc=True), self._누적분당매도수량(rw, calc=True),
                self._분당거래대금평균(rw, calc=True), self._등락율각도(rw, calc=True), self._당일거래대금각도(rw, calc=True)
            ]

    def _update_high_low(self, 종목코드, 현재가또는분봉고가, 분봉저가=None):
        """고가 및 저가의 가격과 인덱스를 업데이트합니다.
        Args:
            종목코드: 종목 코드
            현재가또는분봉고가: 현재가 또는 분봉 고가
            분봉저가: 분봉 저가
        """
        if 분봉저가 is None:
            high_low = self.high_low.get(종목코드)
            if high_low:
                if 현재가또는분봉고가 >= high_low[0]:
                    high_low[0] = 현재가또는분봉고가
                    high_low[1] = self.indexn
                if 현재가또는분봉고가 <= high_low[2]:
                    high_low[2] = 현재가또는분봉고가
                    high_low[3] = self.indexn
            else:
                self.high_low[종목코드] = [현재가또는분봉고가, self.indexn, 현재가또는분봉고가, self.indexn]
        else:
            high_low = self.high_low.get(종목코드)
            if high_low:
                if 현재가또는분봉고가 >= high_low[0]:
                    high_low[0] = 현재가또는분봉고가
                    high_low[1] = self.indexn
                if 분봉저가 <= high_low[2]:
                    high_low[2] = 분봉저가
                    high_low[3] = self.indexn
            else:
                self.high_low[종목코드] = [현재가또는분봉고가, self.indexn, 분봉저가, self.indexn]

    def Buy(self, buy_long=False):
        """매수 주문을 실행합니다.
        Args:
            buy_long: 롱 매수 여부
        """
        취소시그널, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1 = self.info_for_buy
        if 취소시그널:
            주문수량 = 0
        else:
            주문수량 = self._get_buy_count(분할매수횟수, 매수가, 현재가, 저가대비고가등락율)

        if self.market_gubun < 6:
            signal_gubun = '매수'
        else:
            signal_gubun = 'BUY_LONG' if buy_long else 'SELL_SHORT'

        if '지정가' in self.dict_set['매수주문유형']:
            기준가격 = 현재가
            if self.dict_set['매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if self.market_gubun < 6 or buy_long else 매수호가1
            if self.dict_set['매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if self.market_gubun < 6 or buy_long else 매도호가1
            self.dict_signal[signal_gubun].append(self.code)
            self.dict_signal_num[self.code] = self.indexn
            self.traderQ.put((signal_gubun, self.code, self.name, 기준가격, 주문수량, now(), False))
        else:
            if self.market_gubun < 6 or buy_long:
                호가배열 = self.shogainfo[:self.buy_hj_limit]
                잔량배열 = self.shreminfo[:self.buy_hj_limit]
            else:
                호가배열 = self.bhogainfo[:self.buy_hj_limit]
                잔량배열 = self.bhreminfo[:self.buy_hj_limit]

            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                예상체결가 = self._get_order_price(거래금액, 주문수량)
                self.dict_signal[signal_gubun].append(self.code)
                self.dict_signal_num[self.code] = self.indexn
                self.traderQ.put((signal_gubun, self.code, self.name, 예상체결가, 주문수량, now(), False))

    def _get_buy_count(self, 분할매수횟수, 매수가, 현재가, 저가대비고가등락율):
        """매수 수량을 계산합니다.
        Args:
            분할매수횟수: 분할 매수 횟수
            매수가: 매수가
            현재가: 현재가
            저가대비고가등락율: 저가대비고가등락율
        Returns:
            매수 수량
        """
        if self.dict_set['비중조절'][0] == 0:
            betting = self.int_tujagm
        else:
            if self.dict_set['비중조절'][0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.dict_set['비중조절'][0] == 2:
                비중조절기준 = self._거래대금평균대비비율(30)
            elif self.dict_set['비중조절'][0] == 3:
                비중조절기준 = self._등락율각도(30)
            elif self.dict_set['비중조절'][0] == 4:
                비중조절기준 = self._당일거래대금각도(30)
            else:
                비중조절기준 = self.비중조절기준

            if 비중조절기준 < self.dict_set['비중조절'][1]:
                betting = self.int_tujagm * self.dict_set['비중조절'][5]
            elif 비중조절기준 < self.dict_set['비중조절'][2]:
                betting = self.int_tujagm * self.dict_set['비중조절'][6]
            elif 비중조절기준 < self.dict_set['비중조절'][3]:
                betting = self.int_tujagm * self.dict_set['비중조절'][7]
            elif 비중조절기준 < self.dict_set['비중조절'][4]:
                betting = self.int_tujagm * self.dict_set['비중조절'][8]
            else:
                betting = self.int_tujagm * self.dict_set['비중조절'][9]

        oc_ratio = dict_order_ratio[self.dict_set['매수분할방법']][self.dict_set['매수분할횟수']][분할매수횟수]
        매수수량 = self._set_buy_count(betting, 현재가, 매수가, oc_ratio)
        return 매수수량

    def Sell(self, sell_long=False):
        """매도 주문을 실행합니다.
        Args:
            sell_long: 롱 매도 여부
        """
        취소시그널, 전량매도, 강제청산, 보유수량, 분할매도횟수, 매수가, 현재가, 저가대비고가등락율, 매도호가1, 매수호가1 = self.info_for_sell
        if 취소시그널:
            주문수량 = 0
        elif 전량매도:
            주문수량 = 보유수량
        else:
            주문수량 = self._get_sell_count(분할매도횟수, 보유수량)

        if self.market_gubun < 6:
            signal_gubun = '매도'
        else:
            signal_gubun = 'SELL_LONG' if sell_long else 'BUY_SHORT'

        if '지정가' in self.dict_set['매도주문유형'] and not 강제청산:
            기준가격 = 현재가
            if self.dict_set['매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if self.market_gubun < 6 or sell_long else 매수호가1
            if self.dict_set['매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if self.market_gubun < 6 or sell_long else 매도호가1
            self.dict_signal[signal_gubun].append(self.code)
            self.traderQ.put((signal_gubun, self.code, self.name, 기준가격, 주문수량, now(), False))
        else:
            if self.market_gubun < 6 or sell_long:
                호가배열 = self.bhogainfo[:self.sell_hj_limit]
                잔량배열 = self.bhreminfo[:self.sell_hj_limit]
            else:
                호가배열 = self.shogainfo[:self.sell_hj_limit]
                잔량배열 = self.shreminfo[:self.sell_hj_limit]

            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                예상체결가 = self._get_order_price(거래금액, 주문수량)
                self.dict_signal[signal_gubun].append(self.code)
                self.traderQ.put((signal_gubun, self.code, self.name, 예상체결가, 주문수량, now(), True if 강제청산 else False))

    def _get_sell_count(self, 분할매도횟수, 보유수량):
        """매도 수량을 계산합니다.
        Args:
            분할매도횟수: 분할 매도 횟수
            보유수량: 보유 수량
        Returns:
            매도 수량
        """
        if self.dict_set['매도분할횟수'] == 1:
            return 보유수량
        else:
            dict_ratio = dict_order_ratio[self.dict_set['매도분할방법']][self.dict_set['매도분할횟수']]
            oc_ratio = dict_ratio[분할매도횟수]
            보유비율 = sum(비율 for 횟수, 비율 in dict_ratio.items() if 횟수 >= 분할매도횟수)
            매도수량 = self._set_sell_count(보유수량, 보유비율, oc_ratio)
            if 매도수량 > 보유수량 or 분할매도횟수 + 1 == self.dict_set['매도분할횟수']:
                매도수량 = 보유수량
            return 매도수량

    def _put_gsjm_and_delete_profit(self):
        """관심종목을 푸시하고 최고최저수익률 딕셔러니를 정리합니다."""
        if self.dict_gj:
            self.dict_gj = dict(sorted(self.dict_gj.items(), key=lambda x: x[1]['dm'], reverse=True))
            df_gj = pd.DataFrame.from_dict(self.dict_gj, orient='index')
            if self.market_gubun in (1, 4):
                self.windowQ.put((ui_num['관심종목'], self.gubun, df_gj))
            else:
                self.windowQ.put((ui_num['관심종목'], df_gj))
        if self.dict_profit:
            self.dict_profit = {k: v for k, v in self.dict_profit.items() if k in self.dict_jg}

    def _save_data(self, codes):
        """데이터를 저장합니다.
        Args:
            codes: 종목 코드들
        """
        if self.market_gubun not in (6, 7, 8):
            for code in self.dict_data.copy():
                if code not in codes:
                    del self.dict_data[code]

        last = len(self.dict_data)
        columns_ = self.market_info['팩터목록'][self.is_tick][:self.base_cnt]
        con = sqlite3.connect(self.market_info['당일디비'][self.is_tick])
        if last > 0:
            start = now()
            cllen = len(columns_)
            for i, code in enumerate(self.dict_data):
                df = pd.DataFrame(self.dict_data[code][:, :cllen], columns=columns_)
                df['index'] = df['index'].astype('int64')
                if self.market_gubun in (6, 7, 8):
                    name = self.dict_info[code]['종목명']
                    df.to_sql(name, con, index=False, if_exists='append', chunksize=2000)
                else:
                    df.to_sql(code, con, index=False, if_exists='append', chunksize=2000)
                log_text = f'시스템 명령 실행 알림 - 전략연산 프로세스 데이터 저장 중 ... [{self.gubun + 1}]{i + 1}/{last}'
                self.windowQ.put((ui_num['기본로그'], log_text))
            save_time = (now() - start).total_seconds()
            self.windowQ.put((ui_num['기본로그'], f'시스템 명령 실행 알림 - 데이터 저장 쓰기소요시간은 [{save_time:.6f}]초입니다.'))
        con.close()

        if self.market_gubun in (1, 4):
            if self.gubun != 7:
                self.stgQs[self.gubun + 1].put(('데이터저장', codes))
            else:
                for q in self.stgQs:
                    q.put('프로세스종료')
        else:
            self.stgQ.put('프로세스종료')

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return 0

    def _get_profit(self, 매입금액, 보유금액):
        """수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            수익
        """
        return 0

    def _get_profit_long(self, 매입금액, 보유금액):
        """롱 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            롱 수익
        """
        return 0

    def _get_profit_short(self, 매입금액, 보유금액):
        """숏 수익을 계산합니다.
        Args:
            매입금액: 매입 금액
            보유금액: 보유 금액
        Returns:
            숏 수익
        """
        return 0

    def _get_hold_time(self, 매수시간):
        """보유 시간을 계산합니다.
        Args:
            매수시간: 매수 시간
        Returns:
            보유 시간
        """
        return 0

    def _get_hold_time_min(self, 매수시간):
        """보유 시간(분)을 계산합니다.
        Args:
            매수시간: 매수 시간
        Returns:
            보유 시간(분)
        """
        return 0

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다.
        Args:
            betting: 베팅 금액
            현재가: 현재가
            매수가: 매수가
            oc_ratio: 분할 비율
        Returns:
            매수 수량
        """
        return 0

    def _set_sell_count(self, 보유수량, 보유비율, oc_ratio):
        """매도 수량을 설정합니다.
        Args:
            보유수량: 보유 수량
            보유비율: 보유 비율
            oc_ratio: 분할 비율
        Returns:
            매도 수량
        """
        return 0

    def _get_order_price(self, 거래금액, 주문수량):
        """주문 가격을 계산합니다.
        Args:
            거래금액: 거래 금액
            주문수량: 주문 수량
        Returns:
            주문 가격
        """
        return 0
