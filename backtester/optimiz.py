import sys
import time
import optuna
import random
import sqlite3
import operator
import numpy as np
import pandas as pd
from multiprocessing import Process, Queue
from backtester.back_static import SendTextAndStd, PltShow, GetMoneytopQuery, GetBackResult, GetResultDataframe, AddMdd
from utility.static import strf_time, strp_time, now, timedelta_day, threading_timer
from utility.setting import DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, ui_num, DB_STRATEGY, DB_BACKTEST, columns_vc, \
    DICT_SET, DB_SETTING, DB_OPTUNA, DB_STOCK_BACK_MIN, DB_COIN_BACK_MIN


class Total:
    def __init__(self, wq, sq, tq, teleQ, mq, lq, beq_list, bstq_list, backname, ui_gubun, gubun, multi, divid_mode):
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.mq           = mq
        self.lq           = lq
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
        self.savename     = f'{gubun_text}_{self.backname.replace("최적화", "").lower()}'

        self.back_count   = None
        self.file_name    = strf_time('%Y%m%d%H%M%S')

        self.dict_cn      = None
        self.buystg_name  = None
        self.buystg       = None
        self.sellstg      = None
        self.optivars     = None
        self.std_list     = None
        self.optistandard = None
        self.day_count    = None
        self.weeks_train  = None
        self.weeks_valid  = None
        self.weeks_test   = None

        self.betting      = None
        self.startday     = None
        self.endday       = None
        self.list_days    = None
        self.starttime    = None
        self.endtime      = None
        self.schedul      = None

        self.df_kp        = None
        self.df_kd        = None
        self.df_tsg       = None
        self.df_bct       = None

        self.dict_t       = {}
        self.dict_v       = {}

        self.vars         = None
        self.vars_list    = None
        self.opti_turn    = None
        self.stdp         = -2_000_000_000
        self.sub_total    = 0
        self.total_count  = 0
        self.total_count2 = 0

        self.MainLoop()

    def MainLoop(self):
        tt  = 0
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
                _, list_tsg, arry_bct = data
                self.Report(list_tsg, arry_bct)

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
                self.total_count = data[1]
                self.back_count  = data[2]
            elif data[0] == '횟수변경':
                self.total_count = data[1]
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
        self.buystg_name  = data[6]
        self.buystg       = data[7]
        self.sellstg      = data[8]
        self.optivars     = data[9]
        self.dict_cn      = data[10]
        self.std_list     = data[11]
        self.optistandard = data[12]
        self.schedul      = data[13]
        self.df_kp        = data[14]
        self.df_kd        = data[15]
        self.list_days    = data[16]
        self.day_count    = data[17]
        self.weeks_train  = data[18]
        self.weeks_valid  = data[19]
        self.weeks_test   = data[20]
        if self.list_days[1] is not None:
            self.sub_total = len(self.list_days[1]) * 2
        else:
            self.sub_total = 2

    def GetSendData(self, vturn=0, vkey=0):
        if self.opti_turn == 1:
            self.vars[vturn] = self.vars_list[vturn][0][vkey]
        return ['최적화', self.ui_gubun, self.wq, self.mq, self.stdp, self.optistandard, self.opti_turn, vturn, vkey, self.vars, self.startday, self.endday, self.std_list, self.betting]

    def Report(self, list_tsg, arry_bct):
        if not list_tsg:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다.'))
            self.mq.put('백테스트 완료')
            return

        self.df_tsg, self.df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)

        if 'T' in self.backname:
            _, _, test_days = self.list_days
            df_tsg = self.df_tsg[(test_days[0] * 1000000 <= self.df_tsg['매도시간']) & (self.df_tsg['매도시간'] <= test_days[1] * 1000000 + 240000)]
            _arry_bct = arry_bct[(test_days[0] * 1000000 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= test_days[1] * 1000000 + 240000)]
            _df_tsg   = df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy()
            _arry_tsg = np.array(_df_tsg, dtype='float64')
            _arry_bct = np.sort(_arry_bct, axis=0)[::-1]
            result    = GetBackResult(_arry_tsg, _arry_bct, self.betting, self.ui_gubun, test_days[2])
            result    = AddMdd(_arry_tsg, result)
            senddata  = self.GetSendData()
            senddata[0] = '최적화테스트'
            SendTextAndStd(senddata, result)

        _df_tsg  = self.df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy()
        arry_tsg = np.array(_df_tsg, dtype='float64')
        arry_bct = np.sort(arry_bct, axis=0)[::-1]
        result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, self.day_count)
        result   = AddMdd(arry_tsg, result)
        SendTextAndStd(self.GetSendData(), result)
        tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result

        startday, endday, starttime, endtime = str(self.startday), str(self.endday), str(self.starttime).zfill(6), str(self.endtime).zfill(6)
        startday  = startday[:4] + '-' + startday[4:6] + '-' + startday[6:]
        endday    = endday[:4] + '-' + endday[4:6] + '-' + endday[6:]
        starttime = starttime[:2] + ':' + starttime[2:4] + ':' + starttime[4:]
        endtime   = endtime[:2] + ':' + endtime[2:4] + ':' + endtime[4:]
        bet_unit  = '원' if self.ui_gubun != 'CF' else 'USDT'

        if self.weeks_valid == 0 and self.weeks_test == 0:
            back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습+검증기간 : {self.weeks_train}, 거래일수 : {self.day_count}, 평균값계산틱수 : {self.vars[0]}'
        elif self.weeks_valid == 0 and self.weeks_test != 0:
            back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습+검증/확인기간 : {self.weeks_train}/{self.weeks_test}, 거래일수 : {self.day_count}, 평균값계산틱수 : {self.vars[0]}'
        elif self.weeks_test == 0:
            back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습/검증기간 : {self.weeks_train}/{self.weeks_valid}, 거래일수 : {self.day_count}, 평균값계산틱수 : {self.vars[0]}'
        else:
            back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습/검증/확인기간 : {self.weeks_train}/{self.weeks_valid}/{self.weeks_test}, 거래일수 : {self.day_count}, 평균값계산틱수 : {self.vars[0]}'

        mdd_text   = f'최대낙폭금액 {mdd_:,.0f}{bet_unit}' if 'G' in self.optistandard else f'최대낙폭률 {mdd:,.2f}%'
        label_text = f'변수 {self.vars}\n종목당 배팅금액 {int(self.betting):,}{bet_unit}, 필요자금 {seed:,.0f}{bet_unit}, ' \
                     f'거래횟수 {tc}회, 일평균거래횟수 {atc}회, 적정최대보유종목수 {mhct}개, 평균보유기간 {ah:.2f}초\n' \
                     f'익절 {pc}회, 손절 {mc}회, 승률 {wr:.2f}%, 평균수익률 {app:.2f}%, 수익률합계 {tpp:.2f}%, ' \
                     f'{mdd_text}, 수익금합계 {tsg:,}{bet_unit}, 매매성능지수 {tpi:.2f}, 연간예상수익률 {cagr:.2f}%'

        if self.dict_set['스톰라이브']:
            backlive_text = f'back;{startday}~{endday};{starttime}~{endtime};{self.day_count};{self.vars[0]};{int(self.betting)};'\
                            f'{seed};{tc};{atc};{mhct};{ah:.2f};{pc};{mc};{wr:.2f};{app:.2f};{tpp:.2f};{mdd:.2f};{tsg};{cagr:.2f}'
            self.lq.put(backlive_text)

        if 'T' not in self.backname:
            con = sqlite3.connect(DB_SETTING)
            cur = con.cursor()
            df = pd.read_sql(f'SELECT * FROM {self.gubun}', con).set_index('index')
            gubun = '주식' if self.gubun == 'stock' else '코인'
            if self.buystg_name == df[f'{gubun}매수전략'][0]:
                cur.execute(f'UPDATE {self.gubun} SET {gubun}평균값계산틱수={self.vars[0]}')
            con.commit()
            con.close()

            con = sqlite3.connect(DB_STRATEGY)
            cur = con.cursor()
            vars_text = [str(i) for i in self.vars]
            vars_text = ';'.join(vars_text)
            cur.execute(f"UPDATE {self.gubun}optibuy SET 변수값 = '{vars_text}' WHERE `index` = '{self.buystg_name}'")
            con.commit()
            con.close()
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'최적화전략 {self.buystg_name}의 최적값 및 평균틱수 갱신 완료'))

        save_file_name = f'{self.savename}_{self.buystg_name}_{self.optistandard}_{self.file_name}'
        data = [f'{self.vars}', int(self.betting), seed, tc, atc, mhct, ah, pc, mc, wr, app, tpp, mdd, tsg, tpi, cagr, self.buystg, self.sellstg, self.optivars]
        df = pd.DataFrame([data], columns=columns_vc, index=[self.file_name])
        con = sqlite3.connect(DB_BACKTEST)
        df.to_sql(self.savename, con, if_exists='append', chunksize=1000)
        self.df_tsg.to_sql(save_file_name, con, if_exists='append', chunksize=1000)
        con.close()
        self.wq.put((ui_num[f'{self.ui_gubun.replace("F", "")}상세기록'], self.df_tsg))

        self.sq.put(f'{self.backname} 백테스트를 완료하였습니다.')
        self.mq.put('백테스트 완료')
        PltShow('최적화', self.teleQ, self.df_tsg, self.df_bct, self.dict_cn, seed, mdd, self.startday, self.endday, self.starttime, self.endtime,
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


class Optimize:
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
        self.ui_gubun   = ui_gubun   # 'S', 'C', 'CF'
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
            betting = float(data[0]) * 1000000  # 주식용 백만원 단위로 입력된 값
        else:
            betting = float(data[0])            # 바이낸스 선물용 단위 USDT
        starttime   = int(data[1])
        endtime     = int(data[2])
        buystg_name     = data[3]
        sellstg_name    = data[4]
        optivars_name   = data[5]
        dict_cn         = data[6]
        ccount      = int(data[7])
        std_text        = data[8].split(';')
        std_text        = [float(x) for x in std_text]
        optistandard    = data[9]
        back_count      = data[10]
        schedul         = data[11]
        df_kp           = data[12]
        df_kq           = data[13]
        weeks_train     = data[14]
        weeks_valid = int(data[15])
        weeks_test  = int(data[16])
        backengin_sday  = data[17]
        backengin_eday  = data[18]
        optuna_sampler  = data[19]

        optuna_fixvars = []
        if data[20] != '':
            try:
                optuna_fixvars = [int(x.strip()) for x in data[20].split(',')]
            except:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '고정할 범위의 번호를 잘못입력하였습니다.'))
                self.SysExit(True)
        optuna_count = int(data[21])
        optuna_autostep  = data[22]
        random_optivars  = data[23]
        only_buy         = data[24]
        only_sell        = data[25]

        if weeks_train != 'ALL':
            weeks_train = int(weeks_train)
        else:
            allweeks = int(((strp_time('%Y%m%d', backengin_eday) - strp_time('%Y%m%d', backengin_sday)).days + 1) / 7)
            if 'T' in self.backname:
                weeks_train = allweeks - weeks_valid - weeks_test
            elif 'V' in self.backname:
                weeks_train = allweeks - weeks_valid
            else:
                weeks_train = allweeks

        if 'V' not in self.backname: weeks_valid = 0
        if 'T' not in self.backname: weeks_test  = 0
        dt_endday = strp_time('%Y%m%d', backengin_eday)
        startday  = timedelta_day(-(weeks_train + weeks_valid + weeks_test) * 7 + 3, dt_endday)
        startday  = int(strf_time('%Y%m%d', startday))
        endday    = int(backengin_eday)

        if int(backengin_sday) > startday:
            perio_text = '학습시간'
            if 'V' in self.backname:
                perio_text = f'{perio_text} + 검증기간'
            if 'T' in self.backname:
                perio_text = f'{perio_text} + 확인기간'
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'백테엔진에 로딩된 데이터가 부족합니다. 최소 ({perio_text})주 만큼의 데이터가 필요합니다'))
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

        startday, endday = day_list[0], day_list[-1]
        list_days = self.GetListDays(startday, endday, dt_endday, day_list, weeks_train, weeks_valid, weeks_test)

        train_days, valid_days, test_days = list_days
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 학습 기간 {train_days[0]} ~ {train_days[1]}'))
        if 'V' in self.backname:
            for vsday, veday, _ in valid_days:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 검증 기간 {vsday} ~ {veday}'))
        if 'T' in self.backname:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 확인 기간 {test_days[0]} ~ {test_days[1]}'))

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 기간 추출 완료'))

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

        buy_num   = int(buystg.split('self.vars[')[1].split(']')[0])
        sell_num  = int(sellstg.split('self.vars[')[1].split(']')[0])
        buy_first = True if buy_num < sell_num else False

        optivars_ = compile(optivars, '<string>', 'exec')
        try:
            exec(optivars_)
        except Exception as e:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'시스템 명령 오류 알림 - {self.backname} 변수설정 {e}'))
            self.SysExit(True)

        total_count, vars_type, vars_ = self.GetOptomizeVarsList(random_optivars, only_buy, only_sell, buy_first, buy_num, sell_num)

        len_vars    = len(vars_)
        avg_list    = vars_[0][0]
        total_count *= ccount if ccount != 0 else 1
        total_count += 2
        total_count *= back_count
        text = f'{self.backname} 매도수전략 및 변수 설정 완료' if not random_optivars else f'{self.backname} 매도수전략 및 변수 최적값 랜덤 설정 완료'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text))

        mq = Queue()
        Process(
            target=Total,
            args=(self.wq, self.sq, self.tq, self.teleQ, mq, self.lq, self.beq_list, self.bstq_list, self.backname,
                  self.ui_gubun, self.gubun, self.multi, self.divid_mode)
        ).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))
        self.tq.put(('백테정보', betting, startday, endday, starttime, endtime, buystg_name, buystg, sellstg, optivars,
                     dict_cn, std_text, optistandard, schedul, df_kp, df_kq, list_days, len(day_list), weeks_train,
                     weeks_valid, weeks_test))

        time.sleep(1)
        data = ('백테정보', betting, avg_list, startday, endday, starttime, endtime, buystg, sellstg)
        for q in self.beq_list:
            q.put(data)
        if 'B' in self.backname:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'<font color=#45cdf7>OPTUNA Sampler : {optuna_sampler}</font>'))
        if only_buy:
            add_text = ', 매수전략의 변수만 최적화합니다.'
        elif only_sell:
            add_text = ', 매도전략의 변수만 최적화합니다.'
        else:
            add_text = ''
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 시작{add_text}'))

        if 'B' not in self.backname:
            vars_ = self.OptimizeGrid(mq, back_count, len_vars, vars_, only_buy, only_sell, buy_first, buy_num,
                                      sell_num, vars_type, ccount, random_optivars, optivars, optivars_, optivars_name)
        else:
            vars_ = self.OptimizeOptuna(mq, back_count, len_vars, vars_, only_buy, only_sell, buy_first, buy_num,
                                        sell_num, optuna_fixvars, optuna_count, optuna_autostep, optuna_sampler, buystg_name)

        time.sleep(6)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 최적화 완료'))
        time.sleep(1)

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '최적값 백테스트 시작'))
        self.PutData(('변수정보', vars_, 2))
        _ = mq.get()
        if self.dict_set['스톰라이브']: self.lq.put(self.backname.replace('O', '').replace('B', ''))
        self.SaveOptiVars(optivars, optivars_, vars_, optivars_name, only_buy, only_sell, buy_first, buy_num, sell_num)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        _ = mq.get()
        mq.close()
        self.SysExit(False)

    def GetListDays(self, startday, endday, dt_endday, day_list, weeks_train, weeks_valid, weeks_test):
        train_days_ = [startday, int(strf_time('%Y%m%d', timedelta_day(-weeks_test * 7, dt_endday)))]
        valid_days_ = []
        if 'VC' in self.backname:
            for i in range(int(weeks_train / weeks_valid) + 1):
                valid_days_.append([
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * (i + 1) + weeks_test) * 7 + 1, dt_endday))),
                    int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid * i + weeks_test) * 7, dt_endday)))
                ])
        elif 'V' in self.backname:
            valid_days_.append([
                int(strf_time('%Y%m%d', timedelta_day(-(weeks_valid + weeks_test) * 7 + 1, dt_endday))),
                int(strf_time('%Y%m%d', timedelta_day(-weeks_test * 7, dt_endday)))
            ])
        else:
            valid_days_ = None
        if 'T' in self.backname:
            test_days = [int(strf_time('%Y%m%d', timedelta_day(-weeks_test * 7 + 1, dt_endday))), endday]
        else:
            next_day  = int(strf_time('%Y%m%d', timedelta_day(1, dt_endday)))
            test_days = [next_day, next_day]

        train_days_list = [x for x in day_list if train_days_[0] <= x <= train_days_[1]]
        train_days = [train_days_list[0], train_days_list[-1], len(train_days_list)]
        if 'V' in self.backname:
            valid_days = []
            for vdays in valid_days_:
                try:
                    valid_days_list = [x for x in day_list if vdays[0] <= x <= vdays[1]]
                    valid_days.append([valid_days_list[0], valid_days_list[-1], len(valid_days_list)])
                except:
                    self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'백테엔진 마지막 일자와 실제 로딩된 데이터의 마지막 일자가 다릅니다.'))
                    self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'마지막 일자를 실제 데이터의 마지막 일자로 변경하여 재구동하십시오.'))
                    self.SysExit(True)
        else:
            valid_days = None

        if 'T' in self.backname:
            test_days_list = [x for x in day_list if test_days[0] <= x <= test_days[1]]
            test_days = [test_days_list[0], test_days_list[-1], len(test_days_list)]

        list_days = [train_days, valid_days, test_days]
        return list_days

    def GetOptomizeVarsList(self, random_optivars, only_buy, only_sell, buy_first, buy_num, sell_num):
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
            fixed = ((only_buy and ((buy_first and i > sell_num) or (not buy_first and i <= buy_num))) or
                     (only_sell and ((buy_first and i <= sell_num) or (not buy_first and i > buy_num))))
            if gap == 0 or fixed:
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

    def OptimizeGrid(self, mq, back_count, len_vars, vars_, only_buy, only_sell, buy_first, buy_num, sell_num,
                     vars_type, ccount, random_optivars, optivars, optivars_, optivars_name):
        self.tq.put(('경우의수', back_count, back_count))
        self.PutData(('변수정보', vars_, 0))

        hstd = 0
        data = mq.get()
        if type(data) == str:
            self.SysExit(True)
        else:
            hstd = data[-1]

        total_change = None
        total_del_list = [[] for _ in range(len_vars)]
        for k in range(ccount if ccount != 0 else 100):
            if ccount == 0 and total_change == 0: break
            data = (ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} [{k+1}]단계 그리드 최적화 시작, 최고 기준값[{hstd:,.2f}], 최적값 변경 개수 [{total_change}]')
            threading_timer(6, self.wq.put, data)

            receiv_count   = sum([len(x[0]) for x in vars_ if len(x[0]) > 1])
            dict_turn_hvar = {i: var[1] for i, var in enumerate(vars_)}
            dict_turn_hstd = {i: hstd for i, x in enumerate(vars_) if len(x[0]) > 1}
            turn_var_std   = {i: {} for i, x in enumerate(vars_) if len(x[0]) > 1}
            del_vars_list  = [[] for _ in range(len(vars_))]
            fix_vars_list  = []
            total_change   = 0

            self.PutData(('변수정보', vars_, 1))

            for _ in range(receiv_count):
                data = mq.get()
                if type(data) == str:
                    if not random_optivars:
                        self.SaveOptiVars(optivars, optivars_, vars_, optivars_name, only_buy, only_sell, buy_first,
                                          buy_num, sell_num)
                    self.SysExit(True)
                else:
                    vturn, vkey, std = data
                    curr_typ = vars_type[vturn]
                    curr_var = vars_[vturn][0][vkey]
                    preh_var = dict_turn_hvar[vturn]
                    if std > dict_turn_hstd[vturn] or \
                            (std == dict_turn_hstd[vturn] and
                             ((curr_typ and curr_var > preh_var) or (not curr_typ and curr_var < preh_var))):
                        dict_turn_hstd[vturn] = std
                        dict_turn_hvar[vturn] = curr_var
                        if std > hstd: hstd = std

                    if self.dict_set['범위자동관리']:
                        turn_var_std[vturn][curr_var] = std
                    elif std == -2_000_000_000:
                        del_vars_list[vturn].append(curr_var)

            list_turn_hvar = sorted(dict_turn_hvar.items(), key=operator.itemgetter(0))
            for vturn, high_var in list_turn_hvar:
                if high_var != vars_[vturn][1]:
                    total_change += 1
                    vars_[vturn][1] = high_var
                    data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{vturn}]의 최적값 변경 [{high_var}]')
                    threading_timer(5, self.wq.put, data)

            if self.dict_set['범위자동관리'] and hstd > 0:
                for vturn, var_std in turn_var_std.items():
                    set_std = len(set(list(var_std.values())))
                    if set_std <= 2:
                        fix_vars_list.append(vturn)
                    elif len(var_std) > 5:
                        del_list = []
                        for var, std in var_std.items():
                            if std < hstd / 4:
                                del_list.append(var)
                        if del_list:
                            del_list.sort()
                        del_vars_list[vturn] = del_list

            for i, del_list in enumerate(del_vars_list):
                if del_list:
                    for var in del_list:
                        if var not in total_del_list[i]: total_del_list[i].append(var)
                    vars_area = [x for x in vars_[i][0] if x not in del_vars_list[i]]
                    if vars_area:
                        vars_[i][0] = vars_area
                        data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 범위 삭제 {del_vars_list[i]}')
                    else:
                        high_var = vars_[i][1]
                        vars_[i][0] = [high_var]
                        data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 범위 고정 [{high_var}]')
                    threading_timer(5, self.wq.put, data)

            if self.dict_set['범위자동관리']:
                for i in range(len_vars):
                    len_vturn = len(vars_[i][0])
                    if len_vturn >= 7:
                        first  = vars_[i][0][0]
                        second = vars_[i][0][1]
                        last   = vars_[i][0][-1]
                        high   = vars_[i][1]
                        gap    = second - first
                        if high == first:
                            new = (first - gap) if type(gap) == int else round(first - gap, 2)
                            if new not in total_del_list[i]:
                                prev_list = vars_[i][0] if len_vturn < 20 else vars_[i][0][:-1]
                                vars_[i][0] = [new] + prev_list
                                data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 범위 추가 [{new}]')
                                threading_timer(5, self.wq.put, data)
                        elif high == last:
                            new = (last + gap) if type(gap) == int else round(first + gap, 2)
                            if new not in total_del_list[i]:
                                prev_list = vars_[i][0] if len_vturn < 20 else vars_[i][0][1:]
                                vars_[i][0] = prev_list + [new]
                                data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 범위 추가 [{new}]')
                                threading_timer(5, self.wq.put, data)

                for i in range(len_vars):
                    if i in fix_vars_list:
                        high_var = vars_[i][1]
                        vars_[i] = [[high_var], high_var]
                        data = (ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 범위 고정 [{high_var}]')
                        threading_timer(5, self.wq.put, data)
        return vars_

    def OptimizeOptuna(self, mq, back_count, len_vars, vars_, only_buy, only_sell, buy_first, buy_num, sell_num,
                       optuna_fixvars, optuna_count, optuna_autostep, optuna_sampler, buystg_name):
        if optuna_count == 0:
            total_count = back_count * (len_vars + 1)
        else:
            total_count = back_count * optuna_count

        self.tq.put(('경우의수', total_count, back_count))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} OPTUNA 최적화 시작'))

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

                fixed = ((only_buy and ((buy_first and j > sell_num) or (not buy_first and j <= buy_num))) or
                         (only_sell and ((buy_first and j <= sell_num) or (not buy_first and j > buy_num))))
                varsint = type(var_[0][2]) == int
                if not (var_[0][2] == 0 or j in optuna_fixvars or fixed):
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
                self.PutData(('변수정보', optuna_vars, 4))
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

        if optuna_sampler == 'TPESampler':
            sampler = optuna.samplers.TPESampler()
        elif optuna_sampler == 'BruteForceSampler':
            sampler = optuna.samplers.BruteForceSampler()
        elif optuna_sampler == 'CmaEsSampler':
            sampler = optuna.samplers.CmaEsSampler()
        elif optuna_sampler == 'QMCSampler':
            sampler = optuna.samplers.QMCSampler()
        else:
            sampler = optuna.samplers.RandomSampler()

        self.study = optuna.create_study(storage=DB_OPTUNA, study_name=study_name, direction='maximize', sampler=sampler)
        self.study.optimize(objective, n_trials=10000, callbacks=[StopWhenNotUpdateBestCallBack(self.wq, self.tq, back_count, optuna_count, self.ui_gubun, len(self.vars))])
        for k, var in enumerate(list(self.study.best_params.values())):
            if var != vars_[k][1]:
                vars_[k][1] = var
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{k}]의 최적값 변경 [{var}]'))

        return vars_

    def SaveOptiVars(self, optivars, optivars_, vars_, optivars_name, only_buy, only_sell, buy_first, buy_num, sell_num):
        if 'T' not in self.backname:
            change = 0
            optivars = optivars.split('self.vars[0]')[0]
            exec(optivars_)
            for i in range(len(self.vars)):
                fixed = ((only_buy and ((buy_first and i > sell_num) or (not buy_first and i <= buy_num))) or
                         (only_sell and ((buy_first and i <= sell_num) or (not buy_first and i > buy_num))))
                if not fixed:
                    preh_var = self.vars[i][1]
                    curh_var = vars_[i][1]
                    if preh_var != curh_var:
                        change += 1
                        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 결과 self.vars[{i}]의 최적값 {preh_var} -> {curh_var}'))
                    first   = vars_[i][0][0]
                    last    = vars_[i][0][-1]
                    gap_ori = self.vars[i][0][2]
                    gap     = gap_ori if first != last else 0
                    optivars += f'self.vars[{i}] = [[{first}, {last}, {gap}], {curh_var}]\n'
                else:
                    optivars += f'self.vars[{i}] = {self.vars[i]}\n'

            if change > 0:
                optivars = optivars[:-1]
                con = sqlite3.connect(DB_STRATEGY)
                cur = con.cursor()
                cur.execute(f"UPDATE {self.gubun}optivars SET 전략코드 = '{optivars}' WHERE `index` = '{optivars_name}'")
                con.commit()
                con.close()
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} {optivars_name}의 최적값 갱신 완료'))

    def PutData(self, data):
        self.tq.put(data)
        for q in self.bstq_list:
            q.put(('백테시작', data[-1]))
        for q in self.beq_list:
            q.put(data)

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테바'], 0, 100, 0))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 완료'))
        time.sleep(1)
        sys.exit()
