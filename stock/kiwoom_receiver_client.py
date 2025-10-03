import os
import sys
import zmq
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QTimer, pyqtSignal
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, ui_num
from utility.static import now, strf_time, strp_time, timedelta_sec, int_hms


class ZmqRecv(QThread):
    signal1 = pyqtSignal(tuple)
    signal2 = pyqtSignal(tuple)
    signal3 = pyqtSignal(int)

    def __init__(self, sstgQs):
        super().__init__()
        self.sstgQs = sstgQs
        zctx = zmq.Context()
        self.sock = zctx.socket(zmq.SUB)
        self.sock.connect('tcp://localhost:5777')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            if msg == 'tickdata':
                self.signal1.emit(data)
            elif msg == 'focuscodes':
                for q in self.sstgQs:
                    q.put(data)
            elif msg == 'logininfo':
                self.signal2.emit(data)
            elif msg == 'operation':
                self.signal3.emit(data)


class Updater(QThread):
    signal = pyqtSignal(tuple)

    def __init__(self, sreceivQ):
        super().__init__()
        self.sreceivQ = sreceivQ

    def run(self):
        while True:
            data = self.sreceivQ.get()
            self.signal.emit(data)


class KiwoomReceiverClient:
    def __init__(self, qlist):
        app = QApplication(sys.argv)

        self.kwzservQ = qlist[0]
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQs   = qlist[3]
        self.dict_set = DICT_SET

        self.dict_name   = {}
        self.dict_code   = {}
        self.dict_sgbn   = {}
        self.dict_jgdt   = {}
        self.tuple_jango = ()
        self.tuple_order = ()
        self.tuple_kosd  = ()
        self.operation   = 1
        self.dict_bool   = {'프로세스종료': False}

        curr_time = now()
        remaintime = (strp_time('%Y%m%d%H%M%S', strf_time('%Y%m%d') + '090100') - curr_time).total_seconds()
        self.holiday_time = timedelta_sec(remaintime) if remaintime > 0 else None

        self.updater = Updater(self.sreceivQ)
        self.updater.signal.connect(self.UpdateTuple)
        self.updater.start()

        self.zmqrecv = ZmqRecv(self.sstgQs)
        self.zmqrecv.signal1.connect(self.UpdateTickData)
        self.zmqrecv.signal2.connect(self.UpdateLoginInfo)
        self.zmqrecv.signal3.connect(self.UpdateOperation)
        self.zmqrecv.start()

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.Scheduler)
        self.qtimer.start()

        text = '주식 리시버를 시작하였습니다.'
        if self.dict_set['주식알림소리']: self.kwzservQ.put(('sound', text))
        self.kwzservQ.put(('tele', text))
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 시작')))

        app.exec_()

    def UpdateTuple(self, data):
        gubun, data = data
        if gubun == '잔고목록':
            self.tuple_jango = data
        elif gubun == '주문목록':
            self.tuple_order = data
        elif gubun == '설정변경':
            self.dict_set = data

    def UpdateTickData(self, data):
        if len(data) == 3:
            code, c, dt = data
            if code in self.tuple_jango and (code not in self.dict_jgdt.keys() or dt > self.dict_jgdt[code]):
                self.straderQ.put((code, c))
                self.dict_jgdt[code] = dt
        else:
            try:
                code, c = data[-3] if self.dict_set['주식타임프레임'] else data[-4], data[1]
                self.sstgQs[self.dict_sgbn[code]].put(data)
                if code in self.tuple_jango or code in self.tuple_order:
                    if self.dict_set['주식타임프레임']:
                        self.straderQ.put((code, c))
                    else:
                        self.straderQ.put(('주문확인', code, c))
            except:
                print('리시버 공유모드는 클라이언트부터 실행하고 서버를 마지막에 실행해야합니다.')

    def UpdateLoginInfo(self, data):
        self.tuple_kosd, self.dict_sgbn, self.dict_name, self.dict_code = data
        self.kwzservQ.put(('window', (ui_num['종목명데이터'], self.dict_name, self.dict_code, self.dict_sgbn, '더미')))
        self.straderQ.put(('종목구분번호', self.dict_sgbn))
        for q in self.sstgQs:
            q.put(('종목구분번호', self.dict_sgbn))
            q.put(('코스닥목록', self.tuple_kosd))

    def UpdateOperation(self, data):
        self.operation = data

    def Scheduler(self):
        curr_time = now()
        inthms = int_hms()
        if self.operation == 1 and self.holiday_time is not None and self.holiday_time <= curr_time:
            if self.dict_set['휴무프로세스종료'] and not self.dict_bool['프로세스종료']:
                self.ReceiverProcKill()
        if self.operation in (2, 3):
            if not self.dict_bool['프로세스종료'] and self.dict_set['주식전략종료시간'] <= inthms and self.dict_set['주식프로세스종료']:
                self.ReceiverProcKill()
        if self.operation == 8 and not self.dict_bool['프로세스종료'] and 153500 <= inthms:
            self.ReceiverProcKill()

    def ReceiverProcKill(self):
        self.dict_bool['프로세스종료'] = True
        self.straderQ.put('프로세스종료')
        QTimer.singleShot(180 * 1000, self.SysExit)

    def SysExit(self):
        if self.qtimer.isActive():   self.qtimer.stop()
        if self.updater.isRunning(): self.updater.quit()
        for q in self.sstgQs:
            q.put('프로세스종료')
        self.kwzservQ.put(('window', (ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료')))
