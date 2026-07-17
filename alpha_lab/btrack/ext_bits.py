"""B-ext 신규 비트 산출 — 확정 신규 절만, 발견창 온셋 위 벡터 술어 (봉인본 §5·O-4 bits.py 미러).

선정(ext_select)이 확정한 신규 절(ext_id → (canonical, negated))을 compile_clause 로 벡터 술어화해
발견창 온셋 (code,day,off,t0) 위에서 평가한다(D1 P1 네임스페이스 재사용). 기존 39비트는 산출하지
않는다(d1 parquet 재사용). 일자 체크포인트 parts. 산출 `stats_map/btrack_ext_bits.parquet`
(dedup (code,day,off,t0), ext_* 컬럼, git 제외). 원본 tick DB read-only. 엔진 0회.
"""
from __future__ import annotations

import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.btrack.ext_parse import ClauseInfo, compile_clause
from alpha_lab.clause_lab.bank import DISCOVERY_END, DISCOVERY_START, day_list
from alpha_lab.clause_lab.onset_features import build_onset_namespace, load_window_frame
from alpha_lab.dataset import reader
from alpha_lab.stats_map import extract, pilot_v2

logger = logging.getLogger(__name__)

__all__ = [
    "KEY_COLUMNS", "build_day_bits", "compile_ext_predicates", "consolidate",
    "ext_bit_masks", "run_bits",
]

KEY_COLUMNS: Tuple[str, ...] = ("code", "day", "off", "t0")


def compile_ext_predicates(new_bit_defs: Mapping[str, Tuple[str, bool]]) -> Dict[str, ClauseInfo]:
    """{ext_id: (canonical, negated)} → {ext_id: ClauseInfo}(전부 evaluable assert)."""
    out: Dict[str, ClauseInfo] = {}
    for bid, (canon, negated) in new_bit_defs.items():
        ci = compile_clause(canon, negated=bool(negated))
        if not ci.evaluable:
            raise ValueError(f"신규 비트 {bid} 컴파일 불가: {canon!r} ({ci.reason})")
        out[bid] = ci
    return out


def ext_bit_masks(ns: Mapping[str, np.ndarray], predicates: Mapping[str, ClauseInfo]
                  ) -> Dict[str, np.ndarray]:
    """온셋 네임스페이스 → {ext_id: bool 배열}."""
    return {bid: np.asarray(ci.predicate(ns), dtype=bool) for bid, ci in predicates.items()}


def _code_records(conn, code: str, day: int, uni_off: np.ndarray,
                  predicates: Mapping[str, ClauseInfo]) -> Optional[Dict[str, np.ndarray]]:
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
    masks = ext_bit_masks(ns, predicates)
    m = onset_off.size
    rec: Dict[str, np.ndarray] = {
        "code": np.full(m, code, dtype="U6"), "day": np.full(m, day, dtype=np.int32),
        "off": onset_off.astype(np.int16), "t0": np.asarray(t0_ints, dtype=np.int64),
    }
    for bid in predicates:
        rec[bid] = masks[bid].astype(bool)
    return rec


def build_day_bits(db_path, date: str, predicates: Mapping[str, ClauseInfo]
                   ) -> Dict[str, np.ndarray]:
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            rec = _code_records(conn, code, day, uni.get(code, np.empty(0, np.int64)), predicates)
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        keys = list(KEY_COLUMNS) + list(predicates.keys())
        return {k: np.asarray([]) for k in keys}
    return {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0].keys()}


def run_bits(db_dir, run_dir, parts_dir, predicates: Mapping[str, ClauseInfo],
             *, days: Optional[Sequence[Tuple[str, Path]]] = None,
             progress_name: str = "b_ext_bits_progress.txt") -> Dict[str, object]:
    parts = Path(parts_dir)
    parts.mkdir(parents=True, exist_ok=True)
    progress = Path(run_dir) / progress_name
    day_paths = list(days) if days is not None else day_list(db_dir)
    bit_cols = list(predicates.keys())

    def log(msg: str) -> None:
        with open(progress, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
        logger.info(msg)

    log(f"B-EXT-BITS start: {len(day_paths)} days ({DISCOVERY_START}~{DISCOVERY_END}) "
        f"n_ext={len(bit_cols)} parts={parts}")
    t_all = time.monotonic()
    done, total = 0, 0
    for date, path in day_paths:
        part = parts / f"b_ext_bits_{date}.parquet"
        if part.exists():
            done += 1
            total += int(pd.read_parquet(part, columns=["off"]).shape[0])
            continue
        t0 = time.monotonic()
        try:
            rec = build_day_bits(path, date, predicates)
            frame = pd.DataFrame({k: rec[k] for k in rec})
            tmp = parts / f"b_ext_bits_{date}.tmp.parquet"
            frame.to_parquet(tmp, index=False)
            tmp.replace(part)
            done += 1
            total += int(frame.shape[0])
            log(f"  {date}: onsets={frame.shape[0]} ({time.monotonic()-t0:.1f}s) [{done}/{len(day_paths)}]")
        except Exception as exc:  # noqa: BLE001 — 정직 신고 후 계속(재시작 가능).
            log(f"  {date}: ERROR {exc!r}\n{traceback.format_exc()}")
    log(f"B-EXT-BITS done: {done}/{len(day_paths)} days, onsets={total}, "
        f"{(time.monotonic()-t_all)/60:.1f} min")
    return {"days_done": done, "days_total": len(day_paths), "total_onsets": total}


def consolidate(parts_dir, bits_path, bit_cols: Sequence[str]) -> Dict[str, object]:
    parts = sorted(Path(parts_dir).glob("b_ext_bits_*.parquet"))
    if not parts:
        raise FileNotFoundError(f"parts 없음: {parts_dir}")
    full = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    cols = list(KEY_COLUMNS) + list(bit_cols)
    out = full[cols].copy()
    n_dup = int(out.duplicated(subset=list(KEY_COLUMNS)).sum())
    if n_dup:
        raise ValueError(f"온셋 키 중복 {n_dup}건 — (code,day,off,t0) 비유일")
    Path(bits_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(bits_path, index=False)
    return {"n_parts": len(parts), "n_onsets": int(out.shape[0]),
            "bits_path": str(bits_path), "bit_columns": list(bit_cols),
            "satisfied_counts": {b: int(out[b].sum()) for b in bit_cols}}
