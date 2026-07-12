"""O-3 돌파 온셋 검출 — dense 로더 + 5변형 사건 마스크 (봉인본 §3·§14-F6·F7).

봉인 F6: extract.py 무수정(공유 인프라 드리프트 방지). 돌파 컬럼(현재가·고가·시가·
VI해제시간)은 저장 컬럼이며 dense 로더 추가는 gap_o1g `_COLUMNS_O1G` 선례 미러다.
온셋 검출층만 신규 — 라벨층(labels_v2/pilot_v2)은 무변경 재사용(breakouts.py).

공통 역학(§3·F7 봉인):
- L0 = 관심종목=1(≡moneytop) (종목,일,초) dense 오프셋 그리드 + present 마스크.
- 온셋 = 상태 교차(S(t) ∧ ¬S(t_prev)) — **t_prev = 직전 present 행**(서지의
  "직전 초, 부재→False" 규칙과 다름 — 허위 재점화 방지, F7-①). 변형별 독립.
- 동일 종목 30초 쿨다운(`axes._apply_cooldown` 재사용) — VI는 사건당 1회라 불요.
- 공통 워밍업: 오프셋 < 30(09:00:00~09:00:29)은 온셋 제외. entry 여지 off ≤ W−1.

5변형(F1 봉인 — 측정 후 추가·변경 금지):
- P20  : 구간최고가(20초) 돌파 — 현재가(t) > max{현재가: [t−20,t−1] present}, 창 관측 ≥7.
- P300 : 구간최고가(300초) 돌파 — 동, 창 [t−300,t−1], 창 관측 ≥100(원문 미실재 딱지).
- DH   : 당일 신고가 경신 — 고가(t) > 고가(t_prev)(저장 고가 = 당일 누적 최고, 행 갱신).
- OP   : 시가 상향 돌파 — 현재가(t) > 시가(t) 아래→위 교차(마진 0%, F3).
- VI   : VI 발동 후 재개 — VI해제시간>0 ∧ 체결시간≥VI해제시간 ∧ 해당 VI값 첫 present 행.

원본 tick DB read-only(reader.connect_ro). 엔진 백테 0회. print 금지 — logging.
"""
from __future__ import annotations

import logging
import warnings
from typing import Dict, Optional

import numpy as np

from alpha_lab.dataset.schema import as_float
from alpha_lab.stats_map import axes, config, extract

logger = logging.getLogger(__name__)

__all__ = [
    "COLUMNS_O3",
    "PRICE_WINDOW",
    "VARIANTS",
    "WARMUP_OFF",
    "breakout_onset_offsets",
    "load_dense_o3",
]

_W = config.WINDOW_SECONDS               # 1800 (09:00:00~09:30:00 오프셋 상한).
WARMUP_OFF = 30                          # 온셋 판정 최소 오프셋(09:00:30, §3 워밍업).

# 돌파 온셋 로스터(순서 고정 — FDR·리포트 열거 순서).
VARIANTS = ("P20", "P300", "DH", "OP", "VI")

# 창 길이·창 내 최소 관측(P20=20/7, P300=300/100 — 서지 10/30 비율 준용, F7-②).
PRICE_WINDOW: Dict[str, tuple] = {"P20": (20, 7), "P300": (300, 100)}

# dense 적재 컬럼 — v1 8컬럼 골격에 돌파 파생용 현재가·고가·시가·VI해제시간 편입
# (gap_o1g `_COLUMNS_O1G` 선례). 매도호가1=entry·매수호가1=exit·등락율/시가총액=축.
COLUMNS_O3 = (
    "매도호가1", "매수호가1", "등락율", "시가총액",
    "현재가", "고가", "시가", "VI해제시간",
)


def load_dense_o3(conn, code: str) -> Optional[Dict[str, np.ndarray]]:
    """한 종목 테이블 → 오프셋 dense 배열(present 포함) — gap_o1g._load_dense_o1g 미러.

    이름 기반 SELECT(UTF-8 정상 실측). 결측 초는 present=False, 값 0.0(as_float).
    """
    cur = conn.execute(
        f'SELECT "index","' + '","'.join(COLUMNS_O3) + f'" FROM "{code}"')
    rows = cur.fetchall()
    if not rows:
        return None
    present = np.zeros(_W + 1, dtype=bool)
    cols = {name: np.zeros(_W + 1, dtype=np.float64) for name in COLUMNS_O3}
    for row in rows:
        off = extract._hms_to_offset(int(row[0]) % 1_000_000)
        if 0 <= off <= _W:
            present[off] = True
            for name, value in zip(COLUMNS_O3, row[1:]):
                cols[name][off] = as_float(value)
    cols["present"] = present
    return cols


def _offset_to_index(day: int, off: int) -> int:
    """오프셋(09:00:00 기준 초) → int YYYYMMDDHHMMSS (pilot_v2._offset_to_index 동형)."""
    total = 9 * 3600 + int(off)
    hh, rem = divmod(total, 3600)
    mm, ss = divmod(rem, 60)
    return int(day) * 1_000_000 + hh * 10000 + mm * 100 + ss


def _prior_window_max(cur: np.ndarray, present: np.ndarray, n: int):
    """오프셋별 직전 창 [t−n, t−1] 내 present 현재가 최대·관측수(무관측 → NaN·0).

    좌측 n 패딩 + sliding_window_view 로 각 t 의 prior 창을 잡는다(extract._rolling_extremes
    스타일). all-NaN 창은 NaN(관측 0). t 자신은 창에서 제외(직전 창).
    """
    cur_nan = np.where(present, np.asarray(cur, dtype=np.float64), np.nan)
    padded = np.concatenate([np.full(n, np.nan), cur_nan])       # padded[k]=cur_nan[k−n].
    win = np.lib.stride_tricks.sliding_window_view(padded, n)     # win[t] = [t−n, t−1].
    win = win[: _W + 1]                                          # t = 0..W.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # all-NaN → NaN.
        pmax = np.nanmax(win, axis=1)
    cnt = np.isfinite(win).sum(axis=1).astype(np.int64)
    return pmax, cnt


def _cross_offsets(state: np.ndarray, present: np.ndarray) -> np.ndarray:
    """상태 bool → 직전 present 행 기준 상승 교차 오프셋(S ∧ ¬S_prev, F7-① t_prev 규칙).

    present 부분수열 위에서 교차를 잡는다 — 결측 갭을 건너뛴 직전 관측이 t_prev.
    """
    pres = np.flatnonzero(present)
    if pres.size == 0:
        return np.empty(0, dtype=np.int64)
    s = np.asarray(state, dtype=bool)[pres]
    prev = np.concatenate(([False], s[:-1]))                     # 선두 t_prev = False.
    return pres[s & ~prev]


def _high_step_offsets(high: np.ndarray, present: np.ndarray) -> np.ndarray:
    """당일 신고가 경신 온셋 — 고가(t) > 고가(직전 present 행). 선두 present 행 제외."""
    pres = np.flatnonzero(present)
    if pres.size == 0:
        return np.empty(0, dtype=np.int64)
    h = np.asarray(high, dtype=np.float64)[pres]
    prev_h = np.concatenate(([np.inf], h[:-1]))                  # 선두 = inf → 경신 아님.
    return pres[h > prev_h]


def _vi_onsets(vi_release: np.ndarray, present: np.ndarray, day: int) -> np.ndarray:
    """VI 발동 후 재개 온셋 — VI해제시간>0 ∧ 체결시간≥VI해제시간 ∧ 해당 VI값 첫 present 행.

    VI 사건당 1회(쿨다운 불요). 체결시간 = present 행의 전체 timestamp(offset 환산).
    """
    pres = np.flatnonzero(present)
    if pres.size == 0:
        return np.empty(0, dtype=np.int64)
    vi = np.asarray(vi_release, dtype=np.float64)[pres]
    ts = np.array([_offset_to_index(day, int(o)) for o in pres], dtype=np.int64)
    elig = (vi > 0.0) & (ts >= vi)
    if not elig.any():
        return np.empty(0, dtype=np.int64)
    elig_off = pres[elig]
    elig_vi = vi[elig]
    # pres 오름차순이므로 각 VI값 첫 등장 = 최소 오프셋(해제 후 첫 재개 행).
    _, first_idx = np.unique(elig_vi, return_index=True)
    return np.sort(elig_off[first_idx].astype(np.int64))


def _finalize(onset_off: np.ndarray, *, cooldown: bool) -> np.ndarray:
    """워밍업(≥30)·entry 여지(≤W−1) 필터 + (선택) 30초 쿨다운(axes._apply_cooldown 재사용)."""
    onset_off = np.asarray(onset_off, dtype=np.int64)
    onset_off = onset_off[(onset_off >= WARMUP_OFF) & (onset_off <= _W - 1)]
    if onset_off.size == 0:
        return onset_off
    if cooldown:
        cross = np.zeros(_W + 1, dtype=bool)
        cross[onset_off] = True
        kept = axes._apply_cooldown(cross)                      # 봉인 30초 쿨다운.
        onset_off = np.flatnonzero(kept).astype(np.int64)
    return onset_off


def breakout_onset_offsets(dense: Dict[str, np.ndarray], variant: str,
                           day: int) -> np.ndarray:
    """한 종목 dense → 변형 v 의 돌파 온셋 오프셋(공통 워밍업·쿨다운 적용, 유니버스 필터 전).

    유니버스(관심종목)·entry 필터는 호출측(breakouts._code_breakouts)이 서지 경로와
    동일하게 적용한다(cross+cooldown 은 여기서, in_uni & entry_ok 는 이후 — 서지 정합).
    """
    if variant not in VARIANTS:
        raise ValueError(f"알 수 없는 변형: {variant!r} (허용 {VARIANTS})")
    present = dense["present"]
    if variant in PRICE_WINDOW:
        n, min_obs = PRICE_WINDOW[variant]
        pmax, cnt = _prior_window_max(dense["현재가"], present, n)
        state = (present & np.isfinite(pmax) & (cnt >= min_obs)
                 & (dense["현재가"] > pmax))
        return _finalize(_cross_offsets(state, present), cooldown=True)
    if variant == "OP":
        state = present & (dense["시가"] > 0.0) & (dense["현재가"] > dense["시가"])
        return _finalize(_cross_offsets(state, present), cooldown=True)
    if variant == "DH":
        return _finalize(_high_step_offsets(dense["고가"], present), cooldown=True)
    # VI — 사건당 1회, 쿨다운 불요.
    return _finalize(_vi_onsets(dense["VI해제시간"], present, day), cooldown=False)
