import os
import sys
import zmq
import win32gui
import subprocess
from PyQt5.QtWidgets import QApplication
from multiprocessing import Process, Queue
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from kiwoom_trader import KiwoomTrader
from kiwoom_receiver_min import KiwoomReceiverMin
from kiwoom_strategy_min import KiwoomStrategyMin
from kiwoom_receiver_tick import KiwoomReceiverTick
from kiwoom_strategy_tick import KiwoomStrategyTick
from kiwoom_receiver_client import KiwoomReceiverClient
from login_kiwoom.manuallogin import find_window
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, LOGIN_PATH
from utility.static import now, timedelta_sec, int_hms, qtest_qwait, opstarter_kill


class ZmqRecv(QThread):
    signal1 = pyqtSignal(str)
    signal2 = pyqtSignal(tuple)

    def __init__(self, qlist, port_num):
        super().__init__()
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQs   = qlist[3]

        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.SUB)
        self.sock.connect(f'tcp://localhost:{port_num}')
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')

    def run(self):
        while True:
            msg  = self.sock.recv_string()
            data = self.sock.recv_pyobj()
            if msg == 'receiver':
                self.sreceivQ.put(data)
            elif msg == 'trader':
                self.straderQ.put(data)
            elif msg == 'strategy':
                for q in self.sstgQs:
                    q.put(data)
            elif msg == 'manager':
                if type(data) == str:
                    self.signal1.emit(data)
                elif type(data) == tuple:
                    self.signal2.emit(data)
                if data == '통신종료':
                    QThread.sleep(1)
                    break
        self.sock.close()
        self.zctx.term()


class ZmqServ(QThread):
    def __init__(self, qlist, port_num):
        super().__init__()
        self.kwzservQ = qlist[0]
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQs   = qlist[3]

        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:{port_num}')

    def run(self):
        int_hms_ = int_hms()
        while True:
            msg, data = self.kwzservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)
            if int_hms() > int_hms_:
                sstgQs_size = sum([q.qsize() for q in self.sstgQs])
                qsize_data  = ('qsize', (self.sreceivQ.qsize(), self.straderQ.qsize(), sstgQs_size))
                self.sock.send_string('qsize', zmq.SNDMORE)
                self.sock.send_pyobj(qsize_data)
                int_hms_ = int_hms()
            if type(data) == str and data == '통신종료':
                QThread.sleep(1)
                break
        self.sock.close()
        self.zctx.term()


class KiwoomManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.kwzservQ, self.sreceivQ, self.straderQ, sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q = \
            Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue()
        self.sstgQs   = [sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q]
        self.qlist    = [self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQs]
        self.dict_set = DICT_SET

        self.backtest_engine      = False
        self.proc_receiver_stock  = None
        self.proc_strategy_stock1 = None
        self.proc_strategy_stock2 = None
        self.proc_strategy_stock3 = None
        self.proc_strategy_stock4 = None
        self.proc_strategy_stock5 = None
        self.proc_strategy_stock6 = None
        self.proc_strategy_stock7 = None
        self.proc_strategy_stock8 = None
        self.proc_trader_stock    = None

        self.zmqrecv = ZmqRecv(self.qlist, port_num)
        self.zmqrecv.signal1.connect(self.UpdateString)
        self.zmqrecv.signal2.connect(self.UpdateTuple)
        self.zmqrecv.start()

        self.zmqserv = ZmqServ(self.qlist, port_num + 1)
        self.zmqserv.start()

        QTimer.singleShot(5 * 1000, lambda: self.kwzservQ.put(('window', '키움매니저구동완료')))
        app.exec_()

    def UpdateString(self, data):
        if data == '주식수동시작':
            self.StockManualStart()
        elif data == '리시버 종료':
            self.StockReceiverProcessKill()
        elif data == '전략연산 종료':
            self.StockStrategyProcessKill()
        elif data == '트레이더 종료':
            self.StockTraderProcessKill()
        elif data == '통신종료':
            self.ManagerProcessKill()
        elif data == '백테엔진구동':
            self.backtest_engine = True

    def UpdateTuple(self, data):
        if data[0] == '설정변경':
            self.dict_set = data[1]
            if self.StockStrategyProcessAlive():
                for q in self.sstgQs:
                    q.put(('설정변경', self.dict_set))
            if self.StockReceiverProcessAlive():
                self.sreceivQ.put(('설정변경', self.dict_set))
            if self.StockTraderProcessAlive():
                self.straderQ.put(('설정변경', self.dict_set))

    def StockManualStart(self):
        if self.backtest_engine:
            print('백테엔진 구동 중에는 로그인할 수 없습니다.')
            return
        if self.dict_set['리시버공유'] < 2 and self.dict_set['아이디2'] is None:
            print('두번째 계정이 설정되지 않아 리시버를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.')
        elif self.dict_set['주식리시버'] and not self.StockReceiverProcessAlive():
            self.StockReceiverStart()
        if self.dict_set['아이디1'] is None:
            print('첫번째 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.')
        elif self.dict_set['주식트레이더'] and self.StockReceiverProcessAlive() and not self.StockTraderProcessAlive():
            self.StockTraderStart()

    def StockReceiverProcessKill(self):
        if self.StockReceiverProcessAlive():
            self.proc_receiver_stock.kill()

    def StockStrategyProcessKill(self):
        if self.StockStrategyProcessAlive():
            try:
                self.proc_strategy_stock1.kill()
                self.proc_strategy_stock2.kill()
                self.proc_strategy_stock3.kill()
                self.proc_strategy_stock4.kill()
                self.proc_strategy_stock5.kill()
                self.proc_strategy_stock6.kill()
                self.proc_strategy_stock7.kill()
                self.proc_strategy_stock8.kill()
            except:
                pass

    def StockTraderProcessKill(self):
        if self.StockTraderProcessAlive():
            self.proc_trader_stock.kill()

    def ManagerProcessKill(self):
        self.kwzservQ.put(('window', '통신종료'))
        self.StockReceiverProcessKill()
        self.StockStrategyProcessKill()
        self.StockTraderProcessKill()
        qtest_qwait(3)
        sys.exit()

    @staticmethod
    def OpenapiLoginWait():
        result = True
        lwopen = True
        update = False

        time_out_open = timedelta_sec(10)
        while find_window('Open API login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                print('로그인 오류 알림 : 로그인창이 열리지 않아 잠시 후 재시도합니다.')
                break
            qtest_qwait(0.1)

        if lwopen:
            time_out_update = timedelta_sec(30)
            time_out_close  = timedelta_sec(90)
            while find_window('Open API login') != 0:
                if not update:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('Open API login'), 0x40D))
                        if '다운로드' in text or '분석' in text or '기동' in text:
                            update = True
                    except:
                        pass
                    if now() > time_out_update:
                        result = False
                        print('로그인 오류 알림 : 업데이트가 확인되지 않아 잠시 후 재시도합니다.')
                        break
                if now() > time_out_close:
                    result = False
                    print('로그인 오류 알림 : 업데이트 제한 시간 초과로 잠시 후 재시도합니다.')
                    break
                qtest_qwait(0.01)

        if not result: opstarter_kill()

        return result

    def StockVersionUp(self):
        subprocess.Popen(f'python {LOGIN_PATH}/versionupdater.py')
        while not self.OpenapiLoginWait():
            qtest_qwait(0.1)
            subprocess.Popen(f'python {LOGIN_PATH}/versionupdater.py')
        qtest_qwait(10)

    def StockAutoLogin1(self):
        subprocess.Popen(f'python {LOGIN_PATH}/autologin1.py')
        while not self.OpenapiLoginWait():
            qtest_qwait(0.1)
            subprocess.Popen(f'python {LOGIN_PATH}/autologin1.py')
        qtest_qwait(5)

    def StockAutoLogin2(self):
        subprocess.Popen(f'python {LOGIN_PATH}/autologin2.py')
        while not self.OpenapiLoginWait():
            qtest_qwait(0.1)
            subprocess.Popen(f'python {LOGIN_PATH}/autologin2.py')
        qtest_qwait(5)

    def StockReceiverStart(self):
        if self.dict_set['리시버공유'] < 2:
            if self.dict_set['아이디2'] is not None:
                if self.dict_set['버전업']:
                    self.StockVersionUp()
                self.StockAutoLogin2()

                with open('C:/OpenAPI/system/ip_api.dat') as file:
                    text = file.read()
                fast_ip1 = text.split('IP=')[1].split('PORT=')[0].strip()[:7]
                fast_ip2 = text.split('IP=')[2].split('PORT=')[0].strip()[:7]

                while True:
                    qtest_qwait(0.1)
                    if not self.StockReceiverProcessAlive():
                        target = KiwoomReceiverTick if self.dict_set['주식타임프레임'] else KiwoomReceiverMin
                        self.proc_receiver_stock = Process(target=target, args=(self.qlist,), daemon=True)
                        self.proc_receiver_stock.start()
                        if self.OpenapiLoginWait():
                            with open('C:/OpenAPI/system/opcomms.ini') as file:
                                text = file.read()
                            server_ip_select = text.split('SERVER_IP_SELECT=')[1].split('PROBLEM_CONNECTIP=')[0].strip()
                            inthms = int_hms()
                            if inthms < 85000 and fast_ip1 in server_ip_select:
                                print(f'빠른 서버 접속 완료 [{server_ip_select}]')
                                break
                            elif 85000 < inthms < 85500 and (fast_ip1 in server_ip_select or fast_ip2 in server_ip_select):
                                print(f'빠른 서버 접속 완료 [{server_ip_select}]')
                                break
                            elif inthms < 80000 or 85500 < inthms or now().weekday() > 4:
                                print(f'접속 시간 초과, 마지막 접속 유지 [{server_ip_select}]')
                                break
                            else:
                                self.proc_receiver_stock.kill()
                                print('빠른 서버 접속 실패, 잠시 후 재접속합니다.')
                        else:
                            self.proc_receiver_stock.kill()
                            print('로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')
            else:
                print('두번째 계정이 설정되지 않아 리시버를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.')
        else:
            if self.dict_set['버전업']:
                self.StockVersionUp()

            if not self.StockReceiverProcessAlive():
                self.proc_receiver_stock = Process(target=KiwoomReceiverClient, args=(self.qlist,), daemon=True)
                self.proc_receiver_stock.start()

    def StockTraderStart(self):
        if self.dict_set['아이디1'] is not None:
            self.StockAutoLogin1()
            target = KiwoomStrategyTick if self.dict_set['주식타임프레임'] else KiwoomStrategyMin
            self.proc_strategy_stock1 = Process(target=target, args=(0, self.qlist), daemon=True)
            self.proc_strategy_stock2 = Process(target=target, args=(1, self.qlist), daemon=True)
            self.proc_strategy_stock3 = Process(target=target, args=(2, self.qlist), daemon=True)
            self.proc_strategy_stock4 = Process(target=target, args=(3, self.qlist), daemon=True)
            self.proc_strategy_stock5 = Process(target=target, args=(4, self.qlist), daemon=True)
            self.proc_strategy_stock6 = Process(target=target, args=(5, self.qlist), daemon=True)
            self.proc_strategy_stock7 = Process(target=target, args=(6, self.qlist), daemon=True)
            self.proc_strategy_stock8 = Process(target=target, args=(7, self.qlist), daemon=True)
            self.proc_strategy_stock1.start()
            self.proc_strategy_stock2.start()
            self.proc_strategy_stock3.start()
            self.proc_strategy_stock4.start()
            self.proc_strategy_stock5.start()
            self.proc_strategy_stock6.start()
            self.proc_strategy_stock7.start()
            self.proc_strategy_stock8.start()
            while True:
                qtest_qwait(1)
                if not self.StockTraderProcessAlive():
                    self.proc_trader_stock = Process(target=KiwoomTrader, args=(self.qlist,), daemon=True)
                    self.proc_trader_stock.start()
                    if self.OpenapiLoginWait():
                        break
                    else:
                        self.proc_trader_stock.kill()
        else:
            print('첫번째 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.')

    def StockReceiverProcessAlive(self):
        return self.proc_receiver_stock is not None and self.proc_receiver_stock.is_alive()

    def StockTraderProcessAlive(self):
        return self.proc_trader_stock is not None and self.proc_trader_stock.is_alive()

    def StockStrategyProcessAlive(self):
        return self.proc_strategy_stock1 is not None and self.proc_strategy_stock1.is_alive()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    KiwoomManager(port_number)
