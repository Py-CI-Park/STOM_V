
import numpy as np
import pandas as pd
import yfinance as yf
from numba import jit
from traceback import print_exc
from matplotlib import pyplot as plt
from optuna_dashboard import run_server
from matplotlib import font_manager, gridspec
from utility.setting import ui_num, GRAPH_PATH, DB_OPTUNA
from utility.static import thread_decorator, str_hms, str_hm, dt_ymdhms, dt_ymdhm, dt_hms, dt_hm, dt_ymd


@thread_decorator
def RunOptunaServer():
    try:
        run_server(DB_OPTUNA)
    except:
        pass


def get_trade_info(gubun):
    buy_time = dt_ymd('20000101')
    if gubun == 1:
        v = {
            '보유중': 0,
            '매수가': 0,
            '매도가': 0,
            '주문수량': 0,
            '보유수량': 0,
            '최고수익률': 0.,
            '최저수익률': 0.,
            '매수틱번호': 0,
            '매수시간': buy_time
        }
    elif gubun == 2:
        v = {
            '보유중': 0,
            '매수가': 0,
            '매도가': 0,
            '주문수량': 0,
            '보유수량': 0,
            '최고수익률': 0.,
            '최저수익률': 0.,
            '매수틱번호': 0,
            '매수시간': buy_time,
            '추가매수시간': [],
            '매수호가': 0,
            '매도호가': 0,
            '매수호가_': 0,
            '매도호가_': 0,
            '추가매수가': 0,
            '매수호가단위': 0,
            '매도호가단위': 0,
            '매수정정횟수': 0,
            '매도정정횟수': 0,
            '매수분할횟수': 0,
            '매도분할횟수': 0,
            '매수주문취소시간': buy_time,
            '매도주문취소시간': buy_time,
            '주문포지션': None
        }
    else:
        v = {
            '손절횟수': 0,
            '거래횟수': 0,
            '직전거래시간': buy_time,
            '손절매도시간': buy_time
        }
    return v


def GetBackloadCodeQuery(is_tick, code, days, starttime, endtime):
    conditions = []
    for day in days:
        if is_tick:
            sindex = day * 1000000 + starttime
            eindex = day * 1000000 + endtime
        else:
            sindex = day * 10000 + starttime
            eindex = day * 10000 + endtime
        conditions.append(f"(`index` >= {sindex} AND `index` <= {eindex})")
    where_clause = " OR ".join(conditions)
    query = f"SELECT * FROM '{code}' WHERE {where_clause}"
    return query


def GetMoneytopQuery(is_tick, gubun, startday, endday, starttime, endtime):
    if is_tick:
        if gubun == 'S' and starttime < 90030:
            sindex = startday * 1000000 + 90030
            eindex = endday * 1000000 + endtime
        else:
            sindex = startday * 1000000 + starttime
            eindex = endday * 1000000 + endtime
    else:
        sindex = startday * 10000 + starttime
        eindex = endday * 10000 + endtime
    query = f"SELECT * FROM moneytop WHERE " \
            f"`index` >= {sindex} AND `index` <= {eindex}"
    return query


def GetBuyStg(buytxt, gubun):
    lines   = [line for line in buytxt.split('\n') if line and line[0] != '#']
    buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
    indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
    if buystg:
        try:
            buystg = compile(buystg, '<string>', 'exec')
        except:
            buystg = None
            if gubun == 0: print_exc()
    else:
        buystg = None
    if indistg:
        try:
            indistg = compile(indistg, '<string>', 'exec')
        except:
            indistg = None
    else:
        indistg = None
    return buystg, indistg


def GetSellStg(sellstg, gubun):
    sellstg = 'self.sell_cond = 0\n' + sellstg
    sellstg, dict_cond = SetSellCond(sellstg.split('\n'))
    try:
        sellstg = compile(sellstg, '<string>', 'exec')
    except:
        sellstg = None
        if gubun == 0: print_exc()
    return sellstg, dict_cond


def GetBuyConds(buy_conds, gubun):
    buy_conds = 'if not (' + \
                '):\n    매수 = False\nelif not ('.join(buy_conds) + \
                '):\n    매수 = False\nif 매수:\n    self.Buy()'
    try:
        buy_conds = compile(buy_conds, '<string>', 'exec')
    except:
        buy_conds = None
        if gubun == 0: print_exc()
    return buy_conds


def GetSellConds(sell_conds, gubun):
    sell_conds = 'self.sell_cond = 0\nif not (' + \
                 '):\n    매도 = True\nelif not ('.join(sell_conds) + \
                 '):\n    매도 = True\nif 매도:\n    self.Sell()'
    sell_conds, dict_cond = SetSellCond(sell_conds.split('\n'))
    try:
        sell_conds = compile(sell_conds, '<string>', 'exec')
    except:
        sell_conds = None
        if gubun == 0: print_exc()
    return sell_conds, dict_cond


def SetSellCond(selllist):
    count = 1
    sellstg = ''
    dict_cond = {0: '전략종료청산', 100: '분할매도', 200: '손절청산'}
    for i, text in enumerate(selllist):
        if text and text[0] != '#' and ('매도 = True' in text or '매도= True' in text or '매도 =True' in text or '매도=True' in text):
            dict_cond[count] = selllist[i - 1]
            sellstg = f"{sellstg}{text.split('매도')[0]}self.sell_cond = {count}\n"
            count += 1
        if text:
            sellstg = f"{sellstg}{text}\n"
    return sellstg, dict_cond


def GetBuyStgFuture(buystg, gubun):
    lines   = [line for line in buystg.split('\n') if line and line[0] != '#']
    buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
    indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
    if buystg:
        try:
            buystg = compile(buystg, '<string>', 'exec')
        except:
            buystg = None
            if gubun == 0: print_exc()
    else:
        buystg = None
    if indistg:
        try:
            indistg = compile(indistg, '<string>', 'exec')
        except:
            indistg = None
    else:
        indistg = None
    return buystg, indistg


def GetSellStgFuture(sellstg, gubun):
    sellstg = 'self.sell_cond = 0\n' + sellstg
    sellstg, dict_cond = SetSellCondFuture(sellstg.split('\n'))
    try:
        sellstg = compile(sellstg, '<string>', 'exec')
    except:
        sellstg = None
        if gubun == 0: print_exc()
    return sellstg, dict_cond


def GetBuyCondsFuture(is_long, buy_conds, gubun):
    if is_long:
        buy_conds = 'if not (' + \
                    '):\n    BUY_LONG = False\nelif not ('.join(buy_conds) + \
                    '):\n    BUY_LONG = False\nif BUY_LONG:\n    self.Buy(BUY_LONG)'
    else:
        buy_conds = 'if not (' + \
                    '):\n    SELL_SHORT = False\nelif not ('.join(buy_conds) + \
                    '):\n    SELL_SHORT = False\nif SELL_SHORT:\n    self.Buy(BUY_LONG)'
    try:
        buy_conds = compile(buy_conds, '<string>', 'exec')
    except:
        buy_conds = None
        if gubun == 0: print_exc()
    return buy_conds


def GetSellCondsFuture(is_long, sell_conds, gubun):
    if is_long:
        sell_conds = 'self.sell_cond = 0\nif ' + ':\n    SELL_LONG = True\nelif '.join(
            sell_conds) + ':\n    SELL_LONG = True\nif SELL_LONG:\n    self.Sell(SELL_LONG)'
    else:
        sell_conds = 'self.sell_cond = 0\nif ' + ':\n    BUY_SHORT = True\nelif '.join(
            sell_conds) + ':\n    BUY_SHORT = True\nif BUY_SHORT:\n    self.Sell(SELL_LONG)'
    sell_conds, dict_cond = SetSellCondFuture(sell_conds.split('\n'))
    try:
        sell_conds = compile(sell_conds, '<string>', 'exec')
    except:
        sell_conds = None
        if gubun == 0: print_exc()
    return sell_conds, dict_cond


def SetSellCondFuture(selllist):
    count = 1
    sellstg = ''
    dict_cond = {0: '전략종료청산', 100: '분할매도', 200: '손절청산'}
    for i, text in enumerate(selllist):
        if '#' not in text:
            if 'SELL_LONG = True' in text or 'SELL_LONG= True' in text or 'SELL_LONG =True' in text or 'SELL_LONG=True' in text:
                dict_cond[count] = selllist[i - 1]
                sellstg = f"{sellstg}{text.split('SELL_LONG')[0]}self.sell_cond = {count}\n"
                count += 1
            elif 'BUY_SHORT = True' in text or 'BUY_SHORT= True' in text or 'BUY_SHORT =True' in text or 'BUY_SHORT=True' in text:
                dict_cond[count] = selllist[i - 1]
                sellstg = f"{sellstg}{text.split('BUY_SHORT')[0]}self.sell_cond = {count}\n"
                count += 1
        if text:
            sellstg = f"{sellstg}{text}\n"
    return sellstg, dict_cond


def SendResult(result, dict_train, dict_valid=None, exponential=False):
    gubun, ui_gubun, wq, mq, pre_hstd, optistd, opti_turn, vturn, vkey, vars_list, _, _, std_list, _ = result
    if gubun in ('최적화', '최적화테스트'):
        if opti_turn == 1:
            text1 = f"<font color=#ffffa0> self.vars[{vturn}] = {vars_list[vturn]} {'-' * 50}</font>\n"
        else:
            text1 = f'<font color=#a0ffa0> V{vars_list}</font>\n'
    elif gubun == 'GA최적화':
        text1 = f'<font color=white> V{vars_list} </font>'
    else:
        text1 = ''

    if dict_valid is not None:
        tuple_train = sorted(dict_train.items(), key=lambda x: x[0])
        tuple_valid = sorted(dict_valid.items(), key=lambda x: x[0])
        train_text = []
        valid_text = []
        train_stds = []
        valid_stds = []

        for k, v in tuple_train:
            text3, std = GetText3(f'TRAIN{k + 1}', optistd, std_list, v)
            train_text.append(text3)
            train_stds.append(std)
        for k, v in tuple_valid:
            text3, std = GetText3(f'VALID{k + 1}', optistd, std_list, v)
            valid_text.append(text3)
            valid_stds.append(std)

        train_stds = np.array(train_stds, dtype=np.float64)
        valid_stds = np.array(valid_stds, dtype=np.float64)
        std = GetOptiValidStd(train_stds, valid_stds, exponential)
        text2, hstd, sendtext = GetText2(std, pre_hstd)

        if sendtext or opti_turn == 4:
            wq.put((ui_num[f'{ui_gubun}백테스트'], f'{text1}{text2}'))
            for text3 in train_text:
                wq.put((ui_num[f'{ui_gubun}백테스트'], text3))
            for text3 in valid_text:
                wq.put((ui_num[f'{ui_gubun}백테스트'], text3))

    elif dict_train is not None:
        if gubun == '최적화테스트':
            text3, std  = GetText3('TEST', optistd, std_list, dict_train)
            text2, hstd, sendtext = '', pre_hstd, False
        else:
            text3, std  = GetText3('TOTAL', optistd, std_list, dict_train)
            text2, hstd, sendtext = GetText2(std, pre_hstd)

        if sendtext or opti_turn in (2, 4):
            wq.put((ui_num[f'{ui_gubun}백테스트'], f'{text1}{text2}'))
            wq.put((ui_num[f'{ui_gubun}백테스트'], text3))

    else:
        hstd = pre_hstd
        std  = -2_000_000_000

    if opti_turn != 2:
        mq.put((vturn, vkey, std))

    return hstd


def GetText2(std, pre_hstd):
    text = f'<font color=#ffffa0> MERGE[{std:,.2f}]</font>'
    if std > pre_hstd:
        text = f'{text}<font color=#54d2f9> [기준값갱신]</font>'
        return text, std, True
    elif std == pre_hstd:
        text = f'{text}<font color=white> [기준값동일]</font>'
        return text, std, False
    else:
        return text, pre_hstd, False


def GetText3(gubun, optistd, std_list, result):
    tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result
    if tpp < 0 < tsg: tsg = -float('inf')
    mddt  = f'{mdd_:,.0f}' if 'G' in optistd and optistd != 'CAGR' else f'{mdd:,.2f}%'
    color = '#ffa3d7' if 'TRAIN' not in gubun else '#a1afff'
    text  = f"<font color={color}>{gubun}</font>"
    text  = f"{text} <font color={color if tsg >= 0 else '#96969b'}>TC[{tc:,.0f}] ATC[{atc:,.1f}] MH[{mhct}] " \
            f"WR[{wr:,.2f}%] AP[{app:,.2f}%] TP[{tpp:,.2f}%] TG[{tsg:,.0f}] MDD[{mddt}] TPI[{tpi:,.2f}] CAGR[{cagr:,.2f}]"
    text, std = GetOptiStdText(optistd, std_list, result, text)
    return text, std


@jit(nopython=True, cache=True)
def GetOptiValidStd(train_stds, valid_stds, exponential):
    """
    가중치(weight) 예제 : 최고 1.3, 최저 0.7
    10개 : 1.300, 1.233, 1.166, 1.100, 1.033, 0.966, 0.900, 0.833, 0.766, 0.700
    """
    merge = 0.
    count = len(train_stds)
    for i in range(count):
        train_std = train_stds[i] * 0.7
        valid_std = valid_stds[i] * 0.3
        if exponential and count > 1:
            weight = 1.3 + (0.7 - 1.3) * i / (count - 1)
            valid_std *= weight
        merge += train_std + valid_std
    merge = np.round(merge / count, 2)
    return merge if merge != 0 else -float('inf')


def GetOptiStdText(optistd, std_list, result, pre_text):
    mdd_low, mdd_high, mhct_low, mhct_high, wr_low, wr_high, ap_low, ap_high, atc_low, atc_high, cagr_low, cagr_high, tpi_low, tpi_high = std_list
    tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result
    std_true = (mdd_low <= mdd <= mdd_high and mhct_low <= mhct <= mhct_high and wr_low <= wr <= wr_high and
                ap_low <= app <= ap_high and atc_low <= atc <= atc_high and cagr_low <= cagr <= cagr_high and tpi_low <= tpi <= tpi_high)

    std = -float('inf')
    if tc > 0:
        sign = 1 if cagr >= 0 else -1
        optistd_handlers = {
            'TP':   lambda: tpp,
            'PM':   lambda: np.round(tpp / mdd, 2),
            'P2M':  lambda: sign * abs(np.round(tpp * tpp / mdd, 2)),
            'PAM':  lambda: sign * abs(np.round(tpp * app / mdd, 2)),
            'PWM':  lambda: np.round(tpp * wr / mdd / 100, 2),
            'TG':   lambda: np.round(tsg / 1000, 2),
            'GM':   lambda: np.round(tsg / mdd_, 2),
            'G2M':  lambda: sign * abs(np.round(tsg * tsg / mdd_ / 1000, 2)),
            'GAM':  lambda: sign * abs(np.round(tsg * app / mdd_, 2)),
            'GWM':  lambda: np.round(tsg * wr / mdd_ / 100, 2),
            'CAGR': lambda: cagr
        }
        if 'TRAIN' in pre_text or 'TOTAL' in pre_text:
            if std_true:
                std = optistd_handlers[optistd]()
        else:
            std = optistd_handlers[optistd]()
        if std == 0: std = -float('inf')

    text_handlers = {
        'TP':   lambda: f'{pre_text}</font>',
        'TG':   lambda: f'{pre_text}</font>',
        'CAGR': lambda: f'{pre_text}</font>',
        'PM':   lambda: f'{pre_text} PM[{std:,.2f}]</font>',
        'P2M':  lambda: f'{pre_text} P2M[{std:,.2f}]</font>',
        'PAM':  lambda: f'{pre_text} PAM[{std:,.2f}]</font>',
        'PWM':  lambda: f'{pre_text} PWM[{std:,.2f}]</font>',
        'GM':   lambda: f'{pre_text} GM[{std:,.2f}]</font>',
        'G2M':  lambda: f'{pre_text} G2M[{std:,.2f}]</font>',
        'GAM':  lambda: f'{pre_text} GAM[{std:,.2f}]</font>',
        'GWM':  lambda: f'{pre_text} GWM[{std:,.2f}]</font>'
    }
    text = text_handlers[optistd]()
    return text, std


def PlotShow(is_tick, gubun, teleQ, df_tsg, df_bct, dict_cn, seed, mdd, startday, endday, starttime, endtime, list_days,
             backname, back_text, label_text, save_file_name, schedul, plotgraph, buy_vars=None, sell_vars=None):
    df_tsg['수익금합계020'] = df_tsg['수익금합계'].rolling(window=20).mean()
    df_tsg['수익금합계060'] = df_tsg['수익금합계'].rolling(window=60).mean()
    df_tsg['수익금합계120'] = df_tsg['수익금합계'].rolling(window=120).mean()
    df_tsg['수익금합계240'] = df_tsg['수익금합계'].rolling(window=240).mean()
    df_tsg['수익금합계480'] = df_tsg['수익금합계'].rolling(window=480).mean()

    df_tsg['이익금액'] = df_tsg['수익금'].apply(lambda x: x if x >= 0 else 0)
    df_tsg['손실금액'] = df_tsg['수익금'].apply(lambda x: x if x < 0 else 0)

    sig_array = df_tsg['수익금'].values
    mdd_list = []
    for i in range(30):
        random_cumsum = np.cumsum(np.random.permutation(sig_array))
        df_tsg[f'수익금합계{i}'] = random_cumsum
        try:
            lower = np.argmax(np.maximum.accumulate(random_cumsum) - random_cumsum)
            upper = np.argmax(random_cumsum[:lower])
            mdd_ = np.round(abs(random_cumsum[upper] - random_cumsum[lower]) / (random_cumsum[upper] + seed) * 100, 2)
        except:
            mdd_ = 0.
        mdd_list.append(mdd_)

    df_sg = df_tsg[['수익금']].copy()
    df_sg.index = df_sg.index.map(lambda x: dt_ymdhms(x) if is_tick else dt_ymdhm(x))

    df_ts = df_sg.resample('D').sum()
    df_ts['수익금합계'] = df_ts['수익금'].cumsum()
    df_ts['수익금합계'] = ((df_ts['수익금합계'] + seed) / seed - 1) * 100

    df_kp, df_kd, df_nd, df_bc = None, None, None, None
    start_str = str(startday)
    end_str   = str(endday)
    startday  = f'{start_str[:4]}-{start_str[4:6]}-{start_str[6:8]}'
    endday    = f'{end_str[:4]}-{end_str[4:6]}-{end_str[6:8]}'
    if startday != endday:
        if dict_cn is not None and '005930' in dict_cn:
            try:
                df_kp = yf.Ticker('^KS11').history(start=startday, end=endday, interval="1d")
                df_kp['종가'] = (df_kp['Close'] / df_kp['Close'].iloc[0] - 1) * 100
                df_kd = yf.Ticker('^KQ11').history(start=startday, end=endday, interval="1d")
                df_kd['종가'] = (df_kd['Close'] / df_kd['Close'].iloc[0] - 1) * 100
            except:
                pass
        elif dict_cn is not None and '005930' not in dict_cn:
            try:
                df_nd = yf.Ticker('QQQ').history(start=startday, end=endday, interval="1d")
                df_nd['종가'] = (df_nd['Close'] / df_nd['Close'].iloc[0] - 1) * 100
            except:
                pass
        else:
            try:
                df_bc = yf.Ticker('BTC-USD').history(start=startday, end=endday, interval="1d")
                df_bc['종가'] = (df_bc['Close'] / df_bc['Close'].iloc[0] - 1) * 100
            except:
                pass

    df_st = df_tsg[['수익금']].copy()
    df_st.index = df_st.index.map(lambda x: dt_hms(x[8:]) if is_tick else dt_hm(x[8:]))
    start_time = dt_hms(str(starttime).zfill(6))
    end_time = dt_hms(str(endtime).zfill(6))
    total_sec = (end_time - start_time).total_seconds()
    interval = f'{total_sec / 600}min' if total_sec >= 1800 else '3min'
    df_st = df_st.resample(interval).sum()
    df_st.index = df_st.index.map(lambda x: str_hms(x) if is_tick else str_hm(x))
    if is_tick:
        df_st.index = df_st.index.map(lambda x: f'{x[:2]}:{x[2:4]}:{x[4:]}')
    else:
        df_st.index = df_st.index.map(lambda x: f'{x[:2]}:{x[2:]}')
    df_st['이익금액'] = df_st['수익금'].apply(lambda x: x if x >= 0 else 0)
    df_st['손실금액'] = df_st['수익금'].apply(lambda x: x if x < 0 else 0)

    df_wt = df_tsg[['수익금']].copy()
    df_wt['요일'] = df_wt.index
    df_wt['요일'] = df_wt['요일'].apply(lambda x: dt_ymdhms(x).weekday() if is_tick else dt_ymdhm(x).weekday())
    sum_0 = df_wt[df_wt['요일'] == 0]['수익금'].sum()
    sum_1 = df_wt[df_wt['요일'] == 1]['수익금'].sum()
    sum_2 = df_wt[df_wt['요일'] == 2]['수익금'].sum()
    sum_3 = df_wt[df_wt['요일'] == 3]['수익금'].sum()
    sum_4 = df_wt[df_wt['요일'] == 4]['수익금'].sum()
    wt_index = ['월', '화', '수', '목', '금']
    wt_data = [sum_0, sum_1, sum_2, sum_3, sum_4]
    if dict_cn is None:
        sum_5 = df_wt[df_wt['요일'] == 5]['수익금'].sum()
        sum_6 = df_wt[df_wt['요일'] == 6]['수익금'].sum()
        wt_index += ['토', '일']
        wt_data += [sum_5, sum_6]
    wt_datap, wt_datam = [], []
    for data in wt_data:
        if data >= 0:
            wt_datap.append(data)
            wt_datam.append(0)
        else:
            wt_datap.append(0)
            wt_datam.append(data)

    if is_tick:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    else:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:]}')

    endx_list = None
    if gubun == '최적화':
        if is_tick:
            endx_list = [df_tsg[df_tsg['매도시간'] < list_days[2][0] * 1000000 + 240000].index[-1]]
        else:
            endx_list = [df_tsg[df_tsg['매도시간'] < list_days[2][0] * 10000 + 2400].index[-1]]
        if list_days[1] is not None:
            for vsday, _, _ in list_days[1]:
                if is_tick:
                    df_tsg_ = df_tsg[df_tsg['매도시간'] < vsday * 1000000]
                else:
                    df_tsg_ = df_tsg[df_tsg['매도시간'] < vsday * 10000]
                if len(df_tsg_) > 0:
                    endx_list.append(df_tsg_.index[-1])

    font_name = 'C:/Windows/Fonts/malgun.ttf'
    font_family = font_manager.FontProperties(fname=font_name).get_name()
    plt.rcParams['font.family'] = font_family
    plt.rcParams['axes.unicode_minus'] = False

    plt.figure(f'{backname} 부가정보', figsize=(12, 10))
    gs = gridspec.GridSpec(nrows=2, ncols=2, height_ratios=[1, 1])
    # noinspection PyTypeChecker
    plt.subplot(gs[0])
    for i in range(30):
        plt.plot(df_tsg.index, df_tsg[f'수익금합계{i}'], linewidth=0.5, label=f'MDD {mdd_list[i]}%')
    plt.plot(df_tsg.index, df_tsg['수익금합계'], linewidth=2, label=f'MDD {mdd}%', color='orange')
    max_mdd = max(mdd_list)
    min_mdd = min(mdd_list)
    avg_mdd = np.round(sum(mdd_list) / len(mdd_list), 2)
    plt.title(f'Max MDD [{max_mdd}%] | Min MDD [{min_mdd}%] | Avg MDD [{avg_mdd}%]')
    count = int(len(df_tsg) / 15) if int(len(df_tsg) / 15) >= 1 else 1
    plt.xticks(list(df_tsg.index[::count]), rotation=45)
    plt.grid()
    # noinspection PyTypeChecker
    plt.subplot(gs[1])
    plt.plot(df_ts.index, df_ts['수익금합계'], linewidth=2, label='수익률', color='orange')
    if df_kp is not None:
        # noinspection PyTypeChecker
        plt.plot(df_kp.index, df_kp['종가'], linewidth=0.5, label='코스피', color='r')
        plt.plot(df_kd.index, df_kd['종가'], linewidth=0.5, label='코스닥', color='b')
    elif df_nd is not None:
        # noinspection PyTypeChecker
        plt.plot(df_nd.index, df_nd['종가'], linewidth=0.5, label='NQ', color='r')
    elif df_bc is not None:
        # noinspection PyTypeChecker
        plt.plot(df_bc.index, df_bc['종가'], linewidth=0.5, label='KRW-BTC', color='r')
    plt.title('지수비교')
    count = int(len(df_ts) / 20) if int(len(df_ts) / 20) >= 1 else 1
    plt.xticks(list(df_ts.index[::count]), rotation=45)
    plt.legend(loc='best')
    plt.grid()
    # noinspection PyTypeChecker
    plt.subplot(gs[2])
    plt.bar(df_st.index, df_st['이익금액'], label='이익금액', color='r')
    plt.bar(df_st.index, df_st['손실금액'], label='손실금액', color='b')
    plt.title('시간별 수익금')
    plt.xticks(list(df_st.index), rotation=45)
    plt.legend(loc='best')
    plt.grid()
    # noinspection PyTypeChecker
    plt.subplot(gs[3])
    plt.bar(wt_index, wt_datap, label='이익금액', color='r')
    plt.bar(wt_index, wt_datam, label='손실금액', color='b')
    plt.title('요일별 수익금')
    plt.xticks(wt_index)
    plt.legend(loc='best')
    plt.grid()
    plt.tight_layout()
    plt.savefig(f"{GRAPH_PATH}/{save_file_name}_.png")

    if buy_vars is None:
        plt.figure(f'{backname} 결과', figsize=(12, 10))
    else:
        plt.figure(f'{backname} 결과', figsize=(12, 12))
    gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[1, 4])
    # noinspection PyTypeChecker
    plt.subplot(gs[0])
    plt.plot(df_bct.index, df_bct['보유금액'], label='보유금액', color='g')
    plt.xticks([])
    if buy_vars is None:
        plt.xlabel('\n' + back_text + '\n' + label_text)
    else:
        plt.xlabel('\n' + back_text + '\n' + label_text + '\n\n' + buy_vars + '\n\n' + sell_vars)
    plt.legend(loc='best')
    plt.grid()
    # noinspection PyTypeChecker
    plt.subplot(gs[1])
    plt.bar(df_tsg.index, df_tsg['이익금액'], label='이익금액', color='r')
    plt.bar(df_tsg.index, df_tsg['손실금액'], label='손실금액', color='b')
    plt.plot(df_tsg.index, df_tsg['수익금합계480'], linewidth=0.5, label='수익금합계480', color='k')
    plt.plot(df_tsg.index, df_tsg['수익금합계240'], linewidth=0.5, label='수익금합계240', color='gray')
    plt.plot(df_tsg.index, df_tsg['수익금합계120'], linewidth=0.5, label='수익금합계120', color='b')
    plt.plot(df_tsg.index, df_tsg['수익금합계060'], linewidth=0.5, label='수익금합계60', color='g')
    plt.plot(df_tsg.index, df_tsg['수익금합계020'], linewidth=0.5, label='수익금합계20', color='r')
    plt.plot(df_tsg.index, df_tsg['수익금합계'], linewidth=2, label='수익금합계', color='orange')
    if gubun == '최적화':
        for i, endx in enumerate(endx_list):
            plt.axvline(x=endx, color='red' if i == 0 else 'green', linestyle='--')
        plt.axvspan(endx_list[0], df_tsg.index[-1], facecolor='gray', alpha=0.1)
    count = int(len(df_tsg) / 20) if int(len(df_tsg) / 20) >= 1 else 1
    plt.xticks(list(df_tsg.index[::count]), rotation=45)
    plt.legend(loc='best')
    plt.grid()
    plt.tight_layout()
    plt.savefig(f"{GRAPH_PATH}/{save_file_name}.png")

    teleQ.put(f'{backname} {save_file_name.split("_")[1]} 완료.')
    teleQ.put(f"{GRAPH_PATH}/{save_file_name}_.png")
    teleQ.put(f"{GRAPH_PATH}/{save_file_name}.png")

    if not schedul and not plotgraph:
        plt.show()


def GetResultDataframe(ui_gubun, list_tsg, arry_bct):
    columns1 = [
        'index', '종목명', '포지션' if ui_gubun in ('SF', 'CF') else '시가총액', '매수시간', '매도시간',
        '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률', '수익금', '매도조건', '추가매수시간'
    ]
    columns2 = [
        '종목명', '포지션' if ui_gubun in ('SF', 'CF') else '시가총액', '매수시간', '매도시간',
        '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률', '수익금', '수익금합계', '매도조건', '추가매수시간'
    ]
    df_tsg = pd.DataFrame(list_tsg, columns=columns1)
    df_tsg.set_index('index', inplace=True)
    df_tsg.sort_index(inplace=True)
    df_tsg['수익금합계'] = df_tsg['수익금'].cumsum()
    df_tsg = df_tsg[columns2]
    arry_bct = arry_bct[arry_bct[:, 1] > 0]
    df_bct = pd.DataFrame(arry_bct[:, 1:], columns=['보유종목수', '보유금액'], index=arry_bct[:, 0])
    df_bct.index = df_bct.index.astype(str)
    return df_tsg, df_bct


def AddMdd(arry_tsg, result):
    """
    arry_tsg
    보유시간, 매도시간, 수익률, 수익금, 수익금합계
       0       1       2       3      4
    """
    try:
        array = arry_tsg[:, 4]
        lower = np.argmax(np.maximum.accumulate(array) - array)
        upper = np.argmax(array[:lower])
        mdd   = np.round(abs(array[upper] - array[lower]) / (array[upper] + result[10]) * 100, 2)
        mdd_  = int(abs(array[upper] - array[lower]))
    except:
        mdd   = abs(result[7])
        mdd_  = abs(result[8])
    result = result + (mdd, mdd_)
    return result


@jit(nopython=True, cache=True)
def GetResult(arry_tsg, arry_bct, betting, ui_gubun, day_count):
    """
    arry_tsg dtype 'float64'
    보유시간, 매도시간, 수익률, 수익금, 수익금합계
       0       1       2      3      4
    arry_bct dtype 'float64'
    체결시간, 보유중목수, 보유금액
      0         1        2
    """
    tc = len(arry_tsg)
    if tc == 0:
        return (0,) * 13

    profits   = arry_tsg[:, 3]
    is_profit = profits >= 0
    arry_p    = arry_tsg[is_profit]
    arry_m    = arry_tsg[~is_profit]

    pc   = len(arry_p)
    mc   = tc - pc
    atc  = tc / day_count
    wr   = (pc / tc) * 100

    ah   = arry_tsg[:, 0].mean()
    app  = arry_tsg[:, 2].mean()
    tsg  = profits.sum()

    appp = arry_p[:, 2].mean() if pc > 0 else 0
    ampp = abs(arry_m[:, 2].mean()) if mc > 0 else 0

    exclud_top1per = int(len(arry_bct) / 100)
    try:    mhct = int(arry_bct[exclud_top1per:, 1].max())
    except: mhct = 0
    try:    seed = int(arry_bct[exclud_top1per:, 2].max())
    except: seed = betting
    if seed < betting: seed = betting

    tpp  = tsg / seed * 100
    cagr = tpp / day_count * (365 if 'C' in ui_gubun else 250)
    tpi  = wr / 100 * (1 + appp / ampp) if ampp != 0 else 1.0

    return (
        tc,                 # 0 거래횟수
        np.round(atc, 1),   # 1 일평균 거래횟수
        pc,                 # 2 수익 거래횟수
        mc,                 # 3 손실 거래횟수
        np.round(wr, 2),    # 4 승률
        np.round(ah, 2),    # 5 평균보유시간
        np.round(app, 2),   # 6 평균수익률
        np.round(tpp, 2),   # 7 총수익률
        int(tsg),           # 8 총수익금
        mhct,               # 9 최대 보유종목수
        seed,               # 10 필요 자금
        np.round(cagr, 2),  # 11 연간 예상 수익률
        np.round(tpi, 2)    # 12 거래 성과 지수
    )
