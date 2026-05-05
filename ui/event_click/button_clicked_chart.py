
import random
from PyQt5.QtWidgets import QMessageBox
from ui.create_widget.set_text import famous_saying
from utility.settings.setting_base import indi_base, indicator


def indicator_setting_basic(ui):
    """보조지표 기본 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
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
