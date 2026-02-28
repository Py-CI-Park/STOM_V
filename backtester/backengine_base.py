import math
import sqlite3
import numpy as np
import pandas as pd
from talib import stream
from traceback import print_exc
from multiprocessing import shared_memory
from backtester.back_static import GetBuyStg, GetSellStg, GetBuyConds, GetSellConds, GetBackloadCodeQuery, \
    get_trade_info, GetBuyStgFuture, GetSellStgFuture, GetBuyCondsFuture, GetSellCondsFuture
from utility.setting import DB_STOCK_BACK_TICK, BACK_TEMP, ui_num, DICT_SET, DB_STOCK_BACK_MIN, indicator, \
    DB_FUTURE_BACK_TICK, DB_FUTURE_BACK_MIN, DB_COIN_BACK_TICK, DB_COIN_BACK_MIN, list_stock_tick, \
    list_stock_min, list_coin_tick, list_coin_min
# noinspection PyUnresolvedReferences
from utility.static import timedelta_sec, pickle_read, pickle_write, dt_ymdhms, dt_ymdhm, get_angle_cf, get_ema_list, add_rolling_data


class BackEngineBase:
    def __init__(self, gubun, shared_cnt, lock, wq, tq, bq, beq_list, bstq_list, profile=False):
        self.gubun = gubun
        self.shared_cnt = shared_cnt
        self.shared_lock = lock
        self.wq = wq
        self.tq = tq
        self.bq = bq
        self.beq_list = beq_list
        self.beq = beq_list[gubun]
        self.bstq_list = bstq_list
        self.profile = profile
        self.dict_set = DICT_SET

        self.pr = None
        self.back_type = None
        self.betting = None
        self.avgtime = None
        self.avg_list = None
        self.startday = None
        self.endday = None
        self.starttime = None
        self.endtime = None

        self.startday_ = None
        self.endday_ = None
        self.starttime_ = None
        self.endtime_ = None
        self.same_days = False
        self.same_time = False

        self.buystg = None
        self.sellstg = None
        self.indistg = None
        self.dict_cn = None
        self.arry_code = None
        self.unit = None
        self.hour = None
        self.indicator = indicator
        self.arry_code_min = None

        self.code_list = []
        self.vars = []
        self.vars_list = []
        self.vars_lists = []
        self.high_low = []
        self.shogainfo = {}
        self.bhogainfo = {}
        self.dict_buystg = {}
        self.dict_sellstg = {}
        self.dict_sconds = {}
        self.day_info = {}
        self.trade_info = {}
        self.dict_info = {}
        self.dict_kosd = {}

        self.curr_trade_info = {}
        self.curr_day_info = {}
        self.info_for_order = None
        self.vturn = 0
        self.vkey = 0

        self.code = ''
        self.name = ''
        self.sell_cond = 0
        self.opti_turn = 0
        self.index = 0
        self.indexn = 0
        self.indexb = 0
        self.tick_count = 0
        self.sell_count = 0
        self.hoga_unit = 0
        self.profit = 0
        self.hold_time = 0

        self.k = None
        self.mc = None
        self.mh = None
        self.ml = None
        self.mv = None

        self.shared_list = []
        self.shared_count = None
        self.shared_info = None
        self.dict_condition = {}
        self.dict_cond_indexn = {}
        self.dict_findex = {}

        self.market_gubun = None
        self.is_oms = None
        self.is_tick = None
        self.ui_num_txt = None
        self.buy_hj_limit = None
        self.sell_hj_limit = None
        self.set_dict_cond = None
        self.set_weight = None
        self.sma_list = None
        self.base_cnt = None
        self.add_cnt = None
        self.hoga_sidex = None
        self.hoga_eidex = None
        self.angle_pct_cf = None
        self.angle_dtm_cf = None

        self.cached_stg_text = None
        self.prev_global_list = []
        self.conds_text = ''
        self.market_text = ''

        self.UpdateMarketGubun()
        self.UpdateSubVars()
        self.MainLoop()

    def UpdateSubVars(self):
        self.market_text = '주식' if self.market_gubun < 3 else '코인'
        self.ui_num_txt = 'S백테스트' if self.market_gubun < 3 else 'C백테스트'
        self.is_oms = self.dict_set['백테주문관리적용']
        self.is_tick = self.dict_set[f'{self.market_text}타임프레임']
        self.buy_hj_limit = self.dict_set[f'{self.market_text}매수시장가잔량범위']
        self.sell_hj_limit = self.dict_set[f'{self.market_text}매도시장가잔량범위']
        self.set_dict_cond = self.dict_set[f'{self.market_text}경과틱수설정']
        self.set_weight = self.dict_set[f'{self.market_text}비중조절']
        self.sma_list = get_ema_list(self.is_tick)

        if self.market_gubun == 1:
            factor_list = list_stock_tick if self.is_tick else list_stock_min
            self.dict_findex = {name: i for i, name in enumerate(factor_list)}
        else:
            factor_list = list_coin_tick if self.is_tick else list_coin_min
            self.dict_findex = {name: i for i, name in enumerate(factor_list)}

        self.base_cnt = self.dict_findex['관심종목'] + 1
        self.hoga_sidex = self.dict_findex['매도호가5']
        self.hoga_eidex = self.dict_findex['매수잔량5'] + 1
        self.add_cnt = len(self.dict_findex) - self.dict_findex['최고현재가']
        self.angle_pct_cf = get_angle_cf(self.market_gubun, self.is_tick, 0)
        self.angle_dtm_cf = get_angle_cf(self.market_gubun, self.is_tick, 1)

        if self.set_dict_cond:
            def compile_condition(x):
                if self.is_tick:
                    return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')
                else:
                    return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k+str(vturn)+str(vkey)] = self.indexn',
                                   '<string>', 'exec')

            text_list = self.set_dict_cond.split(';')
            half_cnt = int(len(text_list) / 2)
            key_list = text_list[:half_cnt]
            value_text_list = text_list[half_cnt:]
            value_comp_list = [compile_condition(x) for x in value_text_list]
            self.dict_condition = dict(zip(key_list, value_comp_list))
            self.conds_text += ';'.join(value_text_list)

        self.SetGlobalsFunc()

    def MainLoop(self):
        while True:
            data = self.beq.get()
            if '정보' in data[0]:
                if self.back_type == '최적화':
                    if data[0] == '백테정보':
                        self.betting = data[1]
                        avg_list = data[2]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.starttime = data[5]
                        self.endtime = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars = [var[1] for var in self.vars_list]
                        self.BackTest()
                elif self.back_type == '전진분석':
                    if data[0] == '백테정보':
                        self.betting = data[1]
                        avg_list = data[2]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.starttime = data[5]
                        self.endtime = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars = [var[1] for var in self.vars_list]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.CheckDayAndTime()
                        self.BackTest()
                elif self.back_type == 'GA최적화':
                    if data[0] == '백테정보':
                        self.betting = data[1]
                        avg_list = data[2]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.starttime = data[5]
                        self.endtime = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.CheckAvglist(avg_list)
                            self.CheckDayAndTime()
                    elif data[0] == '변수정보':
                        self.vars_lists = data[1]
                        self.opti_turn = data[2]
                        self.BackTest()
                elif self.back_type == '조건최적화':
                    if data[0] == '백테정보':
                        self.betting = data[1]
                        self.avgtime = data[2]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.starttime = data[5]
                        self.endtime = data[6]
                        self.CheckDayAndTime()
                    elif data[0] == '조건정보':
                        self.dict_buystg = {}
                        self.dict_sellstg = {}
                        self.dict_sconds = {}
                        error = False
                        for i in range(20):
                            if self.market_gubun in (1, 3):
                                buystg = GetBuyConds(data[2][i], self.gubun)
                                sellstg, dict_cond = GetSellConds(data[3][i], self.gubun)
                            else:
                                buystg = GetBuyCondsFuture(data[1], data[2][i], self.gubun)
                                sellstg, dict_cond = GetSellCondsFuture(data[1], data[3][i], self.gubun)
                            self.dict_buystg[i] = buystg
                            self.dict_sellstg[i] = sellstg
                            self.dict_sconds[i] = dict_cond
                            if buystg is None or sellstg is None: error = True
                        if error:
                            self.BackStop()
                        else:
                            self.opti_turn = data[4]
                            self.BackTest()
                elif self.back_type == '백테스트':
                    if data[0] == '백테정보':
                        self.betting = data[1]
                        self.avgtime = data[2]
                        self.startday = data[3]
                        self.endday = data[4]
                        self.starttime = data[5]
                        self.endtime = data[6]
                        if self.market_gubun in (1, 3):
                            self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        else:
                            self.buystg, self.indistg = GetBuyStgFuture(data[7], self.gubun)
                            self.sellstg, self.dict_sconds = GetSellStgFuture(data[8], self.gubun)
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.opti_turn = data[9]
                            self.CheckDayAndTime()
                            self.BackTest()
                elif self.back_type == '백파인더':
                    if data[0] == '백테정보':
                        self.avgtime = data[1]
                        self.startday = data[2]
                        self.endday = data[3]
                        self.starttime = data[4]
                        self.endtime = data[5]
                        try:
                            self.buystg = compile(data[6], '<string>', 'exec')
                        except:
                            print_exc()
                            self.BackStop()
                        else:
                            self.opti_turn = data[7]
                            self.CheckDayAndTime()
                            self.BackTest()

            elif data[0] == '백테유형':
                self.back_type = data[1]
            elif data[0] == '설정변경':
                self.dict_set = data[1]
                self.UpdateSubVars()
            elif data[0] == '종목명':
                if self.market_gubun == 1:
                    self.dict_cn = data[1]
                    self.dict_kosd = data[2]
                else:
                    self.dict_info = data[1]
            elif data[0] == '데이터로딩':
                self.DataLoad(data)
            elif data[0] == '공유데이터':
                self.shared_count = data[1]
                self.shared_info = data[2]
            elif data == '백테중지':
                self.BackStop(2)

    def DataLoad(self, data):
        def data_load(days):
            try:
                df = pd.read_sql(GetBackloadCodeQuery(self.is_tick, code, days, starttime, endtime), con)
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
                shared_array = np.ndarray((item['len'], item['data'].shape[1]),
                                          dtype=item['data'].dtype,
                                          buffer=shm.buf[offset:offset + data_size])

                np.copyto(shared_array, item['data'])
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
            self.arry_code = np.ndarray(
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
        return code

    def BackTest(self):
        if self.profile:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.sell_count = 0
        self.InitTradeInfo()

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
                indexs = self.arry_code[:, 0].astype(np.int64)
                day_last_indexs = [i for i in range(last) if str(indexs[i])[:8] != str(indexs[i + 1])[:8]]
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
                            print_exc()
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
        if self.profile: self.pr.print_stats(sort='cumulative')

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
        현재가, 저가대비고가등락율, 순매수금액, 당일거래대금 = self.info_for_order
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = 저가대비고가등락율
            elif self.set_weight[0] == 2:
                비중조절기준 = 순매수금액
            elif self.set_weight[0] == 3:
                비중조절기준 = 당일거래대금
            else:
                비중조절기준 = self._등락율각도(30)
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
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간, 추가매수시간, 매수호가, 매도호가, \
            매수호가_, 매도호가_, 추가매수가, 매수호가단위, 매도호가단위, 매수정정횟수, 매도정정횟수, 매수분할횟수, 매도분할횟수, \
            매수주문취소시간, 매도주문취소시간 = self.curr_trade_info.values()
        """
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.curr_trade_info.values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        매수시간, 매도시간, 매입금액 = int(self.arry_code[매수틱번호, 0]), self.index, 주문수량 * 매수가
        시가총액또는포지션, 평가금액, 수익금, 수익률 = self.GetProfitInfo(매도가, 매수가, 주문수량)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[self.vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True
        data = ('백테결과', self.name, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음,
                self.vturn, self.vkey)
        self.bstq_list[self.vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[self.vturn][self.vkey] = get_trade_info(1)

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
        aidx = self.avg_list.index(self.avgtime if self.back_type in ('백테스트', '조건최적화', '백파인더') else self.vars[0])
        return cidx + self.add_cnt * aidx

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
                return self.arry_code[sidx:eidx, self._fi('현재가')].mean()
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
                arry_high = self.arry_code[sidx:eidx, self._fi('분봉고가')]
                arry_low = self.arry_code[sidx:eidx, self._fi('분봉저가')]
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
                money_avg = self._초당거래대금평균(tick, pre)
            else:
                money_unit = self._분당거래대금N(pre)
                money_avg = self._분당거래대금평균(tick, pre)
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
            pre_avg_buys = self.arry_code[
                sidx - tick:eidx - tick, self._fi('초당매수수량' if self.is_tick else '분당매도수량')].sum()
            return cur_avg_buys / pre_avg_buys if pre_avg_buys != 0 else 0
        return 0

    def _매도수량변동성(self, tick, pre=0):
        if tick * 2 + pre <= self.tick_count:
            sidx, eidx = self._get_double_pre_index(tick, pre)
            cur_arry_sells = self.arry_code[sidx:eidx, self._fi('초당매수수량' if self.is_tick else '분당매수수량')].sum()
            pre_arry_sells = self.arry_code[
                sidx - tick:eidx - tick, self._fi('초당매수수량' if self.is_tick else '분당매도수량')].sum()
            return cur_arry_sells / pre_arry_sells if pre_arry_sells != 0 else 0
        return 0

    def _횡보감지(self, tick, per=0.5, pre=0):
        if tick + pre <= self.tick_count:
            return self._변동성(tick, pre) <= per
        return 0

    def _고가미갱신지속틱수(self):
        return self.indexn - self.high_low[1]

    def _저가미갱신지속틱수(self):
        return self.indexn - self.high_low[3]

    def _고점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[1]
        diff_pct = (self._현재가N(0) / self.high_low[0] - 1) * 100
        return np.round(math.atan2(diff_pct * cf, diff_tick) / (2 * math.pi) * 360, 2)

    def _저점기준등락율각도(self, cf):
        diff_tick = self.indexn - self.high_low[3]
        diff_pct = (self._현재가N(0) / self.high_low[2] - 1) * 100
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
        return self.indexn - self.high_low[3] <= tick and self._가격급등(tick, per)

    def _고가갱신후가격급락(self, tick, per=2):
        return self.indexn - self.high_low[1] <= tick and self._가격급락(tick, per)

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
                return self._현재가N(0) < short_ma and deviation_pct >= deviation2
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
        try:    AD_ = stream.AD(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre])
        except: AD_ = 0
        return AD_

    def _ADOSC_N(self, pre):
        try:    ADOSC_ = stream.ADOSC(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre], fastperiod=self.k[0], slowperiod=self.k[1])
        except: ADOSC_ = 0
        return ADOSC_

    def _ADXR_N(self, pre):
        try:    ADXR_ = stream.ADXR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[2])
        except: ADXR_ = 0
        return ADXR_

    def _APO_N(self, pre):
        try:    APO_ = stream.APO(self.mc[:-pre], fastperiod=self.k[3], slowperiod=self.k[4], matype=self.k[5])
        except: APO_ = 0
        return APO_

    def _AROOND_N(self, pre):
        try:    AROOND_, AROONU_ = stream.AROON(self.mh[:-pre], self.ml[:-pre], timeperiod=self.k[6])
        except: AROOND_, AROONU_ = 0, 0
        return AROOND_

    def _AROONU_N(self, pre):
        try:    AROOND_, AROONU_ = stream.AROON(self.mh[:-pre], self.ml[:-pre], timeperiod=self.k[3])
        except: AROOND_, AROONU_ = 0, 0
        return AROONU_

    def _ATR_N(self, pre):
        try:    ATR_ = stream.ATR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[7])
        except: ATR_ = 0
        return ATR_

    def _BBU_N(self, pre):
        try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
        except: BBU_, BBM_, BBL_ = 0, 0, 0
        return BBU_

    def _BBM_N(self, pre):
        try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
        except: BBU_, BBM_, BBL_ = 0, 0, 0
        return BBM_

    def _BBL_N(self, pre):
        try:    BBU_, BBM_, BBL_ = stream.BBANDS(self.mc[:-pre], timeperiod=self.k[8], nbdevup=self.k[9], nbdevdn=self.k[10], matype=self.k[11])
        except: BBU_, BBM_, BBL_ = 0, 0, 0
        return BBL_

    def _CCI_N(self, pre):
        try:    CCI_ = stream.CCI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[12])
        except: CCI_ = 0
        return CCI_

    def _DIM_N(self, pre):
        try:    DIM_ = stream.MINUS_DI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[13])
        except: DIM_ = 0, 0
        return DIM_

    def _DIP_N(self, pre):
        try:    DIP_ = stream.PLUS_DI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[13])
        except: DIP_ = 0
        return DIP_

    def _MACD_N(self, pre):
        try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
        except: MACD_, MACDS_, MACDH_ = 0, 0, 0
        return MACD_

    def _MACDS_N(self, pre):
        try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
        except: MACD_, MACDS_, MACDH_ = 0, 0, 0
        return MACDS_

    def _MACDH_N(self, pre):
        try:    MACD_, MACDS_, MACDH_ = stream.MACD(self.mc[:-pre], fastperiod=self.k[14], slowperiod=self.k[15], signalperiod=self.k[16])
        except: MACD_, MACDS_, MACDH_ = 0, 0, 0
        return MACDH_

    def _MFI_N(self, pre):
        try:    MFI_ = stream.MFI(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], self.mv[:-pre], timeperiod=self.k[17])
        except: MFI_ = 0
        return MFI_

    def _MOM_N(self, pre):
        try:    MOM_ = stream.MOM(self.mc[:-pre], timeperiod=self.k[18])
        except: MOM_ = 0
        return MOM_

    def _OBV_N(self, pre):
        try:    OBV_ = stream.OBV(self.mc[:-pre], self.mv)
        except: OBV_ = 0
        return OBV_

    def _PPO_N(self, pre):
        try:    PPO_ = stream.PPO(self.mc[:-pre], fastperiod=self.k[19], slowperiod=self.k[20], matype=self.k[21])
        except: PPO_ = 0
        return PPO_

    def _ROC_N(self, pre):
        try:    ROC_ = stream.ROC(self.mc[:-pre], timeperiod=self.k[22])
        except: ROC_ = 0
        return ROC_

    def _RSI_N(self, pre):
        try:    RSI_ = stream.RSI(self.mc[:-pre], timeperiod=self.k[23])
        except: RSI_ = 0
        return RSI_

    def _SAR_N(self, pre):
        try:    SAR_ = stream.SAR(self.mh[:-pre], self.ml[:-pre], acceleration=self.k[24], maximum=self.k[25])
        except: SAR_ = 0
        return SAR_

    def _STOCHSK_N(self, pre):
        try:    STOCHSK_, STOCHSD_ = stream.STOCH(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[26], slowk_period=self.k[27], slowk_matype=self.k[28], slowd_period=self.k[29], slowd_matype=self.k[30])
        except: STOCHSK_, STOCHSD_ = 0, 0
        return STOCHSK_

    def _STOCHSD_N(self, pre):
        try:    STOCHSK_, STOCHSD_ = stream.STOCH(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[26], slowk_period=self.k[27], slowk_matype=self.k[28], slowd_period=self.k[29], slowd_matype=self.k[30])
        except: STOCHSK_, STOCHSD_ = 0, 0
        return STOCHSD_

    def _STOCHFK_N(self, pre):
        try:    STOCHFK_, STOCHFD_ = stream.STOCHF(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[31], fastd_period=self.k[32], fastd_matype=self.k[33])
        except: STOCHFK_, STOCHFD_ = 0, 0
        return STOCHFK_

    def _STOCHFD_N(self, pre):
        try:    STOCHFK_, STOCHFD_ = stream.STOCHF(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], fastk_period=self.k[31], fastd_period=self.k[32], fastd_matype=self.k[33])
        except: STOCHFK_, STOCHFD_ = 0, 0
        return STOCHFD_

    def _WILLR_N(self, pre):
        try:    WILLR_ = stream.WILLR(self.mh[:-pre], self.ml[:-pre], self.mc[:-pre], timeperiod=self.k[34])
        except: WILLR_ = 0
        return WILLR_

    def SetGlobalsFunc(self):
        dict_add_func = {
            'now': self._now,
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
            '전일비각도': self._전일비각도,
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

    def Strategy(self):
        pass

    def UpdateMarketGubun(self):
        pass

    def UpdateGlobalsFunc(self, dict_add_func):
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
