import sys
import time
import random
import sqlite3
import operator
import numpy as np
import pandas as pd
from multiprocessing import Process, Queue
from backtester.back_static import SendTextAndStd, GetMoneytopQuery
from utility.static import factorial, strf_time, now, timedelta_day, strp_time, timedelta_sec
from utility.setting import ui_num, DB_STRATEGY, DICT_SET, DB_BACKTEST, DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, \
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
        self.std_list     = None
        self.optistandard = None
        self.day_count    = None

        self.betting      = None
        self.startday     = None
        self.endday       = None
        self.valid_days   = None
        self.starttime    = None
        self.endtime      = None
        self.avgtime      = None

        self.dict_t       = {}
        self.dict_v       = {}

        self.stdp         = -2_000_000_000
        self.sub_total    = 0
        self.total_count  = 0
        self.total_count2 = 0

        self.MainLoop()

    def MainLoop(self):
        tt = 0
        sc = 0
        bc = 0
        vc = 0
        st = {}
        start = now()
        dict_dummy = {}
        while True:
            data = self.tq.get()
            if data[0] == '백테완료':
                bc  += 1
                if bc == self.back_count:
                    bc = 0
                    for stq in self.bstq_list:
                        stq.put(('백테완료', '미분리집계'))

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
                    for vkey in range(20):
                        if vkey not in dict_dummy[0].keys():
                            self.stdp = SendTextAndStd(self.GetSendData(), None)
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
            elif data[0] == '경우의수':
                self.total_count = data[1]
                self.back_count  = data[2]
                vc = int(self.total_count / self.back_count)
            elif data[0] == '전체틱수':
                self.total_count2 += data[1]
            elif data == '탐색완료':
                tt += 1
                self.wq.put((ui_num[f'{self.ui_gubun}백테바'], tt, self.total_count2 * vc, start))
            elif data == '백테중지':
                self.mq.put('백테중지')
                break

        time.sleep(1)
        sys.exit()

    def BackInfo(self, data):
        self.betting      = data[1]
        self.avgtime      = data[2]
        self.startday     = data[3]
        self.endday       = data[4]
        self.starttime    = data[5]
        self.endtime      = data[6]
        self.std_list     = data[7]
        self.optistandard = data[8]
        self.valid_days   = data[9]
        self.day_count    = data[10]
        if self.valid_days is not None:
            self.sub_total = len(self.valid_days) * 2
        else:
            self.sub_total = 2

    def GetSendData(self, vturn=0, vkey=0):
        return ['조건최적화', self.ui_gubun, self.wq, self.mq, self.stdp, self.optistandard, 0, vturn, vkey, None, self.startday, self.endday, self.std_list, self.betting]


class OptimizeConditions:
    def __init__(self, wq, bq, sq, tq, lq, beq_list, bstq_list, backname, ui_gubun):
        self.wq           = wq
        self.bq           = bq
        self.sq           = sq
        self.tq           = tq
        self.lq           = lq
        self.beq_list     = beq_list
        self.bstq_list    = bstq_list
        self.backname     = backname
        self.ui_gubun     = ui_gubun
        self.result       = {}
        self.opti_list    = []
        self.bst_procs    = []
        self.bcount       = None
        self.scount       = None
        self.buyconds     = None
        self.sellconds    = None
        self.optistandard = None
        self.dict_set     = DICT_SET
        self.gubun        = 'stock' if self.ui_gubun == 'S' else 'coin'
        self.savename     = f'{self.gubun}_{self.backname.replace("최적화", "").lower()}'
        self.Start()

    def Start(self):
        self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        start_time = now()
        data = self.bq.get()
        if self.ui_gubun != 'CF':
            betting = float(data[0]) * 1000000
        else:
            betting = float(data[0])
        avgtime       = int(data[1])
        starttime     = int(data[2])
        endtime       = int(data[3])
        buystg_name       = data[4]
        sellstg_name      = data[5]
        std_text          = data[6].split(';')
        std_text          = [float(x) for x in std_text]
        self.optistandard = data[7]
        self.bcount   = int(data[8])
        self.scount   = int(data[9])
        rcount        = int(data[10])
        back_count        = data[11]
        weeks_train       = data[12]
        weeks_valid   = int(data[13])
        _             = int(data[14])
        backengin_sday    = data[15]
        backengin_eday    = data[16]
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
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}buyconds', con).set_index('index')
        dfs = pd.read_sql(f'SELECT * FROM {self.gubun}sellconds', con).set_index('index')
        con.close()

        self.buyconds  = dfb['전략코드'][buystg_name].split('\n')
        self.sellconds = dfs['전략코드'][sellstg_name].split('\n')

        is_long = None
        if self.ui_gubun == 'CF':
            if '#' in self.buyconds[0] and 'LONG' in self.buyconds[0] and '#' in self.sellconds[0] and 'LONG' in self.sellconds[0]:
                is_long = True
            elif '#' in self.buyconds[0] and 'SHORT' in self.buyconds[0] and '#' in self.sellconds[0] and 'SHORT' in self.sellconds[0]:
                is_long = False
            if is_long is None:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '롱숏구분(#LONG 또는 #SHORT)이 없거나 매도수 구분이 다릅니다.\n'))
                self.SysExit(True)

        self.buyconds  = [x for x in self.buyconds if x != '' and '#' not in x]
        self.sellconds = [x for x in self.sellconds if x != '' and '#' not in x]
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 매도수조건 설정 완료'))

        bc = factorial(len(self.buyconds)) / (factorial(self.bcount) * factorial(len(self.buyconds) - self.bcount))
        sc = factorial(len(self.sellconds)) / (factorial(self.scount) * factorial(len(self.sellconds) - self.scount))
        total_count = int(bc * sc)
        if total_count < rcount:
            rcount = total_count
        rcount = int(rcount / 20)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 전체 경우의 수 계산 완료 [{total_count:,.0f}]'))

        mq = Queue()
        Process(target=Total, args=(self.wq, self.tq, mq, self.bstq_list, self.ui_gubun)).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))
        self.tq.put(('백테정보', betting, avgtime, startday, endday, starttime, endtime, std_text, self.optistandard, valid_days, len(day_list)))

        time.sleep(1)
        data = ('백테정보', betting, avgtime, startday, endday, starttime, endtime)
        for q in self.beq_list:
            q.put(data)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 시작'))

        self.tq.put(('경우의수', rcount * back_count, back_count))
        hstd = -2_000_000_000
        for i in range(rcount):
            buy_conds, sell_conds = self.GetCondlist()
            if len(buy_conds) == 20:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 [{i+1}/{rcount}]단계 시작, 최고 기준값[{hstd:,.2f}]'))
                for q in self.bstq_list:
                    q.put(('백테시작', 3))
                if is_long is None:
                    data = ('조건정보', buy_conds, sell_conds)
                else:
                    data = ('조건정보', is_long, buy_conds, sell_conds)
                for q in self.beq_list:
                    q.put(data)

                for _ in range(20):
                    data = mq.get()
                    if type(data) == str:
                        if len(self.result) > 0:
                            self.ShowTopCondlist(5)
                            self.ShowTopConds()
                        self.SysExit(True)
                    else:
                        _, vkey, std = data
                        if std > hstd: hstd = std
                        if std > 0: self.result[std] = [buy_conds[vkey], sell_conds[vkey]]
            else:
                break

        time.sleep(2)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 최적화 완료'))
        time.sleep(1)

        if len(self.result) > 0:
            self.ShowTopCondlist(5)
            self.ShowTopConds()
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 기준값 0을 초과하는 조합이 없습니다.'))

        mq.close()
        if self.dict_set['스톰라이브']: self.lq.put(self.backname)
        self.sq.put('조건 최적화가 완료되었습니다.')
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        self.SysExit(False)

    def GetCondlist(self):
        buyconds  = []
        sellconds = []
        limit_time = timedelta_sec(30)
        for _ in range(20):
            while now() < limit_time:
                random.shuffle(self.buyconds)
                random.shuffle(self.sellconds)
                buycond  = self.buyconds[:self.bcount]
                sellcond = self.sellconds[:self.scount]
                buycond.sort()
                sellcond.sort()
                opti_list = buycond + sellcond
                if opti_list not in self.opti_list:
                    buyconds.append(buycond)
                    sellconds.append(sellcond)
                    self.opti_list.append(opti_list)
                    break
        return buyconds, sellconds

    def ShowTopCondlist(self, rank):
        rs_list = sorted(self.result.items(), key=operator.itemgetter(0), reverse=True)
        for key, value in rs_list[:rank]:
            buyconds  = 'if ' + ':\n    매수 = False\nelif '.join(value[0]) + ':\n    매수 = False'
            sellconds = 'if ' + ':\n    매도 = True\nelif '.join(value[1]) + ':\n    매도 = True'
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 - {self.optistandard}[{key:,.2f}]\n'))
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 - 매수조건\n{buyconds}\n'))
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 - 매도조건\n{sellconds}\n'))
            data = [[self.optistandard, key, buyconds, sellconds]]
            df = pd.DataFrame(data, columns=['기준', '기준값', '매수코드', '매도코드'], index=[strf_time('%Y%m%d%H%M%S')])
            con = sqlite3.connect(DB_BACKTEST)
            df.to_sql(self.savename, con, if_exists='append', chunksize=1000)
            con.close()

    def ShowTopConds(self):
        buy_conds_freq  = {}
        sell_conds_freq = {}

        rs_list    = sorted(self.result.items(), key=operator.itemgetter(0), reverse=True)
        opti_dict  = {x: y for x, y in rs_list}
        for key, value in opti_dict.items():
            for cond in value[0]:
                if cond in buy_conds_freq.keys():
                    buy_conds_freq[cond] += 1
                else:
                    buy_conds_freq[cond] = 1
            for cond in value[1]:
                if cond in sell_conds_freq.keys():
                    sell_conds_freq[cond] += 1
                else:
                    sell_conds_freq[cond] = 1

        buy_conds_freq  = sorted(buy_conds_freq.items(), key=operator.itemgetter(1), reverse=True)
        sell_conds_freq = sorted(sell_conds_freq.items(), key=operator.itemgetter(1), reverse=True)

        text = '조건회적화 결과 - 매수조건 출현빈도\n'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 - 매수조건 출현빈도'))
        for key, value in buy_conds_freq:
            text += f'[{value}] {key}\n'
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'[{value}] {key}'))

        text += '\n조건회적화 결과 - 매도조건 출현빈도\n'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 - 매도조건 출현빈도'))
        for key, value in sell_conds_freq:
            text += f'[{value}] {key}\n'
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'[{value}] {key}'))

        df = pd.DataFrame({'조건별출현빈도': [text]}, index=[strf_time('%Y%m%d%H%M%S')])
        con = sqlite3.connect(DB_BACKTEST)
        df.to_sql(f'{self.savename}_conds', con, if_exists='append', chunksize=1000)
        con.close()

    def SysExit(self, cancel):
        for proc in self.bst_procs:
            proc.kill()
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 완료'))
        time.sleep(1)
        sys.exit()
