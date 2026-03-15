
import sqlite3
from traceback import format_exc
from multiprocessing import shared_memory
from trade.strategy_base import StrategyBase
from utility.lazy_imports import get_np, get_pd
from trade.formula_manager import get_formula_data
from backtest.back_static import GetBuyStg, GetSellStg, GetBuyConds, GetSellConds, GetBackloadCodeQuery, \
    get_trade_info, GetBuyStgFuture, GetSellStgFuture, GetBuyCondsFuture, GetSellCondsFuture
from utility.setting_base import DB_STOCK_BACK_TICK, BACK_TEMP, ui_num, DB_STOCK_BACK_MIN, indicator, \
    DB_FUTURE_BACK_TICK, DB_FUTURE_BACK_MIN, DB_COIN_BACK_TICK, DB_COIN_BACK_MIN, list_stock_tick, \
    list_stock_min, list_coin_tick, list_coin_min
# noinspection PyUnresolvedReferences
from utility.static import timedelta_sec, pickle_read, pickle_write, dt_ymdhms, dt_ymdhm, get_angle_cf, get_ema_list, \
    add_rolling_data, error_decorator, set_builtin_print


class BackEngineBase(StrategyBase):
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
        self.indicator       = indicator
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

        self.buystg          = None
        self.sellstg         = None
        self.indistg         = None
        self.dict_cn         = None
        self.unit            = None
        self.hour            = None
        self.pr              = None
        self.info_for_order  = None

        self.market_gubun    = None
        self.market_text     = None
        self.ui_num_txt      = None
        self.is_oms          = None
        self.buy_hj_limit    = None
        self.sell_hj_limit   = None
        self.set_dict_cond   = None
        self.set_weight      = None
        self.base_cnt        = None
        self.add_cnt         = None
        self.hoga_sidex      = None
        self.hoga_eidex      = None

        self.code_list       = []
        self.vars_list       = []
        self.vars_lists      = []
        self.shogainfo       = {}
        self.bhogainfo       = {}
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
        self.opti_turn       = 0
        self.sell_count      = 0

        set_builtin_print(True, self.wq)
        self.UpdateMarketGubun()
        self.MainLoop()

    def UpdateSubVars(self):
        self.market_text   = '주식' if self.market_gubun < 3 else '코인'
        self.ui_num_txt    = 'S백테스트' if self.market_gubun < 3 else 'C백테스트'
        self.is_oms        = self.dict_set['백테주문관리적용']
        self.is_tick       = self.dict_set[f'{self.market_text}타임프레임']
        self.buy_hj_limit  = self.dict_set[f'{self.market_text}매수시장가잔량범위']
        self.sell_hj_limit = self.dict_set[f'{self.market_text}매도시장가잔량범위']
        self.set_dict_cond = self.dict_set[f'{self.market_text}경과틱수설정']
        self.set_weight    = self.dict_set[f'{self.market_text}비중조절']
        self.sma_list      = get_ema_list(self.is_tick)

        if self.market_gubun == 1:
            factor_list = list_stock_tick if self.is_tick else list_stock_min
        else:
            factor_list = list_coin_tick if self.is_tick else list_coin_min
        self.dict_findex = {name: i for i, name in enumerate(factor_list)}

        self.base_cnt     = self.dict_findex['관심종목'] + 1
        self.hoga_sidex   = self.dict_findex['매도호가5']
        self.hoga_eidex   = self.dict_findex['매수잔량5'] + 1
        self.add_cnt      = len(self.dict_findex) - self.dict_findex['최고현재가']
        self.angle_pct_cf = get_angle_cf(self.market_gubun, self.is_tick, 0)
        self.angle_dtm_cf = get_angle_cf(self.market_gubun, self.is_tick, 1)

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

        if self.set_dict_cond:
            def compile_condition(x):
                if self.is_tick:
                    return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')
                else:
                    return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k+str(vturn)+str(vkey)] = self.indexn', '<string>', 'exec')

            text_list = self.set_dict_cond.split(';')
            half_cnt = int(len(text_list) / 2)
            key_list = text_list[:half_cnt]
            value_text_list = text_list[half_cnt:]
            value_comp_list = [compile_condition(x) for x in value_text_list]
            self.dict_condition = dict(zip(key_list, value_comp_list))

    @error_decorator
    def MainLoop(self):
        while True:
            data = self.beq.get()
            if '정보' in data[0]:
                if self.back_type == '최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun, self.wq)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun, self.wq)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.BackTest()
                elif self.back_type == '전진분석':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun, self.wq)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun, self.wq)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.CheckDayAndTime()
                        self.BackTest()
                elif self.back_type == 'GA최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun, self.wq)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun, self.wq)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_lists = data[1]
                        self.opti_turn  = data[2]
                        self.BackTest()
                elif self.back_type == '조건최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.CheckDayAndTime()
                    elif data[0] == '조건정보':
                        self.dict_buystg  = {}
                        self.dict_sellstg = {}
                        self.dict_sconds  = {}
                        error = False
                        for i in range(20):
                            if self.market_gubun in (1, 3):
                                buystg = GetBuyConds(data[2][i], self.gubun, self.wq)
                                sellstg, dict_cond = GetSellConds(data[3][i], self.gubun, self.wq)
                            else:
                                buystg = GetBuyCondsFuture(data[1], data[2][i], self.gubun, self.wq)
                                sellstg, dict_cond = GetSellCondsFuture(data[1], data[3][i], self.gubun, self.wq)
                            self.dict_buystg[i]  = buystg
                            self.dict_sellstg[i] = sellstg
                            self.dict_sconds[i]  = dict_cond
                            if buystg is None or sellstg is None: error = True
                        if error:
                            self.BackStop()
                        else:
                            self.opti_turn = data[4]
                            self.BackTest()
                elif self.back_type == '백테스트':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun, self.wq)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun, self.wq)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun, self.wq)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.opti_turn = data[9]
                            self.CheckDayAndTime()
                            self.BackTest()
                elif self.back_type == '백파인더':
                    if data[0] == '백테정보':
                        self.avgtime   = data[1]
                        self.startday  = data[2]
                        self.endday    = data[3]
                        self.starttime = data[4]
                        self.endtime   = data[5]
                        try:
                            self.buystg = compile(data[6], '<string>', 'exec')
                        except:
                            if self.gubun == 0: self.wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매수전략'))
                            self.BackStop()
                        else:
                            self.opti_turn = data[7]
                            self.CheckDayAndTime()
                            self.BackTest()

            elif data[0] == '백테유형':
                self.back_type = data[1]
                self.update_formula = False
            elif data[0] == '설정변경':
                self.dict_set = data[1]
                self.UpdateSubVars()
            elif data[0] == '종목명':
                if self.market_gubun == 1:
                    self.dict_cn   = data[1]
                    self.dict_kosd = data[2]
                else:
                    self.dict_info = data[1]
            elif data[0] == '데이터로딩':
                self.DataLoad(data)
            elif data[0] == '공유데이터':
                self.shared_count = data[1]
                self.shared_info  = data[2]
            elif data == '백테중지':
                self.BackStop(2)

    def DataLoad(self, data):
        def data_load(days):
            try:
                df = get_pd().read_sql(GetBackloadCodeQuery(self.is_tick, code, days, starttime, endtime), con)
            except:
                pass
            else:
                if len(df) > 0:
                    arry = add_rolling_data(df, self.market_gubun, self.is_tick, avg_list)
                    all_data.append({
                        'code': code,
                        'data': arry,
                        'len': len(arry)
                    })

        self.UpdateSubVars()

        if self.market_gubun == 1:
            con = sqlite3.connect(DB_STOCK_BACK_TICK if self.is_tick else DB_STOCK_BACK_MIN)
        elif self.market_gubun == 2:
            con = sqlite3.connect(DB_FUTURE_BACK_TICK if self.is_tick else DB_FUTURE_BACK_MIN)
        else:
            con = sqlite3.connect(DB_COIN_BACK_TICK if self.is_tick else DB_COIN_BACK_MIN)

        all_data = []
        divid_mode = data[-1]
        if divid_mode == '종목코드별 분류':
            _, startday, endday, starttime, endtime, code_list, avg_list, code_days, _, _, _ = data
            for i, code in enumerate(code_list):
                data_load(code_days[code])
        elif divid_mode == '일자별 분류':
            _, startday, endday, starttime, endtime, day_list, avg_list, _, day_codes, _, _ = data
            code_list = set()
            for day in day_list:
                code_list.update(day_codes[day])
            for i, code in enumerate(code_list):
                data_load(day_list)
        else:
            _, startday, endday, starttime, endtime, day_list, avg_list, _, _, code, _ = data
            for i, day in enumerate(day_list):
                data_load([day])
        con.close()

        if self.dict_set['백테일괄로딩'] and all_data:
            name = f'backdata_{self.gubun}'
            total_size = sum(item['len'] * item['data'].dtype.itemsize * item['data'].shape[1] for item in all_data)
            shm = shared_memory.SharedMemory(name=name, create=True, size=total_size)

            shared_info = []
            offset = 0
            for item in all_data:
                data_size = item['len'] * item['data'].dtype.itemsize * item['data'].shape[1]
                shared_array = get_np().ndarray((item['len'], item['data'].shape[1]),
                                                dtype=item['data'].dtype,
                                                buffer=shm.buf[offset:offset + data_size])

                get_np().copyto(shared_array, item['data'])
                shared_info.append({
                    'code': item['code'],
                    'len': item['len'],
                    'shm_name': shm.name,
                    'offset': offset,
                    'shape': item['data'].shape,
                    'dtype': item['data'].dtype
                })
                offset += data_size
            self.shared_list.append(shm)
        else:
            shared_info = []
            for i, item in enumerate(all_data):
                file_name = f'{BACK_TEMP}/back_{self.gubun}_{i}'
                pickle_write(file_name, item['data'])
                shared_info.append({
                    'code': item['code'],
                    'len': item['len'],
                    'file_name': file_name
                })

        self.avg_list = avg_list
        self.startday_, self.endday_, self.starttime_, self.endtime_ = startday, endday, starttime, endtime
        self.bq.put(shared_info)

        self.SetGlobalsFunc()

    def CheckAvglist(self, avg_list):
        not_in_list = [x for x in avg_list if x not in self.avg_list]
        if len(not_in_list) > 0 and self.gubun == 0:
            self.wq.put((ui_num[self.ui_num_txt], '백테엔진 구동 시 포함되지 않은 평균값 틱수를 사용하여 중지되었습니다.'))
            self.wq.put((ui_num[self.ui_num_txt], '누락된 평균값 틱수를 추가하여 백테엔진을 재시작하십시오.'))
            self.BackStop()

    def CheckDayAndTime(self):
        self.same_days = self.startday_ == self.startday and self.endday_ == self.endday
        self.same_time = self.starttime_ == self.starttime and self.endtime_ == self.endtime

        if self.is_tick:
            self.unit = 1000000
            self.hour = 240000
        else:
            self.unit = 10000
            self.hour = 2400

    def BackStop(self, gubun=0):
        self.back_type = None
        if gubun in (0, 1):
            if self.gubun == 0: self.wq.put((ui_num[self.ui_num_txt], '백테스트 엔진 중지 중 ...'))
        if gubun in (1, 2):
            self.bq.put('백테중지완료')
        if gubun == 3:
            if self.gubun == 0: self.wq.put((ui_num[self.ui_num_txt], '백테스트 엔진 전략연산 오류, 자동 중지 중 ...'))

    def InitTradeInfo(self):
        self.high_low = []
        self.tick_count = 0
        self.dict_cond_indexn = {}

        if self.is_oms:
            v1 = get_trade_info(3)
            v2 = get_trade_info(2)

            if self.opti_turn == 1:
                self.day_info = {t: {k: v1 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if
                                 len(x[0]) > 1}
                self.trade_info = {t: {k: v2 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if
                                   len(x[0]) > 1}
            elif self.opti_turn == 3:
                self.day_info = {t: {k: v1 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
                self.trade_info = {t: {k: v2 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
            else:
                self.day_info = {0: {0: v1}}
                self.trade_info = {0: {0: v2}}
        else:
            v = get_trade_info(1)
            if self.opti_turn == 1:
                self.trade_info = {t: {k: v for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if
                                   len(x[0]) > 1}
            elif self.opti_turn == 3:
                self.trade_info = {t: {k: v for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
            else:
                self.trade_info = {0: {0: v}}

    def GetArrayData(self):
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
            data_size = shared_info['len'] * shared_info['dtype'].itemsize * shared_info['shape'][1]
            self.arry_code = get_np().ndarray(
                shared_info['shape'],
                dtype=shared_info['dtype'],
                buffer=shm.buf[shared_info['offset']:shared_info['offset'] + data_size]
            ).copy()
            shm.close()
        else:
            self.arry_code = pickle_read(shared_info['file_name'])

        if self.same_days and self.same_time:
            pass
        elif self.same_time:
            self.arry_code = self.arry_code[(self.arry_code[:, 0] >= self.startday * self.unit) &
                                            (self.arry_code[:, 0] <= self.endday * self.unit + self.hour)]
        elif self.same_days:
            self.arry_code = self.arry_code[(self.arry_code[:, 0] % self.unit >= self.starttime) &
                                            (self.arry_code[:, 0] % self.unit <= self.endtime)]
        else:
            self.arry_code = self.arry_code[(self.arry_code[:, 0] >= self.startday * self.unit) &
                                            (self.arry_code[:, 0] <= self.endday * self.unit + self.hour) &
                                            (self.arry_code[:, 0] % self.unit >= self.starttime) &
                                            (self.arry_code[:, 0] % self.unit <= self.endtime)]

        if self.fm_tcnt > 0:
            self.arry_code = get_np().column_stack((self.arry_code, get_np().zeros((self.arry_code.shape[0], self.fm_tcnt))))

        return code

    def UpdateFormulaData(self):
        total_cnt = self.base_cnt + self.add_cnt * len(self.avg_list)
        self.fm_list, dict_fm, self.fm_tcnt = get_formula_data(False, total_cnt)
        if self.fm_list:
            for fm in self.fm_list:
                fm[8] = compile(fm[-2], '<string>', 'exec')
            self.SetGlobalsFunc()

    def BackTest(self):
        if self.gubun == 0 and self.profile:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        if not self.update_formula:
            self.UpdateFormulaData()
            self.update_formula = True

        self.InitTradeInfo()
        self.sell_count = 0

        j = 0
        while True:
            code = self.GetArrayData()
            if code is None:
                break

            if not self.beq.empty() and self.beq.get() == '백테중지':
                self.BackStop(1)
                return

            if self.is_oms:
                if self.dict_set[f'{self.market_text}매수금지블랙리스트'] and \
                        code in self.dict_set[f'{self.market_text}블랙리스트'] and self.back_type != '백파인더':
                    self.tq.put('백테완료')
                    continue

            if self.market_gubun == 1:
                self.code = code
                self.name = self.dict_cn.get(self.code, self.code)
            elif self.market_gubun == 2:
                self.code = code
                self.name = self.dict_info[code]['종목명']
            else:
                self.code = self.name = code

            last = len(self.arry_code) - 1
            if last > 0:
                indexs = self.arry_code[:, 0].astype(get_np().int64)
                day_last_indexs = indexs // 1000000
                day_last_indexs = [i for i in range(last) if day_last_indexs[i] != day_last_indexs[i + 1]]
                day_last_indexs.append(last)

                start_idx = 0
                for end_idx in day_last_indexs:
                    for i in range(start_idx, end_idx):
                        self.index = indexs[i]
                        self.indexn = i
                        self.tick_count += 1

                        try:
                            self.Strategy()
                        except:
                            if self.gubun == 0: self.wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 매수전략'))
                            self.BackStop(3)
                            return

                        j += 1
                        if j == 1000:
                            j = 0
                            if not self.beq.empty() and self.beq.get() == '백테중지':
                                self.BackStop(1)
                                return

                    self.index = indexs[end_idx]
                    self.indexn = end_idx
                    self.tick_count += 1
                    self.LastSell()
                    self.InitTradeInfo()
                    start_idx = end_idx + 1

            self.tq.put('백테완료')

        if not self.beq.empty() and self.beq.get() == '백테중지':
            self.BackStop(1)
            return

        if self.gubun == 0 and self.profile:
            from utility.profile_utils import extract_profile_text
            profile_text = extract_profile_text(self.pr, limit=50)
            self.wq.put((ui_num['시스템로그'], profile_text))

    def UpdateHighLow(self, 현재가또는분봉고가=None, 분봉저가=None):
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
        self.SetBuyCount()
        주문수량 = 미체결수량 = self.curr_trade_info['주문수량']
        if 주문수량 > 0:
            호가정보 = self.shogainfo if self.market_gubun in (1, 3) or buy_long else self.bhogainfo
            호가정보 = 호가정보[:self.buy_hj_limit]
            매수금액 = 0
            for 호가, 잔량 in 호가정보:
                if 미체결수량 - 잔량 <= 0:
                    매수금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매수금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                보유중 = 1 if self.market_gubun in (1, 3) or buy_long else 2
                매수가 = self.GetBuyPrice(매수금액, 주문수량)
                매수시간 = dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                self.curr_trade_info['보유중'] = 보유중
                self.curr_trade_info['매수가'] = 매수가
                self.curr_trade_info['매도가'] = 0
                self.curr_trade_info['주문수량'] = 0
                self.curr_trade_info['보유수량'] = 주문수량
                self.curr_trade_info['최고수익률'] = 0.
                self.curr_trade_info['최저수익률'] = 0.
                self.curr_trade_info['매수틱번호'] = self.indexn
                self.curr_trade_info['매수시간'] = 매수시간

    def SetBuyCount(self):
        현재가, 저가대비고가등락율 = self.info_for_order[:-2]
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = self._거래대금평균대비비율(30)
            elif self.set_weight[0] == 3:
                비중조절기준 = self._등락율각도(30)
            else:
                비중조절기준 = self._당일거래대금각도(30)

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
        self.curr_trade_info['주문수량'] = self.GetOrderCount(betting, 현재가, False, 0, 100)

    def GetHoldInfo(self, 보유수량, 매수가, 현재가, 최고수익률, 최저수익률, 매수틱번호, 매수시간):
        포지션, _, 수익금, 수익률 = self.GetProfitInfo(현재가, 매수가, 보유수량)
        if 수익률 > 최고수익률:   self.curr_trade_info['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.curr_trade_info['최저수익률'] = 최저수익률 = 수익률
        now_time = self._now()
        보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        self.curr_trade_info['주문수량'] = 보유수량
        self.indexb = 매수틱번호
        return 포지션, 수익금, 수익률, 최고수익률, 최저수익률, 보유시간

    def Sell(self, sell_long=False):
        주문수량 = 미체결수량 = self.curr_trade_info['주문수량']
        호가정보 = self.bhogainfo if self.market_gubun in (1, 3) or sell_long else self.shogainfo
        호가정보 = 호가정보[:self.sell_hj_limit]
        매도금액 = 0
        for 호가, 잔량 in 호가정보:
            if 미체결수량 - 잔량 <= 0:
                매도금액 += 호가 * 미체결수량
                미체결수량 -= 잔량
                break
            else:
                매도금액 += 호가 * 잔량
                미체결수량 -= 잔량
        if 미체결수량 <= 0:
            self.curr_trade_info['매도가'] = self.GetSellPrice(매도금액, 주문수량)
            self.CalculationEyun()

    def LastSell(self):
        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
            self.arry_code[self.indexn, self.hoga_sidex:self.hoga_eidex]

        bhogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        bhogainfo = bhogainfo[:self.sell_hj_limit]
        shogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = shogainfo[:self.sell_hj_limit]

        for vturn in self.trade_info:
            for vkey in self.trade_info[vturn]:
                self.info_for_order = None, None, vturn, vkey
                self.curr_trade_info = self.trade_info[vturn][vkey]
                if self.curr_trade_info['보유중'] > 0:
                    매도금액 = 0
                    보유수량 = 미체결수량 = self.curr_trade_info['보유수량']
                    호가정보 = bhogainfo if self.market_gubun in (1, 3) or self.curr_trade_info['보유중'] == 1 else shogainfo
                    for 호가, 잔량 in 호가정보:
                        if 미체결수량 - 잔량 <= 0:
                            매도금액 += 호가 * 미체결수량
                            미체결수량 -= 잔량
                            break
                        else:
                            매도금액 += 호가 * 잔량
                            미체결수량 -= 잔량

                    self.curr_trade_info['매도가'] = self.GetLastSellPrice(매도금액, 보유수량, 미체결수량)
                    self.curr_trade_info['주문수량'] = 보유수량
                    self.sell_cond = 0
                    self.CalculationEyun()

    def CalculationEyun(self):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.curr_trade_info.values()
        """
        vturn, vkey = self.info_for_order[-2:]
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.curr_trade_info.values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간, 매입금액 = int(self.arry_code[매수틱번호, 0]), self.index, 주문수량 * 매수가
        시가총액또는포지션, 평가금액, 수익금, 수익률 = self.GetProfitInfo(매도가, 매수가, 주문수량)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True
        data = ('백테결과', self.name, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[vturn][vkey] = get_trade_info(1)

    def Strategy(self):
        pass

    def UpdateMarketGubun(self):
        pass

    def GetOrderCount(self, betting, 현재가, 보유중, 매수가, oc_ratio):
        return 0

    def GetBuyPrice(self, 매수금액, 주문수량):
        return 0

    def GetSellPrice(self, 매도금액, 주문수량):
        return 0

    def GetLastSellPrice(self, 매도금액, 보유수량, 미체결수량):
        return 0

    def GetProfitInfo(self, 현재가, 매수가, 보유수량):
        return None, 0, 0, 0
