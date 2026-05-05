
import numpy as np
import pandas as pd
from traceback import format_exc
from utility.settings.setting_base import ui_num
from utility.static_method.static import thread_decorator


@thread_decorator
def RunOptunaServer():
    """Optuna 대시보드 서버를 실행합니다.
    Returns:
        None
    """
    from optuna_dashboard import run_server
    from utility.settings.setting_base import DB_OPTUNA
    try:
        run_server(DB_OPTUNA)
    except Exception:
        pass


def get_trade_info(gubun):
    """거래 정보 딕셔너리를 반환합니다.
    Args:
        gubun: 구분 (1: 기본, 2: OMS, 기타: 일일)
    Returns:
        거래 정보 딕셔너리
    """
    from utility.static_method.static import dt_ymd
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


def get_back_load_code_query(is_tick, code, days, starttime, endtime):
    """백테스트 데이터 로드 쿼리를 생성합니다.
    Args:
        is_tick: 틱 데이터 여부
        code: 종목 코드
        days: 일자 리스트
        starttime: 시작 시간
        endtime: 종료 시간
    Returns:
        SQL 쿼리 문자열
    """
    conditions = []
    for day in days:
        if is_tick:
            sindex = day * 1000000 + starttime
            eindex = day * 1000000 + endtime
        else:
            sindex = day * 10000 + int(starttime / 100)
            eindex = day * 10000 + int(endtime / 100)
        conditions.append(f"(`index` >= {sindex} AND `index` <= {eindex})")
    where_clause = " OR ".join(conditions)
    query = f"SELECT * FROM '{code}' WHERE {where_clause}"
    return query


def get_back_load_code_query_batch(is_tick, code_list, days, starttime, endtime):
    """여러 종목에 대한 배치 쿼리를 생성합니다 (UNION ALL).
    Args:
        is_tick: 틱 데이터 여부
        code_list: 종목 코드 리스트
        days: 일자 리스트
        starttime: 시작 시간
        endtime: 종료 시간
    Returns:
        배치 SQL 쿼리 문자열
    """
    conditions = []
    for day in days:
        if is_tick:
            sindex = day * 1000000 + starttime
            eindex = day * 1000000 + endtime
        else:
            sindex = day * 10000 + int(starttime / 100)
            eindex = day * 10000 + int(endtime / 100)
        conditions.append(f"(`index` >= {sindex} AND `index` <= {eindex})")
    where_clause = " OR ".join(conditions)

    subqueries = []
    for code in code_list:
        subquery = f"SELECT '{code}' as code, * FROM '{code}' WHERE {where_clause}"
        subqueries.append(subquery)

    query = " UNION ALL ".join(subqueries)
    return query


def get_moneytop_query(is_tick, startday, endday, starttime, endtime):
    """거래대금 순위 쿼리를 생성합니다.
    Args:
        is_tick: 틱 데이터 여부
        startday: 시작 일자
        endday: 종료 일자
        starttime: 시작 시간
        endtime: 종료 시간
    Returns:
        SQL 쿼리 문자열
    """
    if is_tick:
        sindex = startday * 1000000 + starttime
        eindex = endday * 1000000 + endtime
    else:
        sindex = startday * 10000 + int(starttime / 100)
        eindex = endday * 10000 + int(endtime / 100)
    query = f"SELECT * FROM moneytop WHERE `index` >= {sindex} AND `index` <= {eindex}"
    return query


def get_buy_stg(buytxt, gubun, wq):
    """매수 전략을 컴파일합니다.
    Args:
        buytxt: 매수 전략 텍스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (매수 전략, 지표 전략) 튜플
    """
    lines   = [line for line in buytxt.split('\n') if line and line[0] != '#']
    buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
    indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
    if buystg:
        try:
            buystg = compile(buystg, '<string>', 'exec')
        except Exception:
            buystg = None
            if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_buy_stg'))
    else:
        buystg = None
    if indistg:
        try:
            indistg = compile(indistg, '<string>', 'exec')
        except Exception:
            indistg = None
    else:
        indistg = None
    return buystg, indistg


def get_sell_stg(sellstg, gubun, wq):
    """매도 전략을 컴파일합니다.
    Args:
        sellstg: 매도 전략 텍스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (매도 전략, 매도조건 딕셔너리) 튜플
    """
    sellstg = 'self.sell_cond = 0\n' + sellstg
    sellstg, dict_cond = set_sell_cond(sellstg.split('\n'))
    try:
        sellstg = compile(sellstg, '<string>', 'exec')
    except Exception:
        sellstg = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_sell_stg'))
    return sellstg, dict_cond


def get_buy_conds(buy_conds, gubun, wq):
    """매수 조건을 컴파일합니다.
    Args:
        buy_conds: 매수 조건 리스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        컴파일된 매수 조건
    """
    buy_conds = 'if not (' + \
                '):\n    매수 = False\nelif not ('.join(buy_conds) + \
                '):\n    매수 = False\nif 매수:\n    self.Buy()'
    try:
        buy_conds = compile(buy_conds, '<string>', 'exec')
    except Exception:
        buy_conds = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_buy_conds'))
    return buy_conds


def get_sell_conds(sell_conds, gubun, wq):
    """매도 조건을 컴파일합니다.
    Args:
        sell_conds: 매도 조건 리스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (컴파일된 매도 조건, 매도조건 딕셔너리) 튜플
    """
    sell_conds = 'self.sell_cond = 0\nif not (' + \
                 '):\n    매도 = True\nelif not ('.join(sell_conds) + \
                 '):\n    매도 = True\nif 매도:\n    self.Sell()'
    sell_conds, dict_cond = set_sell_cond(sell_conds.split('\n'))
    try:
        sell_conds = compile(sell_conds, '<string>', 'exec')
    except Exception:
        sell_conds = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_sell_conds'))
    return sell_conds, dict_cond


def set_sell_cond(selllist):
    """매도 조건을 설정합니다.
    Args:
        selllist: 매도 전략 라인 리스트
    Returns:
        (처리된 매도 전략, 매도조건 딕셔너리) 튜플
    """
    count = 1
    sellstg = ''
    dict_cond = {0: '전략종료청산', 1000: '분할매도', 1001: '익절청산', 1002: '손절청산'}
    for i, text in enumerate(selllist):
        if text and text[0] != '#' and ('매도 = True' in text or '매도= True' in text or '매도 =True' in text or '매도=True' in text):
            dict_cond[count] = selllist[i - 1]
            sellstg = f"{sellstg}{text.split('매도')[0]}self.sell_cond = {count}\n"
            count += 1
        if text:
            sellstg = f"{sellstg}{text}\n"
    return sellstg, dict_cond


def get_buy_stg_future(buystg, gubun, wq):
    """선물 매수 전략을 컴파일합니다.
    Args:
        buystg: 매수 전략 텍스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (매수 전략, 지표 전략) 튜플
    """
    lines   = [line for line in buystg.split('\n') if line and line[0] != '#']
    buystg  = '\n'.join(line for line in lines if 'self.indicator' not in line)
    indistg = '\n'.join(line for line in lines if 'self.indicator' in line)
    if buystg:
        try:
            buystg = compile(buystg, '<string>', 'exec')
        except Exception:
            buystg = None
            if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_buy_stg_future'))
    else:
        buystg = None
    if indistg:
        try:
            indistg = compile(indistg, '<string>', 'exec')
        except Exception:
            indistg = None
    else:
        indistg = None
    return buystg, indistg


def get_sell_stg_future(sellstg, gubun, wq):
    """선물 매도 전략을 컴파일합니다.
    Args:
        sellstg: 매도 전략 텍스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (매도 전략, 매도조건 딕셔너리) 튜플
    """
    sellstg = 'self.sell_cond = 0\n' + sellstg
    sellstg, dict_cond = set_sell_cond_future(sellstg.split('\n'))
    try:
        sellstg = compile(sellstg, '<string>', 'exec')
    except Exception:
        sellstg = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_sell_stg_future'))
    return sellstg, dict_cond


def get_buy_conds_future(is_long, buy_conds, gubun, wq):
    """선물 매수 조건을 컴파일합니다.
    Args:
        is_long: 롱 포지션 여부
        buy_conds: 매수 조건 리스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        컴파일된 매수 조건
    """
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
    except Exception:
        buy_conds = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_buy_conds_future'))
    return buy_conds


def get_sell_conds_future(is_long, sell_conds, gubun, wq):
    """선물 매도 조건을 컴파일합니다.
    Args:
        is_long: 롱 포지션 여부
        sell_conds: 매도 조건 리스트
        gubun: 구분
        wq: 윈도우 큐
    Returns:
        (컴파일된 매도 조건, 매도조건 딕셔너리) 튜플
    """
    if is_long:
        sell_conds = 'self.sell_cond = 0\nif ' + ':\n    SELL_LONG = True\nelif '.join(
            sell_conds) + ':\n    SELL_LONG = True\nif SELL_LONG:\n    self.Sell(SELL_LONG)'
    else:
        sell_conds = 'self.sell_cond = 0\nif ' + ':\n    BUY_SHORT = True\nelif '.join(
            sell_conds) + ':\n    BUY_SHORT = True\nif BUY_SHORT:\n    self.Sell(SELL_LONG)'
    sell_conds, dict_cond = set_sell_cond_future(sell_conds.split('\n'))
    try:
        sell_conds = compile(sell_conds, '<string>', 'exec')
    except Exception:
        sell_conds = None
        if gubun == 0: wq.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - get_sell_conds_future'))
    return sell_conds, dict_cond


def set_sell_cond_future(selllist):
    """선물 매도 조건을 설정합니다.
    Args:
        selllist: 매도 전략 라인 리스트
    Returns:
        (처리된 매도 전략, 매도조건 딕셔너리) 튜플
    """
    count = 1
    sellstg = ''
    dict_cond = {0: '전략종료청산', 1000: '분할매도', 1001: '익절청산', 1002: '손절청산'}
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


def send_result(result, dict_train, dict_valid=None, exponential=False):
    """백테스트 결과를 전송합니다.
    Args:
        result: 결과 데이터 튜플
        dict_train: 학습 데이터 딕셔너리
        dict_valid: 검증 데이터 딕셔너리
        exponential: 지수 가중치 적용 여부
    Returns:
        업데이트된 기준값
    """
    gubun, wq, mq, pre_hstd, optistd, opti_kind, vturn, vkey, vars_list, _, _, std_list, _ = result
    if gubun in ('최적화', '최적화테스트'):
        if opti_kind == 1:
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
            text3, std = get_text3(f'TRAIN{k + 1}', optistd, std_list, v)
            train_text.append(text3)
            train_stds.append(std)
        for k, v in tuple_valid:
            text3, std = get_text3(f'VALID{k + 1}', optistd, std_list, v)
            valid_text.append(text3)
            valid_stds.append(std)

        from backtest.back_static_numba import get_opti_valid_std
        train_stds = np.array(train_stds, dtype=np.float64)
        valid_stds = np.array(valid_stds, dtype=np.float64)
        std = get_opti_valid_std(train_stds, valid_stds, exponential)
        text2, hstd, sendtext = get_text2(std, pre_hstd)

        if sendtext or opti_kind in (0, 4):
            wq.put((ui_num['백테스트'], f'{text1}{text2}'))
            for text3 in train_text:
                wq.put((ui_num['백테스트'], text3))
            for text3 in valid_text:
                wq.put((ui_num['백테스트'], text3))

    elif dict_train is not None:
        if gubun == '최적화테스트':
            text3, std  = get_text3('TEST', optistd, std_list, dict_train)
            text2, hstd, sendtext = '', pre_hstd, False
        else:
            text3, std  = get_text3('TOTAL', optistd, std_list, dict_train)
            text2, hstd, sendtext = get_text2(std, pre_hstd)

        if sendtext or opti_kind in (2, 4):
            wq.put((ui_num['백테스트'], f'{text1}{text2}'))
            wq.put((ui_num['백테스트'], text3))

    else:
        hstd = pre_hstd
        std  = -2_000_000_000

    if opti_kind != 2:
        mq.put((vturn, vkey, std))

    return hstd


def get_text2(std, pre_hstd):
    """결과 텍스트2를 생성합니다.
    Args:
        std: 기준값
        pre_hstd: 이전 기준값
    Returns:
        (텍스트, 업데이트된 기준값, 전송여부) 튜플
    """
    text = f'<font color=#ffffa0> MERGE[{std:,.2f}]</font>'
    if std > pre_hstd:
        text = f'{text}<font color=#54d2f9> [기준값갱신]</font>'
        return text, std, True
    elif std == pre_hstd:
        text = f'{text}<font color=white> [기준값동일]</font>'
        return text, std, False
    else:
        return text, pre_hstd, False


def get_text3(gubun, optistd, std_list, result):
    """결과 텍스트3를 생성합니다.
    Args:
        gubun: 구분
        optistd: 최적화 기준
        std_list: 기준값 리스트
        result: 결과 데이터 튜플
    Returns:
        (텍스트, 기준값) 튜플
    """
    tc, atc, pc, mc, wr, ah, app, tpp, tsg, mhct, seed, cagr, tpi, mdd, mdd_ = result
    if tpp < 0 < tsg: tsg = -float('inf')
    mddt  = f'{mdd_:,.0f}' if 'G' in optistd and optistd != 'CAGR' else f'{mdd:,.2f}%'
    color = '#ffa3d7' if 'TRAIN' not in gubun else '#a1afff'
    text  = f"<font color={color}>{gubun}</font>"
    text  = f"{text} <font color={color if tsg >= 0 else '#96969b'}>TC[{tc:,.0f}] ATC[{atc:,.1f}] MH[{mhct}] " \
            f"WR[{wr:,.2f}%] AP[{app:,.2f}%] TP[{tpp:,.2f}%] TG[{tsg:,.0f}] MDD[{mddt}] TPI[{tpi:,.2f}] CAGR[{cagr:,.2f}]"
    text, std = get_optistd_text(optistd, std_list, result, text)
    return text, std


def get_optistd_text(optistd, std_list, result, pre_text):
    """최적화 기준 텍스트를 생성합니다.
    Args:
        optistd: 최적화 기준
        std_list: 기준값 리스트
        result: 결과 데이터 튜플
        pre_text: 이전 텍스트
    Returns:
        (텍스트, 기준값) 튜플
    """
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


def get_yf_ticker(code, startday, endday):
    """Yahoo Finance에서 티커 데이터를 가져옵니다.
    Args:
        code: 종목 코드
        startday: 시작 일자
        endday: 종료 일자
    Returns:
        주가 데이터프레임
    """
    import yfinance as yf
    start_str  = str(startday)
    end_str    = str(endday)
    start_date = f'{start_str[:4]}-{start_str[4:6]}-{start_str[6:8]}'
    end_date   = f'{end_str[:4]}-{end_str[4:6]}-{end_str[6:8]}'
    df = yf.Ticker(code).history(start=start_date, end=end_date, interval="1d")
    df['종가'] = (df['Close'] / df['Close'].iloc[0] - 1) * 100
    return df


def get_interval(total_sec):
    """시간 간격을 반환합니다.
    Args:
        total_sec: 총 초수
    Returns:
        시간 간격 문자열
    """
    if total_sec <= 1800:
        return '3min'
    elif total_sec <= 3600:
        return '5min'
    elif total_sec <= 7200:
        return '10min'
    elif total_sec <= 10800:
        return '15min'
    return '30min'


def plot_show(gubun, is_tick, teleQ, df_tsg, df_bct, market_gubun, seed, mdd, startday, endday, starttime, endtime,
              list_days, backname, back_text, label_text, save_file_name, schedul, notplotshow,
              buy_vars=None, sell_vars=None):
    """백테스트 결과를 시각화합니다.
    Args:
        gubun: 구분
        is_tick: 틱 데이터 여부
        teleQ: 텔레그램 큐
        df_tsg: 거래 결과 데이터프레임
        df_bct: 보유 결과 데이터프레임
        market_gubun: 마켓 구분
        seed: 초기 자금
        mdd: 최대 낙폭
        startday: 시작 일자
        endday: 종료 일자
        starttime: 시작 시간
        endtime: 종료 시간
        list_days: 일자 리스트
        backname: 백테스트 이름
        back_text: 백테스트 텍스트
        label_text: 라벨 텍스트
        save_file_name: 저장 파일명
        schedul: 스케줄 여부
        notplotshow: 플롯 표시 여부
        buy_vars: 매수 변수
        sell_vars: 매도 변수
    """
    from utility.settings.setting_base import GRAPH_PATH
    from matplotlib import pyplot as plt, font_manager, gridspec
    from utility.static_method.static import dt_hms, dt_hm, dt_ymd, dt_ymdhms, dt_ymdhm, str_ymd_ios, str_ymdhms_ios

    plt.rcParams['figure.max_open_warning'] = 0
    plt.rcParams['font.family'] = font_manager.FontProperties(fname='C:/Windows/Fonts/malgun.ttf').get_name()
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['path.simplify'] = True
    plt.rcParams['path.snap'] = True
    plt.rcParams['figure.autolayout'] = True
    plt.rcParams['figure.constrained_layout.use'] = True

    df_kp, df_kd, df_nd, df_kpf, df_ndf, df_bc = None, None, None, None, None, None
    if startday != endday:
        try:
            if market_gubun < 4:
                df_kp = get_yf_ticker('^KS11', startday, endday)
                df_kd = get_yf_ticker('^KQ11', startday, endday)
            elif market_gubun == 4:
                df_nd = get_yf_ticker('^IXIC', startday, endday)
            elif market_gubun in (6, 7):
                df_kpf = get_yf_ticker('^KS200', startday, endday)
            elif market_gubun == 8:
                df_ndf = get_yf_ticker('QQQ', startday, endday)
            else:
                df_bc = get_yf_ticker('BTC-USD', startday, endday)
        except Exception:
            pass

    profit_series = df_tsg['수익금합계']
    windows = [20, 60, 120, 240, 480]
    for window in windows:
        df_tsg[f'수익금합계{window:03d}'] = profit_series.rolling(window=window).mean()

    df_tsg['이익금액'] = df_tsg['수익금'].clip(lower=0)
    df_tsg['손실금액'] = df_tsg['수익금'].clip(upper=0)

    from backtest.back_static_numba import calculate_mdd_bootstrap
    sig_array = df_tsg['수익금'].values
    mdd_list, random_cumsums = calculate_mdd_bootstrap(sig_array, seed)

    df_ts = df_tsg[['수익금']].copy()
    df_ts.index = df_ts.index.map(lambda x: dt_ymd(x))
    df_ts = df_ts.resample('D').sum()
    df_ts['수익금합계'] = df_ts['수익금'].cumsum()
    df_ts['수익금합계'] = ((df_ts['수익금합계'] + seed) / seed - 1) * 100

    df_st = df_tsg[['수익금']].copy()
    df_st.index = df_st.index.map(lambda x: dt_hm(x[8:12]))
    start_time = dt_hms(str(starttime).zfill(6))
    end_time = dt_hms(str(endtime).zfill(6))
    total_sec = (end_time - start_time).total_seconds()
    interval = get_interval(total_sec)
    df_st = df_st.resample(interval).sum()
    df_st['이익금액'] = df_st['수익금'].clip(lower=0)
    df_st['손실금액'] = df_st['수익금'].clip(upper=0)
    df_st.index = df_st.index.map(lambda x: str_ymdhms_ios(x))

    df_wt = df_tsg[['수익금']].copy()
    df_wt['요일'] = df_wt.index.map(lambda x: dt_ymdhms(x).weekday() if is_tick else dt_ymdhm(x).weekday())
    weekday_sums = df_wt.groupby('요일')['수익금'].sum()
    wt_index = ['월', '화', '수', '목', '금']
    wt_data = [weekday_sums.get(i, 0) for i in range(5)]
    if market_gubun in (5, 9):
        wt_index += ['토', '일']
        wt_data += [weekday_sums.get(5, 0), weekday_sums.get(6, 0)]
    wt_data_array = np.array(wt_data)
    wt_datap = np.where(wt_data_array >= 0, wt_data_array, 0)
    wt_datam = np.where(wt_data_array < 0, wt_data_array, 0)

    if is_tick:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:12]}:{x[12:14]}')
    else:
        df_tsg.index = df_tsg.index.map(lambda x: f'{x[:4]}-{x[4:6]}-{x[6:8]} {x[8:10]}:{x[10:]}')

    endx_list = []
    if gubun == '최적화':
        time_unit, plus_time = (1000000, 240000) if is_tick else (10000, 2400)
        endx_list.append(df_tsg[df_tsg['매도시간'] < list_days[2][0] * time_unit + plus_time].index[-1])
        if list_days[1] is not None:
            for vsday, _, _ in list_days[1]:
                df_tsg_ = df_tsg[df_tsg['매도시간'] < vsday * time_unit]
                if not df_tsg_.empty:
                    endx_list.append(df_tsg_.index[-1])

    if schedul or notplotshow:
        plt.switch_backend('agg')

    fig1 = plt.figure(f'{backname} 부가정보', figsize=(12, 10), dpi=100)
    gs = gridspec.GridSpec(nrows=2, ncols=2, height_ratios=[1, 1])
    ax1 = fig1.add_subplot(gs[0, 0])
    ax2 = fig1.add_subplot(gs[0, 1])
    ax3 = fig1.add_subplot(gs[1, 0])
    ax4 = fig1.add_subplot(gs[1, 1])

    ax1.plot(df_tsg.index, random_cumsums.T, linewidth=0.5, alpha=0.7)
    ax1.plot(df_tsg.index, df_tsg['수익금합계'], linewidth=2, label=f'MDD {mdd}%', color='orange')
    max_mdd = max(mdd_list)
    min_mdd = min(mdd_list)
    # noinspection PyUnresolvedReferences
    avg_mdd = round(sum(mdd_list) / len(mdd_list), 2)
    ax1.set_title(f'Max MDD [{max_mdd}%] | Min MDD [{min_mdd}%] | Avg MDD [{avg_mdd}%]')
    step = max(1, len(df_tsg) // 15)
    xticks = df_tsg.index[::step]
    xticklabels = [str(x)[:10] for x in xticks]
    ax1.set_xticks(xticks)
    ax1.set_xticklabels(xticklabels, rotation=45)
    ax1.grid(True, alpha=0.3)

    ax2.plot(df_ts.index, df_ts['수익금합계'], linewidth=2, label='수익률', color='orange')
    if df_kp is not None and df_kd is not None:
        ax2.plot(df_kp.index, df_kp['종가'], linewidth=0.5, label='코스피', color='r')
        ax2.plot(df_kd.index, df_kd['종가'], linewidth=0.5, label='코스닥', color='b')
    elif df_nd is not None:
        ax2.plot(df_nd.index, df_nd['종가'], linewidth=0.5, label='나스닥', color='r')
    elif df_kpf is not None:
        ax2.plot(df_kpf.index, df_kpf['종가'], linewidth=0.5, label='코스피200', color='r')
    elif df_ndf is not None:
        ax2.plot(df_ndf.index, df_ndf['종가'], linewidth=0.5, label='나스닥선물', color='r')
    elif df_bc is not None:
        ax2.plot(df_bc.index, df_bc['종가'], linewidth=0.5, label='비트코인', color='r')
    ax2.set_title('지수비교')
    step = max(1, len(df_ts) // 15)
    xticks = df_ts.index[::step]
    xticklabels = [str_ymd_ios(x) for x in xticks]
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xticklabels, rotation=45)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    ax3.bar(df_st.index, df_st['이익금액'], label='이익금액', color='r')
    ax3.bar(df_st.index, df_st['손실금액'], label='손실금액', color='b')
    ax3.set_title('시간별 수익금')
    xticks = df_st.index
    xticklabels = [x[11:16] for x in xticks]
    ax3.set_xticks(xticks)
    ax3.set_xticklabels(xticklabels, rotation=45)
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    ax4.bar(wt_index, wt_datap, label='이익금액', color='r')
    ax4.bar(wt_index, wt_datam, label='손실금액', color='b')
    ax4.set_title('요일별 수익금')
    ax4.set_xticks(wt_index)
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3)

    fig2 = plt.figure(f'{backname} 결과', figsize=(12, 12 if buy_vars else 10), dpi=100)
    gs = gridspec.GridSpec(nrows=2, ncols=1, height_ratios=[1, 4])
    ax1 = fig2.add_subplot(gs[0, 0])
    ax2 = fig2.add_subplot(gs[1, 0])

    ax1.plot(df_bct.index, df_bct['보유금액'], label='보유금액', color='g')
    ax1.set_xticks([])
    if buy_vars is None:
        ax1.set_xlabel('\n' + back_text + '\n' + label_text)
    else:
        ax1.set_xlabel('\n' + back_text + '\n' + label_text + '\n\n' + buy_vars + '\n\n' + sell_vars)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    ax2.bar(df_tsg.index, df_tsg['이익금액'], label='이익금액', color='r')
    ax2.bar(df_tsg.index, df_tsg['손실금액'], label='손실금액', color='b')
    ax2.plot(df_tsg.index, df_tsg['수익금합계480'], linewidth=0.5, label='수익금합계480', color='k')
    ax2.plot(df_tsg.index, df_tsg['수익금합계240'], linewidth=0.5, label='수익금합계240', color='gray')
    ax2.plot(df_tsg.index, df_tsg['수익금합계120'], linewidth=0.5, label='수익금합계120', color='b')
    ax2.plot(df_tsg.index, df_tsg['수익금합계060'], linewidth=0.5, label='수익금합계60', color='g')
    ax2.plot(df_tsg.index, df_tsg['수익금합계020'], linewidth=0.5, label='수익금합계20', color='r')
    ax2.plot(df_tsg.index, df_tsg['수익금합계'], linewidth=2, label='수익금합계', color='orange')

    if gubun == '최적화':
        for i, endx in enumerate(endx_list):
            ax2.axvline(x=endx, color='red' if i == 0 else 'green', linestyle='--')
        ax2.axvspan(endx_list[0], df_tsg.index[-1], facecolor='gray', alpha=0.1)

    step = max(1, len(df_tsg) // 20)
    xticks = df_tsg.index[::step]
    xticklabels = [str(x)[:10] for x in xticks]
    ax2.set_xticks(xticks)
    ax2.set_xticklabels(xticklabels, rotation=45)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    if not schedul and not notplotshow:
        plt.tight_layout()
        plt.show()

    fig1.savefig(f"{GRAPH_PATH}/{save_file_name}_.png", dpi=100, bbox_inches='tight')
    fig2.savefig(f"{GRAPH_PATH}/{save_file_name}.png", dpi=100, bbox_inches='tight')

    teleQ.put(f'{backname} {save_file_name.split("_")[1]} 완료.')
    teleQ.put(f"{GRAPH_PATH}/{save_file_name}_.png")
    teleQ.put(f"{GRAPH_PATH}/{save_file_name}.png")


def get_result_dataframe(market_gubun, list_tsg, arry_bct):
    """결과 데이터프레임을 생성합니다.
    Args:
        market_gubun: 마켓 구분
        list_tsg: 거래 결과 리스트
        arry_bct: 보유 결과 배열
    Returns:
        (거래 데이터프레임, 보유 데이터프레임) 튜플
    """
    columns1 = [
        'index', '종목명', '포지션' if market_gubun > 5 else '시가총액', '매수시간', '매도시간',
        '보유시간', '매수가', '매도가', '매수금액', '매도금액', '수익률', '수익금', '매도조건', '추가매수시간'
    ]
    columns2 = [
        '종목명', '포지션' if market_gubun > 5 else '시가총액', '매수시간', '매도시간',
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


def add_mdd(arry_tsg, result):
    """MDD를 계산하여 결과에 추가합니다.
    Args:
        arry_tsg: 거래 결과 배열 (보유시간, 매도시간, 수익률, 수익금, 수익금합계)
        result: 결과 데이터 튜플
    Returns:
        MDD가 추가된 결과 튜플
    """
    try:
        array = arry_tsg[:, 4]
        lower = np.argmax(np.maximum.accumulate(array) - array)
        upper = np.argmax(array[:lower])
        mdd   = round(abs(array[upper] - array[lower]) / (array[upper] + result[10]) * 100, 2)
        mdd_  = int(abs(array[upper] - array[lower]))
    except Exception:
        mdd   = abs(result[7])
        mdd_  = abs(result[8])
    result = result + (mdd, mdd_)
    return result
