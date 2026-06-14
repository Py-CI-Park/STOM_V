
def _check_backengine(ui):
    """백테스트 엔진 구동여부를 확인합니다."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtWidgets import QApplication
    from ui.event_click.button_clicked_backtest_engine import backengine_show

    if ui.backengine_starting:
        QMessageBox.critical(ui, '오류 알림', '백테엔진 구동 중...\n')
        return False

    if ui.dialog_backengine.isVisible() and not ui.backengine_running:
        QMessageBox.critical(ui, '오류 알림', '백테엔진이 구동되지 않았습니다.\n')
        return False

    if not ui.backengine_running or (
            not (QApplication.keyboardModifiers() & Qt.ShiftModifier) and
            not (QApplication.keyboardModifiers() & Qt.AltModifier) and
            (QApplication.keyboardModifiers() & Qt.ControlModifier)
    ):
        backengine_show(ui)
        return False

    if ui.back_cancelling:
        QMessageBox.critical(ui, '오류 알림', '이전 백테스트를 중지하고 있습니다.\n잠시 후 다시 시도하십시오.\n')
        return False

    return True


def _backtest_init(ui):
    from ui.event_click.button_clicked_stg_editer import backtest_log
    backtest_log(ui)
    ui.ss_progressBar_01.setValue(0)
    ui.ssicon_alert = True


def backtest_start(ui):
    """백테스트를 시작합니다."""
    from PyQt5.QtCore import Qt
    from multiprocessing import Process
    from backtest.backtest import BackTest
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtWidgets import QApplication
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
            return

        back_club = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
        if back_club and not ui.backengine_running:
            QMessageBox.critical(ui, '오류 알림', '백테엔진을 먼저 구동하십시오.\n')
            return

        startday  = ui.svjb_dateEditt_01.date().toString('yyyyMMdd')
        endday    = ui.svjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.svjb_lineEditt_02.text()
        endtime   = ui.svjb_lineEditt_03.text()
        betting   = ui.svjb_lineEditt_04.text()
        avgtime   = ui.svjb_lineEditt_05.text()
        buystg    = ui.svjb_comboBoxx_01.currentText()
        sellstg   = ui.svjs_comboBoxx_01.currentText()
        bl        = True if ui.dict_set['블랙리스트추가'] else False

        if int(avgtime) not in ui.avg_list:
            QMessageBox.critical(ui, '오류 알림', '백테엔진 시작 시 포함되지 않은 평균값틱수를 사용하였습니다.\n현재의 틱수로 백테스팅하려면 백테엔진을 다시 시작하십시오.\n')
            return

        if '' in (startday, endday, starttime, endtime, betting, avgtime):
            QMessageBox.critical(ui, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
            return

        if '' in (buystg, sellstg):
            QMessageBox.critical(ui, '오류 알림', '전략을 저장하고 콤보박스에서 선택하십시오.\n')
            return

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '백테스트'))

        ui.proc_backtester_bs = Process(
            target=BackTest,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques, ui.back_sques,
                  ui.dict_set, ui.market_infos, betting, avgtime, startday, endday, starttime, endtime,
                  buystg, sellstg, ui.back_count, bl, False, back_club)
        )
        ui.proc_backtester_bs.start()
        _backtest_init(ui)


def backfinder_start(ui):
    """백파인더를 시작합니다."""
    from multiprocessing import Process
    from PyQt5.QtWidgets import QMessageBox
    from backtest.backfinder import BackFinder
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
            return

        startday  = ui.svjb_dateEditt_01.date().toString('yyyyMMdd')
        endday    = ui.svjb_dateEditt_02.date().toString('yyyyMMdd')
        starttime = ui.svjb_lineEditt_02.text()
        endtime   = ui.svjb_lineEditt_03.text()
        avgtime   = ui.svjb_lineEditt_05.text()
        buystg    = ui.svjb_comboBoxx_01.currentText()

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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '백파인더'))

        ui.proc_backtester_bf = Process(
            target=BackFinder,
            args=(ui.shared_cnt, ui.windowQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.dict_set,
                  ui.market_infos, avgtime, startday, endday, starttime, endtime, buystg, ui.back_count)
        )
        ui.proc_backtester_bf.start()
        _backtest_init(ui)


def opti_start(ui, back_name):
    """최적화를 시작합니다."""
    from PyQt5.QtCore import Qt
    from multiprocessing import Process
    from backtest.optimiz import Optimize
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtWidgets import QApplication
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
            return

        randomopti  = True if not (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.AltModifier) else False
        onlybuy     = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
                    QApplication.keyboardModifiers() & Qt.ShiftModifier) else False
        onlysell    = True if (QApplication.keyboardModifiers() & Qt.ControlModifier) and (
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, ccount, ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, False, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday, optunasampl,
            optunafixv, optunacount, optunaautos, randomopti, onlybuy, onlysell
        ))

        proc = Process(
            target=Optimize,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                  ui.back_sques, ui.multi, back_name, ui.dict_set, ui.market_infos)
        )

        if back_name == '최적화O':
            ui.proc_backtester_o = proc
            ui.proc_backtester_o.start()
        elif back_name == '최적화OV':
            ui.proc_backtester_ov = proc
            ui.proc_backtester_ov.start()
        elif back_name == '최적화OVC':
            ui.proc_backtester_ovc = proc
            ui.proc_backtester_ovc.start()
        elif back_name == '최적화B':
            ui.proc_backtester_b = proc
            ui.proc_backtester_b.start()
        elif back_name == '최적화BV':
            ui.proc_backtester_bv = proc
            ui.proc_backtester_bv.start()
        elif back_name == '최적화BVC':
            ui.proc_backtester_bvc = proc
            ui.proc_backtester_bvc.start()
        elif back_name == '최적화OT':
            ui.proc_backtester_ot = proc
            ui.proc_backtester_ot.start()
        elif back_name == '최적화OVT':
            ui.proc_backtester_ovt = proc
            ui.proc_backtester_ovt.start()
        elif back_name == '최적화OVCT':
            ui.proc_backtester_ovct = proc
            ui.proc_backtester_ovct.start()
        elif back_name == '최적화BT':
            ui.proc_backtester_bt = proc
            ui.proc_backtester_bt.start()
        elif back_name == '최적화BVT':
            ui.proc_backtester_bvt = proc
            ui.proc_backtester_bvt.start()
        else:
            ui.proc_backtester_bvct = proc
            ui.proc_backtester_bvct.start()

        _backtest_init(ui)


def opti_rwft_start(ui, back_name):
    """전진분석을 시작합니다."""
    from PyQt5.QtCore import Qt
    from multiprocessing import Process
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtWidgets import QApplication
    from ui.etcetera.process_alive import backtest_process_alive
    from backtest.rolling_walk_forward_test import RollingWalkForwardTest
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '전진분석'))

        ui.backQ.put((
            betting, startday, endday, starttime, endtime, buystg, sellstg, optivars, ccount,
            ui.dict_set['최적화기준값제한'], optistd, ui.back_count, False, weeks_train, weeks_valid, weeks_test,
            benginesday, bengineeday, optunasampl, optunafixv, optunacount, optunaautos, randomopti
        ))

        proc = Process(
            target=RollingWalkForwardTest,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.teleQ, ui.back_eques,
                  ui.back_sques, ui.multi, back_name, ui.dict_set, ui.market_infos)
        )

        if back_name == '전진분석OR':
            ui.proc_backtester_or = proc
            ui.proc_backtester_or.start()
        elif back_name == '전진분석ORV':
            ui.proc_backtester_orv = proc
            ui.proc_backtester_orv.start()
        elif back_name == '전진분석ORVC':
            ui.proc_backtester_orvc = proc
            ui.proc_backtester_orvc.start()
        elif back_name == '전진분석BR':
            ui.proc_backtester_br = proc
            ui.proc_backtester_br.start()
        elif back_name == '전진분석BRV':
            ui.proc_backtester_brv = proc
            ui.proc_backtester_brv.start()
        else:
            ui.proc_backtester_brvc = proc
            ui.proc_backtester_brvc.start()

        _backtest_init(ui)


def opti_ga_start(ui, back_name):
    """유전알고리즘 최적화를 시작합니다."""
    from multiprocessing import Process
    from PyQt5.QtWidgets import QMessageBox
    from ui.etcetera.process_alive import backtest_process_alive
    from backtest.optimiz_genetic_algorithm import OptimizeGeneticAlgorithm
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', 'GA최적화'))

        ui.backQ.put((
            betting, starttime, endtime, buystg, sellstg, optivars, ui.dict_set['최적화기준값제한'],
            optistd, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        proc = Process(
            target=OptimizeGeneticAlgorithm,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                  ui.multi, back_name, ui.dict_set, ui.market_infos)
        )

        if back_name == '최적화OG':
            ui.proc_backtester_og = proc
            ui.proc_backtester_og.start()
        elif back_name == '최적화OGV':
            ui.proc_backtester_ogv = proc
            ui.proc_backtester_ogv.start()
        else:
            ui.proc_backtester_ogvc = proc
            ui.proc_backtester_ogvc.start()

        _backtest_init(ui)


def opti_cond_start(ui, back_name):
    """조건 최적화를 시작합니다."""
    from multiprocessing import Process
    from PyQt5.QtWidgets import QMessageBox
    from backtest.optimiz_conditions import OptimizeConditions
    from ui.etcetera.process_alive import backtest_process_alive
    from ui.event_click.button_clicked_backtest_engine import clear_backtestQ

    if backtest_process_alive(ui):
        QMessageBox.critical(ui, '오류 알림', '현재 백테스트가 실행중입니다.\n중복 실행할 수 없습니다.\n')
    else:
        if not _check_backengine(ui):
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

        clear_backtestQ(ui)
        for q in ui.back_eques:
            q.put(('백테유형', '조건최적화'))

        ui.backQ.put((
            betting, avgtime, starttime, endtime, buystg, sellstg, ui.dict_set['최적화기준값제한'], optistd, bcount,
            scount, rcount, ui.back_count, weeks_train, weeks_valid, weeks_test, benginesday, bengineeday
        ))

        proc = Process(
            target=OptimizeConditions,
            args=(ui.shared_cnt, ui.windowQ, ui.backQ, ui.soundQ, ui.totalQ, ui.liveQ, ui.back_eques, ui.back_sques,
                  ui.multi, back_name, ui.dict_set, ui.market_infos)
        )

        if back_name == '최적화OC':
            ui.proc_backtester_oc = proc
            ui.proc_backtester_oc.start()
        elif back_name == '최적화OCV':
            ui.proc_backtester_ocv = proc
            ui.proc_backtester_ocv.start()
        else:
            ui.proc_backtester_ocvc = proc
            ui.proc_backtester_ocvc.start()

        _backtest_init(ui)
