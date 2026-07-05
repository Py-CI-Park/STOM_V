"""P3 MCL 피처 v1 — 봉인 동결표(F1~F11 × {5,10,30}s) 측정 구현 (research-only).

단일 원천: docs/research/condition_research/research_runs/alpha_lab_20260705/
p3_preregistration_v1.json 의 features.table (2026-07-06 봉인). 본 모듈은 그
동결표의 조작화이며, 식·윈도우 변경은 SealViolation — 새 봉인 + 새 n_trials
로만 가능하다. 통계는 여기 없다(스크리닝 통계는 alpha_lab.mcl.screening +
alpha_lab.stats_common 전용 — 재구현 금지 규율).

윈도우 규칙(봉인 window_rule 원문 조작화):
- W(t0,w) = [t0-w+1, t0] 구간의 '관측 초'(결측 초 제외).
- 관측 초 수 < max(2, ceil(w/2)) 이면 그 (피처,윈도우) 값은 NaN — 해당
  시행에서만 표본 결측 제외(screen_trials 의 n_missing 으로 정직 집계).
- 't0-w 초' 참조는 W 내 가장 이른 관측 초로 대체(봉인 원문).
- '[t0]' 참조는 W 내 가장 늦은 관측 초(t0 실관측 시 = t0 행)로 해석한다.
  봉인 원문은 t0-w 대체만 명시하므로 이 대칭 해석은 측정 노트로 공개한다
  (영수증 measurement_notes 필수 기재).
- 순간형(F6/F7/F8/F10)은 t0 행만 사용 — t0 행 결측 시 NaN.

값 강제는 dataset.schema.as_float(None→0.0) — 리더/라벨과 동일 규약.
시각 산술은 events.detectors.ts_shift(datetime 파싱 — 분·시 롤오버 정확).
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from alpha_lab.dataset.schema import as_float
from alpha_lab.events.detectors import ts_shift

__all__ = [
    "INSTANT_IDS",
    "N_SEALED_COMBOS",
    "WINDOWED_IDS",
    "WINDOWS_SEC",
    "compute_features",
    "feature_key",
    "min_window_obs",
    "sealed_feature_specs",
]

logger = logging.getLogger(__name__)

WINDOWED_IDS: Tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F9", "F11")
INSTANT_IDS: Tuple[str, ...] = ("F6", "F7", "F8", "F10")
WINDOWS_SEC: Tuple[int, ...] = (5, 10, 30)
N_SEALED_COMBOS = 25  # 윈도우형 7×3 + 순간형 4 (봉인 n_combos).

_NAN = float("nan")


def feature_key(feature_id: str, window_sec: Optional[int]) -> str:
    """(피처 id, 윈도우) → 시행 피처 키 — 'F1_w5' / 순간형은 'F6'."""
    if window_sec is None:
        return str(feature_id)
    return f"{feature_id}_w{int(window_sec)}"


def min_window_obs(window_sec: int) -> int:
    """봉인 최소 관측 초 수 = max(2, ceil(w/2))."""
    return max(2, math.ceil(int(window_sec) / 2))


def sealed_feature_specs(table: Sequence[Mapping]) -> List[Dict[str, object]]:
    """봉인 features.table → 검증된 스펙 목록(봉인 순서 그대로).

    각 스펙 = {key, id, name, kind, window_sec}. 검증: id 는 구현된
    WINDOWED_IDS/INSTANT_IDS 안에 있어야 하고, 윈도우형은 window_sec ∈
    {5,10,30}, 순간형은 window_sec 부재(None). 총 25조합·키 중복 금지 —
    위반은 봉인-구현 드리프트이므로 ValueError(측정 착수 금지).
    """
    specs: List[Dict[str, object]] = []
    seen: set = set()
    for entry in table:
        fid = str(entry.get("id"))
        kind = str(entry.get("kind"))
        window = entry.get("window_sec")
        if kind == "windowed":
            if fid not in WINDOWED_IDS:
                raise ValueError(f"봉인 윈도우형 id 미구현: {fid}")
            if int(window) not in WINDOWS_SEC:
                raise ValueError(f"봉인 외 윈도우: {fid} w={window}")
            window_sec: Optional[int] = int(window)
        elif kind == "instant":
            if fid not in INSTANT_IDS:
                raise ValueError(f"봉인 순간형 id 미구현: {fid}")
            if window is not None:
                raise ValueError(f"순간형에 윈도우 지정: {fid} w={window}")
            window_sec = None
        else:
            raise ValueError(f"알 수 없는 kind: {fid} {kind!r}")
        key = feature_key(fid, window_sec)
        if key in seen:
            raise ValueError(f"봉인 표 키 중복: {key}")
        seen.add(key)
        specs.append({
            "key": key,
            "id": fid,
            "name": str(entry.get("name", "")),
            "kind": kind,
            "window_sec": window_sec,
        })
    if len(specs) != N_SEALED_COMBOS:
        raise ValueError(f"봉인 조합 수 불일치: {len(specs)} != {N_SEALED_COMBOS}")
    return specs


# ---------------------------------------------------------------------------
# 관측 창 수집.
# ---------------------------------------------------------------------------
def _window_rows(
    rows: Mapping[int, Mapping], t0: int, window_sec: int
) -> List[Mapping]:
    """W(t0,w) = [t0-w+1, t0] 의 관측 초 행들(시각 오름차순)."""
    out: List[Mapping] = []
    for back in range(int(window_sec) - 1, -1, -1):
        row = rows.get(ts_shift(int(t0), -back))
        if row is not None:
            out.append(row)
    return out


def _sum(obs: Sequence[Mapping], column: str) -> float:
    return float(sum(as_float(row.get(column)) for row in obs))


def _mean(obs: Sequence[Mapping], column: str) -> float:
    return _sum(obs, column) / float(len(obs))


def _far_sum(row: Mapping) -> float:
    """F11 원거리합 = 매도잔량2+매도잔량3+매도잔량4+매도잔량5 (봉인식)."""
    return float(sum(
        as_float(row.get(name))
        for name in ("매도잔량2", "매도잔량3", "매도잔량4", "매도잔량5")
    ))


# ---------------------------------------------------------------------------
# 봉인식 — 윈도우형 7종. earliest = W 내 가장 이른 관측 초('t0-w' 대체 규칙),
# latest = W 내 가장 늦은 관측 초('[t0]' 참조 해석 — 모듈 독스트링 공개).
# ---------------------------------------------------------------------------
def _windowed_value(feature_id: str, obs: Sequence[Mapping]) -> float:
    earliest, latest = obs[0], obs[-1]
    if feature_id == "F1":
        buy, sell = _sum(obs, "초당매수수량"), _sum(obs, "초당매도수량")
        return (buy - sell) / max(buy + sell, 1.0)
    if feature_id == "F2":
        buy, sell = _sum(obs, "초당매수금액"), _sum(obs, "초당매도금액")
        return (buy - sell) / max(buy + sell, 1.0)
    if feature_id == "F3":
        total = 0.0
        for row in obs:
            bid_total = as_float(row.get("매수총잔량"))
            ask_total = as_float(row.get("매도총잔량"))
            total += (bid_total - ask_total) / max(bid_total + ask_total, 1.0)
        return total / float(len(obs))
    if feature_id == "F4":
        d_bid = as_float(latest.get("매수잔량1")) - as_float(earliest.get("매수잔량1"))
        d_ask = as_float(latest.get("매도잔량1")) - as_float(earliest.get("매도잔량1"))
        denom = as_float(latest.get("매수총잔량")) + as_float(latest.get("매도총잔량"))
        return (d_bid - d_ask) / max(denom, 1.0)
    if feature_id == "F5":
        return _sum(obs, "초당매수수량") / max(_mean(obs, "매도잔량1"), 1.0)
    if feature_id == "F9":
        return as_float(latest.get("체결강도")) - as_float(earliest.get("체결강도"))
    if feature_id == "F11":
        far_max = max(_far_sum(row) for row in obs)
        return (far_max - _far_sum(latest)) / max(far_max, 1.0)
    raise ValueError(f"미구현 윈도우형 피처: {feature_id}")


# ---------------------------------------------------------------------------
# 봉인식 — 순간형 4종(t0 행만).
# ---------------------------------------------------------------------------
def _instant_value(feature_id: str, row: Mapping) -> float:
    if feature_id == "F6":
        near = as_float(row.get("매수잔량1")) + as_float(row.get("매도잔량1"))
        total = as_float(row.get("매수총잔량")) + as_float(row.get("매도총잔량"))
        return near / max(total, 1.0)
    if feature_id == "F7":
        spread = as_float(row.get("매도호가1")) - as_float(row.get("매수호가1"))
        return spread / max(as_float(row.get("현재가")), 1.0)
    if feature_id == "F8":
        return as_float(row.get("라운드피겨위5호가이내"))
    if feature_id == "F10":
        vi_price = as_float(row.get("VI가격"))
        if vi_price > 0.0:
            return as_float(row.get("현재가")) / vi_price - 1.0
        return 0.0
    raise ValueError(f"미구현 순간형 피처: {feature_id}")


def compute_features(
    rows: Mapping[int, Mapping], t0: int, specs: Sequence[Mapping]
) -> Dict[str, float]:
    """진입 t0 의 봉인 피처 25종 계산 — {키: 값(결측은 NaN)}.

    Args:
        rows: {int YYYYMMDDHHMMSS: 행 dict} — dataset.reader.load_stock_rows.
        t0: 진입 신호 초(int YYYYMMDDHHMMSS).
        specs: sealed_feature_specs 반환 목록(봉인 순서).

    Returns:
        스펙 순서를 보존하는 {feature_key: float}. 윈도우형은 관측 초 수
        미달 시 NaN, 순간형은 t0 행 결측 시 NaN — 보간·이월 없음(봉인
        결측 정책: 결측 초 = 그 초 미관측).
    """
    window_cache: Dict[int, List[Mapping]] = {}
    t0_row = rows.get(int(t0))
    out: Dict[str, float] = {}
    for spec in specs:
        fid, window_sec = str(spec["id"]), spec["window_sec"]
        if window_sec is None:
            value = _instant_value(fid, t0_row) if t0_row is not None else _NAN
        else:
            w = int(window_sec)
            if w not in window_cache:
                window_cache[w] = _window_rows(rows, int(t0), w)
            obs = window_cache[w]
            value = (
                _windowed_value(fid, obs)
                if len(obs) >= min_window_obs(w) else _NAN
            )
        out[str(spec["key"])] = float(value)
    return out
