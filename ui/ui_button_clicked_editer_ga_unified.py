
import random
from PyQt5.QtCore import Qt
from ui.set_text import famous_saying
from ui.ui_strategy_version import strategy_version
from PyQt5.QtWidgets import QMessageBox, QApplication
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator


# =============================================================================
# UI 타입별 설정 매핑 (GA 에디터용)
# =============================================================================
UI_GA_EDITER_CONFIG = {
    'coin': {
        'widgets': {
            'gavars_combo': 'cva_comboBoxxx_01',
            'gavars_line': 'cva_lineEdittt_01',
            'gavars_text': 'cs_textEditttt_06',
            'condbuy_combo': 'cvo_comboBoxxx_01',
            'condbuy_line': 'cvo_lineEdittt_01',
            'condbuy_text': 'cs_textEditttt_07',
            'condsell_combo': 'cvo_comboBoxxx_02',
            'condsell_line': 'cvo_lineEdittt_02',
            'condsell_text': 'cs_textEditttt_08',
        },
        'gubun_fn': lambda ui: 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance',
        'tables': {
            'gavars': 'coinvars',
            'condbuy': 'coinbuyconds',
            'condsell': 'coinsellconds',
        }
    },
    'stock': {
        'widgets': {
            'gavars_combo': 'sva_comboBoxxx_01',
            'gavars_line': 'sva_lineEdittt_01',
            'gavars_text': 'ss_textEditttt_06',
            'condbuy_combo': 'svo_comboBoxxx_01',
            'condbuy_line': 'svo_lineEdittt_01',
            'condbuy_text': 'ss_textEditttt_07',
            'condsell_combo': 'svo_comboBoxxx_02',
            'condsell_line': 'svo_lineEdittt_02',
            'condsell_text': 'ss_textEditttt_08',
        },
        'gubun_fn': lambda ui: 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future',
        'tables_fn': lambda gubun: {
            'gavars': f'{gubun}vars',
            'condbuy': f'{gubun}buyconds',
            'condsell': f'{gubun}sellconds',
        }
    }
}


def _get_widget(ui, ui_type, widget_key):
    """설정에서 위젯 객체를 가져옴"""
    # noinspection PyUnresolvedReferences
    widget_name = UI_GA_EDITER_CONFIG[ui_type]['widgets'][widget_key]
    return getattr(ui, widget_name)


def _get_gubun(ui, ui_type):
    """UI 타입에 따른 gubun 반환"""
    return UI_GA_EDITER_CONFIG[ui_type]['gubun_fn'](ui)


def _get_table_name(ui_type, table_type, gubun=None):
    """UI 타입과 테이블 타입에 따른 테이블명 반환"""
    config = UI_GA_EDITER_CONFIG[ui_type]
    if ui_type == 'coin':
        return config['tables'][table_type]
    else:
        return config['tables_fn'](gubun)[table_type]


# =============================================================================
# GA 변수 관련 함수
# =============================================================================
@error_decorator
def gavars_load(ui, ui_type):
    """GA 변수 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'gavars', gubun)
    combo_widget = _get_widget(ui, ui_type, 'gavars_combo')
    line_widget = _get_widget(ui, ui_type, 'gavars_line')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 GA범위가 선택되지 않았습니다.\n최적화 GA범위를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'opti', 'gavars', strategy_name)
    else:
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
def gavars_save(ui, ui_type):
    """GA 변수 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'gavars', gubun)
    line_widget = _get_widget(ui, ui_type, 'gavars_line')
    text_widget = _get_widget(ui, ui_type, 'gavars_text')

    strategy_name = line_widget.text()
    strategy = text_widget.toPlainText()

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest2(strategy, ga=True):
            if ui.proc_chqs.is_alive():
                delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(gubun, 'opti', 'gavars', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 조건 매수 관련 함수
# =============================================================================
@error_decorator
def condbuy_load(ui, ui_type):
    """조건 매수 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'condbuy', gubun)
    combo_widget = _get_widget(ui, ui_type, 'condbuy_combo')
    line_widget = _get_widget(ui, ui_type, 'condbuy_line')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매수전략이 선택되지 않았습니다.\n조건최적화 매수전략를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'cond', 'buy', strategy_name)
    else:
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
def condbuy_save(ui, ui_type):
    """조건 매수 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'condbuy', gubun)
    line_widget = _get_widget(ui, ui_type, 'condbuy_line')
    text_widget = _get_widget(ui, ui_type, 'condbuy_text')

    strategy_name = line_widget.text()
    strategy = text_widget.toPlainText()

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매수', strategy):
            if ui.proc_chqs.is_alive():
                delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(gubun, 'cond', 'buy', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 조건 매도 관련 함수
# =============================================================================
@error_decorator
def condsell_load(ui, ui_type):
    """조건 매도 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'condsell', gubun)
    combo_widget = _get_widget(ui, ui_type, 'condsell_combo')
    line_widget = _get_widget(ui, ui_type, 'condsell_line')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매도전략이 선택되지 않았습니다.\n조건최적화 매도전략를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'cond', 'sell', strategy_name)
    else:
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
def condsell_save(ui, ui_type):
    """조건 매도 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, 'condsell', gubun)
    line_widget = _get_widget(ui, ui_type, 'condsell_line')
    text_widget = _get_widget(ui, ui_type, 'condsell_text')

    strategy_name = line_widget.text()
    strategy = text_widget.toPlainText()

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.BackCodeTest3('매도', strategy):
            if ui.proc_chqs.is_alive():
                delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(gubun, 'cond', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
