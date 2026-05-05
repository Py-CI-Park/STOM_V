
from PyQt5.QtCore import QDate
from ui.create_widget.set_style import style_bc_dk
from PyQt5.QtWidgets import QLineEdit, QMessageBox
from ui.event_click.button_clicked_show_dialog import show_dialog
from ui.event_click.button_clicked_chart import get_indicator_detail


def return_press_01(ui):
    """차트 다이얼로그에서 엔터키 누름 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.dialog_chart.focusWidget() in (ui.ct_lineEdittttt_04, ui.ct_lineEdittttt_05, ui.ct_pushButtonnn_01):
        searchdate = ui.ct_dateEdittttt_01.date().toString('yyyyMMdd')
        linetext   = ui.ct_lineEdittttt_03.text()
        tickcount  = int(linetext) if linetext else 30
        if ui.dialog_chart.focusWidget() == ui.ct_lineEdittttt_04:
            name = ui.ct_lineEdittttt_04.text()
        else:
            name = ui.ct_lineEdittttt_05.text()
        code = ui.dict_code.get(name, name)
        name = ui.dict_name.get(code, code)
        ui.ct_lineEdittttt_04.setText(code)
        ui.ct_lineEdittttt_05.setText(name)
        show_dialog(ui, code, name, tickcount, searchdate, 4)
    elif ui.dialog_chart.focusWidget() == ui.ct_tableWidgett_01:
        row = ui.ct_tableWidgett_01.currentIndex().row()
        item = ui.ct_tableWidgett_01.item(row, 0)
        if item is None:
            return
        name       = item.text()
        code       = ui.dict_code.get(name, name)
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
        data = (code, tickcount, searchdate, starttime, endtime, get_indicator_detail(ui))
        cf1, cf2 = ui.ft_lineEdittttt_36.text(), ui.ft_lineEdittttt_37.text()
        if cf1 and cf2: data += (float(cf1), float(cf2))
        ui.chartQ.put(data)


def return_press_02(ui):
    """비밀번호 다이얼로그에서 엔터키 누름 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if '비밀번호가 변경되었습니다' in ui.pa_labelllllll_01.text():
        ui.dialog_pass.close()
    else:
        if ui.pa_lineEditttt_01.text() == ui.dict_set['프로그램비밀번호']:
            ui.sj_main_liEdit_01.setEchoMode(QLineEdit.Normal)
            ui.sj_accc_liEdit_01.setEchoMode(QLineEdit.Normal)
            ui.sj_accc_liEdit_02.setEchoMode(QLineEdit.Normal)
            ui.sj_tele_liEdit_01.setEchoMode(QLineEdit.Normal)
            ui.sj_tele_liEdit_02.setEchoMode(QLineEdit.Normal)
            ui.sj_etc_liEditt_01.setEchoMode(QLineEdit.Normal)
            ui.sj_etc_pButton_01.setText('계정 텍스트 가리기')
            ui.sj_etc_pButton_01.setStyleSheet(style_bc_dk)
            ui.dialog_pass.close()
        else:
            ui.teleQ.put('경고!! 계정 텍스트 보기 비밀번호 입력 오류가 발생하였습니다.')
            ui.dialog_pass.close()
            QMessageBox.critical(ui, '오류 알림', '프로그램 비밀번호을 잘못입력하였습니다.\n')
