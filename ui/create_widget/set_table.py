
from PyQt5.QtCore import QDate
from ui.etcetera.etc import calendar_clicked
from PyQt5.QtWidgets import QCalendarWidget, QTabWidget
from ui.event_click.button_clicked_etc import ttbutton_clicked_01
from ui.event_click.table_cell_clicked import cell_clicked_01, cell_clicked_02, cell_clicked_03, cell_clicked_04, \
    cell_clicked_10
from utility.settings.setting_base import columns_tt, columns_td, columns_tj, columns_jg, columns_gj, columns_cj, \
    columns_dt, columns_dd, columns_nt, columns_nd, columns_sb, columns_sd


class SetTable:
    """테이블 위젯 설정 클래스입니다.
    거래 내역, 집계, 라이브 데이터 등을 표시하는 테이블 위젯을 설정합니다.
    """
    def __init__(self, ui_class, wc):
        """테이블 위젯 설정을 초기화합니다.
        Args:
            ui_class: UI 클래스
            wc: 위젯 생성자
        """
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """테이블 위젯을 설정합니다."""
        self.ui.tt_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_tt, 1)
        self.ui.td_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_td, 13, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.tj_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_tj, 1)
        self.ui.jg_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_jg, 13, fixed=True, clicked=lambda row, col: cell_clicked_02(self.ui, row, col))
        self.ui.gj_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_gj, 15, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))
        self.ui.cj_tableWidgettt = self.wc.setTablewidget(self.ui.td_tab, columns_cj, 15, fixed=True, clicked=lambda row, col: cell_clicked_01(self.ui, row, col))

        self.ui.table_basic_listt = [
            self.ui.tt_tableWidgettt, self.ui.td_tableWidgettt, self.ui.tj_tableWidgettt,
            self.ui.jg_tableWidgettt, self.ui.gj_tableWidgettt, self.ui.cj_tableWidgettt,
        ]

        self.ui.calendarWidgetttt = QCalendarWidget(self.ui.td_tab)
        todayDate = QDate.currentDate()
        self.ui.calendarWidgetttt.setCurrentPage(todayDate.year(), todayDate.month())
        self.ui.calendarWidgetttt.clicked.connect(lambda: calendar_clicked(self.ui))
        self.ui.dt_tableWidgetttt = self.wc.setTablewidget(self.ui.td_tab, columns_dt, 1)
        self.ui.ds_tableWidgetttt = self.wc.setTablewidget(self.ui.td_tab, columns_dd, 19, clicked=lambda row, col: cell_clicked_03(self.ui, row, col))

        self.ui.nt_pushButtonn_01 = self.wc.setPushbutton('일별집계', parent=self.ui.td_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, '일별집계'))
        self.ui.nt_pushButtonn_02 = self.wc.setPushbutton('월별집계', parent=self.ui.td_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, '월별집계'))
        self.ui.nt_pushButtonn_03 = self.wc.setPushbutton('연도별집계', parent=self.ui.td_tab, animated=True, click=lambda: ttbutton_clicked_01(self.ui, '연도별집계'))
        self.ui.nt_tableWidgetttt = self.wc.setTablewidget(self.ui.td_tab, columns_nt, 1, clicked=lambda row, col: cell_clicked_10(self.ui, row, col))
        self.ui.ns_tableWidgetttt = self.wc.setTablewidget(self.ui.td_tab, columns_nd, 28, clicked=lambda row, col: cell_clicked_04(self.ui, row, col))

        self.ui.table_total_listt = [
            self.ui.calendarWidgetttt, self.ui.dt_tableWidgetttt, self.ui.ds_tableWidgetttt, self.ui.nt_pushButtonn_01,
            self.ui.nt_pushButtonn_02, self.ui.nt_pushButtonn_03, self.ui.nt_tableWidgetttt, self.ui.ns_tableWidgetttt
        ]

        for widget in self.ui.table_total_listt:
            widget.setVisible(False)

        self.ui.slv_tapWidgett_01 = QTabWidget(self.ui.lv_tab)
        self.ui.slv_index1 = self.ui.slv_tapWidgett_01.addTab(self.ui.slv_tab, '주식 라이브')
        self.ui.slv_index2 = self.ui.slv_tapWidgett_01.addTab(self.ui.clv_tab, '코인 라이브')
        self.ui.slv_index3 = self.ui.slv_tapWidgett_01.addTab(self.ui.flv_tab, '선물 라이브')
        self.ui.slv_index4 = self.ui.slv_tapWidgett_01.addTab(self.ui.blv_tab, '백테 라이브')

        self.ui.slsd_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_tt, 30)
        self.ui.slsn_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_nt, 1)
        self.ui.sltd_tableWidgett = self.wc.setTablewidget(self.ui.slv_tab, columns_nd, 28)

        self.ui.slcd_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_tt, 30)
        self.ui.slcn_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_nt, 1)
        self.ui.slct_tableWidgett = self.wc.setTablewidget(self.ui.clv_tab, columns_nd, 28)

        self.ui.slfd_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_tt, 30)
        self.ui.slfn_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_nt, 1)
        self.ui.slft_tableWidgett = self.wc.setTablewidget(self.ui.flv_tab, columns_nd, 28)

        self.ui.slbd_tableWidgett = self.wc.setTablewidget(self.ui.blv_tab, columns_sb, 3)
        self.ui.slbt_tableWidgett = self.wc.setTablewidget(self.ui.blv_tab, columns_sd, 26, vscroll=True)

        # =============================================================================================================

        self.ui.tt_tableWidgettt.setGeometry(7, 10, 668, 42)
        self.ui.td_tableWidgettt.setGeometry(7, 57, 668, 320)
        self.ui.tj_tableWidgettt.setGeometry(7, 382, 668, 42)
        self.ui.jg_tableWidgettt.setGeometry(7, 429, 668, 320)
        self.ui.gj_tableWidgettt.setGeometry(680, 10, 668, 367)
        self.ui.cj_tableWidgettt.setGeometry(680, 382, 668, 367)

        self.ui.calendarWidgetttt.setGeometry(7, 10, 668, 245)
        self.ui.dt_tableWidgetttt.setGeometry(7, 260, 668, 42)
        self.ui.ds_tableWidgetttt.setGeometry(7, 307, 668, 442)

        self.ui.nt_pushButtonn_01.setGeometry(680, 10, 219, 30)
        self.ui.nt_pushButtonn_02.setGeometry(904, 10, 219, 30)
        self.ui.nt_pushButtonn_03.setGeometry(1128, 10, 220, 30)
        self.ui.nt_tableWidgetttt.setGeometry(680, 45, 668, 42)
        self.ui.ns_tableWidgetttt.setGeometry(680, 92, 668, 657)

        self.ui.slv_tapWidgett_01.setGeometry(7, 10, 1341, 740)

        self.ui.slsd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slsn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.sltd_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slcd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slcn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.slct_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slfd_tableWidgett.setGeometry(5, 5, 663, 702)
        self.ui.slfn_tableWidgett.setGeometry(672, 5, 662, 42)
        self.ui.slft_tableWidgett.setGeometry(672, 52, 662, 655)

        self.ui.slbd_tableWidgett.setGeometry(5, 5, 1328, 89)
        self.ui.slbt_tableWidgett.setGeometry(5, 100, 1328, 607)
