import zmq
import time
from threading import Thread
from utility.setting import ui_num, DICT_SET
from utility.static import threading_timer, str_hms, now_utc


class ZmqRecv(Thread):
    def __init__(self, creceivQ, cstgQ, ctraderQ):
        super().__init__()
        self.creceivQ = creceivQ
        self.cstgQ    = cstgQ
        self.ctraderQ = ctraderQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.SUB)
        self.sock.connect(f'tcp://localhost:5778')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            if msg == 'tickdata':
                self.creceivQ.put(data)
            elif msg == 'updatecodes':
                self.ctraderQ.put(data)
            elif msg == 'focuscodes':
                self.cstgQ.put(data)


class UpbitReceiverClient:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ     = qlist[0]
        self.soundQ      = qlist[1]
        self.teleQ       = qlist[3]
        self.hogaQ       = qlist[5]
        self.creceivQ    = qlist[8]
        self.ctraderQ    = qlist[9]
        self.cstgQ       = qlist[10]
        self.dict_set    = DICT_SET

        self.dict_bool   = {'프로세스종료': False}
        self.tuple_jango = ()
        self.tuple_order = ()
        self.dict_jgdt   = {}

        if self.dict_set['리시버공유'] == 1:
            self.zmqserver = ZmqRecv(self.creceivQ, self.cstgQ, self.ctraderQ)
            self.zmqserver.daemon = True
            self.zmqserver.start()

        self.MainLoop()

    def MainLoop(self):
        text = '코인 리시버를 시작하였습니다.'
        if self.dict_set['코인알림소리']: self.soundQ.put(text)
        self.teleQ.put(text)
        self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작'))
        while True:
            data = self.creceivQ.get()
            if type(data) == tuple:
                if len(data) != 2:
                    self.UpdateTickData(data)
                else:
                    self.UpdateTuple(data)
            elif type(data) == str:
                self.UpdateString(data)

            inthmsutc = int(str_hms(now_utc()))
            if self.dict_set['코인전략종료시간'] < inthmsutc < self.dict_set['코인전략종료시간'] + 10:
                if self.dict_set['코인프로세스종료'] and not self.dict_bool['프로세스종료']:
                    self.ReceiverProcKill()

    def UpdateTickData(self, data):
        if len(data) == 3:
            code, c, dt = data
            if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
                self.ctraderQ.put((code, c))
                self.dict_jgdt[code] = dt
        else:
            try:
                code, c = data[-2] if self.dict_set['코인타임프레임'] else data[-3], data[1]
                self.cstgQ.put(data)
                if code in self.tuple_jango or code in self.tuple_order:
                    if self.dict_set['코인타임프레임']:
                        self.ctraderQ.put((code, c))
                    else:
                        self.ctraderQ.put(('주문확인', code, c))
            except:
                print('리시버 공유모드는 클라이언트부터 실행하고 서버를 마지막에 실행해야합니다.')

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data

    def UpdateString(self, data):
        if data == '프로세스종료':
            self.ctraderQ.put('프로세스종료')
            self.cstgQ.put('프로세스종료')
            time.sleep(5)
            self.windowQ.put((ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료'))

    def ReceiverProcKill(self):
        self.dict_bool['프로세스종료'] = True
        threading_timer(180, self.creceivQ.put, '프로세스종료')
