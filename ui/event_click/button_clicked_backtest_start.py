
def bebutton_clicked_01(ui):
    """백테스트 엔진 시작 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtWidgets import QMessageBox
    from utility.static_method.static import qtest_qwait
    from ui.event_click.button_clicked_backtest_engine import backengine_start

    if ui.backengine_starting:
        QMessageBox.critical(ui.dialog_backengine, '오류 알림', '백테엔진 구동 중...\n')
        return

    if not ui.backengine_running:
        backengine_start(ui)
    else:
        buttonReply = QMessageBox.question(
            ui.dialog_backengine, '백테엔진', '이미 백테스트 엔진이 구동중입니다.\n엔진을 재시작하시겠습니까?\n',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if buttonReply == QMessageBox.Yes:
            backtest_engine_kill(ui)
            qtest_qwait(3)
            backengine_start(ui)


def backtest_engine_kill(ui):
    """백테스트 엔진을 종료합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import os
    from multiprocessing import shared_memory
    from utility.settings.setting_base import ui_num
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if ui.shared_info and 'shm_name' in ui.shared_info[0].keys():
        if ui.dialog_backengine.isVisible():
            ui.windowQ.put((ui_num['백테엔진'], '<font color=#54d2f9>공유메모리 삭제 중 ...</font>'))
        else:
            ui.windowQ.put((ui_num['시스템로그'], '백테스트엔진 공유메모리 삭제 중 ...'))
        for shared_info in ui.shared_info:
            try:
                shm = shared_memory.SharedMemory(name=shared_info['shm_name'])
                shm.close()
                shm.unlink()
            except Exception:
                pass
        ui.shared_info = []
        if ui.dialog_backengine.isVisible():
            ui.windowQ.put((ui_num['백테엔진'], '<font color=#54d2f9>공유메모리 삭제 완료</font>'))
        else:
            ui.windowQ.put((ui_num['시스템로그'], '백테스트엔진 공유메모리 삭제 완료'))

    elif ui.shared_info and 'file_name' in ui.shared_info[0].keys():
        if ui.dialog_backengine.isVisible():
            ui.windowQ.put((ui_num['백테엔진'], '<font color=#54d2f9>임시파일 삭제 중 ...</font>'))
        else:
            ui.windowQ.put((ui_num['시스템로그'], '백테스트엔진 임시파일 삭제 중 ...'))
        for shared_info in ui.shared_info:
            try:
                os.remove(shared_info['file_name'])
            except Exception:
                pass
        if ui.dialog_backengine.isVisible():
            ui.windowQ.put((ui_num['백테엔진'], '<font color=#54d2f9>임시파일 삭제 완료</font>'))
        else:
            ui.windowQ.put((ui_num['시스템로그'], '백테스트엔진 임시파일 삭제 완료'))

    clear_backtestQ(ui)
    for p in ui.back_sprocs:
        p.kill()
    for p in ui.back_eprocs:
        p.kill()
    for q in ui.back_sques:
        q.close()
    for q in ui.back_eques:
        q.close()
    ui.windowQ.put((ui_num['시스템로그'], '백테스트엔진 중간집계용 프로세스 종료 완료'))

    ui.back_eprocs = []
    ui.back_sprocs = []
    ui.back_eques  = []
    ui.back_sques  = []
    ui.back_count  = 0
    ui.backengine_starting = False
    ui.backengine_running  = False
    if ui.dialog_backengine.isVisible():
        ui.windowQ.put((ui_num['백테엔진'], '<font color=#54d2f9>백테스트엔진 프로세스 종료 완료</font>'))


def sdbutton_clicked_02(ui):
    """백테스트 스케줄러 시작 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from PyQt5.QtCore import Qt
    from multiprocessing import Process
    from backtest.optimiz import Optimize
    from backtest.backtest import BackTest
    from PyQt5.QtWidgets import QMessageBox, QApplication
    from backtest.optimiz_conditions import OptimizeConditions
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_stg_editer import backtest_log
    from backtest.rolling_walk_forward_test import RollingWalkForwardTest
    from backtest.optimiz_genetic_algorithm import OptimizeGeneticAlgorithm
    from ui.event_click.button_clicked_shortcut import mnbutton_c_clicked_01
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ, backengine_show

    if backtest_process_alive(ui):
        QMessageBox.critical(ui.dialog_scheduler, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if ui.backengine_starting:
            QMessageBox.critical(ui.dialog_backengine, '오류 알림', '백테엔진 구동 중...\n')
            return

        if not ui.backengine_running or (QApplication.keyboardModifiers() & Qt.ControlModifier):
            backengine_show(ui)
            return

        if ui.main_btn != 2:
            mnbutton_c_clicked_01(ui, 2)

        clear_backtestQ(ui)
        if ui.back_schedul:
            ui.back_scount += 1
        else:
            for progressBar in ui.list_progressBarrr:
                progressBar.setValue(0)

        while ui.back_scount < 16 and not ui.list_checkBoxxxxxx[ui.back_scount].isChecked():
            ui.back_scount += 1

        if ui.back_scount < 16:
            back_name = ui.list_gcomboBoxxxxx[ui.back_scount].currentText()
            if back_name == '백테스트':
                startday  = ui.list_sdateEdittttt[ui.back_scount].date().toString('yyyyMMdd')
                endday    = ui.list_edateEdittttt[ui.back_scount].date().toString('yyyyMMdd')
                starttime = ui.list_slineEdittttt[ui.back_scount].text()
                endtime   = ui.list_elineEdittttt[ui.back_scount].text()
                betting   = ui.list_blineEdittttt[ui.back_scount].text()
                avgtime   = ui.list_alineEdittttt[ui.back_scount].text()
                buystg    = ui.list_bcomboBoxxxxx[ui.back_scount].currentText()
                sellstg   = ui.list_scomboBoxxxxx[ui.back_scount].currentText()
                bl = True if ui.dict_set['블랙리스트추가'] else False

                if int(avgtime) not in ui.avg_list:
                    stop_scheduler(ui)
                    QMessageBox.critical(
                        ui.dialog_scheduler,
                        '오류 알림',
                        '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n'
                    )
                    return

                for q in ui.back_eques:
                    q.put(('백테유형', '백테스트'))

                if ui.market_gubun not in (5, 9):
                    ui.proc_backtester_bs = Process(
                        target=BackTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                              ui.back_sques, back_name, ui.dict_set, ui.market_infos, betting, avgtime, startday,
                              endday, starttime, endtime, buystg, sellstg, ui.back_count, bl, True, False)
                    )
                else:
                    ui.proc_backtester_bs = Process(
                        target=BackTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                              ui.back_sques, back_name, ui.dict_set, ui.market_infos, betting, avgtime, startday,
                              endday, starttime, endtime, buystg, sellstg, ui.back_count, bl, True, False)
                    )
                ui.proc_backtester_bs.start()
                backtest_log(ui)
                ui.ss_progressBar_01.setValue(0)
                ui.ssicon_alert = True

            elif '조건' in back_name:
                starttime   = ui.list_slineEdittttt[ui.back_scount].text()
                endtime     = ui.list_elineEdittttt[ui.back_scount].text()
                betting     = ui.list_blineEdittttt[ui.back_scount].text()
                avgtime     = ui.list_alineEdittttt[ui.back_scount].text()
                buystg      = ui.list_bcomboBoxxxxx[ui.back_scount].currentText()
                sellstg     = ui.list_scomboBoxxxxx[ui.back_scount].currentText()
                bcount      = ui.sd_oclineEdittt_01.text()
                scount      = ui.sd_oclineEdittt_02.text()
                rcount      = ui.sd_oclineEdittt_03.text()
                optistd     = ui.list_tcomboBoxxxxx[ui.back_scount].currentText()
                weeks_train = ui.list_p1comboBoxxxx[ui.back_scount].currentText()
                weeks_valid = ui.list_p2comboBoxxxx[ui.back_scount].currentText()
                weeks_test  = ui.list_p3comboBoxxxx[ui.back_scount].currentText()
                benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
                bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

                for q in ui.back_eques:
                    q.put(('백테유형', '조건최적화'))

                ui.backQ.put((
                    betting, avgtime, starttime, endtime, buystg, sellstg, ui.dict_set['최적화기준값제한'], optistd,
                    bcount, scount, rcount, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday,
                    bengineeday
                ))

                if back_name == '조건 최적화':
                    ui.proc_backtester_oc = Process(
                        target=OptimizeConditions,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_oc.start()
                elif back_name == '검증 조건 최적화':
                    ui.proc_backtester_ocv = Process(
                        target=OptimizeConditions,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OCV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ocv.start()
                elif back_name == '교차검증 조건 최적화':
                    ui.proc_backtester_ocvc = Process(
                        target=OptimizeConditions,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OCVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ocvc.start()

                backtest_log(ui)
                ui.ss_progressBar_01.setValue(0)
                ui.ssicon_alert = True

            elif 'GA' in back_name:
                starttime   = ui.list_slineEdittttt[ui.back_scount].text()
                endtime     = ui.list_elineEdittttt[ui.back_scount].text()
                betting     = ui.list_blineEdittttt[ui.back_scount].text()
                buystg      = ui.list_bcomboBoxxxxx[ui.back_scount].currentText()
                sellstg     = ui.list_scomboBoxxxxx[ui.back_scount].currentText()
                optivars    = ui.list_vcomboBoxxxxx[ui.back_scount].currentText()
                optistd     = ui.list_tcomboBoxxxxx[ui.back_scount].currentText()
                weeks_train = ui.list_p1comboBoxxxx[ui.back_scount].currentText()
                weeks_valid = ui.list_p2comboBoxxxx[ui.back_scount].currentText()
                weeks_test  = ui.list_p3comboBoxxxx[ui.back_scount].currentText()
                benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
                bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')

                for q in ui.back_eques:
                    q.put(('백테유형', 'GA최적화'))

                if ui.market_gubun not in (5, 9):
                    ui.backQ.put((
                        betting, starttime, endtime, buystg, sellstg, optivars, ui.dict_set['최적화기준값제한'],
                        optistd, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
                    ))
                else:
                    ui.backQ.put((
                        betting, starttime, endtime, buystg, sellstg, optivars, ui.dict_set['최적화기준값제한'],
                        optistd, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, benginesday
                    ))

                if back_name == 'GA 최적화':
                    ui.proc_backtester_og = Process(
                        target=OptimizeGeneticAlgorithm,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OG', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_og.start()
                elif back_name == '검증 GA 최적화':
                    ui.proc_backtester_ogv = Process(
                        target=OptimizeGeneticAlgorithm,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OGV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ogv.start()
                elif back_name == '교차검증 GA 최적화':
                    ui.proc_backtester_ogvc = Process(
                        target=OptimizeGeneticAlgorithm,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques,
                              ui.back_sques, ui.multi, '최적화OGVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ogvc.start()

                backtest_log(ui)
                ui.ss_progressBar_01.setValue(0)
                ui.ssicon_alert = True

            elif '전진분석' in back_name:
                startday    = ui.list_sdateEdittttt[ui.back_scount].date().toString('yyyyMMdd')
                endday      = ui.list_edateEdittttt[ui.back_scount].date().toString('yyyyMMdd')
                starttime   = ui.list_slineEdittttt[ui.back_scount].text()
                endtime     = ui.list_elineEdittttt[ui.back_scount].text()
                betting     = ui.list_blineEdittttt[ui.back_scount].text()
                buystg      = ui.list_bcomboBoxxxxx[ui.back_scount].currentText()
                sellstg     = ui.list_scomboBoxxxxx[ui.back_scount].currentText()
                optivars    = ui.list_vcomboBoxxxxx[ui.back_scount].currentText()
                weeks_train = ui.list_p1comboBoxxxx[ui.back_scount].currentText()
                weeks_valid = ui.list_p2comboBoxxxx[ui.back_scount].currentText()
                weeks_test  = ui.list_p3comboBoxxxx[ui.back_scount].currentText()
                ccount      = ui.list_p4comboBoxxxx[ui.back_scount].currentText()
                optistd     = ui.list_tcomboBoxxxxx[ui.back_scount].currentText()
                benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
                bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
                optunasampl = ui.op_comboBoxxxx_01.currentText()
                optunafixv  = ui.op_lineEditttt_01.text()
                optunacount = ui.op_lineEditttt_02.text()
                optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

                for q in ui.back_eques:
                    q.put(('백테유형', '전진분석'))

                if ui.market_gubun not in (5, 9):
                    ui.backQ.put((
                        betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, ccount,
                        ui.dict_set['최적화기준값제한'], optistd, ui.back_count, True, weeks_train, weeks_valid,
                        weeks_test, benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos, False
                    ))
                else:
                    ui.backQ.put((
                        betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, ccount,
                        ui.dict_set['최적화기준값제한'], optistd, ui.back_count, True, weeks_train, weeks_valid,
                        weeks_test, benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos, False
                    ))

                if back_name == '그리드 최적화 전진분석':
                    ui.proc_backtester_or = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석OR', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_or.start()
                elif back_name == '그리드 검증 최적화 전진분석':
                    ui.proc_backtester_orv = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석ORV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_orv.start()
                elif back_name == '그리드 교차검증 최적화 전진분석':
                    ui.proc_backtester_orvc = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석ORVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_orvc.start()
                elif back_name == '베이지안 최적화 전진분석':
                    ui.proc_backtester_br = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석BR', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_br.start()
                elif back_name == '베이지안 검증 최적화 전진분석':
                    ui.proc_backtester_brv = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석BRV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_brv.start()
                elif back_name == '베이지안 교차검증 최적화 전진분석':
                    ui.proc_backtester_brvc = Process(
                        target=RollingWalkForwardTest,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '전진분석BRVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_brvc.start()

                backtest_log(ui)
                ui.ss_progressBar_01.setValue(0)
                ui.ssicon_alert = True

            elif '최적화' in back_name:
                starttime   = ui.list_slineEdittttt[ui.back_scount].text()
                endtime     = ui.list_elineEdittttt[ui.back_scount].text()
                betting     = ui.list_blineEdittttt[ui.back_scount].text()
                buystg      = ui.list_bcomboBoxxxxx[ui.back_scount].currentText()
                sellstg     = ui.list_scomboBoxxxxx[ui.back_scount].currentText()
                optivars    = ui.list_vcomboBoxxxxx[ui.back_scount].currentText()
                ccount      = ui.list_p4comboBoxxxx[ui.back_scount].currentText()
                optistd     = ui.list_tcomboBoxxxxx[ui.back_scount].currentText()
                weeks_train = ui.list_p1comboBoxxxx[ui.back_scount].currentText()
                weeks_valid = ui.list_p2comboBoxxxx[ui.back_scount].currentText()
                weeks_test  = ui.list_p3comboBoxxxx[ui.back_scount].currentText()
                benginesday = ui.be_dateEdittttt_01.date().toString('yyyyMMdd')
                bengineeday = ui.be_dateEdittttt_02.date().toString('yyyyMMdd')
                optunasampl = ui.op_comboBoxxxx_01.currentText()
                optunafixv  = ui.op_lineEditttt_01.text()
                optunacount = ui.op_lineEditttt_02.text()
                optunaautos = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

                for q in ui.back_eques:
                    q.put(('백테유형', '최적화'))

                if ui.market_gubun not in (5, 9):
                    ui.backQ.put((
                        betting, starttime, endtime, buystg, sellstg, optivars, ccount, ui.dict_set['최적화기준값제한'],
                        optistd, ui.back_count, True, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday,
                        optunasampl, optunafixv, optunacount, optunaautos, False, False, False
                    ))
                else:
                    ui.backQ.put((
                        betting, starttime, endtime, buystg, sellstg, optivars, ccount, ui.dict_set['최적화기준값제한'],
                        optistd, ui.back_count, True, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday,
                        optunasampl, optunafixv, optunacount, optunaautos, False, False, False
                    ))

                if back_name == '그리드 최적화':
                    ui.proc_backtester_o = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화O', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_o.start()
                elif back_name == '그리드 검증 최적화':
                    ui.proc_backtester_ov = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화OV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ov.start()
                elif back_name == '그리드 교차검증 최적화':
                    ui.proc_backtester_ovc = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화OVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ovc.start()
                elif back_name == '베이지안 최적화':
                    ui.proc_backtester_b = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화B', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_b.start()
                elif back_name == '베이지안 검증 최적화':
                    ui.proc_backtester_bv = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화BV', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_bv.start()
                elif back_name == '베이지안 교차검증 최적화':
                    ui.proc_backtester_bvc = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화BVC', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_bvc.start()
                elif back_name == '그리드 최적화 테스트':
                    ui.proc_backtester_ot = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화OT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ot.start()
                elif back_name == '그리드 검증 최적화 테스트':
                    ui.proc_backtester_ovt = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화OVT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ovt.start()
                elif back_name == '그리드 교차검증 최적화 테스트':
                    ui.proc_backtester_ovct = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화OVCT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_ovct.start()
                elif back_name == '베이지안 최적화 테스트':
                    ui.proc_backtester_bt = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화BT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_bt.start()
                elif back_name == '베이지안 검증 최적화 테스트':
                    ui.proc_backtester_bvt = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화BVT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_bvt.start()
                elif back_name == '베이지안 교차검증 최적화 테스트':
                    ui.proc_backtester_bvct = Process(
                        target=Optimize,
                        args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ,
                              ui.back_eques, ui.back_sques, ui.multi, '최적화BVCT', ui.dict_set, ui.market_infos)
                    )
                    ui.proc_backtester_bvct.start()

                backtest_log(ui)
                ui.ss_progressBar_01.setValue(0)
                ui.ssicon_alert = True

            ui.list_progressBarrr[ui.back_scount].setValue(0)
            ui.back_schedul = True
        else:
            stop_scheduler(ui, True)


def stop_scheduler(ui, gubun=False):
    """백테스트 스케줄러를 중지합니다.
    Args:
        ui: UI 클래스 인스턴스
        gubun: 구분
    """
    import os
    from PyQt5.QtCore import QTimer
    from ui.etcetera.etc import auto_back_schedule

    ui.back_scount = 0
    ui.back_schedul = False
    if ui.auto_mode:
        auto_back_schedule(ui, 3)
    if gubun and ui.sd_scheckBoxxxx_02.isChecked():
        QTimer.singleShot(180 * 1000, ui.process_kill)
        os.system('shutdown /s /t 300')


def sdbutton_clicked_03(ui):
    """백테스트 스케줄러 중지 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    from ui.event_click.button_clicked_stg_editer_backlog import ssbutton_clicked_06

    ssbutton_clicked_06(ui)
    for progressBar in ui.list_progressBarrr:
        progressBar.setValue(0)


def sdbutton_clicked_04(ui):
    """백테스트 스케줄러 로드 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    df = ui.dbreader.read_sql('전략디비', 'SELECT * FROM schedule').set_index('index')
    if len(df) > 0:
        if ui.sd_scheckBoxxxx_01.isChecked():
            ui.sd_scheckBoxxxx_01.nextCheckState()
        ui.sd_dcomboBoxxxx_01.clear()
        indexs = list(df.index)
        indexs.sort()
        for i, index in enumerate(indexs):
            ui.sd_dcomboBoxxxx_01.addItem(index)
            if i == 0:
                ui.sd_dlineEditttt_01.setText(index)


def sdbutton_clicked_05(ui):
    """백테스트 스케줄러 저장 버튼 클릭 이벤트를 처리합니다.
    Args:
        ui: UI 클래스 인스턴스
    """
    import random
    from PyQt5.QtWidgets import QMessageBox
    from ui.create_widget.set_text import famous_saying

    schedule_name = ui.sd_dlineEditttt_01.text()
    if schedule_name == '':
        QMessageBox.critical(ui.dialog_scheduler, '오류 알림', '스케쥴 이름이 공백 상태입니다.\n')
    else:
        schedule = ''
        for i in range(16):
            if ui.list_checkBoxxxxxx[i].isChecked():
                schedule += ui.list_gcomboBoxxxxx[i].currentText() + ';'
                schedule += ui.list_slineEdittttt[i].text() + ';'
                schedule += ui.list_elineEdittttt[i].text() + ';'
                schedule += ui.list_blineEdittttt[i].text() + ';'
                schedule += ui.list_alineEdittttt[i].text() + ';'
                schedule += ui.list_p1comboBoxxxx[i].currentText() + ';'
                schedule += ui.list_p2comboBoxxxx[i].currentText() + ';'
                schedule += ui.list_p3comboBoxxxx[i].currentText() + ';'
                schedule += ui.list_p4comboBoxxxx[i].currentText() + ';'
                schedule += ui.list_tcomboBoxxxxx[i].currentText() + ';'
                schedule += ui.list_bcomboBoxxxxx[i].currentText() + ';'
                schedule += ui.list_scomboBoxxxxx[i].currentText() + ';'
                schedule += ui.list_vcomboBoxxxxx[i].currentText() + '^'
        schedule += '1;' if ui.sd_scheckBoxxxx_02.isChecked() else '0;'
        schedule += ui.sd_oclineEdittt_01.text() + ';'
        schedule += ui.sd_oclineEdittt_02.text() + ';'
        schedule += ui.sd_oclineEdittt_03.text()
        if ui.proc_chqs.is_alive():
            insert_query  = 'INSERT OR REPLACE INTO schedule VALUES (?, ?)'
            insert_values = (schedule_name, schedule)
            ui.queryQ.put(('전략디비', insert_query, insert_values))
            QMessageBox.information(ui.dialog_scheduler, '저장 완료', random.choice(famous_saying))
