
def dbbutton_clicked_01(ui):
    """백테DB 지정일자 데이터를 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        date = ui.db_lineEdittttt_16.text()
        if date == '':
            ui.windowQ.put((ui_num['DB관리'], '일자를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 백테DB의 지정일자 데이터를 삭제합니다."))
            ui.queryQ.put(('백테DB지정일자삭제', date))


def dbbutton_clicked_02(ui):
    """일자DB 지정일자 데이터를 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        date = ui.db_lineEdittttt_01.text()
        if date == '':
            ui.windowQ.put((ui_num['DB관리'], '일자를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 일자DB의 지정일자 데이터를 삭제합니다."))
            ui.queryQ.put(('일자DB지정일자삭제', date))


def dbbutton_clicked_03(ui):
    """일자DB 지정시간 이후 데이터를 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        time = ui.db_lineEdittttt_02.text()
        if time == '':
            ui.windowQ.put((ui_num['DB관리'], '시간를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 일자DB의 지정시간이후 데이터를 삭제합니다."))
            ui.queryQ.put(('일자DB지정시간이후삭제', time))


def dbbutton_clicked_04(ui):
    """당일 데이터 지정시간 이후 데이터를 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        time = ui.db_lineEdittttt_03.text()
        if time == '':
            ui.windowQ.put((ui_num['DB관리'], '시간를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 당일 데이터의 지정시간이후 데이터를 삭제합니다."))
            ui.queryQ.put(('당일데이터지정시간이후삭제', time))


def dbbutton_clicked_05(ui):
    """당일DB 체결시간을 조정합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        date = ui.db_lineEdittttt_04.text()
        if date == '':
            ui.windowQ.put((ui_num['DB관리'], '일자를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 당일DB의 체결시간을 조정합니다."))
            ui.queryQ.put(('체결시간조정', date))


def dbbutton_clicked_06(ui):
    """일자DB로 백테DB를 생성합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        date1 = ui.db_lineEdittttt_05.text()
        date2 = ui.db_lineEdittttt_06.text()
        if '' in (date1, date2):
            ui.windowQ.put((ui_num['DB관리'], '일자를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 일자DB로 백테DB를 생성합니다."))
            ui.queryQ.put(('백테DB생성', date1, date2))


def dbbutton_clicked_07(ui):
    """일자DB를 백테DB로 추가합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        date1 = ui.db_lineEdittttt_07.text()
        date2 = ui.db_lineEdittttt_08.text()
        if '' in (date1, date2):
            ui.windowQ.put((ui_num['DB관리'], '일자를 입력하십시오.'))
            return
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 일자DB를 백테DB로 추가합니다."))
            ui.queryQ.put(('백테디비추가1', date1, date2))


def dbbutton_clicked_08(ui):
    """당일DB를 백테DB로 추가합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 당일DB를 백테DB로 추가합니다."))
            ui.queryQ.put(('백테디비추가2', ''))


def dbbutton_clicked_09(ui):
    """당일DB를 일자DB로 분리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import ui_num

    if not ui.database_control:
        if ui.proc_chqs.is_alive():
            ui.database_control = True
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 당일DB를 일자DB로 분리합니다."))
            ui.queryQ.put(('일자DB분리', ''))


def dbbutton_clicked_10(ui):
    """거래기록을 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import ui_num

    buttonReply = QMessageBox.warning(
        ui.dialog_db, f"{ui.market_info['마켓이름']} 거래기록 삭제", "체결목록, 잔고목록, 거래목록, 일별목록이 모두 삭제됩니다.\n계속하시겠습니까?\n",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.proc_chqs.is_alive():
            ui.queryQ.put(('거래디비', f"DELETE FROM {ui.market_info['전략구분']}_jangolist"))
            ui.queryQ.put(('거래디비', f"DELETE FROM {ui.market_info['전략구분']}_tradelist"))
            ui.queryQ.put(('거래디비', f"DELETE FROM {ui.market_info['전략구분']}_chegeollist"))
            ui.queryQ.put(('거래디비', f"DELETE FROM {ui.market_info['전략구분']}_totaltradelist"))
            ui.queryQ.put(('거래디비', 'VACUUM'))
            ui.windowQ.put((ui_num['DB관리'], f"{ui.market_info['마켓이름']} 거래기록 삭제 완료"))
