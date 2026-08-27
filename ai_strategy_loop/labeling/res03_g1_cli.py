"""CLI boundary for the official RES-03 G1 runner."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


@dataclass(frozen=True, slots=True)
class CliArgs:
    database: Path
    setting_database: Path
    strategy_database: Path
    g1: Path
    event: Path
    source_preregistration: Path
    source_manifest: Path
    output: Path
    checkpoint: Path
    base_urls: tuple[str, ...]


def parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--database", type=Path, required=True)
    _ = parser.add_argument("--setting-database", type=Path, required=True)
    _ = parser.add_argument("--strategy-database", type=Path, required=True)
    _ = parser.add_argument(
        "--g1", type=Path,
        default=EVIDENCE / "2026-08-26_res03_g1_preregistration.json",
    )
    _ = parser.add_argument(
        "--event", type=Path,
        default=EVIDENCE / "2026-08-26_res02_event_gate.json",
    )
    _ = parser.add_argument(
        "--source-preregistration", type=Path,
        default=EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
    )
    _ = parser.add_argument(
        "--source-manifest", type=Path,
        default=EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )
    _ = parser.add_argument(
        "--output", type=Path,
        default=EVIDENCE / "2026-08-26_res03_g1_official.json",
    )
    _ = parser.add_argument(
        "--checkpoint", type=Path,
        default=ROOT / "ai_strategy_loop/state/res03_g1_official_checkpoint.json",
    )
    _ = parser.add_argument("--base-urls", required=True)
    namespace = parser.parse_args()
    return CliArgs(
        database=cast(Path, namespace.database).resolve(),
        setting_database=cast(Path, namespace.setting_database).resolve(),
        strategy_database=cast(Path, namespace.strategy_database).resolve(),
        g1=cast(Path, namespace.g1).resolve(),
        event=cast(Path, namespace.event).resolve(),
        source_preregistration=cast(Path, namespace.source_preregistration).resolve(),
        source_manifest=cast(Path, namespace.source_manifest).resolve(),
        output=cast(Path, namespace.output).resolve(),
        checkpoint=cast(Path, namespace.checkpoint).resolve(),
        base_urls=tuple(
            value.strip().rstrip("/")
            for value in cast(str, namespace.base_urls).split(",")
            if value.strip()
        ),
    )
