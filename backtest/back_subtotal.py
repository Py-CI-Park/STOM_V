
import numpy as np
from traceback import format_exc
from backtest.back_static import add_mdd
from utility.settings.setting_base import ui_num
from backtest.back_static_numba import get_result


class BackSubTotal:
    """백테스트 결과를 집계하는 클래스입니다.
    여러 백테스트 결과를 수집하고 통합합니다.
    """
    def __init__(self, vkey, wq, tq, bstqs, buystd):
        """백테스트 결과 집계기를 초기화합니다.
        Args:
            vkey: 키 값
            wq: 윈도우 큐
            tq: 트레이더 큐
            bstqs: 백테스트 전략 큐 리스트
            buystd: 매수 표준편차
        """
        self.vkey         = vkey
        self.wq           = wq
        self.tq           = tq
        self.bstqs        = bstqs
        self.bstq         = self.bstqs[self.vkey]
        self.buystd       = buystd

        self.opti_kind    = 0
        self.concat_cnt   = 0
        self.dummy_tsg    = {}
        self.ddict_tsg    = {}
        self.ddict_bct    = {}
        self.list_tsg     = []
        self.arry_bct     = None
        self.separation   = None
        self.complete1    = False
        self.complete2    = False

        self.market_gubun = None
        self.list_days    = None
        self.valid_days   = None
        self.arry_bct_    = None
        self.betting      = None
        self.day_count    = None
        self.in_out_cnt   = None

        self._main_loop()

    def _main_loop(self):
        """메인 루프를 실행합니다.
        백테스트 결과를 수집하고 집계합니다.
        """
        while True:
            try:
                data = self.bstq.get()
                if data[0] == '백테결과':
                    self._collect_data(data)

                elif data[0] == '백테완료':
                    self.complete1 = True
                    self.separation = data[1]

                elif data == '결과집계':
                    self._send_data()

                elif data[0] == '개별결과':
                    self._concat_data(data)

                elif data[0] == '백테정보':
                    self.market_gubun = data[1]
                    self.list_days    = data[2]
                    self.valid_days   = data[3]
                    self.arry_bct_    = data[4]
                    self.betting      = data[5]
                    self.day_count    = data[6]

                elif data[0] == '백테시작':
                    self.opti_kind  = data[1]
                    self.dummy_tsg  = {}
                    self.ddict_tsg  = {}
                    self.ddict_bct  = {}
                    self.list_tsg   = []
                    self.arry_bct   = None
                    self.separation = None
                    self.complete1  = False
                    self.concat_cnt = 0
                    if len(data) == 2:
                        self.in_out_cnt = None
                    else:
                        self.in_out_cnt = data[2]

                if self.complete1 and self.bstq.empty():
                    if self.separation == '일괄집계':
                        self.tq.put('수집완료')
                    else:
                        self.tq.put(('더미결과', self.vkey, self.dummy_tsg))
                        self._send_subtotal()
                    self.complete1 = False
            except Exception:
                self.wq.put((ui_num['시스템로그'], format_exc()))

    def _collect_data(self, data):
        """백테스트 결과를 수집합니다."""
        _, 종목명, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매수금액, 매도금액, 수익률, 수익금, 매도조건, \
            추가매수시간, 잔량없음, vturn, vkey = data

        if vturn not in self.ddict_tsg:
            self.dummy_tsg[vturn] = {}
            self.ddict_tsg[vturn] = {}
            self.ddict_bct[vturn] = {}
        if vkey not in self.ddict_tsg[vturn]:
            self.ddict_tsg[vturn][vkey] = []
            self.ddict_bct[vturn][vkey] = self.arry_bct_.copy()

        index = str(매수시간) if self.buystd else str(매도시간)
        if self.opti_kind != 2:
            data = [index, 보유시간, 매도시간, 수익률, 수익금]
        else:
            data = [index, 종목명, 시가총액또는포지션, 매수시간, 매도시간, 보유시간, 매수가, 매도가, 매수금액, 매도금액, 수익률, 수익금, 매도조건, 추가매수시간]
        self.ddict_tsg[vturn][vkey].append(data)

        arry_bct = self.ddict_bct[vturn][vkey]
        mask = (매수시간 <= arry_bct[:, 0]) & (arry_bct[:, 0] <= 매도시간)
        arry_bct[mask, 2] += 매수금액
        if 잔량없음: arry_bct[mask, 1] += 1

    def _send_data(self):
        """집계 결과를 전송합니다."""
        if self.ddict_tsg:
            self.bstqs[0].put(('개별결과', self.ddict_tsg[0][0], self.ddict_bct[0][0]))
        else:
            self.bstqs[0].put(('개별결과', None, None))

    def _concat_data(self, data):
        """결과를 병합합니다."""
        _, list_tsg, arry_bct = data
        if list_tsg is not None:
            if self.arry_bct is None:
                self.arry_bct = arry_bct
            else:
                self.arry_bct[:, 1:] += arry_bct[:, 1:]
            self.list_tsg.extend(list_tsg)

        self.concat_cnt += 1
        if self.concat_cnt == 5:
            if self.opti_kind != 2:
                self._send_subtotal()
            else:
                self.tq.put(('백테결과', self.list_tsg, self.arry_bct))

    def _send_subtotal(self):
        """전체 결과를 전송합니다."""
        def send_result():
            if self.list_days is not None:
                train_days, valid_days, test_days = self.list_days if self.in_out_cnt is None else self.list_days[self.in_out_cnt]
                if valid_days is not None:
                    for i, vdays in enumerate(valid_days):
                        data = (arry_tsg, arry_bct, vdays[0], vdays[1], test_days[0], train_days[2], vdays[2], i, vturn, vkey)
                        self._send_result(data)
                else:
                    data = (arry_tsg, arry_bct, train_days[2], vturn, vkey)
                    self._send_result(data)

            elif self.valid_days is not None:
                for i, vdays in enumerate(self.valid_days):
                    data = (arry_tsg, arry_bct, vdays[0], vdays[1], vdays[2], vdays[3], i, vturn, vkey)
                    self._send_result(data)
            else:
                data = (arry_tsg, arry_bct, self.day_count, vturn, vkey)
                self._send_result(data)

        if self.separation == '분리집계':
            if not self.ddict_tsg:
                return
            for vturn, dict_tsg in self.ddict_tsg.items():
                for vkey, list_tsg in dict_tsg.items():
                    arry_tsg, arry_bct = self._get_sorted_array(list_tsg, self.ddict_bct[vturn][vkey])
                    send_result()
        else:
            if not self.list_tsg:
                self.tq.put(('결과없음',))
                return
            arry_tsg, arry_bct = self._get_sorted_array(self.list_tsg, self.arry_bct)
            vturn, vkey = 0, 0
            send_result()

    @staticmethod
    def _get_sorted_array(list_tsg, arry_bct):
        """보유금액 배열을 정렬합니다."""
        arry_tsg = np.array(list_tsg, dtype='float64')
        arry_tsg = arry_tsg[np.argsort(arry_tsg[:, 0])][:, 1:]
        arry_bct = np.sort(arry_bct[arry_bct[:, 1] > 0], axis=0)[::-1]
        return arry_tsg, arry_bct

    def _send_result(self, data):
        """ 학습구간, 검증구간, 확인구간별 결괄르 전송합니다.
        arry_tsg dtype 'float64'
        보유시간, 매도시간, 수익률, 수익금, 수익금합계
           0       1       2      3      4
        arry_bct dtype 'float64'
        체결시간, 보유중목수, 보유금액
          0         1        2
        """
        arry_tsg, arry_bct = data[:2]
        len_data = len(data)

        if len_data > 5:
            if arry_bct[0, 0] * 1e-12 > 1:
                cf_day, cf_hms = 1000000, 240000
            else:
                cf_day, cf_hms = 10000, 2400

            tsg_time_idx = arry_tsg[:, 1]
            bct_time_idx = arry_bct[:, 0]

            if len_data == 10:
                vsday, veday, tsday, tdaycnt, vdaycnt, index, vturn, vkey = data[2:]
                arry_bct_ = arry_bct[(bct_time_idx < vsday * cf_day) | ((veday * cf_day + cf_hms < bct_time_idx) & (bct_time_idx < tsday * cf_day))]
                arry_tsg_ = arry_tsg[(tsg_time_idx < vsday * cf_day) | ((veday * cf_day + cf_hms < tsg_time_idx) & (tsg_time_idx < tsday * cf_day))]
            else:
                vsday, veday, tdaycnt, vdaycnt, index, vturn, vkey = data[2:]
                arry_bct_ = arry_bct[(bct_time_idx < vsday * cf_day) | (veday * cf_day + cf_hms < bct_time_idx)]
                arry_tsg_ = arry_tsg[(tsg_time_idx < vsday * cf_day) | (veday * cf_day + cf_hms < tsg_time_idx)]

            arry_tsg_ = np.column_stack((arry_tsg_, np.cumsum(arry_tsg_[:, 3])))
            result    = get_result(arry_tsg_, arry_bct_, self.betting, self.market_gubun, tdaycnt)
            result    = add_mdd(arry_tsg_, result)
            self.tq.put(('TRAIN', index, result, vturn, vkey))

            arry_bct_ = arry_bct[(vsday * cf_day <= bct_time_idx) & (bct_time_idx <= veday * cf_day + cf_hms)]
            arry_tsg_ = arry_tsg[(vsday * cf_day <= tsg_time_idx) & (tsg_time_idx <= veday * cf_day + cf_hms)]
            arry_tsg_ = np.column_stack((arry_tsg_, np.cumsum(arry_tsg_[:, 3])))
            result    = get_result(arry_tsg_, arry_bct_, self.betting, self.market_gubun, vdaycnt)
            result    = add_mdd(arry_tsg_, result)
            self.tq.put(('VALID', index, result, vturn, vkey))

        else:
            daycnt, vturn, vkey = data[2:]
            result = get_result(arry_tsg, arry_bct, self.betting, self.market_gubun, daycnt)
            result = add_mdd(arry_tsg, result)
            self.tq.put(('ALL', 0, result, vturn, vkey))
