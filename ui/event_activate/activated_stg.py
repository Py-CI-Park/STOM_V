
# UI 타입별 설정 매핑
UI_ACTIBATED_CONFIG = {
    'tables': [
        '{stg_tname}_buy', '{stg_tname}_sell', '{stg_tname}_optibuy', '{stg_tname}_optivars',
        '{stg_tname}_optisell', '{stg_tname}_vars', '{stg_tname}_buyconds', '{stg_tname}_sellconds'
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
        'combo_09': 'sj_strgy_cbBox_01',
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


def _activated_common(ui, idx):
    """공통 activated 로직"""
    from PyQt5.QtWidgets import QMessageBox
    from ui.event_click.button_clicked_strategy_version import strategy_version

    widgets = UI_ACTIBATED_CONFIG['widgets']
    table = UI_ACTIBATED_CONFIG['tables'][idx - 1]

    combo_name = f'combo_{idx:02d}'
    line_name = f'line_{idx:02d}'
    text_name = f'text_{idx:02d}'

    strategy_name = getattr(ui, widgets[combo_name]).currentText()
    if not strategy_name:
        return

    if '{' in table:
        table = table.format(stg_tname=ui.market_info['전략구분'])

    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {table} WHERE `index` = '{strategy_name}'").set_index('index')

    if len(df) > 0:
        getattr(ui, widgets[text_name]).clear()
        getattr(ui, widgets[text_name]).append(df['전략코드'][strategy_name])
        getattr(ui, widgets[line_name]).setText(strategy_name)

        if getattr(ui, widgets['push_41']).isVisible():
            stg_type = UI_ACTIBATED_CONFIG['types'][idx - 1]
            buysell = UI_ACTIBATED_CONFIG['buysell'][idx - 1]
            strategy_version(ui, stg_type, buysell, strategy_name)
    else:
        QMessageBox.critical(ui, '오류 알림', UI_ACTIBATED_CONFIG['errors'][idx - 1])


def activated_01(ui):
    """전략 탭 활성화 이벤트 1을 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 1)


def activated_02(ui):
    """전략 탭 활성화 이벤트 2를 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 2)


def activated_03(ui):
    """전략 탭 활성화 이벤트 3을 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 3)


def activated_04(ui):
    """전략 탭 활성화 이벤트 4를 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 4)


def activated_05(ui):
    """전략 탭 활성화 이벤트 5를 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 5)


def activated_06(ui):
    """전략 탭 활성화 이벤트 6을 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 6)


def activated_07(ui):
    """전략 탭 활성화 이벤트 7을 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 7)


def activated_08(ui):
    """전략 탭 활성화 이벤트 8을 처리합니다.
    Args:
        ui: UI 객체
    """
    _activated_common(ui, 8)


# noinspection PyUnresolvedReferences
def activated_09(ui):
    """최적화용 전략 선택시 경고 메시지 (09번 공통)"""
    widgets = UI_ACTIBATED_CONFIG['widgets']
    strategy_name = getattr(ui, widgets['combo_09']).currentText()
    if not strategy_name:
        return

    table = UI_ACTIBATED_CONFIG['tables'][2].format(stg_tname=ui.market_info['전략구분'])
    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {table} WHERE `index` = '{strategy_name}'").set_index('index')

    if len(df) > 0:
        try:
            optivars = [float(i) if '.' in i else int(i) for i in df['변수값'][strategy_name].split(';')]
        except Exception:
            optivars = ''
        QMessageBox.warning(
            ui, '경고',
            '최적화용 전략 선택시 최적값으로 전략이 실행됩니다.\n'
            '다음 변수값을 확인하십시오\n'
            f'{optivars}\n'
            f'매도전략 또한 반드시 최적화용 전략으로 변경하십시오.\n'
            f'최적화 백테스트를 실행할 경우 자동으로 변경됩니다.\n'
        )


def activated_10(ui):
    """바이낸스 선물 마진타입 경고"""
    from PyQt5.QtWidgets import QMessageBox
    if ui.sj_main_comBox_03.currentText() == '교차':
        ui.sj_main_comBox_03.setCurrentText('격리')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 마진타입은 격리타입만 지원합니다.\n')


def activated_11(ui):
    """바이낸스 선물 포지션모드 경고"""
    from PyQt5.QtWidgets import QMessageBox
    if ui.sj_main_comBox_04.currentText() == '양방향':
        ui.sj_main_comBox_04.setCurrentText('단방향')
        QMessageBox.warning(ui, '경고', '현재 바이낸스 선물 포지션모드는 단방향만 지원합니다.\n')
