
def strategy_custom_button_show(ui):
    """전략 커스텀 버튼 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.dialog_strategy.show() if not ui.dialog_strategy.isVisible() else ui.dialog_strategy.close()


def strategy_custom_dialog_show(ui):
    """전략 커스텀 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_text_stg_button import dict_stg_name

    if (ui.stg_btn_number <= 205 and not ui.dialog_stg_input1.isVisible()) or \
            (ui.stg_btn_number > 205 and not ui.dialog_stg_input2.isVisible()):
        if ui.stg_btn_number <= 205:
            ui.stginput_lineeditt1.setText('')
            ui.stginput_textEditt1.clear()
        else:
            ui.stginput_lineeditt3.setText('')
            ui.stginput_textEditt2.clear()

        ori_name = dict_stg_name[ui.stg_btn_number]
        stg_text = ui.dict_stg_btn[ui.stg_btn_number]
        if stg_text[-1] != '\n': stg_text = f'{stg_text}\n'

        if ui.stg_btn_number <= 205:
            stg_name = ui.dialog_strategy.focusWidget().text()
            ui.stginput_lineeditt1.setText(stg_name)
            ui.stginput_lineeditt2.setText(ori_name)
            ui.stginput_textEditt1.insertPlainText(stg_text)
        else:
            stg_name = ui.focusWidget().text()
            ui.stginput_lineeditt3.setText(stg_name)
            ui.stginput_lineeditt4.setText(ori_name)
            ui.stginput_textEditt2.insertPlainText(stg_text)

        ui.dialog_stg_input1.show() if ui.stg_btn_number <= 205 else ui.dialog_stg_input2.show()
    else:
        ui.dialog_stg_input1.close() if ui.stg_btn_number <= 205 else ui.dialog_stg_input2.close()


def button_clicked_strategy(ui, cmd):
    """전략 버튼을 클릭합니다.
    Args:
        ui: UI 클래스 인스턴스
        cmd: 버튼 명령 번호
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QMessageBox, QApplication

    if ui.main_btn != 2:
        QMessageBox.critical(ui.dialog_strategy, '오류 알림', '전략버튼은 전략탭에서만 사용할 수 있습니다.')
        return

    ui.stg_btn_number = cmd

    if cmd <= 205:
        if ui.dialog_strategy.focusWidget().text() == '사용자버튼설정' or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            strategy_custom_dialog_show(ui)
            return
    else:
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            strategy_custom_dialog_show(ui)
            return

    if cmd <= 205:
        textEdit = None
        if ui.focusWidget() == ui.ss_textEditttt_01:
            textEdit = ui.ss_textEditttt_01
        elif ui.focusWidget() == ui.ss_textEditttt_02:
            textEdit = ui.ss_textEditttt_02
        if textEdit is None:
            QMessageBox.critical(ui.dialog_strategy, '오류 알림', '텍스트에디터가 포커싱되지 않았습니다.\n매수 또는 매도 전략입력 덱스트에디터에 마우스 클릭한 후에 재시도하십시오.')
            return
    elif cmd <= 211:
        textEdit = ui.ss_textEditttt_01
    else:
        textEdit = ui.ss_textEditttt_02

    stg_text = ui.dict_stg_btn[cmd]
    if stg_text[-1] != '\n': stg_text = f'{stg_text}\n'
    # noinspection PyUnresolvedReferences
    textEdit.insertPlainText(stg_text)


def button_clicked_strategy_delete(ui):
    """전략 버튼을 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying
    from ui.create_widget.set_text_stg_button import dict_stg_button, dict_stg_name

    if ui.proc_chqs.is_alive():
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
    """전략 버튼을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying

    if ui.stg_btn_number <= 205:
        stg_name = ui.stginput_lineeditt1.text()
        stg_text = ui.stginput_textEditt1.toPlainText()
    else:
        stg_name = ui.stginput_lineeditt3.text()
        stg_text = ui.stginput_textEditt2.toPlainText()

    if not stg_name or not stg_text:
        QMessageBox.critical(ui.dialog_stg_input, '오류 알림', '버튼명이나 전략조건이 입력되지 않았습니다.\n')
        return

    if ui.proc_chqs.is_alive():
        insert_query  = 'INSERT OR REPLACE INTO custombutton VALUES (?, ?, ?)'
        insert_values = (ui.stg_btn_number, stg_name, stg_text)
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        ui.dict_stg_btn[ui.stg_btn_number] = stg_text
        if ui.stg_btn_number <= 205:
            ui.dialog_strategy.focusWidget().setText(stg_name)
            QMessageBox.information(ui.dialog_stg_input1, '저장 완료', random.choice(famous_saying))
        else:
            ui.focusWidget().setText(stg_name)
            QMessageBox.information(ui.dialog_stg_input2, '저장 완료', random.choice(famous_saying))
