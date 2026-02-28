
import os
import sys
import zmq
import win32gui
import subprocess
from PyQt5.QtWidgets import QApplication
from multiprocessing import Process, Queue
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from kiwoom_trader import KiwoomTrader
from kiwoom_agent_min import KiwoomAgentMin
from kiwoom_agent_tick import KiwoomAgentTick
from kiwoom_strategy_min import KiwoomStrategyMin
from kiwoom_strategy_tick import KiwoomStrategyTick
from login_kiwoom.manuallogin import find_window
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DICT_SET, LOGIN_PATH
from utility.static import now, timedelta_sec, qtest_qwait, opstarter_kill, str_hms, get_logger


class ZmqRecvFromUI(QThread):
    signal1 = pyqtSignal(str)
    signal2 = pyqtSignal(tuple)

    def __init__(self, main, qlist, port_num):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs
                0            1             2            3
        """
        super().__init__()
        self.main     = main
        self.sagentQ  = qlist[1]
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
            if msg == 'agent':
                if self.main.StockAgentProcessAlive():
                    self.sagentQ.put(data)
            elif msg == 'trader':
                if self.main.StockTraderProcessAlive():
                    self.straderQ.put(data)
            elif msg == 'strategy':
                if self.main.StockStrategyProcessAlive():
                    for q in self.sstgQs:
                        q.put(data)
            elif msg == 'manager':
                if data.__class__ == str:
                    self.signal1.emit(data)
                elif data.__class__ == tuple:
                    self.signal2.emit(data)
                if data == '통신종료':
                    qtest_qwait(1)
                    break
        self.sock.close()
        self.zctx.term()


class ZmqSendToUI(QThread):
    def __init__(self, qlist, port_num):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs
                0            1             2            3
        """
        super().__init__()
        self.mgzservQ = qlist[0]
        self.sagentQ  = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQs   = qlist[3]

        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.PUB)
        self.sock.bind(f'tcp://*:{port_num}')

    def run(self):
        inthms = int(str_hms())
        while True:
            if not self.mgzservQ.empty():
                msg, data = self.mgzservQ.get()
                self.sock.send_string(msg, zmq.SNDMORE)
                self.sock.send_pyobj(data)
                if data.__class__ == str and data == '통신종료':
                    qtest_qwait(1)
                    break

            if int(str_hms()) > inthms:
                inthms = int(str_hms())
                sstgQs_size = sum([q.qsize() for q in self.sstgQs])
                qsize_data  = ('qsize', (self.sagentQ.qsize(), self.straderQ.qsize(), sstgQs_size))
                self.sock.send_string('qsize', zmq.SNDMORE)
                self.sock.send_pyobj(qsize_data)

            qtest_qwait(0.01)

        self.sock.close()
        self.zctx.term()


class KiwoomManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.mgzservQ, self.sagentQ, self.straderQ, sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q = \
            Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue()
        self.sstgQs   = [sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q]
        self.qlist    = [self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs]
        self.dict_set = DICT_SET
        self.logger   = get_logger(self.__class__.__name__)

        self.backtest_engine = False
        self.proc_strategy1  = None
        self.proc_strategy2  = None
        self.proc_strategy3  = None
        self.proc_strategy4  = None
        self.proc_strategy5  = None
        self.proc_strategy6  = None
        self.proc_strategy7  = None
        self.proc_strategy8  = None
        self.proc_trader     = None
        self.proc_agent      = None

        self.zmqrecv = ZmqRecvFromUI(self, self.qlist, port_num)
        self.zmqrecv.signal1.connect(self.UpdateString)
        self.zmqrecv.signal2.connect(self.UpdateTuple)
        self.zmqrecv.start()

        self.zmqserv = ZmqSendToUI(self.qlist, port_num + 1)
        self.zmqserv.start()

        QTimer.singleShot(5 * 1000, lambda: self.mgzservQ.put(('window', '매니저구동완료')))
        app.exec_()

    def UpdateString(self, data):
        if data == '수동시작':
            self.StockManualStart()
        elif data == '전략연산 종료':
            self.StockStrategyProcessKill()
        elif data == '트레이더 종료':
            self.StockTraderProcessKill()
        elif data == '에이전트 종료':
            self.StockAgentProcessKill()
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
            if self.StockTraderProcessAlive():
                self.straderQ.put(('설정변경', self.dict_set))
            if self.StockAgentProcessAlive():
                self.sagentQ.put(('설정변경', self.dict_set))

    def StockManualStart(self):
        if self.backtest_engine:
            self.logger.error('백테엔진 구동 중에는 로그인할 수 없습니다.')
            return

        if self.dict_set['주식에이전트'] and self.dict_set['주식트레이더']:
            self.StockVersionUp()
            self.StockTraderStart()
            self.StockAgentStart()

    def OpenapiLoginWait(self, is_main):
        result = True
        lwopen = True
        update = False
        verup  = False

        time_out_open = timedelta_sec(10)
        while find_window('Open API login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                self.logger.error('로그인 오류 알림 : 로그인창이 열리지 않아 잠시 후 재시도합니다.')
                break
            qtest_qwait(0.1)

        if lwopen:
            time_out_update = timedelta_sec(30)
            time_out_close  = timedelta_sec(60)
            while find_window('Open API login') != 0:
                if not verup:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('opstarter'), 0xFFFF))
                        if '버전처리' in text:
                            verup = True
                    except:
                        pass

                if not update:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('Open API login'), 0x40D))
                        if '다운로드' in text or '분석' in text or '기동' in text:
                            update = True
                    except:
                        pass

                    if now() > time_out_update:
                        result = False
                        self.logger.error('로그인 오류 알림 : 업데이트가 확인되지 않아 잠시 후 재시도합니다.')
                        break

                if now() > time_out_close:
                    result = False
                    self.logger.error('로그인 오류 알림 : 업데이트 제한 시간 초과로 잠시 후 재시도합니다.')
                    break

                qtest_qwait(0.01)

        if not is_main: qtest_qwait(10) if verup else qtest_qwait(2)
        if not result: opstarter_kill()
        return result

    def StockVersionUp(self):
        while True:
            proc = subprocess.Popen(f'python32 {LOGIN_PATH}/versionupdater.py')
            if self.OpenapiLoginWait(False):
                break
            else:
                self.logger.error('버전 업그레이드 실패, 잠시 후 재실행합니다.')
                proc.kill()
            qtest_qwait(1)

    def StockAutoLogin(self):
        subprocess.Popen(f'python32 {LOGIN_PATH}/autologin.py')
        while not self.OpenapiLoginWait(False):
            qtest_qwait(0.1)
            subprocess.Popen(f'python32 {LOGIN_PATH}/autologin.py')
        qtest_qwait(5)

    def StockTraderStart(self):
        target = KiwoomStrategyTick if self.dict_set['주식타임프레임'] else KiwoomStrategyMin
        self.proc_strategy1 = Process(target=target, args=(0, self.qlist), daemon=True)
        self.proc_strategy2 = Process(target=target, args=(1, self.qlist), daemon=True)
        self.proc_strategy3 = Process(target=target, args=(2, self.qlist), daemon=True)
        self.proc_strategy4 = Process(target=target, args=(3, self.qlist), daemon=True)
        self.proc_strategy5 = Process(target=target, args=(4, self.qlist), daemon=True)
        self.proc_strategy6 = Process(target=target, args=(5, self.qlist), daemon=True)
        self.proc_strategy7 = Process(target=target, args=(6, self.qlist), daemon=True)
        self.proc_strategy8 = Process(target=target, args=(7, self.qlist), daemon=True)
        self.proc_strategy1.start()
        self.proc_strategy2.start()
        self.proc_strategy3.start()
        self.proc_strategy4.start()
        self.proc_strategy5.start()
        self.proc_strategy6.start()
        self.proc_strategy7.start()
        self.proc_strategy8.start()
        self.proc_trader = Process(target=KiwoomTrader, args=(self.qlist,), daemon=True)
        self.proc_trader.start()

    def StockAgentStart(self):
        self.StockAutoLogin()

        with open('C:/OpenAPI/system/ip_api.dat') as file:
            text = file.read()
        fast_ip1 = text.split('IP=')[1].split('PORT=')[0].strip()[:7]
        fast_ip2 = text.split('IP=')[2].split('PORT=')[0].strip()[:7]
        target = KiwoomAgentTick if self.dict_set['주식타임프레임'] else KiwoomAgentMin
        while True:
            if not self.StockAgentProcessAlive():
                self.proc_agent = Process(target=target, args=(self.qlist,), daemon=True)
                self.proc_agent.start()
                if self.OpenapiLoginWait(True):
                    with open('C:/OpenAPI/system/opcomms.ini') as file:
                        text = file.read()
                    server_ip_select = text.split('SERVER_IP_SELECT=')[1].split('PROBLEM_CONNECTIP=')[0].strip()
                    inthms = int(str_hms())
                    if inthms < 85000 and fast_ip1 in server_ip_select:
                        self.logger.info(f'빠른 서버 접속 완료 [{server_ip_select}]')
                        break
                    elif 85000 < inthms < 85900 and (fast_ip1 in server_ip_select or fast_ip2 in server_ip_select):
                        self.logger.info(f'빠른 서버 접속 완료 [{server_ip_select}]')
                        break
                    elif inthms < 80000 or 85900 < inthms or now().weekday() > 4:
                        self.logger.info(f'접속 시간 초과, 마지막 접속 유지 [{server_ip_select}]')
                        break
                    else:
                        self.proc_agent.kill()
                        self.logger.error('빠른 서버 접속 실패, 잠시 후 재접속합니다.')
                else:
                    self.proc_agent.kill()
                    self.logger.error('로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')
            qtest_qwait(0.01)

    def StockTraderProcessAlive(self):
        return self.proc_trader is not None and self.proc_trader.is_alive()

    def StockStrategyProcessAlive(self):
        return self.proc_strategy1 is not None and self.proc_strategy1.is_alive()

    def StockAgentProcessAlive(self):
        return self.proc_agent is not None and self.proc_agent.is_alive()

    def StockStrategyProcessKill(self):
        if self.StockStrategyProcessAlive():
            try:
                self.proc_strategy1.kill()
                self.proc_strategy2.kill()
                self.proc_strategy3.kill()
                self.proc_strategy4.kill()
                self.proc_strategy5.kill()
                self.proc_strategy6.kill()
                self.proc_strategy7.kill()
                self.proc_strategy8.kill()
            except:
                pass

    def StockTraderProcessKill(self):
        if self.StockTraderProcessAlive():
            self.proc_trader.kill()

    def StockAgentProcessKill(self):
        if self.StockAgentProcessAlive():
            self.proc_trader.kill()

    def ManagerProcessKill(self):
        self.mgzservQ.put(('window', '통신종료'))
        self.StockStrategyProcessKill()
        self.StockTraderProcessKill()
        self.StockAgentProcessKill()
        sys.exit()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    KiwoomManager(port_number)
