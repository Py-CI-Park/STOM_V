import os
import sys
import zmq
import time
import sqlite3
import pandas as pd
from threading import Thread
from multiprocessing import Queue
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, DB_STOCK_TICK, ui_num, DB_STOCK_MIN
from utility.static import now, timedelta_sec, roundfigure_upper5, GetVIPrice, str_ymdhms, GetSangHahanga, \
    threading_timer


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


class PutListgsjm(Thread):
    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        while True:
            for q in self.main.sstgQs:
                q.put(('관심목록', tuple(self.main.list_gsjm)))
            if self.main.dict_set['리시버공유'] == 1:
                self.main.recvservQ.put(('focuscodes', ('관심목록', tuple(self.main.list_gsjm))))
            time.sleep(1)


class KiwoomReceiverTick:
    def __init__(self, qlist):
        """
        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQs, self.kiwoomQ
                0            1              2             3           4
        """
        self.kwzservQ    = qlist[0]
        self.sreceivQ    = qlist[1]
        self.straderQ    = qlist[2]
        self.sstgQs      = qlist[3]
        self.dict_set    = DICT_SET

        self.dict_name   = {}
        self.dict_tmdt   = {}
        self.dict_hgbs   = {}
        self.dict_data   = {}
        self.dict_vipr   = {}
        self.dict_sghg   = {}
        self.dict_mtop   = {}
        self.dict_sgbn   = {}
        self.dict_jgdt   = {}

        self.list_hgdt   = [0, 0, 0, 0]
        self.list_gsjm   = []
        self.tuple_jango = ()
        self.tuple_order = ()
        self.tuple_kosd  = ()

        self.int_logt    = 0
        self.int_hgtime  = int(str_ymdhms())
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None

        self.put_list_gsjm = PutListgsjm(self)
        self.put_list_gsjm.daemon = True
        self.put_list_gsjm.start()

        self.recvservQ = Queue()
        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.daemon = True
            self.zmqserver.start()

        if self.dict_set['리시버프로파일링']:
            import cProfile
            self.pr = cProfile.Profile()
            self.pr.enable()

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
            if self.dict_name:
                self.UpdateHogaData(data)
        elif gubun == '체결정보':
            if self.dict_name:
                self.UpdateTickData(data)
        elif gubun == '관심진입':
            self.InsertGsjmlist(data)
        elif gubun == '관심이탈':
            self.DeleteGsjmlist(data)
        elif gubun == 'VI발동해제':
            gubun_, code, name = data
            if gubun_ == '1' and code in self.dict_name and \
                    (code not in self.dict_vipr or (self.dict_vipr[code][0] and now() > self.dict_vipr[code][1])):
                self.UpdateViPrice(code, name)
        elif gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '실시간조건검색시작':
            for code in data:
                self.InsertGsjmlist(code)
        elif gubun == '호가종목코드':
            self.hoga_code = data
        elif gubun == '차트종목코드':
            self.chart_code = data
        elif gubun == '종목정보':
            self.tuple_kosd, self.dict_sgbn, self.dict_name, _ = data
            if self.dict_set['리시버공유'] == 1:
                self.recvservQ.put(('logininfo', data))
        elif gubun == '설정변경':
            self.dict_set = data
        elif gubun == '프로파일링결과':
            self.pr.print_stats(sort='cumulative')

    def UpdateString(self, data):
        if data == '프로세스종료':
            threading_timer(180, self.sreceivQ.put, '프로세스종료실행')
        elif data == '프로세스종료실행':
            if self.dict_set['주식데이터저장']:
                self.SaveData()
            else:
                for q in self.sstgQs:
                    q.put('프로세스종료')
            self.straderQ.put('프로세스종료')
            time.sleep(5)
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료')))

    def InsertGsjmlist(self, code):
        if code not in self.list_gsjm:
            self.list_gsjm.append(code)
            if self.dict_set['주식매도취소관심진입']:
                self.straderQ.put(('관심진입', code))

    def DeleteGsjmlist(self, code):
        if code in self.list_gsjm:
            self.list_gsjm.remove(code)
            if self.dict_set['주식매수취소관심이탈']:
                self.straderQ.put(('관심이탈', code))

    def SaveData(self):
        codes = set()
        if self.dict_mtop:
            if self.dict_set['주식타임프레임']:
                for mtop_text in list(self.dict_mtop.values())[29:]:
                    codes.update(mtop_text.split(';'))
                con = sqlite3.connect(DB_STOCK_TICK)
            else:
                for mtop_text in self.dict_mtop.values():
                    codes.update(mtop_text.split(';'))
                con = sqlite3.connect(DB_STOCK_MIN)
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
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 거래대금순위 저장 완료')))

        self.sstgQs[0].put(('데이터저장', codes))

    def UpdateTickData(self, data):
        code, dt, c, o, h, low, per, dm, v, ch, dmp, jvp, vrp, jsvp, sgta, csp, cbp = data

        if code not in self.dict_vipr:
            self.InsertViPrice(code, o)
        elif not self.dict_vipr[code][0] and now() > self.dict_vipr[code][1]:
            self.UpdateViPrice(code, c)

        if code in self.dict_data:
            bids, asks = self.dict_data[code][13:15]
        else:
            bids, asks = 0, 0

        rf = roundfigure_upper5(c, dt)
        bids_, asks_ = 0, 0
        if '+' in v: bids_ = abs(int(v))
        if '-' in v: asks_ = abs(int(v))
        bids += bids_
        asks += asks_

        self.dict_hgbs[code] = (csp, cbp)
        self.dict_data[code] = [c, o, h, low, per, dm, ch, dmp, jvp, vrp, jsvp, sgta, rf, bids, asks, self.dict_vipr[code][1], self.dict_vipr[code][2], self.dict_vipr[code][-1]]

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.kwzservQ.put(('hoga', (self.dict_name[code], c, per, sgta, self.dict_vipr[code][2], o, h, low)))
                if asks > 0: self.kwzservQ.put(('hoga', (-asks, ch)))
                if bids > 0: self.kwzservQ.put(('hoga', (bids, ch)))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, data):
        dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, name, receivetime, lastprice = data
        sm     = 0
        dm     = 0
        send   = False
        dt_min = int(str(dt)[:12])

        if code in self.dict_data:
            dm = self.dict_data[code][5]
            if code in self.dict_tmdt:
                if dt > self.dict_tmdt[code][0] and hoga_bamount[4] != 0:
                    send = True
            else:
                self.dict_tmdt[code] = [dt, 0]
                send = True
            sm = dm - self.dict_tmdt[code][1]

        if send:
            csp, cbp = self.dict_hgbs[code]

            if hoga_seprice[-1] < csp:
                index = next((i for i, price in enumerate(hoga_seprice[::-1]) if price >= csp), None)
                if index is not None:
                    start_idx = (5 - index) if index < 5 else 0
                    end_idx   = 10 - index
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_seprice = (0,) * add_cnt + hoga_seprice[start_idx:end_idx]
                    hoga_samount = (0,) * add_cnt + hoga_samount[start_idx:end_idx]
                else:
                    hoga_seprice = (0,) * 5
                    hoga_samount = (0,) * 5
            else:
                hoga_seprice = hoga_seprice[-5:]
                hoga_samount = hoga_samount[-5:]

            if hoga_buprice[0] > cbp:
                index = next((i for i, price in enumerate(hoga_buprice) if price <= cbp), None)
                if index is not None:
                    start_idx = index
                    end_idx   = index + 5
                    add_cnt   = (index - 5) if index > 5 else 0
                    hoga_buprice = hoga_buprice[start_idx:end_idx] + (0,) * add_cnt
                    hoga_bamount = hoga_bamount[start_idx:end_idx] + (0,) * add_cnt
                else:
                    hoga_buprice = (0,) * 5
                    hoga_bamount = (0,) * 5
            else:
                hoga_buprice = hoga_buprice[:5]
                hoga_bamount = hoga_bamount[:5]

            c     = self.dict_data[code][0]
            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            gsjm  = 1 if code in self.list_gsjm else 0
            data  = (dt,) + tuple(self.dict_data[code]) + (sm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + \
                hoga_samount + hoga_bamount + (hgjrt, gsjm, code, name, logt)

            self.sstgQs[self.dict_sgbn[code]].put(data)

            if code in self.tuple_jango or code in self.tuple_order:
                self.straderQ.put(('잔고갱신', (code, c)))

            if self.dict_set['리시버공유'] == 1:
                self.recvservQ.put(('tickdata', data))

            self.dict_tmdt[code] = [dt, dm]
            self.dict_data[code][13:15] = [0, 0]

            if logt != 0:
                gap = (now() - receivetime).total_seconds()
                self.kwzservQ.put(('window', (ui_num['S단순텍스트'], f'리시버 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap:.6f}]초입니다.')))
                self.int_logt = dt_min

        if self.int_mtdt is None:
            self.int_mtdt = dt
        elif self.int_mtdt < dt:
            self.dict_mtop[dt] = ';'.join(self.list_gsjm)
            self.int_mtdt = dt

        if self.hoga_code == code and dt > self.list_hgdt[1]:
            self.list_hgdt[1] = dt
            if code in self.dict_sghg:
                shg, hhg = self.dict_sghg[code]
            else:
                shg, hhg = GetSangHahanga(code in self.tuple_kosd, lastprice, self.int_hgtime)
                self.dict_sghg[code] = (shg, hhg)
            self.kwzservQ.put(('hoga', (name,) + hoga_tamount + hoga_seprice[-5:] + hoga_buprice[:5] + hoga_samount[-5:] + hoga_bamount[:5] + (shg, hhg)))

    def InsertViPrice(self, code, o):
        uvi, dvi, hogaunit = GetVIPrice(code in self.tuple_kosd, o, self.int_hgtime)
        self.dict_vipr[code] = [True, timedelta_sec(-3600), uvi, dvi, hogaunit]

    def UpdateViPrice(self, code, key):
        if type(key) == str:
            if code in self.dict_vipr:
                self.dict_vipr[code][:2] = False, timedelta_sec(5)
            else:
                self.dict_vipr[code] = [False, timedelta_sec(5), 0, 0, 0]
            self.kwzservQ.put(('window', (ui_num['S로그텍스트'], f'변동성 완화 장치 발동 - [{code}] {key}')))
        elif type(key) == int:
            uvi, dvi, hogaunit = GetVIPrice(code in self.tuple_kosd, key, self.int_hgtime)
            self.dict_vipr[code] = [True, timedelta_sec(5), uvi, dvi, hogaunit]
