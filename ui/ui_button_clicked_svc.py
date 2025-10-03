import random
import sqlite3
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.setting import DB_STRATEGY
from utility.static import text_not_in_special_characters
from ui.set_text import famous_saying, example_stock_buy, example_stock_sell, example_stockopti_buy1, \
    example_stockopti_buy2, example_stockopti_sell1, example_stockopti_sell2, example_opti_vars, example_vars, \
    example_buyconds, example_sellconds, example_stockopti_buy3


def svc_button_clicked_01(ui):
    if ui.ss_textEditttt_03.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM stockoptibuy', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_01.setText(index)


def svc_button_clicked_02(ui):
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
                con = sqlite3.connect(DB_STRATEGY)
                df = pd.read_sql(f"SELECT * FROM stockoptibuy WHERE `index` = '{strategy_name}'", con)
                con.close()
                if ui.proc_query.is_alive():
                    if len(df) > 0:
                        query = f"UPDATE stockoptibuy SET 전략코드 = '{strategy}' WHERE `index` = '{strategy_name}'"
                        ui.queryQ.put(('전략디비', query))
                    else:
                        df = pd.DataFrame([[strategy, '']], columns=['전략코드', '변수값'], index=[strategy_name])
                        ui.queryQ.put(('전략디비', df, 'stockoptibuy', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def svc_button_clicked_03(ui):
    if ui.ss_textEditttt_05.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM stockoptivars', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_02.setText(index)


def svc_button_clicked_04(ui):
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
                    ui.queryQ.put(('전략디비', f"DELETE FROM stockoptivars WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, 'stockoptivars', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def svc_button_clicked_05(ui):
    if ui.ss_textEditttt_04.isVisible():
        con = sqlite3.connect(DB_STRATEGY)
        df = pd.read_sql('SELECT * FROM stockoptisell', con).set_index('index')
        con.close()
        if len(df) > 0:
            ui.svc_comboBoxxx_08.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_08.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_03.setText(index)


def svc_button_clicked_06(ui):
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
                    ui.queryQ.put(('전략디비', f"DELETE FROM stockoptisell WHERE `index` = '{strategy_name}'"))
                    df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
                    ui.queryQ.put(('전략디비', df, 'stockoptisell', 'append'))
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def svc_button_clicked_07(ui):
    if ui.ss_textEditttt_01.isVisible():
        ui.ss_textEditttt_01.clear()
        ui.ss_textEditttt_01.append(example_stock_buy)
    if ui.ss_textEditttt_02.isVisible():
        ui.ss_textEditttt_02.clear()
        ui.ss_textEditttt_02.append(example_stock_sell)
    if ui.ss_textEditttt_03.isVisible():
        ui.ss_textEditttt_03.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_03.append(example_stockopti_buy1)
        else:
            ui.ss_textEditttt_03.append(example_stockopti_buy2 if ui.dict_set['주식타임프레임'] else example_stockopti_buy3)
    if ui.ss_textEditttt_04.isVisible():
        ui.ss_textEditttt_04.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_04.append(example_stockopti_sell1)
        else:
            ui.ss_textEditttt_04.append(example_stockopti_sell2)
    if ui.ss_textEditttt_05.isVisible():
        ui.ss_textEditttt_05.clear()
        ui.ss_textEditttt_05.append(example_opti_vars)
    if ui.ss_textEditttt_06.isVisible():
        ui.ss_textEditttt_06.clear()
        ui.ss_textEditttt_06.append(example_vars)
    if ui.ss_textEditttt_07.isVisible():
        ui.ss_textEditttt_07.clear()
        ui.ss_textEditttt_07.append(example_buyconds)
    if ui.ss_textEditttt_08.isVisible():
        ui.ss_textEditttt_08.clear()
        ui.ss_textEditttt_08.append(example_sellconds)


def svc_button_clicked_08(ui):
    tabl = 'stockoptivars' if not ui.sva_pushButton_01.isVisible() else 'stockvars'
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
    df  = pd.read_sql('SELECT * FROM stockoptibuy', con).set_index('index')
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
        ui.queryQ.put(('전략디비', f"DELETE FROM stockbuy WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, 'stockbuy', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


def svc_button_clicked_09(ui):
    tabl = 'stockoptivars' if not ui.sva_pushButton_01.isVisible() else 'stockvars'
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
    df  = pd.read_sql('SELECT * FROM stockoptisell', con).set_index('index')
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
        ui.queryQ.put(('전략디비', f"DELETE FROM stocksell WHERE `index` = '{name}'"))
        df = pd.DataFrame({'전략코드': [stg]}, index=[name])
        ui.queryQ.put(('전략디비', df, 'stocksell', 'append'))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


def svc_button_clicked_10(ui):
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


def svc_button_clicked_11(ui):
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
