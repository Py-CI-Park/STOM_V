
import numpy as np
from numba import njit


@njit(cache=True)
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
    merge = round(merge / count, 2)
    return merge if merge != 0 else -float('inf')


@njit(cache=True)
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


@njit(cache=True)
def bootstrap_test(returns, n_bootstrap=10000):
    n = len(returns)
    bootstrap_returns = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        bootstrap_sample = np.random.choice(returns, size=n, replace=True)
        # noinspection PyTypeChecker
        total_return = np.prod(1 + bootstrap_sample) - 1
        bootstrap_returns[i] = total_return
    return bootstrap_returns
