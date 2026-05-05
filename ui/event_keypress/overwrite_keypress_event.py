
from PyQt5.QtCore import  QDate
from ui.event_click.button_clicked_stg_editer import *
from ui.event_click.button_clicked_stg_editer_ga import *
from ui.event_click.button_clicked_stg_editer_buy import *
from ui.event_click.button_clicked_stg_editer_sell import *
from ui.event_click.button_clicked_stg_editer_opti import *
from ui.event_click.button_clicked_stg_editer_backlog import ssbutton_clicked_06
from utility.static_method.static import comma2int, comma2float, str_ymd, now_cme, now_utc
from ui.event_click.button_clicked_show_dialog import show_dialog_graph, show_dialog, show_dialog_chart


def key_press_event(_ui, event):
    """키 누름 이벤트를 처리합니다.
    Args:
        _ui: UI 클래스 인스턴스
        event: 키 이벤트
    """
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
        if _ui.dialog_scheduler.focusWidget() == _ui.sd_dpushButtonn_01:
            return

        elif QApplication.keyboardModifiers() & Qt.AltModifier:
            if backtest_process_alive(_ui):
                ssbutton_clicked_06(_ui)
            else:
                if _ui.svj_pushButton_01.isVisible():
                    backtest_start(_ui)

        elif _ui.focusWidget() in (_ui.td_tableWidgettt, _ui.gj_tableWidgettt, _ui.cj_tableWidgettt, _ui.td_tableWidgettt, _ui.gj_tableWidgettt, _ui.cj_tableWidgettt):
            row  = _ui.focusWidget().currentIndex().row()
            col  = _ui.focusWidget().currentIndex().column()
            item = _ui.focusWidget().item(row, 0)
            if item is not None:
                name       = item.text()
                linetext   = _ui.ct_lineEdittttt_03.text()
                tickcount  = int(linetext) if linetext else 30
                if _ui.market_gubun < 4 or _ui.market_gubun in (6, 7):
                    searchdate = str_ymd()
                elif _ui.market_gubun in (4, 8):
                    searchdate = str_ymd(now_cme())
                else:
                    searchdate = str_ymd(now_utc())
                code = _ui.dict_code.get(name, name)
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                show_dialog(_ui, code, name, tickcount, searchdate, col)

        elif _ui.focusWidget() in (_ui.ds_tableWidgetttt, _ui.ds_tableWidgetttt):
            if _ui.focusWidget() == _ui.ds_tableWidgetttt:
                searchdate = _ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
            else:
                searchdate = _ui.calendarWidgetttt.selectedDate().toString('yyyyMMdd')
            row  = _ui.focusWidget().currentIndex().row()
            item = _ui.focusWidget().item(row, 1)
            if item is not None:
                name      = item.text()
                linetext  = _ui.ct_lineEdittttt_03.text()
                tickcount = int(linetext) if linetext else 30
                code = _ui.dict_code.get(name, name)
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                _ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog(_ui, code, name, tickcount, searchdate, 4)

        elif _ui.focusWidget() in (_ui.ns_tableWidgetttt, _ui.cns_tableWidgettt):
            row  = _ui.focusWidget().currentIndex().row()
            item = _ui.focusWidget().item(row, 0)
            if item is not None:
                date = item.text()
                date = date.replace('.', '')
                table_name = _ui.market_info['거래디비']
                df = _ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")

                if len(date) == 6:
                    df['구분용체결시간'] = df['체결시간'].str[:6]
                    df = df[df['구분용체결시간'] == date]
                elif len(date) == 4:
                    df['구분용체결시간'] = df['체결시간'].str[:4]
                    df = df[df['구분용체결시간'] == date]

                df['index'] = df['index'].apply(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
                df.set_index('index', inplace=True)
                show_dialog_graph(_ui, df)

        elif _ui.focusWidget() in (_ui.ss_tableWidget_01, _ui.cs_tableWidget_01):
            tableWidget = _ui.ss_tableWidget_01 if _ui.focusWidget() == _ui.ss_tableWidget_01 else _ui.cs_tableWidget_01
            row  = tableWidget.currentIndex().row()
            item = tableWidget.item(row, 0)
            if item is not None:
                name       = item.text()
                searchdate = tableWidget.item(row, 2).text()[:8]
                buytime    = comma2int(tableWidget.item(row, 2).text())
                if len(str(buytime)) > 12 and not _ui.dict_set['타임프레임']:
                    QMessageBox.critical(_ui, '오류 알림', '현재 데이터 형식의 설정은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트에 표시할 수 없습니다.\n')
                    return
                if len(str(buytime)) < 14 and _ui.dict_set['타임프레임']:
                    QMessageBox.critical(_ui, '오류 알림', '현재 데이터 형식의 설정은 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트에 표시할 수 없습니다.\n')
                    return
                selltime   = comma2int(tableWidget.item(row, 3).text())
                buyprice   = comma2float(tableWidget.item(row, 5).text())
                sellprice  = comma2float(tableWidget.item(row, 6).text())
                detail     = [buytime, buyprice, selltime, sellprice]
                buytimes   = tableWidget.item(row, 13).text()
                code       = _ui.dict_code.get(name, name)
                starttime  = _ui.ct_lineEdittttt_01.text()
                endtime    = _ui.ct_lineEdittttt_02.text()
                if len(starttime) < 6 or len(endtime) < 6:
                    QMessageBox.critical(_ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
                    return
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                _ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog_chart(_ui, False, code, 30, searchdate, starttime, endtime, detail, buytimes)

    elif _ui.main_btn == 2:
        if (QApplication.keyboardModifiers() & Qt.AltModifier) and \
                event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                                Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
            if event.key() == Qt.Key_1:
                stg_editer(_ui)
            elif event.key() == Qt.Key_2:
                opti_editer(_ui)
            elif event.key() == Qt.Key_3:
                opti_test_editer(_ui)
            elif event.key() == Qt.Key_4:
                rwf_test_editer(_ui)
            elif event.key() == Qt.Key_5:
                opti_ga_editer(_ui)
            elif event.key() == Qt.Key_6:
                opti_cond_editer(_ui)
            elif event.key() == Qt.Key_7:
                opti_vars_editer(_ui)
            elif event.key() == Qt.Key_8:
                opti_gavars_editer(_ui)
            elif event.key() == Qt.Key_9:
                backtest_log(_ui)
            elif event.key() == Qt.Key_0:
                backtest_detail(_ui)

        elif event.key() == Qt.Key_F1:
            if _ui.svj_pushButton_01.isVisible():
                buy_stg_load(_ui)
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                opti_buy_load(_ui)
            elif _ui.svo_pushButton_05.isVisible():
                condbuy_load(_ui)

        elif event.key() == Qt.Key_F2:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjb_comboBoxx_01.showPopup()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_comboBoxxx_01.showPopup()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_comboBoxxx_01.showPopup()

        elif event.key() == Qt.Key_F3:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjb_lineEditt_01.setFocus()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_lineEdittt_01.setFocus()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_lineEdittt_01.setFocus()

        elif event.key() == Qt.Key_F4:
            if _ui.svj_pushButton_01.isVisible():
                buy_stg_save(_ui)
            elif _ui.svc_pushButton_06.isVisible() or _ui.svc_pushButton_15.isVisible() or _ui.svc_pushButton_18.isVisible() or _ui.sva_pushButton_01.isVisible():
                opti_buy_save(_ui)
            elif _ui.svo_pushButton_05.isVisible():
                condbuy_save(_ui)

        elif event.key() == Qt.Key_F5:
            if _ui.svj_pushButton_01.isVisible():
                sell_stg_load(_ui)
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                opti_sell_load(_ui)
            elif _ui.svo_pushButton_05.isVisible():
                condsell_load(_ui)

        elif event.key() == Qt.Key_F6:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjs_comboBoxx_01.showPopup()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_comboBoxxx_08.showPopup()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_comboBoxxx_02.showPopup()

        elif event.key() == Qt.Key_F7:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjs_lineEditt_01.setFocus()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_lineEdittt_03.setFocus()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_lineEdittt_02.setFocus()

        elif event.key() == Qt.Key_F8:
            if _ui.svj_pushButton_01.isVisible():
                sell_stg_save(_ui)
            elif _ui.svc_pushButton_06.isVisible() or _ui.svc_pushButton_15.isVisible() or _ui.svc_pushButton_18.isVisible() or _ui.sva_pushButton_01.isVisible():
                opti_sell_save(_ui)
            elif _ui.svo_pushButton_05.isVisible():
                condsell_save(_ui)

        elif event.key() == Qt.Key_F9:
            if _ui.svc_pushButton_06.isVisible():
                opti_vars_load(_ui)
            elif _ui.sva_pushButton_03.isVisible():
                gavars_load(_ui)

        elif event.key() == Qt.Key_F10:
            if _ui.svc_pushButton_06.isVisible():
                _ui.svc_comboBoxxx_02.showPopup()
            elif _ui.sva_pushButton_03.isVisible():
                _ui.sva_comboBoxxx_01.showPopup()

        elif event.key() == Qt.Key_F11:
            if _ui.svc_pushButton_06.isVisible():
                _ui.svc_lineEdittt_02.setFocus()
            elif _ui.sva_pushButton_03.isVisible():
                _ui.sva_lineEdittt_01.setFocus()

        elif event.key() == Qt.Key_F12:
            if _ui.svc_pushButton_06.isVisible():
                opti_vars_save(_ui)
            elif _ui.sva_pushButton_03.isVisible():
                gavars_save(_ui)
