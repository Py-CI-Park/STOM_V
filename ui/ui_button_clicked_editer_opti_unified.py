
import random
from ui.set_text import *
from PyQt5.QtCore import Qt
from traceback import format_exc
from ui.ui_vars_change import get_fix_strategy
from ui.ui_strategy_version import strategy_version
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator


# =============================================================================
# UI 타입별 설정 매핑 (OPTI 에디터용)
# =============================================================================
UI_OPTI_EDITER_CONFIG = {
    'coin': {
        'widgets': {
            'optibuy_combo': 'cvc_comboBoxxx_01',
            'optibuy_line': 'cvc_lineEdittt_01',
            'optibuy_text': 'cs_textEditttt_03',
            'optivars_combo': 'cvc_comboBoxxx_02',
            'optivars_line': 'cvc_lineEdittt_02',
            'optivars_text': 'cs_textEditttt_05',
            'optisell_combo': 'cvc_comboBoxxx_08',
            'optisell_line': 'cvc_lineEdittt_03',
            'optisell_text': 'cs_textEditttt_04',
            'gavars_combo': 'cva_comboBoxxx_01',
            'opti_line_04': 'cvc_lineEdittt_04',
            'opti_line_05': 'cvc_lineEdittt_05',
            'push_24': 'cvc_pushButton_24',
            # 샘플용 텍스트 위젯들
            'text_01': 'cs_textEditttt_01',
            'text_02': 'cs_textEditttt_02',
            'text_03': 'cs_textEditttt_03',
            'text_04': 'cs_textEditttt_04',
            'text_05': 'cs_textEditttt_05',
            'text_06': 'cs_textEditttt_06',
            'text_07': 'cs_textEditttt_07',
            'text_08': 'cs_textEditttt_08',
        },
        'gubun_fn': lambda ui: 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance',
        'is_upbit_fn': lambda ui: '업비트' in ui.dict_set['거래소'],
        'tf_key': '코인타임프레임',
        'tables': {
            'optibuy': 'coinoptibuy',
            'optivars': 'coinoptivars',
            'optisell': 'coinoptisell',
            'buy': 'coinbuy',
            'sell': 'coinsell',
            'gavars': 'coinvars',
        }
    },
    'stock': {
        'widgets': {
            'optibuy_combo': 'svc_comboBoxxx_01',
            'optibuy_line': 'svc_lineEdittt_01',
            'optibuy_text': 'ss_textEditttt_03',
            'optivars_combo': 'svc_comboBoxxx_02',
            'optivars_line': 'svc_lineEdittt_02',
            'optivars_text': 'ss_textEditttt_05',
            'optisell_combo': 'svc_comboBoxxx_08',
            'optisell_line': 'svc_lineEdittt_03',
            'optisell_text': 'ss_textEditttt_04',
            'gavars_combo': 'sva_comboBoxxx_01',
            'opti_line_04': 'svc_lineEdittt_04',
            'opti_line_05': 'svc_lineEdittt_05',
            'push_24': 'svc_pushButton_24',
            # 샘플용 텍스트 위젯들
            'text_01': 'ss_textEditttt_01',
            'text_02': 'ss_textEditttt_02',
            'text_03': 'ss_textEditttt_03',
            'text_04': 'ss_textEditttt_04',
            'text_05': 'ss_textEditttt_05',
            'text_06': 'ss_textEditttt_06',
            'text_07': 'ss_textEditttt_07',
            'text_08': 'ss_textEditttt_08',
        },
        'gubun_fn': lambda ui: 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future',
        'is_stock_fn': lambda ui: '키움증권' in ui.dict_set['증권사'],
        'tf_key': '주식타임프레임',
        'tables_fn': lambda gubun: {
            'optibuy': f'{gubun}optibuy',
            'optivars': f'{gubun}optivars',
            'optisell': f'{gubun}optisell',
            'buy': f'{gubun}buy',
            'sell': f'{gubun}sell',
            'gavars': f'{gubun}vars',
        }
    }
}


def _get_widget(ui, ui_type, widget_key):
    """설정에서 위젯 객체를 가져옴"""
    # noinspection PyUnresolvedReferences
    widget_name = UI_OPTI_EDITER_CONFIG[ui_type]['widgets'][widget_key]
    return getattr(ui, widget_name)


def _get_gubun(ui, ui_type):
    """UI 타입에 따른 gubun 반환"""
    return UI_OPTI_EDITER_CONFIG[ui_type]['gubun_fn'](ui)


def _get_table_name(ui_type, table_type, gubun=None):
    """UI 타입과 테이블 타입에 따른 테이블명 반환"""
    config = UI_OPTI_EDITER_CONFIG[ui_type]
    if ui_type == 'coin':
        return config['tables'][table_type]
    else:
        return config['tables_fn'](gubun)[table_type]


# =============================================================================
# 최적화 매수 관련 함수
# =============================================================================
@error_decorator
def opti_buy_load(ui, ui_type):
    """최적화 매수 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optibuy', gubun)
    combo_widget = _get_widget(ui, ui_type, 'optibuy_combo')
    line_widget = _get_widget(ui, ui_type, 'optibuy_line')
    text_widget = _get_widget(ui, ui_type, 'optibuy_text')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매수전략이 선택되지 않았습니다.\n최적화 매수전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'opti', 'buy', strategy_name)
    elif text_widget.isVisible():
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {table_name}').set_index('index')
        if len(df) > 0:
            combo_widget.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                combo_widget.addItem(index)
                if i == 0:
                    line_widget.setText(index)


@error_decorator
def opti_buy_save(ui, ui_type):
    """최적화 매수 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optibuy', gubun)
    line_widget = _get_widget(ui, ui_type, 'optibuy_line')
    text_widget = _get_widget(ui, ui_type, 'optibuy_text')

    if text_widget.isVisible():
        strategy_name = line_widget.text()
        strategy = text_widget.toPlainText()
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
                    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {table_name} WHERE `index` = '{strategy_name}'")
                    if len(df) > 0:
                        update_query = f'UPDATE {table_name} SET 전략코드 = ? WHERE `index` = ?'
                        update_vlaues = (strategy, strategy_name)
                        ui.queryQ.put(('전략디비', update_query, update_vlaues))
                    else:
                        insert_query = f'INSERT INTO {table_name} VALUES (?, ?, ?)'
                        insert_vlaues = (strategy_name, strategy, '')
                        ui.queryQ.put(('전략디비', insert_query, insert_vlaues))
                    stg_save_version(gubun, 'opti', 'buy', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 최적화 변수 관련 함수
# =============================================================================
@error_decorator
def opti_vars_load(ui, ui_type):
    """최적화 변수 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optivars', gubun)
    combo_widget = _get_widget(ui, ui_type, 'optivars_combo')
    line_widget = _get_widget(ui, ui_type, 'optivars_line')
    text_widget = _get_widget(ui, ui_type, 'optivars_text')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 범위가 선택되지 않았습니다.\n최적화 범위를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'opti', 'vars', strategy_name)
    elif text_widget.isVisible():
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {table_name}').set_index('index')
        if len(df) > 0:
            combo_widget.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                combo_widget.addItem(index)
                if i == 0:
                    line_widget.setText(index)


@error_decorator
def opti_vars_save(ui, ui_type):
    """최적화 변수 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optivars', gubun)
    line_widget = _get_widget(ui, ui_type, 'optivars_line')
    text_widget = _get_widget(ui, ui_type, 'optivars_text')

    if text_widget.isVisible():
        strategy_name = line_widget.text()
        strategy = text_widget.toPlainText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
        elif not text_not_in_special_characters(strategy_name):
            QMessageBox.critical(ui, '오류 알림', '변수범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        elif strategy == '':
            QMessageBox.critical(ui, '오류 알림', '변수범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
        else:
            if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy):
                if ui.proc_chqs.is_alive():
                    delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                    insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    stg_save_version(gubun, 'opti', 'vars', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 최적화 매도 관련 함수
# =============================================================================
@error_decorator
def opti_sell_load(ui, ui_type):
    """최적화 매도 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optisell', gubun)
    combo_widget = _get_widget(ui, ui_type, 'optisell_combo')
    line_widget = _get_widget(ui, ui_type, 'optisell_line')
    text_widget = _get_widget(ui, ui_type, 'optisell_text')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 매도전략이 선택되지 않았습니다.\n최적화 매도전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'opti', 'sell', strategy_name)
    elif text_widget.isVisible():
        df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {table_name}').set_index('index')
        if len(df) > 0:
            combo_widget.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                combo_widget.addItem(index)
                if i == 0:
                    line_widget.setText(index)


@error_decorator
def opti_sell_save(ui, ui_type):
    """최적화 매도 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'optisell', gubun)
    line_widget = _get_widget(ui, ui_type, 'optisell_line')
    text_widget = _get_widget(ui, ui_type, 'optisell_text')

    if text_widget.isVisible():
        strategy_name = line_widget.text()
        strategy = text_widget.toPlainText()
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
                    delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                    insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                    insert_values = (strategy_name, strategy)
                    ui.queryQ.put(('전략디비', delete_query))
                    ui.queryQ.put(('전략디비', insert_query, insert_values))
                    stg_save_version(gubun, 'opti', 'sell', strategy_name, strategy)
                    QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 샘플 예제 로드 함수
# =============================================================================
@error_decorator
def opti_sample(ui, ui_type):
    """샘플 예제 로드 (코인/주식 공통)"""
    config = UI_OPTI_EDITER_CONFIG[ui_type]
    text_01 = _get_widget(ui, ui_type, 'text_01')
    text_02 = _get_widget(ui, ui_type, 'text_02')
    text_03 = _get_widget(ui, ui_type, 'text_03')
    text_04 = _get_widget(ui, ui_type, 'text_04')
    text_05 = _get_widget(ui, ui_type, 'text_05')
    text_06 = _get_widget(ui, ui_type, 'text_06')
    text_07 = _get_widget(ui, ui_type, 'text_07')
    text_08 = _get_widget(ui, ui_type, 'text_08')
    push_24 = _get_widget(ui, ui_type, 'push_24')

    if ui_type == 'coin':
        is_upbit = config['is_upbit_fn'](ui)
        tf_key = config['tf_key']

        if text_01.isVisible():
            text_01.clear()
            text_01.append(example_coin_buy if is_upbit else example_coin_future_buy)
        if text_02.isVisible():
            text_02.clear()
            text_02.append(example_coin_sell if is_upbit else example_coin_future_sell)
        if text_03.isVisible():
            text_03.clear()
            if push_24.isVisible():
                text_03.append(example_coinopti_buy1 if is_upbit else example_coinopti_future_buy1)
            else:
                if is_upbit:
                    text_03.append(example_coinopti_buy2 if ui.dict_set[tf_key] else example_coinopti_buy3)
                else:
                    text_03.append(example_coinopti_future_buy2 if ui.dict_set[tf_key] else example_coinopti_future_buy3)
        if text_04.isVisible():
            text_04.clear()
            if push_24.isVisible():
                text_04.append(example_coinopti_sell1 if is_upbit else example_coinopti_future_sell1)
            else:
                if is_upbit:
                    text_04.append(example_coinopti_sell2 if ui.dict_set[tf_key] else example_coinopti_sell3)
                else:
                    text_04.append(example_coinopti_future_sell2 if ui.dict_set[tf_key] else example_coinopti_future_sell3)
        if text_05.isVisible():
            text_05.clear()
            if is_upbit:
                text_05.append(example_opti_vars)
            else:
                text_05.append(example_opti_vars2 if ui.dict_set[tf_key] else example_opti_vars3)
        if text_06.isVisible():
            text_06.clear()
            if is_upbit:
                text_06.append(example_vars)
            else:
                text_06.append(example_vars2 if ui.dict_set[tf_key] else example_vars3)
        if text_07.isVisible():
            text_07.clear()
            text_07.append(example_buyconds if is_upbit else example_future_buyconds)
        if text_08.isVisible():
            text_08.clear()
            text_08.append(example_sellconds if is_upbit else example_future_sellconds)
    else:
        is_stock = config['is_stock_fn'](ui)
        tf_key = config['tf_key']

        if text_01.isVisible():
            text_01.clear()
            text_01.append(example_stock_buy if is_stock else example_coin_future_buy)
        if text_02.isVisible():
            text_02.clear()
            text_02.append(example_stock_sell if is_stock else example_coin_future_sell)
        if text_03.isVisible():
            text_03.clear()
            if push_24.isVisible():
                text_03.append(example_stockopti_buy1 if is_stock else example_coinopti_future_buy1)
            else:
                if is_stock:
                    text_03.append(example_stockopti_buy2 if ui.dict_set[tf_key] else example_stockopti_buy3)
                else:
                    text_03.append(example_coinopti_future_buy2 if ui.dict_set[tf_key] else example_coinopti_future_buy3)
        if text_04.isVisible():
            text_04.clear()
            if push_24.isVisible():
                text_04.append(example_stockopti_sell1 if is_stock else example_coinopti_future_sell1)
            else:
                if is_stock:
                    text_04.append(example_stockopti_sell2 if ui.dict_set[tf_key] else example_stockopti_sell3)
                else:
                    text_04.append(example_coinopti_future_sell2 if ui.dict_set[tf_key] else example_coinopti_future_sell3)
        if text_05.isVisible():
            text_05.clear()
            text_05.append(example_opti_vars if is_stock else example_opti_vars3)
        if text_06.isVisible():
            text_06.clear()
            text_06.append(example_vars if is_stock else example_vars3)
        if text_07.isVisible():
            text_07.clear()
            text_07.append(example_buyconds if is_stock else example_future_buyconds)
        if text_08.isVisible():
            text_08.clear()
            text_08.append(example_sellconds if is_stock else example_future_sellconds)


# =============================================================================
# 최적화 결과를 실전략으로 저장 함수
# =============================================================================
@error_decorator
def opti_to_buy_save(ui, ui_type):
    """최적화 결과를 매수 실전략으로 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    gavars_table = _get_table_name(ui_type, 'gavars', gubun)
    optivars_table = _get_table_name(ui_type, 'optivars', gubun)
    optibuy_table = _get_table_name(ui_type, 'optibuy', gubun)
    buy_table = _get_table_name(ui_type, 'buy', gubun)

    optibuy_combo = _get_widget(ui, ui_type, 'optibuy_combo')
    optivars_combo = _get_widget(ui, ui_type, 'optivars_combo')
    gavars_combo = _get_widget(ui, ui_type, 'gavars_combo')
    line_04 = _get_widget(ui, ui_type, 'opti_line_04')

    tabl = optivars_table if not _get_widget(ui, ui_type, 'push_24').isVisible() else gavars_table
    stgy = optibuy_combo.currentText()
    opti = optivars_combo.currentText() if not _get_widget(ui, ui_type, 'push_24').isVisible() else gavars_combo.currentText()
    name = line_04.text()

    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매수전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매수전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {optibuy_table}').set_index('index')
    stg = df['전략코드'][stgy]
    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM "{tabl}"').set_index('index')
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
        delete_query = f"DELETE FROM {buy_table} WHERE `index` = '{name}'"
        insert_query = f"INSERT INTO {buy_table} VALUES (?, ?)"
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매수전략을 저장하였습니다.\n')


@error_decorator
def opti_to_sell_save(ui, ui_type):
    """최적화 결과를 매도 실전략으로 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    gavars_table = _get_table_name(ui_type, 'gavars', gubun)
    optivars_table = _get_table_name(ui_type, 'optivars', gubun)
    optisell_table = _get_table_name(ui_type, 'optisell', gubun)
    sell_table = _get_table_name(ui_type, 'sell', gubun)

    optisell_combo = _get_widget(ui, ui_type, 'optisell_combo')
    optivars_combo = _get_widget(ui, ui_type, 'optivars_combo')
    gavars_combo = _get_widget(ui, ui_type, 'gavars_combo')
    line_05 = _get_widget(ui, ui_type, 'opti_line_05')

    tabl = optivars_table if not _get_widget(ui, ui_type, 'push_24').isVisible() else gavars_table
    stgy = optisell_combo.currentText()
    opti = optivars_combo.currentText() if not _get_widget(ui, ui_type, 'push_24').isVisible() else gavars_combo.currentText()
    name = line_05.text()

    if stgy == '' or opti == '' or name == '':
        QMessageBox.critical(ui, '오류 알림', '전략 및 범위 코드를 선택하거나\n매도전략의 이름을 입력하십시오.\n')
        return
    elif not text_not_in_special_characters(name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
        return

    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM {optisell_table}').set_index('index')
    stg = df['전략코드'][stgy]
    df = ui.dbreader.read_sql('전략디비', f'SELECT * FROM "{tabl}"').set_index('index')
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
        delete_query = f"DELETE FROM {sell_table} WHERE `index` = '{name}'"
        insert_query = f"INSERT INTO {sell_table} VALUES (?, ?)"
        insert_values = (name, stg)
        ui.queryQ.put(('전략디비', delete_query))
        ui.queryQ.put(('전략디비', insert_query, insert_values))
        QMessageBox.information(ui, '저장 알림', '최적값으로 매도전략을 저장하였습니다.\n')


# =============================================================================
# 기타 유틸리티 함수
# =============================================================================
@error_decorator
def opti_std(ui):
    """표준편차 다이얼로그 토글 (코인/주식 공통)"""
    ui.dialog_std.show() if not ui.dialog_std.isVisible() else ui.dialog_std.close()


@error_decorator
def opti_optuna(ui):
    """Optuna 다이얼로그 토글 (코인/주식 공통)"""
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
