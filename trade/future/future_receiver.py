
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from utility.static_method.static import now
from trade.base_receiver import BaseReceiver, MonitorReceivQ
from trade.restapi_ls import LsRestAPI, LsRestData, LsWebSocketReceiver


class FutureReceiver(BaseReceiver):
    """선물 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 선물 시장 데이터를 수신합니다.
    """

    def __init__(self, qlist, dict_set, market_infos):
        """수신기를 초기화합니다.
        Args:
            qlist (list): 큐 리스트
            dict_set (dict): 설정 딕셔너리
            market_infos (list): 마켓 정보 리스트
        """
        super().__init__(qlist, dict_set, market_infos)

        app = QApplication(sys.argv)

        self.ls = LsRestAPI(self.windowQ, self.access_key, self.secret_key)
        self.token = self.ls.create_token()

        self._get_code_info()
        self._save_code_info_and_noti()

        self.ws_thread = LsWebSocketReceiver(self.market_info['마켓이름'], self.token, self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

        self.updater = MonitorReceivQ(self.receivQ)
        self.updater.signal1.connect(self._update_tuple)
        self.updater.signal2.connect(self._sys_exit)
        self.updater.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self._scheduler)
        self.qtimer.start()

        app.exec_()

    def _get_code_info(self):
        """종목 정보를 조회합니다."""
        if '지수선물' in self.dict_set['거래소']:
            self.dict_info, self.codes, self.dict_expc = self.ls.get_code_info_future()
        else:
            self.dict_info, self.codes, self.dict_expc = self.ls.get_code_info_future_night()
        if self.dict_info:
            self.traderQ.put(('종목정보', (self.dict_info, self.dict_expc)))

    def _convert_real_data(self, data):
        """실시간 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        body = data['body']
        if body is None:
            return

        start = now()
        tr_cd = data['header']['tr_cd']
        if tr_cd == self.tr_cd_hoga:
            int_hms = int(body['hotime'])
            if self.dict_set['전략종료시간'] < int_hms:
                return
            dt = int(f"{self.str_today}{int_hms}")
            code = body['futcode']
            hoga_seprice = [
                float(body['offerho1']), float(body['offerho2']), float(body['offerho3']),
                float(body['offerho4']), float(body['offerho5'])
            ]
            hoga_buprice = [
                float(body['bidho1']), float(body['bidho2']), float(body['bidho3']),
                float(body['bidho4']), float(body['bidho5'])
            ]
            hoga_samount = [
                int(body['offerrem1']), int(body['offerrem2']), int(body['offerrem3']),
                int(body['offerrem4']), int(body['offerrem5'])
            ]
            hoga_bamount = [
                int(body['bidrem1']), int(body['bidrem2']), int(body['bidrem3']),
                int(body['bidrem4']), int(body['bidrem5'])
            ]
            hoga_tamount = [
                int(body['totofferrem']), int(body['totbidrem'])
            ]
            self._update_hoga_data(dt, code, hoga_seprice, hoga_buprice, hoga_samount,
                                   hoga_bamount, hoga_tamount, start)

        elif tr_cd == self.tr_cd_trade:
            int_hms = int(body['chetime'])
            if self.dict_set['전략종료시간'] < int_hms:
                return
            dt = int(f"{self.str_today}{int_hms}")
            code  = body['futcode']
            c     = float(body['price'])
            o     = float(body['open'])
            h     = float(body['high'])
            low   = float(body['low'])
            v     = int(body['cvolume'])
            per   = float(body['drate'])
            dm    = int(body['value'])
            cg    = body['cgubun']
            tbids = int(body['msvolume'])
            tasks = int(body['mdvolume'])
            ch    = float(body['cpower'])
            self._update_tick_data(dt, code, c, o, h, low, per, dm, v, cg, tbids, tasks, ch)

        elif tr_cd == self.tr_cd_oper:
            if body['jangubun'] == self.oper_gubun:
                operation = int(body['jstatus'])
                if operation in LsRestData.장운영상태:
                    self.operation = operation
                    self.soundQ.put(LsRestData.장운영상태[self.operation])
