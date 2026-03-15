
import os
import sys
import time
import pythoncom
from manuallogin import *
from PyQt5 import QtWidgets
from multiprocessing import Process
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))))
from utility.static import now, timedelta_sec, opstarter_kill


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
    opstarter_kill()
    time.sleep(3)

    proc = Process(target=Window, daemon=True)
    proc.start()

    while find_window('영웅문W login') == 0:
        time.sleep(0.1)

    update = False
    endtime = timedelta_sec(90)
    while find_window('영웅문W login') != 0:
        hwnd = find_window('nfstarter')
        if hwnd != 0:
            try:
                static_hwnd = win32gui.GetDlgItem(hwnd, 0xFFFF)
                text = win32gui.GetWindowText(static_hwnd)
                if '버전처리' in text:
                    time.sleep(3)
                    if proc.is_alive(): proc.kill()
                    click_button(win32gui.GetDlgItem(hwnd, 0x2))
                    update = True
            except:
                pass

        if not proc.is_alive():
            break

        time.sleep(0.1)
        if now() > endtime:
            opstarter_kill()
            break

    if update:
        time.sleep(5)
        hwnd = find_window('업그레이드 확인')
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    opstarter_kill()
    sys.exit()
