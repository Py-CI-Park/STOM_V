"""Write the append-only ANA03 G0-to-G1 paired decision evidence."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.revision.mcap_event_contract import EventGateContractError
from ai_strategy_loop.revision.mcap_g0_contract import G0BatchEvidence
from ai_strategy_loop.revision.mcap_g1_contract import G1Preregistration
from ai_strategy_loop.revision.mcap_g1_official_contract import G1BatchEvidence
from ai_strategy_loop.revision.mcap_g1_paired_report import build_g0_g1_paired_analysis

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"
DEFAULT_G0 = EVIDENCE / "2026-08-26_res02_g0_official.json"
DEFAULT_G1 = EVIDENCE / "2026-08-26_res03_g1_official.json"
DEFAULT_PREREG = EVIDENCE / "2026-08-26_res03_g1_preregistration.json"
DEFAULT_OUTPUT = EVIDENCE / "2026-08-26_res03_g0_g1_paired_analysis.json"


@dataclass(frozen=True, slots=True)
class CliArgs:
    g0: Path
    g1: Path
    preregistration: Path
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
        raise EventGateContractError("official ANA03 requires a clean tracked worktree")


def run(args: CliArgs) -> None:
    _assert_clean_tracked_worktree()
    if args.output.exists():
        raise EventGateContractError(f"append-only ANA03 output exists: {args.output}")
    report = build_g0_g1_paired_analysis(
        G0BatchEvidence.model_validate_json(args.g0.read_bytes()),
        G1BatchEvidence.model_validate_json(args.g1.read_bytes()),
        G1Preregistration.model_validate_json(args.preregistration.read_bytes()),
        g0_path=args.g0,
        g1_path=args.g1,
        preregistration_path=args.preregistration,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _ = args.output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    print(
        f"[ANA03] verdict={report.verdict} "
        + f"paired_pass={report.paired_pass_count}/{report.candidate_count} "
        + f"development_pass={report.development_rule_pass_count}/{report.candidate_count} "
        + f"output={args.output}",
        flush=True,
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--g0", type=Path, default=DEFAULT_G0)
    _ = parser.add_argument("--g1", type=Path, default=DEFAULT_G1)
    _ = parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREG)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    namespace = parser.parse_args()
    return CliArgs(
        g0=cast(Path, namespace.g0).resolve(),
        g1=cast(Path, namespace.g1).resolve(),
        preregistration=cast(Path, namespace.preregistration).resolve(),
        output=cast(Path, namespace.output).resolve(),
    )


if __name__ == "__main__":
    run(_parse_args())
