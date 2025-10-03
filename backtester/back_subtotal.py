import numpy as np
import pandas as pd
from backtester.back_static import GetBackResult, AddMdd


class BackSubTotal:
    def __init__(self, vk, tq, bctqs, buystd):
        self.vkey   = vk
        self.tq         = tq
        self.bstqs      = bctqs
        self.bstq       = self.bstqs[self.vkey]
        self.buystd     = buystd

        self.opti_turn  = 0
        self.dummy_tsg  = {}
        self.ddict_tsg  = {}
        self.ddict_bct  = {}
        self.list_tsg   = []
        self.arry_bct   = None
        self.separation = None
        self.complete1  = False
        self.complete2  = False

        self.ui_gubun   = None
        self.list_days  = None
        self.valid_days = None
        self.arry_bct_  = None
        self.betting    = None
        self.day_count  = None
        self.in_out_cnt = None
        self.MainLoop()

    def MainLoop(self):
        while True:
            data = self.bstq.get()
            if data[0] == '백테결과':
                self.CollectData(data)
            elif data[0] == '백테완료':
                self.complete1 = True
                self.separation = data[1]
            elif data == '결과분리':
                self.DivideData()
            elif data[0] == '분리결과':
                self.ConcatData(data)
            elif data == '결과전송':
                self.complete2 = True
            elif data[0] == '백테정보':
                self.ui_gubun   = data[1]
                self.list_days  = data[2]
                self.valid_days = data[3]
                self.arry_bct_  = data[4]
                self.betting    = data[5]
                self.day_count  = data[6]
            elif data[0] == '백테시작':
                self.opti_turn  = data[1]
                self.dummy_tsg  = {}
                self.ddict_tsg  = {}
                self.ddict_bct  = {}
                self.list_tsg   = []
                self.arry_bct   = None
                self.separation = None
                self.complete1  = False
                self.complete2  = False
                if len(data) == 2:
                    self.in_out_cnt = None
                else:
                    self.in_out_cnt = data[2]
            if self.complete1 and self.bstq.empty():
                if self.separation == '분리집계':
                    self.tq.put('집계완료')
                else:
                    self.tq.put(('더미결과', self.vkey, self.dummy_tsg))
                    self.SendSubTotal1()
                self.complete1 = False

            if self.complete2 and self.bstq.empty():
                if self.opti_turn != 2:
                    self.SendSubTotal2()
                else:
                    self.tq.put(('백테결과', self.list_tsg, self.arry_bct))
                self.complete2 = False

    def CollectData(self, data):
        _, 종목명, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매수금액, 매도금액, 수익률, 수익금, 매도조건, \
            추가매수시간, 잔량없음, vturn, vkey = data
        if vturn not in self.ddict_tsg.keys():
            self.dummy_tsg[vturn] = {}
            self.ddict_tsg[vturn] = {}
            self.ddict_bct[vturn] = {}
        if vkey not in self.ddict_tsg[vturn].keys():
            self.dummy_tsg[vturn][vkey] = 0
            self.ddict_tsg[vturn][vkey] = []
            self.ddict_bct[vturn][vkey] = self.arry_bct_.copy()

        index = str(매수시간) if self.buystd else str(매도시간)
        if self.opti_turn != 2:
            data = [index, 보유시간, 매도시간, 수익률, 수익금]
        else:
            data = [index, 종목명, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매수금액, 매도금액, 수익률, 수익금, 매도조건, 추가매수시간]
        self.ddict_tsg[vturn][vkey].append(data)

        arry_bct  = self.ddict_bct[vturn][vkey]
        arry_bct_ = arry_bct[(매수시간 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= 매도시간)]
        arry_bct_[:, 2] += 매수금액
        if 잔량없음: arry_bct_[:, 1] += 1
        arry_bct[(매수시간 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= 매도시간)] = arry_bct_
        self.ddict_bct[vturn][vkey] = arry_bct

    def DivideData(self):
        try:
            self.bstqs[0].put(('분리결과', self.ddict_tsg[0][0], self.ddict_bct[0][0]))
        except:
            pass
        self.tq.put('분리완료')

    def ConcatData(self, data):
        _, list_tsg, arry_bct = data
        if self.arry_bct is None:
            self.arry_bct = arry_bct
        else:
            self.arry_bct[:, 1] += arry_bct[:, 1]
            self.arry_bct[:, 2] += arry_bct[:, 2]
        self.list_tsg += list_tsg

    def SendSubTotal1(self):
        if self.ddict_tsg:
            columns = ['index', '보유시간', '매도시간', '수익률', '수익금']
            for vturn, dict_tsg in self.ddict_tsg.items():
                for vkey, list_tsg in dict_tsg.items():
                    arry_bct = self.ddict_bct[vturn][vkey]
                    data = (columns, list_tsg, arry_bct)
                    if self.list_days is not None:
                        train_days, valid_days, test_days = self.list_days if self.in_out_cnt is None else self.list_days[self.in_out_cnt]
                        if valid_days is not None:
                            for i, vdays in enumerate(valid_days):
                                data_ = data + (vdays[0], vdays[1], test_days[0], train_days[2] - vdays[2], vdays[2], i, vturn, vkey)
                                self.Result(1, data_)
                                self.Result(0, data_)
                        else:
                            data_ = data + (train_days[2], vturn, vkey)
                            self.Result(0, data_)
                    elif self.valid_days is not None:
                        for i, vdays in enumerate(self.valid_days):
                            data_ = data + (vdays[0], vdays[1], vdays[2], vdays[3], i, vturn, vkey)
                            self.Result(1, data_)
                            self.Result(0, data_)
                    else:
                        data_ = data + (self.day_count, vturn, vkey)
                        self.Result(0, data_)

    def SendSubTotal2(self):
        if not self.list_tsg:
            self.tq.put(('결과없음',))
            return

        columns = ['index', '보유시간', '매도시간', '수익률', '수익금']
        data = (columns, self.list_tsg, self.arry_bct)
        if self.list_days is not None:
            train_days, valid_days, test_days = self.list_days if self.in_out_cnt is None else self.list_days[self.in_out_cnt]
            if valid_days is not None:
                for i, vdays in enumerate(valid_days):
                    data_ = data + (vdays[0], vdays[1], test_days[0], train_days[2] - vdays[2], vdays[2], i, 0, 0)
                    self.Result(1, data_)
                    self.Result(0, data_)
            else:
                data_ = data + (train_days[2], 0, 0)
                self.Result(0, data_)
        elif self.valid_days is not None:
            for i, vdays in enumerate(self.valid_days):
                data_ = data + (vdays[0], vdays[1], vdays[2], vdays[3], i, 0, 0)
                self.Result(1, data_)
                self.Result(0, data_)
        else:
            data_ = data + (self.day_count, 0, 0)
            self.Result(0, data_)

    def Result(self, gubun, data):
        """
        보유시간, 매도시간, 수익률, 수익금, 수익금합계
          0       1       2       3      4
        """
        columns, list_data, arry_bct = data[:3]
        df_tsg = pd.DataFrame(list_data, columns=columns)
        df_tsg.set_index('index', inplace=True)
        df_tsg.sort_index(inplace=True)
        df_tsg['수익금합계'] = df_tsg['수익금'].cumsum()
        arry_tsg = np.array(df_tsg, dtype='float64')
        arry_bct = arry_bct[arry_bct[:, 1] > 0]
        arry_bct = np.sort(arry_bct, axis=0)[::-1]
        if len(data) == 11:
            vsday, veday, tsday, tdaycnt, vdaycnt, index, vturn, vkey = data[3:]
            if gubun:
                arry_tsg = arry_tsg[(arry_tsg[:, 1] < vsday * 1000000) | ((veday * 1000000 + 240000 < arry_tsg[:, 1]) & (arry_tsg[:, 1] < tsday * 1000000))]
                arry_bct = arry_bct[(arry_bct[:, 0] < vsday * 1000000) | ((veday * 1000000 + 240000 < arry_bct[:, 0]) & (arry_bct[:, 0] < tsday * 1000000))]
                result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, tdaycnt)
            else:
                arry_tsg = arry_tsg[(vsday * 1000000 <= arry_tsg[:, 1]) & (arry_tsg[:, 1] <= veday * 1000000 + 240000)]
                arry_bct = arry_bct[(vsday * 1000000 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= veday * 1000000 + 240000)]
                result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, vdaycnt)
            result = AddMdd(arry_tsg, result)
            self.tq.put(('TRAIN' if gubun else 'VALID', index, result, vturn, vkey))
        elif len(data) == 10:
            vsday, veday, tdaycnt, vdaycnt, index, vturn, vkey = data[3:]
            if gubun:
                arry_tsg = arry_tsg[(arry_tsg[:, 1] < vsday * 1000000) | (veday * 1000000 + 240000 < arry_tsg[:, 1])]
                arry_bct = arry_bct[(vsday * 1000000 < arry_bct[:, 0]) | (arry_bct[:, 0] > veday * 1000000 + 240000)]
                result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, tdaycnt)
            else:
                arry_tsg = arry_tsg[(vsday * 1000000 <= arry_tsg[:, 1]) & (arry_tsg[:, 1] <= veday * 1000000 + 240000)]
                arry_bct = arry_bct[(vsday * 1000000 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= veday * 1000000 + 240000)]
                result   = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, vdaycnt)
            result = AddMdd(arry_tsg, result)
            self.tq.put(('TRAIN' if gubun else 'VALID', index, result, vturn, vkey))
        else:
            daycnt, vturn, vkey = data[3:]
            result = GetBackResult(arry_tsg, arry_bct, self.betting, self.ui_gubun, daycnt)
            result = AddMdd(arry_tsg, result)
            self.tq.put(('ALL', 0, result, vturn, vkey))
