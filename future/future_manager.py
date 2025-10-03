import os
import sys
import zmq
import win32gui
import subprocess
from multiprocessing import Process, Queue
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from future_trader import FutureTrader
from future_receiver_min import FutureReceiverMin
from future_strategy_min import FutureStrategyMin
from future_receiver_tick import FutureReceiverTick
from future_strategy_tick import FutureStrategyTick
from future_receiver_client import FutureReceiverClient
from login_future.manuallogin import find_window, manual_login, leftClick, doubleClick, press_keys, click_button
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET
from utility.static import now, timedelta_sec, qtest_qwait, opstarter_kill, str_hms


class ZmqRecv(QThread):
    signal1 = pyqtSignal(str)
    signal2 = pyqtSignal(tuple)

    def __init__(self, qlist, port_num):
        super().__init__()
        self.sreceivQ = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQ    = qlist[3]

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
                self.sstgQ.put(data)
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
        self.sstgQ    = qlist[3]

        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:{port_num}')

    def run(self):
        int_hms_ = int(str_hms())
        while True:
            msg, data = self.kwzservQ.get()
            self.sock.send_string(msg, zmq.SNDMORE)
            self.sock.send_pyobj(data)
            if int(str_hms()) > int_hms_:
                qsize_data  = ('qsize', (self.sreceivQ.qsize(), self.straderQ.qsize(), self.sstgQ.qsize()))
                self.sock.send_string('qsize', zmq.SNDMORE)
                self.sock.send_pyobj(qsize_data)
                int_hms_ = int(str_hms())
            if type(data) == str and data == '통신종료':
                QThread.sleep(1)
                break
        self.sock.close()
        self.zctx.term()


def set_password(password: str):
    while True:
        hwnd = find_window('계좌번호관리')
        if hwnd != 0:
            qtest_qwait(1)
            leftClick(10, 10, win32gui.GetDlgItem(hwnd, 0x3E8))
            qtest_qwait(1)
            doubleClick(10, 10, win32gui.GetDlgItem(hwnd, 0x3E9))
            qtest_qwait(1)
            for key in password:
                press_keys(int(key))
                qtest_qwait(0.2)
            qtest_qwait(1)
            click_button(win32gui.GetDlgItem(hwnd, 0x3EC))
            qtest_qwait(1)
            click_button(win32gui.GetDlgItem(hwnd, 0x2))
            try:
                click_button(win32gui.GetDlgItem(hwnd, 0x2))
            except:
                pass
            qtest_qwait(1)
            print('계좌비밀번호 등록 완료')
            break
        else:
            qtest_qwait(0.1)


class FutureManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQ = Queue(), Queue(), Queue(), Queue()
        self.qlist    = [self.kwzservQ, self.sreceivQ, self.straderQ, self.sstgQ]
        self.dict_set = DICT_SET

        self.login_progress       = False
        self.backtest_engine      = False
        self.proc_receiver_future = None
        self.proc_strategy_future = None
        self.proc_trader_future   = None

        self.zmqrecv = ZmqRecv(self.qlist, port_num)
        self.zmqrecv.signal1.connect(self.UpdateString)
        self.zmqrecv.signal2.connect(self.UpdateTuple)
        self.zmqrecv.start()

        self.zmqserv = ZmqServ(self.qlist, port_num + 1)
        self.zmqserv.start()

        QTimer.singleShot(5 * 1000, lambda: self.kwzservQ.put(('window', '매니저구동완료')))
        app.exec_()

    def UpdateString(self, data):
        if data == '수동시작':
            self.FutureManualStart()
        elif data == '리시버 종료':
            self.FutureReceiverProcessKill()
        elif data == '전략연산 종료':
            self.FutureStrategyProcessKill()
        elif data == '트레이더 종료':
            self.FutureTraderProcessKill()
        elif data == '통신종료':
            self.ManagerProcessKill()
        elif data == '백테엔진구동':
            self.backtest_engine = True

    def UpdateTuple(self, data):
        if data[0] == '설정변경':
            self.dict_set = data[1]
            if self.FutureStrategyProcessAlive():
                self.sstgQ.put(('설정변경', self.dict_set))
            if self.FutureReceiverProcessAlive():
                self.sreceivQ.put(('설정변경', self.dict_set))
            if self.FutureTraderProcessAlive():
                self.straderQ.put(('설정변경', self.dict_set))

    def FutureManualStart(self):
        if self.backtest_engine:
            print('백테엔진 구동 중에는 로그인할 수 없습니다.')
            return
        if self.dict_set['버전업']:
            self.FutureVersionUp()
        if self.dict_set['주식리시버'] and not self.FutureReceiverProcessAlive():
            self.FutureReceiverStart()
        if self.dict_set['주식트레이더'] and self.FutureReceiverProcessAlive() and not self.FutureTraderProcessAlive():
            self.FutureTraderStart()

    def FutureReceiverProcessKill(self):
        if self.FutureReceiverProcessAlive(): self.proc_receiver_future.kill()

    def FutureStrategyProcessKill(self):
        if self.FutureStrategyProcessAlive(): self.proc_strategy_future.kill()

    def FutureTraderProcessKill(self):
        if self.FutureTraderProcessAlive(): self.proc_trader_future.kill()

    def ManagerProcessKill(self):
        self.kwzservQ.put(('window', '통신종료'))
        self.FutureReceiverProcessKill()
        self.FutureStrategyProcessKill()
        self.FutureTraderProcessKill()
        qtest_qwait(3)
        sys.exit()

    def OpenapiLoginWait(self, gubun):
        result = True
        lwopen = True
        update = False
        verup  = False

        time_out_open = timedelta_sec(10)
        while find_window('영웅문W login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                print('로그인 오류 알림 : 로그인창이 열리지 않아 잠시 후 재시도합니다.')
                break
            qtest_qwait(0.1)

        if lwopen:
            if gubun in (1, 2):
                if gubun == 1:
                    id_num = int(self.dict_set['증권사'][4:]) * 2 - 1
                else:
                    id_num = int(self.dict_set['증권사'][4:]) * 2
                print('아이디 및 패스워드 입력 대기 중 ...')
                qtest_qwait(2)
                manual_login(id_num)
                print('아이디 및 패스워드 입력 완료')

            time_out_update = timedelta_sec(30)
            time_out_close  = timedelta_sec(60)
            while find_window('영웅문W login') != 0:
                if not verup:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('nfstarter'), 0xFFFF))
                        if '버전처리' in text:
                            verup = True
                    except:
                        pass

                if not update:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('영웅문W login'), 0x40D))
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

        qtest_qwait(10) if verup else qtest_qwait(2)
        if not result: opstarter_kill()
        return result

    def FutureVersionUp(self):
        while True:
            proc = subprocess.Popen('python ./future/login_future/versionupdater.py')
            if self.OpenapiLoginWait(3):
                break
            else:
                print('버전 업그레이드 실패, 잠시 후 재실행합니다.')
                proc.kill()
            qtest_qwait(1)

    def FutureReceiverStart(self):
        if self.dict_set['리시버공유'] < 2:
            while True:
                if not self.FutureReceiverProcessAlive():
                    target = FutureReceiverTick if self.dict_set['주식타임프레임'] else FutureReceiverMin
                    self.proc_receiver_future = Process(target=target, args=(self.qlist,), daemon=True)
                    self.proc_receiver_future.start()
                    if self.OpenapiLoginWait(2):
                        break
                    else:
                        self.proc_receiver_future.kill()
                        print('로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')
                qtest_qwait(0.1)
        else:
            if not self.FutureReceiverProcessAlive():
                self.proc_receiver_future = Process(target=FutureReceiverClient, args=(self.qlist,), daemon=True)
                self.proc_receiver_future.start()

    def FutureTraderStart(self):
        target = FutureStrategyTick if self.dict_set['주식타임프레임'] else FutureStrategyMin
        self.proc_strategy_future = Process(target=target, args=(self.qlist,), daemon=True)
        self.proc_strategy_future.start()
        password = self.dict_set[f"계좌비밀번호{int(self.dict_set['증권사'][4:]) * 2 - 1}"]
        while True:
            if not self.FutureTraderProcessAlive():
                set_pass_proc = Process(target=set_password, args=(password,))
                set_pass_proc.start()
                self.proc_trader_future = Process(target=FutureTrader, args=(self.qlist,))
                self.proc_trader_future.start()
                if self.OpenapiLoginWait(1):
                    break
                else:
                    if set_pass_proc.is_alive(): set_pass_proc.kill()
                    self.proc_trader_future.kill()
                    print('로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')
            qtest_qwait(0.1)

    def FutureReceiverProcessAlive(self):
        return self.proc_receiver_future is not None and self.proc_receiver_future.is_alive()

    def FutureTraderProcessAlive(self):
        return self.proc_trader_future is not None and self.proc_trader_future.is_alive()

    def FutureStrategyProcessAlive(self):
        return self.proc_strategy_future is not None and self.proc_strategy_future.is_alive()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    FutureManager(port_number)
