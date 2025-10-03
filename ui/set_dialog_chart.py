import pyqtgraph as pg
from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout
from ui.set_style import style_bc_dk, style_ck_bx, color_bg_bk
from utility.setting import DICT_SET, indi_base


class SetDialogChart:
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        self.ui.dialog_chart = self.wc.setDialog('STOM CHART')
        self.ui.dialog_chart.geometry().center()
        self.ui.ct_groupBoxxxxx_01 = QGroupBox(' ', self.ui.dialog_chart)
        self.ui.ct_groupBoxxxxx_02 = QGroupBox(' ', self.ui.dialog_chart)

        self.ui.ct_dateEdittttt_01 = self.wc.setDateEdit(self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_labellllllll_01 = QLabel('시작시간', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_01 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.ct_labellllllll_02 = QLabel('종료시간', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_02 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.ct_labellllllll_03 = QLabel('평균틱수', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_03 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, ltext='30', style=style_bc_dk)
        self.ui.ct_labellllllll_04 = QLabel('종목코드', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_04 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, enter=self.ui.ReturnPress_01, style=style_bc_dk)
        self.ui.ct_labellllllll_05 = QLabel('종목명', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_05 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, enter=self.ui.ReturnPress_01, style=style_bc_dk)
        self.ui.ct_pushButtonnn_01 = self.wc.setPushbutton('검색하기', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.ReturnPress_01)
        self.ui.ct_checkBoxxxxx_01 = self.wc.setCheckBox('십자선', self.ui.ct_groupBoxxxxx_01, checked=True, style=style_ck_bx)
        self.ui.ct_checkBoxxxxx_02 = self.wc.setCheckBox('정보창', self.ui.ct_groupBoxxxxx_01, checked=True, style=style_ck_bx)
        text = '1. 시작시간과 종료시간을 설정하면 해당시간의 데이터만 표시됩니다.\n' \
               '2. 평균틱수를 설정하면 평균, 최고, 최저값의 기준이 설정한 값으로 변경됩니다.\n' \
               '3. 날짜선택 후 종목코드 및 종목명으로 차트를 검색할 수 있습니다.\n' \
               '4. 팩터설정 버튼 클릭 후 8개의 차트에 표시할 팩터를 선택할 수 있습니다.\n' \
               '5. 확장 버튼 클릭 시 설정한 날짜의 거래대금순위 종목의 리스트가 표시됩니다.\n' \
               '6. 확장 버튼은 최초 클릭 시 주식, 다시 클릭 시 코인으로 변경됩니다.\n' \
               '7. 확장 버튼 클릭 후 표시된 테이블에서 종목명 클릭 시 차트가 표시됩니다.\n' \
               '8. 차트에서 마우스 드레그로 영역을 선택하면 줌인됩니다.\n' \
               '9. 줌인된 상태에서 마우스 우클릭시 줌아웃됩니다.\n' \
               '10. 호가창이 열린 상태에서 마우스 좌클릭 시 해당 시간의 호가정보가 표시됩니다.\n' \
               '11. 키움 HTS에 멀티차트와도 연동됩니다. 단, 좌측 일봉, 우측 분봉 상태여야합니다.'
        self.ui.ct_pushButtonnn_02 = self.wc.setPushbutton('도움말', box=self.ui.ct_groupBoxxxxx_01, tip=text)
        self.ui.ct_pushButtonnn_03 = self.wc.setPushbutton('펙터설정', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.ShowDialogFactor)
        self.ui.ct_pushButtonnn_04 = self.wc.setPushbutton('CHART 8', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.ChartCountChange)
        self.ui.ct_pushButtonnn_06 = self.wc.setPushbutton('확장', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.ChartSizeChange)
        self.ui.ct_pushButtonnn_10 = self.wc.setPushbutton('', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.hgButtonClicked_01, cmd='이전', shortcut='Alt+left')
        self.ui.ct_pushButtonnn_11 = self.wc.setPushbutton('', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.hgButtonClicked_01, cmd='다음', shortcut='Alt+right')
        self.ui.ct_pushButtonnn_12 = self.wc.setPushbutton('', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.hgButtonClicked_02, cmd='매수', shortcut='Alt+up')
        self.ui.ct_pushButtonnn_13 = self.wc.setPushbutton('', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.hgButtonClicked_02, cmd='매도', shortcut='Alt+down')
        self.ui.ct_pushButtonnn_14 = self.wc.setPushbutton('', box=self.ui.ct_groupBoxxxxx_01, click=self.ui.ChartScreenShot2, shortcut='Shift+S')

        self.ui.ct_dateEdittttt_02 = self.wc.setDateEdit(self.ui.dialog_chart, changed=self.ui.ChartMoneyTopList)
        self.ui.ct_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_chart, ['종목명'], 100, vscroll=True, clicked=self.ui.CellClicked_07)

        self.ui.ctpg = {}
        self.ui.ctpg_cvb = {}
        pg.setConfigOption('background', color_bg_bk)
        self.ui.ctpg_layout = pg.GraphicsLayoutWidget()
        if (self.ui.dict_set['주식리시버'] and not self.ui.dict_set['주식타임프레임']) or \
                (self.ui.dict_set['코인리시버'] and not self.ui.dict_set['코인타임프레임']):
            self.ui.ctpg[0], self.ui.ctpg_cvb[0] = self.wc.setaddPlot(self.ui.ctpg_layout, 0, 0, colspan=2)
            self.ui.ctpg[1], self.ui.ctpg_cvb[1] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 0, colspan=2)
            self.ui.ctpg[2], self.ui.ctpg_cvb[2] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 0)
            self.ui.ctpg[3], self.ui.ctpg_cvb[3] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 0)
            self.ui.ctpg[4], self.ui.ctpg_cvb[4] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 1)
            self.ui.ctpg[5], self.ui.ctpg_cvb[5] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 1)
            qGraphicsGridLayout = self.ui.ctpg_layout.ci.layout
            qGraphicsGridLayout.setRowStretchFactor(0, 3)
            qGraphicsGridLayout.setRowStretchFactor(1, 2)
            qGraphicsGridLayout.setRowStretchFactor(2, 2)
            qGraphicsGridLayout.setRowStretchFactor(3, 2)
        else:
            self.ui.ctpg[0], self.ui.ctpg_cvb[0] = self.wc.setaddPlot(self.ui.ctpg_layout, 0, 0)
            self.ui.ctpg[1], self.ui.ctpg_cvb[1] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 0)
            self.ui.ctpg[2], self.ui.ctpg_cvb[2] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 0)
            self.ui.ctpg[3], self.ui.ctpg_cvb[3] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 0)
            self.ui.ctpg[4], self.ui.ctpg_cvb[4] = self.wc.setaddPlot(self.ui.ctpg_layout, 0, 1)
            self.ui.ctpg[5], self.ui.ctpg_cvb[5] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 1)
            self.ui.ctpg[6], self.ui.ctpg_cvb[6] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 1)
            self.ui.ctpg[7], self.ui.ctpg_cvb[7] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 1)
            qGraphicsGridLayout = self.ui.ctpg_layout.ci.layout
            qGraphicsGridLayout.setRowStretchFactor(0, 1)
            qGraphicsGridLayout.setRowStretchFactor(1, 1)
            qGraphicsGridLayout.setRowStretchFactor(2, 1)
            qGraphicsGridLayout.setRowStretchFactor(3, 1)

        self.ui.ctpg_vboxLayout = QVBoxLayout(self.ui.ct_groupBoxxxxx_02)
        self.ui.ctpg_vboxLayout.setContentsMargins(3, 6, 3, 3)
        self.ui.ctpg_vboxLayout.addWidget(self.ui.ctpg_layout)

        self.ui.dialog_jisu = self.wc.setDialog('STOM JISU')
        self.ui.dialog_jisu.geometry().center()
        self.ui.js_groupBox_01 = QGroupBox(' ', self.ui.dialog_jisu)

        self.ui.jspg = {}
        pg.setConfigOption('background', color_bg_bk)
        jspg = pg.GraphicsLayoutWidget()
        self.ui.jspg[1], _ = self.wc.setaddPlot(jspg, 0, 0, title='<span style="font-size:13px;font-family:나눔고딕;">KOSPI</span>')
        self.ui.jspg[2], _ = self.wc.setaddPlot(jspg, 1, 0, title='<span style="font-size:13px;font-family:나눔고딕;">KOSDAQ</span>')

        jspg_vboxLayout = QVBoxLayout(self.ui.js_groupBox_01)
        jspg_vboxLayout.setContentsMargins(3, 6, 3, 3)
        jspg_vboxLayout.addWidget(jspg)

        self.ui.dialog_factor = self.wc.setDialog('STOM FACTOR', tab=self.ui.dialog_chart)
        self.ui.dialog_factor.geometry().center()
        self.ui.jp_groupBoxxxxx_01 = QGroupBox(' ', self.ui.dialog_factor)

        is_min = (self.ui.dict_set['주식리시버'] and not self.ui.dict_set['주식타임프레임']) or \
                 (self.ui.dict_set['코인리시버'] and not self.ui.dict_set['코인타임프레임'])
        checkbox_choice = [int(x) for x in DICT_SET['팩터선택'].split(';')]
        self.ui.ft_checkBoxxxxx_01 = self.wc.setCheckBox('현재가', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[0] else False, changed=self.ui.CheckboxChanged_10, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_02 = self.wc.setCheckBox('분당거래대금' if is_min else '초당거래대금', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[1] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_03 = self.wc.setCheckBox('체결강도', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[2] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_04 = self.wc.setCheckBox('분당체결수량' if is_min else '초당체결수량', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[3] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_05 = self.wc.setCheckBox('등락율', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[4] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_06 = self.wc.setCheckBox('고저평균대비등락율', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[5] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_07 = self.wc.setCheckBox('호가총잔량', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[6] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_08 = self.wc.setCheckBox('매도수호가잔량1', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[7] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_09 = self.wc.setCheckBox('매도수5호가잔량합', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[8] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_10 = self.wc.setCheckBox('당일거래대금', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[9] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_11 = self.wc.setCheckBox('누적분당매도수수량' if is_min else '누적초당매도수수량', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[10] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_12 = self.wc.setCheckBox('등락율각도', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[11] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_13 = self.wc.setCheckBox('당일거래대금각도', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[12] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_14 = self.wc.setCheckBox('거래대금증감', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[13] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_15 = self.wc.setCheckBox('전일비', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[14] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_16 = self.wc.setCheckBox('회전율', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[15] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_17 = self.wc.setCheckBox('전일동시간비', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[16] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_18 = self.wc.setCheckBox('전일비각도', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[17] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)

        self.ui.ft_checkBoxxxxx_19 = self.wc.setCheckBox('AD',     self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[18] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_20 = self.wc.setCheckBox('ADOSC',  self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[19] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_21 = self.wc.setCheckBox('ADXR',   self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[20] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_22 = self.wc.setCheckBox('APO',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[21] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_23 = self.wc.setCheckBox('AROON',  self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[22] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_24 = self.wc.setCheckBox('ATR',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[23] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_25 = self.wc.setCheckBox('BBAND',  self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[24] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_26 = self.wc.setCheckBox('CCI',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[25] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_27 = self.wc.setCheckBox('DMI',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[26] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_28 = self.wc.setCheckBox('MACD',   self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[27] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_29 = self.wc.setCheckBox('MFI',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[28] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_30 = self.wc.setCheckBox('MOM',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[29] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_31 = self.wc.setCheckBox('OBV',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[30] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_32 = self.wc.setCheckBox('PPO',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[31] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_33 = self.wc.setCheckBox('ROC',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[32] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_34 = self.wc.setCheckBox('RSI',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[33] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_35 = self.wc.setCheckBox('SAR',    self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[34] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_36 = self.wc.setCheckBox('STOCHS', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[35] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_37 = self.wc.setCheckBox('STOCHF', self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[36] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)
        self.ui.ft_checkBoxxxxx_38 = self.wc.setCheckBox('WILLR',  self.ui.jp_groupBoxxxxx_01, checked=True if checkbox_choice[37] else False, changed=self.ui.CheckboxChanged_19, style=style_ck_bx)

        self.ui.ft_labellllllll_01 = QLabel('fastperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_02 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_03 = QLabel('fastperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_04 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_05 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_06 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_07 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_08 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_09 = QLabel('fastperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_10 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_11 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_12 = QLabel('fastperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_13 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_14 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_15 = QLabel('acceleration', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_16 = QLabel('fastk_period', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_17 = QLabel('fastk_period', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_18 = QLabel('timeperiod',   self.ui.jp_groupBoxxxxx_01)

        self.ui.ft_labellllllll_21 = QLabel('slowperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_23 = QLabel('slowperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_26 = QLabel('nbdevup',      self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_29 = QLabel('slowperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_32 = QLabel('slowperiod',   self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_35 = QLabel('maximum',      self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_36 = QLabel('slowk_period', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_37 = QLabel('fastd_period', self.ui.jp_groupBoxxxxx_01)

        self.ui.ft_labellllllll_43 = QLabel('matype',       self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_46 = QLabel('nbdevdn',      self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_49 = QLabel('signalperiod', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_52 = QLabel('matype',       self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_56 = QLabel('slowk_matype', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_57 = QLabel('fastd_matype', self.ui.jp_groupBoxxxxx_01)

        self.ui.ft_labellllllll_66 = QLabel('matype', self.ui.jp_groupBoxxxxx_01)
        self.ui.ft_labellllllll_76 = QLabel('slowd_period', self.ui.jp_groupBoxxxxx_01)

        self.ui.ft_labellllllll_96 = QLabel('slowd_matype', self.ui.jp_groupBoxxxxx_01)

        k = [str(x) for x in list(indi_base.values())]
        self.ui.ft_lineEdittttt_01 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[0], style=style_bc_dk)
        self.ui.ft_lineEdittttt_02 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[1], style=style_bc_dk)
        self.ui.ft_lineEdittttt_03 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[2], style=style_bc_dk)
        self.ui.ft_lineEdittttt_04 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[3], style=style_bc_dk)
        self.ui.ft_lineEdittttt_05 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[4], style=style_bc_dk)
        self.ui.ft_lineEdittttt_06 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[5], style=style_bc_dk)
        self.ui.ft_lineEdittttt_07 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[6], style=style_bc_dk)
        self.ui.ft_lineEdittttt_08 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[7], style=style_bc_dk)
        self.ui.ft_lineEdittttt_09 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[8], style=style_bc_dk)
        self.ui.ft_lineEdittttt_10 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[9], style=style_bc_dk)
        self.ui.ft_lineEdittttt_11 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[10], style=style_bc_dk)
        self.ui.ft_lineEdittttt_12 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[11], style=style_bc_dk)
        self.ui.ft_lineEdittttt_13 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[12], style=style_bc_dk)
        self.ui.ft_lineEdittttt_14 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[13], style=style_bc_dk)
        self.ui.ft_lineEdittttt_15 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[14], style=style_bc_dk)
        self.ui.ft_lineEdittttt_16 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[15], style=style_bc_dk)
        self.ui.ft_lineEdittttt_17 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[16], style=style_bc_dk)
        self.ui.ft_lineEdittttt_18 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[17], style=style_bc_dk)
        self.ui.ft_lineEdittttt_19 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[18], style=style_bc_dk)
        self.ui.ft_lineEdittttt_20 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[19], style=style_bc_dk)
        self.ui.ft_lineEdittttt_21 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[20], style=style_bc_dk)
        self.ui.ft_lineEdittttt_22 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[21], style=style_bc_dk)
        self.ui.ft_lineEdittttt_23 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[22], style=style_bc_dk)
        self.ui.ft_lineEdittttt_24 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[23], style=style_bc_dk)
        self.ui.ft_lineEdittttt_25 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[24], style=style_bc_dk)
        self.ui.ft_lineEdittttt_26 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[25], style=style_bc_dk)
        self.ui.ft_lineEdittttt_27 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[26], style=style_bc_dk)
        self.ui.ft_lineEdittttt_28 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[27], style=style_bc_dk)
        self.ui.ft_lineEdittttt_29 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[28], style=style_bc_dk)
        self.ui.ft_lineEdittttt_30 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[29], style=style_bc_dk)
        self.ui.ft_lineEdittttt_31 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[30], style=style_bc_dk)
        self.ui.ft_lineEdittttt_32 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[31], style=style_bc_dk)
        self.ui.ft_lineEdittttt_33 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[32], style=style_bc_dk)
        self.ui.ft_lineEdittttt_34 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[33], style=style_bc_dk)
        self.ui.ft_lineEdittttt_35 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, ltext=k[34], style=style_bc_dk)

        text = '매수전략으로 설정된\n보조지표값 사용하기\n체크를 해제하면\n좌측 설정값으로 표시됨'
        self.ui.ft_checkBoxxxxx_39 = self.wc.setCheckBox(text, self.ui.jp_groupBoxxxxx_01, checked=False, style=style_ck_bx)
        self.ui.ft_pushButtonnn_01 = self.wc.setPushbutton('보조지표설정 기본값', box=self.ui.jp_groupBoxxxxx_01, click=self.ui.ctButtonClicked_01)
        self.ui.ft_pushButtonnn_02 = self.wc.setPushbutton('보조지표설정 불러오기', box=self.ui.jp_groupBoxxxxx_01, click=self.ui.ctButtonClicked_02)
        self.ui.ft_pushButtonnn_03 = self.wc.setPushbutton('보조지표설정 저장하기', box=self.ui.jp_groupBoxxxxx_01, click=self.ui.ctButtonClicked_03)

        self.ui.factor_checkbox_list = [
            self.ui.ft_checkBoxxxxx_01, self.ui.ft_checkBoxxxxx_02, self.ui.ft_checkBoxxxxx_03, self.ui.ft_checkBoxxxxx_04,
            self.ui.ft_checkBoxxxxx_05, self.ui.ft_checkBoxxxxx_06, self.ui.ft_checkBoxxxxx_07, self.ui.ft_checkBoxxxxx_08,
            self.ui.ft_checkBoxxxxx_09, self.ui.ft_checkBoxxxxx_10, self.ui.ft_checkBoxxxxx_11, self.ui.ft_checkBoxxxxx_12,
            self.ui.ft_checkBoxxxxx_13, self.ui.ft_checkBoxxxxx_14, self.ui.ft_checkBoxxxxx_15, self.ui.ft_checkBoxxxxx_16,
            self.ui.ft_checkBoxxxxx_17, self.ui.ft_checkBoxxxxx_18, self.ui.ft_checkBoxxxxx_19, self.ui.ft_checkBoxxxxx_20,
            self.ui.ft_checkBoxxxxx_21, self.ui.ft_checkBoxxxxx_22, self.ui.ft_checkBoxxxxx_23, self.ui.ft_checkBoxxxxx_24,
            self.ui.ft_checkBoxxxxx_25, self.ui.ft_checkBoxxxxx_26, self.ui.ft_checkBoxxxxx_27, self.ui.ft_checkBoxxxxx_28,
            self.ui.ft_checkBoxxxxx_29, self.ui.ft_checkBoxxxxx_30, self.ui.ft_checkBoxxxxx_31, self.ui.ft_checkBoxxxxx_32,
            self.ui.ft_checkBoxxxxx_33, self.ui.ft_checkBoxxxxx_34, self.ui.ft_checkBoxxxxx_35, self.ui.ft_checkBoxxxxx_36,
            self.ui.ft_checkBoxxxxx_37, self.ui.ft_checkBoxxxxx_38
        ]

        self.ui.factor_linedit_list = [
            self.ui.ft_lineEdittttt_01, self.ui.ft_lineEdittttt_02, self.ui.ft_lineEdittttt_03, self.ui.ft_lineEdittttt_04,
            self.ui.ft_lineEdittttt_05, self.ui.ft_lineEdittttt_06, self.ui.ft_lineEdittttt_07, self.ui.ft_lineEdittttt_08,
            self.ui.ft_lineEdittttt_09, self.ui.ft_lineEdittttt_10, self.ui.ft_lineEdittttt_11, self.ui.ft_lineEdittttt_12,
            self.ui.ft_lineEdittttt_13, self.ui.ft_lineEdittttt_14, self.ui.ft_lineEdittttt_15, self.ui.ft_lineEdittttt_16,
            self.ui.ft_lineEdittttt_17, self.ui.ft_lineEdittttt_18, self.ui.ft_lineEdittttt_19, self.ui.ft_lineEdittttt_20,
            self.ui.ft_lineEdittttt_21, self.ui.ft_lineEdittttt_22, self.ui.ft_lineEdittttt_23, self.ui.ft_lineEdittttt_24,
            self.ui.ft_lineEdittttt_25, self.ui.ft_lineEdittttt_26, self.ui.ft_lineEdittttt_27, self.ui.ft_lineEdittttt_28,
            self.ui.ft_lineEdittttt_29, self.ui.ft_lineEdittttt_30, self.ui.ft_lineEdittttt_31, self.ui.ft_lineEdittttt_32,
            self.ui.ft_lineEdittttt_33, self.ui.ft_lineEdittttt_34, self.ui.ft_lineEdittttt_35
        ]

        self.ui.dialog_chart.setFixedSize(1403, 1370 if not DICT_SET['저해상도'] else 1010)
        if self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_chart.move(self.ui.dict_set['창위치'][2], self.ui.dict_set['창위치'][3])
            except:
                pass
        self.ui.ct_groupBoxxxxx_01.setGeometry(5, -10, 1393, 62)
        self.ui.ct_groupBoxxxxx_02.setGeometry(5, 40, 1393, 1325 if not DICT_SET['저해상도'] else 965)

        self.ui.ct_dateEdittttt_01.setGeometry(10, 25, 100, 30)
        self.ui.ct_labellllllll_01.setGeometry(120, 25, 50, 30)
        self.ui.ct_lineEdittttt_01.setGeometry(170, 25, 60, 30)
        self.ui.ct_labellllllll_02.setGeometry(240, 25, 50, 30)
        self.ui.ct_lineEdittttt_02.setGeometry(290, 25, 60, 30)
        self.ui.ct_labellllllll_03.setGeometry(360, 25, 50, 30)
        self.ui.ct_lineEdittttt_03.setGeometry(410, 25, 60, 30)
        self.ui.ct_labellllllll_04.setGeometry(480, 25, 50, 30)
        self.ui.ct_lineEdittttt_04.setGeometry(530, 25, 60, 30)
        self.ui.ct_labellllllll_05.setGeometry(605, 25, 50, 30)
        self.ui.ct_lineEdittttt_05.setGeometry(655, 25, 100, 30)
        self.ui.ct_pushButtonnn_01.setGeometry(765, 25, 60, 30)
        self.ui.ct_checkBoxxxxx_01.setGeometry(835, 25, 60, 30)
        self.ui.ct_checkBoxxxxx_02.setGeometry(900, 25, 60, 30)
        self.ui.ct_pushButtonnn_02.setGeometry(1050, 25, 80, 30)
        self.ui.ct_pushButtonnn_03.setGeometry(1135, 25, 80, 30)
        self.ui.ct_pushButtonnn_04.setGeometry(1220, 25, 80, 30)
        self.ui.ct_pushButtonnn_06.setGeometry(1305, 25, 80, 30)
        self.ui.ct_pushButtonnn_10.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_11.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_12.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_13.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_14.setGeometry(0, 0, 0, 0)

        self.ui.ct_dateEdittttt_02.setGeometry(1403, 15, 120, 30)
        self.ui.ct_tableWidgett_01.setGeometry(1403, 55, 120, 1310 if not DICT_SET['저해상도'] else 950)

        self.ui.dialog_jisu.setFixedSize(770, 700)
        if self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_jisu.move(self.ui.dict_set['창위치'][6], self.ui.dict_set['창위치'][7])
            except:
                pass
        self.ui.js_groupBox_01.setGeometry(5, -10, 760, 700)

        self.ui.dialog_factor.setFixedSize(850, 595)
        self.ui.jp_groupBoxxxxx_01.setGeometry(5, -10, 840, 600)
        self.ui.ft_checkBoxxxxx_01.setGeometry(10, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_02.setGeometry(150, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_03.setGeometry(290, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_04.setGeometry(430, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_05.setGeometry(570, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_06.setGeometry(710, 25, 120, 20)
        self.ui.ft_checkBoxxxxx_07.setGeometry(10, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_08.setGeometry(150, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_09.setGeometry(290, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_10.setGeometry(430, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_11.setGeometry(570, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_12.setGeometry(710, 50, 120, 20)
        self.ui.ft_checkBoxxxxx_13.setGeometry(10, 75, 120, 20)
        self.ui.ft_checkBoxxxxx_14.setGeometry(150, 75, 120, 20)
        self.ui.ft_checkBoxxxxx_15.setGeometry(290, 75, 120, 20)
        self.ui.ft_checkBoxxxxx_16.setGeometry(430, 75, 120, 20)
        self.ui.ft_checkBoxxxxx_17.setGeometry(570, 75, 120, 20)
        self.ui.ft_checkBoxxxxx_18.setGeometry(710, 75, 120, 20)

        self.ui.ft_checkBoxxxxx_19.setGeometry(10, 100, 380, 20)
        self.ui.ft_checkBoxxxxx_20.setGeometry(10, 125, 380, 20)
        self.ui.ft_checkBoxxxxx_21.setGeometry(10, 150, 380, 20)
        self.ui.ft_checkBoxxxxx_22.setGeometry(10, 175, 380, 20)
        self.ui.ft_checkBoxxxxx_23.setGeometry(10, 200, 380, 20)
        self.ui.ft_checkBoxxxxx_24.setGeometry(10, 225, 380, 20)
        self.ui.ft_checkBoxxxxx_25.setGeometry(10, 250, 380, 20)
        self.ui.ft_checkBoxxxxx_26.setGeometry(10, 275, 380, 20)
        self.ui.ft_checkBoxxxxx_27.setGeometry(10, 300, 380, 20)
        self.ui.ft_checkBoxxxxx_28.setGeometry(10, 325, 380, 20)
        self.ui.ft_checkBoxxxxx_29.setGeometry(10, 350, 380, 20)
        self.ui.ft_checkBoxxxxx_30.setGeometry(10, 375, 380, 20)
        self.ui.ft_checkBoxxxxx_31.setGeometry(10, 400, 380, 20)
        self.ui.ft_checkBoxxxxx_32.setGeometry(10, 425, 380, 20)
        self.ui.ft_checkBoxxxxx_33.setGeometry(10, 450, 380, 20)
        self.ui.ft_checkBoxxxxx_34.setGeometry(10, 475, 380, 20)
        self.ui.ft_checkBoxxxxx_35.setGeometry(10, 500, 380, 20)
        self.ui.ft_checkBoxxxxx_36.setGeometry(10, 525, 380, 20)
        self.ui.ft_checkBoxxxxx_37.setGeometry(10, 550, 380, 20)
        self.ui.ft_checkBoxxxxx_38.setGeometry(10, 575, 380, 20)

        self.ui.ft_labellllllll_01.setGeometry(100, 125, 300, 20)
        self.ui.ft_labellllllll_02.setGeometry(100, 150, 300, 20)
        self.ui.ft_labellllllll_03.setGeometry(100, 175, 300, 20)
        self.ui.ft_labellllllll_04.setGeometry(100, 200, 300, 20)
        self.ui.ft_labellllllll_05.setGeometry(100, 225, 300, 20)
        self.ui.ft_labellllllll_06.setGeometry(100, 250, 300, 20)
        self.ui.ft_labellllllll_07.setGeometry(100, 275, 300, 20)
        self.ui.ft_labellllllll_08.setGeometry(100, 300, 300, 20)
        self.ui.ft_labellllllll_09.setGeometry(100, 325, 300, 20)
        self.ui.ft_labellllllll_10.setGeometry(100, 350, 300, 20)
        self.ui.ft_labellllllll_11.setGeometry(100, 375, 300, 20)
        self.ui.ft_labellllllll_12.setGeometry(100, 425, 300, 20)
        self.ui.ft_labellllllll_13.setGeometry(100, 450, 300, 20)
        self.ui.ft_labellllllll_14.setGeometry(100, 475, 300, 20)
        self.ui.ft_labellllllll_15.setGeometry(100, 500, 300, 20)
        self.ui.ft_labellllllll_16.setGeometry(100, 525, 300, 20)
        self.ui.ft_labellllllll_17.setGeometry(100, 550, 300, 20)
        self.ui.ft_labellllllll_18.setGeometry(100, 575, 300, 20)

        self.ui.ft_labellllllll_21.setGeometry(250, 125, 300, 20)
        self.ui.ft_labellllllll_23.setGeometry(250, 175, 300, 20)
        self.ui.ft_labellllllll_26.setGeometry(250, 250, 300, 20)
        self.ui.ft_labellllllll_29.setGeometry(250, 325, 300, 20)
        self.ui.ft_labellllllll_32.setGeometry(250, 425, 300, 20)
        self.ui.ft_labellllllll_35.setGeometry(250, 500, 300, 20)
        self.ui.ft_labellllllll_36.setGeometry(250, 525, 300, 20)
        self.ui.ft_labellllllll_37.setGeometry(250, 550, 300, 20)

        self.ui.ft_labellllllll_43.setGeometry(400, 175, 300, 20)
        self.ui.ft_labellllllll_46.setGeometry(400, 250, 300, 20)
        self.ui.ft_labellllllll_49.setGeometry(400, 325, 300, 20)
        self.ui.ft_labellllllll_52.setGeometry(400, 425, 300, 20)
        self.ui.ft_labellllllll_56.setGeometry(400, 525, 300, 20)
        self.ui.ft_labellllllll_57.setGeometry(400, 550, 300, 20)

        self.ui.ft_labellllllll_66.setGeometry(550, 250, 300, 20)
        self.ui.ft_labellllllll_76.setGeometry(550, 525, 300, 20)

        self.ui.ft_labellllllll_96.setGeometry(700, 525, 300, 20)

        self.ui.ft_lineEdittttt_01.setGeometry(180, 125, 40, 20)
        self.ui.ft_lineEdittttt_02.setGeometry(330, 125, 40, 20)
        self.ui.ft_lineEdittttt_03.setGeometry(180, 150, 40, 20)
        self.ui.ft_lineEdittttt_04.setGeometry(180, 175, 40, 20)
        self.ui.ft_lineEdittttt_05.setGeometry(330, 175, 40, 20)
        self.ui.ft_lineEdittttt_06.setGeometry(480, 175, 40, 20)
        self.ui.ft_lineEdittttt_07.setGeometry(180, 200, 40, 20)
        self.ui.ft_lineEdittttt_08.setGeometry(180, 225, 40, 20)
        self.ui.ft_lineEdittttt_09.setGeometry(180, 250, 40, 20)
        self.ui.ft_lineEdittttt_10.setGeometry(330, 250, 40, 20)
        self.ui.ft_lineEdittttt_11.setGeometry(480, 250, 40, 20)
        self.ui.ft_lineEdittttt_12.setGeometry(630, 250, 40, 20)
        self.ui.ft_lineEdittttt_13.setGeometry(180, 275, 40, 20)
        self.ui.ft_lineEdittttt_14.setGeometry(180, 300, 40, 20)
        self.ui.ft_lineEdittttt_15.setGeometry(180, 325, 40, 20)
        self.ui.ft_lineEdittttt_16.setGeometry(330, 325, 40, 20)
        self.ui.ft_lineEdittttt_17.setGeometry(480, 325, 40, 20)
        self.ui.ft_lineEdittttt_18.setGeometry(180, 350, 40, 20)
        self.ui.ft_lineEdittttt_19.setGeometry(180, 375, 40, 20)
        self.ui.ft_lineEdittttt_20.setGeometry(180, 425, 40, 20)
        self.ui.ft_lineEdittttt_21.setGeometry(330, 425, 40, 20)
        self.ui.ft_lineEdittttt_22.setGeometry(480, 425, 40, 20)
        self.ui.ft_lineEdittttt_23.setGeometry(180, 450, 40, 20)
        self.ui.ft_lineEdittttt_24.setGeometry(180, 475, 40, 20)
        self.ui.ft_lineEdittttt_25.setGeometry(180, 500, 40, 20)
        self.ui.ft_lineEdittttt_26.setGeometry(330, 500, 40, 20)
        self.ui.ft_lineEdittttt_27.setGeometry(180, 525, 40, 20)
        self.ui.ft_lineEdittttt_28.setGeometry(330, 525, 40, 20)
        self.ui.ft_lineEdittttt_29.setGeometry(480, 525, 40, 20)
        self.ui.ft_lineEdittttt_30.setGeometry(630, 525, 40, 20)
        self.ui.ft_lineEdittttt_31.setGeometry(790, 525, 40, 20)
        self.ui.ft_lineEdittttt_32.setGeometry(180, 550, 40, 20)
        self.ui.ft_lineEdittttt_33.setGeometry(330, 550, 40, 20)
        self.ui.ft_lineEdittttt_34.setGeometry(480, 550, 40, 20)
        self.ui.ft_lineEdittttt_35.setGeometry(180, 575, 40, 20)

        self.ui.ft_checkBoxxxxx_39.setGeometry(685, 300, 150, 80)
        self.ui.ft_pushButtonnn_01.setGeometry(685, 385, 150, 30)
        self.ui.ft_pushButtonnn_02.setGeometry(685, 420, 150, 30)
        self.ui.ft_pushButtonnn_03.setGeometry(685, 455, 150, 30)
