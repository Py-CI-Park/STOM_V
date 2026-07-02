"""시드 격자 CLI (T1.4) — ``build`` (시드+passport 생성) / ``coverage`` (지도 산출).

**백테스트 실행은 이 CLI 범위 밖이다.** ``build`` 는 격자 열거 → 시드 생성 →
seeds JSON + Condition Passport md 를 파일로 내기만 하고, 백테스트는 기존
러너가 그 시드 파일을 소비해서 수행한다. ``coverage`` 는 러너가 남긴 결과 요약
JSON 들을 읽어 coverage map / coverage gap 목록을 산출한다 (discovery 프롬프트
입력 형식 — :mod:`ai_strategy_loop.seeds.coverage` 참조).

사용 예::

    python -m cli.seed_lattice build --out-dir docs/research/condition_research/generated_conditions/lattice
    python -m cli.seed_lattice coverage --seeds .../lattice_seeds.json \
        --results results_a.json results_b.json --out coverage_map.json \
        --gaps-out coverage_gaps.json --min-trades 300

연구 레인 전용: 승격/export/live 권한 로직과 무관한 순수 파일 산출 CLI 다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401  (env-before-import 계약)
from ai_strategy_loop.seeds.coverage import (  # noqa: E402
    COVERAGE_GAPS_SCHEMA,
    DEFAULT_MIN_TRADES,
    build_coverage_map,
    coverage_gaps,
    save_coverage_map,
)
from ai_strategy_loop.seeds.lattice import (  # noqa: E402
    SeedRecord,
    build_seed,
    default_pattern_families,
    enumerate_cells,
    load_pattern_families,
)
from ai_strategy_loop.seeds.passport import (  # noqa: E402
    passport_condition_id,
    passport_filename,
    render_passport,
)

SEEDS_JSON_SCHEMA = "seed_lattice_seeds_v1"
SEEDS_JSON_NAME = "lattice_seeds.json"
PASSPORT_DIRNAME = "passports"

# 기본 출력 위치 (연구 문서 트리 아래 — backtest/graph/ 등 결과 데이터와 무관).
DEFAULT_OUT_DIR = (
    _PROJECT_ROOT / "docs" / "research" / "condition_research"
    / "generated_conditions" / "lattice"
)


def _emit(payload: Mapping[str, Any]) -> None:
    """요약 JSON 한 덩이를 stdout 으로 내보낸다 (print 금지 규약 — write 사용).

    stdout 은 Windows cp949 콘솔일 수 있어 ``ensure_ascii=True`` 로 이스케이프한다
    (JSON 이스케이프는 무손실 — json.loads 로 한글이 복원된다). 디스크 산출물은
    utf-8 + ensure_ascii=False 를 유지한다.
    """
    sys.stdout.write(json.dumps(dict(payload), ensure_ascii=True, indent=2) + "\n")


def _seed_to_dict(rec: SeedRecord) -> Dict[str, Any]:
    """SeedRecord 를 JSON 직렬화 dict 로 변환한다 (passport 참조 필드 포함)."""
    return {
        "condition_id": passport_condition_id(rec),
        "cell_id": rec.cell_id,
        "family": rec.family,
        "buy_code": rec.buy_code,
        "sell_code": rec.sell_code,
        "buy_sha256": rec.buy_sha256,
        "sell_sha256": rec.sell_sha256,
        "params": dict(rec.params),
        "created_reason": rec.created_reason,
        "passport_md": f"{PASSPORT_DIRNAME}/{passport_filename(rec)}",
    }


# ---------------------------------------------------------------------------
# build — 격자 열거 → 시드 생성 → seeds JSON + passport md
# ---------------------------------------------------------------------------
def _cmd_build(args: argparse.Namespace) -> int:
    """build 서브커맨드: 시드 JSON 과 Condition Passport md 를 생성한다."""
    families = default_pattern_families()
    if args.families_json:
        # 외부 패밀리(JSON)를 불변 병합 — 같은 이름은 외부가 우선.
        families = {**families, **load_pattern_families(args.families_json)}

    selected = list(args.family) if args.family else sorted(families)
    unknown = [name for name in selected if name not in families]
    if unknown:
        raise SystemExit(f"미등록 패밀리: {unknown} (등록: {sorted(families)})")

    cells = enumerate_cells()
    if args.lane:
        cells = [c for c in cells if c.lane in set(args.lane)]

    out_dir = Path(args.out_dir)
    passport_dir = out_dir / PASSPORT_DIRNAME
    passport_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    for cell in cells:
        for name in selected:
            fam = families[name]
            if cell.lane not in fam.lanes:
                continue
            rec = build_seed(cell, fam, families=families)
            records.append(_seed_to_dict(rec))
            if not args.skip_passports:
                (passport_dir / passport_filename(rec)).write_text(
                    render_passport(rec), encoding="utf-8")

    seeds_path = out_dir / SEEDS_JSON_NAME
    seeds_path.write_text(
        json.dumps(
            {
                "schema": SEEDS_JSON_SCHEMA,
                "families": selected,
                "lanes": sorted({c.lane for c in cells}),
                "seed_count": len(records),
                "seeds": records,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _emit({
        "command": "build",
        "seeds_json": str(seeds_path),
        "passport_dir": None if args.skip_passports else str(passport_dir),
        "cells": len(cells),
        "families": selected,
        "seed_count": len(records),
        "note": "백테스트 실행은 이 CLI 범위 밖 — 기존 러너가 시드 파일을 소비한다",
    })
    return 0


# ---------------------------------------------------------------------------
# coverage — 결과 요약 JSON 들 → coverage map (+ gaps)
# ---------------------------------------------------------------------------
def _load_seed_dicts(path: Path) -> List[Dict[str, Any]]:
    """build 산출 seeds JSON 에서 시드 dict 목록을 읽는다."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SEEDS_JSON_SCHEMA:
        raise SystemExit(f"seeds JSON 스키마 불일치: {path}")
    seeds = data.get("seeds")
    if not isinstance(seeds, list):
        raise SystemExit(f"seeds JSON 에 seeds 리스트가 없습니다: {path}")
    return seeds


def _load_result_entries(paths: Sequence[str]) -> List[Mapping[str, Any]]:
    """결과 요약 JSON 들을 평탄화해 읽는다 (리스트 또는 {"results": [...]} 허용)."""
    entries: List[Mapping[str, Any]] = []
    for raw in paths:
        data = json.loads(Path(raw).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("results", [data] if data else [])
        if not isinstance(data, list):
            raise SystemExit(f"결과 JSON 형식 오류 (리스트/results 키 필요): {raw}")
        entries.extend(data)
    return entries


def _cmd_coverage(args: argparse.Namespace) -> int:
    """coverage 서브커맨드: coverage map 과 gap 목록 JSON 을 산출한다."""
    seeds = _load_seed_dicts(Path(args.seeds))
    results = _load_result_entries(args.results or [])
    cov_map = build_coverage_map(seeds, results)
    out_path = save_coverage_map(cov_map, args.out)

    gaps = coverage_gaps(cov_map, min_trades=args.min_trades)
    gaps_path: Optional[Path] = None
    if args.gaps_out:
        gaps_path = Path(args.gaps_out)
        gaps_path.parent.mkdir(parents=True, exist_ok=True)
        gaps_path.write_text(
            json.dumps(
                {
                    "schema": COVERAGE_GAPS_SCHEMA,
                    "min_trades": args.min_trades,
                    "gap_count": len(gaps),
                    "gaps": gaps,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    _emit({
        "command": "coverage",
        "coverage_map": str(out_path),
        "gaps_out": None if gaps_path is None else str(gaps_path),
        "min_trades": args.min_trades,
        "totals": cov_map["totals"],
        "gap_count": len(gaps),
    })
    return 0


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """CLI 파서를 만든다 (build/coverage 서브커맨드)."""
    parser = argparse.ArgumentParser(
        prog="seed_lattice",
        description="시드 격자 build/coverage CLI (백테스트 실행은 범위 밖)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_build = sub.add_parser("build", help="격자 열거 → 시드 JSON + passport md 생성")
    p_build.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR),
                         help="출력 디렉토리 (기본: docs/research/condition_research/"
                              "generated_conditions/lattice)")
    p_build.add_argument("--families-json", default=None,
                         help="외부 패밀리 JSON (기본 레지스트리와 불변 병합)")
    p_build.add_argument("--family", action="append", default=None,
                         help="생성할 패밀리 이름 (반복 지정, 기본: 전체)")
    p_build.add_argument("--lane", action="append", choices=("tick", "min"),
                         default=None, help="레인 필터 (반복 지정, 기본: 전체)")
    p_build.add_argument("--skip-passports", action="store_true",
                         help="passport md 생성 생략 (seeds JSON 만)")
    p_build.set_defaults(func=_cmd_build)

    p_cov = sub.add_parser("coverage", help="결과 요약 JSON → coverage map/gaps 산출")
    p_cov.add_argument("--seeds", required=True, help="build 산출 lattice_seeds.json 경로")
    p_cov.add_argument("--results", nargs="*", default=None,
                       help="백테스트 결과 요약 JSON 경로들 (없으면 전 셀 gap)")
    p_cov.add_argument("--out", required=True, help="coverage map JSON 출력 경로")
    p_cov.add_argument("--gaps-out", default=None, help="coverage gap JSON 출력 경로")
    p_cov.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES,
                       help=f"셀당 최소 거래수 목표 (기본 {DEFAULT_MIN_TRADES})")
    p_cov.set_defaults(func=_cmd_coverage)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 엔트리포인트 (argv 주입 가능 — 테스트용)."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
