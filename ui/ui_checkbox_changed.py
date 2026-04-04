
from PyQt5.QtCore import Qt
from ui.set_widget import BounceButton
from utility.static import error_decorator
from PyQt5.QtWidgets import QPushButton, QMessageBox
from ui.ui_process_alive import coin_trader_process_alive


@error_decorator
def checkbox_changed_01(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            id_num = ui.dict_set['증권사'][4:]
            if ui.dict_set[f'아이디{id_num}'] is None:
                ui.sj_main_cheBox_01.nextCheckState()
                QMessageBox.critical(ui, '오류 알림', '계정이 설정되지 않아 리시버를 선택할 수 없습니다.\n계정 설정 후 다시 선택하십시오.\n')
            elif not ui.sj_main_cheBox_02.isChecked():
                ui.sj_main_cheBox_02.nextCheckState()
        else:
            if ui.sj_main_cheBox_02.isChecked():
                ui.sj_main_cheBox_02.nextCheckState()


@error_decorator
def checkbox_changed_02(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            id_num = ui.dict_set['증권사'][4:]
            if ui.dict_set[f'아이디{id_num}'] is None:
                ui.sj_main_cheBox_02.nextCheckState()
                QMessageBox.critical(ui, '오류 알림', '계정이 설정되지 않아 트레이더를 선택할 수 없습니다.\n계정 설정 후 다시 선택하십시오.\n')
            elif not ui.sj_main_cheBox_01.isChecked():
                ui.sj_main_cheBox_01.nextCheckState()
        else:
            if ui.sj_main_cheBox_01.isChecked():
                ui.sj_main_cheBox_01.nextCheckState()


@error_decorator
def checkbox_changed_03(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if not ui.sj_main_cheBox_01.isChecked():
            ui.sj_main_cheBox_01.nextCheckState()
        if not ui.sj_main_cheBox_02.isChecked():
            ui.sj_main_cheBox_02.nextCheckState()


@error_decorator
def checkbox_changed_04(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if not ui.sj_main_cheBox_05.isChecked():
                ui.sj_main_cheBox_05.nextCheckState()
        else:
            if ui.sj_main_cheBox_05.isChecked():
                ui.sj_main_cheBox_05.nextCheckState()


@error_decorator
def checkbox_changed_05(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if not ui.sj_main_cheBox_04.isChecked():
                ui.sj_main_cheBox_04.nextCheckState()
        else:
            if ui.sj_main_cheBox_04.isChecked():
                ui.sj_main_cheBox_04.nextCheckState()


@error_decorator
def checkbox_changed_06(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if not ui.sj_main_cheBox_04.isChecked():
            ui.sj_main_cheBox_04.nextCheckState()
        if not ui.sj_main_cheBox_05.isChecked():
            ui.sj_main_cheBox_05.nextCheckState()


@error_decorator
def checkbox_changed_07(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        buttonReply = QMessageBox.question(
            ui, '경고', '트레이더 실행 중에 모의모드를 해제하면\n바로 실매매로 전환됩니다. 해제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply != QMessageBox.Yes:
            ui.sj_stock_ckBox_01.nextCheckState()


@error_decorator
def checkbox_changed_08(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked and coin_trader_process_alive(ui):
        ui.sj_coin_cheBox_01.nextCheckState()
        QMessageBox.critical(ui, '오류 알림', '트레이더 실행 중에는 모의모드를 해제할 수 없습니다.\n')


@error_decorator
def checkbox_changed_09(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.com_exit_list:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def checkbox_changed_10(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        if ui.dialog_factor.focusWidget() == ui.ft_checkBoxxxxx_01:
            ui.ft_checkBoxxxxx_01.nextCheckState()
            QMessageBox.critical(ui.dialog_factor, '오류 알림', '현재가는 해제할 수 없습니다.\n')


@error_decorator
def checkbox_changed_11(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sj_ilbunback_listtt:
            if widget != ui.focusWidget() and widget.isChecked():
                widget.nextCheckState()


@error_decorator
def checkbox_changed_12(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if not ui.sj_back_cheBox_11.isChecked():
            ui.sj_back_cheBox_11.nextCheckState()


@error_decorator
def checkbox_changed_13(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        if ui.sj_back_cheBox_10.isChecked():
            ui.sj_back_cheBox_10.nextCheckState()


@error_decorator
def checkbox_changed_14(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        if ui.sj_back_cheBox_09.isChecked():
            ui.sj_back_cheBox_09.nextCheckState()


@error_decorator
def checkbox_changed_15(ui, state):
    gubun = ui.list_checkBoxxxxxx.index(ui.dialog_scheduler.focusWidget())
    if state == Qt.Checked:
        for item in ('백테스트',
                     '그리드 최적화', '그리드 검증 최적화', '그리드 교차검증 최적화',
                     '그리드 최적화 테스트', '그리드 검증 최적화 테스트', '그리드 교차검증 최적화 테스트',
                     '그리드 최적화 전진분석', '그리드 검증 최적화 전진분석', '그리드 교차검증 최적화 전진분석',
                     '베이지안 최적화', '베이지안 검증 최적화', '베이지안 교차검증 최적화',
                     '베이지안 최적화 테스트', '베이지안 검증 최적화 테스트', '베이지안 교차검증 최적화 테스트',
                     '베이지안 최적화 전진분석', '베이지안 검증 최적화 전진분석', '베이지안 교차검증 최적화 전진분석',
                     'GA 최적화', '검증 GA 최적화', '교차검증 GA 최적화',
                     '조건 최적화', '검증 조건 최적화', '교차검증 조건 최적화'):
            ui.list_gcomboBoxxxxx[gubun].addItem(item)
    else:
        ui.list_gcomboBoxxxxx[gubun].clear()
        ui.list_bcomboBoxxxxx[gubun].clear()
        ui.list_scomboBoxxxxx[gubun].clear()
        ui.list_vcomboBoxxxxx[gubun].clear()
        ui.list_p1comboBoxxxx[gubun].clear()
        ui.list_p2comboBoxxxx[gubun].clear()
        ui.list_p3comboBoxxxx[gubun].clear()
        ui.list_p4comboBoxxxx[gubun].clear()
        ui.list_tcomboBoxxxxx[gubun].clear()


@error_decorator
def checkbox_changed_16(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if ui.sj_back_cheBox_15.isChecked():
                ui.sj_back_cheBox_15.nextCheckState()
        else:
            if not ui.sj_back_cheBox_15.isChecked():
                ui.sj_back_cheBox_15.nextCheckState()


@error_decorator
def checkbox_changed_17(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if ui.sj_back_cheBox_14.isChecked():
                ui.sj_back_cheBox_14.nextCheckState()
        else:
            if not ui.sj_back_cheBox_14.isChecked():
                ui.sj_back_cheBox_14.nextCheckState()


# noinspection PyUnusedLocal
@error_decorator
def checkbox_changed_18(ui, state):
    ui.ctpg_code = None


@error_decorator
def sbcheckbox_changed_01(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sodb_checkbox_list1:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def sbcheckbox_changed_02(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sodb_checkbox_list2:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def sscheckbox_changed_01(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sods_checkbox_list1:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def sscheckbox_changed_02(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sods_checkbox_list2:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def cbcheckbox_changed_01(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.codb_checkbox_list1:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()
    if ui.dict_set['거래소'] == '업비트':
        if ui.cs_buyy_checkBox_03.isChecked() or ui.cs_buyy_checkBox_04.isChecked():
            if ui.cs_buyy_checkBox_03.isChecked():
                ui.cs_buyy_checkBox_03.nextCheckState()
            else:
                ui.cs_buyy_checkBox_04.nextCheckState()
            QMessageBox.critical(ui, '오류 알림', '업비트는 해당주문유형을 사용할 수 없습니다.\n')
            ui.cs_buyy_checkBox_01.setFocus()
            ui.cs_buyy_checkBox_01.setChecked(True)


@error_decorator
def cbcheckbox_changed_02(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.codb_checkbox_list2:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def cscheckbox_changed_01(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.cods_checkbox_list1:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()
    if ui.dict_set['거래소'] == '업비트':
        if ui.cs_sell_checkBox_03.isChecked() or ui.cs_sell_checkBox_04.isChecked():
            if ui.cs_sell_checkBox_03.isChecked():
                ui.cs_buyy_checkBox_03.nextCheckState()
            else:
                ui.cs_sell_checkBox_04.nextCheckState()
            QMessageBox.critical(ui, '오류 알림', '업비트는 해당주문유형을 사용할 수 없습니다.\n')
            ui.cs_sell_checkBox_01.setFocus()
            ui.cs_sell_checkBox_01.setChecked(True)


@error_decorator
def cscheckbox_changed_02(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.cods_checkbox_list2:
            if widget != ui.focusWidget():
                if widget.isChecked():
                    widget.nextCheckState()


@error_decorator
def setting_stock_weight_cotrol_changed(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            for widget in ui.ss_bj_check_button_list:
                if widget != ui.focusWidget():
                    if widget.isChecked():
                        widget.nextCheckState()


@error_decorator
def setting_coin_weight_cotrol_changed(ui, state):
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            for widget in ui.cs_bj_check_button_list:
                if widget != ui.focusWidget():
                    if widget.isChecked():
                        widget.nextCheckState()
