import gc
import math
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from utility.setting import DB_STOCK_BACK_TICK, BACK_TEMP, ui_num, DICT_SET, DB_STOCK_BACK_MIN, indicator
# noinspection PyUnresolvedReferences
from utility.static import strp_time, timedelta_sec, pickle_read, pickle_write, GetKiwoomPgSgSp, GetUvilower5, GetHogaunit
from backtester.back_static import GetBuyStg, GetSellStg, GetBuyConds, GetSellConds, GetBackloadCodeQuery, GetBackloadDayQuery, AddAvgData, GetTradeInfo


# noinspection PyUnusedLocal
class BackEngineKiwoomTick:
    def __init__(self, gubun, wq, tq, bq, beq_list, bstq_list, profile=False):
        gc.disable()
        self.gubun        = gubun
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

        self.buystg       = None
        self.sellstg      = None
        self.indistg      = None
        self.dict_cn      = None
        self.arry_data    = None
        self.indicator    = indicator

        self.code_list    = []
        self.vars         = []
        self.vars_list    = []
        self.vars_lists   = []
        self.dict_arry    = {}
        self.bhogainfo    = {}
        self.shogainfo    = {}
        self.dict_buystg  = {}
        self.dict_sellstg = {}
        self.dict_sconds  = {}
        self.day_info     = {}
        self.trade_info   = {}

        self.code         = ''
        self.name         = ''
        self.sell_cond    = 0
        self.opti_turn    = 0
        self.index        = 0
        self.indexn       = 0
        self.indexb       = 0
        self.tick_count   = 0
        self.sell_count   = 0

        self.tick_calcul      = False
        self.dict_condition   = {}
        self.dict_cond_indexn = {}
        self.SetDictCondition()

        self.MainLoop()

    def SetDictCondition(self):
        if self.dict_set['주식경과틱수설정'] != '':
            def compile_condition(x):
                return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')
            text_list  = self.dict_set['주식경과틱수설정'].split(';')
            half_cnt   = int(len(text_list) / 2)
            key_list   = text_list[:half_cnt]
            value_list = text_list[half_cnt:]
            value_list = [compile_condition(x) for x in value_list]
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
                        self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        self.CheckAvglist(avg_list)
                        if self.buystg is None or self.sellstg is None: self.BackStop()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == '전진분석':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.starttime = data[3]
                        self.endtime   = data[4]
                        self.buystg, self.indistg = GetBuyStg(data[5], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStg(data[6], self.gubun)
                        self.CheckAvglist(avg_list)
                        if self.buystg is None or self.sellstg is None: self.BackStop()
                    elif data[0] == '변수정보':
                        self.vars_list = data[1]
                        self.opti_turn = data[2]
                        self.vars      = [var[1] for var in self.vars_list]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        if self.opti_turn == 0: self.tick_calcul = False
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == 'GA최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        avg_list       = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        self.CheckAvglist(avg_list)
                        if self.buystg is None or self.sellstg is None: self.BackStop()
                    elif data[0] == '변수정보':
                        self.vars_lists = data[1]
                        self.InitDivid()
                        self.InitTradeInfo()
                        self.BackTest()
                elif self.back_type == '조건최적화':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                    elif data[0] == '조건정보':
                        self.dict_buystg  = {}
                        self.dict_sellstg = {}
                        self.dict_sconds  = {}
                        error = False
                        for i in range(20):
                            buystg = GetBuyConds(data[1][i], self.gubun)
                            sellstg, dict_cond = GetSellConds(data[2][i], self.gubun)
                            self.dict_buystg[i]  = buystg
                            self.dict_sellstg[i] = sellstg
                            self.dict_sconds[i]  = dict_cond
                            if buystg is None or sellstg is None: error = True
                        self.InitDivid()
                        self.InitTradeInfo()
                        if error:
                            self.BackStop()
                        else:
                            self.BackTest()
                elif self.back_type == '백테스트':
                    if data[0] == '백테정보':
                        self.betting   = data[1]
                        self.avgtime   = data[2]
                        self.startday  = data[3]
                        self.endday    = data[4]
                        self.starttime = data[5]
                        self.endtime   = data[6]
                        self.buystg, self.indistg = GetBuyStg(data[7], self.gubun)
                        self.sellstg, self.dict_sconds = GetSellStg(data[8], self.gubun)
                        self.InitDivid()
                        self.InitTradeInfo()
                        if self.buystg is None or self.sellstg is None:
                            self.BackStop()
                        else:
                            self.BackTest()
                elif self.back_type == '백파인더':
                    if data[0] == '백테정보':
                        self.avgtime   = data[1]
                        self.startday  = data[2]
                        self.endday    = data[3]
                        self.starttime = data[4]
                        self.endtime   = data[5]
                        self.InitDivid()
                        self.InitTradeInfo()
                        try:
                            self.buystg = compile(data[6], '<string>', 'exec')
                        except:
                            print_exc()
                            self.BackStop()
                        else:
                            self.BackTest()
            elif data[0] == '백테유형':
                self.back_type = data[1]
                self.tick_calcul = False
            elif data[0] == '설정변경':
                self.dict_set = data[1]
                self.SetDictCondition()
            elif data[0] == '종목명':
                self.dict_cn = data[1]
            elif data[0] in ('데이터크기', '데이터로딩'):
                self.DataLoad(data)
            elif data[0] == '데이터이동':
                self.SendData(data)
            elif data[0] == '데이터전송':
                self.RecvdData(data)

    def SendData(self, data):
        _, cnt, procn = data
        for i, code in enumerate(self.code_list):
            if i >= cnt:
                data = ('데이터전송', code, self.dict_arry[code])
                self.beq_list[procn].put(data)
                del self.dict_arry[code]
                print(f'백테엔진 데이터 재분배: 종목코드[{code}] 엔진번호[{self.gubun}->{procn}]')
        self.code_list = self.code_list[:cnt]

    def RecvdData(self, data):
        _, code, arry = data
        if code in self.dict_arry.keys():
            arry = np.r_[self.dict_arry[code], arry]
        self.dict_arry[code] = arry
        if code not in self.code_list:
            self.code_list.append(code)

    def InitDivid(self):
        self.sell_count = 0
        if self.back_type in ('백테스트', '백파인더'):     self.opti_turn = 2
        elif self.back_type in ('GA최적화', '조건최적화'): self.opti_turn = 3

    def InitTradeInfo(self):
        self.dict_cond_indexn = {}
        self.tick_count = 0
        v = GetTradeInfo(1)
        if self.opti_turn == 1:
            self.trade_info = {t: {k: v for k in range(len(x[0]))} for t, x in enumerate(self.vars_list) if len(x[0]) > 1}
        elif self.opti_turn == 3:
            self.trade_info = {t: {k: v for k in range(20)} for t in range(50 if self.back_type == 'GA최적화' else 1)}
        else:
            self.trade_info = {0: {0: v}}

    def DataLoad(self, data):
        bk = 0
        divid_mode = data[-1]
        is_tick = self.dict_set['주식타임프레임']
        con = sqlite3.connect(DB_STOCK_BACK_TICK if is_tick else DB_STOCK_BACK_MIN)

        if divid_mode == '종목코드별 분류':
            gubun, startday, endday, starttime, endtime, code_list, avg_list, code_days, _, _, _ = data
            for code in code_list:
                df_tick, len_df_tick = None, 0
                try:
                    df_tick = pd.read_sql(GetBackloadCodeQuery(code, code_days[code], starttime, endtime), con)
                    len_df_tick = len(df_tick)
                except:
                    pass
                if gubun == '데이터크기':
                    self.bq.put((code, len_df_tick))
                elif len_df_tick > 0:
                    df_tick = AddAvgData(df_tick, 3, is_tick, avg_list)
                    arry_tick = np.array(df_tick)
                    if self.dict_set['백테일괄로딩']:
                        self.dict_arry[code] = arry_tick
                    else:
                        pickle_write(f'{BACK_TEMP}/{self.gubun}_{code}_tick', arry_tick)
                    self.code_list.append(code)
                    bk += 1
        elif divid_mode == '일자별 분류':
            gubun, startday, endday, starttime, endtime, day_list, avg_list, code_days, day_codes, _, _ = data
            if gubun == '데이터크기':
                for day in day_list:
                    len_df_tick = 0
                    for code in day_codes[day]:
                        try:
                            df_tick = pd.read_sql(GetBackloadDayQuery(day, code, starttime, endtime), con)
                            len_df_tick += len(df_tick)
                        except:
                            pass
                    self.bq.put((day, len_df_tick))
            elif gubun == '데이터로딩':
                code_list = []
                for day in day_list:
                    for code in day_codes[day]:
                        if code not in code_list:
                            code_list.append(code)
                for code in code_list:
                    days = [day for day in day_list if day in code_days[code]]
                    df_tick, len_df_tick = None, 0
                    try:
                        df_tick = pd.read_sql(GetBackloadCodeQuery(code, days, starttime, endtime), con)
                        len_df_tick += len(df_tick)
                    except:
                        pass
                    if len_df_tick > 0:
                        df_tick = AddAvgData(df_tick, 3, is_tick, avg_list)
                        arry_tick = np.array(df_tick)
                        if self.dict_set['백테일괄로딩']:
                            self.dict_arry[code] = arry_tick
                        else:
                            pickle_write(f'{BACK_TEMP}/{self.gubun}_{code}_tick', arry_tick)
                        self.code_list.append(code)
                        bk += 1
        else:
            gubun, startday, endday, starttime, endtime, day_list, avg_list, _, _, code, _ = data
            if gubun == '데이터크기':
                for day in day_list:
                    len_df_tick = 0
                    try:
                        df_tick = pd.read_sql(GetBackloadDayQuery(day, code, starttime, endtime), con)
                        len_df_tick = len(df_tick)
                    except:
                        pass
                    self.bq.put((day, len_df_tick))
            elif gubun == '데이터로딩':
                df_tick, len_df_tick = None, 0
                try:
                    df_tick = pd.read_sql(GetBackloadCodeQuery(code, day_list, starttime, endtime), con)
                    len_df_tick = len(df_tick)
                except:
                    pass
                if len_df_tick > 0:
                    df_tick = AddAvgData(df_tick, 3, is_tick, avg_list)
                    arry_tick = np.array(df_tick)
                    if self.dict_set['백테일괄로딩']:
                        self.dict_arry[code] = arry_tick
                    else:
                        pickle_write(f'{BACK_TEMP}/{self.gubun}_{code}_tick', arry_tick)
                    self.code_list.append(code)
                    bk += 1

        con.close()
        if gubun == '데이터로딩':
            self.bq.put(bk)
            self.avg_list = avg_list
            self.startday_, self.endday_, self.starttime_, self.endtime_ = startday, endday, starttime, endtime

    def CheckAvglist(self, avg_list):
        not_in_list = [x for x in avg_list if x not in self.avg_list]
        if len(not_in_list) > 0 and self.gubun == 0:
            self.wq.put((ui_num['S백테스트'], '백테엔진 구동 시 포함되지 않은 평균값 틱수를 사용하여 중지되었습니다.'))
            self.wq.put((ui_num['S백테스트'], '누락된 평균값 틱수를 추가하여 백테엔진을 재시작하십시오.'))
            self.BackStop()

    def BackStop(self):
        self.back_type = None
        if self.gubun == 0:
            self.wq.put((ui_num['S백테스트'], '전략 코드 오류로 백테스트를 중지합니다.'))

    def SetArrayTick(self, code, same_days, same_time):
        if not self.dict_set['백테일괄로딩']:
            self.dict_arry = {code: pickle_read(f'{BACK_TEMP}/{self.gubun}_{code}_tick')}

        if same_days and same_time:
            self.arry_data = self.dict_arry[code]
        elif same_time:
            self.arry_data = self.dict_arry[code][(self.dict_arry[code][:, 0] >= self.startday * 1000000) &
                                                  (self.dict_arry[code][:, 0] <= self.endday * 1000000 + 240000)]
        elif same_days:
            self.arry_data = self.dict_arry[code][(self.dict_arry[code][:, 0] % 1000000 >= self.starttime) &
                                                  (self.dict_arry[code][:, 0] % 1000000 <= self.endtime)]
        else:
            self.arry_data = self.dict_arry[code][(self.dict_arry[code][:, 0] >= self.startday * 1000000) &
                                                  (self.dict_arry[code][:, 0] <= self.endday * 1000000 + 240000) &
                                                  (self.dict_arry[code][:, 0] % 1000000 >= self.starttime) &
                                                  (self.dict_arry[code][:, 0] % 1000000 <= self.endtime)]

    def BackTest(self):
        if self.profile:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        same_days = self.startday_ == self.startday and self.endday_ == self.endday
        same_time = self.starttime_ == self.starttime and self.endtime_ == self.endtime

        if not self.tick_calcul and self.opti_turn in (1, 3):
            total_ticks = 0
            for code in self.code_list:
                self.SetArrayTick(code, same_days, same_time)
                total_ticks += len(self.arry_data)
            self.tq.put(('전체틱수', int(total_ticks / 100)))
            self.tick_calcul = True

        j = 0
        len_codes = len(self.code_list)
        for k, code in enumerate(self.code_list):
            self.code = code
            self.name = self.dict_cn[self.code] if self.code in self.dict_cn.keys() else self.code
            self.SetArrayTick(code, same_days, same_time)
            last = len(self.arry_data) - 1
            if last > 0:
                for i, index in enumerate(self.arry_data[:, 0]):
                    self.index  = int(index)
                    self.indexn = i
                    self.tick_count += 1
                    next_day_change = i == last or str(index)[:8] != str(self.arry_data[i + 1, 0])[:8]
                    if not next_day_change:
                        try:
                            self.Strategy()
                        except:
                            print_exc()
                            self.BackStop()
                            return
                    else:
                        self.LastSell()
                        self.InitTradeInfo()

                    j += 1
                    if self.opti_turn in (1, 3) and j % 100 == 0: self.tq.put('탐색완료')

            self.tq.put(('백테완료', self.gubun, k+1, len_codes))

        if self.profile: self.pr.print_stats(sort='cumulative')

    def Strategy(self):
        def now():
            return strp_time('%Y%m%d%H%M%S', str(self.index))

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
            return Parameter_Dgree(59, 5, tick, pre, 5)

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(60, 6, tick, pre, 0.01)

        def 전일비각도(tick, pre=0):
            return Parameter_Dgree(61, 9, tick, pre, 1)

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn.keys() and \
                    조건명 in self.dict_cond_indexn[종목코드].keys() and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        종목명, 종목코드, 데이터길이, 시분초 = self.name, self.code, self.tick_count, int(str(self.index)[8:])
        현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, \
            초당매수수량, 초당매도수량, VI해제시간, VI가격, VI호가단위, 초당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도수5호가잔량합, 관심종목 = self.arry_data[self.indexn, 1:45]
        호가단위 = 매도호가2 - 매도호가1
        VI해제시간, VI아래5호가 = strp_time('%Y%m%d%H%M%S', str(int(VI해제시간))), GetUvilower5(VI가격, VI호가단위, self.index)
        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.dict_set['주식매수시장가잔량범위']]
        self.shogainfo = shogainfo[:self.dict_set['주식매도시장가잔량범위']]

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn.keys():
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                exec(v)

        if self.opti_turn == 1:
            for vturn in self.trade_info.keys():
                self.vars = [var[1] for var in self.vars_list]
                if vturn != 0 and self.tick_count < self.vars[0]:
                    break

                for vkey in self.trade_info[vturn].keys():
                    self.vars[vturn] = self.vars_list[vturn][0][vkey]
                    if self.tick_count < self.vars[0]:
                        continue

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                        exec(self.buystg)
                    else:
                        수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                        exec(self.sellstg)

        elif self.opti_turn == 3:
            for vturn in self.trade_info.keys():
                for vkey in self.trade_info[vturn].keys():
                    index_ = vturn * 20 + vkey
                    if self.back_type != '조건최적화':
                        self.vars = self.vars_lists[index_]
                        if self.tick_count < self.vars[0]:
                            break
                    elif self.tick_count < self.avgtime:
                        break

                    매수, 매도 = True, False
                    if not self.trade_info[vturn][vkey]['보유중']:
                        if not 관심종목: continue
                        self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                        if self.back_type != '조건최적화':
                            exec(self.buystg)
                        else:
                            exec(self.dict_buystg[index_])
                    else:
                        수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
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

            매수, 매도 = True, False
            if not self.trade_info[vturn][vkey]['보유중']:
                if not 관심종목: return
                self.SetBuyCount(vturn, vkey, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), 전일비, 회전율, 전일동시간비)
                exec(self.buystg)
            else:
                수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호 = self.SetSellCount(vturn, vkey, 현재가, now())
                exec(self.sellstg)

    def SetBuyCount(self, vturn, vkey, 현재가, 고가, 저가, 등락율각도, 당일거래대금각도, 전일비, 회전율, 전일동시간비):
        if self.dict_set['주식비중조절'][0] == 0:
            betting = self.betting
        else:
            if self.dict_set['주식비중조절'][0] == 1:
                비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
            elif self.dict_set['주식비중조절'][0] == 2:
                비중조절기준 = 등락율각도
            elif self.dict_set['주식비중조절'][0] == 3:
                비중조절기준 = 당일거래대금각도
            elif self.dict_set['주식비중조절'][0] == 4:
                비중조절기준 = 전일비
            elif self.dict_set['주식비중조절'][0] == 5:
                비중조절기준 = 회전율
            else:
                비중조절기준 = 전일동시간비

            if 비중조절기준 < self.dict_set['주식비중조절'][1]:
                betting = self.betting * self.dict_set['주식비중조절'][5]
            elif 비중조절기준 < self.dict_set['주식비중조절'][2]:
                betting = self.betting * self.dict_set['주식비중조절'][6]
            elif 비중조절기준 < self.dict_set['주식비중조절'][3]:
                betting = self.betting * self.dict_set['주식비중조절'][7]
            elif 비중조절기준 < self.dict_set['주식비중조절'][4]:
                betting = self.betting * self.dict_set['주식비중조절'][8]
            else:
                betting = self.betting * self.dict_set['주식비중조절'][9]

        self.trade_info[vturn][vkey]['주문수량'] = int(betting / 현재가)

    def Buy(self, vturn, vkey):
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
                    '매수시간': strp_time('%Y%m%d%H%M%S', str(self.index)) if len(str(self.index)) == 14 else strp_time('%Y%m%d%H%M', str(self.index))
                }

    def SetSellCount(self, vturn, vkey, 현재가, now_time):
        _, 매수가, _, _, 보유수량, 최고수익률, 최저수익률, 매수틱번호, 매수시간 = self.trade_info[vturn][vkey].values()
        _, _, 수익률 = GetKiwoomPgSgSp(보유수량 * 매수가, 보유수량 * 현재가)
        if 수익률 > 최고수익률:   self.trade_info[vturn][vkey]['최고수익률'] = 최고수익률 = 수익률
        elif 수익률 < 최저수익률: self.trade_info[vturn][vkey]['최저수익률'] = 최저수익률 = 수익률
        보유시간 = (now_time - 매수시간).total_seconds() if len(str(self.index)) == 14 else int((now_time - 매수시간).total_seconds() / 60)
        self.indexb = 매수틱번호
        self.trade_info[vturn][vkey]['주문수량'] = 보유수량
        return 수익률, 최고수익률, 최저수익률, 보유시간, 매수틱번호

    def Sell(self, vturn, vkey, sell_cond):
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
        if self.dict_set['주식타임프레임']:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 23:43]
        else:
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5 = \
                self.arry_data[self.indexn, 26:46]
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        shogainfo = shogainfo[:self.dict_set['주식매도시장가잔량범위']]

        for vturn in self.trade_info.keys():
            for vkey in self.trade_info[vturn].keys():
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
        _, bp, sp, oc, _, _, _, bi, bdt = self.trade_info[vturn][vkey].values()
        sgtg = int(self.arry_data[self.indexn, 12])
        if len(str(self.index)) == 14:
            ht = int((strp_time('%Y%m%d%H%M%S', str(self.index)) - bdt).total_seconds())
        else:
            ht = int((strp_time('%Y%m%d%H%M', str(self.index)) - bdt).total_seconds() / 60)
        bt, st, bg = int(self.arry_data[bi, 0]), self.index, oc * bp
        pg, sg, pp = GetKiwoomPgSgSp(bg, oc * sp)
        sc = self.dict_sconds[self.sell_cond] if self.back_type != '조건최적화' else self.dict_sconds[vkey][self.sell_cond]
        abt, bcx = '', True
        data = ('백테결과', self.name, sgtg, bt, st, ht, bp, sp, bg, pg, pp, sg, sc, abt, bcx, vturn, vkey)
        self.bstq_list[vkey if self.opti_turn in (1, 3) else (self.sell_count % 5)].put(data)
        self.sell_count += 1
        self.trade_info[vturn][vkey] = GetTradeInfo(1)
