
from numba import jit, prange
from utility.lazy_imports import get_np

np = get_np()


@jit(nopython=True, parallel=True)
def numba_rolling_mean(data, window):
    """
    Numba로 최적화된 롤링 평균 계산
    병렬 처리로 속도 향상
    """
    n = len(data)
    result = np.empty(n)
    result[:window-1] = 0
    for i in prange(window-1, n):
        result[i] = np.mean(data[i-window+1:i+1])
    return result


@jit(nopython=True, parallel=True)
def numba_rolling_std(data, window):
    """
    Numba로 최적화된 롤링 표준편차 계산
    """
    n = len(data)
    result = np.empty(n)
    result[:window-1] = 0
    for i in prange(window-1, n):
        window_data = data[i-window+1:i+1]
        result[i] = np.std(window_data)
    return result


@jit(nopython=True, parallel=True)
def numba_rolling_max(data, window):
    """
    Numba로 최적화된 롤링 최대값 계산
    """
    n = len(data)
    result = np.empty(n)
    result[:window-1] = 0
    for i in prange(window-1, n):
        result[i] = np.max(data[i-window+1:i+1])
    return result


@jit(nopython=True, parallel=True)
def numba_rolling_min(data, window):
    """
    Numba로 최적화된 롤링 최소값 계산
    """
    n = len(data)
    result = np.empty(n)
    result[:window-1] = 0
    for i in prange(window-1, n):
        result[i] = np.min(data[i-window+1:i+1])
    return result


@jit(nopython=True, parallel=True)
def numba_rolling_sum(data, window):
    """
    Numba로 최적화된 롤링 합계 계산
    """
    n = len(data)
    result = np.empty(n)
    result[:window-1] = 0
    for i in prange(window-1, n):
        result[i] = np.sum(data[i-window+1:i+1])
    return result


@jit(nopython=True, parallel=True)
def numba_multiple_rolling(data, windows):
    """
    여러 윈도우 크기에 대한 롤링 계산을 한 번에 처리
    """
    n = len(data)
    num_windows = len(windows)
    results = np.empty((num_windows, n))
    for w_idx in prange(num_windows):
        window = windows[w_idx]
        for i in range(window-1, n):
            results[w_idx, i] = np.mean(data[i-window+1:i+1])
        results[w_idx, :window-1] = 0
    return results
