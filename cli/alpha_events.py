"""alpha_events — P2 이벤트 스터디 CLI (E1~E5 감지 → 결과 → 셀 통계 → 플라시보).

사용: python -m cli.alpha_events --dates 20240103,20240104 [--db-dir ...]
      python -m cli.alpha_events --mvp

흐름: 봉인 검증 → 일·종목별 detect_events → measure_event_outcomes(실사건 +
플라시보 2종 동일 파이프) → attach_cells(시총×시간밴드×등락율 층화) →
aggregate_cells(min_n·일 블록 부트스트랩·BH-FDR) → compare_with_placebo →
event_cells_report.json + registry.append_trials(P2, n=통계 검정된 실사건 셀
행 전수 — (사건족,셀,지평) 단위 정직 합산).

파라미터의 단일 원천은 봉인 사전등록 events_spec 이다. 플라시보 random 표집
seed는 (전역 seed, 일자, 종목) crc32 파생으로 결정적이다.
"""
from __future__ import annotations

import argparse
import logging
import re
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from alpha_lab import registry
from alpha_lab.dataset.reader import connect_ro, load_stock_rows
from alpha_lab.events import (
    EVENT_FAMILIES,
    MIN_N,
    REFRACTORY_SEC,
    aggregate_cells,
    attach_cells,
    compare_with_placebo,
    detect_events,
    measure_event_outcomes,
    random_time_matched,
    shift_plus_60,
)
from cli.alpha_common import (
    DEFAULT_DB_DIR,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    LEDGER_NAME,
    add_date_selection_args,
    add_run_dir_args,
    float_list,
    resolve_dates,
    setup_logging,
    verified_prereg_or_none,
    write_receipt,
)

logger = logging.getLogger(__name__)

REPORT_NAME = "event_cells_report.json"
DEFAULT_SEED = 20260705
DEFAULT_N_BOOT = 1000
DEFAULT_BAND_MINUTES = 5
DEFAULT_CAP_EDGES = (1500.0, 3000.0, 10000.0)   # 봉인 층화(격자 재사용).
DEFAULT_CHG_EDGES = (3.0, 8.0)

_CODE_RE = re.compile(r"^\d{6}$")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_events",
        description="tick 일 DB에서 E1~E5 사건 셀 EV·CI·FDR·플라시보를 집계한다.",
    )
    add_date_selection_args(parser)
    add_run_dir_args(parser)
    parser.add_argument(
        "--db-dir", default=str(DEFAULT_DB_DIR),
        help="stock_tick_YYYYMMDD.db 디렉토리 (기본 _database)",
    )
    return parser


def _params(prereg: Dict[str, Any]) -> Dict[str, Any]:
    """봉인 events_spec → CLI 실행 파라미터(부재 키는 봉인 기본값)."""
    spec = prereg.get("events_spec", {})
    strata = spec.get("strata", {})
    return {
        "refractory_sec": int(spec.get("refractory_sec", REFRACTORY_SEC)),
        "min_n": int(spec.get("min_n_cell", MIN_N)),
        "fdr_q": float(spec.get("fdr_q", 0.05)),
        "horizons": [int(h) for h in spec.get("horizons", (60, 180, 300))],
        "n_boot": int(spec.get("n_boot", DEFAULT_N_BOOT)),
        "seed": int(
            spec.get("seed", prereg.get("mining_spec", {}).get("seed", DEFAULT_SEED))
        ),
        "cap_bins_억": float_list(
            strata.get("시가총액_억", {}).get("edges", DEFAULT_CAP_EDGES)
        ),
        "chg_bins_pct": float_list(
            strata.get("등락율_pct", {}).get("edges", DEFAULT_CHG_EDGES)
        ),
        "band_minutes": int(
            strata.get("시간밴드", {}).get("band_minutes", DEFAULT_BAND_MINUTES)
        ),
    }


def _day_codes(conn) -> List[str]:
    """일 DB의 6자리 종목 테이블 목록(이름순)."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [name for (name,) in cursor if _CODE_RE.fullmatch(name)]


def _placebo_seed(seed: int, date: str, code: str) -> int:
    """(전역 seed, 일자, 종목) → 결정적 random 플라시보 seed."""
    return (int(seed) & 0xFFFFFFFF) ^ zlib.crc32(f"{date}|{code}".encode("utf-8"))


def _attach(samples: List[dict], params: Dict[str, Any]) -> List[dict]:
    return attach_cells(
        samples,
        cap_bins_억=params["cap_bins_억"],
        band_minutes=params["band_minutes"],
        chg_bins_pct=params["chg_bins_pct"],
    )


def _process_code(
    rows: Dict[int, dict], *, date: str, code: str, params: Dict[str, Any]
) -> Tuple[List[dict], List[dict], List[dict], Dict[str, int]]:
    """한 종목·일: 감지 → 실사건/플라시보 2종 동일 파이프 측정 → 층화 부착."""
    day = int(date)
    horizons = tuple(params["horizons"])
    events = detect_events(
        sorted(rows.items()), day=day, refractory_sec=params["refractory_sec"]
    )
    detected: Dict[str, int] = {}
    for event in events:
        detected[event["event"]] = detected.get(event["event"], 0) + 1
    if not events:
        return [], [], [], detected
    real = measure_event_outcomes(events, rows, day=day, code=code, horizons=horizons)
    randoms = measure_event_outcomes(
        random_time_matched(events, rows, seed=_placebo_seed(params["seed"], date, code)),
        rows, day=day, code=code, horizons=horizons,
    )
    shifts = measure_event_outcomes(
        shift_plus_60(events), rows, day=day, code=code, horizons=horizons
    )
    return (
        _attach(real, params), _attach(randoms, params), _attach(shifts, params),
        detected,
    )


def _collect(
    db_dir: Path, dates: Sequence[str], params: Dict[str, Any]
) -> Dict[str, Any]:
    """전 일자·종목 순회 — 실사건/플라시보 표본 풀과 감지 카운트 수집."""
    pools: Dict[str, List[dict]] = {"real": [], "random": [], "shift": []}
    detected = {family: 0 for family in EVENT_FAMILIES}
    processed: List[str] = []
    skipped: List[str] = []
    for date in dates:
        db_path = db_dir / f"stock_tick_{date}.db"
        if not db_path.exists():
            logger.warning("일 DB 없음 — 정직 스킵: %s", db_path)
            skipped.append(date)
            continue
        conn = connect_ro(db_path)
        try:
            for code in _day_codes(conn):
                rows = load_stock_rows(conn, code)
                real, randoms, shifts, counts = _process_code(
                    rows, date=date, code=code, params=params
                )
                pools["real"].extend(real)
                pools["random"].extend(randoms)
                pools["shift"].extend(shifts)
                for family, n in counts.items():
                    detected[family] = detected.get(family, 0) + n
        finally:
            conn.close()
        processed.append(date)
        logger.info("events %s: 누적 실사건 표본 %d", date, len(pools["real"]))
    return {
        "pools": pools, "detected": detected,
        "processed": processed, "skipped": skipped,
    }


def _aggregate_pools(
    pools: Dict[str, List[dict]], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """실사건·플라시보 3풀 동일 파이프 셀 통계 → 플라시보 EV 병합 행."""
    cells = {
        name: aggregate_cells(
            samples,
            min_n=params["min_n"],
            n_boot=params["n_boot"],
            seed=params["seed"],
            fdr_q=params["fdr_q"],
        )
        for name, samples in pools.items()
    }
    return compare_with_placebo(cells["real"], cells["random"], cells["shift"])


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    dates = resolve_dates(args, prereg)
    params = _params(prereg)
    collected = _collect(Path(args.db_dir), dates, params)
    if not collected["processed"]:
        logger.error("전 일자 DB 결측 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    merged = _aggregate_pools(collected["pools"], params)
    batch = f"P2-events-{now.strftime('%Y%m%dT%H%M%S')}"
    report = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "db_dir": str(args.db_dir),
        "dates_requested": dates,
        "days_processed": collected["processed"],
        "days_skipped_missing_db": collected["skipped"],
        "params": params,
        "events_detected": collected["detected"],
        "n_outcome_samples": {
            name: len(samples) for name, samples in collected["pools"].items()
        },
        "n_cells": len(merged),
        "cells": merged,
        "ledger": {"program": "P2", "batch": batch, "n": len(merged)},
    }
    write_receipt(run_dir / REPORT_NAME, report)
    registry.append_trials(
        run_dir / LEDGER_NAME,
        program="P2",
        batch=batch,
        n=len(merged),
        now=now,
        meta={"n_days": len(collected["processed"]), "min_n": params["min_n"]},
    )
    logger.info(
        "events 완료: 감지 %s → 셀 행 %d — %s",
        collected["detected"], len(merged), run_dir / REPORT_NAME,
    )
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
