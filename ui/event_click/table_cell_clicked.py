
from PyQt5.QtCore import QDate, QUrl
from PyQt5.QtWidgets import QMessageBox
from ui.event_change.changed_text import text_changed_05
from ui.etcetera.process_alive import trader_process_alive
from ui.event_click.button_clicked_chart import get_indicator_detail
from utility.settings.setting_base import columns_jg, columns_jgf, columns_jgcf, ui_num
from utility.static_method.static import comma2int, comma2float, now, str_ymd, now_utc, now_cme, qtest_qwait
from ui.event_click.button_clicked_show_dialog import show_db, show_dialog_graph, show_dialog, show_dialog_web, \
    show_dialog_chart


def cell_clicked_01(ui, row, col):
    """테이블 셀 클릭 시 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    item = ui.focusWidget().item(row, 0)
    if item is None:
        return

    name      = item.text()
    linetext  = ui.ct_lineEdittttt_03.text()
    tickcount = int(linetext) if linetext else 30

    if ui.market_gubun < 4 or ui.market_gubun in (6, 7):
        searchdate = str_ymd()
    elif ui.market_gubun in (4, 8):
        searchdate = str_ymd(now_cme())
    else:
        searchdate = str_ymd(now_utc())

    code = ui.dict_code.get(name, name)
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    show_dialog(ui, code, name, tickcount, searchdate, col)


# noinspection PyUnusedLocal
def cell_clicked_02(ui, row, col):
    """시장가 매도를 실행합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    item = ui.jg_tableWidgettt.item(row, 0)
    if item is None:
        return

    name = item.text()
    columns = columns_jg if ui.market_gubun < 6 else columns_jgf if ui.market_gubun < 9 else columns_jgcf
    oc = comma2int(ui.jg_tableWidgettt.item(row, columns.index('보유수량')).text())
    c = comma2int(ui.jg_tableWidgettt.item(row, columns.index('현재가')).text())
    buttonReply = QMessageBox.question(
        ui, f"{ui.market_info['마켓이름']} 시장가 매도', f'{name} {oc}주를 시장가매도합니다.\n계속하시겠습니까?\n",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if trader_process_alive(ui):
            if ui.market_gubun < 6:
                ui.traderQ.put(('매도', ui.dict_code[name], name, c, oc, now(), True))
            else:
                position = ui.jg_tableWidgettt.item(row, columns.index('포지션')).text()
                position = 'SELL_LONG' if position == 'LONG' else 'BUY_SHORT'
                ui.traderQ.put((position, ui.dict_code[name], name, c, oc, now(), True))


# noinspection PyUnusedLocal
def cell_clicked_03(ui, row, col):
    """날짜별 테이블 셀 클릭 시 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    searchdate = ''
    if ui.focusWidget() == ui.ds_tableWidgetttt:
        searchdate = ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
    elif ui.focusWidget() == ui.ds_tableWidgetttt:
        searchdate = ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
    item = ui.focusWidget().item(row, 1)
    if item is None:
        return

    name      = item.text()
    linetext  = ui.ct_lineEdittttt_03.text()
    tickcount = int(linetext) if linetext else 30
    code      = ui.dict_code.get(name, name)
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
    show_dialog(ui, code, name, tickcount, searchdate, 4)


# noinspection PyUnusedLocal
def cell_clicked_04(ui, row, col):
    """날짜별 거래 그래프를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    item = ui.focusWidget().item(row, 0)
    if item is None:
        return

    date = item.text()
    date = date.replace('.', '')
    table_name = ui.market_info['거래디비']
    df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")

    if len(date) == 6:
        df['구분용체결시간'] = df['index'].str[:6]
        df = df[df['구분용체결시간'] == date]
    elif len(date) == 4:
        df['구분용체결시간'] = df['index'].str[:4]
        df = df[df['구분용체결시간'] == date]

    df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    df.set_index('index', inplace=True)
    show_dialog_graph(ui, df)


# noinspection PyUnusedLocal,PyUnresolvedReferences
def cell_clicked_05(ui, row, col):
    """백테스트 결과 차트를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    tableWidget = None
    if ui.focusWidget() == ui.ss_tableWidget_01 or ui.focusWidget().parentWidget() == ui.ss_tableWidget_01:
        tableWidget = ui.ss_tableWidget_01
    if tableWidget is None:
        return

    item = tableWidget.item(row, 0)
    if item is None:
        return

    name       = item.text()
    searchdate = tableWidget.item(row, 2).text()[:8]
    buytime    = comma2int(tableWidget.item(row, 2).text())

    if len(str(buytime)) > 12 and not ui.dict_set['타임프레임']:
        QMessageBox.critical(ui, '오류 알림', '현재 데이터 형식의 설정은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트에 표시할 수 없습니다.\n')
        return
    elif len(str(buytime)) < 14 and ui.dict_set['타임프레임']:
        QMessageBox.critical(ui, '오류 알림', '현재 데이터 형식의 설정 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트에 표시할 수 없습니다.\n')
        return

    selltime   = comma2int(tableWidget.item(row, 3).text())
    buyprice   = comma2float(tableWidget.item(row, 5).text())
    sellprice  = comma2float(tableWidget.item(row, 6).text())
    detail     = [buytime, buyprice, selltime, sellprice]
    buytimes   = tableWidget.item(row, 13).text()
    code = ui.dict_code.get(name, name)
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
    tickcount = int(ui.svjb_lineEditt_05.text())
    starttime = ui.ct_lineEdittttt_01.text()
    endtime   = ui.ct_lineEdittttt_02.text()

    if len(starttime) < 6 or len(endtime) < 6:
        QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
        return

    show_dialog_chart(ui, False, code, tickcount, searchdate, starttime, endtime, detail, buytimes)


# noinspection PyUnusedLocal
def cell_clicked_06(ui, row, col):
    """차트 테이블 셀 클릭 시 차트를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
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
    if ui.dialog_web.isVisible(): show_dialog_web(ui, False, code)


# noinspection PyUnusedLocal
def cell_clicked_07(ui, row, col):
    """웹페이지를 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    item = ui.dialog_info.focusWidget().item(row, 3)
    if item is None:
        return
    if ui.dialog_web.isVisible():
        ui.webEngineView.load(QUrl(item.text()))


def cell_clicked_08(ui, row, col):
    """데이터베이스 항목을 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    if ui.dialog_db.focusWidget() == ui.db_tableWidgett_01:
        item = ui.db_tableWidgett_01.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        buttonReply = QMessageBox.question(
            ui.dialog_db, '전략 삭제', f"{ui.market_info['마켓이름']} 전략 '{stg_name}'을(를) 삭제합니다.\n계속하시겠습니까?\n",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if col == 0:
                query = f"DELETE FROM {ui.market_info['전략구분']}_buy WHERE `index` = '{stg_name}'"
            elif col == 1:
                query = f"DELETE FROM {ui.market_info['전략구분']}_sell WHERE `index` = '{stg_name}'"
            elif col == 2:
                query = f"DELETE FROM {ui.market_info['전략구분']}_optibuy WHERE `index` = '{stg_name}'"
            else:
                query = f"DELETE FROM {ui.market_info['전략구분']}_optisell WHERE `index` = '{stg_name}'"
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f"DB 명령 실행 알림 - {ui.market_info['마켓이름']} 전략 '{stg_name}' 삭제 완료"))

    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_02:
        item = ui.db_tableWidgett_02.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        buttonReply = QMessageBox.question(
            ui.dialog_db, '범위 또는 조건 삭제', f"{ui.market_info['마켓이름']} 범위 또는 조건 '{stg_name}'을(를) 삭제합니다.\n계속하시겠습니까?\n",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if col == 0:
                query = f"DELETE FROM {ui.market_info['전략구분']}_optivars WHERE `index` = '{stg_name}'"
            elif col == 1:
                query = f"DELETE FROM {ui.market_info['전략구분']}_optigavars WHERE `index` = '{stg_name}'"
            elif col == 2:
                query = f"DELETE FROM {ui.market_info['전략구분']}_buyconds WHERE `index` = '{stg_name}'"
            else:
                query = f"DELETE FROM {ui.market_info['전략구분']}_sellconds WHERE `index` = '{stg_name}'"
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f"DB 명령 실행 알림 - {ui.market_info['마켓이름']} 범위 또는 조건 '{stg_name}' 삭제 완료"))

    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_03:
        item = ui.db_tableWidgett_03.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        buttonReply = QMessageBox.question(
            ui.dialog_db, '스케쥴 삭제', f'스케쥴 "{stg_name}"을(를) 삭제합니다.\n계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            query = f"DELETE FROM schedule WHERE `index` = '{stg_name}'"
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f'DB 명령 실행 알림 - 스케쥴 "{stg_name}" 삭제 완료'))

    qtest_qwait(0.5)
    show_db(ui)


def cell_clicked_09(ui, row, col):
    """호가 테이블 셀 클릭 시 주문 가격을 설정합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    item = ui.hg_tableWidgett_01.item(row, col)
    if item is not None:
        text = item.text()
        if '.' in text:
            order_price = comma2float(text)
        else:
            order_price = comma2int(text)
        ui.od_lineEdittttt_01.setText(str(order_price))
        text_changed_05(ui)


# noinspection PyUnusedLocal
def cell_clicked_10(ui, row, col):
    """전체 거래 그래프를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        row: 행 인덱스
        col: 열 인덱스
    """
    table_name = ui.market_info['거래디비']
    df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name}")
    df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    df.set_index('index', inplace=True)
    show_dialog_graph(ui, df)
