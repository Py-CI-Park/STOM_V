import random
import sqlite3
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.set_text import famous_saying
from utility.setting import DB_STRATEGY
from utility.static import text_not_in_special_characters


def stock_gavars_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    con = sqlite3.connect(DB_STRATEGY)
    df = pd.read_sql(f'SELECT * FROM {gubun}vars', con).set_index('index')
    con.close()
    if len(df) > 0:
        ui.sva_comboBoxxx_01.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.sva_comboBoxxx_01.addItem(index)
            if i == 0:
                ui.sva_lineEdittt_01.setText(index)


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
            if ui.proc_query.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}vars WHERE `index` = '{strategy_name}'"))
                df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                ui.queryQ.put(('전략디비', df, f'{gubun}vars', 'append'))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def stock_condbuy_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    con = sqlite3.connect(DB_STRATEGY)
    df = pd.read_sql(f'SELECT * FROM {gubun}buyconds', con).set_index('index')
    con.close()
    if len(df) > 0:
        ui.svo_comboBoxxx_01.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.svo_comboBoxxx_01.addItem(index)
            if i == 0:
                ui.svo_lineEdittt_01.setText(index)


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
            if ui.proc_query.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}buyconds WHERE `index` = '{strategy_name}'"))
                df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                ui.queryQ.put(('전략디비', df, f'{gubun}buyconds', 'append'))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def stock_condsell_load(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    con = sqlite3.connect(DB_STRATEGY)
    df = pd.read_sql(f'SELECT * FROM {gubun}sellconds', con).set_index('index')
    con.close()
    if len(df) > 0:
        ui.svo_comboBoxxx_02.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.svo_comboBoxxx_02.addItem(index)
            if i == 0:
                ui.svo_lineEdittt_02.setText(index)


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
            if ui.proc_query.is_alive():
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}sellconds WHERE `index` = '{strategy_name}'"))
                df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                ui.queryQ.put(('전략디비', df, f'{gubun}sellconds', 'append'))
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
