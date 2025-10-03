import math
import time
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from utility.setting import DB_STRATEGY, DICT_SET, ui_num, columns_jgf, columns_gj, dict_order_ratio, DB_COIN_TICK, \
    DB_COIN_MIN, indicator
# noinspection PyUnresolvedReferences
from utility.static import now, now_utc, strp_time, int_hms_utc, timedelta_sec, GetBinanceShortPgSgSp, \
    GetBinanceLongPgSgSp, get_buy_indi_stg


# noinspection PyUnusedLocal
class BinanceStrategyTick:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ          = qlist[0]
        self.ctraderQ         = qlist[9]
        self.cstgQ            = qlist[10]
        self.dict_set         = DICT_SET

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
        self.indicator        = indicator
        self.dict_info        = {}
        self.dict_signal      = {'BUY_LONG': [], 'SELL_SHORT': [], 'SELL_LONG': [], 'BUY_SHORT': []}

        self.indexn           = 0
        self.indexb           = 0
        self.jgrv_count       = 0
        self.int_tujagm       = 0
        self.df_gj            = pd.DataFrame(columns=columns_gj)
        self.df_jg            = pd.DataFrame(columns=columns_jgf)

        self.UpdateStringategy()
        self.MainLoop()

    def UpdateStringategy(self):
        con  = sqlite3.connect(DB_STRATEGY)
        dfb  = pd.read_sql('SELECT * FROM coinbuy', con).set_index('index')
        dfs  = pd.read_sql('SELECT * FROM coinsell', con).set_index('index')
        dfob = pd.read_sql('SELECT * FROM coinoptibuy', con).set_index('index')
        dfos = pd.read_sql('SELECT * FROM coinoptisell', con).set_index('index')
        try:
            dfid = pd.read_sql(f"SELECT * FROM coinindi_{self.dict_set['코인매수전략']}", con).set_index('index')
        except:
            dfid = None
        con.close()

        buytxt = ''
        if self.dict_set['코인매수전략'] in dfb.index:
            buytxt = dfb['전략코드'][self.dict_set['코인매수전략']]
        elif self.dict_set['코인매수전략'] in dfob.index:
            buytxt = dfob['전략코드'][self.dict_set['코인매수전략']]
            vars_text = dfob['변수값'][self.dict_set['코인매수전략']]
            if vars_text != '':
                vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                self.vars = {i: var for i, var in enumerate(vars_list)}

        self.SetBuyStg(buytxt)

        if self.dict_set['코인매도전략'] in dfs.index:
            self.sellstrategy = compile(dfs['전략코드'][self.dict_set['코인매도전략']], '<string>', 'exec')
        elif self.dict_set['코인매도전략'] in dfos.index:
            self.sellstrategy = compile(dfos['전략코드'][self.dict_set['코인매도전략']], '<string>', 'exec')

        if self.dict_set['코인경과틱수설정'] != '':
            def compile_condition(x):
                return compile(f'if {x}:\n    self.dict_cond_indexn[종목코드][k] = self.indexn', '<string>', 'exec')
            text_list = self.dict_set['코인경과틱수설정'].split(';')
            half_cnt = int(len(text_list) / 2)
            key_list = text_list[:half_cnt]
            value_list = text_list[half_cnt:]
            value_list = [compile_condition(x) for x in value_list]
            self.dict_condition = dict(zip(key_list, value_list))

    def SetBuyStg(self, buytxt):
        self.buystrategy, indistg = get_buy_indi_stg(buytxt)
        if indistg is not None:
            try:
                exec(indistg)
            except:
                pass
            else:
                print(self.indicator)

    def MainLoop(self):
        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 전략 연산 시작'))
        while True:
            data = self.cstgQ.get()
            if type(data) == tuple:
                if len(data) > 3:
                    self.Strategy(data)
                elif len(data) == 2:
                    self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)
                if data == '프로세스종료':
                    break

        self.windowQ.put((ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 전략연산 종료'))
        time.sleep(1)

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '관심목록':
            drop_index_list = list(set(list(self.df_gj.index)) - set(data))
            if drop_index_list: self.df_gj.drop(index=drop_index_list, inplace=True)
        elif '_COMPLETE' in gubun:
            gubun = gubun.replace('_COMPLETE', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
            if gubun in ('BUY_LONG', 'SELL_SHORT'):
                if data in self.dict_signal_num.keys():
                    self.dict_buy_num[data] = self.dict_signal_num[data]
                else:
                    self.dict_buy_num[data] = len(self.dict_arry[data]) - 1
        elif '_CANCEL' in gubun:
            gubun = gubun.replace('_CANCEL', '')
            if data in self.dict_signal[gubun]:
                self.dict_signal[gubun].remove(data)
        elif '_MANUAL' in gubun:
            gubun = gubun.replace('_MANUAL', '')
            if data not in self.dict_signal[gubun]:
                self.dict_signal[gubun].append(data)
        elif gubun == '잔고목록':
            self.df_jg = data
            self.jgrv_count += 1
            if self.jgrv_count == 2:
                self.jgrv_count = 0
                self.PutGsjmAndDeleteHilo()
        elif gubun == '매수전략':
            self.SetBuyStg(data)
        elif gubun == '매도전략':
            self.sellstrategy = compile(data, '<string>', 'exec')
        elif gubun == '종목당투자금':
            self.int_tujagm = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
            self.UpdateStringategy()
        elif gubun == '바낸선물단위정보':
            self.dict_info = data
        elif gubun == '데이터저장':
            self.SaveData(data)

    def UpdateString(self, data):
        if data == '매수전략중지':
            self.buystrategy = None
        elif data == '매도전략중지':
            self.sellstrategy = None

    def Strategy(self, data):
        체결시간, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, 초당거래대금, 고저평균대비등락율, 매도총잔량, 매수총잔량, \
            매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
            매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
            매도수5호가잔량합, 관심종목, 종목코드, 틱수신시간 = data

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
            return Parameter_Dgree(50, 5, tick, pre, 10)

        def 당일거래대금각도(tick, pre=0):
            return Parameter_Dgree(51, 6, tick, pre, 0.00000001)

        def 경과틱수(조건명):
            if 종목코드 in self.dict_cond_indexn.keys() and \
                    조건명 in self.dict_cond_indexn[종목코드].keys() and self.dict_cond_indexn[종목코드][조건명] != 0:
                return self.indexn - self.dict_cond_indexn[종목코드][조건명]
            return 0

        시분초, 호가단위 = int(str(체결시간)[8:]), self.dict_info[종목코드]['호가단위']
        데이터길이 = len(self.dict_arry[종목코드]) + 1 if 종목코드 in self.dict_arry.keys() else 1
        평균값계산틱수 = self.dict_set['코인평균값계산틱수']
        이동평균0060, 이동평균0300, 이동평균0600, 이동평균1200, 최고현재가_, 최저현재가_ = 0., 0., 0., 0., 0, 0
        체결강도평균_, 최고체결강도_, 최저체결강도_, 최고초당매수수량_, 최고초당매도수량_ = 0., 0., 0., 0, 0
        누적초당매수수량_, 누적초당매도수량_, 초당거래대금평균_, 등락율각도_, 당일거래대금각도_, 전일비각도_ = 0, 0, 0., 0., 0., 0.

        bhogainfo = ((매도호가1, 매도잔량1), (매도호가2, 매도잔량2), (매도호가3, 매도잔량3), (매도호가4, 매도잔량4), (매도호가5, 매도잔량5))
        shogainfo = ((매수호가1, 매수잔량1), (매수호가2, 매수잔량2), (매수호가3, 매수잔량3), (매수호가4, 매수잔량4), (매수호가5, 매수잔량5))
        self.bhogainfo = bhogainfo[:self.dict_set['코인매수시장가잔량범위']]
        self.shogainfo = shogainfo[:self.dict_set['코인매도시장가잔량범위']]

        if 종목코드 in self.dict_arry.keys():
            if len(self.dict_arry[종목코드]) >=   59: 이동평균0060 = round((self.dict_arry[종목코드][  -59:, 1].sum() + 현재가) /   60, 8)
            if len(self.dict_arry[종목코드]) >=  299: 이동평균0300 = round((self.dict_arry[종목코드][ -299:, 1].sum() + 현재가) /  300, 8)
            if len(self.dict_arry[종목코드]) >=  599: 이동평균0600 = round((self.dict_arry[종목코드][ -599:, 1].sum() + 현재가) /  600, 8)
            if len(self.dict_arry[종목코드]) >= 1199: 이동평균1200 = round((self.dict_arry[종목코드][-1199:, 1].sum() + 현재가) / 1200, 8)
            if len(self.dict_arry[종목코드]) >= 평균값계산틱수 - 1:
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
                등락율각도_      = round(math.atan2((등락율 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 5]) * 10, 평균값계산틱수) / (2 * math.pi) * 360, 2)
                당일거래대금각도_ = round(math.atan2((당일거래대금 - self.dict_arry[종목코드][-(평균값계산틱수 - 1), 6]) / 100_000_000, 평균값계산틱수) / (2 * math.pi) * 360, 2)

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

        if 종목코드 not in self.dict_arry.keys():
            self.dict_arry[종목코드] = np.array([new_data_tick])
        else:
            self.dict_arry[종목코드] = np.r_[self.dict_arry[종목코드], np.array([new_data_tick])]

        데이터길이 = len(self.dict_arry[종목코드])
        self.indexn = 데이터길이 - 1

        if self.dict_condition:
            if 종목코드 not in self.dict_cond_indexn.keys():
                self.dict_cond_indexn[종목코드] = {}
            for k, v in self.dict_condition.items():
                try:
                    exec(v)
                except:
                    print_exc()
                    self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 오류 알림 - 경과틱수 연산오류'))

        if 체결강도평균_ != 0 and 체결시간 < self.dict_set['코인전략종료시간']:
            if 종목코드 in self.df_jg.index:
                if 종목코드 not in self.dict_buy_num.keys():
                    self.dict_buy_num[종목코드] = len(self.dict_arry[종목코드]) - 1
                매수틱번호 = self.dict_buy_num[종목코드]
                포지션 = self.df_jg['포지션'][종목코드]
                매입가 = self.df_jg['매입가'][종목코드]
                보유수량 = self.df_jg['보유수량'][종목코드]
                매입금액 = self.df_jg['매입금액'][종목코드]
                레버리지 = self.df_jg['레버리지'][종목코드]
                분할매수횟수 = int(self.df_jg['분할매수횟수'][종목코드])
                분할매도횟수 = int(self.df_jg['분할매도횟수'][종목코드])
                if 포지션 == 'LONG':
                    _, 수익금, 수익률 = GetBinanceLongPgSgSp(매입금액, 보유수량 * 현재가, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                else:
                    _, 수익금, 수익률 = GetBinanceShortPgSgSp(매입금액, 보유수량 * 현재가, '시장가' in self.dict_set['코인매수주문구분'], '시장가' in self.dict_set['코인매도주문구분'])
                매수시간 = strp_time('%Y%m%d%H%M%S', self.df_jg['매수시간'][종목코드])
                보유시간 = (now_utc() - 매수시간).total_seconds()
                if 종목코드 not in self.dict_hilo.keys():
                    self.dict_hilo[종목코드] = [수익률, 수익률]
                else:
                    if 수익률 > self.dict_hilo[종목코드][0]:
                        self.dict_hilo[종목코드][0] = 수익률
                    elif 수익률 < self.dict_hilo[종목코드][1]:
                        self.dict_hilo[종목코드][1] = 수익률
                최고수익률, 최저수익률 = self.dict_hilo[종목코드]
            else:
                포지션, 매수틱번호, 수익금, 수익률, 레버리지, 매입가, 보유수량, 분할매수횟수, 분할매도횟수, 매수시간, 보유시간, 최고수익률, 최저수익률 = None, 0, 0, 0, 1, 0, 0, 0, 0, now(), 0, 0, 0
            self.indexb = 매수틱번호

            BBT  = not self.dict_set['코인매수금지시간'] or not (self.dict_set['코인매수금지시작시간'] < 시분초 < self.dict_set['코인매수금지종료시간'])
            BLK  = not self.dict_set['코인매수금지블랙리스트'] or 종목코드 not in self.dict_set['코인블랙리스트']
            C20  = not self.dict_set['코인매수금지200원이하'] or 현재가 > 200
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']
            NISL = 종목코드 not in self.dict_signal['SELL_LONG']
            NIBS = 종목코드 not in self.dict_signal['BUY_SHORT']
            A    = 관심종목 and NIBL and 포지션 is None
            B    = 관심종목 and NISS and 포지션 is None
            C    = self.dict_set['코인매수분할시그널']
            D    = NIBL and 포지션 == 'LONG' and 분할매수횟수 < self.dict_set['코인매수분할횟수']
            E    = NISS and 포지션 == 'SHORT' and 분할매수횟수 < self.dict_set['코인매수분할횟수']
            F    = NIBL and self.dict_set['코인매도취소매수시그널'] and not NISL
            G    = NISS and self.dict_set['코인매도취소매수시그널'] and not NIBS

            if BBT and BLK and C20 and (A or B or (C and D) or (C and E) or D or E or F or G):
                매수수량 = 0
                if not (F or G):
                    매수수량 = self.SetBuyCount(분할매수횟수, 매입가, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), self.dict_info[종목코드]['소숫점자리수'])

                if A or B or (C and (D or E)) or F or G:
                    BUY_LONG, SELL_SHORT = True, True
                    if self.buystrategy is not None:
                        try:
                            exec(self.buystrategy)
                        except:
                            print_exc()
                            self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 오류 알림 - BuyStrategy'))
                elif D or E:
                    BUY_LONG, SELL_SHORT = False, False
                    분할매수기준수익률 = round((현재가 / 현재가N(-1) - 1) * 100, 2) if self.dict_set['코인매수분할고정수익률'] else 수익률
                    if D:
                        if self.dict_set['코인매수분할하방'] and 분할매수기준수익률 < -self.dict_set['코인매수분할하방수익률']:
                            BUY_LONG   = True
                        elif self.dict_set['코인매수분할상방'] and 분할매수기준수익률 > self.dict_set['코인매수분할상방수익률']:
                            BUY_LONG   = True
                    elif E:
                        if self.dict_set['코인매수분할하방'] and 분할매수기준수익률 < -self.dict_set['코인매수분할하방수익률']:
                            SELL_SHORT = True
                        elif self.dict_set['코인매수분할상방'] and 분할매수기준수익률 > self.dict_set['코인매수분할상방수익률']:
                            SELL_SHORT = True

                    if BUY_LONG or SELL_SHORT:
                        self.Buy(종목코드, BUY_LONG, 현재가, 매도호가1, 매수호가1, 매수수량, 데이터길이)

            SBT  = not self.dict_set['코인매도금지시간'] or not (self.dict_set['코인매도금지시작시간'] < 시분초 < self.dict_set['코인매도금지종료시간'])
            SCC  = self.dict_set['코인매수분할횟수'] == 1 or not self.dict_set['코인매도금지매수횟수'] or 분할매수횟수 > self.dict_set['코인매도금지매수횟수값']
            NIBL = 종목코드 not in self.dict_signal['BUY_LONG']
            NISS = 종목코드 not in self.dict_signal['SELL_SHORT']

            A    = NIBL and NISL and SCC and 포지션 == 'LONG' and self.dict_set['코인매도분할횟수'] == 1
            B    = NISS and NIBS and SCC and 포지션 == 'SHORT' and self.dict_set['코인매도분할횟수'] == 1
            C    = self.dict_set['코인매도분할시그널']
            D    = NIBL and NISL and SCC and 포지션 == 'LONG' and 분할매도횟수 < self.dict_set['코인매도분할횟수']
            E    = NISS and NIBS and SCC and 포지션 == 'SHORT' and 분할매도횟수 < self.dict_set['코인매도분할횟수']
            F    = NISL and self.dict_set['코인매수취소매도시그널'] and not NIBL
            G    = NIBS and self.dict_set['코인매수취소매도시그널'] and not NISS
            H    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['코인매도손절수익률청산'] and 수익률 < -self.dict_set['코인매도손절수익률']
            J    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['코인매도손절수익률청산'] and 수익률 < -self.dict_set['코인매도손절수익률']
            K    = NIBL and NISL and 포지션 == 'LONG' and self.dict_set['코인매도손절수익금청산'] and 수익금 < -self.dict_set['코인매도손절수익금']
            L    = NISS and NIBS and 포지션 == 'SHORT' and self.dict_set['코인매도손절수익금청산'] and 수익금 < -self.dict_set['코인매도손절수익금']
            M    = NIBL and NISL and 포지션 == 'LONG' and 수익률 * 레버리지 < -90
            N    = NISS and NIBS and 포지션 == 'SHORT' and 수익률 * 레버리지 < -90

            if SBT and (A or B or (C and D) or (C and E) or D or E or F or G or H or J or K or L or M or N):
                SELL_LONG, BUY_SHORT = False, False
                매도수량 = 0
                강제청산 = H or J or K or L or M or N

                if A or B or H or J or K or L or M or N:
                    매도수량 = 보유수량
                elif not (F or G):
                    매도수량 = self.SetSellCount(분할매도횟수, 보유수량, 매입가, 현재가, 고가, 저가, 등락율각도(30), 당일거래대금각도(30), self.dict_info[종목코드]['소숫점자리수'])

                if A or B or (C and (D or E)) or F or G:
                    if self.sellstrategy is not None:
                        try:
                            exec(self.sellstrategy)
                        except:
                            print_exc()
                            self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 오류 알림 - SellStrategy'))
                elif D or E or H or J or K or L or M or N:
                    if H or K or M:
                        SELL_LONG = True
                    elif J or L or N:
                        BUY_SHORT = True
                    elif D:
                        if self.dict_set['코인매도분할하방'] and 수익률 < -self.dict_set['코인매도분할하방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                        elif self.dict_set['코인매도분할상방'] and 수익률 > self.dict_set['코인매도분할상방수익률'] * (분할매도횟수 + 1):
                            SELL_LONG = True
                    elif E:
                        if self.dict_set['코인매도분할하방'] and 수익률 < -self.dict_set['코인매도분할하방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True
                        elif self.dict_set['코인매도분할상방'] and 수익률 > self.dict_set['코인매도분할상방수익률'] * (분할매도횟수 + 1):
                            BUY_SHORT = True

                    if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):
                        self.Sell(종목코드, SELL_LONG, 현재가, 매도호가1, 매수호가1, 매도수량, 강제청산)

        if 관심종목:
            self.df_gj.loc[종목코드] = 종목코드, 등락율, 고저평균대비등락율, 초당거래대금, 초당거래대금평균_, 당일거래대금, 체결강도, 체결강도평균_, 최고체결강도_

        if len(self.dict_arry[종목코드]) >= 평균값계산틱수 and self.chart_code == 종목코드:
            self.windowQ.put((ui_num['실시간차트'], 종목코드, self.dict_arry[종목코드]))

        if 틱수신시간 != 0:
            gap = (now() - 틱수신시간).total_seconds()
            self.windowQ.put((ui_num['C단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))

    def SetBuyCount(self, 분할매수횟수, 매입가, 현재가, 고가, 저가, 등락율각도, 당일거래대금각도, 소숫점자리수):
        if self.dict_set['코인비중조절'][0] == 0:
            betting = self.int_tujagm
        else:
            if self.dict_set['코인비중조절'][0] == 1:
                비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
            elif self.dict_set['코인비중조절'][0] == 2:
                비중조절기준 = 등락율각도
            else:
                비중조절기준 = 당일거래대금각도

            if 비중조절기준 < self.dict_set['코인비중조절'][1]:
                betting = self.int_tujagm * self.dict_set['코인비중조절'][5]
            elif 비중조절기준 < self.dict_set['코인비중조절'][2]:
                betting = self.int_tujagm * self.dict_set['코인비중조절'][6]
            elif 비중조절기준 < self.dict_set['코인비중조절'][3]:
                betting = self.int_tujagm * self.dict_set['코인비중조절'][7]
            elif 비중조절기준 < self.dict_set['코인비중조절'][4]:
                betting = self.int_tujagm * self.dict_set['코인비중조절'][8]
            else:
                betting = self.int_tujagm * self.dict_set['코인비중조절'][9]

        oc_ratio = dict_order_ratio[self.dict_set['코인매수분할방법']][self.dict_set['코인매수분할횟수']][분할매수횟수]
        매수수량 = round(betting / (현재가 if 매입가 == 0 else 매입가) * oc_ratio / 100, 소숫점자리수)
        return 매수수량

    def SetSellCount(self, 분할매도횟수, 보유수량, 매입가, 현재가, 고가, 저가, 등락율각도, 당일거래대금각도, 소숫점자리수):
        if self.dict_set['코인매도분할횟수'] == 1:
            return 보유수량
        else:
            if self.dict_set['코인비중조절'][0] == 0:
                betting = self.int_tujagm
            else:
                if self.dict_set['코인비중조절'][0] == 1:
                    비중조절기준 = round((고가 / 저가 - 1) * 100, 2)
                elif self.dict_set['코인비중조절'][0] == 2:
                    비중조절기준 = 등락율각도
                else:
                    비중조절기준 = 당일거래대금각도

                if 비중조절기준 < self.dict_set['코인비중조절'][1]:
                    betting = self.int_tujagm * self.dict_set['코인비중조절'][5]
                elif 비중조절기준 < self.dict_set['코인비중조절'][2]:
                    betting = self.int_tujagm * self.dict_set['코인비중조절'][6]
                elif 비중조절기준 < self.dict_set['코인비중조절'][3]:
                    betting = self.int_tujagm * self.dict_set['코인비중조절'][7]
                elif 비중조절기준 < self.dict_set['코인비중조절'][4]:
                    betting = self.int_tujagm * self.dict_set['코인비중조절'][8]
                else:
                    betting = self.int_tujagm * self.dict_set['코인비중조절'][9]

            oc_ratio = dict_order_ratio[self.dict_set['코인매도분할방법']][self.dict_set['코인매도분할횟수']][분할매도횟수]
            매도수량 = round(betting / 매입가 * oc_ratio / 100, 소숫점자리수)
            if 매도수량 > 보유수량 or 분할매도횟수 + 1 == self.dict_set['코인매도분할횟수']: 매도수량 = 보유수량
            return 매도수량

    def Buy(self, 종목코드, BUY_LONG, 현재가, 매도호가1, 매수호가1, 매수수량, 데이터길이):
        구분 = 'BUY_LONG' if BUY_LONG else 'SELL_SHORT'
        if '지정가' in self.dict_set['코인매수주문구분']:
            기준가격 = 현재가
            if self.dict_set['코인매수지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if BUY_LONG else 매수호가1
            if self.dict_set['코인매수지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if BUY_LONG else 매도호가1
            self.dict_signal[구분].append(종목코드)
            self.dict_signal_num[종목코드] = 데이터길이 - 1
            self.ctraderQ.put((구분, 종목코드, 기준가격, 매수수량, now(), False))
        else:
            매수금액 = 0
            미체결수량 = 매수수량
            hogainfo = self.bhogainfo if BUY_LONG else self.shogainfo
            hogainfo = hogainfo[:self.dict_set['코인매수시장가잔량범위']]
            for 호가, 잔량 in hogainfo:
                if 미체결수량 - 잔량 <= 0:
                    매수금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매수금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                예상체결가 = round(매수금액 / 매수수량, 8) if 매수수량 != 0 else 0
                self.dict_signal[구분].append(종목코드)
                self.dict_signal_num[종목코드] = 데이터길이 - 1
                self.ctraderQ.put((구분, 종목코드, 예상체결가, 매수수량, now(), False))

    def Sell(self, 종목코드, SELL_LONG, 현재가, 매도호가1, 매수호가1, 매도수량, 강제청산):
        구분 = 'SELL_LONG' if SELL_LONG else 'BUY_SHORT'
        if '지정가' in self.dict_set['코인매도주문구분'] and not 강제청산:
            기준가격 = 현재가
            if self.dict_set['코인매도지정가기준가격'] == '매도1호가': 기준가격 = 매도호가1 if 구분 == 'SELL_LONG' else 매수호가1
            if self.dict_set['코인매도지정가기준가격'] == '매수1호가': 기준가격 = 매수호가1 if 구분 == 'SELL_LONG' else 매도호가1
            self.dict_signal[구분].append(종목코드)
            self.ctraderQ.put((구분, 종목코드, 기준가격, 매도수량, now(), False))
        else:
            매도금액 = 0
            미체결수량 = 매도수량
            hogainfo = self.shogainfo if 구분 == 'SELL_LONG' else self.bhogainfo
            hogainfo = hogainfo[:self.dict_set['코인매도시장가잔량범위']]
            for 호가, 잔량 in hogainfo:
                if 미체결수량 - 잔량 <= 0:
                    매도금액 += 호가 * 미체결수량
                    미체결수량 -= 잔량
                    break
                else:
                    매도금액 += 호가 * 잔량
                    미체결수량 -= 잔량
            if 미체결수량 <= 0:
                예상체결가 = round(매도금액 / 매도수량, 8) if 매도수량 != 0 else 0
                self.dict_signal[구분].append(종목코드)
                self.ctraderQ.put((구분, 종목코드, 예상체결가, 매도수량, now(), True if 강제청산 else False))

    def PutGsjmAndDeleteHilo(self):
        self.df_gj.sort_values(by=['d_money'], ascending=False, inplace=True)
        self.windowQ.put((ui_num['C관심종목'], self.df_gj))
        for code in list(self.dict_hilo.keys()):
            if code not in self.df_jg.index:
                del self.dict_hilo[code]

    def SaveData(self, codes):
        for code in list(self.dict_arry.keys()):
            if code not in codes:
                del self.dict_arry[code]

        if self.dict_set['코인타임프레임']:
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
        con  = sqlite3.connect(DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN)
        if last > 0:
            start = now()
            cllen = len(columns_ts)
            for i, code in enumerate(list(self.dict_arry.keys())):
                df = pd.DataFrame(self.dict_arry[code][:, :cllen], columns=columns_ts)
                df[['index']] = df[['index']].astype('int64')
                df.set_index('index', inplace=True)
                df.to_sql(code, con, if_exists='append', chunksize=1000)
                text = f'시스템 명령 실행 알림 - 전략연산 프로세스 데이터 저장 중 ... {i + 1}/{last}'
                self.windowQ.put((ui_num['C단순텍스트'], text))
            save_time = (now() - start).total_seconds()
            text = f'시스템 명령 실행 알림 - 데이터 저장 쓰기소요시간은 [{save_time:.6f}]초입니다.'
            self.windowQ.put((ui_num['C단순텍스트'], text))
        con.close()

        self.cstgQ.put('프로세스종료')
