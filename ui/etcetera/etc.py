
import psutil
import random
import pandas as pd
from io import BytesIO
from PyQt5.QtGui import QPixmap
from ui.create_widget.set_text import famous_saying
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QSize, Qt, QBuffer, QIODevice
from utility.settings.setting_base import columns_dt, columns_dd, ui_num
from ui.event_click.button_clicked_shortcut import mnbutton_c_clicked_01
from utility.static_method.static import thread_decorator, qtest_qwait, str_ymdhmsf
from ui.event_click.button_clicked_backtest_engine import backengine_start, backengine_show
from ui.event_click.button_clicked_backtest_start import backtest_engine_kill, sdbutton_clicked_04
from ui.etcetera.process_alive import strategy_process_alive, trader_process_alive, receiver_process_alive


def update_image(ui, data):
    """이미지를 업데이트합니다.
    Args:
        ui: UI 객체
        data: 이미지 데이터 튜플
    """
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


@thread_decorator
def update_cpuper(ui):
    """CPU 사용률을 업데이트합니다.
    Args:
        ui: UI 객체
    """
    ui.cpu_per = int(psutil.cpu_percent(interval=1))


def auto_back_schedule(ui, gubun):
    """자동 백테스트 스케줄러를 실행합니다.
    Args:
        ui: UI 객체
        gubun (int): 구분 번호 (1: 시작, 2: 스케줄러 표시)
    """
    if gubun == 1:
        ui.auto_mode = True
        if ui.dict_set['알림소리'] or ui.dict_set['알림소리']:
            ui.soundQ.put('예약된 백테스트 스케쥴러를 시작합니다.')
        if not ui.dialog_backengine.isVisible():
            backengine_show(ui)
        qtest_qwait(2)
        backtest_engine_kill(ui)
        qtest_qwait(3)
        backengine_start(ui)
    elif gubun == 2:
        if not ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.show()
        qtest_qwait(2)
        sdbutton_clicked_04(ui)
        qtest_qwait(2)
        ui.sd_dcomboBoxxxx_01.setCurrentText(ui.dict_set['백테스케쥴명'])
        qtest_qwait(2)
        ui.sdButtonClicked_02()
    elif gubun == 3:
        if ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.close()
        ui.teleQ.put('백테스트 스케쥴러 완료')
        ui.auto_mode = False


def update_dictset(ui):
    """설정 딕셔너리를 업데이트합니다.
    Args:
        ui: UI 객체
    """
    update_market_gubun(ui)

    if receiver_process_alive(ui):
        ui.receivQ.put(('설정변경', ui.dict_set))
    if trader_process_alive(ui):
        ui.traderQ.put(('설정변경', ui.dict_set))
    if strategy_process_alive(ui):
        if ui.market_gubun < 5:
            for q in ui.stgQs:
                q.put(('설정변경', ui.dict_set))
        else:
            ui.stgQs[0].put(('설정변경', ui.dict_set))

    if ui.proc_chqs.is_alive():
        ui.chartQ.put(('설정변경', ui.dict_set))
    if ui.telegram.isRunning():
        ui.teleQ.put(('설정변경', ui.dict_set))

    if ui.backtest_engine:
        for bpq in ui.back_eques:
            bpq.put(('설정변경', ui.dict_set))


def update_market_gubun(ui):
    """시장 구분을 업데이트합니다.
    Args:
        ui: UI 객체
    """
    from utility.settings.setting_market import DICT_MARKET_GUBUN, DICT_MARKET_INFO
    ui.market_gubun = DICT_MARKET_GUBUN[ui.dict_set['거래소']]
    ui.market_info  = DICT_MARKET_INFO[ui.market_gubun]
    ui.market_infos = [ui.market_gubun, ui.market_info]
    factor_list     = ui.market_info['팩터목록'][ui.dict_set['타임프레임']]
    ui.dict_findex  = {factor: i for i, factor in enumerate(factor_list)}


def chart_clear(ui):
    """차트 데이터를 초기화합니다.
    Args:
        ui: UI 객체
    """
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


def calendar_clicked(ui):
    """캘린더 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 객체
    """
    table_name = ui.market_info['거래디비']
    searchday = ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
    df1 = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{searchday}%'").set_index('index')
    if len(df1) > 0:
        df1.sort_values(by=['체결시간'], ascending=True, inplace=True)
        if ui.market_gubun > 5:
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
    ui.update_tablewidget.update_tablewidget((ui_num['당일합계'], df2))
    ui.update_tablewidget.update_tablewidget((ui_num['당일상세'], df1))


def stom_live_screenshot(ui):
    """STOM 라이브 스크린샷을 찍습니다.
    Args:
        ui: UI 객체
    """
    prev_main_btn = ui.main_btn
    mnbutton_c_clicked_01(ui, 3)
    qtest_qwait(1)
    if ui.market_gubun in (1, 2, 3):
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index1)
    elif ui.market_gubun in (5, 9):
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index2)
    else:
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index3)
    qtest_qwait(1)
    screen = QApplication.primaryScreen()
    # noinspection PyUnresolvedReferences
    pixmap = screen.grabWindow(ui.winId())

    # QBuffer를 사용하여 QPixmap을 바이트 배열로 변환
    qbuffer = QBuffer()
    # noinspection PyUnresolvedReferences
    qbuffer.open(QIODevice.WriteOnly)
    pixmap.save(qbuffer, 'PNG')
    byte_array = qbuffer.data().data()  # QByteArray -> bytes
    qbuffer.close()

    # BytesIO로 감싸서 전송
    buffer = BytesIO(byte_array)
    buffer.seek(0)
    ui.teleQ.put(buffer)
    mnbutton_c_clicked_01(ui, prev_main_btn)


def chart_screenshot(ui):
    """차트 스크린샷을 찍습니다.
    Args:
        ui: UI 객체
    """
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        # noinspection PyUnresolvedReferences
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui, '차트 스샷 전송 완료', random.choice(famous_saying))


def chart_screenshot2(ui):
    """차트 스크린샷을 찍습니다 (다이얼로그 기준).
    Args:
        ui: UI 객체
    """
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        # noinspection PyUnresolvedReferences
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui.dialog_chart, '차트 스샷 전송 완료', random.choice(famous_saying))


def manual_save_and_exit(ui):
    """수동으로 저장하고 종료합니다.
    Args:
        ui: UI 객체
    """
    buttonReply = QMessageBox.question(
        ui, '수동종료', '현재까지의 데이터를 저장하고 수동종료합니다.\n계속 하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if receiver_process_alive(ui):
            ui.receivQ.put(('수동데이터저장', 'dummy'))


def stom_public_use_limit(ui):
    """STOM 퍼블릭 사용 제한을 표시합니다.
    Args:
        ui: UI 객체
    """
    QMessageBox.critical(ui, 'STOM PUBLIC', '현재의 권한으로 사용할 수 없는 기능입니다.\n구독문의: https://cafe.naver.com/stom')


def strategy_setting_label_change(ui):
    """전략 설정 라벨을 변경합니다.
    Args:
        ui: UI 객체
    """
    if ui.market_gubun < 4 or ui.market_gubun == 5:
        ui.sj_strgy_label_02.setText(
            '종목당투자금                          백만원                  ▣  전략중지 및 잔고청산   |')
    elif ui.market_gubun in (6, 7, 8):
        ui.sj_strgy_label_02.setText(
            '종목당투자금                          계약수                  ▣  전략중지 및 잔고청산   |')
    elif ui.market_gubun == 4:
        ui.sj_strgy_label_02.setText(
            '종목당투자금                          USD                    ▣  전략중지 및 잔고청산   |')
    else:
        ui.sj_strgy_label_02.setText(
            '종목당투자금                          USDT                  ▣  전략중지 및 잔고청산   |')
