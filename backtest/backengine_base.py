
import sqlite3
import numpy as np
import pandas as pd
from traceback import format_exc
from multiprocessing import shared_memory
from strategy.analyzer_risk import AnalyzerRisk
from strategy.stg_globals_func import StgGlobalsFunc
from strategy.manager_formula import get_formula_data
from strategy.analyzer_volume_spike import AnalyzerVolumeSpike
from strategy.analyzer_candle_pattern import AnalyzerCandlePattern
from strategy.analyzer_volume_profile import AnalyzerVolumeProfile
from strategy.analyzer_microstructure import AnalyzerMicrostructure
from strategy.analyzer_volatility_pattern import AnalyzerVolatilityPattern
from utility.settings.setting_base import DICT_INDICATOR, UI_NUM, BACK_TEMP, DB_STRATEGY, DB_SETTING
from utility.static_method.static import pickle_read, pickle_write, dt_ymdhms, dt_ymdhm, get_ema_list, add_rolling_data, \
    set_builtin_print, get_profile_text
from backtest.back_static import get_buy_stg, get_sell_stg, get_buy_conds, get_sell_conds, get_back_load_code_query, \
    get_trade_info, get_buy_stg_future, get_sell_stg_future, get_buy_conds_future, get_sell_conds_future


class BackEngineBase(StgGlobalsFunc):
    """백테스트 엔진의 기본 클래스입니다.
    주문 관리 시스템(OMS)이 적용되지 않은 백테스트 엔진으로,
    데이터 로드, 전략 실행, 기본 매수/매도 로직을 처리합니다."""

    def __init__(self, gubun, shared_cnt, lock, wq, tq, bq, beq_list, bstq_list, dict_set, profile=False):
        super().__init__()
        self.gubun           = gubun
        self.shared_cnt      = shared_cnt
        self.shared_lock     = lock
        self.wq              = wq
        self.tq              = tq
        self.bq              = bq
        self.beq_list        = beq_list
        self.beq             = beq_list[gubun]
        self.bstq_list       = bstq_list
        self.profile         = profile
        self.dict_set        = dict_set
        self.indicator       = DICT_INDICATOR
        self.backtest        = True
        self.update_formula  = False

        self.back_type       = None
        self.betting         = None
        self.avgtime         = None
        self.startday        = None
        self.endday          = None
        self.starttime       = None
        self.endtime         = None

        self.startday_       = None
        self.endday_         = None
        self.starttime_      = None
        self.endtime_        = None
        self.same_days       = False
        self.same_time       = False
        self.is_etfn         = False

        self.buystg          = None
        self.sellstg         = None
        self.indistg         = None
        self.unit            = None
        self.hour            = None
        self.pr              = None
        self.info_for_order  = None
        self.black_list      = None

        self.market_gubun    = None
        self.market_info     = None
        self.is_oms          = None
        self.buy_hj_limit    = None
        self.sell_hj_limit   = None
        self.set_weight      = None
        self.base_cnt        = None
        self.add_cnt         = None
        self.hoga_sidex      = None
        self.hoga_eidex      = None
        self.index_arry      = None
        self.ms_analyzer     = None
        self.rk_analyzer     = None
        self.pt_analyzer     = None
        self.vf_analyzer     = None

        self.code_list       = []
        self.vars_list       = []
        self.vars_lists      = []
        self.dict_buystg     = {}
        self.dict_sellstg    = {}
        self.dict_sconds     = {}
        self.dict_info       = {}
        self.dict_kosd       = {}
        self.day_info        = {}
        self.trade_info      = {}
        self.curr_trade_info = {}
        self.curr_day_info   = {}

        self.shared_list     = []
        self.shared_count    = None
        self.shared_info     = None

        self.sell_cond       = 0
        self.opti_kind       = 0
        self.sell_count      = 0
        self.비중조절기준       = 0

        set_builtin_print(True)
        self._main_loop()

    def _update_sub_vars(self):
        """하위 변수들을 업데이트합니다.
        마켓 구분, 시장 정보, OMS 적용 여부, 호가 잔량 범위 등
        백테스트에 필요한 변수들을 설정에서 가져와 업데이트합니다."""
        from utility.settings.setting_market import DICT_MARKET_GUBUN, DICT_MARKET_INFO

        self.market_gubun  = DICT_MARKET_GUBUN[self.dict_set['거래소']]
        self.market_info   = DICT_MARKET_INFO[self.market_gubun]

        self.is_oms        = self.dict_set['백테주문관리적용']
        self.is_etfn       = self.market_gubun in (2, 3)

        self.is_tick       = self.dict_set['타임프레임']
        self.buy_hj_limit  = self.dict_set['매수시장가잔량범위']
        self.sell_hj_limit = self.dict_set['매도시장가잔량범위']
        self.set_weight    = self.dict_set['비중조절']
        self.sma_list      = get_ema_list(self.is_tick)

        self.ma_round_unit = self.market_info['반올림단위']
        angle_cf           = self.market_info['각도계수'][self.is_tick]
        self.angle_pct_cf  = angle_cf[0]
        self.angle_dtm_cf  = angle_cf[1]
        factor_list        = self.market_info['팩터목록'][self.is_tick]
        self.dict_findex   = {factor: i for i, factor in enumerate(factor_list)}
        self.base_cnt      = self.dict_findex['관심종목'] + 1

        self.hoga_sidex    = self.dict_findex['매도호가1']
        self.hoga_eidex    = self.dict_findex['매수잔량5'] + 1
        self.add_cnt       = len(self.dict_findex) - self.dict_findex['최고현재가']

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

        if self.is_tick:
            self.index_arry = np.array([
                self.dict_findex['현재가'], self.dict_findex['체결강도'], self.dict_findex['등락율'],
                self.dict_findex['당일거래대금'], self.dict_findex['초당매수수량'], self.dict_findex['초당매도수량'],
                self.dict_findex['초당거래대금']
            ])
        else:
            self.index_arry = np.array([
                self.dict_findex['현재가'], self.dict_findex['체결강도'], self.dict_findex['등락율'],
                self.dict_findex['당일거래대금'], self.dict_findex['분당매수수량'], self.dict_findex['분당매도수량'],
                self.dict_findex['분당거래대금'], self.dict_findex['분봉고가'], self.dict_findex['분봉저가']
            ])

        self.ms_analyzer = AnalyzerMicrostructure(self.market_info['마켓구분'], factor_list)
        self.rk_analyzer = AnalyzerRisk(self.market_info['마켓구분'], factor_list)
        self.pt_analyzer = AnalyzerCandlePattern(self.market_gubun, self.market_info, backtest=True)
        self.vf_analyzer = AnalyzerVolumeProfile(self.market_gubun, self.market_info, backtest=True)
        self.vs_analyzer = AnalyzerVolumeSpike(self.market_gubun, self.market_info, backtest=True)
        self.vp_analyzer = AnalyzerVolatilityPattern(self.market_gubun, self.market_info, backtest=True)

        self._set_passticks_and_blacklist()

    def _set_passticks_and_blacklist(self):
        """패스틱스 조건과 블랙리스트를 설정합니다.
        데이터베이스에서 패스틱스 전략을 읽어 컴파일하고,
        블랙리스트를 설정합니다."""
        def compile_condition(x):
            return compile(f"if {x}:\n    self.dict_cond_indexn[종목코드][k+self.turn_key] = self.indexn", '<string>', 'exec')

        table_name_stg_passticks = f"{self.market_info['전략구분']}_passticks"
        con  = sqlite3.connect(DB_STRATEGY)
        dfpt = pd.read_sql(f'SELECT * FROM {table_name_stg_passticks}', con).set_index('index')
        con.close()

        if len(dfpt) > 0:
            name_list = list(dfpt.index)
            stg_list  = dfpt['전략코드'].to_list()
            stg_list  = [compile_condition(x) for x in stg_list]
            self.dict_condition = dict(zip(name_list, stg_list))

        con  = sqlite3.connect(DB_SETTING)
        dfbl = pd.read_sql('SELECT * FROM strategy', con).set_index('index')
        con.close()

        blacklist = dfbl['블랙리스트'][int(self.dict_set['거래소'][-2:])]
        if blacklist != '':
            self.black_list = blacklist.split(';')

    def _main_loop(self):
        """백테스트 엔진의 메인 루프입니다.
        큐에서 데이터를 받아 백테스트 유형에 따라 적절한 처리를 수행합니다.
        지원하는 백테스트 유형: 최적화, 전진분석, GA최적화, 조건최적화, 백테스트, 백파인더."""
        while True:
            data = self.beq.get()
            try:
                if '정보' in data[0]:
                    if self.back_type == '최적화':
                        if data[0] == '백테정보':
                            self.betting   = data[1]
                            avg_list       = data[2]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self.starttime = data[5]
                            self.endtime   = data[6]
                            if self.market_gubun < 6:
                                self.buystg, self.indistg = get_buy_stg(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg(data[8], self.gubun, self.wq)
                            else:
                                self.buystg, self.indistg = get_buy_stg_future(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg_future(data[8], self.gubun, self.wq)
                            if self.buystg is None or self.sellstg is None:
                                self._back_stop()
                            else:
                                self._check_avg_list(avg_list)
                                self._check_day_and_time()
                        elif data[0] == '변수정보':
                            self.vars_list = data[1]
                            self.opti_kind = data[2]
                            self.vars      = [var[1] for var in self.vars_list]
                            self._back_test()
                    elif self.back_type == '전진분석':
                        if data[0] == '백테정보':
                            self.betting   = data[1]
                            avg_list       = data[2]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self.starttime = data[5]
                            self.endtime   = data[6]
                            if self.market_gubun < 6:
                                self.buystg, self.indistg = get_buy_stg(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg(data[8], self.gubun, self.wq)
                            else:
                                self.buystg, self.indistg = get_buy_stg_future(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg_future(data[8], self.gubun, self.wq)
                            if self.buystg is None or self.sellstg is None:
                                self._back_stop()
                            else:
                                self._check_avg_list(avg_list)
                                self._check_day_and_time()
                        elif data[0] == '변수정보':
                            self.vars_list = data[1]
                            self.opti_kind = data[2]
                            self.vars      = [var[1] for var in self.vars_list]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self._check_day_and_time()
                            self._back_test()
                    elif self.back_type == 'GA최적화':
                        if data[0] == '백테정보':
                            self.betting   = data[1]
                            avg_list       = data[2]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self.starttime = data[5]
                            self.endtime   = data[6]
                            if self.market_gubun < 6:
                                self.buystg, self.indistg = get_buy_stg(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg(data[8], self.gubun, self.wq)
                            else:
                                self.buystg, self.indistg = get_buy_stg_future(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg_future(data[8], self.gubun, self.wq)
                            if self.buystg is None or self.sellstg is None:
                                self._back_stop()
                            else:
                                self._check_avg_list(avg_list)
                                self._check_day_and_time()
                        elif data[0] == '변수정보':
                            self.vars_lists = data[1]
                            self.opti_kind  = data[2]
                            self._back_test()
                    elif self.back_type == '조건최적화':
                        if data[0] == '백테정보':
                            self.betting   = data[1]
                            self.avgtime   = data[2]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self.starttime = data[5]
                            self.endtime   = data[6]
                            self._check_day_and_time()
                        elif data[0] == '조건정보':
                            self.dict_buystg  = {}
                            self.dict_sellstg = {}
                            self.dict_sconds  = {}
                            error = False
                            for i in range(20):
                                if self.market_gubun < 6:
                                    buystg = get_buy_conds(data[2][i], self.gubun, self.wq)
                                    sellstg, dict_cond = get_sell_conds(data[3][i], self.gubun, self.wq)
                                else:
                                    buystg = get_buy_conds_future(data[1], data[2][i], self.gubun, self.wq)
                                    sellstg, dict_cond = get_sell_conds_future(data[1], data[3][i], self.gubun, self.wq)
                                self.dict_buystg[i]  = buystg
                                self.dict_sellstg[i] = sellstg
                                self.dict_sconds[i]  = dict_cond
                                if buystg is None or sellstg is None: error = True
                            if error:
                                self._back_stop()
                            else:
                                self.opti_kind = data[4]
                                self._back_test()
                    elif self.back_type == '백테스트':
                        if data[0] == '백테정보':
                            self.betting   = data[1]
                            self.avgtime   = data[2]
                            self.startday  = data[3]
                            self.endday    = data[4]
                            self.starttime = data[5]
                            self.endtime   = data[6]
                            if self.market_gubun < 6:
                                self.buystg, self.indistg = get_buy_stg(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg(data[8], self.gubun, self.wq)
                            else:
                                self.buystg, self.indistg = get_buy_stg_future(data[7], self.gubun, self.wq)
                                self.sellstg, self.dict_sconds = get_sell_stg_future(data[8], self.gubun, self.wq)
                            if self.buystg is None or self.sellstg is None:
                                self._back_stop()
                            else:
                                self.opti_kind = data[9]
                                self._check_day_and_time()
                                self._back_test()
                    elif self.back_type == '백파인더':
                        if data[0] == '백테정보':
                            self.avgtime   = data[1]
                            self.startday  = data[2]
                            self.endday    = data[3]
                            self.starttime = data[4]
                            self.endtime   = data[5]
                            try:
                                self.buystg = compile(data[6], '<string>', 'exec')
                            except Exception:
                                if self.gubun == 0:
                                    self.wq.put((UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - 매수전략'))
                                self._back_stop()
                            else:
                                self.opti_kind = data[7]
                                self._check_day_and_time()
                                self._back_test()

                elif data[0] == '백테유형':
                    self.back_type = data[1]
                    self.update_formula = False
                    if self.dict_set['시장미시구조분석']:
                        self.ms_analyzer.clear_data()
                elif data[0] == '설정변경':
                    self.dict_set = data[1]
                    self._update_sub_vars()
                elif data[0] == '종목명':
                    self.dict_info = data[1]
                elif data[0] == '데이터로딩':
                    self._data_load(data)
                elif data[0] == '공유데이터':
                    self.shared_count = data[1]
                    self.shared_info  = data[2]
                elif data == '백테중지':
                    self._back_stop(2)
            except Exception:
                if self.gubun == 0:
                    self.wq.put((UI_NUM['시스템로그'], format_exc()))

    def _data_load(self, data):
        """백테스트 데이터를 로드합니다.
        데이터베이스에서 종목 데이터를 읽어 공유 메모리 또는 파일에 저장합니다.
        Args:
            data: 로드에 필요한 데이터 튜플
        """

        def load_and_add_data():
            """종목의 코드, 일자들, 시작시간, 종료시간으로 쿼리를 만들어서 데이터를 로딩 한 후에 롤링 데이터를 추가하고 2차원 어레이로 만든다.
            만든 2차원 어레이와 관련 정보를 all_data에 기록한다."""
            try:
                df = pd.read_sql(get_back_load_code_query(self.is_tick, code, days, starttime, endtime), con)
            except Exception:
                pass
            else:
                if len(df) > 0:
                    arry = add_rolling_data(df, round_unit, angle_cf_list, avg_list, self.is_tick, self.index_arry)
                    all_data.append({
                        'code': code,
                        'data': arry,
                        'shape': arry.shape,
                        'dtype': arry.dtype,
                        'size': arry.shape[0] * arry.shape[1] * arry.dtype.itemsize
                    })

        self._update_sub_vars()

        round_unit = self.market_info['반올림단위']
        angle_cf_list = self.market_info['각도계수'][self.is_tick]

        con = sqlite3.connect(self.market_info['백테디비'][self.is_tick])

        all_data = []
        divid_mode = data[-1]

        if divid_mode == '종목코드별 분류':
            _, startday, endday, starttime, endtime, code_list, avg_list, code_days, _, _, _ = data
            for code in code_list:
                days = code_days[code]
                load_and_add_data()

        elif divid_mode == '일자별 분류':
            _, startday, endday, starttime, endtime, day_list, avg_list, _, day_codes, _, _ = data
            code_list = set()
            for day in day_list:
                code_list.update(day_codes[day])
            for code in code_list:
                days = day_list
                load_and_add_data()

        else:
            _, startday, endday, starttime, endtime, day_list, avg_list, _, _, code, _ = data
            for day in day_list:
                days = [day]
                load_and_add_data()

        con.close()

        if self.dict_set['백테일괄로딩'] and all_data:
            name = f'backdata_{self.gubun}'
            total_size = sum(item['size'] for item in all_data)
            shm = shared_memory.SharedMemory(name=name, create=True, size=total_size)

            shared_info = []
            offset = 0
            for item in all_data:
                # noinspection PyUnresolvedReferences
                shared_array = np.ndarray(
                    item['shape'],
                    dtype=item['dtype'],
                    buffer=shm.buf[offset:offset + item['size']]
                )

                np.copyto(shared_array, item['data'])
                shared_info.append({
                    'shm_name': shm.name,
                    'code': item['code'],
                    'shape': item['shape'],
                    'dtype': item['dtype'],
                    'size': item['size'],
                    'offset': offset
                })
                offset += item['size']
            self.shared_list.append(shm)

        else:
            shared_info = []
            for i, item in enumerate(all_data):
                file_name = f'{BACK_TEMP}/back_{self.gubun}_{i}'
                pickle_write(file_name, item['data'])
                shared_info.append({
                    'file_name': file_name,
                    'code': item['code'],
                    'shape': item['shape']
                })

        self.avg_list = avg_list
        self.startday_, self.endday_, self.starttime_, self.endtime_ = startday, endday, starttime, endtime
        self.bq.put(shared_info)

        self.set_globals_func()

    def _update_globals_func(self, dict_add_func):
        """전역 함수를 업데이트합니다.
        Args:
            dict_add_func: 추가할 전역 함수 딕셔너리
        """
        globals().update(dict_add_func)

    def _check_avg_list(self, avg_list):
        """평균값 틱수 목록을 검증합니다.
        백테 엔진 구동 시 포함되지 않은 평균값 틱수가 있으면
        백테스트를 중지합니다.
        Args:
            avg_list: 평균값 틱수 목록
        """
        not_in_list = [x for x in avg_list if x not in self.avg_list]
        if len(not_in_list) > 0 and self.gubun == 0:
            self.wq.put((UI_NUM['백테스트'], '백테엔진 구동 시 포함되지 않은 평균값 틱수를 사용하여 중지되었습니다.'))
            self.wq.put((UI_NUM['백테스트'], '누락된 평균값 틱수를 추가하여 백테엔진을 재시작하십시오.'))
            self._back_stop()

    def _check_day_and_time(self):
        """날짜와 시간 범위를 확인하고 설정합니다.
        이전 데이터 로딩과 현재 설정이 동일한지 확인하고,
        틱/분봉에 따른 단위를 설정합니다."""
        self.same_days = self.startday_ == self.startday and self.endday_ == self.endday
        self.same_time = self.starttime_ == self.starttime and self.endtime_ == self.endtime

        if self.is_tick:
            self.unit = 1000000
            self.hour = 240000
        else:
            self.unit = 10000
            self.hour = 2400

    def _back_stop(self, gubun=0):
        """백테스트를 중지합니다.
        Args:
            gubun: 중지 구분 (0:일반, 1:사용자요청, 2:완료알림, 3:오류)
        """
        self.back_type = None
        if gubun in (0, 1):
            if self.gubun == 0: self.wq.put((UI_NUM['백테스트'], '백테스트 엔진 중지 중 ...'))
        if gubun in (1, 2):
            self.bq.put('백테중지완료')
        if gubun == 3:
            if self.gubun == 0: self.wq.put((UI_NUM['백테스트'], '백테스트 엔진 전략연산 오류, 자동 중지 중 ...'))

    def _init_trade_info(self):
        """거래 정보를 초기화합니다.
        백테스트에 필요한 거래 관련 변수들을 초기화하고,
        OMS 적용 여부에 따라 적절한 구조로 설정합니다."""
        self.high_low = []
        self.tick_count = 0
        self.dict_cond_indexn = {}
        if self.dict_set['시장미시구조분석']:
            self.ms_analyzer.clear_code_data(self.code)

        if self.is_oms:
            v1 = get_trade_info(3)
            v2 = get_trade_info(2)

            if self.opti_kind == 1:
                self.day_info   = {t: {k: v1 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
                self.trade_info = {t: {k: v2 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
            elif self.opti_kind == 3:
                self.day_info   = {t: {k: v1 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
                self.trade_info = {t: {k: v2 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
            else:
                self.day_info   = {0: {0: v1}}
                self.trade_info = {0: {0: v2}}
        else:
            v = get_trade_info(1)
            if self.opti_kind == 1:
                self.trade_info = {t: {k: v for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
            elif self.opti_kind == 3:
                self.trade_info = {t: {k: v for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
            else:
                self.trade_info = {0: {0: v}}

    # noinspection PyUnresolvedReferences
    def _get_array_data(self):
        """공유 메모리 또는 파일에서 배열 데이터를 가져옵니다.
        Returns:
            종목 코드. 데이터가 없으면 None을 반환합니다.
        """
        shared_info = None
        with self.shared_lock:
            shared_cnt = self.shared_cnt.value
            if shared_cnt < self.shared_count:
                shared_info = self.shared_info[shared_cnt]
            self.shared_cnt.value += 1

        if shared_info is None:
            return None

        code = shared_info['code']
        if self.dict_set['백테일괄로딩']:
            shm = shared_memory.SharedMemory(name=shared_info['shm_name'])
            arry_code = np.ndarray(
                shared_info['shape'],
                dtype=shared_info['dtype'],
                buffer=shm.buf[shared_info['offset']:shared_info['offset'] + shared_info['size']]
            ).copy()
            shm.close()
        else:
            arry_code = pickle_read(shared_info['file_name'])

        if self.same_days and self.same_time:
            pass
        elif self.same_time:
            indices = arry_code[:, 0]
            arry_code = arry_code[(indices >= self.startday * self.unit) &
                                  (indices <= self.endday * self.unit + self.hour)]
        elif self.same_days:
            indices = arry_code[:, 0]
            arry_code = arry_code[(indices % self.unit >= self.starttime) &
                                  (indices % self.unit <= self.endtime)]
        else:
            indices = arry_code[:, 0]
            arry_code = arry_code[(indices >= self.startday * self.unit) &
                                  (indices <= self.endday * self.unit + self.hour) &
                                  (indices % self.unit >= self.starttime) &
                                  (indices % self.unit <= self.endtime)]

        if self.fm_tcnt > 0:
            arry_code = np.column_stack((arry_code, np.zeros((self.arry_code.shape[0], self.fm_tcnt))))

        self.arry_code = arry_code
        return code

    def _update_formula_data(self):
        """사용자 수식 데이터를 업데이트합니다.
        데이터베이스에서 수식을 읽어 컴파일하고 전역 함수를 설정합니다."""
        total_cnt = self.base_cnt + 5 + self.add_cnt * len(self.avg_list)
        self.fm_list, _, self.fm_tcnt = get_formula_data(False, total_cnt)
        if self.fm_list:
            for fm in self.fm_list:
                fm[8] = compile(fm[-2], '<string>', 'exec')
            self.set_globals_func()

    def _back_test(self):
        """백테스트를 실행합니다.
        데이터를 순회하며 전략을 실행하고 매수/매도 시그널을 처리합니다.
        프로파일링이 활성화된 경우 성능 측정을 수행합니다."""
        if self.gubun == 0 and self.profile:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        if not self.update_formula:
            self._update_formula_data()
            self.update_formula = True

        self._init_trade_info()
        self.sell_count = 0

        j = 0
        while True:
            code = self._get_array_data()
            if code is None:
                break

            if not self.beq.empty() and self.beq.get() == '백테중지':
                self._back_stop(1)
                return

            self.code = code
            self.name = self.dict_info.get(self.code, {}).get('종목명', self.code)

            if self.is_oms:
                if self.dict_set['매수금지블랙리스트'] and self.name in self.black_list and self.back_type != '백파인더':
                    self.tq.put('백테완료')
                    continue

            last = len(self.arry_code) - 1
            if last > 0:
                indexs = self.arry_code[:, 0].astype(np.int64)
                day_vals = indexs // 1_000_000 if self.is_tick else indexs // 10_000
                # noinspection PyUnresolvedReferences
                day_last_indexs = np.where(day_vals[:-1] != day_vals[1:])[0]
                day_last_indexs = np.concatenate([day_last_indexs, [last]])

                start_idx = 0
                for end_idx in day_last_indexs:
                    for i in range(start_idx, end_idx):
                        self.index = indexs[i]
                        self.indexn = i
                        self.tick_count += 1

                        try:
                            self._strategy()
                        except Exception:
                            if self.gubun == 0: self.wq.put((UI_NUM['시스템로그'], format_exc()))
                            self._back_stop(3)
                            return

                        j += 1
                        if j == 1000:
                            j = 0
                            if not self.beq.empty() and self.beq.get() == '백테중지':
                                self._back_stop(1)
                                return

                    self.index = indexs[end_idx]
                    self.indexn = end_idx
                    self.tick_count += 1
                    self._last_sell()
                    self._init_trade_info()
                    start_idx = end_idx + 1

            self.tq.put('백테완료')

        if not self.beq.empty() and self.beq.get() == '백테중지':
            self._back_stop(1)
            return

        if self.gubun == 0 and self.profile:
            self.wq.put((UI_NUM['시스템로그'], get_profile_text(self.pr)))

    # noinspection PyUnusedLocal
    def _strategy(self):
        """전략을 실행합니다.
        현재 틱 데이터를 기반으로 매수/매도 전략을 실행합니다."""

        초당매수금액, 초당매도금액, 분당매수금액, 분당매도금액 = 0, 0, 0, 0
        if self.market_gubun < 4:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                    VI해제시간, VI가격, VI호가단위, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                    VI해제시간, VI가격, VI호가단위, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            VI해제시간 = dt_ymdhms(str(int(VI해제시간)))
        elif self.market_gubun == 4:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 시가총액, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, 시가총액, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
        else:
            if self.is_tick:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                    초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
            else:
                현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                    분봉시가, 분봉고가, 분봉저가, \
                    분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, \
                    당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                    매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                    매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                    매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

        시분초 = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
        순매수금액 = 초당매수금액 - 초당매도금액 if self.is_tick else 분당매수금액 - 분당매도금액
        종목명, 종목코드, 데이터길이, 체결시간 = self.name, self.code, self.tick_count, self.index
        self.hoga_unit = 호가단위 = self._get_hogaunit(현재가 if self.market_gubun < 6 else self.code)

        리스크점수 = 0
        if self.is_tick and 데이터길이 >= 30 and (self.dict_set['시장미시구조분석'] or self.dict_set['리스크분석']):
            current_data = self.arry_code[self.indexn + 1 - self.tick_count:self.indexn + 1, :]
            if self.dict_set['시장미시구조분석']:
                self.ms_analyzer.update_data(self.code, current_data)
            if self.dict_set['리스크분석']:
                리스크점수 = self.rk_analyzer.get_risk_score(current_data)

        패턴점수, 패턴신뢰도, 가격대점수, 가격대신뢰도, 거래량점수, 거래량신뢰도, 변동성점수, 변동성신뢰도 = 0, 0, 0, 0, 0, 0, 0, 0
        if not self.is_tick and (
                self.dict_set['캔들분석'] or self.dict_set['가격대분석'] or
                self.dict_set['거래량분석'] or self.dict_set['변동성분석']
        ):
            current_data = self.arry_code[self.indexn + 1 - self.tick_count:self.indexn + 1, :]
            if self.dict_set['캔들분석']:
                패턴점수, 패턴신뢰도 = self.pt_analyzer.analyze_current_patterns(self.code, current_data)
            if self.dict_set['가격대분석']:
                가격대점수, 가격대신뢰도 = self.vf_analyzer.analyze_current_price(self.code, 현재가)
            if self.dict_set['거래량분석']:
                거래량점수, 거래량신뢰도 = self.vs_analyzer.analyze_current_spike(self.code, current_data)
            if self.dict_set['변동성분석']:
                변동성점수, 변동성신뢰도 = self.vp_analyzer.analyze_current_volatility(self.code, current_data)

        self.shogainfo[:] = [매도호가1, 매도호가2, 매도호가3, 매도호가4, 매도호가5]
        self.shreminfo[:] = [매도잔량1, 매도잔량2, 매도잔량3, 매도잔량4, 매도잔량5]
        self.bhogainfo[:] = [매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5]
        self.bhreminfo[:] = [매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5]

        self._update_highlow(현재가)

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

                    if self.dict_condition:
                        self.turn_key = f'{vturn}{vturn}'
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

                    매수, 매도 = True, False
                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if not 보유중:
                        if not 관심종목: continue
                        exec(self.buystg)
                    else:
                        포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                            self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
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

                    if self.dict_condition:
                        self.turn_key = f'{vturn}{vturn}'
                        if 종목코드 not in self.dict_cond_indexn:
                            self.dict_cond_indexn[종목코드] = {}
                        for k, v in self.dict_condition.items():
                            exec(v)

                    self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
                    self.curr_trade_info = self.trade_info[vturn][vkey]
                    보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

                    매수, 매도 = True, False
                    BUY_LONG, SELL_SHORT = True, True
                    SELL_LONG, BUY_SHORT = False, False

                    if not 보유중:
                        if not 관심종목: continue
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                            self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
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

            if self.dict_condition:
                self.turn_key = f'{vturn}{vturn}'
                if 종목코드 not in self.dict_cond_indexn:
                    self.dict_cond_indexn[종목코드] = {}
                for k, v in self.dict_condition.items():
                    exec(v)

            self.info_for_order = 현재가, 저가대비고가등락율, vturn, vkey
            self.curr_trade_info = self.trade_info[vturn][vkey]
            보유중, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()

            매수, 매도 = True, False
            BUY_LONG, SELL_SHORT = True, True
            SELL_LONG, BUY_SHORT = False, False

            if not 보유중:
                if not 관심종목: return
                exec(self.buystg)
            else:
                포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간 = \
                    self._get_hold_info(보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간)
                self.profit, self.hold_time = 수익률, 보유시간
                exec(self.sellstg)

    def _update_highlow(self, 현재가또는분봉고가=None, 분봉저가=None):
        """고가/저가 정보를 업데이트합니다.
        Args:
            현재가또는분봉고가: 현재가 또는 분봉 고가
            분봉저가: 분봉 저가
        """
        if 분봉저가 is None:
            if self.high_low:
                if 현재가또는분봉고가 >= self.high_low[0]:
                    self.high_low[0] = 현재가또는분봉고가
                    self.high_low[1] = self.indexn
                if 현재가또는분봉고가 <= self.high_low[2]:
                    self.high_low[2] = 현재가또는분봉고가
                    self.high_low[3] = self.indexn
            else:
                self.high_low = [현재가또는분봉고가, self.indexn, 현재가또는분봉고가, self.indexn]
        else:
            if self.high_low:
                if 현재가또는분봉고가 >= self.high_low[0]:
                    self.high_low[0] = 현재가또는분봉고가
                    self.high_low[1] = self.indexn
                if 분봉저가 <= self.high_low[2]:
                    self.high_low[2] = 분봉저가
                    self.high_low[3] = self.indexn
            else:
                self.high_low = [현재가또는분봉고가, self.indexn, 분봉저가, self.indexn]

    def Buy(self, buy_long=False):
        """매수 주문을 실행합니다.
        Args:
            buy_long: 롱 포지션 여부
        """
        self._get_buy_count()
        주문수량 = self.curr_trade_info['주문수량']
        if 주문수량 > 0:
            if self.market_gubun < 6 or buy_long:
                호가배열 = self.shogainfo[:self.buy_hj_limit]
                잔량배열 = self.shreminfo[:self.buy_hj_limit]
            else:
                호가배열 = self.bhogainfo[:self.buy_hj_limit]
                잔량배열 = self.bhreminfo[:self.buy_hj_limit]

            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                보유중 = 1 if self.market_gubun < 6 or buy_long else 2
                매수가 = self._get_order_price(거래금액, 주문수량)
                매수시간 = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                self.curr_trade_info.update({
                    '보유중': 보유중,
                    '매수가': 매수가,
                    '매도가': 0,
                    '주문수량': 0,
                    '보유수량': 주문수량,
                    '최고수익률': 0.,
                    '최저수익률': 0.,
                    '매수틱번호': self.indexn,
                    '매수시간': 매수시간
                })

    def _get_buy_count(self):
        """매수 수량을 계산합니다.
        비중 조절 설정에 따라 배팅 금액을 조절하고,
        현재가에 따른 주문 수량을 계산합니다."""
        현재가, 저가대비고가등락율 = self.info_for_order[:2]
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = self._거래대금평균대비비율(30)
            elif self.set_weight[0] == 3:
                비중조절기준 = self._등락율각도(30)
            elif self.set_weight[0] == 4:
                비중조절기준 = self._당일거래대금각도(30)
            else:
                비중조절기준 = self.비중조절기준

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
        self.curr_trade_info['주문수량'] = self._set_buy_count(betting, 현재가, 0, 100)

    def _get_hold_info(self, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간):
        """보유 정보를 계산합니다.
        Args:
            보유수량: 보유 수량
            매수가: 매수 가격
            현재가: 현재 가격
            최고수익률: 최고 수익률
            최저수익률: 최저 수익률
            매수틱번호: 매수 틱 번호
            매수시간: 매수 시간
        Returns:
            (시가총액또는포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간) 튜플
        """
        시가총액또는포지션, _, 수익금, 수익률 = self._get_profit_info(현재가, 매수가, 보유수량)
        if 수익률 > 최고수익률:   self.curr_trade_info['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.curr_trade_info['최저수익률'] = 최저수익률 = 수익률
        now_time = self._now()
        # noinspection PyUnresolvedReferences
        보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        self.curr_trade_info['주문수량'] = 보유수량
        self.indexb = 매수틱번호
        return 시가총액또는포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def Sell(self, sell_long=False):
        """매도 주문을 실행합니다.
        Args:
            sell_long: 롱 포지션 매도 여부
        """
        주문수량 = self.curr_trade_info['주문수량']
        if 주문수량 > 0:
            if self.market_gubun < 6 or sell_long:
                호가배열 = self.bhogainfo[:self.sell_hj_limit]
                잔량배열 = self.bhreminfo[:self.sell_hj_limit]
            else:
                호가배열 = self.shogainfo[:self.sell_hj_limit]
                잔량배열 = self.shreminfo[:self.sell_hj_limit]

            거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
            if 체결완료:
                self.curr_trade_info['매도가'] = self._get_order_price(거래금액, 주문수량)
                self._calculation_eyun()

    def _last_sell(self):
        """마지막 틱에서 매도를 처리합니다.
        일일 마지막 틱에서 보유 중인 포지션을 청산합니다."""
        호가데이터 = self.arry_code[self.indexn, self.hoga_sidex:self.hoga_eidex]
        매도호가배열 = 호가데이터[:5]
        매수호가배열 = 호가데이터[5:10]
        매도잔량배열 = 호가데이터[10:15]
        매수잔량배열 = 호가데이터[15:20]

        for vturn in self.trade_info:
            for vkey in self.trade_info[vturn]:
                self.info_for_order = None, None, vturn, vkey
                self.curr_trade_info = self.trade_info[vturn][vkey]
                if self.curr_trade_info['보유중'] > 0:
                    주문수량 = self.curr_trade_info['보유수량']
                    if self.market_gubun < 6 or self.curr_trade_info['보유중'] == 1:
                        호가배열 = 매수호가배열[:self.sell_hj_limit]
                        잔량배열 = 매수잔량배열[:self.sell_hj_limit]
                    else:
                        호가배열 = 매도호가배열[:self.sell_hj_limit]
                        잔량배열 = 매도잔량배열[:self.sell_hj_limit]

                    거래금액, 체결완료 = self._calc_fill_amount(주문수량, 호가배열, 잔량배열)
                    if not 체결완료:
                        거래금액 = 주문수량 * 호가배열[0]

                    self.curr_trade_info['매도가'] = self._get_order_price(거래금액, 주문수량)
                    self.curr_trade_info['주문수량'] = 주문수량
                    self.sell_cond = 0
                    self._calculation_eyun()

    def _calculation_eyun(self):
        """수익을 계산하고 결과를 전송합니다.
        거래 완료 후 수익금, 수익률 등을 계산하고 백테스트 결과를 큐에 전송합니다."""
        vturn, vkey = self.info_for_order[-2:]
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.curr_trade_info.values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간, 매입금액 = int(self.arry_code[매수틱번호, 0]), self.index, 주문수량 * 매수가
        시가총액또는포지션, 평가금액, 수익금, 수익률 = self._get_profit_info(매도가, 매수가, 주문수량)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True

        data = ('백테결과', self.name, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금,
                매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_kind in (1, 3) else (self.sell_count % 5)].put(data)

        self.sell_count += 1
        self.trade_info[vturn][vkey] = get_trade_info(1)

    def _get_hogaunit(self, 주문가격또는종목코드):
        """호가 단위를 반환합니다.
        Args:
            주문가격또는종목코드: 주문 가격 또는 종목 코드
        Returns:
            호가 단위
        """
        return 0

    def _set_buy_count(self, betting, 현재가, 매수가, oc_ratio):
        """매수 수량을 설정합니다.
        Args:
            betting: 배팅 금액
            현재가: 현재 가격
            매수가: 매수 가격
            oc_ratio: OC 비율
        Returns:
            매수 수량
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

    def _get_profit_info(self, 현재가, 매수가, 보유수량):
        """수익 정보를 계산합니다.
        Args:
            현재가: 현재 가격
            매수가: 매수 가격
            보유수량: 보유 수량
        Returns:
            (포지션, 평가금액, 수익금, 수익률) 튜플
        """
        return None, 0, 0, 0
