import zmq
import time
import sqlite3
import pyupbit
import operator
import numpy as np
import pandas as pd
from threading import Thread
from multiprocessing import Process, Queue
from coin.upbit_websocket import WebSocketReceiver
from utility.setting import ui_num, DICT_SET, DB_COIN_TICK, DB_COIN_MIN
from utility.static import now, strf_time, timedelta_sec, from_timestamp, int_hms_utc, threading_timer


class ZmqServ(Thread):
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


class UpbitReceiverTick:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ  = qlist[0]
        self.soundQ   = qlist[1]
        self.queryQ   = qlist[2]
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
            '거래대금순위검색': curr_time
        }

        self.dict_tmdt   = {}
        self.dict_jgdt   = {}
        self.dict_data   = {}
        self.dict_daym   = {}
        self.dict_mtop   = {}

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

        self.recvservQ   = Queue()
        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqServ(self.recvservQ)
            self.zmqserver.start()

        self.MainLoop()

    def MainLoop(self):
        text = '코인 리시버를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작'))
        self.GetTickers()
        self.WebSocketsStart(self.creceivQ)
        while True:
            data = self.creceivQ.get()
            curr_time = now()
            inthmsutc = int_hms_utc()
            if type(data) == tuple:
                self.UpdateTuple(data)
            elif type(data) == dict:
                if data['type'] == 'ticker':
                    try:
                        dt        = int(strf_time('%Y%m%d%H%M%S', from_timestamp(int(data['timestamp'] / 1000 - 32400))))
                        if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]): continue
                        code      = data['code']
                        c         = data['trade_price']
                        o         = data['opening_price']
                        h         = data['high_price']
                        low       = data['low_price']
                        per = round(data['signed_change_rate'] * 100, 2)
                        tbids     = data['acc_bid_volume']
                        tasks     = data['acc_ask_volume']
                        dm        = data['acc_trade_price']
                    except Exception as e:
                        self.windowQ.put((ui_num['C단순텍스트'], f'시스템 명령 오류 알림 - 웹소켓 ticker {e}'))
                    else:
                        self.UpdateTickData(code, c, o, h, low, per, dm, tbids, tasks, dt)
                elif data['type'] == 'orderbook':
                    try:
                        dt   = int(strf_time('%Y%m%d%H%M%S', from_timestamp(int(data['timestamp'] / 1000 - 32400))))
                        if self.dict_set['코인전략종료시간'] < int(str(dt)[8:]): continue
                        code = data['code']
                        hoga_tamount = (
                            data['total_ask_size'], data['total_bid_size']
                        )
                        data = data['orderbook_units']
                        hoga_seprice = (
                            data[9]['ask_price'], data[8]['ask_price'], data[7]['ask_price'], data[6]['ask_price'], data[5]['ask_price'],
                            data[4]['ask_price'], data[3]['ask_price'], data[2]['ask_price'], data[1]['ask_price'], data[0]['ask_price']
                        )
                        hoga_buprice = (
                            data[0]['bid_price'], data[1]['bid_price'], data[2]['bid_price'], data[3]['bid_price'], data[4]['bid_price'],
                            data[5]['bid_price'], data[6]['bid_price'], data[7]['bid_price'], data[8]['bid_price'], data[9]['bid_price']
                        )
                        hoga_samount = (
                            data[9]['ask_size'], data[8]['ask_size'], data[7]['ask_size'], data[6]['ask_size'], data[5]['ask_size'],
                            data[4]['ask_size'], data[3]['ask_size'], data[2]['ask_size'], data[1]['ask_size'], data[0]['ask_size']
                        )
                        hoga_bamount = (
                            data[0]['bid_size'], data[1]['bid_size'], data[2]['bid_size'], data[3]['bid_size'], data[4]['bid_size'],
                            data[5]['bid_size'], data[6]['bid_size'], data[7]['bid_size'], data[8]['bid_size'], data[9]['bid_size']
                        )
                    except Exception as e:
                        self.windowQ.put((ui_num['C단순텍스트'], f'시스템 명령 오류 알림 - 웹소켓 orderbook {e}'))
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

            if (self.dict_set['코인전략종료시간'] < inthmsutc < self.dict_set['코인전략종료시간'] + 10 and not self.dict_bool['프로세스종료'] and self.dict_set['코인프로세스종료']) or \
                    (235000 < inthmsutc < 235010 and not self.dict_bool['프로세스종료']):
                self.ReceiverProcKill()

    def WebSocketsStart(self, q):
        self.proc_webs = Process(target=WebSocketReceiver, args=(self.codes, q), daemon=True)
        self.proc_webs.start()

    def WebProcessKill(self):
        if self.proc_webs is not None and self.proc_webs.is_alive(): self.proc_webs.kill()

    def GetTickers(self):
        self.codes = pyupbit.get_tickers(fiat="KRW")
        last = len(self.codes)
        for i, code in enumerate(self.codes):
            time.sleep(0.05)
            df = pyupbit.get_ohlcv(ticker=code)
            if df is not None:
                self.dict_daym[code] = df['value'].iloc[-1]
            print(f'분봉 데이터 조회 중 ... [{i+1}/{last}][{code}]')

        self.list_gsjm = [x for x, y in sorted(self.dict_daym.items(), key=operator.itemgetter(1), reverse=True)[:10]]
        data = tuple(self.list_gsjm)
        self.cstgQ.put(('관심목록', data))
        if self.dict_set['리시버공유'] == 1:
            self.recvservQ.put(('focuscodes', ('관심목록', data)))

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

    def UpdateTickData(self, code, c, o, h, low, per, dm, tbids, tasks, dt):
        if code in self.dict_data.keys():
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
            self.soundQ.put('업비트 시스템을 3분 후 종료합니다.')

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
