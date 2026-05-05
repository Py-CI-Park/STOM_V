
def sell_stg_load(ui):
    """매도 전략을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import Qt
    from ui.create_widget.set_style import style_bc_st
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from ui.event_click.button_clicked_strategy_version import strategy_version

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svjs_comboBoxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '매도전략이 선택되지 않았습니다.\n매도전략을 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'basic', 'sell', strategy_name)
    elif ui.ss_textEditttt_02.isVisible():
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_sell").set_index('index')
        if len(df) > 0:
            ui.svjs_comboBoxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svjs_comboBoxx_01.addItem(index)
                if i == 0:
                    ui.svjs_lineEditt_01.setText(index)
            ui.svjs_pushButon_04.setStyleSheet(style_bc_st)


def sell_stg_save(ui):
    """매도 전략을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtCore import Qt
    from ui.create_widget.set_style import style_bc_st
    from ui.create_widget.set_text import famous_saying
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from utility.static_method.static import text_not_in_special_characters
    from ui.event_click.button_clicked_varstext_change import get_fix_strategy
    from utility.static_method.strategy_version_manager import stg_save_version

    strategy_name = ui.svjs_lineEditt_01.text()
    strategy = ui.ss_textEditttt_02.toPlainText()
    strategy = get_fix_strategy(ui, strategy, '매도')

    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도전략의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if 'self.tickcols' in strategy or (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.ui_back_code_test1(strategy):
            if ui.proc_chqs.is_alive():
                insert_query  = f"INSERT OR REPLACE INTO {ui.market_info['전략구분']}_sell VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                ui.svjs_pushButon_04.setStyleSheet(style_bc_st)
                stg_save_version(ui.market_info['전략구분'], 'basic', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def sell_factor(ui):
    """매도 팩터를 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_style import style_bc_st
    from ui.create_widget.set_text import sell_text

    ui.ss_textEditttt_02.clear()
    ui.ss_textEditttt_02.append(sell_text if ui.dict_set['타임프레임'] else sell_text)
    ui.svjs_pushButon_04.setStyleSheet(style_bc_st)


def sell_stg_start(ui):
    """매도 전략 연산을 시작합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_style import style_bc_st, style_bc_dk

    strategy = ui.ss_textEditttt_02.toPlainText()
    if strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도전략의 코드가 공백 상태입니다.\n')
    else:
        buttonReply = QMessageBox.question(
            ui, '전략시작', '매도전략의 연산을 시작합니다. 계속하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            ui.wdzservQ.put(('strategy', ('매도전략', strategy)))
            ui.svjs_pushButon_04.setStyleSheet(style_bc_dk)
            ui.svjs_pushButon_14.setStyleSheet(style_bc_st)


def sell_signal_insert(ui):
    """매도 시그널을 삽입합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_text import sell_signal, sell_signal_future

    signal = sell_signal if ui.market_gubun < 6 else sell_signal_future
    ui.ss_textEditttt_02.append(signal)


def sell_stg_stop(ui):
    """매도 전략 연산을 중지합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_style import style_bc_st, style_bc_dk

    ui.wdzservQ.put(('strategy', '매도전략중지'))
    ui.svjs_pushButon_14.setStyleSheet(style_bc_dk)
    ui.svjs_pushButon_04.setStyleSheet(style_bc_st)
