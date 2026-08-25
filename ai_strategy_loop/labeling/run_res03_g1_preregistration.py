"""Write append-only RES-03 G1 preregistration and strategy sources."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g1_generation import (
    build_g1_preregistration,
    render_strategy_text,
)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"
DEFAULT_OUTPUT = EVIDENCE / "2026-08-26_res03_g1_preregistration.json"
DEFAULT_STRATEGY_OUTPUT = ROOT / "utility/ai_agent/strategy/RES03_G1_STRUCTURE_20260826.txt"


@dataclass(frozen=True, slots=True)
class CliArgs:
    output: Path
    strategy_output: Path


def _assert_clean_tracked_worktree() -> None:
    completed = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=no"), cwd=ROOT,
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    if completed.stdout.strip():
        raise EventGateContractError("official G1 preregistration requires clean tracked worktree")


def run(args: CliArgs) -> None:
    _assert_clean_tracked_worktree()
    if args.output.exists() or args.strategy_output.exists():
        raise EventGateContractError("append-only G1 preregistration output already exists")
    report = build_g1_preregistration(
        autopsy_path=EVIDENCE / "2026-08-26_res02_g0_structural_autopsy.json",
        event_path=EVIDENCE / "2026-08-26_res02_event_gate.json",
        preregistration_path=EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        manifest_path=EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
        strategy_reference_path=ROOT / "utility/ai_agent/strategy.txt",
        rules_reference_path=ROOT / "utility/ai_agent/rules.txt",
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.strategy_output.parent.mkdir(parents=True, exist_ok=True)
    _ = args.output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    _ = args.strategy_output.write_text(render_strategy_text(report), encoding="utf-8")
    print(
        f"[RES03_G1_PREREG] candidates={report.candidate_count} "
        + f"tasks={report.task_count} output={args.output}", flush=True,
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    _ = parser.add_argument("--strategy-output", type=Path, default=DEFAULT_STRATEGY_OUTPUT)
    namespace = parser.parse_args()
    return CliArgs(
        output=cast(Path, namespace.output).resolve(),
        strategy_output=cast(Path, namespace.strategy_output).resolve(),
    )


if __name__ == "__main__":
    run(_parse_args())
