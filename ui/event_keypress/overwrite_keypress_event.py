from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ui.event_click.table_cell_clicked import *
from ui.event_click.button_clicked_shortcut import *
from ui.event_click.button_clicked_stg_editer import *
from ui.event_click.button_clicked_show_dialog import *
from ui.event_click.button_clicked_stg_editer_ga import *
from ui.event_click.button_clicked_stg_editer_opti import *

from ui.event_keypress.extend_window import extend_window
from ui.etcetera.process_alive import backtest_process_alive
from ui.etcetera.etc import chart_screenshot, manual_save_and_exit
from ui.event_click.button_clicked_stg_editer_backlog import ssbutton_clicked_06
from ui.event_click.button_clicked_stg_editer_buy import buy_stg_load, buy_stg_save
from ui.event_click.button_clicked_stg_editer_sell import sell_stg_load, sell_stg_save
from ui.event_click.button_clicked_etc import hg_button_clicked_01, hg_button_clicked_02


def key_press_event(ui, event):
    """키 누름 이벤트를 처리합니다."""
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

    elif QApplication.keyboardModifiers() & Qt.AltModifier:
        if ui.main_btn == 2 and \
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

        elif event.key() in (Qt.Key_T, Qt.Key_L, Qt.Key_D, Qt.Key_Z, Qt.Key_K, Qt.Key_C, Qt.Key_H, Qt.Key_G,
                             Qt.Key_U, Qt.Key_Q, Qt.Key_B, Qt.Key_X, Qt.Key_S, Qt.Key_V, Qt.Key_O, Qt.Key_E,
                             Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            if event.key() == Qt.Key_T:
                mnbutton_c_clicked_02(ui)
            elif event.key() == Qt.Key_L:
                mnbutton_c_clicked_03(ui)
            elif event.key() == Qt.Key_D:
                show_db(ui)
            elif event.key() == Qt.Key_Z:
                mnbutton_c_clicked_04(ui)
            elif event.key() == Qt.Key_K:
                show_kimp(ui)
            elif event.key() == Qt.Key_C:
                show_chart(ui)
            elif event.key() == Qt.Key_H:
                show_hoga(ui)
            elif event.key() == Qt.Key_G:
                show_giup(ui)
            elif event.key() == Qt.Key_U:
                show_treemap(ui)
            elif event.key() == Qt.Key_Q:
                show_qsize(ui)
            elif event.key() == Qt.Key_B:
                show_backscheduler(ui)
            elif event.key() == Qt.Key_X:
                trade_process_kill(ui)
            elif event.key() == Qt.Key_S:
                chart_screenshot(ui)
            elif event.key() == Qt.Key_V:
                manual_save_and_exit(ui)
            elif event.key() == Qt.Key_O:
                show_order(ui)
            elif event.key() == Qt.Key_E:
                extend_window(ui)
            elif event.key() == Qt.Key_Left:
                hg_button_clicked_01(ui, '이전')
            elif event.key() == Qt.Key_Right:
                hg_button_clicked_01(ui, '다음')
            elif event.key() == Qt.Key_Up:
                hg_button_clicked_02(ui, '매수')
            elif event.key() == Qt.Key_Down:
                hg_button_clicked_02(ui, '매도')

    elif QApplication.keyboardModifiers() & Qt.ControlModifier:
        if event.key() in (Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_5, Qt.Key_6, Qt.Key_B, Qt.Key_A):
            if event.key() == Qt.Key_1:
                mnbutton_c_clicked_01(ui, 0)
            elif event.key() == Qt.Key_2:
                mnbutton_c_clicked_01(ui, 1)
            elif event.key() == Qt.Key_3:
                mnbutton_c_clicked_01(ui, 2)
            elif event.key() == Qt.Key_4:
                mnbutton_c_clicked_01(ui, 3)
            elif event.key() == Qt.Key_5:
                mnbutton_c_clicked_01(ui, 4)
            elif event.key() == Qt.Key_6:
                mnbutton_c_clicked_01(ui, 5)
            elif event.key() == Qt.Key_B:
                mnbutton_c_clicked_05(ui)
            elif event.key() == Qt.Key_A:
                mnbutton_c_clicked_06(ui)

    elif ui.main_btn == 2 and \
            event.key() in (Qt.Key_F1, Qt.Key_F2, Qt.Key_F3, Qt.Key_F4, Qt.Key_F5, Qt.Key_F6, Qt.Key_F7, Qt.Key_F8,
                            Qt.Key_F9, Qt.Key_F10, Qt.Key_F11, Qt.Key_F12):
        if event.key() == Qt.Key_F1:
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
