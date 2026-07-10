"""셀 축 버킷화 + 서지 온셋 탐지 — 사전등록 §2/§3 봉인 규약 구현.

- time_bucket: t0의 09:00:00 기준 초 오프셋 → 5분 버킷(900..925).
- updown_quartile / mktcap_bucket: 봉인 경계로 digitize(경계값은 상단 구간 포함).
- surge_ratio / surge_onset: 초당거래대금(t) / 직전 30초 평균(관측≥10·평균>0),
  <2→≥2 교차(직전 초 미충족→당해 초 충족), 동일 종목 30초 쿨다운.
  프로파일링 §7 "서지배수/L1 온셋" 정의와 동일 — 여기가 단일 출처다.
"""
from __future__ import annotations

import numpy as np

from alpha_lab.stats_map import config

__all__ = [
    "mktcap_bucket",
    "surge_onset_mask",
    "surge_ratio",
    "time_bucket_label",
    "time_bucket_offset",
    "updown_quartile",
]


def time_bucket_offset(offset: np.ndarray) -> np.ndarray:
    """초 오프셋(09:00:00 기준) → 5분 버킷 인덱스 0..5."""
    return np.asarray(offset, dtype=np.int64) // config.TIME_BUCKET_SECONDS


def time_bucket_label(bucket_index: np.ndarray) -> np.ndarray:
    """버킷 인덱스 0..5 → 라벨(900/905/.../925)."""
    return 900 + np.asarray(bucket_index, dtype=np.int64) * 5


def updown_quartile(updown: np.ndarray) -> np.ndarray:
    """등락율 → 4분위 인덱스 0..3(경계 1.71/3.47/6.70, 경계값은 상단 포함)."""
    return np.searchsorted(np.asarray(config.UPDOWN_EDGES),
                           np.asarray(updown, dtype=np.float64), side="right")


def mktcap_bucket(mktcap: np.ndarray) -> np.ndarray:
    """시가총액(억) → 3구간 인덱스 0..2(<1000/1000-3000/3000+)."""
    return np.searchsorted(np.asarray(config.MKTCAP_EDGES),
                           np.asarray(mktcap, dtype=np.float64), side="right")


def surge_ratio(amount: np.ndarray, present: np.ndarray) -> np.ndarray:
    """초당거래대금(dense) → 서지배수(직전 30초 평균 대비), 무효는 NaN.

    Args:
        amount: 오프셋별 초당거래대금(결측 초는 값 무시 — present로 판별).
        present: 오프셋별 관측 여부 bool.

    직전 30초 창 [off-30, off-1] 안 present 관측이 ≥10이고 평균>0일 때만
    amount[off]/평균, 아니면 NaN. off 자신이 결측이면 NaN.
    """
    amt = np.asarray(amount, dtype=np.float64)
    obs = np.asarray(present, dtype=bool)
    n = amt.shape[0]
    contrib = np.where(obs, amt, 0.0)
    csum = np.concatenate([[0.0], np.cumsum(contrib)])
    ccnt = np.concatenate([[0.0], np.cumsum(obs.astype(np.float64))])
    win = config.SURGE_WINDOW_SEC
    out = np.full(n, np.nan, dtype=np.float64)
    idx = np.arange(n)
    lo = np.maximum(idx - win, 0)
    win_sum = csum[idx] - csum[lo]          # [off-30, off-1] 합.
    win_cnt = ccnt[idx] - ccnt[lo]          # 그 창 관측 수.
    mean = np.divide(win_sum, win_cnt, out=np.full(n, np.nan), where=win_cnt > 0)
    ok = obs & (win_cnt >= config.SURGE_MIN_OBS) & (mean > 0.0)
    out[ok] = amt[ok] / mean[ok]
    return out


def surge_onset_mask(ratio: np.ndarray, present: np.ndarray) -> np.ndarray:
    """서지배수 dense → 온셋 오프셋 bool(교차 + 30초 쿨다운 적용).

    온셋(off) = present[off] & ratio[off]≥2 & NOT(ratio[off-1]≥2). 이후 동일
    종목 30초 이내 온셋은 억제한다(첫 온셋 후 gap<30 억제, gap≥30 허용).
    """
    r = np.asarray(ratio, dtype=np.float64)
    obs = np.asarray(present, dtype=bool)
    state = obs & (r >= config.SURGE_THRESHOLD)   # NaN>=2 → False.
    prev = np.concatenate([[False], state[:-1]])  # 직전 초 상태(부재→False).
    cross = state & ~prev
    return _apply_cooldown(cross)


def _apply_cooldown(cross: np.ndarray) -> np.ndarray:
    """교차 마스크에 30초 쿨다운 적용 — 채택 온셋만 True로 남긴다."""
    kept = np.zeros_like(cross, dtype=bool)
    last = -config.ONSET_COOLDOWN_SEC - 1
    for off in np.nonzero(cross)[0]:
        if off - last >= config.ONSET_COOLDOWN_SEC:
            kept[off] = True
            last = off
    return kept
