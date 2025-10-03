import sys
import win32api
import win32con
import win32gui
import datetime
import pythoncom
from multiprocessing import Process
from PyQt5.QtTest import QTest
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

아이디 = ''
아이디비밀번호 = ''
계좌비밀번호 = ''
인증서비밀번호 = ''


def window_enumeration_handler(hwnd, top_windows):
    top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))


def enum_windows():
    windows = []
    win32gui.EnumWindows(window_enumeration_handler, windows)
    return windows


def find_window(caption):
    hwnd = win32gui.FindWindow(None, caption)
    if hwnd == 0:
        windows = enum_windows()
        for handle, title in windows:
            if caption in title:
                hwnd = handle
                break
    return hwnd


def leftClick(x, y, hwnd):
    lParam = win32api.MAKELONG(x, y)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    win32api.Sleep(300)


def doubleClick(x, y, hwnd):
    leftClick(x, y, hwnd)
    leftClick(x, y, hwnd)


def click_button(btn_hwnd):
    win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONDOWN, 0, 0)
    win32api.Sleep(200)
    win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONUP, 0, 0)
    win32api.Sleep(500)


def enter_keys(hwndd, data):
    win32api.SendMessage(hwndd, win32con.EM_SETSEL, 0, -1)
    win32api.SendMessage(hwndd, win32con.EM_REPLACESEL, 0, data)
    win32api.Sleep(500)


def qtest_qwait(sec):
    # noinspection PyArgumentList
    QTest.qWait(int(sec * 1000))


def press_keys(data: int):
    key = 0x30 + data
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)


def set_password():
    while True:
        hwnd = find_window('계좌번호관리')
        if hwnd != 0:
            qtest_qwait(1)
            leftClick(10, 10, win32gui.GetDlgItem(hwnd, 0x3E8))
            qtest_qwait(1)
            doubleClick(10, 10, win32gui.GetDlgItem(hwnd, 0x3E9))
            qtest_qwait(1)
            for key in 계좌비밀번호:
                press_keys(int(key))
                qtest_qwait(0.2)
            qtest_qwait(1)
            click_button(win32gui.GetDlgItem(hwnd, 0x3EC))
            qtest_qwait(1)
            click_button(win32gui.GetDlgItem(hwnd, 0x2))
            qtest_qwait(1)
            print('계좌비밀번호 등록 완료')
            break
        else:
            qtest_qwait(0.1)


def manual_login():
    hwnd = find_window('영웅문W login')
    if not win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
        click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
    if not win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
        click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E8), 아이디)
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E9), 아이디비밀번호)
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3EA), 인증서비밀번호)
    win32api.Sleep(1000)
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3E8))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E8), 아이디)
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3E9))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E9), 아이디비밀번호)
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3EA))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3EA), 인증서비밀번호)
    click_button(win32gui.GetDlgItem(hwnd, 0x1))
    click_button(win32gui.GetDlgItem(hwnd, 0x1))
    print('아이디, 계좌비밀번호, 인증서비밀번호 입력 완료')


class Futurelogin:
    def __init__(self):
        app = QApplication(sys.argv)

        Process(target=set_password).start()

        self.login = False

        self.qtimer = QTimer()
        self.qtimer.setInterval(1 * 1000)
        self.qtimer.timeout.connect(self.process_monitor)
        self.qtimer.start()

        self.ocx = QAxWidget('KFOPENAPI.KFOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.CommConnect()
        self.ShowAccountWindow()
        print('계좌비밀번호 등록 후 블럭 해제 완료')

        app.exec_()

    @staticmethod
    def process_monitor():
        print(datetime.datetime.now(), 'main process alive')

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect(0)')
        print('로그인창 열림 대기 중 ...')
        while find_window('영웅문W login') == 0:
            qtest_qwait(0.1)
        print('아이디 및 패스워드 입력 대기 중 ...')
        qtest_qwait(2)
        manual_login()
        while not self.login:
            pythoncom.PumpWaitingMessages()
        print('KFOPENAPI 로그인 완료')

    def OnEventConnect(self, err_code):
        if err_code == 0: self.login = True

    def ShowAccountWindow(self):
        self.ocx.dynamicCall('GetCommonFunc(QString, QString)', 'ShowAccountWindow', '')


if __name__ == '__main__':
    Futurelogin()
