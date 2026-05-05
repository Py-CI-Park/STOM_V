
import numpy as np
from numba import njit, prange


@njit(cache=True, fastmath=True)
def get_profit_stock(bg, cg, etfn=False):
    """주식 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        etfn: etf, etn
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00015 if not etfn else 0.00005
    texs = int(cg * 0.0018)
    bfee = int(bg * fee / 10) * 10
    sfee = int(cg * fee / 10) * 10
    pg = int(cg - texs - bfee - sfee + 0.5)
    sg = int(pg - bg + 0.5)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_stock_os(bg, cg):
    """해외 주식 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    texs = int(cg * 0.000008)
    bfee = int(bg * 0.00065 / 10) * 10
    sfee = int(cg * 0.00065 / 10) * 10
    pg = int(cg - texs - bfee - sfee + 0.5)
    sg = int(pg - bg + 0.5)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_future_long(bg, cg):
    """선물 롱 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00002
    pg = round(cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_future_short(bg, cg):
    """선물 숏 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 0.00002
    pg = round(bg + bg - cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_future_os_long(mini, bg, cg):
    """해외 선물 롱 수익을 계산합니다.
    Args:
        mini: 미니선물
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 2 if mini else 7.5
    pg = round(cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_future_os_short(mini, bg, cg):
    """해외 선물 숏 수익을 계산합니다.
    Args:
        mini: 미니선물
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    fee = 2 if mini else 7.5
    pg = round(bg + bg - cg - fee * 2, 1)
    sg = round(pg - bg, 1)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_coin(bg, cg):
    """코인 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * 0.0005
    sfee = cg * 0.0005
    pg = round(cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_coin_future_long(bg, cg, market1, market2):
    """코인 선물 롱 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        market1: 시장1
        market2: 시장2
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * (0.0004 if market1 else 0.0002)
    sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
    pg = round(cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


@njit(cache=True, fastmath=True)
def get_profit_coin_future_short(bg, cg, market1, market2):
    """코인 선물 숏 수익을 계산합니다.
    Args:
        bg: 매수 금액
        cg: 매도 금액
        market1: 시장1
        market2: 시장2
    Returns:
        (수익금, 수익금액, 수익률)
    """
    bfee = bg * (0.0004 if market1 else 0.0002)
    sfee = (cg - bfee) * (0.0004 if market2 else 0.0002)
    pg = round(bg + bg - cg - bfee - sfee, 4)
    sg = round(pg - bg, 4)
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


def add_rolling_data(df, round_unit, angle_cf_list, avg_list, is_tick, index_arry, cf1=None, cf2=None):
    """numba를 사용하여 롤링 데이터를 추가합니다.
    Args:
        df: 데이터프레임
        round_unit: 반올림 단위
        angle_cf_list: 각도 계수 리스트
        avg_list: 평균 리스트
        is_tick: 틱 데이터 여부
        index_arry: 칼럼인덱스 배열
        cf1: 각도 계수1
        cf2: 각도 계수2
    Returns:
        배열
    """
    from utility.static_method.static_etcetera import get_ema_list

    if cf1 is None:
        cf1, cf2 = angle_cf_list

    input_array = df.values
    ema_windows = get_ema_list(is_tick)

    if is_tick:
        result_array = numba_rolling_data_tick(input_array, ema_windows, avg_list, cf1, cf2, round_unit, index_arry)
    else:
        result_array = numba_rolling_data_min(input_array, ema_windows, avg_list, cf1, cf2, round_unit, index_arry)

    return np.nan_to_num(result_array)


@njit(cache=True, fastmath=True, parallel=True)
def numba_rolling_data_tick(input_array, ema_windows, avg_windows, angle_cf1, angle_cf2, round_unit, index_arry):
    """틱 데이터용 배열 기반 롤링 데이터 계산"""
    input_row_cnt     = input_array.shape[0]
    input_col_cnt     = input_array.shape[1]
    price_data        = input_array[:, index_arry[0]]
    strength_data     = input_array[:, index_arry[1]]
    rate_data         = input_array[:, index_arry[2]]
    day_amount_data   = input_array[:, index_arry[3]]
    buy_volume_data   = input_array[:, index_arry[4]]
    sell_volume_data  = input_array[:, index_arry[5]]
    trade_amount_data = input_array[:, index_arry[6]]

    ema_cnt = len(ema_windows)
    avg_cnt = len(avg_windows)
    add_cnt = ema_cnt + 12 * avg_cnt

    result_array = np.zeros((input_row_cnt, input_col_cnt + add_cnt))
    result_array[:, :input_col_cnt] = input_array

    offset = input_col_cnt

    for idx in prange(ema_cnt):
        window = ema_windows[idx]
        for i in range(window-1, input_row_cnt):
            result_array[i, offset + idx] = np.round(np.mean(price_data[i+1-window:i+1]), round_unit)

    offset += ema_cnt

    for idx in prange(avg_cnt):
        window = avg_windows[idx]

        for i in range(window-1, input_row_cnt):
            price_window = price_data[i+1-window:i+1]
            result_array[i, offset + 0] = np.max(price_window)
            result_array[i, offset + 1] = np.min(price_window)

            strength_window = strength_data[i+1-window:i+1]
            result_array[i, offset + 2] = np.round(np.mean(strength_window), 3)
            result_array[i, offset + 3] = np.max(strength_window)
            result_array[i, offset + 4] = np.min(strength_window)

            buy_window   = buy_volume_data[i+1-window:i+1]
            sell_window  = sell_volume_data[i+1-window:i+1]
            trade_window = trade_amount_data[i+1-window:i+1]
            result_array[i, offset + 5] = np.max(buy_window)
            result_array[i, offset + 6] = np.max(sell_window)
            result_array[i, offset + 7] = np.sum(buy_window)
            result_array[i, offset + 8] = np.sum(sell_window)
            result_array[i, offset + 9] = np.round(np.mean(trade_window), 0)

            rate_diff   = rate_data[i] - rate_data[i+1-window]
            amount_diff = day_amount_data[i] - day_amount_data[i+1-window]
            result_array[i, offset + 10] = np.arctan2(rate_diff * angle_cf1, window) / (2 * np.pi) * 360
            result_array[i, offset + 11] = np.arctan2(amount_diff * angle_cf2, window) / (2 * np.pi) * 360

    return result_array


@njit(cache=True, fastmath=True, parallel=True)
def numba_rolling_data_min(input_array, ema_windows, avg_windows, angle_cf1, angle_cf2, round_unit, index_arry):
    """분봉 데이터용 배열 기반 롤링 데이터 계산"""
    input_row_cnt     = input_array.shape[0]
    input_col_cnt     = input_array.shape[1]
    price_data        = input_array[:, index_arry[0]]
    strength_data     = input_array[:, index_arry[1]]
    rate_data         = input_array[:, index_arry[2]]
    day_amount_data   = input_array[:, index_arry[3]]
    buy_volume_data   = input_array[:, index_arry[4]]
    sell_volume_data  = input_array[:, index_arry[5]]
    trade_amount_data = input_array[:, index_arry[6]]
    high_data         = input_array[:, index_arry[7]]
    low_data          = input_array[:, index_arry[8]]

    ema_cnt = len(ema_windows)
    avg_cnt = len(avg_windows)
    add_cnt = ema_cnt + 14 * avg_cnt

    result_array = np.zeros((input_row_cnt, input_col_cnt + add_cnt))
    result_array[:, :input_col_cnt] = input_array

    offset = input_col_cnt

    for idx in prange(ema_cnt):
        window = ema_windows[idx]
        for i in range(window-1, input_row_cnt):
            result_array[i, offset + idx] = np.round(np.mean(price_data[i+1-window:i+1]), round_unit)

    offset += ema_cnt

    for idx in prange(avg_cnt):
        window = avg_windows[idx]

        for i in range(window-1, input_row_cnt):
            price_window = price_data[i+1-window:i+1]
            result_array[i, offset + 0] = np.max(price_window)
            result_array[i, offset + 1] = np.min(price_window)

            high_window = high_data[i+1-window:i+1]
            low_window  = low_data[i+1-window:i+1]
            result_array[i, offset + 2] = np.max(high_window)
            result_array[i, offset + 3] = np.min(low_window)

            strength_window = strength_data[i+1-window:i+1]
            result_array[i, offset + 4] = np.round(np.mean(strength_window), 3)
            result_array[i, offset + 5] = np.max(strength_window)
            result_array[i, offset + 6] = np.min(strength_window)

            buy_window   = buy_volume_data[i+1-window:i+1]
            sell_window  = sell_volume_data[i+1-window:i+1]
            trade_window = trade_amount_data[i+1-window:i+1]
            result_array[i, offset + 7]  = np.max(buy_window)
            result_array[i, offset + 8]  = np.max(sell_window)
            result_array[i, offset + 9]  = np.sum(buy_window)
            result_array[i, offset + 10] = np.sum(sell_window)
            result_array[i, offset + 11] = np.round(np.mean(trade_window), 0)

            rate_diff   = rate_data[i] - rate_data[i+1-window]
            amount_diff = day_amount_data[i] - day_amount_data[i+1-window]
            result_array[i, offset + 12] = np.arctan2(rate_diff * angle_cf1, window) / (2 * np.pi) * 360
            result_array[i, offset + 13] = np.arctan2(amount_diff * angle_cf2, window) / (2 * np.pi) * 360

    return result_array
