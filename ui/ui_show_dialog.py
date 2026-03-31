
import os
import sqlite3
import pandas as pd
from PyQt5.QtCore import QUrl, Qt
from multiprocessing import Process
from PyQt5.QtWidgets import QVBoxLayout, QTableWidgetItem, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from ui.ui_dialog_animation import DialogAnimator
from utility.kimp_upbit_binance import Kimp
from utility.static import str_hms, dt_hms, error_decorator
from utility.setting_base import columns_hc, DB_COIN_TICK_BACK, DB_STOCK_TICK_BACK, DB_PATH, DB_COIN_MIN_BACK, \
    DB_STOCK_MIN_BACK, DB_FUTURE_MIN_BACK, DB_FUTURE_TICK_BACK
from ui.set_style import style_bc_bt, style_bc_bb


class QuietPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, p_str, p_int, p_str_1):
        pass


@error_decorator
def show_dialog_graph(ui, df):
    if not ui.dialog_graph.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_graph, duration=250)
        ui.dialog_graph.show()

    df['이익금액'] = df['수익금'].clip(lower=0)
    df['손실금액'] = df['수익금'].clip(upper=0)
    df['수익금합계'] = df['수익금'].cumsum()
    df['수익금합계020'] = df['수익금합계'].rolling(window=20).mean()
    df['수익금합계060'] = df['수익금합계'].rolling(window=60).mean()
    df['수익금합계120'] = df['수익금합계'].rolling(window=120).mean()
    df['수익금합계240'] = df['수익금합계'].rolling(window=240).mean()
    df['수익금합계480'] = df['수익금합계'].rolling(window=480).mean()

    from matplotlib import pyplot as plt, font_manager
    font_name = 'C:/Windows/Fonts/malgun.ttf'
    font_family = font_manager.FontProperties(fname=font_name).get_name()
    plt.rcParams['font.family'] = font_family
    plt.rcParams['axes.unicode_minus'] = False

    plt.figure('누적수익금', figsize=(12, 10))
    plt.bar(df.index, df['이익금액'], label='이익금액', color='r')
    plt.bar(df.index, df['손실금액'], label='손실금액', color='b')
    plt.plot(df.index, df['수익금합계480'], linewidth=0.5, label='수익금합계480', color='k')
    plt.plot(df.index, df['수익금합계240'], linewidth=0.5, label='수익금합계240', color='gray')
    plt.plot(df.index, df['수익금합계120'], linewidth=0.5, label='수익금합계120', color='b')
    plt.plot(df.index, df['수익금합계060'], linewidth=0.5, label='수익금합계60', color='g')
    plt.plot(df.index, df['수익금합계020'], linewidth=0.5, label='수익금합계20', color='r')
    plt.plot(df.index, df['수익금합계'], linewidth=2, label='수익금합계', color='orange')
    plt.legend(loc='best')
    plt.tight_layout()
    plt.grid()
    plt.draw()


@error_decorator
def show_dialog(ui, code_or_name, tickcount, searchdate, col):
    coin = False
    if code_or_name in ui.dict_code:
        code = ui.dict_code[code_or_name]
    elif code_or_name in ui.dict_code.values():
        code = code_or_name
    else:
        code = code_or_name
        coin = True

    if col == 0:
        if not coin:
            ui.ShowDialogWeb(True, code)
        else:
            ui.ShowDialogHoga(True, coin, code)
    elif col == 1:
        if not coin:
            ui.ShowDialogWeb(False, code)
        ui.ShowDialogHoga(True, coin, code)
    elif col < 4 or ui.focusWidget() in (ui.sgj_tableWidgettt, ui.scj_tableWidgettt, ui.cgj_tableWidgettt, ui.ccj_tableWidgettt):
        if not coin:
            ui.ShowDialogWeb(False, code)
        ui.ShowDialogHoga(False, coin, code)
        ui.ShowDialogChart(True, coin, code)
    else:
        starttime = ui.ct_lineEdittttt_01.text()
        endtime   = ui.ct_lineEdittttt_02.text()
        if len(starttime) < 6 or len(endtime) < 6:
            QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
            return
        if not coin:
            ui.ShowDialogWeb(False, code)
        ui.ShowDialogHoga(False, coin, code)
        ui.ShowDialogChart(False, coin, code, tickcount, searchdate, starttime, endtime)


@error_decorator
def show_dialog_web(ui, _show, code):
    if ui.webEngineView is None:
        webengineview_set(ui)
    if _show and not ui.dialog_web.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_web, duration=250)
        ui.dialog_web.show()
    if _show and not ui.dialog_info.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_info, duration=250)
        ui.dialog_info.show()
    if ui.dialog_web.isVisible() and ui.dialog_info.isVisible():
        ui.webEngineView.load(QUrl(f'https://finance.naver.com/item/main.naver?code={code}'))
        ui.webcQ.put(('기업정보', code))


@error_decorator
def webengineview_set(ui):
    ui.webEngineView = QWebEngineView()
    p = QuietPage(ui.webEngineView)
    ui.webEngineView.setPage(p)
    web_layout = QVBoxLayout(ui.dialog_web)
    web_layout.setContentsMargins(0, 0, 0, 0)
    web_layout.addWidget(ui.webEngineView)


@error_decorator
def show_dialog_hoga(ui, _show, coin, code):
    if _show and not ui.dialog_hoga.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_hoga, duration=250)
        ui.dialog_hoga.show()
    if ui.dialog_hoga.isVisible():
        ui.PutHogaCode(coin, code)
    if ui.dialog_order.isVisible():
        name = ui.dict_name[code] if code in ui.dict_name else code
        if name not in ui.order_combo_name_list:
            ui.od_comboBoxxxxx_01.addItem(name)
        ui.od_comboBoxxxxx_01.setCurrentText(name)


@error_decorator
def show_dialog_chart(ui, real, coin, code, tickcount, searchdate, starttime, endtime, detail, buytimes):
    if not ui.dialog_chart.isVisible():
        dialog_chart_show(ui)
    if ui.dialog_chart.isVisible() and ui.proc_chqs.is_alive():
        if real:
            ui.ChartClear()
            if coin:
                if ui.CoinStrategyProcessAlive(): ui.cstgQ.put(('차트종목코드', code))
                if not ui.dict_set['코인타임프레임'] and ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('차트종목코드', code))
            else:
                ui.wdzservQ.put(('strategy', ('차트종목코드', code)))
                if not ui.dict_set['주식타임프레임']: ui.wdzservQ.put(('agent', ('차트종목코드', code)))
        else:
            ui.ChartClear()
            cf1, cf2 = ui.ft_lineEdittttt_36.text(), ui.ft_lineEdittttt_37.text()
            data = (coin, code, tickcount, searchdate, starttime, endtime, ui.GetIndicatorDetail(code))
            if detail is not None: data += (detail, buytimes)
            if cf1 and cf2:        data += (float(cf1), float(cf2))
            ui.chartQ.put(data)


@error_decorator
def dialog_chart_show(ui):
    ui.ct_pushButtonnn_05.setText('CHART III')
    ui.ChartCountChange()

    is_min = (ui.dict_set['주식에이전트'] and not ui.dict_set['주식타임프레임']) or \
             (ui.dict_set['코인리시버'] and not ui.dict_set['코인타임프레임'])
    if is_min:
        if ui.ft_checkBoxxxxx_02.text() != '분당거래대금': ui.ft_checkBoxxxxx_02.setText('분당거래대금')
        if ui.ft_checkBoxxxxx_03.text() != '분당매도수금액': ui.ft_checkBoxxxxx_03.setText('분당매도수금액')
        if ui.ft_checkBoxxxxx_08.text() != '분당체결수량': ui.ft_checkBoxxxxx_08.setText('분당체결수량')
        if ui.ft_checkBoxxxxx_16.text() != '누적분당매도수수량': ui.ft_checkBoxxxxx_16.setText('누적분당매도수수량')
    else:
        if ui.ft_checkBoxxxxx_02.text() != '초당거래대금': ui.ft_checkBoxxxxx_02.setText('초당거래대금')
        if ui.ft_checkBoxxxxx_03.text() != '초당매도수금액': ui.ft_checkBoxxxxx_03.setText('초당매도수금액')
        if ui.ft_checkBoxxxxx_08.text() != '초당체결수량': ui.ft_checkBoxxxxx_08.setText('초당체결수량')
        if ui.ft_checkBoxxxxx_16.text() != '누적초당매도수수량': ui.ft_checkBoxxxxx_16.setText('누적초당매도수수량')

    if ui.dict_set['주식에이전트']:
        if '키움증권' in ui.dict_set['증권사']:
            starttime = '090000'
        else:
            starttime = '093000'
        endtime = str_hms(dt_hms(str(ui.dict_set['주식전략종료시간']))).zfill(6)
    else:
        starttime = '000000'
        endtime = str_hms(dt_hms(str(ui.dict_set['코인전략종료시간']))).zfill(6)

    ui.ct_lineEdittttt_01.setText(starttime)
    ui.ct_lineEdittttt_02.setText(endtime)
    DialogAnimator.setup_dialog_animation(ui.dialog_chart, duration=300)
    ui.dialog_chart.show()


@error_decorator
def show_qsize(ui):
    if not ui.showQsize:
        ui.qs_pushButton.setStyleSheet(style_bc_bt)
        ui.showQsize = True
    else:
        ui.qs_pushButton.setStyleSheet(style_bc_bb)
        ui.showQsize = False


@error_decorator
def show_dialog_formula(ui):
    if not ui.dialog_formula.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_formula, duration=250)
        ui.dialog_formula.show()
    else:
        ui.dialog_formula.close()


@error_decorator
def show_dialog_factor(ui):
    if not ui.dialog_factor.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_factor, duration=250)
        ui.dialog_factor.show()
    else:
        ui.dialog_factor.close()


@error_decorator
def show_chart(ui):
    if not ui.dialog_chart.isVisible():
        dialog_chart_show(ui)
    else:
        ui.dialog_chart.close()


@error_decorator
def show_hoga(ui):
    if not ui.dialog_hoga.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_hoga, duration=250)
        ui.dialog_hoga.setFixedSize(572, 355)
        ui.hj_tableWidgett_01.setGeometry(5, 5, 562, 42)
        ui.hj_tableWidgett_01.setColumnWidth(0, 140)
        ui.hj_tableWidgett_01.setColumnWidth(1, 140)
        ui.hj_tableWidgett_01.setColumnWidth(2, 140)
        ui.hj_tableWidgett_01.setColumnWidth(3, 140)
        ui.hj_tableWidgett_01.setColumnWidth(4, 140)
        ui.hj_tableWidgett_01.setColumnWidth(5, 140)
        ui.hj_tableWidgett_01.setColumnWidth(6, 140)
        ui.hj_tableWidgett_01.setColumnWidth(7, 140)
        ui.hc_tableWidgett_01.setHorizontalHeaderLabels(columns_hc)
        ui.hc_tableWidgett_02.setVisible(False)
        ui.hg_tableWidgett_01.setGeometry(285, 52, 282, 297)
        ui.dialog_hoga.show()
    else:
        ui.dialog_hoga.close()


@error_decorator
def show_giup(ui):
    if ui.webEngineView is None:
        webengineview_set(ui)
    if not ui.dialog_web.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_web, duration=250)
        ui.dialog_web.show()
        ui.webEngineView.load(QUrl('https://finance.naver.com/sise/'))
    else:
        ui.dialog_web.close()
    if not ui.dialog_info.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_info, duration=250)
        ui.dialog_info.show()
    else:
        ui.dialog_info.close()


@error_decorator
def show_treemap(ui):
    if not ui.dialog_tree.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_tree, duration=250)
        ui.dialog_tree.show()
        ui.webcQ.put(('트리맵', ''))
    else:
        ui.dialog_tree.close()


@error_decorator
def show_jisu(ui):
    if not ui.dialog_jisu.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_jisu, duration=250)
        ui.dialog_jisu.show()
    else:
        ui.dialog_jisu.close()


@error_decorator
def show_db(ui):
    if not ui.dialog_db.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_db, duration=250)
        ui.dialog_db.show()

    ui.db_tableWidgett_01.clearContents()
    ui.db_tableWidgett_02.clearContents()
    ui.db_tableWidgett_03.clearContents()
    ui.db_tableWidgett_04.clearContents()
    ui.db_tableWidgett_05.clearContents()

    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    stock_stg_list = [f'{gubun}buy', f'{gubun}sell', f'{gubun}optibuy', f'{gubun}optisell']
    maxlow = 0
    for i, stock_stg in enumerate(stock_stg_list):
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {stock_stg}')
        stg_names = df['index'].to_list()
        stg_names.sort()
        if len(df) > maxlow:
            maxlow = len(df)
            ui.db_tableWidgett_01.setRowCount(maxlow)
        for j, stg_name in enumerate(stg_names):
            item = QTableWidgetItem(stg_name)
            item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
            ui.db_tableWidgett_01.setItem(j, i, item)
    if maxlow < 8:
        ui.db_tableWidgett_01.setRowCount(8)

    stock_stg_list = [f'{gubun}optivars', f'{gubun}vars', f'{gubun}buyconds', f'{gubun}sellconds']
    maxlow = 0
    for i, stock_stg in enumerate(stock_stg_list):
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {stock_stg}')
        stg_names = df['index'].to_list()
        stg_names.sort()
        if len(df) > maxlow:
            maxlow = len(df)
            ui.db_tableWidgett_02.setRowCount(maxlow)
        for j, stg_name in enumerate(stg_names):
            item = QTableWidgetItem(stg_name)
            item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
            ui.db_tableWidgett_02.setItem(j, i, item)
    if maxlow < 8:
        ui.db_tableWidgett_02.setRowCount(8)

    maxlow = 0
    coin_stg_list = ['coinbuy', 'coinsell', 'coinoptibuy', 'coinoptisell']
    for i, coin_stg in enumerate(coin_stg_list):
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {coin_stg}')
        stg_names = df['index'].to_list()
        stg_names.sort()
        if len(df) > maxlow:
            maxlow = len(df)
            ui.db_tableWidgett_03.setRowCount(maxlow)
        for j, stg_name in enumerate(stg_names):
            item = QTableWidgetItem(stg_name)
            item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
            ui.db_tableWidgett_03.setItem(j, i, item)
    if maxlow < 8:
        ui.db_tableWidgett_03.setRowCount(8)

    stock_stg_list = ['coinoptivars', 'coinvars', 'coinbuyconds', 'coinsellconds']
    maxlow = 0
    for i, stock_stg in enumerate(stock_stg_list):
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {stock_stg}')
        stg_names = df['index'].to_list()
        stg_names.sort()
        if len(df) > maxlow:
            maxlow = len(df)
            ui.db_tableWidgett_04.setRowCount(maxlow)
        for j, stg_name in enumerate(stg_names):
            item = QTableWidgetItem(stg_name)
            item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
            ui.db_tableWidgett_04.setItem(j, i, item)
    if maxlow < 8:
        ui.db_tableWidgett_04.setRowCount(8)

    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM schedule')
    stg_names = df['index'].to_list()
    stg_names.sort()
    if len(df) > maxlow:
        maxlow = len(df)
        ui.db_tableWidgett_05.setRowCount(maxlow)
    for j, stg_name in enumerate(stg_names):
        item = QTableWidgetItem(stg_name)
        item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
        ui.db_tableWidgett_05.setItem(j, 0, item)
    if maxlow < 8:
        ui.db_tableWidgett_05.setRowCount(8)


@error_decorator
def show_backscheduler(ui):
    if not ui.dialog_scheduler.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_scheduler, duration=250)
        ui.dialog_scheduler.show()
    else:
        ui.dialog_scheduler.close()


@error_decorator
def show_kimp(ui):
    if not ui.dialog_kimp.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_kimp, duration=250)
        ui.dialog_kimp.show()
        if not ui.CoinKimpProcessAlive():
            ui.proc_coin_kimp = Process(target=Kimp, args=(ui.qlist,))
            ui.proc_coin_kimp.start()
    else:
        ui.dialog_kimp.close()
        if ui.CoinKimpProcessAlive():
            ui.proc_coin_kimp.kill()


@error_decorator
def show_order(ui):
    if not ui.dialog_order.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_order, duration=250)
        ui.dialog_order.show()

        tableWidget = None
        if ui.main_btn == 1:
            tableWidget = ui.sgj_tableWidgettt
        elif ui.main_btn == 2:
            tableWidget = ui.cgj_tableWidgettt

        if tableWidget is not None:
            ui.od_comboBoxxxxx_01.clear()
            for row in range(100):
                item = tableWidget.item(row, 0)
                if item is not None:
                    name = item.text()
                    ui.order_combo_name_list.append(name)
                    ui.od_comboBoxxxxx_01.addItem(name)
                else:
                    break
    else:
        ui.dialog_order.close()


@error_decorator
def put_hoga_code(ui, coin, code):
    if coin:
        ui.wdzservQ.put(('agent', ('호가종목코드', '000000')))
        if ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('호가종목코드', code))
    else:
        if ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('호가종목코드', '000000'))
        ui.wdzservQ.put(('agent', ('호가종목코드', code)))


@error_decorator
def chart_moneytop_list(ui):
    searchdate = ui.ct_dateEdittttt_02.date().toString('yyyyMMdd')
    starttime  = ui.ct_lineEdittttt_01.text()
    endtime    = ui.ct_lineEdittttt_02.text()
    coin = True if ui.ct_pushButtonnn_06.text() == '코인' else False

    is_min = False
    if coin:
        db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db' if ui.dict_set['코인타임프레임'] else f'{DB_PATH}/coin_min_{searchdate}.db'
        db_name2 = DB_COIN_TICK_BACK if ui.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
        if ui.dict_set['코인타임프레임']:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                    f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
        else:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                    f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"
            is_min = True
    else:
        if '키움증권' in ui.dict_set['증권사']:
            db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db' if ui.dict_set['주식타임프레임'] else f'{DB_PATH}/stock_min_{searchdate}.db'
            db_name2 = DB_STOCK_TICK_BACK if ui.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
        else:
            db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db' if ui.dict_set['주식타임프레임'] else f'{DB_PATH}/future_min_{searchdate}.db'
            db_name2 = DB_FUTURE_TICK_BACK if ui.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK

        if ui.dict_set['주식타임프레임']:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                    f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
        else:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                    f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"
            is_min = True

    df = None
    try:
        if os.path.isfile(db_name1):
            con = sqlite3.connect(db_name1)
            df = pd.read_sql(query, con)
            con.close()
        elif os.path.isfile(db_name2):
            con = sqlite3.connect(db_name2)
            df = pd.read_sql(query, con)
            con.close()
    except:
        pass

    if df is None or len(df) == 0:
        ui.ct_tableWidgett_01.clearContents()
        return

    if is_min:
        # noinspection PyUnresolvedReferences
        table_list = list(set(';'.join(df['거래대금순위'].to_list()).split(';')))
    else:
        # noinspection PyUnresolvedReferences
        table_list = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
    name_list = [ui.dict_name[code] if code in ui.dict_name else code for code in table_list] if not coin else table_list
    name_list.sort()

    ui.ct_tableWidgett_01.setRowCount(len(name_list))
    for i, name in enumerate(name_list):
        item = QTableWidgetItem(name)
        item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignLeft))
        ui.ct_tableWidgett_01.setItem(i, 0, item)
    if len(name_list) < 100:
        ui.ct_tableWidgett_01.setRowCount(100)


@error_decorator
def chart_size_change(ui):
    if ui.ct_pushButtonnn_06.text() == '확장':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1528
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2213
        else:
            width = 2898
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('주식')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bb)
        ui.ChartMoneyTopList()
    elif ui.ct_pushButtonnn_06.text() == '주식':
        ui.ct_pushButtonnn_06.setText('코인')
        ui.ChartMoneyTopList()
    elif ui.ct_pushButtonnn_06.text() == '코인':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1403
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2088
        else:
            width = 2773
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)
