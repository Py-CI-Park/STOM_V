
from utility.static import error_decorator
from utility.setting_base import columns_jg, columns_jgf, columns_jgcf


@error_decorator
def text_changed_01(ui):
    if ui.dialog_scheduler.focusWidget() not in ui.list_slineEdittttt:
        return
    if ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_slineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_slineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_slineEdittttt):
            if i != gubun:
                widget.setText(text)


@error_decorator
def text_changed_02(ui):
    if ui.dialog_scheduler.focusWidget() not in ui.list_elineEdittttt:
        return
    if ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_elineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_elineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_elineEdittttt):
            if i != gubun:
                widget.setText(text)


@error_decorator
def text_changed_03(ui):
    if ui.dialog_scheduler.focusWidget() not in ui.list_blineEdittttt:
        return
    if ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_blineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_blineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_blineEdittttt):
            if i != gubun:
                widget.setText(text)


@error_decorator
def text_changed_04(ui):
    if ui.dialog_scheduler.focusWidget() not in ui.list_alineEdittttt:
        return
    if ui.sd_scheckBoxxxx_01.isChecked():
        gubun = ui.list_alineEdittttt.index(ui.dialog_scheduler.focusWidget())
        text  = ui.list_alineEdittttt[gubun].text()
        for i, widget in enumerate(ui.list_alineEdittttt):
            combo_text = ui.list_gcomboBoxxxxx[i].currentText()
            if i != gubun and '최적화' not in combo_text and '전진분석' not in combo_text:
                widget.setText(text)


@error_decorator
def text_changed_05(ui):
    name = ui.hj_tableWidgett_01.item(0, 0).text()
    if name:
        try:
            if ui.main_btn == 1:
                row_num = next((row for row in range(ui.sjg_tableWidgettt.rowCount()) if ui.sjg_tableWidgettt.item(row, 0).text() == name), None)
                columns = columns_jg if '키움증권' in ui.dict_set['증권사'] else columns_jgf
                col_num = columns.index('보유수량')
            else:
                row_num = next((row for row in range(ui.cjg_tableWidgettt.rowCount()) if ui.cjg_tableWidgettt.item(row, 0).text() == name), None)
                columns = columns_jg if '업비트' in ui.dict_set['거래소'] else columns_jgcf
                col_num = columns.index('보유수량')
        except:
            order_price = float(ui.od_lineEdittttt_01.text())
            if ui.main_btn == 1:
                if '키움증권' in ui.dict_set['증권사']:
                    order_count = int(ui.dict_set['주식투자금'] * 1_000_000 / order_price)
                else:
                    order_count = int(ui.dict_set['주식투자금'])
            else:
                if 'KRW' in name:
                    order_count = round(ui.dict_set['코인투자금'] * 1_000_000 / order_price, 8)
                else:
                    order_count = round(ui.dict_set['코인투자금'] / order_price, 8)
        else:
            if ui.main_btn == 1:
                order_count = ui.sjg_tableWidgettt.item(row_num, col_num).text()
            else:
                order_count = ui.cjg_tableWidgettt.item(row_num, col_num).text()

        if name not in ui.order_combo_name_list:
            ui.od_comboBoxxxxx_01.addItem(name)
        ui.od_comboBoxxxxx_01.setCurrentText(name)
        ui.od_lineEdittttt_02.setText(str(order_count))
