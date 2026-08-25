"""Execute the sealed RES-02 G0 candidates on official development folds."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from ai_strategy_loop.revision.mcap_event_contract import (
    EventGateContractError,
    SourceFingerprint,
)
from ai_strategy_loop.revision.mcap_g0_client import execute_task
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0BatchEvidence,
    G0Checkpoint,
    G0JobEvidence,
    G0Task,
)
from ai_strategy_loop.revision.mcap_g0_http import DashboardClient
from ai_strategy_loop.revision.mcap_g0_inputs import SealedG0Plan, load_sealed_g0_plan
from ai_strategy_loop.revision.mcap_g0_recovery import recover_terminal_attempts
from ai_strategy_loop.revision.mcap_g0_report import build_g0_report
from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    sqlite_fingerprint,
    sqlite_sidefile_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENT = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res02_event_gate.json"
)
DEFAULT_PREREG = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res01_lt3000_prereg.json"
)
DEFAULT_MANIFEST = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-15_d3_candidate_manifest.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "docs/research/quant_scoring_pipeline/evidence/2026-08-26_res02_g0_official.json"
)
DEFAULT_CHECKPOINT = ROOT / "ai_strategy_loop/state/res02_g0_official_checkpoint.json"
SELL_SOURCE = """# D3 baseline risk/time exit · development only
매도 = False
if 수익률 <= -2.0:
    매도 = True
elif 수익률 >= 3.0:
    매도 = True
elif 보유시간 >= 300:
    매도 = True
elif 시분초 >= 92900:
    매도 = True

if 매도:
    self.Sell()
"""


@dataclass(frozen=True, slots=True)
class CliArgs:
    database: Path
    event: Path
    prereg: Path
    manifest: Path
    output: Path
    checkpoint: Path
    base_urls: tuple[str, ...]


def _git_value(*arguments: str) -> str:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _assert_clean_tracked_worktree() -> None:
    if _git_value("status", "--porcelain", "--untracked-files=no"):
        raise EventGateContractError("official G0 requires a clean tracked worktree")


def _validate_runtime(
    plan: SealedG0Plan, database: Path, base_urls: tuple[str, ...]
) -> SourceFingerprint:
    profile = plan.preregistration.official_execution
    if not base_urls or len(base_urls) > profile.manager_workers_max:
        raise EventGateContractError("manager URL count violates preregistration")
    if (
        hashlib.sha256(SELL_SOURCE.encode("utf-8")).hexdigest()
        != profile.sell_source_sha256
    ):
        raise EventGateContractError("sealed sell source identity mismatch")
    fingerprint = SourceFingerprint.model_validate(sqlite_fingerprint(database))
    if (
        fingerprint.size != plan.event_gate.database.size_bytes
        or fingerprint.hash_mode != plan.event_gate.database.fingerprint_mode
        or fingerprint.sha256 != plan.event_gate.database.fingerprint_sha256
    ):
        raise EventGateContractError("official G0 database identity mismatch")
    for base_url in base_urls:
        health = DashboardClient(base_url).call("GET", "/health")
        if health.get("status") not in {"ok", "healthy"}:
            raise EventGateContractError(f"dashboard manager is unhealthy: {base_url}")
    return fingerprint


def _load_checkpoint(path: Path, plan: SealedG0Plan) -> dict[str, G0JobEvidence]:
    if not path.exists():
        return {}
    checkpoint = G0Checkpoint.model_validate_json(path.read_text(encoding="utf-8"))
    if checkpoint.batch_identity_sha256 != plan.batch_identity_sha256:
        raise EventGateContractError("official G0 checkpoint identity mismatch")
    rows = {row.task_id: row for row in checkpoint.jobs}
    if len(rows) != len(checkpoint.jobs):
        raise EventGateContractError("official G0 checkpoint contains duplicate tasks")
    allowed = {task.task_id for task in plan.tasks}
    if not set(rows).issubset(allowed):
        raise EventGateContractError("official G0 checkpoint contains unknown tasks")
    return rows


def _write_checkpoint(
    path: Path, plan: SealedG0Plan, rows: dict[str, G0JobEvidence]
) -> None:
    ordered = tuple(rows[task.task_id] for task in plan.tasks if task.task_id in rows)
    payload = G0Checkpoint(
        batch_identity_sha256=plan.batch_identity_sha256, jobs=ordered
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    _ = temporary.write_text(payload.model_dump_json(indent=2) + "\n", encoding="utf-8")
    _ = temporary.replace(path)


def _run_jobs(
    plan: SealedG0Plan,
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
            task=task,
            profile=profile,
            sell_source=SELL_SOURCE,
            base_url=base_urls[index],
            manager_id=f"res02-g0-manager-{index + 1}",
            max_attempts=profile.infrastructure_retry_max + 1,
        )

    def execute(task: G0Task) -> G0JobEvidence:
        index = task_index[task.task_id] % len(base_urls)
        return execute_task(
            task=task,
            profile=profile,
            sell_source=SELL_SOURCE,
            base_url=base_urls[index],
            manager_id=f"res02-g0-manager-{index + 1}",
            prior_attempts=recovered[task.task_id],
        )

    with ThreadPoolExecutor(max_workers=len(base_urls)) as executor:
        futures = {executor.submit(execute, task): task for task in pending}
        for future in as_completed(futures):
            row = future.result()
            completed[row.task_id] = row
            _write_checkpoint(checkpoint_path, plan, completed)
            print(
                f"[RES02_G0] completed={len(completed)}/{len(plan.tasks)} "
                + f"task={row.task_id} execution={row.final_execution} valid={row.valid_execution}",
                flush=True,
            )
    return tuple(completed[task.task_id] for task in plan.tasks)


def run(args: CliArgs) -> G0BatchEvidence:
    _assert_clean_tracked_worktree()
    plan = load_sealed_g0_plan(args.event, args.prereg, args.manifest)
    before = sqlite_sidefile_snapshot(args.database)
    database = _validate_runtime(plan, args.database, args.base_urls)
    jobs = _run_jobs(plan, args.base_urls, args.checkpoint)
    assert_sqlite_sidefiles_unchanged(args.database, before)
    return build_g0_report(
        plan,
        database,
        args.base_urls,
        jobs,
        generated_at=datetime.now(timezone.utc).isoformat(),
        implementation_branch=_git_value("branch", "--show-current"),
        implementation_head_sha=_git_value("rev-parse", "HEAD"),
    )


def _parse_args() -> CliArgs:
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--database", type=Path, required=True)
    _ = parser.add_argument("--event", type=Path, default=DEFAULT_EVENT)
    _ = parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    _ = parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    _ = parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    _ = parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    _ = parser.add_argument("--base-urls", required=True)
    namespace = parser.parse_args()
    return CliArgs(
        database=cast(Path, namespace.database).resolve(),
        event=cast(Path, namespace.event).resolve(),
        prereg=cast(Path, namespace.prereg).resolve(),
        manifest=cast(Path, namespace.manifest).resolve(),
        output=cast(Path, namespace.output).resolve(),
        checkpoint=cast(Path, namespace.checkpoint).resolve(),
        base_urls=tuple(
            value.strip().rstrip("/")
            for value in cast(str, namespace.base_urls).split(",")
            if value.strip()
        ),
    )


def main() -> None:
    args = _parse_args()
    if args.output.exists():
        raise EventGateContractError(
            f"append-only G0 output already exists: {args.output}"
        )
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _ = args.output.write_text(
        report.model_dump_json(indent=2, by_alias=True) + "\n", encoding="utf-8"
    )
    print(
        f"[RES02_G0] verdict={report.platform_verdict} "
        + f"valid={report.valid_execution_count}/{report.config.task_count} output={args.output}",
        flush=True,
    )


if __name__ == "__main__":
    main()
