from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar

import pytest

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.labeling.run_res02_g0_official import SELL_SOURCE
from ai_strategy_loop.revision import mcap_g0_recovery
from ai_strategy_loop.revision.mcap_g0_inputs import load_sealed_g0_plan
from ai_strategy_loop.revision.mcap_g0_recovery import recover_terminal_attempts

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/research/quant_scoring_pipeline/evidence"


class FakeDashboardClient:
    rows: ClassVar[list[JsonValue]] = []

    def __init__(self, base_url: str) -> None:
        self.base_url: str = base_url

    def call(
        self,
        method: str,
        path: str,
        body: dict[str, JsonValue] | None = None,
    ) -> dict[str, JsonValue]:
        del method, body
        if path == "/bt/jobs":
            return {"jobs": self.rows}
        if path.startswith("/bt/result"):
            return {"metrics": None}
        if path.startswith("/research-truth"):
            return {"truth_available": False, "reason": "test_truth_unavailable"}
        return {"bundle_available": False, "reason": "test_bundle_unavailable"}


def test_recovery_accepts_only_exact_sealed_terminal_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = load_sealed_g0_plan(
        EVIDENCE / "2026-08-26_res02_event_gate.json",
        EVIDENCE / "2026-08-26_res01_lt3000_prereg.json",
        EVIDENCE / "2026-08-15_d3_candidate_manifest.json",
    )
    task = plan.tasks[0]
    profile = plan.preregistration.official_execution
    exact_spec: dict[str, JsonValue] = {
        "buy_code": task.candidate.source,
        "sell_code": SELL_SOURCE,
        "start": task.fold.start,
        "end": task.fold.end,
        "start_time": profile.start_time,
        "end_time": profile.end_time,
        "timeframe": profile.timeframe,
        "engines": profile.engines_per_job,
        "timeout": profile.job_timeout_seconds,
    }
    hashes: dict[str, JsonValue] = {
        "buy": task.candidate.source_sha256,
        "sell": hashlib.sha256(SELL_SOURCE.encode("utf-8")).hexdigest(),
    }
    FakeDashboardClient.rows = [
        {
            "job_id": "exact-job",
            "status": "error",
            "created_at": 1.0,
            "started_at": 2.0,
            "finished_at": 5.0,
            "spec": exact_spec,
            "strategy_db_snapshot_hashes": hashes,
        },
        {
            "job_id": "changed-period",
            "status": "error",
            "created_at": 2.0,
            "spec": {**exact_spec, "end": task.fold.end + 1},
            "strategy_db_snapshot_hashes": hashes,
        },
    ]
    monkeypatch.setattr(mcap_g0_recovery, "DashboardClient", FakeDashboardClient)

    attempts = recover_terminal_attempts(
        task=task,
        profile=profile,
        sell_source=SELL_SOURCE,
        base_url="http://127.0.0.1:1",
        manager_id="manager",
        max_attempts=2,
    )

    assert len(attempts) == 1
    assert attempts[0].job_id == "exact-job"
    assert attempts[0].elapsed_seconds == 3.0
