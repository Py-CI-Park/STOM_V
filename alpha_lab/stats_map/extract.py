"""일 DB → 표본 배열 추출(dense per-second, read-only) — 벡터화 라벨링.

한 종목-일을 09:00:00~09:30:00 초 오프셋 dense 배열로 올린 뒤:
- L0 후보 = present(t0) & moneytop(t0) & entry(t0+1 매도호가1>0).
- 지평별 net = costs 벡터식(exit=t0+h 매수호가1), 절단(off+h>1800)·결측 분리.
- MFE/MAE = 창 내 매수호가1 최대/최소의 net(net_rate가 매수호가에 단조라
  최대/최소 호가에 1:1 대응 — 경로 전수스캔 없이 rolling max/min).
- 서지 온셋 = axes.surge_onset_mask(교차+쿨다운).
원본은 reader.connect_ro로만 열고(URI mode=ro), 엔진은 호출하지 않는다.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from alpha_lab.dataset.reader import connect_ro, moneytop_universe
from alpha_lab.dataset.schema import as_float
from alpha_lab.stats_map import axes, config, costs

# dense 배열로 올릴 저장 컬럼(이름 기반 — UTF-8 정상 실측).
_COLUMNS = (
    "매도호가1", "매수호가1", "초당거래대금", "등락율", "시가총액",
    "체결강도", "매수총잔량", "매도총잔량",
)
_W = config.WINDOW_SECONDS
_ONE_DAY_SECONDS = 9 * 3600  # 09:00:00 기준 오프셋 변환용.


def _hms_to_offset(hhmmss: int) -> int:
    """int HHMMSS → 09:00:00 기준 초 오프셋(창 밖이면 음수/초과 가능)."""
    h, m, s = hhmmss // 10000, (hhmmss // 100) % 100, hhmmss % 100
    return h * 3600 + m * 60 + s - _ONE_DAY_SECONDS


def _moneytop_by_code(conn) -> Dict[str, np.ndarray]:
    """moneytop → {종목코드: 유니버스 소속 오프셋 배열}(창 내 오프셋만)."""
    out: Dict[str, List[int]] = {}
    for hhmmss, codes in moneytop_universe(conn).items():
        off = _hms_to_offset(int(hhmmss))
        if 0 <= off <= _W:
            for code in codes:
                out.setdefault(code, []).append(off)
    return {code: np.asarray(sorted(offs), dtype=np.int64)
            for code, offs in out.items()}


def _load_dense(conn, code: str) -> Optional[Dict[str, np.ndarray]]:
    """한 종목 테이블을 오프셋 dense 배열로 적재(present 마스크 포함)."""
    cur = conn.execute(f'SELECT "index","' + '","'.join(_COLUMNS) + f'" FROM "{code}"')
    rows = cur.fetchall()
    if not rows:
        return None
    present = np.zeros(_W + 1, dtype=bool)
    cols = {name: np.zeros(_W + 1, dtype=np.float64) for name in _COLUMNS}
    for row in rows:
        off = _hms_to_offset(int(row[0]) % 1_000_000)
        if 0 <= off <= _W:
            present[off] = True
            for name, value in zip(_COLUMNS, row[1:]):
                cols[name][off] = as_float(value)
    cols["present"] = present
    return cols


def _rolling_extremes(bid: np.ndarray, present: np.ndarray, h: int):
    """창 (off+1..off+h] 내 매수호가1 최대/최소 배열(결측은 무시, 무관측 NaN)."""
    bid_nan = np.where(present, bid, np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(bid_nan, h)  # [i]=[i,i+h-1]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN 창 → NaN.
        win_max = np.nanmax(windows, axis=1)
        win_min = np.nanmin(windows, axis=1)
    maxb = np.full(_W + 1, np.nan)
    minb = np.full(_W + 1, np.nan)
    # off의 창은 sliding index off+1(=[off+1, off+h]); off ≤ W-h에서만 정의.
    upper = _W - h
    maxb[1:upper + 1] = win_max[2:upper + 2]
    minb[1:upper + 1] = win_min[2:upper + 2]
    return maxb, minb


def _code_records(dense: Dict[str, np.ndarray], code: str, day: int,
                  uni_offsets: np.ndarray) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 L0 후보 표본 레코드(dict of 배열) — 없으면 None."""
    present = dense["present"]
    ask, bid = dense["매도호가1"], dense["매수호가1"]
    offs = np.arange(config.GRID_START_OFFSET, _W)  # t0 ∈ 09:00:01..09:29:59.
    in_uni = np.isin(offs, uni_offsets)
    entry_ok = present[offs + 1] & (ask[offs + 1] > 0.0)
    cand = present[offs] & in_uni & entry_ok
    t0 = offs[cand]
    if t0.size == 0:
        return None
    return _assemble_records(dense, code, day, t0)


def _assemble_records(dense, code, day, t0) -> Dict[str, np.ndarray]:
    """후보 t0 배열에서 축·라벨·서지·corr 변수를 벡터로 조립한다."""
    present, ask, bid = dense["present"], dense["매도호가1"], dense["매수호가1"]
    entry_ask = ask[t0 + 1]
    ratio = axes.surge_ratio(dense["초당거래대금"], present)
    onset = axes.surge_onset_mask(ratio, present)
    rec: Dict[str, np.ndarray] = {
        "day": np.full(t0.size, day, dtype=np.int32),
        "off": t0.astype(np.int16),
        "time_b": axes.time_bucket_offset(t0).astype(np.int8),
        "updown_q": axes.updown_quartile(dense["등락율"][t0]).astype(np.int8),
        "mktcap_b": axes.mktcap_bucket(dense["시가총액"][t0]).astype(np.int8),
        "is_onset": onset[t0],
        "minute": t0.astype(np.int16),
        "mktcap": dense["시가총액"][t0].astype(np.float32),
        "updown": dense["등락율"][t0].astype(np.float32),
        "surge": ratio[t0].astype(np.float32),
        "strength": dense["체결강도"][t0].astype(np.float32),
        "rest_ratio": _rest_ratio(dense, t0).astype(np.float32),
    }
    for h in config.HORIZONS:
        _add_horizon(rec, dense, t0, entry_ask, h)
    return rec


def _rest_ratio(dense, t0) -> np.ndarray:
    """매수총잔량/매도총잔량(잔량비) — 분모 0 가드(프로파일링 잔량비 축)."""
    return dense["매수총잔량"][t0] / np.maximum(dense["매도총잔량"][t0], 1.0)


def _add_horizon(rec, dense, t0, entry_ask, h: int) -> None:
    """지평 h의 net·valid·censor·MFE·MAE를 레코드에 추가한다."""
    present, bid = dense["present"], dense["매수호가1"]
    exit_off = t0 + h
    within = exit_off <= _W                       # 창 내(절단 아님).
    censored = ~within                            # off+h>1800 = 우측 절단.
    exit_present = np.zeros(t0.size, dtype=bool)
    exit_present[within] = present[exit_off[within]]
    valid = within & exit_present
    net = np.full(t0.size, np.nan, dtype=np.float64)
    net[valid] = costs.net_from_quotes(entry_ask[valid], bid[exit_off[valid]])
    maxb, minb = _rolling_extremes(bid, present, h)
    mfe = np.full(t0.size, np.nan)
    mae = np.full(t0.size, np.nan)
    ok = valid & np.isfinite(maxb[t0])
    mfe[ok] = costs.net_from_quotes(entry_ask[ok], maxb[t0][ok])
    mae[ok] = costs.net_from_quotes(entry_ask[ok], minb[t0][ok])
    rec[f"net_{h}"] = net.astype(np.float32)
    rec[f"valid_{h}"] = valid
    rec[f"censored_{h}"] = censored
    rec[f"mfe_{h}"] = mfe.astype(np.float32)
    rec[f"mae_{h}"] = mae.astype(np.float32)


def extract_day(db_path, date: str) -> Dict[str, np.ndarray]:
    """일 DB 하나의 전 종목 L0 후보 표본을 배열 dict로 반환(결정론)."""
    conn = connect_ro(Path(db_path))
    try:
        uni = _moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            dense = _load_dense(conn, code)
            if dense is None:
                continue
            rec = _code_records(dense, code, day, uni.get(code, np.empty(0, np.int64)))
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    return _concat_chunks(chunks)


def _concat_chunks(chunks: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    """종목별 레코드 dict들을 컬럼별로 이어붙인다(빈 입력은 빈 배열)."""
    if not chunks:
        return {}
    keys = chunks[0].keys()
    return {key: np.concatenate([c[key] for c in chunks]) for key in keys}
