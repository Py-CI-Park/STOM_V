import psutil
import random
import sqlite3
import pandas as pd
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtMultimedia import QMediaPlayer
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.set_text import famous_saying
from utility.setting import DB_TRADELIST
from utility.setting import columns_dt, columns_dd, ui_num
from utility.static import thread_decorator, qtest_qwait, strf_time


def update_image(ui, data):
    ui.image_label1.clear()
    qpix = QPixmap()
    qpix.loadFromData(data[1])
    qpix = qpix.scaled(QSize(335, 105), Qt.IgnoreAspectRatio)
    ui.image_label1.setPixmap(qpix)
    ui.image_label2.clear()
    qpix = QPixmap()
    qpix.loadFromData(data[2])
    qpix = qpix.scaled(QSize(335, 602), Qt.IgnoreAspectRatio)
    ui.image_label2.setPixmap(qpix)


def update_sqsize(ui, data):
    ui.srqsize, ui.stqsize, ui.ssqsize = data


@thread_decorator
def update_cpuper(ui):
    ui.cpu_per = int(psutil.cpu_percent(interval=1))


def auto_back_schedule(ui, gubun):
    if gubun == 1:
        ui.auto_mode = True
        if ui.dict_set['주식알림소리'] or ui.dict_set['코인알림소리']:
            ui.soundQ.put('예약된 백테스트 스케쥴러를 시작합니다.')
        if not ui.dialog_backengine.isVisible():
            ui.BackTestengineShow(ui.dict_set['백테스케쥴구분'])
        qtest_qwait(2)
        ui.BacktestEngineKill()
        qtest_qwait(3)
        ui.StartBacktestEngine(ui.dict_set['백테스케쥴구분'])
    elif gubun == 2:
        if not ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.show()
        qtest_qwait(2)
        ui.sdButtonClicked_04()
        qtest_qwait(2)
        ui.sd_pushButtonnn_01.setText(ui.dict_set['백테스케쥴구분'])
        ui.sd_dcomboBoxxxx_01.setCurrentText(ui.dict_set['백테스케쥴명'])
        qtest_qwait(2)
        ui.sdButtonClicked_02()
    elif gubun == 3:
        if ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.close()
        ui.teleQ.put('백테스트 스케쥴러 완료')
        ui.auto_mode = False


def update_dictset(ui):
    ui.wdzservQ.put(('manager', ('설정변경', ui.dict_set)))
    if ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('설정변경', ui.dict_set))
    if ui.CoinTraderProcessAlive():   ui.ctraderQ.put(('설정변경', ui.dict_set))
    if ui.CoinStrategyProcessAlive(): ui.cstgQ.put(('설정변경', ui.dict_set))
    if ui.proc_chart.is_alive():      ui.chartQ.put(('설정변경', ui.dict_set))
    if ui.proc_query.is_alive():      ui.queryQ.put(('설정변경', ui.dict_set))
    if ui.proc_hoga.is_alive():       ui.hogaQ.put(('설정변경', ui.dict_set))
    if ui.backtest_engine:
        for bpq in ui.back_eques:
            bpq.put(('설정변경', ui.dict_set))


def chart_clear(ui):
    ui.ctpg_name             = None
    ui.ctpg_cline            = None
    ui.ctpg_hline            = None
    ui.ctpg_xticks           = None
    ui.ctpg_arry             = None
    ui.ctpg_last_candlestick = None
    ui.ctpg_last_volumebar   = None
    ui.ctpg_last_xtick       = None
    ui.ctpg_legend           = {}
    ui.ctpg_item             = {}
    ui.ctpg_data             = {}
    ui.ctpg_factors          = []
    ui.ctpg_labels           = []


def calendar_clicked(ui, gubun):
    if gubun == 'S':
        table = 's_tradelist'
        searchday = ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
    else:
        table = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
        searchday = ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
    con = sqlite3.connect(DB_TRADELIST)
    df1 = pd.read_sql(f"SELECT * FROM {table} WHERE 체결시간 LIKE '{searchday}%'", con).set_index('index')
    con.close()
    if len(df1) > 0:
        df1.sort_values(by=['체결시간'], ascending=True, inplace=True)
        if table == 'c_tradelist_future':
            df1 = df1[['체결시간', '종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        else:
            df1 = df1[['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        nbg, nsg = df1['매수금액'].sum(), df1['매도금액'].sum()
        sp = round((nsg / nbg - 1) * 100, 2)
        npg, nmg, nsig = df1[df1['수익금'] > 0]['수익금'].sum(), df1[df1['수익금'] < 0]['수익금'].sum(), df1['수익금'].sum()
        df2 = pd.DataFrame(columns=columns_dt)
        df2.loc[0] = searchday, nbg, nsg, npg, nmg, sp, nsig
    else:
        df1 = pd.DataFrame(columns=columns_dd)
        df2 = pd.DataFrame(columns=columns_dt)
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일합계'], df2))
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일상세'], df1))


def video_widget_close(ui, state):
    if state == QMediaPlayer.StoppedState:
        ui.videoWidget.setVisible(False)


def stom_live_screenshot(ui, cmd):
    ui.mnButtonClicked_01(4)
    qtest_qwait(1)
    if cmd == 'S스톰라이브':
        mid = 'S'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index1)
    elif cmd == 'C스톰라이브':
        mid = 'C'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index2)
    else:
        mid = 'B'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index3)
    qtest_qwait(1)
    file_name = f'./_log/StomLive_{mid}_{strf_time("%Y%m%d%H%M%S")}.png'
    screen = QApplication.primaryScreen()
    screenshot = screen.grabWindow(ui.winId())
    screenshot.save(file_name, 'png')
    ui.teleQ.put(file_name)
    ui.mnButtonClicked_01(0)


def chart_screenshot(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{strf_time("%Y%m%d%H%M%S%f")}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui, '차트 스샷 전송 완료', random.choice(famous_saying))


def chart_screenshot2(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{strf_time("%Y%m%d%H%M%S%f")}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui.dialog_chart, '차트 스샷 전송 완료', random.choice(famous_saying))
