
import random
from PyQt5.QtCore import Qt
from ui.set_style import style_bc_st, style_bc_dk
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator
from ui.set_text import famous_saying, sell_signal, future_sell_signal, sell_text


@error_decorator
def coin_sell_stg_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvjs_comboBoxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '매도전략이 선택되지 않았습니다.\n매도전략을 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'basic', 'sell', strategy_name)
    elif ui.cs_textEditttt_02.isVisible():
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


@error_decorator
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
        if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM coinsell WHERE `index` = '{strategy_name}'"
                insert_query  = 'INSERT INTO coinsell VALUES (?, ?)'
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)
                gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                stg_save_version(gubun, 'basic', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_sell_factor(ui):
    ui.cs_textEditttt_02.clear()
    ui.cs_textEditttt_02.append(sell_text if ui.dict_set['코인타임프레임'] else sell_text)
    ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)


@error_decorator
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


@error_decorator
def coin_sell_signal_insert(ui):
    ui.cs_textEditttt_02.append(sell_signal if ui.dict_set['거래소'] == '업비트' else future_sell_signal)


@error_decorator
def coin_sell_stg_stop(ui):
    if ui.CoinStrategyProcessAlive():
        ui.cstgQ.put('매도전략중지')
    ui.cvjs_pushButon_14.setStyleSheet(style_bc_dk)
    ui.cvjs_pushButon_04.setStyleSheet(style_bc_st)
