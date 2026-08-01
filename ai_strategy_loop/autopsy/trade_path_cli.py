"""Read-only CLI for QSP7 preflight and bounded real-data smoke analysis."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder, read_trade_rows
from ai_strategy_loop.autopsy.trade_path_analysis import analyze_trade_paths, source_contract
from ai_strategy_loop.autopsy.trade_path_models import Timeframe


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QSP7 거래 경로 read-only 분석")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--timeframe", choices=("tick", "min"), required=True)
    parser.add_argument("--forced-liquidation", type=int, default=93000)
    parser.add_argument("--database-dir", default="_database")
    parser.add_argument("--code-info", default="_database/code_info.db")
    parser.add_argument("--run-id", default="qsp7-cli")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--limit", type=int, default=20, help="분석 거래 상한; 0이면 전체")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    csv_path = Path(args.csv).resolve()
    timeframe = Timeframe(args.timeframe)
    try:
        rows = read_trade_rows(csv_path)
        source = source_contract(
            run_id=args.run_id,
            csv_path=csv_path,
            timeframe=timeframe,
            forced_liquidation_time=args.forced_liquidation,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"available": False, "reason": str(exc)}, ensure_ascii=False))
        return 2
    dates = {
        row.buy_time // (1_000_000 if timeframe is Timeframe.TICK else 10_000)
        for row in rows
    }
    repository = MarketPathRepository(database_dir=Path(args.database_dir))
    covered = sum(1 for date in dates if repository.database_path(date, timeframe) is not None)
    payload: dict[str, object] = {
        "available": True,
        "authority": "diagnostic",
        "source": asdict(source),
        "trade_count": len(rows),
        "date_count": len(dates),
        "covered_date_count": covered,
        "counterfactual_limit": "forced_liquidation_boundary",
    }
    if args.analyze:
        builder = EpisodeBuilder(repository=repository, code_info_db=Path(args.code_info))
        analysis = analyze_trade_paths(
            analysis_id="cli-smoke",
            source=source,
            builder=builder,
            decision_horizons=(30, 60, 90, 120, 180, 300),
            continuation_horizons=(30, 60, 120, 300, 600),
            max_trades=None if args.limit == 0 else max(1, min(args.limit, 100_000)),
        )
        payload["smoke"] = {
            "summary": asdict(analysis.totals),
            "exclusions": [asdict(row) for row in analysis.exclusions[:20]],
            "sample": [asdict(row) for row in analysis.episodes[:5]],
        }
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
