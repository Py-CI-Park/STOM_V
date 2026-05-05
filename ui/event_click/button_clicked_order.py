
from PyQt5.QtWidgets import QMessageBox
from utility.static_method.static import comma2float, now
from ui.etcetera.process_alive import trader_process_alive


def odbutton_clicked_01(ui):
    """매수 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('매수', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_02(ui):
    """매도 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('매도', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_03(ui):
    """롱 매수 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('BUY_LONG', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_04(ui):
    """롱 매도 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('SELL_LONG', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_05(ui):
    """숏 매도 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('SELL_SHORT', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_06(ui):
    """숏 매수 주문을 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    ordertype = ui.od_comboBoxxxxx_02.currentText()
    op = ui.od_lineEdittttt_01.text()
    oc = ui.od_lineEdittttt_02.text()
    if '' in (op, oc, name):
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명, 주문가격, 주문수량을 올바르게 입력하십시오.\n')
        return

    if trader_process_alive(ui):
        ui.traderQ.put(('BUY_SHORT', code, name, comma2float(op), comma2float(oc), now(), False, ordertype))


def odbutton_clicked_07(ui):
    """매수 주문을 취소합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    if name == '':
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명을 선택하십시오.\n종목명은 관심종목 테이블의 리스트입니다.\n')
        return

    if trader_process_alive(ui):
        if '선물' in ui.dict_set['거래소']:
            ui.traderQ.put(('BUY_LONG_CANCEL', code, name, 0, 0, now(), False))
            ui.traderQ.put(('SELL_SHORT_CANCEL', code, name, 0, 0, now(), False))
        else:
            ui.traderQ.put(('매수취소', code, name, 0, 0, now(), False))


def odbutton_clicked_08(ui):
    """매도 주문을 취소합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    name = ui.od_comboBoxxxxx_01.currentText()
    code = ui.dict_code.get(name)
    if code is None:
        return

    if name == '':
        QMessageBox.critical(ui.dialog_order, '오류 알림', '종목명을 선택하십시오.\n종목명은 관심종목 테이블의 리스트입니다.\n')
        return

    if trader_process_alive(ui):
        if '선물' in ui.dict_set['거래소']:
            ui.traderQ.put(('SELL_LONG_CANCEL', code, name, 0, 0, now(), False))
            ui.traderQ.put(('BUY_SHORT_CANCEL', code, name, 0, 0, now(), False))
        else:
            ui.traderQ.put(('매도취소', code, name, 0, 0, now(), False))
