
from PyQt5.QtWidgets import QLabel, QGridLayout
from ui.event_click.button_clicked_stg_module import *
from ui.create_widget.set_style import qfont14, style_bc_dk
from ui.create_widget.set_text_stg_button import dict_stg_name


class SetDialogStrategy:
    """전략 다이얼로그 설정 클래스입니다.
    전략 선택 다이얼로그를 설정합니다.
    """
    def __init__(self, ui_class, wc):
        self.ui = ui_class
        self.wc = wc
        self.set()

    def set(self):
        """전략 다이얼로그를 설정합니다."""
        self.ui.dialog_strategy = self.wc.setDialog('STOM STRATEGY')
        self.ui.dialog_strategy.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_strategy)

        def color_number():
            if idx in (66, 71, 76, 86, 116):
                return 2
            elif idx <= 30:
                return 7
            elif idx <= 45:
                return 8
            elif idx <= 65:
                return 9
            elif idx <= 75:
                return 10
            elif idx <= 85:
                return 11
            elif idx <= 115:
                return 12
            elif idx <= 185:
                return 13
            return 14

        for i, name in enumerate(list(dict_stg_name.values())[:205]):
            idx = i + 1
            color = color_number()
            pushButton = self.wc.setPushbutton(name, parent=self.ui.dialog_strategy, color=color,
                                               click=lambda _, idx_=idx: button_clicked_strategy(self.ui, idx_))
            setattr(self.ui, f'stg_pushButton_{idx:03d}', pushButton)

        self.ui.dialog_strategy.resize(1050, 1365)
        if self.ui.dict_set is not None and self.ui.dict_set['창위치기억'] and self.ui.dict_set['창위치'] is not None:
            try:
                self.ui.dialog_strategy.move(self.ui.dict_set['창위치'][20], self.ui.dict_set['창위치'][21])
            except Exception:
                pass

        self.ui.button_index_list = [x for x in range(116, 206)]
        self.ui.button_index_list = self.ui.button_index_list + [x for x in range(1, 116)]
        grid_layout = QGridLayout(self.ui.dialog_strategy)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(5, 5, 5, 5)
        for i, button_num in enumerate(self.ui.button_index_list):
            button = getattr(self.ui, f'stg_pushButton_{button_num:03d}')
            row = i // 5
            col = i % 5
            grid_layout.addWidget(button, row, col)

        self.ui.dialog_stg_input1 = self.wc.setDialog('사용자 버튼 설정', self.ui.dialog_strategy)
        self.ui.dialog_stg_input1.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_stg_input1)

        self.ui.stginput_labelllll1 = QLabel(' ▣ 버튼의 이름과 전략조건을 입력하십시오.                            삭제하기 버튼을 누르면 아래의 원래 버튼으로 복구됩니다.', self.ui.dialog_stg_input1)
        self.ui.stginput_lineeditt1 = self.wc.setLineedit(self.ui.dialog_stg_input1, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_lineeditt2 = self.wc.setLineedit(self.ui.dialog_stg_input1, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_textEditt1 = self.wc.setTextEdit(self.ui.dialog_stg_input1, filter_=True, font=qfont14)
        self.ui.stginput_pushBtn011 = self.wc.setPushbutton('삭제하기', parent=self.ui.dialog_stg_input1, animated=True, click=lambda: button_clicked_strategy_delete(self.ui))
        self.ui.stginput_pushBtn012 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_stg_input1, animated=True, click=lambda: button_clicked_strategy_save(self.ui))

        self.ui.dialog_stg_input2 = self.wc.setDialog('사용자 버튼 설정', self.ui)
        self.ui.dialog_stg_input2.geometry().center()
        self.ui.dialog_list.append(self.ui.dialog_stg_input2)

        self.ui.stginput_labelllll2 = QLabel(' ▣ 버튼의 이름과 전략조건을 입력하십시오.                            삭제하기 버튼을 누르면 아래의 원래 버튼으로 복구됩니다.', self.ui.dialog_stg_input2)
        self.ui.stginput_lineeditt3 = self.wc.setLineedit(self.ui.dialog_stg_input2, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_lineeditt4 = self.wc.setLineedit(self.ui.dialog_stg_input2, font=qfont14, acenter=True, style=style_bc_dk)
        self.ui.stginput_textEditt2 = self.wc.setTextEdit(self.ui.dialog_stg_input2, filter_=True, font=qfont14)
        self.ui.stginput_pushBtn021 = self.wc.setPushbutton('삭제하기', parent=self.ui.dialog_stg_input2, animated=True, click=lambda: button_clicked_strategy_delete(self.ui))
        self.ui.stginput_pushBtn022 = self.wc.setPushbutton('저장하기', parent=self.ui.dialog_stg_input2, animated=True, click=lambda: button_clicked_strategy_save(self.ui))

        self.ui.dialog_stg_input1.setFixedSize(600, 218)
        self.ui.stginput_labelllll1.setGeometry(5, 7, 590, 30)
        self.ui.stginput_lineeditt1.setGeometry(5, 40, 292, 30)
        self.ui.stginput_lineeditt2.setGeometry(302, 40, 293, 30)
        self.ui.stginput_textEditt1.setGeometry(5, 75, 590, 100)
        self.ui.stginput_pushBtn011.setGeometry(5, 180, 292, 30)
        self.ui.stginput_pushBtn012.setGeometry(302, 180, 293, 30)

        self.ui.dialog_stg_input2.setFixedSize(600, 218)
        self.ui.stginput_labelllll2.setGeometry(5, 7, 590, 30)
        self.ui.stginput_lineeditt3.setGeometry(5, 40, 292, 30)
        self.ui.stginput_lineeditt4.setGeometry(302, 40, 293, 30)
        self.ui.stginput_textEditt2.setGeometry(5, 75, 590, 100)
        self.ui.stginput_pushBtn021.setGeometry(5, 180, 292, 30)
        self.ui.stginput_pushBtn022.setGeometry(302, 180, 293, 30)
