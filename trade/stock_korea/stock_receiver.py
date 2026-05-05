
import sys
from PyQt5.QtCore import QTimer
from traceback import format_exc
from trade.restapi_ls import LsRestData
from PyQt5.QtWidgets import QApplication
from utility.static_method.static import now
from utility.settings.setting_base import ui_num
from trade.restapi_ls import LsRestAPI, LsWebSocketReceiver
from trade.base_receiver import BaseReceiver, MonitorReceivQ


class StockReceiver(BaseReceiver):
    """국내 주식 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 국내 주식 시장 데이터를 수신합니다.
    """

    def __init__(self, qlist, dict_set, market_infos):
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
        self.dict_info, self.codes = self.ls.get_code_info_stock(self.market_gubun-1)
        if self.dict_info:
            if self.market_gubun == 1:
                self.dict_sgbn = {code: i % 8 for i, code in enumerate(self.dict_info)}
                self.traderQ.put(('종목정보', (self.dict_info, self.dict_sgbn)))
            else:
                self.traderQ.put(('종목정보', self.dict_info))

    def _convert_real_data(self, data):
        """실시간 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        body = data['body']
        if body is None:
            return

        try:
            start = now()
            tr_cd = data['header']['tr_cd']
            if tr_cd == self.tr_cd_hoga:
                int_hms = int(body['hotime'])
                if int_hms < self.market_open or self.dict_set['전략종료시간'] < int_hms:
                    return
                dt = int(f"{self.str_today}{int_hms}")
                code = body['shcode']
                hoga_seprice = [
                    float(body['offerho1']), float(body['offerho2']), float(body['offerho3']), float(body['offerho4']),
                    float(body['offerho5']), float(body['offerho6']), float(body['offerho7']), float(body['offerho8']),
                    float(body['offerho9']), float(body['offerho10'])
                ]
                hoga_buprice = [
                    float(body['bidho1']), float(body['bidho2']), float(body['bidho3']), float(body['bidho4']),
                    float(body['bidho5']), float(body['bidho6']), float(body['bidho7']), float(body['bidho8']),
                    float(body['bidho9']), float(body['bidho10'])
                ]
                hoga_samount = [
                    float(body['krx_offerrem1']), float(body['krx_offerrem2']), float(body['krx_offerrem3']),
                    float(body['krx_offerrem4']), float(body['krx_offerrem5']), float(body['krx_offerrem6']),
                    float(body['krx_offerrem7']), float(body['krx_offerrem8']), float(body['krx_offerrem9']),
                    float(body['krx_offerrem10'])
                ]
                hoga_bamount = [
                    int(body['krx_bidrem1']), int(body['krx_bidrem2']), int(body['krx_bidrem3']), int(body['krx_bidrem4']),
                    int(body['krx_bidrem5']), int(body['krx_bidrem6']), int(body['krx_bidrem7']), int(body['krx_bidrem8']),
                    int(body['krx_bidrem9']), int(body['krx_bidrem10'])
                ]
                hoga_tamount = [
                    int(body['krx_totofferrem']), int(body['krx_totbidrem'])
                ]
                self._update_hoga_data(dt, code, hoga_seprice, hoga_buprice, hoga_samount,
                                       hoga_bamount, hoga_tamount, start)

            elif tr_cd == self.tr_cd_trade:
                market = body['exchname']
                if market != 'KRX':
                    return
                int_hms = int(body['chetime'])
                if int_hms < self.market_open or self.dict_set['전략종료시간'] < int_hms:
                    return
                dt = int(f"{self.str_today}{int_hms}")
                code  = body['shcode']
                c     = int(body['price'])
                o     = int(body['open'])
                h     = int(body['high'])
                low   = int(body['low'])
                v     = int(body['cvolume'])
                per   = float(body['drate'])
                dm    = int(body['value'])
                cg    = body['cgubun']
                tbids = int(body['msvolume'])
                tasks = int(body['mdvolume'])
                ch    = float(body['cpower'])
                self._update_tick_data(dt, code, c, o, h, low, per, dm, v, cg, tbids, tasks, ch)

            elif tr_cd == self.tr_cd_vi:
                if body['krx_vi_gubun'] in ('1', '3'):
                    code = body['ex_shcode'][-6:]
                    self._update_vi(code)

            elif tr_cd == self.tr_cd_oper:
                if body['jangubun'] == self.oper_gubun:
                    operation = int(body['jstatus'])
                    if operation in LsRestData.장운영상태:
                        text = LsRestData.장운영상태[operation]
                        self.windowQ.put((ui_num['기본로그'], f'장운영 정보 수신 알림 - {text}'))
                        self.soundQ.put(text)

        except Exception:
            self.windowQ.put((ui_num['시스템로그'], format_exc()))
