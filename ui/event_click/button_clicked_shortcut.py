
from utility.static_method.static import thread_decorator


def mnbutton_c_clicked_01(ui, index):
    """메인 탭을 변경합니다.
    Args:
        ui: UI 클래스 인스턴스
        index: 탭 인덱스
    """
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_style import style_bc_bb, style_bc_st
    from PyQt5.QtCore import QTimer, QPropertyAnimation, QSize, QEasingCurve

    if ui.extend_window:
        QMessageBox.critical(ui, '오류 알림', '전략탭 확장 상태에서는 탭을 변경할 수 없습니다.')
        return

    prev_main_btn = ui.main_btn
    if prev_main_btn == index:
        return

    ui.image_label1.setVisible(False)
    if index == 2:
        ui.svjb_lineEditt_04.setText(str(ui.dict_set['투자금']))
    elif index == 4 and ui.lgicon_alert:
        ui.lgicon_alert = False
        ui.main_btn_list[index].setIcon(ui.icon_log)
    elif index == 5:
        from ui.etcetera.etc import strategy_setting_label_change
        strategy_setting_label_change(ui)

    ui.main_btn = index
    ui.main_btn_list[prev_main_btn].setStyleSheet(style_bc_bb)
    ui.main_btn_list[ui.main_btn].setStyleSheet(style_bc_st)
    ui.main_box_list[prev_main_btn].setVisible(False)
    ui.main_box_list[ui.main_btn].setVisible(True)
    QTimer.singleShot(300, lambda: ui.image_label1.setVisible(True if ui.svc_labellllll_05.isVisible() else False))
    ui.animation = QPropertyAnimation(ui.main_box_list[ui.main_btn], b'size')
    ui.animation.setEasingCurve(QEasingCurve.InOutCirc)
    ui.animation.setDuration(300)
    ui.animation.setStartValue(QSize(0, 757))
    ui.animation.setEndValue(QSize(1353, 757))
    ui.animation.start()


def mnbutton_c_clicked_02(ui):
    """테이블 표시를 전환합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox

    if ui.main_btn == 1:
        if not ui.calendarWidgetttt.isVisible():
            boolean1 = False
            boolean2 = True
        else:
            boolean1 = True
            boolean2 = False
        for widget in ui.table_basic_listt:
            widget.setVisible(boolean1)
        for widget in ui.table_total_listt:
            widget.setVisible(boolean2)
    else:
        QMessageBox.warning(ui, '오류 알림', '해당 버튼은 트레이더탭에서만 작동합니다.\n')


def mnbutton_c_clicked_03(ui, auto=False):
    """매매 시스템을 시작합니다.
    Args:
        ui: UI 클래스 인스턴스
        auto: 자동 시작 여부
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import ui_num
    from ui.create_widget.set_style import style_bc_st
    from ui.etcetera.process_alive import receiver_process_alive
    from utility.static_method.static import qtest_qwait, cme_normal_open, now, get_inthms

    if auto:
        buttonReply = QMessageBox.Yes
    else:
        if ui.dialog_web.isVisible():
            QMessageBox.critical(ui, '오류 알림', '웹뷰어창이 열린 상태에서는 수동시작할 수 없습니다.\n웹뷰어창을 닫고 재시도하십시오.\n')
            return

        inthms = get_inthms(ui.market_gubun)
        if inthms > ui.dict_set['전략종료시간']:
            buttonReply = QMessageBox.critical(
                ui, '수동 시작',
                f"현재 시간이 {ui.market_info['마켓이름']} 전략종료시간 이후입니다.\n로그인을 진행해도 관심종목이 보이지 않으며 매매가 진행되지 않습니다.\n계속하시겠습니까?\n",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
        else:
            buttonReply = QMessageBox.question(
                ui, '수동 시작',
                f"{ui.market_info['마켓이름']} 매매시스템 시작합니다.\n이미 실행 중이라면 기존 프로세스는 종료됩니다.\n계속하시겠습니까?\n",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

    if buttonReply == QMessageBox.Yes:
        if auto:
            holiday = False
            if ui.market_gubun not in (5, 9) and now().weekday() > 4:
                holiday = True
            elif ui.market_gubun == 8 and not cme_normal_open():
                holiday = True

            if holiday:
                ui.windowQ.put((ui_num['시스템로그'], f"거래소 {ui.market_info['마켓이름']}, 휴무 종료"))
                return

        mnbutton_c_clicked_01(ui, 1)
        if receiver_process_alive(ui):
            ui.receivQ.put('프로그램종료')
            qtest_qwait(3)

        acc_no = ui.dict_set['거래소'][-2:]
        if ui.dict_set[f'access_key{acc_no}'] is None or ui.dict_set[f'secret_key{acc_no}'] is None:
            QMessageBox.critical(ui, '오류 알림', '계정이 설정되지 않아 매매시스템을 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n')
        else:
            trade_process_start(ui)
            ui.ms_pushButton.setStyleSheet(style_bc_st)


def mnbutton_c_clicked_04(ui):
    """창 크기를 변경합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.create_widget.set_style import style_bc_bb, style_bc_st

    if ui.geometry().width() > 1000:
        ui.setFixedSize(726, 384)
        ui.zo_pushButton.setStyleSheet(style_bc_st)
    else:
        ui.setFixedSize(1403, 763)
        ui.zo_pushButton.setStyleSheet(style_bc_bb)


def mnbutton_c_clicked_05(ui):
    """백테 그래프 및 기록 DB를 삭제합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    from PyQt5.QtWidgets import QMessageBox
    from utility.settings.setting_base import GRAPH_PATH

    buttonReply = QMessageBox.warning(
        ui, '백테기록삭제', '백테 그래프 및 기록 DB가 삭제됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        file_list = os.listdir(GRAPH_PATH)
        for file_name in file_list:
            os.remove(f'{GRAPH_PATH}/{file_name}')
        if ui.proc_chqs.is_alive():
            df = ui.dbreader.read_sql('백테디비', "SELECT name FROM sqlite_master WHERE TYPE = 'table'")
            table_list = df['name'].to_list()
            for table_name in table_list:
                ui.queryQ.put(('백테디비', f'DROP TABLE {table_name}'))
            ui.queryQ.put(('백테디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '백테그래프 및 기록DB가 삭제되었습니다.')


def mnbutton_c_clicked_06(ui):
    """계정 설정을 초기화합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import pandas as pd
    from PyQt5.QtWidgets import QMessageBox

    buttonReply = QMessageBox.warning(
        ui, '계정 설정 초기화', '계정 설정 항목이 모두 초기화됩니다.\n계속하시겠습니까?\n',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )
    if buttonReply == QMessageBox.Yes:
        if ui.proc_chqs.is_alive():
            ui.queryQ.put(('설정디비', 'DELETE FROM account'))
            ui.queryQ.put(('설정디비', 'DELETE FROM telegram'))

            columns = ["index", "access_key", "secret_key"]
            data = [
                [1, '', ''], [2, '', ''], [3, '', ''], [4, '', ''], [5, '', ''], [6, '', ''],
                [7, '', ''], [8, '', ''], [9, '', ''], [10, '', ''], [11, '', ''], [12, '', ''],
                [13, '', ''], [14, '', ''], [15, '', ''], [16, '', ''], [17, '', ''], [18, '', '']
            ]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put(('설정디비', df, 'account', 'append'))

            columns = ["index", "bot_token", "chatingid"]
            data = [
                [1, '', ''], [2, '', ''], [3, '', ''], [4, '', ''], [5, '', ''], [6, '', ''],
                [7, '', ''], [8, '', ''], [9, '', ''], [10, '', ''], [11, '', ''], [12, '', ''],
                [13, '', ''], [14, '', ''], [15, '', ''], [16, '', ''], [17, '', ''], [18, '', '']
            ]
            df = pd.DataFrame(data, columns=columns).set_index('index')
            ui.queryQ.put(('설정디비', df, 'telegram', 'append'))

            ui.queryQ.put(('설정디비', 'VACUUM'))
            QMessageBox.information(ui, '알림', '계정 설정 항목이 모두 초기화되었습니다.')


@thread_decorator
def trade_process_start(ui):
    """거래 프로세스를 시작합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from multiprocessing import Process

    target = ui.market_info['프로세스'][0]
    ui.proc_receiver = Process(target=target, args=(ui.qlist, ui.dict_set, ui.market_infos))
    ui.proc_receiver.start()

    target = ui.market_info['프로세스'][1]
    ui.proc_trader = Process(target=target, args=(ui.qlist, ui.dict_set, ui.market_infos))
    ui.proc_trader.start()

    target = ui.market_info['프로세스'][2]
    if ui.market_gubun in (1, 4):
        for i in range(8):
            p = Process(target=target, args=(i, ui.qlist, ui.dict_set, ui.market_infos))
            p.start()
            ui.proc_strategys.append(p)
    else:
        p = Process(target=target, args=(0, ui.qlist, ui.dict_set, ui.market_infos))
        p.start()
        ui.proc_strategys.append(p)

    if ui.dict_set['웹대시보드']:
        from ui.ui_mainwindow import get_ip
        from dashboard.dashboard_starter import DashboardStarter
        port = ui.dict_set['웹대시보드포트번호']
        ui.web_dashboard = DashboardStarter(ui.market_gubun, port)
        ui.web_dashboard.log_received.connect(ui.web_dashboard_log)
        ui.web_dashboard.start()
        # noinspection HttpUrlsUsage
        ui.teleQ.put(f'http://{get_ip()}:{port}')
