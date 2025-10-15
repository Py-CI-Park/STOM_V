import sys
import zmq
import time
import sqlite3
import pyupbit
import pandas as pd
from multiprocessing import Queue
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from coin.upbit_websocket import WebSocketReceiver
from utility.setting import ui_num, DICT_SET, DB_COIN_TICK, DB_COIN_MIN
from utility.static import now, timedelta_sec, threading_timer, str_ymdhms_utc, str_hms, now_utc, get_logger


class ZmqServ(QThread):
    def __init__(self, recvservQ):
        super().__init__()
        self.recvservQ = recvservQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:5778')

    def run(self):
        while True:
            msg, data = self.recvservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)


class Updater(QThread):
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal()

    def __init__(self, creceivQ):
        super().__init__()
        self.creceivQ = creceivQ

    def run(self):
        while True:
            data = self.creceivQ.get()
            if type(data) == tuple:
                self.signal1.emit(data)
            elif type(data) == str:
                self.signal2.emit()


class UpbitReceiverTick:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        app = QApplication(sys.argv)

        self.windowQ     = qlist[0]
        self.soundQ      = qlist[1]
        self.queryQ      = qlist[2]
        self.teleQ       = qlist[3]
        self.hogaQ       = qlist[5]
        self.creceivQ    = qlist[8]
        self.ctraderQ    = qlist[9]
        self.cstgQ       = qlist[10]
        self.dict_set    = DICT_SET

        self.logger      = get_logger(self.__class__.__name__)

        self.dict_tmdt   = {}
        self.dict_jgdt   = {}
        self.dict_data   = {}
        self.dict_daym   = {}
        self.dict_mtop   = {}

        self.list_hgdt   = [0, 0, 0, 0]
        self.list_gsjm   = []
        self.tuple_jango = ()
        self.tuple_order = ()

        self.int_logt    = 0
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None
        self.codes       = None
        self.last_gsjm   = None

        self.dict_bool   = {
            '프로세스종료': False
        }
        self.dict_time = {
            '거래대금순위검색': now()
        }

        self.GetTickers()

        self.recvservQ = Queue()
        if self.dict_set['에이전트공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.daemon = True
            self.zmqserver.start()

        self.ws_thread = WebSocketReceiver(self.codes)
        self.ws_thread.signal1.connect(self.UpdateTickData)
        self.ws_thread.signal2.connect(self.UpdateHogaData)
        self.ws_thread.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.Scheduler)
        self.qtimer.start()

        self.updater = Updater(self.creceivQ)
        self.updater.signal1.connect(self.UpdateTuple)
        self.updater.signal2.connect(self.SysExit)
        self.updater.start()

        app.exec_()

    def GetTickers(self):
        self.codes = pyupbit.get_tickers(fiat="KRW")
        url = "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW"
        headers = {"accept": "application/json"}
        import requests
        data = requests.get(url, headers=headers).json()
        self.dict_daym = {d['market']: int(d['acc_trade_price']) for d in data}
        self.list_gsjm = [x for x, y in sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:10]]
        data = tuple(self.list_gsjm)
        self.cstgQ.put(('관심목록', data))
        if self.dict_set['에이전트공유'] == 1:
            self.recvservQ.put(('focuscodes', ('관심목록', data)))

        text = '코인 리시버를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작'))
        self.logger.info('리시버 시작 완료')

    def UpdateTickData(self, data):
        try:
            dt = int(str_ymdhms_utc(data['timestamp']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code  = data['code']
            c     = data['trade_price']
            o     = data['opening_price']
            h     = data['high_price']
            low   = data['low_price']
            per   = round(data['signed_change_rate'] * 100, 2)
            tbids = data['acc_bid_volume']
            tasks = data['acc_ask_volume']
            dm    = data['acc_trade_price']
        except:
            return

        if code in self.dict_data:
            bids, asks, pretbids, pretasks = self.dict_data[code][7:]
        else:
            bids, asks, pretbids, pretasks = 0, 0, tbids, tasks

        bids_ = round(tbids - pretbids, 8)
        asks_ = round(tasks - pretasks, 8)
        bids += bids_
        asks += asks_
        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.

        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]
        self.dict_daym[code] = dm

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.hogaQ.put((code, c, per, 0, -1, o, h, low))
                if asks > 0: self.hogaQ.put((-asks, ch))
                if bids > 0: self.hogaQ.put((bids, ch))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, data):
        try:
            dt = int(str_ymdhms_utc(data['timestamp']))
            if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]):
                return

            code = data['code']
            hoga_tamount = (
                data['total_ask_size'], data['total_bid_size']
            )
            data = data['orderbook_units']
            hoga_seprice = (
                data[9]['ask_price'], data[8]['ask_price'], data[7]['ask_price'], data[6]['ask_price'],
                data[5]['ask_price'],
                data[4]['ask_price'], data[3]['ask_price'], data[2]['ask_price'], data[1]['ask_price'],
                data[0]['ask_price']
            )
            hoga_buprice = (
                data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'],
                data[4]['bid_price'],
                data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'], data[8]['bid_price'],
                data[9]['bid_price']
            )
            hoga_samount = (
                data[9]['ask_size'], data[8]['ask_size'], data[7]['ask_size'], data[6]['ask_size'], data[5]['ask_size'],
                data[4]['ask_size'], data[3]['ask_size'], data[2]['ask_size'], data[1]['ask_size'], data[0]['ask_size']
            )
            hoga_bamount = (
                data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'], data[4]['bid_size'],
                data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'], data[8]['bid_size'], data[9]['bid_size']
            )
            receivetime = now()
        except:
            return

        sm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data:
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt:
                if dt > self.dict_tmdt[code][0]:
                    send = True
            else:
                self.dict_tmdt[code] = [dt, 0]
                send = True
            sm = dm - self.dict_tmdt[code][1]

        if send:
            c = self.dict_data[code][0]
            csp, cbp = c, c

            if hoga_seprice[-1] < csp:
                index = next((i for i, price in enumerate(hoga_seprice[::-1]) if price >= csp), None)
                if index is not None:
                    start_idx = (5 - index) if index < 5 else 0
                    end_idx   = 10 - index
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_seprice = (0.,) * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = (0.,) * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = (0.,) * 5
                    hoga_samount = (0.,) * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = next((i for i, price in enumerate(hoga_buprice) if price <= cbp), None)
                if index is not None:
                    start_idx = index
                    end_idx   = index + 5
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + (0.,) * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + (0.,) * add_cnt
                else:
                    hoga_buprice = (0.,) * 5
                    hoga_bamount = (0.,) * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            gsjm  = 1 if code in self.list_gsjm else 0
            data  = (dt,) + tuple(self.dict_data[code][:9]) + (sm, hlp) + \
                hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + \
                (hgjrt, gsjm, code, logt)

            self.cstgQ.put(data)
            if code in self.tuple_order or code in self.tuple_jango:
                self.ctraderQ.put(('잔고갱신', (code, c)))

            if self.dict_set['에이전트공유'] == 1:
                self.recvservQ.put(('tickdata', data))

            self.dict_tmdt[code] = [dt, dm]
            self.dict_data[code][7:9] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.windowQ.put((ui_num['C단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.'))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt
        elif self.int_mtdt < dt:
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.hogaQ.put((code,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5])

    def Scheduler(self):
        self.UpdateMoneyTop()

        curr_time = now()
        inthmsutc = int(str_hms(now_utc()))
        if curr_time > self.dict_time['거래대금순위검색']:
            self.MoneyTopSearch()
            self.dict_time['거래대금순위검색'] = timedelta_sec(10)

        if not self.dict_bool['프로세스종료'] and \
                ((self.dict_set['코인전략종료시간'] < inthmsutc < self.dict_set['코인전략종료시간'] + 10 and self.dict_set['코인프로세스종료']) or 235000 < inthmsutc < 235010):
            self.ReceiverProcKill()

    def UpdateMoneyTop(self):
        current_gsjm = tuple(self.list_gsjm)
        if current_gsjm != self.last_gsjm:
            self.cstgQ.put(('관심목록', current_gsjm))
            if self.dict_set['에이전트공유'] == 1:
                self.recvservQ.put(('focuscodes', ('관심목록', current_gsjm)))
            self.last_gsjm = current_gsjm

    def MoneyTopSearch(self):
        if self.dict_daym:
            list_mtop = [x for x, y in sorted(self.dict_daym.items(), key=lambda x: x[1], reverse=True)[:10]]
            insert_set = set(list_mtop) - set(self.list_gsjm)
            delete_set = set(self.list_gsjm) - set(list_mtop)
            if insert_set:
                for code in insert_set:
                    self.InsertGsjmlist(code)
            if delete_set:
                for code in delete_set:
                    self.DeleteGsjmlist(code)

    def InsertGsjmlist(self, code):
        if code not in self.list_gsjm:
            self.list_gsjm.append(code)
            if self.dict_set['코인매도취소관심진입']:
                self.ctraderQ.put(('관심진입', code))

    def DeleteGsjmlist(self, code):
        if code in self.list_gsjm:
            self.list_gsjm.remove(code)
            if self.dict_set['코인매수취소관심이탈']:
                self.ctraderQ.put(('관심이탈', code))

    def ReceiverProcKill(self):
        self.dict_bool['프로세스종료'] = True
        self.WebProcessKill()
        threading_timer(180, self.creceivQ.put, '프로세스종료')
        if self.dict_set['코인알림소리']:
            self.soundQ.put('업비트 시스템을 3분 후 종료합니다.')

    def WebProcessKill(self):
        if self.ws_thread:
            self.ws_thread.stop()
            self.ws_thread.terminate()

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '호가종목코드':
            self.hoga_code = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '설정변경':
            self.dict_set = data
            if not self.dict_set['코인리시버'] and not self.dict_set['코인트레이더']:
                self.creceivQ.put('프로세스종료')

    def SysExit(self):
        if self.dict_set['코인데이터저장']:
            self.SaveData()
        else:
            self.cstgQ.put('프로세스종료')
        self.ctraderQ.put('프로세스종료')
        time.sleep(5)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료'))

    def SaveData(self):
        codes = set()
        if self.dict_mtop:
            for mtop_text in self.dict_mtop.values():
                codes.update(mtop_text.split(';'))
            con = sqlite3.connect(DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN)
            last_index = 0
            try:
                df = pd.read_sql(f'SELECT * FROM moneytop ORDER BY "index" DESC LIMIT 1', con)
                last_index = df['index'][0]
            except:
                pass
            dict_mtop = {key: value for key, value in self.dict_mtop.items() if key > last_index}
            df = pd.DataFrame(dict_mtop.values(), columns=['거래대금순위'], index=list(dict_mtop))
            df.to_sql('moneytop', con, if_exists='append', chunksize=1000)
            con.close()
            self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 거래대금순위 저장 완료'))

        self.logger.info('거래대금순위 저장 완료')
        self.cstgQ.put(('데이터저장', codes))
