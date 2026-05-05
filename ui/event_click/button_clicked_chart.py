
def chart_moneytop_list(ui):
    """차트 거래대금 순위 목록을 표시합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    import sqlite3
    import pandas as pd
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QTableWidgetItem

    searchdate = ui.ct_dateEdittttt_02.date().toString('yyyyMMdd')
    starttime  = ui.ct_lineEdittttt_01.text()
    endtime    = ui.ct_lineEdittttt_02.text()

    is_tick  = ui.dict_set['타임프레임']
    db_name1 = f"{ui.market_info['일자디비경로'][is_tick]}_{searchdate}.db"
    db_name2 = ui.market_info['백테디비'][is_tick]

    if is_tick:
        query = f"SELECT * FROM moneytop WHERE " \
                f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
    else:
        query = f"SELECT * FROM moneytop WHERE " \
                f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"

    df = None
    try:
        if os.path.isfile(db_name1):
            con = sqlite3.connect(db_name1)
            df = pd.read_sql(query, con)
            con.close()
        elif os.path.isfile(db_name2):
            con = sqlite3.connect(db_name2)
            df = pd.read_sql(query, con)
            con.close()
    except Exception:
        pass

    if df is None or len(df) == 0:
        ui.ct_tableWidgett_01.clearContents()
        return

    table_list = list(set(';'.join(df['거래대금순위'].to_list()).split(';')))
    name_list = [ui.dict_name.get(code, code) for code in table_list]
    name_list.sort()

    ui.ct_tableWidgett_01.setRowCount(len(name_list))
    for i, name in enumerate(name_list):
        item = QTableWidgetItem(name)
        item.setTextAlignment(int(Qt.AlignVCenter | Qt.AlignLeft))
        ui.ct_tableWidgett_01.setItem(i, 0, item)
    if len(name_list) < 100:
        ui.ct_tableWidgett_01.setRowCount(100)


def chart_size_change(ui):
    """차트 크기를 변경합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_style import style_bc_bt, style_bc_bb

    if ui.ct_pushButtonnn_06.text() == '확장':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1528
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2213
        else:
            width = 2898
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('축소')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bb)
        chart_moneytop_list(ui)

    elif ui.ct_pushButtonnn_06.text() == '축소':
        if ui.ct_pushButtonnn_05.text() == 'CHART I':
            width = 1403
        elif ui.ct_pushButtonnn_05.text() == 'CHART II':
            width = 2088
        else:
            width = 2773
        ui.dialog_chart.setFixedSize(width, 1370 if not ui.dict_set['저해상도'] else 1010)
        ui.ct_pushButtonnn_06.setText('확장')
        ui.ct_pushButtonnn_06.setStyleSheet(style_bc_bt)


def indicator_setting_basic(ui):
    """보조지표 기본 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from utility.settings.setting_base import indi_base

    k = list(indi_base.values())
    for i, linedit in enumerate(ui.factor_linedit_list):
        linedit.setText(str(k[i]))


def indicator_setting_load(ui):
    """보조지표 설정을 데이터베이스에서 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM back')
    k_list = df['보조지표설정'][0]
    k_list = k_list.split(';')
    for i, linedit in enumerate(ui.factor_linedit_list):
        linedit.setText(k_list[i])


def indicator_setting_save(ui):
    """보조지표 설정을 데이터베이스에 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying

    k_list = []
    for linedit in ui.factor_linedit_list:
        k_list.append(linedit.text())
    k_list = ';'.join(k_list)
    if ui.proc_chqs.is_alive():
        query = f"UPDATE back SET 보조지표설정 = '{k_list}'"
        ui.queryQ.put(('설정디비', query))
        QMessageBox.information(ui.dialog_factor, '저장 완료', random.choice(famous_saying))


def get_indicator_detail(ui):
    """보조지표 상세 설정을 가져옵니다.
    Args:
        ui: UI 클래스 인스턴스
    Returns:
        보조지표 설정 리스트
    """
    from utility.settings.setting_base import indicator

    k_list = None
    if not ui.dict_set['타임프레임']:
        if ui.ft_checkBoxxxxx_44.isChecked():
            buystg = None
            vars_  = None
            try:
                stg_name = ui.dict_set['매수전략']
                df1 = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_buy").set_index('index')
                df2 = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_optibuy").set_index('index')
                if stg_name in df1.index:
                    buystg = df1['전략코드'][stg_name]
                elif stg_name in df2.index:
                    buystg = df2['전략코드'][stg_name]
                    vars_text = df2['변수값'][stg_name]
                    vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                    vars_ = {i: var for i, var in enumerate(vars_list)}
            except Exception:
                pass
            else:
                indistg = ''
                if buystg is not None:
                    # noinspection PyUnresolvedReferences
                    for line in buystg.split('\n'):
                        if 'self.indicator' in line and line[0] != '#':
                            indistg += f"{line.replace('self.indicator', 'indicator_')}\n"
                if indistg:
                    indicator_ = indicator
                    if vars_ is not None:
                        indistg = indistg.replace('self.vars', 'vars_')
                    exec(compile(indistg, '<string>', 'exec'))
                    k_list = list(indicator_.values())

        if k_list is None:
            k_list = [linedit.text() for linedit in ui.factor_linedit_list]
            k_list = [int(x) if '.' not in x else float(x) for x in k_list]

    return k_list
