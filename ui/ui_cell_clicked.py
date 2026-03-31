
from PyQt5.QtCore import QDate, QUrl
from PyQt5.QtWidgets import QMessageBox
from utility.setting_base import columns_jg, columns_jgf, columns_jgcf, ui_num
from utility.static import comma2int, comma2float, now, str_ymd, now_utc, now_cme, qtest_qwait, error_decorator


@error_decorator
def cell_clicked_01(ui, row, col):
    stock = True
    if ui.focusWidget() in (ui.ctd_tableWidgettt, ui.cgj_tableWidgettt, ui.ccj_tableWidgettt):
        stock = False
    if ui.focusWidget().parentWidget() in (ui.ctd_tableWidgettt, ui.cgj_tableWidgettt, ui.ccj_tableWidgettt):
        stock = False
    item = ui.focusWidget().item(row, 0)
    if item is None:
        return
    name       = item.text()
    linetext   = ui.ct_lineEdittttt_03.text()
    tickcount  = int(linetext) if linetext else 30
    searchdate = str_ymd(now_utc()) if not stock else str_ymd() if '키움증권' in ui.dict_set['증권사'] else str_ymd(now_cme())
    code       = ui.dict_code[name] if name in ui.dict_code else name
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    ui.ShowDialog(name, tickcount, searchdate, col)


@error_decorator
def cell_clicked_02(ui, row):
    item = ui.sjg_tableWidgettt.item(row, 0)
    if item is None:
        return
    name = item.text()
    gubun = '주식' if '키움증권' in ui.dict_set['증권사'] else '해선'
    columns = columns_jg if gubun == '주식' else columns_jgf
    oc = comma2int(ui.sjg_tableWidgettt.item(row, columns.index('보유수량')).text())
    c = comma2int(ui.sjg_tableWidgettt.item(row, columns.index('현재가')).text())
    buttonReply = QMessageBox.question(
        ui, f'{gubun} 시장가 매도', f'{name} {oc}주를 시장가매도합니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if gubun == '주식':
            ui.wdzservQ.put(('trade', ('매도', ui.dict_code[name], name, c, oc, now(), True)))
        else:
            p = ui.sjg_tableWidgettt.item(row, columns.index('포지션')).text()
            p = 'SELL_LONG' if p == 'LONG' else 'BUY_SHORT'
            ui.wdzservQ.put(('trade', (p, ui.dict_code[name], name, c, oc, now(), True)))


# noinspection PyUnusedLocal
@error_decorator
def cell_clicked_03(ui, row, col):
    item = ui.cjg_tableWidgettt.item(row, 0)
    if item is None:
        return
    code    = item.text()
    columns = columns_jg if 'KRW' in code else columns_jgcf
    oc      = comma2float(ui.cjg_tableWidgettt.item(row, columns.index('보유수량')).text())
    c       = comma2float(ui.cjg_tableWidgettt.item(row, columns.index('현재가')).text())
    buttonReply = QMessageBox.question(
        ui, '코인 시장가 매도', f'{code} {oc}개를 시장가매도합니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.CoinTraderProcessAlive():
            if 'KRW' in code:
                ui.ctraderQ.put(('매도', code, c, oc, now(), True))
            else:
                p = ui.cjg_tableWidgettt.item(row, columns.index('포지션')).text()
                p = 'SELL_LONG' if p == 'LONG' else 'BUY_SHORT'
                ui.ctraderQ.put((p, code, c, oc, now(), True))


@error_decorator
def cell_clicked_04(ui, row):
    searchdate = ''
    if ui.focusWidget() == ui.sds_tableWidgettt:
        searchdate = ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
    elif ui.focusWidget() == ui.cds_tableWidgettt:
        searchdate = ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
    item = ui.focusWidget().item(row, 1)
    if item is None:
        return
    name      = item.text()
    linetext  = ui.ct_lineEdittttt_03.text()
    tickcount = int(linetext) if linetext else 30
    code      = ui.dict_code[name] if name in ui.dict_code else name
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
    ui.ShowDialog(name, tickcount, searchdate, 4)


@error_decorator
def cell_clicked_05(ui, row):
    gubun = '주식'
    if ui.focusWidget() == ui.cns_tableWidgettt:
        gubun = '코인'
    item = ui.focusWidget().item(row, 0)
    if item is None:
        return
    date = item.text()
    date = date.replace('.', '')
    if gubun == '주식':
        table_name = 's_tradelist' if '키움증권' in ui.dict_set['증권사'] else 'f_tradelist'
    else:
        table_name = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'

    df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")

    if len(date) == 6 and gubun == '코인':
        df['구분용체결시간'] = df['index'].str[:6]
        df = df[df['구분용체결시간'] == date]
    elif len(date) == 4 and gubun == '코인':
        df['구분용체결시간'] = df['index'].str[:4]
        df = df[df['구분용체결시간'] == date]
    df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    df.set_index('index', inplace=True)

    ui.ShowDialogGraph(df)


@error_decorator
def cell_clicked_06(ui, row):
    tableWidget = None
    if ui.focusWidget() == ui.ss_tableWidget_01 or ui.focusWidget().parentWidget() == ui.ss_tableWidget_01:
        tableWidget = ui.ss_tableWidget_01
    elif ui.focusWidget() == ui.cs_tableWidget_01 or ui.focusWidget().parentWidget() == ui.cs_tableWidget_01:
        tableWidget = ui.cs_tableWidget_01
    if tableWidget is None:
        return

    item = tableWidget.item(row, 0)
    if item is None:
        return

    name       = item.text()
    searchdate = tableWidget.item(row, 2).text()[:8]
    buytime    = comma2int(tableWidget.item(row, 2).text())
    selltime   = comma2int(tableWidget.item(row, 3).text())
    buyprice   = comma2float(tableWidget.item(row, 5).text())
    sellprice  = comma2float(tableWidget.item(row, 6).text())
    detail     = [buytime, buyprice, selltime, sellprice]
    buytimes   = tableWidget.item(row, 13).text()

    coin = True if 'KRW' in name or 'USDT' in name else False
    if len(str(buytime)) > 12 and (coin and not ui.dict_set['코인타임프레임'] or not coin and not ui.dict_set['주식타임프레임']):
        QMessageBox.critical(ui, '오류 알림', '현재 전략설정의 데이터타입은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트를 표시할 수 없습니다.\n')
        return
    elif len(str(buytime)) < 14 and (coin and ui.dict_set['코인타임프레임'] or not coin and ui.dict_set['주식타임프레임']):
        QMessageBox.critical(ui, '오류 알림', '현재 전략설정의 데이터타입은 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트를 표시할 수 없습니다.\n')
        return

    code = ui.dict_code[name] if name in ui.dict_code else name
    ui.ct_lineEdittttt_04.setText(code)
    ui.ct_lineEdittttt_05.setText(name)
    ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
    tickcount = int(ui.cvjb_lineEditt_05.text()) if coin else int(ui.svjb_lineEditt_05.text())
    starttime = ui.ct_lineEdittttt_01.text()
    endtime   = ui.ct_lineEdittttt_02.text()
    if len(starttime) < 6 or len(endtime) < 6:
        QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
        return

    ui.ShowDialogChart(False, coin, code, tickcount, searchdate, starttime, endtime, detail, buytimes)


@error_decorator
def cell_clicked_07(ui, row):
    item = ui.ct_tableWidgett_01.item(row, 0)
    if item is None:
        return
    name       = item.text()
    coin       = True if 'KRW' in name or 'USDT' in name else False
    code       = ui.dict_code[name] if name in ui.dict_code else name
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
    data = (coin, code, tickcount, searchdate, starttime, endtime, ui.GetIndicatorDetail(code))
    cf1, cf2 = ui.ft_lineEdittttt_36.text(), ui.ft_lineEdittttt_37.text()
    if cf1 and cf2: data += (float(cf1), float(cf2))
    ui.chartQ.put(data)
    if ui.dialog_web.isVisible(): ui.ShowDialogWeb(False, code)


@error_decorator
def cell_clicked_08(ui, row):
    item = ui.dialog_info.focusWidget().item(row, 3)
    if item is None:
        return
    if ui.dialog_web.isVisible():
        ui.webEngineView.load(QUrl(item.text()))


@error_decorator
def cell_clicked_09(ui, row, col):
    if ui.dialog_db.focusWidget() == ui.db_tableWidgett_01:
        item = ui.db_tableWidgett_01.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        gubun = '주식' if '키움증권' in ui.dict_set['증권사'] else '해선'
        buttonReply = QMessageBox.question(
            ui.dialog_db, '전략 삭제', f'{gubun}전략 "{stg_name}"을(를) 삭제합니다.\n계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
            if col == 0:
                query = f'DELETE FROM {gubun}buy WHERE "index" = "{stg_name}"'
            elif col == 1:
                query = f'DELETE FROM {gubun}sell WHERE "index" = "{stg_name}"'
            elif col == 2:
                query = f'DELETE FROM {gubun}optibuy WHERE "index" = "{stg_name}"'
            else:
                query = f'DELETE FROM {gubun}optisell WHERE "index" = "{stg_name}"'
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f'DB 명령 실행 알림 - 주식전략 "{stg_name}" 삭제 완료'))
    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_02:
        item = ui.db_tableWidgett_02.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        gubun = '주식' if '키움증권' in ui.dict_set['증권사'] else '해선'
        buttonReply = QMessageBox.question(
            ui.dialog_db, '범위 또는 조건 삭제', f'{gubun} 범위 또는 조건 "{stg_name}"을(를) 삭제합니다.\n계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
            if col == 0:
                query = f'DELETE FROM {gubun}optivars WHERE "index" = "{stg_name}"'
            elif col == 1:
                query = f'DELETE FROM {gubun}vars WHERE "index" = "{stg_name}"'
            elif col == 2:
                query = f'DELETE FROM {gubun}buyconds WHERE "index" = "{stg_name}"'
            else:
                query = f'DELETE FROM {gubun}sellconds WHERE "index" = "{stg_name}"'
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f'DB 명령 실행 알림 - 주식 범위 또는 조건 "{stg_name}" 삭제 완료'))
    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_03:
        item = ui.db_tableWidgett_03.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        buttonReply = QMessageBox.question(
            ui.dialog_db, '전략 삭제', f'코인전략 "{stg_name}"을(를) 삭제합니다.\n계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if col == 0:
                query = f'DELETE FROM coinbuy WHERE "index" = "{stg_name}"'
            elif col == 1:
                query = f'DELETE FROM coinsell WHERE "index" = "{stg_name}"'
            elif col == 2:
                query = f'DELETE FROM coinoptibuy WHERE "index" = "{stg_name}"'
            else:
                query = f'DELETE FROM coinoptisell WHERE "index" = "{stg_name}"'
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f'DB 명령 실행 알림 - 코인전략 "{stg_name}" 삭제 완료'))
    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_04:
        item = ui.db_tableWidgett_04.item(row, col)
        if item is None:
            return
        stg_name = item.text()
        buttonReply = QMessageBox.question(
            ui.dialog_db, '범위 또는 조건 삭제', f'코인 범위 또는 조건 "{stg_name}"을(를) 삭제합니다.\n계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if col == 0:
                query = f'DELETE FROM coinoptivars WHERE "index" = "{stg_name}"'
            elif col == 1:
                query = f'DELETE FROM coinvars WHERE "index" = "{stg_name}"'
            elif col == 2:
                query = f'DELETE FROM coinbuyconds WHERE "index" = "{stg_name}"'
            else:
                query = f'DELETE FROM coinsellconds WHERE "index" = "{stg_name}"'
            ui.queryQ.put(('전략디비', query))
            ui.windowQ.put((ui_num['DB관리'], f'DB 명령 실행 알림 - 코인 범위 또는 조건 "{stg_name}" 삭제 완료'))
    elif ui.dialog_db.focusWidget() == ui.db_tableWidgett_05:
        item = ui.db_tableWidgett_05.item(row, col)
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
    ui.ShowDB()


@error_decorator
def cell_clicked_10(ui, row, col):
    item = ui.hg_tableWidgett_01.item(row, col)
    if item is not None:
        text = item.text()
        if '.' in text:
            order_price = comma2float(text)
        else:
            order_price = comma2int(text)
        ui.od_lineEdittttt_01.setText(str(order_price))
        ui.TextChanged_05()


@error_decorator
def cell_clicked_11(ui):
    if ui.focusWidget() == ui.snt_tableWidgettt:
        table_name = 's_tradelist' if '키움증권' in ui.dict_set['증권사'] else 'f_tradelist'
    else:
        table_name = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
    df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name}")
    df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    df.set_index('index', inplace=True)
    ui.ShowDialogGraph(df)
