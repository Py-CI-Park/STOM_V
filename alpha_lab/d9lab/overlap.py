"""전이 온셋 ∩ 서지 온셋 겹침률 — 봉인본 §8·§14-2.

같은 (일자, code)에서 |전이초 − 서지초| ≤ window 면 겹침. 판정 window = ±30초
(서지 쿨다운 ONSET_COOLDOWN_SEC=30 정합), 민감도 0초(정확 일치)·±60초 병기.
겹침률 = |겹친 전이 온셋| / |전이 온셋| ≤ 0.50 이라야 "구별 모집단"(§7 kill-3).

서지 온셋은 기존 onset_l3_bank.parquet(code, day, off)을 read-only 로만 소비 —
재산출하지 않는다(§14-8 은행 봉인). 전이 온셋 은행은 R1 산출물.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = ["OVERLAP_CAP", "OVERLAP_WINDOWS", "PRIMARY_WINDOW", "compute_overlap"]

OVERLAP_CAP = 0.50            # 겹침률 상한(§8, 초과 = 구별 모집단 아님 kill-3).
PRIMARY_WINDOW = 30           # 판정 window(±초, §14-2).
OVERLAP_WINDOWS = (0, 30, 60)  # 판정(30) + 민감도(0·60), §14-2.


def _overlap_mask_one_day(
    tr_off: np.ndarray, sg_off: np.ndarray, window: int,
) -> np.ndarray:
    """한 (일자,code)의 전이 오프셋 각각이 서지 오프셋과 window 내 겹치는지(bool)."""
    if tr_off.size == 0:
        return np.empty(0, dtype=bool)
    if sg_off.size == 0:
        return np.zeros(tr_off.size, dtype=bool)
    sg = np.sort(sg_off)
    # 각 전이 오프셋에 대해 가장 가까운 서지 오프셋과의 거리 ≤ window.
    pos = np.searchsorted(sg, tr_off)
    left = np.clip(pos - 1, 0, sg.size - 1)
    right = np.clip(pos, 0, sg.size - 1)
    dist = np.minimum(np.abs(tr_off - sg[left]), np.abs(tr_off - sg[right]))
    return dist <= window


def _overlap_rate(
    tr: pd.DataFrame, surge_by_key: Dict[tuple, np.ndarray], window: int,
    subpop_mask: np.ndarray,
) -> Dict[str, float]:
    """서브모집단(subpop_mask)의 겹침률 — (일자,code) 그룹별 벡터 판정 후 집계."""
    idx = np.flatnonzero(subpop_mask)
    if idx.size == 0:
        return {"n": 0, "n_overlap": 0, "rate": float("nan")}
    overlapped = np.zeros(idx.size, dtype=bool)
    codes = tr["code"].to_numpy()[idx]
    days = tr["day"].to_numpy()[idx]
    offs = tr["off"].to_numpy()[idx].astype(np.int64)
    order = np.lexsort((offs, codes, days))
    # 그룹별 처리(같은 key 연속 구간).
    keys = list(zip(days[order], codes[order]))
    start = 0
    while start < len(keys):
        end = start
        while end < len(keys) and keys[end] == keys[start]:
            end += 1
        g = order[start:end]
        sg = surge_by_key.get((int(days[g[0]]), str(codes[g[0]])), np.empty(0, np.int64))
        overlapped[g] = _overlap_mask_one_day(offs[g], sg, window)
        start = end
    n_ov = int(overlapped.sum())
    return {"n": int(idx.size), "n_overlap": n_ov, "rate": n_ov / idx.size}


def _surge_index(surge_bank_path) -> Dict[tuple, np.ndarray]:
    """onset_l3_bank.parquet → {(day, code): 서지 오프셋 배열}. read-only."""
    df = pd.read_parquet(surge_bank_path, columns=["code", "day", "off"])
    out: Dict[tuple, list] = {}
    for code, day, off in zip(df["code"].to_numpy(), df["day"].to_numpy(),
                              df["off"].to_numpy()):
        out.setdefault((int(day), str(code)), []).append(int(off))
    return {k: np.asarray(sorted(v), dtype=np.int64) for k, v in out.items()}


def compute_overlap(
    transition_df: pd.DataFrame, surge_bank_path,
    *, windows: Sequence[int] = OVERLAP_WINDOWS,
) -> Dict[str, object]:
    """전이 온셋(관측가능) vs 서지 은행 겹침률 — window별 × 서브모집단별.

    판정: PRIMARY_WINDOW(±30) pooled 겹침률 ≤ OVERLAP_CAP. 초과 = kill-3(무가치 종결).
    Returns: {surge_n_keys, per_window{window: {pooled, new, reentry}}, gate_pass, cap, primary_window}.
    """
    surge = _surge_index(surge_bank_path)
    obs = transition_df["observable"].to_numpy().astype(bool)
    reentry = transition_df["is_reentry"].to_numpy().astype(bool)
    masks = {"pooled": obs, "new": obs & ~reentry, "reentry": obs & reentry}
    per_window: Dict[str, Dict[str, Dict[str, float]]] = {}
    for w in windows:
        per_window[str(w)] = {
            name: _overlap_rate(transition_df, surge, int(w), mask)
            for name, mask in masks.items()
        }
    primary = per_window[str(PRIMARY_WINDOW)]["pooled"]
    gate_pass = bool(np.isfinite(primary["rate"]) and primary["rate"] <= OVERLAP_CAP)
    return {
        "surge_n_keys": len(surge),
        "primary_window": PRIMARY_WINDOW,
        "cap": OVERLAP_CAP,
        "per_window": per_window,
        "primary_pooled_rate": primary["rate"],
        "gate_pass": gate_pass,
    }
