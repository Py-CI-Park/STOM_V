
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QLabel, QGroupBox, QFrame
from ui.create_widget.set_style import style_ck_bx, style_bc_dk, qfont14
from ui.event_click.button_clicked_formula import formula_button_clicked, formula_activated


class SetDialogFormula:
    """수식 관리자 다이얼로그 설정 클래스입니다.
    사용자 수식을 관리하는 다이얼로그를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """수식 관리자 다이얼로그를 설정합니다."""
        self.ui.dialog_formula = self.wc.setDialog('STOM FORMULA', parent=self.ui.dialog_chart)
        self.ui.dialog_formula.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_formula)

        self.ui.fm_groupBoxxxxx_01 = QGroupBox('', self.ui.dialog_formula)
        self.ui.fm_groupBoxxxxx_02 = QGroupBox('', self.ui.dialog_formula)
        self.ui.fm_groupBoxxxxx_03 = QGroupBox('', self.ui.dialog_formula)

        text = '1. 수식관리자는 전략탭의 매수, 매도 전략코드와 같은 방식으로 수식을 작성할 수 있습니다.\n' \
               '2. 선 형태의 지표, 화살표 형태의 신호, 범위 형태의 지표로 구분되어 있으며 예제를 확인 후 입력하십시오.\n' \
               '3. 선 형태의 지표는 "self.line, self.check"를 지정하는 형태로 입력합니다.\n' \
               '4. 화살표 형태의 신호는 "self.check, self.buy, self.sell"을 지정하는 형태로 입력합니다.\n' \
               '5. 범위 형태의 지표는 "self.check, self.up, self.down"을 지정하는 형태로 입력합니다.'
        self.ui.fm_labellllllll_01 = QLabel(text, self.ui.fm_groupBoxxxxx_01)

        self.ui.fm_lineEdittttt_01 = self.wc.setLineedit(self.ui.fm_groupBoxxxxx_02, aleft=True, style=style_bc_dk)
        self.ui.fm_comboBoxxxxx_00 = self.wc.setCombobox(self.ui.fm_groupBoxxxxx_02, hover=False, activated=lambda: formula_activated(self.ui))
        self.ui.fm_pushButtonnn_01 = self.wc.setPushbutton('불러오기', parent=self.ui.fm_groupBoxxxxx_02, color=4, click=lambda: formula_button_clicked(self.ui))
        self.ui.fm_pushButtonnn_02 = self.wc.setPushbutton('저장하기', parent=self.ui.fm_groupBoxxxxx_02, color=4, click=lambda: formula_button_clicked(self.ui))

        self.ui.fm_checkBoxxxxx_01 = self.wc.setCheckBox('차트 표시 유무 선택', self.ui.fm_groupBoxxxxx_02, style=style_ck_bx)
        self.ui.fm_checkBoxxxxx_02 = self.wc.setCheckBox('전략연산 및 백테 적용', self.ui.fm_groupBoxxxxx_02, style=style_ck_bx)

        items = [
            '현재가', '초당거래대금', '분당거래대금', '초당매도수금액', '분당매도수금액', '당일매도수금액', '최고매도수금액', '최고매도수가격',
            '체결강도', '초당체결수량', '분당체결수량', '등락율', '고저평균대비등락율', '저가대비고가등락율', '호가총잔량', '매도수호가잔량1',
            '매도수5호가잔량합', '당일거래대금', '누적초당매도수수량', '누적분당매도수수량', '등락율각도', '당일거래대금각도',
            'AD', 'ADOSC', 'ADXR', 'APO', 'AROON', 'ATR', 'BBAND', 'CCI',
            'DMI', 'MACD', 'MFI', 'MOM', 'OBV', 'PPO', 'ROC', 'RSI', 'SAR', 'STOCHS', 'STOCHF', 'WILLR'
        ]
        self.ui.fm_comboBoxxxxx_01 = self.wc.setCombobox(self.ui.fm_groupBoxxxxx_02, hover=False, items=items)

        items = ['선:일반', '선:조건', '화살표:일반', '화살표:매매', '범위']
        self.ui.fm_comboBoxxxxx_02 = self.wc.setCombobox(self.ui.fm_groupBoxxxxx_02, hover=False, items=items)

        color_name = QColor(150, 150, 160).name()
        self.ui.fm_frameeeeeeee_01 = QFrame(self.ui.fm_groupBoxxxxx_02)
        self.ui.fm_frameeeeeeee_01.setStyleSheet('QWidget { background-color: %s }' % color_name)
        self.ui.fm_pushButtonnn_03 = self.wc.setPushbutton('색상선택', parent=self.ui.fm_groupBoxxxxx_02, click=lambda: formula_button_clicked(self.ui))
        self.ui.fm_lineEdittttt_02 = self.wc.setLineedit(self.ui.fm_groupBoxxxxx_02, style=style_bc_dk, ltext=color_name)

        items = ['0.5', '1.0', '2.0', '3.0', '4.0', '5.0', '10.0', '20.0', '30.0', '40.0', '50.0']
        self.ui.fm_comboBoxxxxx_03 = self.wc.setCombobox(self.ui.fm_groupBoxxxxx_02, hover=False, items=items, tip='선의 굵기(0.5~5.0) 또는 화살표의 크기(10~50)를 선택하십시오.')

        items = ['1:실선', '2:대시선', '3:점선', '4:대시점선', '5:대시점점선', '6:위쪽화살표(↑)', '7:아래쪽화살표(↓)', '8:우측쪽화살표(→)', '9:좌쪽화살표(←)']
        self.ui.fm_comboBoxxxxx_04 = self.wc.setCombobox(self.ui.fm_groupBoxxxxx_02, hover=False, items=items, tip='선의 종류(1~5) 또는 화살표의 종류(6~9)를 선택하십시오.')

        self.ui.fm_pushButtonnn_04 = self.wc.setPushbutton('삭제하기', parent=self.ui.fm_groupBoxxxxx_02, color=2, click=lambda: formula_button_clicked(self.ui))
        self.ui.fm_pushButtonnn_05 = self.wc.setPushbutton('예제확인', parent=self.ui.fm_groupBoxxxxx_02, color=3, click=lambda: formula_button_clicked(self.ui))

        self.ui.fm_textEdittttt_01 = self.wc.setTextEdit(self.ui.fm_groupBoxxxxx_03, vscroll=True, filter_=True, font=qfont14)

        self.ui.dialog_formula.setMinimumSize(700, 560)
        self.ui.dialog_formula.setMaximumSize(5000, 560)

        self.ui.fm_groupBoxxxxx_01.setGeometry(5, 5, 690, 85)
        self.ui.fm_groupBoxxxxx_02.setGeometry(5, 90, 160, 465)
        self.ui.fm_groupBoxxxxx_03.setGeometry(170, 90, 525, 465)

        self.ui.fm_labellllllll_01.setGeometry(5, 5, 540, 75)

        self.ui.fm_lineEdittttt_01.setGeometry(5, 10, 150, 30)
        self.ui.fm_comboBoxxxxx_00.setGeometry(5, 45, 150, 30)
        self.ui.fm_pushButtonnn_01.setGeometry(5, 80, 150, 30)
        self.ui.fm_pushButtonnn_02.setGeometry(5, 115, 150, 30)

        self.ui.fm_checkBoxxxxx_01.setGeometry(10, 153, 150, 30)
        self.ui.fm_checkBoxxxxx_02.setGeometry(10, 182, 150, 30)
        self.ui.fm_comboBoxxxxx_01.setGeometry(5, 220, 150, 30)
        self.ui.fm_comboBoxxxxx_02.setGeometry(5, 255, 150, 30)
        self.ui.fm_frameeeeeeee_01.setGeometry(5, 290, 72, 30)
        self.ui.fm_pushButtonnn_03.setGeometry(82, 290, 73, 30)
        self.ui.fm_lineEdittttt_02.setGeometry(170, 290, 100, 30)
        self.ui.fm_comboBoxxxxx_03.setGeometry(5, 325, 150, 30)
        self.ui.fm_comboBoxxxxx_04.setGeometry(5, 360, 150, 30)

        self.ui.fm_pushButtonnn_04.setGeometry(5, 395, 150, 30)
        self.ui.fm_pushButtonnn_05.setGeometry(5, 430, 150, 30)

        self.ui.fm_textEdittttt_01.setGeometry(5, 10, 515, 450)

        self.ui.dialog_formula.resizeEvent = self.on_formula_dialog_resize

    def on_formula_dialog_resize(self, event):
        """수식 다이얼로그 크기 조정 이벤트를 처리합니다.
        Args:
            event: 리사이즈 이벤트
        """
        dialog_width = self.ui.dialog_formula.width()
        right_group_width = dialog_width - 175
        self.ui.fm_groupBoxxxxx_01.setGeometry(5, 5, dialog_width - 10, 85)
        self.ui.fm_groupBoxxxxx_03.setGeometry(170, 90, right_group_width, 465)
        self.ui.fm_labellllllll_01.setGeometry(5, 5, dialog_width - 20, 75)
        self.ui.fm_textEdittttt_01.setGeometry(5, 10, right_group_width - 10, 450)
        event.accept()
