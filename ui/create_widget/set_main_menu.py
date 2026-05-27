
from PyQt5.QtCore import Qt
from ui.event_click.button_clicked_shortcut import *
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox
from ui.event_keypress.extend_window import extend_window
from ui.etcetera.etc import chart_screenshot, manual_save_and_exit
from ui.create_widget.set_style import qfont12, style_pgbar2, color_fg_bc
from ui.event_click.button_clicked_show_dialog import show_order, show_backscheduler, show_qsize, show_treemap, \
    show_db, show_kimp, show_chart, show_hoga, show_giup


class SetMainMenu:
    """메인 메뉴 설정 클래스입니다.
    메인 윈도우의 메뉴 버튼 및 단축키를 설정합니다."""
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

        self.ui.pushButton_01 = self.wc.setPushbutton('', icon=self.ui.icon_home,   color=1, click=lambda: mnbutton_c_clicked_01(self.ui, 0), animated=True, tip='홈(Ctrl+1)')
        self.ui.pushButton_02 = self.wc.setPushbutton('', icon=self.ui.icon_stock,  color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 1), animated=True, tip='트레이더(Ctrl+2)')
        self.ui.pushButton_03 = self.wc.setPushbutton('', icon=self.ui.icon_stgs,   color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 2), animated=True, tip='전략작성(Ctrl+3)')
        self.ui.pushButton_04 = self.wc.setPushbutton('', icon=self.ui.icon_live,   color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 3), animated=True, tip='스톰라이브(Ctrl+4)')
        self.ui.pushButton_05 = self.wc.setPushbutton('', icon=self.ui.icon_log,    color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 4), animated=True, tip='로그(Ctrl+5)')
        self.ui.pushButton_06 = self.wc.setPushbutton('', icon=self.ui.icon_set,    color=6, click=lambda: mnbutton_c_clicked_01(self.ui, 5), animated=True, tip='설정(Ctrl+6)')

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

        self.ui.progressBar01 = self.wc.setProgressBar(self.ui, vertical=True, style=style_pgbar2)
        self.ui.progressBar02 = self.wc.setProgressBar(self.ui, vertical=True, style=style_pgbar2)
        self.ui.progressBar03 = self.wc.setProgressBar(self.ui, vertical=True, style=style_pgbar2)
        self.ui.progressBar01.setFormat('')
        self.ui.progressBar02.setFormat('')
        self.ui.progressBar03.setFormat('')

        self.ui.progressLbl01 = QLabel('CPU\n0%', self.ui)
        self.ui.progressLbl01.setAlignment(Qt.AlignCenter)
        self.ui.progressLbl01.setStyleSheet(f"color: {color_fg_bc.name()}; font-size: 11px; font-weight: bold;")
        self.ui.progressLbl01.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.ui.progressLbl02 = QLabel('MEM\n0%', self.ui)
        self.ui.progressLbl02.setAlignment(Qt.AlignCenter)
        self.ui.progressLbl02.setStyleSheet(f"color: {color_fg_bc.name()}; font-size: 11px; font-weight: bold;")
        self.ui.progressLbl02.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.ui.progressLbl03 = QLabel('NET\n0.0\nMbps', self.ui)
        self.ui.progressLbl03.setAlignment(Qt.AlignCenter)
        self.ui.progressLbl03.setStyleSheet(f"color: {color_fg_bc.name()}; font-size: 11px; font-weight: bold;")
        self.ui.progressLbl03.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.ui.at_pushButton = self.wc.setPushbutton('Alt', color=6, animated=True)
        self.ui.tt_pushButton = self.wc.setPushbutton('T', color=6, click=lambda: mnbutton_c_clicked_02(self.ui), animated=True, tip='수익집계')
        self.ui.ms_pushButton = self.wc.setPushbutton('L', color=6, click=lambda: mnbutton_c_clicked_03(self.ui), animated=True, tip='수동시작')
        self.ui.dd_pushButton = self.wc.setPushbutton('D', color=6, click=lambda: show_db(self.ui),               animated=True, tip='DB관리')
        self.ui.zo_pushButton = self.wc.setPushbutton('Z', color=6, click=lambda: mnbutton_c_clicked_04(self.ui), animated=True, tip='축소확대')
        self.ui.kp_pushButton = self.wc.setPushbutton('K', color=6, click=lambda: show_kimp(self.ui),             animated=True, tip='김프')
        self.ui.ct_pushButton = self.wc.setPushbutton('C', color=6, click=lambda: show_chart(self.ui),            animated=True, tip='차트창')
        self.ui.hg_pushButton = self.wc.setPushbutton('H', color=6, click=lambda: show_hoga(self.ui),             animated=True, tip='호가창')
        self.ui.gu_pushButton = self.wc.setPushbutton('G', color=6, click=lambda: show_giup(self.ui),             animated=True, tip='기업정보')
        self.ui.uj_pushButton = self.wc.setPushbutton('U', color=6, click=lambda: show_treemap(self.ui),          animated=True, tip='트리맵')
        self.ui.qs_pushButton = self.wc.setPushbutton('Q', color=6, click=lambda: show_qsize(self.ui),            animated=True, tip='큐사이즈')
        self.ui.bs_pushButton = self.wc.setPushbutton('B', color=6, click=lambda: show_backscheduler(self.ui),    animated=True, tip='백테스케쥴러')
        self.ui.ex_pushButton = self.wc.setPushbutton('X', color=6, click=lambda: trade_process_kill(self.ui),    animated=True, tip='매매프로세스종료')
        self.ui.bb_pushButton = self.wc.setPushbutton('S', color=6, click=lambda: chart_screenshot(self.ui),      animated=True, tip='차트창 스샷 텔레그램 전송')
        self.ui.ds_pushButton = self.wc.setPushbutton('V', color=6, click=lambda: manual_save_and_exit(self.ui),  animated=True, tip='데이터 저장 및 수동 종료')
        self.ui.od_pushButton = self.wc.setPushbutton('O', color=6, click=lambda: show_order(self.ui),            animated=True, tip='수동주문창')
        self.ui.zz_pushButton = self.wc.setPushbutton('E', color=6, click=lambda: extend_window(self.ui),         animated=True, tip='전략탭확장')
        self.ui.cl_pushButton = self.wc.setPushbutton('Ctrl', color=6, animated=True)
        self.ui.bd_pushButton = self.wc.setPushbutton('B', color=6, click=lambda: mnbutton_c_clicked_05(self.ui), animated=True, tip='백테기록삭제')
        self.ui.ad_pushButton = self.wc.setPushbutton('A', color=6, click=lambda: mnbutton_c_clicked_06(self.ui), animated=True, tip='계정삭제')

        self.ui.image_label1 = QLabel(self.ui)
        self.ui.image_label2 = QLabel(self.ui)
        self.ui.image_label1.setVisible(False)
        self.ui.image_label2.setVisible(False)

        self.ui.setFixedSize(1403, 763)

        for i in range(6):
            y = 5 + i * 40
            getattr(self.ui, f'pushButton_{i+1:02d}').setGeometry(6, y, 35, 40)

        for tab in (self.ui.hm_tab, self.ui.td_tab, self.ui.st_tab, self.ui.lg_tab, self.ui.sj_tab, self.ui.lv_tab):
            tab.setGeometry(45, 0, 1353, 757)

        self.ui.at_pushButton.setGeometry(6, 250, 35, 15)
        self.ui.tt_pushButton.setGeometry(6, 270, 17, 15)
        self.ui.ms_pushButton.setGeometry(24, 270, 17, 15)
        self.ui.dd_pushButton.setGeometry(6, 290, 17, 15)
        self.ui.zo_pushButton.setGeometry(24, 290, 17, 15)
        self.ui.kp_pushButton.setGeometry(6, 310, 17, 15)
        self.ui.ct_pushButton.setGeometry(24, 310, 17, 15)
        self.ui.hg_pushButton.setGeometry(6, 330, 17, 15)
        self.ui.gu_pushButton.setGeometry(24, 330, 17, 15)
        self.ui.uj_pushButton.setGeometry(6, 350, 17, 15)
        self.ui.qs_pushButton.setGeometry(24, 350, 17, 15)
        self.ui.bs_pushButton.setGeometry(6, 370, 17, 15)
        self.ui.ex_pushButton.setGeometry(24, 370, 17, 15)

        self.ui.bb_pushButton.setGeometry(6, 390, 17, 15)
        self.ui.ds_pushButton.setGeometry(24, 390, 17, 15)
        self.ui.od_pushButton.setGeometry(6, 410, 17, 15)
        self.ui.zz_pushButton.setGeometry(24, 410, 17, 15)

        self.ui.cl_pushButton.setGeometry(6, 430, 35, 15)
        self.ui.bd_pushButton.setGeometry(6, 450, 17, 15)
        self.ui.ad_pushButton.setGeometry(24, 450, 17, 15)

        self.ui.progressBar01.setGeometry(6, 470, 35, 93)
        self.ui.progressBar02.setGeometry(6, 568, 35, 93)
        self.ui.progressBar03.setGeometry(6, 666, 35, 92)
        self.ui.progressLbl01.setGeometry(6, 470, 35, 93)
        self.ui.progressLbl02.setGeometry(6, 568, 35, 93)
        self.ui.progressLbl03.setGeometry(6, 666, 35, 92)

        self.ui.image_label1.setGeometry(1057, 475, 335, 105)
        self.ui.image_label2.setGeometry(1057, 755, 335, 600)
