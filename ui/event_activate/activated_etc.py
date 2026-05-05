
from PyQt5.QtWidgets import QPushButton
from utility.settings.setting_base import ui_num
from ui.create_widget.set_widget import BounceButton


def dactivated_01(ui):
    """테이블 콤보박스 활성화 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        table_name = ui.focusWidget().currentText()
        if table_name is None:
            return
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{table_name}'").set_index('index')
        ui.update_tablewidget.update_tablewidget((ui_num['상세기록'], df))


def dactivated_02(ui):
    """설정 이름 콤보박스 활성화 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    name = ui.sj_set_comBoxx_01.currentText()
    ui.sj_set_liEditt_01.setText(name)


def dactivated_03(ui):
    """주문 종목 콤보박스 활성화 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    ui.od_comboBoxxxxx_02.clear()
    if ui.market_gubun in (1, 2, 3, 6, 7):
        items = ['시장가', '지정가', '최유리지정가', '지정가IOC', '최유리IOC', '지정가FOK', '최유리FOK']
    elif ui.market_gubun == 5:
        items = ['시장가', '지정가', '지정가IOC', '최유리IOC', '지정가FOK', '최유리FOK']
    elif ui.market_gubun in (4, 8):
        items = ['시장가', '지정가']
    else:
        items = ['시장가', '지정가', '지정가IOC', '지정가FOK']
    for item in items:
        ui.od_comboBoxxxxx_02.addItem(item)
