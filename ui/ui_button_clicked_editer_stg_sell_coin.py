import random
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.static import text_not_in_special_characters
from ui.set_style import style_bc_st, style_bc_dk
from ui.set_text import famous_saying, coin_sell_var, coin_future_sell_var, coin_sell1, coin_sell2, coin_sell3, \
    coin_sell4, coin_sell5, coin_sell6, coin_sell7, coin_sell8, coin_sell_signal, coin_future_sell_signal, \
    coin_sell_var2, coin_future_sell_var2


def coin_sell_stg_load(ui):
    if ui.cs_textEditttt_02.isVisible():
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinsell').set_index('index')
        if len(df) > 0:
            ui.cvjs_comboBoxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvjs_comboBoxx_01.addItem(index)
                if i == 0:
                    ui.cvjs_lineEditt_01.setText(index)
            ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)


def coin_sell_stg_save(ui):
    strategy_name = ui.cvjs_lineEditt_01.text()
    strategy = ui.cs_textEditttt_02.toPlainText()
    strategy = ui.GetFixStrategy(strategy, '매도')

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(
                strategy):
            if ui.proc_query.is_alive():
                ui.queryQ.put(('전략디비', f"DELETE FROM coinsell WHERE `index` = '{strategy_name}'"))
                df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                ui.queryQ.put(('전략디비', df, 'coinsell', 'append'))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
            ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)


def coin_sell_factor(ui):
    ui.cs_textEditttt_02.clear()
    if ui.dict_set['거래소'] == '업비트':
        ui.cs_textEditttt_02.append(coin_sell_var if ui.dict_set['코인타임프레임'] else coin_sell_var2)
    else:
        ui.cs_textEditttt_02.append(coin_future_sell_var if ui.dict_set['코인타임프레임'] else coin_future_sell_var2)
    ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)


def coin_sell_stg_start(ui):
    strategy = ui.cs_textEditttt_02.toPlainText()
    if strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n')
    else:
        buttonReply = QMessageBox.question(
            ui, '전략시작', '매도전략의 연산을 시작합니다. 계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if ui.CoinStrategyProcessAlive():
                ui.cstgQ.put(('매도전략', strategy))
            ui.cvjs_pushButon_04.setStyleSheet(style_bc_dk)
            ui.cvjs_pushButon_14.setStyleSheet(style_bc_st)


def coin_sell_dead_line(ui):
    ui.cs_textEditttt_02.append(coin_sell1)


def coin_sell_profit_line(ui):
    ui.cs_textEditttt_02.append(coin_sell2)


def coin_sell_profit_save(ui):
    ui.cs_textEditttt_02.append(coin_sell3)


def coin_sell_hold_time(ui):
    ui.cs_textEditttt_02.append(coin_sell4)


def coin_sell_ch_avg_comparison(ui):
    ui.cs_textEditttt_02.append(coin_sell5)


def coin_sell_ch_high_comparison(ui):
    ui.cs_textEditttt_02.append(coin_sell6)


def coin_sell_low_high_avg_per(ui):
    ui.cs_textEditttt_02.append(coin_sell7)


def coin_sell_ask_price_ramain_count(ui):
    ui.cs_textEditttt_02.append(coin_sell8)


def coin_sell_signal_insert(ui):
    ui.cs_textEditttt_02.append(coin_sell_signal if ui.dict_set['거래소'] == '업비트' else coin_future_sell_signal)


def coin_sell_stg_stop(ui):
    if ui.CoinStrategyProcessAlive():
        ui.cstgQ.put('매도전략중지')
    ui.cvjs_pushButon_14.setStyleSheet(style_bc_dk)
    ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)
