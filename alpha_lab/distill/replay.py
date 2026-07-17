"""P5 청산 축 — 챔피언 매도식 재현(재현게이트) + 청산격자 반사실 시뮬레이터.

봉인 근거: docs/research/condition_research/research_runs/alpha_lab_20260705/
p5_preregistration_v1.json (sha256 84eeb95a...). 본 모듈은 두 층을 담는다.

[1] 엔진 미러 재현(재현게이트용) — backtest 엔진의 실측 의미론을 그대로 미러:
    - 수익률/최고수익률: utility.static.GetKiwoomPgSgSp 실측식(수수료·세금 int
      절사, round 2)을 재구현(kiwoom_pgsgsp) — 챔피언 원장 671행 전수 대조로
      검증(원장 매수가·매도가 → 기록 수익률 재현 0 불일치).
    - 매도식 평가는 backtest/backengine_kiwoom_tick.py Strategy() 흐름 미러:
      보유 중 매 행 GetHoldInfo(수익률·최고수익률 갱신) → 매도식 exec →
      매도=True 시 매수호가1..3 사다리 체결(_calc_fill_amount 미러,
      주식매도시장가잔량범위=3 실측), 일 마지막 행은 LastSell 전용.
    - 윈도 함수는 trade/base_strategy.py 실측: 이동평균(60)=rolling(60).mean()
      .round(3) 사전계산 컬럼(sma_list 상시), 등락율각도(30)=avg_list=[30]
      (게이트런 avgtime=30 실측 — 원장 090036 진입이 avgtime=60과 모순) 사전계산
      shift(29) 의미론, 최저현재가=구간 min, 게이트는 tick_count(일중 행수) 기준.

[2] 격자 반사실 시뮬(simulate_exit) — 봉인 exit_grid 정의 그대로:
    hard_stop → trailing(arm 3.0) → profit_cap → time_stop 평가 순서,
    발동 초 다음 관측 초 매수호가1 체결(다음 초 부재 시 그 초), force_exit
    92900(결측 시 직전 마지막 관측 초), 매도 체결 tick2 불리 강제
    (alpha_lab.dataset.labels.adverse_fill), net_rate는 비용 v1 봉인식.

tick DB 접근은 read-only URI 전용(file:...?mode=ro). print 금지 — logging.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from itertools import product
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset.labels import ADVERSE_TICKS, adverse_fill, net_rate

__all__ = [
    "CHAMPION_SELL_CONDS",
    "EXIT_GRID_AXES",
    "FORCE_EXIT_HHMMSS",
    "GATE_WINDOW",
    "connect_back_ro",
    "exit_grid_policies",
    "hoga_unit",
    "kiwoom_pgsgsp",
    "load_day_rows",
    "precompute_windows",
    "replay_champion_exit",
    "replay_path",
    "simulate_exit",
    "tick_distance",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 봉인 상수 — p5_preregistration_v1.json 실측값 그대로.
# ---------------------------------------------------------------------------
FORCE_EXIT_HHMMSS = 92900        # 격자 반사실 force_exit(번역 규약 실측).
GATE_WINDOW = (90000, 92800)     # 게이트런 엔진 창(run receipts 실측 start/end_time).
SELL_HJ_LIMIT = 3                # 주식매도시장가잔량범위(setting.db 실측).
TRAILING_ARM_PCT = 3.0           # 봉인 trailing_arm_pct 고정.

# 봉인 exit_grid 축(데카르트 곱 192) — 순서는 combo_rule 명기 순서 그대로.
EXIT_GRID_AXES: Dict[str, Tuple] = {
    "hard_stop_pct": (-5.0, -3.5, -3.0, -2.0),
    "trailing_pct": (None, 50.0, 60.0, 72.0),
    "time_stop_sec": (None, 60, 180, 300),
    "profit_cap_pct": (None, 3.0, 4.5),
}

# 챔피언 현직 매도식 절 원문 — condition passport(rr8_12_turnover_min_902_1.5.md
# sell_code_sha256 8ef01e0e...)에서 SetSellCond가 기록하는 형태(발동 절의 직전
# 조건 줄, 선행 공백 보존) 그대로. 0='전략종료청산'(LastSell).
CHAMPION_SELL_CONDS: Dict[int, str] = {
    0: "전략종료청산",
    1: "if 등락율 > 29.5:",
    2: "elif 시가대비등락율 < 0 and 수익률 <= -2.0 and 현재가 < 최저현재가(int(60), int(보유시간)):",
    3: "elif 보유시간 > 60 and 현재가 < 최저현재가(int(60), int(보유시간)):",
    4: "    if 수익률 >= 9 or 수익률 <= -5.0:",
    5: "    elif 최고수익률 > 3 and 최고수익률 * 0.6 >= 수익률:",
    6: "        if 등락율각도(30) >= 10 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.5 "
       "and (현재가 / 현재가N(1) - 1) * 100 < -0.5:",
    7: "        elif 등락율각도(30) < 10 and 등락율각도(30) >= 5 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.7 "
       "and (현재가 / 현재가N(1) - 1) * 100 < -0.7:",
    8: "        elif 등락율각도(30) < 5 and 등락율각도(30) >= 0 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.8 "
       "and (현재가 / 현재가N(1) - 1) * 100 < -0.5:",
    9: "        elif 4.5 < 최고수익률 and 현재가N(1) >= 이동평균(60, 1) and 이동평균(60) > 현재가:",
}

_TS_FORMAT = "%Y%m%d%H%M%S"

# 게이트 재현에 필요한 컬럼(list_stock_tick 실측 이름).
_NEEDED_COLUMNS = (
    "index", "현재가", "시가", "등락율", "초당매수수량", "초당매도수량",
    "시가총액", "매수총잔량", "매수호가1", "매수호가2", "매수호가3",
    "매수잔량1", "매수잔량2", "매수잔량3",
)


def connect_back_ro(db_path) -> sqlite3.Connection:
    """stock_tick_back.db read-only 연결 — file:...?mode=ro URI 강제."""
    posix = str(db_path).replace("\\", "/")
    return sqlite3.connect(f"file:{posix}?mode=ro", uri=True)


def kiwoom_pgsgsp(bg: float, cg: float) -> Tuple[int, int, float]:
    """utility.static.GetKiwoomPgSgSp 미러 — (평가금액, 수익금, 수익률).

    세금 0.18%·수수료 0.015%(10원 절사), 수익률은 round(…, 2). 원장 671행
    전수 대조로 검증된 엔진 실측식이다(재구현 사유: alpha_lab 격리 —
    trade/backtest 모듈 import 없이 동작).
    """
    texs = int(cg * 0.0018)
    bfee = int(bg * 0.00015 / 10) * 10
    sfee = int(cg * 0.00015 / 10) * 10
    pg = int(cg - texs - bfee - sfee)
    sg = int(round(pg - bg))
    sp = round(sg / bg * 100, 2)
    return pg, sg, sp


def hoga_unit(price: float, day: int) -> float:
    """일자 인지 호가단위 — utility.static.GetHogaunit 미러(kosd=False).

    2023-01-25 개편 전 코스피/코스닥 단위는 100,000원 미만 구간에서 동일하므로
    본 원장 가격대(≤ ~65,000원)에서 kosd 구분은 결과에 영향이 없다(정직 명기).
    """
    if int(day) < 20230125:
        bands = ((1000, 1), (5000, 5), (10000, 10), (50000, 50),
                 (100000, 100), (500000, 500))
    else:
        bands = ((2000, 1), (5000, 5), (20000, 10), (50000, 50),
                 (200000, 100), (500000, 500))
    for edge, unit in bands:
        if price < edge:
            return float(unit)
    return 1000.0


def tick_distance(price_a: float, price_b: float, day: int, cap: int = 10000) -> float:
    """두 가격 사이의 호가단위 거리(틱 수) — 하단에서 상단으로 단계 통과.

    격자 위 가격이면 정수 틱 수, VWAP 등 격자 밖 가격이면 잔여분을 소수 틱으로
    더한다(보수적 — 게이트 '95% ≤ 1틱' 판정에 유리하게 반올림하지 않음).
    """
    lo, hi = sorted((float(price_a), float(price_b)))
    if hi <= lo:
        return 0.0
    steps = 0.0
    cur = lo
    while cur < hi and steps < cap:
        unit = hoga_unit(cur, day)
        nxt = cur + unit
        if nxt > hi:
            steps += (hi - cur) / unit
            return steps
        cur = nxt
        steps += 1.0
    return steps


def load_day_rows(
    conn: sqlite3.Connection, code: str, day: int,
    start_hms: int = GATE_WINDOW[0], end_hms: int = GATE_WINDOW[1],
) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    """(code, day)의 엔진 창 행을 index 오름차순으로 적재.

    Returns:
        (idxs int64[n], arr float64[n, len(_NEEDED_COLUMNS)-1], 열이름→arr열).
        NULL은 0.0 (엔진 np.nan_to_num 미러). 행이 없으면 n=0.
    """
    if not str(code).isdigit() or len(str(code)) != 6:
        raise ValueError(f"6자리 종목코드가 아님: {code!r}")
    lo = int(day) * 1_000_000 + int(start_hms)
    hi = int(day) * 1_000_000 + int(end_hms)
    names = ", ".join(f'"{c}"' for c in _NEEDED_COLUMNS)
    cursor = conn.execute(
        f'SELECT {names} FROM "{code}" WHERE "index" BETWEEN ? AND ? '
        'ORDER BY "index"', (lo, hi),
    )
    rows = cursor.fetchall()
    logger.debug("load_day_rows code=%s day=%s rows=%d", code, day, len(rows))
    if not rows:
        return (np.zeros(0, dtype=np.int64), np.zeros((0, len(_NEEDED_COLUMNS) - 1)),
                {c: i for i, c in enumerate(_NEEDED_COLUMNS[1:])})
    mat = np.array(
        [[0.0 if v is None else float(v) for v in row] for row in rows],
        dtype=np.float64,
    )
    idxs = mat[:, 0].astype(np.int64)
    return idxs, mat[:, 1:], {c: i for i, c in enumerate(_NEEDED_COLUMNS[1:])}


def precompute_windows(arr: np.ndarray, ci: Mapping[str, int]) -> Dict[str, np.ndarray]:
    """엔진 사전계산 컬럼 미러 — 이동평균60(round 3)·등락율각도30(shift 29).

    등락율각도는 게이트런 avg_list=[30] 실측(utility.static.add_rolling_data의
    shift(avg-1) 의미론)을 따른다. 값 미충족 구간은 NaN — 호출측 게이트
    (tick_count)가 먼저 차단하므로 노출되지 않는다.
    """
    price = arr[:, ci["현재가"]]
    pct = arr[:, ci["등락율"]]
    n = price.shape[0]
    ma60 = np.full(n, np.nan)
    if n >= 60:
        kernel = np.convolve(price, np.ones(60) / 60.0, mode="valid")
        ma60[59:] = np.round(kernel, 3)
    ang30 = np.full(n, np.nan)
    if n >= 30:
        diff = pct[29:] - pct[:-29]
        ang30[29:] = np.round(
            np.arctan2(diff * 5.0, 30.0) / (2 * np.pi) * 360.0, 2
        )
    return {"ma60": ma60, "ang30": ang30}


def _ladder_fill(qty: int, hoga: Sequence[float], rem: Sequence[float]) -> Optional[float]:
    """매수호가 사다리 체결 미러(_calc_fill_amount+GetSellPrice) — 매도가 | None."""
    cum = 0.0
    amount = 0.0
    for price, volume in zip(hoga, rem):
        vol = float(volume)
        if cum + vol >= qty:
            amount += float(price) * (qty - cum)
            return float(int(amount / qty + 0.5))
        cum += vol
        amount += float(price) * vol
    return None


def _hms_to_dt(index_value: int) -> datetime:
    return datetime.strptime(str(int(index_value)), _TS_FORMAT)


def replay_champion_exit(
    idxs: np.ndarray, arr: np.ndarray, ci: Mapping[str, int],
    pre: Mapping[str, np.ndarray], *, buy_time: int, buy_price: float, qty: int,
) -> Dict[str, object]:
    """챔피언 현직 매도식의 보유 경로 재실행 — 엔진 미러(재현게이트 핵심).

    Returns:
        {'status': 'ok', 'sell_time', 'sell_price', 'profit_pct', 'cond',
         'best', 'worst'}  또는 {'status': 'entry_row_missing'}.
        cond는 CHAMPION_SELL_CONDS 키(0=전략종료청산).
    """
    n = idxs.shape[0]
    pos = int(np.searchsorted(idxs, int(buy_time)))
    if pos >= n or int(idxs[pos]) != int(buy_time):
        return {"status": "entry_row_missing"}
    t_buy = _hms_to_dt(buy_time)
    price = arr[:, ci["현재가"]]
    best = 0.0
    worst = 0.0
    bg = qty * float(buy_price)
    for i in range(pos + 1, n):
        if i == n - 1:
            break  # 일 마지막 행은 LastSell 전용(엔진 range(start, end_idx) 미러).
        cur = price[i]
        _, _, sp = kiwoom_pgsgsp(bg, qty * cur)
        if sp > best:
            best = sp
        elif sp < worst:
            worst = sp
        fired = _eval_sell_clauses(
            idxs, arr, ci, pre, i=i, profit=sp, best=best,
            hold_sec=(_hms_to_dt(idxs[i]) - t_buy).total_seconds(),
        )
        if fired is None:
            continue
        sell_price = _ladder_fill(
            qty,
            [arr[i, ci["매수호가1"]], arr[i, ci["매수호가2"]], arr[i, ci["매수호가3"]]],
            [arr[i, ci["매수잔량1"]], arr[i, ci["매수잔량2"]], arr[i, ci["매수잔량3"]]],
        )
        if sell_price is None:
            continue  # 잔량 부족 — 미체결, 보유 지속(엔진 Sell() no-op 미러).
        _, _, sell_sp = kiwoom_pgsgsp(bg, qty * sell_price)
        return {
            "status": "ok", "sell_time": int(idxs[i]), "sell_price": sell_price,
            "profit_pct": sell_sp, "cond": fired, "best": best, "worst": worst,
        }
    # LastSell — 사다리 체결 실패 시 매수호가1 강제(GetLastSellPrice 미러).
    last = n - 1
    sell_price = _ladder_fill(
        qty,
        [arr[last, ci["매수호가1"]], arr[last, ci["매수호가2"]], arr[last, ci["매수호가3"]]],
        [arr[last, ci["매수잔량1"]], arr[last, ci["매수잔량2"]], arr[last, ci["매수잔량3"]]],
    )
    if sell_price is None:
        sell_price = float(int(arr[last, ci["매수호가1"]] + 0.5))
    _, _, sell_sp = kiwoom_pgsgsp(bg, qty * sell_price)
    return {
        "status": "ok", "sell_time": int(idxs[last]), "sell_price": sell_price,
        "profit_pct": sell_sp, "cond": 0, "best": best, "worst": worst,
    }


def _eval_sell_clauses(
    idxs, arr, ci, pre, *, i: int, profit: float, best: float, hold_sec: float,
) -> Optional[int]:
    """매도식 절 평가 — 발동 절 번호(CHAMPION_SELL_CONDS 키) 또는 None.

    tick_count = i+1 (일중 행수 — 단일 일 배열 전제, 엔진 per-day reset 미러).
    """
    tick_count = i + 1
    cur = arr[i, ci["현재가"]]
    open_price = arr[i, ci["시가"]]
    pct = arr[i, ci["등락율"]]
    open_vs = ((cur - open_price) / open_price) * 100 if open_price else 0.0
    hms = int(idxs[i]) % 1_000_000

    def low_price(tick: int, pre_n: int) -> float:
        if tick + pre_n <= tick_count:
            s, e = i + 1 - tick - pre_n, i + 1 - pre_n
            return float(arr[s:e, ci["현재가"]].min())
        return 0.0

    def ma(tick: int, pre_n: int = 0) -> float:
        if tick + pre_n <= tick_count:
            return float(pre["ma60"][i - pre_n])
        return 0.0

    def angle(pre_n: int = 0) -> float:
        if 30 + pre_n <= tick_count:
            return float(pre["ang30"][i - pre_n])
        return 0.0

    prev_price = arr[i - 1, ci["현재가"]] if 1 < tick_count else 0.0
    sell_vol = arr[i, ci["초당매도수량"]]
    buy_vol = arr[i, ci["초당매수수량"]]
    bid_total = arr[i, ci["매수총잔량"]]
    cap = arr[i, ci["시가총액"]]

    if pct > 29.5:
        return 1
    if open_vs < 0 and profit <= -2.0 and cur < low_price(60, int(hold_sec)):
        return 2
    if hold_sec > 60 and cur < low_price(60, int(hold_sec)):
        return 3
    if hms < 93000:
        if profit >= 9 or profit <= -5.0:
            return 4
        if best > 3 and best * 0.6 >= profit:
            return 5
        if cap < 10000:
            drop = (cur / prev_price - 1) * 100 if prev_price else 0.0
            if angle() >= 10 and (sell_vol - buy_vol) >= bid_total * 0.5 and drop < -0.5:
                return 6
            if 5 <= angle() < 10 and (sell_vol - buy_vol) >= bid_total * 0.7 and drop < -0.7:
                return 7
            if 0 <= angle() < 5 and (sell_vol - buy_vol) >= bid_total * 0.8 and drop < -0.5:
                return 8
            if 4.5 < best and prev_price >= ma(60, 1) and ma(60) > cur:
                return 9
    return None


# ---------------------------------------------------------------------------
# [2] 격자 반사실 — 봉인 exit_grid 정의 구현.
# ---------------------------------------------------------------------------

def exit_grid_policies() -> List[Dict[str, object]]:
    """봉인 격자 192 조합 — hard_stop × trailing × time_stop × profit_cap 전수."""
    out: List[Dict[str, object]] = []
    for hard, trail, tstop, cap in product(
        EXIT_GRID_AXES["hard_stop_pct"], EXIT_GRID_AXES["trailing_pct"],
        EXIT_GRID_AXES["time_stop_sec"], EXIT_GRID_AXES["profit_cap_pct"],
    ):
        out.append({
            "hard_stop_pct": hard, "trailing_pct": trail,
            "trailing_arm_pct": TRAILING_ARM_PCT if trail is not None else None,
            "time_stop_sec": tstop, "profit_cap_pct": cap,
        })
    return out


def replay_path(
    trade: Mapping[str, object], conn: sqlite3.Connection,
    *, force_exit_hhmmss: int = FORCE_EXIT_HHMMSS,
) -> List[Tuple[int, float]]:
    """거래 보유구간의 (초 오프셋, 매수호가1) 관측 경로 — 격자 반사실 입력.

    trade는 {'code6': 6자리 코드, '진입일자': 'YYYYMMDD', '매수시간': int 14자리}
    를 요구한다. 경로는 매수시간 직후 초부터 force_exit(기본 92900)까지의
    관측 초만 담는다(결측 초 미관측 — 보간·이월 금지, 봉인 path_coverage).
    매수호가1 ≤ 0 행은 관측 불능으로 제외한다.
    """
    code = str(trade["code6"])
    day = int(str(trade["진입일자"]))
    buy_time = int(trade["매수시간"])
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"6자리 종목코드가 아님: {code!r}")
    hi = day * 1_000_000 + int(force_exit_hhmmss)
    cursor = conn.execute(
        f'SELECT "index", "매수호가1" FROM "{code}" '
        'WHERE "index" > ? AND "index" <= ? ORDER BY "index"',
        (buy_time, hi),
    )
    t_buy = _hms_to_dt(buy_time)
    path: List[Tuple[int, float]] = []
    for index_value, bid in cursor:
        bid_f = float(bid) if bid is not None else 0.0
        if bid_f <= 0.0:
            continue
        sec = int((_hms_to_dt(int(index_value)) - t_buy).total_seconds())
        path.append((sec, bid_f))
    return path


def simulate_exit(
    path: Sequence[Tuple[int, float]], policy: Mapping[str, object],
    *, entry_price: float,
) -> Dict[str, float]:
    """봉인 격자 정책 1건의 반사실 청산 — {'exit_sec','exit_price','net_rate',...}.

    의미론(봉인 policy_semantics):
    - 관측 초마다 hard_stop → trailing → profit_cap → time_stop 순 평가.
    - 판정 지표 수익률(%) = net_rate(원장 매수가, 그 초 매수호가1) × 100
      (진입 재모델링 금지 — 매수가 그대로, 마크는 불리틱 미적용).
    - 발동 시 다음 관측 초 매수호가1 체결(다음 초 부재 시 그 초 체결 —
      force_exit 결측 규약과 일관), 미발동 시 force_exit(경로 마지막 관측 초).
    - 체결가는 tick2 불리 강제: sell_fill = adverse_fill(entry, bid)[1].
    - 반환 net_rate는 비용 v1 net_rate(entry_price, sell_fill) 소수(≒원장
      수익률/100과 동일 단위).
    """
    if not path:
        raise ValueError("빈 경로 — 관측 초가 없는 거래는 호출 전에 제외하라")
    entry = float(entry_price)
    hard = policy.get("hard_stop_pct")
    trail = policy.get("trailing_pct")
    tstop = policy.get("time_stop_sec")
    cap = policy.get("profit_cap_pct")
    arm = TRAILING_ARM_PCT
    peak = 0.0
    trigger_pos: Optional[int] = None
    reason = "force_exit"
    for k, (sec, bid) in enumerate(path):
        mark = net_rate(entry, bid) * 100.0
        if mark > peak:
            peak = mark
        if hard is not None and mark <= float(hard):
            trigger_pos, reason = k, "hard_stop"
            break
        if trail is not None and peak > arm and mark <= peak * (float(trail) / 100.0):
            trigger_pos, reason = k, "trailing"
            break
        if cap is not None and mark >= float(cap):
            trigger_pos, reason = k, "profit_cap"
            break
        if tstop is not None and sec >= int(tstop):
            trigger_pos, reason = k, "time_stop"
            break
    if trigger_pos is None:
        fill_pos = len(path) - 1
    else:
        fill_pos = trigger_pos + 1 if trigger_pos + 1 < len(path) else trigger_pos
    fill_sec, fill_bid = path[fill_pos]
    _, sell_fill = adverse_fill(entry, fill_bid, ADVERSE_TICKS)
    rate = net_rate(entry, sell_fill)
    return {
        "exit_sec": float(fill_sec),
        "exit_price": float(sell_fill),
        "net_rate": float(rate),
        "reason": reason,
    }
