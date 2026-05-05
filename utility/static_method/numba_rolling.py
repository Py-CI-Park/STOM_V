
import numpy as np
from numba import njit, prange


@njit(cache=True, fastmath=True, parallel=True)
def numba_rolling_data_tick(input_array, ema_windows, avg_windows, angle_cf1, angle_cf2, round_unit, index_arry):
    """
    틱 데이터용 배열 기반 롤링 데이터 계산
    """
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
    """
    분봉 데이터용 배열 기반 롤링 데이터 계산
    """
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
