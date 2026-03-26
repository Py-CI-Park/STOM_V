
import sys
from utility.setting_base import ui_num
from PyQt5.QtWidgets import QApplication
from utility.static import qtest_qwait, opstarter_kill, error_decorator


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
    if ui.CoinReceiverProcessAlive():
        ui.proc_receiver_coin.kill()
    if ui.CoinTraderProcessAlive():
        ui.proc_trader_coin.kill()
    if ui.CoinStrategyProcessAlive():
        ui.proc_strategy_coin.kill()
        ui.windowQ.put((ui_num['시스템로그'], 'Coin process terminate completed'))

    if ui.qtimer0.isActive(): ui.qtimer0.stop()
    if ui.qtimer1.isActive(): ui.qtimer1.stop()
    if ui.qtimer2.isActive(): ui.qtimer2.stop()
    if ui.qtimer3.isActive(): ui.qtimer3.stop()
    ui.windowQ.put((ui_num['시스템로그'], 'QTimer stop completed'))

    if ui.zmqserv.isRunning(): ui.zmqserv.stop()
    if ui.zmqrecv.isRunning(): ui.zmqrecv.stop()
    ui.windowQ.put((ui_num['시스템로그'], 'QThread terminate completed'))

    if ui.dialog_db.isVisible():         ui.dialog_db.close()
    if ui.dialog_web.isVisible():        ui.dialog_web.close()
    if ui.dialog_std.isVisible():        ui.dialog_std.close()
    if ui.dialog_jisu.isVisible():       ui.dialog_jisu.close()
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

    if ui.dict_set['창위치기억']:
        geo_len = len(ui.dict_set['창위치']) if ui.dict_set['창위치'] is not None else 0
        geometry = f"{ui.x()};{ui.y()};"
        geometry += f"{ui.dialog_chart.x()};{ui.dialog_chart.y() - 31 if geo_len > 3 and ui.dict_set['창위치'][3] + 31 == ui.dialog_chart.y() else ui.dialog_chart.y()};"
        geometry += f"{ui.dialog_scheduler.x()};{ui.dialog_scheduler.y() - 31 if geo_len > 5 and ui.dict_set['창위치'][5] + 31 == ui.dialog_scheduler.y() else ui.dialog_scheduler.y()};"
        geometry += f"{ui.dialog_jisu.x()};{ui.dialog_jisu.y() - 31 if geo_len > 7 and ui.dict_set['창위치'][7] + 31 == ui.dialog_jisu.y() else ui.dialog_jisu.y()};"
        geometry += f"{ui.dialog_info.x()};{ui.dialog_info.y() - 31 if geo_len > 9 and ui.dict_set['창위치'][9] + 31 == ui.dialog_info.y() else ui.dialog_info.y()};"
        geometry += f"{ui.dialog_web.x()};{ui.dialog_web.y() - 31 if geo_len > 11 and ui.dict_set['창위치'][11] + 31 == ui.dialog_web.y() else ui.dialog_web.y()};"
        geometry += f"{ui.dialog_tree.x()};{ui.dialog_tree.y() - 31 if geo_len > 13 and ui.dict_set['창위치'][13] + 31 == ui.dialog_tree.y() else ui.dialog_tree.y()};"
        geometry += f"{ui.dialog_kimp.x()};{ui.dialog_kimp.y() - 31 if geo_len > 15 and ui.dict_set['창위치'][15] + 31 == ui.dialog_kimp.y() else ui.dialog_kimp.y()};"
        geometry += f"{ui.dialog_hoga.x()};{ui.dialog_hoga.y() - 31 if geo_len > 17 and ui.dict_set['창위치'][17] + 31 == ui.dialog_hoga.y() else ui.dialog_hoga.y()};"
        geometry += f"{ui.dialog_backengine.x()};{ui.dialog_backengine.y() - 31 if geo_len > 19 and ui.dict_set['창위치'][19] + 31 == ui.dialog_backengine.y() else ui.dialog_backengine.y()};"
        geometry += f"{ui.dialog_order.x()};{ui.dialog_order.y() - 31 if geo_len > 21 and ui.dict_set['창위치'][21] + 31 == ui.dialog_order.y() else ui.dialog_order.y()};"
        geometry += f"{ui.dialog_strategy.x()};{ui.dialog_strategy.y() - 31 if geo_len > 23 and ui.dict_set['창위치'][23] + 31 == ui.dialog_strategy.y() else ui.dialog_strategy.y()}"
        query = f"UPDATE etc SET 창위치 = '{geometry}'"
        ui.queryQ.put(('설정디비', query))
    ui.windowQ.put((ui_num['시스템로그'], 'Etc setting save completed'))

    ui.queryQ.put('프로세스종료')
    while ui.proc_chqs.is_alive():
        qtest_qwait(0.1)

    if ui.writer.isRunning():
        ui.writer.terminate()

    opstarter_kill()
    qtest_qwait(1)

    QApplication.instance().quit()
    sys.exit()
