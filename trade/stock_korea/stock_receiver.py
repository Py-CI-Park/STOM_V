
import sys
from trade.restapi_ls import LsRestData
from PyQt5.QtWidgets import QApplication
from trade.base_receiver import BaseReceiver
from utility.settings.setting_base import ui_num
from trade.restapi_ls import LsRestAPI, LsWebSocketReceiver
from utility.static_method.static import now, error_decorator


class StockReceiver(BaseReceiver):
    """국내 주식 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 국내 주식 시장 데이터를 수신합니다."""
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
        self.dict_info, self.codes = self.ls.get_code_info_stock(self.market_gubun-1)
        if self.dict_info:
            if self.market_gubun == 1:
                self.dict_sgbn = {code: i % 8 for i, code in enumerate(self.dict_info)}
                self.traderQ.put(('종목정보', (self.dict_info, self.dict_sgbn)))
            else:
                self.traderQ.put(('종목정보', self.dict_info))

    @error_decorator
    def _convert_real_data(self, data):
        """실시간 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        if self.dict_bool['프로세스종료']:
            return

        start = now()
        tr_cd = data['header']['tr_cd']
        body  = data['body']

        if tr_cd == self.tr_cd_hoga:
            str_hms = body['hotime']
            if int(str_hms) < self.market_open:
                return

            dt   = int(f"{self.str_today}{str_hms}")
            code = body['shcode']
            hoga_seprice = [
                int(body['offerho1']), int(body['offerho2']), int(body['offerho3']), int(body['offerho4']),
                int(body['offerho5']), int(body['offerho6']), int(body['offerho7']), int(body['offerho8']),
                int(body['offerho9']), int(body['offerho10'])
            ]
            hoga_buprice = [
                int(body['bidho1']), int(body['bidho2']), int(body['bidho3']), int(body['bidho4']),
                int(body['bidho5']), int(body['bidho6']), int(body['bidho7']), int(body['bidho8']),
                int(body['bidho9']), int(body['bidho10'])
            ]
            hoga_samount = [
                int(body['krx_offerrem1']), int(body['krx_offerrem2']), int(body['krx_offerrem3']),
                int(body['krx_offerrem4']), int(body['krx_offerrem5']), int(body['krx_offerrem6']),
                int(body['krx_offerrem7']), int(body['krx_offerrem8']), int(body['krx_offerrem9']),
                int(body['krx_offerrem10'])
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
            str_hms = body['chetime']
            if int(str_hms) < self.market_open:
                return

            dt    = int(f"{self.str_today}{str_hms}")
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
