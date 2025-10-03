import random
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QMessageBox
from ui.set_text import famous_saying
from utility.setting import DB_SETTING, indi_base, DB_STRATEGY, indicator


def ct_button_clicked_01(ui):
    k = list(indi_base.values())
    for i, linedit in enumerate(ui.factor_linedit_list):
        linedit.setText(str(k[i]))


def ct_button_clicked_02(ui):
    con = sqlite3.connect(DB_SETTING)
    df = pd.read_sql('SELECT * FROM back', con)
    k_list = df['보조지표설정'][0]
    k_list = k_list.split(';')
    con.close()
    for i, linedit in enumerate(ui.factor_linedit_list):
        linedit.setText(k_list[i])


def ct_button_clicked_03(ui):
    k_list = []
    for linedit in ui.factor_linedit_list:
        k_list.append(linedit.text())
    k_list = ';'.join(k_list)
    if ui.proc_query.is_alive():
        query = f"UPDATE back SET 보조지표설정 = '{k_list}'"
        ui.queryQ.put(('설정디비', query))
        QMessageBox.information(ui.dialog_factor, '저장 완료', random.choice(famous_saying))


def get_k_list(ui, code):
    k_list = None
    if not ui.dict_set['주식타임프레임'] or not ui.dict_set['코인타임프레임']:
        if ui.ft_checkBoxxxxx_39.isChecked():
            buystg = None
            vars_  = None
            try:
                con = sqlite3.connect(DB_STRATEGY)
                if 'KRW' not in code and 'USDT' not in code:
                    stg_name = ui.dict_set['주식매수전략']
                    df1 = pd.read_sql('SELECT * FROM stockbuy', con).set_index('index')
                    df2 = pd.read_sql('SELECT * FROM stockoptibuy', con).set_index('index')
                else:
                    stg_name = ui.dict_set['코인매수전략']
                    df1 = pd.read_sql('SELECT * FROM coinbuy', con).set_index('index')
                    df2 = pd.read_sql('SELECT * FROM coinoptibuy', con).set_index('index')
                con.close()
                if stg_name in df1.index:
                    buystg = df1['전략코드'][stg_name]
                elif stg_name in df2.index:
                    buystg = df2['전략코드'][stg_name]
                    vars_text = ['변수값'][stg_name]
                    vars_list = [float(i) if '.' in i else int(i) for i in vars_text.split(';')]
                    vars_ = {i: var for i, var in enumerate(vars_list)}
            except:
                pass
            else:
                indistg = ''
                if buystg is not None:
                    for line in buystg.split('\n'):
                        if 'self.indicator' in line and '#' not in line:
                            indistg += f"{line.replace('self.indicator', 'indicator_')}\n"
                if indistg != '':
                    indicator_ = indicator
                    if vars_ is not None: indistg = indistg.replace('self.vars', 'vars_')
                    exec(compile(indistg, '<string>', 'exec'))
                    k_list = list(indicator_.values())
        if k_list is None:
            k_list = [linedit.text() for linedit in ui.factor_linedit_list]
            k_list = [int(x) if '.' not in x else float(x) for x in k_list]
    return k_list
