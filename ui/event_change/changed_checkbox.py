
from PyQt5.QtCore import Qt
from ui.create_widget.set_widget import BounceButton
from PyQt5.QtWidgets import QPushButton, QMessageBox
from ui.etcetera.process_alive import trader_process_alive


def checkbox_changed_01(ui, state):
    """모의투자 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked and trader_process_alive(ui):
        ui.sj_main_cheBox_01.nextCheckState()
        QMessageBox.critical(ui, '오류 알림', '트레이더 실행 중에는 모의모드를 해제할 수 없습니다.\n')


def checkbox_changed_02(ui, state):
    """팩터 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        if ui.dialog_factor.focusWidget() == ui.ft_checkBoxxxxx_01:
            ui.ft_checkBoxxxxx_01.nextCheckState()
            QMessageBox.critical(ui.dialog_factor, '오류 알림', '현재가는 해제할 수 없습니다.\n')


def checkbox_changed_03(ui, state):
    """일괄/분할 로딩 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sj_ilbunback_listtt:
            if widget != ui.focusWidget() and widget.isChecked():
                widget.nextCheckState()


def checkbox_changed_04(ui, state):
    """백테스트로그 기록 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if not ui.sj_back_cheBox_13.isChecked():
            ui.sj_back_cheBox_13.nextCheckState()


def checkbox_changed_05(ui, state):
    """그래프 저장 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state != Qt.Checked:
        if ui.sj_back_cheBox_12.isChecked():
            ui.sj_back_cheBox_12.nextCheckState()


def checkbox_changed_06(ui, state):
    """백테스트 스케줄러 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
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


def checkbox_changed_07(ui, state):
    """일전 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if ui.sj_back_cheBox_16.isChecked():
                ui.sj_back_cheBox_16.nextCheckState()
        else:
            if not ui.sj_back_cheBox_16.isChecked():
                ui.sj_back_cheBox_16.nextCheckState()


def checkbox_changed_08(ui, state):
    """고정 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            if ui.sj_back_cheBox_15.isChecked():
                ui.sj_back_cheBox_15.nextCheckState()
        else:
            if not ui.sj_back_cheBox_15.isChecked():
                ui.sj_back_cheBox_15.nextCheckState()


# noinspection PyUnusedLocal
def checkbox_changed_09(ui, state):
    """차트 코드 초기화 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    ui.ctpg_code = None


# noinspection PyUnresolvedReferences
def sbcheckbox_changed_01(ui, state):
    """매수 주문유형 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if ui.market_gubun in (1, 2, 3, 6, 7):
            for widget in ui.sodb_checkbox_list1:
                if widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        elif ui.market_gubun == 5:
            for i, widget in enumerate(ui.sodb_checkbox_list1):
                if widget == ui.focusWidget() and i == 2:
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        elif ui.market_gubun in (4, 8):
            for i, widget in enumerate(ui.sodb_checkbox_list1):
                if widget == ui.focusWidget() and i > 1:
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        else:
            for i, widget in enumerate(ui.sodb_checkbox_list1):
                if widget == ui.focusWidget() and i in (2, 4, 6):
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()


def sbcheckbox_changed_02(ui, state):
    """분할매수방법 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sodb_checkbox_list2:
            if widget != ui.focusWidget() and widget.isChecked():
                widget.nextCheckState()


# noinspection PyUnresolvedReferences
def sscheckbox_changed_01(ui, state):
    """매도 주문유형 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        if ui.market_gubun in (1, 2, 3, 6, 7):
            for widget in ui.sods_checkbox_list1:
                if widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        elif ui.market_gubun == 5:
            for i, widget in enumerate(ui.sods_checkbox_list1):
                if widget == ui.focusWidget() and widget.text() == '최유리지정가':
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        elif ui.market_gubun in (4, 8):
            for i, widget in enumerate(ui.sods_checkbox_list1):
                if widget == ui.focusWidget() and \
                        ('최유리' in widget.text() or 'IOC' in widget.text() or 'FOK' in widget.text()):
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
        else:
            for i, widget in enumerate(ui.sods_checkbox_list1):
                if widget == ui.focusWidget() and '최유리' in widget.text():
                    widget.nextCheckState()
                    QMessageBox.critical(ui, '오류 알림', f"{ui.market_info['마켓이름']} 거래소에서는 선택할 수 없는 주문유형입니다.\n")
                    break
                elif widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()


def sscheckbox_changed_02(ui, state):
    """분할매도방법 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton) and state == Qt.Checked:
        for widget in ui.sods_checkbox_list2:
            if widget != ui.focusWidget() and widget.isChecked():
                widget.nextCheckState()


def setting_stock_weight_cotrol_changed(ui, state):
    """비중조절 체크박스 변경 이벤트를 처리합니다.
    Args:
        ui: UI 객체
        state: 체크 상태
    """
    if ui.focusWidget().__class__ not in (QPushButton, BounceButton):
        if state == Qt.Checked:
            for widget in ui.ss_bj_check_button_list:
                if widget != ui.focusWidget() and widget.isChecked():
                    widget.nextCheckState()
