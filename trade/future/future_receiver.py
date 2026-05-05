
import sys
from traceback import format_exc
from PyQt5.QtWidgets import QApplication
from trade.base_receiver import BaseReceiver
from utility.static_method.static import now
from utility.settings.setting_base import ui_num
from trade.restapi_ls import LsRestAPI, LsRestData, LsWebSocketReceiver


class FutureReceiver(BaseReceiver):
    """선물 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 선물 시장 데이터를 수신합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        app = QApplication(sys.argv)

        super().__init__(qlist, dict_set, market_infos)

        self.ls = LsRestAPI(self.windowQ, self.access_key, self.secret_key)
        self.token = self.ls.create_token()

        self._get_code_info()
        self._save_code_info_and_noti()

        self.ws_thread = LsWebSocketReceiver(self.market_info['마켓이름'], self.token, self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

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
        if self.dict_bool['프로세스종료']:
            return

        try:
            start = now()
            tr_cd = data['header']['tr_cd']
            body  = data['body']

            if tr_cd == self.tr_cd_hoga:
                int_hms = int(body['hotime'])
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
                        text = LsRestData.장운영상태[operation]
                        self.windowQ.put((ui_num['기본로그'], f'장운영 정보 수신 알림 - {text}'))
                        self.soundQ.put(text)

        except Exception:
            self.windowQ.put((ui_num['시스템로그'], format_exc()))
