"""Generate the preregistered D3 QMC manifest and 40 performance-blind screen sources."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from ai_strategy_loop.revision.mcap_qmc import propose_d3_candidates
from ai_strategy_loop.revision.window_contract import window_contract_from_census

_CENSUS = Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_mcap_census.json")
_OUTPUT = Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json")
_STRATEGIES = Path("utility/ai_agent/strategy/D3_OpeningStateMachine_시총4Band_20260815.txt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", type=Path, default=_CENSUS)
    parser.add_argument("--output", type=Path, default=_OUTPUT)
    parser.add_argument("--strategy-output", type=Path, default=_STRATEGIES)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--per-cell-budget", type=int, default=32)
    parser.add_argument("--selected-per-cell", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    census = json.loads(args.census.read_text(encoding="utf-8"))
    window = window_contract_from_census(census)
    eligible_bands = [row["band_id"] for row in census["bands"] if row["verdict"] == "CENSUS_PASS"]
    batch = propose_d3_candidates(
        window=window, seed=args.seed, per_cell_budget=args.per_cell_budget,
        selected_per_cell=args.selected_per_cell, eligible_bands=eligible_bands,
    )
    selected_ids = {candidate.candidate_id for candidate in batch.selected_candidates}
    payload = {
        "schema": "stom.d3_mcap_qmc_manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authority": batch.authority,
        "can_adopt": False,
        "seed": batch.seed,
        "per_cell_budget": batch.per_cell_budget,
        "raw_count": len(batch.raw_candidates),
        "selected_count": len(batch.selected_candidates),
        "window_contract": window.to_dict(),
        "eligible_bands": eligible_bands,
        "selection": "performance_blind_maximin_two_per_family_band",
        "receipts": batch.receipts,
        "candidates": [
            {**candidate.to_dict(), "selected_for_engine": candidate.candidate_id in selected_ids}
            for candidate in batch.raw_candidates
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(args.output)
    args.strategy_output.parent.mkdir(parents=True, exist_ok=True)
    strategy_text = []
    for candidate in batch.selected_candidates:
        strategy_text.extend(("=" * 100, candidate.candidate_id, candidate.source, ""))
    args.strategy_output.write_text("\n".join(strategy_text), encoding="utf-8")
    print(json.dumps({"raw_count": payload["raw_count"], "selected_count": payload["selected_count"],
                      "output": str(args.output), "strategy_output": str(args.strategy_output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
