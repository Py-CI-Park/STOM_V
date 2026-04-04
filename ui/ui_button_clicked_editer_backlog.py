
from PIL import Image
from PyQt5.QtWidgets import QMessageBox
from utility.static import error_decorator
from utility.setting_base import ui_num, GRAPH_PATH
from ui.ui_backtest_engine import backtest_process_kill


@error_decorator
def ssbutton_clicked_01(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_01.clear()
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    for table in df['name'].to_list()[::-1]:
        if gubun in table and '_bt_' in table:
            ui.ss_comboBoxxxx_01.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_01.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['S상세기록'], df))


@error_decorator
def ssbutton_clicked_02(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_02.clear()
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    for table in df['name'].to_list()[::-1]:
        if gubun in table and ('o_' in table or 'ov_' in table or 'ovc_' in table or 'b_' in table or 'bv_' in table or 'bvc_' in table):
            ui.ss_comboBoxxxx_02.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_02.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['S상세기록'], df))


@error_decorator
def ssbutton_clicked_03(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_03.clear()
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    for table in df['name'].to_list()[::-1]:
        if gubun in table and '_bt_' not in table and ('t_' in table or 'or_' in table or 'orv_' in table or 'orvc_' in table or 'br_' in table or 'brv_' in table or 'brvc_' in table):
            ui.ss_comboBoxxxx_03.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_03.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['S상세기록'], df))


@error_decorator
def ssbutton_clicked_04(ui):
    comboBox = None
    if ui.focusWidget() == ui.ss_pushButtonn_02:
        comboBox = ui.ss_comboBoxxxx_01
    elif ui.focusWidget() == ui.ss_pushButtonn_04:
        comboBox = ui.ss_comboBoxxxx_02
    elif ui.focusWidget() == ui.ss_pushButtonn_06:
        comboBox = ui.ss_comboBoxxxx_03

    if comboBox is None:
        return

    # noinspection PyUnresolvedReferences
    file_name = comboBox.currentText()

    try:
        image1 = Image.open(f"{GRAPH_PATH}/{file_name}.png")
        image2 = Image.open(f"{GRAPH_PATH}/{file_name}_.png")
        image1.show()
        image2.show()
    except:
        QMessageBox.critical(ui, '오류 알림', '저장된 그래프 파일이 존재하지 않습니다.\n')


@error_decorator
def ssbutton_clicked_05(ui):
    if not ui.dialog_comp.isVisible():
        ui.dialog_comp.show()

        df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")

        if len(df) > 0:
            gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
            ui.backdetail_list = [x for x in df['name'].to_list()[::-1] if gubun in x and ('t_' in x or 'v_' in x or 'c_' in x or 'vc_' in x)]
            if ui.backdetail_list:
                ui.backcheckbox_list = []
                count = len(ui.backdetail_list)
                ui.cp_tableWidget_01.setRowCount(count)
                for i, backdetailname in enumerate(ui.backdetail_list):
                    checkBox = ui.wc.setCheckBox(backdetailname, ui)
                    ui.backcheckbox_list.append(checkBox)
                    ui.cp_tableWidget_01.setCellWidget(i, 0, checkBox)
                if count < 40:
                    ui.cp_tableWidget_01.setRowCount(40)
    else:
        ui.dialog_comp.close()


@error_decorator
def ssbutton_clicked_06(ui):
    buttonReply = QMessageBox.question(
        ui, '백테스트 중지', '진행중인 백테스트를 중지합니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        backtest_process_kill(ui, False, False)


@error_decorator
def csbutton_clicked_01(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.cs_comboBoxxxx_01.clear()
    for table in df['name'].to_list()[::-1]:
        if 'coin' in table and '_bt_' in table:
            ui.cs_comboBoxxxx_01.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.cs_comboBoxxxx_01.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['C상세기록'], df))


@error_decorator
def csbutton_clicked_02(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.cs_comboBoxxxx_02.clear()
    for table in df['name'].to_list()[::-1]:
        if 'coin' in table and ('o_' in table or 'ov_' in table or 'ovc_' in table or 'b_' in table or 'bv_' in table or 'bvc_' in table):
            ui.cs_comboBoxxxx_02.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.cs_comboBoxxxx_02.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['C상세기록'], df))


@error_decorator
def csbutton_clicked_03(ui):
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.cs_comboBoxxxx_03.clear()
    for table in df['name'].to_list()[::-1]:
        if 'coin' in table and '_bt_' not in table and ('t_' in table or 'or_' in table or 'orv_' in table or 'orvc_' in table or 'br_' in table or 'brv_' in table or 'brvc_' in table):
            ui.cs_comboBoxxxx_03.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.cs_comboBoxxxx_03.currentText()}'").set_index('index')
    except:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['C상세기록'], df))


@error_decorator
def csbutton_clicked_04(ui):
    comboBox = None
    if ui.focusWidget() == ui.cs_pushButtonn_02:
        comboBox = ui.cs_comboBoxxxx_01
    elif ui.focusWidget() == ui.cs_pushButtonn_04:
        comboBox = ui.cs_comboBoxxxx_02
    elif ui.focusWidget() == ui.cs_pushButtonn_06:
        comboBox = ui.cs_comboBoxxxx_03

    if comboBox is None:
        return

    # noinspection PyUnresolvedReferences
    file_name = comboBox.currentText()

    try:
        image1 = Image.open(f"{GRAPH_PATH}/{file_name}.png")
        image2 = Image.open(f"{GRAPH_PATH}/{file_name}_.png")
        image1.show()
        image2.show()
    except:
        QMessageBox.critical(ui, '오류 알림', '저장된 그래프 파일이 존재하지 않습니다.\n')


@error_decorator
def csbutton_clicked_05(ui):
    if not ui.dialog_comp.isVisible():
        ui.dialog_comp.show()

        df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")

        if len(df) > 0:
            ui.backdetail_list = [x for x in df['name'].to_list()[::-1] if 'coin' in x and ('t_' in x or 'v_' in x or 'c_' in x or 'h_' in x)]

        if ui.backdetail_list:
            ui.backcheckbox_list = []
            count = len(ui.backdetail_list)
            ui.cp_tableWidget_01.setRowCount(count)
            for i, backdetailname in enumerate(ui.backdetail_list):
                checkBox = ui.wc.setCheckBox(backdetailname, ui)
                ui.backcheckbox_list.append(checkBox)
                ui.cp_tableWidget_01.setCellWidget(i, 0, checkBox)
            if count < 40:
                ui.cp_tableWidget_01.setRowCount(40)
    else:
        ui.dialog_comp.close()


@error_decorator
def csbutton_clicked_06(ui):
    buttonReply = QMessageBox.question(
        ui, '백테스트 중지', '진행중인 백테스트를 중지합니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        backtest_process_kill(ui, True, False)
