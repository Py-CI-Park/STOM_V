
import sqlite3
import numpy as np
import pandas as pd
from trade.restapi_ls import LsRestData
from utility.settings.setting_base import UI_NUM
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from utility.static_method.static import now, timedelta_sec, get_inthms, get_vi_price, qtest_qwait


class MonitorReceivQ(QThread):
    """리시버 큐를 모니터링하는 스레드 클래스입니다.
    수신 큐에서 데이터를 읽어와 시그널로 전송합니다."""
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(str)

    def __init__(self, receivQ):
        super().__init__()
        self.receivQ = receivQ

    def run(self):
        """큐 모니터링 루프를 실행합니다."""
        while True:
            data = self.receivQ.get()
            if data.__class__ == tuple:
                self.signal1.emit(data)
            elif data.__class__ == str:
                if data == '큐스레드종료':
                    break
                self.signal2.emit(data)


class BaseReceiver:
    """실시간 데이터를 수신하고 처리하는 기본 클래스입니다.
    다양한 큐를 통해 다른 모듈과 통신하며,
    시장 데이터(체결, 호가)를 처리합니다."""
    def __init__(self, qlist, dict_set, market_infos):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ, testQ
           0        1       2      3       4      5      6      7       8        9       10     11    12
        """
        self.windowQ      = qlist[0]
        self.soundQ       = qlist[1]
        self.queryQ       = qlist[2]
        self.teleQ        = qlist[3]
        self.hogaQ        = qlist[5]
        self.receivQ      = qlist[8]
        self.traderQ      = qlist[9]
        self.stgQs        = qlist[10]
        self.stgQ         = qlist[10][0]
        self.dict_set     = dict_set
        self.market_gubun = market_infos[0]
        self.market_info  = market_infos[1]

        self.dict_dtdm: dict[str, list]        = {}
        self.dict_data: dict[str, list]        = {}
        self.dict_money: dict[str, list]       = {}
        self.dict_bmbyp: dict[str, np.ndarray] = {}
        self.dict_smbyp: dict[str, np.ndarray] = {}
        self.dict_index: dict[str, dict]       = {}
        self.dict_vipr: dict[str, list]        = {}
        self.dict_dlhp: dict[str, list]        = {}

        self.dict_info = {}
        self.dict_expc = {}
        self.dict_sgbn = {}
        self.dict_sncd = {}
        self.dict_daym = {}
        self.dict_mtop = {}
        self.dict_jgdt = {}
        self.dict_prec = {}
        self.dict_bool = {
            '프로세스종료': False
        }

        self.list_hgdt    = [0, 0, 0, 0]
        self.list_gsjm    = []
        self.codes        = []
        self.tuple_jango  = ()
        self.tuple_order  = ()
        self.tuple_kosd   = ()

        self.lvhp_time    = now()
        self.int_logt     = 0

        self.ls           = None
        self.token        = None
        self.int_mtdt     = None
        self.hoga_code    = None
        self.chart_code   = None
        self.last_gsjm    = None
        self.ws_thread    = None
        self.tr_cd_trade  = None
        self.tr_cd_hoga   = None
        self.tr_cd_oper   = None
        self.tr_cd_vi     = None
        self.oper_gubun   = None

        self.is_tick      = self.dict_set['타임프레임']
        self.access_key   = self.dict_set['access_key']
        self.secret_key   = self.dict_set['secret_key']

        self.market_open  = self.market_info['시작시간']
        self.market_close = self.market_info['프로세스종료시간']
        self.mtop_rank    = self.market_info['거래대금순위']

        self.str_today    = LsRestData.당일일자
        if self.market_gubun not in (5, 9):
            self.tr_cd_trade = LsRestData.실시간거래코드[f"{self.market_info['마켓이름']}체결"]
            self.tr_cd_hoga  = LsRestData.실시간거래코드[f"{self.market_info['마켓이름']}호가"]
            self.tr_cd_oper  = LsRestData.실시간거래코드['장운영정보']
            self.oper_gubun  = LsRestData.장구분[self.market_gubun]
            if self.market_gubun < 4:
                self.tr_cd_vi = LsRestData.실시간거래코드['국내주식VI']

        self.updater = MonitorReceivQ(self.receivQ)
        self.updater.signal1.connect(self._update_tuple)
        self.updater.signal2.connect(self._sys_exit)
        self.updater.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self._scheduler)
        self.qtimer.start()

    def _save_code_info_and_noti(self):
        """종목명 정보를 조회하고 저장 후 리시버 시작 알림을 보냅니다."""
        if self.dict_info:
            dict_name = {code: value['종목명'] for code, value in self.dict_info.items()}
            dict_code = {name: code for code, name in dict_name.items()}

            self.windowQ.put((UI_NUM['종목명데이터'], dict_name, dict_code))
            if self.market_gubun > 5:
                self.stgQ.put(('종목정보', self.dict_info))

            df = pd.DataFrame.from_dict(self.dict_info, orient='index')
            self.queryQ.put(('종목디비', df, self.market_info['종목디비'], 'replace'))

            text = f"{self.market_info['마켓이름']} 시스템을 시작하였습니다."
            self.teleQ.put(text)
            if self.dict_set['알림소리']:
                self.soundQ.put(text)

            self.windowQ.put((UI_NUM['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 리시버 시작"))
        else:
            self.windowQ.put((UI_NUM['시스템로그'], f"오류 알림 - 종목정보 조회 실패 매매 프로세스를 종료합니다."))
            self._sys_exit('강제종료')

    def _update_vi(self, code):
        """정적VI 발동을 기록합니다.
        Args:
            code: 종목 코드
        """
        if code not in self.dict_info:
            return

        if code in self.dict_vipr:
            self.dict_vipr[code][:2] = False, timedelta_sec(5)
        else:
            self.dict_vipr[code] = [False, timedelta_sec(5), 0, 0, 0]

        self.windowQ.put((UI_NUM['기본로그'], f"변동성 완화 장치 발동 - [{code}] {self.dict_info[code]['종목명']}"))

    def _check_vi(self, code, c, o):
        """장시작 최초틱 및 VI발동 이후 최초틱 수신 시 VI가격을 계산합니다.
        Args:
            code: 종목 코드
            c: 현재가
            o: 시작가
        """
        vipr = self.dict_vipr.get(code)
        if vipr is None:
            self._insert_vi_price(code, o)
        elif not vipr[0] and now() > vipr[1]:
            self._update_vi_price(code, c)

    def _insert_vi_price(self, code, o):
        """시가 기준 VI가격을 계산합니다.
        Args:
            code: 종목 코드
            o: 시가
        """
        uvi, dvi, vi_hgunit = get_vi_price(o)
        self.dict_vipr[code] = [True, timedelta_sec(-3600), uvi, dvi, vi_hgunit]

    def _update_vi_price(self, code, price):
        """VI발동 이후 현재가 기준 VI가격을 계산합니다.
        Args:
            code: 종목 코드
            price: 가격
        """
        uvi, dvi, vi_hgunit = get_vi_price(price)
        self.dict_vipr[code] = [True, timedelta_sec(5), uvi, dvi, vi_hgunit]

    def _update_tick_data(self, dt, code, c, o, h, low, per, dm, v=None, cg=None, tbids=None, tasks=None, ch=None):
        """틱 데이터를 업데이트합니다.
        실시간 체결 데이터를 처리합니다 (바이낸스선물 제외).
        Args:
            dt: 데이터 시간
            code: 종목 코드
            c: 현재가
            o: 시작가
            h: 고가
            low: 저가
            per: 등락율
            dm: 당일거래대금
            v: 거래량
            cg: 체결구분
            tbids: 총 매수수량
            tasks: 총 매도수량
            ch: 체결강도
        """
        if self.market_gubun < 4:
            self._check_vi(code, c, o)

        if not self.is_tick and code in self.tuple_jango:
            pre_dt = self.dict_jgdt.get(code)
            if pre_dt is None or dt > pre_dt:
                self.traderQ.put(('잔고갱신', (code, c)))
                self.dict_jgdt[code] = dt

        mo = mh = ml = c
        code_data = self.dict_data.get(code)
        if code_data:
            bids, asks, pretbids, pretasks = code_data[7:11]
            if not self.is_tick:
                if bids == 0 and asks == 0:
                    mo = mh = ml = c
                else:
                    mo, mh, ml = code_data[-3:]
                    if mh < c: mh = c
                    if ml > c: ml = c
        else:
            bids, asks, pretbids, pretasks = 0, 0, 0, 0
            if not self.is_tick:
                mo = mh = ml = c

        if v is None:
            bids_ = round(tbids - pretbids, 8)
            asks_ = round(tasks - pretasks, 8)
        else:
            bids_ = v if cg == '+' else 0
            asks_ = v if cg == '-' else 0

        bids += bids_
        asks += asks_

        if tbids is None:
            tbids = pretbids + bids_
            tasks = pretasks + asks_

        if ch is None:
            ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500

        self.dict_daym[code] = dm

        if self.market_gubun < 4:
            sgta = int(c * self.dict_info[code]['상장주식수'] / 100_000_000)
            _, vi_dt, uvi, _, vi_hgunit = self.dict_vipr[code]
            if self.is_tick:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, sgta, vi_dt, uvi, vi_hgunit]
            else:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, sgta, vi_dt, uvi, vi_hgunit, mo, mh, ml]
        elif self.market_gubun == 4:
            sgta = int(c * self.dict_info[code]['상장주식수'] / 100_000)
            if self.is_tick:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, sgta]
            else:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, sgta, mo, mh, ml]
        else:
            if self.is_tick:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]
            else:
                self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        self._update_money_factor(code, c, int(c * bids_), int(c * asks_))
        if self.hoga_code == code:
            self._update_hoga_window_tick(dt, code, bids_, asks_, c, per, o, h, low, ch)

    def _update_tick_data_coin_future(self, dt, code, c, v, m):
        """코인 선물 틱 데이터를 업데이트합니다.
        실시간 체결 데이터를 처리합니다 (바이낸스선물용).
        Args:
            dt: 데이터 시간
            code: 종목 코드
            c: 현재가
            v: 거래량
            m: 매수여부
        """
        if not self.is_tick and code in self.tuple_jango:
            pre_dt = self.dict_jgdt.get(code)
            if pre_dt is None or dt > pre_dt:
                self.traderQ.put(('잔고갱신', (code, c)))
                self.dict_jgdt[code] = dt

        mo = mh = ml = c
        ymd = str(dt)[:8]
        code_data = self.dict_data[code]
        code_prec = self.dict_prec[code]
        if ymd != code_prec[0]:
            code_prec[0] = ymd
            code_prec[1] = code_data[0]
            bids, asks, pretbids, pretasks = 0, 0, 0, 0
            o, h, low = c, c, c
            dm = int(v * c)
            if not self.is_tick:
                mo = mh = ml = c
        else:
            dm, _, bids, asks, pretbids, pretasks = code_data[5:11]
            o, h, low = code_data[1:4]
            if c > h: h = c
            if c < low: low = c
            dm = int(dm + v * c)
            if not self.is_tick:
                if bids == 0 and asks == 0:
                    mo = mh = ml = c
                else:
                    mo, mh, ml = code_data[-3:]
                    if mh < c: mh = c
                    if ml > c: ml = c

        bids_ = v if not m else 0
        asks_ = 0 if not m else v
        bids += bids_
        asks += asks_
        tbids = round(pretbids + bids_, 8)
        tasks = round(pretasks + asks_, 8)
        ch = min(500, round(tbids / tasks * 100, 2)) if tasks > 0 else 500
        per = round((c / code_prec[1] - 1) * 100, 2)

        self.dict_daym[code] = dm
        if self.is_tick:
            self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]
        else:
            self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks, mo, mh, ml]

        self._update_money_factor(code, c, int(c * bids_), int(c * asks_))
        if self.hoga_code == code:
            self._update_hoga_window_tick(dt, code, bids_, asks_, c, per, o, h, low, ch)

        dt_ = int(str(dt)[:13])
        data_dlhp = self.dict_dlhp.get(code)
        if data_dlhp:
            if dt_ != data_dlhp[0]:
                data_dlhp[0] = dt_
                data_dlhp[1] = round((h / low - 1) * 100, 2)
        else:
            self.dict_dlhp[code] = [dt_, round((h / low - 1) * 100, 2)]

    def _update_money_factor(self, code, c, buy_money, sell_money):
        """머니 팩터를 업데이트합니다.
        Args:
            code: 종목 코드
            c: 현재가
            buy_money: 매수 금액
            sell_money: 매도 금액
        """
        if code not in self.dict_money:
            """초당(분당)매수금액, 초당(분당)매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격
                      0               1            2          3          4          5          6          7"""
            self.dict_money[code] = [buy_money, sell_money, buy_money, buy_money, c, sell_money, sell_money, c]
            self.dict_index[code] = {c: 0}
            self.dict_bmbyp[code] = np.zeros(2000, dtype=np.float64)
            self.dict_smbyp[code] = np.zeros(2000, dtype=np.float64)
            self.dict_bmbyp[code][0] = buy_money
            self.dict_smbyp[code][0] = sell_money
            self.dict_index[code]['count'] = 1
        else:
            money_arr = self.dict_money[code]
            price_idx = self.dict_index[code]
            buy_arr = self.dict_bmbyp[code]
            sell_arr = self.dict_smbyp[code]

            money_arr[0] += buy_money
            money_arr[1] += sell_money
            money_arr[2] += buy_money
            money_arr[5] += sell_money

            idx = price_idx.get(c)
            if idx is not None:
                buy_arr[idx] += buy_money
                sell_arr[idx] += sell_money
            else:
                idx = price_idx['count']
                if idx >= len(buy_arr):
                    self.dict_bmbyp[code] = np.resize(buy_arr, len(buy_arr) * 2)
                    self.dict_smbyp[code] = np.resize(sell_arr, len(sell_arr) * 2)
                    buy_arr = self.dict_bmbyp[code]
                    sell_arr = self.dict_smbyp[code]

                price_idx[c] = idx
                buy_arr[idx] = buy_money
                sell_arr[idx] = sell_money
                price_idx['count'] += 1

            if buy_arr[idx] >= money_arr[3]:
                money_arr[3] = buy_arr[idx]
                money_arr[4] = c
            if sell_arr[idx] >= money_arr[6]:
                money_arr[6] = sell_arr[idx]
                money_arr[7] = c

    def _update_hoga_window_tick(self, dt, code, bids_, asks_, c, per, o, h, low, ch):
        """호가 윈도우 틱을 업데이트합니다.
        Args:
            dt: 날짜시간
            code: 종목 코드
            bids_: 매수 호가
            asks_: 매도 호가
            c: 현재가
            per: 등락율
            o: 시가
            h: 고가
            low: 저가
            ch: 체결
        """
        bids, asks = self.list_hgdt[2:4]
        if bids_ > 0: bids += bids_
        if asks_ > 0: asks += asks_
        self.list_hgdt[2:4] = bids, asks
        if dt > self.list_hgdt[0]:
            name = self.dict_info[code]['종목명']
            self.hogaQ.put((name, c, per, 0, -1, o, h, low))
            if asks > 0: self.hogaQ.put((-asks, ch))
            if bids > 0: self.hogaQ.put((bids, ch))
            self.list_hgdt[0] = dt
            self.list_hgdt[2:4] = [0, 0]

    def _update_hoga_data(self, dt, code, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, hoga_tamount,
                          receivetime):
        """호가 데이터를 업데이트합니다.
        Args:
            dt: 날짜시간
            code: 종목 코드
            hoga_seprice: 호가 매도 가격
            hoga_buprice: 호가 매수 가격
            hoga_samount: 호가 매도 수량
            hoga_bamount: 호가 매수 수량
            hoga_tamount: 호가 총 수량
            receivetime: 호가 데이터 수신 시간
        """
        send = False
        dt_min = int(str(dt)[:12])
        dt_std = dt if self.is_tick else dt_min

        code_data = self.dict_data.get(code)
        money_arr = self.dict_money.get(code)
        if code_data and money_arr:
            code_dtdm = self.dict_dtdm.get(code)
            if code_dtdm:
                if dt_std > code_dtdm[0] and (self.market_gubun > 3 or hoga_bamount[4] != 0):
                    send = True
            else:
                self.dict_dtdm[code] = [dt_std, 0]
                code_dtdm = self.dict_dtdm[code]
                if self.is_tick:
                    send = True

            if send or (
                    not self.is_tick and
                    (code == self.chart_code or self.market_gubun in (6, 7, 8) or code in self.list_gsjm)
            ):
                hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount = self._correction_hoga_data(
                    code_data[0], hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount
                )

                send_data, c, dm, logt = self._get_send_data(
                    code, code_data, code_dtdm, money_arr, hoga_samount, hoga_bamount, hoga_seprice,
                    hoga_buprice, hoga_tamount, dt, dt_min
                )

                if not self.is_tick:
                    send_data.append(send)

                if self.market_gubun in (1, 4):
                    self.stgQs[self.dict_sgbn[code]].put(send_data)
                else:
                    self.stgQ.put(send_data)

                if self.is_tick and (code in self.tuple_order or code in self.tuple_jango):
                    self.traderQ.put(('잔고갱신', (code, c)))

                if self.is_tick or send:
                    if not self.is_tick and code in self.tuple_order:
                        self.traderQ.put(('주문확인', (code, c)))

                    code_dtdm[0] = dt_std
                    code_dtdm[1] = dm
                    code_data[7] = 0
                    code_data[8] = 0
                    money_arr[0] = 0
                    money_arr[1] = 0

                if logt != 0:
                    self._send_log(dt_min, receivetime)

        self._update_money_top(dt_std)
        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self._update_hoga_window_rem(dt, code, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount)

    def _correction_hoga_data(self, curr_price, hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount):
        """호가 데이터를 보정합니다.
        Args:
            curr_price: 현재가
            hoga_seprice: 호가 매도 가격
            hoga_samount: 호가 매도 수량
            hoga_buprice: 호가 매수 가격
            hoga_bamount: 호가 매수 수량
        """
        if len(hoga_seprice) == 10:
            if hoga_seprice[0] < curr_price:
                valid_indices = [i for i, price in enumerate(hoga_seprice) if price >= curr_price]
                start_idx = valid_indices[0] if valid_indices else None
                if start_idx is not None:
                    end_idx = min(start_idx + 5, 10)
                    add_cnt = max(start_idx - 5, 0)
                    hoga_seprice = hoga_seprice[start_idx:end_idx] + [0.] * add_cnt
                    hoga_samount = hoga_samount[start_idx:end_idx] + [0.] * add_cnt
                else:
                    hoga_seprice = [0.] * 5
                    hoga_samount = [0.] * 5
            else:
                hoga_seprice = hoga_seprice[:5]
                hoga_samount = hoga_samount[:5]

            if hoga_buprice[0] > curr_price:
                valid_indices = [i for i, price in enumerate(hoga_buprice) if price <= curr_price]
                start_idx = valid_indices[0] if valid_indices else None
                if start_idx is not None:
                    end_idx = min(start_idx + 5, 10)
                    add_cnt = max(start_idx - 5, 0)
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + [0.] * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + [0.] * add_cnt
                else:
                    hoga_buprice = [0.] * 5
                    hoga_bamount = [0.] * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]
        else:
            if hoga_seprice[0] < curr_price:
                valid_indices = [i for i, price in enumerate(hoga_seprice) if price >= curr_price]
                start_idx = valid_indices[0] if valid_indices else None
                if start_idx is not None:
                    hoga_seprice = hoga_seprice[start_idx:] + [0.] * start_idx
                    hoga_samount = hoga_samount[start_idx:] + [0] * start_idx
                else:
                    hoga_seprice = [0.] * 5
                    hoga_samount = [0.] * 5

            if hoga_buprice[0] > curr_price:
                valid_indices = [i for i, price in enumerate(hoga_buprice) if price <= curr_price]
                start_idx = valid_indices[0] if valid_indices else None
                if start_idx is not None:
                    hoga_buprice = hoga_buprice[start_idx:] + [0.] * start_idx
                    hoga_bamount = hoga_bamount[start_idx:] + [0] * start_idx
                else:
                    hoga_buprice = [0.] * 5
                    hoga_bamount = [0.] * 5

        return hoga_seprice, hoga_samount, hoga_buprice, hoga_bamount

    def _get_send_data(self, code, code_data, code_dtdm, money_arr, hoga_samount, hoga_bamount,
                       hoga_seprice, hoga_buprice, hoga_tamount, dt, dt_min):
        """전송 데이터를 생성합니다.
        Args:
            code: 종목 코드
            code_data: 코드 데이터
            code_dtdm: 코드 데이터타임
            money_arr: 머니 배열
            hoga_samount: 호가 매도 수량
            hoga_bamount: 호가 매수 수량
            hoga_tamount: 호가 총 수량
            hoga_seprice: 호가 매도 가격
            hoga_buprice: 호가 매수 가격
        Returns:
            전송 데이터 튜플
        """
        c, _, h, low, _, dm, _, bids, asks = code_data[:9]
        tm   = dm - code_dtdm[1]
        hlp  = round((c / ((h + low) / 2) - 1) * 100, 2)
        lhp  = round((h / low - 1) * 100, 2)
        hjt  = sum(hoga_samount + hoga_bamount)
        gsjm = 1 if self.market_gubun in (6, 7, 8) or code in self.list_gsjm else 0
        name = self.dict_info[code]['종목명']
        logt = now() if self.int_logt < dt_min else 0

        if not self.is_tick or self.market_gubun < 5:
            time_frame_data = code_data[:9] + code_data[11:]
            if not self.is_tick:
                dt = code_dtdm[0]
        else:
            time_frame_data = code_data[:9]

        send_data = [dt] + time_frame_data + [tm, hlp, lhp] + money_arr + hoga_seprice + hoga_buprice + \
            hoga_samount + hoga_bamount + hoga_tamount + [hjt, gsjm, code, name, logt]
        return send_data, c, dm, logt

    def _send_log(self, dt_min, receivetime):
        """로그를 전송합니다.
        Args:
            dt_min: 날짜시간 분
            receivetime: 수신 시간
        """
        gap = (now() - receivetime).total_seconds()
        self.windowQ.put((UI_NUM['타임로그'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))
        self.int_logt = dt_min

    def _update_money_top(self, dt_std):
        """거래대금 순위를 업데이트합니다.
        Args:
            dt_std: 날짜시간 표준
        """
        if self.int_mtdt is None:
            self.int_mtdt = dt_std
        elif self.int_mtdt < dt_std:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt_std

    def _update_hoga_window_rem(self, dt, code, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount):
        """호가 윈도우 잔량을 업데이트합니다.
        Args:
            dt: 날짜시간
            code: 종목 코드
            hoga_tamount: 호가 총 수량
            hoga_seprice: 호가 매도 가격
            hoga_buprice: 호가 매수 가격
            hoga_samount: 호가 매도 수량
            hoga_bamount: 호가 매수 수량
        """
        self.list_hgdt[1] = dt
        name = self.dict_info[code]['종목명']
        self.hogaQ.put(
            [name] + hoga_tamount + hoga_seprice[:5][::-1] + hoga_buprice[:5] +
            hoga_samount[:5][::-1] + hoga_bamount[:5]
        )

    def _scheduler(self):
        """스케줄러를 실행합니다."""
        if self.dict_daym:
            self._money_top_search()

        inthms = get_inthms(self.market_gubun)
        A = self.dict_set['전략종료시간'] < inthms < self.dict_set['전략종료시간'] + 10 and self.dict_set['프로세스종료']
        B = self.market_close < inthms < self.market_close + 10
        if not self.dict_bool['프로세스종료'] and (A or B):
            self._receiver_process_kill()

        if self.market_gubun not in (6, 7, 8):
            current_gsjm = tuple(self.list_gsjm)
            if current_gsjm != self.last_gsjm:
                if self.market_gubun in (1, 4):
                    for q in self.stgQs:
                        q.put(('관심목록', current_gsjm))
                else:
                    self.stgQ.put(('관심목록', current_gsjm))
                self.last_gsjm = current_gsjm

        if self.market_gubun == 9:
            curr_time = now()
            if not self.dict_set['바이낸스선물고정레버리지'] and curr_time > self.lvhp_time:
                if self.dict_dlhp:
                    self.traderQ.put(('저가대비고가등락율', self.dict_dlhp))
                self.lvhp_time = timedelta_sec(300)

    def _money_top_search(self):
        """머니 탑을 검색합니다."""
        sorted_daym = sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:self.mtop_rank]
        if self.market_gubun in (6, 7, 8):
            list_mtop = [self.dict_info[x]['종목명'] for x, y in sorted_daym]
        else:
            list_mtop = [x for x, y in sorted_daym]
        insert_set = set(list_mtop) - set(self.list_gsjm)
        delete_set = set(self.list_gsjm) - set(list_mtop)
        if insert_set:
            for code in insert_set:
                self._insert_gsjm_list(code)
        if delete_set:
            for code in delete_set:
                self._delete_gsjm_list(code)

    def _insert_gsjm_list(self, code):
        """관심종목 리스트에 추가합니다.
        Args:
            code: 종목코드
        """
        self.list_gsjm.append(code)
        if self.market_gubun not in (6, 7, 8) and self.dict_set['매도취소관심진입']:
            self.traderQ.put(('관심진입', code))

    def _delete_gsjm_list(self, code):
        """관심종목 리스트에서 삭제합니다.
        Args:
            code: 종목코드
        """
        self.list_gsjm.remove(code)
        if self.market_gubun not in (6, 7, 8) and self.dict_set['매수취소관심이탈']:
            self.traderQ.put(('관심이탈', code))

    def _receiver_process_kill(self):
        """리시버 프로세스를 종료합니다."""
        self.dict_bool['프로세스종료'] = True
        self._websocket_kill()
        if self.dict_set['알림소리']:
            self.soundQ.put(f"{self.market_info['마켓이름']} 시스템을 3분 후 종료합니다.")
        QTimer.singleShot(180 * 1000, lambda: self.receivQ.put('프로세스종료'))

    def _websocket_kill(self):
        """웹소켓을 종료합니다."""
        if self.ws_thread:
            self.ws_thread.stop()
            self.ws_thread.terminate()
            self.ws_thread = None

    def _update_tuple(self, data):
        """튜플을 업데이트합니다.
        Args:
            data: 데이터
        """
        gubun, data = data
        if gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '호가종목코드':
            self.hoga_code = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '수동데이터저장':
            self._save_moneytop()
        elif gubun == '설정변경':
            self.dict_set = data

    def _sys_exit(self, data):
        """시스템을 종료합니다.
        Args:
            data: 데이터
        """
        self._websocket_kill()

        if data == '프로세스종료' and self.dict_set['데이터저장']:
            self._save_moneytop()

        if self.market_gubun in (1, 4):
            for q in self.stgQs:
                q.put(data)
        else:
            self.stgQ.put(data)
        self.traderQ.put(data)

        if data != '프로그램종료':
            exit_text = '리시버 종료' if data == '프로세스종료' else '리시버 STOP'
            self.windowQ.put((UI_NUM['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} {exit_text}"))

        import sys
        qtest_qwait(1)
        self.receivQ.put('큐스레드종료')
        self.updater.wait()
        sys.exit()

    def _save_moneytop(self):
        """거래대금 순위 데이터를 저장합니다."""
        codes = set()
        if self.dict_mtop:
            mtop_list = list(self.dict_mtop.values())
            if self.is_tick:
                mtop_list = mtop_list[29:]

            for mtop_text in mtop_list:
                codes.update(mtop_text.split(';'))

            con = sqlite3.connect(self.market_info['당일디비'][self.is_tick])
            df = pd.DataFrame(self.dict_mtop.values(), columns=['거래대금순위'], index=self.dict_mtop.keys())
            df.to_sql('moneytop', con, if_exists='append', chunksize=2000)
            con.close()

            self.windowQ.put((UI_NUM['기본로그'], f"시스템 명령 실행 알림 - {self.market_info['마켓이름']} 거래대금순위 저장 완료"))

        if self.market_gubun in (1, 4):
            self.stgQs[0].put(('데이터저장', codes))
        else:
            self.stgQ.put(('데이터저장', codes))
