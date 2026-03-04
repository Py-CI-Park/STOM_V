
import sys
from utility.static import qtest_qwait, opstarter_kill


def process_kill(ui):
    if ui.dict_set['에이전트프로파일링']:
        ui.wdzservQ.put(('agent', '프로파일링결과'))
        qtest_qwait(3)
    if ui.dict_set['트레이더프로파일링']:
        ui.wdzservQ.put(('trade', '프로파일링결과'))
        qtest_qwait(3)
    if ui.dict_set['전략연산프로파일링']:
        ui.wdzservQ.put(('analyzer', '프로파일링결과'))
        qtest_qwait(3)

    ui.wdzservQ.put(('manager', '통신종료'))
    ui.logger.info('Manager Process Terminate Completed')

    if ui.CoinKimpProcessAlive():
        ui.proc_coin_kimp.kill()
    if ui.CoinReceiverProcessAlive():
        ui.proc_receiver_coin.kill()
    if ui.CoinTraderProcessAlive():
        ui.proc_trader_coin.kill()
    if ui.CoinStrategyProcessAlive():
        ui.proc_strategy_coin.kill()
        ui.logger.info('Coin Process Terminate Completed')
        qtest_qwait(3)

    if ui.writer.isRunning():  ui.writer.terminate()
    if ui.zmqrecv.isRunning(): ui.zmqrecv.terminate()
    if ui.zmqserv.isRunning():
        ui.zmqserv.terminate()
        ui.logger.info('QThread Terminate Completed')

    if ui.shared_cnt is not None:
        ui.BacktestProcessKill(True, True)
        ui.logger.info('Backtest Engine Process Terminate Completed')

    factor_choice = ''
    for checkbox in ui.factor_checkbox_list:
        factor_choice = f"{factor_choice}{'1' if checkbox.isChecked() else '0'};"
    query = f"UPDATE etc SET 팩터선택 = '{factor_choice[:-1]}'"
    ui.queryQ.put(('설정디비', query))
    divid_mode = ui.be_comboBoxxxxx_01.currentText()
    optuna_sampler = ui.op_comboBoxxxx_01.currentText()
    optuna_fixvars = ui.op_lineEditttt_01.text()
    optuna_count = int(ui.op_lineEditttt_02.text())
    optuna_autostep = 1 if ui.op_checkBoxxxx_01.isChecked() else 0
    query = f"UPDATE back SET 백테엔진분류방법 = '{divid_mode}', '옵튜나샘플러' = '{optuna_sampler}', '옵튜나고정변수' = '{optuna_fixvars}', '옵튜나실행횟수' = {optuna_count}, '옵튜나자동스탭' = {optuna_autostep}"
    ui.queryQ.put(('설정디비', query))

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

    ui.logger.info('Etc Setting Save Completed')
    ui.queryQ.put('프로세스종료')
    while ui.proc_query.is_alive():
        qtest_qwait(0.1)
    opstarter_kill()
    ui.logger.info('Main Process Terminate Completed')
    sys.exit()
