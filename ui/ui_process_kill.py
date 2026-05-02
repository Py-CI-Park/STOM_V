
from utility.setting_base import ui_num
from PyQt5.QtWidgets import QApplication
from utility.static import qtest_qwait, opstarter_kill, error_decorator


def _remember_window_positions(ui):
    """Persist live window positions before shutdown closes dialogs.

    The backtest engine dialog position is part of the window-position list
    at indexes 16 and 17. Persisting before dialog close prevents the Qt
    close/fade path from resetting coordinates before they are written.
    """
    try:
        if not ui.dict_set['창위치기억']:
            return

        saved = ui.dict_set['창위치'] if ui.dict_set['창위치'] is not None else []
        saved_len = len(saved)

        def normalized_y(widget, y_index):
            y = widget.y()
            if saved_len > y_index and saved[y_index] + 31 == y:
                return y - 31
            return y

        widgets = (
            (ui, 1),
            (ui.dialog_chart, 3),
            (ui.dialog_scheduler, 5),
            (ui.dialog_info, 7),
            (ui.dialog_web, 9),
            (ui.dialog_tree, 11),
            (ui.dialog_kimp, 13),
            (ui.dialog_hoga, 15),
            (ui.dialog_backengine, 17),
            (ui.dialog_order, 19),
            (ui.dialog_strategy, 21),
        )

        positions = []
        for widget, y_index in widgets:
            positions.extend([widget.x(), normalized_y(widget, y_index)])

        geometry = ';'.join(str(value) for value in positions)
        ui.dict_set['창위치'] = positions
        ui.queryQ.put(('설정디비', f"UPDATE etc SET 창위치 = '{geometry}'"))
    except Exception:
        pass


@error_decorator
def telegram_process_kill(ui):
    if ui.TelegramProcessAlive():
        ui.proc_tele.kill()


@error_decorator
def process_kill(ui):
    if ui.proc_manager is not None and ui.proc_manager.poll() is None:
        ui.wdzservQ.put(('manager', '프로세스종료'))
        ui.windowQ.put((ui_num['시스템로그'], 'Manager process terminate completed'))

    if ui.dict_set['에이전트프로파일링']:
        ui.wdzservQ.put(('agent', '프로파일링결과'))
        qtest_qwait(3)
    if ui.dict_set['트레이더프로파일링']:
        ui.wdzservQ.put(('trade', '프로파일링결과'))
        qtest_qwait(3)
    if ui.dict_set['전략연산프로파일링']:
        ui.wdzservQ.put(('strategy', '프로파일링결과'))
        qtest_qwait(3)

    if ui.CoinKimpProcessAlive():
        ui.proc_coin_kimp.kill()
    telegram_process_kill(ui)
    if ui.CoinReceiverProcessAlive():
        ui.proc_receiver_coin.kill()
    if ui.CoinTraderProcessAlive():
        ui.proc_trader_coin.kill()
    if ui.CoinStrategyProcessAlive():
        ui.proc_strategy_coin.kill()
        ui.windowQ.put((ui_num['시스템로그'], 'Coin process terminate completed'))

    if ui.qtimer1.isActive(): ui.qtimer1.stop()
    if ui.qtimer2.isActive(): ui.qtimer2.stop()
    if ui.qtimer3.isActive(): ui.qtimer3.stop()
    ui.windowQ.put((ui_num['시스템로그'], 'QTimer stop completed'))

    if hasattr(ui, 'webc') and ui.webc.isRunning():
        ui.webc.stop()
    if ui.zmqserv.isRunning(): ui.zmqserv.stop()
    if ui.zmqrecv.isRunning(): ui.zmqrecv.stop()
    ui.windowQ.put((ui_num['시스템로그'], 'QThread terminate completed'))

    _remember_window_positions(ui)

    if ui.dialog_db.isVisible():         ui.dialog_db.close()
    if ui.dialog_web.isVisible():        ui.dialog_web.close()
    if ui.dialog_std.isVisible():        ui.dialog_std.close()
    if ui.dialog_hoga.isVisible():       ui.dialog_hoga.close()
    if ui.dialog_info.isVisible():       ui.dialog_info.close()
    if ui.dialog_tree.isVisible():       ui.dialog_tree.close()
    if ui.dialog_kimp.isVisible():       ui.dialog_kimp.close()
    if ui.dialog_pass.isVisible():       ui.dialog_pass.close()
    if ui.dialog_comp.isVisible():       ui.dialog_comp.close()
    if ui.dialog_chart.isVisible():      ui.dialog_chart.close()
    if ui.dialog_graph.isVisible():      ui.dialog_graph.close()
    if ui.dialog_order.isVisible():      ui.dialog_order.close()
    if ui.dialog_cetsj.isVisible():      ui.dialog_cetsj.close()
    if ui.dialog_setsj.isVisible():      ui.dialog_setsj.close()
    if ui.dialog_factor.isVisible():     ui.dialog_factor.close()
    if ui.dialog_optuna.isVisible():     ui.dialog_optuna.close()
    if ui.dialog_formula.isVisible():    ui.dialog_formula.close()
    if ui.dialog_strategy.isVisible():   ui.dialog_strategy.close()
    if ui.dialog_leverage.isVisible():   ui.dialog_leverage.close()
    if ui.dialog_scheduler.isVisible():  ui.dialog_scheduler.close()
    if ui.dialog_backengine.isVisible(): ui.dialog_backengine.close()
    if ui.dialog_stg_input1.isVisible(): ui.dialog_stg_input1.close()
    if ui.dialog_stg_input2.isVisible(): ui.dialog_stg_input2.close()
    ui.windowQ.put((ui_num['시스템로그'], 'UI dialog window close completed'))

    if ui.shared_cnt is not None:
        ui.BacktestProcessKill(True, True)
        ui.windowQ.put((ui_num['시스템로그'], 'Backtest engine process terminate completed'))

    factor_choice = ''
    for checkbox in ui.factor_checkbox_list:
        factor_choice = f"{factor_choice}{'1' if checkbox.isChecked() else '0'};"
    query = f"UPDATE etc SET 팩터선택 = '{factor_choice[:-1]}'"
    ui.queryQ.put(('설정디비', query))

    백테엔진분류방법 = ui.be_comboBoxxxxx_01.currentText()
    옵튜나샘플러 = ui.op_comboBoxxxx_01.currentText()
    옵튜나고정변수 = ui.op_lineEditttt_01.text()
    옵튜나실행횟수 = int(ui.op_lineEditttt_02.text())
    옵튜나자동스탭 = 1 if ui.op_checkBoxxxx_01.isChecked() else 0

    columns = ['백테엔진분류방법', '옵튜나샘플러', '옵튜나고정변수', '옵튜나실행횟수', '옵튜나자동스탭']
    set_txt = ', '.join([f'{col} = ?' for col in columns])
    query   = f'UPDATE back SET {set_txt}'
    localvs = locals()
    values  = tuple(localvs[col] for col in columns)
    ui.queryQ.put(('설정디비', query, values))

    # Window positions are persisted before dialogs are closed.
    ui.windowQ.put((ui_num['시스템로그'], 'Etc setting save completed'))

    ui.queryQ.put('프로세스종료')
    while ui.proc_chqs.is_alive():
        qtest_qwait(0.1)

    if ui.writer.isRunning():
        ui.writer.terminate()

    opstarter_kill()
    qtest_qwait(1)

    QApplication.instance().quit()
