import re
import zmq
import time
import sqlite3
import binance
import operator
import numpy as np
import pandas as pd
from threading import Thread
from multiprocessing import Process, Queue
from coin.binance_websocket import WebSocketReceiver
from utility.setting import ui_num, DICT_SET, DB_COIN_TICK, DB_COIN_MIN
from utility.static import now, strf_time, timedelta_sec, from_timestamp, int_hms_utc, threading_timer


class ZmqServ(Thread):
    def __init__(self, recvservQ):
        super().__init__()
        self.recvservQ = recvservQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:5779')

    def run(self):
        while True:
            msg, data = self.recvservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)


class BinanceReceiverTick:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ  = qlist[0]
        self.soundQ   = qlist[1]
        self.teleQ    = qlist[3]
        self.hogaQ    = qlist[5]
        self.creceivQ = qlist[8]
        self.ctraderQ = qlist[9]
        self.cstgQ    = qlist[10]
        self.dict_set = DICT_SET

        self.dict_bool = {
            '프로세스종료': False
        }

        curr_time = now()
        self.dict_time = {
            '거래대금순위전송': curr_time,
            '거래대금순위검색': curr_time,
            '저가대비고가등락율갱신': curr_time
        }

        self.dict_tmdt   = {}
        self.dict_jgdt   = {}
        self.dict_data   = {}
        self.dict_daym   = {}
        self.dict_mtop   = {}
        self.dict_tddt   = {}
        self.dict_dlhp   = {}

        self.list_hgdt   = [0, 0, 0, 0]
        self.list_gsjm   = []
        self.tuple_jango = ()
        self.tuple_order = ()

        self.int_logt    = int(strf_time('%Y%m%d%H%M', timedelta_sec(-32400)))
        self.int_mtdt    = None
        self.hoga_code   = None
        self.chart_code  = None
        self.proc_webs   = None
        self.codes       = None
        self.binance     = binance.Client()

        self.recvservQ = Queue()
        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.start()

        self.MainLoop()

    def MainLoop(self):
        text = '코인 리시버를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작'))
        self.codes = self.GetTickers()
        self.WebSocketsStart(self.creceivQ)
        while True:
            data = self.creceivQ.get()
            curr_time = now()
            inthmsutc = int_hms_utc()
            if type(data) == tuple:
                self.UpdateTuple(data)
            elif type(data) == list:
                if data[0] == 'trade':
                    try:
                        data = data[1]['data']
                        dt   = int(strf_time('%Y%m%d%H%M%S', from_timestamp(int(data['T']) / 1000 - 32400)))
                        code = data['s']
                        c    = float(data['p'])
                        v    = float(data['q'])
                        m    = data['m']
                    except Exception as e:
                        self.windowQ.put((ui_num['C단순텍스트'], f'시스템 명령 오류 알림 - 웹소켓 trade {e}'))
                    else:
                        self.UpdateTradeData(code, c, v, m, dt)
                elif data[0] == 'depth':
                    try:
                        data = data[1]['data']
                        dt   = int(strf_time('%Y%m%d%H%M%S', from_timestamp(int(data['T']) / 1000 - 32400)))
                        if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]): continue
                        code = data['s']
                        hoga_seprice = (
                            float(data['a'][9][0]), float(data['a'][8][0]), float(data['a'][7][0]), float(data['a'][6][0]), float(data['a'][5][0]),
                            float(data['a'][4][0]), float(data['a'][3][0]), float(data['a'][2][0]), float(data['a'][1][0]), float(data['a'][0][0])
                        )
                        hoga_buprice = (
                            float(data['b'][0][0]), float(data['b'][1][0]), float(data['b'][2][0]), float(data['b'][3][0]), float(data['b'][4][0]),
                            float(data['b'][5][0]), float(data['b'][6][0]), float(data['b'][7][0]), float(data['b'][8][0]), float(data['b'][9][0])
                        )
                        hoga_samount = (
                            float(data['a'][9][1]), float(data['a'][8][1]), float(data['a'][7][1]), float(data['a'][6][1]), float(data['a'][5][1]),
                            float(data['a'][4][1]), float(data['a'][3][1]), float(data['a'][2][1]), float(data['a'][1][1]), float(data['a'][0][1])
                        )
                        hoga_bamount = (
                            float(data['b'][0][1]), float(data['b'][1][1]), float(data['b'][2][1]), float(data['b'][3][1]), float(data['b'][4][1]),
                            float(data['b'][5][1]), float(data['b'][6][1]), float(data['b'][7][1]), float(data['b'][8][1]), float(data['b'][9][1])
                        )
                        hoga_tamount = (
                            round(sum(hoga_samount), 8), round(sum(hoga_bamount), 8)
                        )
                    except Exception as e:
                        self.windowQ.put((ui_num['C단순텍스트'], f'시스템 명령 오류 알림 - 웹소켓 depth {e}'))
                    else:
                        self.UpdateHogaData(dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, curr_time)
            elif data == '프로세스종료':
                self.SysExit()
                break

            if curr_time > self.dict_time['거래대금순위전송']:
                self.UpdateMoneyTop()
                self.dict_time['거래대금순위전송'] = timedelta_sec(1)

            if curr_time > self.dict_time['거래대금순위검색']:
                self.MoneyTopSearch()
                self.dict_time['거래대금순위검색'] = timedelta_sec(10)

            if not self.dict_set['바이낸스선물고정레버리지'] and curr_time > self.dict_time['저가대비고가등락율갱신']:
                if len(self.dict_dlhp) > 0:
                    self.ctraderQ.put(('저가대비고가등락율', self.dict_dlhp))
                self.dict_time['저가대비고가등락율갱신'] = timedelta_sec(300)

            if (self.dict_set['코인전략종료시간'] < inthmsutc < self.dict_set['코인전략종료시간'] + 10 and not self.dict_bool['프로세스종료'] and self.dict_set['코인프로세스종료']) or \
                    (235000 < inthmsutc < 235010 and not self.dict_bool['프로세스종료']):
                self.ReceiverProcKill()

    def WebSocketsStart(self, q):
        self.proc_webs = Process(target=WebSocketReceiver, args=(self.codes, q), daemon=True)
        self.proc_webs.start()

    def WebProcessKill(self):
        if self.proc_webs is not None and self.proc_webs.is_alive(): self.proc_webs.kill()

    def GetTickers(self):
        dict_daym = {}
        try:
            datas = self.binance.futures_ticker()
        except Exception as e:
            print(e)
        else:
            datas = [data for data in datas if re.search('USDT$', data['symbol']) is not None]
            ymd   = strf_time('%Y%m%d', timedelta_sec(-32400))
            for data in datas:
                code = data['symbol']
                if code not in self.dict_data.keys():
                    c    = float(data['lastPrice'])
                    o    = float(data['openPrice'])
                    h    = float(data['highPrice'])
                    low  = float(data['lowPrice'])
                    per  = round(float(data['priceChangePercent']), 2)
                    dm   = float(data['quoteVolume'])
                    prec = round(c - float(data['priceChange']), 8)
                    self.dict_data[code] = [c, o, h, low, per, dm, 0, 0, 0, 0, 0, c, c, c]
                    self.dict_tddt[code] = [ymd, prec]
                    dict_daym[code] = dm

        self.list_gsjm = [x for x, y in sorted(dict_daym.items(), key=operator.itemgetter(1), reverse=True)[:10]]
        data = tuple(self.list_gsjm)
        self.cstgQ.put(('관심목록', data))
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('focuscodes', ('관심목록', data)))

        return list(self.dict_data.keys())

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

    def UpdateTradeData(self, code, c, v, m, dt):
        ymd = str(dt)[:8]
        if ymd != self.dict_tddt[code][0]:
            self.dict_tddt[code] = [ymd, self.dict_data[code][0]]
            bids, asks, pretbids, pretasks = 0, 0, 0, 0
            o, h, low = c, c, c
            dm = round(v * c, 2)
        else:
            bids, asks, pretbids, pretasks = self.dict_data[code][7:]
            o, h, low = self.dict_data[code][1:4]
            if c > h: h = c
            if c < low: low = c
            dm = round(self.dict_data[code][5] + v * c, 2)

        bids_ = v if not m else 0
        asks_ = 0 if not m else v
        bids += bids_
        asks += asks_
        tbids = round(pretbids + bids_, 8)
        tasks = round(pretasks + asks_, 8)
        try:
            ch = round(tbids / tasks * 100, 2)
        except:
            ch = 500.
        if ch > 500: ch = 500.
        per = round((c / self.dict_tddt[code][1] - 1) * 100, 2)

        self.dict_data[code] = [c, o, h, low, per, dm, ch, bids, asks, tbids, tasks]
        self.dict_daym[code] = dm

        dt_ = int(str(dt)[:13])
        if code not in self.dict_dlhp.keys() or dt_ != self.dict_dlhp[code][0]:
            self.dict_dlhp[code] = [dt_, round((h / low - 1) * 100, 2)]

        if self.hoga_code == code:
            bids, asks = self.list_hgdt[2:4]
            if bids_ > 0: bids += bids_
            if asks_ > 0: asks += asks_
            self.list_hgdt[2:4] = bids, asks
            if dt > self.list_hgdt[0]:
                self.hogaQ.put((code, c, per, 0, 0, o, h, low))
                if asks > 0: self.hogaQ.put((-asks, ch))
                if bids > 0: self.hogaQ.put((bids, ch))
                self.list_hgdt[0] = dt
                self.list_hgdt[2:4] = [0, 0]

    def UpdateHogaData(self, dt, hoga_tamount, hoga_seprice, hoga_buprice, hoga_samount, hoga_bamount, code, receivetime):
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
                send = True
            sm = dm - self.dict_tmdt[code][1]

        if send:
            c = self.dict_data[code][0]

            if hoga_seprice[-1] < c:
                index = 0
                for i, price in enumerate(hoga_seprice[::-1]):
                    if price >= c:
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

            if hoga_buprice[0] > c:
                index = 0
                for i, price in enumerate(hoga_buprice):
                    if price <= c:
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

            hlp   = round((c / ((self.dict_data[code][2] + self.dict_data[code][3]) / 2) - 1) * 100, 2)
            hgjrt = sum(hoga_samount + hoga_bamount)
            logt  = now() if self.int_logt < dt_min else 0
            gsjm  = 1 if code in self.list_gsjm else 0
            data  = (dt,) + tuple(self.dict_data[code][:9]) + (sm, hlp) + hoga_tamount + hoga_seprice + hoga_buprice + hoga_samount + hoga_bamount + (hgjrt, gsjm, code, logt)

            self.cstgQ.put(data)
            if code in self.tuple_order or code in self.tuple_jango:
                self.ctraderQ.put((code, c))

            if self.dict_set['리시버공유'] == 1:
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

    def UpdateMoneyTop(self):
        data = tuple(self.list_gsjm)
        self.cstgQ.put(('관심목록', data))
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('focuscodes', ('관심목록', data)))

    def MoneyTopSearch(self):
        if len(self.dict_daym) > 0:
            list_mtop = [x for x, y in sorted(self.dict_daym.items(), key=operator.itemgetter(1), reverse=True)[:10]]
            insert_set = set(list_mtop) - set(self.list_gsjm)
            delete_set = set(self.list_gsjm) - set(list_mtop)
            if len(insert_set) > 0:
                for code in insert_set:
                    self.InsertGsjmlist(code)
            if len(delete_set) > 0:
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
        self.ctraderQ.put('프로세스종료')
        self.WebProcessKill()
        threading_timer(180, self.creceivQ.put, '프로세스종료')
        if self.dict_set['코인알림소리']:
            self.soundQ.put('바이낸스 시스템을 3분 후 종료합니다.')

    def SysExit(self):
        if self.dict_set['코인데이터저장']:
            self.SaveData()
        else:
            self.cstgQ.put('프로세스종료')
        time.sleep(5)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료'))
        time.sleep(1)

    def SaveData(self):
        codes = []
        if len(self.dict_mtop) > 0:
            codes = list(set(';'.join(list(self.dict_mtop.values())).split(';')))
            con = sqlite3.connect(DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN)
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
            self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 거래대금순위 저장 완료'))

        self.cstgQ.put(('데이터저장', codes))
