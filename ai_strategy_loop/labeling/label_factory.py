"""하루치 시세 DB → 진입 후보 라벨 테이블 (QSP9 M-0). tick(초)·min(분) 공용.

설계 원칙:
- 시세 DB 는 **read-only** (`file:...?mode=ro`) 로만 연다.
- 시간 그리드 재색인 + ffill 로 스테일/공백을 명시적으로 다룬다(함정 2·4).
- 가격 기준 2종: A = 매도호가1→매수호가1 — QA-1 실측으로 **엔진 체결과 일치 확인**(주 라벨).
  B = 현재가→현재가(참조용).
- 모든 수치는 비용 차감 후(%). 라벨 2족 = 고정 h + 경로 MFE/MAE.
- 레인 차이(시간 해상도·분당/초당 컬럼·세션 창)는 lanes.LaneSpec 이 정본.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import derived
from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.lanes import BARRIERS_DOWN, BARRIERS_UP, TICK, LaneSpec
from ai_strategy_loop.labeling.trailing import trailing_columns

_SKIP_TABLES = frozenset({"moneytop", "sqlite_sequence"})


def _stock_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return [name for (name,) in rows if name not in _SKIP_TABLES]


def _grid_series(uod: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(uod, grid, side="right") - 1
    return np.where(idx >= 0, values[np.clip(idx, 0, None)], np.nan)


def _forward_extreme(values: np.ndarray, window: int, mode: str) -> np.ndarray:
    """t 이후 (t, t+window] 구간의 최대/최소 — 역방향 rolling 으로 O(n)."""
    series = pd.Series(values[::-1])
    rolled = series.rolling(window, min_periods=1).max() if mode == "max" else \
        series.rolling(window, min_periods=1).min()
    shifted = rolled.to_numpy()[::-1]
    out = np.empty_like(shifted)
    out[:-1] = shifted[1:]
    out[-1] = np.nan
    return out


def _barrier_hits(out: dict, *, price: np.ndarray, bid: np.ndarray, buy_ask: np.ndarray,
                  entry_pos: np.ndarray, end_pos: int, horizon: int) -> None:
    """배리어 최초 도달 시각(진입 후 경과 단위). 미도달은 `horizon` 으로 표기.

    체결 가능 기준: 매수는 `매도호가1`, 청산은 `매수호가1` — QA-1 로 검증된 엔진 모델.
    비용은 배리어 정의에서 제외한다(임계는 **가격 기준 %** 이고, 비용은 기대값 계산에서 뺀다).
    """
    n_entries = len(entry_pos)
    ups = {level: np.full(n_entries, horizon, dtype=np.int32) for level in BARRIERS_UP}
    downs = {level: np.full(n_entries, horizon, dtype=np.int32) for level in BARRIERS_DOWN}

    for index in range(n_entries):
        start = int(entry_pos[index])
        entry_price = buy_ask[index]
        if not np.isfinite(entry_price) or entry_price <= 0:
            continue
        stop = min(start + horizon, end_pos)
        if stop <= start:
            continue
        path = bid[start + 1:stop + 1]
        if path.size == 0:
            continue
        ratio = (path / entry_price - 1.0) * 100.0
        running_max = np.maximum.accumulate(ratio)
        running_min = np.minimum.accumulate(ratio)
        for level in BARRIERS_UP:
            pos = int(np.searchsorted(running_max, level, side="left"))
            if pos < ratio.size:
                ups[level][index] = pos + 1
        for level in BARRIERS_DOWN:
            pos = int(np.searchsorted(-running_min, level, side="left"))
            if pos < ratio.size:
                downs[level][index] = pos + 1

    for level, values in ups.items():
        out[f"hit_up_{int(level)}"] = values
    for level, values in downs.items():
        out[f"hit_dn_{int(level)}"] = values


def _label_one_stock(frame: pd.DataFrame, code: str, day: int,
                     lane: LaneSpec) -> pd.DataFrame | None:
    clock_mod = 10 ** (lane.time_digits - 8)
    frame = frame.drop_duplicates(subset="index", keep="last").sort_values("index")
    clock = (frame["index"].to_numpy(dtype=np.int64) % clock_mod).astype(np.int64)
    uod = np.array([lane.unit_of_day(int(c)) for c in clock], dtype=np.int64)
    keep = uod <= lane.unit_of_day(lane.forced_exit)
    if not keep.any():
        return None
    frame, uod, clock = frame.loc[keep], uod[keep], clock[keep]

    grid = np.arange(uod[0], uod[-1] + 1, dtype=np.int64)
    price = _grid_series(uod, frame["현재가"].to_numpy(dtype=np.float64), grid)
    ask = _grid_series(uod, frame["매도호가1"].to_numpy(dtype=np.float64), grid)
    bid = _grid_series(uod, frame["매수호가1"].to_numpy(dtype=np.float64), grid)
    last_obs = _grid_series(uod, uod.astype(np.float64), grid)
    age = grid - last_obs

    entry_mask = (uod >= lane.unit_of_day(lane.entry_start)) & \
        (uod <= lane.unit_of_day(lane.entry_end))
    if not entry_mask.any():
        return None
    entry_uod = uod[entry_mask]
    entry_pos = entry_uod - grid[0]
    rows = frame.loc[entry_mask]

    buy_b = price[entry_pos]
    buy_a = ask[entry_pos]
    out: dict[str, np.ndarray] = {}

    def _net_return(buy: np.ndarray, sell: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            return ((sell * (1 - spec.COST_OUT)) / (buy * (1 + spec.COST_IN)) - 1) * 100

    end_pos = len(grid) - 1
    for horizon in lane.horizons:
        tgt = entry_pos + horizon
        valid = tgt <= end_pos
        tgt_c = np.clip(tgt, 0, end_pos)
        ok = valid & (age[tgt_c] <= lane.stale_tolerance)
        out[f"frB_{horizon}"] = _net_return(buy_b, np.where(ok, price[tgt_c], np.nan))
        out[f"frA_{horizon}"] = _net_return(np.where(buy_a > 0, buy_a, np.nan),
                                            np.where(ok, bid[tgt_c], np.nan))

    out["frB_close"] = _net_return(buy_b, np.full_like(buy_b, price[end_pos]))
    out["frA_close"] = _net_return(np.where(buy_a > 0, buy_a, np.nan),
                                   np.full_like(buy_a, bid[end_pos]))
    truncated = int(grid[-1] < lane.unit_of_day(lane.close_truncated_before))
    out["close_truncated"] = np.full(len(entry_uod), truncated, dtype=np.int8)

    window = lane.path_window
    fmax = _forward_extreme(price, window, "max")
    fmin = _forward_extreme(price, window, "min")
    with np.errstate(invalid="ignore", divide="ignore"):
        out[f"mfe_{window}"] = (fmax[entry_pos] / buy_b - 1) * 100
        out[f"mae_{window}"] = (fmin[entry_pos] / buy_b - 1) * 100

    # ── v2 ① 봉투: 체크포인트마다 "그때까지의" 최고/최저 (누적 → 단조 보장).
    for point in lane.checkpoints:
        if point == window:
            continue
        cmax = _forward_extreme(price, point, "max")
        cmin = _forward_extreme(price, point, "min")
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"mfe_{point}"] = (cmax[entry_pos] / buy_b - 1) * 100
            out[f"mae_{point}"] = (cmin[entry_pos] / buy_b - 1) * 100

    # ── v2 ② 배리어 도달 시각: **실현 가능 경로**(매도호가1 매수 → 매수호가1 청산) 기준.
    #    누적 최대/최소 bid 가 임계를 처음 넘은 시점을 이분 탐색으로 찾는다.
    horizon = lane.barrier_horizon
    with np.errstate(invalid="ignore", divide="ignore"):
        ret_path = (bid * (1 - spec.COST_OUT)) / (ask * (1 + spec.COST_IN)) - 1.0
    # ret_path 는 "지금 팔면"의 수익률. 진입 시점 ask 기준으로 다시 계산해야 하므로
    #   각 진입에 대해 bid 경로를 훑는다 — 누적 max/min 을 O(n) 으로 만들고 위치를 찾는다.
    _barrier_hits(out, price=price, bid=bid, buy_ask=buy_a, entry_pos=entry_pos,
                  end_pos=end_pos, horizon=horizon)

    # ── v4: 트레일링 **실현값**. 경로를 그대로 시뮬레이션하므로 근사가 아니라
    #    계산이다(러닝 최고만 사용 — 구간 최종 최고를 쓰면 미래 참조가 된다).
    #    W3 재현 게이트가 "청산 표현력 부족"으로 멈춘 지점을 여는 열이다.
    out.update(trailing_columns(
        bid=bid, ask=ask, entry_pos=entry_pos, horizon=horizon,
        stale_ok=(age <= lane.stale_tolerance).astype(np.int8),
    ))

    flow_tv = f"{lane.flow_prefix}거래대금"
    tv = rows[flow_tv].to_numpy(dtype=np.float64)
    rate = rows["등락율"].to_numpy(dtype=np.float64)
    vi_price = rows["VI가격"].to_numpy(dtype=np.float64)
    vi_tick = rows["VI호가단위"].to_numpy(dtype=np.float64)
    out["flag_no_trade"] = (tv <= 0).astype(np.int8)
    out["flag_limit_up"] = (rate >= spec.LIMIT_UP_RATE).astype(np.int8)
    vi_line = vi_price - spec.VI_TICKS_BELOW * vi_tick
    out["flag_vi_near"] = ((vi_price > 0) & (buy_b >= vi_line)).astype(np.int8)

    close_prev = buy_b / (1 + rate / 100)
    open_price = rows["시가"].to_numpy(dtype=np.float64)
    high = rows["고가"].to_numpy(dtype=np.float64)
    low = rows["저가"].to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["시가등락율"] = (open_price - close_prev) / close_prev * 100
        out["시가대비등락율"] = (buy_b - open_price) / open_price * 100
        out["spread_pct"] = np.where(buy_b > 0, (ask[entry_pos] - bid[entry_pos]) / buy_b * 100,
                                     np.nan)
        span = high - low
        out["일중위치"] = np.where(span > 0, (buy_b - low) / span, np.nan)
    out[f"{lane.flow_prefix}순매수금액"] = (
        (rows[f"{lane.flow_prefix}매수수량"].to_numpy(dtype=np.float64)
         - rows[f"{lane.flow_prefix}매도수량"].to_numpy(dtype=np.float64))
        * buy_b / 1_000_000
    )

    # ── v3 파생 특징(변화율·비율·누적·직전 대비). QSP10 근본 원인 교정 —
    #    지도가 '현재 값'만 갖고 있어 902/905 류 신호를 볼 수 없었다.
    #    창은 관측 시계열 위에서 계산하고, 진입 행만 잘라낸다(미래 미참조).
    derived_all = derived.build(frame, flow_prefix=lane.flow_prefix)
    entry_rows = np.flatnonzero(entry_mask)
    for name, series in derived_all.items():
        out[name] = series[entry_rows]

    result = pd.DataFrame(out, index=rows.index)
    for column in lane.snapshot_columns:
        result[column] = rows[column].to_numpy(dtype=np.float64)
    result.insert(0, "일자", np.int32(day))
    result.insert(1, "종목코드", code)
    result.insert(2, "시분초", clock[entry_mask].astype(np.int32))
    result.insert(3, "분", (entry_uod - lane.unit_of_day(lane.entry_start)).astype(np.int32)
                  // (60 if lane.time_digits == 14 else 1))
    # 집행 우주 필터용 — 종목별 수집 시작 후 경과(시간 단위). C1 부검 교훈.
    result.insert(4, "경과", (entry_uod - int(grid[0])).astype(np.int32))
    return result


def build_day_labels(db_path: str, *, day: int, lane: LaneSpec = TICK) -> pd.DataFrame:
    """하루치 시세 DB(read-only) → 라벨 DataFrame. 종목 테이블 단위 벡터화."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        parts: list[pd.DataFrame] = []
        for code in _stock_tables(connection):
            frame = pd.read_sql(f'SELECT * FROM "{code}"', connection)
            if frame.empty:
                continue
            labeled = _label_one_stock(frame, code, day, lane)
            if labeled is not None and not labeled.empty:
                parts.append(labeled)
        if not parts:
            return pd.DataFrame()
        return pd.concat(parts, ignore_index=True)
    finally:
        connection.close()
