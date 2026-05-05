
import sys
import time
import copy
import random
import sqlite3
import numpy as np
import pandas as pd
from traceback import format_exc
from multiprocessing import Process, Queue
from backtest.back_static import send_result, get_moneytop_query
from utility.settings.setting_base import UI_NUM, DB_STRATEGY, DB_BACKTEST
from utility.static_method.strategy_version_manager import stg_save_version
from utility.static_method.static import now, timedelta_day, timedelta_sec, str_ymd, str_ymdhms, dt_ymd, error_decorator


class Total:
    """유전 알고리즘 최적화를 실행하는 클래스입니다.
    유전 알고리즘을 사용하여 파라미터 최적화를 수행합니다.
    """
    def __init__(self, wq, tq, mq, bstq_list, dict_set):
        self.wq           = wq
        self.tq           = tq
        self.mq           = mq
        self.bstq_list    = bstq_list
        self.dict_set     = dict_set

        self.back_count   = None
        self.std_list     = None
        self.optistandard = None
        self.betting      = None
        self.startday     = None
        self.endday       = None
        self.valid_days   = None

        self.dict_t       = {}
        self.dict_v       = {}

        self.vars_lists   = None
        self.stdp         = -float('inf')
        self.sub_total    = 0

        self._main_loop()

    def _main_loop(self):
        """메인 루프를 실행합니다.
        백테스트 결과를 수집하고 유전 알고리즘 최적화를 수행합니다.
        """
        sc = 0
        bc = 0
        st = {}
        dict_dummy = {}
        while True:
            try:
                data = self.tq.get()
                if data == '백테완료':
                    bc  += 1
                    if bc == self.back_count:
                        bc = 0
                        for q in self.bstq_list:
                            q.put(('백테완료', '분리집계'))

                elif data[0] == '더미결과':
                    sc += 1
                    _, vkey, _dict_dummy = data
                    if _dict_dummy:
                        for vturn in _dict_dummy:
                            dict_dummy[vturn][vkey] = 0

                    if sc == 20:
                        sc = 0
                        for vturn in range(50):
                            for vkey in range(20):
                                if vkey not in dict_dummy[vturn]:
                                    self.stdp = send_result(self._get_send_data(vturn, vkey), None)
                        dict_dummy = {}

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
                        self.stdp = send_result(
                            self._get_send_data(vturn, vkey),
                            self.dict_t[vturn][vkey],
                            self.dict_v[vturn][vkey],
                            self.dict_set['교차검증가중치']
                        )
                        st[vturn][vkey] = 0

                elif data[0] == 'ALL':
                    _, _, data, vturn, vkey = data
                    self.stdp = send_result(self._get_send_data(vturn, vkey), data)

                elif data[0] == '백테정보':
                    self._back_info(data)

                elif data[0] == '변수정보':
                    self.vars_lists = data[1]
                    dict_dummy      = {x: {} for x in range(50)}

                elif data[0] == '경우의수':
                    self.back_count = data[1]

                elif data == '백테완료중지':
                    break

                elif data == '백테중지':
                    self.mq.put('백테중지')
                    time.sleep(1)
                    break
            except Exception:
                self.wq.put((UI_NUM['시스템로그'], format_exc()))
                self.mq.put('백테중지')
                time.sleep(1)
                break

        sys.exit()

    def _back_info(self, data):
        """백테스트 정보를 설정합니다.
        Args:
            data: 백테스트 정보 데이터
        """
        self.betting      = data[1]
        self.startday     = data[2]
        self.endday       = data[3]
        self.std_list     = data[4]
        self.optistandard = data[5]
        self.valid_days   = data[6]
        if self.valid_days is not None:
            self.sub_total = len(self.valid_days) * 2
        else:
            self.sub_total = 2

    def _get_send_data(self, vturn, vkey):
        """전송 데이터를 생성합니다.
        Args:
            vturn: 회전 수
            vkey: 키 값
        Returns:
            전송 데이터 리스트
        """
        index = vturn * 20 + vkey
        return ['GA최적화', self.wq, self.mq, self.stdp, self.optistandard, 0, vturn, vkey, self.vars_lists[index], self.startday, self.endday, self.std_list, self.betting]


class OptimizeGeneticAlgorithm:
    """유전 알고리즘 최적화 엔진 클래스입니다.
    유전 알고리즘을 사용하여 파라미터 최적화를 수행합니다.
    """
    def __init__(self, sc, wq, bq, sq, tq, lq, beq_list, bstq_list, multi, backname, ui_gubun, dict_set, market_infos):
        self.shared_cnt   = sc
        self.wq           = wq
        self.bq           = bq
        self.sq           = sq
        self.tq           = tq
        self.lq           = lq
        self.beq_list     = beq_list
        self.bstq_list    = bstq_list
        self.multi        = multi
        self.backname     = backname
        self.ui_gubun     = ui_gubun
        self.dict_set     = dict_set
        self.market_gubun = market_infos[0]
        self.market_info  = market_infos[1]
        self.high_list    = []
        self.vars_list    = []
        self.opti_lists   = []
        self.high_vars    = []
        self.result       = {}
        self.vars         = {}
        self.total_count  = 0
        self.savename     = f"{self.market_info['전략구분']}_{self.backname.replace('최적화', '').lower()}"
        self.orignal_vars_list = []

        try:
            self._start()
        except SystemExit:
            pass
        except Exception:
            self.wq.put((UI_NUM['시스템로그'], format_exc()))
            self.tq.put('백테중지')

    # noinspection PyUnresolvedReferences
    @error_decorator
    def _start(self):
        """유전 알고리즘 최적화를 시작합니다."""
        start_time = now()
        data = self.bq.get()
        if self.market_gubun in (1, 2, 3, 5):
            betting = float(data[0]) * 1000000
        else:
            betting = float(data[0])
        starttime   = int(data[1])
        endtime     = int(data[2])
        buystg_name     = data[3]
        sellstg_name    = data[4]
        optivars_name   = data[5]
        std_text        = data[6].split(';')
        std_text        = [float(x) for x in std_text]
        optistandard    = data[8]
        back_count      = data[9]
        weeks_train     = data[10]
        weeks_valid = int(data[11])
        _           = int(data[12])
        backengin_sday  = data[13]
        backengin_eday  = data[14]

        if 'V' not in self.backname: weeks_valid = 0

        if weeks_train != 'ALL':
            weeks_train = int(weeks_train)
        else:
            weeks_train = int(((dt_ymd(backengin_eday) - dt_ymd(backengin_sday)).days + 1) / 7)

        dt_endday   = dt_ymd(backengin_eday)
        plus_day    = 3 if 'S' in self.ui_gubun else 1
        startday    = timedelta_day(-weeks_train * 7 + plus_day, dt_endday)
        startday    = int(str_ymd(startday))
        endday      = int(backengin_eday)
        valid_days_ = []
        if 'VC' in self.backname:
            for i in range(int(weeks_train / weeks_valid)):
                valid_days_.append([
                    int(str_ymd(timedelta_day(-(weeks_valid * 7 * (i + 1)) + 1, dt_endday))),
                    int(str_ymd(timedelta_day(-(weeks_valid * 7 * i), dt_endday)))
                ])
        elif 'V' in self.backname:
            valid_days_.append([int(str_ymd(timedelta_day(-weeks_valid * 7 + 1, dt_endday))), endday])
        else:
            valid_days_ = None

        if int(backengin_sday) > startday:
            self.wq.put((UI_NUM['백테스트'], '백테엔진에 로딩된 데이터가 부족합니다. 최소 학습기간 만큼의 데이터가 필요합니다'))
            self._sys_exit(True)

        con   = sqlite3.connect(self.market_info['백테디비'][self.is_tick])
        query = get_moneytop_query(is_tick, startday, endday, starttime, endtime)
        df_mt = pd.read_sql(query, con)
        con.close()

        if len(df_mt) == 0 or back_count == 0:
            self.wq.put((UI_NUM['백테스트'], '날짜 지정이 잘못되었거나 데이터가 존재하지 않습니다.'))
            self._sys_exit(True)

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f"SELECT * FROM {self.market_info['전략구분']}_optibuy", con).set_index('index')
        dfs = pd.read_sql(f"SELECT * FROM {self.market_info['전략구분']}_optisell", con).set_index('index')
        dfv = pd.read_sql(f"SELECT * FROM {self.market_info['전략구분']}_vars", con).set_index('index')
        buystg = dfb['전략코드'][buystg_name]
        sellstg = dfs['전략코드'][sellstg_name]
        optivars = dfv['전략코드'][optivars_name]
        con.close()

        optivars_ = None
        try:
            optivars_ = compile(optivars, '<string>', 'exec')
            exec(optivars_)
        except Exception:
            self.wq.put((UI_NUM['백테스트'], f'{format_exc()}오류 알림 - {self.backname} 변수설정'))
            self._sys_exit(True)

        if 'self.ms_analyzer' in buystg and not self.dict_set['시장미시구조분석']:
            self.wq.put((UI_NUM['백테스트'], '시장미시구조분석 미적용 상태입니다. 설정을 변경하십시오.'))
            self._sys_exit(True)

        if is_tick:
            df_mt['일자'] = (df_mt['index'].values // 1000000).astype(np.int64)
        else:
            df_mt['일자'] = (df_mt['index'].values // 10000).astype(np.int64)
        day_list = df_mt['일자'].unique()
        day_list.sort()

        valid_days = None
        startday, endday = day_list[0], day_list[-1]
        train_count = len([x for x in day_list if startday <= x <= endday])
        if 'V' in self.backname:
            valid_days = []
            for vsday, veday in valid_days_:
                try:
                    valid_days_list = [x for x in day_list if vsday <= x <= veday]
                    vdaycnt = len(valid_days_list)
                    tdaycnt = train_count - vdaycnt
                    valid_days.append([valid_days_list[0], valid_days_list[-1], tdaycnt, vdaycnt])
                except Exception:
                    self.wq.put((UI_NUM['백테스트'], f'[{vsday} ~ {veday}] 구간의 데이터가 존재하지 않습니다.'))
                    self._sys_exit(True)
            if not valid_days:
                self.wq.put((UI_NUM['백테스트'], '백테엔진의 데이터 로딩 마지막 일자가 잘못되었거나 검증구간의 데이터가 존재하지 않습니다.'))
                self._sys_exit(True)

        self.wq.put((UI_NUM['백테스트'], '텍스트에디터 클리어'))

        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 학습 기간 {startday} ~ {endday}'))
        if 'V' in self.backname:
            for vsday, veday, _, _ in valid_days:
                self.wq.put((UI_NUM['백테스트'], f'{self.backname} 검증 기간 {vsday} ~ {veday}'))
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 기간 추출 완료'))

        self.total_count = 1
        for value in list(self.vars.values()):
            self.total_count *= len(value[0])
            self.vars_list.append(value[0])
            self.high_list.append(value[1])
        self.orignal_vars_list = copy.deepcopy(self.vars_list)
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 매도수전략 설정 완료'))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.ui_gubun, None, valid_days, arry_bct, betting, len(day_list))
        for q in self.bstq_list:
            q.put(data)

        data = ('백테정보', betting, self.vars[0][0], startday, endday, starttime, endtime, buystg, sellstg)
        for q in self.beq_list:
            q.put(data)

        self.tq.put(('백테정보', betting, startday, endday, std_text, optistandard, valid_days))

        mq = Queue()
        Process(target=Total, args=(self.wq, self.tq, mq, self.bstq_list, self.dict_set)).start()
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))

        self.wq.put((UI_NUM['백테스트'], f'{self.backname} START'))

        k    = 1
        vc   = len(self.vars_list)
        hstd = -float('inf')
        goal = 2 ** int(vc / 2 + 0.5)
        self.opti_lists = []
        while self.total_count > goal:
            if k > 1: self._save_varslist(100, optistandard, buystg, sellstg)
            self.tq.put(('경우의수', back_count))

            for i in range(vc):
                vars_lists = self._get_varslist()
                if len(vars_lists) == 1000:
                    self.wq.put((UI_NUM['백테스트'], f'{self.backname} 백테스트 [{k}][{i+1}/{vc}]단계 시작, 최고 기준값[{hstd:,.2f}]'))

                    self.shared_cnt.value = 0
                    data = ('변수정보', vars_lists, 3)
                    self.tq.put(data)
                    for q in self.bstq_list:
                        q.put(('백테시작', 3))
                    for q in self.beq_list:
                        q.put(data)

                    for _ in range(1000):
                        data = mq.get()
                        if data.__class__ == str:
                            if self.result:
                                self._save_varslist(100, optistandard, buystg, sellstg)
                            self._sys_exit(True)
                        else:
                            vturn, vkey, std = data
                            index = vturn * 20 + vkey
                            self.result[std] = vars_lists[index]
                            if std > hstd: hstd = std
                else:
                    self.total_count = 0
                    break

            if self.total_count == 0:
                self.wq.put((UI_NUM['백테스트'], f'{self.backname} 모든 경우의 수 탐색 완료'))
                break

            if self.result: self._set_optilist(k, int(vc / 4) if vc / 4 > 5 else 5, goal)
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 현재 경우의수[{self.total_count:,.0f}] 목표 경우의수[{goal:,.0f}]'))
            k += 1

        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 최적화 완료'))
        self._save_varslist(100, optistandard, buystg, sellstg)

        exec(optivars_)
        optivars = optivars.split('self.vars[0]')[0]
        for i in range(len(self.vars)):
            if self.vars[i][1] != self.high_vars[i]:
                self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 self.vars[{i}]의 최적값 변경 {self.vars[i][1]} -> {self.high_vars[i]}'))
                self.vars[i][1] = self.high_vars[i]
            optivars += f'self.vars[{i}] = {self.vars[i]}\n'

        con = sqlite3.connect(DB_STRATEGY)
        cur = con.cursor()
        cur.execute(f"UPDATE {self.market_info['전략구분']}_vars SET 전략코드 = '{optivars}' WHERE `index` = '{optivars_name}'")
        con.commit()
        con.close()

        stg_save_version(self.market_info['전략구분'], 'opti', 'gavars', optivars_name, optivars)

        if self.dict_set['스톰라이브']: self.lq.put(self.backname)
        self.sq.put('지에이 최적화가 완료되었습니다.')
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        self._sys_exit(False)

    def _get_varslist(self):
        """변수 리스트를 생성합니다.
        Returns:
            변수 리스트
        """
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

    def _set_optilist(self, count, rank, goal):
        """최적화 리스트를 설정합니다.
        Args:
            count: 카운트
            rank: 랭크
            goal: 목표
        """
        self.vars_list = [[] for _ in self.vars_list]
        rs_list = sorted(self.result.items(), key=lambda x: x[0], reverse=True)

        text = f'{self.backname} 결과\n'
        for std, vars_list in rs_list[:rank]:
            text += f' 기준값 [{std:.2f}] 변수 {vars_list}\n'
            for i, vars_ in enumerate(vars_list):
                if vars_ not in self.vars_list[i]:
                    self.vars_list[i].append(vars_)
        self.wq.put((UI_NUM['백테스트'], text[:-1]))

        self.total_count = 1
        for i, vars_ in enumerate(self.vars_list):
            if count < 4 and self.high_list[i] not in vars_:
                self.vars_list[i].append(self.high_list[i])
            self.vars_list[i].sort()
            self.total_count *= len(self.vars_list[i])

        if self.total_count <= goal:
            text = ''
            for std, vars_list in rs_list[rank:100 - rank]:
                text += f' 기준값 [{std:.2f}] 변수 {vars_list}\n'
            self.wq.put((UI_NUM['백테스트'], text[:-1]))

        elif self.total_count > goal * count:
            for i, vars_list in enumerate(self.orignal_vars_list):
                vars_ = random.choice(vars_list)
                if vars_ not in self.vars_list[i]:
                    self.vars_list[i].append(vars_)

    def _save_varslist(self, rank, optistandard, buystg, sellstg):
        """변수 리스트를 저장합니다.
        Args:
            rank: 랭크
            optistandard: 최적화 기준
            buystg: 매수 전략
            sellstg: 매도 전략
        """
        rs_list = sorted(self.result.items(), key=lambda x: x[0], reverse=True)
        con = sqlite3.connect(DB_BACKTEST)
        for std, vars_list in rs_list[:rank]:
            data = [[optistandard, std, f'{vars_list}', buystg, sellstg]]
            df = pd.DataFrame(data, columns=['기준', '기준값', '범위설정', '매수코드', '매도코드'], index=[str_ymdhms()])
            df.to_sql(self.savename, con, if_exists='append', chunksize=2000)
        con.close()
        self.high_vars = rs_list[0][1]
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 상위100위 결과 저장 완료'))

    def _sys_exit(self, cancel):
        """시스템을 종료합니다.
        Args:
            cancel: 취소 여부
        """
        if cancel:
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} STOP'))
        else:
            self.tq.put('백테완료중지')
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} COMPLETE'))
        time.sleep(1)
        sys.exit()
