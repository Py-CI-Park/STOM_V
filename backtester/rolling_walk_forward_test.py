import sys
import time
import optuna
import random
import sqlite3
import operator
import numpy as np
import pandas as pd
from multiprocessing import Process, Queue
from backtester.back_static import SendTextAndStd, GetMoneytopQuery, PltShow, GetResultDataframe, GetBackResult, AddMdd
from utility.static import strf_time, now, timedelta_day, strp_time, threading_timer
from utility.setting import ui_num, DB_STRATEGY, DB_BACKTEST, DICT_SET, DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, \
    DB_OPTUNA, DB_STOCK_BACK_MIN, DB_COIN_BACK_MIN


class Total:
    def __init__(self, wq, sq, tq, teleQ, mq, beq_list, bstq_list, backname, ui_gubun, gubun, multi, divid_mode):
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.mq           = mq
        self.teleQ        = teleQ
        self.beq_list     = beq_list
        self.bstq_list    = bstq_list
        self.backname     = backname
        self.ui_gubun     = ui_gubun
        self.gubun        = gubun
        self.multi        = multi
        self.divid_mode   = divid_mode
        self.dict_set     = DICT_SET
        gubun_text        = f'{self.gubun}_future' if self.ui_gubun == 'CF' else self.gubun
        self.savename     = f'{gubun_text}_{self.backname.replace("전진분석", "").lower()}'

        self.back_count   = None
        self.in_out_count = None
        self.file_name    = strf_time('%Y%m%d%H%M%S')

        self.dict_cn      = None
        self.buystg_name  = None
        self.buystg       = None
        self.sellstg      = None
        self.optivars     = None
        self.list_days    = None
        self.std_list     = None
        self.optistandard = None
        self.weeks_train  = None
        self.weeks_valid  = None
        self.weeks_test   = None

        self.betting      = None
        self.startday_    = None
        self.endday_      = None
        self.startday     = None
        self.endday       = None
        self.starttime    = None
        self.endtime      = None
        self.schedul      = None

        self.df_kp        = None
        self.df_kd        = None
        self.df_tsg       = None
        self.df_bct       = None

        self.df_ttsg      = []
        self.df_tbct      = []

        self.dict_t       = {}
        self.dict_v       = {}

        self.vars         = None
        self.vars_list    = None
        self.opti_turn    = None
        self.hstd_list    = None
        self.stdp         = -2_000_000_000
        self.sub_total    = 0
        self.total_count  = 0
        self.total_count2 = 0

        self.MainLoop()

    def MainLoop(self):
        tt  = 0
        oc  = 0
        sc  = 0
        bc  = 0
        tbc = 0
        st  = {}
        start = now()
        dict_dummy = {}
        first_time = None
        divid_time = now()
        divid_multi = int(self.multi * 90 / 100)
        fast_proc_list = []
        slow_proc_dict = {}
        while True:
            data = self.tq.get()
            if data[0] == '백테완료':
                bc  += 1
                tbc += 1
                if self.opti_turn == 1:
                    if self.dict_set['백테일괄로딩'] and self.divid_mode != '한종목 로딩':
                        if first_time is None: first_time = now()
                        procn, cnt, total = data[1:]
                        if cnt == total:
                            fast_proc_list.append(procn)
                            if len(fast_proc_list) == divid_multi:
                                divid_time = now()
                        if len(fast_proc_list) > divid_multi and procn not in slow_proc_dict.keys():
                            slow_proc_dict[procn] = cnt
                elif self.opti_turn in (0, 2):
                    self.wq.put((ui_num[f'{self.ui_gubun}백테바'], bc, self.total_count, start))
                elif self.opti_turn == 4:
                    self.wq.put((ui_num[f'{self.ui_gubun}백테바'], tbc, self.total_count, start))

                if bc == self.back_count:
                    bc = 0
                    if self.opti_turn == 1:
                        if self.dict_set['백테일괄로딩'] and self.divid_mode != '한종목 로딩':
                            time_90 = (divid_time - first_time).total_seconds()
                            time_10 = (now() - divid_time).total_seconds()
                            if time_90 * 5 / 90 < time_10:
                                k = 0
                                for procn, cnt in slow_proc_dict.items():
                                    self.beq_list[procn].put(('데이터이동', cnt, fast_proc_list[k]))
                                    k += 1
                            first_time = None
                            fast_proc_list = []
                            slow_proc_dict = {}
                        for q in self.bstq_list:
                            q.put(('백테완료', '미분리집계'))
                    else:
                        for q in self.bstq_list[:5]:
                            q.put(('백테완료', '분리집계'))

            elif data == '집계완료':
                sc += 1
                if sc == 5:
                    sc = 0
                    for q in self.bstq_list[:5]:
                        q.put('결과분리')

            elif data == '분리완료':
                sc += 1
                if sc == 5:
                    sc = 0
                    self.bstq_list[0].put('결과전송')

            elif data[0] == '결과없음':
                self.stdp = SendTextAndStd(self.GetSendData(), None)

            elif data[0] == '더미결과':
                sc += 1
                _, vkey, _dict_dummy = data
                if _dict_dummy:
                    for vturn in _dict_dummy.keys():
                        dict_dummy[vturn][vkey] = 0

                if sc == 20:
                    sc = 0
                    for vturn in list(dict_dummy.keys()):
                        curr_vars_count = len(self.vars_list[vturn][0])
                        key_list = list(dict_dummy[vturn].keys())
                        zero_key_list = [x for x in range(curr_vars_count) if x not in key_list]
                        if zero_key_list:
                            for vkey in zero_key_list:
                                self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), None)
                    dict_dummy = {}

            elif data[0] == '백테결과':
                oc += 1
                _, list_tsg, arry_bct = data
                self.Report(list_tsg, arry_bct, oc)

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
                    self.stdp = SendTextAndStd(
                        self.GetSendData(vturn, vkey),
                        self.dict_t[vturn][vkey],
                        self.dict_v[vturn][vkey],
                        self.dict_set['교차검증가중치']
                    )
                    st[vturn][vkey] = 0

            elif data[0] == 'ALL':
                _, _, data, vturn, vkey = data
                self.stdp = SendTextAndStd(self.GetSendData(vturn, vkey), data)

            elif data[0] == '백테정보':
                self.BackInfo(data)
            elif data[0] == '변수정보':
                self.vars_list = data[1]
                self.opti_turn = data[2]
                self.vars      = [var[1] for var in self.vars_list]
                dict_dummy     = {i: {} for i, x in enumerate(self.vars_list) if len(x[0]) > 1}
                if self.opti_turn != 4:
                    tt = 0
                    start = now()
            elif data[0] == '경우의수':
                self.total_count  = data[1]
                self.back_count   = data[2]
                self.startday     = data[3]
                self.endday       = data[4]
                self.in_out_count = data[5]
                self.stdp         = -2_000_000_000
                self.total_count2 = 0
            elif data[0] == '횟수변경':
                self.total_count = data[1]
            elif data[0] == '전체틱수':
                self.total_count2 += data[1]
            elif data == '탐색완료':
                tt += 1
                self.wq.put((ui_num[f'{self.ui_gubun}백테바'], tt, self.total_count2, start))
            elif data[0] == '최적화정보':
                self.hstd_list = data[1]
            elif data == '백테중지':
                self.mq.put('백테중지')
                break

        time.sleep(1)
        sys.exit()

    def BackInfo(self, data):
        self.betting      = data[1]
        self.startday_    = data[2]
        self.endday_      = data[3]
        self.starttime    = data[4]
        self.endtime      = data[5]
        self.buystg_name  = data[6]
        self.buystg       = data[7]
        self.sellstg      = data[8]
        self.optivars     = data[9]
        self.dict_cn      = data[10]
        self.list_days    = data[11]
        self.std_list     = data[12]
        self.optistandard = data[13]
        self.schedul      = data[14]
        self.df_kp        = data[15]
        self.df_kd        = data[16]
        self.weeks_train  = data[17]
        self.weeks_valid  = data[18]
        self.weeks_test   = data[19]
        if self.list_days[0][1] is not None:
            self.sub_total = len(self.list_days[0][1]) * 2
        else:
            self.sub_total = 2

    def GetSendData(self, vturn=0, vkey=0):
        if self.opti_turn == 1:
            self.vars[vturn] = self.vars_list[vturn][0][vkey]
        return ['최적화', self.ui_gubun, self.wq, self.mq, self.stdp, self.optistandard, self.opti_turn, vturn, vkey, self.vars, self.startday, self.endday, self.std_list, self.betting]

    def Report(self, list_tsg, arry_bct, oc):
        tc = len(list_tsg)
        if tc > 0:
            self.df_tsg, self.df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)
            self.df_ttsg.append(self.df_tsg)
            self.df_tbct.append(self.df_bct)
            pc     = len(self.df_tsg[self.df_tsg['수익률'] >= 0])
            wr     = round(pc / tc * 100, 2)
            tsg    = int(self.df_tsg['수익금'].sum())
            df_bct = self.df_bct.sort_values(by=['보유종목수'], ascending=False)
            mhct   = df_bct['보유종목수'].iloc[int(len(self.df_bct) * 0.01):].max()
            seed  = df_bct['보유금액'].iloc[int(len(self.df_bct) * 0.01):].max()
            tpp    = round(tsg / seed * 100, 2)
        else:
            wr     = 0
            tsg    = 0
            mhct   = 0
            tpp    = 0.

        startday = self.hstd_list[oc - 1][0]
        endday   = self.hstd_list[oc - 1][1]
        merge    = self.hstd_list[oc - 1][2]
        text1    = f'[IN] P[{startday}~{endday}] {self.vars} MERGE[{merge:,.2f}]'
        text2    = f'[OUT] P[{self.startday}~{self.endday}] TC[{tc}] MH[{mhct}] WR[{wr:.2f}%] TP[{tpp:.2f}%] TG[{tsg:,.0f}]'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text1))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text2))
        self.mq.put('아웃샘플 백테스트')

        if oc == self.in_out_count:
            self.df_ttsg = pd.concat(self.df_ttsg)
            self.df_ttsg['수익금합계'] = self.df_ttsg['수익금'].cumsum()
            self.df_tbct = pd.concat(self.df_tbct)

            df_ttsg = self.df_ttsg[['수익금']].copy()
            df_ttsg['index'] = df_ttsg.index
            df_ttsg['index'] = df_ttsg['index'].apply(lambda x: x[:8])
            out_day_count = len(list(set(df_ttsg['index'].to_list())))

            df_tsg   = self.df_ttsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy()
            df_tbc   = self.df_tbct.copy()
            df_tbc['체결시간'] = df_tbc.index
            df_tbc['체결시간'] = df_tbc['체결시간'].apply(lambda x: float(x))
            df_tbc = df_tbc[['체결시간', '보유종목수', '보유금액']]
            arry_tsg = np.array(df_tsg, dtype='float64')
            arry_bct = np.array(df_tbc, dtype='float64')
            arry_bct = np.sort(arry_bct, axis=0)[::-1]
            result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, out_day_count)
            result   = AddMdd(arry_tsg, result)
            tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result

            startday, endday, starttime, endtime = str(self.startday_), str(self.endday_), str(self.starttime).zfill(6), str(self.endtime).zfill(6)
            startday  = startday[:4] + '-' + startday[4:6] + '-' + startday[6:]
            endday    = endday[:4] + '-' + endday[4:6] + '-' + endday[6:]
            starttime = starttime[:2] + ':' + starttime[2:4] + ':' + starttime[4:]
            endtime   = endtime[:2] + ':' + endtime[2:4] + ':' + endtime[4:]
            bet_unit  = '원' if self.ui_gubun != 'CF' else 'USDT'

            if self.weeks_valid == 0:
                back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습+검증/확인기간 : {self.weeks_train}/{self.weeks_test}, 거래일수 : {out_day_count}'
            else:
                back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습/검증/확인기간 : {self.weeks_train}/{self.weeks_valid}/{self.weeks_test}, 거래일수 : {out_day_count}'

            mdd_test   = f'최대낙폭금액 {mdd_:,.0f}{bet_unit}' if 'G' in self.optistandard else f'최대낙폭률 {mdd:,.2f}%'
            label_text = f'종목당 배팅금액 {int(self.betting):,}{bet_unit}, 필요자금 {seed:,.0f}{bet_unit}, ' \
                         f'거래횟수 {tc}회, 일평균거래횟수 {atc}회, 적정최대보유종목수 {mhct}개, 평균보유기간 {ah:.2f}초\n' \
                         f'익절 {pc}회, 손절 {mc}회, 승률 {wr:.2f}%, 평균수익률 {app:.2f}%, 수익률합계 {tpp:.2f}%, ' \
                         f'{mdd_test}, 수익금합계 {tsg:,}{bet_unit}, 매매성능지수 {tpi:.2f}, 연간예상수익률 {cagr:.2f}%'

            save_file_name = f"{self.savename}_{self.buystg_name}_{self.optistandard}_{self.file_name}"
            con = sqlite3.connect(DB_BACKTEST)
            self.df_ttsg.to_sql(save_file_name, con, if_exists='append', chunksize=1000)
            con.close()
            self.wq.put((ui_num[f'{self.ui_gubun.replace("F", "")}상세기록'], self.df_tsg))

            self.sq.put(f'{self.backname} 백테스트를 완료하였습니다.')
            self.mq.put('백테스트 완료')
            PltShow('전진분석', self.teleQ, self.df_ttsg, self.df_tbct, self.dict_cn, seed, mdd, self.startday, self.endday, self.starttime, self.endtime,
                    self.df_kp, self.df_kd, self.list_days, self.backname, back_text, label_text, save_file_name, self.schedul, False)
            self.mq.put('백테스트 완료')


class StopWhenNotUpdateBestCallBack:
    def __init__(self, wq, tq, back_count, optuna_count, ui_gubun, len_vars):
        self.wq           = wq
        self.tq           = tq
        self.back_count   = back_count
        self.optuna_count = optuna_count
        self.ui_gubun     = ui_gubun
        self.len_vars     = len_vars

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        best_opt    = study.best_value
        best_num    = study.best_trial.number
        curr_num    = trial.number
        last_num    = (best_num + self.len_vars) if self.optuna_count == 0 else (best_num + self.optuna_count)
        rema_num    = last_num - curr_num
        total_count = self.back_count * (last_num + 1)
        self.tq.put(('횟수변경', total_count))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'<font color=#45cdf7>OPTUNA INFO 최고기준값[{best_opt:,}] 기준값갱신[{best_num}] 현재횟수[{curr_num}] 남은횟수[{rema_num}]</font>'))
        if curr_num == last_num:
            study.stop()


class RollingWalkForwardTest:
    def __init__(self, wq, bq, sq, tq, lq, teleQ, beq_list, bstq_list, multi, divid_mode, backname, ui_gubun):
        self.wq         = wq
        self.bq         = bq
        self.sq         = sq
        self.tq         = tq
        self.lq         = lq
        self.teleQ      = teleQ
        self.beq_list   = beq_list
        self.bstq_list  = bstq_list
        self.multi      = multi
        self.divid_mode = divid_mode
        self.backname   = backname
        self.ui_gubun   = ui_gubun
        self.dict_set   = DICT_SET
        self.gubun      = 'stock' if self.ui_gubun == 'S' else 'coin'
        self.vars       = {}
        self.study      = None
        self.dict_simple_vars = {}
        self.Start()

    def Start(self):
        self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        start_time = now()
        data = self.bq.get()
        if self.ui_gubun != 'CF':
            betting = float(data[0]) * 1000000
        else:
            betting = float(data[0])
        startday    = int(data[1])
        endday      = int(data[2])
        starttime   = int(data[3])
        endtime     = int(data[4])
        buystg_name     = data[5]
        sellstg_name    = data[6]
        optivars_name   = data[7]
        dict_cn         = data[8]
        ccount      = int(data[9])
        std_text        = data[10].split(';')
        std_text        = [float(x) for x in std_text]
        optistandard    = data[11]
        back_count      = data[12]
        schedul         = data[13]
        df_kp           = data[14]
        df_kd           = data[15]
        weeks_train = int(data[16])
        weeks_valid = int(data[17])
        weeks_test  = int(data[18])
        backengin_sday  = data[19]
        backengin_eday  = data[20]
        optuna_sampler  = data[21]
        if optuna_sampler == 'BruteForceSampler':
            sampler = optuna.samplers.BruteForceSampler()
        elif optuna_sampler == 'CmaEsSampler':
            sampler = optuna.samplers.CmaEsSampler()
        elif optuna_sampler == 'QMCSampler':
            sampler = optuna.samplers.QMCSampler()
        elif optuna_sampler == 'RandomSampler':
            sampler = optuna.samplers.RandomSampler()
        elif optuna_sampler == 'TPESampler':
            sampler = optuna.samplers.TPESampler()
        else:
            sampler = None
        optuna_fixvars = []
        if data[22] != '':
            try:
                optuna_fixvars  = [int(x.strip()) for x in data[22].split(',')]
            except:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '고정할 범위의 번호를 잘못입력하였습니다.'))
                self.SysExit(True)
        optuna_count = int(data[23])
        optuna_autostep  = data[24]
        random_optivars  = data[25]

        if 'V' in self.backname:
            int_day = int(strf_time('%Y%m%d', timedelta_day(-(weeks_train + weeks_valid + weeks_test + 1) * 7 + 3, strp_time('%Y%m%d', str(endday)))))
            if int(backengin_sday) > int_day or startday > int_day or endday > int(backengin_eday):
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 (학습기간 + 검증기간 + 확인기간 + 1)주 만큼의 데이터가 필요합니다'))
                self.SysExit(True)
        else:
            int_day = int(strf_time('%Y%m%d', timedelta_day(-(weeks_train + weeks_test + 1) * 7 + 3, strp_time('%Y%m%d', str(endday)))))
            if int(backengin_sday) > int_day or startday > int_day or endday > int(backengin_eday):
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 (학습기간 + 확인기간 + 1)주 만큼의 데이터가 필요합니다'))
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
        day_list = list(set(df_mt['일자'].to_list()))
        day_list.sort()

        if 'V' not in self.backname: weeks_valid = 0
        list_days = self.GetListDays(startday, endday, weeks_train, weeks_valid, weeks_test, day_list)
        for i, days in enumerate(list_days):
            train_days, valid_days, test_days = days
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 학습기간 {i + 1} : {train_days[0]} ~ {train_days[1]}'))
            if 'V' in self.backname:
                for vsday, veday, _ in valid_days:
                    self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 검증기간 {i + 1} : {vsday} ~ {veday}'))
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 확인기간 {i + 1} : {test_days[0]} ~ {test_days[1]}'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 일자 추출 완료'))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.ui_gubun, list_days, None, arry_bct, betting, len(day_list))
        for q in self.bstq_list:
            q.put(data)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 보유종목수 어레이 생성 완료'))

        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql(f'SELECT * FROM {self.gubun}optibuy', con).set_index('index')
        buystg = df['전략코드'][buystg_name]
        df = pd.read_sql(f'SELECT * FROM {self.gubun}optisell', con).set_index('index')
        sellstg = df['전략코드'][sellstg_name]
        df = pd.read_sql(f'SELECT * FROM {self.gubun}optivars', con).set_index('index')
        optivars = df['전략코드'][optivars_name]
        con.close()

        optivars_ = compile(optivars, '<string>', 'exec')
        try:
            exec(optivars_)
        except Exception as e:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - 최적화 변수설정 1단계 {e}'))
            self.SysExit(True)

        total_count, vars_type, vars_ = self.GetOptomizeVarsList(random_optivars)

        out_count   = len(list_days)
        len_vars    = len(vars_)
        avg_list    = vars_[0][0]
        total_count *= ccount if ccount != 0 else 1
        total_count += 1
        total_count *= out_count
        total_count += out_count
        total_count *= back_count
        text = f'{self.backname} 매도수전략 및 변수 설정 완료' if not random_optivars else f'{self.backname} 매도수전략 및 변수 최적값 랜덤 설정 완료'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text))

        mq = Queue()
        Process(
            target=Total,
            args=(self.wq, self.sq, self.tq, self.teleQ, mq, self.beq_list, self.bstq_list, self.backname, self.ui_gubun,
                  self.gubun, self.multi, self.divid_mode)
        ).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))
        self.tq.put(('백테정보', betting, startday, endday, starttime, endtime, buystg_name, buystg, sellstg, optivars,
                     dict_cn, list_days, std_text, optistandard, schedul, df_kp, df_kd, weeks_train, weeks_valid, weeks_test))

        time.sleep(1)
        data = ('백테정보', betting, avg_list, starttime, endtime, buystg, sellstg)
        for q in self.beq_list:
            q.put(data)
        if 'B' in self.backname:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'<font color=#45cdf7>OPTUNA Sampler : {optuna_sampler}</font>'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 최적화 시작'))

        hstd_list = []
        hvar_list = []
        for i, days in enumerate(list_days):
            train_days, _, _ = days
            startday, endday = train_days[0], train_days[1]

            if 'B' not in self.backname:
                vars_, hstd = self.OptimizeGrid(mq, total_count, back_count, ccount, vars_type, vars_, startday, endday, i)
            else:
                vars_, hstd = self.OptimizeOptuna(mq, optuna_count, back_count, len_vars, optuna_fixvars, optuna_autostep, buystg_name, sampler, vars_, startday, endday, i)

            hvar_list.append(vars_)
            hstd_list.append([startday, endday, hstd])

        time.sleep(6)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 최적화 완료'))
        time.sleep(1)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 아웃샘플 백테스트 시작'))

        self.tq.put(('최적화정보', hstd_list))
        for i, days in enumerate(list_days):
            startday, endday = days[2]
            self.tq.put(('경우의수', total_count, back_count, startday, endday, out_count))
            self.PutData(('변수정보', hvar_list[i], 2, startday, endday, i))
            _ = mq.get()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 아웃샘플 백테스트 완료'))

        _ = mq.get()
        if self.dict_set['스톰라이브']: self.lq.put(self.backname.replace('O', '').replace('B', ''))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        _ = mq.get()
        mq.close()
        self.SysExit(False)

    def GetListDays(self, startday, endday, weeks_train, weeks_valid, weeks_test, day_list):
        k = 0
        list_days_ = []
        dt_endday  = strp_time('%Y%m%d', str(endday))
        startday_  = int(strf_time('%Y%m%d', timedelta_day(-(weeks_train + weeks_valid + weeks_test * (k + 1)) * 7 + 3, dt_endday)))
        while startday_ >= startday:
            train_days = [
                startday_, int(strf_time('%Y%m%d', timedelta_day(-weeks_test * (k + 1) * 7, dt_endday)))
            ]
            valid_days_ = []
            if 'VC' in self.backname:
                for i in range(int(weeks_train / weeks_valid) + 1):
                    valid_days_.append([
                        int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * (i + 1) + weeks_test * (k + 1)) * 7 + 3, dt_endday))),
                        int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * i + weeks_test * (k + 1)) * 7, dt_endday)))
                    ])
            elif 'V' in self.backname:
                valid_days_.append([
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid + weeks_test * (k + 1)) * 7 + 3, dt_endday))),
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_test * (k + 1)) * 7, dt_endday)))
                ])
            else:
                valid_days_ = None
            test_days = [
                int(strf_time('%Y%m%d', timedelta_day(-(weeks_test * (k + 1)) * 7 + 3, dt_endday))),
                int(strf_time('%Y%m%d', timedelta_day(-(weeks_test * k) * 7, dt_endday)))
            ]
            list_days_.append([train_days, valid_days_, test_days])
            k += 1
            startday_ = int(strf_time('%Y%m%d', timedelta_day(-(weeks_train + weeks_valid + weeks_test * (k + 1)) * 7 + 3, dt_endday)))

        list_days = []
        for train_days_, valid_days_, test_days_ in list_days_:
            train_days_list = [x for x in day_list if train_days_[0] <= x <= train_days_[1]]
            train_days = [train_days_list[0], train_days_list[-1], len(train_days_list)]
            valid_days = []
            if 'V' in self.backname:
                for vsday, veday in valid_days_:
                    valid_days_list = [x for x in day_list if vsday <= x <= veday]
                    valid_days.append([valid_days_list[0], valid_days_list[-1], len(valid_days_list)])
            else:
                valid_days = None
            test_days_list = [x for x in day_list if test_days_[0] <= x <= test_days_[1]]
            test_days = [test_days_list[0], test_days_list[-1]]
            list_days.append([train_days, valid_days, test_days])

        return list_days[::-1]

    def GetOptomizeVarsList(self, random_optivars):
        total_count = 0
        vars_type = []
        vars_ = []
        for i, var in enumerate(list(self.vars.values())):
            error = False
            if len(var) != 2:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - self.vars[{i}]의 범위 설정 오류'))
                error = True
            if len(var[0]) != 3:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - self.vars[{i}]의 범위 설정 오류'))
                error = True
            if var[0][0] < var[0][1] and var[0][2] < 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - self.vars[{i}]의 범위 간격 설정 오류'))
                error = True
            if var[0][0] > var[0][1] and var[0][2] > 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - self.vars[{i}]의 범위 간격 설정 오류'))
                error = True
            if error:
                self.SysExit(True)
            low, high, gap = var[0]
            opti = var[1]
            varint = type(gap) == int
            lowhigh = low < high
            vars_type.append(lowhigh)
            vars_list = [[], opti]
            if gap == 0:
                vars_list[0].append(opti)
            else:
                total_count += 1
                for k in range(1000):
                    if varint:
                        next_var = low + gap * k
                    else:
                        next_var = round(low + gap * k, 2)
                    if (lowhigh and next_var <= high) or (not lowhigh and next_var >= high):
                        vars_list[0].append(next_var)
                    else:
                        break
            if opti not in vars_list[0] or random_optivars:
                vars_list[1] = random.choice(vars_list[0])
            vars_.append(vars_list)

        return total_count, vars_type, vars_

    def OptimizeGrid(self, mq, total_count, back_count, ccount, vars_type, vars_, startday, endday, i):
        self.tq.put(('경우의수', total_count, back_count, startday, endday, i))
        self.PutData(('변수정보', vars_, 0, startday, endday, i))

        hstd = 0
        data = mq.get()
        if type(data) == str:
            self.SysExit(True)
        else:
            hstd = data[-1]

        total_change = None
        for k in range(ccount if ccount != 0 else 100):
            if ccount == 0 and total_change == 0: break
            data = (ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 [{i+1}]구간 [{k+1}]단계 그리드 최적화 시작, 최고 기준값[{hstd:,.2f}], 최적값 변경 개수 [{total_change}]')
            threading_timer(6, self.wq.put, data)

            receiv_count   = sum([len(x[0]) for x in vars_ if len(x[0]) > 1])
            dict_turn_hvar = {i: var[1] for i, var in enumerate(vars_)}
            dict_turn_hstd = {i: hstd for i, x in enumerate(vars_) if len(x[0]) > 1}
            total_change   = 0

            self.PutData(('변수정보', vars_, 1, startday, endday, i))

            for _ in range(receiv_count):
                data = mq.get()
                if type(data) == str:
                    self.SysExit(True)
                else:
                    vturn, vkey, std = data
                    curr_typ = vars_type[vturn]
                    curr_var = vars_[vturn][0][vkey]
                    preh_var = vars_[vturn][1]
                    if std > dict_turn_hstd[vturn] or \
                            (std == dict_turn_hstd[vturn] and
                             ((curr_typ and curr_var > preh_var) or (not curr_typ and curr_var < preh_var))):
                        dict_turn_hstd[vturn] = std
                        dict_turn_hvar[vturn] = curr_var
                        if std > hstd: hstd = std

            list_turn_hvar = sorted(dict_turn_hvar.items(), key=operator.itemgetter(0))
            for vturn, high_var in list_turn_hvar:
                if high_var != vars_[vturn][1]:
                    total_change += 1
                    vars_[vturn][1] = high_var
                    data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{vturn}]의 최적값 변경 [{high_var}]')
                    threading_timer(5, self.wq.put, data)

        return vars_, hstd

    def OptimizeOptuna(self, mq, optuna_count, back_count, len_vars, optuna_fixvars, optuna_autostep, buystg_name,
                       sampler, vars_, startday, endday, i):
        self.dict_simple_vars = {}
        if optuna_count == 0:
            total_count = back_count * (len_vars + 1)
        else:
            total_count = back_count * optuna_count
        self.tq.put(('경우의수', total_count, back_count, startday, endday, i))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 [{i+1}]구간 OPTUNA 최적화 시작'))

        def objective(trial):
            simple_vars = []
            optuna_vars = []
            for j, var_ in enumerate(list(self.vars.values())):
                if j < 10:
                    trial_name = f'00{j}'
                elif j < 100:
                    trial_name = f'0{j}'
                else:
                    trial_name = f'{j}'

                varsint = type(var_[0][2]) == int
                if not (var_[0][2] == 0 or j in optuna_fixvars):
                    if optuna_autostep:
                        if varsint:
                            if var_[0][0] < var_[0][1]:
                                trial_ = trial.suggest_int(trial_name, var_[0][0], var_[0][1])
                            else:
                                trial_ = trial.suggest_int(trial_name, var_[0][1], var_[0][0])
                        else:
                            if var_[0][0] < var_[0][1]:
                                trial_ = trial.suggest_float(trial_name, var_[0][0], var_[0][1])
                            else:
                                trial_ = trial.suggest_float(trial_name, var_[0][1], var_[0][0])
                    else:
                        if varsint:
                            if var_[0][0] < var_[0][1]:
                                trial_ = trial.suggest_int(trial_name, var_[0][0], var_[0][1], step=var_[0][2])
                            else:
                                trial_ = trial.suggest_int(trial_name, var_[0][1], var_[0][0], step=-var_[0][2])
                        else:
                            if var_[0][0] < var_[0][1]:
                                trial_ = trial.suggest_float(trial_name, var_[0][0], var_[0][1], step=var_[0][2])
                            else:
                                trial_ = trial.suggest_float(trial_name, var_[0][1], var_[0][0], step=-var_[0][2])
                else:
                    if varsint:
                        trial_ = trial.suggest_int(trial_name, var_[1], var_[1])
                    else:
                        trial_ = trial.suggest_float(trial_name, var_[1], var_[1])

                simple_vars.append(trial_)
                optuna_vars.append(['', trial_])

            str_simple_vars = str(simple_vars)
            if str_simple_vars not in self.dict_simple_vars.keys():
                self.PutData(('변수정보', optuna_vars, 4, startday, endday, i))
                data_ = mq.get()
                if type(data_) == str:
                    ostd = 0
                    self.SysExit(True)
                else:
                    ostd = data_[2]
                    self.dict_simple_vars[str_simple_vars] = ostd
            else:
                ostd = self.dict_simple_vars[str_simple_vars]
            return ostd

        study_name = f'{self.backname}_{buystg_name}_{strf_time("%Y%m%d%H%M%S")}'
        optuna.logging.disable_default_handler()
        if sampler is None:
            self.study = optuna.create_study(storage=DB_OPTUNA, study_name=study_name, direction='maximize')
        else:
            self.study = optuna.create_study(storage=DB_OPTUNA, study_name=study_name, direction='maximize', sampler=sampler)
        self.study.optimize(objective, n_trials=10000, callbacks=[StopWhenNotUpdateBestCallBack(self.wq, self.tq, back_count, optuna_count, self.ui_gubun, len(self.vars))])
        for k, var in enumerate(list(self.study.best_params.values())):
            if var != vars_[k][1]:
                vars_[k][1] = var
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{k}]의 최적값 변경 [{var}]'))

        return vars_, self.study.best_value

    def PutData(self, data):
        self.tq.put(data[:3])
        for q in self.bstq_list:
            q.put(('백테시작', data[2], data[-1]))
        for q in self.beq_list:
            q.put(data[:5])

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 완료'))
        time.sleep(1)
        sys.exit()
