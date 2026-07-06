"""alpha_crosscheck — P1 교차창 안정성 점검 CLI (A창 채굴 → B창 lift 재평가).

사용: python -m cli.alpha_crosscheck --mvp [--run-dir ...]
      python -m cli.alpha_crosscheck --dates-a 20230102,... --dates-b 20240103,...

흐름: 봉인 검증 → 두 창(연도) 샤드 각각 적재 → 창별 mine_rules(봉인
mining_spec 파라미터·피처 서브셋 그대로) → 각 리프 규칙을 '두 창 모두'에서
point lift로 재계산 → cross_window_report.json
{rules: [{rule, lift_<A>, lift_<B>, both_ge_1_3}, ...]}.

창 이름은 각 창 일자들의 공통 연도(YYYY)다 — 공식 MVP 창이면 lift_2023 /
lift_2024 키가 된다. 양방향(2023→2024, 2024→2023) 채굴 리프 전수 합은
n_trials 원장 P1에 정직 합산한다(탐색 전수 규율 — 이중 장부 금지).

교차 안정 기준 lift ≥ 1.3(CROSS_LIFT_MIN)은 연구 프로그램 성공 판정
"교차창 양방향 lift ≥ 1.3 규칙 ≥ 1개"(2026-07-04 신규 알파 연구 프로그램)
에서 온 사전판단 상수다 — 채택 게이트(사전등록 adopt)와 별개이며 보고서에
값을 함께 기록한다.
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from alpha_lab import registry
from alpha_lab.dataset.cache import load_shards
from alpha_lab.dataset.schema import ALL_FEATURES
from alpha_lab.mining import mine_rules, rule_mask
from alpha_lab.stats_common import lift as _lift
from cli.alpha_common import (
    EXIT_INPUT,
    EXIT_OK,
    EXIT_SEAL,
    LEDGER_NAME,
    PREREG_NAME,
    add_run_dir_args,
    parse_dates,
    receipt_filename,
    setup_logging,
    spec_int,
    verified_prereg_or_none,
    write_receipt,
)
from cli.alpha_mine import DEFAULT_LABEL, DEFAULT_PROGRAM, feature_subsets

logger = logging.getLogger(__name__)

REPORT_NAME = "cross_window_report.json"
CROSS_LIFT_MIN = 1.3  # 연구 프로그램 성공 판정 "교차창 양방향 lift>=1.3" 상수.


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alpha_crosscheck",
        description=(
            "한 창에서 채굴한 리프 규칙의 lift를 반대 창에서 재평가한다"
            " (양방향 교차창 안정성 점검)."
        ),
    )
    parser.add_argument(
        "--mvp",
        action="store_true",
        help="봉인 사전등록 windows.mvp 연도 그룹 2개를 두 창으로 사용",
    )
    parser.add_argument("--dates-a", default=None, help="A창 콤마 구분 YYYYMMDD 목록")
    parser.add_argument("--dates-b", default=None, help="B창 콤마 구분 YYYYMMDD 목록")
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


def _validate_window_args(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """--mvp xor (--dates-a and --dates-b) — 위반 시 usage 오류(exit 2)."""
    explicit = args.dates_a is not None or args.dates_b is not None
    if args.mvp and explicit:
        parser.error("--mvp 와 --dates-a/--dates-b 는 함께 쓸 수 없다")
    if not args.mvp and (args.dates_a is None or args.dates_b is None):
        parser.error("--dates-a 와 --dates-b 를 함께 지정하거나 --mvp 를 사용하라")


def _window_name(dates: Sequence[str]) -> str:
    """창 이름 = 일자들의 공통 연도(YYYY). 혼합 연도 창은 거부."""
    years = {str(d)[:4] for d in dates}
    if len(years) != 1:
        raise ValueError(f"한 창의 일자들이 단일 연도가 아니다: {sorted(years)}")
    return years.pop()


def resolve_windows(
    args: argparse.Namespace, prereg: Dict[str, Any]
) -> List[Tuple[str, List[str]]]:
    """두 창 [(이름, 일자들), (이름, 일자들)] — 이름은 서로 달라야 한다."""
    if args.mvp:
        mvp = prereg.get("windows", {}).get("mvp")
        if not isinstance(mvp, dict) or len(mvp) != 2:
            raise ValueError(
                "--mvp 교차창에는 windows.mvp 연도 그룹이 정확히 2개 필요하다"
                f" (현재 {sorted(mvp) if isinstance(mvp, dict) else mvp})"
            )
        groups = [[str(d) for d in mvp[key]] for key in sorted(mvp)]
    else:
        groups = [parse_dates(args.dates_a), parse_dates(args.dates_b)]
    named = [(_window_name(dates), dates) for dates in groups]
    if named[0][0] == named[1][0]:
        raise ValueError(f"두 창의 연도가 같다: {named[0][0]!r} — 교차창이 아니다")
    return named


def _load_window(
    cache_dir: Path, name: str, dates: Sequence[str], label: str
) -> Dict[str, np.ndarray]:
    """창 하나의 샤드 병합 적재 + 표본/라벨 존재 검증(실패는 ValueError)."""
    data = load_shards(cache_dir, dates)
    if not data or int(data["features"].shape[0]) == 0:
        raise ValueError(f"창 {name} 표본 0건 — 입력 부족")
    if label not in data:
        raise ValueError(f"창 {name} 샤드에 라벨 {label!r} 이 없다 (가용: {sorted(data)})")
    return data


def _window_stats(data: Dict[str, np.ndarray], label: str) -> Dict[str, Any]:
    y_pos = np.asarray(data[label]) == 1
    return {
        "n_samples": int(y_pos.shape[0]),
        "positives": int(y_pos.sum()),
        "base_rate": float(y_pos.mean()),
    }


def _cross_eval_rules(
    windows: List[Tuple[str, List[str]]],
    datasets: Dict[str, Dict[str, np.ndarray]],
    label: str,
    spec: Dict[str, Any],
    program: str = DEFAULT_PROGRAM,
) -> Dict[str, Any]:
    """양방향 채굴 + 두 창 lift 재계산 — 보고서 rules/카운트 구성요소."""
    seed = spec_int(spec, "seed", 20260705)
    max_depth = spec_int(spec, "max_depth", 4)
    min_samples_leaf = spec_int(spec, "min_samples_leaf", 2000)
    names = [name for name, _ in windows]
    features = {
        name: np.asarray(datasets[name]["features"], dtype=np.float32)
        for name in names
    }
    y_pos = {
        name: (np.asarray(datasets[name][label]) == 1).astype(np.float64)
        for name in names
    }
    base = {name: float(y_pos[name].mean()) for name in names}
    subsets = feature_subsets(seed, features[names[0]].shape[1])
    rules: List[Dict[str, Any]] = []
    n_by_window: Dict[str, int] = {}
    for mined_on in names:
        leaves = mine_rules(
            features[mined_on], datasets[mined_on][label], ALL_FEATURES,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            seed=seed,
            feature_subsets=subsets,
        )
        n_by_window[mined_on] = len(leaves)
        for leaf in leaves:
            entry: Dict[str, Any] = {
                "rule_id": (
                    f"{program}XW-{mined_on}"
                    f"-s{leaf['subset_id']:02d}-l{leaf['leaf_id']:03d}"
                ),
                "mined_on": mined_on,
                "subset_id": leaf["subset_id"],
                "leaf_id": leaf["leaf_id"],
                "rule": [[name, op, float(thr)] for name, op, thr in leaf["rule"]],
                "rule_cols": list(leaf["rule_cols"]),
            }
            lifts: List[float] = []
            for wname in names:
                mask = rule_mask(features[wname], leaf)
                support = int(mask.sum())
                positives = int(y_pos[wname][mask].sum())
                lift_val = float(_lift(positives, support, base[wname]))
                entry[f"support_{wname}"] = support
                entry[f"positives_{wname}"] = positives
                entry[f"lift_{wname}"] = lift_val
                lifts.append(lift_val)
            # nan 비교는 False — 반대 창 support 0 등은 보수적으로 탈락.
            entry["both_ge_1_3"] = bool(all(v >= CROSS_LIFT_MIN for v in lifts))
            rules.append(entry)
    both = [r for r in rules if r["both_ge_1_3"]]
    return {
        "rules": rules,
        "n_rules": len(rules),
        "n_rules_by_window": n_by_window,
        "n_both_ge_1_3": len(both),
        "n_both_ge_1_3_by_window": {
            name: sum(1 for r in both if r["mined_on"] == name) for name in names
        },
        "params": {
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "seed": seed,
            "feature_subsets": subsets,
        },
    }


def _run(args: argparse.Namespace, now: datetime) -> int:
    run_dir = Path(args.run_dir)
    verified = verified_prereg_or_none(run_dir, logger, args.prereg_name)
    if verified is None:
        return EXIT_SEAL
    prereg, prereg_sha = verified
    spec = prereg.get("mining_spec", {})
    label = args.label or spec.get("label") or DEFAULT_LABEL
    program = args.program
    cache_dir = Path(args.cache_dir) if args.cache_dir else run_dir / "cache"
    try:
        windows = resolve_windows(args, prereg)
        datasets = {
            name: _load_window(cache_dir, name, dates, label)
            for name, dates in windows
        }
    except (FileNotFoundError, ValueError) as exc:
        logger.error("교차창 입력 실패 — %s (exit %d)", exc, EXIT_INPUT)
        return EXIT_INPUT
    crossed = _cross_eval_rules(windows, datasets, label, spec, program)
    batch = f"{program}XW-{label}-{now.strftime('%Y%m%dT%H%M%S')}"
    report = {
        "generated_at": now.isoformat(),
        "prereg_sha": prereg_sha,
        "label": label,
        "cross_lift_min": CROSS_LIFT_MIN,
        "windows": {name: list(dates) for name, dates in windows},
        "window_stats": {
            name: _window_stats(datasets[name], label) for name, _ in windows
        },
        "params": crossed["params"],
        "n_rules": crossed["n_rules"],
        "n_rules_by_window": crossed["n_rules_by_window"],
        "n_both_ge_1_3": crossed["n_both_ge_1_3"],
        "n_both_ge_1_3_by_window": crossed["n_both_ge_1_3_by_window"],
        "rules": crossed["rules"],
        "ledger": {"program": program, "batch": batch, "n": crossed["n_rules"]},
    }
    write_receipt(run_dir / args.report_name, report)
    registry.append_trials(
        run_dir / LEDGER_NAME,
        program=program,
        batch=batch,
        n=crossed["n_rules"],
        now=now,
        meta={
            "kind": "cross_window",
            "label": label,
            "windows": {name: len(dates) for name, dates in windows},
            "n_rules_by_window": crossed["n_rules_by_window"],
            "n_both_ge_1_3": crossed["n_both_ge_1_3"],
        },
    )
    logger.info(
        "crosscheck 완료: 규칙 %d(양방향 lift>=%.1f %d) — %s",
        crossed["n_rules"], CROSS_LIFT_MIN, crossed["n_both_ge_1_3"],
        run_dir / args.report_name,
    )
    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용). now는 여기서 1회 주입."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_window_args(parser, args)
    setup_logging(args.log_level)
    return _run(args, now=datetime.now())


if __name__ == "__main__":
    raise SystemExit(main())
