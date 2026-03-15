import os
import sys
import time
import pythoncom
from manuallogin import *
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from multiprocessing import Process
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))))))
from utility.setting_user import load_settings
from utility.setting_base import OPENAPI_PATH
from utility.static import opstarter_kill


class Window(QtWidgets.QMainWindow):
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self, id_num_, dict_set_):
        super().__init__()
        self.id_num   = id_num_
        self.dict_set = dict_set_
        self.bool_connected = False
        self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.CommConnect()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect()')
        while not self.bool_connected:
            pythoncom.PumpWaitingMessages()

    def OnEventConnect(self, err_code):
        if err_code == 0:
            self.bool_connected = True
        self.AutoLoginOn()

    def AutoLoginOn(self):
        QTimer.singleShot(1000, lambda: auto_on(self.id_num, self.dict_set))
        self.ocx.dynamicCall('KOA_Functions(QString, QString)', 'ShowAccountWindow', '')
        opstarter_kill()


if __name__ == '__main__':
    opstarter_kill()
    autologin_dat = f'{OPENAPI_PATH}/system/Autologin.dat'
    if os.path.isfile(autologin_dat): os.remove(autologin_dat)

    dict_set = load_settings()
    id_num   = dict_set['증권사'][4:]

    Process(target=Window, args=(id_num, dict_set), daemon=True).start()

    while find_window('Open API login') == 0:
        time.sleep(0.1)

    while find_window('Open API login') != 0:
        time.sleep(0.1)

    time.sleep(5)
    sys.exit()
