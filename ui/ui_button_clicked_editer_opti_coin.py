
import random
from PyQt5.QtCore import Qt
from traceback import format_exc
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator
from ui.set_text import famous_saying, example_opti_vars, example_vars, example_buyconds, example_sellconds, \
    example_coin_buy, example_coin_future_buy, example_coin_sell, example_coin_future_sell, example_coinopti_buy1, \
    example_coinopti_future_buy1, example_coinopti_buy2, example_coinopti_future_buy2, example_coinopti_sell1, \
    example_coinopti_future_sell1, example_coinopti_sell2, example_coinopti_future_sell2, example_opti_vars2, \
    example_vars2, example_future_buyconds, example_future_sellconds, example_coinopti_buy3, example_vars3, \
    example_coinopti_future_buy3, example_coinopti_sell3, example_coinopti_future_sell3, example_opti_vars3


@error_decorator
def coin_opti_buy_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvc_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략이 선택되지 않았습니다.\n최적화 매수전략을 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'opti', 'buy', strategy_name)
    elif ui.cs_textEditttt_03.isVisible():
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptibuy').set_index('index')
        if len(df) > 0:
            ui.cvc_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_01.setText(index)


@error_decorator
def coin_opti_buy_save(ui):
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
            if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                if ui.proc_chqs.is_alive():
                    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM coinoptibuy WHERE `index` = '{strategy_name}'")
                    if len(df) > 0:
                        update_query  = 'UPDATE coinoptibuy SET 전략코드 = ? WHERE `index` = ?'
                        update_vlaues = (strategy, strategy_name)
                        ui.queryQ.put(('전략디비', update_query, update_vlaues))
                    else:
                        insert_query  = 'INSERT INTO coinoptibuy VALUES (?, ?, ?)'
                        insert_vlaues = (strategy_name, strategy, '')
                        ui.queryQ.put(('전략디비', insert_query, insert_vlaues))
                    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                    stg_save_version(gubun, 'opti', 'buy', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_opti_vars_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvc_comboBoxxx_02.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 범위가 선택되지 않았습니다.\n최적화 범위를 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'opti', 'vars', strategy_name)
    elif ui.cs_textEditttt_05.isVisible():
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptivars').set_index('index')
        if len(df) > 0:
            ui.cvc_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_02.setText(index)


@error_decorator
def coin_opti_vars_save(ui):
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
                if ui.proc_chqs.is_alive():
                    delete_query  = f"DELETE FROM coinoptivars WHERE `index` = '{strategy_name}'"
                    insert_query  = 'INSERT INTO coinoptivars VALUES (?, ?)'
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                    stg_save_version(gubun, 'opti', 'vars', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_opti_sell_load(ui):
    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.cvc_comboBoxxx_08.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략이 선택되지 않았습니다.\n최적화 매도전략을 선택한 후에 재시도하십시오.\n')
            return
        ui.StrategyVersion(gubun, 'opti', 'sell', strategy_name)
    elif ui.cs_textEditttt_04.isVisible():
        df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptisell').set_index('index')
        if len(df) > 0:
            ui.cvc_comboBoxxx_08.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.cvc_comboBoxxx_08.addItem(index)
                if i == 0:
                    ui.cvc_lineEdittt_03.setText(index)


@error_decorator
def coin_opti_sell_save(ui):
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
            if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                if ui.proc_chqs.is_alive():
                    delete_query  = f"DELETE FROM coinoptisell WHERE `index` = '{strategy_name}'"
                    insert_query  = 'INSERT INTO coinoptisell VALUES (?, ?)'
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    gubun = 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance'
                    stg_save_version(gubun, 'opti', 'sell', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


@error_decorator
def coin_opti_sample(ui):
    if ui.cs_textEditttt_01.isVisible():
        ui.cs_textEditttt_01.clear()
        ui.cs_textEditttt_01.append(example_coin_buy if ui.dict_set['거래소'] == '업비트' else example_coin_future_buy)
    if ui.cs_textEditttt_02.isVisible():
        ui.cs_textEditttt_02.clear()
        ui.cs_textEditttt_02.append(example_coin_sell if ui.dict_set['거래소'] == '업비트' else example_coin_future_sell)
    if ui.cs_textEditttt_03.isVisible():
        ui.cs_textEditttt_03.clear()
        if ui.cvc_pushButton_24.isVisible():
            ui.cs_textEditttt_03.append(example_coinopti_buy1 if ui.dict_set['거래소'] == '업비트' else example_coinopti_future_buy1)
        else:
            if ui.dict_set['거래소'] == '업비트':
                ui.cs_textEditttt_03.append(example_coinopti_buy2 if ui.dict_set['코인타임프레임'] else example_coinopti_buy3)
            else:
                ui.cs_textEditttt_03.append(example_coinopti_future_buy2 if ui.dict_set['코인타임프레임'] else example_coinopti_future_buy3)
    if ui.cs_textEditttt_04.isVisible():
        ui.cs_textEditttt_04.clear()
        if ui.cvc_pushButton_24.isVisible():
            ui.cs_textEditttt_04.append(example_coinopti_sell1 if ui.dict_set['거래소'] == '업비트' else example_coinopti_future_sell1)
        else:
            if ui.dict_set['거래소'] == '업비트':
                ui.cs_textEditttt_04.append(example_coinopti_sell2 if ui.dict_set['코인타임프레임'] else example_coinopti_sell3)
            else:
                ui.cs_textEditttt_04.append(example_coinopti_future_sell2 if ui.dict_set['코인타임프레임'] else example_coinopti_future_sell3)
    if ui.cs_textEditttt_05.isVisible():
        ui.cs_textEditttt_05.clear()
        if ui.dict_set['거래소'] == '업비트':
            ui.cs_textEditttt_05.append(example_opti_vars)
        else:
            ui.cs_textEditttt_05.append(example_opti_vars2 if ui.dict_set['코인타임프레임'] else example_opti_vars3)
    if ui.cs_textEditttt_06.isVisible():
        ui.cs_textEditttt_06.clear()
        if ui.dict_set['거래소'] == '업비트':
            ui.cs_textEditttt_06.append(example_vars)
        else:
            ui.cs_textEditttt_06.append(example_vars2 if ui.dict_set['코인타임프레임'] else example_vars3)
    if ui.cs_textEditttt_07.isVisible():
        ui.cs_textEditttt_07.clear()
        ui.cs_textEditttt_07.append(example_buyconds if ui.dict_set['거래소'] == '업비트' else example_future_buyconds)
    if ui.cs_textEditttt_08.isVisible():
        ui.cs_textEditttt_08.clear()
        ui.cs_textEditttt_08.append(example_sellconds if ui.dict_set['거래소'] == '업비트' else example_future_sellconds)


@error_decorator
def coin_opti_to_buy_save(ui):
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

    df  = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptibuy').set_index('index')
    stg = df['전략코드'][stgy]
    df  = ui.dbreader.read_sql('전략디비', f'SELECT * FROM "{tabl}"').set_index('index')
    opt = df['전략코드'][opti]

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except:
        QMessageBox.critical(ui, '오류 알림', format_exc())
        return

    if ui.proc_chqs.is_alive():
        delete_query  = f"DELETE FROM coinbuy WHERE `index` = '{name}'"
        insert_query  = 'INSERT INTO coinbuy VALUES (?, ?)'
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


@error_decorator
def coin_opti_to_sell_save(ui):
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

    df  = ui.dbreader.read_sql('전략디비', 'SELECT * FROM coinoptisell').set_index('index')
    stg = df['전략코드'][stgy]
    df  = ui.dbreader.read_sql('전략디비', f'SELECT * FROM "{tabl}"').set_index('index')
    opt = df['전략코드'][opti]

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except:
        QMessageBox.critical(ui, '오류 알림', format_exc())
        return

    if ui.proc_chqs.is_alive():
        delete_query  = f"DELETE FROM coinsell WHERE `index` = '{name}'"
        insert_query  = 'INSERT INTO coinsell VALUES (?, ?)'
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


@error_decorator
def coin_opti_std(ui):
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


@error_decorator
def coin_opti_optuna(ui):
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
