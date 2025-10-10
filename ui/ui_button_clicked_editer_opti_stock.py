import random
import sqlite3
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.setting import DB_STRATEGY
from utility.static import text_not_in_special_characters
from ui.set_text import famous_saying, example_stock_buy, example_stock_sell, example_stockopti_buy1, \
    example_stockopti_buy2, example_stockopti_sell1, example_stockopti_sell2, example_opti_vars, example_vars, \
    example_buyconds, example_sellconds, example_stockopti_buy3, example_coin_future_buy, example_coin_future_sell, \
    example_coinopti_future_buy1, example_coinopti_future_buy3, example_coinopti_future_sell1, example_vars3, \
    example_future_buyconds, example_future_sellconds, example_opti_vars3, example_coinopti_future_sell3, \
    example_stockopti_sell3, example_coinopti_future_buy2, example_coinopti_future_sell2


def stock_opti_buy_load(ui):
    if ui.ss_textEditttt_03.isVisible():
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql(f'SELECT * FROM {gubun}optibuy', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_01.setText(index)


def stock_opti_buy_save(ui):
    if ui.ss_textEditttt_03.isVisible():
        strategy_name = ui.svc_lineEdittt_01.text()
        strategy = ui.ss_textEditttt_03.toPlainText()
        strategy = ui.GetFixStrategy(strategy, '매수')

        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if 'self.tickcols' in strategy or (
                    QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                con = sqlite3.connect(DB_STRATEGY)
                df = pd.read_sql(f"SELECT * FROM {gubun}optibuy WHERE `index` = '{strategy_name}'", con)
                con.close()
                if ui.proc_query.is_alive():
                    if len(df) > 0:
                        query = f"UPDATE {gubun}optibuy SET 전략코드 = '{strategy}' WHERE `index` = '{strategy_name}'"
                        ui.queryQ.put(('전략디비', query))
                    else:
                        df = pd.DataFrame([[strategy, '']], columns=['전략코드', '변수값'], index=[strategy_name])
                        ui.queryQ.put(('전략디비', df, f'{gubun}optibuy', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def stock_opti_vars_load(ui):
    if ui.ss_textEditttt_05.isVisible():
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql(f'SELECT * FROM {gubun}optivars', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_02.setText(index)


def stock_opti_vars_save(ui):
    if ui.ss_textEditttt_05.isVisible():
        strategy_name = ui.svc_lineEdittt_02.text()
        strategy = ui.ss_textEditttt_05.toPlainText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy):
                if ui.proc_query.is_alive():
                    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                    ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}optivars WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, f'{gubun}optivars', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def stock_opti_sell_load(ui):
    if ui.ss_textEditttt_04.isVisible():
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql(f'SELECT * FROM {gubun}optisell', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_08.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_08.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_03.setText(index)


def stock_opti_sell_save(ui):
    if ui.ss_textEditttt_04.isVisible():
        strategy_name = ui.svc_lineEdittt_03.text()
        strategy = ui.ss_textEditttt_04.toPlainText()
        strategy = ui.GetFixStrategy(strategy, '매도')

        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if 'self.tickcols' in strategy or (
                    QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                if ui.proc_query.is_alive():
                    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
                    ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}optisell WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, f'{gubun}optisell', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def stock_opti_sample(ui):
    if ui.ss_textEditttt_01.isVisible():
        ui.ss_textEditttt_01.clear()
        ui.ss_textEditttt_01.append(example_stock_buy if '키움증권' in ui.dict_set['증권사'] else example_coin_future_buy)
    if ui.ss_textEditttt_02.isVisible():
        ui.ss_textEditttt_02.clear()
        ui.ss_textEditttt_02.append(example_stock_sell if '키움증권' in ui.dict_set['증권사'] else example_coin_future_sell)
    if ui.ss_textEditttt_03.isVisible():
        ui.ss_textEditttt_03.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_03.append(example_stockopti_buy1 if '키움증권' in ui.dict_set['증권사'] else example_coinopti_future_buy1)
        else:
            if '키움증권' in ui.dict_set['증권사']:
                ui.ss_textEditttt_03.append(example_stockopti_buy2 if ui.dict_set['주식타임프레임'] else example_stockopti_buy3)
            else:
                ui.ss_textEditttt_03.append(example_coinopti_future_buy2 if ui.dict_set['주식타임프레임'] else example_coinopti_future_buy3)
    if ui.ss_textEditttt_04.isVisible():
        ui.ss_textEditttt_04.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_04.append(example_stockopti_sell1 if '키움증권' in ui.dict_set['증권사'] else example_coinopti_future_sell1)
        else:
            if '키움증권' in ui.dict_set['증권사']:
                ui.ss_textEditttt_04.append(example_stockopti_sell2 if ui.dict_set['주식타임프레임'] else example_stockopti_sell3)
            else:
                ui.ss_textEditttt_04.append(example_coinopti_future_sell2 if ui.dict_set['주식타임프레임'] else example_coinopti_future_sell3)
    if ui.ss_textEditttt_05.isVisible():
        ui.ss_textEditttt_05.clear()
        ui.ss_textEditttt_05.append(example_opti_vars if '키움증권' in ui.dict_set['증권사'] else example_opti_vars3)
    if ui.ss_textEditttt_06.isVisible():
        ui.ss_textEditttt_06.clear()
        ui.ss_textEditttt_06.append(example_vars if '키움증권' in ui.dict_set['증권사'] else example_vars3)
    if ui.ss_textEditttt_07.isVisible():
        ui.ss_textEditttt_07.clear()
        ui.ss_textEditttt_07.append(example_buyconds if '키움증권' in ui.dict_set['증권사'] else example_future_buyconds)
    if ui.ss_textEditttt_08.isVisible():
        ui.ss_textEditttt_08.clear()
        ui.ss_textEditttt_08.append(example_sellconds if '키움증권' in ui.dict_set['증권사'] else example_future_sellconds)


def stock_opti_to_buy_save(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    tabl = f'{gubun}optivars' if not ui.sva_pushButton_01.isVisible() else f'{gubun}vars'
    stgy = ui.svc_comboBoxxx_01.currentText()
    opti = ui.svc_comboBoxxx_02.currentText() if not ui.sva_pushButton_01.isVisible() else ui.sva_comboBoxxx_01.currentText()
    name = ui.svc_lineEdittt_04.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매수전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    con = sqlite3.connect(DB_STRATEGY)
    df  = pd.read_sql(f'SELECT * FROM {gubun}optibuy', con).set_index('index')
    stg = df['전략코드'][stgy]
    df  = pd.read_sql(f'SELECT * FROM "{tabl}"', con).set_index('index')
    opt = df['전략코드'][opti]
    con.close()

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except Exception as e:
        QMessageBox.critical(ui, '오류 알림', f'{e}')
        return

    if ui.proc_query.is_alive():
        ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}buy WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, f'{gubun}buy', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


def stock_opti_to_sell_save(ui):
    gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
    tabl = f'{gubun}optivars' if not ui.sva_pushButton_01.isVisible() else f'{gubun}vars'
    stgy = ui.svc_comboBoxxx_08.currentText()
    opti = ui.svc_comboBoxxx_02.currentText() if not ui.sva_pushButton_01.isVisible() else ui.sva_comboBoxxx_01.currentText()
    name = ui.svc_lineEdittt_05.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매도전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    con = sqlite3.connect(DB_STRATEGY)
    df  = pd.read_sql(f'SELECT * FROM {gubun}optisell', con).set_index('index')
    stg = df['전략코드'][stgy]
    df  = pd.read_sql(f'SELECT * FROM "{tabl}"', con).set_index('index')
    opt = df['전략코드'][opti]
    con.close()

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except Exception as e:
        QMessageBox.critical(ui, '오류 알림', f'{e}')
        return

    if ui.proc_query.is_alive():
        ui.queryQ.put(('전략디비', f"DELETE FROM {gubun}sell WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, f'{gubun}sell', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


def stock_opti_std(ui):
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


def stock_opti_optuna(ui):
    if not ui.dialog_optuna.isVisible():
        if not ui.optuna_window_open:
            ui.op_lineEditttt_01.setText(ui.dict_set['옵튜나고정변수'])
            ui.op_lineEditttt_02.setText(str(ui.dict_set['옵튜나실행횟수']))
            ui.op_checkBoxxxx_01.setChecked(True) if ui.dict_set['옵튜나자동스탭'] else ui.op_checkBoxxxx_01.setChecked(
                False)
            ui.op_comboBoxxxx_01.setCurrentText(ui.dict_set['옵튜나샘플러'])
        ui.dialog_optuna.show()
        ui.optuna_window_open = True
    else:
        ui.dialog_optuna.close()
