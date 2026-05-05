
from ui.event_click.button_clicked_shortcut import *
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox
from ui.event_keypress.extend_window import extend_window
from ui.create_widget.set_style import qfont12, style_pgbar
from ui.etcetera.etc import chart_screenshot, manual_save_and_exit
from ui.event_click.button_clicked_show_dialog import show_order, show_backscheduler, show_qsize, show_treemap, \
    show_db, show_kimp, show_chart, show_hoga, show_giup


class SetMainMenu:
    """메인 메뉴 설정 클래스입니다.
    메인 윈도우의 메뉴 버튼 및 단축키를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """메인 메뉴를 설정합니다."""
        self.ui.setFont(qfont12)
        self.ui.setWindowTitle('STOM')
        self.ui.setWindowIcon(self.ui.icon_main)
        self.ui.geometry().center()

        self.ui.pushButton_01 = self.wc.setPushbutton('', icon=self.ui.icon_home,   color=1, click=lambda: mnbutton_c_clicked_01(self.ui, 0), animated=True, shortcut='Ctrl+1', tip='홈(Ctrl+1)')
        self.ui.pushButton_02 = self.wc.setPushbutton('', icon=self.ui.icon_stock,  color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 1), animated=True, shortcut='Ctrl+2', tip='트레이더(Ctrl+2)')
        self.ui.pushButton_03 = self.wc.setPushbutton('', icon=self.ui.icon_stgs,   color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 2), animated=True, shortcut='Ctrl+3', tip='전략작성(Ctrl+3)')
        self.ui.pushButton_04 = self.wc.setPushbutton('', icon=self.ui.icon_live,   color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 3), animated=True, shortcut='Ctrl+4', tip='스톰라이브(Ctrl+4)')
        self.ui.pushButton_05 = self.wc.setPushbutton('', icon=self.ui.icon_log,    color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 4), animated=True, shortcut='Ctrl+5', tip='로그(Ctrl+5)')
        self.ui.pushButton_06 = self.wc.setPushbutton('', icon=self.ui.icon_set,    color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 5), animated=True, shortcut='Ctrl+6', tip='설정(Ctrl+6)')

        self.ui.main_btn_list = [
            self.ui.pushButton_01, self.ui.pushButton_02, self.ui.pushButton_03, self.ui.pushButton_04,
            self.ui.pushButton_05, self.ui.pushButton_06
        ]

        self.ui.hm_tab = QGroupBox('', self.ui)
        self.ui.td_tab = QGroupBox('', self.ui)
        self.ui.st_tab = QGroupBox('', self.ui)
        self.ui.lv_tab = QGroupBox('', self.ui)
        self.ui.lg_tab = QGroupBox('', self.ui)
        self.ui.sj_tab = QGroupBox('', self.ui)

        self.ui.hm_tab.setVisible(True)
        self.ui.td_tab.setVisible(False)
        self.ui.st_tab.setVisible(False)
        self.ui.lv_tab.setVisible(False)
        self.ui.lg_tab.setVisible(False)
        self.ui.sj_tab.setVisible(False)

        self.ui.main_box_list = [
            self.ui.hm_tab, self.ui.td_tab, self.ui.st_tab, self.ui.lv_tab, self.ui.lg_tab, self.ui.sj_tab
        ]

        self.ui.slv_tab = QWidget()
        self.ui.clv_tab = QWidget()
        self.ui.flv_tab = QWidget()
        self.ui.blv_tab = QWidget()

        self.ui.progressBarrr = self.wc.setProgressBar(self.ui, vertical=True, style=style_pgbar)
        self.ui.at_pushButton = self.wc.setPushbutton('Alt', animated=True)
        self.ui.tt_pushButton = self.wc.setPushbutton('T', color=6, click=lambda: mnbutton_c_clicked_02(self.ui), shortcut='Alt+T',   animated=True, tip='수익집계')
        self.ui.ms_pushButton = self.wc.setPushbutton('L', color=6, click=lambda: mnbutton_c_clicked_03(self.ui), shortcut='Alt+L',   animated=True, tip='수동시작')
        self.ui.dd_pushButton = self.wc.setPushbutton('D', color=6, click=lambda: show_db(self.ui),               shortcut='Alt+D',   animated=True, tip='DB관리')
        self.ui.zo_pushButton = self.wc.setPushbutton('Z', color=6, click=lambda: mnbutton_c_clicked_04(self.ui), shortcut='Alt+Z',   animated=True, tip='축소확대')
        self.ui.kp_pushButton = self.wc.setPushbutton('K', color=6, click=lambda: show_kimp(self.ui),             shortcut='Alt+K',   animated=True, tip='김프')
        self.ui.ct_pushButton = self.wc.setPushbutton('C', color=6, click=lambda: show_chart(self.ui),            shortcut='Alt+C',   animated=True, tip='차트창')
        self.ui.hg_pushButton = self.wc.setPushbutton('H', color=6, click=lambda: show_hoga(self.ui),             shortcut='Alt+H',   animated=True, tip='호가창')
        self.ui.gu_pushButton = self.wc.setPushbutton('G', color=6, click=lambda: show_giup(self.ui),             shortcut='Alt+G',   animated=True, tip='기업정보')
        self.ui.uj_pushButton = self.wc.setPushbutton('U', color=6, click=lambda: show_treemap(self.ui),          shortcut='Alt+U',   animated=True, tip='트리맵')
        self.ui.qs_pushButton = self.wc.setPushbutton('Q', color=6, click=lambda: show_qsize(self.ui),            shortcut='Alt+Q',   animated=True, tip='큐사이즈')
        self.ui.bs_pushButton = self.wc.setPushbutton('B', color=6, click=lambda: show_backscheduler(self.ui),    shortcut='Alt+B',   animated=True, tip='백테스케쥴러')
        self.ui.ex_pushButton = self.wc.setPushbutton('X', color=6, click=lambda: trade_process_kill(self.ui),    shortcut='Alt+X',   animated=True, tip='매매프로세스종료')
        self.ui.sf_pushButton = self.wc.setPushbutton('Shift', animated=True)
        self.ui.bb_pushButton = self.wc.setPushbutton('S', color=6, click=lambda: chart_screenshot(self.ui),      shortcut='Shift+S', animated=True, tip='차트창 스샷 텔레그램 전송')
        self.ui.ds_pushButton = self.wc.setPushbutton('Q', color=6, click=lambda: manual_save_and_exit(self.ui),  shortcut='Shift+Q', animated=True, tip='데이터 저장 및 수동 종료')
        self.ui.od_pushButton = self.wc.setPushbutton('O', color=6, click=lambda: show_order(self.ui),            shortcut='Shift+O', animated=True, tip='수동주문창')
        self.ui.zz_pushButton = self.wc.setPushbutton('E', color=6, click=lambda: extend_window(self.ui),         shortcut='Shift+E', animated=True, tip='전략탭확장')
        self.ui.cl_pushButton = self.wc.setPushbutton('Ctrl', animated=True)
        self.ui.bd_pushButton = self.wc.setPushbutton('B', color=6, click=lambda: mnbutton_c_clicked_05(self.ui), shortcut='Ctrl+B',  animated=True, tip='백테기록삭제')
        self.ui.ad_pushButton = self.wc.setPushbutton('A', color=6, click=lambda: mnbutton_c_clicked_06(self.ui), shortcut='Ctrl+A',  animated=True, tip='계정삭제')

        self.ui.image_label1 = QLabel(self.ui)
        self.ui.image_label2 = QLabel(self.ui)
        self.ui.image_label1.setVisible(False)
        self.ui.image_label2.setVisible(False)

        self.ui.setFixedSize(1403, 763)

        for i in range(6):
            y = 5 + i * 40
            getattr(self.ui, f'pushButton_{i+1:02d}').setGeometry(5, y, 35, 40)

        for tab in (self.ui.hm_tab, self.ui.td_tab, self.ui.st_tab, self.ui.lg_tab, self.ui.sj_tab, self.ui.lv_tab):
            tab.setGeometry(45, 0, 1353, 757)

        self.ui.at_pushButton.setGeometry(5, 250, 35, 15)
        self.ui.tt_pushButton.setGeometry(8, 270, 16, 15)
        self.ui.ms_pushButton.setGeometry(23, 270, 16, 15)
        self.ui.dd_pushButton.setGeometry(8, 290, 16, 15)
        self.ui.zo_pushButton.setGeometry(23, 290, 16, 15)
        self.ui.kp_pushButton.setGeometry(8, 310, 16, 15)
        self.ui.ct_pushButton.setGeometry(23, 310, 16, 15)
        self.ui.hg_pushButton.setGeometry(8, 330, 16, 15)
        self.ui.gu_pushButton.setGeometry(23, 330, 16, 15)
        self.ui.uj_pushButton.setGeometry(8, 350, 16, 15)
        self.ui.qs_pushButton.setGeometry(23, 350, 16, 15)
        self.ui.bs_pushButton.setGeometry(8, 370, 16, 15)
        self.ui.ex_pushButton.setGeometry(23, 370, 16, 15)

        self.ui.sf_pushButton.setGeometry(5, 390, 35, 15)
        self.ui.bb_pushButton.setGeometry(8, 410, 16, 15)
        self.ui.ds_pushButton.setGeometry(23, 410, 16, 15)
        self.ui.od_pushButton.setGeometry(8, 430, 16, 15)
        self.ui.zz_pushButton.setGeometry(23, 430, 16, 15)

        self.ui.cl_pushButton.setGeometry(5, 450, 35, 15)
        self.ui.bd_pushButton.setGeometry(8, 470, 16, 15)
        self.ui.ad_pushButton.setGeometry(23, 470, 16, 15)

        self.ui.progressBarrr.setGeometry(6, 490, 35, 267)

        self.ui.image_label1.setGeometry(1057, 478, 335, 105)
        self.ui.image_label2.setGeometry(1057, 756, 335, 602)
