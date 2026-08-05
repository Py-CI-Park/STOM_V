"""하루치 tick DB → 진입 후보 라벨 테이블 (QSP9 M-0).

설계 원칙:
- tick DB 는 **read-only** (`file:...?mode=ro`) 로만 연다.
- 초 그리드 재색인 + ffill 로 스테일/공백을 명시적으로 다룬다(함정 2·4).
- 가격 기준 2종: A = 매도호가1→매수호가1 — QA-1 실측으로 **엔진 체결과 일치 확인**(주 라벨).
  B = 현재가→현재가(참조용).
- 모든 수치는 비용 차감 후(%). 라벨 2족 = 고정 h + 경로 MFE/MAE.
"""

from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec

_SKIP_TABLES = frozenset({"moneytop", "sqlite_sequence"})


def _stock_tables(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return [name for (name,) in rows if name not in _SKIP_TABLES]


def _grid_series(sod: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """관측(sod, 값) → 초 그리드 ffill. 그리드 시작 전 구간은 NaN."""
    idx = np.searchsorted(sod, grid, side="right") - 1
    out = np.where(idx >= 0, values[np.clip(idx, 0, None)], np.nan)
    return out


def _forward_extreme(values: np.ndarray, window: int, mode: str) -> np.ndarray:
    """t 이후 (t, t+window] 구간의 최대/최소 — 역방향 rolling 으로 O(n)."""
    series = pd.Series(values[::-1])
    rolled = series.rolling(window, min_periods=1).max() if mode == "max" else \
        series.rolling(window, min_periods=1).min()
    shifted = rolled.to_numpy()[::-1]
    # (t, t+w] 이므로 자기 자신을 빼기 위해 한 칸 앞으로 민 값을 쓴다.
    out = np.empty_like(shifted)
    out[:-1] = shifted[1:]
    out[-1] = np.nan
    return out


def _label_one_stock(frame: pd.DataFrame, code: str, day: int) -> pd.DataFrame | None:
    frame = frame.drop_duplicates(subset="index", keep="last").sort_values("index")
    hhmmss = (frame["index"].to_numpy(dtype=np.int64) % 1_000_000).astype(np.int64)
    sod = ((hhmmss // 10000) * 3600 + ((hhmmss // 100) % 100) * 60 + (hhmmss % 100)).astype(np.int64)
    keep = sod <= spec.hhmmss_to_sod(spec.FORCED_EXIT)
    if not keep.any():
        return None
    frame, sod, hhmmss = frame.loc[keep], sod[keep], hhmmss[keep]

    grid = np.arange(sod[0], sod[-1] + 1, dtype=np.int64)
    price = _grid_series(sod, frame["현재가"].to_numpy(dtype=np.float64), grid)
    ask = _grid_series(sod, frame["매도호가1"].to_numpy(dtype=np.float64), grid)
    bid = _grid_series(sod, frame["매수호가1"].to_numpy(dtype=np.float64), grid)
    # 각 그리드 초의 "관측 나이" — 스테일 판정(함정 2).
    last_obs = _grid_series(sod, sod.astype(np.float64), grid)
    age = grid - last_obs

    entry_mask = (sod >= spec.hhmmss_to_sod(spec.ENTRY_START)) & (sod <= spec.hhmmss_to_sod(spec.ENTRY_END))
    if not entry_mask.any():
        return None
    entry_sod = sod[entry_mask]
    entry_pos = entry_sod - grid[0]
    rows = frame.loc[entry_mask]

    buy_b = price[entry_pos]
    buy_a = ask[entry_pos]
    out: dict[str, np.ndarray] = {}

    def _net_return(buy: np.ndarray, sell: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore", divide="ignore"):
            return ((sell * (1 - spec.COST_OUT)) / (buy * (1 + spec.COST_IN)) - 1) * 100

    end_pos = len(grid) - 1
    for h in spec.HORIZONS:
        tgt = entry_pos + h
        valid = tgt <= end_pos
        tgt_c = np.clip(tgt, 0, end_pos)
        ok = valid & (age[tgt_c] <= spec.STALE_TOLERANCE_SEC)
        sell_b = np.where(ok, price[tgt_c], np.nan)
        sell_a = np.where(ok, bid[tgt_c], np.nan)
        out[f"frB_{h}"] = _net_return(buy_b, sell_b)
        out[f"frA_{h}"] = _net_return(np.where(buy_a > 0, buy_a, np.nan), sell_a)

    # close 라벨 — 그리드 마지막(전체청산 또는 수집 종료) 가격.
    out["frB_close"] = _net_return(buy_b, np.full_like(buy_b, price[end_pos]))
    out["frA_close"] = _net_return(np.where(buy_a > 0, buy_a, np.nan), np.full_like(buy_a, bid[end_pos]))
    truncated = int(grid[-1] < spec.hhmmss_to_sod(spec.CLOSE_TRUNCATED_BEFORE))
    out["close_truncated"] = np.full(len(entry_sod), truncated, dtype=np.int8)

    # 경로 라벨(모양) — 비용 없이 가격 대비 % (청산 시뮬레이션이 아님).
    fmax = _forward_extreme(price, spec.PATH_WINDOW_SEC, "max")
    fmin = _forward_extreme(price, spec.PATH_WINDOW_SEC, "min")
    with np.errstate(invalid="ignore", divide="ignore"):
        out["mfe_300"] = (fmax[entry_pos] / buy_b - 1) * 100
        out["mae_300"] = (fmin[entry_pos] / buy_b - 1) * 100

    # 제외 플래그(함정 2·3).
    tv = rows["초당거래대금"].to_numpy(dtype=np.float64)
    rate = rows["등락율"].to_numpy(dtype=np.float64)
    vi_price = rows["VI가격"].to_numpy(dtype=np.float64)
    vi_tick = rows["VI호가단위"].to_numpy(dtype=np.float64)
    out["flag_no_trade"] = (tv <= 0).astype(np.int8)
    out["flag_limit_up"] = (rate >= spec.LIMIT_UP_RATE).astype(np.int8)
    vi_line = vi_price - spec.VI_TICKS_BELOW * vi_tick
    out["flag_vi_near"] = ((vi_price > 0) & (buy_b >= vi_line)).astype(np.int8)

    # 파생(902/905 공통 지표 재현) — 분위 격자 연구용.
    close_prev = buy_b / (1 + rate / 100)
    open_price = rows["시가"].to_numpy(dtype=np.float64)
    high = rows["고가"].to_numpy(dtype=np.float64)
    low = rows["저가"].to_numpy(dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        out["시가등락율"] = (open_price - close_prev) / close_prev * 100
        out["시가대비등락율"] = (buy_b - open_price) / open_price * 100
        out["spread_pct"] = np.where(buy_b > 0, (ask[entry_pos] - bid[entry_pos]) / buy_b * 100, np.nan)
        span = high - low
        out["일중위치"] = np.where(span > 0, (buy_b - low) / span, np.nan)
    out["초당순매수금액"] = (
        (rows["초당매수수량"].to_numpy(dtype=np.float64) - rows["초당매도수량"].to_numpy(dtype=np.float64))
        * buy_b / 1_000_000
    )

    result = pd.DataFrame(out, index=rows.index)
    for col in spec.SNAPSHOT_COLUMNS:
        result[col] = rows[col].to_numpy(dtype=np.float64)
    result.insert(0, "일자", np.int32(day))
    result.insert(1, "종목코드", code)
    hh = rows["index"].to_numpy(dtype=np.int64) % 1_000_000
    result.insert(2, "시분초", hh.astype(np.int32))
    result.insert(3, "분", ((hh - spec.ENTRY_START) // 100).astype(np.int32))
    return result


def build_day_labels(db_path: str, *, day: int) -> pd.DataFrame:
    """하루치 tick DB(read-only) → 라벨 DataFrame. 종목 테이블 단위 벡터화."""
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        parts: list[pd.DataFrame] = []
        for code in _stock_tables(connection):
            frame = pd.read_sql(f'SELECT * FROM "{code}"', connection)
            if frame.empty:
                continue
            labeled = _label_one_stock(frame, code, day)
            if labeled is not None and not labeled.empty:
                parts.append(labeled)
        if not parts:
            return pd.DataFrame()
        return pd.concat(parts, ignore_index=True)
    finally:
        connection.close()
