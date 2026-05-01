
from PyQt5.QtCore import  QDate
from ui.ui_button_clicked_editer_unified import *
from ui.ui_button_clicked_editer_ga_unified import *
from ui.ui_button_clicked_editer_opti_unified import *
from ui.ui_button_clicked_editer_stg_buy_unified import *
from ui.ui_button_clicked_editer_stg_sell_unified import *
from utility.static import comma2int, comma2float, str_ymd, now_cme, now_utc
from ui.ui_show_dialog import show_dialog_graph, show_dialog, show_dialog_chart
from ui.ui_button_clicked_editer_backlog import csbutton_clicked_06, ssbutton_clicked_06


@error_decorator
def key_press_event(_ui, event):
    if event.key() in (Qt.Key_Return, Qt.Key_Enter):
        if _ui.dialog_scheduler.focusWidget() == _ui.sd_dpushButtonn_01:
            return

        elif QApplication.keyboardModifiers() & Qt.AltModifier:
            if backtest_process_alive(_ui):
                if _ui.main_btn == 3:
                    ssbutton_clicked_06(_ui)
                elif _ui.main_btn == 4:
                    csbutton_clicked_06(_ui)
            else:
                if _ui.main_btn == 3:
                    if _ui.svj_pushButton_01.isVisible():
                        backtest_start(_ui, 'stock')
                elif _ui.main_btn == 4:
                    if _ui.cvj_pushButton_01.isVisible():
                        backtest_start(_ui, 'coin')

        elif _ui.focusWidget() in (_ui.std_tableWidgettt, _ui.sgj_tableWidgettt, _ui.scj_tableWidgettt, _ui.ctd_tableWidgettt, _ui.cgj_tableWidgettt, _ui.ccj_tableWidgettt):
            stock = True
            if _ui.focusWidget() in (_ui.ctd_tableWidgettt, _ui.cgj_tableWidgettt, _ui.ccj_tableWidgettt):
                stock = False
            row  = _ui.focusWidget().currentIndex().row()
            col  = _ui.focusWidget().currentIndex().column()
            item = _ui.focusWidget().item(row, 0)
            if item is not None:
                name       = item.text()
                linetext   = _ui.ct_lineEdittttt_03.text()
                tickcount  = int(linetext) if linetext else 30
                searchdate = str_ymd(now_utc()) if not stock else str_ymd() if '키움증권' in _ui.dict_set['증권사'] else str_ymd(now_cme())
                code       = _ui.dict_code[name] if name in _ui.dict_code else name
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                show_dialog(_ui, name, tickcount, searchdate, col)

        elif _ui.focusWidget() in (_ui.sds_tableWidgettt, _ui.cds_tableWidgettt):
            if _ui.focusWidget() == _ui.sds_tableWidgettt:
                searchdate = _ui.s_calendarWidgett.selectedDate().toString('yyyyMMdd')
            else:
                searchdate = _ui.c_calendarWidgett.selectedDate().toString('yyyyMMdd')
            row  = _ui.focusWidget().currentIndex().row()
            item = _ui.focusWidget().item(row, 1)
            if item is not None:
                name      = item.text()
                linetext  = _ui.ct_lineEdittttt_03.text()
                tickcount = int(linetext) if linetext else 30
                code      = _ui.dict_code[name] if name in _ui.dict_code else name
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                _ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog(_ui, name, tickcount, searchdate, 4)

        elif _ui.focusWidget() in (_ui.sns_tableWidgettt, _ui.cns_tableWidgettt):
            if _ui.focusWidget() == _ui.sns_tableWidgettt:
                gubun_ = '주식'
            else:
                gubun_ = '코인'
            row  = _ui.focusWidget().currentIndex().row()
            item = _ui.focusWidget().item(row, 0)
            if item is not None:
                date = item.text()
                date = date.replace('.', '')
                if gubun_ == '주식':
                    table_name = 's_tradelist' if '키움증권' in _ui.dict_set['증권사'] else 'f_tradelist'
                else:
                    table_name = 'c_tradelist' if _ui.dict_set['거래소'] == '업비트' else 'c_tradelist_future'
                df = _ui.dbreader.read_sql('거래디비', f"SELECT * FROM {table_name} WHERE 체결시간 LIKE '{date}%'")
                if len(date) == 6 and gubun_ == '코인':
                    df['구분용체결시간'] = df['체결시간'].str[:6]
                    df = df[df['구분용체결시간'] == date]
                elif len(date) == 4 and gubun_ == '코인':
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
                selltime   = comma2int(tableWidget.item(row, 3).text())
                buyprice   = comma2float(tableWidget.item(row, 5).text())
                sellprice  = comma2float(tableWidget.item(row, 6).text())
                detail     = [buytime, buyprice, selltime, sellprice]
                buytimes   = tableWidget.item(row, 13).text()
                coin       = True if 'KRW' in name or 'USDT' in name else False
                code       = _ui.dict_code[name] if name in _ui.dict_code else name
                starttime  = _ui.ct_lineEdittttt_01.text()
                endtime    = _ui.ct_lineEdittttt_02.text()
                if len(str(buytime)) > 12 and (coin and not _ui.dict_set['코인타임프레임'] or not coin and not _ui.dict_set['주식타임프레임']):
                    QMessageBox.critical(_ui, '오류 알림', '현재 전략설정의 데이터타입은 1분봉 상태입니다.\n1초스냅샷용 백테결과는 차트를 표시할 수 없습니다.\n')
                    return
                if len(str(buytime)) < 14 and (coin and _ui.dict_set['코인타임프레임'] or not coin and _ui.dict_set['주식타임프레임']):
                    QMessageBox.critical(_ui, '오류 알림', '현재 전략설정의 데이터타입은 1초스냅샷 상태입니다.\n1분봉용 백테결과는 차트를 표시할 수 없습니다.\n')
                    return
                if len(starttime) < 6 or len(endtime) < 6:
                    QMessageBox.critical(_ui.dialog_chart, '오류 알림', '차트의 시작 및 종료시간은 초단위까지로 입력하십시오.\n(예: 000000, 090000, 152000)\n')
                    return
                _ui.ct_lineEdittttt_04.setText(code)
                _ui.ct_lineEdittttt_05.setText(name)
                _ui.ct_dateEdittttt_01.setDate(QDate.fromString(searchdate, 'yyyyMMdd'))
                show_dialog_chart(_ui, False, coin, code, 30, searchdate, starttime, endtime, detail, buytimes)

    elif (QApplication.keyboardModifiers() & Qt.AltModifier) and \
            event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5,
                            Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9, Qt.Key_0):
        gubun_ = 'stock' if _ui.main_btn == 3 else 'coin'
        if event.key() == Qt.Key_1:
            stg_editer(_ui, gubun_)
        elif event.key() == Qt.Key_2:
            opti_editer(_ui, gubun_)
        elif event.key() == Qt.Key_3:
            opti_test_editer(_ui, gubun_)
        elif event.key() == Qt.Key_4:
            rwf_test_editer(_ui, gubun_)
        elif event.key() == Qt.Key_5:
            opti_ga_editer(_ui, gubun_)
        elif event.key() == Qt.Key_6:
            cond_editer(_ui, gubun_)
        elif event.key() == Qt.Key_7:
            opti_vars_editer(_ui, gubun_)
        elif event.key() == Qt.Key_8:
            vars_editer(_ui, gubun_)
        elif event.key() == Qt.Key_9:
            backtest_log(_ui, gubun_)
        elif event.key() == Qt.Key_0:
            backtest_detail(_ui, gubun_)

    elif event.key() == Qt.Key_F1:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                buy_stg_load(_ui, 'stock')
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                opti_buy_load(_ui, 'stock')
            elif _ui.svo_pushButton_05.isVisible():
                condbuy_load(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                buy_stg_load(_ui, 'coin')
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                opti_buy_load(_ui, 'coin')
            elif _ui.cvo_pushButton_05.isVisible():
                condbuy_load(_ui, 'coin')

    elif event.key() == Qt.Key_F2:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjb_comboBoxx_01.showPopup()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_comboBoxxx_01.showPopup()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_comboBoxxx_01.showPopup()
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                _ui.cvjb_comboBoxx_01.showPopup()
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                _ui.cvc_comboBoxxx_01.showPopup()
            elif _ui.cvo_pushButton_05.isVisible():
                _ui.cvo_comboBoxxx_01.showPopup()

    elif event.key() == Qt.Key_F3:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjb_lineEditt_01.setFocus()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_lineEdittt_01.setFocus()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_lineEdittt_01.setFocus()
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                _ui.cvjb_lineEditt_01.setFocus()
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                _ui.cvc_lineEdittt_01.setFocus()
            elif _ui.cvo_pushButton_05.isVisible():
                _ui.cvo_lineEdittt_01.setFocus()

    elif event.key() == Qt.Key_F4:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                buy_stg_save(_ui, 'stock')
            elif _ui.svc_pushButton_06.isVisible() or _ui.svc_pushButton_15.isVisible() or _ui.svc_pushButton_18.isVisible() or _ui.sva_pushButton_01.isVisible():
                opti_buy_save(_ui, 'stock')
            elif _ui.svo_pushButton_05.isVisible():
                condbuy_save(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                buy_stg_save(_ui, 'coin')
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cvc_pushButton_15.isVisible() or _ui.cvc_pushButton_18.isVisible() or _ui.cva_pushButton_01.isVisible():
                opti_buy_save(_ui, 'coin')
            elif _ui.cvo_pushButton_05.isVisible():
                condbuy_save(_ui, 'coin')

    elif event.key() == Qt.Key_F5:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                sell_stg_load(_ui, 'stock')
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                opti_sell_load(_ui, 'stock')
            elif _ui.svo_pushButton_05.isVisible():
                condsell_load(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                sell_stg_load(_ui, 'coin')
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                opti_sample(_ui, 'coin')
            elif _ui.cvo_pushButton_05.isVisible():
                condsell_load(_ui, 'coin')

    elif event.key() == Qt.Key_F6:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjs_comboBoxx_01.showPopup()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_comboBoxxx_08.showPopup()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_comboBoxxx_02.showPopup()
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                _ui.cvjs_comboBoxx_01.showPopup()
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                _ui.cvc_comboBoxxx_08.showPopup()
            elif _ui.cvo_pushButton_05.isVisible():
                _ui.cvo_comboBoxxx_02.showPopup()

    elif event.key() == Qt.Key_F7:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                _ui.svjs_lineEditt_01.setFocus()
            elif _ui.svc_pushButton_06.isVisible() or _ui.sva_pushButton_03.isVisible():
                _ui.svc_lineEdittt_03.setFocus()
            elif _ui.svo_pushButton_05.isVisible():
                _ui.svo_lineEdittt_02.setFocus()
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                _ui.cvjs_lineEditt_01.setFocus()
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cva_pushButton_01.isVisible():
                _ui.cvc_lineEdittt_03.setFocus()
            elif _ui.cvo_pushButton_05.isVisible():
                _ui.cvo_lineEdittt_02.setFocus()

    elif event.key() == Qt.Key_F8:
        if _ui.main_btn == 3:
            if _ui.svj_pushButton_01.isVisible():
                sell_stg_save(_ui, 'stock')
            elif _ui.svc_pushButton_06.isVisible() or _ui.svc_pushButton_15.isVisible() or _ui.svc_pushButton_18.isVisible() or _ui.sva_pushButton_01.isVisible():
                opti_sell_save(_ui, 'stock')
            elif _ui.svo_pushButton_05.isVisible():
                condsell_save(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvj_pushButton_01.isVisible():
                sell_stg_save(_ui, 'coin')
            elif _ui.cvc_pushButton_06.isVisible() or _ui.cvc_pushButton_15.isVisible() or _ui.cvc_pushButton_18.isVisible() or _ui.cva_pushButton_01.isVisible():
                opti_sell_save(_ui, 'coin')
            elif _ui.cvo_pushButton_05.isVisible():
                condsell_save(_ui, 'coin')

    elif event.key() == Qt.Key_F9:
        if _ui.main_btn == 3:
            if _ui.svc_pushButton_06.isVisible():
                opti_vars_load(_ui, 'stock')
            elif _ui.sva_pushButton_03.isVisible():
                gavars_load(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvc_pushButton_06.isVisible():
                opti_vars_load(_ui, 'coin')
            elif _ui.cva_pushButton_01.isVisible():
                gavars_save(_ui, 'coin')

    elif event.key() == Qt.Key_F10:
        if _ui.main_btn == 3:
            if _ui.svc_pushButton_06.isVisible():
                _ui.svc_comboBoxxx_02.showPopup()
            elif _ui.sva_pushButton_03.isVisible():
                _ui.sva_comboBoxxx_01.showPopup()
        elif _ui.main_btn == 4:
            if _ui.cvc_pushButton_06.isVisible():
                _ui.cvc_comboBoxxx_02.showPopup()
            elif _ui.cva_pushButton_01.isVisible():
                _ui.cva_comboBoxxx_01.showPopup()

    elif event.key() == Qt.Key_F11:
        if _ui.main_btn == 3:
            if _ui.svc_pushButton_06.isVisible():
                _ui.svc_lineEdittt_02.setFocus()
            elif _ui.sva_pushButton_03.isVisible():
                _ui.sva_lineEdittt_01.setFocus()
        elif _ui.main_btn == 4:
            if _ui.cvc_pushButton_06.isVisible():
                _ui.cvc_lineEdittt_02.setFocus()
            elif _ui.cva_pushButton_01.isVisible():
                _ui.cva_lineEdittt_01.setFocus()

    elif event.key() == Qt.Key_F12:
        if _ui.main_btn == 3:
            if _ui.svc_pushButton_06.isVisible():
                opti_vars_save(_ui, 'stock')
            elif _ui.sva_pushButton_03.isVisible():
                gavars_save(_ui, 'stock')
        elif _ui.main_btn == 4:
            if _ui.cvc_pushButton_06.isVisible():
                opti_vars_save(_ui, 'coin')
            elif _ui.cva_pushButton_03.isVisible():
                gavars_save(_ui, 'coin')
