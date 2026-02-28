
import random
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.static import text_not_in_special_characters
from ui.set_style import style_bc_st, style_bc_dk
from ui.set_text import famous_saying, buy_text_tick, buy_signal, future_buy_signal, buy_text_min


def coin_buy_stg_load(ui):
    if ui.cs_textEditttt_01.isVisible():
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinbuy').set_index('index')
        if len(df) > 0:
            ui.cvjb_comboBoxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvjb_comboBoxx_01.addItem(index)
                if i == 0:
                    ui.cvjb_lineEditt_01.setText(index)
            ui.cvjb_pushButon_04.setStyleSheet(style_bc_st)


def coin_buy_stg_save(ui):
    strategy_name = ui.cvjb_lineEditt_01.text()
    strategy = ui.cs_textEditttt_01.toPlainText()
    if 'self.tickcols' not in strategy:
        strategy = ui.GetFixStrategy(strategy, '매수')

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(
                strategy):
            if ui.proc_query.is_alive():
                ui.queryQ.put(('전략디비', f"DELETE FROM coinbuy WHERE `index` = '{strategy_name}'"))
                df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                ui.queryQ.put(('전략디비', df, 'coinbuy', 'append'))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
            ui.cvjb_pushButon_04.setStyleSheet(style_bc_st)


def coin_buy_factor(ui):
    ui.cs_textEditttt_01.clear()
    ui.cs_textEditttt_01.append(buy_text_tick if ui.dict_set['코인타임프레임'] else buy_text_min)
    ui.cvjb_pushButon_04.setStyleSheet(style_bc_st)


def coin_buy_stg_start(ui):
    strategy = ui.cs_textEditttt_01.toPlainText()
    if strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수전략의 코드가 공백 상태입니다.\n')
    else:
        buttonReply = QMessageBox.question(
            ui, '전략시작', '매수전략의 연산을 시작합니다. 계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if ui.CoinStrategyProcessAlive():
                ui.cstgQ.put(('매수전략', strategy))
            ui.cvjb_pushButon_04.setStyleSheet(style_bc_dk)
            ui.cvjb_pushButon_12.setStyleSheet(style_bc_st)


def coin_buy_signal_insert(ui):
    ui.cs_textEditttt_01.append(buy_signal if ui.dict_set['거래소'] == '업비트' else future_buy_signal)


def coin_buy_stg_stop(ui):
    if ui.CoinStrategyProcessAlive():
        ui.cstgQ.put('매수전략중지')
    ui.cvjb_pushButon_12.setStyleSheet(style_bc_dk)
    ui.cvjb_pushButon_04.setStyleSheet(style_bc_st)
