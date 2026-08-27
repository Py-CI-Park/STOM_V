from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from ai_strategy_loop.dashboard.analysis_bundle_builder import (
    build_legacy_job_analysis_bundle,
)
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import project_legacy_job_truth
from ai_strategy_loop.revision.mcap_g0_contract import (
    G0Attempt,
    G0Checkpoint,
    G0JobEvidence,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "research_truth_ui"


def test_checkpoint_roundtrips_nested_analysis_bundle_alias() -> None:
    record = TypeAdapter(dict[str, JsonValue]).validate_json(
        (FIXTURES / "ux_fixture_error.json").read_bytes()
    )
    truth = project_legacy_job_truth(
        record,
        manager_id="checkpoint-test",
        jobs_dir=FIXTURES.as_posix(),
        log_size_bytes=None,
    )
    bundle = build_legacy_job_analysis_bundle(record, truth, None)
    attempt = G0Attempt(
        attempt=1,
        manager_id="checkpoint-test",
        base_url="http://127.0.0.1:1",
        job_id="job",
        raw_status="error",
        runner_poll_timeout=False,
        transport_error=False,
        elapsed_seconds=1.0,
        source_snapshot_match=True,
        truth=truth,
        truth_unavailable_reason=None,
        analysis_bundle=bundle,
        bundle_unavailable_reason=None,
        metrics=None,
        submission_error=None,
    )
    job = G0JobEvidence(
        task_id="candidate::fold",
        candidate_id="candidate",
        family_id="family",
        fold_id="fold",
        start=20220101,
        end=20220131,
        buy_source_sha256="a" * 64,
        sell_source_sha256="b" * 64,
        attempts=(attempt,),
        final_execution=truth.execution,
        final_failure_cause=truth.failure_cause,
        valid_execution=False,
    )
    checkpoint = G0Checkpoint(batch_identity_sha256="c" * 64, jobs=(job,))

    encoded = checkpoint.model_dump_json(by_alias=True)
    restored = G0Checkpoint.model_validate_json(encoded)

    assert '"schema":"stom.analysis_bundle.v2"' in encoded
    assert restored == checkpoint
