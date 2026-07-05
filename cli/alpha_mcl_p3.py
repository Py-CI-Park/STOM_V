"""P3 MCL 오프라인 스크리닝 러너 — 재조인·재라벨·시행·판정 (research-only).

서브커맨드(실행 순서):
  annex   챔피언 풀 목록 부속 봉인(별도 파일 + 커밋 해시) — p3 봉인
          champion_pool 조항의 '목록 부속 봉인 전 착수 금지' 충족용.
  rejoin  발견창 필터 → dedup 감사 → 종목명→코드 해석 → tick 재조인(ro)
          → A안 재라벨 → 봉인 피처 25조합 — 일 단위 청크, 청크 영수증 기록.
  screen  청크 병합 → build_targets → screen_trials → apply_fdr →
          screen_verdict → n_trials 원장 P3 계상 → p3_screening_report.json.

규율: 측정 파라미터의 단일 원천은 봉인(p3_preregistration_v1.json) —
CLI 플래그는 경로·청크 선택만. tick DB 는 read-only URI 전용. 봉인-모듈
상수 드리프트는 착수 전 검사에서 exit 3. print 금지(logging).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from alpha_lab import registry
from alpha_lab.dataset.labels import (
    ADVERSE_TICKS,
    FEE_RATE,
    L1_NET_THRESHOLD,
    TAX_RATE,
)
from alpha_lab.distill.ledger_wiring import read_ledger
from alpha_lab.mcl import screening
from alpha_lab.mcl.features import sealed_feature_specs
from alpha_lab.mcl.rejoin import load_stockinfo_map, rejoin_day
from cli.alpha_common import (
    DEFAULT_DB_DIR,
    DEFAULT_RUN_DIR,
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    LEDGER_NAME,
    REPO_ROOT,
    add_run_dir_args,
    setup_logging,
    write_receipt,
)

logger = logging.getLogger(__name__)

P3_PREREG_STEM = "p3_preregistration_v1"
ANNEX_STEM = "p3_champion_pool_annex_v1"
REPORT_NAME = "p3_screening_report.json"
CHAMPION_LEDGER_REL = Path("distill") / "champion_ledger.jsonl"
P5_RECEIPT_REL = Path("distill") / "p5_phase0_receipt.json"
DEFAULT_MAP_DB = DEFAULT_DB_DIR / "stock_tick_back.db"
DEFAULT_MAP_FALLBACK_DB = DEFAULT_DB_DIR / "code_info.db"

# '[t0]' 참조 해석 등 — 봉인 원문이 명시하지 않아 공개하는 측정 결정.
MEASUREMENT_NOTES: Tuple[str, ...] = (
    "윈도우형 '[t0]' 참조는 W 내 가장 늦은 관측 초로 해석(봉인 window_rule 은 "
    "t0-w 대체만 명시 — features.py 독스트링 공개)",
    "C4 감지는 파일 태그 필요 — 원장 레코드에 source_file 태그가 없어 스킵"
    "(dedup 은 P5 Phase 0 스캔에서 32개 CSV first-wins 로 선수행됨)",
    "종목명→코드 매핑 원천 = 엔진 dict_cn 원천(stock_tick_back.db::stockinfo), "
    "fallback = code_info.db::stockinfo, 최종 검증 = 거래일 tick DB 테이블 실재",
)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_seal(run_dir: Path, stem: str) -> Tuple[Dict[str, Any], str]:
    """<stem>.json 을 <stem>.sha256 사이드카로 검증 후 (payload, sha) 반환."""
    path = Path(run_dir) / f"{stem}.json"
    sidecar = Path(run_dir) / f"{stem}.sha256"
    if not path.exists() or not sidecar.exists():
        raise FileNotFoundError(f"봉인 또는 사이드카 부재: {path} / {sidecar}")
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    registry.verify_seal(path, expected)
    return json.loads(path.read_text(encoding="utf-8")), expected


def _seal_drift(prereg: Dict[str, Any]) -> List[str]:
    """봉인값 ↔ 모듈 상수 대조 — 불일치 목록(비면 정합)."""
    label = prereg["label_spec"]
    scr = prereg["screening"]
    costs = label["costs"]
    checks: List[Tuple[str, Any, Any]] = [
        ("discovery_end_day", prereg["dedup_rules"]["discovery_end_day"],
         screening.DISCOVERY_END_DAY),
        ("c1_return_tol", prereg["dedup_rules"]["c1_return_tol"],
         screening.C1_RETURN_TOL),
        ("fdr_q", prereg["fdr_q"], screening.FDR_Q),
        ("horizons_sec", tuple(label["horizons_sec"]), screening.L1_HORIZONS),
        ("entry_hms_min", label["entry_time_eligibility"]["entry_hms_min"],
         screening.ENTRY_HMS_MIN),
        ("entry_hms_max", label["entry_time_eligibility"]["entry_hms_max"],
         screening.ENTRY_HMS_MAX),
        ("path_window_sec", label["path_window_sec"], screening.PATH_WINDOW_SEC),
        ("commission_buy", costs["commission_buy"], FEE_RATE),
        ("sell_tax", costs["sell_tax"], TAX_RATE),
        ("adverse_fill_ticks", costs["adverse_fill_ticks"], ADVERSE_TICKS),
        ("min_cell_n", scr["min_samples"]["min_cell_n"], screening.MIN_CELL_N),
        ("min_pool_n", scr["min_samples"]["min_pool_n"], screening.MIN_POOL_N),
        ("n_quantiles", prereg["quantile_grid"]["n_quantiles"], screening.N_QUANTILES),
        ("mae_tail_pct", scr["target_operationalization"]["mae_tail_pct"],
         screening.MAE_TAIL_PCT),
        ("valid_trial_min_fraction", scr["valid_trial_min_fraction"],
         screening.VALID_TRIAL_MIN_FRACTION),
        ("n_combos", prereg["features"]["n_combos"], 25),
        ("planned_trials", prereg["n_trials"]["planned_trials"],
         25 * len(screening.LABEL_TARGETS)),
        ("l1_net_threshold", 0.01, L1_NET_THRESHOLD),
    ]
    drift = [
        f"{name}: 봉인={sealed!r} 모듈={module!r}"
        for name, sealed, module in checks if sealed != module
    ]
    agree = scr["year_sign_stability"]["year_agree_min_fraction"]
    if abs(float(agree) - screening.YEAR_AGREE_MIN_FRACTION) > 1e-9:
        drift.append(f"year_agree_min_fraction: 봉인={agree!r}")
    return drift


def _verified_context(run_dir: Path, *, need_annex: bool):
    """(p3 봉인, p3 sha, annex, annex sha) — 드리프트·봉인 불일치는 예외."""
    prereg, p3_sha = _load_seal(run_dir, P3_PREREG_STEM)
    drift = _seal_drift(prereg)
    if drift:
        raise registry.SealViolation(f"봉인-모듈 상수 드리프트: {drift}")
    if not need_annex:
        return prereg, p3_sha, None, None
    annex, annex_sha = _load_seal(run_dir, ANNEX_STEM)
    if annex["p3_preregistration_sha256"] != p3_sha:
        raise registry.SealViolation("annex 가 참조하는 p3 봉인 sha 불일치")
    ledger_path = run_dir / CHAMPION_LEDGER_REL
    actual = _sha256_of(ledger_path)
    if annex["ledger_sha256"] != actual:
        raise registry.SealViolation(
            f"champion_ledger sha 불일치: annex={annex['ledger_sha256']} 실제={actual}"
        )
    return prereg, p3_sha, annex, annex_sha


# ---------------------------------------------------------------------------
# annex — 챔피언 풀 목록 부속 봉인(별도 파일 + 커밋 해시).
# ---------------------------------------------------------------------------
def _git(args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout.strip()


def _cmd_annex(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    try:
        prereg, p3_sha, _, _ = _verified_context(run_dir, need_annex=False)
    except (registry.SealViolation, FileNotFoundError) as exc:
        logger.error("봉인 검증 실패 — annex 착수 금지: %s", exc)
        return EXIT_SEAL
    ledger_path = run_dir / CHAMPION_LEDGER_REL
    receipt_path = run_dir / P5_RECEIPT_REL
    if not ledger_path.exists() or not receipt_path.exists():
        logger.error("원장/영수증 부재: %s / %s", ledger_path, receipt_path)
        return EXIT_INPUT
    try:
        ledger_rel = ledger_path.resolve().relative_to(REPO_ROOT).as_posix()
        _git(["ls-files", "--error-unmatch", ledger_rel])
        head = _git(["rev-parse", "HEAD"])
    except RuntimeError as exc:
        logger.error("원장이 커밋되어 있지 않아 부속 봉인 불가: %s", exc)
        return EXIT_INPUT
    records = read_ledger(ledger_path)
    strategies: Dict[str, int] = {}
    for rec in records:
        key = str(rec.get("전략명"))
        strategies[key] = strategies.get(key, 0) + 1
    payload = {
        "annex": "champion_pool_list_v1",
        "program": prereg["program"],
        "p3_preregistration_sha256": p3_sha,
        "ledger_path": ledger_path.resolve().relative_to(REPO_ROOT).as_posix(),
        "ledger_sha256": _sha256_of(ledger_path),
        "ledger_records": len(records),
        "git_head": head,
        "strategies": strategies,
        "source_receipt": {
            "path": receipt_path.resolve().relative_to(REPO_ROOT).as_posix(),
            "sha256": _sha256_of(receipt_path),
        },
        "mapping_source": {
            "primary": "_database/stock_tick_back.db::stockinfo (엔진 dict_cn 원천)",
            "fallback": "_database/code_info.db::stockinfo",
            "validation": "해당 거래일 tick DB 테이블 실재",
        },
        "scope_note": (
            "rr8_12 계보 단일 챔피언 원장만 확정 — 봉인 초안의 추가 대상"
            "(r8_exclude_cap_lt_1500, hard-stop 매도 축)은 미포함. 풀 확장은 "
            "새 부속 봉인 + 새 n_trials 로만 가능(봉인 champion_pool 조항)."
        ),
    }
    annex_path = run_dir / f"{ANNEX_STEM}.json"
    try:
        sha = registry.seal(payload, annex_path)
    except registry.SealViolation as exc:
        logger.error("annex 봉인 위반: %s", exc)
        return EXIT_SEAL
    sidecar = run_dir / f"{ANNEX_STEM}.sha256"
    if sidecar.exists():
        if sidecar.read_text(encoding="utf-8").split()[0] != sha:
            logger.error("annex 사이드카 불일치 — 수동 확인 필요: %s", sidecar)
            return EXIT_SEAL
    else:
        sidecar.write_text(sha + "\n", encoding="utf-8")
    logger.info("annex 봉인 완료 %s sha=%s records=%d head=%s",
                annex_path, sha[:16], len(records), head[:12])
    return EXIT_OK


# ---------------------------------------------------------------------------
# rejoin — 발견창 필터·dedup 감사·재조인·재라벨·피처 (일 단위 청크).
# ---------------------------------------------------------------------------
def _merge_counts(total: Dict[str, int], part: Dict[str, int]) -> Dict[str, int]:
    merged = dict(total)
    for key, value in part.items():
        merged[key] = merged.get(key, 0) + int(value)
    return merged


def _chunk_receipt_name(index: int, count: int) -> str:
    return f"p3_rejoin_chunk_{index + 1}of{count}.json"


def _cmd_rejoin(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    try:
        prereg, p3_sha, annex, annex_sha = _verified_context(run_dir, need_annex=True)
    except (registry.SealViolation, FileNotFoundError) as exc:
        logger.error("봉인 검증 실패 — 측정 착수 금지: %s", exc)
        return EXIT_SEAL
    if not (0 <= args.chunk_index < args.chunk_count):
        logger.error("청크 인덱스 범위 오류: %d/%d", args.chunk_index, args.chunk_count)
        return EXIT_INPUT

    specs = sealed_feature_specs(prereg["features"]["table"])
    horizons = tuple(int(h) for h in prereg["label_spec"]["horizons_sec"])
    records = read_ledger(run_dir / CHAMPION_LEDGER_REL)
    kept, validation_dropped = screening.filter_discovery(
        records, end_day=str(prereg["dedup_rules"]["discovery_end_day"])
    )
    unique, audit = screening.dedup_trades(kept)

    by_day: Dict[str, List[dict]] = {}
    for rec in unique:
        by_day.setdefault(str(rec["진입일자"]), []).append(rec)
    days = sorted(by_day)
    chunk_days = days[args.chunk_index::args.chunk_count]

    primary, primary_codes = load_stockinfo_map(Path(args.map_db))
    fallback, fallback_codes = load_stockinfo_map(Path(args.map_db_fallback))

    samples: List[dict] = []
    exclusions: List[dict] = []
    resolution: Dict[str, int] = {}
    relabel: Dict[str, int] = {}
    db_dir = Path(args.db_dir)
    for day in chunk_days:
        day_samples, day_exclusions, counters = rejoin_day(
            db_dir / f"stock_tick_{day}.db", day, by_day[day],
            primary=primary, primary_codes=primary_codes,
            fallback=fallback, fallback_codes=fallback_codes,
            specs=specs, horizons=horizons,
        )
        samples.extend(day_samples)
        exclusions.extend(day_exclusions)
        resolution = _merge_counts(resolution, counters["resolution"])
        relabel = _merge_counts(relabel, counters["relabel"])

    receipt = {
        "kind": "p3_rejoin_chunk",
        "generated": now.isoformat(),
        "p3_preregistration_sha256": p3_sha,
        "annex_sha256": annex_sha,
        "chunk_index": args.chunk_index,
        "chunk_count": args.chunk_count,
        "days_total": len(days),
        "chunk_days": len(chunk_days),
        "ledger_rows": len(records),
        "discovery_kept": len(kept),
        "validation_dropped": validation_dropped,
        "dedup_audit": audit,
        "resolution_counts": resolution,
        "relabel_counts": relabel,
        "n_samples": len(samples),
        "n_exclusions": len(exclusions),
        "exclusions": exclusions,
        "samples": samples,
    }
    path = write_receipt(run_dir / _chunk_receipt_name(args.chunk_index,
                                                       args.chunk_count), receipt)
    logger.info("rejoin 청크 %d/%d 완료: days=%d samples=%d exclusions=%d → %s",
                args.chunk_index + 1, args.chunk_count, len(chunk_days),
                len(samples), len(exclusions), path)
    return EXIT_OK


# ---------------------------------------------------------------------------
# screen — 청크 병합·시행·FDR·판정·n_trials·보고서.
# ---------------------------------------------------------------------------
def _feature_matrix(
    samples: Sequence[Dict[str, Any]], specs: Sequence[Dict[str, Any]]
) -> Dict[str, List[float]]:
    """표본 features dict → 봉인 순서 열 벡터(None→NaN — '측정 불가' 복원)."""
    nan = float("nan")
    return {
        str(spec["key"]): [
            nan if (v := s["features"].get(str(spec["key"]))) is None else float(v)
            for s in samples
        ]
        for spec in specs
    }


def _trial_report_row(row: Dict[str, Any], *, fdr_q: float) -> Dict[str, Any]:
    """apply_fdr 행 → 보고 스키마 행(name/window/lift_q/year_signs/... 정렬)."""
    key = str(row["feature"])
    window = int(key.split("_w", 1)[1]) if "_w" in key else None
    cells = row.get("cells") or []
    return {
        "name": key,
        "window": window,
        "target": row["target"],
        "n": row["n"],
        "n_missing": row["n_missing"],
        "verdict": row["verdict"],
        "lift_q": [c["lift"] for c in cells] if cells else None,
        "cells": cells or None,
        "monotone": row["monotone"],
        "direction": row["direction"],
        "p_trial": row["p_trial"],
        "q": fdr_q,
        "fdr_pass": row["fdr_pass"],
        "year_signs": row["year_lifts"] or None,
        "year_stable": row["year_stable"],
        "mae_suppressor": row["mae_suppressor"],
        "placebo_delta": None,  # 생존 후보 없어 플라시보 게이트 미실행(보고서 placebo 절).
        "survivor": row["survivor"],
    }


def _consistency_failures(
    chunks: Sequence[Dict[str, Any]], samples: Sequence[dict],
    exclusions: Sequence[dict],
) -> List[str]:
    first = chunks[0]
    problems: List[str] = []
    for chunk in chunks[1:]:
        for key in ("ledger_rows", "discovery_kept", "validation_dropped",
                    "days_total", "chunk_count"):
            if chunk[key] != first[key]:
                problems.append(f"청크 간 {key} 불일치")
    covered = len(samples) + len(exclusions)
    if covered != first["dedup_audit"]["unique_rows"]:
        problems.append(
            f"표본+제외({covered}) != dedup 고유({first['dedup_audit']['unique_rows']})"
        )
    return problems


def _cmd_screen(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    try:
        prereg, p3_sha, annex, annex_sha = _verified_context(run_dir, need_annex=True)
    except (registry.SealViolation, FileNotFoundError) as exc:
        logger.error("봉인 검증 실패 — 측정 착수 금지: %s", exc)
        return EXIT_SEAL
    chunk_paths = [
        run_dir / _chunk_receipt_name(i, args.chunk_count)
        for i in range(args.chunk_count)
    ]
    missing = [str(p) for p in chunk_paths if not p.exists()]
    if missing:
        logger.error("rejoin 청크 부재: %s", missing)
        return EXIT_INPUT
    chunks = [json.loads(p.read_text(encoding="utf-8")) for p in chunk_paths]
    samples = [s for c in chunks for s in c["samples"]]
    exclusions = [e for c in chunks for e in c["exclusions"]]
    resolution: Dict[str, int] = {}
    relabel: Dict[str, int] = {}
    for chunk in chunks:
        resolution = _merge_counts(resolution, chunk["resolution_counts"])
        relabel = _merge_counts(relabel, chunk["relabel_counts"])
    problems = _consistency_failures(chunks, samples, exclusions)
    if problems:
        logger.error("청크 정합 실패: %s", problems)
        return EXIT_INPUT
    if not samples:
        logger.error("재라벨 표본 0 — 시행 불가(전량 제외)")
        return EXIT_INPUT

    scr = prereg["screening"]
    specs = sealed_feature_specs(prereg["features"]["table"])
    features = _feature_matrix(samples, specs)
    targets, thresholds = screening.build_targets(
        samples,
        mfe_threshold=L1_NET_THRESHOLD,
        mae_tail_pct=float(scr["target_operationalization"]["mae_tail_pct"]),
    )
    day_ids = [int(s["day"]) for s in samples]
    trials = screening.screen_trials(
        features, targets, day_ids,
        n_boot=int(scr["bootstrap"]["n_boot"]),
        seed=int(scr["bootstrap"]["base_seed"]),
        min_cell_n=int(scr["min_samples"]["min_cell_n"]),
        n_quantiles=int(prereg["quantile_grid"]["n_quantiles"]),
    )
    rows = screening.apply_fdr(trials, q=float(prereg["fdr_q"]))

    # 봉인 pass_rule: 공식 생존 = survivor ∧ 플라시보 소멸. 생존 후보가 없으면
    # 게이트 결합 대상이 없다(미실행 정직 기재). 후보가 있는데 미실행이면
    # 성공/포기 어느 쪽도 확정하지 않는다(placebo_pending — 오판 방지).
    pre_survivors = [r for r in rows if r["survivor"]]
    placebo_pending = bool(pre_survivors)
    official_rows = (
        [{**r, "survivor": False} for r in rows] if placebo_pending else rows
    )
    verdict = screening.screen_verdict(official_rows, pool_n=len(samples))
    if placebo_pending:
        verdict = {**verdict, "verdict": "placebo_pending",
                   "note": "생존 후보 존재 — 플라시보 라운드 실행 전 판정 보류"}

    ledger_path = run_dir / LEDGER_NAME
    planned = int(prereg["n_trials"]["planned_trials"])
    if len(rows) != planned:
        logger.error("시행 수 %d != 봉인 선계상 %d", len(rows), planned)
        return EXIT_INPUT
    already = registry.total_trials(ledger_path, "P3")
    if already == 0:
        registry.append_trials(
            ledger_path, program="P3",
            batch=f"P3-mcl-screening-{now.strftime('%Y%m%dT%H%M%S')}",
            n=planned, now=now,
            meta={
                "kind": "mcl_screening_precommit",
                "pool_n": len(samples),
                "valid_trials": verdict["valid_trials"],
                "survivors": verdict["survivors"],
                "counting_rule": "피처25×표적6 전수 선계상(미실행분 반환 없음)",
            },
        )
        logger.info("n_trials 원장 P3 +%d 계상", planned)
    else:
        logger.warning("P3 계상 이미 존재(%d) — 중복 계상 생략(재실행 안전)", already)

    audit = chunks[0]["dedup_audit"]
    mapping_excluded = sum(
        resolution.get(k, 0)
        for k in ("day_db_missing", "unmapped", "no_day_table", "ambiguous_day_table")
    )
    report = {
        "program": prereg["program"],
        "generated": now.isoformat(),
        "seal": {
            "p3_preregistration_sha256": p3_sha,
            "annex_sha256": annex_sha,
            "annex_git_head": annex["git_head"],
            "ledger_sha256": annex["ledger_sha256"],
        },
        "phase0_audit": {
            "ledger_rows": chunks[0]["ledger_rows"],
            "discovery_end_day": prereg["dedup_rules"]["discovery_end_day"],
            "discovery_kept": chunks[0]["discovery_kept"],
            "validation_dropped": chunks[0]["validation_dropped"],
            "dedup_audit": audit,
            "c3_note": "동명이식 sha 분리는 상류 소관 — 원장 전략명 1종(annex)",
            "resolution_counts": resolution,
            "rejoin_mapping_excluded": mapping_excluded,
            "relabel_counts": relabel,
            "final_samples": len(samples),
            "exclusions_total": len(exclusions),
        },
        "coverage": {
            "trades_used": len(samples),
            "denominator_discovery_dedup": audit["unique_rows"],
            "coverage_pct": 100.0 * len(samples) / audit["unique_rows"],
        },
        "labels": {
            "targets": list(screening.LABEL_TARGETS),
            "thresholds": thresholds,
            "base_rates": {
                name: float(sum(vec)) / len(samples)
                for name, vec in targets.items()
            },
        },
        "screening_params": {
            "n_boot": int(scr["bootstrap"]["n_boot"]),
            "base_seed": int(scr["bootstrap"]["base_seed"]),
            "min_cell_n": int(scr["min_samples"]["min_cell_n"]),
            "min_pool_n": int(scr["min_samples"]["min_pool_n"]),
            "n_quantiles": int(prereg["quantile_grid"]["n_quantiles"]),
            "fdr_q": float(prereg["fdr_q"]),
            "mae_tail_pct": float(scr["target_operationalization"]["mae_tail_pct"]),
        },
        "features": [
            {
                "key": spec["key"], "id": spec["id"], "name": spec["name"],
                "kind": spec["kind"], "window_sec": spec["window_sec"],
                "n_missing": int(sum(
                    1 for v in features[str(spec["key"])] if math.isnan(v)
                )),
            }
            for spec in specs
        ],
        "trials": [
            _trial_report_row(row, fdr_q=float(prereg["fdr_q"])) for row in rows
        ],
        "placebo": {
            "executed": False,
            "kind": scr["placebo"]["kind"],
            "seed": scr["placebo"]["seed"],
            "reason": (
                "FDR·단조·연도 생존 후보 0 — 봉인 pass_rule 상 플라시보 게이트는 "
                "survivor 에 결합하는 관문이라 결합 대상이 없음"
                if not placebo_pending else
                "생존 후보 존재 — 별도 플라시보 라운드 필요(판정 보류)"
            ),
        },
        "n_trials": {
            "planned_trials": planned,
            "appended": planned if already == 0 else 0,
            "ledger_total_p3": registry.total_trials(ledger_path, "P3"),
            "ledger_total_all": registry.total_trials(ledger_path),
        },
        "verdict": verdict,
        "measurement_notes": list(MEASUREMENT_NOTES),
        "exclusions": exclusions,
    }
    path = write_receipt(run_dir / REPORT_NAME, report)
    logger.info(
        "screen 완료: pool_n=%d valid=%d survivors=%d verdict=%s → %s",
        len(samples), verdict["valid_trials"], verdict["survivors"],
        verdict["verdict"], path,
    )
    return EXIT_OK


# ---------------------------------------------------------------------------
# 파서 / 엔트리포인트.
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_mcl_p3",
        description="P3 MCL 오프라인 스크리닝 러너 (annex/rejoin/screen)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    annex = sub.add_parser("annex", help="챔피언 풀 목록 부속 봉인")
    add_run_dir_args(annex)

    rejoin = sub.add_parser("rejoin", help="발견창·dedup·재조인·재라벨·피처")
    add_run_dir_args(rejoin)
    rejoin.add_argument("--db-dir", default=str(DEFAULT_DB_DIR),
                        help="tick 일 DB 디렉토리(read-only)")
    rejoin.add_argument("--map-db", default=str(DEFAULT_MAP_DB),
                        help="종목명→코드 primary stockinfo DB")
    rejoin.add_argument("--map-db-fallback", default=str(DEFAULT_MAP_FALLBACK_DB),
                        help="종목명→코드 fallback stockinfo DB")
    rejoin.add_argument("--chunk-index", type=int, default=0,
                        help="일 청크 인덱스(0부터)")
    rejoin.add_argument("--chunk-count", type=int, default=1,
                        help="일 청크 총수")

    screen = sub.add_parser("screen", help="청크 병합·시행·FDR·판정·보고")
    add_run_dir_args(screen)
    screen.add_argument("--chunk-count", type=int, default=1,
                        help="병합할 rejoin 청크 총수")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 — now 는 여기서 1회 주입(registry 규율)."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    now = datetime.now()
    if args.command == "annex":
        return _cmd_annex(args, now)
    if args.command == "rejoin":
        return _cmd_rejoin(args, now)
    return _cmd_screen(args, now)


if __name__ == "__main__":
    raise SystemExit(main())
