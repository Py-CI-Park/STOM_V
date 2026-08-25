"""Execute sealed RES-03 G1 candidates on the official development folds."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.labeling.run_res02_g0_official import SELL_SOURCE
from ai_strategy_loop.revision.mcap_event_contract import (
    EventGateContractError,
    SourceFingerprint,
)
from ai_strategy_loop.revision.mcap_g0_client import execute_task
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0JobEvidence,
    G0Task,
)
from ai_strategy_loop.revision.mcap_g0_http import DashboardClient
from ai_strategy_loop.revision.mcap_g0_recovery import recover_terminal_attempts
from ai_strategy_loop.revision.mcap_g1_inputs import SealedG1Plan, load_sealed_g1_plan
from ai_strategy_loop.revision.mcap_g1_official_contract import (
    G1BatchEvidence,
    G1Checkpoint,
)
from ai_strategy_loop.revision.mcap_g1_report import build_g1_report
from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    sqlite_fingerprint,
    sqlite_sidefile_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"
DEFAULT_OUTPUT = EVIDENCE / "2026-08-26_res03_g1_official.json"
DEFAULT_CHECKPOINT = ROOT / "ai_strategy_loop/state/res03_g1_official_checkpoint.json"


@dataclass(frozen=True, slots=True)
class CliArgs:
    database: Path
    g1: Path
    event: Path
    source_preregistration: Path
    source_manifest: Path
    output: Path
    checkpoint: Path
    base_urls: tuple[str, ...]


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments), cwd=ROOT, check=True, capture_output=True,
        text=True, encoding="utf-8",
    )
    return completed.stdout.strip()


def _assert_clean_tracked_worktree() -> None:
    if _git_value("status", "--porcelain", "--untracked-files=no"):
        raise EventGateContractError("official G1 requires a clean tracked worktree")


def _validate_runtime(
    plan: SealedG1Plan, database: Path, base_urls: tuple[str, ...]
) -> SourceFingerprint:
    profile = plan.preregistration.official_execution
    if not base_urls or len(base_urls) > profile.manager_workers_max:
        raise EventGateContractError("manager URL count violates G1 preregistration")
    if hashlib.sha256(SELL_SOURCE.encode("utf-8")).hexdigest() != profile.sell_source_sha256:
        raise EventGateContractError("sealed G1 sell source identity mismatch")
    fingerprint = SourceFingerprint.model_validate(sqlite_fingerprint(database))
    expected = plan.database_expected
    if (
        fingerprint.size != expected.size
        or fingerprint.hash_mode != expected.hash_mode
        or fingerprint.sha256 != expected.sha256
    ):
        raise EventGateContractError("official G1 database identity mismatch")
    for base_url in base_urls:
        health = DashboardClient(base_url).call("GET", "/health")
        if health.get("status") not in {"ok", "healthy"}:
            raise EventGateContractError(f"G1 dashboard manager is unhealthy: {base_url}")
    return fingerprint


def _load_checkpoint(path: Path, plan: SealedG1Plan) -> dict[str, G0JobEvidence]:
    if not path.exists():
        return {}
    checkpoint = G1Checkpoint.model_validate_json(path.read_bytes())
    if checkpoint.batch_identity_sha256 != plan.batch_identity_sha256:
        raise EventGateContractError("official G1 checkpoint identity mismatch")
    rows = {row.task_id: row for row in checkpoint.jobs}
    allowed = {task.task_id for task in plan.tasks}
    if len(rows) != len(checkpoint.jobs) or not set(rows).issubset(allowed):
        raise EventGateContractError("official G1 checkpoint task set is invalid")
    return rows


def _write_checkpoint(
    path: Path, plan: SealedG1Plan, rows: dict[str, G0JobEvidence]
) -> None:
    ordered = tuple(rows[task.task_id] for task in plan.tasks if task.task_id in rows)
    payload = G1Checkpoint(
        batch_identity_sha256=plan.batch_identity_sha256, jobs=ordered
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    _ = temporary.write_text(
        payload.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    _ = temporary.replace(path)


def _run_jobs(
    plan: SealedG1Plan,
    base_urls: tuple[str, ...],
    checkpoint_path: Path,
) -> tuple[G0JobEvidence, ...]:
    completed = _load_checkpoint(checkpoint_path, plan)
    task_index = {task.task_id: index for index, task in enumerate(plan.tasks)}
    pending = tuple(task for task in plan.tasks if task.task_id not in completed)
    profile = plan.preregistration.official_execution
    recovered: dict[str, tuple[G0Attempt, ...]] = {}
    for task in pending:
        index = task_index[task.task_id] % len(base_urls)
        recovered[task.task_id] = recover_terminal_attempts(
            task=task, profile=profile, sell_source=SELL_SOURCE,
            base_url=base_urls[index], manager_id=f"res03-g1-manager-{index + 1}",
            max_attempts=profile.infrastructure_retry_max + 1,
        )

    def execute(task: G0Task) -> G0JobEvidence:
        index = task_index[task.task_id] % len(base_urls)
        return execute_task(
            task=task, profile=profile, sell_source=SELL_SOURCE,
            base_url=base_urls[index], manager_id=f"res03-g1-manager-{index + 1}",
            prior_attempts=recovered[task.task_id],
        )

    with ThreadPoolExecutor(max_workers=len(base_urls)) as executor:
        futures = {executor.submit(execute, task): task for task in pending}
        for future in as_completed(futures):
            row = future.result()
            completed[row.task_id] = row
            _write_checkpoint(checkpoint_path, plan, completed)
            print(
                f"[RES03_G1] completed={len(completed)}/{len(plan.tasks)} "
                + f"task={row.task_id} execution={row.final_execution} valid={row.valid_execution}",
                flush=True,
            )
    return tuple(completed[task.task_id] for task in plan.tasks)


def run(args: CliArgs) -> G1BatchEvidence:
    _assert_clean_tracked_worktree()
    plan = load_sealed_g1_plan(
        args.g1, args.event, args.source_preregistration, args.source_manifest
    )
    before = sqlite_sidefile_snapshot(args.database)
    database = _validate_runtime(plan, args.database, args.base_urls)
    jobs = _run_jobs(plan, args.base_urls, args.checkpoint)
    assert_sqlite_sidefiles_unchanged(args.database, before)
    return build_g1_report(
        plan, database, args.base_urls, jobs,
        generated_at=datetime.now(timezone.utc).isoformat(),
        implementation_branch=_git_value("branch", "--show-current"),
        implementation_head_sha=_git_value("rev-parse", "HEAD"),
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--database", type=Path, required=True)
    _ = parser.add_argument("--g1", type=Path, default=EVIDENCE / "2026-08-26_res03_g1_preregistration.json")
    _ = parser.add_argument("--event", type=Path, default=EVIDENCE / "2026-08-26_res02_event_gate.json")
    _ = parser.add_argument("--source-preregistration", type=Path, default=EVIDENCE / "2026-08-26_res01_lt3000_prereg.json")
    _ = parser.add_argument("--source-manifest", type=Path, default=EVIDENCE / "2026-08-15_d3_candidate_manifest.json")
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    _ = parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    _ = parser.add_argument("--base-urls", required=True)
    namespace = parser.parse_args()
    return CliArgs(
        database=cast(Path, namespace.database).resolve(), g1=cast(Path, namespace.g1).resolve(),
        event=cast(Path, namespace.event).resolve(),
        source_preregistration=cast(Path, namespace.source_preregistration).resolve(),
        source_manifest=cast(Path, namespace.source_manifest).resolve(),
        output=cast(Path, namespace.output).resolve(), checkpoint=cast(Path, namespace.checkpoint).resolve(),
        base_urls=tuple(value.strip().rstrip("/") for value in cast(str, namespace.base_urls).split(",") if value.strip()),
    )


def main() -> None:
    args = _parse_args()
    if args.output.exists():
        raise EventGateContractError(f"append-only G1 output already exists: {args.output}")
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _ = args.output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    print(
        f"[RES03_G1] verdict={report.platform_verdict} "
        + f"valid={report.valid_execution_count}/{report.config.task_count} output={args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
