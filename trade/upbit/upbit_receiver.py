
import sys
from traceback import format_exc
from PyQt5.QtWidgets import QApplication
from trade.base_receiver import BaseReceiver
from utility.settings.setting_base import ui_num
from trade.restapi_upbit import get_symbols_info
from trade.restapi_upbit import UpbitWebSocketReceiver
from utility.static_method.static import now, str_ymdhms_utc


class UpbitReceiver(BaseReceiver):
    """업비트 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 업비트 시장 데이터를 수신합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        app = QApplication(sys.argv)

        super().__init__(qlist, dict_set, market_infos)

        self._get_code_info()
        self._save_code_info_and_noti()

        self.ws_thread = UpbitWebSocketReceiver(self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

        app.exec_()

    def _get_code_info(self):
        """종목 정보를 조회합니다."""
        self.dict_info, self.codes = get_symbols_info()
        if self.dict_info:
            self.traderQ.put(('종목정보', self.dict_info))
            self.dict_daym = {code: value['거래대금'] for code, value in self.dict_info.items() if '거래대금' in value.keys()}
            self.list_gsjm = [x for x, y in sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:self.mtop_rank]]
            data = tuple(self.list_gsjm)
            self.stgQ.put(('관심목록', data))

    def _convert_real_data(self, data):
        """실시간 데이터를 변환합니다.
        Args:
            data: 데이터
        """
        if self.dict_bool['프로세스종료']:
            return

        try:
            if data['type'] == 'orderbook':
                dt = int(str_ymdhms_utc(data['timestamp']))
                if self.dict_set['전략종료시간'] < dt % 1000000:
                    return

                receivetime = now()
                code = data['code']
                hoga_tamount = [
                    data['total_ask_size'], data['total_bid_size']
                ]
                data = data['orderbook_units']
                hoga_seprice = [
                    data[0]['ask_price'], data[1]['ask_price'], data[2]['ask_price'], data[3]['ask_price'],
                    data[4]['ask_price'], data[5]['ask_price'], data[6]['ask_price'], data[7]['ask_price'],
                    data[8]['ask_price'], data[9]['ask_price']
                ]
                hoga_buprice = [
                    data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'],
                    data[4]['bid_price'], data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'],
                    data[8]['bid_price'], data[9]['bid_price']
                ]
                hoga_samount = [
                    data[0]['ask_size'], data[1]['ask_size'], data[2]['ask_size'], data[3]['ask_size'],
                    data[4]['ask_size'], data[5]['ask_size'], data[6]['ask_size'], data[7]['ask_size'],
                    data[8]['ask_size'], data[9]['ask_size']
                ]
                hoga_bamount = [
                    data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'],
                    data[4]['bid_size'], data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'],
                    data[8]['bid_size'], data[9]['bid_size']
                ]
                self._update_hoga_data(dt, code, hoga_seprice, hoga_buprice, hoga_samount,
                                       hoga_bamount, hoga_tamount, receivetime)

            elif data['type'] == 'ticker':
                dt    = int(str_ymdhms_utc(data['timestamp']))
                code  = data['code']
                c     = data['trade_price']
                o     = data['opening_price']
                h     = data['high_price']
                low   = data['low_price']
                per   = round(data['signed_change_rate'] * 100, 2)
                dm    = data['acc_trade_price']
                tbids = data['acc_bid_volume']
                tasks = data['acc_ask_volume']
                self._update_tick_data(dt, code, c, o, h, low, per, dm, tbids=tbids, tasks=tasks)

        except Exception:
            self.windowQ.put((ui_num['시스템로그'], format_exc()))
