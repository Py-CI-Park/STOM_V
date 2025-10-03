import os
import sys
import zmq
from threading import Thread
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, ui_num
from utility.static import threading_timer


class ZmqRecv(Thread):
    def __init__(self, sreceivQ):
        super().__init__()
        self.sreceivQ = sreceivQ
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.SUB)
        self.sock.connect('tcp://localhost:5777')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            self.sreceivQ.put((msg, data))


class KiwoomReceiverClient:
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

        self.dict_sgbn   = {}
        self.dict_jgdt   = {}

        self.tuple_jango = ()
        self.tuple_order = ()

        self.zmqrecv = ZmqRecv(self.sreceivQ)
        self.zmqrecv.daemon = True
        self.zmqrecv.start()

        text = '주식 리시버를 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작')))

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
        if gubun == 'tickdata':
            self.UpdateTickData(data)
        elif gubun == 'focuscodes':
            for q in self.sstgQs:
                q.put(data)
        elif gubun == 'logininfo':
            self.UpdateLoginInfo(data)
        elif gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '설정변경':
            self.dict_set = data

    def UpdateTickData(self, data):
        if len(data) == 3:
            code, c, dt = data
            if code in self.tuple_jango and (code not in self.dict_jgdt or dt > self.dict_jgdt[code]):
                self.straderQ.put((code, c))
                self.dict_jgdt[code] = dt
        else:
            try:
                code, c = data[-3] if self.dict_set['주식타임프레임'] else data[-4], data[1]
                self.sstgQs[self.dict_sgbn[code]].put(data)
                if self.dict_set['주식타임프레인']:
                    if code in self.tuple_jango or code in self.tuple_order:
                        self.straderQ.put(('주문확인', code, c))
                else:
                    if code in self.tuple_order:
                        self.straderQ.put(('주문확인', code, c))
            except:
                print('리시버 공유모드는 클라이언트부터 실행하고 서버를 마지막에 실행해야합니다.')

    def UpdateLoginInfo(self, data):
        tuple_kosd, self.dict_sgbn, dict_name, dict_code = data
        self.kwzservQ.put(('window', (ui_num['종목명데이터'], dict_name, dict_code)))
        self.straderQ.put(('종목구분번호', self.dict_sgbn))
        for q in self.sstgQs:
            q.put(('코스닥목록', tuple_kosd))

    def UpdateString(self, data):
        if data == '프로세스종료':
            threading_timer(180, self.sreceivQ.put, '프로세스종료실행')
        elif data == '프로세스종료실행':
            for q in self.sstgQs:
                q.put('프로세스종료')
            self.straderQ.put('프로세스종료')
            self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료')))
