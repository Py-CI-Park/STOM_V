
from PyQt5.QtWidgets import QWidget, QLabel, QGroupBox
from ui.set_widget import error_decorator
from ui.set_style import qfont12, style_pgbar


class SetMainMenu:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    @error_decorator
    def set(self):
        self.ui.setFont(qfont12)
        self.ui.setWindowTitle('STOM')
        self.ui.setWindowIcon(self.ui.icon_main)
        self.ui.geometry().center()

        self.ui.pushButton_00 = self.wc.setPushbutton('', icon=self.ui.icon_home,   color=1, click=self.ui.mnButtonClicked_01, cmd=0, animated=True, shortcut='Ctrl+1', tip='홈(Ctrl+1)')
        self.ui.pushButton_01 = self.wc.setPushbutton('', icon=self.ui.icon_stock,  color=6, click=self.ui.mnButtonClicked_01, cmd=1, animated=True, shortcut='Ctrl+2', tip='주식 및 해선 트레이더(Ctrl+2)')
        self.ui.pushButton_02 = self.wc.setPushbutton('', icon=self.ui.icon_coin,   color=6, click=self.ui.mnButtonClicked_01, cmd=2, animated=True, shortcut='Ctrl+3', tip='업비트 및 바이낸스 트레이더(Ctrl+3)')
        self.ui.pushButton_03 = self.wc.setPushbutton('', icon=self.ui.icon_stocks, color=6, click=self.ui.mnButtonClicked_01, cmd=3, animated=True, shortcut='Ctrl+4', tip='주식 및 해선 전략(Ctrl+4)')
        self.ui.pushButton_04 = self.wc.setPushbutton('', icon=self.ui.icon_coins,  color=6, click=self.ui.mnButtonClicked_01, cmd=4, animated=True, shortcut='Ctrl+5', tip='업비트 및 바이낸스 전략(Ctrl+5)')
        self.ui.pushButton_05 = self.wc.setPushbutton('', icon=self.ui.icon_live,   color=6, click=self.ui.mnButtonClicked_01, cmd=5, animated=True, shortcut='Ctrl+6', tip='스톰 라이브(Ctrl+6)')
        self.ui.pushButton_06 = self.wc.setPushbutton('', icon=self.ui.icon_log,    color=6, click=self.ui.mnButtonClicked_01, cmd=6, animated=True, shortcut='Ctrl+7', tip='로그(Ctrl+7)')
        self.ui.pushButton_07 = self.wc.setPushbutton('', icon=self.ui.icon_set,    color=6, click=self.ui.mnButtonClicked_01, cmd=7, animated=True, shortcut='Ctrl+8', tip='설정(Ctrl+8)')

        self.ui.main_btn_list = [
            self.ui.pushButton_00, self.ui.pushButton_01, self.ui.pushButton_02, self.ui.pushButton_03,
            self.ui.pushButton_04, self.ui.pushButton_05, self.ui.pushButton_06, self.ui.pushButton_07
        ]

        self.ui.hm_tab = QGroupBox('', self.ui)
        self.ui.st_tab = QGroupBox('', self.ui)
        self.ui.ct_tab = QGroupBox('', self.ui)
        self.ui.ss_tab = QGroupBox('', self.ui)
        self.ui.cs_tab = QGroupBox('', self.ui)
        self.ui.lv_tab = QGroupBox('', self.ui)
        self.ui.lg_tab = QGroupBox('', self.ui)
        self.ui.sj_tab = QGroupBox('', self.ui)

        self.ui.hm_tab.setVisible(True)
        self.ui.st_tab.setVisible(False)
        self.ui.ct_tab.setVisible(False)
        self.ui.ss_tab.setVisible(False)
        self.ui.cs_tab.setVisible(False)
        self.ui.lv_tab.setVisible(False)
        self.ui.lg_tab.setVisible(False)
        self.ui.sj_tab.setVisible(False)

        self.ui.main_box_list = [
            self.ui.hm_tab, self.ui.st_tab, self.ui.ct_tab, self.ui.ss_tab, self.ui.cs_tab, self.ui.lv_tab, self.ui.lg_tab, self.ui.sj_tab
        ]

        self.ui.slv_tab = QWidget()
        self.ui.clv_tab = QWidget()
        self.ui.flv_tab = QWidget()
        self.ui.blv_tab = QWidget()

        self.ui.progressBarrr = self.wc.setProgressBar(self.ui, vertical=True, style=style_pgbar)
        self.ui.at_pushButton = self.wc.setPushbutton('Alt', animated=True)
        self.ui.tt_pushButton = self.wc.setPushbutton('T', color=6, click=self.ui.mnButtonClicked_02, shortcut='Alt+T', animated=True, tip='수익집계')
        self.ui.ms_pushButton = self.wc.setPushbutton('L', color=6, click=self.ui.mnButtonClicked_03, shortcut='Alt+L', animated=True, tip='수동시작')
        self.ui.dd_pushButton = self.wc.setPushbutton('D', color=6, click=self.ui.ShowDB,             shortcut='Alt+D', animated=True, tip='DB관리')
        self.ui.zo_pushButton = self.wc.setPushbutton('Z', color=6, click=self.ui.mnButtonClicked_04, shortcut='Alt+Z', animated=True, tip='축소확대')
        self.ui.kp_pushButton = self.wc.setPushbutton('K', color=6, click=self.ui.ShowKimp,           shortcut='Alt+K', animated=True, tip='김프')
        self.ui.ct_pushButton = self.wc.setPushbutton('C', color=6, click=self.ui.ShowChart,          shortcut='Alt+C', animated=True, tip='차트창')
        self.ui.hg_pushButton = self.wc.setPushbutton('H', color=6, click=self.ui.ShowHoga,           shortcut='Alt+H', animated=True, tip='호가창')
        self.ui.gu_pushButton = self.wc.setPushbutton('G', color=6, click=self.ui.ShowGiup,           shortcut='Alt+G', animated=True, tip='기업정보')
        self.ui.uj_pushButton = self.wc.setPushbutton('U', color=6, click=self.ui.ShowTreemap,        shortcut='Alt+U', animated=True, tip='트리맵')
        self.ui.qs_pushButton = self.wc.setPushbutton('Q', color=6, click=self.ui.ShowQsize,          shortcut='Alt+Q', animated=True, tip='큐사이즈')
        self.ui.bs_pushButton = self.wc.setPushbutton('B', color=6, click=self.ui.ShowBackScheduler,  shortcut='Alt+B', animated=True, tip='백테스케쥴러')
        self.ui.sf_pushButton = self.wc.setPushbutton('Shift', animated=True)
        self.ui.bb_pushButton = self.wc.setPushbutton('S', color=6, click=self.ui.ChartScreenShot,    shortcut='Shift+S', animated=True, tip='차트창 스샷 텔레그램 전송')
        self.ui.ds_pushButton = self.wc.setPushbutton('Q', color=6, click=self.ui.ManualSaveAndExit,  shortcut='Shift+Q', animated=True, tip='데이터 저장 및 수동 종료')
        self.ui.od_pushButton = self.wc.setPushbutton('O', color=6, click=self.ui.ShowOrder,          shortcut='Shift+O', animated=True, tip='수동주문창')
        self.ui.zz_pushButton = self.wc.setPushbutton('E', color=6, click=self.ui.ExtendWindow,       shortcut='Shift+E', animated=True, tip='전략탭확장')
        self.ui.cl_pushButton = self.wc.setPushbutton('Ctrl', animated=True)
        self.ui.bd_pushButton = self.wc.setPushbutton('B', color=6, click=self.ui.mnButtonClicked_05, shortcut='Ctrl+B', animated=True, tip='백테기록삭제')
        self.ui.ad_pushButton = self.wc.setPushbutton('A', color=6, click=self.ui.mnButtonClicked_06, shortcut='Ctrl+A', animated=True, tip='계정삭제')

        self.ui.image_label1 = QLabel(self.ui)
        self.ui.image_label2 = QLabel(self.ui)
        self.ui.image_label1.setVisible(False)
        self.ui.image_label2.setVisible(False)

        self.ui.setFixedSize(1403, 763)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.move(self.ui.dict_set['창위치'][0], self.ui.dict_set['창위치'][1])
            except:
                pass
        self.ui.pushButton_00.setGeometry(5, 5, 35, 40)
        self.ui.pushButton_01.setGeometry(5, 45, 35, 40)
        self.ui.pushButton_02.setGeometry(5, 85, 35, 40)
        self.ui.pushButton_03.setGeometry(5, 125, 35, 40)
        self.ui.pushButton_04.setGeometry(5, 165, 35, 40)
        self.ui.pushButton_05.setGeometry(5, 205, 35, 40)
        self.ui.pushButton_06.setGeometry(5, 245, 35, 40)
        self.ui.pushButton_07.setGeometry(5, 285, 35, 40)
        self.ui.hm_tab.setGeometry(45, 0, 1353, 757)
        self.ui.st_tab.setGeometry(45, 0, 1353, 757)
        self.ui.ct_tab.setGeometry(45, 0, 1353, 757)
        self.ui.ss_tab.setGeometry(45, 0, 1353, 757)
        self.ui.cs_tab.setGeometry(45, 0, 1353, 757)
        self.ui.lg_tab.setGeometry(45, 0, 1353, 757)
        self.ui.sj_tab.setGeometry(45, 0, 1353, 757)
        self.ui.lv_tab.setGeometry(45, 0, 1353, 757)
        self.ui.at_pushButton.setGeometry(5, 330, 35, 15)
        self.ui.tt_pushButton.setGeometry(8, 350, 16, 15)
        self.ui.ms_pushButton.setGeometry(23, 350, 16, 15)
        self.ui.dd_pushButton.setGeometry(8, 370, 16, 15)
        self.ui.zo_pushButton.setGeometry(23, 370, 16, 15)
        self.ui.kp_pushButton.setGeometry(8, 390, 16, 15)
        self.ui.ct_pushButton.setGeometry(23, 390, 16, 15)
        self.ui.hg_pushButton.setGeometry(8, 410, 16, 15)
        self.ui.gu_pushButton.setGeometry(23, 410, 16, 15)
        self.ui.uj_pushButton.setGeometry(8, 430, 16, 15)
        self.ui.qs_pushButton.setGeometry(23, 430, 16, 15)
        self.ui.bs_pushButton.setGeometry(8, 450, 16, 15)

        self.ui.sf_pushButton.setGeometry(5, 470, 35, 15)
        self.ui.bb_pushButton.setGeometry(8, 490, 16, 15)
        self.ui.ds_pushButton.setGeometry(23, 490, 16, 15)
        self.ui.od_pushButton.setGeometry(8, 510, 16, 15)
        self.ui.zz_pushButton.setGeometry(23, 510, 16, 15)

        self.ui.cl_pushButton.setGeometry(5, 530, 35, 15)
        self.ui.bd_pushButton.setGeometry(8, 550, 16, 15)
        self.ui.ad_pushButton.setGeometry(23, 550, 16, 15)

        self.ui.progressBarrr.setGeometry(6, 570, 35, 187)
        self.ui.image_label1.setGeometry(1057, 478, 335, 105)
        self.ui.image_label2.setGeometry(1057, 756, 335, 602)
