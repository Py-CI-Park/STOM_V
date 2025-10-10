import time
import telegram
import pythoncom
from manuallogin import *
from PyQt5 import QtWidgets
from multiprocessing import Process
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
from utility.static import now, timedelta_sec, opstarter_kill, get_logger
from utility.setting import DICT_SET


def TelegramMassage(txt):
    try:
        gubun = DICT_SET['증권사'][4:]
        bot = telegram.Bot(DICT_SET[f'텔레그램봇토큰{gubun}'])
        bot.sendMessage(chat_id=DICT_SET[f'텔레그램사용자아이디{gubun}'], text=txt)
    except:
        logger.error(txt)


class Window(QtWidgets.QMainWindow):
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self):
        super().__init__()
        self.bool_connected = False
        self.ocx = QAxWidget('KFOPENAPI.KFOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.CommConnect()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect(0)')
        while not self.bool_connected:
            pythoncom.PumpWaitingMessages()

    def OnEventConnect(self, err_code):
        if err_code == 0:
            self.bool_connected = True
            sys.exit()


if __name__ == '__main__':
    logger = get_logger('VersionUpdater')
    opstarter_kill()
    time.sleep(3)

    proc = Process(target=Window, daemon=True)
    proc.start()

    logger.info('버전처리용 로그인 프로세스 시작')
    while find_window('영웅문W login') == 0:
        logger.info('로그인창 열림 대기 중 ...')
        time.sleep(1)

    logger.info('아이디 및 패스워드 입력 대기 중 ...')
    time.sleep(2)

    id_num = int(DICT_SET['증권사'][4:])
    manual_login(id_num)
    logger.info('아이디 및 패스워드 입력 완료')

    update = False
    endtime = timedelta_sec(90)
    while find_window('영웅문W login') != 0:
        hwnd = find_window('글로벌 OpenAPI')
        if hwnd != 0:
            try:
                static_hwnd = win32gui.GetDlgItem(hwnd, 0xFFFF)
                text = win32gui.GetWindowText(static_hwnd)
                if '키움증권을 이용해 주셔서 감사드립니다' in text:
                    logger.error('키움증권 홈페이지, 해외파생 OPENAPI 게시판에서 시세이용신청 및 이용료납부를 완료해야만 접속가능합니다.')
                    time.sleep(3)
                    click_button(win32gui.GetDlgItem(hwnd, 0x2))
                    break
            except:
                pass

        hwnd = find_window('인증서 만료공지')
        if hwnd != 0:
            try:
                click_button(win32gui.GetDlgItem(hwnd, 0x7F3))
                click_button(win32gui.GetDlgItem(hwnd, 0x1))
                TelegramMassage('인증서 만료기간이 얼마남지 않았습니다.\n인증서를 갱신하십시오.')
            except:
                pass

        hwnd = find_window('nfstarter')
        if hwnd != 0:
            try:
                static_hwnd = win32gui.GetDlgItem(hwnd, 0xFFFF)
                text = win32gui.GetWindowText(static_hwnd)
                if '버전처리' in text:
                    time.sleep(3)
                    if proc.is_alive(): proc.kill()
                    click_button(win32gui.GetDlgItem(hwnd, 0x2))
                    logger.info('버전 업그레이드 완료')
                    update = True
            except:
                pass

        if not proc.is_alive():
            break

        logger.info('버전처리 및 로그인창 닫힘 대기 중 ...')
        time.sleep(1)
        if now() > endtime:
            opstarter_kill()
            break

    if update:
        time.sleep(5)
        hwnd = find_window('업그레이드 확인')
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        logger.info('버전 업그레이드 확인 완료')

    opstarter_kill()
    sys.exit()
