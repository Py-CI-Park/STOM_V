import os
import sys
import zmq
import time
import sqlite3
import numpy as np
import pandas as pd
from threading import Thread
from multiprocessing import Queue
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, ui_num, DB_FUTURE_MIN, DB_FUTURE_TICK
from utility.static import now, threading_timer


class ZmqServ(Thread):
    def __init__(self, recvservQ):
        super().__init__()
        self.recvservQ = recvservQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.PUB)
        self.sock.bind('tcp://*:5777')

    def run(self):
        while True:
            msg, data = self.recvservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)


class FutureReceiverTick:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQ, self.futureQ
                0            1              2             3           4
        """
        self.kwzservQ = qlist[0]
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQ    = qlist[3]
        self.dict_set = DICT_SET

        self.dict_tmdt   = {}
        self.dict_hgbs   = {}
        self.dict_data   = {}
        self.dict_jgdt   = {}
        self.dict_info   = {}
        self.dict_mtop   = {}

        self.list_gsjm   = []
        self.list_hgdt   = [0, 0, 0, 0]
        self.tuple_jango = ()
        self.tuple_order = ()

        self.int_logt    = 0
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None

        self.recvservQ = Queue()
        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.daemon = True
            self.zmqserver.start()

        self.Mainloop()

    def Mainloop(self):
        self.kwzservQ.put(('window', (ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 리시버 시작')))
        while True:
            data = self.sreceivQ.get()
            if type(data) == tuple:
                self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '호가정보':
            if self.dict_info: self.UpdateHogaData(data)
        elif gubun == '체결정보':
            if self.dict_info: self.UpdateTickData(data)
        elif gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '호가종목코드':
            self.hoga_code = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '종목정보':
            self.dict_info = data
            if self.dict_set['리시버공유'] == 1:
                self.recvservQ.put(('logininfo', self.dict_info))
        elif gubun == '설정변경':
            self.dict_set = data

    def UpdateString(self, data):
        if data == '프로세스종료':
            threading_timer(180, self.sreceivQ.put, '프로세스종료실행')
        elif data == '프로세스종료실행':
            self.SysExit()

    def SysExit(self):
        if self.dict_set['주식데이터저장']:
            self.SaveData()
        self.sstgQ.put('프로세스종료')
        self.straderQ.put('프로세스종료')
        time.sleep(5)
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료')))

    def SaveData(self):
        if self.dict_mtop:
            con = sqlite3.connect(DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN)
            last_index = 0
            try:
                df = pd.read_sql(f'SELECT * FROM moneytop ORDER BY "index" DESC LIMIT 1', con)
                last_index = df['index'][0]
            except:
                pass
            df = {key: value for key, value in self.dict_mtop.items() if key > last_index}
            df = pd.DataFrame(df.values(), columns=['거래대금순위'], index=list(df.keys()))
            df.to_sql('moneytop', con, if_exists='append', chunksize=1000)
            con.close()
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 데이터수집목록 저장 완료')))

    def UpdateTickData(self, data):
        code, dt, c, o, h, low, per, v, csp, cbp = data

        if code not in self.dict_data.keys():
            dm, bids, asks, tbids, tasks = 0, 0, 0, 0, 0
        else:
            dm, _, bids, asks, tbids, tasks = self.dict_data[code][5:11]

        bids_, asks_ = 0, 0
        wtm = self.dict_info[code]['위탁증거금']
        if '+' in v:
            bids_ = abs(int(v))
            dm   += int(bids_ * wtm)
        if '-' in v:
            asks_ = abs(int(v))
            dm   += int(asks_ * wtm)
        bids += bids_
        asks += asks_
        tbids += bids_
        tasks += asks_

        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]

        if code not in self.list_gsjm:
            self.list_gsjm.append(code)

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.kwzservQ.put(('hoga', (self.dict_info[code]['종목명'], c, per, 0, 0, o, h, low)))
                if asks > 0: self.kwzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.kwzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, data):
        dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, receivetime = data
        sm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data.keys():
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt.keys():
                if dt > self.dict_tmdt[code][0]:
                    send = True
            else:
                self.dict_tmdt[code] = [dt, 0]
            sm = dm - self.dict_tmdt[code][1]

        if send:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = 0
                for i, price in enumerate(hoga_seprice[::-1]):
                    if price >= csp:
                        index = i
                        break
                if index <= 5:
                    hoga_seprice = hoga_seprice[5 - index:10 - index]
                    hoga_samount = hoga_samount[5 - index:10 - index]
                else:
                    hoga_seprice = tuple(np.zeros(index - 5)) + hoga_seprice[:10 - index]
                    hoga_samount = tuple(np.zeros(index - 5)) + hoga_samount[:10 - index]
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = 0
                for i, price in enumerate(hoga_buprice):
                    if price <= cbp:
                        index = i
                        break
                hoga_buprice = hoga_buprice[index:index + 5]
                hoga_bamount = hoga_bamount[index:index + 5]
                if index > 5:
                    hoga_buprice = hoga_buprice + tuple(np.zeros(index - 5))
                    hoga_bamount = hoga_bamount + tuple(np.zeros(index - 5))
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            c     = self.dict_data[code][0]
            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            data  = (dt,) + tuple(self.dict_data[code][:9]) + (sm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + (hgjrt, 1, code, name, logt)

            self.sstgQ.put(data)
            if code in self.tuple_jango or code in self.tuple_order:
                self.straderQ.put(('잔고갱신', (code, c)))

            if self.dict_set['리시버공유'] == 1:
                self.recvservQ.put(('tickdata', data))

            self.dict_tmdt[code] = [dt, dm]
            self.dict_data[code][7:9] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt
        elif self.int_mtdt < dt and str(self.int_mtdt)[-4:] < '1600':
            self.dict_mtop[self.int_mtdt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt
            self.list_gsjm = []

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            self.kwzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5]))
