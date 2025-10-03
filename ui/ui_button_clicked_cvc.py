import random
import sqlite3
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.setting import DB_STRATEGY
from utility.static import text_not_in_special_characters
from ui.set_text import famous_saying, example_opti_vars, example_vars, example_buyconds, example_sellconds, \
    example_coin_buy, example_coin_future_buy, example_coin_sell, example_coin_future_sell, example_coinopti_buy1, \
    example_coinopti_future_buy1, example_coinopti_buy2, example_coinopti_future_buy2, example_coinopti_sell1, \
    example_coinopti_future_sell1, example_coinopti_sell2, example_coinopti_future_sell2, example_opti_future_vars, \
    example_future_vars, example_future_buyconds, example_future_sellconds, example_coinopti_buy3, \
    example_coinopti_future_buy3


def cvc_button_clicked_01(ui):
    if ui.cs_textEditttt_03.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM coinoptibuy', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.cvc_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_01.setText(index)


def cvc_button_clicked_02(ui):
    if ui.cs_textEditttt_03.isVisible():
        strategy_name = ui.cvc_lineEdittt_01.text()
        strategy = ui.cs_textEditttt_03.toPlainText()
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
                con = sqlite3.connect(DB_STRATEGY)
                df = pd.read_sql(f"SELECT * FROM coinoptibuy WHERE `index` = '{strategy_name}'", con)
                con.close()
                if ui.proc_query.is_alive():
                    if len(df) > 0:
                        query = f"UPDATE coinoptibuy SET 전략코드 = '{strategy}' WHERE `index` = '{strategy_name}'"
                        ui.queryQ.put(('전략디비', query))
                    else:
                        df = pd.DataFrame([[strategy, '']], columns=['전략코드', '변수값'], index=[strategy_name])
                        ui.queryQ.put(('전략디비', df, 'coinoptibuy', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def cvc_button_clicked_03(ui):
    if ui.cs_textEditttt_05.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM coinoptivars', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.cvc_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_02.setText(index)


def cvc_button_clicked_04(ui):
    if ui.cs_textEditttt_05.isVisible():
        strategy_name = ui.cvc_lineEdittt_02.text()
        strategy = ui.cs_textEditttt_05.toPlainText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy):
                if ui.proc_query.is_alive():
                    ui.queryQ.put(('전략디비', f"DELETE FROM coinoptivars WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, 'coinoptivars', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def cvc_button_clicked_05(ui):
    if ui.cs_textEditttt_04.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM coinoptisell', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.cvc_comboBoxxx_08.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_08.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_03.setText(index)


def cvc_button_clicked_06(ui):
    if ui.cs_textEditttt_04.isVisible():
        strategy_name = ui.cvc_lineEdittt_03.text()
        strategy = ui.cs_textEditttt_04.toPlainText()
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
                    ui.queryQ.put(('전략디비', f"DELETE FROM coinoptisell WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, 'coinoptisell', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def cvc_button_clicked_07(ui):
    if ui.cs_textEditttt_01.isVisible():
        ui.cs_textEditttt_01.clear()
        ui.cs_textEditttt_01.append(example_coin_buy if ui.dict_set['거래소'] == '업비트' else example_coin_future_buy)
    if ui.cs_textEditttt_02.isVisible():
        ui.cs_textEditttt_02.clear()
        ui.cs_textEditttt_02.append(example_coin_sell if ui.dict_set['거래소'] == '업비트' else example_coin_future_sell)
    if ui.cs_textEditttt_03.isVisible():
        ui.cs_textEditttt_03.clear()
        if ui.cvc_pushButton_24.isVisible():
            ui.cs_textEditttt_03.append(
                example_coinopti_buy1 if ui.dict_set['거래소'] == '업비트' else example_coinopti_future_buy1)
        else:
            if ui.dict_set['거래소'] == '업비트':
                ui.cs_textEditttt_03.append(example_coinopti_buy2 if ui.dict_set['코인타임프레임'] else example_coinopti_buy3)
            else:
                ui.cs_textEditttt_03.append(example_coinopti_future_buy2 if ui.dict_set['코인타임프레임'] else example_coinopti_future_buy3)
    if ui.cs_textEditttt_04.isVisible():
        ui.cs_textEditttt_04.clear()
        if ui.cvc_pushButton_24.isVisible():
            ui.cs_textEditttt_04.append(
                example_coinopti_sell1 if ui.dict_set['거래소'] == '업비트' else example_coinopti_future_sell1)
        else:
            ui.cs_textEditttt_04.append(
                example_coinopti_sell2 if ui.dict_set['거래소'] == '업비트' else example_coinopti_future_sell2)
    if ui.cs_textEditttt_05.isVisible():
        ui.cs_textEditttt_05.clear()
        ui.cs_textEditttt_05.append(example_opti_vars if ui.dict_set['거래소'] == '업비트' else example_opti_future_vars)
    if ui.cs_textEditttt_06.isVisible():
        ui.cs_textEditttt_06.clear()
        ui.cs_textEditttt_06.append(example_vars if ui.dict_set['거래소'] == '업비트' else example_future_vars)
    if ui.cs_textEditttt_07.isVisible():
        ui.cs_textEditttt_07.clear()
        ui.cs_textEditttt_07.append(example_buyconds if ui.dict_set['거래소'] == '업비트' else example_future_buyconds)
    if ui.cs_textEditttt_08.isVisible():
        ui.cs_textEditttt_08.clear()
        ui.cs_textEditttt_08.append(example_sellconds if ui.dict_set['거래소'] == '업비트' else example_future_sellconds)


def cvc_button_clicked_08(ui):
    tabl = 'coinoptivars' if not ui.cva_pushButton_01.isVisible() else 'coinvars'
    stgy = ui.cvc_comboBoxxx_01.currentText()
    opti = ui.cvc_comboBoxxx_02.currentText() if not ui.cva_pushButton_01.isVisible() else ui.cva_comboBoxxx_01.currentText()
    name = ui.cvc_lineEdittt_04.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매수전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    con = sqlite3.connect(DB_STRATEGY)
    df  = pd.read_sql('SELECT * FROM coinoptibuy', con).set_index('index')
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
        ui.queryQ.put(('전략디비', f"DELETE FROM coinbuy WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, 'coinbuy', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


def cvc_button_clicked_09(ui):
    tabl = 'coinoptivars' if not ui.cva_pushButton_01.isVisible() else 'coinvars'
    stgy = ui.cvc_comboBoxxx_08.currentText()
    opti = ui.cvc_comboBoxxx_02.currentText() if not ui.cva_pushButton_01.isVisible() else ui.cva_comboBoxxx_01.currentText()
    name = ui.cvc_lineEdittt_05.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매도전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    con = sqlite3.connect(DB_STRATEGY)
    df  = pd.read_sql('SELECT * FROM coinoptisell', con).set_index('index')
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
        ui.queryQ.put(('전략디비', f"DELETE FROM coinsell WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, 'coinsell', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


def cvc_button_clicked_10(ui):
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


def cvc_button_clicked_11(ui):
    if not ui.dialog_optuna.isVisible():
        if not ui.optuna_window_open:
            ui.op_lineEditttt_01.setText(ui.dict_set['옵튜나고정변수'])
            ui.op_lineEditttt_02.setText(str(ui.dict_set['옵튜나실행횟수']))
            ui.op_checkBoxxxx_01.setChecked(True) if ui.dict_set['옵튜나자동스탭'] else ui.op_checkBoxxxx_01.setChecked(False)
            ui.op_comboBoxxxx_01.setCurrentText(ui.dict_set['옵튜나샘플러'])
        ui.dialog_optuna.show()
        ui.optuna_window_open = True
    else:
        ui.dialog_optuna.close()
