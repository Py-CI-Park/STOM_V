
def gavars_load(ui):
    """GA 변수 범위를 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from ui.event_click.button_clicked_strategy_version import strategy_version

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.sva_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '최적화 GA범위가 선택되지 않았습니다.\n최적화 GA범위를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'opti', 'gavars', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optigavars").set_index('index')
        if len(df) > 0:
            ui.sva_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.sva_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.sva_lineEdittt_01.setText(index)


def gavars_save(ui):
    """GA 변수 범위를 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtCore import Qt
    from ui.create_widget.set_text import famous_saying
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from utility.static_method.static import text_not_in_special_characters
    from utility.static_method.strategy_version_manager import stg_save_version

    strategy_name = ui.sva_lineEdittt_01.text()
    strategy = ui.ss_textEditttt_06.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', 'GA범위의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if (QApplication.keyboardModifiers() & Qt.ControlModifier) or ui.ui_back_code_test2(strategy, ga=True):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_optigavars WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_optigavars VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(ui.market_info['전략구분'], 'opti', 'gavars', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def condbuy_load(ui):
    """조건 최적화 매수 전략을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from ui.event_click.button_clicked_strategy_version import strategy_version

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svo_comboBoxxx_01.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매수전략이 선택되지 않았습니다.\n조건최적화 매수전략를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'cond', 'buy', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_buyconds").set_index('index')
        if len(df) > 0:
            ui.svo_comboBoxxx_01.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svo_comboBoxxx_01.addItem(index)
                if i == 0:
                    ui.svo_lineEdittt_01.setText(index)


def condbuy_save(ui):
    """조건 최적화 매수 전략을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying
    from utility.static_method.static import text_not_in_special_characters
    from utility.static_method.strategy_version_manager import stg_save_version

    strategy_name = ui.svo_lineEdittt_01.text()
    strategy = ui.ss_textEditttt_07.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매수조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매수조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.ui_back_code_test3('매수', strategy):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_buyconds WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_buyconds VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(ui.market_info['전략구분'], 'cond', 'buy', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))


def condsell_load(ui):
    """조건 최적화 매도 전략을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from ui.event_click.button_clicked_strategy_version import strategy_version

    if QApplication.keyboardModifiers() & Qt.ControlModifier:
        strategy_name = ui.svo_comboBoxxx_02.currentText()
        if strategy_name == '':
            QMessageBox.critical(ui, '오류 알림', '조건최적화 매도전략이 선택되지 않았습니다.\n조건최적화 매도전략를 선택한 후에 재시도하십시오.\n')
            return
        strategy_version(ui, 'cond', 'sell', strategy_name)
    else:
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_sellconds").set_index('index')
        if len(df) > 0:
            ui.svo_comboBoxxx_02.clear()
            indexs = list(df.index)
            indexs.sort()
            for i, index in enumerate(indexs):
                ui.svo_comboBoxxx_02.addItem(index)
                if i == 0:
                    ui.svo_lineEdittt_02.setText(index)


def condsell_save(ui):
    """조건 최적화 매도 전략을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying
    from utility.static_method.static import text_not_in_special_characters
    from utility.static_method.strategy_version_manager import stg_save_version

    strategy_name = ui.svo_lineEdittt_02.text()
    strategy = ui.ss_textEditttt_08.toPlainText()
    if strategy_name == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n')
    elif not text_not_in_special_characters(strategy_name):
        QMessageBox.critical(ui, '오류 알림', '매도조건의 이름에 특문이 포함되어 있습니다.\n언더바(_)를 제외한 특문을 제거하십시오.\n')
    elif strategy == '':
        QMessageBox.critical(ui, '오류 알림', '매도조건의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n')
    else:
        if ui.ui_back_code_test3('매도', strategy):
            if ui.proc_chqs.is_alive():
                delete_query  = f"DELETE FROM {ui.market_info['전략구분']}_sellconds WHERE `index` = '{strategy_name}'"
                insert_query  = f"INSERT INTO {ui.market_info['전략구분']}_sellconds VALUES (?, ?)"
                insert_values = (strategy_name, strategy)
                ui.queryQ.put(('전략디비', delete_query))
                ui.queryQ.put(('전략디비', insert_query, insert_values))
                stg_save_version(ui.market_info['전략구분'], 'cond', 'sell', strategy_name, strategy)
                QMessageBox.information(ui, '저장 완료', random.choice(famous_saying))
