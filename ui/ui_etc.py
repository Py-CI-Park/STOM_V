
import psutil
import random
import pandas as pd
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox
from ui.set_text import famous_saying
from utility.setting_base import columns_dt, columns_dd, ui_num
from utility.static import thread_decorator, qtest_qwait, str_ymdhmsf, str_ymdhms, error_decorator


@error_decorator
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


@error_decorator
def update_sqsize(ui, data):
    ui.saqsize, ui.stqsize, ui.ssqsize = data


@thread_decorator
def update_cpuper(ui):
    ui.cpu_per = int(psutil.cpu_percent(interval=1))


@error_decorator
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
        ui.BacktestEngineStart(ui.dict_set['백테스케쥴구분'])
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


@error_decorator
def update_dictset(ui):
    if ui.proc_manager is not None and ui.proc_manager.poll() is None:
        ui.wdzservQ.put(('manager', ('설정변경', ui.dict_set)))
    if ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('설정변경', ui.dict_set))
    if ui.CoinTraderProcessAlive():   ui.ctraderQ.put(('설정변경', ui.dict_set))
    if ui.CoinStrategyProcessAlive(): ui.cstgQ.put(('설정변경', ui.dict_set))
    if ui.proc_chqs.is_alive():       ui.chartQ.put(('설정변경', ui.dict_set))
    if ui.telegram.isRunning():       ui.teleQ.put(('설정변경', ui.dict_set))
    if ui.backtest_engine:
        for bpq in ui.back_eques:
            bpq.put(('설정변경', ui.dict_set))


@error_decorator
def chart_clear(ui):
    ui.ctpg_code    = None
    ui.ctpg_cline   = None
    ui.ctpg_hline   = None
    ui.ctpg_xticks  = None
    ui.ctpg_arry    = None
    ui.ctpg_legend  = {}
    ui.ctpg_item    = {}
    ui.ctpg_data    = {}
    ui.ctpg_factors = []
    ui.ctpg_labels  = []


@error_decorator
def calendar_clicked(ui, gubun):
    if gubun == 'S':
        table = 's_tradelist' if '키움증권' in ui.dict_set['증권사'] else 'f_tradelist'
        searchday = ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
    else:
        table = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
        searchday = ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
    df1 = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table} WHERE 체결시간 LIKE '{searchday}%'").set_index('index')
    if len(df1) > 0:
        df1.sort_values(by=['체결시간'], ascending=True, inplace=True)
        if table in ('f_tradelist', 'c_tradelist_future'):
            df1 = df1[['체결시간', '종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        else:
            df1 = df1[['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        nbg, nsg = df1['매수금액'].sum(), df1['매도금액'].sum()
        sp = round((nsg / nbg - 1) * 100, 2)
        npg, nmg, nsig = df1[df1['수익금'] > 0]['수익금'].sum(), df1[df1['수익금'] < 0]['수익금'].sum(), df1['수익금'].sum()
        df2 = pd.DataFrame(columns=columns_dt)
        df2.loc[0] = [searchday, nbg, nsg, npg, nmg, sp, nsig]
    else:
        df1 = pd.DataFrame(columns=columns_dd)
        df2 = pd.DataFrame(columns=columns_dt)
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일합계'], df2))
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일상세'], df1))


@error_decorator
def stom_live_screenshot(ui, cmd):
    prev_main_btn = ui.main_btn
    ui.mnButtonClicked_01(5)
    qtest_qwait(1)
    if '주식' in cmd:
        mid = 'S'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index1)
    elif '코인' in cmd:
        mid = 'C'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index2)
    elif '해선' in cmd:
        mid = 'F'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index3)
    else:
        mid = 'B'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index4)
    qtest_qwait(1)
    file_name = f'./_log/StomLive_{mid}_{str_ymdhms()}.png'
    screen = QApplication.primaryScreen()
    screenshot = screen.grabWindow(ui.winId())
    screenshot.save(file_name, 'png')
    ui.teleQ.put(file_name)
    ui.mnButtonClicked_01(prev_main_btn)


@error_decorator
def chart_screenshot(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui, '차트 스샷 전송 완료', random.choice(famous_saying))


@error_decorator
def chart_screenshot2(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui.dialog_chart, '차트 스샷 전송 완료', random.choice(famous_saying))


@error_decorator
def manual_save_and_exit(ui):
    buttonReply = QMessageBox.question(
        ui, '수동종료', '현재까지의 데이터를 저장하고 수동종료합니다.\n계속 하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.CoinReceiverProcessAlive():
            ui.creceivQ.put(('수동데이터저장', 'dummy'))
        else:
            ui.wdzservQ.put(('agent', ('수동데이터저장', 'dummy')))


def stom_public_use_limit(ui):
    QMessageBox.critical(ui, 'STOM PUBLIC', '현재의 권한으로 사용할 수 없는 기능입니다.\n구독문의: https://cafe.naver.com/stom')
