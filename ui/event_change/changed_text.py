
def text_changed_01(ui):
    """시작일 라인에딧 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    if ui.dialog_scheduler.focusWidget() in ui.list_slineEdittttt and ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_slineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_slineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_slineEdittttt):
            if i != gubun:
                widget.setText(text)


def text_changed_02(ui):
    """종료일 라인에딧 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    if ui.dialog_scheduler.focusWidget() in ui.list_elineEdittttt and ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_elineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_elineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_elineEdittttt):
            if i != gubun:
                widget.setText(text)


def text_changed_03(ui):
    """배팅금액 라인에딧 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    if ui.dialog_scheduler.focusWidget() in ui.list_blineEdittttt and ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_blineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_blineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_blineEdittttt):
            if i != gubun:
                widget.setText(text)


def text_changed_04(ui):
    """추가매수 라인에딧 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    if ui.dialog_scheduler.focusWidget() in ui.list_alineEdittttt and ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_alineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_alineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_alineEdittttt):
            combo_text = ui.list_gcomboBoxxxxx[i].currentText()
            if i != gubun and '최적화' not in combo_text and '전진분석' not in combo_text:
                widget.setText(text)


def text_changed_05(ui):
    """주문 종목 테이블 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    name = ui.hj_tableWidgett_01.item(0, 0).text()
    if name:
        try:
            from utility.settings.setting_base import columns_jg, columns_jgf, columns_jgcf
            row_num = next((row for row in range(ui.jg_tableWidgettt.rowCount()) if ui.jg_tableWidgettt.item(row, 0).text() == name), None)
            columns = columns_jg if ui.market_gubun < 6 else columns_jgf if ui.market_gubun < 9 else columns_jgcf
            col_num = columns.index('보유수량')
        except Exception:
            order_price = float(ui.od_lineEdittttt_01.text())
            if ui.market_gubun in (1, 2, 3, 5):
                order_count = int(ui.dict_set['투자금'] * 1_000_000 / order_price)
            else:
                order_count = int(ui.dict_set['투자금'])
        else:
            order_count = ui.jg_tableWidgettt.item(row_num, col_num).text()

        if name not in ui.order_combo_name_list:
            ui.od_comboBoxxxxx_01.addItem(name)
        ui.od_comboBoxxxxx_01.setCurrentText(name)
        ui.od_lineEdittttt_02.setText(str(order_count))
