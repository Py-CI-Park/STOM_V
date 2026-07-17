"""alpha_mine — npz 샤드에서 P1 규칙 채굴 CLI (mine → evaluate → adopt).

사용: python -m cli.alpha_mine --dates 20240103,20240104 [--label L1_180]
      python -m cli.alpha_mine --mvp [--cache-dir ...]

흐름: 봉인 검증 → load_shards → mine_rules(리프 전수) → evaluate_leaves
(일 블록 부트스트랩 + BH-FDR) → adopt(봉인 게이트) → mining_report.json
(리프 전수 + 채택 표시) + registry.append_trials(P1, n=전체 리프 수 — 채택
여부와 무관한 탐색 전수 정직 합산).

파라미터의 단일 원천은 봉인 사전등록 mining_spec 이다. 피처 서브셋 구성은
봉인 문안 '전체25 1회 + 무작위 12피처 서브셋 4회(seed 20260705+k)'를
np.random.default_rng(seed+k) 비복원 추출로 구현한다(k=1..4, 결정적).
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from alpha_lab import registry
from alpha_lab.dataset.cache import load_shards
from alpha_lab.dataset.schema import ALL_FEATURES
from alpha_lab.mining import adopt, evaluate_leaves, mine_rules
from cli.alpha_common import (
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    LEDGER_NAME,
    PREREG_NAME,
    add_date_selection_args,
    add_run_dir_args,
    receipt_filename,
    resolve_dates,
    setup_logging,
    spec_float,
    spec_int,
    verified_prereg_or_none,
    write_receipt,
)

logger = logging.getLogger(__name__)

REPORT_NAME = "mining_report.json"
DEFAULT_LABEL = "L1_180"          # 봉인 기본 라벨.
DEFAULT_PROGRAM = "P1"            # 기본 원장 태그·rule_id 접두(v2는 V2M).
N_RANDOM_SUBSETS = 4              # 봉인 문안: 무작위 서브셋 4회.
RANDOM_SUBSET_SIZE = 12           # 봉인 문안: 12피처.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_mine",
        description="npz 샤드에서 결정트리 리프 규칙을 채굴하고 봉인 게이트로 채택한다.",
    )
    add_date_selection_args(parser)
    add_run_dir_args(parser)
    parser.add_argument(
        "--cache-dir", default=None,
        help="npz 샤드 디렉토리 (기본 {run-dir}/cache)",
    )
    parser.add_argument(
        "--label", default=None,
        help=f"학습 라벨 키 (기본: 사전등록 mining_spec.label, 최종 폴백 {DEFAULT_LABEL})",
    )
    parser.add_argument(
        "--prereg-name", type=receipt_filename, default=PREREG_NAME,
        help=(
            f"run-dir 안 사전등록 파일명 (기본 {PREREG_NAME}"
            " — v2 run은 preregistration_v2.json)"
        ),
    )
    parser.add_argument(
        "--program", default=DEFAULT_PROGRAM,
        choices=sorted(registry.ALLOWED_PROGRAMS),
        help=(
            f"n_trials 원장 프로그램 태그·rule_id 접두 (기본 {DEFAULT_PROGRAM}"
            " — v2 채굴은 V2M)"
        ),
    )
    parser.add_argument(
        "--report-name", type=receipt_filename, default=REPORT_NAME,
        help=f"run-dir 안 보고서 파일명 (기본 {REPORT_NAME})",
    )
    return parser


def feature_subsets(seed: int, n_features: int) -> List[List[int]]:
    """전체 피처 1회 + 무작위 12피처 서브셋 4회(seed+k, k=1..4) — 결정적."""
    subsets: List[List[int]] = [list(range(n_features))]
    size = min(RANDOM_SUBSET_SIZE, n_features)
    for k in range(1, N_RANDOM_SUBSETS + 1):
        rng = np.random.default_rng(seed + k)
        cols = sorted(int(c) for c in rng.choice(n_features, size=size, replace=False))
        subsets.append(cols)
    return subsets


def _serialize_rules(
    evaluated: Sequence[dict], adopted: Sequence[dict],
    program: str = DEFAULT_PROGRAM,
) -> List[Dict[str, Any]]:
    """평가 리프 전수 → 영수증 rule 항목(내부 '_' 키 제외, 채택 표시 부착)."""
    adopted_by_key = {(leaf["subset_id"], leaf["leaf_id"]): leaf for leaf in adopted}
    rows: List[Dict[str, Any]] = []
    for leaf in evaluated:
        key = (leaf["subset_id"], leaf["leaf_id"])
        row: Dict[str, Any] = {
            "rule_id": f"{program}-s{leaf['subset_id']:02d}-l{leaf['leaf_id']:03d}",
            "subset_id": leaf["subset_id"],
            "leaf_id": leaf["leaf_id"],
            "rule": [[name, op, float(thr)] for name, op, thr in leaf["rule"]],
            "rule_cols": list(leaf["rule_cols"]),
            "support": leaf["support"],
            "positives": leaf["positives"],
            "lift": leaf["lift"],
            "ci_low": leaf["ci_low"],
            "ci_high": leaf["ci_high"],
            "p": leaf["p"],
            "fdr_pass": bool(leaf["fdr_survivor"]),
            "adopted": key in adopted_by_key,
        }
        if key in adopted_by_key:
            row["per_year_lift"] = {
                str(year): float(v)
                for year, v in adopted_by_key[key]["per_year_lift"].items()
            }
        rows.append(row)
    return rows


def _mine_and_adopt(
    data: Dict[str, np.ndarray], label: str, spec: Dict[str, Any],
    *, program: str = DEFAULT_PROGRAM,
) -> Dict[str, Any]:
    """채굴→평가→채택 일괄 수행 후 보고서 구성요소 dict 반환."""
    X = data["features"]
    y = data[label]
    day_ids = data["date"]
    seed = spec_int(spec, "seed", 20260705)
    subsets = feature_subsets(seed, X.shape[1])
    leaves = mine_rules(
        X, y, ALL_FEATURES,
        max_depth=spec_int(spec, "max_depth", 4),
        min_samples_leaf=spec_int(spec, "min_samples_leaf", 2000),
        seed=seed,
        feature_subsets=subsets,
    )
    evaluated = evaluate_leaves(
        leaves, X, y, day_ids,
        n_boot=int(spec.get("bootstrap", {}).get("n", 1000)),
        seed=seed,
        q=spec_float(spec, "fdr_q", 0.05),
    )
    years = sorted(int(v) for v in np.unique(np.asarray(day_ids) // 10000))
    masks = {year: (np.asarray(day_ids) // 10000) == year for year in years}
    gate = spec.get("adopt", {})
    adopted = adopt(
        evaluated,
        lift_min=spec_float(gate, "lift_min", 1.5),
        support_min=spec_int(gate, "support_min", 2000),
        per_year_masks=masks,
        per_year_lift_gt=spec_float(gate, "per_year_lift_gt", 1.0),
    )
    return {
        "rules": _serialize_rules(evaluated, adopted, program),
        "n_discovered": len(evaluated),
        "n_fdr_survived": sum(1 for leaf in evaluated if leaf["fdr_survivor"]),
        "n_adopted": len(adopted),
        "n_samples": int(X.shape[0]),
        "base_rate": float(np.mean(np.asarray(y) == 1)),
        "years": years,
        "feature_subsets": subsets,
        "seed": seed,
    }


def _build_report(
    mined: Dict[str, Any], *, spec: Dict[str, Any], label: str,
    dates: Sequence[str], prereg_sha: str, batch: str, now: datetime,
    program: str = DEFAULT_PROGRAM,
) -> Dict[str, Any]:
    """mining_report.json 본문(리프 전수 + 파라미터 + 원장 기록 요약)."""
    return {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "label": label,
        "dates": list(dates),
        "params": {
            "max_depth": spec_int(spec, "max_depth", 4),
            "min_samples_leaf": spec_int(spec, "min_samples_leaf", 2000),
            "seed": mined["seed"],
            "n_boot": int(spec.get("bootstrap", {}).get("n", 1000)),
            "fdr_q": spec_float(spec, "fdr_q", 0.05),
            "adopt": spec.get("adopt", {}),
            "feature_subsets": mined["feature_subsets"],
        },
        "n_samples": mined["n_samples"],
        "base_rate": mined["base_rate"],
        "years": mined["years"],
        "n_discovered": mined["n_discovered"],
        "n_fdr_survived": mined["n_fdr_survived"],
        "n_adopted": mined["n_adopted"],
        "rules": mined["rules"],
        "ledger": {"program": program, "batch": batch, "n": mined["n_discovered"]},
    }


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger, args.prereg_name)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    dates = resolve_dates(args, prereg)
    cache_dir = Path(args.cache_dir) if args.cache_dir else run_dir / "cache"
    spec = prereg.get("mining_spec", {})
    label = args.label or spec.get("label") or DEFAULT_LABEL
    program = args.program
    try:
        data = load_shards(cache_dir, dates)
    except FileNotFoundError as exc:
        logger.error("샤드 결측 — 먼저 alpha_dataset을 실행하라: %s", exc)
        return EXIT_INPUT
    if not data or int(data["features"].shape[0]) == 0:
        logger.error("표본 0건 — 입력 부족(exit %d)", EXIT_INPUT)
        return EXIT_INPUT
    if label not in data:
        logger.error("라벨 %r 이 샤드에 없다 (가용: %s)", label, sorted(data))
        return EXIT_INPUT
    mined = _mine_and_adopt(data, label, spec, program=program)
    batch = f"{program}-{label}-{now.strftime('%Y%m%dT%H%M%S')}"
    report = _build_report(
        mined, spec=spec, label=label, dates=dates,
        prereg_sha=prereg_sha, batch=batch, now=now, program=program,
    )
    write_receipt(run_dir / args.report_name, report)
    registry.append_trials(
        run_dir / LEDGER_NAME,
        program=program,
        batch=batch,
        n=mined["n_discovered"],
        now=now,
        meta={"label": label, "n_days": len(dates), "n_adopted": mined["n_adopted"]},
    )
    logger.info(
        "mine 완료: 리프 %d(FDR 생존 %d, 채택 %d) — %s",
        mined["n_discovered"], mined["n_fdr_survived"], mined["n_adopted"],
        run_dir / args.report_name,
    )
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    args = build_parser().parse_args(argv)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
