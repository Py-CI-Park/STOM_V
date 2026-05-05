
from PIL import Image
from PyQt5.QtWidgets import QMessageBox
from utility.settings.setting_base import ui_num, GRAPH_PATH
from ui.event_click.button_clicked_backtest_engine import backtest_process_kill


def ssbutton_clicked_01(ui):
    """백테스트 기록 테이블 목록을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_01.clear()
    for table in df['name'].to_list()[::-1]:
        if ui.market_info['전략구분'] in table and '_bt_' in table:
            ui.ss_comboBoxxxx_01.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_01.currentText()}'").set_index('index')
    except Exception:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['상세기록'], df))


def ssbutton_clicked_02(ui):
    """최적화 기록 테이블 목록을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_02.clear()
    for table in df['name'].to_list()[::-1]:
        if ui.market_info['전략구분'] in table and \
                ('o_' in table or 'ov_' in table or 'ovc_' in table or 'b_' in table or
                 'bv_' in table or 'bvc_' in table):
            ui.ss_comboBoxxxx_02.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_02.currentText()}'").set_index('index')
    except Exception:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['상세기록'], df))


def ssbutton_clicked_03(ui):
    """전진분석 기록 테이블 목록을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
    ui.ss_comboBoxxxx_03.clear()
    for table in df['name'].to_list()[::-1]:
        if ui.market_info['전략구분'] in table and '_bt_' not in table and \
                ('t_' in table or 'or_' in table or 'orv_' in table or 'orvc_' in table or 'br_' in table or
                 'brv_' in table or 'brvc_' in table):
            ui.ss_comboBoxxxx_03.addItem(table)
    try:
        df = ui.dbreader.read_sql('백테디비', f"SELECT * FROM '{ui.ss_comboBoxxxx_03.currentText()}'").set_index('index')
    except Exception:
        pass
    else:
        ui.update_tablewidget.update_tablewidget((ui_num['상세기록'], df))


def ssbutton_clicked_04(ui):
    """선택된 백테스트 그래프를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
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
    except Exception:
        QMessageBox.critical(ui, '오류 알림', '저장된 그래프 파일이 존재하지 않습니다.\n')


def ssbutton_clicked_05(ui):
    """백테스트 비교 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_comp.isVisible():
        ui.dialog_comp.show()

        df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")

        if len(df) > 0:
            ui.backdetail_list = [x for x in df['name'].to_list()[::-1] if ui.market_info['전략구분'] in x and ('t_' in x or 'v_' in x or 'c_' in x or 'vc_' in x)]
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


def ssbutton_clicked_06(ui):
    """백테스트를 중지합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    buttonReply = QMessageBox.question(
        ui, '백테스트 중지', '진행중인 백테스트를 중지합니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        backtest_process_kill(ui, False, False)
