"""A-5 — 백파인더 승자 셋업 채굴 → 밴드 시드 아티팩트(band_seeds.json) 생성 CLI.

fitness/backfinder_principle의 순수 파이프라인(mine_tick_window →
winning_setup_distribution → to_band_seeds)을 오프라인 1회 실행해, 루프 생성
프롬프트가 소비할 수 있는 JSON 아티팩트를 만든다.

계약:
- tick DB는 **읽기 전용**으로만 연다(테이블 열거 + SELECT). 어떤 보호 경로에도 쓰지 않는다.
- 출력은 기본 `ai_strategy_loop/state/band_seeds.json`(gitignored 런타임 상태).
- 이 출력은 **생성 시드 전용**이다(lookahead/survivorship 편향 — backfinder_principle
  모듈 caveat 그대로). 최종 전략이 아니며 holdout/다년 OOS 검증 필수.

사용 예 (subset DB 스모크):
    PYTHONUTF8=1 python -m ai_strategy_loop.scripts.mine_band_seeds \
        --db ai_strategy_loop/state/tick_subset_small.db \
        --days 20250408,20250409 --max-codes 30 \
        --out ai_strategy_loop/state/band_seeds.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401  (env-before-import 계약)
from ai_strategy_loop.fitness.backfinder_principle import (  # noqa: E402
    DEFAULT_LOOKAHEAD_TICKS,
    DEFAULT_THRESHOLD_PCT,
    DEFAULT_TIME_HI,
    DEFAULT_TIME_LO,
    mine_tick_window,
    to_band_seeds,
    winning_setup_distribution,
)

BAND_SEEDS_SCHEMA = "band_seed_hint_v1"
DEFAULT_OUT = _PROJECT_ROOT / "ai_strategy_loop" / "state" / "band_seeds.json"


def _list_stock_tables(db_path: str, max_codes: int) -> List[str]:
    """tick DB의 종목 테이블 이름을 결정론적 정렬로 최대 max_codes개 나열한다(읽기 전용)."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        finally:
            con.close()
    except Exception:  # noqa: BLE001 — 없는 DB 등은 빈 목록(무예외 계약)
        return []
    names = [r[0] for r in rows if r and r[0] and not str(r[0]).startswith("sqlite_")]
    return names[: max(0, int(max_codes))]


def serialize_seeds(seeds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """to_band_seeds 출력(BandSpec 포함)을 JSON-safe dict 목록으로 직렬화한다."""
    out: List[Dict[str, Any]] = []
    for seed in seeds:
        bands = [
            {"var": b.var, "op": b.op, "lo": b.lo, "hi": b.hi}
            for b in (seed.get("band_specs") or [])
        ]
        out.append({
            "time_segment": seed.get("time_segment"),
            "market_cap_segment": seed.get("market_cap_segment"),
            "winner_rate": seed.get("winner_rate"),
            "lift": seed.get("lift"),
            "bands": bands,
            "nl_guide": seed.get("nl_guide"),
        })
    return out


def build_artifact(
    *,
    db_path: str,
    days: Sequence[int],
    codes: Optional[Sequence[str]] = None,
    max_codes: int = 50,
    time_lo: int = DEFAULT_TIME_LO,
    time_hi: int = DEFAULT_TIME_HI,
    lookahead_ticks: int = DEFAULT_LOOKAHEAD_TICKS,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
    min_lift: float = 1.0,
    min_count: int = 30,
) -> Dict[str, Any]:
    """채굴→분포→시드 파이프라인을 실행해 아티팩트 dict를 만든다(무예외 지향)."""
    resolved_codes = list(codes) if codes else _list_stock_tables(db_path, max_codes)
    mined = mine_tick_window(
        db_path, resolved_codes, list(days),
        time_lo=time_lo, time_hi=time_hi,
        lookahead_ticks=lookahead_ticks, threshold_pct=threshold_pct,
    )
    frame = mined.get("all")
    distribution: List[Dict[str, Any]] = []
    if frame is not None and len(frame) > 0:
        distribution = winning_setup_distribution(frame, min_count=min_count)
    seeds = to_band_seeds(distribution, min_lift=min_lift)
    return {
        "schema": BAND_SEEDS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "db_path": str(db_path),
            "days": [int(d) for d in days],
            "codes_count": len(resolved_codes),
            "time_lo": time_lo, "time_hi": time_hi,
            "lookahead_ticks": lookahead_ticks, "threshold_pct": threshold_pct,
            "min_lift": min_lift, "min_count": min_count,
        },
        "caveat": "generation-seed-only: lookahead/survivorship bias — OOS validation required",
        "row_count": int(mined.get("rows") or 0),
        "winner_count": int(mined.get("winner_count") or 0),
        "seeds": serialize_seeds(seeds),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mine_band_seeds",
        description="백파인더 승자 셋업 채굴 → band_seeds.json 아티팩트 생성(읽기 전용 채굴).",
    )
    parser.add_argument("--db", required=True, help="tick DB 경로(subset 권장).")
    parser.add_argument("--days", required=True,
                        help="쉼표 구분 YYYYMMDD 목록 (예: 20250408,20250409).")
    parser.add_argument("--codes", default="",
                        help="쉼표 구분 종목 테이블명. 비우면 DB에서 --max-codes개 자동 열거.")
    parser.add_argument("--max-codes", type=int, default=50)
    parser.add_argument("--time-lo", type=int, default=DEFAULT_TIME_LO)
    parser.add_argument("--time-hi", type=int, default=DEFAULT_TIME_HI)
    parser.add_argument("--lookahead-ticks", type=int, default=DEFAULT_LOOKAHEAD_TICKS)
    parser.add_argument("--threshold-pct", type=float, default=DEFAULT_THRESHOLD_PCT)
    parser.add_argument("--min-lift", type=float, default=1.0)
    parser.add_argument("--min-count", type=int, default=30)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    days = [int(d) for d in str(args.days).split(",") if d.strip()]
    codes = [c.strip() for c in str(args.codes).split(",") if c.strip()] or None
    artifact = build_artifact(
        db_path=args.db, days=days, codes=codes, max_codes=args.max_codes,
        time_lo=args.time_lo, time_hi=args.time_hi,
        lookahead_ticks=args.lookahead_ticks, threshold_pct=args.threshold_pct,
        min_lift=args.min_lift, min_count=args.min_count,
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sys.stdout.write(json.dumps({
        "out": str(out_path),
        "row_count": artifact["row_count"],
        "winner_count": artifact["winner_count"],
        "seed_count": len(artifact["seeds"]),
    }, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
