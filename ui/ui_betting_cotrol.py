import random
import sqlite3
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QPushButton
from ui.set_text import famous_saying
from utility.setting import DB_SETTING


def bjs_button_clicked_01(ui):
    ui.bjs_checkBoxxx_01.setChecked(False)
    ui.bjs_checkBoxxx_02.setChecked(False)
    ui.bjs_checkBoxxx_03.setChecked(False)
    ui.bjs_checkBoxxx_04.setChecked(False)
    ui.bjs_checkBoxxx_05.setChecked(False)
    ui.bjs_checkBoxxx_06.setChecked(False)
    ui.bjs_checkBoxxx_07.setChecked(False)
    con = sqlite3.connect(DB_SETTING)
    df = pd.read_sql('SELECT * FROM stockbuyorder', con)
    con.close()
    bjjj_list = df['주식비중조절'][0]
    bjjj_list = bjjj_list.split(';')
    if bjjj_list[0] == '0':   ui.bjs_checkBoxxx_01.setChecked(True)
    elif bjjj_list[0] == '1': ui.bjs_checkBoxxx_02.setChecked(True)
    elif bjjj_list[0] == '2': ui.bjs_checkBoxxx_03.setChecked(True)
    elif bjjj_list[0] == '3': ui.bjs_checkBoxxx_04.setChecked(True)
    elif bjjj_list[0] == '4': ui.bjs_checkBoxxx_05.setChecked(True)
    elif bjjj_list[0] == '5': ui.bjs_checkBoxxx_06.setChecked(True)
    elif bjjj_list[0] == '6': ui.bjs_checkBoxxx_07.setChecked(True)
    ui.bjs_lineEdittt_01.setText(bjjj_list[1])
    ui.bjs_lineEdittt_02.setText(bjjj_list[2])
    ui.bjs_lineEdittt_03.setText(bjjj_list[3])
    ui.bjs_lineEdittt_04.setText(bjjj_list[4])
    ui.bjs_lineEdittt_05.setText(bjjj_list[5])
    ui.bjs_lineEdittt_06.setText(bjjj_list[6])
    ui.bjs_lineEdittt_07.setText(bjjj_list[7])
    ui.bjs_lineEdittt_08.setText(bjjj_list[8])
    ui.bjs_lineEdittt_09.setText(bjjj_list[9])


def bjs_button_clicked_02(ui):
    bjjj_list = []
    if ui.bjs_checkBoxxx_01.isChecked():   bjjj_list.append('0')
    elif ui.bjs_checkBoxxx_02.isChecked(): bjjj_list.append('1')
    elif ui.bjs_checkBoxxx_03.isChecked(): bjjj_list.append('2')
    elif ui.bjs_checkBoxxx_04.isChecked(): bjjj_list.append('3')
    elif ui.bjs_checkBoxxx_05.isChecked(): bjjj_list.append('4')
    elif ui.bjs_checkBoxxx_06.isChecked(): bjjj_list.append('5')
    elif ui.bjs_checkBoxxx_07.isChecked(): bjjj_list.append('6')
    if not bjjj_list:
        QMessageBox.critical(ui.dialog_bjjs, '오류 알림', '비중조절 기준값을 선택합시오.\n')
        return
    save = True
    if ui.bjs_lineEdittt_01.text() == '': save = False
    if ui.bjs_lineEdittt_02.text() == '': save = False
    if ui.bjs_lineEdittt_03.text() == '': save = False
    if ui.bjs_lineEdittt_04.text() == '': save = False
    if ui.bjs_lineEdittt_05.text() == '': save = False
    if ui.bjs_lineEdittt_06.text() == '': save = False
    if ui.bjs_lineEdittt_07.text() == '': save = False
    if ui.bjs_lineEdittt_08.text() == '': save = False
    if ui.bjs_lineEdittt_09.text() == '': save = False
    if not save:
        QMessageBox.critical(ui.dialog_bjjs, '오류 알림', '구간 또는 비율 값의 일부가 공백 상태입니다.\n')
        return
    bjjj_list.append(ui.bjs_lineEdittt_01.text())
    bjjj_list.append(ui.bjs_lineEdittt_02.text())
    bjjj_list.append(ui.bjs_lineEdittt_03.text())
    bjjj_list.append(ui.bjs_lineEdittt_04.text())
    bjjj_list.append(ui.bjs_lineEdittt_05.text())
    bjjj_list.append(ui.bjs_lineEdittt_06.text())
    bjjj_list.append(ui.bjs_lineEdittt_07.text())
    bjjj_list.append(ui.bjs_lineEdittt_08.text())
    bjjj_list.append(ui.bjs_lineEdittt_09.text())
    bjjj_text = ';'.join(bjjj_list)
    if ui.proc_query.is_alive():
        query = f"UPDATE stockbuyorder SET 주식비중조절 = '{bjjj_text}'"
        ui.queryQ.put(('설정디비', query))
        QMessageBox.information(ui.dialog_bjjs, '저장 완료', random.choice(famous_saying))
    ui.dict_set['주식비중조절'] = [float(x) for x in bjjj_text.split(';')]
    ui.UpdateDictSet()


def bjc_button_clicked_01(ui):
    ui.bjc_checkBoxxx_01.setChecked(False)
    ui.bjc_checkBoxxx_02.setChecked(False)
    ui.bjc_checkBoxxx_03.setChecked(False)
    ui.bjc_checkBoxxx_04.setChecked(False)
    con = sqlite3.connect(DB_SETTING)
    df = pd.read_sql('SELECT * FROM coinbuyorder', con)
    con.close()
    bjjj_list = df['코인비중조절'][0]
    bjjj_list = bjjj_list.split(';')
    if bjjj_list[0] == '0':   ui.bjc_checkBoxxx_01.setChecked(True)
    elif bjjj_list[0] == '1': ui.bjc_checkBoxxx_02.setChecked(True)
    elif bjjj_list[0] == '2': ui.bjc_checkBoxxx_03.setChecked(True)
    elif bjjj_list[0] == '3': ui.bjc_checkBoxxx_04.setChecked(True)
    ui.bjc_lineEdittt_01.setText(bjjj_list[1])
    ui.bjc_lineEdittt_02.setText(bjjj_list[2])
    ui.bjc_lineEdittt_03.setText(bjjj_list[3])
    ui.bjc_lineEdittt_04.setText(bjjj_list[4])
    ui.bjc_lineEdittt_05.setText(bjjj_list[5])
    ui.bjc_lineEdittt_06.setText(bjjj_list[6])
    ui.bjc_lineEdittt_07.setText(bjjj_list[7])
    ui.bjc_lineEdittt_08.setText(bjjj_list[8])
    ui.bjc_lineEdittt_09.setText(bjjj_list[9])


def bjc_button_clicked_02(ui):
    bjjj_list = []
    if ui.bjc_checkBoxxx_01.isChecked():   bjjj_list.append('0')
    elif ui.bjc_checkBoxxx_02.isChecked(): bjjj_list.append('1')
    elif ui.bjc_checkBoxxx_03.isChecked(): bjjj_list.append('2')
    elif ui.bjc_checkBoxxx_04.isChecked(): bjjj_list.append('3')
    if not bjjj_list:
        QMessageBox.critical(ui.dialog_bjjc, '오류 알림', '비중조절 기준값을 선택합시오.\n')
        return
    save = True
    if ui.bjc_lineEdittt_01.text() == '': save = False
    if ui.bjc_lineEdittt_02.text() == '': save = False
    if ui.bjc_lineEdittt_03.text() == '': save = False
    if ui.bjc_lineEdittt_04.text() == '': save = False
    if ui.bjc_lineEdittt_05.text() == '': save = False
    if ui.bjc_lineEdittt_06.text() == '': save = False
    if ui.bjc_lineEdittt_07.text() == '': save = False
    if ui.bjc_lineEdittt_08.text() == '': save = False
    if ui.bjc_lineEdittt_09.text() == '': save = False
    if not save:
        QMessageBox.critical(ui.dialog_bjjc, '오류 알림', '구간 또는 비율 값의 일부가 공백 상태입니다.\n')
        return
    bjjj_list.append(ui.bjc_lineEdittt_01.text())
    bjjj_list.append(ui.bjc_lineEdittt_02.text())
    bjjj_list.append(ui.bjc_lineEdittt_03.text())
    bjjj_list.append(ui.bjc_lineEdittt_04.text())
    bjjj_list.append(ui.bjc_lineEdittt_05.text())
    bjjj_list.append(ui.bjc_lineEdittt_06.text())
    bjjj_list.append(ui.bjc_lineEdittt_07.text())
    bjjj_list.append(ui.bjc_lineEdittt_08.text())
    bjjj_list.append(ui.bjc_lineEdittt_09.text())
    bjjj_text = ';'.join(bjjj_list)
    if ui.proc_query.is_alive():
        query = f"UPDATE coinbuyorder SET 코인비중조절 = '{bjjj_text}'"
        ui.queryQ.put(('설정디비', query))
        QMessageBox.information(ui.dialog_bjjc, '저장 완료', random.choice(famous_saying))
    ui.dict_set['코인비중조절'] = [float(x) for x in bjjj_text.split(';')]
    ui.UpdateDictSet()


def bjs_check_changed_01(ui, state):
    if type(ui.dialog_bjjs.focusWidget()) != QPushButton:
        if state == Qt.Checked:
            for widget in ui.bjs_check_button_list:
                if widget != ui.dialog_bjjs.focusWidget():
                    if widget.isChecked():
                        widget.nextCheckState()


def bjc_check_changed_01(ui, state):
    if type(ui.dialog_bjjc.focusWidget()) != QPushButton:
        if state == Qt.Checked:
            for widget in ui.bjc_check_button_list:
                if widget != ui.dialog_bjjc.focusWidget():
                    if widget.isChecked():
                        widget.nextCheckState()
