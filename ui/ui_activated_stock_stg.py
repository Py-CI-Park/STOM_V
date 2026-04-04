
from PyQt5.QtWidgets import QMessageBox
from utility.static import error_decorator


@error_decorator
def sactivated_01(ui):
    strategy_name = ui.svjb_comboBoxx_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}buy WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_01.clear()
            ui.ss_textEditttt_01.append(df['전략코드'][strategy_name])
            ui.svjb_lineEditt_01.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'basic', 'buy', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_02(ui):
    strategy_name = ui.svjs_comboBoxx_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}sell WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_02.clear()
            ui.ss_textEditttt_02.append(df['전략코드'][strategy_name])
            ui.svjs_lineEditt_01.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'basic', 'sell', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_03(ui):
    strategy_name = ui.svc_comboBoxxx_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}optibuy WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_03.clear()
            ui.ss_textEditttt_03.append(df['전략코드'][strategy_name])
            ui.svc_lineEdittt_01.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'opti', 'buy', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_04(ui):
    strategy_name = ui.svc_comboBoxxx_02.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}optivars WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_05.clear()
            ui.ss_textEditttt_05.append(df['전략코드'][strategy_name])
            ui.svc_lineEdittt_02.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'opti', 'vars', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_05(ui):
    strategy_name = ui.svc_comboBoxxx_08.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}optisell WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_04.clear()
            ui.ss_textEditttt_04.append(df['전략코드'][strategy_name])
            ui.svc_lineEdittt_03.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'opti', 'sell', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_06(ui):
    strategy_name = ui.sva_comboBoxxx_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}vars WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_06.clear()
            ui.ss_textEditttt_06.append(df['전략코드'][strategy_name])
            ui.sva_lineEdittt_01.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'opti', 'gavars', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_07(ui):
    strategy_name = ui.svo_comboBoxxx_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}buyconds WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_07.clear()
            ui.ss_textEditttt_07.append(df['전략코드'][strategy_name])
            ui.svo_lineEdittt_01.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'cond', 'buy', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_08(ui):
    strategy_name = ui.svo_comboBoxxx_02.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}sellconds WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            ui.ss_textEditttt_08.clear()
            ui.ss_textEditttt_08.append(df['전략코드'][strategy_name])
            ui.svo_lineEdittt_02.setText(strategy_name)
            if ui.ss_pushButtonn_41.isVisible():
                ui.StrategyVersion(gubun, 'cond', 'sell', strategy_name)
        else:
            QMessageBox.critical(ui, '오류 알림', '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n')


@error_decorator
def sactivated_09(ui):
    strategy_name = ui.sj_stock_cbBox_01.currentText()
    if strategy_name:
        gubun = 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future'
        df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {gubun}optibuy WHERE `index` = '{strategy_name}'").set_index('index')
        if len(df) > 0:
            try:
                optivars = [float(i) if '.' in i else int(i) for i in df['변수값'][strategy_name].split(';')]
            except:
                optivars = ''
            QMessageBox.warning(
                ui, '경고',
                '최적화용 전략 선택시 최적값으로 전략이 실행됩니다.\n'
                '다음 변수값을 확인하십시오\n'
                f'{optivars}\n'
                f'매도전략 또한 반드시 최적화용 전략으로 변경하십시오.\n'
                f'최적화 백테스트를 실행할 경우 자동으로 변경됩니다.\n'
            )
