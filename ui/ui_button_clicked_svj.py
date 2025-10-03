from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QApplication
from multiprocessing import Process
from backtester.optimiz import Optimize
from backtester.backtest import BackTest
from backtester.backfinder import BackFinder
from backtester.optimiz_conditions import OptimizeConditions
from backtester.rolling_walk_forward_test import RollingWalkForwardTest
from backtester.optimiz_genetic_algorithm import OptimizeGeneticAlgorithm
from ui.set_style import style_bc_by, style_bc_dk, style_bc_bs, style_bc_bd
from ui.set_text import testtext, rwfttext, gaoptext, vedittxt, optitext, condtext, cedittxt, example_finder


def svj_button_clicked_01(ui):
    ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_04.setGeometry(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    ui.ss_textEditttt_05.setGeometry(659, 10, 347, 1347 if ui.extend_window else 740)

    ui.svc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 150, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 150, 165, 30)

    ui.szoo_pushButon_01.setGeometry(599, 15, 50, 20)
    ui.szoo_pushButon_02.setGeometry(599, 761 if ui.extend_window else 483, 50, 20)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(True)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)
    for item in ui.stock_optest_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(testtext)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_09.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_02(ui):
    ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_04.setGeometry(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    ui.ss_textEditttt_05.setGeometry(659, 10, 347, 1347 if ui.extend_window else 740)

    ui.svc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 150, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 150, 165, 30)

    ui.szoo_pushButon_01.setGeometry(599, 15, 50, 20)
    ui.szoo_pushButon_02.setGeometry(599, 761 if ui.extend_window else 483, 50, 20)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(True)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)
    for item in ui.stock_rwftvd_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_01.setVisible(False)
    ui.svc_labellllll_04.setText(rwfttext)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_07.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_03(ui):
    ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_04.setGeometry(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    ui.ss_textEditttt_06.setGeometry(659, 10, 347, 1347 if ui.extend_window else 740)

    ui.svc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 150, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 150, 165, 30)

    ui.sva_comboBoxxx_01.setGeometry(1012, 115, 165, 30)
    ui.sva_lineEdittt_01.setGeometry(1182, 115, 165, 30)
    ui.sva_pushButton_04.setGeometry(1012, 150, 165, 30)
    ui.sva_pushButton_05.setGeometry(1182, 150, 165, 30)

    ui.szoo_pushButon_01.setGeometry(599, 15, 50, 20)
    ui.szoo_pushButon_02.setGeometry(599, 761 if ui.extend_window else 483, 50, 20)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(True)

    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(True)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)
    for item in ui.stock_gaopti_list:
        item.setVisible(True)

    ui.sva_pushButton_04.setText('GA 변수범위 로딩(F9)')
    ui.sva_pushButton_05.setText('GA 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(gaoptext)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_08.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_04(ui):
    ui.ss_textEditttt_05.setGeometry(7, 10, 497, 1347 if ui.extend_window else 740)
    ui.ss_textEditttt_06.setGeometry(509, 10, 497, 1347 if ui.extend_window else 740)

    ui.svc_comboBoxxx_02.setGeometry(1012, 10, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 10, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 45, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 45, 165, 30)

    ui.sva_comboBoxxx_01.setGeometry(1012, 80, 165, 30)
    ui.sva_lineEdittt_01.setGeometry(1182, 80, 165, 30)
    ui.sva_pushButton_04.setGeometry(1012, 115, 165, 30)
    ui.sva_pushButton_05.setGeometry(1182, 115, 165, 30)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(True)

    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(False)
    for item in ui.stock_optimz_list:
        item.setVisible(False)
    for item in ui.stock_period_list:
        item.setVisible(True)
    for item in ui.stock_gaopti_list:
        item.setVisible(True)

    ui.sva_pushButton_04.setText('GA 변수범위 로딩')
    ui.sva_pushButton_05.setText('GA 변수범위 저장')
    ui.svc_pushButton_03.setText('최적화 변수범위 로딩')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장')

    ui.svc_pushButton_06.setVisible(False)
    ui.svc_pushButton_07.setVisible(False)
    ui.svc_pushButton_08.setVisible(False)
    ui.svc_pushButton_27.setVisible(False)
    ui.svc_pushButton_28.setVisible(False)
    ui.svc_pushButton_29.setVisible(False)

    ui.sva_pushButton_01.setVisible(False)
    ui.sva_pushButton_02.setVisible(False)
    ui.sva_pushButton_03.setVisible(False)

    ui.svc_comboBoxxx_02.setVisible(True)
    ui.svc_lineEdittt_02.setVisible(True)
    ui.svc_pushButton_03.setVisible(True)
    ui.svc_pushButton_04.setVisible(True)

    ui.svc_pushButton_11.setVisible(True)

    ui.image_label1.setVisible(True)
    ui.svc_labellllll_05.setVisible(True)
    ui.svc_labellllll_04.setText(gaoptext)
    ui.svc_labellllll_05.setText(vedittxt)
    ui.svc_pushButton_21.setVisible(True)
    ui.svc_pushButton_22.setVisible(True)
    ui.svc_pushButton_23.setVisible(True)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_12.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_05(ui):
    ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_04.setGeometry(7, 756 if ui.extend_window else 478, 647, 602 if ui.extend_window else 272)
    ui.ss_textEditttt_05.setGeometry(659, 10, 347, 1347 if ui.extend_window else 740)

    ui.svc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 150, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 150, 165, 30)

    ui.szoo_pushButon_01.setGeometry(599, 15, 50, 20)
    ui.szoo_pushButon_02.setGeometry(599, 761 if ui.extend_window else 483, 50, 20)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(True)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(True)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)

    ui.svc_pushButton_03.setText('최적화 변수범위 로딩(F9)')
    ui.svc_pushButton_04.setText('최적화 변수범위 저장(F12)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(optitext)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_11.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_06(ui):
    ui.ss_textEditttt_01.setGeometry(7, 10, 497, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_02.setGeometry(7, 756 if ui.extend_window else 478, 497, 602 if ui.extend_window else 272)
    ui.ss_textEditttt_03.setGeometry(509, 10, 497, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_04.setGeometry(509, 756 if ui.extend_window else 478, 497, 602 if ui.extend_window else 272)

    ui.svjb_comboBoxx_01.setGeometry(1012, 10, 165, 30)
    ui.svjb_pushButon_01.setGeometry(1182, 10, 165, 30)
    ui.svjs_comboBoxx_01.setGeometry(1012, 478, 165, 30)
    ui.svjs_pushButon_01.setGeometry(1182, 478, 165, 30)

    ui.svc_comboBoxxx_02.setGeometry(1012, 115, 165, 30)
    ui.svc_lineEdittt_02.setGeometry(1182, 115, 165, 30)
    ui.svc_pushButton_03.setGeometry(1012, 150, 165, 30)
    ui.svc_pushButton_04.setGeometry(1182, 150, 165, 30)

    ui.ss_textEditttt_01.setVisible(True)
    ui.ss_textEditttt_02.setVisible(True)
    ui.ss_textEditttt_03.setVisible(True)
    ui.ss_textEditttt_04.setVisible(True)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_esczom_list:
        item.setVisible(False)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)

    ui.svjb_pushButon_01.setText('매수전략 로딩')
    ui.svjs_pushButon_01.setText('매도전략 로딩')

    ui.svjb_comboBoxx_01.setVisible(True)
    ui.svjb_pushButon_01.setVisible(True)
    ui.svjs_comboBoxx_01.setVisible(True)
    ui.svjs_pushButon_01.setVisible(True)

    ui.svc_lineEdittt_04.setVisible(False)
    ui.svc_pushButton_13.setVisible(False)
    ui.svc_lineEdittt_05.setVisible(False)
    ui.svc_pushButton_14.setVisible(False)

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_04.setText(optitext)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(True)
    ui.svc_pushButton_25.setVisible(True)
    ui.svc_pushButton_26.setVisible(True)

    ui.svj_pushButton_16.setFocus()
    sChangeSvjButtonColor(ui)


def change_pre_button_edit(ui):
    if ui.svj_pushButton_01.isVisible():
        ui.svj_pushButton_15.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_32.isVisible():
        ui.svj_pushButton_09.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_35.isVisible():
        ui.svj_pushButton_07.setStyleSheet(style_bc_bd)
    elif ui.sva_pushButton_03.isVisible():
        ui.svj_pushButton_08.setStyleSheet(style_bc_bd)
    elif ui.svo_pushButton_08.isVisible():
        ui.svj_pushButton_10.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_23.isVisible():
        ui.svj_pushButton_12.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_26.isVisible():
        ui.svj_pushButton_16.setStyleSheet(style_bc_bd)
    elif ui.svc_pushButton_29.isVisible():
        ui.svj_pushButton_11.setStyleSheet(style_bc_bd)


def svj_button_clicked_07(ui):
    change_pre_button_edit(ui)
    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)
    ui.ss_textEditttt_07.setVisible(False)
    ui.ss_textEditttt_08.setVisible(False)

    ui.ss_textEditttt_09.setGeometry(7, 10, 1000, 1313 if ui.extend_window else 703)
    ui.ss_progressBar_01.setGeometry(7, 1328 if ui.extend_window else 718, 830, 30)
    ui.ss_pushButtonn_08.setGeometry(842, 1328 if ui.extend_window else 718, 165, 30)

    for item in ui.stock_esczom_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(True)

    ui.ss_pushButtonn_08.setStyleSheet(style_bc_by)
    ui.svj_pushButton_13.setFocus()
    ui.svj_pushButton_13.setStyleSheet(style_bc_dk)
    ui.svj_pushButton_14.setStyleSheet(style_bc_bs)


def svj_button_clicked_08(ui):
    change_pre_button_edit(ui)
    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)
    ui.ss_textEditttt_07.setVisible(False)
    ui.ss_textEditttt_08.setVisible(False)

    ui.ss_tableWidget_01.setGeometry(7, 40, 1000, 1318 if ui.extend_window else 713)
    if (ui.extend_window and ui.ss_tableWidget_01.rowCount() < 60) or \
            (not ui.extend_window and ui.ss_tableWidget_01.rowCount() < 32):
        ui.ss_tableWidget_01.setRowCount(60 if ui.extend_window else 32)

    for item in ui.stock_esczom_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(True)

    ui.svj_pushButton_14.setFocus()
    ui.svj_pushButton_14.setStyleSheet(style_bc_dk)
    ui.svj_pushButton_13.setStyleSheet(style_bc_bs)


def svj_button_clicked_09(ui):
    ui.ss_textEditttt_01.setGeometry(7, 10, 1000, 740 if ui.extend_window else 463)
    ui.ss_textEditttt_02.setGeometry(7, 756 if ui.extend_window else 478, 1000, 602 if ui.extend_window else 272)

    ui.svjb_comboBoxx_01.setGeometry(1012, 10, 165, 25)
    ui.svjb_pushButon_01.setGeometry(1012, 40, 165, 30)
    ui.svjs_comboBoxx_01.setGeometry(1012, 478, 165, 25)
    ui.svjs_pushButon_01.setGeometry(1012, 508, 165, 30)

    ui.szoo_pushButon_01.setGeometry(952, 15, 50, 20)
    ui.szoo_pushButon_02.setGeometry(952, 761 if ui.extend_window else 483, 50, 20)

    ui.szoo_pushButon_01.setText('확대(esc)')
    ui.szoo_pushButon_02.setText('확대(esc)')

    ui.ss_textEditttt_01.setVisible(True)
    ui.ss_textEditttt_02.setVisible(True)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_optimz_list:
        item.setVisible(False)
    for item in ui.stock_period_list:
        item.setVisible(False)
    for item in ui.stock_opcond_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_datedt_list:
        item.setVisible(True)
    for item in ui.stock_esczom_list:
        item.setVisible(True)
    for item in ui.stock_backte_list:
        item.setVisible(True)

    ui.svjb_pushButon_01.setText('매수전략 로딩(F1)')
    ui.svjs_pushButon_01.setText('매도전략 로딩(F5)')

    ui.image_label1.setVisible(False)
    ui.svc_labellllll_05.setVisible(False)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_15.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_10(ui):
    ui.ss_textEditttt_07.setGeometry(7, 10, 497, 1347 if ui.extend_window else 740)
    ui.ss_textEditttt_08.setGeometry(509, 10, 497, 1347 if ui.extend_window else 740)

    ui.ss_textEditttt_01.setVisible(False)
    ui.ss_textEditttt_02.setVisible(False)
    ui.ss_textEditttt_03.setVisible(False)
    ui.ss_textEditttt_04.setVisible(False)
    ui.ss_textEditttt_05.setVisible(False)
    ui.ss_textEditttt_06.setVisible(False)

    for item in ui.stock_esczom_list:
        item.setVisible(False)
    for item in ui.stock_backte_list:
        item.setVisible(False)
    for item in ui.stock_detail_list:
        item.setVisible(False)
    for item in ui.stock_baklog_list:
        item.setVisible(False)
    for item in ui.stock_gaopti_list:
        item.setVisible(False)
    for item in ui.stock_optest_list:
        item.setVisible(False)
    for item in ui.stock_rwftvd_list:
        item.setVisible(False)
    for item in ui.stock_datedt_list:
        item.setVisible(False)
    for item in ui.stock_optimz_list:
        item.setVisible(True)
    for item in ui.stock_period_list:
        item.setVisible(True)
    for item in ui.stock_opcond_list:
        item.setVisible(True)

    ui.svc_lineEdittt_04.setVisible(False)
    ui.svc_lineEdittt_05.setVisible(False)
    ui.svc_pushButton_13.setVisible(False)
    ui.svc_pushButton_14.setVisible(False)

    ui.svc_comboBoxxx_08.setVisible(False)
    ui.svc_lineEdittt_03.setVisible(False)
    ui.svc_pushButton_09.setVisible(False)
    ui.svc_pushButton_10.setVisible(False)

    ui.svc_comboBoxxx_02.setVisible(False)
    ui.svc_lineEdittt_02.setVisible(False)
    ui.svc_pushButton_03.setVisible(False)
    ui.svc_pushButton_04.setVisible(False)

    ui.image_label1.setVisible(True)
    ui.svc_labellllll_01.setVisible(False)
    ui.svc_labellllll_04.setVisible(True)
    ui.svc_labellllll_05.setVisible(True)
    ui.svc_labellllll_04.setText(condtext)
    ui.svc_labellllll_05.setText(cedittxt)
    ui.svc_pushButton_21.setVisible(False)
    ui.svc_pushButton_22.setVisible(False)
    ui.svc_pushButton_23.setVisible(False)
    ui.svc_pushButton_24.setVisible(False)
    ui.svc_pushButton_25.setVisible(False)
    ui.svc_pushButton_26.setVisible(False)

    ui.svj_pushButton_10.setFocus()
    sChangeSvjButtonColor(ui)


def svj_button_clicked_11(ui):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        back_club = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
        if back_club and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진을 먼저 구동하십시오.\n')
            return
        if not back_club and (not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier)):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday = ui.svjb_dateEditt_01.date().toString('yyyyMMdd')
        endday = ui.svjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.svjb_lineEditt_02.text()
        endtime = ui.svjb_lineEditt_03.text()
        betting = ui.svjb_lineEditt_04.text()
        avgtime = ui.svjb_lineEditt_05.text()
        buystg = ui.svjb_comboBoxx_01.currentText()
        sellstg = ui.svjs_comboBoxx_01.currentText()
        bl = True if ui.dict_set['블랙리스트추가'] else False

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (startday, endday, starttime, endtime, betting, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '백테스트'))

        ui.backQ.put((
            betting, avgtime, startday, endday, starttime, endtime, buystg, sellstg, ui.dict_cn, ui.back_count,
            bl, False, ui.df_kp, ui.df_kd, back_club
        ))
        ui.proc_backtester_bs = Process(
            target=BackTest,
            args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques, '백테스트', 'S')
        )
        ui.proc_backtester_bs.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_12(ui):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        startday = ui.svjb_dateEditt_01.date().toString('yyyyMMdd')
        endday = ui.svjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.svjb_lineEditt_02.text()
        endtime = ui.svjb_lineEditt_03.text()
        avgtime = ui.svjb_lineEditt_05.text()
        buystg = ui.svjb_comboBoxx_01.currentText()

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (startday, endday, starttime, endtime, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if buystg == '':
            QMessageBox.critical(ui, '오류 알림', '매수전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if 'self.tickcols' not in ui.ss_textEditttt_01.toPlainText():
            QMessageBox.critical(ui, '오류 알림', '현재 매수전략이 백파인더용이 아닙니다.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '백파인더'))

        ui.backQ.put((avgtime, startday, endday, starttime, endtime, buystg, ui.back_count))
        ui.proc_backtester_bf = Process(
            target=BackFinder, args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, 'S')
        )
        ui.proc_backtester_bf.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_13(ui):
    if ui.ss_textEditttt_01.isVisible():
        ui.ss_textEditttt_01.clear()
        ui.ss_textEditttt_02.clear()
        ui.ss_textEditttt_01.append(example_finder)


def svj_button_clicked_14(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (not (QApplication.keyboardModifiers() & Qt.ShiftModifier) and
                                      not (QApplication.keyboardModifiers() & Qt.AltModifier) and
                                      (QApplication.keyboardModifiers() & Qt.ControlModifier)):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        randomopti = True if not (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
        onlybuy = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.ShiftModifier) else False
        onlysell = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
        starttime   = ui.svjb_lineEditt_02.text()
        endtime     = ui.svjb_lineEditt_03.text()
        betting     = ui.svjb_lineEditt_04.text()
        buystg      = ui.svc_comboBoxxx_01.currentText()
        sellstg     = ui.svc_comboBoxxx_08.currentText()
        optivars    = ui.svc_comboBoxxx_02.currentText()
        ccount      = ui.svc_comboBoxxx_06.currentText()
        optistd     = ui.svc_comboBoxxx_07.currentText()
        weeks_train = ui.svc_comboBoxxx_03.currentText()
        weeks_valid = ui.svc_comboBoxxx_04.currentText()
        weeks_test  = ui.svc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
        optunasampl = ui.op_comboBoxxxx_01.currentText()
        optunafixv  = ui.op_lineEditttt_01.text()
        optunacount = ui.op_lineEditttt_02.text()
        optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, ui.dict_cn, ccount, ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, False, ui.df_kp, ui.df_kd, weeks_train, weeks_valid, weeks_test, benginesday,
            bengineeday, optunasampl, optunafixv, optunacount, optunaautos, randomopti, onlybuy, onlysell
        ))
        if back_name == '최적화O':
            ui.proc_backtester_o = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_o.start()
        elif back_name == '최적화OV':
            ui.proc_backtester_ov = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_ov.start()
        elif back_name == '최적화OVC':
            ui.proc_backtester_ovc = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_ovc.start()
        elif back_name == '최적화B':
            ui.proc_backtester_b = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_b.start()
        elif back_name == '최적화BV':
            ui.proc_backtester_bv = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_bv.start()
        elif back_name == '최적화BVC':
            ui.proc_backtester_bvc = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_bvc.start()
        elif back_name == '최적화OT':
            ui.proc_backtester_ot = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_ot.start()
        elif back_name == '최적화OVT':
            ui.proc_backtester_ovt = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_ovt.start()
        elif back_name == '최적화OVCT':
            ui.proc_backtester_ovct = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_ovct.start()
        elif back_name == '최적화BT':
            ui.proc_backtester_bt = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_bt.start()
        elif back_name == '최적화BVT':
            ui.proc_backtester_bvt = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_bvt.start()
        else:
            ui.proc_backtester_bvct = Process(
                target=Optimize,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_bvct.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_15(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        randomopti  = True if (QApplication.keyboardModifiers() & Qt.AltModifier) and 'B' not in back_name else False
        startday    = ui.svjb_dateEditt_01.date().toString('yyyyMMdd')
        endday      = ui.svjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime   = ui.svjb_lineEditt_02.text()
        endtime     = ui.svjb_lineEditt_03.text()
        betting     = ui.svjb_lineEditt_04.text()
        buystg      = ui.svc_comboBoxxx_01.currentText()
        sellstg     = ui.svc_comboBoxxx_08.currentText()
        optivars    = ui.svc_comboBoxxx_02.currentText()
        ccount      = ui.svc_comboBoxxx_06.currentText()
        optistd     = ui.svc_comboBoxxx_07.currentText()
        weeks_train = ui.svc_comboBoxxx_03.currentText()
        weeks_valid = ui.svc_comboBoxxx_04.currentText()
        weeks_test  = ui.svc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
        optunasampl = ui.op_comboBoxxxx_01.currentText()
        optunafixv  = ui.op_lineEditttt_01.text()
        optunacount = ui.op_lineEditttt_02.text()
        optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if weeks_train == 'ALL':
            QMessageBox.critical(ui, '오류 알림', '전진분석 학습기간은 전체를 선택할 수 없습니다.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '전진분석'))

        ui.backQ.put((
            betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, ui.dict_cn, ccount,
            ui.dict_set['최적화기준값제한'], optistd, ui.back_count, False, ui.df_kp, ui.df_kd, weeks_train,
            weeks_valid, weeks_test, benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos,
            randomopti
        ))
        if back_name == '전진분석OR':
            ui.proc_backtester_or = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_or.start()
        elif back_name == '전진분석ORV':
            ui.proc_backtester_orv = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_orv.start()
        elif back_name == '전진분석ORVC':
            ui.proc_backtester_orvc = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_orvc.start()
        elif back_name == '전진분석BR':
            ui.proc_backtester_br = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_br.start()
        elif back_name == '전진분석BRV':
            ui.proc_backtester_brv = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_brv.start()
        else:
            ui.proc_backtester_brvc = Process(
                target=RollingWalkForwardTest,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                      ui.multi, ui.divid_mode, back_name, 'S')
            )
            ui.proc_backtester_brvc.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_16(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime   = ui.svjb_lineEditt_02.text()
        endtime     = ui.svjb_lineEditt_03.text()
        betting     = ui.svjb_lineEditt_04.text()
        buystg      = ui.svc_comboBoxxx_01.currentText()
        sellstg     = ui.svc_comboBoxxx_08.currentText()
        optivars    = ui.sva_comboBoxxx_01.currentText()
        optistd     = ui.svc_comboBoxxx_07.currentText()
        weeks_train = ui.svc_comboBoxxx_03.currentText()
        weeks_valid = ui.svc_comboBoxxx_04.currentText()
        weeks_test  = ui.svc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if '' in (starttime, endtime, betting):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return
        if optivars == '':
            QMessageBox.critical(ui, '오류 알림', '변수를 설장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', 'GA최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, ui.dict_cn, ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))
        if back_name == '최적화OG':
            ui.proc_backtester_og = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_og.start()
        elif back_name == '최적화OGV':
            ui.proc_backtester_ogv = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_ogv.start()
        else:
            ui.proc_backtester_ogvc = Process(
                target=OptimizeGeneticAlgorithm,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_ogvc.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_17(ui, back_name):
    if ui.BacktestProcessAlive():
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.back_engining:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
            return
        if ui.dialog_backengine.isVisible() and not ui.backtest_engine:
            QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
            return
        if not ui.backtest_engine or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            ui.BackTestengineShow('주식')
            return
        if ui.back_cancelling:
            QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
            return

        starttime   = ui.svjb_lineEditt_02.text()
        endtime     = ui.svjb_lineEditt_03.text()
        betting     = ui.svjb_lineEditt_04.text()
        avgtime     = ui.svjb_lineEditt_05.text()
        buystg      = ui.svo_comboBoxxx_01.currentText()
        sellstg     = ui.svo_comboBoxxx_02.currentText()
        bcount      = ui.svo_lineEdittt_03.text()
        scount      = ui.svo_lineEdittt_04.text()
        rcount      = ui.svo_lineEdittt_05.text()
        optistd     = ui.svc_comboBoxxx_07.currentText()
        weeks_train = ui.svc_comboBoxxx_03.currentText()
        weeks_valid = ui.svc_comboBoxxx_04.currentText()
        weeks_test  = ui.svc_comboBoxxx_05.currentText()
        benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
        bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

        if 'VC' in back_name and weeks_train != 'ALL' and int(weeks_train) % int(weeks_valid) != 0:
            QMessageBox.critical(ui, '오류 알림', '교차검증의 학습기간은 검증기간의 배수로 선택하십시오.\n')
            return
        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return
        if '' in (starttime, endtime, betting, avgtime, bcount, scount, rcount):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return
        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '조건을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        ui.ClearBacktestQ()
        for q in ui.back_eques:
            q.put(('백테유형', '조건최적화'))

        ui.backQ.put((
            betting, avgtime, starttime, endtime, buystg, sellstg, ui.dict_set['최적화기준값제한'], optistd, bcount,
            scount, rcount, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))
        if back_name == '최적화OC':
            ui.proc_backtester_oc = Process(
                target=OptimizeConditions,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_oc.start()
        elif back_name == '최적화OCV':
            ui.proc_backtester_ocv = Process(
                target=OptimizeConditions,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_ocv.start()
        else:
            ui.proc_backtester_ocvc = Process(
                target=OptimizeConditions,
                args=(ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques, back_name, 'S')
            )
            ui.proc_backtester_ocvc.start()
        ui.svjButtonClicked_07()
        ui.ss_progressBar_01.setValue(0)
        ui.ssicon_alert = True


def svj_button_clicked_18(ui):
    opti_vars_text = ui.ss_textEditttt_05.toPlainText()
    if opti_vars_text != '':
        ga_vars_text = ui.GetOptivarsToGavars(opti_vars_text)
        ui.ss_textEditttt_06.clear()
        ui.ss_textEditttt_06.append(ga_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 최적화 범위 코드가 공백 상태입니다.\n최적화 범위 코드를 작성하거나 로딩하십시오.\n')


def svj_button_clicked_19(ui):
    ga_vars_text = ui.ss_textEditttt_06.toPlainText()
    if ga_vars_text != '':
        opti_vars_text = ui.GetGavarsToOptivars(ga_vars_text)
        ui.ss_textEditttt_05.clear()
        ui.ss_textEditttt_05.append(opti_vars_text)
    else:
        QMessageBox.critical(ui, '오류 알림', '현재 GA 범위 코드가 공백 상태입니다.\nGA 범위 코드를 작성하거나 로딩하십시오.\n')


def svj_button_clicked_20(ui):
    buystg = ui.ss_textEditttt_01.toPlainText()
    sellstg = ui.ss_textEditttt_02.toPlainText()
    buystg_str, sellstg_str = ui.GetStgtxtToVarstxt(buystg, sellstg)
    ui.ss_textEditttt_03.clear()
    ui.ss_textEditttt_04.clear()
    ui.ss_textEditttt_03.append(buystg_str)
    ui.ss_textEditttt_04.append(sellstg_str)


def svj_button_clicked_21(ui):
    optivars = ui.ss_textEditttt_05.toPlainText()
    gavars = ui.ss_textEditttt_06.toPlainText()
    optivars_str, gavars_str = ui.GetStgtxtSort2(optivars, gavars)
    ui.ss_textEditttt_05.clear()
    ui.ss_textEditttt_06.clear()
    ui.ss_textEditttt_05.append(optivars_str)
    ui.ss_textEditttt_06.append(gavars_str)


def svj_button_clicked_22(ui):
    buystg = ui.ss_textEditttt_03.toPlainText()
    sellstg = ui.ss_textEditttt_04.toPlainText()
    buystg_str, sellstg_str = ui.GetStgtxtSort(buystg, sellstg)
    ui.ss_textEditttt_03.clear()
    ui.ss_textEditttt_04.clear()
    ui.ss_textEditttt_03.append(buystg_str)
    ui.ss_textEditttt_04.append(sellstg_str)


def sChangeSvjButtonColor(ui):
    for button in ui.stock_editer_list:
        button.setStyleSheet(style_bc_dk if ui.focusWidget() == button else style_bc_bs)
