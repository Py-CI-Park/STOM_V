
import sqlite3
from PyQt5.QtWidgets import QCompleter
from utility.lazy_imports import get_pd
from utility.static import error_decorator
from utility.setting_base import DB_CODE_INFO, DB_COIN_BACK_TICK, list_stock_tick, list_stock_min, list_coin_tick, \
    list_coin_min, list_stock_tick2, list_stock_min2, list_coin_tick2, list_coin_min2, list_future_tick2, \
    list_future_min2


@error_decorator
def load_database(ui):
    con = sqlite3.connect(DB_CODE_INFO)
    df = get_pd().read_sql('SELECT * FROM stockinfo', con).set_index('index')
    ui.dict_name.update(df['종목명'].to_dict())
    df = get_pd().read_sql('SELECT * FROM futureinfo', con).set_index('index')
    ui.dict_name.update(df['종목명'].to_dict())
    con.close()
    ui.dict_code = {name: code for code, name in ui.dict_name.items()}

    con = sqlite3.connect(DB_COIN_BACK_TICK)
    df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
    con.close()
    ui.ct_lineEdittttt_04.setCompleter(QCompleter(list(ui.dict_code.values())))
    ui.ct_lineEdittttt_05.setCompleter(QCompleter(list(ui.dict_name.values()) + df['name'].to_list()))

    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM custombutton").set_index('index')
    if len(df) > 0:
        for index in df.index:
            ui.dict_stg_btn[index] = df['전략코드'][index]
            if index <= 205:
                button = getattr(ui, f'stg_pushButton_{index:03d}')
            elif index <= 211:
                button = getattr(ui, f'svjb_pushButon_{index - 201:02d}')
            elif index <= 219:
                button = getattr(ui, f'svjs_pushButon_{index - 207:02d}')
            elif index <= 225:
                button = getattr(ui, f'cvjb_pushButon_{index - 215:02d}')
            else:
                button = getattr(ui, f'cvjs_pushButon_{index - 221:02d}')
            button.setText(df['버튼명'][index])

    ui.dict_findex_stock_tick   = {name: i for i, name in enumerate(list_stock_tick)}
    ui.dict_findex_stock_min    = {name: i for i, name in enumerate(list_stock_min)}
    ui.dict_findex_coin_tick    = {name: i for i, name in enumerate(list_coin_tick)}
    ui.dict_findex_coin_min     = {name: i for i, name in enumerate(list_coin_min)}
    ui.dict_findex_stock_tick2  = {name: i for i, name in enumerate(list_stock_tick2)}
    ui.dict_findex_stock_min2   = {name: i for i, name in enumerate(list_stock_min2)}
    ui.dict_findex_coin_tick2   = {name: i for i, name in enumerate(list_coin_tick2)}
    ui.dict_findex_coin_min2    = {name: i for i, name in enumerate(list_coin_min2)}
    ui.dict_findex_future_tick2 = {name: i for i, name in enumerate(list_future_tick2)}
    ui.dict_findex_future_min2  = {name: i for i, name in enumerate(list_future_min2)}
