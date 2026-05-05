
def key_press_event(ui, event):
    """키 누름 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
        event: 키 이벤트
    """
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_stg_editer import backtest_start
    from ui.event_click.button_clicked_stg_editer_backlog import ssbutton_clicked_06
    from ui.event_click.button_clicked_stg_editer_buy import buy_stg_load, buy_stg_save
    from ui.event_click.button_clicked_stg_editer_sell import sell_stg_load, sell_stg_save
    from ui.event_click.table_cell_clicked import cell_clicked_05, cell_clicked_04, cell_clicked_03, cell_clicked_01
    from ui.event_click.button_clicked_stg_editer_ga import condbuy_load, condbuy_save, condsell_load, condsell_save, \
        gavars_load, gavars_save
    from ui.event_click.button_clicked_stg_editer_opti import opti_buy_load, opti_buy_save, opti_sell_load, opti_sell_save, \
        opti_vars_load, opti_vars_save
    from ui.event_click.button_clicked_stg_editer import stg_editer, opti_editer, opti_test_editer, rwf_test_editer, \
        opti_ga_editer, opti_cond_editer, opti_vars_editer, opti_gavars_editer, backtest_log, backtest_detail

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
            cell_clicked_01(ui, row, col)

        elif ui.focusWidget() == ui.ds_tableWidgetttt:
            row = ui.ds_tableWidgetttt.currentIndex().row()
            cell_clicked_03(ui, row, 0)

        elif ui.focusWidget() == ui.ns_tableWidgetttt:
            row = ui.ns_tableWidgetttt.currentIndex().row()
            cell_clicked_04(ui, row, 0)

        elif ui.focusWidget() == ui.ss_tableWidget_01:
            row = ui.ss_tableWidget_01.currentIndex().row()
            cell_clicked_05(ui, row, 0)

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
