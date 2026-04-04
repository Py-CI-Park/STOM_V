
from PyQt5.QtWidgets import QMessageBox
from utility.static import error_decorator
from ui.ui_strategy_version import strategy_version


# UI 타입별 설정 매핑
UI_CONFIG = {
    'coin': {
        'gubun_fn': lambda ui: 'upbit' if '업비트' in ui.dict_set['거래소'] else 'binance',
        'tables': [
            'coinbuy', 'coinsell', 'coinoptibuy', 'coinoptivars',
            'coinoptisell', 'coinvars', 'coinbuyconds', 'coinsellconds'
        ],
        'widgets': {
            'text_01': 'cs_textEditttt_01', 'text_02': 'cs_textEditttt_02',
            'text_03': 'cs_textEditttt_03', 'text_04': 'cs_textEditttt_05',
            'text_05': 'cs_textEditttt_04', 'text_06': 'cs_textEditttt_06',
            'text_07': 'cs_textEditttt_07', 'text_08': 'cs_textEditttt_08',
            'combo_01': 'cvjb_comboBoxx_01', 'line_01': 'cvjb_lineEditt_01',
            'combo_02': 'cvjs_comboBoxx_01', 'line_02': 'cvjs_lineEditt_01',
            'combo_03': 'cvc_comboBoxxx_01', 'line_03': 'cvc_lineEdittt_01',
            'combo_04': 'cvc_comboBoxxx_02', 'line_04': 'cvc_lineEdittt_02',
            'combo_05': 'cvc_comboBoxxx_08', 'line_05': 'cvc_lineEdittt_03',
            'combo_06': 'cva_comboBoxxx_01', 'line_06': 'cva_lineEdittt_01',
            'combo_07': 'cvo_comboBoxxx_01', 'line_07': 'cvo_lineEdittt_01',
            'combo_08': 'cvo_comboBoxxx_02', 'line_08': 'cvo_lineEdittt_02',
            'combo_09': 'sj_coin_comBox_01',
            'push_41': 'cs_pushButtonn_41',
        },
        'types': ['basic', 'basic', 'opti', 'opti', 'opti', 'opti', 'cond', 'cond'],
        'buysell': ['buy', 'sell', 'buy', 'vars', 'sell', 'gavars', 'buy', 'sell'],
        'errors': [
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n',
            '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n',
            '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n'
        ]
    },
    'stock': {
        'gubun_fn': lambda ui: 'stock' if '키움증권' in ui.dict_set['증권사'] else 'future',
        'tables': [
            '{gubun}buy', '{gubun}sell', '{gubun}optibuy', '{gubun}optivars',
            '{gubun}optisell', '{gubun}vars', '{gubun}buyconds', '{gubun}sellconds'
        ],
        'widgets': {
            'text_01': 'ss_textEditttt_01', 'text_02': 'ss_textEditttt_02',
            'text_03': 'ss_textEditttt_03', 'text_04': 'ss_textEditttt_05',
            'text_05': 'ss_textEditttt_04', 'text_06': 'ss_textEditttt_06',
            'text_07': 'ss_textEditttt_07', 'text_08': 'ss_textEditttt_08',
            'combo_01': 'svjb_comboBoxx_01', 'line_01': 'svjb_lineEditt_01',
            'combo_02': 'svjs_comboBoxx_01', 'line_02': 'svjs_lineEditt_01',
            'combo_03': 'svc_comboBoxxx_01', 'line_03': 'svc_lineEdittt_01',
            'combo_04': 'svc_comboBoxxx_02', 'line_04': 'svc_lineEdittt_02',
            'combo_05': 'svc_comboBoxxx_08', 'line_05': 'svc_lineEdittt_03',
            'combo_06': 'sva_comboBoxxx_01', 'line_06': 'sva_lineEdittt_01',
            'combo_07': 'svo_comboBoxxx_01', 'line_07': 'svo_lineEdittt_01',
            'combo_08': 'svo_comboBoxxx_02', 'line_08': 'svo_lineEdittt_02',
            'combo_09': 'sj_stock_cbBox_01',
            'push_41': 'ss_pushButtonn_41',
        },
        'types': ['basic', 'basic', 'opti', 'opti', 'opti', 'opti', 'cond', 'cond'],
        'buysell': ['buy', 'sell', 'buy', 'vars', 'sell', 'gavars', 'buy', 'sell'],
        'errors': [
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n',
            '전략이 DB에 존재하지 않습니다.\n전략을 다시 로딩하십시오.\n',
            '범위가 DB에 존재하지 않습니다.\n범위을 다시 로딩하십시오.\n',
            '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n',
            '조건이 DB에 존재하지 않습니다.\n조건을 다시 로딩하십시오.\n'
        ]
    }
}


# noinspection PyUnresolvedReferences
def _activated_common(ui, ui_type, idx):
    """공통 activated 로직"""
    config = UI_CONFIG[ui_type]
    widgets = config['widgets']
    table = config['tables'][idx - 1]
    
    combo_name = f'combo_{idx:02d}'
    line_name = f'line_{idx:02d}'
    text_name = f'text_{idx:02d}'
    
    strategy_name = getattr(ui, widgets[combo_name]).currentText()
    
    if not strategy_name:
        return
    
    # gubun 계산 (stock/future 또는 upbit/binance)
    gubun = config['gubun_fn'](ui)

    # 테이블명 동적 치환 (stock의 경우)
    if '{' in table:
        table = table.format(gubun=gubun)
    
    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {table} WHERE `index` = '{strategy_name}'").set_index('index')
    
    if len(df) > 0:
        getattr(ui, widgets[text_name]).clear()
        getattr(ui, widgets[text_name]).append(df['전략코드'][strategy_name])
        getattr(ui, widgets[line_name]).setText(strategy_name)
        
        if getattr(ui, widgets['push_41']).isVisible():
            stg_type = config['types'][idx - 1]
            buysell = config['buysell'][idx - 1]
            strategy_version(ui, gubun, stg_type, buysell, strategy_name)
    else:
        QMessageBox.critical(ui, '오류 알림', config['errors'][idx - 1])


@error_decorator
def activated_01(ui, ui_type):
    _activated_common(ui, ui_type, 1)


@error_decorator
def activated_02(ui, ui_type):
    _activated_common(ui, ui_type, 2)


@error_decorator
def activated_03(ui, ui_type):
    _activated_common(ui, ui_type, 3)


@error_decorator
def activated_04(ui, ui_type):
    _activated_common(ui, ui_type, 4)


@error_decorator
def activated_05(ui, ui_type):
    _activated_common(ui, ui_type, 5)


@error_decorator
def activated_06(ui, ui_type):
    _activated_common(ui, ui_type, 6)


@error_decorator
def activated_07(ui, ui_type):
    _activated_common(ui, ui_type, 7)


@error_decorator
def activated_08(ui, ui_type):
    _activated_common(ui, ui_type, 8)


# noinspection PyUnresolvedReferences
@error_decorator
def activated_09(ui, ui_type):
    """최적화용 전략 선택시 경고 메시지 (09번 공통)"""
    config = UI_CONFIG[ui_type]
    widgets = config['widgets']

    strategy_name = getattr(ui, widgets['combo_09']).currentText()
    if not strategy_name:
        return
    
    gubun = config['gubun_fn'](ui)
    table = config['tables'][2].format(gubun=gubun) if ui_type == 'stock' else config['tables'][2]
    
    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {table} WHERE `index` = '{strategy_name}'").set_index('index')
    
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


# 코인 전용 추가 함수
@error_decorator
def activated_10(ui):
    """바이낸스 선물 마진타입 경고"""
    if ui.dict_set['거래소'] == '바이낸스선물' and ui.sj_main_comBox_03.currentText() == '교차':
        ui.sj_main_comBox_03.setCurrentText('격리')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 마진타입은 격리타입만 지원합니다.\n')


@error_decorator
def activated_11(ui):
    """바이낸스 선물 포지션모드 경고"""
    if ui.dict_set['거래소'] == '바이낸스선물' and ui.sj_main_comBox_04.currentText() == '양방향':
        ui.sj_main_comBox_04.setCurrentText('단방향')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 포지션모드는 단방향만 지원합니다.\n')
