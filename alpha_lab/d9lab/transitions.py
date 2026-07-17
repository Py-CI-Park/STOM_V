"""D9 전이 온셋 검출 + L3 접목 (R1 일 단위 추출) — 봉인본 §3·§4·§14-5·§14-7·§14-8.

한 종목-일에서:
- 저장 `관심종목` 플래그(행 시퀀스, 09:00~09:30)의 **0→1 전이**를 온셋으로 잡는다
  (선두 flag=1 at pos0 포함) — 프로브 probe_min_d9 method.entry_event 정의 그대로.
- 신규진입 = 직전 flag=1 이력 없음(선두 포함). 재진입 = 직전 이탈(1→0) 있음.
- 관측가능 = 행 위치 ≥60(관심종목N(60) 클램프 규칙, §14-5). 미관측(<60)은 별도 bin.
- L3 라벨 = 봉인 pilot_v2._l3_labels 이중 세율 규약(§14-8, 발화 엔진 0.18% + 실현 연도 세율).
  h300(고정 300초, 연도 세율)을 보조 병기(§14-8, 채택 조건 아님).
- GT 패리티(§14-7): 저장 플래그(엔진-가시) vs moneytop 문자열 멤버십(offline GT) 행 단위
  일치. 관측가능 온셋 집합 일치율은 R1 리포트에서 판정(judge <99.9% → R3 진입 금지).

봉인 인프라 재사용(드리프트 금지): reader.load_stock_rows/connect_ro,
extract._moneytop_by_code/_load_dense/_hms_to_offset, pilot_v2._l3_labels/_h300_labels/
_offset_to_index/updown_quartile_v2, axes.time_bucket_offset/mktcap_bucket. 원본 read-only.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from alpha_lab.dataset import reader
from alpha_lab.dataset.labels_v2 import CHAMPION_SELL_SHA256
from alpha_lab.dataset.schema import as_float
from alpha_lab.stats_map import axes, config, extract, pilot_v2

logger = logging.getLogger(__name__)

__all__ = [
    "OBSERVABLE_MIN_POS",
    "TRANSITION_COLUMNS",
    "WINDOW_END_HMS",
    "WINDOW_START_HMS",
    "build_day_transitions",
    "classify_transitions",
]

# 관측가능 임계 — 행 위치 ≥60 이라야 관심종목N(60)이 실조회(클램프-0 아님, §14-5).
OBSERVABLE_MIN_POS = 60
WINDOW_START_HMS = 90000   # 09:00:00 — L3 창 시작(labels_v2.L3_WINDOW_START_HMS 정합).
WINDOW_END_HMS = 93000     # 09:30:00 — L3 강제 캡(labels_v2.L3_CAP_HMS 정합).
_W = config.WINDOW_SECONDS  # 1800.
_FLAG_COL = "관심종목"

# 전이 온셋 은행 컬럼(식별 + 서브모집단 + L3 + h300 보조).
TRANSITION_COLUMNS: Tuple[str, ...] = (
    "code", "day", "off", "t0", "year", "row_pos",
    "is_reentry", "observable", "gt_member",
    "updown_q", "mktcap_b", "time_b",
    "l3_net", "l3_labeled", "l3_clause", "l3_exit",
    "h300_net", "h300_valid",
)


def classify_transitions(flags: np.ndarray) -> Dict[str, np.ndarray]:
    """관심종목 플래그 행 시퀀스 → 0→1 전이 위치·재진입·관측가능 (프로브 정의 그대로).

    온셋 = f[i]==1 ∧ (i==0[선두] ∨ f[i-1]==0). 재진입 = i 이전에 f==1 이력 존재
    (직전 이탈 1→0 후 복귀). 신규진입 = 그 이력 없음(선두 flag=1 포함). 관측가능 =
    행 위치 ≥ OBSERVABLE_MIN_POS.

    Returns:
        {"pos": 온셋 행 위치(int64), "is_reentry": bool, "observable": bool}.
    """
    f = (np.asarray(flags, dtype=np.float64) > 0.5).astype(np.int8)
    n = f.size
    if n == 0:
        empty_i = np.empty(0, dtype=np.int64)
        empty_b = np.empty(0, dtype=bool)
        return {"pos": empty_i, "is_reentry": empty_b, "observable": empty_b}
    prev = np.concatenate(([0], f[:-1]))              # pos0 직전 = 0(선두 = 0→1 취급).
    onset = (f == 1) & (prev == 0)
    pos = np.flatnonzero(onset).astype(np.int64)
    # i 직전(strict)까지 f==1 이력 여부 = cummax 를 한 칸 시프트.
    ever_before = np.concatenate(([0], np.maximum.accumulate(f)[:-1]))
    is_reentry = ever_before[pos] == 1
    observable = pos >= OBSERVABLE_MIN_POS
    return {"pos": pos, "is_reentry": is_reentry, "observable": observable}


def _ordered_window_rows(
    rows: Dict[int, dict],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """{index: row} → 창[09:00,09:30] 행을 시각순 (idxs, flags, offsets)로 정렬.

    행 위치 = 이 정렬 순서(엔진 indexn 미러 — 창 시작 09:00:00 기준).
    """
    keys = sorted(
        t for t in rows
        if WINDOW_START_HMS <= int(t) % 1_000_000 <= WINDOW_END_HMS
    )
    if not keys:
        return (np.empty(0, np.int64), np.empty(0, np.float64), np.empty(0, np.int64))
    idxs = np.asarray(keys, dtype=np.int64)
    flags = np.array([as_float(rows[int(t)].get(_FLAG_COL)) for t in keys],
                     dtype=np.float64)
    offs = np.array([extract._hms_to_offset(int(t) % 1_000_000) for t in keys],
                    dtype=np.int64)
    return idxs, flags, offs


def _row_parity(offs: np.ndarray, flags: np.ndarray,
                uni_off: np.ndarray) -> Tuple[int, int]:
    """행 단위 저장 플래그 vs GT(오프셋∈uni_off) 일치 (n_match, n_rows) — 프로브 패리티."""
    if offs.size == 0:
        return 0, 0
    stored = flags > 0.5
    gt = np.isin(offs, uni_off)
    return int(np.count_nonzero(stored == gt)), int(offs.size)


def _code_transitions(
    conn, code: str, day: int, uni_off: np.ndarray, sell_text: str,
    *, spot_pure: bool,
) -> Tuple[Optional[Dict[str, np.ndarray]], Tuple[int, int]]:
    """한 종목의 전이 온셋 레코드 + 행 패리티 (n_match, n_rows). 온셋 0이면 (None, 패리티)."""
    rows = reader.load_stock_rows(conn, code)
    idxs, flags, offs = _ordered_window_rows(rows)
    parity = _row_parity(offs, flags, uni_off)
    if idxs.size == 0:
        return None, parity
    tr = classify_transitions(flags)
    pos = tr["pos"]
    if pos.size == 0:
        return None, parity
    onset_off = offs[pos]
    # L3 창·entry 정합: t0+1 ≤ 09:30:00 이라야 접목 가능 → off ≤ W-1.
    keep = onset_off <= (_W - 1)
    pos, onset_off = pos[keep], onset_off[keep]
    is_reentry = tr["is_reentry"][keep]
    observable = tr["observable"][keep]
    if pos.size == 0:
        return None, parity

    dense = extract._load_dense(conn, code)
    if dense is None:
        return None, parity
    entry_ask = dense["매도호가1"][onset_off + 1]
    t0_ints = [pilot_v2._offset_to_index(day, int(o)) for o in onset_off]
    year = day // 10000

    net_v, exit_v, _price_v, clause_v, lab_v = pilot_v2._l3_labels(
        rows, t0_ints, entry_ask, sell_text, "vector", year, CHAMPION_SELL_SHA256)
    h300_net, h300_valid, _cens = pilot_v2._h300_labels(dense, onset_off, year)

    m = pos.size
    gt_member = np.isin(onset_off, uni_off)
    rec: Dict[str, np.ndarray] = {
        "code": np.full(m, code, dtype="U6"),
        "day": np.full(m, day, dtype=np.int32),
        "off": onset_off.astype(np.int16),
        "t0": np.asarray(t0_ints, dtype=np.int64),
        "year": np.full(m, year, dtype=np.int16),
        "row_pos": pos.astype(np.int32),
        "is_reentry": is_reentry.astype(bool),
        "observable": observable.astype(bool),
        "gt_member": gt_member.astype(bool),
        "updown_q": pilot_v2.updown_quartile_v2(dense["등락율"][onset_off]).astype(np.int8),
        "mktcap_b": axes.mktcap_bucket(dense["시가총액"][onset_off]).astype(np.int8),
        "time_b": axes.time_bucket_offset(onset_off).astype(np.int8),
        "l3_net": net_v.astype(np.float64),
        "l3_labeled": lab_v.astype(bool),
        "l3_clause": clause_v.astype(np.int16),
        "l3_exit": exit_v.astype(np.int64),
        "h300_net": h300_net.astype(np.float64),
        "h300_valid": h300_valid.astype(bool),
    }
    if spot_pure:
        net_p, exit_p, _pp, _cp, lab_p = pilot_v2._l3_labels(
            rows, t0_ints, entry_ask, sell_text, "pure", year, CHAMPION_SELL_SHA256)
        rec["l3_net_pure"] = net_p.astype(np.float64)
        rec["l3_exit_pure"] = exit_p.astype(np.int64)
        rec["l3_labeled_pure"] = lab_p.astype(bool)
    return rec, parity


def build_day_transitions(
    db_path, date: str, sell_text: str, *, spot_pure: bool = False,
) -> Tuple[Dict[str, np.ndarray], Dict[str, int]]:
    """일 DB 하나의 전 종목 전이 온셋 은행 레코드 + 일 메타(패리티·서브모집단 카운트).

    Returns:
        (record, meta). record = 컬럼별 배열 dict(온셋 0이면 빈 배열).
        meta = {n_codes, parity_n_rows, parity_n_match, n_onsets, n_observable,
                n_new, n_reentry, n_labeled}.
    """
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        p_match = p_rows = 0
        for code in codes:
            rec, (nm, nr) = _code_transitions(
                conn, code, day, uni.get(code, np.empty(0, np.int64)),
                sell_text, spot_pure=spot_pure)
            p_match += nm
            p_rows += nr
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        rec = {k: np.asarray([]) for k in TRANSITION_COLUMNS}
        meta = {"n_codes": len(codes), "parity_n_rows": p_rows,
                "parity_n_match": p_match, "n_onsets": 0, "n_observable": 0,
                "n_new": 0, "n_reentry": 0, "n_labeled": 0}
        return rec, meta
    record = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0].keys()}
    obs = record["observable"]
    meta = {
        "n_codes": len(codes),
        "parity_n_rows": p_rows,
        "parity_n_match": p_match,
        "n_onsets": int(record["off"].size),
        "n_observable": int(obs.sum()),
        "n_new": int((obs & ~record["is_reentry"]).sum()),
        "n_reentry": int((obs & record["is_reentry"]).sum()),
        "n_labeled": int((obs & record["l3_labeled"]).sum()),
    }
    return record, meta
