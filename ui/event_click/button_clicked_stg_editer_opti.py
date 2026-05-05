
import random
from PyQt5.QtCore import Qt
from traceback import format_exc
from ui.create_widget.set_text import *
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.static_method.static import text_not_in_special_characters
from ui.event_click.button_clicked_varstext_change import get_fix_strategy
from ui.event_click.button_clicked_strategy_version import strategy_version
from utility.static_method.strategy_version_manager import stg_save_version


def opti_buy_load(ui):
    """최적화 매수 전략을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svc_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략이 선택되지 않았습니다.\n최적화 매수전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'opti', 'buy', strategy_name)
    elif ui.ss_textEditttt_03.isVisible():
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optibuy").set_index('index')
        if len(df) > 0:
            ui.svc_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_01.setText(index)


def opti_buy_save(ui):
    """최적화 매수 전략을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.ss_textEditttt_03.isVisible():
        strategy_name = ui.svc_lineEdittt_01.text()
        strategy = ui.ss_textEditttt_03.toPlainText()
        strategy = get_fix_strategy(ui, strategy, '매수')

        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                if ui.proc_chqs.is_alive():
                    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optibuy WHERE `index` = '{strategy_name}'")
                    if len(df) > 0:
                        update_query  = f"UPDATE {ui.market_info['전략구분']}_optibuy SET 전략코드 = ? WHERE `index` = ?"
                        update_vlaues = (strategy, strategy_name)
                        ui.queryQ.put(('전략디비', update_query, update_vlaues))
                    else:
                        insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_optibuy VALUES (?, ?, ?)"
                        insert_vlaues = (strategy_name, strategy, '')
                        ui.queryQ.put(('전략디비', insert_query, insert_vlaues))
                    stg_save_version(ui.market_info['전략구분'], 'opti', 'buy', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def opti_vars_load(ui):
    """최적화 변수 범위를 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svc_comboBoxxx_02.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 범위가 선택되지 않았습니다.\n최적화 범위를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'opti', 'vars', strategy_name)
    elif ui.ss_textEditttt_05.isVisible():
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optivars").set_index('index')
        if len(df) > 0:
            ui.svc_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_02.setText(index)


def opti_vars_save(ui):
    """최적화 변수 범위를 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
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
                if ui.proc_chqs.is_alive():
                    delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_optivars WHERE `index` = '{strategy_name}'"
                    insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_optivars VALUES (?, ?)"
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    stg_save_version(ui.market_info['전략구분'], 'opti', 'vars', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def opti_sell_load(ui):
    """최적화 매도 전략을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svc_comboBoxxx_08.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략이 선택되지 않았습니다.\n최적화 매도전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'opti', 'sell', strategy_name)
    elif ui.ss_textEditttt_04.isVisible():
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optisell").set_index('index')
        if len(df) > 0:
            ui.svc_comboBoxxx_08.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svc_comboBoxxx_08.addItem(index)
                if i == 0:
                    ui.svc_lineEdittt_03.setText(index)


def opti_sell_save(ui):
    """최적화 매도 전략을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.ss_textEditttt_04.isVisible():
        strategy_name = ui.svc_lineEdittt_03.text()
        strategy = ui.ss_textEditttt_04.toPlainText()
        strategy = get_fix_strategy(ui, strategy, '매도')

        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
                if ui.proc_chqs.is_alive():
                    delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_optisell WHERE `index` = '{strategy_name}'"
                    insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_optisell VALUES (?, ?)"
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    stg_save_version(ui.market_info['전략구분'], 'opti', 'sell', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def opti_sample(ui):
    """최적화 샘플을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    if ui.ss_textEditttt_01.isVisible():
        ui.ss_textEditttt_01.clear()
        ui.ss_textEditttt_01.append(example_stg_buy if ui.market_gubun < 6 else example_stg_buy_future)

    if ui.ss_textEditttt_02.isVisible():
        ui.ss_textEditttt_02.clear()
        ui.ss_textEditttt_02.append(example_stg_sell if ui.market_gubun < 6 else example_stg_sell_future)

    if ui.ss_textEditttt_03.isVisible():
        ui.ss_textEditttt_03.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_03.append(example_stg_buy_vchange if ui.market_gubun < 6 else example_stg_buy_vchange_future)
        else:
            if ui.market_gubun < 6:
                ui.ss_textEditttt_03.append(example_stg_optibuy if ui.dict_set['타임프레임'] else example_stg_optibuy_min)
            else:
                ui.ss_textEditttt_03.append(example_stg_optibuy_future if ui.dict_set['타임프레임'] else example_stg_optibuy_future_min)

    if ui.ss_textEditttt_04.isVisible():
        ui.ss_textEditttt_04.clear()
        if ui.svc_pushButton_24.isVisible():
            ui.ss_textEditttt_04.append(example_stg_sell_vchange if ui.market_gubun < 6 else example_stg_sell_vchange_future)
        else:
            if ui.market_gubun < 6:
                ui.ss_textEditttt_04.append(example_stg_optisell if ui.dict_set['타임프레임'] else example_stg_optisell_min)
            else:
                ui.ss_textEditttt_04.append(example_stg_optisell_future if ui.dict_set['타임프레임'] else example_stg_optisell_future_min)

    if ui.ss_textEditttt_05.isVisible():
        ui.ss_textEditttt_05.clear()
        if ui.market_gubun < 6:
            ui.ss_textEditttt_05.append(example_opti_vars if ui.dict_set['타임프레임'] else example_opti_vars_min)
        else:
            ui.ss_textEditttt_05.append(example_opti_vars_future if ui.dict_set['타임프레임'] else example_opti_vars_future_min)

    if ui.ss_textEditttt_06.isVisible():
        ui.ss_textEditttt_06.clear()
        if ui.market_gubun < 6:
            ui.ss_textEditttt_06.append(example_gavars if ui.dict_set['타임프레임'] else example_gavars_min)
        else:
            ui.ss_textEditttt_06.append(example_gavars_future if ui.dict_set['타임프레임'] else example_gavars_future_min)

    if ui.ss_textEditttt_07.isVisible():
        ui.ss_textEditttt_07.clear()
        ui.ss_textEditttt_07.append(example_buyconds if ui.market_gubun < 6 else example_buyconds_future)

    if ui.ss_textEditttt_08.isVisible():
        ui.ss_textEditttt_08.clear()
        ui.ss_textEditttt_08.append(example_sellconds if ui.market_gubun < 6 else example_sellconds_future)


def opti_to_buy_save(ui):
    """최적화 매수 전략을 매수 전략으로 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    tabl = f"{ui.market_info['전략구분']}_optivars" if not ui.sva_pushButton_01.isVisible() else f"{ui.market_info['전략구분']}_optigavars"
    stgy = ui.svc_comboBoxxx_01.currentText()
    opti = ui.svc_comboBoxxx_02.currentText() if not ui.sva_pushButton_01.isVisible() else ui.sva_comboBoxxx_01.currentText()
    name = ui.svc_lineEdittt_04.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매수전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    df  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optibuy").set_index('index')
    stg = df['전략코드'][stgy]
    df  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM '{tabl}'").set_index('index')
    opt = df['전략코드'][opti]

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except Exception:
        QMessageBox.critical(ui, '오류 알림', format_exc())
        return

    if ui.proc_chqs.is_alive():
        delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_buy WHERE `index` = '{name}'"
        insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_buy VALUES (?, ?)"
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


def opti_to_sell_save(ui):
    """최적화 매도 전략을 매도 전략으로 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    tabl = f"{ui.market_info['전략구분']}_optivars" if not ui.sva_pushButton_01.isVisible() else f"{ui.market_info['전략구분']}_optigavars"
    stgy = ui.svc_comboBoxxx_08.currentText()
    opti = ui.svc_comboBoxxx_02.currentText() if not ui.sva_pushButton_01.isVisible() else ui.sva_comboBoxxx_01.currentText()
    name = ui.svc_lineEdittt_05.text()
    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매도전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    df  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optisell").set_index('index')
    stg = df['전략코드'][stgy]
    df  = ui.dbreader.read_sql('전략디비', f"SELECT * FROM '{tabl}'").set_index('index')
    opt = df['전략코드'][opti]

    try:
        vars_ = {}
        opt = opt.replace('self.vars', 'vars_')
        exec(compile(opt, '<string>', 'exec'))
        for i in range(len(vars_)):
            stg = stg.replace(f'self.vars[{i}]', f'{vars_[i][1]}')
    except Exception:
        QMessageBox.critical(ui, '오류 알림', format_exc())
        return

    if ui.proc_chqs.is_alive():
        delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_sell WHERE `index` = '{name}'"
        insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_sell VALUES (?, ?)"
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


def show_opti_std(ui):
    """최적화 기준 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


def show_opti_optuna(ui):
    """옵튜나 다이얼로그를 토글합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
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
