
import random
from PyQt5.QtCore import Qt
from ui.set_text import famous_saying
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator


@error_decorator
def coin_gavars_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cva_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 GA범위가 선택되지 않았습니다.\n최적화 GA범위를 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'opti', 'gavars', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinvars').set_index('index')
        if len(df) > 0:
            ui.cva_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cva_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.cva_lineEdittt_01.setText(index)


@error_decorator
def coin_gavars_save(ui):
    strategy_name = ui.cva_lineEdittt_01.text()
    strategy = ui.cs_textEditttt_06.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy, ga=True):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM coinvars WHERE `index` = '{strategy_name}'"
                insert_query  = 'INSERT INTO coinvars VALUES (?, ?)'
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                stg_save_version(gubun, 'opti', 'gavars', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_condbuy_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvo_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매수전략이 선택되지 않았습니다.\n조건최적화 매수전략를 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'cond', 'buy', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinbuyconds').set_index('index')
        if len(df) > 0:
            ui.cvo_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvo_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.cvo_lineEdittt_01.setText(index)


@error_decorator
def coin_condbuy_save(ui):
    strategy_name = ui.cvo_lineEdittt_01.text()
    strategy = ui.cs_textEditttt_07.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매수', strategy):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM coinbuyconds WHERE `index` = '{strategy_name}'"
                insert_query  = 'INSERT INTO coinbuyconds VALUES (?, ?)'
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                stg_save_version(gubun, 'cond', 'buy', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_condsell_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvo_comboBoxxx_02.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매도전략이 선택되지 않았습니다.\n조건최적화 매도전략를 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'cond', 'sell', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinsellconds').set_index('index')
        if len(df) > 0:
            ui.cvo_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvo_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.cvo_lineEdittt_02.setText(index)


@error_decorator
def coin_condsell_save(ui):
    strategy_name = ui.cvo_lineEdittt_02.text()
    strategy = ui.cs_textEditttt_08.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매도', strategy):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM coinsellconds WHERE `index` = '{strategy_name}'"
                insert_query  = 'INSERT INTO coinsellconds VALUES (?, ?)'
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                stg_save_version(gubun, 'cond', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
