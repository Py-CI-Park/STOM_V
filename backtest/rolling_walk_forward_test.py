
import sys
import time
import copy
import optuna
import random
import sqlite3
import numpy as np
import pandas as pd
from traceback import format_exc
from multiprocessing import Process, Queue
from backtest.back_static_numba import GetResult, bootstrap_test
from utility.static import now, timedelta_day, str_ymd, str_ymdhms, dt_ymd
from backtest.back_static import SendResult, GetMoneytopQuery, PlotShow, GetResultDataframe, AddMdd
from utility.setting_base import ui_num, DB_STRATEGY, DB_BACKTEST, DB_STOCK_TICK_BACK, DB_COIN_TICK_BACK, \
    DB_OPTUNA, DB_STOCK_MIN_BACK, DB_COIN_MIN_BACK, DB_FUTURE_MIN_BACK, DB_FUTURE_TICK_BACK


class Total:
    def __init__(self, wq, sq, tq, teleQ, mq, bstq_list, backname, ui_gubun, gubun, market_text, dict_set):
        self.wq           = wq
        self.sq           = sq
        self.tq           = tq
        self.mq           = mq
        self.teleQ        = teleQ
        self.bstq_list    = bstq_list
        self.backname     = backname
        self.ui_gubun     = ui_gubun
        self.gubun        = gubun
        self.market_text  = market_text
        self.dict_set     = dict_set
        gubun_text        = f'{self.gubun}_future' if self.ui_gubun == 'CF' else self.gubun
        self.savename     = f'{gubun_text}_{self.backname.replace("전진분석", "").lower()}'

        self.back_count   = None
        self.out_count    = None
        self.file_name    = str_ymdhms()

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

        self.df_tsg       = None
        self.df_bct       = None

        self.list_tsg     = []
        self.list_bct     = []

        self.dict_t       = {}
        self.dict_v       = {}

        self.vars         = None
        self.vars_list    = None
        self.opti_kind    = None
        self.hstd_list    = None
        self.hstd         = -float('inf')
        self.sub_total    = 0

        self.MainLoop()

    def MainLoop(self):
        oc  = 0
        sc  = 0
        bc  = 0
        st  = {}
        dict_dummy = {}
        while True:
            try:
                data = self.tq.get()
                if data == '백테완료':
                    bc  += 1
                    if bc == self.back_count:
                        bc = 0
                        if self.opti_kind == 1:
                            for q in self.bstq_list:
                                q.put(('백테완료', '분리집계'))
                        else:
                            for q in self.bstq_list[:5]:
                                q.put(('백테완료', '일괄집계'))

                elif data[0] == '더미결과':
                    sc += 1
                    _, vkey, _dict_dummy = data
                    if _dict_dummy:
                        for vturn in _dict_dummy:
                            dict_dummy[vturn][vkey] = 0

                    if sc == 20:
                        sc = 0
                        for vturn in dict_dummy:
                            for vkey in range(len(self.vars_list[vturn][0])):
                                if vkey not in dict_dummy[vturn]:
                                    self.hstd = SendResult(self.GetSendData(vturn, vkey), None)
                        dict_dummy = {}

                elif data == '수집완료':
                    sc += 1
                    if sc == 5:
                        sc = 0
                        for q in self.bstq_list[:5]:
                            q.put('결과집계')

                elif data[0] == '결과없음':
                    self.hstd = SendResult(self.GetSendData(), None)

                elif data[0] in ('TRAIN', 'VALID'):
                    gubun, num, data, vturn, vkey = data
                    if gubun == 'TRAIN':
                        if vturn not in self.dict_t:
                            self.dict_t[vturn] = {}
                        if vkey not in self.dict_t[vturn]:
                            self.dict_t[vturn][vkey] = {}
                        self.dict_t[vturn][vkey][num] = data
                    else:
                        if vturn not in self.dict_v:
                            self.dict_v[vturn] = {}
                        if vkey not in self.dict_v[vturn]:
                            self.dict_v[vturn][vkey] = {}
                        self.dict_v[vturn][vkey][num] = data

                    if vturn not in st:
                        st[vturn] = {}
                    if vkey not in st[vturn]:
                        st[vturn][vkey] = 0
                    st[vturn][vkey] += 1

                    if st[vturn][vkey] == self.sub_total:
                        self.hstd = SendResult(
                            self.GetSendData(vturn, vkey),
                            self.dict_t[vturn][vkey],
                            self.dict_v[vturn][vkey],
                            self.dict_set['교차검증가중치']
                        )
                        st[vturn][vkey] = 0

                elif data[0] == 'ALL':
                    _, _, data, vturn, vkey = data
                    self.hstd = SendResult(self.GetSendData(vturn, vkey), data)

                elif data[0] == '백테결과':
                    oc += 1
                    _, list_tsg, arry_bct = data
                    self.Report(list_tsg, arry_bct, oc)

                elif data[0] == '백테정보':
                    self.BackInfo(data)

                elif data[0] == '변수정보':
                    self.vars_list = data[1]
                    self.opti_kind = data[2]
                    self.vars      = [var[1] for var in self.vars_list]
                    dict_dummy     = {x: {} for x, vars_ in enumerate(self.vars_list) if len(vars_[0]) > 1}

                elif data[0] == '경우의수':
                    self.back_count   = data[1]
                    self.startday     = data[2]
                    self.endday       = data[3]
                    self.out_count    = data[4]
                    self.hstd         = -float('inf')

                elif data[0] == '최적화정보':
                    self.hstd_list = data[1]

                elif data == '백테중지':
                    self.mq.put('백테중지')
                    time.sleep(1)
                    break
            except SystemExit:
                break
            except:
                self.wq.put((ui_num['시스템로그'], format_exc()))
                self.mq.put('백테중지')
                time.sleep(1)
                break

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
        self.weeks_train  = data[15]
        self.weeks_valid  = data[16]
        self.weeks_test   = data[17]
        if self.list_days[0][1] is not None:
            self.sub_total = len(self.list_days[0][1]) * 2
        else:
            self.sub_total = 2

    def GetSendData(self, vturn=0, vkey=0):
        vars_copy = self.vars.copy()
        if self.opti_kind == 1:
            vars_copy[vturn] = self.vars_list[vturn][0][vkey]
        return ['최적화', self.ui_gubun, self.wq, self.mq, self.hstd, self.optistandard, self.opti_kind, vturn, vkey, vars_copy, self.startday, self.endday, self.std_list, self.betting]

    def Report(self, list_tsg, arry_bct, oc):
        startday = self.hstd_list[oc - 1][0]
        endday   = self.hstd_list[oc - 1][1]
        merge    = self.hstd_list[oc - 1][2]
        text1    = f'[IN] P[{startday}~{endday}] {self.vars} MERGE[{merge:,.2f}]'
        text2    = f'[OUT] P[{self.startday}~{self.endday}] '

        tc = len(list_tsg)
        if tc > 0:
            self.df_tsg, self.df_bct = GetResultDataframe(self.ui_gubun, list_tsg, arry_bct)
            self.list_tsg.append(self.df_tsg)
            self.list_bct.append(self.df_bct)
            day_cnt  = len(np.unique(np.array([str(x)[:8] for x in arry_bct[:, 0]])))
            arry_tsg = np.array(self.df_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy(), dtype='float64')
            arry_bct = np.sort(arry_bct, axis=0)[::-1]
            result   = GetResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, day_cnt)
            result   = AddMdd(arry_tsg, result)
            tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result
            mddt   = f'{mdd_:,.0f}' if 'G' in self.optistandard else f'{mdd:,.2f}%'
            text2 += f'TC[{tc:,.0f}] ATC[{atc:,.1f}] MH[{mhct}] WR[{wr:,.2f}%] AP[{app:,.2f}%] TP[{tpp:,.2f}%] '\
                     f'TG[{tsg:,.0f}] MDD[{mddt}] TPI[{tpi:,.2f}] CAGR[{cagr:,.2f}]'
        else:
            text2 += '매수전략을 만족하는 경우가 없어 결과를 표시할 수 없습니다.'

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text1))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text2))
        self.mq.put('아웃샘플 백테스트 완료')

        if oc == self.out_count:
            df_all_tsg = pd.concat(self.list_tsg)
            df_all_bct = pd.concat(self.list_bct)

            df_all_tsg['수익금합계'] = df_all_tsg['수익금'].cumsum()

            df_tsg   = df_all_tsg[['보유시간', '매도시간', '수익률', '수익금', '수익금합계']].copy()
            df_tbc   = df_all_bct.copy()
            df_tbc['체결시간'] = df_tbc.index
            df_tbc['체결시간'] = df_tbc['체결시간'].astype(float)
            df_tbc   = df_tbc[['체결시간', '보유종목수', '보유금액']]
            arry_tsg = np.array(df_tsg, dtype='float64')
            arry_bct = np.array(df_tbc, dtype='float64')
            arry_bct = np.sort(arry_bct, axis=0)[::-1]
            day_cnt  = len(np.unique(np.array([str(x)[:8] for x in arry_bct[:, 0]])))
            result   = GetResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, day_cnt)
            result   = AddMdd(arry_tsg, result)
            tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result

            bootstrap_dist = bootstrap_test(df_all_tsg['수익률'].values / 100)
            bootstrap_avg  = round(np.mean(bootstrap_dist), 2)
            bootstrap_min  = round(np.percentile(bootstrap_dist, 2.5), 2)
            bootstrap_max  = round(np.percentile(bootstrap_dist, 97.5), 2)
            bootstrap_pv   = round(np.mean(bootstrap_dist > 0) * 100, 2)
            bootstrap_text = f"\n부트스트랩 평균수익률: {bootstrap_avg}%, 예상최소수익률: {bootstrap_min}%, 예상최대수익률: {bootstrap_max}%, 전략유의확률(pv): {bootstrap_pv}%"
            bootstrap_cmt  = f"\n이 전략은 95%의 확률로 [{bootstrap_min}~{bootstrap_max}%]의 수익률이 예상되며, 수익일 확률은 [{bootstrap_pv}%]입니다."
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '부트스트랩 결과' + bootstrap_text + bootstrap_cmt))

            startday, endday = str(self.startday_), str(self.endday_)
            startday = f'{startday[:4]}-{startday[4:6]}-{startday[6:]}'
            endday   = f'{endday[:4]}-{endday[4:6]}-{endday[6:]}'
            starttime, endtime = str(self.starttime).zfill(6), str(self.endtime).zfill(6)
            starttime = f'{starttime[:2]}:{starttime[2:4]}:{starttime[4:]}'
            endtime   = f'{endtime[:2]}:{endtime[2:4]}:{endtime[4:]}'

            bet_unit  = '원' if self.ui_gubun in ('S', 'C') else '계약' if self.ui_gubun == 'SF' else 'USDT'
            tsg_unit  = '원' if self.ui_gubun in ('S', 'C') else 'USD' if self.ui_gubun == 'SF' else 'USDT'
            mdd_text  = f'최대낙폭금액 {mdd_:,.0f}{tsg_unit}' if 'G' in self.optistandard else f'최대낙폭률 {mdd:,.2f}%'
            if self.dict_set[f'{self.market_text}타임프레임']:
                bc_unit = '초'
                is_tick = True
            else:
                bc_unit = '분'
                is_tick = False

            if self.weeks_valid == 0:
                back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습/확인기간 : {self.weeks_train}/{self.weeks_test}, 거래일수 : {day_cnt}'
            else:
                back_text = f'백테기간 : {startday}~{endday}, 백테시간 : {starttime}~{endtime}, 학습/검증/확인기간 : {self.weeks_train}/{self.weeks_valid}/{self.weeks_test}, 거래일수 : {day_cnt}'

            label_text = f'종목당 배팅금액 {int(self.betting):,}{bet_unit}, 필요자금 {seed:,.0f}{tsg_unit}, ' \
                         f'거래횟수 {tc}회, 일평균거래횟수 {atc:.1f}회, 적정최대보유종목수 {mhct}개, 평균보유기간 {ah:.2f}{bc_unit}\n' \
                         f'익절 {pc}회, 손절 {mc}회, 승률 {wr:.2f}%, 평균수익률 {app:.2f}%, 수익률합계 {tpp:.2f}%, ' \
                         f'수익금합계 {tsg:,}{tsg_unit}, {mdd_text}, 매매성능지수 {tpi:.2f}, 연간예상수익률 {cagr:.2f}%{bootstrap_text}'

            save_file_name = f"{self.savename}_{self.buystg_name}_{self.optistandard}_{self.file_name}"
            con = sqlite3.connect(DB_BACKTEST)
            df_all_tsg.to_sql(save_file_name, con, if_exists='append', chunksize=1000)
            con.close()
            self.wq.put((ui_num[f'{self.ui_gubun.replace("F", "")}상세기록'], df_all_tsg))

            self.sq.put(f'{self.backname} 백테스트를 완료하였습니다.')
            self.mq.put('백테스트 완료')
            PlotShow('전진분석', is_tick, self.teleQ, df_all_tsg, df_all_bct, self.dict_cn, seed, mdd, self.startday,
                     self.endday, self.starttime, self.endtime, self.list_days, self.backname, back_text, label_text,
                     save_file_name, self.schedul, False)
            self.mq.put('백테스트 완료')
            time.sleep(1)
            sys.exit()


class RollingWalkForwardTest:
    def __init__(self, sc, wq, bq, sq, tq, lq, teleQ, beq_list, bstq_list, multi, backname, ui_gubun, dict_set):
        self.shared_cnt = sc
        self.wq         = wq
        self.bq         = bq
        self.sq         = sq
        self.tq         = tq
        self.lq         = lq
        self.teleQ      = teleQ
        self.beq_list   = beq_list
        self.bstq_list  = bstq_list
        self.multi      = multi
        self.backname   = backname
        self.ui_gubun   = ui_gubun
        self.dict_set   = dict_set
        if self.ui_gubun == 'S':
            self.gubun = 'stock'
        elif self.ui_gubun == 'SF':
            self.gubun = 'future'
        else:
            self.gubun = 'coin'
        self.vars       = {}
        self.vars_      = []
        self.study      = None
        self.dict_simple_vars = {}

        try:
            self.Start()
        except SystemExit:
            sys.exit()
        except:
            self.wq.put((ui_num['시스템로그'], format_exc()))
            self.tq.put('백테중지')

    # noinspection PyUnresolvedReferences
    def Start(self):
        start_time = now()
        data = self.bq.get()
        if self.ui_gubun not in ('CF', 'SF'):
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
        weeks_train = int(data[14])
        weeks_valid = int(data[15])
        weeks_test  = int(data[16])
        backengin_sday  = data[17]
        backengin_eday  = data[18]

        sampler = None
        optuna_sampler  = data[19]
        if optuna_sampler == 'TPESampler':
            sampler = optuna.samplers.TPESampler()
        elif optuna_sampler == 'BruteForceSampler':
            sampler = optuna.samplers.BruteForceSampler()
        elif optuna_sampler == 'CmaEsSampler':
            sampler = optuna.samplers.CmaEsSampler()
        elif optuna_sampler == 'QMCSampler':
            sampler = optuna.samplers.QMCSampler()
        elif optuna_sampler == 'RandomSampler':
            sampler = optuna.samplers.RandomSampler()

        optuna_fixvars = []
        if data[20]:
            try:
                optuna_fixvars = [int(x.strip()) for x in data[20].split(',')]
            except:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '고정할 범위의 번호를 잘못입력하였습니다.'))
                self.SysExit(True)

        optuna_count = int(data[21])
        optuna_autostep  = data[22]
        random_optivars  = data[23]

        plus_day = 3 if 'S' in self.ui_gubun else 1
        int_day  = int(str_ymd(timedelta_day(-(weeks_train + weeks_test * 2) * 7 + plus_day, dt_ymd(str(endday)))))

        if int(backengin_sday) > int_day:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 (학습기간 + 확인기간 * 2)주 만큼의 데이터가 필요합니다'))
            self.SysExit(True)
        elif startday > int_day:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '전진분석 시작 일자가 잘못되었습니다. (학습기간 + 확인기간 * 2)주 이전 일자로 선택하십시오.'))
            self.SysExit(True)
        elif endday > int(backengin_eday):
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '전진분석 종료 일자가 잘못되었습니다. 백테엔진 데이터 로딩 마지막 일자로 선택하십시오.'))
            self.SysExit(True)

        market_text = '주식' if self.ui_gubun in ('S', 'SF') else '코인'
        if self.ui_gubun == 'S':
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_STOCK_TICK_BACK
                is_tick = True
            else:
                db = DB_STOCK_MIN_BACK
                is_tick = False
        elif self.ui_gubun == 'SF':
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_FUTURE_TICK_BACK
                is_tick = True
            else:
                db = DB_FUTURE_MIN_BACK
                is_tick = False
        else:
            if self.dict_set[f'{market_text}타임프레임']:
                db = DB_COIN_TICK_BACK
                is_tick = True
            else:
                db = DB_COIN_MIN_BACK
                is_tick = False

        con   = sqlite3.connect(db)
        query = GetMoneytopQuery(is_tick, self.ui_gubun, startday, endday, starttime, endtime)
        df_mt = pd.read_sql(query, con)
        con.close()

        if len(df_mt) == 0 or back_count == 0:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '날짜 지정이 잘못되었거나 데이터가 존재하지 않습니다.'))
            self.SysExit(True)

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f'SELECT * FROM {self.gubun}optibuy', con).set_index('index')
        dfs = pd.read_sql(f'SELECT * FROM {self.gubun}optisell', con).set_index('index')
        dfv = pd.read_sql(f'SELECT * FROM {self.gubun}optivars', con).set_index('index')
        buystg = dfb['전략코드'][buystg_name]
        sellstg = dfs['전략코드'][sellstg_name]
        optivars = dfv['전략코드'][optivars_name]
        con.close()

        try:
            exec(compile(optivars, '<string>', 'exec'))
        except:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{format_exc()}오류 알림 - 최적화 변수설정 1단계'))
            self.SysExit(True)

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '텍스트에디터 클리어'))

        if is_tick:
            df_mt['일자'] = (df_mt['index'].values // 1000000).astype(np.int64)
        else:
            df_mt['일자'] = (df_mt['index'].values // 10000).astype(np.int64)
        day_list = df_mt['일자'].unique()
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

        out_count = len(list_days)
        vars_type, avg_list = self.GetOptomizeVarsList(random_optivars)
        text = f'{self.backname} 매도수전략 및 변수 설정 완료' if not random_optivars else f'{self.backname} 매도수전략 및 변수 최적값 랜덤 설정 완료'
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.ui_gubun, list_days, None, arry_bct, betting, len(day_list))
        for q in self.bstq_list:
            q.put(data)

        data = ('백테정보', betting, avg_list, startday, endday, starttime, endtime, buystg, sellstg)
        for q in self.beq_list:
            q.put(data)

        self.tq.put(('백테정보', betting, startday, endday, starttime, endtime, buystg_name, buystg, sellstg, optivars,
                     dict_cn, list_days, std_text, optistandard, schedul, weeks_train, weeks_valid, weeks_test))

        mq = Queue()
        Process(
            target=Total,
            args=(self.wq, self.sq, self.tq, self.teleQ, mq, self.bstq_list, self.backname, self.ui_gubun,
                  self.gubun, market_text, self.dict_set)
        ).start()
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))

        if 'B' in self.backname:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'<font color=#54d2f9>OPTUNA Sampler : {optuna_sampler}</font>'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} START'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 최적화 시작'))

        hstd_list = []
        hvar_list = []
        for in_count, days in enumerate(list_days):
            train_days, _, _ = days
            startday, endday = train_days[0], train_days[1]

            if 'B' not in self.backname:
                hstd = self.OptimizeGrid(
                    mq, back_count, ccount, vars_type, startday, endday, in_count
                )
            else:
                hstd = self.OptimizeOptuna(
                    mq, optuna_count, back_count, optuna_fixvars, optuna_autostep, buystg_name, sampler,
                    startday, endday, in_count
                )

            hvar_list.append(copy.deepcopy(self.vars_))
            hstd_list.append([startday, endday, hstd])

        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 최적화 완료'))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 아웃샘플 백테스트 시작'))

        self.tq.put(('최적화정보', hstd_list))
        for i, days in enumerate(list_days):
            startday, endday = days[2]
            self.tq.put(('경우의수', back_count, startday, endday, out_count))
            self.BackStart(('변수정보', hvar_list[i], 2, startday, endday, i))
            data = mq.get()
            if data != '아웃샘플 백테스트 완료': self.SysExit(True)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 아웃샘플 백테스트 완료'))

        data = mq.get()
        if data != '백테스트 완료': self.SysExit(True)
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        if self.dict_set['스톰라이브']: self.lq.put(self.backname.replace('O', '').replace('B', ''))

        data = mq.get()
        if data != '백테스트 완료': self.SysExit(True)
        self.SysExit(False)

    def GetListDays(self, startday, endday, weeks_train, weeks_valid, weeks_test, day_list):
        k = 0
        list_days_ = []
        dt_endday  = dt_ymd(str(endday))
        plus_day   = 3 if 'S' in self.ui_gubun else 1
        startday_  = int(str_ymd(timedelta_day(-(weeks_train + weeks_test * (k + 1)) * 7 + plus_day, dt_endday)))
        while startday_ >= startday:
            train_days_ = [
                startday_, int(str_ymd(timedelta_day(-weeks_test * (k + 1) * 7, dt_endday)))
            ]
            valid_days_ = []
            if 'VC' in self.backname:
                for i in range(int(weeks_train / weeks_valid)):
                    valid_days_.append([
                        int(str_ymd(timedelta_day(-(weeks_valid * (i + 1) + weeks_test * (k + 1)) * 7 + plus_day, dt_endday))),
                        int(str_ymd(timedelta_day(-(weeks_valid * i + weeks_test * (k + 1)) * 7, dt_endday)))
                    ])
            elif 'V' in self.backname:
                valid_days_.append([
                    int(str_ymd(timedelta_day(-(weeks_valid + weeks_test * (k + 1)) * 7 + plus_day, dt_endday))),
                    int(str_ymd(timedelta_day(-(weeks_test * (k + 1)) * 7, dt_endday)))
                ])
            else:
                valid_days_ = None
            test_days_ = [
                int(str_ymd(timedelta_day(-(weeks_test * (k + 1)) * 7 + plus_day, dt_endday))),
                int(str_ymd(timedelta_day(-(weeks_test * k) * 7, dt_endday)))
            ]
            list_days_.append([train_days_, valid_days_, test_days_])
            k += 1
            startday_ = int(str_ymd(timedelta_day(-(weeks_train + weeks_test * (k + 1)) * 7 + plus_day, dt_endday)))

        list_days = []
        for train_days_, valid_days_, test_days_ in list_days_:
            train_days_list = [x for x in day_list if train_days_[0] <= x <= train_days_[1]]
            if 'V' in self.backname:
                total_vdays_count = 0
                valid_days = []
                for vsday, veday in valid_days_:
                    valid_days_list = [x for x in day_list if vsday <= x <= veday]
                    vdays_count = len(valid_days_list)
                    total_vdays_count += vdays_count
                    valid_days.append([valid_days_list[0], valid_days_list[-1], vdays_count])
                avg_vdays_count = int(total_vdays_count / len(valid_days))
                train_days = [train_days_list[0], train_days_list[-1], len(train_days_list) - avg_vdays_count]
            else:
                valid_days = None
                train_days = [train_days_list[0], train_days_list[-1], len(train_days_list)]
            test_days_list = [x for x in day_list if test_days_[0] <= x <= test_days_[1]]
            test_days = [test_days_list[0], test_days_list[-1]]
            list_days.append([train_days, valid_days, test_days])

        return list_days[::-1]

    def GetOptomizeVarsList(self, random_optivars):
        vars_type   = []
        self.vars_  = []
        for i, var in enumerate(list(self.vars.values())):
            error = False
            if len(var) != 2:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'오류 알림 - self.vars[{i}]의 범위 설정 오류'))
                error = True
            if len(var[0]) != 3:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'오류 알림 - self.vars[{i}]의 범위 설정 오류'))
                error = True
            if var[0][0] < var[0][1] and var[0][2] < 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'오류 알림 - self.vars[{i}]의 범위 간격 설정 오류'))
                error = True
            if var[0][0] > var[0][1] and var[0][2] > 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'오류 알림 - self.vars[{i}]의 범위 간격 설정 오류'))
                error = True
            if error:
                self.SysExit(True)
            low, high, gap = var[0]
            opti = var[1]
            varint = gap.__class__ == int
            lowhigh = low < high
            vars_type.append(lowhigh)
            vars_list = [[], opti]
            if gap == 0:
                vars_list[0].append(opti)
            else:
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
            self.vars_.append(vars_list)

        return vars_type, self.vars_[0][0]

    def OptimizeGrid(self, mq, back_count, ccount, vars_type, startday, endday, in_count):
        self.tq.put(('경우의수', back_count, startday, endday, in_count))
        self.BackStart(('변수정보', self.vars_, 0, startday, endday, in_count))

        hstd = 0
        data = mq.get()
        if data.__class__ == str:
            self.SysExit(True)
        else:
            hstd = data[-1]

        vars_change_count = None
        init_std          = -float('inf')
        for k in range(ccount if ccount != 0 else 100):
            self.wq.put((
                ui_num[f'{self.ui_gubun}백테스트'],
                f'{self.backname} 인샘플 [{in_count + 1}]구간 [{k + 1}]단계 그리드 최적화 시작, 최고 기준값[{hstd:,.2f}], 최적값 변경 개수 [{vars_change_count}]'
            ))

            vars_change_count   = 0
            previous_high_std   = hstd
            bool_changed_hstd   = False
            result_receiv_count = sum([len(x[0]) for x in self.vars_ if len(x[0]) > 1])
            dict_turn_hvar_hstd = {i: [x[1], init_std] for i, x in enumerate(self.vars_) if len(x[0]) > 1}

            if result_receiv_count == 0:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '모든 파라미터 고정, 최적화를 종료합니다.'))
                break

            self.BackStart(('변수정보', self.vars_, 1, startday, endday, in_count))

            for _ in range(result_receiv_count):
                data = mq.get()
                if data.__class__ == str:
                    self.SysExit(True)
                else:
                    vturn, vkey, std = data
                    cur_turn_type  = vars_type[vturn]
                    cur_turn_var   = self.vars_[vturn][0][vkey]
                    turn_hvar_hstd = dict_turn_hvar_hstd[vturn]
                    pre_turn_hvar, pre_turn_hstd = turn_hvar_hstd
                    A = std > pre_turn_hstd
                    B = std == pre_turn_hstd and cur_turn_var > pre_turn_hvar and cur_turn_type
                    C = std == pre_turn_hstd and cur_turn_var < pre_turn_hvar and not cur_turn_type
                    if A or B or C:
                        turn_hvar_hstd[0] = cur_turn_var
                        turn_hvar_hstd[1] = std
                        if std > hstd:
                            hstd = std
                            if not bool_changed_hstd:
                                bool_changed_hstd = True

            high_ratio = []
            if bool_changed_hstd:
                high_ratio, vars_change_count = self.CheckOptivalueCombination(
                    mq, previous_high_std, vars_change_count, dict_turn_hvar_hstd, startday, endday, in_count
                )

            if previous_high_std > 0:
                self.AdjustVarsRange()

            if not bool_changed_hstd:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '최고기준값 갱신 없음, 최적화를 종료합니다.'))
                break

            if previous_high_std > 0 and hstd > 0 and high_ratio[0] < self.dict_set['기준값최소상승률']:
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f"기준값 상승률 {self.dict_set['기준값최소상승률']}% 미달성, 최적화를 종료합니다."))
                break

            hstd = high_ratio[2]

        return hstd

    def CheckOptivalueCombination(self, mq, previous_high_std, vars_change_count, dict_turn_hvar_hstd, startday, endday, in_count):
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '최적값 조합 확인 시작'))
        high_ratio = [0, previous_high_std, previous_high_std]
        std_set = sorted(set(v[1] for v in dict_turn_hvar_hstd.values()))
        last = len(std_set)
        for i, std in enumerate(std_set):
            vars_copy = copy.deepcopy(self.vars_)
            for vturn, hvar_hstd in dict_turn_hvar_hstd.items():
                pre_turn_hvar = vars_copy[vturn][1]
                cur_turn_hvar, cur_turn_hstd = hvar_hstd
                if cur_turn_hstd >= std and cur_turn_hvar != pre_turn_hvar:
                    vars_copy[vturn][1] = cur_turn_hvar

            self.BackStart(('변수정보', vars_copy, 0, startday, endday, in_count))
            data = mq.get()
            if data.__class__ == str:
                self.SysExit(True)
            else:
                check_hstd = data[-1]
                if previous_high_std > 0:
                    ratio = round((check_hstd / previous_high_std - 1) * 100, 2)
                else:
                    ratio = round((1 - check_hstd / previous_high_std) * 100, 2)
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'최적값 조합 확인 중[{i+1}/{last}] ... 조합기준값[{std:,.2f}] 기준값상승률[{ratio}%]'))
                if ratio > high_ratio[0]:
                    high_ratio = [ratio, std, check_hstd]
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], '최적값 조합 확인 완료'))

        text = '\n'
        high_ratio_std = high_ratio[1]
        for vturn, hvar_hstd in dict_turn_hvar_hstd.items():
            pre_turn_hvar = self.vars_[vturn][1]
            cur_turn_hvar, cur_turn_hstd = hvar_hstd
            if cur_turn_hstd >= high_ratio_std and cur_turn_hvar != pre_turn_hvar:
                vars_change_count += 1
                self.vars_[vturn][1] = cur_turn_hvar
                text = f'{text}self.vars[{vturn}]의 최적값 변경 [{pre_turn_hvar} -> {cur_turn_hvar}]\n'
        if text != '\n': self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text[:-1]))
        return high_ratio, vars_change_count

    def AdjustVarsRange(self, best_params=None):
        text = '\n'
        for i, var in enumerate(self.vars_):
            len_var = len(var[0])
            if len_var >= 5:
                first  = var[0][0]
                second = var[0][1]
                last   = var[0][-1]
                gap    = second - first
                if best_params is None:
                    high = var[1]
                else:
                    high = best_params[i]
                if high == first:
                    new = (first - gap) if gap.__class__ == int else round(first - gap, 2)
                    prev_list = var[0] if len_var < 20 else var[0][:-1]
                    self.vars_[i][0] = [new] + prev_list
                    text = f'{text}self.vars[{i}]의 범위 추가 [{new}]\n'
                elif high == last:
                    new = (last + gap) if gap.__class__ == int else round(first + gap, 2)
                    prev_list = var[0] if len_var < 20 else var[0][1:]
                    self.vars_[i][0] = prev_list + [new]
                    text = f'{text}self.vars[{i}]의 범위 추가 [{new}]\n'
        if text != '\n': self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], text[:-1]))

    def OptimizeOptuna(self, mq, optuna_count, back_count, optuna_fixvars, optuna_autostep, buystg_name,
                       sampler, startday, endday, in_count):

        self.dict_simple_vars = {}
        self.tq.put(('경우의수', back_count, startday, endday, in_count))
        self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} 인샘플 [{in_count + 1}]구간 OPTUNA 최적화 시작'))

        def objective(trial):
            optuna_vars = []
            backte_vars = []
            for i, var_ in enumerate(self.vars_):
                trial_name = f'{i:03d}'
                varsint = var_[0][2].__class__ == int
                suggest_func = trial.suggest_int if varsint else trial.suggest_float
                if not (var_[0][2] == 0 or i in optuna_fixvars):
                    min_val, max_val = sorted((var_[0][0], var_[0][1]))
                    if optuna_autostep:
                        trial_ = suggest_func(trial_name, min_val, max_val)
                    else:
                        step = var_[0][2] if min_val == var_[0][0] else -var_[0][2]
                        trial_ = suggest_func(trial_name, min_val, max_val, step=step)
                else:
                    trial_ = suggest_func(trial_name, var_[1], var_[1])

                if '.' in str(trial_): trial_ = round(trial_, 2)

                optuna_vars.append(trial_)
                backte_vars.append([[], trial_])

            str_simple_vars = str(optuna_vars)
            if str_simple_vars not in self.dict_simple_vars:
                self.BackStart(('변수정보', backte_vars, 4, startday, endday, in_count))
                data_ = mq.get()
                if data_.__class__ == str:
                    ostd = 0
                    self.SysExit(True)
                else:
                    ostd = data_[2]
                    self.dict_simple_vars[str_simple_vars] = ostd
            else:
                ostd = self.dict_simple_vars[str_simple_vars]
            return ostd

        optuna.logging.disable_default_handler()
        self.study = optuna.create_study(
            storage=DB_OPTUNA,
            study_name=f'{self.backname}_{buystg_name}_{str_ymdhms()}',
            direction='maximize',
            sampler=sampler
        )
        self.study.enqueue_trial({f'{i:03d}': var[1] for i, var in enumerate(self.vars_)})
        callback = StopWhenNotUpdateBestCallBack(self, back_count, optuna_count)
        self.study.optimize(objective, n_trials=10000, callbacks=[callback])
        for i, high_var in enumerate(self.study.best_params.values()):
            pre_hvar = self.vars_[i][1]
            if high_var != pre_hvar:
                self.vars_[i][1] = high_var
                self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'self.vars[{i}]의 최적값 변경 [{pre_hvar} -> {high_var}]'))

        return self.study.best_value

    def BackStart(self, data):
        self.shared_cnt.value = 0
        self.tq.put(data[:3])
        for q in self.bstq_list:
            q.put(('백테시작', data[2], data[-1]))
        for q in self.beq_list:
            q.put(data[:5])

    def SysExit(self, cancel):
        if cancel:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} STOP'))
        else:
            self.wq.put((ui_num[f'{self.ui_gubun}백테스트'], f'{self.backname} COMPLETE'))
        time.sleep(1)
        sys.exit()


class StopWhenNotUpdateBestCallBack:
    def __init__(self, main, back_count, optuna_count):
        self.main         = main
        self.back_count   = back_count
        self.optuna_count = optuna_count
        self.len_vars     = len(self.main.vars_)
        self.adjust_cnt   = max(self.len_vars, self.optuna_count)

    def __call__(self, study: optuna.study.Study, trial: optuna.trial.FrozenTrial) -> None:
        best_opt = study.best_value
        best_num = study.best_trial.number
        curr_num = trial.number
        last_num = (best_num + self.len_vars) if self.optuna_count == 0 else (best_num + self.optuna_count)
        rema_num = last_num - curr_num
        self.main.wq.put((ui_num[f'{self.main.ui_gubun}백테스트'], f'<font color=#54d2f9>OPTUNA INFO 최고기준값[{best_opt:,}] 기준값갱신[{best_num}] 현재횟수[{curr_num}] 남은횟수[{rema_num}]</font>'))
        if curr_num >= self.adjust_cnt and curr_num == best_num:
            self.main.AdjustVarsRange(list(study.best_params.values()))
        if curr_num == last_num:
            study.stop()
