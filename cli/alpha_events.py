"""alpha_events — P2 이벤트 스터디 CLI (E1~E5 감지 → 결과 → 셀 통계 → 플라시보).

사용: python -m cli.alpha_events --dates 20240103,20240104 [--db-dir ...]
      python -m cli.alpha_events --mvp
      # 청크 분할(additive): 1단계 수집 전용 → 2단계 병합 집계(통계는 전 기간 1회)
      python -m cli.alpha_events --dates <10일> --collect-name events_pool_c1.json
      python -m cli.alpha_events --mvp --from-collected events_pool_c1.json,...

흐름: 봉인 검증 → 일·종목별 detect_events → measure_event_outcomes(실사건 +
플라시보 2종 동일 파이프) → attach_cells(시총×시간밴드×등락율 층화) →
aggregate_cells(min_n·일 블록 부트스트랩·BH-FDR) → compare_with_placebo →
event_cells_report.json + registry.append_trials(P2, n=통계 검정된 실사건 셀
행 전수 — (사건족,셀,지평) 단위 정직 합산).

청크 분할 규율: --collect-name 은 표본 풀만 기록하고 셀 통계·원장 기록을
하지 않는다(통계 검정 0회 — n_trials 대상 아님). --from-collected 는 수집
풀들의 prereg_sha·params 일치와 일자 전수·순서를 검증한 뒤 단일 집계를
수행한다 — min_n·부트스트랩·BH-FDR 이 전 기간 풀에 1회 적용되므로 결과는
동일 일자 단일 실행과 결정적으로 같다.

파라미터의 단일 원천은 봉인 사전등록 events_spec 이다. 플라시보 random 표집
seed는 (전역 seed, 일자, 종목) crc32 파생으로 결정적이다.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

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


def _receipt_filename(value: str) -> str:
    """파일명 검증 — 경로 구분자 금지(run-dir 밖 탈출 방지)."""
    name = str(value).strip()
    if not name or Path(name).name != name:
        raise argparse.ArgumentTypeError(
            f"경로 구분자 없는 파일명이어야 한다: {value!r}"
        )
    return name


def _receipt_filenames(value: str) -> List[str]:
    """콤마 구분 파일명 목록 검증(--from-collected 용, 빈 목록 거부)."""
    names = [_receipt_filename(part) for part in str(value).split(",") if part.strip()]
    if not names:
        raise argparse.ArgumentTypeError(f"빈 수집 풀 파일 목록: {value!r}")
    return names


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
    stage = parser.add_mutually_exclusive_group()
    stage.add_argument(
        "--collect-name", type=_receipt_filename, default=None,
        help=(
            "수집 전용(청크 1단계): 셀 통계·보고서·원장 없이 표본 풀 JSON을 "
            "run-dir 안 지정 파일명으로 기록"
        ),
    )
    stage.add_argument(
        "--from-collected", type=_receipt_filenames, default=None,
        help=(
            "집계 전용(청크 2단계): run-dir 안 수집 풀 파일들(콤마 구분, 일자 순)을 "
            "병합해 단일 셀 통계·보고서·원장을 기록 — DB 접근 없음"
        ),
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


def _rehydrate(samples: Sequence[Mapping[str, Any]]) -> List[dict]:
    """수집 풀 JSON 표본 → 집계 파이프 입력형(net 지평 키 int 복원)."""
    out: List[dict] = []
    for sample in samples:
        out.append({
            "event": str(sample["event"]),
            "day": int(sample["day"]),
            "code": str(sample["code"]),
            "t0": int(sample["t0"]),
            "net": {int(h): float(v) for h, v in dict(sample["net"]).items()},
            "cell": str(sample["cell"]),
        })
    return out


def _pool_payload(
    args: argparse.Namespace,
    *,
    now: datetime,
    prereg_sha: str,
    dates: Sequence[str],
    params: Dict[str, Any],
    collected: Dict[str, Any],
) -> Dict[str, Any]:
    """--collect-name 수집 풀 영수증 본문(셀 통계 없음 — n_trials 대상 아님)."""
    return {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "db_dir": str(args.db_dir),
        "dates_requested": list(dates),
        "days_processed": collected["processed"],
        "days_skipped_missing_db": collected["skipped"],
        "params": params,
        "events_detected": collected["detected"],
        "n_outcome_samples": {
            name: len(samples) for name, samples in collected["pools"].items()
        },
        "pools": collected["pools"],
    }


def _load_collected(
    run_dir: Path,
    names: Sequence[str],
    *,
    expected_sha: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """수집 풀 파일들을 검증·병합해 _collect 동형 dict로 만든다.

    검증: prereg_sha·params 가 현재 봉인과 일치, 처리 일자 파일 간 중복 금지.
    위반은 ValueError(호출측이 EXIT_INPUT 처리).
    """
    pools: Dict[str, List[dict]] = {"real": [], "random": [], "shift": []}
    detected = {family: 0 for family in EVENT_FAMILIES}
    processed: List[str] = []
    skipped: List[str] = []
    for name in names:
        payload = json.loads((Path(run_dir) / name).read_text(encoding="utf-8"))
        if payload.get("prereg_sha") != expected_sha:
            raise ValueError(f"수집 풀 prereg_sha 불일치: {name}")
        if payload.get("params") != params:
            raise ValueError(f"수집 풀 params 불일치(다른 봉인 파라미터): {name}")
        overlap = set(payload["days_processed"]) & set(processed)
        if overlap:
            raise ValueError(f"수집 풀 처리 일자 중복: {name} {sorted(overlap)}")
        for pool_name in pools:
            pools[pool_name].extend(_rehydrate(payload["pools"][pool_name]))
        for family, count in payload["events_detected"].items():
            detected[family] = detected.get(family, 0) + int(count)
        processed.extend(str(d) for d in payload["days_processed"])
        skipped.extend(str(d) for d in payload["days_skipped_missing_db"])
    return {
        "pools": pools, "detected": detected,
        "processed": processed, "skipped": skipped,
    }


def _coverage_problem(
    dates: Sequence[str], collected: Dict[str, Any]
) -> Optional[str]:
    """수집 풀 병합 일자가 요청 일자 전수·순서와 일치하지 않으면 사유 문자열."""
    processed = list(collected["processed"])
    skipped = list(collected["skipped"])
    if sorted(processed + skipped) != sorted(dates):
        return "processed+skipped 합집합이 요청 일자 집합과 다르다"
    if processed != [d for d in dates if d not in set(skipped)]:
        return "수집 풀 순서가 요청 일자 순서와 다르다"
    return None


def _finalize(
    run_dir: Path,
    *,
    db_dir: str,
    dates: Sequence[str],
    collected: Dict[str, Any],
    params: Dict[str, Any],
    prereg_sha: str,
    now: datetime,
    collected_from: Optional[Sequence[str]] = None,
) -> int:
    """병합 풀 → 단일 셀 통계 → 보고서 + P2 원장 append (전 경로 공통 종결부)."""
    merged = _aggregate_pools(collected["pools"], params)
    batch = f"P2-events-{now.strftime('%Y%m%dT%H%M%S')}"
    report = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "db_dir": str(db_dir),
        "dates_requested": list(dates),
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
    if collected_from is not None:
        report["collected_from"] = list(collected_from)
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


def _run_from_collected(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    prereg_sha: str,
    dates: Sequence[str],
    params: Dict[str, Any],
    now: datetime,
) -> int:
    """--from-collected 집계 전용 경로 — DB 접근 없이 수집 풀만 병합·검증."""
    try:
        collected = _load_collected(
            run_dir, args.from_collected, expected_sha=prereg_sha, params=params
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.error("수집 풀 적재 실패 — 입력 부족(exit %d): %s", EXIT_INPUT, exc)
        return EXIT_INPUT
    problem = _coverage_problem(dates, collected)
    if problem is not None:
        logger.error("수집 풀 일자 검증 실패 — %s (exit %d)", problem, EXIT_INPUT)
        return EXIT_INPUT
    if not collected["processed"]:
        logger.error("전 일자 DB 결측 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    return _finalize(
        run_dir, db_dir=str(args.db_dir), dates=dates, collected=collected,
        params=params, prereg_sha=prereg_sha, now=now,
        collected_from=args.from_collected,
    )


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    dates = resolve_dates(args, prereg)
    params = _params(prereg)
    if args.from_collected is not None:
        return _run_from_collected(
            args, run_dir=run_dir, prereg_sha=prereg_sha, dates=dates,
            params=params, now=now,
        )
    collected = _collect(Path(args.db_dir), dates, params)
    if not collected["processed"]:
        logger.error("전 일자 DB 결측 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    if args.collect_name is not None:
        pool_path = write_receipt(
            run_dir / args.collect_name,
            _pool_payload(args, now=now, prereg_sha=prereg_sha, dates=dates,
                          params=params, collected=collected),
        )
        logger.info(
            "events 수집 전용 완료: 감지 %s → 실사건 표본 %d — %s",
            collected["detected"], len(collected["pools"]["real"]), pool_path,
        )
        return EXIT_OK
    return _finalize(
        run_dir, db_dir=str(args.db_dir), dates=dates, collected=collected,
        params=params, prereg_sha=prereg_sha, now=now,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
