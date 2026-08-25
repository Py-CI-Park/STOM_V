"""Build the append-only ANA02 structural autopsy from official RES-02 G0."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_autopsy import build_g0_structural_autopsy
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchEvidence
from ai_strategy_loop.revision.mcap_g0_inputs import load_sealed_g0_plan

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"
DEFAULT_SOURCE = EVIDENCE / "2026-08-26_res02_g0_official.json"
DEFAULT_EVENT = EVIDENCE / "2026-08-26_res02_event_gate.json"
DEFAULT_PREREG = EVIDENCE / "2026-08-26_res01_lt3000_prereg.json"
DEFAULT_MANIFEST = EVIDENCE / "2026-08-15_d3_candidate_manifest.json"
DEFAULT_OUTPUT = EVIDENCE / "2026-08-26_res02_g0_structural_autopsy.json"


@dataclass(frozen=True, slots=True)
class CliArgs:
    source: Path
    event: Path
    prereg: Path
    manifest: Path
    output: Path


def _assert_clean_tracked_worktree() -> None:
    completed = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=no"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.stdout.strip():
        raise EventGateContractError("official ANA02 requires a clean tracked worktree")


def run(args: CliArgs) -> None:
    _assert_clean_tracked_worktree()
    if args.output.exists():
        raise EventGateContractError(f"append-only ANA02 output exists: {args.output}")
    g0 = G0BatchEvidence.model_validate_json(args.source.read_bytes())
    plan = load_sealed_g0_plan(args.event, args.prereg, args.manifest)
    report = build_g0_structural_autopsy(
        g0,
        plan.preregistration,
        source_file=args.source,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _ = args.output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    print(
        f"[ANA02] verdict={report.verdict} "
        + f"rule_pass={report.g0_development_rule_pass_count}/{report.candidate_count} "
        + f"output={args.output}",
        flush=True,
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    _ = parser.add_argument("--event", type=Path, default=DEFAULT_EVENT)
    _ = parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    _ = parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    namespace = parser.parse_args()
    return CliArgs(
        source=cast(Path, namespace.source).resolve(),
        event=cast(Path, namespace.event).resolve(),
        prereg=cast(Path, namespace.prereg).resolve(),
        manifest=cast(Path, namespace.manifest).resolve(),
        output=cast(Path, namespace.output).resolve(),
    )


if __name__ == "__main__":
    run(_parse_args())
