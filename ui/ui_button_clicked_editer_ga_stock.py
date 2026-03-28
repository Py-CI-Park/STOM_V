
import random
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.set_text import famous_saying
from utility.static import text_not_in_special_characters, error_decorator


@error_decorator
def stock_gavars_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}vars').set_index('index')
    if len(df) > 0:
        ui.sva_comboBoxxx_01.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.sva_comboBoxxx_01.addItem(index)
            if i == 0:
                ui.sva_lineEdittt_01.setText(index)


@error_decorator
def stock_gavars_save(ui):
    strategy_name = ui.sva_lineEdittt_01.text()
    strategy = ui.ss_textEditttt_06.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy, ga=True):
            if ui.proc_chqs.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                delete_query  = f"DELETE FROM {gubun}vars WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {gubun}vars VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def stock_condbuy_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}buyconds').set_index('index')
    if len(df) > 0:
        ui.svo_comboBoxxx_01.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.svo_comboBoxxx_01.addItem(index)
            if i == 0:
                ui.svo_lineEdittt_01.setText(index)


@error_decorator
def stock_condbuy_save(ui):
    strategy_name = ui.svo_lineEdittt_01.text()
    strategy = ui.ss_textEditttt_07.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매수', strategy):
            if ui.proc_chqs.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                delete_query  = f"DELETE FROM {gubun}buyconds WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {gubun}buyconds VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def stock_condsell_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {gubun}sellconds').set_index('index')
    if len(df) > 0:
        ui.svo_comboBoxxx_02.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.svo_comboBoxxx_02.addItem(index)
            if i == 0:
                ui.svo_lineEdittt_02.setText(index)


@error_decorator
def stock_condsell_save(ui):
    strategy_name = ui.svo_lineEdittt_02.text()
    strategy = ui.ss_textEditttt_08.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매도', strategy):
            if ui.proc_chqs.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                delete_query  = f"DELETE FROM {gubun}sellconds WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {gubun}sellconds VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
