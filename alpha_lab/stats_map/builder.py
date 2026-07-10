"""빌드 오케스트레이션 — 일별 추출(재시작 가능) → 셀·corr 조립 → stats_map.db.

Phase1: 일 DB마다 표본을 뽑아 workspace에 npz 체크포인트(부분 영수증)로 저장한다
(이미 있으면 건너뜀 — 청크 재시작). Phase2: 전 npz를 이어붙여 L0/L1 × 2축/3축
셀과 corr을 계산하고 DB에 적재한다. 빌드는 결정론(고정 시드) — summary_sha가
같으면 같은 지도다(재현성 게이트).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from alpha_lab.dataset.reader import list_day_dbs
from alpha_lab.stats_map import config, extract, schema, stats


def iter_pilot_dates(db_dir, start: str, end: str) -> List[Tuple[str, Path]]:
    """[start, end] 범위의 (date, tick DB 경로) 목록(날짜순)."""
    return [(d, p) for d, p in list_day_dbs(db_dir) if start <= d <= end]


def run_extract(dates: List[Tuple[str, Path]], workspace) -> List[Path]:
    """일별 추출을 npz로 저장(재시작 가능). npz 경로 목록 반환."""
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for date, db_path in dates:
        npz = ws / f"extract_{date}.npz"
        if not npz.exists():
            _extract_one(date, db_path, npz)
        paths.append(npz)
    return paths


def _extract_one(date: str, db_path: Path, npz: Path) -> None:
    """한 일자 추출 → npz + 부분 영수증(.done.json) 원자적 기록."""
    rec = extract.extract_day(db_path, date)
    # np.savez_compressed는 .npz 미포함 시 접미를 붙이므로 tmp도 .npz로 끝낸다.
    tmp = npz.parent / f"{npz.stem}.tmp.npz"
    if rec:
        np.savez_compressed(tmp, **rec)
    else:  # 표본 0 — 빈 마커 저장(재시작 시 재계산 방지).
        np.savez_compressed(tmp, off=np.empty(0, np.int16))
    tmp.replace(npz)
    n = int(rec["off"].size) if rec else 0
    npz.with_suffix(".done.json").write_text(
        json.dumps({"date": date, "n": n}), encoding="utf-8")


def load_samples(npz_paths: List[Path]) -> Dict[str, np.ndarray]:
    """전 일자 npz를 컬럼별로 이어붙인다. year 파생 컬럼을 추가한다."""
    per_key: Dict[str, List[np.ndarray]] = {}
    for path in npz_paths:
        with np.load(path) as data:
            if data["off"].size == 0:
                continue
            for key in data.files:
                per_key.setdefault(key, []).append(data[key])
    if not per_key:
        return {}
    sample = {key: np.concatenate(arrs) for key, arrs in per_key.items()}
    sample["year"] = (sample["day"] // 10000).astype(np.int16)
    return sample


def build_all(sample: Dict[str, np.ndarray]) -> Dict[str, object]:
    """L0/L1 × 2축/3축 셀과 corr 행을 조립한다."""
    cells = {
        "cells_l0": _map_cells(sample, config.MAP_L0),
        "cells_l1": _map_cells(sample, config.MAP_L1),
    }
    corr = stats.corr_rows(sample)
    return {"cells": cells, "corr": corr}


def _map_cells(sample, map_type: str) -> List[Dict[str, object]]:
    """한 지도(l0/l1)의 2축+3축 전 셀 행."""
    base = np.ones(sample["off"].size, bool) if map_type == config.MAP_L0 \
        else sample["is_onset"].astype(bool)
    rows: List[Dict[str, object]] = []
    for tb in range(len(config.TIME_BUCKETS)):
        for uq in range(4):
            rows += _cells_at(sample, map_type, base, tb, uq, mc=None)
            for mb in range(3):
                rows += _cells_at(sample, map_type, base, tb, uq, mc=mb)
    return rows


def _cells_at(sample, map_type, base, tb, uq, mc) -> List[Dict[str, object]]:
    """(시간대tb, 등락율uq[, 시총mc])·전 지평 셀 행. mc=None이면 2축."""
    membership = base & (sample["time_b"] == tb) & (sample["updown_q"] == uq)
    axis_set = config.AXIS_TIME_UD if mc is None else config.AXIS_TIME_MC_UD
    if mc is not None:
        membership = membership & (sample["mktcap_b"] == mc)
    out: List[Dict[str, object]] = []
    for h in config.HORIZONS:
        out.append(_one_cell(sample, map_type, axis_set, tb, uq, mc, h,
                             membership))
    return out


def _one_cell(sample, map_type, axis_set, tb, uq, mc, h, membership):
    """단일 셀·지평 행 조립(축 키 + stats.cell_stats)."""
    valid = sample[f"valid_{h}"]
    apply_floor = axis_set == config.AXIS_TIME_MC_UD
    n_used = int((membership & valid).sum())
    seed = stats.cell_seed(map_type, axis_set, tb, uq, mc, h)
    row = stats.cell_stats(
        sample[f"net_{h}"], sample["day"], membership, valid,
        sample[f"censored_{h}"], sample["year"], sample[f"mfe_{h}"],
        sample[f"mae_{h}"], seed=seed,
        insufficient=apply_floor and n_used < config.MIN_CELL_N)
    row.update({
        "axis_set": axis_set, "map_type": map_type,
        "time_label": config.TIME_BUCKETS[tb], "time_b": tb, "updown_q": uq,
        "mktcap_b": -1 if mc is None else mc, "h": h,
    })
    return row


def write_db(db_path, built: Dict[str, object], meta: Dict[str, object]) -> str:
    """스키마 생성 + 셀·corr·영수증 적재. summary_sha 반환."""
    cells: Dict[str, List] = built["cells"]  # type: ignore[assignment]
    corr: List = built["corr"]               # type: ignore[assignment]
    sha = schema.summary_sha(cells, corr)
    conn = sqlite3.connect(str(db_path))
    try:
        schema.create_schema(conn)
        for table, rows in cells.items():
            schema.insert_cells(conn, table, rows)
        schema.insert_corr(conn, config.MAP_L0, corr)
        schema.insert_receipt(conn, _receipt(meta, cells, sha))
    finally:
        conn.close()
    return sha


def _receipt(meta, cells, sha) -> Dict[str, object]:
    """build_receipts 1행 dict(빌드ID·일자범위·행수·파라미터/요약 sha).

    n_l0/n_l1 = 고유 표본 수(L0 후보 / L1 온셋). 셀 n 합계가 아니다 —
    셀 합계는 지평·축집합마다 같은 표본을 중복 계상하므로 provenance에 부적합.
    """
    return {
        "build_id": meta["build_id"], "date_start": meta["date_start"],
        "date_end": meta["date_end"], "input_files": meta["input_files"],
        "row_count": int(meta["row_count"]), "n_l0": int(meta["row_count"]),
        "n_l1": int(meta["l1_onsets"]), "param_sha": config.param_sha(),
        "summary_sha": sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_pilot(db_dir, start: str, end: str, *, db_path, workspace,
                build_id: str) -> Dict[str, object]:
    """파일럿 전체 파이프라인 — 추출→조립→적재. 요약 dict 반환."""
    dates = iter_pilot_dates(db_dir, start, end)
    npz_paths = run_extract(dates, workspace)
    sample = load_samples(npz_paths)
    built = build_all(sample)
    meta = {
        "build_id": build_id, "date_start": start, "date_end": end,
        "input_files": len(dates),
        "row_count": int(sample.get("off", np.empty(0)).size),
        "l1_onsets": int(sample["is_onset"].sum()) if sample else 0,
    }
    sha = write_db(db_path, built, meta)
    return {
        "summary_sha": sha, "param_sha": config.param_sha(),
        "input_files": len(dates), "row_count": meta["row_count"],
        "sample": sample, "built": built,
    }
