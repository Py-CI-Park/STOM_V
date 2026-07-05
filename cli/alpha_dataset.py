"""alpha_dataset — tick 일 DB → npz 샤드 캐시 빌더 CLI (P1 데이터 단계).

사용: python -m cli.alpha_dataset --mvp            (사전등록 windows.mvp 60일)
      python -m cli.alpha_dataset --dates 20240103,20240104 [--db-dir ...]

흐름: 봉인 검증 → 일자 해석 → 일별 reader.stream_samples → cache.write_shard
→ dataset_build_receipt.json(일수·표본수·라벨 양성률·스킵·경과초·prereg_sha).
tick DB 연결은 reader.connect_ro(read-only URI) 전용이다. 결측 일 DB는
정직 스킵으로 기록하고 계속 진행하며, 전 일자 결측이면 exit 4.
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset.cache import to_arrays, write_shard
from alpha_lab.dataset.reader import connect_ro, stream_samples
from cli.alpha_common import (
    DEFAULT_DB_DIR,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    add_date_selection_args,
    add_run_dir_args,
    resolve_dates,
    setup_logging,
    verified_prereg_or_none,
    write_receipt,
)

logger = logging.getLogger(__name__)

RECEIPT_NAME = "dataset_build_receipt.json"
DEFAULT_STRIDE_SEC = 5                     # 봉인 그리드 stride.
DEFAULT_HORIZONS = (60, 180, 300)          # 봉인 L1 지평.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_dataset",
        description="tick 일 DB에서 표본·라벨 npz 샤드를 빌드한다 (read-only).",
    )
    add_date_selection_args(parser)
    add_run_dir_args(parser)
    parser.add_argument(
        "--db-dir", default=str(DEFAULT_DB_DIR),
        help="stock_tick_YYYYMMDD.db 디렉토리 (기본 _database)",
    )
    parser.add_argument(
        "--cache-dir", default=None,
        help="npz 샤드 출력 디렉토리 (기본 {run-dir}/cache)",
    )
    return parser


def _grid_params(prereg: Dict[str, Any]) -> Tuple[int, Tuple[int, ...]]:
    """사전등록 label_spec에서 (stride초, L1 지평 튜플)을 읽는다."""
    label_spec = prereg.get("label_spec", {})
    stride = int(label_spec.get("grid", {}).get("stride_sec", DEFAULT_STRIDE_SEC))
    horizons = tuple(
        int(h) for h in label_spec.get("L1", {}).get("horizons_sec", DEFAULT_HORIZONS)
    )
    return stride, horizons


def _label_counts(arrays: Dict[str, np.ndarray], horizons: Sequence[int]) -> Dict[str, Any]:
    """샤드 배열에서 라벨별 카운트 dict를 만든다(L1 양성수, L2 3분류)."""
    n = int(arrays["t0"].shape[0])
    out: Dict[str, Any] = {}
    for h in horizons:
        key = f"L1_{h}"
        out[key] = {"n": n, "positives": int(np.sum(arrays[key] == 1))}
    l2 = arrays["L2"]
    out["L2"] = {
        "n": n,
        "pos": int(np.sum(l2 == 1)),
        "neg": int(np.sum(l2 == -1)),
        "zero": int(np.sum(l2 == 0)),
    }
    return out


def _build_one_day(
    db_path: Path, date: str, cache_dir: Path, stride: int, horizons: Tuple[int, ...]
) -> Dict[str, Any]:
    """일 DB 하나 → 샤드 기록 + 일별 통계 dict."""
    conn = connect_ro(db_path)
    try:
        samples = list(
            stream_samples(conn, date=date, stride=stride, horizons=horizons)
        )
    finally:
        conn.close()
    arrays = to_arrays(samples)
    shard_path = write_shard(cache_dir, date, arrays)
    counts = _label_counts(arrays, horizons)
    logger.info("dataset %s: 표본 %d → %s", date, len(samples), shard_path.name)
    return {"n_samples": len(samples), "shard": shard_path.name, "labels": counts}


def _merge_labels(per_day: Dict[str, Dict[str, Any]], horizons: Sequence[int]) -> Dict[str, Any]:
    """일별 라벨 카운트 합산 + 양성률 계산."""
    total: Dict[str, Any] = {}
    keys = [f"L1_{h}" for h in horizons]
    for key in keys:
        n = sum(d["labels"][key]["n"] for d in per_day.values())
        pos = sum(d["labels"][key]["positives"] for d in per_day.values())
        total[key] = {
            "n": n, "positives": pos,
            "positive_rate": (pos / n) if n else None,
        }
    n2 = sum(d["labels"]["L2"]["n"] for d in per_day.values())
    l2 = {
        "n": n2,
        "pos": sum(d["labels"]["L2"]["pos"] for d in per_day.values()),
        "neg": sum(d["labels"]["L2"]["neg"] for d in per_day.values()),
        "zero": sum(d["labels"]["L2"]["zero"] for d in per_day.values()),
    }
    l2["positive_rate"] = (l2["pos"] / n2) if n2 else None
    total["L2"] = l2
    return total


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    dates = resolve_dates(args, prereg)
    stride, horizons = _grid_params(prereg)
    db_dir = Path(args.db_dir)
    cache_dir = Path(args.cache_dir) if args.cache_dir else run_dir / "cache"
    started = time.monotonic()
    per_day: Dict[str, Dict[str, Any]] = {}
    skipped: List[str] = []
    for date in dates:
        db_path = db_dir / f"stock_tick_{date}.db"
        if not db_path.exists():
            logger.warning("일 DB 없음 — 정직 스킵: %s", db_path)
            skipped.append(date)
            continue
        per_day[date] = _build_one_day(db_path, date, cache_dir, stride, horizons)
    receipt = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "date_source": "mvp" if args.mvp else "dates",
        "db_dir": str(db_dir),
        "cache_dir": str(cache_dir),
        "stride_sec": stride,
        "horizons_sec": list(horizons),
        "dates_requested": dates,
        "days_built": list(per_day),
        "days_skipped_missing_db": skipped,
        "n_days": len(per_day),
        "n_samples": sum(d["n_samples"] for d in per_day.values()),
        "labels": _merge_labels(per_day, horizons) if per_day else {},
        "per_day": per_day,
        "elapsed_sec": round(time.monotonic() - started, 3),
    }
    write_receipt(run_dir / RECEIPT_NAME, receipt)
    logger.info(
        "dataset 완료: 일수 %d(스킵 %d) 표본 %d — %s",
        len(per_day), len(skipped), receipt["n_samples"], run_dir / RECEIPT_NAME,
    )
    if not per_day:
        logger.error("전 일자 DB 결측 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
