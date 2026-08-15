"""Run the existing-DB market-cap census without mutating source databases."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from ai_strategy_loop.labeling.mcap_census import CensusConfig, scan_mcap_census

_DEFAULT_OUTPUT = Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_mcap_census.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="_database/stock_tick_back.db")
    parser.add_argument("--lane", choices=("stock_tick", "stock_min"), default="stock_tick")
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--progress-every", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    def progress(payload: dict) -> None:
        print(json.dumps({"event": "census_progress", **payload}, ensure_ascii=False), flush=True)

    result = scan_mcap_census(CensusConfig(
        db_path=args.db, lane=args.lane, progress_every=max(1, args.progress_every),
    ), progress=progress)
    result["started_at"] = started_at
    result["completed_at"] = datetime.now(timezone.utc).isoformat()
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"event": "census_completed", "output": str(output), "elapsed_seconds": result["elapsed_seconds"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
