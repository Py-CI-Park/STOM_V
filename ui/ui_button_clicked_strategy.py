import random
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.set_text import famous_saying
from ui.set_text_stg_button import dict_stg_button, dict_stg_name


def button_clicked_strategy(ui, cmd):
    if ui.main_btn not in (2, 3):
        QMessageBox.critical(ui.dialog_strategy, '오류 알림', '전략버튼은 전략탭에서만 사용할 수 있습니다.')
        return

    ui.stg_btn_number = cmd

    if cmd <= 205:
        if ui.dialog_strategy.focusWidget().text() == '사용자버튼설정' or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.StrategyCustomDialogShow()
            return
    else:
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            ui.StrategyCustomDialogShow()
            return

    if cmd <= 205:
        textEdit = None
        if ui.focusWidget() == ui.ss_textEditttt_01:
            textEdit = ui.ss_textEditttt_01
        elif ui.focusWidget() == ui.ss_textEditttt_02:
            textEdit = ui.ss_textEditttt_02
        elif ui.focusWidget() == ui.cs_textEditttt_01:
            textEdit = ui.cs_textEditttt_01
        elif ui.focusWidget() == ui.cs_textEditttt_02:
            textEdit = ui.cs_textEditttt_02
        if textEdit is None:
            QMessageBox.critical(ui.dialog_strategy, '오류 알림', '텍스트에디터가 포커싱되지 않았습니다.\n매수 또는 매도 전략입력 덱스트에디터에 마우스 클릭한 후에 재시도하십시오.')
            return
    elif cmd <= 211:
        textEdit = ui.ss_textEditttt_01
    elif cmd <= 219:
        textEdit = ui.ss_textEditttt_02
    elif cmd <= 225:
        textEdit = ui.cs_textEditttt_01
    else:
        textEdit = ui.cs_textEditttt_02

    stg_text = ui.dict_stg_btn[cmd]
    if stg_text[-1] != '\n': stg_text = f'{stg_text}\n'
    textEdit.insertPlainText(stg_text)


def button_clicked_strategy_delete(ui):
    if ui.proc_query.is_alive():
        query = f"DELETE FROM custombutton WHERE `index` = {ui.stg_btn_number}"
        ui.queryQ.put(('전략디비', query))
        stg_name = dict_stg_name[ui.stg_btn_number]
        stg_text = dict_stg_button[ui.stg_btn_number]
        ui.dict_stg_btn[ui.stg_btn_number] = stg_text
        if ui.stg_btn_number <= 205:
            ui.dialog_strategy.focusWidget().setText(stg_name)
            ui.stginput_textEditt1.clear()
            ui.stginput_textEditt1.insertPlainText(stg_text)
            QMessageBox.information(ui.dialog_stg_input1, '삭제 완료', random.choice(famous_saying))
        else:
            ui.focusWidget().setText(stg_name)
            ui.stginput_textEditt2.clear()
            ui.stginput_textEditt2.insertPlainText(stg_text)
            QMessageBox.information(ui.dialog_stg_input2, '삭제 완료', random.choice(famous_saying))


def button_clicked_strategy_save(ui):
    if ui.stg_btn_number <= 205:
        stg_name = ui.stginput_lineeditt1.text()
        stg_text = ui.stginput_textEditt1.toPlainText()
    else:
        stg_name = ui.stginput_lineeditt3.text()
        stg_text = ui.stginput_textEditt2.toPlainText()

    if not stg_name or not stg_text:
        QMessageBox.critical(ui.dialog_stg_input, '오류 알림', '버튼명이나 전략조건이 입력되지 않았습니다.\n')
        return

    if ui.proc_query.is_alive():
        ui.queryQ.put(('전략디비', f"DELETE FROM custombutton WHERE `index` = {ui.stg_btn_number}"))
        df = pd.DataFrame({'버튼명': [stg_name], '전략코드': [stg_text]}, index=[ui.stg_btn_number])
        ui.queryQ.put(('전략디비', df, 'custombutton', 'append'))
        ui.dict_stg_btn[ui.stg_btn_number] = stg_text
        if ui.stg_btn_number <= 205:
            ui.dialog_strategy.focusWidget().setText(stg_name)
            QMessageBox.information(ui.dialog_stg_input1, '저장 완료', random.choice(famous_saying))
        else:
            ui.focusWidget().setText(stg_name)
            QMessageBox.information(ui.dialog_stg_input2, '저장 완료', random.choice(famous_saying))
