
from PyQt5.QtCore import  QDate
from ui.event_click.button_clicked_stg_editer import *
from ui.event_click.button_clicked_stg_editer_ga import *
from ui.event_click.button_clicked_stg_editer_buy import *
from ui.event_click.button_clicked_stg_editer_sell import *
from ui.event_click.button_clicked_stg_editer_opti import *
from ui.event_click.button_clicked_stg_editer_backlog import ssbutton_clicked_06
from utility.static_method.static import comma2int, comma2float, str_ymd, now_cme, now_utc
from ui.event_click.button_clicked_show_dialog import show_dialog_graph, show_dialog, show_dialog_chart


def key_press_event(ui, event):
    """키 누름 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
        event: 키 이벤트
    """
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
        if ui.dialog_scheduler.focusWidget() == ui.sd_dpushButtonn_01:
            return

        elif QApplication.keyboardModifiers() & Qt.AltModifier:
            if backtest_process_alive(ui):
                ssbutton_clicked_06(ui)
            else:
                if ui.svj_pushButton_01.isVisible():
                    backtest_start(ui)

        elif ui.focusWidget() in (ui.td_tableWidgettt, ui.gj_tableWidgettt, ui.cj_tableWidgettt):
            row  = ui.focusWidget().currentIndex().row()
            col  = ui.focusWidget().currentIndex().column()
            item = ui.focusWidget().item(row, 0)
            if item is not None:
                name       = item.text()
                linetext   = ui.ct_lineEdittttt_03.text()
                tickcount  = int(linetext) if linetext else 30
                if ui.market_gubun < 4 or ui.market_gubun in (6, 7):
                    searchdate = str_ymd()
                elif ui.market_gubun in (4, 8):
                    searchdate = str_ymd(now_cme())
                else:
                    searchdate = str_ymd(now_utc())
                code = ui.dict_code.get(name, name)
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                show_dialog(ui, code, name, tickcount, searchdate, col)

        elif ui.focusWidget() == ui.ds_tableWidgetttt:
            if ui.focusWidget() == ui.ds_tableWidgetttt:
                searchdate = ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
            else:
                searchdate = ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
            row  = ui.focusWidget().currentIndex().row()
            item = ui.focusWidget().item(row, 1)
            if item is not None:
                name      = item.text()
                linetext  = ui.ct_lineEdittttt_03.text()
                tickcount = int(linetext) if linetext else 30
                code = ui.dict_code.get(name, name)
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog(ui, code, name, tickcount, searchdate, 4)

        elif ui.focusWidget() == ui.ns_tableWidgetttt:
            row  = ui.focusWidget().currentIndex().row()
            item = ui.focusWidget().item(row, 0)
            if item is not None:
                date = item.text()
                date = date.replace('.', '')
                table_name = ui.market_info['거래디비']
                df = ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")

                if len(date) == 6:
                    df['구분용체결시간'] = df['체결시간'].str[:6]
                    df = df[df['구분용체결시간'] == date]
                elif len(date) == 4:
                    df['구분용체결시간'] = df['체결시간'].str[:4]
                    df = df[df['구분용체결시간'] == date]

                df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
                df.set_index('index', inplace=True)
                show_dialog_graph(ui, df)

        elif ui.focusWidget() == ui.ss_tableWidget_01:
            tableWidget = ui.ss_tableWidget_01
            row  = tableWidget.currentIndex().row()
            item = tableWidget.item(row, 0)
            if item is not None:
                name       = item.text()
                searchdate = tableWidget.item(row, 2).text()[:8]
                buytime    = comma2int(tableWidget.item(row, 2).text())
                if len(str(buytime)) > 12 and not ui.dict_set['타임프레임']:
                    QMessageBox.critical(
                        ui, '오류 알림',
                        '현재 데이터 형식의 설정은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트에 표시할 수 없습니다.\n'
                    )
                    return
                if len(str(buytime)) < 14 and ui.dict_set['타임프레임']:
                    QMessageBox.critical(
                        ui, '오류 알림',
                        '현재 데이터 형식의 설정은 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트에 표시할 수 없습니다.\n'
                    )
                    return
                selltime   = comma2int(tableWidget.item(row, 3).text())
                buyprice   = comma2float(tableWidget.item(row, 5).text())
                sellprice  = comma2float(tableWidget.item(row, 6).text())
                detail     = [buytime, buyprice, selltime, sellprice]
                buytimes   = tableWidget.item(row, 13).text()
                code       = ui.dict_code.get(name, name)
                starttime  = ui.ct_lineEdittttt_01.text()
                endtime    = ui.ct_lineEdittttt_02.text()
                if len(starttime) < 6 or len(endtime) < 6:
                    QMessageBox.critical(
                        ui.dialog_chart, '오류 알림',
                        '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n'
                    )
                    return
                ui.ct_lineEdittttt_04.setText(code)
                ui.ct_lineEdittttt_05.setText(name)
                ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog_chart(ui, False, code, 30, searchdate, starttime, endtime, detail, buytimes)

    elif ui.main_btn == 2:
        if (QApplication.keyboardModifiers() & Qt.AltModifier) and \
                event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                                Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
            if event.key() == Qt.Key_1:
                stg_editer(ui)
            elif event.key() == Qt.Key_2:
                opti_editer(ui)
            elif event.key() == Qt.Key_3:
                opti_test_editer(ui)
            elif event.key() == Qt.Key_4:
                rwf_test_editer(ui)
            elif event.key() == Qt.Key_5:
                opti_ga_editer(ui)
            elif event.key() == Qt.Key_6:
                opti_cond_editer(ui)
            elif event.key() == Qt.Key_7:
                opti_vars_editer(ui)
            elif event.key() == Qt.Key_8:
                opti_gavars_editer(ui)
            elif event.key() == Qt.Key_9:
                backtest_log(ui)
            elif event.key() == Qt.Key_0:
                backtest_detail(ui)

        elif event.key() == Qt.Key_F1:
            if ui.svj_pushButton_01.isVisible():
                buy_stg_load(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                opti_buy_load(ui)
            elif ui.svo_pushButton_05.isVisible():
                condbuy_load(ui)

        elif event.key() == Qt.Key_F2:
            if ui.svj_pushButton_01.isVisible():
                ui.svjb_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_comboBoxxx_01.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_comboBoxxx_01.showPopup()

        elif event.key() == Qt.Key_F3:
            if ui.svj_pushButton_01.isVisible():
                ui.svjb_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_01.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_01.setFocus()

        elif event.key() == Qt.Key_F4:
            if ui.svj_pushButton_01.isVisible():
                buy_stg_save(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.svc_pushButton_15.isVisible() or \
                    ui.svc_pushButton_18.isVisible() or ui.sva_pushButton_01.isVisible():
                opti_buy_save(ui)
            elif ui.svo_pushButton_05.isVisible():
                condbuy_save(ui)

        elif event.key() == Qt.Key_F5:
            if ui.svj_pushButton_01.isVisible():
                sell_stg_load(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                opti_sell_load(ui)
            elif ui.svo_pushButton_05.isVisible():
                condsell_load(ui)

        elif event.key() == Qt.Key_F6:
            if ui.svj_pushButton_01.isVisible():
                ui.svjs_comboBoxx_01.showPopup()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_comboBoxxx_08.showPopup()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_comboBoxxx_02.showPopup()

        elif event.key() == Qt.Key_F7:
            if ui.svj_pushButton_01.isVisible():
                ui.svjs_lineEditt_01.setFocus()
            elif ui.svc_pushButton_06.isVisible() or ui.sva_pushButton_03.isVisible():
                ui.svc_lineEdittt_03.setFocus()
            elif ui.svo_pushButton_05.isVisible():
                ui.svo_lineEdittt_02.setFocus()

        elif event.key() == Qt.Key_F8:
            if ui.svj_pushButton_01.isVisible():
                sell_stg_save(ui)
            elif ui.svc_pushButton_06.isVisible() or ui.svc_pushButton_15.isVisible() or \
                    ui.svc_pushButton_18.isVisible() or ui.sva_pushButton_01.isVisible():
                opti_sell_save(ui)
            elif ui.svo_pushButton_05.isVisible():
                condsell_save(ui)

        elif event.key() == Qt.Key_F9:
            if ui.svc_pushButton_06.isVisible():
                opti_vars_load(ui)
            elif ui.sva_pushButton_03.isVisible():
                gavars_load(ui)

        elif event.key() == Qt.Key_F10:
            if ui.svc_pushButton_06.isVisible():
                ui.svc_comboBoxxx_02.showPopup()
            elif ui.sva_pushButton_03.isVisible():
                ui.sva_comboBoxxx_01.showPopup()

        elif event.key() == Qt.Key_F11:
            if ui.svc_pushButton_06.isVisible():
                ui.svc_lineEdittt_02.setFocus()
            elif ui.sva_pushButton_03.isVisible():
                ui.sva_lineEdittt_01.setFocus()

        elif event.key() == Qt.Key_F12:
            if ui.svc_pushButton_06.isVisible():
                opti_vars_save(ui)
            elif ui.sva_pushButton_03.isVisible():
                gavars_save(ui)
