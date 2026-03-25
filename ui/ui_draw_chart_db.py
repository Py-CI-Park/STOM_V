
import win32api
import win32gui
from utility.setting_base import ui_num
from PyQt5.QtWidgets import QMessageBox
from utility.static import error_decorator
from ui.ui_draw_chart_base import DrawChartBase
from utility.static import from_timestamp, thread_decorator, str_ymd
from trade.stock_korea.login_kiwoom.manuallogin import leftClick, enter_keys, press_keys


class DrawDBChart(DrawChartBase):
    @error_decorator
    def draw_db_chart(self, data):
        self.real = False
        self.ui.ChartClear()
        if not self.ui.dialog_chart.isVisible():
            return

        self.gubun, self.ui.ctpg_xticks, self.ui.ctpg_arry, self.ui.buy_index, self.ui.sell_index, \
            fm_list, dict_fm, fm_tcnt = data[1:]

        if dict_fm:
            self.ui.fm_list = fm_list
            self.ui.dict_fm = dict_fm
        else:
            self.ui.fm_list = []
            self.ui.dict_fm = None

        if self.gubun == '차트오류':
            QMessageBox.critical(self.ui.dialog_chart, '오류 알림', '해당 날짜의 데이터가 존재하지 않습니다.\n')
            return

        self.code = self.ui.ct_lineEdittttt_04.text()
        self.chart_cnt = len(self.ui.ctpg)
        self.is_min = self.chart_cnt in (6, 8) or (self.chart_cnt == 10 and self.ui.ct_pushButtonnn_05.text() == 'CHART III')

        self.gsjm_arry = self.ui.ctpg_arry[:, self.fi('관심종목')]
        self.xmin, self.xmax = self.ui.ctpg_xticks[0], self.ui.ctpg_xticks[-1]
        self.hms = from_timestamp(self.xmax).strftime('%H:%M' if self.is_min else '%H:%M:%S')
        self.same_time = False

        self.update_factor_list()
        self.update_dict_idxs()
        self.update_ctpg_date()
        self.draw_all_chart()

        if self.gubun == 'S':
            self.KiwoomHTSChart(self.code, str_ymd(from_timestamp(self.xmin)))

        if self.ui.dialog_hoga.isVisible() and self.ui.hg_labellllllll_01.text():
            self.ui.hgButtonClicked_02('매수')

    @thread_decorator
    def KiwoomHTSChart(self, code, date):
        try:
            hwnd_mult = win32gui.FindWindowEx(None, None, None, "[0607] 멀티차트")
            if hwnd_mult != 0:
                win32gui.SetForegroundWindow(hwnd_mult)
                self.HTSControl(code, date, hwnd_mult)
            else:
                hwnd_main = win32gui.FindWindowEx(None, None, '_NKHeroMainClass', None)
                if hwnd_main != 0:
                    win32gui.SetForegroundWindow(hwnd_main)
                    hwnd_mult = win32gui.FindWindowEx(hwnd_main, None, "MDIClient", None)
                    hwnd_mult = win32gui.FindWindowEx(hwnd_mult, None, None, "[0607] 멀티차트")
                    self.HTSControl(code, date, hwnd_mult)
        except:
            pass

    def HTSControl(self, code, date, hwnd_mult):
        try:
            hwnd_part = win32gui.FindWindowEx(hwnd_mult, None, "AfxFrameOrView110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)
            hwnd_mid1 = win32gui.FindWindowEx(hwnd_part, hwnd_prev, "AfxWnd110", None)
            hwnd_mid2 = win32gui.FindWindowEx(hwnd_part, hwnd_mid1, "AfxWnd110", None)
            hwnd_mid3 = win32gui.FindWindowEx(hwnd_part, hwnd_mid2, "AfxWnd110", None)

            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, None, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)
            hwnd_code = win32gui.FindWindowEx(hwnd_mid2, hwnd_prev, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_code, 0x01))
            enter_keys(win32gui.GetDlgItem(hwnd_code, 0x01), code)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_mid3, 0x834))
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid1, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_mid1, hwnd_prev, "AfxWnd110", None)
            hwnd_date = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_date, 0x7D1))
            press_keys(int(date[0]))
            press_keys(int(date[1]))
            press_keys(int(date[2]))
            press_keys(int(date[3]))
            press_keys(int(date[4]))
            press_keys(int(date[5]))
            press_keys(int(date[6]))
            press_keys(int(date[7]))
            win32api.Sleep(200)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_mid3, 0x838))
            hwnd_prev = win32gui.FindWindowEx(hwnd_mid1, None, "AfxWnd110", None)
            hwnd_part = win32gui.FindWindowEx(hwnd_mid1, hwnd_prev, "AfxWnd110", None)
            hwnd_date = win32gui.FindWindowEx(hwnd_part, None, "AfxWnd110", None)

            leftClick(15, 15, win32gui.GetDlgItem(hwnd_date, 0x7D1))
            press_keys(int(date[4]))
            press_keys(int(date[5]))
            press_keys(int(date[6]))
            press_keys(int(date[7]))
        except:
            self.ui.windowQ.put((ui_num['시스템로그'], '키움HTS에 멀티차트가 없거나 일봉, 분봉 차트 두개로 설정되어 있지 않습니다.'))
            self.ui.windowQ.put((ui_num['시스템로그'], '2x1로 좌측은 일봉, 우측은 분봉, 종목일괄변경으로 설정하신 다음 실행하십시오.'))

        win32gui.SetForegroundWindow(int(self.ui.winId()))
