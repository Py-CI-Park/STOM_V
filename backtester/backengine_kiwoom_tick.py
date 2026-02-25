import math
import os
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from multiprocessing import shared_memory
from backtester.back_static import GetBuyStg, GetSellStg, GetBuyConds, GetSellConds, GetBackloadCodeQuery, \
    AddAvgData, GetTradeInfo, GetBuyStgFuture, GetSellStgFuture, GetBuyCondsFuture, GetSellCondsFuture
from utility.setting import DB_STOCK_BACK_TICK, BACK_TEMP, ui_num, DICT_SET, DB_STOCK_BACK_MIN, indicator, dgree, \
    DB_FUTURE_BACK_TICK, DB_FUTURE_BACK_MIN, DB_COIN_BACK_TICK, DB_COIN_BACK_MIN
# noinspection PyUnresolvedReferences
from utility.static import timedelta_sec, pickle_read, pickle_write, GetKiwoomPgSgSp, GetUvilower5, dt_ymdhms, dt_ymdhm
from utility.safe_exec import safe_compile, guard_exec_code, UnsafeStrategyCodeError


# noinspection PyUnusedLocal
class BackEngineKiwoomTick:
    def __init__(self, gubun, shared_cnt, lock, wq, tq, bq, beq_list, bstq_list, profile=False):
        self.gubun        = gubun
        self.shared_cnt   = shared_cnt
        self.shared_lock  = lock
        self.wq           = wq
        self.tq           = tq
        self.bq           = bq
        self.beq_list     = beq_list
        self.beq          = beq_list[gubun]
        self.bstq_list    = bstq_list
        self.profile      = profile
        self.dict_set     = DICT_SET

        self.pr           = None
        self.back_type    = None
        self.betting      = None
        self.avgtime      = None
        self.avg_list     = None
        self.startday     = None
        self.endday       = None
        self.starttime    = None
        self.endtime      = None

        self.startday_    = None
        self.endday_      = None
        self.starttime_   = None
        self.endtime_     = None
        self.same_days    = False
        self.same_time    = False

        self.buystg       = None
        self.sellstg      = None
        self.indistg      = None
        self.dict_cn      = None
        self.arry_data    = None
        self.unit         = None
        self.hour         = None
        self.indicator    = indicator

        self.code_list    = []
        self.vars         = []
        self.vars_list    = []
        self.vars_lists   = []
        self.bhogainfo    = {}
        self.shogainfo    = {}
        self.dict_buystg  = {}
        self.dict_sellstg = {}
        self.dict_sconds  = {}
        self.day_info     = {}
        self.trade_info   = {}
        self.dict_info    = {}

        self.code         = ''
        self.name         = ''
        self.sell_cond    = 0
        self.opti_turn    = 0
        self.index        = 0
        self.indexn       = 0
        self.indexb       = 0
        self.tick_count   = 0
        self.sell_count   = 0

        self.shared_list      = []
        self.shared_count     = None
        self.shared_info      = None
        self.dict_condition   = {}
        self.dict_cond_indexn = {}

        self.market_gubun     = None
        self.is_oms           = None
        self.is_tick          = None
        self.ui_num_txt       = None
        self.buy_hj_limit     = None
        self.sell_hj_limit    = None
        self.set_dict_cond    = None
        self.set_weight       = None

        self.Settings()
        self.SetDictCondition()
        self.MainLoop()

    def Settings(self):
        self.market_gubun  = 1
        self.ui_num_txt    = 'S백테스트'
        self.is_oms        = self.dict_set['백테주문관리적용']
        self.is_tick       = self.dict_set['주식타임프레임']
        self.buy_hj_limit  = self.dict_set['주식매수시장가잔량범위']
        self.sell_hj_limit = self.dict_set['주식매도시장가잔량범위']
        self.set_dict_cond = self.dict_set['주식경과틱수설정']
        self.set_weight    = self.dict_set['주식비중조절']

    def SetDictCondition(self):
        if self.set_dict_cond:
            def compile_condition(x):
                if self.is_tick:
                    return safe_compile(
                        f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn',
                        '<string>', 'exec', context='BackEngineKiwoomTick.dict_condition.tick'
                    )
                else:
                    return safe_compile(
                        f'if {x}:\n    self.dict_cond_indexn[종목코드][k+str(vturn)+str(vkey)] = self.indexn',
                        '<string>', 'exec', context='BackEngineKiwoomTick.dict_condition.min'
                    )
            text_list  = self.set_dict_cond.split(';')
            half_cnt   = int(len(text_list) / 2)
            key_list   = text_list[:half_cnt]
            value_list = text_list[half_cnt:]
            try:
                value_list = [compile_condition(x) for x in value_list]
            except (UnsafeStrategyCodeError, SyntaxError, ValueError) as e:
                self.wq.put((ui_num[self.ui_num_txt], f'경과틱수 조건식 검증 실패 - {e}'))
                self.wq.put((ui_num[self.ui_num_txt], '해당 조건식은 비활성화되어 백테스트를 계속 진행합니다.'))
                self.dict_condition = {}
                return
            self.dict_condition = dict(zip(key_list, value_list))

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
                                buystg = GetBuyConds(data[2][i], self.gubun)
                                sellstg, dict_cond = GetSellConds(data[3][i], self.gubun)
                            else:
                                buystg = GetBuyCondsFuture(data[1], data[2][i], self.gubun)
                                sellstg, dict_cond = GetSellCondsFuture(data[1], data[3][i], self.gubun)
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
                        self.avgtime   = data[1]
                        self.startday  = data[2]
                        self.endday    = data[3]
                        self.starttime = data[4]
                        self.endtime   = data[5]
                        try:
                            self.buystg = safe_compile(data[6], '<string>', 'exec', context='BackEngineKiwoomTick.backfinder.buystg')
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
                self.SetDictCondition()
            elif data[0] == '종목명':
                if self.market_gubun == 1:
                    self.dict_cn = data[1]
                else:
                    self.dict_info = data[1]
            elif data[0] == '데이터로딩':
                self.DataLoad(data)
            elif data[0] == '공유데이터':
                self.shared_count = data[1]
                self.shared_info  = data[2]
            elif data == '전체틱수계산':
                self.GetTickCount()
            elif data == '백테중지':
                self.BackStop(2)

    def DataLoad(self, data):
        def data_load(days):
            try:
                df = pd.read_sql(GetBackloadCodeQuery(code, days, starttime, endtime), con)
            except:
                pass
            else:
                if len(df) > 0:
                    df = AddAvgData(df, self.market_gubun, self.is_tick, avg_list)
                    array = np.array(df)
                    if self.dict_set['백테일괄로딩']:
                        name = f'back_{self.gubun}_{i}'
                        shm = shared_memory.SharedMemory(name=name, create=True, size=array.nbytes)
                        shared_array = np.ndarray(array.shape, dtype=array.dtype, buffer=shm.buf)
                        np.copyto(shared_array, array)
                        shared_info.append({
                            'code': code,
                            'len': len(array),
                            'shm_name': shm.name,
                            'shape': array.shape,
                            'dtype': array.dtype
                        })
                        self.shared_list.append(shm)
                    else:
                        file_name = f'{BACK_TEMP}/back_{self.gubun}_{i}'
                        pickle_write(file_name, array)
                        shared_info.append({
                            'code': code,
                            'len': len(array),
                            'file_name': file_name
                        })

        if self.market_gubun == 1:
            con = sqlite3.connect(DB_STOCK_BACK_TICK if self.is_tick else DB_STOCK_BACK_MIN)
        elif self.market_gubun == 2:
            con = sqlite3.connect(DB_FUTURE_BACK_TICK if self.is_tick else DB_FUTURE_BACK_MIN)
        else:
            con = sqlite3.connect(DB_COIN_BACK_TICK if self.is_tick else DB_COIN_BACK_MIN)

        shared_info = []
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

    def GetTickCount(self):
        total_ticks = 0
        while True:
            code = self.GetArrayData()
            if code is not None:
                total_ticks += len(self.arry_data)
            else:
                break
        self.bq.put(total_ticks)

    def InitTradeInfo(self):
        self.tick_count = 0
        self.dict_cond_indexn = {}
        if self.is_oms:
            v1 = GetTradeInfo(3)
            v2 = GetTradeInfo(2)
            if self.market_gubun in (2, 4):
                v2['주문포지션'] = ''

            if self.opti_turn == 1:
                self.day_info   = {t: {k: v1 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
                self.trade_info = {t: {k: v2 for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
            elif self.opti_turn == 3:
                self.day_info   = {t: {k: v1 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
                self.trade_info = {t: {k: v2 for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
            else:
                self.day_info   = {0: {0: v1}}
                self.trade_info = {0: {0: v2}}
        else:
            v = GetTradeInfo(1)
            if self.opti_turn == 1:
                self.trade_info = {t: {k: v for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
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
            self.arry_data = np.ndarray(shared_info['shape'], dtype=shared_info['dtype'], buffer=shm.buf).copy()
            shm.close()
        else:
            file_name = shared_info.get('file_name')
            if file_name is None:
                raise ValueError('shared_info missing file_name')
            back_temp_root = os.path.abspath(BACK_TEMP)
            target_pkl = os.path.abspath(file_name if str(file_name).endswith('.pkl') else f'{file_name}.pkl')
            try:
                in_back_temp = os.path.commonpath([target_pkl, back_temp_root]) == back_temp_root
            except ValueError:
                in_back_temp = False
            if not in_back_temp:
                raise ValueError(f'Unsafe shared_info file_name: {file_name}')
            self.arry_data = pickle_read(file_name, allowed_root=back_temp_root)
            if self.arry_data is None:
                raise ValueError(f'Failed to load backtest pickle data: {file_name}')

        if self.same_days and self.same_time:
            pass
        elif self.same_time:
            self.arry_data = self.arry_data[(self.arry_data[:, 0] >= self.startday * self.unit) &
                                            (self.arry_data[:, 0] <= self.endday * self.unit + self.hour)]
        elif self.same_days:
            self.arry_data = self.arry_data[(self.arry_data[:, 0] % self.unit >= self.starttime) &
                                            (self.arry_data[:, 0] % self.unit <= self.endtime)]
        else:
            self.arry_data = self.arry_data[(self.arry_data[:, 0] >= self.startday * self.unit) &
                                            (self.arry_data[:, 0] <= self.endday * self.unit + self.hour) &
                                            (self.arry_data[:, 0] % self.unit >= self.starttime) &
                                            (self.arry_data[:, 0] % self.unit <= self.endtime)]
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
                if self.market_gubun < 3:
                    if self.dict_set['주식매수금지블랙리스트'] and code in self.dict_set['주식블랙리스트'] and self.back_type != '백파인더':
                        self.tq.put('백테완료')
                        continue
                else:
                    if self.dict_set['코인매수금지블랙리스트'] and self.code in self.dict_set['코인블랙리스트'] and self.back_type != '백파인더':
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

            last = len(self.arry_data) - 1
            if last > 0:
                indexs = self.arry_data[:, 0].astype(np.int64)
                day_last_indexs = [i for i in range(last) if str(indexs[i])[:8] != str(indexs[i + 1])[:8]]
                day_last_indexs.append(last)

                start_idx = 0
                for end_idx in day_last_indexs:
                    for i in range(start_idx, end_idx):
                        self.index  = indexs[i]
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
                            if self.opti_turn in (1, 3): self.tq.put('탐색완료')
                            if not self.beq.empty() and self.beq.get() == '백테중지':
                                self.BackStop(1)
                                return

                    j += 1
                    if j == 1000:
                        j = 0
                        if self.opti_turn in (1, 3): self.tq.put('탐색완료')

                    self.index  = indexs[end_idx]
                    self.indexn = end_idx
                    self.tick_count += 1
                    self.LastSell()
                    self.InitTradeInfo()
                    start_idx = end_idx + 1

            self.tq.put('백테완료')

        if self.opti_turn in (1, 3): self.tq.put(('탐색완료', j))
        if self.profile: self.pr.print_stats(sort='cumulative')

    def Strategy(self):
        def now():
            return dt_ymdhms(str(self.index))

        def Parameter_Previous(aindex, pre):
            if pre < 데이터길이:
                pindex = (self.indexn - pre) if pre != -1 else self.indexb
                return self.arry_data[pindex, aindex]
            return 0

        def 현재가N(pre):
            return Parameter_Previous(1, pre)

        def 시가N(pre):
            return Parameter_Previous(2, pre)

        def 고가N(pre):
            return Parameter_Previous(3, pre)

        def 저가N(pre):
            return Parameter_Previous(4, pre)

        def 등락율N(pre):
            return Parameter_Previous(5, pre)

        def 당일거래대금N(pre):
            return Parameter_Previous(6, pre)

        def 체결강도N(pre):
            return Parameter_Previous(7, pre)

        def 거래대금증감N(pre):
            return Parameter_Previous(8, pre)

        def 전일비N(pre):
            return Parameter_Previous(9, pre)

        def 회전율N(pre):
            return Parameter_Previous(10, pre)

        def 전일동시간비N(pre):
            return Parameter_Previous(11, pre)

        def 시가총액N(pre):
            return Parameter_Previous(12, pre)

        def 라운드피겨위5호가이내N(pre):
            return Parameter_Previous(13, pre)

        def 초당매수수량N(pre):
            return Parameter_Previous(14, pre)

        def 초당매도수량N(pre):
            return Parameter_Previous(15, pre)

        def 초당거래대금N(pre):
            return Parameter_Previous(19, pre)

        def 고저평균대비등락율N(pre):
            return Parameter_Previous(20, pre)

        def 매도총잔량N(pre):
            return Parameter_Previous(21, pre)

        def 매수총잔량N(pre):
            return Parameter_Previous(22, pre)

        def 매도호가5N(pre):
            return Parameter_Previous(23, pre)

        def 매도호가4N(pre):
            return Parameter_Previous(24, pre)

        def 매도호가3N(pre):
            return Parameter_Previous(25, pre)

        def 매도호가2N(pre):
            return Parameter_Previous(26, pre)

        def 매도호가1N(pre):
            return Parameter_Previous(27, pre)

        def 매수호가1N(pre):
            return Parameter_Previous(28, pre)

        def 매수호가2N(pre):
            return Parameter_Previous(29, pre)

        def 매수호가3N(pre):
            return Parameter_Previous(30, pre)

        def 매수호가4N(pre):
            return Parameter_Previous(31, pre)

        def 매수호가5N(pre):
            return Parameter_Previous(32, pre)

        def 매도잔량5N(pre):
            return Parameter_Previous(33, pre)

        def 매도잔량4N(pre):
            return Parameter_Previous(34, pre)

        def 매도잔량3N(pre):
            return Parameter_Previous(35, pre)

        def 매도잔량2N(pre):
            return Parameter_Previous(36, pre)

        def 매도잔량1N(pre):
            return Parameter_Previous(37, pre)

        def 매수잔량1N(pre):
            return Parameter_Previous(38, pre)

        def 매수잔량2N(pre):
            return Parameter_Previous(39, pre)

        def 매수잔량3N(pre):
            return Parameter_Previous(40, pre)

        def 매수잔량4N(pre):
            return Parameter_Previous(41, pre)

        def 매수잔량5N(pre):
            return Parameter_Previous(42, pre)

        def 매도수5호가잔량합N(pre):
            return Parameter_Previous(43, pre)

        def 관심종목N(pre):
            return Parameter_Previous(44, pre)

        def 이동평균(tick, pre=0):
            if tick == 60:
                return Parameter_Previous(45, pre)
            elif tick == 300:
                return Parameter_Previous(46, pre)
            elif tick == 600:
                return Parameter_Previous(47, pre)
            elif tick == 1200:
                return Parameter_Previous(48, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    return round(self.arry_data[sindex:eindex, 1].mean(), 3)
                return 0

        def GetArrayIndex(aindex):
            return aindex + 13 * self.avg_list.index(self.avgtime if self.back_type in ('백테스트', '조건최적화', '백파인더') else self.vars[0])

        def Parameter_Area(aindex, vindex, tick, pre, gubun_):
            if tick in self.avg_list:
                return Parameter_Previous(GetArrayIndex(aindex), pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    if gubun_ == 'max':
                        return self.arry_data[sindex:eindex, vindex].max()
                    elif gubun_ == 'min':
                        return self.arry_data[sindex:eindex, vindex].min()
                    elif gubun_ == 'sum':
                        return self.arry_data[sindex:eindex, vindex].sum()
                    else:
                        return self.arry_data[sindex:eindex, vindex].mean()
                return 0

        def 최고현재가(tick, pre=0):
            return Parameter_Area(49, 1, tick, pre, 'max')

        def 최저현재가(tick, pre=0):
            return Parameter_Area(50, 1, tick, pre, 'min')

        def 체결강도평균(tick, pre=0):
            return round(Parameter_Area(51, 7, tick, pre, 'mean'), 3)

        def 최고체결강도(tick, pre=0):
            return Parameter_Area(52, 7, tick, pre, 'max')

        def 최저체결강도(tick, pre=0):
            return Parameter_Area(53, 7, tick, pre, 'min')

        def 최고초당매수수량(tick, pre=0):
            return Parameter_Area(54, 14, tick, pre, 'max')

        def 최고초당매도수량(tick, pre=0):
            return Parameter_Area(55, 15, tick, pre, 'max')

        def 누적초당매수수량(tick, pre=0):
            return Parameter_Area(56, 14, tick, pre, 'sum')

        def 누적초당매도수량(tick, pre=0):
            return Parameter_Area(57, 15, tick, pre, 'sum')

        def 초당거래대금평균(tick, pre=0):
            return int(Parameter_Area(58, 19, tick, pre, 'mean'))

        def Parameter_Dgree(aindex, vindex, tick, pre, cf):
            if tick in self.avg_list:
                return Parameter_Previous(GetArrayIndex(aindex), pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn - pre - tick + 1) if pre != -1  else self.indexb - tick + 1
                    eindex = (self.indexn - pre) if pre != -1  else self.indexb
                    dmp_gap = self.arry_data[eindex, vindex] - self.arry_data[sindex, vindex]
                    return round(math.atan2(dmp_gap * cf, tick) / (2 * math.pi) * 360, 2)
                return 0

        def 등락율각도(tick, pre=0):
            return Parameter_Dgree(59, 5, tick, pre, dgree['stock']['tick'][0])

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(60, 6, tick, pre, dgree['stock']['tick'][1])

        def 전일비각도(tick, pre=0):
            return Parameter_Dgree(61, 9, tick, pre, 1)

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn and \
                    조건명 in self.dict_cond_indexn[종목코드] and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        종목명, 종목코드, 데이터길이, 시분초 = self.name, self.code, self.tick_count, int(str(self.index)[8:])
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, \
            초당매수수량, 초당매도수량, VI해제시간, VI가격, VI호가단위, 초당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도수5호가잔량합, 관심종목 = self.arry_data[self.indexn, 1:45]
        호가단위 = 매도호가2 - 매도호가1
        VI해제시간, VI아래5호가 = dt_ymdhms(str(int(VI해제시간))), GetUvilower5(VI가격, VI호가단위, self.index)
        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.buy_hj_limit]
        self.shogainfo = shogainfo[:self.sell_hj_limit]

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(guard_exec_code(v, f'BackEngineKiwoomTick.condition.{k}'))

        if self.opti_turn == 1:
            for vturn in self.trade_info:
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    return

                for vkey in self.trade_info[vturn]:
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if vturn == 0 and self.tick_count < self.vars[0]:
                        continue

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                        exec(guard_exec_code(self.buystg, 'BackEngineKiwoomTick.buystg'))
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                        exec(guard_exec_code(self.sellstg, 'BackEngineKiwoomTick.sellstg'))

        elif self.opti_turn == 3:
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

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                        if self.back_type != '조건최적화':
                            exec(guard_exec_code(self.buystg, 'BackEngineKiwoomTick.buystg'))
                        else:
                            exec(guard_exec_code(self.dict_buystg[index_], f'BackEngineKiwoomTick.dict_buystg.{index_}'))
                    else:
                        수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                        if self.back_type != '조건최적화':
                            exec(guard_exec_code(self.sellstg, 'BackEngineKiwoomTick.sellstg'))
                        else:
                            exec(guard_exec_code(self.dict_sellstg[index_], f'BackEngineKiwoomTick.dict_sellstg.{index_}'))

        else:
            vturn, vkey = 0, 0
            if self.back_type in ('최적화', '전진분석'):
                if self.tick_count < self.vars[0]:
                    return
            else:
                if self.tick_count < self.avgtime:
                    return

            매수, 매도 = True, False
            if not self.trade_info[vturn][vkey]['보유중']:
                if not 관심종목: return
                self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                exec(guard_exec_code(self.buystg, 'BackEngineKiwoomTick.buystg'))
            else:
                수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                exec(guard_exec_code(self.sellstg, 'BackEngineKiwoomTick.sellstg'))

    def SetBuyCount(self, vturn, vkey, 현재가, 고가, 저가, 등락율각도, 당일거래대금각도, 전일비, 회전율, 전일동시간비):
        if self.set_weight[0] == 0:
            betting = self.betting
        else:
            if self.set_weight[0] == 1:
                비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
            elif self.set_weight[0] == 2:
                비중조절기준 = 등락율각도
            elif self.set_weight[0] == 3:
                비중조절기준 = 당일거래대금각도
            elif self.set_weight[0] == 4:
                비중조절기준 = 전일비
            elif self.set_weight[0] == 5:
                비중조절기준 = 회전율
            else:
                비중조절기준 = 전일동시간비

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

        self.trade_info[vturn][vkey]['주문수량'] = int(betting / 현재가)

    def Buy(self, vturn, vkey, gubun=None):
        매수금액 = 0
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        if 주문수량 > 0:
            for 매도호가, 매도잔량 in self.bhogainfo:
                if 미체결수량 - 매도잔량 <= 0:
                    매수금액 += 매도호가 * 미체결수량
                    미체결수량 -= 매도잔량
                    break
                else:
                    매수금액 += 매도호가 * 매도잔량
                    미체결수량 -= 매도잔량
            if 미체결수량 <= 0:
                self.trade_info[vturn][vkey] = {
                    '보유중': 1,
                    '매수가': int(round(매수금액 / 주문수량)),
                    '매도가': 0,
                    '주문수량': 0,
                    '보유수량': 주문수량,
                    '최고수익률': 0.,
                    '최저수익률': 0.,
                    '매수틱번호': self.indexn,
                    '매수시간': dt_ymdhms(str(self.index)) if self.is_tick else dt_ymdhm(str(self.index))
                }

    def SetSellCount(self, vturn, vkey, 현재가, now_time):
        _, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        _, _, 수익률 = GetKiwoomPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
        if 수익률 > 최고수익률:   self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
        보유시간 = (now_time - 매수시간).total_seconds() if self.is_tick else int((now_time - 매수시간).total_seconds() / 60)
        self.indexb = 매수틱번호
        self.trade_info[vturn][vkey]['주문수량'] = 보유수량
        return 수익률, 최고수익률, 최저수익률, 보유수량, 보유시간, 매수틱번호

    def Sell(self, vturn, vkey, sell_cond, gubun=None):
        매도금액 = 0
        주문수량 = 미체결수량 = self.trade_info[vturn][vkey]['주문수량']
        for 매수호가, 매수잔량 in self.shogainfo:
            if 미체결수량 - 매수잔량 <= 0:
                매도금액 += 매수호가 * 미체결수량
                미체결수량 -= 매수잔량
                break
            else:
                매도금액 += 매수호가 * 매수잔량
                미체결수량 -= 매수잔량
        if 미체결수량 <= 0:
            self.trade_info[vturn][vkey]['매도가'] = int(round(매도금액 / 주문수량))
            self.sell_cond = sell_cond
            self.CalculationEyun(vturn, vkey)

    def LastSell(self):
        if self.is_tick:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 23:43]
        else:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 26:46]
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        shogainfo = shogainfo[:self.sell_hj_limit]

        for vturn in self.trade_info:
            for vkey in self.trade_info[vturn]:
                if self.trade_info[vturn][vkey]['보유중']:
                    매도금액 = 0
                    보유수량 = 미체결수량 = self.trade_info[vturn][vkey]['보유수량']
                    for 매수호가, 매수잔량 in shogainfo:
                        if 미체결수량 - 매수잔량 <= 0:
                            매도금액 += 매수호가 * 미체결수량
                            미체결수량 -= 매수잔량
                            break
                        else:
                            매도금액 += 매수호가 * 매수잔량
                            미체결수량 -= 매수잔량
                    if 미체결수량 <= 0:
                        self.trade_info[vturn][vkey]['매도가'] = int(round(매도금액 / 보유수량))
                    elif 매도금액 == 0:
                        self.trade_info[vturn][vkey]['매도가'] = self.arry_data[self.indexn, 1]
                    else:
                        self.trade_info[vturn][vkey]['매도가'] = int(round(매도금액 / (보유수량 - 미체결수량)))

                    self.trade_info[vturn][vkey]['주문수량'] = 보유수량
                    self.sell_cond = 0
                    self.CalculationEyun(vturn, vkey)

    def CalculationEyun(self, vturn, vkey):
        """
        보유중, 매수가, 매도가, 주문수량, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        """
        _, 매수가, 매도가, 주문수량, _, _, _, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        if self.is_tick:
            보유시간 = int((dt_ymdhms(str(self.index)) - 매수시간).total_seconds())
        else:
            보유시간 = int((dt_ymdhm(str(self.index)) - 매수시간).total_seconds() / 60)
        시가총액 = int(self.arry_data[self.indexn, 12])
        매수시간, 매도시간, 매입금액 = int(self.arry_data[매수틱번호, 0]), self.index, 주문수량 * 매수가
        평가금액, 수익금, 수익률 = GetKiwoomPgSgSp(매입금액, 주문수량 * 매도가)
        매도조건 = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        추가매수시간, 잔고없음 = '', True
        data = ('백테결과', self.name, 시가총액, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매입금액, 평가금액, 수익률, 수익금, 매도조건, 추가매수시간, 잔고없음, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[vturn][vkey] = GetTradeInfo(1)
