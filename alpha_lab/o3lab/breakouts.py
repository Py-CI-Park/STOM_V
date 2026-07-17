"""O-3 돌파 온셋 일 단위 추출 + L3 접목 — 봉인본 §3·§6 (transitions.py 미러).

한 종목-일에서 5변형(detect.VARIANTS) 각각의 돌파 온셋을 잡아:
- 유니버스(관심종목=1≡moneytop)·entry(t0+1 매도호가1>0) 필터(서지 경로 정합).
- L3 라벨 = **봉인 pilot_v2._l3_labels 벡터 경로**(발화 = 엔진 0.18% 의미론
  labels_v2.build_l3_labels, 실현 = 연도 세율 재계상 costs_v2, §14-8 이중 규약).
  raw build_l3_labels 직사용 금지(F6 봉인) — 래퍼만.
- h300(고정 300초, 연도 세율) 보조 병기(pilot_v2._h300_labels, 채택 조건 아님).
- 축 = 시간대(time_b)·등락율 분위(updown_q v2 경계)·시총(mktcap_b)·시가갭(gap_b,
  O-1G 경계 — 서술 분해용).

서지 겹침(±30초 서지-비중첩 모집단)·유형간 중복 매트릭스·G4 서지 정확일치 L3 대조는
추출이 아니라 판정/게이트 단계(run.py)에서 서지 은행(onset_l3_bank.parquet) 대비
산출한다 — 추출은 원본 tick DB read-only 결정론만 유지(서지 은행 비의존).

봉인 인프라 재사용(드리프트 금지): detect.load_dense_o3/breakout_onset_offsets,
pilot_v2._l3_labels/_h300_labels/_offset_to_index/updown_quartile_v2,
axes.time_bucket_offset/mktcap_bucket, gap_o1g.gap_percent/gap_bucket. 원본 read-only.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from alpha_lab.dataset import reader
from alpha_lab.dataset.labels_v2 import CHAMPION_SELL_SHA256
from alpha_lab.o3lab import detect
from alpha_lab.stats_map import axes, extract, gap_o1g, pilot_v2

logger = logging.getLogger(__name__)

__all__ = ["BREAKOUT_COLUMNS", "build_day_breakouts"]

# 돌파 온셋 은행 컬럼(식별 + 변형 + 축 + L3 + h300 보조). variant 는 dedup 키 성분(F5).
BREAKOUT_COLUMNS: Tuple[str, ...] = (
    "code", "day", "off", "t0", "year", "variant",
    "updown_q", "mktcap_b", "time_b", "gap_b",
    "l3_net", "l3_labeled", "l3_clause", "l3_exit",
    "h300_net", "h300_valid",
)


def _code_breakouts(
    conn, code: str, day: int, uni_off: np.ndarray, sell_text: str,
    *, spot_pure: bool,
) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 전 변형 돌파 온셋 레코드(식별+변형+축+L3+h300). 온셋 0이면 None."""
    dense = detect.load_dense_o3(conn, code)
    if dense is None:
        return None
    present, ask = dense["present"], dense["매도호가1"]
    year = day // 10000
    rows = None
    gap_all: Optional[np.ndarray] = None
    parts: List[Dict[str, np.ndarray]] = []

    for variant in detect.VARIANTS:
        onset_off = detect.breakout_onset_offsets(dense, variant, day)
        if onset_off.size == 0:
            continue
        # 유니버스·entry 필터(서지 pilot_v2._onset_offsets 정합 — cross+쿨다운 후 적용).
        in_uni = np.isin(onset_off, uni_off)
        entry_ok = present[onset_off + 1] & (ask[onset_off + 1] > 0.0)
        onset_off = onset_off[in_uni & entry_ok]
        if onset_off.size == 0:
            continue

        if rows is None:
            rows = reader.load_stock_rows(conn, code)
        if gap_all is None:
            gap_all, _valid = gap_o1g.gap_percent(
                dense["현재가"], dense["등락율"], dense["시가"])

        entry_ask = ask[onset_off + 1]
        t0_ints = [pilot_v2._offset_to_index(day, int(o)) for o in onset_off]
        net_v, exit_v, _price_v, clause_v, lab_v = pilot_v2._l3_labels(
            rows, t0_ints, entry_ask, sell_text, "vector", year, CHAMPION_SELL_SHA256)
        h300_net, h300_valid, _cens = pilot_v2._h300_labels(dense, onset_off, year)

        m = onset_off.size
        rec: Dict[str, np.ndarray] = {
            "code": np.full(m, code, dtype="U6"),
            "day": np.full(m, day, dtype=np.int32),
            "off": onset_off.astype(np.int16),
            "t0": np.asarray(t0_ints, dtype=np.int64),
            "year": np.full(m, year, dtype=np.int16),
            "variant": np.full(m, variant, dtype="U4"),
            "updown_q": pilot_v2.updown_quartile_v2(
                dense["등락율"][onset_off]).astype(np.int8),
            "mktcap_b": axes.mktcap_bucket(dense["시가총액"][onset_off]).astype(np.int8),
            "time_b": axes.time_bucket_offset(onset_off).astype(np.int8),
            "gap_b": gap_o1g.gap_bucket(gap_all[onset_off]).astype(np.int8),
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
        parts.append(rec)

    if not parts:
        return None
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0].keys()}


def _variant_meta(rec: Dict[str, np.ndarray]) -> Dict[str, Dict[str, int]]:
    """레코드 → 변형별 온셋/라벨/연도 카운트(자격 census — L3 분포 미관측)."""
    out: Dict[str, Dict[str, int]] = {}
    if not rec or rec["off"].size == 0:
        return {v: {"n": 0, "n_labeled": 0, "n_2022": 0, "n_2023": 0}
                for v in detect.VARIANTS}
    variant = rec["variant"]
    lab = rec["l3_labeled"].astype(bool)
    year = rec["year"]
    for v in detect.VARIANTS:
        m = variant == v
        out[v] = {
            "n": int(m.sum()),
            "n_labeled": int((m & lab).sum()),
            "n_2022": int((m & (year == 2022)).sum()),
            "n_2023": int((m & (year == 2023)).sum()),
        }
    return out


def build_day_breakouts(
    db_path, date: str, sell_text: str, *, spot_pure: bool = False,
) -> Tuple[Dict[str, np.ndarray], Dict[str, object]]:
    """일 DB 하나의 전 종목 돌파 온셋 은행 레코드 + 일 메타(변형별 census).

    Returns:
        (record, meta). record = 컬럼별 배열 dict(온셋 0이면 빈 배열).
        meta = {n_codes, n_onsets, per_variant{v: {n, n_labeled, n_2022, n_2023}}}.
    """
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            rec = _code_breakouts(
                conn, code, day, uni.get(code, np.empty(0, np.int64)),
                sell_text, spot_pure=spot_pure)
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        empty = {k: np.asarray([]) for k in BREAKOUT_COLUMNS}
        meta = {"n_codes": len(codes), "n_onsets": 0,
                "per_variant": _variant_meta({})}
        return empty, meta
    record = {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0].keys()}
    meta = {
        "n_codes": len(codes),
        "n_onsets": int(record["off"].size),
        "per_variant": _variant_meta(record),
    }
    return record, meta
