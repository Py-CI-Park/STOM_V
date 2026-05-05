
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QCompleter
from utility.settings.setting_base import DB_CODE_INFO, code_info_tables


def load_database(ui):
    """데이터베이스를 로드합니다.

    Args:
        ui: UI 객체
    """
    con = sqlite3.connect(DB_CODE_INFO)
    for table in code_info_tables:
        df = pd.read_sql(f'SELECT * FROM {table}', con).set_index('index')
        ui.dict_name.update(df['종목명'].to_dict())
    con.close()
    ui.dict_code = {name: code for code, name in ui.dict_name.items()}

    ui.ct_lineEdittttt_04.setCompleter(QCompleter(list(ui.dict_code.values())))
    ui.ct_lineEdittttt_05.setCompleter(QCompleter(list(ui.dict_name.values())))

    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM custombutton").set_index('index')
    if len(df) > 0:
        for index in df.index:
            ui.dict_stg_btn[index] = df['전략코드'][index]
            if index <= 205:
                button = getattr(ui, f'stg_pushButton_{index:03d}')
            elif index <= 211:
                button = getattr(ui, f'svjb_pushButon_{index - 201:02d}')
            else:
                button = getattr(ui, f'svjs_pushButon_{index - 207:02d}')
            button.setText(df['버튼명'][index])
