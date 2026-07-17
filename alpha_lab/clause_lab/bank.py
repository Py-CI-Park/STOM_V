"""온셋 L3 은행 + 절 비트 재산출 — 일 단위 체크포인트·재시작 가능 (사전등록 §5·§13-F1).

발견창(2022-03-23~2023-12-31) 437일의 L1 서지 온셋(2.0×·쿨다운 30초)에:
- L3 = labels_v2 벡터 경로 챔피언 출구 반사실 실현 순손익(연도 세율, sell_sha 8ef01e0e).
  봉인 v2a 인프라(pilot_v2._onset_offsets/_l3_labels, extract._load_dense) 그대로 재사용
  → L3 값이 stats_map v2a 와 동일. 여기에 종목코드를 보존하고 절 비트를 추가한다.
- 절 비트 = onset_features.build_onset_namespace + clauses.evaluate_clause_bits(39절).

산출: onset_l3_bank.parquet(F1 출구 은행 자산) + d1_onset_clause_bits.parquet(D1 파티션).
둘 다 git 제외. 일별 체크포인트(parts/), 재시작 시 완료 일 건너뜀, 진행 로그.

원본 tick DB read-only. 엔진 백테 0회.
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

from alpha_lab.clause_lab.clauses import CLAUSE_SPECS, evaluate_clause_bits
from alpha_lab.clause_lab.onset_features import build_onset_namespace, load_window_frame
from alpha_lab.dataset import reader
from alpha_lab.dataset.labels_v2 import CHAMPION_SELL_SHA256, load_champion_sell_expr, verify_sell_expr
from alpha_lab.dataset.schema import as_float
from alpha_lab.stats_map import axes, config_v2, extract, pilot_v2

logger = logging.getLogger(__name__)

__all__ = [
    "BANK_COLUMNS",
    "build_day_bank",
    "champion_sell_text",
    "consolidate",
    "day_list",
    "run_bank",
    "spot_reproduction_check",
]

DISCOVERY_START, DISCOVERY_END = "20220323", "20231231"

# 은행 식별 컬럼 + L3 + 축(절 비트는 bit_1..bit_39 로 별도 추가).
BANK_COLUMNS: Tuple[str, ...] = (
    "code", "day", "off", "t0", "year", "updown_q", "mktcap_b", "time_b",
    "l3_net", "l3_labeled", "l3_clause", "l3_exit",
)


def champion_sell_text(strategy_db_path) -> str:
    """챔피언 현직 매도식 원문 로드 + sha 봉인 검증(labels_v2 재사용)."""
    text = load_champion_sell_expr(strategy_db_path)
    verify_sell_expr(text, CHAMPION_SELL_SHA256)
    return text


def day_list(db_dir, start: str = DISCOVERY_START, end: str = DISCOVERY_END
             ) -> List[Tuple[str, Path]]:
    """발견창 일 DB 목록(날짜순) — run_full_extract.days 와 동일 규약."""
    out: List[Tuple[str, Path]] = []
    for p in sorted(Path(db_dir).glob("stock_tick_*.db")):
        d = p.name[len("stock_tick_"):-len(".db")]
        if len(d) == 8 and d.isdigit() and start <= d <= end:
            out.append((d, p))
    return out


def _code_records(
    conn, code: str, day: int, uni_off: np.ndarray, sell_text: str,
    *, spot_pure: bool,
) -> Optional[Dict[str, np.ndarray]]:
    """한 종목의 온셋 레코드(식별+L3 벡터+절 비트). 온셋 0 또는 창 부재면 None.

    L3·온셋은 봉인 pilot_v2 경로 그대로(값 동일 보장). spot_pure=True 면 순수 경로 L3 도
    산출해 재현 게이트/스팟 재검용 컬럼을 덧붙인다.
    """
    dense = extract._load_dense(conn, code)
    if dense is None:
        return None
    onset_off = pilot_v2._onset_offsets(dense, uni_off)
    if onset_off.size == 0:
        return None
    year = day // 10000
    entry_ask = dense["매도호가1"][onset_off + 1]
    t0_ints = [pilot_v2._offset_to_index(day, int(o)) for o in onset_off]
    rows = reader.load_stock_rows(conn, code)

    net_v, exit_v, _price_v, clause_v, lab_v = pilot_v2._l3_labels(
        rows, t0_ints, entry_ask, sell_text, "vector", year, CHAMPION_SELL_SHA256)

    # 절 비트 — 창 프레임 + 온셋 index.
    loaded = load_window_frame(conn, code, day)
    if loaded is None:
        return None
    idx, df = loaded
    ns = build_onset_namespace(idx, df, t0_ints)
    bits = evaluate_clause_bits(ns)

    m = onset_off.size
    rec: Dict[str, np.ndarray] = {
        "code": np.full(m, code, dtype="U6"),
        "day": np.full(m, day, dtype=np.int32),
        "off": onset_off.astype(np.int16),
        "t0": np.asarray(t0_ints, dtype=np.int64),
        "year": np.full(m, year, dtype=np.int16),
        "updown_q": pilot_v2.updown_quartile_v2(dense["등락율"][onset_off]).astype(np.int8),
        "mktcap_b": axes.mktcap_bucket(dense["시가총액"][onset_off]).astype(np.int8),
        "time_b": axes.time_bucket_offset(onset_off).astype(np.int8),
        "l3_net": net_v.astype(np.float64),
        "l3_labeled": lab_v.astype(bool),
        "l3_clause": clause_v.astype(np.int16),
        "l3_exit": exit_v.astype(np.int64),
    }
    for spec in CLAUSE_SPECS:
        rec[f"bit_{spec.num}"] = bits[spec.num].astype(bool)
    if spot_pure:
        net_p, exit_p, _pp, _cp, lab_p = pilot_v2._l3_labels(
            rows, t0_ints, entry_ask, sell_text, "pure", year, CHAMPION_SELL_SHA256)
        rec["l3_net_pure"] = net_p.astype(np.float64)
        rec["l3_exit_pure"] = exit_p.astype(np.int64)
        rec["l3_labeled_pure"] = lab_p.astype(bool)
    return rec


def build_day_bank(
    db_path, date: str, sell_text: str, *, spot_pure: bool = False,
) -> Dict[str, np.ndarray]:
    """일 DB 하나의 전 종목 온셋 은행 레코드(식별+L3+절 비트) — 결정론."""
    conn = reader.connect_ro(Path(db_path))
    try:
        uni = extract._moneytop_by_code(conn)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        codes = [n for (n,) in cur if n.isdigit() and len(n) == 6]
        day = int(date)
        chunks: List[Dict[str, np.ndarray]] = []
        for code in codes:
            rec = _code_records(
                conn, code, day, uni.get(code, np.empty(0, np.int64)),
                sell_text, spot_pure=spot_pure)
            if rec is not None:
                chunks.append(rec)
    finally:
        conn.close()
    if not chunks:
        keys = list(BANK_COLUMNS) + [f"bit_{s.num}" for s in CLAUSE_SPECS]
        return {k: np.asarray([]) for k in keys}
    return {k: np.concatenate([c[k] for c in chunks]) for k in chunks[0].keys()}


def _to_frame(rec: Dict[str, np.ndarray]) -> pd.DataFrame:
    return pd.DataFrame({k: rec[k] for k in rec})


def run_bank(
    db_dir, run_dir, parts_dir, sell_text: str,
    *, spot_days: Sequence[str] = (), progress_name: str = "d1_progress.txt",
) -> Dict[str, object]:
    """437일 루프 — 일별 parquet 체크포인트, 재시작 시 완료 일 건너뜀, 진행 로그.

    spot_days 는 순수 경로도 산출(재현 게이트·스팟 재검용). 반환: 요약 dict.
    """
    parts = Path(parts_dir)
    parts.mkdir(parents=True, exist_ok=True)
    progress = Path(run_dir) / progress_name
    spot = set(spot_days)

    def log(msg: str) -> None:
        line = f"{datetime.now().isoformat()} {msg}"
        with open(progress, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.info(msg)

    days = day_list(db_dir)
    log(f"D1-BANK start: {len(days)} days ({DISCOVERY_START}~{DISCOVERY_END}) "
        f"parts={parts} spot_days={sorted(spot)}")
    t_all = time.monotonic()
    done, total_onsets = 0, 0
    for date, path in days:
        part = parts / f"bank_{date}.parquet"
        if part.exists():
            done += 1
            total_onsets += int(pd.read_parquet(part, columns=["off"]).shape[0])
            continue
        t0 = time.monotonic()
        try:
            rec = build_day_bank(path, date, sell_text, spot_pure=(date in spot))
            frame = _to_frame(rec)
            tmp = parts / f"bank_{date}.tmp.parquet"
            frame.to_parquet(tmp, index=False)
            tmp.replace(part)
            done += 1
            total_onsets += int(frame.shape[0])
            log(f"  {date}: onsets={frame.shape[0]} labeled={int(frame['l3_labeled'].sum())} "
                f"({time.monotonic()-t0:.1f}s) [{done}/{len(days)}]")
        except Exception as exc:  # noqa: BLE001 — 정직 신고 후 계속(재시작 가능).
            log(f"  {date}: ERROR {exc!r}\n{traceback.format_exc()}")
    log(f"D1-BANK done: {done}/{len(days)} days, onsets={total_onsets}, "
        f"{(time.monotonic()-t_all)/60:.1f} min")
    return {"days_done": done, "days_total": len(days), "total_onsets": total_onsets}


def consolidate(parts_dir, bank_path, bits_path) -> Dict[str, object]:
    """일별 parts → onset_l3_bank.parquet(식별+L3+축) + d1_onset_clause_bits.parquet(비트).

    두 파일은 행 순서가 동일(같은 parts 순서 concat)해 위치로 조인된다. 반환: 요약.
    """
    parts = sorted(Path(parts_dir).glob("bank_*.parquet"))
    if not parts:
        raise FileNotFoundError(f"parts 없음: {parts_dir}")
    frames = [pd.read_parquet(p) for p in parts]
    full = pd.concat(frames, ignore_index=True)
    bit_cols = [f"bit_{s.num}" for s in CLAUSE_SPECS]
    # 스팟 일의 순수-경로 컬럼(l3_*_pure)은 은행에서 제외(명시 컬럼만).
    bank = full[list(BANK_COLUMNS)].copy()
    bits = full[["code", "day", "off", "t0"] + bit_cols].copy()
    Path(bank_path).parent.mkdir(parents=True, exist_ok=True)
    bank.to_parquet(bank_path, index=False)
    bits.to_parquet(bits_path, index=False)
    return {
        "n_parts": len(parts), "n_onsets": int(full.shape[0]),
        "n_labeled": int(full["l3_labeled"].sum()),
        "bank_path": str(bank_path), "bits_path": str(bits_path),
    }


def spot_reproduction_check(parts_dir, spot_days: Sequence[str]) -> Dict[str, object]:
    """임의 2일 순수 경로 스팟 재검 — 벡터 L3 vs 순수 L3 청산시각·net 일치(재현 게이트).

    스팟 일 parts 는 build_day_bank(spot_pure=True) 로 l3_*_pure 컬럼을 담는다.
    """
    out: Dict[str, object] = {"spot_days": list(spot_days), "per_day": []}
    all_pass = True
    for date in spot_days:
        p = Path(parts_dir) / f"bank_{date}.parquet"
        if not p.exists():
            out["per_day"].append({"day": date, "status": "part_missing"})
            all_pass = False
            continue
        d = pd.read_parquet(p)
        if "l3_net_pure" not in d.columns:
            out["per_day"].append({"day": date, "status": "no_pure_columns"})
            all_pass = False
            continue
        both = d["l3_labeled"].to_numpy().astype(bool) & d["l3_labeled_pure"].to_numpy().astype(bool)
        net_v = d["l3_net"].to_numpy(dtype=np.float64)[both]
        net_p = d["l3_net_pure"].to_numpy(dtype=np.float64)[both]
        exit_v = d["l3_exit"].to_numpy(dtype=np.int64)[both]
        exit_p = d["l3_exit_pure"].to_numpy(dtype=np.int64)[both]
        net_err = float(np.max(np.abs(net_v - net_p))) if both.any() else 0.0
        exit_match = float(np.mean(exit_v == exit_p)) if both.any() else 1.0
        day_pass = bool(net_err <= 1e-12 and exit_match >= 0.999)
        all_pass = all_pass and day_pass
        out["per_day"].append({
            "day": date, "n_paired": int(both.sum()),
            "net_max_abs_err": net_err, "exit_match_rate": exit_match,
            "pass": day_pass,
        })
    out["reproduction_pass"] = bool(all_pass)
    return out
