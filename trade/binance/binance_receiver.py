
import re
import sys
import binance
from traceback import format_exc
from PyQt5.QtWidgets import QApplication
from trade.base_receiver import BaseReceiver
from utility.settings.setting_base import ui_num
from trade.restapi_binance import BinanceWebSocketReceiver
from utility.static_method.static import now, now_utc, str_ymd, str_ymdhms_utc


class BinanceReceiver(BaseReceiver):
    """바이낸스 데이터 수신 클래스입니다.
    BaseReceiver를 상속받아 바이낸스 시장 데이터를 수신합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        app = QApplication(sys.argv)

        super().__init__(qlist, dict_set, market_infos)

        self.binance = binance.Client()

        self._get_code_info()
        self._save_code_info_and_noti()

        self.ws_thread = BinanceWebSocketReceiver(self.codes, self.windowQ)
        self.ws_thread.signal.connect(self._convert_real_data)
        self.ws_thread.start()

        app.exec_()

    def _get_code_info(self):
        """종목 정보를 조회합니다."""
        def get_decimal_place(float_):
            float_ = str(float(float_))
            if '.' in float_:
                float_ = float_.split('.')[1]
                return len(float_)
            return 0

        datas = self.binance.futures_exchange_info()
        datas = [x for x in datas['symbols'] if re.search('USDT$', x['symbol']) is not None]
        for data in datas:
            code = data['symbol']
            tick_size = data['filters'][0]['tickSize']
            self.dict_info[code] = {
                '종목명': code,
                '호가단위': float(tick_size),
                '가격소숫점자리수': get_decimal_place(tick_size),
                '수량소숫점자리수': get_decimal_place(data['filters'][2]['minQty'])
            }

        self.traderQ.put(('종목정보', self.dict_info))

        datas = self.binance.futures_ticker()
        datas = [data for data in datas if re.search('USDT$', data['symbol']) is not None]
        ymd   = str_ymd(now_utc())
        for data in datas:
            code = data['symbol']
            if code not in self.dict_data:
                c    = float(data['lastPrice'])
                o    = float(data['openPrice'])
                h    = float(data['highPrice'])
                low  = float(data['lowPrice'])
                per  = round(float(data['priceChangePercent']), 2)
                dm   = float(data['quoteVolume'])
                prec = round(c - float(data['priceChange']), 8)
                self.dict_data[code] = [c, o, h, low, per, dm, 0, 0, 0, 0, 0, c, c, c]
                self.dict_prec[code] = [ymd, prec]
                self.dict_daym[code] = dm

        self.codes = list(self.dict_data)
        self.list_gsjm = \
            [x for x, y in sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:self.mtop_rank]]
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
            stream_name = data['stream']
            data = data['data']

            if '@depth10' in stream_name:
                dt = int(str_ymdhms_utc(data['T']))
                receivetime = now()
                code = data['s']
                asks_data = data['a']
                bids_data = data['b']
                hoga_seprice = [
                    float(asks_data[0][0]), float(asks_data[1][0]), float(asks_data[2][0]), float(asks_data[3][0]),
                    float(asks_data[4][0]), float(asks_data[5][0]), float(asks_data[6][0]), float(asks_data[7][0]),
                    float(asks_data[8][0]), float(asks_data[9][0])
                ]
                hoga_buprice = [
                    float(bids_data[0][0]), float(bids_data[1][0]), float(bids_data[2][0]), float(bids_data[3][0]),
                    float(bids_data[4][0]), float(bids_data[5][0]), float(bids_data[6][0]), float(bids_data[7][0]),
                    float(bids_data[8][0]), float(bids_data[9][0])
                ]
                hoga_samount = [
                    float(asks_data[0][1]), float(asks_data[1][1]), float(asks_data[2][1]), float(asks_data[3][1]),
                    float(asks_data[4][1]), float(asks_data[5][1]), float(asks_data[6][1]), float(asks_data[7][1]),
                    float(asks_data[8][1]), float(asks_data[9][1])
                ]
                hoga_bamount = [
                    float(bids_data[0][1]), float(bids_data[1][1]), float(bids_data[2][1]), float(bids_data[3][1]),
                    float(bids_data[4][1]), float(bids_data[5][1]), float(bids_data[6][1]), float(bids_data[7][1]),
                    float(bids_data[8][1]), float(bids_data[9][1])
                ]
                hoga_tamount = [
                    round(sum(hoga_samount), 8), round(sum(hoga_bamount), 8)
                ]
                self._update_hoga_data(dt, code, hoga_seprice, hoga_buprice, hoga_samount,
                                       hoga_bamount, hoga_tamount, receivetime)

            elif '@aggTrade' in stream_name:
                dt = int(str_ymdhms_utc(data['T']))
                code = data['s']
                c = float(data['p'])
                v = float(data['q'])
                m = data['m']
                self._update_tick_data_coin_future(dt, code, c, v, m)

        except Exception:
            self.windowQ.put((ui_num['시스템로그'], format_exc()))
