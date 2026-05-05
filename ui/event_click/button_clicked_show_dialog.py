
import os
import sqlite3
import pandas as pd
from PyQt5.QtCore import QUrl, Qt
from multiprocessing import Process
from ui.etcetera.etc import chart_clear
from utility.settings.setting_base import columns_hc
from utility.static_method.static import str_hms, dt_hms
from ui.create_widget.dialog_animation import DialogAnimator
from utility.sub_process_and_thread.kimp_upbit_binance import Kimp
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage
from ui.event_click.button_clicked_chart import get_indicator_detail
from PyQt5.QtWidgets import QVBoxLayout, QTableWidgetItem, QMessageBox
from ui.event_click.button_clicked_chart_count import chart_count_change
from ui.create_widget.set_style import style_bc_bt, style_bc_bb, style_bc_st
from ui.etcetera.process_alive import coinkimp_process_alive, strategy_process_alive, receiver_process_alive


class QuietPage(QWebEnginePage):
    """자바스크립트 콘솔 메시지를 무시하는 웹엔진 페이지 클래스입니다."""
    def javaScriptConsoleMessage(self, level, p_str, p_int, p_str_1):
        pass


def show_dialog_graph(ui, df):
    """그래프 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        df: 데이터프레임
    """
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


def show_dialog(ui, code, name, tickcount, searchdate, col):
    """다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        code: 코드
        name: 이름
        tickcount: 틱 카운트
        searchdate: 검색 일자
        col: 컬럼 인덱스
    """
    if col == 0:
        if ui.market_gubun < 4:
            show_dialog_web(ui, True, code)
        else:
            show_dialog_hoga(ui, True, code)
    elif col == 1:
        if ui.market_gubun < 4:
            show_dialog_web(ui, False, code)
        show_dialog_hoga(ui, True, code)
    elif col < 4 or ui.focusWidget() in (ui.gj_tableWidgettt, ui.cj_tableWidgettt):
        if ui.market_gubun < 4:
            show_dialog_web(ui, False, code)
        show_dialog_hoga(ui, False, code)
        show_dialog_chart(ui, True, code)
    else:
        starttime = ui.ct_lineEdittttt_01.text()
        endtime   = ui.ct_lineEdittttt_02.text()
        if len(starttime) < 6 or len(endtime) < 6:
            QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
            return
        if ui.market_gubun < 4:
            show_dialog_web(ui, False, code)
        show_dialog_hoga(ui, False, code)
        if ui.market_gubun in (6, 7):
            show_dialog_chart(ui, False, name, tickcount, searchdate, starttime, endtime)
        else:
            show_dialog_chart(ui, False, code, tickcount, searchdate, starttime, endtime)


def show_dialog_web(ui, _show, code):
    """웹 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        _show: 표시 여부
        code: 코드
    """
    if ui.webEngineView is None:
        webengineview_set(ui)
    if _show and not ui.dialog_web.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_web, duration=250)
        ui.dialog_web.show()
    if _show and not ui.dialog_info.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_info, duration=250)
        ui.dialog_info.show()
    if ui.dialog_web.isVisible() and ui.dialog_info.isVisible():
        # noinspection PyUnresolvedReferences
        ui.webEngineView.load(QUrl(f'https://finance.naver.com/item/main.naver?code={code}'))
        ui.webcQ.put(('기업정보', code))


def webengineview_set(ui):
    """웹엔진 뷰를 설정합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.webEngineView = QWebEngineView()
    p = QuietPage(ui.webEngineView)
    ui.webEngineView.setPage(p)
    web_layout = QVBoxLayout(ui.dialog_web)
    web_layout.setContentsMargins(0, 0, 0, 0)
    web_layout.addWidget(ui.webEngineView)


def show_dialog_hoga(ui, _show, code):
    """호가 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        _show: 표시 여부
        code: 코드
    """
    if _show and not ui.dialog_hoga.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_hoga, duration=250)
        ui.dialog_hoga.show()
    if ui.dialog_hoga.isVisible():
        put_hoga_code(ui, code)
    if ui.dialog_order.isVisible():
        name = ui.dict_name.get(code, code)
        if name not in ui.order_combo_name_list:
            ui.od_comboBoxxxxx_01.addItem(name)
        ui.od_comboBoxxxxx_01.setCurrentText(name)


def show_dialog_chart(ui, real, code, tickcount=None, searchdate=None, starttime=None, endtime=None,
                      detail=None, buytimes=None):
    """차트 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
        real: 실시간 여부
        code: 코드
        tickcount: 틱 카운트
        searchdate: 검색 일자
        starttime: 시작 시간
        endtime: 종료 시간
        detail: 상세 정보
        buytimes: 매수 시간
    """
    if not ui.dialog_chart.isVisible():
        dialog_chart_show(ui)
    if ui.proc_chqs.is_alive():
        if real:
            chart_clear(ui)
            if receiver_process_alive(ui):
                ui.receivQ.put(('차트종목코드', code))
            if strategy_process_alive(ui):
                if ui.market_gubun in (1, 4):
                    for q in ui.stgQs:
                        q.put(('차트종목코드', code))
                else:
                    ui.stgQs[0].put(('차트종목코드', code))
        else:
            chart_clear(ui)
            cf1, cf2 = ui.ft_lineEdittttt_36.text(), ui.ft_lineEdittttt_37.text()
            data = (code, tickcount, searchdate, starttime, endtime, get_indicator_detail(ui))
            if detail is not None: data += (detail, buytimes)
            if cf1 and cf2:        data += (float(cf1), float(cf2))
            ui.chartQ.put(data)


def dialog_chart_show(ui):
    """차트 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.ct_pushButtonnn_05.setText('CHART III')
    chart_count_change(ui)

    is_min = not ui.dict_set['타임프레임']
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

    starttime = str(ui.market_info['시작시간']).zfill(6)
    endtime = str_hms(dt_hms(str(ui.dict_set['전략종료시간']))).zfill(6)

    ui.ct_lineEdittttt_01.setText(starttime)
    ui.ct_lineEdittttt_02.setText(endtime)
    DialogAnimator.setup_dialog_animation(ui.dialog_chart, duration=300)
    ui.dialog_chart.show()


def show_qsize(ui):
    """큐 사이즈 표시를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.showQsize:
        ui.qs_pushButton.setStyleSheet(style_bc_st)
        ui.showQsize = True
    else:
        ui.qs_pushButton.setStyleSheet(style_bc_bb)
        ui.showQsize = False


def show_dialog_formula(ui):
    """수식 관리자 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_formula.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_formula, duration=250)
        ui.dialog_formula.show()
    else:
        ui.dialog_formula.close()


def show_dialog_factor(ui):
    """팩터 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_factor.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_factor, duration=250)
        ui.dialog_factor.show()
    else:
        ui.dialog_factor.close()


def show_chart(ui):
    """차트 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_chart.isVisible():
        dialog_chart_show(ui)
    else:
        ui.dialog_chart.close()


def show_hoga(ui):
    """호가 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
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


def show_giup(ui):
    """기업정보 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.webEngineView is None:
        webengineview_set(ui)
    if not ui.dialog_web.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_web, duration=250)
        ui.dialog_web.show()
        # noinspection PyUnresolvedReferences
        ui.webEngineView.load(QUrl('https://finance.naver.com/sise/'))
    else:
        ui.dialog_web.close()
    if not ui.dialog_info.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_info, duration=250)
        ui.dialog_info.show()
    else:
        ui.dialog_info.close()


def show_treemap(ui):
    """트리맵 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_tree.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_tree, duration=250)
        ui.dialog_tree.show()
        ui.webcQ.put(('트리맵', ''))
    else:
        ui.dialog_tree.close()


def show_db(ui):
    """데이터베이스 관리 다이얼로그를 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_db.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_db, duration=250)
        ui.dialog_db.show()

    ui.db_tableWidgett_01.clearContents()
    ui.db_tableWidgett_02.clearContents()
    ui.db_tableWidgett_03.clearContents()

    stock_stg_list = [f"{ui.market_info['전략구분']}_buy", f"{ui.market_info['전략구분']}_sell",
                      f"{ui.market_info['전략구분']}_optibuy", f"{ui.market_info['전략구분']}_optisell"]
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

    stock_stg_list = [f"{ui.market_info['전략구분']}_optivars", f"{ui.market_info['전략구분']}_optigavars",
                      f"{ui.market_info['전략구분']}_buyconds", f"{ui.market_info['전략구분']}_sellconds"]
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

    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM schedule')
    stg_names = df['index'].to_list()
    stg_names.sort()
    if len(df) > maxlow:
        maxlow = len(df)
        ui.db_tableWidgett_03.setRowCount(maxlow)
    for j, stg_name in enumerate(stg_names):
        item = QTableWidgetItem(stg_name)
        item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignCenter))
        ui.db_tableWidgett_03.setItem(j, 0, item)
    if maxlow < 8:
        ui.db_tableWidgett_03.setRowCount(8)


def show_backscheduler(ui):
    """백테스트 스케줄러 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_scheduler.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_scheduler, duration=250)
        ui.dialog_scheduler.show()
    else:
        ui.dialog_scheduler.close()


def show_kimp(ui):
    """김프 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_kimp.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_kimp, duration=250)
        ui.dialog_kimp.show()
        if not coinkimp_process_alive(ui):
            ui.proc_coin_kimp = Process(target=Kimp, args=(ui.qlist,))
            ui.proc_coin_kimp.start()
    else:
        ui.dialog_kimp.close()
        if coinkimp_process_alive(ui):
            ui.proc_coin_kimp.kill()


def show_order(ui):
    """주문 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if not ui.dialog_order.isVisible():
        DialogAnimator.setup_dialog_animation(ui.dialog_order, duration=250)
        ui.dialog_order.show()

        tableWidget = None
        if ui.main_btn == 1:
            tableWidget = ui.gj_tableWidgettt

        if tableWidget is not None:
            ui.od_comboBoxxxxx_01.clear()
            for row in range(100):
                # noinspection PyUnresolvedReferences
                item = tableWidget.item(row, 0)
                if item is not None:
                    name = item.text()
                    ui.order_combo_name_list.append(name)
                    ui.od_comboBoxxxxx_01.addItem(name)
                else:
                    break
    else:
        ui.dialog_order.close()


def put_hoga_code(ui, code):
    """호가 코드를 전송합니다.
    Args:
        ui: UI 클래스 인스턴스
        code: 코드
    """
    if receiver_process_alive(ui):
        ui.receivQ.put(('호가종목코드', code))


def chart_moneytop_list(ui):
    """차트 거래대금 순위 목록을 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    searchdate = ui.ct_dateEdittttt_02.date().toString('yyyyMMdd')
    starttime  = ui.ct_lineEdittttt_01.text()
    endtime    = ui.ct_lineEdittttt_02.text()

    is_tick  = ui.dict_set['타임프레임']
    db_name1 = f"{ui.market_info['일자디비경로'][is_tick]}_{searchdate}.db"
    db_name2 = ui.market_info['백테디비'][is_tick]

    if is_tick:
        query = f"SELECT * FROM moneytop WHERE " \
                f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
    else:
        query = f"SELECT * FROM moneytop WHERE " \
                f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"

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
    except Exception:
        pass

    if df is None or len(df) == 0:
        ui.ct_tableWidgett_01.clearContents()
        return

    table_list = list(set(';'.join(df['거래대금순위'].to_list()).split(';')))
    name_list = [ui.dict_name.get(code, code) for code in table_list]
    name_list.sort()

    ui.ct_tableWidgett_01.setRowCount(len(name_list))
    for i, name in enumerate(name_list):
        item = QTableWidgetItem(name)
        item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignLeft))
        ui.ct_tableWidgett_01.setItem(i, 0, item)
    if len(name_list) < 100:
        ui.ct_tableWidgett_01.setRowCount(100)


def chart_size_change(ui):
    """차트 크기를 변경합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.ct_pushButtonnn_06.text() == '확장':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1528
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2213
        else:
            width = 2898
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('축소')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bb)
        chart_moneytop_list(ui)
    elif ui.ct_pushButtonnn_06.text() == '축소':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1403
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2088
        else:
            width = 2773
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)
