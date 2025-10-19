import sqlite3
import pandas as pd
from multiprocessing import Process, Queue, Value, Lock
from backtester.back_code_test import BackCodeTest
from backtester.back_static import GetMoneytopQuery
from backtester.backengine_kiwoom_tick import BackEngineKiwoomTick
from backtester.backengine_kiwoom_tick2 import BackEngineKiwoomTick2
from backtester.backengine_kiwoom_min import BackEngineKiwoomMin
from backtester.backengine_kiwoom_min2 import BackEngineKiwoomMin2
from backtester.backengine_future_tick import BackEngineFutureTick
from backtester.backengine_future_tick2 import BackEngineFutureTick2
from backtester.backengine_future_min import BackEngineFutureMin
from backtester.backengine_future_min2 import BackEngineFutureMin2
from backtester.backengine_upbit_tick import BackEngineUpbitTick
from backtester.backengine_upbit_tick2 import BackEngineUpbitTick2
from backtester.backengine_upbit_min import BackEngineUpbitMin
from backtester.backengine_upbit_min2 import BackEngineUpbitMin2
from backtester.backengine_binance_tick import BackEngineBinanceTick
from backtester.backengine_binance_tick2 import BackEngineBinanceTick2
from backtester.backengine_binance_min import BackEngineBinanceMin
from backtester.backengine_binance_min2 import BackEngineBinanceMin2
from backtester.back_subtotal import BackSubTotal
from ui.set_style import style_bc_dk
from utility.static import thread_decorator, qtest_qwait
from utility.setting import DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, ui_num, DB_STOCK_BACK_MIN, DB_COIN_BACK_MIN, \
    DB_FUTURE_BACK_MIN, DB_FUTURE_BACK_TICK


def backengine_show(ui, gubun):
    table_list = []
    if gubun == '주식':
        if '키움증권' in ui.dict_set['증권사']:
            db = DB_STOCK_BACK_TICK if ui.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
        else:
            db = DB_FUTURE_BACK_TICK if ui.dict_set['주식타임프레임'] else DB_FUTURE_BACK_MIN
    else:
        db = DB_COIN_BACK_TICK if ui.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
    con = sqlite3.connect(db)
    try:
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()
        table_list.remove('moneytop')
        table_list.remove('stockinfo')
        table_list.remove('futureinfo')
    except:
        pass
    con.close()
    if table_list:
        name_list = [ui.dict_name[code] if code in ui.dict_name else code for code in table_list]
        name_list.sort()
        ui.be_comboBoxxxxx_02.clear()
        for name in name_list:
            ui.be_comboBoxxxxx_02.addItem(name)
    if gubun == '주식':
        if '키움증권' in ui.dict_set['증권사']:
            if ui.dict_set['주식타임프레임']:
                starttime = '90000'
            else:
                starttime = '900'
        else:
            if ui.dict_set['주식타임프레임']:
                starttime = '93000'
            else:
                starttime = '900'
        if '키움증권' in ui.dict_set['증권사']:
            if ui.dict_set['주식타임프레임']:
                endtime = '93000'
            else:
                endtime = '1520'
        else:
            if ui.dict_set['주식타임프레임']:
                endtime = '103000'
            else:
                endtime = '1600'
        ui.be_lineEdittttt_01.setText(starttime)
        ui.be_lineEdittttt_02.setText(endtime)
    else:
        ui.be_lineEdittttt_01.setText('0')
        ui.be_lineEdittttt_02.setText('235000' if ui.dict_set['코인타임프레임'] else '2350')
    if not ui.backengin_window_open:
        ui.be_comboBoxxxxx_01.setCurrentText(ui.dict_set['백테엔진분류방법'])
    ui.dialog_backengine.show()
    ui.backengin_window_open = True


@thread_decorator
def backengine_start(ui, gubun):
    ui.back_engining = True
    ui.startday   = int(ui.be_dateEdittttt_01.date().toString('yyyyMMdd'))
    ui.endday     = int(ui.be_dateEdittttt_02.date().toString('yyyyMMdd'))
    ui.starttime  = int(ui.be_lineEdittttt_01.text())
    ui.endtime    = int(ui.be_lineEdittttt_02.text())
    ui.avg_list   = [int(x) for x in ui.be_lineEdittttt_03.text().split(',')]
    multi         = int(ui.be_lineEdittttt_04.text())
    divid_mode    = ui.be_comboBoxxxxx_01.currentText()
    one_name      = ui.be_comboBoxxxxx_02.currentText()
    one_code      = ui.dict_code[one_name] if one_name in ui.dict_code else one_name
    ui.multi      = multi
    ui.divid_mode = divid_mode

    for i in range(20):
        bctq = Queue()
        ui.back_sques.append(bctq)
    for i in range(20):
        proc = Process(target=BackSubTotal, args=(i, ui.totalQ, ui.back_sques, ui.dict_set['백테매수시간기준']), daemon=True)
        proc.start()
        ui.back_sprocs.append(proc)
        ui.windowQ.put((ui_num['백테엔진'], f'중간집계 프로세스{i + 1} 생성 완료'))

    ui.shared_cnt  = Value('i', 0)
    ui.shared_lock = Lock()

    for i in range(multi):
        beq = Queue()
        ui.back_eques.append(beq)

    for i in range(multi):
        if gubun == '주식':
            if not ui.dict_set['백테주문관리적용']:
                target = BackEngineKiwoomTick if ui.dict_set['주식타임프레임'] else BackEngineKiwoomMin
            else:
                target = BackEngineKiwoomTick2 if ui.dict_set['주식타임프레임'] else BackEngineKiwoomMin2
        elif gubun == '해선':
            if not ui.dict_set['백테주문관리적용']:
                target = BackEngineFutureTick if ui.dict_set['주식타임프레임'] else BackEngineFutureMin
            else:
                target = BackEngineFutureTick2 if ui.dict_set['주식타임프레임'] else BackEngineFutureMin2
        else:
            if ui.dict_set['거래소'] == '업비트':
                if not ui.dict_set['백테주문관리적용']:
                    target = BackEngineUpbitTick if ui.dict_set['코인타임프레임'] else BackEngineUpbitMin
                else:
                    target = BackEngineUpbitTick2 if ui.dict_set['코인타임프레임'] else BackEngineUpbitMin2
            else:
                if not ui.dict_set['백테주문관리적용']:
                    target = BackEngineBinanceTick if ui.dict_set['코인타임프레임'] else BackEngineBinanceMin
                else:
                    target = BackEngineBinanceTick2 if ui.dict_set['코인타임프레임'] else BackEngineBinanceMin2

        if i == 0 and ui.dict_set['백테엔진프로파일링']:
            proc = Process(
                target=target, args=(i, ui.shared_cnt, ui.shared_lock, ui.windowQ, ui.totalQ, ui.backQ, ui.back_eques, ui.back_sques, True), daemon=True
            )
        else:
            proc = Process(
                target=target, args=(i, ui.shared_cnt, ui.shared_lock, ui.windowQ, ui.totalQ, ui.backQ, ui.back_eques, ui.back_sques), daemon=True
            )
        proc.start()
        ui.back_eprocs.append(proc)
        ui.windowQ.put((ui_num['백테엔진'], f'엔진 프로세스{i + 1} 생성 완료'))

    dict_info = {}
    try:
        if gubun == '주식':
            db = DB_STOCK_BACK_TICK if ui.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
        elif gubun == '해선':
            db = DB_FUTURE_BACK_TICK if ui.dict_set['주식타임프레임'] else DB_FUTURE_BACK_MIN
        else:
            db = DB_COIN_BACK_TICK if ui.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN

        con = sqlite3.connect(db)
        if gubun == '주식':
            try:
                df_cn = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
            except:
                df_cn = pd.read_sql('SELECT * FROM codename', con).set_index('index')
            ui.dict_cn = df_cn['종목명'].to_dict()
        elif gubun == '해선':
            df_cn = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
            dict_info = df_cn.to_dict('index')
            ui.dict_cn = df_cn['종목명'].to_dict()

        gubun_ = 'S' if gubun == '주식' else 'X'
        query = GetMoneytopQuery(gubun_, ui.startday, ui.endday, ui.starttime, ui.endtime)
        df_mt = pd.read_sql(query, con)
        df_mt['일자'] = df_mt['index'].apply(lambda x: int(str(x)[:8]))
        df_mt.set_index('index', inplace=True)
        con.close()
    except:
        if gubun in ('주식', '해선'):
            if ui.dict_cn is None:
                ui.windowQ.put((ui_num['백테엔진'], '백테디비에 데이터가 존재하지 않습니다. 디비관리창(Alt + D)에서 백테디비를 생성하십시오.'))
            elif gubun == '주식' and len(ui.dict_cn) < 100:
                ui.windowQ.put((ui_num['백테엔진'], '종목명 테이블이 갱신되지 않았습니다. 수동로그인(Alt + S)을 1회 실행하시오.'))
            else:
                ui.windowQ.put((ui_num['백테엔진'], '백테디비에 데이터가 존재하지 않습니다. 디비관리창(Alt + D)에서 백테디비를 생성하십시오.'))
        else:
            ui.windowQ.put((ui_num['백테엔진'], '백테디비에 데이터가 존재하지 않습니다. 디비관리창(Alt + D)에서 백테디비를 생성하십시오.'))
        ui.BacktestEngineKill()
        return

    if df_mt is None or df_mt.empty:
        ui.windowQ.put((ui_num['백테엔진'], '시작 또는 종료일자가 잘못 선택되었거나 해당 일자에 데이터가 존재하지 않습니다.'))
        ui.BacktestEngineKill()
        return

    day_set = set(df_mt['일자'].to_list())

    code_set = set()
    for mt_text in df_mt['거래대금순위'].values:
        code_set.update(mt_text.split(';'))

    day_codes = {}
    for day in day_set:
        df_mt_ = df_mt[df_mt['일자'] == day]
        codes = set()
        for mt_text in df_mt_['거래대금순위'].values:
            codes.update(mt_text.split(';'))
        day_codes[day] = codes

    code_days = {}
    for code in code_set:
        code_days[code] = {day for day, codes in day_codes.items() if code in codes}

    if divid_mode == '종목코드별 분류' and len(code_set) < multi:
        ui.windowQ.put((ui_num['백테엔진'], '선택한 일자의 종목의 개수가 멀티수보다 작습니다. 일자를 늘리십시오.'))
        ui.BacktestEngineKill()
        return

    if divid_mode == '일자별 분류' and len(day_set) < multi:
        ui.windowQ.put((ui_num['백테엔진'], '선택한 일자의 수가 멀티수보다 작습니다. 일자를 늘리십시오.'))
        ui.BacktestEngineKill()
        return

    if divid_mode == '한종목 로딩' and one_code not in code_days:
        ui.windowQ.put((ui_num['백테엔진'], f'{one_name} 종목은 선택한 일자에 데이터가 존재하지 않습니다.'))
        ui.BacktestEngineKill()
        return

    if divid_mode == '한종목 로딩' and len(code_days[one_code]) < multi:
        ui.windowQ.put((ui_num['백테엔진'], f'{one_name} 선택한 종목의 일자의 수가 멀티수보다 작습니다. 일자를 늘리십시오.'))
        ui.BacktestEngineKill()
        return

    ui.wdzservQ.put(('manager', '백테엔진구동'))

    if gubun in ('주식', '해선'):
        for i in range(multi):
            if gubun == '주식':
                ui.back_eques[i].put(('종목명', ui.dict_cn))
            else:
                ui.back_eques[i].put(('종목명', dict_info))
    ui.windowQ.put((ui_num['백테엔진'], '거래대금순위 및 종목코드 추출 완료'))

    log_gubun = divid_mode.split()[0]
    if log_gubun == '한종목': log_gubun = f'{log_gubun} 일자별'

    ui.windowQ.put((ui_num['백테엔진'], f'{log_gubun} 데이터 로딩 시작'))
    data_list  = code_set if log_gubun == '종목코드별' else day_set if log_gubun == '일자별' else code_days[one_code]
    data_lists = []
    for i in range(multi):
        data_lists.append([data for j, data in enumerate(data_list) if j % multi == i])
    for i, datas in enumerate(data_lists):
        ui.back_eques[i].put(('데이터로딩', ui.startday, ui.endday, ui.starttime, ui.endtime, datas, ui.avg_list, code_days, day_codes, one_code, divid_mode))

    ui.shared_info = []
    for i in range(multi):
        shared_info_ = ui.backQ.get()
        ui.shared_info += shared_info_
        ui.windowQ.put((ui_num['백테엔진'], f'{log_gubun} 데이터 로딩 중 ... [{i+1}/{multi}]'))
    ui.shared_info = sorted(ui.shared_info, key=lambda x: x['len'], reverse=True)
    ui.windowQ.put((ui_num['백테엔진'], f'{log_gubun} 데이터 로딩 완료'))

    ui.back_count = len(ui.shared_info)
    for q in ui.back_eques:
        q.put(('공유데이터', ui.back_count, ui.shared_info))

    ui.back_engining = False
    ui.backtest_engine = True
    ui.windowQ.put((ui_num['백테엔진'], '백테엔진 준비 완료'))


def back_code_test1(ui, stg, testQ):
    while not testQ.empty():
        testQ.get()
    thread = BackCodeTest(testQ, stg)
    thread.start()
    thread.wait()
    return get_code_test_result(ui, '전략', testQ)


def back_code_test2(ui, vars_code, testQ, ga):
    while not testQ.empty():
        testQ.get()
    thread = BackCodeTest(testQ, None, vars_code, ga)
    thread.start()
    thread.wait()
    return get_code_test_result(ui, '범위', testQ)


def back_code_test3(ui, gubun, conds_code, testQ):
    while not testQ.empty():
        testQ.get()
    conds_code = conds_code.split('\n')
    conds_code = [x for x in conds_code if x and '#' not in x]
    if gubun == '매수':
        conds_code = 'if not (' + '):\n    매수 = False\nelif not ('.join(conds_code) + '):\n    매수 = False'
    else:
        conds_code = 'if ' + ':\n    매도 = True\nelif '.join(conds_code) + ':\n    매도 = True'
    thread = BackCodeTest(testQ, conds_code)
    thread.start()
    thread.wait()
    return get_code_test_result(ui, '조건', testQ)


def get_code_test_result(ui, gubun, testQ):
    data = testQ.get()
    if data == '전략테스트오류':
        ui.logger.error(f'{gubun}에 오류가 있어 저장하지 못하였습니다.')
        return False
    else:
        return True


def clear_backtestQ(ui):
    if not ui.backQ.empty():
        while not ui.backQ.empty():
            ui.backQ.get()
    if not ui.totalQ.empty():
        while not ui.totalQ.empty():
            ui.totalQ.get()


def backtest_process_kill(ui, coin, enginekill):
    ui.back_cancelling = True
    for q in ui.back_eques:
        q.put('백테중지')
    ui.totalQ.put('백테중지')

    count = 0
    while True:
        if not ui.backQ.empty():
            data = ui.backQ.get()
            if data == '백테중지완료':
                count += 1
                if count == ui.multi:
                    break
        qtest_qwait(0.01)

    ui.windowQ.put((ui_num['C백테스트' if coin else 'S백테스트'], '백테스트 중지 완료'))
    if not coin:
        ui.ss_pushButtonn_08.setStyleSheet(style_bc_dk)
        ui.ssicon_alert = False
        ui.main_btn_list[2].setIcon(ui.icon_stocks)
        ui.ss_progressBar_01.setValue(0)
        ui.ss_progressBar_01.setFormat('%p%')
    else:
        ui.cs_pushButtonn_08.setStyleSheet(style_bc_dk)
        ui.csicon_alert = False
        ui.main_btn_list[3].setIcon(ui.icon_coins)
        ui.cs_progressBar_01.setValue(0)
        ui.cs_progressBar_01.setFormat('%p%')

    ui.back_scount = 0
    ui.back_schedul = False

    if enginekill: ui.BacktestEngineKill()
    ui.back_cancelling = False
