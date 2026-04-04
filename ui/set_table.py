
from PyQt5.QtCore import QDate
from ui.ui_etc import calendar_clicked
from ui.set_widget import error_decorator
from PyQt5.QtWidgets import QCalendarWidget, QTabWidget
from ui.ui_button_clicked_etc import ttbutton_clicked_01
from ui.ui_cell_clicked import cell_clicked_11, cell_clicked_01, cell_clicked_04, cell_clicked_05, cell_clicked_03
from utility.setting_base import columns_tt, columns_td, columns_tj, columns_jg, columns_gj, columns_cj, columns_dt, \
    columns_dd, columns_nt, columns_nd, columns_sb, columns_sd


class SetTable:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.stt_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_tt, 1)
        self.ui.std_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_td, 13, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.stj_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_tj, 1)
        self.ui.sjg_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_jg, 13, fixed=True, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.sgj_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_gj, 15, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.scj_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_cj, 15, fixed=True, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))

        self.ui.stock_basic_listt = [
            self.ui.stt_tableWidgettt, self.ui.std_tableWidgettt, self.ui.stj_tableWidgettt,
            self.ui.sjg_tableWidgettt, self.ui.sgj_tableWidgettt, self.ui.scj_tableWidgettt,
        ]

        self.ui.s_calendarWidgett = QCalendarWidget(self.ui.st_tab)
        todayDate = QDate.currentDate()
        self.ui.s_calendarWidgett.setCurrentPage(todayDate.year(), todayDate.month())
        self.ui.s_calendarWidgett.clicked.connect(lambda: calendar_clicked(self.ui, 'S'))
        self.ui.sdt_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_dt, 1)
        self.ui.sds_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_dd, 19, clicked=lambda row, col: cell_clicked_04(self.ui, row, col))

        self.ui.snt_pushButton_01 = self.wc.setPushbutton('일별집계', parent=self.ui.st_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'S일별집계'))
        self.ui.snt_pushButton_02 = self.wc.setPushbutton('월별집계', parent=self.ui.st_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'S월별집계'))
        self.ui.snt_pushButton_03 = self.wc.setPushbutton('연도별집계', parent=self.ui.st_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'S연도별집계'))
        self.ui.snt_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_nt, 1, clicked=lambda row, col: cell_clicked_11(self.ui, row, col))
        self.ui.sns_tableWidgettt = self.wc.setTablewidget(self.ui.st_tab, columns_nd, 28, clicked=lambda row, col: cell_clicked_05(self.ui, row, col))

        self.ui.stock_total_listt = [
            self.ui.s_calendarWidgett, self.ui.sdt_tableWidgettt, self.ui.sds_tableWidgettt, self.ui.snt_pushButton_01,
            self.ui.snt_pushButton_02, self.ui.snt_pushButton_03, self.ui.snt_tableWidgettt, self.ui.sns_tableWidgettt
        ]

        for widget in self.ui.stock_total_listt:
            widget.setVisible(False)

        self.ui.slv_tapWidgett_01 = QTabWidget(self.ui.lv_tab)
        self.ui.slv_index1 = self.ui.slv_tapWidgett_01.addTab(self.ui.slv_tab, '주식 라이브')
        self.ui.slv_index2 = self.ui.slv_tapWidgett_01.addTab(self.ui.clv_tab, '코인 라이브')
        self.ui.slv_index3 = self.ui.slv_tapWidgett_01.addTab(self.ui.flv_tab, '해선 라이브')
        self.ui.slv_index4 = self.ui.slv_tapWidgett_01.addTab(self.ui.blv_tab, '백테 라이브')

        self.ui.slsd_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_tt, 30)
        self.ui.slsn_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_nt, 1)
        self.ui.slst_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_nd, 28)

        self.ui.slcd_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_tt, 30)
        self.ui.slcn_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_nt, 1)
        self.ui.slct_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_nd, 28)

        self.ui.slfd_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_tt, 30)
        self.ui.slfn_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_nt, 1)
        self.ui.slft_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_nd, 28)

        self.ui.slbd_tableWidgett = self.wc.setTablewidget(self.ui.blv_tab, columns_sb, 3)
        self.ui.slbt_tableWidgett = self.wc.setTablewidget(self.ui.blv_tab, columns_sd, 26, vscroll=True)

        # =============================================================================================================

        self.ui.ctt_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_tt, 1)
        self.ui.ctd_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_td, 13, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.ctj_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_tj, 1)
        self.ui.cjg_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_jg, 13, fixed=True, clicked=lambda row, col: cell_clicked_03(self.ui, row, col))
        self.ui.cgj_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_gj, 15, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.ccj_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_cj, 15, fixed=True, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))

        self.ui.coin_basic_listtt = [
            self.ui.ctt_tableWidgettt, self.ui.ctd_tableWidgettt, self.ui.ctj_tableWidgettt,
            self.ui.cjg_tableWidgettt, self.ui.cgj_tableWidgettt, self.ui.ccj_tableWidgettt,
        ]

        self.ui.c_calendarWidgett = QCalendarWidget(self.ui.ct_tab)
        self.ui.c_calendarWidgett.setCurrentPage(todayDate.year(), todayDate.month())
        self.ui.c_calendarWidgett.clicked.connect(lambda: calendar_clicked(self.ui, 'C'))
        self.ui.cdt_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_dt, 1)
        self.ui.cds_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_dd, 19, clicked=lambda row, col: cell_clicked_04(self.ui, row, col))

        self.ui.cnt_pushButton_01 = self.wc.setPushbutton('일별집계', parent=self.ui.ct_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'C일별집계'))
        self.ui.cnt_pushButton_02 = self.wc.setPushbutton('월별집계', parent=self.ui.ct_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'C월별집계'))
        self.ui.cnt_pushButton_03 = self.wc.setPushbutton('연도별집계', parent=self.ui.ct_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, 'C연도별집계'))
        self.ui.cnt_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_nt, 1, clicked=lambda row, col: cell_clicked_11(self.ui, row, col))
        self.ui.cns_tableWidgettt = self.wc.setTablewidget(self.ui.ct_tab, columns_nd, 28, clicked=lambda row, col: cell_clicked_05(self.ui, row, col))

        self.ui.coin_total_listtt = [
            self.ui.c_calendarWidgett, self.ui.cdt_tableWidgettt, self.ui.cds_tableWidgettt, self.ui.cnt_pushButton_01,
            self.ui.cnt_pushButton_02, self.ui.cnt_pushButton_03, self.ui.cnt_tableWidgettt, self.ui.cns_tableWidgettt
        ]

        for widget in self.ui.coin_total_listtt:
            widget.setVisible(False)

        self.ui.stt_tableWidgettt.setGeometry(7, 10, 668, 42)
        self.ui.std_tableWidgettt.setGeometry(7, 57, 668, 320)
        self.ui.stj_tableWidgettt.setGeometry(7, 382, 668, 42)
        self.ui.sjg_tableWidgettt.setGeometry(7, 429, 668, 320)
        self.ui.sgj_tableWidgettt.setGeometry(680, 10, 668, 367)
        self.ui.scj_tableWidgettt.setGeometry(680, 382, 668, 367)

        self.ui.s_calendarWidgett.setGeometry(7, 10, 668, 245)
        self.ui.sdt_tableWidgettt.setGeometry(7, 260, 668, 42)
        self.ui.sds_tableWidgettt.setGeometry(7, 307, 668, 442)

        self.ui.snt_pushButton_01.setGeometry(680, 10, 219, 30)
        self.ui.snt_pushButton_02.setGeometry(904, 10, 219, 30)
        self.ui.snt_pushButton_03.setGeometry(1128, 10, 220, 30)
        self.ui.snt_tableWidgettt.setGeometry(680, 45, 668, 42)
        self.ui.sns_tableWidgettt.setGeometry(680, 92, 668, 657)

        self.ui.slv_tapWidgett_01.setGeometry(7, 10, 1341, 740)

        self.ui.slsd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slsn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.slst_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slcd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slcn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.slct_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slfd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slfn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.slft_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slbd_tableWidgett.setGeometry(5, 5, 1328, 89)
        self.ui.slbt_tableWidgett.setGeometry(5, 100, 1328, 607)

        self.ui.ctt_tableWidgettt.setGeometry(7, 10, 668, 42)
        self.ui.ctd_tableWidgettt.setGeometry(7, 57, 668, 320)
        self.ui.ctj_tableWidgettt.setGeometry(7, 382, 668, 42)
        self.ui.cjg_tableWidgettt.setGeometry(7, 429, 668, 320)
        self.ui.cgj_tableWidgettt.setGeometry(680, 10, 668, 367)
        self.ui.ccj_tableWidgettt.setGeometry(680, 382, 668, 367)

        self.ui.c_calendarWidgett.setGeometry(7, 10, 668, 245)
        self.ui.cdt_tableWidgettt.setGeometry(7, 260, 668, 42)
        self.ui.cds_tableWidgettt.setGeometry(7, 307, 668, 442)

        self.ui.cnt_pushButton_01.setGeometry(680, 10, 219, 30)
        self.ui.cnt_pushButton_02.setGeometry(904, 10, 219, 30)
        self.ui.cnt_pushButton_03.setGeometry(1128, 10, 220, 30)
        self.ui.cnt_tableWidgettt.setGeometry(680, 45, 668, 42)
        self.ui.cns_tableWidgettt.setGeometry(680, 92, 668, 657)
