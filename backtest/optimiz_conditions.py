
import sys
import time
import random
import sqlite3
import numpy as np
import pandas as pd
from traceback import format_exc
from multiprocessing import Process, Queue
from utility.settings.setting_base import UI_NUM, DB_BACKTEST
from backtest.back_static import send_result, get_moneytop_query
from utility.static_method.static import factorial, now, timedelta_day, timedelta_sec, str_ymd, str_ymdhms, dt_ymd, \
    error_decorator


class Total:
    """조건 최적화를 실행하는 클래스입니다.
    다양한 조건 조합을 테스트하여 최적 조건을 찾습니다.
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

        self.stdp         = -float('inf')
        self.sub_total    = 0

        self._main_loop()

    def _main_loop(self):
        """메인 루프를 실행합니다.
        백테스트 결과를 수집하고 조건 최적화를 수행합니다.
        """
        sc = 0
        bc = 0
        st = {}
        dict_dummy = {}
        while True:
            try:
                data = self.tq.get()
                if data == '백테완료':
                    bc += 1
                    if bc == self.back_count:
                        bc = 0
                        for stq in self.bstq_list:
                            stq.put(('백테완료', '분리집계'))

                elif data[0] == '더미결과':
                    sc += 1
                    _, vkey, _dict_dummy = data
                    if _dict_dummy:
                        dict_dummy[vkey] = 0

                    if sc == 20:
                        sc = 0
                        for vkey in range(20):
                            if vkey not in dict_dummy:
                                self.stdp = send_result(self._get_send_data(), None)
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

                elif data[0] == '경우의수':
                    self.back_count  = data[1]

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

    def _get_send_data(self, vturn=0, vkey=0):
        """전송 데이터를 생성합니다.
        Args:
            vturn: 회전 수
            vkey: 키 값
        Returns:
            전송 데이터 리스트
        """
        return ['조건최적화', self.wq, self.mq, self.stdp, self.optistandard, 0, vturn, vkey, None, self.startday, self.endday, self.std_list, self.betting]


class OptimizeConditions:
    """조건 최적화 엔진 클래스입니다.
    다양한 조건 조합을 테스트하여 최적 조건을 찾습니다.
    """
    def __init__(self, sc, wq, bq, sq, tq, lq, beq_list, bstq_list, multi, backname, dict_set, market_infos):
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
        self.dict_set     = dict_set
        self.is_tick      = self.dict_set['타임프레임']
        self.market_gubun = market_infos[0]
        self.market_info  = market_infos[1]
        self.result       = {}
        self.opti_list    = []
        self.bcount       = None
        self.scount       = None
        self.buyconds     = None
        self.sellconds    = None
        self.optistandard = None
        self.savename     = f"{self.market_info['전략구분']}_{self.backname.replace('최적화', '').lower()}"

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
        """조건 최적화를 시작합니다."""
        start_time = now()
        data = self.bq.get()
        if self.market_gubun in (1, 2, 3, 5):
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

        if 'V' not in self.backname: weeks_valid = 0

        if weeks_train != 'ALL':
            weeks_train = int(weeks_train)
        else:
            weeks_train = int(((dt_ymd(backengin_eday) - dt_ymd(backengin_sday)).days + 1) / 7)

        dt_endday   = dt_ymd(backengin_eday)
        plus_day    = 3 if self.market_gubun not in (5, 9) else 1
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
        query = get_moneytop_query(self.is_tick, startday, endday, starttime, endtime)
        df_mt = pd.read_sql(query, con)
        con.close()

        if len(df_mt) == 0 or back_count == 0:
            self.wq.put((UI_NUM['백테스트'], '날짜 지정이 잘못되었거나 데이터가 존재하지 않습니다.'))
            self._sys_exit(True)

        con = sqlite3.connect(DB_STRATEGY)
        dfb = pd.read_sql(f"SELECT * FROM {self.market_info['전략구분']}_buyconds", con).set_index('index')
        dfs = pd.read_sql(f"SELECT * FROM {self.market_info['전략구분']}_sellconds", con).set_index('index')
        con.close()

        self.buyconds  = dfb['전략코드'][buystg_name].split('\n')
        self.sellconds = dfs['전략코드'][sellstg_name].split('\n')

        is_long = None
        if self.market_gubun > 5:
            if '#' in self.buyconds[0] and 'LONG' in self.buyconds[0] and '#' in self.sellconds[0] and 'LONG' in self.sellconds[0]:
                is_long = True
            elif '#' in self.buyconds[0] and 'SHORT' in self.buyconds[0] and '#' in self.sellconds[0] and 'SHORT' in self.sellconds[0]:
                is_long = False
            if is_long is None:
                self.wq.put((UI_NUM['백테스트'], '롱숏구분(#LONG 또는 #SHORT)이 없거나 매도수 구분이 다릅니다.\n'))
                self._sys_exit(True)

        if self.is_tick:
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

        self.buyconds  = [x for x in self.buyconds if x and x[0] != '#']
        self.sellconds = [x for x in self.sellconds if x and x[0] != '#']
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 매도수조건 설정 완료'))

        arry_bct = np.zeros((len(df_mt), 3), dtype='float64')
        arry_bct[:, 0] = df_mt['index'].values
        data = ('백테정보', self.market_gubun, None, valid_days, arry_bct, betting, len(day_list))
        for q in self.bstq_list:
            q.put(data)

        bc = factorial(len(self.buyconds)) / (factorial(self.bcount) * factorial(len(self.buyconds) - self.bcount))
        sc = factorial(len(self.sellconds)) / (factorial(self.scount) * factorial(len(self.sellconds) - self.scount))
        total_count = int(bc * sc)
        if total_count < rcount:
            rcount = total_count
        rcount = int(rcount / 20)
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 전체 경우의 수 계산 완료 [{total_count:,.0f}]'))

        data = ('백테정보', betting, avgtime, startday, endday, starttime, endtime)
        for q in self.beq_list:
            q.put(data)

        self.tq.put(('백테정보', betting, startday, endday, std_text, self.optistandard, valid_days))
        self.tq.put(('경우의수', back_count))

        mq = Queue()
        Process(target=Total, args=(self.wq, self.tq, mq, self.bstq_list, self.dict_set)).start()
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 집계용 프로세스 생성 완료'))

        self.wq.put((UI_NUM['백테스트'], f'{self.backname} START'))

        hstd = -float('inf')
        for i in range(rcount):
            buy_conds, sell_conds = self._get_cond_list()
            if len(buy_conds) == 20:
                self.wq.put((UI_NUM['백테스트'], f'{self.backname} 백테스트 [{i+1}/{rcount}]단계 시작, 최고 기준값[{hstd:,.2f}]'))
                self.shared_cnt.value = 0
                data = ('조건정보', is_long, buy_conds, sell_conds, 3)
                for q in self.bstq_list:
                    q.put(('백테시작', 3))
                for q in self.beq_list:
                    q.put(data)

                for _ in range(20):
                    data = mq.get()
                    if data.__class__ == str:
                        if self.result:
                            self._show_top_condlist(5, is_long)
                            self._show_top_conds()
                        self._sys_exit(True)
                    else:
                        _, vkey, std = data
                        if std > hstd: hstd = std
                        if std > 0: self.result[std] = [buy_conds[vkey], sell_conds[vkey]]
            else:
                break

        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 최적화 완료'))
        if self.result:
            self._show_top_condlist(5, is_long)
            self._show_top_conds()
        else:
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} 기준값 0을 초과하는 조합이 없습니다.'))

        if self.dict_set['스톰라이브']: self.lq.put(self.backname)
        self.sq.put('조건 최적화가 완료되었습니다.')
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 백테스트 소요시간 {now() - start_time}'))
        self._sys_exit(False)

    def _get_cond_list(self):
        """조건 리스트를 생성합니다.
        Returns:
            (buyconds, sellconds) 튜플
        """
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

    def _show_top_condlist(self, rank, is_long):
        """상위 조건 리스트를 표시합니다.
        Args:
            rank: 랭크
            is_long: 롱 여부
        """
        rs_list = sorted(self.result.items(), key=lambda x: x[0], reverse=True)
        for key, value in rs_list[:rank]:
            if self.market_gubun > 5:
                if is_long:
                    buyconds = 'if not (' + \
                               '):\n    BUY_LONG = False\nelif not ('.join(value[0]) + \
                               '):\n    BUY_LONG = False'
                    sellconds = 'if ' + \
                                ':\n    SELL_LONG = True\nelif '.join(value[1]) + \
                                ':\n    SELL_LONG = True'
                else:
                    buyconds = 'if not (' + \
                               '):\n    SELL_SHORT = False\nelif not ('.join(value[0]) + \
                               '):\n    SELL_SHORT = False'
                    sellconds = 'if ' + \
                                ':\n    BUY_SHORT = True\nelif '.join(value[1]) + \
                                ':\n    BUY_SHORT = True'
            else:
                buyconds  = 'if not (' + '):\n    매수 = False\nelif not ('.join(value[0]) + '):\n    매수 = False'
                sellconds = 'if ' + ':\n    매도 = True\nelif '.join(value[1]) + ':\n    매도 = True'

            self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 - {self.optistandard}[{key:,.2f}]\n'))
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 - 매수조건\n{buyconds}\n'))
            self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 - 매도조건\n{sellconds}\n'))
            data = [[self.optistandard, key, buyconds, sellconds]]
            df = pd.DataFrame(data, columns=['기준', '기준값', '매수코드', '매도코드'], index=[str_ymdhms()])
            con = sqlite3.connect(DB_BACKTEST)
            df.to_sql(self.savename, con, if_exists='append', chunksize=2000)
            con.close()

    def _show_top_conds(self):
        """상위 조건을 표시합니다."""
        buy_conds_freq  = {}
        sell_conds_freq = {}

        opti_dict = dict(sorted(self.result.items(), key=lambda x: x[0], reverse=True))
        for key, value in opti_dict.items():
            for cond in value[0]:
                if cond in buy_conds_freq:
                    buy_conds_freq[cond] += 1
                else:
                    buy_conds_freq[cond] = 1
            for cond in value[1]:
                if cond in sell_conds_freq:
                    sell_conds_freq[cond] += 1
                else:
                    sell_conds_freq[cond] = 1

        buy_conds_freq  = sorted(buy_conds_freq.items(), key=lambda x: x[1], reverse=True)
        sell_conds_freq = sorted(sell_conds_freq.items(), key=lambda x: x[1], reverse=True)

        text = '조건회적화 결과 - 매수조건 출현빈도\n'
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 - 매수조건 출현빈도'))
        for key, value in buy_conds_freq:
            text += f'[{value}] {key}\n'
            self.wq.put((UI_NUM['백테스트'], f'[{value}] {key}'))

        text += '\n조건회적화 결과 - 매도조건 출현빈도\n'
        self.wq.put((UI_NUM['백테스트'], f'{self.backname} 결과 - 매도조건 출현빈도'))
        for key, value in sell_conds_freq:
            text += f'[{value}] {key}\n'
            self.wq.put((UI_NUM['백테스트'], f'[{value}] {key}'))

        df = pd.DataFrame({'조건별출현빈도': [text]}, index=[str_ymdhms()])
        con = sqlite3.connect(DB_BACKTEST)
        df.to_sql(f'{self.savename}_conds', con, if_exists='append', chunksize=2000)
        con.close()

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
