
from PyQt5.QtCore import  QDate
from ui.ui_button_clicked_editer_coin import *
from ui.ui_button_clicked_editer_stock import *
from ui.ui_button_clicked_editer_ga_coin import *
from ui.ui_button_clicked_editer_ga_stock import *
from ui.ui_button_clicked_editer_opti_coin import *
from ui.ui_button_clicked_editer_opti_stock import *
from ui.ui_button_clicked_editer_stg_buy_coin import *
from ui.ui_button_clicked_editer_stg_buy_stock import *
from ui.ui_button_clicked_editer_stg_sell_coin import *
from ui.ui_button_clicked_editer_stg_sell_stock import *
from ui.ui_button_clicked_editer_backlog import csbutton_clicked_06, ssbutton_clicked_06
from ui.ui_show_dialog import show_dialog_graph, show_dialog, show_dialog_chart
from utility.static import comma2int, comma2float, str_ymd, now_cme, now_utc


@error_decorator
def key_press_event(ui, event):
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
        if ui.dialog_scheduler.focusWidget() == ui.sd_dpushButtonn_01:
            return

        elif QApplication.keyboardModifiers() & Qt.AltModifier:
            if backtest_process_alive(ui):
                if ui.main_btn == 3:
                    ssbutton_clicked_06(ui)
                elif ui.main_btn == 4:
                    csbutton_clicked_06(ui)
            else:
                if ui.main_btn == 3:
                    if ui.svj_pushButton_01.isVisible():
                        stock_backtest_start(ui)
                elif ui.main_btn == 4:
                    if ui.cvj_pushButton_01.isVisible():
                        coin_backtest_start(ui)

        elif ui.focusWidget() in (ui.std_tableWidgettt, ui.sgj_tableWidgettt, ui.scj_tableWidgettt, ui.ctd_tableWidgettt, ui.cgj_tableWidgettt, ui.ccj_tableWidgettt):
            stock = True
            if ui.focusWidget() in (ui.ctd_tableWidgettt, ui.cgj_tableWidgettt, ui.ccj_tableWidgettt):
                stock = False
            row  = ui.focusWidget().currentIndex().row()
            col  = ui.focusWidget().currentIndex().column()
            item = ui.focusWidget().item(row, 0)
            if item is not None:
                name       = item.text()
                linetext   = ui.ct_lineEdittttt_03.text()
                tickcount  = int(linetext) if linetext else 30
                searchdate = str_ymd(now_utc()) if not stock else str_ymd() if '키움증권' in ui.dict_set['증권사'] else str_ymd(now_cme())
                code       = ui.dict_code[name] if name in ui.dict_code else name
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                show_dialog(ui, name, tickcount, searchdate, col)

        elif ui.focusWidget() in (ui.sds_tableWidgettt, ui.cds_tableWidgettt):
            if ui.focusWidget() == ui.sds_tableWidgettt:
                searchdate = ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
            else:
                searchdate = ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
            row  = ui.focusWidget().currentIndex().row()
            item = ui.focusWidget().item(row, 1)
            if item is not None:
                name      = item.text()
                linetext  = ui.ct_lineEdittttt_03.text()
                tickcount = int(linetext) if linetext else 30
                code      = ui.dict_code[name] if name in ui.dict_code else name
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog(ui, name, tickcount, searchdate, 4)

        elif ui.focusWidget() in (ui.sns_tableWidgettt, ui.cns_tableWidgettt):
            if ui.focusWidget() == ui.sns_tableWidgettt:
                gubun = '주식'
            else:
                gubun = '코인'
            row  = ui.focusWidget().currentIndex().row()
            item = ui.focusWidget().item(row, 0)
            if item is not None:
                date = item.text()
                date = date.replace('.', '')
                if gubun == '주식':
                    table_name = 's_tradelist' if '키움증권' in ui.dict_set['증권사'] else 'f_tradelist'
                else:
                    table_name = 'c_tradelist' if ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
                df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")
                if len(date) == 6 and gubun == '코인':
                    df['구분용체결시간'] = df['체결시간'].str[:6]
                    df = df[df['구분용체결시간'] == date]
                elif len(date) == 4 and gubun == '코인':
                    df['구분용체결시간'] = df['체결시간'].str[:4]
                    df = df[df['구분용체결시간'] == date]
                df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
                df.set_index('index', inplace=True)
                show_dialog_graph(ui, df)

        elif ui.focusWidget() in (ui.ss_tableWidget_01, ui.cs_tableWidget_01):
            tableWidget = ui.ss_tableWidget_01 if ui.focusWidget() == ui.ss_tableWidget_01 else ui.cs_tableWidget_01
            row  = tableWidget.currentIndex().row()
            item = tableWidget.item(row, 0)
            if item is not None:
                name       = item.text()
                searchdate = tableWidget.item(row, 2).text()[:8]
                buytime    = comma2int(tableWidget.item(row, 2).text())
                selltime   = comma2int(tableWidget.item(row, 3).text())
                buyprice   = comma2float(tableWidget.item(row, 5).text())
                sellprice  = comma2float(tableWidget.item(row, 6).text())
                detail     = [buytime, buyprice, selltime, sellprice]
                buytimes   = tableWidget.item(row, 13).text()
                coin       = True if 'KRW' in name or 'USDT' in name else False
                code       = ui.dict_code[name] if name in ui.dict_code else name
                starttime  = ui.ct_lineEdittttt_01.text()
                endtime    = ui.ct_lineEdittttt_02.text()
                if len(str(buytime)) > 12 and (coin and not ui.dict_set['코인타임프레임'] or not coin and not ui.dict_set['주식타임프레임']):
                    QMessageBox.critical(ui, '오류 알림', '현재 전략설정의 데이터타입은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트를 표시할 수 없습니다.\n')
                    return
                if len(str(buytime)) < 14 and (coin and ui.dict_set['코인타임프레임'] or not coin and ui.dict_set['주식타임프레임']):
                    QMessageBox.critical(ui, '오류 알림', '현재 전략설정의 데이터타입은 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트를 표시할 수 없습니다.\n')
                    return
                if len(starttime) < 6 or len(endtime) < 6:
                    QMessageBox.critical(ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
                    return
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog_chart(ui, False, coin, code, 30, searchdate, starttime, endtime, detail, buytimes)

    elif (QApplication.keyboardModifiers() & Qt.AltModifier) and \
            event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                            Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
        if ui.main_btn == 3:
            if event.key() == Qt.Key_1:
                stock_stg_editer(ui)
            elif event.key() == Qt.Key_2:
                stock_opti_editer(ui)
            elif event.key() == Qt.Key_3:
                stock_opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                stock_rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                stock_opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                stock_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                stock_opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                stock_vars_editer(ui)
            elif event.key() == Qt.Key_9:
                stock_backtest_log(ui)
            elif event.key() == Qt.Key_0:
                stock_backtest_detail(ui)
        elif ui.main_btn == 4:
            if event.key() == Qt.Key_1:
                coin_stg_editer(ui)
            elif event.key() == Qt.Key_2:
                coin_opti_editer(ui)
            elif event.key() == Qt.Key_3:
                coin_opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                coin_rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                coin_opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                coin_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                coin_opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                coin_vars_editer(ui)
            elif event.key() == Qt.Key_9:
                coin_backtest_log(ui)
            elif event.key() == Qt.Key_0:
                coin_backtest_detail(ui)

    elif event.key() == Qt.Key_F1:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                stock_buy_stg_load(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                stock_opti_buy_load(ui)
            elif ui.svo_pushButton_05.isVisible():
                stock_condbuy_load(ui)
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                coin_buy_stg_load(ui)
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                coin_opti_buy_load(ui)
            elif ui.cvo_pushButton_05.isVisible():
                coin_condbuy_load(ui)

    elif event.key() == Qt.Key_F2:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                ui.svjb_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_comboBoxxx_01.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_comboBoxxx_01.showPopup()
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjb_comboBoxx_01.showPopup()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_comboBoxxx_01.showPopup()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_comboBoxxx_01.showPopup()

    elif event.key() == Qt.Key_F3:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                ui.svjb_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_01.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_01.setFocus()
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjb_lineEditt_01.setFocus()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_lineEdittt_01.setFocus()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_lineEdittt_01.setFocus()

    elif event.key() == Qt.Key_F4:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                stock_buy_stg_save(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.svc_pushButton_15.isVisible() or ui.svc_pushButton_18.isVisible() or ui.sva_pushButton_01.isVisible():
                stock_opti_buy_save(ui)
            elif ui.svo_pushButton_05.isVisible():
                stock_condbuy_save(ui)
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                coin_buy_stg_save(ui)
            elif ui.cvc_pushButton_06.isVisible() or ui.cvc_pushButton_15.isVisible() or ui.cvc_pushButton_18.isVisible() or ui.cva_pushButton_01.isVisible():
                coin_opti_buy_save(ui)
            elif ui.cvo_pushButton_05.isVisible():
                coin_condbuy_save(ui)

    elif event.key() == Qt.Key_F5:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                stock_sell_stg_load(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                stock_opti_sell_load(ui)
            elif ui.svo_pushButton_05.isVisible():
                stock_condsell_load(ui)
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                coin_sell_stg_load(ui)
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                coin_opti_sample(ui)
            elif ui.cvo_pushButton_05.isVisible():
                coin_condsell_load(ui)

    elif event.key() == Qt.Key_F6:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                ui.svjs_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_comboBoxxx_08.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_comboBoxxx_02.showPopup()
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjs_comboBoxx_01.showPopup()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_comboBoxxx_08.showPopup()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_comboBoxxx_02.showPopup()

    elif event.key() == Qt.Key_F7:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                ui.svjs_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_03.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_02.setFocus()
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                ui.cvjs_lineEditt_01.setFocus()
            elif ui.cvc_pushButton_06.isVisible() or ui.cva_pushButton_01.isVisible():
                ui.cvc_lineEdittt_03.setFocus()
            elif ui.cvo_pushButton_05.isVisible():
                ui.cvo_lineEdittt_02.setFocus()

    elif event.key() == Qt.Key_F8:
        if ui.main_btn == 3:
            if ui.svj_pushButton_01.isVisible():
                stock_sell_stg_save(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.svc_pushButton_15.isVisible() or ui.svc_pushButton_18.isVisible() or ui.sva_pushButton_01.isVisible():
                stock_opti_sell_save(ui)
            elif ui.svo_pushButton_05.isVisible():
                stock_condsell_save(ui)
        elif ui.main_btn == 4:
            if ui.cvj_pushButton_01.isVisible():
                coin_sell_stg_save(ui)
            elif ui.cvc_pushButton_06.isVisible() or ui.cvc_pushButton_15.isVisible() or ui.cvc_pushButton_18.isVisible() or ui.cva_pushButton_01.isVisible():
                coin_opti_sell_save(ui)
            elif ui.cvo_pushButton_05.isVisible():
                coin_condsell_save(ui)

    elif event.key() == Qt.Key_F9:
        if ui.main_btn == 3:
            if ui.svc_pushButton_06.isVisible():
                stock_opti_vars_load(ui)
            elif ui.sva_pushButton_03.isVisible():
                stock_gavars_load(ui)
        elif ui.main_btn == 4:
            if ui.cvc_pushButton_06.isVisible():
                coin_opti_vars_load(ui)
            elif ui.cva_pushButton_01.isVisible():
                coin_gavars_save(ui)

    elif event.key() == Qt.Key_F10:
        if ui.main_btn == 3:
            if ui.svc_pushButton_06.isVisible():
                ui.svc_comboBoxxx_02.showPopup()
            elif ui.sva_pushButton_03.isVisible():
                ui.sva_comboBoxxx_01.showPopup()
        elif ui.main_btn == 4:
            if ui.cvc_pushButton_06.isVisible():
                ui.cvc_comboBoxxx_02.showPopup()
            elif ui.cva_pushButton_01.isVisible():
                ui.cva_comboBoxxx_01.showPopup()

    elif event.key() == Qt.Key_F11:
        if ui.main_btn == 3:
            if ui.svc_pushButton_06.isVisible():
                ui.svc_lineEdittt_02.setFocus()
            elif ui.sva_pushButton_03.isVisible():
                ui.sva_lineEdittt_01.setFocus()
        elif ui.main_btn == 4:
            if ui.cvc_pushButton_06.isVisible():
                ui.cvc_lineEdittt_02.setFocus()
            elif ui.cva_pushButton_01.isVisible():
                ui.cva_lineEdittt_01.setFocus()

    elif event.key() == Qt.Key_F12:
        if ui.main_btn == 3:
            if ui.svc_pushButton_06.isVisible():
                stock_opti_vars_save(ui)
            elif ui.sva_pushButton_03.isVisible():
                stock_gavars_save(ui)
        elif ui.main_btn == 4:
            if ui.cvc_pushButton_06.isVisible():
                coin_opti_vars_save(ui)
            elif ui.cva_pushButton_03.isVisible():
                coin_gavars_save(ui)
