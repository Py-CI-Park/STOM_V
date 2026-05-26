
def extend_window(ui):
    """전략탭 창을 확장/축소합니다."""
    from PyQt5.QtWidgets import QMessageBox

    if ui.main_btn != 2:
        QMessageBox.critical(ui, '오류 알림', '전략탭 확장기능은 전략탭에서만 사용할 수 있습니다.')
        return

    if not ui.extend_window:
        ui.extend_window = True
        ui.setFixedSize(1403, 1368)
        ui.image_label2.setVisible(True)
        ui.progressBarrr.setGeometry(5, 490, 35, 872)
    else:
        ui.extend_window = False
        ui.setFixedSize(1403, 763)
        ui.image_label2.setVisible(False)
        ui.progressBarrr.setGeometry(5, 490, 35, 267)

    ui.st_tab.setGeometry(45, 0, 1353, 1362 if ui.extend_window else 757)

    if ui.ss_pushButtonn_08.isVisible():
        ui.ss_textEditttt_09.setGeometry(7, 10, 1000, 1313 if ui.extend_window else 705)
        ui.ss_progressBar_01.setGeometry(7, 1328 if ui.extend_window else 720, 830, 30)
        ui.ss_pushButtonn_08.setGeometry(842, 1328 if ui.extend_window else 720, 165, 30)

    elif ui.ss_pushButtonn_01.isVisible():
        ui.ss_tableWidget_01.setGeometry(7, 40, 1000, 1315 if ui.extend_window else 710)
        if (ui.extend_window and ui.ss_tableWidget_01.rowCount() < 60) or (
                not ui.extend_window and ui.ss_tableWidget_01.rowCount() < 32):
            ui.ss_tableWidget_01.setRowCount(60 if ui.extend_window else 32)

    elif ui.svj_pushButton_01.isVisible():
        if ui.ss_pushButtonn_41.isVisible():
            if ui.ss_textEditttt_01.isVisible():
                ui.ss_textEditttt_01.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            else:
                ui.ss_textEditttt_02.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            ui.ss_textEditttt_10.setGeometry(509, 40, 497, 1315 if ui.extend_window else 710)
        else:
            ui.ss_textEditttt_01.setGeometry(7, 10, 1000, 740 if ui.extend_window else 460)
            ui.ss_textEditttt_02.setGeometry(7, 755 if ui.extend_window else 475, 1000, 600 if ui.extend_window else 275)
            ui.szoo_pushButon_02.setGeometry(937, 760 if ui.extend_window else 480, 50, 20)
            ui.ss_textEditttt_01.setVisible(True)
            ui.ss_textEditttt_02.setVisible(True)
            ui.szoo_pushButon_01.setVisible(True)
            ui.szoo_pushButon_02.setVisible(True)
            ui.szoo_pushButon_01.setText('확대(esc)')
            ui.szoo_pushButon_02.setText('확대(esc)')

    elif ui.svc_pushButton_24.isVisible():
        ui.ss_textEditttt_01.setGeometry(7, 10, 497, 740 if ui.extend_window else 460)
        ui.ss_textEditttt_02.setGeometry(7, 755 if ui.extend_window else 475, 497, 600 if ui.extend_window else 275)
        ui.ss_textEditttt_03.setGeometry(509, 10, 497, 740 if ui.extend_window else 460)
        ui.ss_textEditttt_04.setGeometry(509, 755 if ui.extend_window else 475, 497, 600 if ui.extend_window else 275)

    elif ui.svc_pushButton_21.isVisible():
        ui.ss_textEditttt_05.setGeometry(7, 10, 497, 1345 if ui.extend_window else 740)
        ui.ss_textEditttt_06.setGeometry(509, 10, 497, 1345 if ui.extend_window else 740)

    elif ui.svo_pushButton_05.isVisible():
        if ui.ss_pushButtonn_41.isVisible():
            if ui.ss_textEditttt_07.isVisible():
                ui.ss_textEditttt_07.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            else:
                ui.ss_textEditttt_08.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            ui.ss_textEditttt_10.setGeometry(509, 40, 497, 1315 if ui.extend_window else 710)
        else:
            ui.ss_textEditttt_07.setGeometry(7, 10, 497, 1345 if ui.extend_window else 740)
            ui.ss_textEditttt_08.setGeometry(509, 10, 497, 1345 if ui.extend_window else 740)

    elif ui.sva_pushButton_01.isVisible():
        if ui.ss_pushButtonn_41.isVisible():
            if ui.ss_textEditttt_03.isVisible():
                ui.ss_textEditttt_03.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            elif ui.ss_textEditttt_04.isVisible():
                ui.ss_textEditttt_04.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            else:
                ui.ss_textEditttt_06.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            ui.ss_textEditttt_10.setGeometry(509, 40, 497, 1315 if ui.extend_window else 710)
        else:
            ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 460)
            ui.ss_textEditttt_04.setGeometry(7, 755 if ui.extend_window else 475, 647, 600 if ui.extend_window else 275)
            ui.ss_textEditttt_06.setGeometry(659, 10, 347, 1345 if ui.extend_window else 740)
            ui.szoo_pushButon_02.setGeometry(584, 760 if ui.extend_window else 480, 50, 20)
            ui.ss_textEditttt_03.setVisible(True)
            ui.ss_textEditttt_04.setVisible(True)
            ui.ss_textEditttt_06.setVisible(True)
            ui.szoo_pushButon_01.setVisible(True)
            ui.szoo_pushButon_02.setVisible(True)
            ui.szoo_pushButon_01.setText('확대(esc)')
            ui.szoo_pushButon_02.setText('확대(esc)')

    else:
        if ui.ss_pushButtonn_41.isVisible():
            if ui.ss_textEditttt_03.isVisible():
                ui.ss_textEditttt_03.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            elif ui.ss_textEditttt_04.isVisible():
                ui.ss_textEditttt_04.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            else:
                ui.ss_textEditttt_05.setGeometry(7, 40, 497, 1315 if ui.extend_window else 710)
            ui.ss_textEditttt_10.setGeometry(509, 40, 497, 1315 if ui.extend_window else 710)
        else:
            ui.ss_textEditttt_03.setGeometry(7, 10, 647, 740 if ui.extend_window else 460)
            ui.ss_textEditttt_04.setGeometry(7, 755 if ui.extend_window else 475, 647, 600 if ui.extend_window else 275)
            ui.ss_textEditttt_05.setGeometry(659, 10, 347, 1345 if ui.extend_window else 740)
            ui.szoo_pushButon_02.setGeometry(584, 760 if ui.extend_window else 480, 50, 20)
            ui.ss_textEditttt_03.setVisible(True)
            ui.ss_textEditttt_04.setVisible(True)
            ui.ss_textEditttt_05.setVisible(True)
            ui.szoo_pushButon_01.setVisible(True)
            ui.szoo_pushButon_02.setVisible(True)
            ui.szoo_pushButon_01.setText('확대(esc)')
            ui.szoo_pushButon_02.setText('확대(esc)')
