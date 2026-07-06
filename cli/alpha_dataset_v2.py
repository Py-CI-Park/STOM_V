"""alpha_dataset_v2 — L3_replay 라벨 npz 샤드 빌더 + 등가성 게이트 CLI.

사용:
  python -m cli.alpha_dataset_v2 build --mvp                (봉인 sample_grid 60일)
  python -m cli.alpha_dataset_v2 build --dates 20230102,... [--l3-engine auto]
  python -m cli.alpha_dataset_v2 gate                       (667거래 등가성 영수증)

봉인 규율:
- 시작 시 run dir 의 preregistration_v2.json 을 .sha256 사이드카로 verify_seal
  (불일치/부재 exit 3).
- 매도식 원문은 strategy.db stocksell 'ALP_EXITCHK_A_INCUMBENT' 에서 읽어
  sha256 이 봉인 label_spec_v2.champion_sell_sha256 과 일치해야 한다
  (불일치 → blocked, exit 3).
- 표본 채택 규칙은 v1 과 동일(sample_grid.same_as_v1 봉인) — reader 의 t0
  그리드·유니버스·entry/exit 행 존재 요건을 그대로 재사용해 v1 표본 집합을
  재현하고, 라벨만 L3_net/L3_pos 로 교체한다.
- 벡터 라벨 경로는 등가성 게이트 영수증(v2_labeler_equivalence.json,
  gate_pass=True) 이 있을 때만 사용(--l3-engine auto). 미달·부재 시 pure.

npz 샤드 스키마: v1 META(date/code/t0) + features float32(25) +
L3_net float32 + L3_pos int8. tick DB 는 read-only URI 전용.

캐시 v3 증축(additive — v3 P1):
  build --derived 는 v3_feature_annex.json(봉인 .sha256 사이드카 검증,
  --annex-dir 기본 alpha_lab_v3_20260706)의 '패리티 통과' 파생 피처만
  엔진 미러(compute_derived_tick, 공식 창 90000~93000·avg=30·단일일)로
  재계산해 features 뒤에 증축 저장한다(feature_names 메타 포함).
  --derived 미지정 실행은 기존 v2 산출과 동일하다.
"""
from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.dataset import reader
from alpha_lab.dataset.cache import to_arrays, write_shard
from alpha_lab.dataset.derived import (
    AVG_WINDOW_FROZEN,
    DERIVED_TICK_FEATURES,
    SOURCE_COLUMNS,
    compute_derived_tick,
)
from alpha_lab.dataset.labels_v2 import (
    EQUIVALENCE_THRESHOLD,
    SellExprMismatch,
    build_l3_labels,
    equivalence_gate_pass,
    load_champion_sell_expr,
    run_equivalence_gate,
    verify_sell_expr,
)
from alpha_lab.dataset.parity import OFFICIAL_END_TIME, OFFICIAL_START_TIME
from alpha_lab.dataset.schema import ALL_FEATURES, META_COLUMNS
from cli.alpha_common import (
    ANNEX_V3_NAME,
    DEFAULT_DB_DIR,
    DEFAULT_RUN_DIR,
    DEFAULT_RUN_DIR_V2,
    DEFAULT_RUN_DIR_V3,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    PREREG_V2_NAME,
    add_date_selection_args,
    parse_dates,
    setup_logging,
    verified_prereg_or_none,
    write_receipt,
)

logger = logging.getLogger(__name__)

RECEIPT_NAME = "v2_dataset_build_receipt.json"
GATE_RECEIPT_NAME = "v2_labeler_equivalence.json"
DEFAULT_STRIDE_SEC = 5
# v1 채택 규칙 재현용 지평(sample_grid.same_as_v1 봉인) — 라벨로는 쓰지 않는다.
ADMISSION_HORIZONS = (60, 180, 300)
DEFAULT_STRATEGY_DB = DEFAULT_DB_DIR / "strategy.db"
DEFAULT_LEDGER = DEFAULT_RUN_DIR / "distill" / "champion_ledger.jsonl"
DEFAULT_BACK_DB = DEFAULT_DB_DIR / "stock_tick_back.db"
DEFAULT_FALLBACK_DB = DEFAULT_DB_DIR / "code_info.db"

_LABEL_DTYPES = {"L3_net": np.float32, "L3_pos": np.int8}


def _receipt_filename(value: str) -> str:
    """--receipt-name 검증 — 경로 구분자 금지(run-dir 밖 탈출 방지)."""
    name = str(value).strip()
    if not name or Path(name).name != name:
        raise argparse.ArgumentTypeError(
            f"경로 구분자 없는 파일명이어야 한다: {value!r}"
        )
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_dataset_v2",
        description="L3_replay 라벨 npz 샤드 빌더 + 등가성 게이트 (read-only).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="일 DB → META+25피처+L3 npz 샤드")
    add_date_selection_args(build)  # --dates xor --mvp(=봉인 sample_grid 일자)
    _add_common_args(build)
    build.add_argument(
        "--db-dir", default=str(DEFAULT_DB_DIR),
        help="stock_tick_YYYYMMDD.db 디렉토리 (기본 _database)",
    )
    build.add_argument(
        "--cache-dir", default=None,
        help="npz 샤드 출력 디렉토리 (기본 {run-dir}/cache)",
    )
    build.add_argument(
        "--l3-engine", default="auto", choices=("auto", "vector", "pure"),
        help="라벨 경로 — auto: 등가성 영수증 gate_pass 시 vector, 아니면 pure",
    )
    build.add_argument(
        "--receipt-name", type=_receipt_filename, default=RECEIPT_NAME,
        help=f"run-dir 안 영수증 파일명 (기본 {RECEIPT_NAME} — 청크 분할 실행용)",
    )
    build.add_argument(
        "--derived", action="store_true",
        help="캐시 v3 — annex 패리티 통과 파생 피처를 features에 증축 저장",
    )
    build.add_argument(
        "--annex-dir", default=str(DEFAULT_RUN_DIR_V3),
        help=f"{ANNEX_V3_NAME}(+.sha256) 디렉토리 (기본 alpha_lab_v3_20260706)",
    )

    gate = sub.add_parser(
        "gate", help="P5 원장 667거래 등가성 게이트 → v2_labeler_equivalence.json"
    )
    _add_common_args(gate)
    gate.add_argument(
        "--ledger", default=str(DEFAULT_LEDGER),
        help="챔피언 원장 JSONL (기본 v1 run distill/champion_ledger.jsonl)",
    )
    gate.add_argument(
        "--back-db", default=str(DEFAULT_BACK_DB),
        help="stock_tick_back.db 경로 (read-only)",
    )
    gate.add_argument(
        "--fallback-db", default=str(DEFAULT_FALLBACK_DB),
        help="code_info.db 경로 (종목명 해석 fallback)",
    )
    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--run-dir", default=str(DEFAULT_RUN_DIR_V2),
        help="v2 사전등록·영수증 run 디렉토리 (기본 alpha_lab_v2_20260706)",
    )
    parser.add_argument(
        "--strategy-db", default=str(DEFAULT_STRATEGY_DB),
        help="strategy.db 경로 (stocksell 매도식 원문 — read-only)",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="로그 레벨 (기본 INFO)",
    )


def _resolve_dates_v2(args: argparse.Namespace, prereg: Dict[str, Any]) -> List[str]:
    """--dates xor --mvp — --mvp 는 봉인 sample_grid.days(연도 키 정렬 순)."""
    if getattr(args, "mvp", False):
        days = prereg.get("sample_grid", {}).get("days")
        if not isinstance(days, dict) or not days:
            raise ValueError("사전등록에 sample_grid.days 가 없다 — --dates 사용")
        out: List[str] = []
        for key in sorted(days):
            out.extend(str(d) for d in days[key])
        return out
    return parse_dates(args.dates)


def _verified_sell_expr(
    strategy_db: Path, expected_sha: str
) -> Optional[Tuple[str, str]]:
    """매도식 원문 적재 + sha 검증 — (원문, sha) 또는 None(blocked)."""
    try:
        text = load_champion_sell_expr(strategy_db)
        sha = verify_sell_expr(text, expected_sha)
    except SellExprMismatch as exc:
        logger.error("매도식 sha 불일치 — blocked: %s", exc)
        return None
    except (ValueError, OSError) as exc:
        logger.error("매도식 적재 실패 — blocked: %s", exc)
        return None
    return text, sha


def _select_engine(args: argparse.Namespace, run_dir: Path) -> Optional[str]:
    """--l3-engine 해석 — vector 는 등가성 영수증 gate_pass 필요(미달 None)."""
    receipt = run_dir / GATE_RECEIPT_NAME
    passed = equivalence_gate_pass(receipt)
    if args.l3_engine == "vector":
        if not passed:
            logger.error(
                "벡터 경로 불허: %s gate_pass 아님 — gate 먼저 실행", receipt
            )
            return None
        return "vector"
    if args.l3_engine == "pure":
        return "pure"
    engine = "vector" if passed else "pure"
    logger.info(
        "l3-engine auto → %s (영수증 %s, gate_pass=%s)", engine, receipt.name, passed
    )
    return engine


def _annex_passed_derived(annex_payload: Dict[str, Any]) -> List[str]:
    """봉인 annex의 passed_features → 엔진 18항 순서의 파생 피처명 목록.

    순서는 annex 기재 순이 아니라 DERIVED_TICK_FEATURES(엔진 add_rolling_data
    추가 순서 = list_stock_tick[54:72]) 순으로 고정한다(결정성). 18항 밖의
    이름은 무시하되 경고를 남긴다.
    """
    passed = {
        str(item.get("name"))
        for item in annex_payload.get("passed_features", [])
    }
    unknown = sorted(passed - set(DERIVED_TICK_FEATURES))
    if unknown:
        logger.warning("annex passed_features에 파생 18항 밖 이름 무시: %s", unknown)
    return [name for name in DERIVED_TICK_FEATURES if name in passed]


def _derived_by_index(
    rows: Dict[int, dict],
    derived_names: List[str],
    *,
    start_time: int = OFFICIAL_START_TIME,
    end_time: int = OFFICIAL_END_TIME,
) -> Dict[int, Dict[str, float]]:
    """종목 하루 rows → {index int: {파생명: 값}} (엔진 입력 미러 재계산).

    미러 규약(annex method와 동일): 단일일·공식 창(HHMMSS 90000~93000)·
    rowid(삽입) 순 시계열 위에서 compute_derived_tick(avg=30, NaN→0.0).
    NULL 저장값은 pd.read_sql과 같은 의미론(NaN)으로 들어가 워밍업과 함께
    엔진의 nan_to_num 단계에서 0.0이 된다. 일 경계 롤링 없음(단일일).
    """
    window_items = [
        (idx, row) for idx, row in rows.items()
        if start_time <= idx % 1_000_000 <= end_time
    ]
    if not window_items:
        return {}
    frame = pd.DataFrame(
        {
            name: pd.to_numeric(
                pd.Series(
                    [row.get(name) for _, row in window_items], dtype="object"
                ),
                errors="coerce",
            )
            for name in SOURCE_COLUMNS
        }
    )
    derived = compute_derived_tick(frame, AVG_WINDOW_FROZEN)
    columns = {
        name: derived[name].to_numpy(dtype="float64") for name in derived_names
    }
    return {
        idx: {name: float(columns[name][pos]) for name in derived_names}
        for pos, (idx, _) in enumerate(window_items)
    }


def _stream_v2_samples(
    conn, *, date: str, stride: int, sell_text: str, expected_sha: str,
    engine: str, day_stats: Dict[str, int],
    derived_names: Optional[List[str]] = None,
) -> Iterator[dict]:
    """v1 채택 규칙 재현(reader 내부 재사용) + L3 라벨 부착 표본 스트림.

    reader._code_samples/_select_codes 는 사설 심볼이지만 의도적 재사용이다 —
    v2 표본 집합이 v1 과 동일해야 한다는 봉인(sample_grid.same_as_v1)을
    구현 공유로 보증한다(재구현 드리프트 금지).
    derived_names 지정 시(캐시 v3, additive) 표본마다 t0 행의 파생값을
    features 뒤에 붙인다 — 파생 조회 불가 표본은 정직 제외(derived_missing).
    """
    universe = reader.moneytop_universe(conn)
    day_int = int(date)
    for code in reader._select_codes(conn, None):
        rows = reader.load_stock_rows(conn, code)
        samples = list(reader._code_samples(
            rows, code=code, date=str(date), day_int=day_int,
            universe=universe, stride=int(stride), horizons=ADMISSION_HORIZONS,
        ))
        if not samples:
            continue
        derived_map: Dict[int, Dict[str, float]] = (
            _derived_by_index(rows, derived_names) if derived_names else {}
        )
        labels, stats = build_l3_labels(
            rows, [s["t0"] for s in samples], sell_text,
            engine=engine, expected_sha=expected_sha,
        )
        for key in ("fired", "forced_cap", "bad_fire_quote_rows",
                    "no_exit_quote", "path_empty", "entry_missing",
                    "entry_quote_bad"):
            day_stats[key] = day_stats.get(key, 0) + int(stats[key])
        for sample in samples:
            label = labels[int(sample["t0"])]
            if label is None:
                day_stats["l3_excluded"] = day_stats.get("l3_excluded", 0) + 1
                continue
            out = {name: sample[name] for name in META_COLUMNS}
            for name in ALL_FEATURES:
                out[name] = sample[name]
            if derived_names:
                extra = derived_map.get(int(sample["t0"]))
                if extra is None:
                    day_stats["derived_missing"] = (
                        day_stats.get("derived_missing", 0) + 1
                    )
                    continue
                for name in derived_names:
                    out[name] = extra[name]
            out["L3_net"] = float(label["L3_net"])
            out["L3_pos"] = int(label["L3_pos"])
            yield out


def _label_summary(arrays: Dict[str, np.ndarray]) -> Dict[str, Any]:
    n = int(arrays["t0"].shape[0])
    net = arrays["L3_net"].astype(np.float64) if n else np.zeros(0)
    pos = int(np.sum(arrays["L3_pos"] == 1)) if n else 0
    return {
        "L3_pos": {"n": n, "positives": pos,
                   "positive_rate": (pos / n) if n else None},
        "L3_net": {
            "n": n,
            "mean": float(net.mean()) if n else None,
            "p10": float(np.percentile(net, 10)) if n else None,
            "p50": float(np.percentile(net, 50)) if n else None,
            "p90": float(np.percentile(net, 90)) if n else None,
        },
    }


def _build_one_day(
    db_path: Path, date: str, cache_dir: Path, *, stride: int,
    sell_text: str, expected_sha: str, engine: str,
    derived_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    day_stats: Dict[str, int] = {}
    conn = reader.connect_ro(db_path)
    try:
        samples = list(_stream_v2_samples(
            conn, date=date, stride=stride, sell_text=sell_text,
            expected_sha=expected_sha, engine=engine, day_stats=day_stats,
            derived_names=derived_names,
        ))
    finally:
        conn.close()
    arrays = to_arrays(
        samples, label_dtypes=_LABEL_DTYPES, extra_features=derived_names
    )
    shard_path = write_shard(cache_dir, date, arrays)
    logger.info("dataset v2 %s: 표본 %d → %s", date, len(samples), shard_path.name)
    return {
        "n_samples": len(samples), "shard": shard_path.name,
        "labels": _label_summary(arrays), "l3_stats": day_stats,
    }


def _merge_labels(per_day: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    n = sum(d["labels"]["L3_pos"]["n"] for d in per_day.values())
    pos = sum(d["labels"]["L3_pos"]["positives"] for d in per_day.values())
    return {
        "L3_pos": {"n": n, "positives": pos,
                   "positive_rate": (pos / n) if n else None},
    }


def _run_build(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger, PREREG_V2_NAME)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    label_spec = prereg.get("label_spec_v2", {})
    expected_sha = str(label_spec.get("champion_sell_sha256", ""))
    if not expected_sha:
        logger.error("봉인 label_spec_v2.champion_sell_sha256 부재 — exit 3")
        return EXIT_SEAL
    sell = _verified_sell_expr(Path(args.strategy_db), expected_sha)
    if sell is None:
        return EXIT_SEAL
    sell_text, sell_sha = sell
    try:
        dates = _resolve_dates_v2(args, prereg)
    except ValueError as exc:
        logger.error("일자 해석 실패: %s", exc)
        return EXIT_INPUT
    stride = int(prereg.get("sample_grid", {}).get("stride_sec", DEFAULT_STRIDE_SEC))
    engine = _select_engine(args, run_dir)
    if engine is None:
        return EXIT_SEAL  # 게이트 미통과 벡터 강제 — 규율 위반 차단.
    derived_names: Optional[List[str]] = None
    annex_sha: Optional[str] = None
    if getattr(args, "derived", False):
        annex = verified_prereg_or_none(
            Path(args.annex_dir), logger, ANNEX_V3_NAME
        )
        if annex is None:
            return EXIT_SEAL  # annex 봉인 불일치/부재 — 파생 증축 차단.
        annex_payload, annex_sha = annex
        derived_names = _annex_passed_derived(annex_payload)
        if not derived_names:
            logger.error(
                "annex 패리티 통과 파생 0종 — --derived 불가(exit %d)", EXIT_INPUT
            )
            return EXIT_INPUT
        logger.info(
            "캐시 v3 파생 증축 %d종 (annex %s)", len(derived_names), annex_sha[:8]
        )
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
        per_day[date] = _build_one_day(
            db_path, date, cache_dir, stride=stride, sell_text=sell_text,
            expected_sha=expected_sha, engine=engine,
            derived_names=derived_names,
        )
    receipt = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "label_mode": "v2",
        "l3_engine": engine,
        "sell_sha_ok": True,
        "sell_sha256": sell_sha,
        "date_source": "mvp" if args.mvp else "dates",
        "db_dir": str(db_dir),
        "cache_dir": str(cache_dir),
        "stride_sec": stride,
        "admission_horizons_sec": list(ADMISSION_HORIZONS),
        "admission": "same_as_v1",
        "derived": bool(derived_names),
        "derived_features": derived_names or [],
        "annex_sha256": annex_sha,
        "derived_window_hhmmss": (
            [OFFICIAL_START_TIME, OFFICIAL_END_TIME] if derived_names else None
        ),
        "derived_avg": AVG_WINDOW_FROZEN if derived_names else None,
        "n_feature_columns": len(ALL_FEATURES) + len(derived_names or []),
        "dates_requested": dates,
        "days_built": list(per_day),
        "days_skipped_missing_db": skipped,
        "n_days": len(per_day),
        "n_samples": sum(d["n_samples"] for d in per_day.values()),
        "labels": _merge_labels(per_day) if per_day else {},
        "per_day": per_day,
        "elapsed_sec": round(time.monotonic() - started, 3),
    }
    receipt_path = run_dir / getattr(args, "receipt_name", RECEIPT_NAME)
    write_receipt(receipt_path, receipt)
    logger.info(
        "dataset v2 완료: 일수 %d(스킵 %d) 표본 %d engine=%s — %s",
        len(per_day), len(skipped), receipt["n_samples"], engine, receipt_path,
    )
    if not per_day:
        logger.error("전 일자 DB 결측 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    return EXIT_OK


def _run_gate(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger, PREREG_V2_NAME)
    if verified is None:
        return EXIT_SEAL
    prereg, _ = verified
    expected_sha = str(
        prereg.get("label_spec_v2", {}).get("champion_sell_sha256", "")
    )
    sell = _verified_sell_expr(Path(args.strategy_db), expected_sha)
    if sell is None:
        return EXIT_SEAL
    for name, path in (("ledger", args.ledger), ("back-db", args.back_db),
                       ("fallback-db", args.fallback_db)):
        if not Path(path).exists():
            logger.error("%s 부재: %s (exit %d)", name, path, EXIT_INPUT)
            return EXIT_INPUT
    out_path = run_dir / GATE_RECEIPT_NAME
    report = run_equivalence_gate(
        args.ledger, args.back_db, args.fallback_db, out_path,
        generated=now.isoformat(), threshold=EQUIVALENCE_THRESHOLD,
    )
    logger.info(
        "gate 완료: n=%d equivalence=%.4f%% pass=%s — %s",
        report["n_trades"], report["equivalence_pct"], report["gate_pass"],
        out_path,
    )
    return EXIT_OK if report["n_trades"] > 0 else EXIT_INPUT


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    now = datetime.now()
    if args.command == "gate":
        return _run_gate(args, now)
    return _run_build(args, now)


if __name__ == "__main__":
    raise SystemExit(main())
