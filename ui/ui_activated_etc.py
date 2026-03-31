
from ui.set_widget import BounceButton
from PyQt5.QtWidgets import QPushButton
from utility.setting_base import ui_num
from utility.static import error_decorator


@error_decorator
def dactivated_01(ui):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        table_name = ui.focusWidget().currentText()
        if ui.focusWidget() in (ui.ss_comboBoxxxx_01, ui.ss_comboBoxxxx_02, ui.ss_comboBoxxxx_03):
            ui_num_text = 'S상세기록'
        else:
            ui_num_text = 'C상세기록'
        if table_name is None:
            return

        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{table_name}'").set_index('index')
        ui.update_tablewidget.update_tablewidget((ui_num[ui_num_text], df))


@error_decorator
def dactivated_02(ui):
    name = ui.sj_set_comBoxx_01.currentText()
    ui.sj_set_liEditt_01.setText(name)


@error_decorator
def dactivated_03(ui):
    name = ui.od_comboBoxxxxx_01.currentText()
    ui.od_comboBoxxxxx_02.clear()
    if 'KRW' in name or '해외선물' in ui.dict_set['증권사']:
        items = ['시장가', '지정가']
    elif 'USDT' in name:
        items = ['시장가', '지정가', '지정가IOC', '지정가FOK']
    else:
        items = [
            '시장가', '지정가', '최유리지정가', '최우선지정가', '지정가IOC', '시장가IOC', '최유리IOC', '지정가FOK',
            '시장가FOK', '최유리FOK'
        ]
    for item in items:
        ui.od_comboBoxxxxx_02.addItem(item)
