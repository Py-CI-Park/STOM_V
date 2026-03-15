
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
from login_kiwoom.manuallogin import find_window, manual_login, click_button
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utility.setting_user import load_settings
from utility.setting_base import STOCK_LOGIN_PATH, ui_num
from utility.static import now, timedelta_sec, qtest_qwait, opstarter_kill, str_hms


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
        self.port_num   = port_num
        self.is_running = False
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
                        for q in self.sstgQs:
                            q.put(data)
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
        self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs
                0            1             2            3
        """
        super().__init__()
        self.mgzservQ   = qlist[0]
        self.sagentQ    = qlist[1]
        self.straderQ   = qlist[2]
        self.sstgQs     = qlist[3]
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
                    sstgQs_size = sum([q.qsize() for q in self.sstgQs])
                    qsize_data  = ('qsize', (self.sagentQ.qsize(), self.straderQ.qsize(), sstgQs_size))
                    self.sock.send_string('qsize', zmq.SNDMORE)
                    self.sock.send_pyobj(qsize_data)
            except:
                pass

        self.sock.close()
        self.zctx.term()

    def stop(self):
        self.is_running = False


class KiwoomManager:
    def __init__(self, port_num):
        app = QApplication(sys.argv)

        self.mgzservQ, self.sagentQ, self.straderQ, sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q = \
            Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue()
        self.sstgQs   = [sstg1Q, sstg2Q, sstg3Q, sstg4Q, sstg5Q, sstg6Q, sstg7Q, sstg8Q]
        self.qlist    = [self.mgzservQ, self.sagentQ, self.straderQ, self.sstgQs]
        self.dict_set = load_settings(ui_num, self.mgzservQ, True)

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

        QTimer.singleShot(3 * 1000, lambda: self.mgzservQ.put(('window', '매니저구동완료')))
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
        elif data == '프로세스종료':
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
            self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 백테엔진 구동 중에는 로그인할 수 없습니다.')))
            return

        if self.dict_set['주식에이전트'] and self.dict_set['주식트레이더']:
            self.StockVersionUp()
            self.StockTraderStart()
            self.StockAgentStart()

    def OpenapiLoginWait(self, manual=True):
        result = True
        lwopen = True
        update = False
        verup  = False

        if manual: self.mgzservQ.put(('window', (ui_num['타임로그'], '로그인창 열림 대기 중 ...')))
        time_out_open = timedelta_sec(10)
        while find_window('Open API login') == 0:
            if now() > time_out_open:
                result = False
                lwopen = False
                self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 로그인창이 열리지 않아 잠시 후 재시도합니다.')))
                break
            qtest_qwait(0.1)

        if lwopen:
            if manual:
                self.mgzservQ.put(('window', (ui_num['타임로그'], '아이디 및 패스워드 입력 대기 중 ...')))
                id_num = self.dict_set['증권사'][4:]
                qtest_qwait(2)
                manual_login(id_num, self.dict_set)
                self.mgzservQ.put(('window', (ui_num['타임로그'], '아이디 및 패스워드 입력 완료')))

            time_out_update = timedelta_sec(30)
            time_out_close  = timedelta_sec(60)
            if manual: self.mgzservQ.put(('window', (ui_num['타임로그'], '업데이트 및 버전업 확인 중 ...')))
            while find_window('Open API login') != 0:
                hwnd = find_window('인증서 만료공지')
                if hwnd != 0:
                    try:
                        click_button(win32gui.GetDlgItem(hwnd, 0x7F3))
                        click_button(win32gui.GetDlgItem(hwnd, 0x1))
                        if manual: self.mgzservQ.put(('tele', '인증서 만료기간이 얼마남지 않았습니다.\n인증서를 갱신하십시오.'))
                    except:
                        pass

                if not verup:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('opstarter'), 0xFFFF))
                        if '버전처리' in text:
                            verup = True
                            if manual: self.mgzservQ.put(('window', (ui_num['타임로그'], '버전 업데이트 확인 완료')))
                    except:
                        pass

                if not update:
                    try:
                        text = win32gui.GetWindowText(win32gui.GetDlgItem(find_window('Open API login'), 0x40D))
                        if '다운로드' in text or '분석' in text or '기동' in text:
                            update = True
                            if manual: self.mgzservQ.put(('window', (ui_num['타임로그'], '업데이트 확인 완료')))
                    except:
                        pass

                    if now() > time_out_update:
                        result = False
                        self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 업데이트가 확인되지 않아 잠시 후 재시도합니다.')))
                        break

                if now() > time_out_close:
                    result = False
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 업데이트 제한 시간 초과로 잠시 후 재시도합니다.')))
                    break

                qtest_qwait(0.01)

        if verup:
            self.mgzservQ.put(('window', (ui_num['타임로그'], '버전 업데이트 처리 완료')))
            qtest_qwait(10)
        else:
            qtest_qwait(2)
        if not result: opstarter_kill()
        return result

    def StockVersionUp(self):
        while True:
            proc = subprocess.Popen(f'python32 {STOCK_LOGIN_PATH}/versionupdater.py')
            if self.OpenapiLoginWait():
                break
            else:
                self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 버전 업그레이드 실패, 잠시 후 재실행합니다.')))
                proc.kill()
            qtest_qwait(1)

    def StockAutoLogin(self):
        subprocess.Popen(f'python32 {STOCK_LOGIN_PATH}/autologin.py')
        while not self.OpenapiLoginWait():
            qtest_qwait(0.1)
            subprocess.Popen(f'python32 {STOCK_LOGIN_PATH}/autologin.py')
        qtest_qwait(5)

    def StockTraderStart(self):
        target = KiwoomStrategyTick if self.dict_set['주식타임프레임'] else KiwoomStrategyMin
        self.proc_strategy1 = Process(target=target, args=(0, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy2 = Process(target=target, args=(1, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy3 = Process(target=target, args=(2, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy4 = Process(target=target, args=(3, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy5 = Process(target=target, args=(4, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy6 = Process(target=target, args=(5, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy7 = Process(target=target, args=(6, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy8 = Process(target=target, args=(7, self.qlist, self.dict_set), daemon=True)
        self.proc_strategy1.start()
        self.proc_strategy2.start()
        self.proc_strategy3.start()
        self.proc_strategy4.start()
        self.proc_strategy5.start()
        self.proc_strategy6.start()
        self.proc_strategy7.start()
        self.proc_strategy8.start()
        self.proc_trader = Process(target=KiwoomTrader, args=(self.qlist, self.dict_set), daemon=True)
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
                self.proc_agent = Process(target=target, args=(self.qlist, self.dict_set), daemon=True)
                self.proc_agent.start()
                if self.OpenapiLoginWait(False):
                    with open('C:/OpenAPI/system/opcomms.ini') as file:
                        text = file.read()
                    server_ip_select = text.split('SERVER_IP_SELECT=')[1].split('PROBLEM_CONNECTIP=')[0].strip()
                    inthms = int(str_hms())
                    if inthms < 85000 and fast_ip1 in server_ip_select:
                        self.mgzservQ.put(('window', (ui_num['타임로그'], f'빠른 서버 접속 완료 [{server_ip_select}]')))
                        break
                    elif 85000 < inthms < 85900 and (fast_ip1 in server_ip_select or fast_ip2 in server_ip_select):
                        self.mgzservQ.put(('window', (ui_num['타임로그'], f'빠른 서버 접속 완료 [{server_ip_select}]')))
                        break
                    elif inthms < 80000 or 85900 < inthms or now().weekday() > 4:
                        self.mgzservQ.put(('window', (ui_num['타임로그'], f'접속 시간 초과, 마지막 접속 유지 [{server_ip_select}]')))
                        break
                    else:
                        self.proc_agent.kill()
                        self.mgzservQ.put(('window', (ui_num['타임로그'], '빠른 서버 접속 실패, 잠시 후 재접속합니다.')))
                else:
                    self.proc_agent.kill()
                    self.mgzservQ.put(('window', (ui_num['시스템로그'], '오류 알림 - 로그인 또는 업데이트 실패, 잠시 후 재접속합니다.')))
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
        if self.zmqrecv.isRunning(): self.zmqrecv.stop()
        if self.zmqserv.isRunning(): self.zmqserv.stop()
        self.StockStrategyProcessKill()
        self.StockTraderProcessKill()
        self.StockAgentProcessKill()
        qtest_qwait(1)
        sys.exit()


if __name__ == '__main__':
    port_number = int(sys.argv[1])
    KiwoomManager(port_number)
