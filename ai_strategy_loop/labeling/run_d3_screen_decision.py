"""Seal the D3 screen gate and conditional D4 admission evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_strategy_loop.revision.mcap_screen_decision import decide_d3_screen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_engine_screen.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_screen_decision.json"))
    args = parser.parse_args()
    decision = decide_d3_screen(json.loads(args.screen.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": decision["verdict"], "advanced_count": decision["advanced_count"],
                      "d4_bo": decision["d4_bo"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
