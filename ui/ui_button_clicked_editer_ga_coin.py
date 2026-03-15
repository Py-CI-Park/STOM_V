
import random
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.set_text import famous_saying
from utility.static import text_not_in_special_characters, error_decorator


@error_decorator
def coin_gavars_load(ui):
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
            if ui.proc_query.is_alive():
                delete_query = f"DELETE FROM coinvars WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO coinvars (`index`, 전략코드) VALUES ('{strategy_name}', '{strategy}')"
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_condbuy_load(ui):
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
            if ui.proc_query.is_alive():
                delete_query = f"DELETE FROM coinbuyconds WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO coinbuyconds (`index`, 전략코드) VALUES ('{strategy_name}', '{strategy}')"
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_condsell_load(ui):
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
            if ui.proc_query.is_alive():
                delete_query = f"DELETE FROM coinsellconds WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO coinsellconds (`index`, 전략코드) VALUES ('{strategy_name}', '{strategy}')"
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
