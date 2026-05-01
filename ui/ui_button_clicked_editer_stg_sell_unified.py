
import random
from PyQt5.QtCore import Qt
from ui.ui_vars_change import get_fix_strategy
from ui.set_style import style_bc_st, style_bc_dk
from ui.ui_strategy_version import strategy_version
from PyQt5.QtWidgets import QMessageBox, QApplication
from ui.ui_process_alive import coin_strategy_process_alive
from utility.strategy_version_manager import stg_save_version
from utility.static import text_not_in_special_characters, error_decorator
from ui.set_text import famous_saying, sell_signal, future_sell_signal, sell_text


# =============================================================================
# UI 타입별 설정 매핑 (STG SELL 에디터용)
# =============================================================================
UI_STG_SELL_EDITER_CONFIG = {
    'coin': {
        'widgets': {
            'combo': 'cvjs_comboBoxx_01',
            'line': 'cvjs_lineEditt_01',
            'text': 'cs_textEditttt_02',
            'push_04': 'cvjs_pushButon_04',
            'push_14': 'cvjs_pushButon_14',
        },
        'gubun_fn': lambda ui: 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance',
        'is_upbit_fn': lambda ui: '업비트' in ui.dict_set['거래소'],
        'tf_key': '코인타임프레임',
        'table': 'coinsell',
        'queue': 'cstgQ',
        'need_process_check': True,
        'signal_fn': lambda ui: sell_signal if '업비트' in ui.dict_set['거래소'] else future_sell_signal,
    },
    'stock': {
        'widgets': {
            'combo': 'svjs_comboBoxx_01',
            'line': 'svjs_lineEditt_01',
            'text': 'ss_textEditttt_02',
            'push_04': 'svjs_pushButon_04',
            'push_14': 'svjs_pushButon_14',
        },
        'gubun_fn': lambda ui: 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future',
        'is_stock_fn': lambda ui: '키움증권' in ui.dict_set['증권사'],
        'tf_key': '주식타임프레임',
        'table_fn': lambda gubun: f'{gubun}sell',
        'queue': 'wdzservQ',
        'need_process_check': False,
        'signal_fn': lambda ui: sell_signal if '키움증권' in ui.dict_set['증권사'] else future_sell_signal,
    }
}


def _get_widget(ui, ui_type, widget_key):
    """설정에서 위젯 객체를 가져옴"""
    # noinspection PyUnresolvedReferences
    widget_name = UI_STG_SELL_EDITER_CONFIG[ui_type]['widgets'][widget_key]
    return getattr(ui, widget_name)


def _get_gubun(ui, ui_type):
    """UI 타입에 따른 gubun 반환"""
    return UI_STG_SELL_EDITER_CONFIG[ui_type]['gubun_fn'](ui)


def _get_table_name(ui_type, gubun=None):
    """UI 타입에 따른 테이블명 반환"""
    config = UI_STG_SELL_EDITER_CONFIG[ui_type]
    if ui_type == 'coin':
        return config['table']
    else:
        return config['table_fn'](gubun)


def _get_queue(ui, ui_type):
    """UI 타입에 따른 큐 객체 반환"""
    queue_name = UI_STG_SELL_EDITER_CONFIG[ui_type]['queue']
    return getattr(ui, queue_name)


# =============================================================================
# 매도 전략 로드/저장 함수
# =============================================================================
@error_decorator
def sell_stg_load(ui, ui_type):
    """매도 전략 로드 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, gubun)
    combo_widget = _get_widget(ui, ui_type, 'combo')
    line_widget = _get_widget(ui, ui_type, 'line')
    text_widget = _get_widget(ui, ui_type, 'text')
    push_04 = _get_widget(ui, ui_type, 'push_04')

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = combo_widget.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '매도전략이 선택되지 않았습니다.\n매도전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, gubun, 'basic', 'sell', strategy_name)
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
            push_04.setStyleSheet(style_bc_st)


@error_decorator
def sell_stg_save(ui, ui_type):
    """매도 전략 저장 (코인/주식 공통)"""
    gubun = _get_gubun(ui, ui_type)
    table_name = _get_table_name(ui_type, gubun)
    line_widget = _get_widget(ui, ui_type, 'line')
    text_widget = _get_widget(ui, ui_type, 'text')
    push_04 = _get_widget(ui, ui_type, 'push_04')

    strategy_name = line_widget.text()
    strategy = text_widget.toPlainText()
    strategy = get_fix_strategy(ui, strategy, '매도')

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.BackCodeTest1(strategy):
            if ui.proc_chqs.is_alive():
                delete_query = f"DELETE FROM {table_name} WHERE `index` = '{strategy_name}'"
                insert_query = f"INSERT INTO {table_name} VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                push_04.setStyleSheet(style_bc_st)
                stg_save_version(gubun, 'basic', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


# =============================================================================
# 팩터 및 시그널 함수
# =============================================================================
@error_decorator
def sell_factor(ui, ui_type):
    """매도 팩터 템플릿 삽입 (코인/주식 공통)"""
    text_widget = _get_widget(ui, ui_type, 'text')
    push_04 = _get_widget(ui, ui_type, 'push_04')

    text_widget.clear()
    text_widget.append(sell_text)
    push_04.setStyleSheet(style_bc_st)


@error_decorator
def sell_signal_insert(ui, ui_type):
    """매도 시그널 삽입 (코인/주식 공통)"""
    config = UI_STG_SELL_EDITER_CONFIG[ui_type]
    text_widget = _get_widget(ui, ui_type, 'text')
    signal = config['signal_fn'](ui)
    text_widget.append(signal)


# =============================================================================
# 전략 시작/중지 함수
# =============================================================================
@error_decorator
def sell_stg_start(ui, ui_type):
    """매도 전략 시작 (코인/주식 공통)"""
    text_widget = _get_widget(ui, ui_type, 'text')
    push_04 = _get_widget(ui, ui_type, 'push_04')
    push_14 = _get_widget(ui, ui_type, 'push_14')
    queue = _get_queue(ui, ui_type)

    strategy = text_widget.toPlainText()
    if strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n')
    else:
        buttonReply = QMessageBox.question(
            ui, '전략시작', '매도전략의 연산을 시작합니다. 계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            if ui_type == 'coin':
                if coin_strategy_process_alive(ui):
                    queue.put(('매도전략', strategy))
            else:
                queue.put(('strategy', ('매도전략', strategy)))
            push_04.setStyleSheet(style_bc_dk)
            push_14.setStyleSheet(style_bc_st)


@error_decorator
def sell_stg_stop(ui, ui_type):
    """매도 전략 중지 (코인/주식 공통)"""
    push_04 = _get_widget(ui, ui_type, 'push_04')
    push_14 = _get_widget(ui, ui_type, 'push_14')
    queue = _get_queue(ui, ui_type)

    if ui_type == 'coin':
        if coin_strategy_process_alive(ui):
            queue.put('매도전략중지')
    else:
        queue.put(('strategy', '매도전략중지'))

    push_14.setStyleSheet(style_bc_dk)
    push_04.setStyleSheet(style_bc_st)
