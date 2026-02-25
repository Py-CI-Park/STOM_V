import os
import sys
import math
import time
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DB_STRATEGY, DICT_SET, ui_num, dict_order_ratio, indicator, DB_FUTURE_MIN, dgree, DB_FUTURE_TICK
from utility.static import now, now_cme, get_buy_indi_stg, GetFutureLongPgSgSp, GetFutureShortPgSgSp, dt_ymdhms, \
    get_logger
from utility.safe_exec import safe_compile, guard_exec_code, UnsafeStrategyCodeError


# noinspection PyUnusedLocal
class FutureStrategyTick:
    def __init__(self, qlist):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ
                0            1             2            3
        """
        self.mgzservQ         = qlist[0]
        self.straderQ         = qlist[2]
        self.sstgQ            = qlist[3]
        self.dict_set         = DICT_SET
        self.logger           = get_logger(self.__class__.__name__)

        self.buystrategy      = None
        self.sellstrategy     = None
        self.chart_code       = None

        self.vars             = {}
        self.dict_arry        = {}
        self.dict_signal_num  = {}
        self.dict_buy_num     = {}
        self.dict_condition   = {}
        self.dict_cond_indexn = {}
        self.bhogainfo        = {}
        self.shogainfo        = {}
        self.dict_hilo        = {}
        self.dict_gj          = {}
        self.dict_jg          = {}
        self.dict_info        = {}
        self.indicator        = indicator
        self.dict_signal      = {'BUY_LONG': [], 'SELL_SHORT': [], 'SELL_LONG': [], 'BUY_SHORT': []}

        self.indexn           = 0
        self.indexb           = 0
        self.jgrv_count       = 0

        if self.dict_set['전략연산프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

        self.UpdateStringategy()
        self.Mainloop()

    def UpdateStringategy(self):
        con  = sqlite3.connect(DB_STRATEGY)
        dfb  = pd.read_sql('SELECT * FROM futurebuy', con).set_index('index')
        dfs  = pd.read_sql('SELECT * FROM futuresell', con).set_index('index')
        dfob = pd.read_sql('SELECT * FROM futureoptibuy', con).set_index('index')
        dfos = pd.read_sql('SELECT * FROM futureoptisell', con).set_index('index')
        con.close()

        buytxt = ''
        if self.dict_set['주식매수전략'] in dfb.index:
            buytxt = dfb['전략코드'][self.dict_set['주식매수전략']]
        elif self.dict_set['주식매수전략'] in dfob.index:
            buytxt = dfob['전략코드'][self.dict_set['주식매수전략']]
            vars_text = dfob['변수값'][self.dict_set['주식매수전략']]
            if vars_text != '':
                vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                self.vars = {i: var for i, var in enumerate(vars_list)}

        self.SetBuyStg(buytxt)

        try:
            if self.dict_set['주식매도전략'] in dfs.index:
                self.sellstrategy = safe_compile(dfs['전략코드'][self.dict_set['주식매도전략']], '<string>', 'exec',
                                                 context='FutureStrategyTick.sellstrategy.db')
            elif self.dict_set['주식매도전략'] in dfos.index:
                self.sellstrategy = safe_compile(dfos['전략코드'][self.dict_set['주식매도전략']], '<string>', 'exec',
                                                 context='FutureStrategyTick.sellstrategy.opti')
        except (UnsafeStrategyCodeError, SyntaxError, ValueError) as e:
            self.sellstrategy = None
            self.ReportCompileError('매도전략', e)

        if self.dict_set['주식경과틱수설정']:
            def compile_condition(x):
                return safe_compile(
                    f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn',
                    '<string>', 'exec', context='FutureStrategyTick.condition'
                )
            text_list  = self.dict_set['주식경과틱수설정'].split(';')
            half_cnt   = int(len(text_list) / 2)
            key_list   = text_list[:half_cnt]
            value_list = text_list[half_cnt:]
            try:
                value_list = [compile_condition(x) for x in value_list]
                self.dict_condition = dict(zip(key_list, value_list))
            except (UnsafeStrategyCodeError, SyntaxError, ValueError) as e:
                self.dict_condition = {}
                self.ReportCompileError('경과틱수 조건', e)

    def SetBuyStg(self, buytxt):
        self.buystrategy, indistg = get_buy_indi_stg(buytxt)
        if indistg is not None:
            try:
                exec(guard_exec_code(indistg, 'FutureStrategyTick.SetBuyStg.indistg'))
            except:
                pass
            else:
                self.logger.info(self.indicator)

    def ReportCompileError(self, part, err):
        self.logger.error(f'{part} 컴파일 실패 - {err}')
        self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'시스템 명령 오류 알림 - {part} 컴파일 실패')))

    def Mainloop(self):
        self.mgzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 전략연산 시작')))
        self.logger.info('전략연산 시작 완료')
        while True:
            data = self.sstgQ.get()
            if type(data) == tuple:
                if len(data) != 2:
                    self.Strategy(data)
                else:
                    self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.dict_jg = data
            self.jgrv_count += 1
            if self.jgrv_count == 2:
                self.jgrv_count = 0
                self.PutGsjmAndDeleteHilo()
        elif '_COMPLETE' in gubun:
            gubun = gubun.replace('_COMPLETE', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
            if gubun in ('BUY_LONG', 'SELL_SHORT'):
                self.dict_buy_num[data] = self.dict_signal_num.get(data, len(self.dict_arry[data]) - 1)
        elif '_CANCEL' in gubun:
            gubun = gubun.replace('_CANCEL', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
        elif '_MANUAL' in gubun:
            gubun = gubun.replace('_MANUAL', '')
            if data not in self.dict_signal[gubun]:
                self.dict_signal[gubun].append(data)
        elif gubun == '매수전략':
            self.SetBuyStg(data)
        elif gubun == '매도전략':
            try:
                self.sellstrategy = safe_compile(
                    data,
                    '<string>',
                    'exec',
                    context='FutureStrategyTick.sellstrategy.update'
                )
            except (UnsafeStrategyCodeError, SyntaxError, ValueError) as e:
                self.sellstrategy = None
                self.ReportCompileError('매도전략', e)
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
            self.UpdateStringategy()
        elif gubun == '종목정보':
            self.dict_info = data
        elif data == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')

    def UpdateString(self, data):
        if data == '매수전략중지':
            self.buystrategy = None
            self.mgzservQ.put(('tele', '해선 매수전략 중지 완료'))
        elif data == '매도전략중지':
            self.sellstrategy = None
            self.mgzservQ.put(('tele', '해선 매도전략 중지 완료'))
        elif data == '프로세스종료':
            self.SysExit()

    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도수5호가잔량합, 관심종목, 종목코드, 종목명, 틱수신시간 = data

        def Parameter_Previous(aindex, pre):
            if pre < 데이터길이:
                pindex = (self.indexn - pre) if pre != -1 else self.indexb
                return self.dict_arry[종목코드][pindex, aindex]
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

        def 초당매수수량N(pre):
            return Parameter_Previous(8, pre)

        def 초당매도수량N(pre):
            return Parameter_Previous(9, pre)

        def 초당거래대금N(pre):
            return Parameter_Previous(10, pre)

        def 고저평균대비등락율N(pre):
            return Parameter_Previous(11, pre)

        def 매도총잔량N(pre):
            return Parameter_Previous(12, pre)

        def 매수총잔량N(pre):
            return Parameter_Previous(13, pre)

        def 매도호가5N(pre):
            return Parameter_Previous(14, pre)

        def 매도호가4N(pre):
            return Parameter_Previous(15, pre)

        def 매도호가3N(pre):
            return Parameter_Previous(16, pre)

        def 매도호가2N(pre):
            return Parameter_Previous(17, pre)

        def 매도호가1N(pre):
            return Parameter_Previous(18, pre)

        def 매수호가1N(pre):
            return Parameter_Previous(19, pre)

        def 매수호가2N(pre):
            return Parameter_Previous(20, pre)

        def 매수호가3N(pre):
            return Parameter_Previous(21, pre)

        def 매수호가4N(pre):
            return Parameter_Previous(22, pre)

        def 매수호가5N(pre):
            return Parameter_Previous(23, pre)

        def 매도잔량5N(pre):
            return Parameter_Previous(24, pre)

        def 매도잔량4N(pre):
            return Parameter_Previous(25, pre)

        def 매도잔량3N(pre):
            return Parameter_Previous(26, pre)

        def 매도잔량2N(pre):
            return Parameter_Previous(27, pre)

        def 매도잔량1N(pre):
            return Parameter_Previous(28, pre)

        def 매수잔량1N(pre):
            return Parameter_Previous(29, pre)

        def 매수잔량2N(pre):
            return Parameter_Previous(30, pre)

        def 매수잔량3N(pre):
            return Parameter_Previous(31, pre)

        def 매수잔량4N(pre):
            return Parameter_Previous(32, pre)

        def 매수잔량5N(pre):
            return Parameter_Previous(33, pre)

        def 매도수5호가잔량합N(pre):
            return Parameter_Previous(34, pre)

        def 관심종목N(pre):
            return Parameter_Previous(35, pre)

        def 이동평균(tick, pre=0):
            if tick == 60:
                return Parameter_Previous(36, pre)
            elif tick == 300:
                return Parameter_Previous(37, pre)
            elif tick == 600:
                return Parameter_Previous(38, pre)
            elif tick == 1200:
                return Parameter_Previous(39, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    return round(self.dict_arry[종목코드][sindex:eindex, 1].mean(), 8)
                return 0

        def Parameter_Area(aindex, vindex, tick, pre, gubun_):
            if tick == 평균값계산틱수:
                return Parameter_Previous(aindex, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn + 1 - pre - tick) if pre != -1  else self.indexb + 1 - tick
                    eindex = (self.indexn + 1 - pre) if pre != -1  else self.indexb + 1
                    if gubun_ == 'max':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].max()
                    elif gubun_ == 'min':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].min()
                    elif gubun_ == 'sum':
                        return self.dict_arry[종목코드][sindex:eindex, vindex].sum()
                    else:
                        return self.dict_arry[종목코드][sindex:eindex, vindex].mean()
                return 0

        def 최고현재가(tick, pre=0):
            return Parameter_Area(40, 1, tick, pre, 'max')

        def 최저현재가(tick, pre=0):
            return Parameter_Area(41, 1, tick, pre, 'min')

        def 체결강도평균(tick, pre=0):
            return round(Parameter_Area(42, 7, tick, pre, 'mean'), 3)

        def 최고체결강도(tick, pre=0):
            return Parameter_Area(43, 7, tick, pre, 'max')

        def 최저체결강도(tick, pre=0):
            return Parameter_Area(44, 7, tick, pre, 'min')

        def 최고초당매수수량(tick, pre=0):
            return Parameter_Area(45, 8, tick, pre, 'max')

        def 최고초당매도수량(tick, pre=0):
            return Parameter_Area(46, 9, tick, pre, 'max')

        def 누적초당매수수량(tick, pre=0):
            return Parameter_Area(47, 8, tick, pre, 'sum')

        def 누적초당매도수량(tick, pre=0):
            return Parameter_Area(48, 9, tick, pre, 'sum')

        def 초당거래대금평균(tick, pre=0):
            return int(Parameter_Area(49, 10, tick, pre, 'mean'))

        def Parameter_Dgree(aindex, vindex, tick, pre, cf):
            if tick == 평균값계산틱수:
                return Parameter_Previous(aindex, pre)
            else:
                if tick + pre <= 데이터길이:
                    sindex = (self.indexn - pre - tick + 1) if pre != -1  else self.indexb - tick + 1
                    eindex = (self.indexn - pre) if pre != -1  else self.indexb
                    dmp_gap = self.dict_arry[종목코드][eindex, vindex] - self.dict_arry[종목코드][sindex, vindex]
                    return round(math.atan2(dmp_gap * cf, tick) / (2 * math.pi) * 360, 2)
                return 0

        def 등락율각도(tick, pre=0):
            return Parameter_Dgree(50, 5, tick, pre, dgree['future']['tick'][0])

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(51, 6, tick, pre, dgree['future']['tick'][1])

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn and \
                    조건명 in self.dict_cond_indexn[종목코드] and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        시분초, 호가단위 = int(str(체결시간)[8:]), self.dict_info[종목코드]['호가단위']
        데이터길이 = len(self.dict_arry[종목코드]) + 1 if 종목코드 in self.dict_arry else 1
        평균값계산틱수 = self.dict_set['주식평균값계산틱수']
        이동평균0060, 이동평균0300, 이동평균0600, 이동평균1200, 최고현재가_, 최저현재가_ = 0., 0., 0., 0., 0, 0
        체결강도평균_, 최고체결강도_, 최저체결강도_, 최고초당매수수량_, 최고초당매도수량_ = 0., 0., 0., 0, 0
        누적초당매수수량_, 누적초당매도수량_, 초당거래대금평균_, 등락율각도_, 당일거래대금각도_, 전일비각도_ = 0, 0, 0., 0., 0., 0.

        self.bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        self.shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))

        if 종목코드 in self.dict_arry:
            len_array = len(self.dict_arry[종목코드])
            if len_array >=   59: 이동평균0060 = round((self.dict_arry[종목코드][  -59:, 1].sum() + 현재가) /   60, 8)
            if len_array >=  299: 이동평균0300 = round((self.dict_arry[종목코드][ -299:, 1].sum() + 현재가) /  300, 8)
            if len_array >=  599: 이동평균0600 = round((self.dict_arry[종목코드][ -599:, 1].sum() + 현재가) /  600, 8)
            if len_array >= 1199: 이동평균1200 = round((self.dict_arry[종목코드][-1199:, 1].sum() + 현재가) / 1200, 8)
            if len_array >= 평균값계산틱수 - 1:
                최고현재가_      = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 1].max(), 현재가)
                최저현재가_      = min(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 1].min(), 현재가)
                체결강도평균_    = round((self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].sum() + 체결강도) / 평균값계산틱수, 3)
                최고체결강도_    = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].max(), 체결강도)
                최저체결강도_    = min(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 7].min(), 체결강도)
                최고초당매수수량_ = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 8].max(), 초당매수수량)
                최고초당매도수량_ = max(self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 9].max(), 초당매도수량)
                누적초당매수수량_ =     self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 8].sum() + 초당매수수량
                누적초당매도수량_ =     self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 9].sum() + 초당매도수량
                초당거래대금평균_ = int((self.dict_arry[종목코드][-(평균값계산틱수 - 1):, 10].sum() + 초당거래대금) / 평균값계산틱수)
                등락율각도_      = round(math.atan2((등락율 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 5]) * dgree['future']['tick'][0], 평균값계산틱수) / (2 * math.pi) * 360, 2)
                당일거래대금각도_ = round(math.atan2((당일거래대금 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 6]) * dgree['future']['tick'][1], 평균값계산틱수) / (2 * math.pi) * 360, 2)

            """
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율,
               0      1     2    3     4     5        6         7         8           9          10            11
            매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
               12        13        14       15       16        17       18        19       20       21        22       23
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목,
               24        25       26       27        28       29        30       31       32        33         34           35
            이동평균0060, 이동평균0300, 이동평균0600, 이동평균1200, 최고현재가_, 최저현재가_, 체결강도평균_, 최고체결강도_, 최저체결강도_,
                36         37           38          39          40         51          42           43          44
            최고초당매수수량_, 최고초당매도수량_, 누적초당매수수량_, 누적초당매도수량_, 초당거래대금평균_, 등락율각도_, 당일거래대금각도_
                   45            46              47              48              49           50           51
            """

        new_data_tick = [
            체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금,
            고저평균대비등락율, 매도총잔량, 매수총잔량, 매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2,
            매수호가3, 매수호가4, 매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3,
            매수잔량4, 매수잔량5, 매도수5호가잔량합, 관심종목, 이동평균0060, 이동평균0300, 이동평균0600, 이동평균1200, 최고현재가_,
            최저현재가_, 체결강도평균_, 최고체결강도_, 최저체결강도_, 최고초당매수수량_, 최고초당매도수량_, 누적초당매수수량_,
            누적초당매도수량_, 초당거래대금평균_, 등락율각도_, 당일거래대금각도_
        ]

        if 종목코드 not in self.dict_arry:
            self.dict_arry[종목코드] = np.array([new_data_tick])
        else:
            self.dict_arry[종목코드] = np.r_[self.dict_arry[종목코드], np.array([new_data_tick])]

        데이터길이 = len(self.dict_arry[종목코드])
        self.indexn = 데이터길이 - 1

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn:
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                try:
                    exec(guard_exec_code(v, f'FutureStrategyTick.condition.{k}'))
                except:
                    print_exc()
                    self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - 경과틱수 연산오류')))

        if 체결강도평균_ != 0:
            if 종목코드 in self.dict_jg:
                if 종목코드 not in self.dict_buy_num:
                    self.dict_buy_num[종목코드] = self.indexn
                # ['종목명', '포지션', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량', '분할매수횟수', '분할매도횟수', '매수시간']
                _, 포지션, 매입가, _, _, _, 매입금액, _, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간 = self.dict_jg[종목코드].values()
                평가금액 = 매입금액 + (현재가 - 매입가) * self.dict_info[종목코드]['틱가치'] * 보유수량
                if 포지션 == 'LONG':
                    _, 수익금, 수익률 = GetFutureLongPgSgSp(매입금액, 평가금액, 종목코드)
                else:
                    _, 수익금, 수익률 = GetFutureShortPgSgSp(매입금액, 평가금액, 종목코드)
                if 종목코드 not in self.dict_hilo:
                    self.dict_hilo[종목코드] = [수익률, 수익률]
                else:
                    if 수익률 > self.dict_hilo[종목코드][0]:
                        self.dict_hilo[종목코드][0] = 수익률
                    elif 수익률 < self.dict_hilo[종목코드][1]:
                        self.dict_hilo[종목코드][1] = 수익률
                최고수익률, 최저수익률 = self.dict_hilo[종목코드]
                보유시간 = (now_cme() - dt_ymdhms(매수시간)).total_seconds()
                매수틱번호 = self.dict_buy_num[종목코드]
            else:
                포지션, 매수틱번호, 수익금, 수익률, 매입가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = None, 0, 0, 0, 0, 0, 0, 0, now_cme(), 0, 0, 0
            self.indexb = 매수틱번호

            BBT  = not self.dict_set['주식매수금지시간'] or not (self.dict_set['주식매수금지시작시간'] < 시분초 < self.dict_set['주식매수금지종료시간'])
            BLK  = not self.dict_set['주식매수금지블랙리스트'] or 종목코드 not in self.dict_set['해선블랙리스트']
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
            NISL = 종목코드 not in self.dict_signal['SELL_LONG']
            NIBS = 종목코드 not in self.dict_signal['BUY_SHORT']
            A    = NIBL and 포지션 is None
            B    = NISS and 포지션 is None
            C    = self.dict_set['주식매수분할시그널']
            D    = NIBL and 포지션 == 'LONG' and 분할매수횟수 < self.dict_set['주식매수분할횟수']
            E    = NISS and 포지션 == 'SHORT' and 분할매수횟수 < self.dict_set['주식매수분할횟수']
            F    = NIBL and self.dict_set['주식매도취소매수시그널'] and not NISL
            G    = NISS and self.dict_set['주식매도취소매수시그널'] and not NIBS

            if BBT and BLK and (A or B or (C and D) or (C and E) or D or E or F or G):
                매수수량 = 0
                if not (F or G):
                    매수수량 = self.SetBuyCount(분할매수횟수, 매입가, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30))

                if A or B or (C and (D or E)) or F or G:
                    BUY_LONG, SELL_SHORT = True, True
                    if self.buystrategy is not None:
                        try:
                            exec(guard_exec_code(self.buystrategy, 'FutureStrategyTick.buystrategy'))
                        except:
                            print_exc()
                            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - BuyStrategy')))
                elif D or E:
                    BUY_LONG, SELL_SHORT = False, False
                    분할매수기준수익률 = round((현재가 / 현재가N(-1) - 1) * 100, 2) if self.dict_set['주식매수분할고정수익률'] else 수익률
                    if D:
                        if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                            BUY_LONG   = True
                        elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                            BUY_LONG   = True
                    elif E:
                        if self.dict_set['주식매수분할하방'] and 분할매수기준수익률 < -self.dict_set['주식매수분할하방수익률']:
                            SELL_SHORT = True
                        elif self.dict_set['주식매수분할상방'] and 분할매수기준수익률 > self.dict_set['주식매수분할상방수익률']:
                            SELL_SHORT = True

                    if BUY_LONG or SELL_SHORT:
                        self.Buy(종목코드, 종목명, BUY_LONG, 현재가, 매도호가1, 매수호가1, 매수수량, 데이터길이)

            SBT  = not self.dict_set['주식매도금지시간'] or not (self.dict_set['주식매도금지시작시간'] < 시분초 < self.dict_set['주식매도금지종료시간'])
            SCC  = self.dict_set['주식매수분할횟수'] == 1 or not self.dict_set['주식매도금지매수횟수'] or 분할매수횟수 > self.dict_set['주식매도금지매수횟수값']
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
            GJCS = 수익금 / self.dict_info[종목코드]['위탁증거금'] * 100 <= -30

            A    = NIBL and NISL and SCC and 포지션 == 'LONG' and self.dict_set['주식매도분할횟수'] == 1
            B    = NISS and NIBS and SCC and 포지션 == 'SHORT' and self.dict_set['주식매도분할횟수'] == 1
            C    = self.dict_set['주식매도분할시그널']
            D    = NIBL and NISL and SCC and 포지션 == 'LONG' and 분할매도횟수 < self.dict_set['주식매도분할횟수']
            E    = NISS and NIBS and SCC and 포지션 == 'SHORT' and 분할매도횟수 < self.dict_set['주식매도분할횟수']
            F    = NISL and self.dict_set['주식매수취소매도시그널'] and not NIBL
            G    = NIBS and self.dict_set['주식매수취소매도시그널'] and not NISS
            H    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
            J    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['주식매도손절수익률청산'] and 수익률 < -self.dict_set['주식매도손절수익률']
            K    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']
            L    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['주식매도손절수익금청산'] and 수익금 < -self.dict_set['주식매도손절수익금']
            M    = NIBL and NISL and 포지션 == 'LONG' and GJCS
            N    = NISS and NIBS and 포지션 == 'SHORT' and GJCS

            if SBT and (A or B or (C and D) or (C and E) or D or E or F or G or H or J or K or L or M or N):
                SELL_LONG, BUY_SHORT = False, False
                매도수량 = 0
                강제청산 = H or J or K or L or M or N

                if A or B or 강제청산:
                    매도수량 = 보유수량
                elif not (F or G):
                    매도수량 = self.SetSellCount(분할매도횟수, 보유수량, 매입가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30))

                if A or B or (C and (D or E)) or F or G:
                    if self.sellstrategy is not None:
                        try:
                            exec(guard_exec_code(self.sellstrategy, 'FutureStrategyTick.sellstrategy'))
                        except:
                            print_exc()
                            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 오류 알림 - SellStrategy')))
                elif D or E or 강제청산:
                    if H or K or M:
                        SELL_LONG = True
                    elif J or L or N:
                        BUY_SHORT = True
                    elif D:
                        if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                        elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                    elif E:
                        if self.dict_set['주식매도분할하방'] and 수익률 < -self.dict_set['주식매도분할하방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True
                        elif self.dict_set['주식매도분할상방'] and 수익률 > self.dict_set['주식매도분할상방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True

                    if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):
                        self.Sell(종목코드, 종목명, SELL_LONG, 현재가, 매도호가1, 매수호가1, 매도수량, 강제청산)

        if 관심종목:
            # ['종목명', 'per', 'hlp', 'sm', 'sma', 'dm', 'ch', 'cha', 'chh']
            self.dict_gj[종목코드] = {
                '종목명': 종목명,
                'per': 등락율,
                'hlp': 고저평균대비등락율,
                'sm': 초당거래대금,
                'sma': 초당거래대금평균_,
                'dm': 당일거래대금,
                'ch': 체결강도,
                'cha': 체결강도평균_,
                'chh': 최고체결강도_
            }

        if 데이터길이 >= 평균값계산틱수 and self.chart_code == 종목코드:
            self.mgzservQ.put(('window', (ui_num['실시간차트'], 종목명, self.dict_arry[종목코드])))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))

    def SetBuyCount(self, 분할매수횟수, 매입가, 현재가, 고가, 저가, 등락율각도, 당일거래대금각도):
        if self.dict_set['주식비중조절'][0] == 0:
            betting = self.dict_set['주식투자금']
        else:
            if self.dict_set['주식비중조절'][0] == 1:
                비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
            elif self.dict_set['주식비중조절'][0] == 2:
                비중조절기준 = 등락율각도
            else:
                비중조절기준 = 당일거래대금각도

            if 비중조절기준 < self.dict_set['주식비중조절'][1]:
                betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][5]
            elif 비중조절기준 < self.dict_set['주식비중조절'][2]:
                betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][6]
            elif 비중조절기준 < self.dict_set['주식비중조절'][3]:
                betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][7]
            elif 비중조절기준 < self.dict_set['주식비중조절'][4]:
                betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][8]
            else:
                betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][9]

        oc_ratio = dict_order_ratio[self.dict_set['주식매수분할방법']][self.dict_set['주식매수분할횟수']][분할매수횟수]
        매수수량 = int(betting * oc_ratio / 100)
        return 매수수량

    def SetSellCount(self, 분할매도횟수, 보유수량, 매입가, 고가, 저가, 등락율각도, 당일거래대금각도):
        if self.dict_set['주식매도분할횟수'] == 1:
            return 보유수량
        else:
            if self.dict_set['주식비중조절'][0] == 0:
                betting = self.dict_set['주식투자금']
            else:
                if self.dict_set['주식비중조절'][0] == 1:
                    비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
                elif self.dict_set['주식비중조절'][0] == 2:
                    비중조절기준 = 등락율각도
                else:
                    비중조절기준 = 당일거래대금각도

                if 비중조절기준 < self.dict_set['주식비중조절'][1]:
                    betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][5]
                elif 비중조절기준 < self.dict_set['주식비중조절'][2]:
                    betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][6]
                elif 비중조절기준 < self.dict_set['주식비중조절'][3]:
                    betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][7]
                elif 비중조절기준 < self.dict_set['주식비중조절'][4]:
                    betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][8]
                else:
                    betting = self.dict_set['주식투자금'] * self.dict_set['주식비중조절'][9]

            oc_ratio = dict_order_ratio[self.dict_set['주식매도분할방법']][self.dict_set['주식매도분할횟수']][분할매도횟수]
            매도수량 = int(betting * oc_ratio / 100)
            if 매도수량 > 보유수량 or 분할매도횟수 + 1 == self.dict_set['주식매도분할횟수']: 매도수량 = 보유수량
            return 매도수량

    def Buy(self, 종목코드, 종목명, BUY_LONG, 현재가, 매도호가1, 매수호가1, 매수수량, 데이터길이):
        구분 = 'BUY_LONG' if BUY_LONG else 'SELL_SHORT'
        if '지정가' in self.dict_set['주식매수주문구분']:
            기준가격 = 현재가
            if self.dict_set['주식매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if BUY_LONG else 매수호가1
            if self.dict_set['주식매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if BUY_LONG else 매도호가1
            self.dict_signal[구분].append(종목코드)
            self.dict_signal_num[종목코드] = 데이터길이 - 1
            self.straderQ.put((구분, 종목코드, 종목명, 기준가격, 매수수량, now(), False))
        else:
            매수금액 = 0
            미체결수량 = 매수수량
            hogainfo = self.bhogainfo if BUY_LONG else self.shogainfo
            hogainfo = hogainfo[:self.dict_set['주식매수시장가잔량범위']]
            for 호가, 잔량 in hogainfo:
                if 미체결수량 - 잔량 <= 0:
                    매수금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매수금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                예상체결가 = round(매수금액 / 매수수량, self.dict_info[종목코드]['소숫점자리수']) if 매수수량 != 0 else 0
                self.dict_signal[구분].append(종목코드)
                self.dict_signal_num[종목코드] = 데이터길이 - 1
                self.straderQ.put((구분, 종목코드, 종목명, 예상체결가, 매수수량, now(), False))

    def Sell(self, 종목코드, 종목명, SELL_LONG, 현재가, 매도호가1, 매수호가1, 매도수량, 강제청산):
        구분 = 'SELL_LONG' if SELL_LONG else 'BUY_SHORT'
        if '지정가' in self.dict_set['주식매도주문구분'] and not 강제청산:
            기준가격 = 현재가
            if self.dict_set['주식매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if 구분 == 'SELL_LONG' else 매수호가1
            if self.dict_set['주식매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if 구분 == 'SELL_LONG' else 매도호가1
            self.dict_signal[구분].append(종목코드)
            self.straderQ.put((구분, 종목코드, 종목명, 기준가격, 매도수량, now(), False))
        else:
            매도금액 = 0
            미체결수량 = 매도수량
            hogainfo = self.shogainfo if 구분 == 'SELL_LONG' else self.bhogainfo
            hogainfo = hogainfo[:self.dict_set['주식매도시장가잔량범위']]
            for 호가, 잔량 in hogainfo:
                if 미체결수량 - 잔량 <= 0:
                    매도금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매도금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                예상체결가 = round(매도금액 / 매도수량, self.dict_info[종목코드]['소숫점자리수']) if 매도수량 != 0 else 0
                self.dict_signal[구분].append(종목코드)
                self.straderQ.put((구분, 종목코드, 종목명, 예상체결가, 매도수량, now(), True if 강제청산 else False))

    def PutGsjmAndDeleteHilo(self):
        if self.dict_gj:
            self.dict_gj = dict(sorted(self.dict_gj.items(), key=lambda x: x[1]['dm'], reverse=True))
            df_gj = pd.DataFrame.from_dict(self.dict_gj, orient='index')
            self.mgzservQ.put(('window', (ui_num[f'S관심종목'], df_gj)))
        if self.dict_hilo:
            self.dict_hilo = {k: v for k, v in self.dict_hilo.copy().items() if k in self.dict_jg}

    def SysExit(self):
        if self.dict_set['주식데이터저장']:
            self.SaveData()
        time.sleep(5)
        self.mgzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 전략연산 종료')))

    def SaveData(self):
        if self.dict_set['주식타임프레임']:
            columns_ts = [
                'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
                '초당거래대금', '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5', '매도호가4', '매도호가3', '매도호가2',
                '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5', '매도잔량5', '매도잔량4', '매도잔량3',
                '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5', '매도수5호가잔량합', '관심종목'
            ]
        else:
            columns_ts = [
                'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
                '분봉시가', '분봉고가', '분봉저가', '분당거래대금', '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5',
                '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
                '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4',
                '매수잔량5', '매도수5호가잔량합', '관심종목'
            ]

        last = len(self.dict_arry)
        con = sqlite3.connect(DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN)
        if last > 0:
            start = now()
            cllen = len(columns_ts)
            for i, code in enumerate(self.dict_arry):
                df = pd.DataFrame(self.dict_arry[code][:, :cllen], columns=columns_ts)
                df['index'] = df['index'].astype('int64')
                df.set_index('index', inplace=True)
                df.to_sql(code, con, if_exists='append', chunksize=1000)
                text = f'시스템 명령 실행 알림 - 전략연산 프로세스 데이터 저장 중 ... {i + 1}/{last}'
                self.mgzservQ.put(('window', (ui_num['S단순텍스트'], text)))
            save_time = (now() - start).total_seconds()
            text = f'시스템 명령 실행 알림 - 데이터 저장 쓰기소요시간은 [{save_time:.6f}]초입니다.'
            self.mgzservQ.put(('window', (ui_num['S단순텍스트'], text)))
        con.close()

        self.logger.info('데이터 저장 완료')
