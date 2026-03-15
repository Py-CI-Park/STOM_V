
import psutil
import random
import sqlite3
import numpy as np
import pandas as pd
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QApplication, QMessageBox, QColorDialog
from ui.set_text import famous_saying
from utility.setting_base import columns_dt, columns_dd, ui_num, DB_STRATEGY
from utility.static import thread_decorator, qtest_qwait, str_ymdhmsf, str_ymdhms


def update_image(ui, data):
    ui.image_label1.clear()
    qpix = QPixmap()
    qpix.loadFromData(data[1])
    qpix = qpix.scaled(QSize(335, 105), Qt.IgnoreAspectRatio)
    ui.image_label1.setPixmap(qpix)
    ui.image_label2.clear()
    qpix = QPixmap()
    qpix.loadFromData(data[2])
    qpix = qpix.scaled(QSize(335, 602), Qt.IgnoreAspectRatio)
    ui.image_label2.setPixmap(qpix)


def update_sqsize(ui, data):
    ui.saqsize, ui.stqsize, ui.ssqsize = data


@thread_decorator
def update_cpuper(ui):
    ui.cpu_per = int(psutil.cpu_percent(interval=1))


def auto_back_schedule(ui, gubun):
    if gubun == 1:
        ui.auto_mode = True
        if ui.dict_set['주식알림소리'] or ui.dict_set['코인알림소리']:
            ui.soundQ.put('예약된 백테스트 스케쥴러를 시작합니다.')
        if not ui.dialog_backengine.isVisible():
            ui.BackTestengineShow(ui.dict_set['백테스케쥴구분'])
        qtest_qwait(2)
        ui.BacktestEngineKill()
        qtest_qwait(3)
        ui.BacktestEngineStart(ui.dict_set['백테스케쥴구분'])
    elif gubun == 2:
        if not ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.show()
        qtest_qwait(2)
        ui.sdButtonClicked_04()
        qtest_qwait(2)
        ui.sd_pushButtonnn_01.setText(ui.dict_set['백테스케쥴구분'])
        ui.sd_dcomboBoxxxx_01.setCurrentText(ui.dict_set['백테스케쥴명'])
        qtest_qwait(2)
        ui.sdButtonClicked_02()
    elif gubun == 3:
        if ui.dialog_scheduler.isVisible():
            ui.dialog_scheduler.close()
        ui.teleQ.put('백테스트 스케쥴러 완료')
        ui.auto_mode = False


def update_dictset(ui):
    ui.wdzservQ.put(('manager', ('설정변경', ui.dict_set)))
    if ui.CoinReceiverProcessAlive(): ui.creceivQ.put(('설정변경', ui.dict_set))
    if ui.CoinTraderProcessAlive():   ui.ctraderQ.put(('설정변경', ui.dict_set))
    if ui.CoinStrategyProcessAlive(): ui.cstgQ.put(('설정변경', ui.dict_set))
    if ui.proc_chart.is_alive():      ui.chartQ.put(('설정변경', ui.dict_set))
    if ui.proc_query.is_alive():      ui.queryQ.put(('설정변경', ui.dict_set))
    if ui.proc_hoga.is_alive():       ui.hogaQ.put(('설정변경', ui.dict_set))
    if ui.backtest_engine:
        for bpq in ui.back_eques:
            bpq.put(('설정변경', ui.dict_set))


def chart_clear(ui):
    ui.ctpg_name             = None
    ui.ctpg_cline            = None
    ui.ctpg_hline            = None
    ui.ctpg_xticks           = None
    ui.ctpg_arry             = None
    ui.ctpg_last_candlestick = None
    ui.ctpg_last_volumebar   = None
    ui.ctpg_last_xtick       = None
    ui.ctpg_legend           = {}
    ui.ctpg_item             = {}
    ui.ctpg_data             = {}
    ui.ctpg_factors          = []
    ui.ctpg_labels           = []


def calendar_clicked(ui, gubun):
    if gubun == 'S':
        table = 's_tradelist' if '키움증권' in ui.dict_set['증권사'] else 'f_tradelist'
        searchday = ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
    else:
        table = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
        searchday = ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
    df1 = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table} WHERE 체결시간 LIKE '{searchday}%'").set_index('index')
    if len(df1) > 0:
        df1.sort_values(by=['체결시간'], ascending=True, inplace=True)
        if table in ('f_tradelist', 'c_tradelist_future'):
            df1 = df1[['체결시간', '종목명', '포지션', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        else:
            df1 = df1[['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']]
        nbg, nsg = df1['매수금액'].sum(), df1['매도금액'].sum()
        sp = np.round((nsg / nbg - 1) * 100, 2)
        npg, nmg, nsig = df1[df1['수익금'] > 0]['수익금'].sum(), df1[df1['수익금'] < 0]['수익금'].sum(), df1['수익금'].sum()
        df2 = pd.DataFrame(columns=columns_dt)
        df2.loc[0] = [searchday, nbg, nsg, npg, nmg, sp, nsig]
    else:
        df1 = pd.DataFrame(columns=columns_dd)
        df2 = pd.DataFrame(columns=columns_dt)
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일합계'], df2))
    ui.update_tablewidget.update_tablewidget((ui_num[f'{gubun}당일상세'], df1))


def stom_live_screenshot(ui, cmd):
    prev_main_btn = ui.main_btn
    ui.mnButtonClicked_01(4)
    qtest_qwait(1)
    if '주식' in cmd:
        mid = 'S'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index1)
    elif '코인' in cmd:
        mid = 'C'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index2)
    elif '해선' in cmd:
        mid = 'F'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index3)
    else:
        mid = 'B'
        ui.slv_tapWidgett_01.setCurrentIndex(ui.slv_index4)
    qtest_qwait(1)
    file_name = f'./_log/StomLive_{mid}_{str_ymdhms()}.png'
    screen = QApplication.primaryScreen()
    screenshot = screen.grabWindow(ui.winId())
    screenshot.save(file_name, 'png')
    ui.teleQ.put(file_name)
    ui.mnButtonClicked_01(prev_main_btn)


def chart_screenshot(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui, '차트 스샷 전송 완료', random.choice(famous_saying))


def chart_screenshot2(ui):
    if ui.dialog_chart.isVisible():
        file_name = f'./_log/chart_{str_ymdhmsf()}.png'
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(ui.dialog_chart.winId())
        screenshot.save(file_name, 'png')
        ui.teleQ.put(file_name)
        QMessageBox.information(ui.dialog_chart, '차트 스샷 전송 완료', random.choice(famous_saying))


def manual_save_and_exit(ui):
    buttonReply = QMessageBox.question(
        ui, '수동종료', '현재까지의 데이터를 저장하고 수동종료합니다.\n계속 하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.CoinReceiverProcessAlive():
            ui.creceivQ.put(('수동데이터저장', 'dummy'))
        else:
            ui.wdzservQ.put(('agent', ('수동데이터저장', 'dummy')))


def formula_activated(ui):
    dict_style = {
        1: '1:실선',
        2: '2:대시선',
        3: '3:점선',
        4: '4:대시점선',
        5: '5:대시점점선',
        6: '6:위쪽화살표(↑)',
        7: '7:아래쪽화살표(↓)',
        8: '8:우측쪽화살표(→)',
        9: '9:좌쪽화살표(←)'
    }
    fname = ui.fm_comboBoxxxxx_00.currentText()
    con = sqlite3.connect(DB_STRATEGY)
    cursor = con.cursor()
    cursor.execute(f"SELECT * FROM formula WHERE 수식명 = '{fname}'")
    row = cursor.fetchone()
    con.close()
    if row:
        name, check, fname, vtype, color, width, style, stg = row
        ui.fm_lineEdittttt_01.setText(name)
        ui.fm_checkBoxxxxx_01.setChecked(check)
        ui.fm_comboBoxxxxx_01.setCurrentText(fname)
        ui.fm_comboBoxxxxx_02.setCurrentText(vtype)
        if '#' in color:
            ui.fm_frameeeeeeee_01.setStyleSheet('QWidget { background-color: %s }' % color)
            ui.fm_lineEdittttt_02.setText(color)
        ui.fm_comboBoxxxxx_03.setCurrentText(str(width))
        ui.fm_comboBoxxxxx_04.setCurrentText(dict_style[style])
        ui.fm_textEdittttt_01.clear()
        ui.fm_textEdittttt_01.append(stg)


def formila_button_clicked(ui):
    button_text = ui.dialog_formula.focusWidget().text()

    if button_text == '불러오기':
        con = sqlite3.connect(DB_STRATEGY)
        cursor = con.cursor()
        cursor.execute("SELECT * FROM formula")
        rows = cursor.fetchall()
        con.close()
        ui.fm_comboBoxxxxx_00.clear()
        name_list = [row[0] for row in rows]
        for name in name_list:
            ui.fm_comboBoxxxxx_00.addItem(name)

    elif button_text == '저장하기':
        name  = ui.fm_lineEdittttt_01.text()
        check = 1 if ui.fm_checkBoxxxxx_01.isChecked() else 0
        fname = ui.fm_comboBoxxxxx_01.currentText()
        vtype = ui.fm_comboBoxxxxx_02.currentText()
        color = ui.fm_lineEdittttt_02.text()
        width = float(ui.fm_comboBoxxxxx_03.currentText())
        style = int(ui.fm_comboBoxxxxx_04.currentText()[:1])
        stg   = ui.fm_textEdittttt_01.toPlainText()

        if name == '' or stg == '':
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '수식명 또는 수식코드가 공백상태입니다.\n')
            return
        elif vtype in ('선:일반', '선:조건') and width > 5:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '실선의 최대크기는 5입니다.\n')
            return
        elif vtype in ('선:일반', '선:조건') and style > 5:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '선의 종류 선택이 잘못되었습니다.\n')
            return
        elif vtype == '화살표:일반' and width < 10:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '화살표의 최소크기는 10입니다.\n')
            return
        elif vtype == '화살표:일반' and style < 6:
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '화살표의 방향 선택이 잘못되었습니다.\n')
            return

        if ui.FormulaCodeTest(stg) and ui.proc_query.is_alive():
            delete_query = f"DELETE FROM formula WHERE 수식명 = '{name}'"
            insert_query = f"INSERT INTO formula (수식명, 체크유무, 팩터명, 표시형태, 색상, 크기, 라인타입, 수식코드) " \
                           f"VALUES ('{name}', {check}, '{fname}', '{vtype}', '{color}', {width}, {style}, '{stg}')"
            ui.queryQ.put(('전략디비', delete_query))
            ui.queryQ.put(('전략디비', insert_query))
            QMessageBox.information(ui.dialog_formula, '수식 저장 완료', random.choice(famous_saying))

    elif button_text == '삭제하기':
        name = ui.fm_lineEdittttt_01.text()
        if name == '':
            QMessageBox.critical(ui.dialog_formula, '오류 알림', '삭제할 수식명을 선택하십시오.\n')
            return
        if ui.proc_query.is_alive():
            query = f"DELETE FROM formula WHERE 수식명 = '{name}'"
            ui.queryQ.put(('전략디비', query))
            QMessageBox.information(ui.dialog_formula, '수식 삭제 완료', random.choice(famous_saying))
            qtest_qwait(0.5)

            con = sqlite3.connect(DB_STRATEGY)
            cursor = con.cursor()
            cursor.execute("SELECT * FROM formula")
            rows = cursor.fetchall()
            con.close()
            ui.fm_comboBoxxxxx_00.clear()
            name_list = [row[0] for row in rows]
            for name in name_list:
                ui.fm_comboBoxxxxx_00.addItem(name)

    elif button_text == '색상선택':
        from PyQt5.QtCore import QTimer

        def center_dialog():
            parent_center_x = ui.dialog_formula.x() + ui.dialog_formula.width() // 2
            parent_center_y = ui.dialog_formula.y() + ui.dialog_formula.height() // 2
            dialog_x = parent_center_x - dialog.width() // 2
            dialog_y = parent_center_y - dialog.height() // 2
            dialog.move(dialog_x, dialog_y)

        dialog = QColorDialog(ui.dialog_formula)
        dialog.show()
        QTimer.singleShot(10, center_dialog)

        if dialog.exec_() == QColorDialog.Accepted:
            col = dialog.selectedColor()
            ui.fm_frameeeeeeee_01.setStyleSheet('QWidget { background-color: %s }' % col.name())
            ui.fm_lineEdittttt_02.setText(col.name())

    elif button_text == '예제확인':
        text = """# 수식관리자는 로딩된 차트 데이터를 기반으로
# 전략연산과 유사한 방식으로 작동되도록 설계되었으며
# 전략연산과 다르게 매도관련 팩터를 사용할 수 없으니
# 유의하시길 바랍니다. (보유수량, 최고수익률, 수익률 등)

# 선:일반, 고가 라인 표시
self.line = 최고현재가(60)

# 선:조건, 최저현재가 대비 최고현재가 등락율 2%이상
# 발생한 시점에 선을 긋고 유지되며 다시 발생하면 갱신됨.
high_price = 최고현재가(30)
low_price = 최저현재가(30)
self.check = (high_price / low_price - 1) * 100 >= 2
self.line = (high_price + low_price) / 2

# 화살표:일반, 호가상승압력
총잔량 = 매수총잔량 + 매도총잔량
self.check = 매수총잔량 / 총잔량 > 0.7

# 화살표:매매, 이평돌파 및 이탈 매매
현재이평 = 이동평균(60)
직전이평 = 이동평균(60, 1)
if 데이터길이 < 61: continue
self.buy = 현재가N(1) <= 직전이평 and 현재이평 < 현재가
self.sell = 현재가N(1) >= 직전이평 and 현재이평 > 현재가

# 범위, 이동평균위
이평60 = 이동평균(60)
self.check = 현재가 > 이평60 and 이평60 > 0
self.up = 현재가
self.down = 이평60
"""
        ui.fm_textEdittttt_01.clear()
        ui.fm_textEdittttt_01.append(text)
