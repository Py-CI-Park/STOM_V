
import pyqtgraph as pg
from ui.etcetera.etc import chart_screenshot2
from utility.settings.setting_base import indi_base
from utility.static_method.static import str_hms, dt_hms
from PyQt5.QtWidgets import QGroupBox, QLabel, QVBoxLayout
from ui.event_click.table_cell_clicked import cell_clicked_06
from ui.event_keypress.overwrite_return_press import return_press_01
from ui.event_click.button_clicked_chart_count import chart_count_change
from ui.create_widget.set_style import style_bc_dk, style_ck_bx, color_bg_bk
from ui.event_change.changed_checkbox import checkbox_changed_02, checkbox_changed_09
from ui.event_click.button_clicked_etc import hg_button_clicked_01, hg_button_clicked_02
from ui.event_click.button_clicked_chart import indicator_setting_basic, indicator_setting_load, indicator_setting_save
from ui.event_click.button_clicked_show_dialog import show_dialog_formula, show_dialog_factor, chart_size_change, \
    chart_moneytop_list


class SetDialogChart:
    """차트 다이얼로그 설정 클래스입니다.
    차트 다이얼로그와 팩터 설정 다이얼로그를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        """차트 다이얼로그 설정을 초기화합니다.
        Args:
            ui_class: UI 클래스
            wc: 위젯 생성자
        """
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """차트 다이얼로그를 설정합니다."""
        self.ui.dialog_chart = self.wc.setDialog('STOM CHART')
        self.ui.dialog_chart.geometry().center()
        self.ui.ct_groupBoxxxxx_01 = QGroupBox(' ', self.ui.dialog_chart)
        self.ui.ct_groupBoxxxxx_02 = QGroupBox(' ', self.ui.dialog_chart)

        if self.ui.dict_set is not None:
            starttime = str(self.ui.market_info['시작시간']).zfill(6)
            endtime   = str_hms(dt_hms(str(self.ui.dict_set['전략종료시간']))).zfill(6)
        else:
            starttime = '090000'
            endtime   = '093000'

        self.ui.ct_dateEdittttt_01 = self.wc.setDateEdit(self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_labellllllll_01 = QLabel('시작시간', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_01 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, ltext=starttime, style=style_bc_dk)
        self.ui.ct_labellllllll_02 = QLabel('종료시간', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_02 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, ltext=endtime, style=style_bc_dk)
        self.ui.ct_labellllllll_03 = QLabel('평균틱수', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_03 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, ltext='30', style=style_bc_dk)
        self.ui.ct_labellllllll_04 = QLabel('종목코드', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_04 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, enter=lambda: return_press_01(self.ui), style=style_bc_dk)
        self.ui.ct_labellllllll_05 = QLabel('종목명', self.ui.ct_groupBoxxxxx_01)
        self.ui.ct_lineEdittttt_05 = self.wc.setLineedit(self.ui.ct_groupBoxxxxx_01, enter=lambda: return_press_01(self.ui), style=style_bc_dk)
        self.ui.ct_pushButtonnn_01 = self.wc.setPushbutton('검색하기', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: return_press_01(self.ui))
        self.ui.ct_checkBoxxxxx_01 = self.wc.setCheckBox('십자선', self.ui.ct_groupBoxxxxx_01, checked=True, style=style_ck_bx)
        self.ui.ct_checkBoxxxxx_02 = self.wc.setCheckBox('정보창', self.ui.ct_groupBoxxxxx_01, checked=False, style=style_ck_bx)
        text = '1. 시작시간과 종료시간을 설정하면 해당시간의 데이터만 표시됩니다.\n' \
               '2. 평균틱수를 설정하면 구간연산 팩터의 기본값이 변경됩니다.\n' \
               '3. 좌측 날짜선택 후 종목코드 및 종목명으로 차트를 검색할 수 있습니다.\n' \
               '4. 팩터설정 버튼 클릭 후 차트에 표시할 팩터를 선택할 수 있습니다.\n' \
               '5. 확장 버튼 클릭 시 설정한 날짜의 거래대금순위 종목의 리스트가 표시됩니다.\n' \
               '6. 확장 버튼 클릭 후 표시된 테이블에서 종목명 클릭 시 차트가 표시됩니다.\n' \
               '7. 수식관리자 버튼을 클릭하여 사용자 수식을 차트에 표현할 수 있습니다.\n' \
               '8. 차트에서 마우스 드레그로 영역을 선택하면 줌인됩니다.\n' \
               '9. 줌인된 상태에서 마우스 우클릭시 줌아웃됩니다.\n' \
               '10. 줌인된 상태에서 마우스 우클릭으로 드레그하면 좌우로 움직입니다.\n' \
               '11. 호가창이 열린 상태에서 마우스 좌클릭 시 해당 시간의 호가정보가 표시됩니다.\n' \
               '12. 팩터설정 창, 우측 빈칸에 등락율각도, 거래대금각도 계수를 입력하여 다른 계수값 기반 각도를 표시할 수 있습니다.'
        self.ui.ct_pushButtonnn_02 = self.wc.setPushbutton('도움말', parent=self.ui.ct_groupBoxxxxx_01, tip=text)
        self.ui.ct_pushButtonnn_03 = self.wc.setPushbutton('수식관리자', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: show_dialog_formula(self.ui))
        self.ui.ct_pushButtonnn_04 = self.wc.setPushbutton('펙터설정', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: show_dialog_factor(self.ui))
        self.ui.ct_pushButtonnn_05 = self.wc.setPushbutton('CHART I', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: chart_count_change(self.ui))
        self.ui.ct_pushButtonnn_06 = self.wc.setPushbutton('확장', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: chart_size_change(self.ui))
        self.ui.ct_pushButtonnn_07 = self.wc.setPushbutton('', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: hg_button_clicked_01(self.ui, '이전'), shortcut='Alt+left')
        self.ui.ct_pushButtonnn_08 = self.wc.setPushbutton('', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: hg_button_clicked_01(self.ui, '다음'), shortcut='Alt+right')
        self.ui.ct_pushButtonnn_09 = self.wc.setPushbutton('', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: hg_button_clicked_02(self.ui, '매수'), shortcut='Alt+up')
        self.ui.ct_pushButtonnn_10 = self.wc.setPushbutton('', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: hg_button_clicked_02(self.ui, '매도'), shortcut='Alt+down')
        self.ui.ct_pushButtonnn_11 = self.wc.setPushbutton('', parent=self.ui.ct_groupBoxxxxx_01, click=lambda: chart_screenshot2(self.ui), shortcut='Shift+S')

        self.ui.ct_dateEdittttt_02 = self.wc.setDateEdit(self.ui.dialog_chart, changed=lambda: chart_moneytop_list(self.ui))
        self.ui.ct_tableWidgett_01 = self.wc.setTablewidget(self.ui.dialog_chart, ['종목명'], 100, vscroll=True, clicked=lambda row, col: cell_clicked_06(self.ui, row, col))

        self.ui.ctpg = {}
        self.ui.ctpg_cvb = {}
        pg.setConfigOption('background', color_bg_bk)
        self.ui.ctpg_layout = pg.GraphicsLayoutWidget()
        if self.ui.dict_set is not None and not self.ui.dict_set['타임프레임']:
            self.ui.ctpg[0], self.ui.ctpg_cvb[0] = self.wc.setaddPlot(self.ui.ctpg_layout, 0, 0, colspan=2)
            self.ui.ctpg[1], self.ui.ctpg_cvb[1] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 0, colspan=2)
            self.ui.ctpg[2], self.ui.ctpg_cvb[2] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 0)
            self.ui.ctpg[3], self.ui.ctpg_cvb[3] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 0)
            self.ui.ctpg[4], self.ui.ctpg_cvb[4] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 1)
            self.ui.ctpg[5], self.ui.ctpg_cvb[5] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 1)
        else:
            self.ui.ctpg[0], self.ui.ctpg_cvb[0] = self.wc.setaddPlot(self.ui.ctpg_layout, 0, 0, colspan=2)
            self.ui.ctpg[1], self.ui.ctpg_cvb[1] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 0)
            self.ui.ctpg[2], self.ui.ctpg_cvb[2] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 0)
            self.ui.ctpg[3], self.ui.ctpg_cvb[3] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 0)
            self.ui.ctpg[4], self.ui.ctpg_cvb[4] = self.wc.setaddPlot(self.ui.ctpg_layout, 1, 1)
            self.ui.ctpg[5], self.ui.ctpg_cvb[5] = self.wc.setaddPlot(self.ui.ctpg_layout, 2, 1)
            self.ui.ctpg[6], self.ui.ctpg_cvb[6] = self.wc.setaddPlot(self.ui.ctpg_layout, 3, 1)

        qGraphicsGridLayout = self.ui.ctpg_layout.ci.layout
        qGraphicsGridLayout.setRowStretchFactor(0, 3)
        qGraphicsGridLayout.setRowStretchFactor(1, 2)
        qGraphicsGridLayout.setRowStretchFactor(2, 2)
        qGraphicsGridLayout.setRowStretchFactor(3, 2)

        self.ui.ctpg_vboxLayout = QVBoxLayout(self.ui.ct_groupBoxxxxx_02)
        self.ui.ctpg_vboxLayout.setContentsMargins(3, 6, 3, 3)
        self.ui.ctpg_vboxLayout.addWidget(self.ui.ctpg_layout)

        self.ui.dialog_factor = self.wc.setDialog('STOM FACTOR', parent=self.ui.dialog_chart)
        self.ui.dialog_factor.geometry().center()
        self.ui.jp_groupBoxxxxx_01 = QGroupBox(' ', self.ui.dialog_factor)

        if self.ui.dict_set is not None:
            is_min = not self.ui.dict_set['타임프레임']
            checkbox_choice = [int(x) for x in self.ui.dict_set['팩터선택'].split(';')]
        else:
            is_min = False
            checkbox_choice = []

        if len(checkbox_choice) < 43: checkbox_choice = [1] * 43

        # 체크박스 데이터 정의 (텍스트, 변경 핸들러 인덱스)
        checkbox_data = [
            ('현재가', 10),
            ('분당거래대금' if is_min else '초당거래대금', 18),
            ('분당매도수금액' if is_min else '초당매도수금액', 18),
            ('당일매도수금액', 18),
            ('최고매도수금액', 18),
            ('최고매도수가격', 18),
            ('체결강도', 18),
            ('분당체결수량' if is_min else '초당체결수량', 18),
            ('등락율', 18),
            ('고저평균대비등락율', 18),
            ('저가대비고가등락율', 18),
            ('호가총잔량', 18),
            ('매도수호가잔량1', 18),
            ('매도수5호가잔량합', 18),
            ('당일거래대금', 18),
            ('누적분당매도수수량' if is_min else '누적초당매도수수량', 18),
            ('등락율각도', 18),
            ('당일거래대금각도', 18),
            ('AD', 18),
            ('ADOSC', 18),
            ('ADXR', 18),
            ('APO', 18),
            ('AROON', 18),
            ('ATR', 18),
            ('BBAND', 18),
            ('CCI', 18),
            ('DMI', 18),
            ('MACD', 18),
            ('MFI', 18),
            ('MOM', 18),
            ('OBV', 18),
            ('PPO', 18),
            ('ROC', 18),
            ('RSI', 18),
            ('SAR', 18),
            ('STOCHS', 18),
            ('STOCHF', 18),
            ('WILLR', 18),
        ]

        self.ui.factor_checkbox_list = []
        for i, (text, handler_idx) in enumerate(checkbox_data, 1):
            if i == 1:
                checkbox = self.wc.setCheckBox(
                    text, self.ui.jp_groupBoxxxxx_01,
                    checked=True if checkbox_choice[i-1] else False,
                    changed=lambda state: checkbox_changed_02(self.ui, state),
                    style=style_ck_bx
                )
            else:
                checkbox = self.wc.setCheckBox(
                    text, self.ui.jp_groupBoxxxxx_01,
                    checked=True if checkbox_choice[i-1] else False,
                    changed=lambda state: checkbox_changed_09(self.ui, state),
                    style=style_ck_bx
                )
            setattr(self.ui, f'ft_checkBoxxxxx_{i:02d}', checkbox)
            self.ui.factor_checkbox_list.append(checkbox)

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

        # 35개 라인에딧 동적 생성
        self.ui.factor_linedit_list = []
        for i in range(1, 36):
            lineedit = self.wc.setLineedit(
                self.ui.jp_groupBoxxxxx_01,
                ltext=k[i-1] if i <= len(k) else '',
                style=style_bc_dk
            )
            setattr(self.ui, f'ft_lineEdittttt_{i:02d}', lineedit)
            self.ui.factor_linedit_list.append(lineedit)

        # 36, 37번 라인에딧 (빈 값)
        self.ui.ft_lineEdittttt_36 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, style=style_bc_dk)
        self.ui.ft_lineEdittttt_37 = self.wc.setLineedit(self.ui.jp_groupBoxxxxx_01, style=style_bc_dk)

        text = '매수전략으로 설정된\n보조지표값 사용하기\n체크를 해제하면\n좌측 설정값으로 표시됨'
        self.ui.ft_checkBoxxxxx_44 = self.wc.setCheckBox(text, self.ui.jp_groupBoxxxxx_01, checked=False, style=style_ck_bx)
        self.ui.ft_pushButtonnn_01 = self.wc.setPushbutton('보조지표설정 기본값', parent=self.ui.jp_groupBoxxxxx_01, click=lambda: indicator_setting_basic(self.ui))
        self.ui.ft_pushButtonnn_02 = self.wc.setPushbutton('보조지표설정 불러오기', parent=self.ui.jp_groupBoxxxxx_01, click=lambda: indicator_setting_load(self.ui))
        self.ui.ft_pushButtonnn_03 = self.wc.setPushbutton('보조지표설정 저장하기', parent=self.ui.jp_groupBoxxxxx_01, click=lambda: indicator_setting_save(self.ui))

        if self.ui.dict_set is not None:
            self.ui.dialog_chart.setFixedSize(1403, 1370 if not self.ui.dict_set['저해상도'] else 1010)
            if self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
                try:
                    self.ui.dialog_chart.move(self.ui.dict_set['창위치'][2], self.ui.dict_set['창위치'][3])
                except Exception:
                    pass
        else:
            self.ui.dialog_chart.setFixedSize(1403, 1370)

        self.ui.ct_groupBoxxxxx_01.setGeometry(5, -10, 1393, 62)
        # noinspection PyUnresolvedReferences
        self.ui.ct_groupBoxxxxx_02.setGeometry(5, 40, 1393, 1325 if not self.ui.dict_set['저해상도'] else 965)

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
        self.ui.ct_pushButtonnn_02.setGeometry(965, 25, 80, 30)
        self.ui.ct_pushButtonnn_03.setGeometry(1050, 25, 80, 30)
        self.ui.ct_pushButtonnn_04.setGeometry(1135, 25, 80, 30)
        self.ui.ct_pushButtonnn_05.setGeometry(1220, 25, 80, 30)
        self.ui.ct_pushButtonnn_06.setGeometry(1305, 25, 80, 30)
        self.ui.ct_pushButtonnn_07.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_08.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_09.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_10.setGeometry(0, 0, 0, 0)
        self.ui.ct_pushButtonnn_11.setGeometry(0, 0, 0, 0)

        self.ui.ct_dateEdittttt_02.setGeometry(1403, 15, 120, 30)
        if self.ui.dict_set is not None:
            self.ui.ct_tableWidgett_01.setGeometry(1403, 55, 120, 1310 if not self.ui.dict_set['저해상도'] else 950)
        else:
            self.ui.ct_tableWidgett_01.setGeometry(1403, 55, 120, 1310)

        self.ui.dialog_factor.setFixedSize(850, 620)
        self.ui.jp_groupBoxxxxx_01.setGeometry(5, -10, 840, 625)
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

        for i in range(16):
            y = 125 + i * 25
            getattr(self.ui, f'ft_checkBoxxxxx_{i+19}').setGeometry(10, y, 380, 20)

        for i in range(18):
            y = 150 + i * 25 if i < 10 else 175 + i * 25
            getattr(self.ui, f'ft_labellllllll_{i+1:02d}').setGeometry(100, y, 300, 20)

        self.ui.ft_lineEdittttt_01.setGeometry(180, 150, 40, 20)
        self.ui.ft_lineEdittttt_03.setGeometry(180, 175, 40, 20)
        self.ui.ft_lineEdittttt_04.setGeometry(180, 200, 40, 20)
        self.ui.ft_lineEdittttt_07.setGeometry(180, 225, 40, 20)
        self.ui.ft_lineEdittttt_08.setGeometry(180, 250, 40, 20)
        self.ui.ft_lineEdittttt_09.setGeometry(180, 275, 40, 20)
        self.ui.ft_lineEdittttt_13.setGeometry(180, 300, 40, 20)
        self.ui.ft_lineEdittttt_14.setGeometry(180, 325, 40, 20)
        self.ui.ft_lineEdittttt_15.setGeometry(180, 350, 40, 20)
        self.ui.ft_lineEdittttt_18.setGeometry(180, 375, 40, 20)
        self.ui.ft_lineEdittttt_19.setGeometry(180, 425, 40, 20)
        self.ui.ft_lineEdittttt_23.setGeometry(180, 450, 40, 20)
        self.ui.ft_lineEdittttt_24.setGeometry(180, 475, 40, 20)
        self.ui.ft_lineEdittttt_25.setGeometry(180, 500, 40, 20)
        self.ui.ft_lineEdittttt_20.setGeometry(180, 525, 40, 20)
        self.ui.ft_lineEdittttt_27.setGeometry(180, 550, 40, 20)
        self.ui.ft_lineEdittttt_32.setGeometry(180, 575, 40, 20)
        self.ui.ft_lineEdittttt_35.setGeometry(180, 600, 40, 20)

        self.ui.ft_labellllllll_21.setGeometry(250, 150, 300, 20)
        self.ui.ft_labellllllll_23.setGeometry(250, 200, 300, 20)
        self.ui.ft_labellllllll_26.setGeometry(250, 275, 300, 20)
        self.ui.ft_labellllllll_29.setGeometry(250, 350, 300, 20)
        self.ui.ft_labellllllll_32.setGeometry(250, 450, 300, 20)
        self.ui.ft_labellllllll_35.setGeometry(250, 525, 300, 20)
        self.ui.ft_labellllllll_36.setGeometry(250, 550, 300, 20)
        self.ui.ft_labellllllll_37.setGeometry(250, 575, 300, 20)

        self.ui.ft_lineEdittttt_02.setGeometry(330, 150, 40, 20)
        self.ui.ft_lineEdittttt_05.setGeometry(330, 200, 40, 20)
        self.ui.ft_lineEdittttt_10.setGeometry(330, 275, 40, 20)
        self.ui.ft_lineEdittttt_16.setGeometry(330, 350, 40, 20)
        self.ui.ft_lineEdittttt_21.setGeometry(330, 450, 40, 20)
        self.ui.ft_lineEdittttt_26.setGeometry(330, 525, 40, 20)
        self.ui.ft_lineEdittttt_28.setGeometry(330, 550, 40, 20)
        self.ui.ft_lineEdittttt_33.setGeometry(330, 575, 40, 20)

        self.ui.ft_labellllllll_43.setGeometry(400, 200, 300, 20)
        self.ui.ft_labellllllll_46.setGeometry(400, 275, 300, 20)
        self.ui.ft_labellllllll_49.setGeometry(400, 350, 300, 20)
        self.ui.ft_labellllllll_52.setGeometry(400, 450, 300, 20)
        self.ui.ft_labellllllll_56.setGeometry(400, 550, 300, 20)
        self.ui.ft_labellllllll_57.setGeometry(400, 575, 300, 20)

        self.ui.ft_lineEdittttt_06.setGeometry(480, 200, 40, 20)
        self.ui.ft_lineEdittttt_11.setGeometry(480, 275, 40, 20)
        self.ui.ft_lineEdittttt_17.setGeometry(480, 350, 40, 20)
        self.ui.ft_lineEdittttt_22.setGeometry(480, 450, 40, 20)
        self.ui.ft_lineEdittttt_29.setGeometry(480, 550, 40, 20)
        self.ui.ft_lineEdittttt_34.setGeometry(480, 575, 40, 20)

        self.ui.ft_labellllllll_66.setGeometry(550, 275, 300, 20)
        self.ui.ft_labellllllll_76.setGeometry(550, 550, 300, 20)
        self.ui.ft_labellllllll_96.setGeometry(700, 550, 300, 20)

        self.ui.ft_lineEdittttt_12.setGeometry(630, 275, 40, 20)
        self.ui.ft_lineEdittttt_30.setGeometry(630, 550, 40, 20)
        self.ui.ft_lineEdittttt_31.setGeometry(790, 550, 40, 20)

        self.ui.ft_lineEdittttt_36.setGeometry(685, 150, 150, 20)
        self.ui.ft_lineEdittttt_37.setGeometry(685, 175, 150, 20)

        self.ui.ft_checkBoxxxxx_44.setGeometry(685, 325, 150, 80)
        self.ui.ft_pushButtonnn_01.setGeometry(685, 410, 150, 30)
        self.ui.ft_pushButtonnn_02.setGeometry(685, 445, 150, 30)
        self.ui.ft_pushButtonnn_03.setGeometry(685, 480, 150, 30)
