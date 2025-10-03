import random
import sqlite3
import pandas as pd
from PyQt5.QtWidgets import QMessageBox
from ui.set_text import famous_saying
from utility.setting import DB_SETTING


def set_button_clicked_01(ui):
    ui.set_lineEdittt_01.setText('이평60데드')
    ui.set_lineEdittt_02.setText('이평60골든')
    ui.set_lineEdittt_11.setText('현재가N(1) >= 이동평균(60, 1) and  이동평균(60) > 현재가')
    ui.set_lineEdittt_12.setText('현재가N(1) <= 이동평균(60, 1) and  이동평균(60) < 현재가')


def set_button_clicked_02(ui):
    for lineedit in ui.scn_lineedit_list:
        lineedit.clear()
    for lineedit in ui.scc_lineedit_list:
        lineedit.clear()
    con = sqlite3.connect(DB_SETTING)
    df  = pd.read_sql('SELECT * FROM stock', con).set_index('index')
    con.close()
    if df['주식경과틱수설정'][0] != '':
        text_list  = df['주식경과틱수설정'][0].split(';')
        half_cnt   = int(len(text_list) / 2)
        key_list   = text_list[:half_cnt]
        value_list = text_list[half_cnt:]
        for i, key in enumerate(key_list):
            ui.scn_lineedit_list[i].setText(key)
        for i, value in enumerate(value_list):
            ui.scc_lineedit_list[i].setText(value)


def set_button_clicked_03(ui):
    text = ''
    for i, lineedit in enumerate(ui.scn_lineedit_list):
        ltext = lineedit.text()
        if ltext != '' and ui.scc_lineedit_list[i].text() != '':
            text = f'{text}{ltext};'
    for i, lineedit in enumerate(ui.scc_lineedit_list):
        ltext = lineedit.text()
        if ltext != '' and ui.scn_lineedit_list[i].text() != '':
            text = f'{text}{ltext};'
    if text != '':
        text = text[:-1]
        if ui.proc_query.is_alive():
            query = f"UPDATE stock SET 주식경과틱수설정 = '{text}'"
            ui.queryQ.put(('설정디비', query))
            QMessageBox.information(ui.dialog_setsj, '저장 완료', random.choice(famous_saying))


def cet_button_clicked_01(ui):
    ui.cet_lineEdittt_01.setText('이평60데드')
    ui.cet_lineEdittt_02.setText('이평60골든')
    ui.cet_lineEdittt_11.setText('현재가N(1) >= 이동평균(60, 1) and  이동평균(60) > 현재가')
    ui.cet_lineEdittt_12.setText('현재가N(1) <= 이동평균(60, 1) and  이동평균(60) < 현재가')


def cet_button_clicked_02(ui):
    for lineedit in ui.ccn_lineedit_list:
        lineedit.clear()
    for lineedit in ui.ccc_lineedit_list:
        lineedit.clear()
    con = sqlite3.connect(DB_SETTING)
    df  = pd.read_sql('SELECT * FROM coin', con).set_index('index')
    con.close()
    if df['코인경과틱수설정'][0] != '':
        text_list  = df['코인경과틱수설정'][0].split(';')
        half_cnt   = int(len(text_list) / 2)
        key_list   = text_list[:half_cnt]
        value_list = text_list[half_cnt:]
        for i, key in enumerate(key_list):
            ui.ccn_lineedit_list[i].setText(key)
        for i, value in enumerate(value_list):
            ui.ccc_lineedit_list[i].setText(value)


def cet_button_clicked_03(ui):
    text = ''
    for i, lineedit in enumerate(ui.ccn_lineedit_list):
        ltext = lineedit.text()
        if ltext != '' and ui.ccc_lineedit_list[i].text() != '':
            text = f'{text}{ltext};'
    for i, lineedit in enumerate(ui.ccc_lineedit_list):
        ltext = lineedit.text()
        if ltext != '' and ui.ccn_lineedit_list[i].text() != '':
            text = f'{text}{ltext};'
    if text != '':
        text = text[:-1]
        if ui.proc_query.is_alive():
            query = f"UPDATE coin SET 코인경과틱수설정 = '{text}'"
            ui.queryQ.put(('설정디비', query))
            QMessageBox.information(ui.dialog_cetsj, '저장 완료', random.choice(famous_saying))
