import os
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer, QPropertyAnimation, QSize, QEasingCurve
from multiprocessing import Process
from coin.binance_trader import BinanceTrader
from coin.binance_receiver_min import BinanceReceiverMin
from coin.binance_strategy_min import BinanceStrategyMin
from coin.binance_receiver_tick import BinanceReceiverTick
from coin.binance_strategy_tick import BinanceStrategyTick
from coin.binance_receiver_client import BinanceReceiverClient
from coin.upbit_trader import UpbitTrader
from coin.upbit_receiver_min import UpbitReceiverMin
from coin.upbit_strategy_min import UpbitStrategyMin
from coin.upbit_receiver_tick import UpbitReceiverTick
from coin.upbit_strategy_tick import UpbitStrategyTick
from coin.upbit_receiver_client import UpbitReceiverClient
from ui.set_style import style_bc_bt, style_bc_bb
from utility.setting import GRAPH_PATH, DB_BACKTEST, columns_tdf, columns_jgf, ui_num
from utility.static import qtest_qwait


def mnbutton_c_clicked_01(ui, index):
    if ui.extend_window:
        QMessageBox.critical(ui, '오류 알림', '전략탭 확장 상태에서는 탭을 변경할 수 없습니다.')
        return
    prev_main_btn = ui.main_btn
    if prev_main_btn == index: return
    ui.image_label1.setVisible(False)
    if index == 3:
        if ui.dict_set['거래소'] == '업비트':
            ui.cvjb_labelllll_03.setText('백테스트 기본설정   배팅(백만)                        평균틱수   self.vars[0]')
            if ui.cvjb_lineEditt_04.text() == '10000':
                ui.cvjb_lineEditt_04.setText('20')
        else:
            ui.cvjb_labelllll_03.setText('백테스트 기본설정배팅(USDT)                        평균틱수   self.vars[0]')
            if ui.cvjb_lineEditt_04.text() == '20':
                ui.cvjb_lineEditt_04.setText('10000')
    elif index == 5 and ui.lgicon_alert:
        ui.lgicon_alert = False
        ui.main_btn_list[index].setIcon(ui.icon_log)
    elif index == 6:
        if ui.dict_set['거래소'] == '업비트':
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          백만원                                  전략중지 및 잔고청산   |')
        else:
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          USDT                                   전략중지 및 잔고청산   |')

    ui.main_btn = index
    ui.main_btn_list[prev_main_btn].setStyleSheet(style_bc_bb)
    ui.main_btn_list[ui.main_btn].setStyleSheet(style_bc_bt)
    ui.main_box_list[prev_main_btn].setVisible(False)
    ui.main_box_list[ui.main_btn].setVisible(True)
    QTimer.singleShot(400, lambda: ui.image_label1.setVisible(True if ui.svc_labellllll_05.isVisible() or ui.cvc_labellllll_05.isVisible() else False))
    ui.animation = QPropertyAnimation(ui.main_box_list[ui.main_btn], b'size')
    ui.animation.setEasingCurve(QEasingCurve.InCirc)
    ui.animation.setDuration(300)
    ui.animation.setStartValue(QSize(0, 757))
    ui.animation.setEndValue(QSize(1353, 757))
    ui.animation.start()


def mnbutton_c_clicked_02(ui):
    if ui.main_btn == 0:
        if not ui.s_calendarWidgett.isVisible():
            boolean1 = False
            boolean2 = True
        else:
            boolean1 = True
            boolean2 = False
        for widget in ui.stock_basic_listt:
            widget.setVisible(boolean1)
        for widget in ui.stock_total_listt:
            widget.setVisible(boolean2)
    elif ui.main_btn == 1:
        if not ui.c_calendarWidgett.isVisible():
            boolean1 = False
            boolean2 = True
        else:
            boolean1 = True
            boolean2 = False
        for widget in ui.coin_basic_listtt:
            widget.setVisible(boolean1)
        for widget in ui.coin_total_listtt:
            widget.setVisible(boolean2)
    else:
        QMessageBox.warning(ui, '오류 알림', '해당 버튼은 트레이더탭에서만 작동합니다.\n')


def mnbutton_c_clicked_03(ui, login):
    if login in (1, 2):
        buttonReply = QMessageBox.Yes
    else:
        if ui.dialog_web.isVisible():
            QMessageBox.critical(ui, '오류 알림', '웹뷰어창이 열린 상태에서는 수동시작할 수 없습니다.\n웹뷰어창을 닫고 재시도하십시오.\n')
            return
        if ui.dict_set['주식리시버']:
            buttonReply = QMessageBox.question(
                ui, '주식 수동 시작', '주식 리시버 또는 트레이더를 시작합니다.\n이미 실행 중이라면 기존 프로세스는 종료됩니다.\n계속하시겠습니까?\n',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
        elif ui.dict_set['코인리시버']:
            buttonReply = QMessageBox.question(
                ui, '코인 수동 시작', '코인 리시버 또는 트레이더를 시작합니다.\n이미 실행 중이라면 기존 프로세스는 종료됩니다.\n계속하시겠습니까?\n',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
        else:
            buttonReply = QMessageBox.No

    if buttonReply == QMessageBox.Yes:
        if login == 1 or (login == 0 and ui.dict_set['주식리시버']):
            ui.wdzservQ.put(('manager', '리시버 종료'))
            ui.wdzservQ.put(('manager', '전략연산 종료'))
            ui.wdzservQ.put(('manager', '트레이더 종료'))
            qtest_qwait(3)
            if ui.dict_set['리시버공유'] < 2 and ui.dict_set['아이디2'] is None:
                QMessageBox.critical(ui, '오류 알림', '두번째 계정이 설정되지 않아\n리시버를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            elif ui.dict_set['아이디1'] is None:
                QMessageBox.critical(ui, '오류 알림', '첫번째 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            elif ui.dict_set['주식리시버'] and ui.dict_set['주식트레이더']:
                if ui.dict_set['주식알림소리']:
                    ui.soundQ.put('키움증권 OPEN API에 로그인을 시작합니다.')
                ui.wdzservQ.put(('manager', '주식수동시작'))
                ui.ms_pushButton.setStyleSheet(style_bc_bt)
        elif login == 2 or (login == 0 and ui.dict_set['코인리시버']):
            if ui.CoinReceiverProcessAlive(): ui.proc_receiver_coin.kill()
            if ui.CoinStrategyProcessAlive(): ui.proc_strategy_coin.kill()
            if ui.CoinTraderProcessAlive():   ui.proc_trader_coin.kill()
            qtest_qwait(3)
            if ui.dict_set['거래소'] == '업비트' and (ui.dict_set['Access_key1'] is None or ui.dict_set['Secret_key1'] is None):
                QMessageBox.critical(ui, '오류 알림', '업비트 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            elif ui.dict_set['거래소'] == '바이낸스선물' and (ui.dict_set['Access_key2'] is None or ui.dict_set['Secret_key2'] is None):
                QMessageBox.critical(ui, '오류 알림', '바이낸스선물 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            else:
                if ui.dict_set['코인리시버']:
                    CoinReceiverStart(ui, ui.qlist)
                if ui.dict_set['코인트레이더']:
                    CoinTraderStart(ui, ui.qlist, ui.windowQ)
                ui.ms_pushButton.setStyleSheet(style_bc_bt)


def mnbutton_c_clicked_04(ui):
    if ui.geometry().width() > 1000:
        ui.setFixedSize(722, 383)
        ui.zo_pushButton.setStyleSheet(style_bc_bt)
    else:
        ui.setFixedSize(1403, 763)
        ui.zo_pushButton.setStyleSheet(style_bc_bb)


def mnbutton_c_clicked_05(ui):
    buttonReply = QMessageBox.warning(
        ui, '백테기록삭제', '백테 그래프 및 기록 DB가 삭제됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        file_list = os.listdir(GRAPH_PATH)
        for file_name in file_list:
            os.remove(f'{GRAPH_PATH}/{file_name}')
        if ui.proc_query.is_alive():
            con = sqlite3.connect(DB_BACKTEST)
            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
            con.close()
            table_list = df['name'].to_list()
            for table_name in table_list:
                ui.queryQ.put(('백테디비', f'DROP TABLE {table_name}'))
            ui.queryQ.put(('백테디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '백테그래프 및 기록DB가 삭제되었습니다.')


def mnbutton_c_clicked_06(ui):
    buttonReply = QMessageBox.warning(
        ui, '계정 설정 초기화', '계정 설정 항목이 모두 초기화됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.proc_query.is_alive():
            ui.queryQ.put(('설정디비', 'DELETE FROM sacc'))
            ui.queryQ.put(('설정디비', 'DELETE FROM cacc'))
            ui.queryQ.put(('설정디비', 'DELETE FROM telegram'))
            columns = [
                "index", "아이디", "비밀번호", "인증서비밀번호", "계좌비밀번호"
            ]
            data = [
                [1, '', '', '', ''],
                [2, '', '', '', ''],
                [3, '', '', '', ''],
                [4, '', '', '', ''],
                [5, '', '', '', ''],
                [6, '', '', '', ''],
                [7, '', '', '', ''],
                [8, '', '', '', '']
            ]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put((df, 'sacc', 'append'))
            columns = ["index", "Access_key", "Secret_key"]
            data = [[1, '', ''], [2, '', '']]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put((df, 'cacc', 'append'))
            columns = ["index", "str_bot", "int_id"]
            data = [[1, '', ''], [2, '', ''], [3, '', ''], [4, '', '']]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put((df, 'telegram', 'append'))
            ui.queryQ.put(('설정디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '계정 설정 항목이 모두 초기화되었습니다.')


def CoinReceiverStart(ui, qlist):
    if not ui.CoinReceiverProcessAlive():
        if ui.dict_set['리시버공유'] < 2:
            if ui.dict_set['코인타임프레임']:
                target = UpbitReceiverTick if ui.dict_set['거래소'] == '업비트' else BinanceReceiverTick
            else:
                target = UpbitReceiverMin if ui.dict_set['거래소'] == '업비트' else BinanceReceiverMin
            ui.proc_receiver_coin = Process(target=target, args=(qlist,))
        else:
            ui.proc_receiver_coin = Process(target=UpbitReceiverClient if ui.dict_set['거래소'] == '업비트' else BinanceReceiverClient, args=(qlist,))
        ui.proc_receiver_coin.start()


def CoinTraderStart(ui, qlist, windowQ):
    if ui.dict_set['거래소'] == '업비트' and (ui.dict_set['Access_key1'] is None or ui.dict_set['Secret_key1'] is None):
        windowQ.put((ui_num['C단순텍스트'], '시스템 명령 오류 알림 - 업비트 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.'))
        return
    elif ui.dict_set['거래소'] == '바이낸스선물' and (ui.dict_set['Access_key2'] is None or ui.dict_set['Secret_key2'] is None):
        windowQ.put((ui_num['C단순텍스트'], '시스템 명령 오류 알림 - 바이낸스선물 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.'))
        return

    if not ui.CoinStrategyProcessAlive():
        if ui.dict_set['코인타임프레임']:
            target = UpbitStrategyTick if ui.dict_set['거래소'] == '업비트' else BinanceStrategyTick
        else:
            target = UpbitStrategyMin if ui.dict_set['거래소'] == '업비트' else BinanceStrategyMin
        ui.proc_strategy_coin = Process(target=target, args=(qlist,), daemon=True)
        ui.proc_strategy_coin.start()
    if not ui.CoinTraderProcessAlive():
        ui.proc_trader_coin = Process(target=UpbitTrader if ui.dict_set['거래소'] == '업비트' else BinanceTrader, args=(qlist,))
        ui.proc_trader_coin.start()
        if ui.dict_set['거래소'] == '바이낸스선물':
            ui.ctd_tableWidgettt.setColumnCount(len(columns_tdf))
            ui.ctd_tableWidgettt.setHorizontalHeaderLabels(columns_tdf)
            ui.ctd_tableWidgettt.setColumnWidth(0, 96)
            ui.ctd_tableWidgettt.setColumnWidth(1, 90)
            ui.ctd_tableWidgettt.setColumnWidth(2, 90)
            ui.ctd_tableWidgettt.setColumnWidth(3, 90)
            ui.ctd_tableWidgettt.setColumnWidth(4, 140)
            ui.ctd_tableWidgettt.setColumnWidth(5, 70)
            ui.ctd_tableWidgettt.setColumnWidth(6, 90)
            ui.ctd_tableWidgettt.setColumnWidth(7, 90)
            ui.cjg_tableWidgettt.setColumnCount(len(columns_jgf))
            ui.cjg_tableWidgettt.setHorizontalHeaderLabels(columns_jgf)
            ui.cjg_tableWidgettt.setColumnWidth(0, 96)
            ui.cjg_tableWidgettt.setColumnWidth(1, 70)
            ui.cjg_tableWidgettt.setColumnWidth(2, 115)
            ui.cjg_tableWidgettt.setColumnWidth(3, 115)
            ui.cjg_tableWidgettt.setColumnWidth(4, 90)
            ui.cjg_tableWidgettt.setColumnWidth(5, 90)
            ui.cjg_tableWidgettt.setColumnWidth(6, 90)
            ui.cjg_tableWidgettt.setColumnWidth(7, 90)
            ui.cjg_tableWidgettt.setColumnWidth(8, 90)
            ui.cjg_tableWidgettt.setColumnWidth(9, 90)
            ui.cjg_tableWidgettt.setColumnWidth(10, 90)
            ui.cjg_tableWidgettt.setColumnWidth(11, 90)
