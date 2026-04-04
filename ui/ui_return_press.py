
from PyQt5.QtCore import QDate
from ui.set_style import style_bc_dk
from ui.ui_show_dialog import show_dialog
from utility.static import error_decorator
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from ui.ui_button_clicked_chart import get_indicator_detail


@error_decorator
def return_press_01(ui):
    if ui.dialog_chart.focusWidget() in (ui.ct_lineEdittttt_04, ui.ct_lineEdittttt_05, ui.ct_pushButtonnn_01):
        searchdate = ui.ct_dateEdittttt_01.date().toString('yyyyMMdd')
        linetext   = ui.ct_lineEdittttt_03.text()
        tickcount  = int(linetext) if linetext else 30
        if ui.dialog_chart.focusWidget() == ui.ct_lineEdittttt_04:
            name = ui.ct_lineEdittttt_04.text()
        else:
            name = ui.ct_lineEdittttt_05.text()
        if name in ui.dict_code:
            code = ui.dict_code[name]
        else:
            code = name
            name = ui.dict_name[code] if code in ui.dict_name else code
        ui.ct_lineEdittttt_04.setText(code)
        ui.ct_lineEdittttt_05.setText(name)
        show_dialog(ui, name, tickcount, searchdate, 4)
    elif ui.dialog_chart.focusWidget() == ui.ct_tableWidgett_01:
        row = ui.ct_tableWidgett_01.currentIndex().row()
        item = ui.ct_tableWidgett_01.item(row, 0)
        if item is None:
            return
        name       = item.text()
        coin       = True if 'KRW' in name or 'USDT' in name else False
        code       = ui.dict_code[name] if name in ui.dict_code else name
        searchdate = ui.ct_dateEdittttt_02.date().toString('yyyyMMdd')
        linetext   = ui.ct_lineEdittttt_03.text()
        tickcount  = int(linetext) if linetext else 30
        starttime  = ui.ct_lineEdittttt_01.text()
        endtime    = ui.ct_lineEdittttt_02.text()
        if len(starttime) < 6 or len(endtime) < 6:
            QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
            return
        ui.ct_lineEdittttt_04.setText(code)
        ui.ct_lineEdittttt_05.setText(name)
        ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
        data = (coin, code, tickcount, searchdate, starttime, endtime, get_indicator_detail(ui, code))
        cf1, cf2 = ui.ft_lineEdittttt_36.text(), ui.ft_lineEdittttt_37.text()
        if cf1 and cf2: data += (float(cf1), float(cf2))
        ui.chartQ.put(data)


@error_decorator
def return_press_02(ui):
    if ui.pa_lineEditttt_01.text() == ui.dict_set['계좌비밀번호1'] or \
            (ui.pa_lineEditttt_01.text() == '' and ui.dict_set['계좌비밀번호1'] is None):
        ui.sj_sacc_liEdit_01.setEchoMode(QLineEdit.Normal)
        ui.sj_sacc_liEdit_02.setEchoMode(QLineEdit.Normal)
        ui.sj_sacc_liEdit_03.setEchoMode(QLineEdit.Normal)
        ui.sj_sacc_liEdit_04.setEchoMode(QLineEdit.Normal)
        ui.sj_cacc_liEdit_01.setEchoMode(QLineEdit.Normal)
        ui.sj_cacc_liEdit_02.setEchoMode(QLineEdit.Normal)
        ui.sj_tele_liEdit_01.setEchoMode(QLineEdit.Normal)
        ui.sj_tele_liEdit_02.setEchoMode(QLineEdit.Normal)
        ui.sj_etc_liEditt_01.setEchoMode(QLineEdit.Normal)
        ui.sj_etc_pButton_01.setText('계정 텍스트 가리기')
        ui.sj_etc_pButton_01.setStyleSheet(style_bc_dk)
        ui.dialog_pass.close()
    else:
        ui.teleQ.put('경고!! 계정 텍스트 보기 비밀번호 입력 오류가 발생하였습니다.')
