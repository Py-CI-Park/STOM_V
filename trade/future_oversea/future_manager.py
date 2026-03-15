
import os
import sys
import zmq
import win32gui
import subprocess
from PyQt5.QtWidgets import QApplication
from multiprocessing import Process, Queue
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from future_trader import FutureTrader
from future_agent_min import FutureAgentMin
from future_agent_tick import FutureAgentTick
from future_strategy_min import FutureStrategyMin
from future_strategy_tick import FutureStrategyTick
from login_future.manuallogin import find_window, manual_login, leftClick, doubleClick, press_keys, click_button
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.setting_user import DICT_SET
from utility.static import now, timedelta_sec, qtest_qwait, opstarter_kill, str_hms, get_logger


class ZmqRecvFromUI(QThread):
    signal1 = pyqtSignal(str)
    signal2 = pyqtSignal(tuple)

    def __init__(self, main, qlist, port_num):
        """
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ
                0            1             2            3
        """
        super().__init__()
        self.main     = main
        self.sagentQ  = qlist[1]
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
            if msg == 'agent':
                if self.main.FutureAgentProcessAlive():
                    self.sagentQ.put(data)
            elif msg == 'trade':
                if self.main.FutureTraderProcessAlive():
                    self.straderQ.put(data)
            elif msg == 'analyzer':
                if self.main.FutureStrategyProcessAlive():
                    self.sstgQ.put(data)
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
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ
                0            1             2            3
        """
        super().__init__()
        self.mgzservQ = qlist[0]
        self.sagentQ  = qlist[1]
        self.straderQ = qlist[2]
        self.sstgQ    = qlist[3]

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
                qsize_data  = ('qsize', (self.sagentQ.qsize(), self.straderQ.qsize(), self.sstgQ.qsize()))
                self.sock.send_string('qsize', zmq.SNDMORE)
                self.sock.send_pyobj(qsize_data)

            qtest_qwait(0.01)

        self.sock.close()
        self.zctx.term()


def set_password(password: str):
    logger = get_logger('FutureManager')
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
            logger.info('계좌비밀번호 등록 완료')
            break
        qtest_qwait(0.1)


class FutureManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ = Queue(), Queue(), Queue(), Queue()
        self.qlist    = [self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ]
        self.dict_set = DICT_SET
        self.logger   = get_logger(self.__class__.__name__)

        self.backtest_engine = False
        self.proc_strategy   = None
        self.proc_trader     = None
        self.proc_agent      = None

        self.zmqrecv = ZmqRecvFromUI(self, self.qlist, port_num)
        self.zmqrecv.signal1.connect(self.UpdateString)
        self.zmqrecv.signal2.connect(self.UpdateTuple)
        self.zmqrecv.start()

        self.zmqserv = ZmqSendToUI(self.qlist, port_num + 1)
        self.zmqserv.start()

        QTimer.singleShot(3 * 1000, lambda: self.mgzservQ.put(('window', '매니저구동완료')))
        app.exec_()

    def UpdateString(self, data):
        if data == '수동시작':
            self.FutureManualStart()
        elif data == '전략연산 종료':
            self.FutureStrategyProcessKill()
        elif data == '트레이더 종료':
            self.FutureTraderProcessKill()
        elif data == '에이전트 종료':
            self.FutureAgentProcessKill()
        elif data == '통신종료':
            self.ManagerProcessKill()
        elif data == '백테엔진구동':
            self.backtest_engine = True

    def UpdateTuple(self, data):
        if data[0] == '설정변경':
            self.dict_set = data[1]
            if self.FutureStrategyProcessAlive():
                self.sstgQ.put(('설정변경', self.dict_set))
            if self.FutureTraderProcessAlive():
                self.straderQ.put(('설정변경', self.dict_set))
            if self.FutureAgentProcessAlive():
                self.sagentQ.put(('설정변경', self.dict_set))

    def FutureManualStart(self):
        if self.backtest_engine:
            self.logger.error('백테엔진 구동 중에는 로그인할 수 없습니다.')
            return

        if self.dict_set['주식에이전트'] and self.dict_set['주식트레이더']:
            self.FutureVersionUp()
            self.FutureTraderStart()
            self.FutureAgentStart()

    def OpenapiLoginWait(self, is_main):
        result = True
        lwopen = True
        update = False
        verup  = False

        time_out_open = timedelta_sec(10)
        while find_window('영웅문W login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                self.logger.error('로그인 오류 알림 : 로그인창이 열리지 않아 잠시 후 재시도합니다.')
                break
            qtest_qwait(0.1)

        if lwopen:
            if is_main:
                id_num = int(self.dict_set['증권사'][4:])
                self.logger.info('아이디 및 패스워드 입력 대기 중 ...')
                qtest_qwait(2)
                manual_login(id_num, self.dict_set)
                self.logger.info('아이디 및 패스워드 입력 완료')

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
                        self.logger.error('로그인 오류 알림 : 업데이트가 확인되지 않아 잠시 후 재시도합니다.')
                        break

                if now() > time_out_close:
                    result = False
                    self.logger.error('로그인 오류 알림 : 업데이트 제한 시간 초과로 잠시 후 재시도합니다.')
                    break

                qtest_qwait(0.01)

        qtest_qwait(10) if verup else qtest_qwait(2)
        if not result: opstarter_kill()
        return result

    def FutureVersionUp(self):
        while True:
            proc = subprocess.Popen('python32 ./future/login_future/versionupdater.py')
            if self.OpenapiLoginWait(False):
                break
            else:
                self.logger.error('버전 업그레이드 실패, 잠시 후 재실행합니다.')
                proc.kill()
            qtest_qwait(1)

    def FutureTraderStart(self):
        target = FutureStrategyTick if self.dict_set['주식타임프레임'] else FutureStrategyMin
        self.proc_strategy = Process(target=target, args=(self.qlist, self.dict_set), daemon=True)
        self.proc_strategy.start()
        self.proc_trader = Process(target=FutureTrader, args=(self.qlist, self.dict_set))
        self.proc_trader.start()

    def FutureAgentStart(self):
        target = FutureAgentTick if self.dict_set['주식타임프레임'] else FutureAgentMin
        password = self.dict_set[f"계좌비밀번호{int(self.dict_set['증권사'][4:])}"]
        while True:
            if not self.FutureAgentProcessAlive():
                set_pass_proc = Process(target=set_password, args=(password,))
                set_pass_proc.start()
                self.proc_agent = Process(target=target, args=(self.qlist, self.dict_set), daemon=True)
                self.proc_agent.start()
                if self.OpenapiLoginWait(True):
                    break
                else:
                    set_pass_proc.kill()
                    self.proc_agent.kill()
                    self.logger.error('로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')
            qtest_qwait(0.01)

    def FutureStrategyProcessAlive(self):
        return self.proc_strategy is not None and self.proc_strategy.is_alive()

    def FutureTraderProcessAlive(self):
        return self.proc_trader is not None and self.proc_trader.is_alive()

    def FutureAgentProcessAlive(self):
        return self.proc_agent is not None and self.proc_agent.is_alive()

    def FutureStrategyProcessKill(self):
        if self.FutureStrategyProcessAlive(): self.proc_strategy.kill()

    def FutureTraderProcessKill(self):
        if self.FutureTraderProcessAlive(): self.proc_trader.kill()

    def FutureAgentProcessKill(self):
        if self.FutureAgentProcessAlive(): self.proc_agent.kill()

    def ManagerProcessKill(self):
        self.mgzservQ.put(('window', '통신종료'))
        self.FutureStrategyProcessKill()
        self.FutureTraderProcessKill()
        self.FutureAgentProcessKill()
        sys.exit()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    FutureManager(port_number)
