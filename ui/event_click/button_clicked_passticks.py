
import random
from PyQt5.QtWidgets import QMessageBox
from ui.create_widget.set_text import famous_saying


def setting_passticks_sample(ui):
    """패스틱스 설정 샘플을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    ui.set_lineEdittt_01.setText('이평60데드')
    ui.set_lineEdittt_02.setText('이평60골든')
    ui.set_lineEdittt_11.setText('현재가N(1) >= 이동평균(60, 1) and  이동평균(60) > 현재가')
    ui.set_lineEdittt_12.setText('현재가N(1) <= 이동평균(60, 1) and  이동평균(60) < 현재가')


def setting_passticks_load(ui):
    """패스틱스 설정을 로드합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    for lineedit in ui.scn_lineedit_list:
        lineedit.clear()
    for lineedit in ui.scc_lineedit_list:
        lineedit.clear()

    df = ui.dbreader.read_sql('전략디비', f"SELECT * FROM {ui.market_info['전략구분']}_passticks")
    if len(df) > 0:
        name_list = df['index'].tolist()
        stg_list  = df['전략코드'].tolist()
        for i, key in enumerate(name_list):
            ui.scn_lineedit_list[i].setText(key)
        for i, value in enumerate(stg_list):
            ui.scc_lineedit_list[i].setText(value)


def setting_passticks_save(ui):
    """패스틱스 설정을 저장합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    data_list = []
    for lineedit1, lineedit2 in zip(ui.scn_lineedit_list, ui.scc_lineedit_list):
        ltext1, ltext2 = lineedit1.text(), lineedit2.text()
        if ltext1 and ltext2:
            data_list.append([ltext1, ltext2])

    if data_list:
        if ui.proc_chqs.is_alive():
            import pandas as pd
            df = pd.DataFrame(data_list, columns=['index', '전략코드']).set_index('index')
            ui.queryQ.put(('전략디비', df, f"{ui.market_info['전략구분']}_passticks", 'replace'))
            QMessageBox.information(ui.dialog_setsj, '저장 완료', random.choice(famous_saying))
