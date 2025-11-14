import os
import sys
import win32api
import win32con
import win32gui
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))
from utility.setting import DICT_SET


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
    # noinspection PyUnresolvedReferences
    lParam = win32api.MAKELONG(x, y)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    # noinspection PyUnresolvedReferences
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
    # noinspection PyTypeChecker
    win32api.SendMessage(hwndd, win32con.EM_SETSEL, 0, -1)
    # noinspection PyTypeChecker
    win32api.SendMessage(hwndd, win32con.EM_REPLACESEL, 0, data)
    win32api.Sleep(500)


def press_keys(data):
    key = 0x30 + data
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)


def manual_login(gubun):
    hwnd = find_window('영웅문W login')
    if not win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
        click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
    if not win32gui.IsWindowEnabled(win32gui.GetDlgItem(hwnd, 0x3EA)):
        click_button(win32gui.GetDlgItem(hwnd, 0x3ED))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E8), DICT_SET[f'아이디{gubun}'])
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E9), DICT_SET[f'비밀번호{gubun}'])
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3EA), DICT_SET[f'인증서비밀번호{gubun}'])
    win32api.Sleep(1000)
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3E8))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E8), DICT_SET[f'아이디{gubun}'])
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3E9))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3E9), DICT_SET[f'비밀번호{gubun}'])
    doubleClick(15, 15, win32gui.GetDlgItem(hwnd, 0x3EA))
    enter_keys(win32gui.GetDlgItem(hwnd, 0x3EA), DICT_SET[f'인증서비밀번호{gubun}'])
    click_button(win32gui.GetDlgItem(hwnd, 0x1))
    try:
        click_button(win32gui.GetDlgItem(hwnd, 0x1))
    except:
        pass
