
import os
import pandas as pd
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QTimer, QPropertyAnimation, QSize, QEasingCurve
from multiprocessing import Process
from trade.binance.binance_trader import BinanceTrader
from trade.binance.binance_receiver_min import BinanceReceiverMin
from trade.binance.binance_strategy_min import BinanceStrategyMin
from trade.binance.binance_receiver_tick import BinanceReceiverTick
from trade.binance.binance_strategy_tick import BinanceStrategyTick
from trade.upbit.upbit_trader import UpbitTrader
from trade.upbit.upbit_receiver_min import UpbitReceiverMin
from trade.upbit.upbit_strategy_min import UpbitStrategyMin
from trade.upbit.upbit_receiver_tick import UpbitReceiverTick
from trade.upbit.upbit_strategy_tick import UpbitStrategyTick
from ui.set_style import style_bc_bb, style_bc_st
from utility.setting_base import GRAPH_PATH, ui_num
from utility.static import qtest_qwait, cme_normal_open, error_decorator


@error_decorator
def mnbutton_c_clicked_01(ui, index):
    if ui.extend_window:
        QMessageBox.critical(ui, '오류 알림', '전략탭 확장 상태에서는 탭을 변경할 수 없습니다.')
        return
    prev_main_btn = ui.main_btn
    if prev_main_btn == index: return
    ui.image_label1.setVisible(False)
    if index == 3:
        ui.svjb_lineEditt_04.setText(str(ui.dict_set['주식투자금']))
    elif index == 4:
        ui.cvjb_lineEditt_04.setText(str(ui.dict_set['코인투자금']))
    elif index == 6 and ui.lgicon_alert:
        ui.lgicon_alert = False
        ui.main_btn_list[index].setIcon(ui.icon_log)
    elif index == 7:
        if '키움증권' in ui.dict_set['증권사']:
            ui.sj_stock_label_03.setText(
                '종목당투자금                          백만원                                  전략중지 및 잔고청산   |')
        else:
            ui.sj_stock_label_03.setText(
                '종목당투자금                          계약수                                  전략중지 및 잔고청산   |')
        if ui.dict_set['거래소'] == '업비트':
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          백만원                                  전략중지 및 잔고청산   |')
        else:
            ui.sj_coin_labell_03.setText(
                '종목당투자금                          USDT                                   전략중지 및 잔고청산   |')

    ui.main_btn = index
    ui.main_btn_list[prev_main_btn].setStyleSheet(style_bc_bb)
    ui.main_btn_list[ui.main_btn].setStyleSheet(style_bc_st)
    ui.main_box_list[prev_main_btn].setVisible(False)
    ui.main_box_list[ui.main_btn].setVisible(True)
    QTimer.singleShot(300, lambda: ui.image_label1.setVisible(True if ui.svc_labellllll_05.isVisible() or ui.cvc_labellllll_05.isVisible() else False))
    ui.animation = QPropertyAnimation(ui.main_box_list[ui.main_btn], b'size')
    ui.animation.setEasingCurve(QEasingCurve.InOutCirc)
    ui.animation.setDuration(300)
    ui.animation.setStartValue(QSize(0, 757))
    ui.animation.setEndValue(QSize(1353, 757))
    ui.animation.start()


@error_decorator
def mnbutton_c_clicked_02(ui):
    if ui.main_btn == 1:
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
    elif ui.main_btn == 2:
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


@error_decorator
def mnbutton_c_clicked_03(ui, login):
    if login in (1, 2, 3):
        buttonReply = QMessageBox.Yes
    else:
        if ui.dialog_web.isVisible():
            QMessageBox.critical(ui, '오류 알림', '웹뷰어창이 열린 상태에서는 수동시작할 수 없습니다.\n웹뷰어창을 닫고 재시도하십시오.\n')
            return
        if ui.dict_set['주식에이전트']:
            if '키움증권' in ui.dict_set['증권사']:
                buttonReply = QMessageBox.question(
                    ui, '주식 수동 시작', '주식 리시버 또는 트레이더를 시작합니다.\n이미 실행 중이라면 기존 프로세스는 종료됩니다.\n계속하시겠습니까?\n',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
            else:
                buttonReply = QMessageBox.question(
                    ui, '해선 수동 시작', '해선 리시버 또는 트레이더를 시작합니다.\n이미 실행 중이라면 기존 프로세스는 종료됩니다.\n계속하시겠습니까?\n',
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
        if login in (1, 3) or (login == 0 and ui.dict_set['주식에이전트']):
            ui.mnButtonClicked_01(1)
            if login == 3 and not cme_normal_open():
                ui.windowQ.put((ui_num['기본로그'], '해외선물은 휴무 또는 조기마감일입니다.'))
                ui.windowQ.put((ui_num['기본로그'], '시스템 명령 실행 알림 - 해외선물 휴무 종료'))
                return
            ui.wdzservQ.put(('manager', '에이전트 종료'))
            ui.wdzservQ.put(('manager', '전략연산 종료'))
            ui.wdzservQ.put(('manager', '트레이더 종료'))
            qtest_qwait(3)
            id_num = ui.dict_set['증권사'][4:]
            if ui.dict_set[f"아이디{id_num}"] is None:
                QMessageBox.critical(ui, '오류 알림', '계정이 설정되지 않아 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            elif ui.dict_set['주식에이전트'] and ui.dict_set['주식트레이더']:
                if ui.dict_set['주식알림소리']:
                    ui.soundQ.put(f"{ui.dict_set['증권사'][:4]} OPEN API에 로그인을 시작합니다.")
                ui.wdzservQ.put(('manager', '수동시작'))
                ui.ms_pushButton.setStyleSheet(style_bc_st)
        elif login == 2 or (login == 0 and ui.dict_set['코인리시버']):
            ui.mnButtonClicked_01(2)
            if ui.CoinTraderProcessAlive():   ui.proc_trader_coin.kill()
            if ui.CoinStrategyProcessAlive(): ui.proc_strategy_coin.kill()
            if ui.CoinReceiverProcessAlive(): ui.proc_receiver_coin.kill()
            qtest_qwait(3)
            if ui.dict_set['거래소'] == '업비트' and (ui.dict_set['Access_key1'] is None or ui.dict_set['Secret_key1'] is None):
                QMessageBox.critical(ui, '오류 알림', '업비트 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            elif ui.dict_set['거래소'] == '바이낸스선물' and (ui.dict_set['Access_key2'] is None or ui.dict_set['Secret_key2'] is None):
                QMessageBox.critical(ui, '오류 알림', '바이낸스선물 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
            else:
                if ui.dict_set['코인트레이더']:
                    CoinTraderStart(ui)
                if ui.dict_set['코인리시버']:
                    CoinReceiverStart(ui)
                ui.ms_pushButton.setStyleSheet(style_bc_st)


@error_decorator
def mnbutton_c_clicked_04(ui):
    if ui.geometry().width() > 1000:
        ui.setFixedSize(722, 383)
        ui.zo_pushButton.setStyleSheet(style_bc_st)
    else:
        ui.setFixedSize(1403, 763)
        ui.zo_pushButton.setStyleSheet(style_bc_bb)


@error_decorator
def mnbutton_c_clicked_05(ui):
    buttonReply = QMessageBox.warning(
        ui, '백테기록삭제', '백테 그래프 및 기록 DB가 삭제됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        file_list = os.listdir(GRAPH_PATH)
        for file_name in file_list:
            os.remove(f'{GRAPH_PATH}/{file_name}')
        if ui.proc_chqs.is_alive():
            df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            table_list = df['name'].to_list()
            for table_name in table_list:
                ui.queryQ.put(('백테디비', f'DROP TABLE {table_name}'))
            ui.queryQ.put(('백테디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '백테그래프 및 기록DB가 삭제되었습니다.')


@error_decorator
def mnbutton_c_clicked_06(ui):
    buttonReply = QMessageBox.warning(
        ui, '계정 설정 초기화', '계정 설정 항목이 모두 초기화됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.proc_chqs.is_alive():
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
            data = [
                [1, '', ''],
                [2, '', ''],
                [3, '', ''],
                [4, '', ''],
                [5, '', ''],
                [6, '', ''],
                [7, '', ''],
                [8, '', '']
            ]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put((df, 'telegram', 'append'))

            ui.queryQ.put(('설정디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '계정 설정 항목이 모두 초기화되었습니다.')


@error_decorator
def CoinReceiverStart(ui):
    if not ui.CoinReceiverProcessAlive():
        if ui.dict_set['코인타임프레임']:
            target = UpbitReceiverTick if ui.dict_set['거래소'] == '업비트' else BinanceReceiverTick
        else:
            target = UpbitReceiverMin if ui.dict_set['거래소'] == '업비트' else BinanceReceiverMin
        ui.proc_receiver_coin = Process(target=target, args=(ui.qlist, ui.dict_set))
        ui.proc_receiver_coin.start()


@error_decorator
def CoinTraderStart(ui):
    if ui.dict_set['거래소'] == '업비트' and (ui.dict_set['Access_key1'] is None or ui.dict_set['Secret_key1'] is None):
        ui.windowQ.put((ui_num['시스템로그'], '오류 알림 - 업비트 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.'))
        return
    elif ui.dict_set['거래소'] == '바이낸스선물' and (ui.dict_set['Access_key2'] is None or ui.dict_set['Secret_key2'] is None):
        ui.windowQ.put((ui_num['시스템로그'], '오류 알림 - 바이낸스선물 계정이 설정되지 않아 트레이더를 시작할 수 없습니다. 계정 설정 후 다시 시작하십시오.'))
        return

    if not ui.CoinStrategyProcessAlive():
        if ui.dict_set['코인타임프레임']:
            target = UpbitStrategyTick if ui.dict_set['거래소'] == '업비트' else BinanceStrategyTick
        else:
            target = UpbitStrategyMin if ui.dict_set['거래소'] == '업비트' else BinanceStrategyMin
        ui.proc_strategy_coin = Process(target=target, args=(ui.qlist, ui.dict_set), daemon=True)
        ui.proc_strategy_coin.start()
    if not ui.CoinTraderProcessAlive():
        ui.proc_trader_coin = Process(target=UpbitTrader if ui.dict_set['거래소'] == '업비트' else BinanceTrader, args=(ui.qlist, ui.dict_set))
        ui.proc_trader_coin.start()
