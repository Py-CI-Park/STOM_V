
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
from utility.setting_user import load_settings
from utility.setting_base import ui_num, FUTURE_LOGIN_PATH
from utility.static import now, timedelta_sec, qtest_qwait, opstarter_kill, str_hms


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
        self.port_num   = port_num
        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.SUB)
        self.sock.setsockopt(zmq.LINGER, 0)
        self.sock.setsockopt(zmq.SNDTIMEO, 5000)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, '')
        self.sock.connect(f'tcp://localhost:{self.port_num}')
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                msg  = self.sock.recv_string()
                data = self.sock.recv_pyobj()
                if msg == 'agent':
                    if self.main.StockAgentProcessAlive():
                        self.sagentQ.put(data)
                elif msg == 'trade':
                    if self.main.StockTraderProcessAlive():
                        self.straderQ.put(data)
                elif msg == 'strategy':
                    if self.main.StockStrategyProcessAlive():
                        self.sstgQ.put(data)
                elif msg == 'manager':
                    if data.__class__ == str:
                        self.signal1.emit(data)
                    elif data.__class__ == tuple:
                        self.signal2.emit(data)
            except:
                pass

        self.sock.close()
        self.zctx.term()

    def stop(self):
        self.is_running = False


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
        self.port_num   = port_num
        self.zctx = zmq.Context()
        self.sock = self.zctx.socket(zmq.PUB)
        self.sock.setsockopt(zmq.LINGER, 0)
        self.sock.setsockopt(zmq.SNDTIMEO, 5000)
        self.sock.bind(f'tcp://*:{self.port_num}')
        self.is_running = True

    def run(self):
        inthms = int(str_hms())
        while self.is_running:
            try:
                msg, data = self.mgzservQ.get(timeout=1)
                try:
                    self.sock.send_string(msg, zmq.SNDMORE)
                    self.sock.send_pyobj(data)
                except:
                    pass

                if int(str_hms()) > inthms:
                    inthms = int(str_hms())
                    qsize_data  = ('qsize', (self.sagentQ.qsize(), self.straderQ.qsize(), self.sstgQ.qsize()))
                    self.sock.send_string('qsize', zmq.SNDMORE)
                    self.sock.send_pyobj(qsize_data)
            except:
                pass

        self.sock.close()
        self.zctx.term()

    def stop(self):
        self.is_running = False


def set_password(password: str, mgzservQ):
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
            mgzservQ.put(('window', (ui_num['타임로그'], '계좌비밀번호 등록 완료')))
            break
        qtest_qwait(0.1)


class FutureManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ = Queue(), Queue(), Queue(), Queue()
        self.qlist    = [self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQ]
        self.dict_set = load_settings()

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
        elif data == '프로세스종료':
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
            self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 백테엔진 구동 중에는 로그인할 수 없습니다.')))
            return

        if self.dict_set['주식에이전트'] and self.dict_set['주식트레이더']:
            self.FutureVersionUp()
            self.FutureTraderStart()
            self.FutureAgentStart()

    def OpenapiLoginWait(self):
        result = True
        lwopen = True
        update = False
        verup  = False

        self.mgzservQ.put(('window', (ui_num['타임로그'], '로그인창 열림 대기 중 ...')))
        time_out_open = timedelta_sec(10)
        while find_window('영웅문W login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 로그인창이 열리지 않아 잠시 후 재시도합니다.')))
                break
            qtest_qwait(0.1)

        if lwopen:
            self.mgzservQ.put(('window', (ui_num['타임로그'], '아이디 및 패스워드 입력 대기 중 ...')))
            id_num = self.dict_set['증권사'][4:]
            qtest_qwait(2)
            manual_login(id_num, self.dict_set)
            self.mgzservQ.put(('window', (ui_num['타임로그'], '아이디 및 패스워드 입력 완료')))

            time_out_update = timedelta_sec(30)
            time_out_close  = timedelta_sec(60)
            self.mgzservQ.put(('window', (ui_num['타임로그'], '업데이트 및 버전업 확인 중 ...')))
            while find_window('영웅문W login') != 0:
                hwnd = find_window('글로벌 OpenAPI')
                if hwnd != 0:
                    try:
                        static_hwnd = win32gui.GetDlgItem(hwnd, 0xFFFF)
                        text = win32gui.GetWindowText(static_hwnd)
                        if '키움증권을 이용해 주셔서 감사드립니다' in text:
                            self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 키움증권 홈페이지, 해외파생 OPENAPI 게시판에서 시세이용신청 및 이용료납부를 완료해야만 접속가능합니다.')))
                            click_button(win32gui.GetDlgItem(hwnd, 0x2))
                            result = False
                            break
                    except:
                        pass

                hwnd = find_window('인증서 만료공지')
                if hwnd != 0:
                    try:
                        click_button(win32gui.GetDlgItem(hwnd, 0x7F3))
                        click_button(win32gui.GetDlgItem(hwnd, 0x1))
                        self.mgzservQ.put(('tele', '인증서 만료기간이 얼마남지 않았습니다.\n인증서를 갱신하십시오.'))
                    except:
                        pass

                if not verup:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('nfstarter'), 0xFFFF))
                        if '버전처리' in text:
                            verup = True
                            self.mgzservQ.put(('window', (ui_num['타임로그'], '버전 업데이트 확인 완료')))
                    except:
                        pass

                if not update:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('영웅문W login'), 0x40D))
                        if '다운로드' in text or '분석' in text or '기동' in text:
                            update = True
                            self.mgzservQ.put(('window', (ui_num['타임로그'], '업데이트 확인 완료')))
                    except:
                        pass

                    if now() > time_out_update:
                        self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 업데이트가 확인되지 않아 잠시 후 재시도합니다.')))
                        result = False
                        break

                if now() > time_out_close:
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 업데이트 제한 시간 초과로 잠시 후 재시도합니다.')))
                    result = False
                    break

                qtest_qwait(0.1)

        if verup:
            self.mgzservQ.put(('window', (ui_num['타임로그'], '버전 업데이트 처리 완료')))
            qtest_qwait(10)
        else:
            qtest_qwait(2)
        if not result: opstarter_kill()
        return result

    def FutureVersionUp(self):
        while True:
            proc = subprocess.Popen(f'python32 {FUTURE_LOGIN_PATH}/versionupdater.py')
            if self.OpenapiLoginWait():
                break
            else:
                self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 버전 업그레이드 실패, 잠시 후 재실행합니다.')))
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
                set_pass_proc = Process(target=set_password, args=(password, self.mgzservQ))
                set_pass_proc.start()
                self.proc_agent = Process(target=target, args=(self.qlist, self.dict_set), daemon=True)
                self.proc_agent.start()
                if self.OpenapiLoginWait():
                    break
                else:
                    set_pass_proc.kill()
                    self.proc_agent.kill()
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')))
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
        if self.zmqrecv.isRunning(): self.zmqrecv.stop()
        if self.zmqserv.isRunning(): self.zmqserv.stop()
        self.FutureStrategyProcessKill()
        self.FutureTraderProcessKill()
        self.FutureAgentProcessKill()
        qtest_qwait(1)
        sys.exit()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    FutureManager(port_number)
