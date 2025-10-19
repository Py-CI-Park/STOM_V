import numpy as np
import pandas as pd
import yfinance as yf
from numba import jit
from talib import stream
from traceback import print_exc
from matplotlib import pyplot as plt
from optuna_dashboard import run_server
from matplotlib import font_manager, gridspec
from utility.setting import ui_num, GRAPH_PATH, DB_OPTUNA, dgree
from utility.static import thread_decorator, str_hms, str_hm, dt_ymdhms, dt_ymdhm, dt_hms, dt_hm, dt_ymd


@thread_decorator
def RunOptunaServer():
    try:
        run_server(DB_OPTUNA)
    except:
        pass


def GetTradeInfo(gubun):
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
            '매도주문취소시간': buy_time
        }
    else:
        v = {
            '손절횟수': 0,
            '거래횟수': 0,
            '직전거래시간': buy_time,
            '손절매도시간': buy_time
        }
    return v


def GetBackloadCodeQuery(code, days, starttime, endtime):
    like_text = " or ".join([f"`index` LIKE '{day}%'" for day in days])
    like_text = f"({like_text})"

    if len(str(endtime)) < 5:
        query = f"SELECT * FROM '{code}' WHERE {like_text} and " \
                f"`index` % 10000 >= {starttime} and " \
                f"`index` % 10000 <= {endtime}"
    else:
        query = f"SELECT * FROM '{code}' WHERE {like_text} and " \
                f"`index` % 1000000 >= {starttime} and " \
                f"`index` % 1000000 <= {endtime}"
    return query


def GetBackloadDayQuery(day, code, starttime, endtime):
    if len(str(endtime)) < 5:
        query = f"SELECT * FROM '{code}' WHERE " \
                f"`index` LIKE '{day}%' and " \
                f"`index` % 10000 >= {starttime} and " \
                f"`index` % 10000 <= {endtime}"
    else:
        query = f"SELECT * FROM '{code}' WHERE " \
                f"`index` LIKE '{day}%' and " \
                f"`index` % 1000000 >= {starttime} and " \
                f"`index` % 1000000 <= {endtime}"
    return query


def GetMoneytopQuery(gubun, startday, endday, starttime, endtime):
    if len(str(endtime)) < 5:
        query = f"SELECT * FROM moneytop WHERE " \
                f"`index` >= {startday * 10000} and " \
                f"`index` <= {endday * 10000 + 2400} and " \
                f"`index` % 10000 >= {starttime} and " \
                f"`index` % 10000 <= {endtime}"
    else:
        if gubun == 'S' and starttime < 90030:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {startday * 1000000} and " \
                    f"`index` <= {endday * 1000000 + 240000} and " \
                    f"`index` % 1000000 >= 90030 and " \
                    f"`index` % 1000000 <= {endtime}"
        else:
            query = f"SELECT * FROM moneytop WHERE " \
                    f"`index` >= {startday * 1000000} and " \
                    f"`index` <= {endday * 1000000 + 240000} and " \
                    f"`index` % 1000000 >= {starttime} and " \
                    f"`index` % 1000000 <= {endtime}"
    return query


def AddAvgData(df, avg_gubun, is_tick, avg_list):
    """
    avg_gubun = 1   # 주식
    avg_gubun = 2   # 해선
    avg_gubun = 3   # 코인
    """
    if avg_gubun == 1:
        round_unit = 3
    else:
        round_unit = 8
    if is_tick:
        df['이평0060'] = df['현재가'].rolling(window=60).mean().round(round_unit)
        df['이평0300'] = df['현재가'].rolling(window=300).mean().round(round_unit)
        df['이평0600'] = df['현재가'].rolling(window=600).mean().round(round_unit)
        df['이평1200'] = df['현재가'].rolling(window=1200).mean().round(round_unit)
    else:
        df['이평005'] = df['현재가'].rolling(window=5).mean().round(round_unit)
        df['이평010'] = df['현재가'].rolling(window=10).mean().round(round_unit)
        df['이평020'] = df['현재가'].rolling(window=20).mean().round(round_unit)
        df['이평060'] = df['현재가'].rolling(window=60).mean().round(round_unit)
        df['이평120'] = df['현재가'].rolling(window=120).mean().round(round_unit)
    for avg in avg_list:
        df[f'최고현재가{avg}'] = df['현재가'].rolling(window=avg).max()
        df[f'최저현재가{avg}'] = df['현재가'].rolling(window=avg).min()
        if not is_tick:
            df[f'최고분봉고가{avg}'] = df['분봉고가'].rolling(window=avg).max()
            df[f'최저분봉저가{avg}'] = df['분봉저가'].rolling(window=avg).min()
        df[f'체결강도평균{avg}'] = df['체결강도'].rolling(window=avg).mean().round(3)
        df[f'최고체결강도{avg}'] = df['체결강도'].rolling(window=avg).max()
        df[f'최저체결강도{avg}'] = df['체결강도'].rolling(window=avg).min()
        if is_tick:
            df[f'최고초당매수수량{avg}'] = df['초당매수수량'].rolling(window=avg).max()
            df[f'최고초당매도수량{avg}'] = df['초당매도수량'].rolling(window=avg).max()
            df[f'누적초당매수수량{avg}'] = df['초당매수수량'].rolling(window=avg).sum()
            df[f'누적초당매도수량{avg}'] = df['초당매도수량'].rolling(window=avg).sum()
            df[f'초당거래대금평균{avg}'] = df['초당거래대금'].rolling(window=avg).mean().round(0)
        else:
            df[f'최고분당매수수량{avg}'] = df['분당매수수량'].rolling(window=avg).max()
            df[f'최고분당매도수량{avg}'] = df['분당매도수량'].rolling(window=avg).max()
            df[f'누적분당매수수량{avg}'] = df['분당매수수량'].rolling(window=avg).sum()
            df[f'누적분당매도수량{avg}'] = df['분당매도수량'].rolling(window=avg).sum()
            df[f'분당거래대금평균{avg}'] = df['분당거래대금'].rolling(window=avg).mean().round(0)
        if avg_gubun == 1:
            df2 = df[['등락율', '당일거래대금', '전일비']].copy()
            df2[f'등락율N{avg}'] = df2['등락율'].shift(avg - 1)
            df2['등락율차이'] = df2['등락율'] - df2[f'등락율N{avg}']
            df2[f'당일거래대금N{avg}'] = df2['당일거래대금'].shift(avg - 1)
            df2['당일거래대금차이'] = df2['당일거래대금'] - df2[f'당일거래대금N{avg}']
            df2[f'전일비N{avg}'] = df2['전일비'].shift(avg - 1)
            df2['전일비차이'] = df2['전일비'] - df2[f'전일비N{avg}']
            cf1, cf2 = dgree['stock']['tick'] if is_tick else dgree['stock']['min']
            df['등락율각도'] = np.round(np.arctan2(df2['등락율차이'] * cf1, avg) / (2 * np.pi) * 360, 2)
            df['당일거래대금각도'] = np.round(np.arctan2(df2['당일거래대금차이'] * cf2, avg) / (2 * np.pi) * 360, 2)
            df['전일비각도'] = np.round(np.arctan2(df2['전일비차이'], avg) / (2 * np.pi) * 360, 2)
        else:
            df2 = df[['등락율', '당일거래대금']].copy()
            df2[f'등락율N{avg}'] = df2['등락율'].shift(avg - 1)
            df2['등락율차이'] = df2['등락율'] - df2[f'등락율N{avg}']
            df2[f'당일거래대금N{avg}'] = df2['당일거래대금'].shift(avg - 1)
            df2['당일거래대금차이'] = df2['당일거래대금'] - df2[f'당일거래대금N{avg}']
            if avg_gubun == 2:
                cf1, cf2 = dgree['future']['tick'] if is_tick else dgree['future']['min']
                df['등락율각도'] = np.round(np.arctan2(df2['등락율차이'] * cf1, avg) / (2 * np.pi) * 360, 2)
                df['당일거래대금각도'] = np.round(np.arctan2(df2['당일거래대금차이'] * cf2, avg) / (2 * np.pi) * 360, 2)
            else:
                cf1, cf2 = dgree['coin']['tick'] if is_tick else dgree['coin']['min']
                df['등락율각도'] = np.round(np.arctan2(df2['등락율차이'] * cf1, avg) / (2 * np.pi) * 360, 2)
                df['당일거래대금각도'] = np.round(np.arctan2(df2['당일거래대금차이'] * cf2, avg) / (2 * np.pi) * 360, 2)
    return df


def GetBuyStg(buytxt, gubun):
    buytxt  = buytxt.split('if 매수:')[0] + 'if 매수:\n    self.Buy(vturn, vkey)'
    buystg  = ''
    indistg = ''
    for line in buytxt.split('\n'):
        if 'self.indicator' in line:
            indistg += f'{line}\n'
        else:
            buystg += f'{line}\n'
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
    sellstg = 'sell_cond = 0\n' + sellstg.split('if 매도:')[0] + 'if 매도:\n    self.Sell(vturn, vkey, sell_cond)'
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
                '):\n    매수 = False\nif 매수:\n    self.Buy(vturn, vkey)'
    try:
        buy_conds = compile(buy_conds, '<string>', 'exec')
    except:
        buy_conds = None
        if gubun == 0: print_exc()
    return buy_conds


def GetSellConds(sell_conds, gubun):
    sell_conds = 'sell_cond = 0\nif not (' + \
                 '):\n    매도 = True\nelif not ('.join(sell_conds) + \
                 '):\n    매도 = True\nif 매도:\n    self.Sell(vturn, vkey, sell_cond)'
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
        if '#' not in text and ('매도 = True' in text or '매도= True' in text or '매도 =True' in text or '매도=True' in text):
            dict_cond[count] = selllist[i - 1]
            sellstg = f"{sellstg}{text.split('매도')[0]}sell_cond = {count}\n"
            count += 1
        if text:
            sellstg = f"{sellstg}{text}\n"
    return sellstg, dict_cond


def GetBuyStgFuture(buystg, gubun):
    buytxt  = buystg.split('if BUY_LONG or SELL_SHORT:')[
                 0] + 'if BUY_LONG:\n    self.Buy(vturn, vkey, "LONG")\nelif SELL_SHORT:\n    self.Buy(vturn, vkey, "SHORT")'
    buystg  = ''
    indistg = ''
    for line in buytxt.split('\n'):
        if 'self.indicator' in line:
            indistg += f'{line}\n'
        else:
            buystg += f'{line}\n'
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
    sellstg = 'sell_cond = 0\n' + sellstg.split("if (포지션 == 'LONG' and SELL_LONG) or (포지션 == 'SHORT' and BUY_SHORT):")[
        0] + "if 포지션 == 'LONG' and SELL_LONG:\n    self.Sell(vturn, vkey, sell_cond, 'LONG')\nelif 포지션 == 'SHORT' and BUY_SHORT:\n    self.Sell(vturn, vkey, sell_cond, 'SHORT')"
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
                    '):\n    BUY_LONG = False\nif BUY_LONG:\n    self.Buy(vturn, vkey, "LONG")'
    else:
        buy_conds = 'if not (' + \
                    '):\n    SELL_SHORT = False\nelif not ('.join(buy_conds) + \
                    '):\n    SELL_SHORT = False\nif SELL_SHORT:\n    self.Buy(vturn, vkey, "SHORT")'
    try:
        buy_conds = compile(buy_conds, '<string>', 'exec')
    except:
        buy_conds = None
        if gubun == 0: print_exc()
    return buy_conds


def GetSellCondsFuture(is_long, sell_conds, gubun):
    if is_long:
        sell_conds = 'sell_cond = 0\nif ' + ':\n    SELL_LONG = True\nelif '.join(
            sell_conds) + ':\n    SELL_LONG = True\nif SELL_LONG:\n    self.Sell(vturn, vkey, sell_cond, "LONG")'
    else:
        sell_conds = 'sell_cond = 0\nif ' + ':\n    BUY_SHORT = True\nelif '.join(
            sell_conds) + ':\n    BUY_SHORT = True\nif BUY_SHORT:\n    self.Sell(vturn, vkey, sell_cond, "SHORT")'
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
                sellstg = f"{sellstg}{text.split('SELL_LONG')[0]}sell_cond = {count}\n"
                count += 1
            elif 'BUY_SHORT = True' in text or 'BUY_SHORT= True' in text or 'BUY_SHORT =True' in text or 'BUY_SHORT=True' in text:
                dict_cond[count] = selllist[i - 1]
                sellstg = f"{sellstg}{text.split('BUY_SHORT')[0]}sell_cond = {count}\n"
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
        divide = True if optistd in ('TG', 'G2M') else False
        std = GetOptiValidStd(train_stds, valid_stds, divide, exponential)
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
def GetOptiValidStd(train_stds, valid_stds, divide, exponential):
    """
    가중치(exs) 예제
    10개 : 2.00, 1.80, 1.60, 1.40, 1.20, 1.00, 0.80, 0.60, 0.40, 0.20
    8개  : 2.00, 1.75, 1.50, 1.25, 1.00, 0.75, 0.50, 0.25
    7개  : 2.00, 1.71, 1.42, 1.14, 0.86, 0.57, 0.29
    6개  : 2.00, 1.66, 1.33, 1.00, 0.66, 0.33
    5개  : 2.00, 1.60, 1.20, 0.80, 0.40
    4개  : 2.00, 1.50, 1.00, 0.50
    3개  : 2.00, 1.33, 0.66
    2개  : 2.00, 1.0
    """
    merge = 0.
    count = len(train_stds)
    for i in range(count):
        sign = -1. if train_stds[i] < 0 and valid_stds[i] < 0 else 1.
        ostd = sign * train_stds[i] * valid_stds[i]
        if exponential and count > 1:
            ostd *= (count - i) * 2 / count
        merge += ostd
    merge = round(merge / count / 1000, 2) if divide else round(merge / count, 2)
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
            'PM':   lambda: round(tpp / mdd, 2),
            'P2M':  lambda: sign * abs(round(tpp * tpp / mdd, 2)),
            'PAM':  lambda: sign * abs(round(tpp * app / mdd, 2)),
            'PWM':  lambda: round(tpp * wr / mdd / 100, 2),
            'TG':   lambda: round(tsg / 1000, 2),
            'GM':   lambda: round(tsg / mdd_, 2),
            'G2M':  lambda: sign * abs(round(tsg * tsg / mdd_ / 1000, 2)),
            'GAM':  lambda: sign * abs(round(tsg * app / mdd_, 2)),
            'GWM':  lambda: round(tsg * wr / mdd_ / 100, 2),
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


def PlotShow(gubun, teleQ, df_tsg, df_bct, dict_cn, seed, mdd, startday, endday, starttime, endtime, list_days,
             backname, back_text, label_text, save_file_name, schedul, plotgraph, buy_vars=None, sell_vars=None):
    df_tsg['수익금합계020'] = df_tsg['수익금합계'].rolling(window=20).mean().round(2)
    df_tsg['수익금합계060'] = df_tsg['수익금합계'].rolling(window=60).mean().round(2)
    df_tsg['수익금합계120'] = df_tsg['수익금합계'].rolling(window=120).mean().round(2)
    df_tsg['수익금합계240'] = df_tsg['수익금합계'].rolling(window=240).mean().round(2)
    df_tsg['수익금합계480'] = df_tsg['수익금합계'].rolling(window=480).mean().round(2)

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
            mdd_ = round(abs(random_cumsum[upper] - random_cumsum[lower]) / (random_cumsum[upper] + seed) * 100, 2)
        except:
            mdd_ = 0.
        mdd_list.append(mdd_)

    is_min = len(str(endtime)) < 5
    df_sg = df_tsg[['수익금']].copy()
    df_sg.index = df_sg.index.map(lambda x: dt_ymdhms(x) if not is_min else dt_ymdhm(x))

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
    df_st.index = df_st.index.map(lambda x: dt_hms(x[8:]) if not is_min else dt_hm(x[8:]))
    if not is_min:
        start_time = dt_hms(str(starttime).zfill(6))
        end_time = dt_hms(str(endtime).zfill(6))
    else:
        start_time = dt_hm(str(starttime).zfill(4))
        end_time = dt_hm(str(endtime).zfill(4))
    total_sec = (end_time - start_time).total_seconds()
    interval = f'{total_sec / 600}min' if total_sec >= 1800 else '3min'
    df_st = df_st.resample(interval).sum()
    df_st.index = df_st.index.map(lambda x: str_hms(x) if not is_min else str_hm(x))
    if not is_min:
        df_st.index = df_st.index.map(lambda x: f'{x[:2]}:{x[2:4]}:{x[4:]}')
    else:
        df_st.index = df_st.index.map(lambda x: f'{x[:2]}:{x[2:]}')
    df_st['이익금액'] = df_st['수익금'].apply(lambda x: x if x >= 0 else 0)
    df_st['손실금액'] = df_st['수익금'].apply(lambda x: x if x < 0 else 0)

    df_wt = df_tsg[['수익금']].copy()
    df_wt['요일'] = df_wt.index
    df_wt['요일'] = df_wt['요일'].apply(lambda x: dt_ymdhms(x).weekday() if not is_min else dt_ymdhm(x).weekday())
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

    if not is_min:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    else:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:]}')

    endx_list = None
    if gubun == '최적화':
        if not is_min:
            endx_list = [df_tsg[df_tsg['매도시간'] < list_days[2][0] * 1000000 + 240000].index[-1]]
        else:
            endx_list = [df_tsg[df_tsg['매도시간'] < list_days[2][0] * 10000 + 2400].index[-1]]
        if list_days[1] is not None:
            for vsday, _, _ in list_days[1]:
                if not is_min:
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
    avg_mdd = round(sum(mdd_list) / len(mdd_list), 2)
    plt.title(f'Max MDD [{max_mdd}%] | Min MDD [{min_mdd}%] | Avg MDD [{avg_mdd}%]')
    count = int(len(df_tsg) / 15) if int(len(df_tsg) / 15) >= 1 else 1
    plt.xticks(list(df_tsg.index[::count]), rotation=45)
    plt.grid()
    # noinspection PyTypeChecker
    plt.subplot(gs[1])
    plt.plot(df_ts.index, df_ts['수익금합계'], linewidth=2, label='수익률', color='orange')
    if df_kp is not None:
        plt.plot(df_kp.index, df_kp['종가'], linewidth=0.5, label='코스피', color='r')
        plt.plot(df_kd.index, df_kd['종가'], linewidth=0.5, label='코스닥', color='b')
    elif df_nd is not None:
        plt.plot(df_nd.index, df_nd['종가'], linewidth=0.5, label='NQ', color='r')
    elif df_bc is not None:
        plt.plot(df_bc.index, df_bc['종가'], linewidth=0.5, label='KRW-BTC', color='r')
    plt.title('지수비교' if df_bc is None else 'BTC비교')
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
    plt.legend(loc='upper left')
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
        mdd   = round(abs(array[upper] - array[lower]) / (array[upper] + result[10]) * 100, 2)
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

    exclud_top10per = int(len(arry_bct) / 100)
    try:    mhct = int(arry_bct[exclud_top10per:, 1].max())
    except: mhct = 0
    try:    seed = int(arry_bct[exclud_top10per:, 2].max())
    except: seed = betting
    if seed < betting: seed = betting

    tpp  = tsg / (seed if seed > betting else betting) * 100
    cagr = tpp / day_count * (365 if 'C' in ui_gubun else 250)
    tpi  = wr / 100 * (1 + appp / ampp) if ampp != 0 else 1.0

    return (
        tc,              # 0 거래횟수
        round(atc, 1),   # 1 일평균 거래횟수
        pc,              # 2 수익 거래횟수
        mc,              # 3 손실 거래횟수
        round(wr, 2),    # 4 승률
        round(ah, 2),    # 5 평균보유시간
        round(app, 2),   # 6 평균수익률
        round(tpp, 2),   # 7 총수익률
        int(tsg),        # 8 총수익금
        mhct,            # 9 최대 보유종목수
        seed,            # 10 필요 자금
        round(cagr, 2),  # 11 연간 예상 수익률
        round(tpi, 2)    # 12 거래 성과 지수
    )


def GetIndicator(mc, mh, ml, mv, k):
    AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, PPO, \
        ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR = \
        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    try:    AD                     = stream.AD(      mh, ml, mc, mv)
    except: AD                     = 0
    if k[0] != 0:
        try:    ADOSC              = stream.ADOSC(   mh, ml, mc, mv, fastperiod=k[0], slowperiod=k[1])
        except: ADOSC              = 0
    if k[2] != 0:
        try:    ADXR               = stream.ADXR(    mh, ml, mc,     timeperiod=k[2])
        except: ADXR               = 0
    if k[3] != 0:
        try:    APO                = stream.APO(     mc,             fastperiod=k[3], slowperiod=k[4], matype=k[5])
        except: APO                = 0
    if k[6] != 0:
        try:    AROOND, AROONU     = stream.AROON(   mh, ml,         timeperiod=k[6])
        except: AROOND, AROONU     = 0, 0
    if k[7] != 0:
        try:    ATR                = stream.ATR(     mh, ml, mc,     timeperiod=k[7])
        except: ATR                = 0
    if k[8] != 0:
        try:    BBU, BBM, BBL      = stream.BBANDS(  mc,             timeperiod=k[8], nbdevup=k[9], nbdevdn=k[10], matype=k[11])
        except: BBU, BBM, BBL      = 0, 0, 0
    if k[12] != 0:
        try:    CCI                = stream.CCI(     mh, ml, mc,     timeperiod=k[12])
        except: CCI                = 0
    if k[13] != 0:
        try:    DIM, DIP           = stream.MINUS_DI(mh, ml, mc,     timeperiod=k[13]), stream.PLUS_DI( mh, ml, mc, timeperiod=k[13])
        except: DIM, DIP           = 0, 0
    if k[14] != 0:
        try:    MACD, MACDS, MACDH = stream.MACD(    mc,             fastperiod=k[14], slowperiod=k[15], signalperiod=k[16])
        except: MACD, MACDS, MACDH = 0, 0, 0
    if k[17] != 0:
        try:    MFI                = stream.MFI(     mh, ml, mc, mv, timeperiod=k[17])
        except: MFI                = 0
    if k[18] != 0:
        try:    MOM                = stream.MOM(     mc,             timeperiod=k[18])
        except: MOM                = 0
    try:    OBV                    = stream.OBV(     mc, mv)
    except: OBV                    = 0
    if k[19] != 0:
        try:    PPO                = stream.PPO(     mc,             fastperiod=k[19], slowperiod=k[20], matype=k[21])
        except: PPO                = 0
    if k[22] != 0:
        try:    ROC                = stream.ROC(     mc,             timeperiod=k[22])
        except: ROC                = 0
    if k[23] != 0:
        try:    RSI                = stream.RSI(     mc,             timeperiod=k[23])
        except: RSI                = 0
    if k[24] != 0:
        try:    SAR                = stream.SAR(     mh, ml,         acceleration=k[24], maximum=k[25])
        except: SAR                = 0
    if k[26] != 0:
        try:    STOCHSK, STOCHSD   = stream.STOCH(   mh, ml, mc,     fastk_period=k[26], slowk_period=k[27], slowk_matype=k[28], slowd_period=k[29], slowd_matype=k[30])
        except: STOCHSK, STOCHSD   = 0, 0
    if k[31] != 0:
        try:    STOCHFK, STOCHFD   = stream.STOCHF(  mh, ml, mc,     fastk_period=k[31], fastd_period=k[32], fastd_matype=k[33])
        except: STOCHFK, STOCHFD   = 0, 0
    if k[34] != 0:
        try:    WILLR              = stream.WILLR(   mh, ml, mc,     timeperiod=k[34])
        except: WILLR              = 0
    return AD, ADOSC, ADXR, APO, AROOND, AROONU, ATR, BBU, BBM, BBL, CCI, DIM, DIP, MACD, MACDS, MACDH, MFI, MOM, OBV, PPO, ROC, RSI, SAR, STOCHSK, STOCHSD, STOCHFK, STOCHFD, WILLR
