
def dactivated_01(ui, combobox_no):
    """테이블 콤보박스 활성화 이벤트를 처리합니다."""
    if combobox_no == 1:
        comboBox = ui.ss_comboBoxxxx_01
    elif combobox_no == 2:
        comboBox = ui.ss_comboBoxxxx_02
    else:
        comboBox = ui.ss_comboBoxxxx_03

    table_name = comboBox.currentText()
    if table_name:
        from utility.settings.setting_base import UI_NUM
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{table_name}'").set_index('index')
        ui.update_tablewidget.update_tablewidget((UI_NUM['상세기록'], df))


def dactivated_02(ui):
    """설정 이름 콤보박스 활성화 이벤트를 처리합니다."""
    name = ui.sj_set_comBoxx_01.currentText()
    ui.sj_set_liEditt_01.setText(name)


def dactivated_03(ui):
    """주문 종목 콤보박스 활성화 이벤트를 처리합니다."""
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


def mactivated_01(ui):
    """거래소 변경 시 타임프레임 자동 변경"""
    no = int(ui.sj_main_comBox_01.currentText()[-2:])
    ui.sj_main_comBox_02.setCurrentText('1분봉' if no % 2 == 0 else '1초스냅샷')


def mactivated_02(ui):
    """바이낸스 선물 마진타입 경고"""
    from PyQt5.QtWidgets import QMessageBox
    if ui.sj_main_comBox_03.currentText() == '교차':
        ui.sj_main_comBox_03.setCurrentText('격리')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 마진타입은 격리타입만 지원합니다.\n')


def mactivated_03(ui):
    """바이낸스 선물 포지션모드 경고"""
    from PyQt5.QtWidgets import QMessageBox
    if ui.sj_main_comBox_04.currentText() == '양방향':
        ui.sj_main_comBox_04.setCurrentText('단방향')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 포지션모드는 단방향만 지원합니다.\n')
