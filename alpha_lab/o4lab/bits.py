"""O-4 신규 재도출 비트 산출 — 발견창 온셋 위 벡터 평가 (봉인본 §5.2·§14-F7).

D1 은행 빌드(clause_lab.bank._code_records)를 그대로 미러하되 **L3·39절 비트는 산출하지
않고** 재도출 임계 5종(grammar.NEW_BITS)만 온셋 시점 네임스페이스에서 평가한다:
  o4_netbuy_gt1  = 초당순매수금액 > 1.0        (F1, 원-절 상한 제거 단측)
  o4_qty_022/035/050 = 초당매수수량 > 매도총잔량 * {0.22,0.35,0.50}  (F4 재도출)
  o4_avoid_gap_lt8   = 시가등락율 < 8.0        (A 회피)

온셋 (code,day,off,t0) 는 D1 과 동일한 결정론 경로(pilot_v2._onset_offsets)로 재도출되므로
d1_onset_clause_bits.parquet 과 키-집합이 일치한다(gate.py 가 검증). 피처 재구성은
onset_features.build_onset_namespace(D1 P1) 그대로 — 신규 U-보류 심볼 없음(§14-F7 컬럼 확인).

산출: o4_candidate_bits.parquet(git 제외). 일별 체크포인트(parts/), 재시작 시 완료 일 건너뜀.
기존 비트(bit_4/10/16/17)는 재산출하지 않는다(d1 parquet 재사용). 원본 tick DB read-only.
엔진 백테 0회.
"""
from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.bank import DISCOVERY_END, DISCOVERY_START, day_list
from alpha_lab.clause_lab.onset_features import build_onset_namespace, load_window_frame
from alpha_lab.dataset import reader
from alpha_lab.o4lab.grammar import NEW_BITS
from alpha_lab.stats_map import extract, pilot_v2

logger = logging.getLogger(__name__)

__all__ = [
    "BIT_COLUMNS",
    "KEY_COLUMNS",
    "NEW_BIT_PREDICATES",
    "build_day_bits",
    "consolidate",
    "new_bit_masks",
    "run_bits",
]

KEY_COLUMNS: Tuple[str, ...] = ("code", "day", "off", "t0")
BIT_COLUMNS: Tuple[str, ...] = tuple(NEW_BITS.keys())


def _p_netbuy(ns):
    return ns["초당순매수금액"] > 1.0


def _p_qty(mult: float):
    return lambda ns: ns["초당매수수량"] > ns["매도총잔량"] * mult


def _p_avoid_gap(ns):
    return ns["시가등락율"] < 8.0


# threshold_id → 벡터 술어(온셋 네임스페이스 → bool 배열). RAW_EXPR 은 grammar.NEW_BITS.
NEW_BIT_PREDICATES = {
    "o4_netbuy_gt1": _p_netbuy,
    "o4_qty_022": _p_qty(0.22),
    "o4_qty_035": _p_qty(0.35),
    "o4_qty_050": _p_qty(0.50),
    "o4_avoid_gap_lt8": _p_avoid_gap,
}


def new_bit_masks(ns) -> Dict[str, np.ndarray]:
    """온셋 네임스페이스 → {threshold_id: bool 배열(만족)} — 신규 5비트."""
    return {tid: np.asarray(pred(ns), dtype=bool)
            for tid, pred in NEW_BIT_PREDICATES.items()}


def _code_records(conn, code: str, day: int, uni_off: np.ndarray
                  ) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 온셋 (식별 + 신규 5비트). 온셋 0 또는 창 부재면 None.

    온셋 경로는 clause_lab.bank._code_records 와 동일(pilot_v2) — 키 집합이 D1 과 일치.
    """
    dense = extract._load_dense(conn, code)
    if dense is None:
        return None
    onset_off = pilot_v2._onset_offsets(dense, uni_off)
    if onset_off.size == 0:
        return None
    t0_ints = [pilot_v2._offset_to_index(day, int(o)) for o in onset_off]
    loaded = load_window_frame(conn, code, day)
    if loaded is None:
        return None
    idx, df = loaded
    ns = build_onset_namespace(idx, df, t0_ints)
    masks = new_bit_masks(ns)

    m = onset_off.size
    rec: Dict[str, np.ndarray] = {
        "code": np.full(m, code, dtype="U6"),
        "day": np.full(m, day, dtype=np.int32),
        "off": onset_off.astype(np.int16),
        "t0": np.asarray(t0_ints, dtype=np.int64),
    }
    for tid in BIT_COLUMNS:
        rec[tid] = masks[tid].astype(bool)
    return rec


def build_day_bits(db_path, date: str) -> Dict[str, np.ndarray]:
    """일 DB 하나의 전 종목 온셋 신규 비트 레코드 — 결정론(clause_lab.bank 미러)."""
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            rec = _code_records(conn, code, day,
                                uni.get(code, np.empty(0, np.int64)))
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        keys = list(KEY_COLUMNS) + list(BIT_COLUMNS)
        return {k: np.asarray([]) for k in keys}
    return {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0].keys()}


def run_bits(
    db_dir, run_dir, parts_dir,
    *, days: Optional[Sequence[Tuple[str, Path]]] = None,
    progress_name: str = "o4_bits_progress.txt",
) -> Dict[str, object]:
    """발견창 일 루프 — 일별 parquet 체크포인트, 재시작 시 완료 일 건너뜀, 진행 로그."""
    parts = Path(parts_dir)
    parts.mkdir(parents=True, exist_ok=True)
    progress = Path(run_dir) / progress_name
    day_paths = list(days) if days is not None else day_list(db_dir)

    def log(msg: str) -> None:
        line = f"{datetime.now().isoformat()} {msg}"
        with open(progress, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.info(msg)

    log(f"O4-BITS start: {len(day_paths)} days ({DISCOVERY_START}~{DISCOVERY_END}) "
        f"parts={parts} bits={list(BIT_COLUMNS)}")
    t_all = time.monotonic()
    done, total = 0, 0
    for date, path in day_paths:
        part = parts / f"o4bits_{date}.parquet"
        if part.exists():
            done += 1
            total += int(pd.read_parquet(part, columns=["off"]).shape[0])
            continue
        t0 = time.monotonic()
        try:
            rec = build_day_bits(path, date)
            frame = pd.DataFrame({k: rec[k] for k in rec})
            tmp = parts / f"o4bits_{date}.tmp.parquet"
            frame.to_parquet(tmp, index=False)
            tmp.replace(part)
            done += 1
            total += int(frame.shape[0])
            rates = " ".join(f"{b}={int(frame[b].sum()) if frame.shape[0] else 0}"
                             for b in BIT_COLUMNS)
            log(f"  {date}: onsets={frame.shape[0]} {rates} "
                f"({time.monotonic()-t0:.1f}s) [{done}/{len(day_paths)}]")
        except Exception as exc:  # noqa: BLE001 — 정직 신고 후 계속(재시작 가능).
            log(f"  {date}: ERROR {exc!r}\n{traceback.format_exc()}")
    log(f"O4-BITS done: {done}/{len(day_paths)} days, onsets={total}, "
        f"{(time.monotonic()-t_all)/60:.1f} min")
    return {"days_done": done, "days_total": len(day_paths), "total_onsets": total}


def consolidate(parts_dir, bits_path) -> Dict[str, object]:
    """일별 parts → o4_candidate_bits.parquet(KEY + 신규 5비트). (code,day,off,t0) 유일성 assert."""
    parts = sorted(Path(parts_dir).glob("o4bits_*.parquet"))
    if not parts:
        raise FileNotFoundError(f"parts 없음: {parts_dir}")
    full = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    cols = list(KEY_COLUMNS) + list(BIT_COLUMNS)
    out = full[cols].copy()
    # dedup 키 (code,day,off,t0) 유일성(§5.2) — 중복이면 온셋 경로 결함.
    n_dup = int(out.duplicated(subset=list(KEY_COLUMNS)).sum())
    if n_dup:
        raise ValueError(f"온셋 키 중복 {n_dup}건 — (code,day,off,t0) 비유일(파이프라인 결함)")
    Path(bits_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(bits_path, index=False)
    sat = {b: int(out[b].sum()) for b in BIT_COLUMNS}
    return {
        "n_parts": len(parts), "n_onsets": int(out.shape[0]),
        "bits_path": str(bits_path), "bit_columns": list(BIT_COLUMNS),
        "satisfied_counts": sat,
    }
