
import random
from ui.set_text import famous_saying
from PyQt5.QtWidgets import QMessageBox
from utility.static import error_decorator


@error_decorator
def setting_stock_elapsed_tick_number_sample(ui):
    ui.set_lineEdittt_01.setText('이평60데드')
    ui.set_lineEdittt_02.setText('이평60골든')
    ui.set_lineEdittt_11.setText('현재가N(1) >= 이동평균(60, 1) and  이동평균(60) > 현재가')
    ui.set_lineEdittt_12.setText('현재가N(1) <= 이동평균(60, 1) and  이동평균(60) < 현재가')


@error_decorator
def setting_stock_elapsed_tick_number_load(ui):
    for lineedit in ui.scn_lineedit_list:
        lineedit.clear()
    for lineedit in ui.scc_lineedit_list:
        lineedit.clear()
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM stock').set_index('index')
    if df['주식경과틱수설정'][0]:
        text_list  = df['주식경과틱수설정'][0].split(';')
        half_cnt   = int(len(text_list) / 2)
        key_list   = text_list[:half_cnt]
        value_list = text_list[half_cnt:]
        for i, key in enumerate(key_list):
            ui.scn_lineedit_list[i].setText(key)
        for i, value in enumerate(value_list):
            ui.scc_lineedit_list[i].setText(value)


@error_decorator
def setting_stock_elapsed_tick_number_save(ui):
    text = ''
    for i, lineedit in enumerate(ui.scn_lineedit_list):
        ltext = lineedit.text()
        if ltext and ui.scc_lineedit_list[i].text():
            text = f'{text}{ltext};'
    for i, lineedit in enumerate(ui.scc_lineedit_list):
        ltext = lineedit.text()
        if ltext and ui.scn_lineedit_list[i].text():
            text = f'{text}{ltext};'
    if text:
        text = text[:-1]
        if ui.proc_chqs.is_alive():
            query = f"UPDATE stock SET 주식경과틱수설정 = '{text}'"
            ui.queryQ.put(('설정디비', query))
            QMessageBox.information(ui.dialog_setsj, '저장 완료', random.choice(famous_saying))


@error_decorator
def setting_coin_elapsed_tick_number_sample(ui):
    ui.cet_lineEdittt_01.setText('이평60데드')
    ui.cet_lineEdittt_02.setText('이평60골든')
    ui.cet_lineEdittt_11.setText('현재가N(1) >= 이동평균(60, 1) and  이동평균(60) > 현재가')
    ui.cet_lineEdittt_12.setText('현재가N(1) <= 이동평균(60, 1) and  이동평균(60) < 현재가')


@error_decorator
def setting_coin_elapsed_tick_number_load(ui):
    for lineedit in ui.ccn_lineedit_list:
        lineedit.clear()
    for lineedit in ui.ccc_lineedit_list:
        lineedit.clear()
    df = ui.dbreader.read_sql('설정디비', 'SELECT * FROM coin').set_index('index')
    if df['코인경과틱수설정'][0]:
        text_list  = df['코인경과틱수설정'][0].split(';')
        half_cnt   = int(len(text_list) / 2)
        key_list   = text_list[:half_cnt]
        value_list = text_list[half_cnt:]
        for i, key in enumerate(key_list):
            ui.ccn_lineedit_list[i].setText(key)
        for i, value in enumerate(value_list):
            ui.ccc_lineedit_list[i].setText(value)


@error_decorator
def setting_coin_elapsed_tick_number_save(ui):
    text = ''
    for i, lineedit in enumerate(ui.ccn_lineedit_list):
        ltext = lineedit.text()
        if ltext and ui.ccc_lineedit_list[i].text():
            text = f'{text}{ltext};'
    for i, lineedit in enumerate(ui.ccc_lineedit_list):
        ltext = lineedit.text()
        if ltext and ui.ccn_lineedit_list[i].text():
            text = f'{text}{ltext};'
    if text:
        text = text[:-1]
        if ui.proc_chqs.is_alive():
            query = f"UPDATE coin SET 코인경과틱수설정 = '{text}'"
            ui.queryQ.put(('설정디비', query))
            QMessageBox.information(ui.dialog_cetsj, '저장 완료', random.choice(famous_saying))
