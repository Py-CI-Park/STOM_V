import sys
import time
import random
import sqlite3
import operator
import numpy as np
import pandas as pd
from multiprocessing import Process, Queue
from backtester.back_static import SendTextAndStd, GetMoneytopQuery
from utility.static import strf_time, now, timedelta_day, timedelta_sec, strp_time, threading_timer
from utility.setting import DB_STOCK_BACK_TICK, ui_num, DB_STRATEGY, DB_BACKTEST, DICT_SET, DB_COIN_BACK_TICK, \
    DB_STOCK_BACK_MIN, DB_COIN_BACK_MIN


class Total:
    def __init__(self, wq, tq, mq, bstq_list, ui_gubun):
        self.wq           = wq
        self.tq           = tq
        self.mq           = mq
        self.bstq_list    = bstq_list
        self.ui_gubun     = ui_gubun
        self.dict_set     = DICT_SET

        self.back_count   = None
        self.dict_cn      = None
        self.buystg       = None
        self.sellstg      = None
        self.std_list     = None
        self.optistandard = None
        self.day_count    = None

        self.betting      = None
        self.startday     = None
        self.endday       = None
        self.valid_days   = None
        self.starttime    = None
        self.endtime      = None

        self.dict_t       = {}
        self.dict_v       = {}

        self.vars_lists   = None
        self.stdp         = -2_000_000_000
        self.sub_total    = 0
        self.total_count  = 0
        self.total_count2 = 0

        self.MainLoop()

    def MainLoop(self):
        tt = 0
        sc = 0
        bc = 0
        st = {}
        start = now()
        dict_dummy = {}
        while True:
            data = self.tq.get()
            if data[0] == '백테완료':
                bc  += 1
                if bc == self.back_count:
                    bc = 0
                    for q in self.bstq_list:
                        q.put(('백테완료', '미분리집계'))

            elif data[0] == '더미결과':
                sc += 1
                _, vkey, _dict_dummy = data
                if _dict_dummy:
                    for vturn in _dict_dummy.keys():
                        if vturn not in dict_dummy.keys():
                            dict_dummy[vturn] = {}
                        dict_dummy[vturn][vkey] = 0

                if sc == 20:
                    sc = 0
                    for vturn in range(50):
                        if vturn not in dict_dummy.keys():
                            for vkey in range(20):
                                self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), None)
                        else:
                            for vkey in range(20):
                                if vkey not in dict_dummy[vturn].keys():
                                    self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), None)
                    dict_dummy = {}

            elif data[0] in ('TRAIN', 'VALID'):
                gubun, num, data, vturn, vkey = data
                if vturn not in self.dict_t.keys():
                    self.dict_t[vturn] = {}
                if vkey not in self.dict_t[vturn].keys():
                    self.dict_t[vturn][vkey] = {}
                if vturn not in self.dict_v.keys():
                    self.dict_v[vturn] = {}
                if vkey not in self.dict_v[vturn].keys():
                    self.dict_v[vturn][vkey] = {}
                if vturn not in st.keys():
                    st[vturn] = {}
                if vkey not in st[vturn].keys():
                    st[vturn][vkey] = 0

                if gubun == 'TRAIN':
                    self.dict_t[vturn][vkey][num] = data
                else:
                    self.dict_v[vturn][vkey][num] = data

                st[vturn][vkey] += 1
                if st[vturn][vkey] == self.sub_total:
                    self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), self.dict_t[vturn][vkey], self.dict_v[vturn][vkey], self.dict_set['교차검증가중치'])
                    st[vturn][vkey] = 0

            elif data[0] == 'ALL':
                _, _, data, vturn, vkey = data
                self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), data)

            elif data[0] == '백테정보':
                self.BackInfo(data)
            elif data[0] == '변수정보':
                self.vars_lists = data[1]
                start = now()
                tt = 0
            elif data[0] == '경우의수':
                self.total_count = data[1]
                self.back_count  = data[2]
            elif data[0] == '전체틱수':
                self.total_count2 += data[1]
            elif data == '탐색완료':
                tt += 1
                self.wq.put((ui_num[f'{self.ui_gubun}백테바'], tt, self.total_count2, start))
            elif data == '백테중지':
                self.mq.put('백테중지')
                break

        time.sleep(1)
        sys.exit()

    def BackInfo(self, data):
        self.betting      = data[1]
        self.startday     = data[2]
        self.endday       = data[3]
        self.starttime    = data[4]
        self.endtime      = data[5]
        self.buystg       = data[6]
        self.sellstg      = data[7]
        self.dict_cn      = data[8]
        self.std_list     = data[9]
        self.optistandard = data[10]
        self.valid_days   = data[11]
        self.day_count    = data[12]
        if self.valid_days is not None:
            self.sub_total = len(self.valid_days) * 2
        else:
            self.sub_total = 2

    def GetSendData(self, vturn, vkey):
        index = vturn * 20 + vkey
        return ['GA최적화', self.ui_gubun, self.wq, self.mq, self.stdp, self.optistandard, 0, vturn, vkey, self.vars_lists[index], self.startday, self.endday, self.std_list, self.betting]


class OptimizeGeneticAlgorithm:
    def __init__(self, wq, bq, sq, tq, lq, beq_list, bstq_list, backname, ui_gubun):
        self.wq          = wq
        self.bq          = bq
        self.sq          = sq
        self.tq          = tq
        self.lq          = lq
        self.beq_list    = beq_list
        self.bstq_list   = bstq_list
        self.backname    = backname
        self.ui_gubun    = ui_gubun
        self.high_list   = []
        self.vars_list   = []
        self.opti_lists  = []
        self.high_vars   = []
        self.result      = {}
        self.vars        = {}
        self.total_count = 0
        self.dict_set    = DICT_SET
        self.gubun       = 'stock' if self.ui_gubun == 'S' else 'coin'
        self.savename    = f'{self.gubun}_{self.backname.replace("최적화", "").lower()}'
        self.Start()

    def Start(self):
        self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        start_time = now()
        data = self.bq.get()
        if self.ui_gubun != 'CF':
            betting = float(data[0]) * 1000000
        else:
            betting = float(data[0])
        starttime   = int(data[1])
        endtime     = int(data[2])
        buystg_name     = data[3]
        sellstg_name    = data[4]
        optivars_name   = data[5]
        dict_cn         = data[6]
        std_text        = data[7].split(';')
        std_text        = [float(x) for x in std_text]
        optistandard    = data[8]
        back_count      = data[9]
        weeks_train     = data[10]
        weeks_valid = int(data[11])
        _           = int(data[12])
        backengin_sday  = data[13]
        backengin_eday  = data[14]
        if weeks_train != 'ALL':
            weeks_train = int(weeks_train)
        else:
            allweeks = int(((strp_time('%Y%m%d', backengin_eday) - strp_time('%Y%m%d', backengin_sday)).days + 1) / 7)
            if 'V' in self.backname:
                weeks_train = allweeks - weeks_valid
            else:
                weeks_train = allweeks

        if 'V' not in self.backname: weeks_valid = 0
        dt_endday   = strp_time('%Y%m%d', backengin_eday)
        startday    = timedelta_day(-(weeks_train + weeks_valid) * 7 + 1, dt_endday)
        sweek       = startday.weekday()
        if sweek != 0: startday = timedelta_day(7 - sweek, startday)
        startday    = int(strf_time('%Y%m%d', startday))
        endday      = int(backengin_eday)
        valid_days_ = []
        if 'VC' in self.backname:
            for i in range(int(weeks_train / weeks_valid) + 1):
                valid_days_.append([
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * 7 * (i + 1)) + 1, dt_endday))),
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * 7 * i), dt_endday)))
                ])
        elif 'V' in self.backname:
            valid_days_.append([int(strf_time('%Y%m%d', timedelta_day(-weeks_valid * 7 + 1, dt_endday))), endday])
        else:
            valid_days_ = None

        if int(backengin_sday) > startday:
            if 'V' in self.backname:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 학습기간 + 검증기간 만큼의 데이터가 필요합니다'))
            else:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 학습기간 만큼의 데이터가 필요합니다'))
            self.SysExit(True)

        if self.ui_gubun == 'S':
            db = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
        else:
            db = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
        con   = sqlite3.connect(db)
        query = GetMoneytopQuery(self.ui_gubun, startday, endday, starttime, endtime)
        df_mt = pd.read_sql(query, con)
        con.close()

        if len(df_mt) == 0 or back_count == 0:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '날짜 지정이 잘못되었거나 데이터가 존재하지 않습니다.'))
            self.SysExit(True)

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '텍스트에디터 클리어'))

        df_mt['일자'] = df_mt['index'].apply(lambda x: int(str(x)[:8]))
        day_list  = list(set(df_mt['일자'].to_list()))
        day_list.sort()

        valid_days = None
        startday, endday = day_list[0], day_list[-1]
        train_count = len([x for x in day_list if startday <= x <= endday])
        if 'V' in self.backname:
            valid_days = []
            for vsday, veday in valid_days_:
                valid_days_list = [x for x in day_list if vsday <= x <= veday]
                vdaycnt = len(valid_days_list)
                tdaycnt = train_count - vdaycnt
                valid_days.append([valid_days_list[0], valid_days_list[-1], tdaycnt, vdaycnt])

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 학습 기간 {startday} ~ {endday}'))
        if 'V' in self.backname:
            for vsday, veday, _, _ in valid_days:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 검증 기간 {vsday} ~ {veday}'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 기간 추출 완료'))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.ui_gubun, None, valid_days, arry_bct, betting, len(day_list))
        for q in self.bstq_list:
            q.put(data)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 보유종목수 어레이 생성 완료'))

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}optibuy', con).set_index('index')
        dfs = pd.read_sql(f'SELECT * FROM {self.gubun}optisell', con).set_index('index')
        buystg  = dfb['전략코드'][buystg_name]
        sellstg = dfs['전략코드'][sellstg_name]
        df = pd.read_sql(f'SELECT * FROM {self.gubun}vars', con).set_index('index')
        optivars = df['전략코드'][optivars_name]
        con.close()

        optivars_ = compile(df['전략코드'][optivars_name], '<string>', 'exec')
        try:
            exec(optivars_)
        except Exception as e:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - {self.backname} 변수설정 {e}'))
            self.SysExit(True)

        self.total_count = 1
        for value in list(self.vars.values()):
            self.total_count *= len(value[0])
            self.vars_list.append(value[0])
            self.high_list.append(value[1])
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 매도수전략 설정 완료'))

        mq = Queue()
        Process(target=Total, args=(self.wq, self.tq, mq, self.bstq_list, self.ui_gubun)).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))
        self.tq.put(('백테정보', betting, startday, endday, starttime, endtime, buystg, sellstg, dict_cn, std_text,
                     optistandard, valid_days, len(day_list)))

        time.sleep(1)
        data = ('백테정보', betting, self.vars[0][0], startday, endday, starttime, endtime, buystg, sellstg)
        for q in self.beq_list:
            q.put(data)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 시작'))

        k    = 1
        vc   = len(self.vars_list)
        hstd = -2_000_000_000
        goal = 2 ** int(round(vc / 2))
        self.opti_lists = []
        while self.total_count > goal:
            if k > 1: self.SaveVarslist(100, optistandard, buystg, sellstg)
            self.tq.put(('경우의수', vc * back_count, back_count))

            for i in range(vc):
                vars_lists = self.GetVarslist()
                if len(vars_lists) == 1000:
                    data = (ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 [{k}][{i+1}/{vc}]단계 시작, 최고 기준값[{hstd:,.2f}]')
                    threading_timer(6, self.wq.put, data)

                    data = ('변수정보', vars_lists)
                    self.tq.put(data)
                    for q in self.bstq_list:
                        q.put(('백테시작', 3))
                    for q in self.beq_list:
                        q.put(data)

                    for _ in range(1000):
                        data = mq.get()
                        if type(data) == str:
                            if len(self.result) > 0:
                                self.SaveVarslist(100, optistandard, buystg, sellstg)
                            self.SysExit(True)
                        else:
                            vturn, vkey, std = data
                            index = vturn * 20 + vkey
                            self.result[std] = vars_lists[index]
                            if std > hstd: hstd = std
                else:
                    self.total_count = 0
                    break

            if self.total_count == 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 모든 경우의 수 탐색 완료'))
                break

            if len(self.result) > 0: self.SetOptilist(k, int(vc / 4) if vc / 4 > 5 else 5, goal)
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 현재 경우의수[{self.total_count:,.0f}] 목표 경우의수[{goal:,.0f}]'))
            k += 1

        time.sleep(6)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 최적화 완료'))
        time.sleep(1)

        self.SaveVarslist(100, optistandard, buystg, sellstg)

        exec(optivars_)
        optivars = optivars.split('self.vars[0]')[0]
        for i in range(len(self.vars)):
            if self.vars[i][1] != self.high_vars[i]:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 self.vars[{i}]의 최적값 변경 {self.vars[i][1]} -> {self.high_vars[i]}'))
                self.vars[i][1] = self.high_vars[i]
            optivars += f'self.vars[{i}] = {self.vars[i]}\n'

        con = sqlite3.connect(DB_STRATEGY)
        cur = con.cursor()
        cur.execute(f"UPDATE {self.gubun}vars SET 전략코드 = '{optivars}' WHERE `index` = '{optivars_name}'")
        con.commit()
        con.close()

        mq.close()
        if self.dict_set['스톰라이브']: self.lq.put(f'{self.backname}')
        self.sq.put('지에이 최적화가 완료되었습니다.')
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        self.SysExit(False)

    def GetVarslist(self):
        vars_lists = []
        limit_time = timedelta_sec(30)
        for _ in range(1000):
            while now() < limit_time:
                vars_list = []
                for vars_ in self.vars_list:
                    vars_list.append(random.choice(vars_))
                if vars_list not in self.opti_lists:
                    vars_lists.append(vars_list)
                    self.opti_lists.append(vars_list)
                    break
        return vars_lists

    def SetOptilist(self, count, rank, goal):
        self.vars_list = [[] for _ in self.vars_list]
        rs_list = sorted(self.result.items(), key=operator.itemgetter(0), reverse=True)

        text = f'{self.backname} 결과\n'
        for std, vars_list in rs_list[:rank]:
            text += f' 기준값 [{std:.2f}] 변수 {vars_list}\n'
            for i, vars_ in enumerate(vars_list):
                if vars_ not in self.vars_list[i]:
                    self.vars_list[i].append(vars_)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text[:-1]))

        self.total_count = 1
        for i, vars_ in enumerate(self.vars_list):
            if count < 4 and self.high_list[i] not in vars_:
                self.vars_list[i].append(self.high_list[i])
            self.vars_list[i].sort()
            self.total_count *= len(vars_)

        if self.total_count <= goal:
            text = ''
            for std, vars_list in rs_list[rank:100 - rank]:
                text += f' 기준값 [{std:.2f}] 변수 {vars_list}\n'
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text[:-1]))

    def SaveVarslist(self, rank, optistandard, buystg, sellstg):
        rs_list = sorted(self.result.items(), key=operator.itemgetter(0), reverse=True)
        con = sqlite3.connect(DB_BACKTEST)
        for std, vars_list in rs_list[:rank]:
            data = [[optistandard, std, f'{vars_list}', buystg, sellstg]]
            df = pd.DataFrame(data, columns=['기준', '기준값', '범위설정', '매수코드', '매도코드'], index=[strf_time('%Y%m%d%H%M%S')])
            df.to_sql(self.savename, con, if_exists='append', chunksize=1000)
        con.close()
        self.high_vars = rs_list[0][1]
        data = (ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 상위100위 결과 저장 완료')
        threading_timer(5, self.wq.put, data)

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 완료'))
        time.sleep(1)
        sys.exit()
