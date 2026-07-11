from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_strategy_loop.scripts.run_canonical_mini_loop import (
    DEFAULT_PROFILE,
    MiniLoopConfig,
    REFUSAL_OPERATING_DB_PATH,
    run_mini_loop,
)


class FakeClock:
    def __init__(self, *, start: float = 0.0, step: float = 1.0) -> None:
        self.value = start
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.proposals_seen = 0

    def propose_pack(self, *, round_no: int, feedback: list[dict]) -> list[dict]:
        self.calls += 1
        self.proposals_seen += 4
        suffix = f"r{round_no}"
        return [
            self._proposal(f"{suffix}-repair-a", "repair", "momentum", "체결강도 > 100", 0.2),
            self._proposal(f"{suffix}-repair-b", "repair", "volatility", "등락율 < 5", 0.3),
            self._proposal(
                f"{suffix}-discovery-a",
                "discovery",
                "momentum",
                f"체결강도 >= {round_no}.0",
                0.9,
            ),
            self._proposal(f"{suffix}-discovery-b", "discovery", "breadth", "등락율 < -3", 0.7),
        ]

    @staticmethod
    def _proposal(candidate_id: str, lane: str, family: str, expression: str, novelty: float) -> dict:
        return {
            "candidate_id": candidate_id,
            "lane": lane,
            "family": family,
            "expression": expression,
            "buy": expression,
            "sell": "보유시간 >= 1",
            "family": family,
            "timeframe": "min",
            "novelty": novelty,
            "threshold_provenance": {
                "estimator": "fake",
                "parameters": {"round": candidate_id},
                "fit_role": "unit",
                "period": "tmp",
                "row_count": 12,
                "row_signature": "fake-rowset",
                "dataset_sha": "a" * 64,
                "fold_id": "fold-1",
                "source_receipt": "fake-receipt",
            },
        }


class FakeEvaluator:
    def __init__(self, *, mutate_manifest_after_first: bool = False) -> None:
        self.calls: list[tuple[str, str]] = []
        self.mutate_manifest_after_first = mutate_manifest_after_first
        self._mutated = False

    def evaluate(self, candidate: dict, *, kind: str, arm: str | None, context: dict) -> dict:
        self.calls.append((kind, arm or ""))
        if self.mutate_manifest_after_first and not self._mutated:
            self._mutated = True
            con = sqlite3.connect(context["strategy_db"])
            try:
                con.execute(
                    "UPDATE evaluation_manifests SET payload_json = ? WHERE role = 'CL-R07'",
                    (json.dumps({"tampered": True}),),
                )
                con.commit()
            finally:
                con.close()
        base = 10.0 + len(self.calls)
        return {
            "status": "ok",
            "profit": base,
            "mdd": 1.0,
            "trade_count": 40,
            "daily_freq": 0.8,
            "clause": candidate.get("expression", "control"),
        }


def _read_payloads(db_path: Path, table: str) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(f"SELECT payload_json FROM {table} ORDER BY created_at").fetchall()
    finally:
        con.close()
    return [json.loads(row["payload_json"]) for row in rows]


def _run(tmp_path: Path, **kwargs):
    provider = kwargs.pop("provider", FakeProvider())
    evaluator = kwargs.pop("evaluator", FakeEvaluator())
    clock = kwargs.pop("clock", FakeClock())
    summary = run_mini_loop(
        MiniLoopConfig(
            strategy_db=tmp_path / "isolated.sqlite",
            evidence_dir=tmp_path / "evidence",
            **kwargs,
        ),
        provider=provider,
        evaluator=evaluator,
        clock=clock,
    )
    return summary, provider, evaluator


def test_help_exits_zero_without_required_args():
    script = Path("ai_strategy_loop/scripts/run_canonical_mini_loop.py")
    result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)

    assert result.returncode == 0
    assert "--strategy-db" in result.stdout
    assert "--evidence-dir" in result.stdout


def test_happy_three_round_fake_run_freezes_preregistration_and_writes_only_tmp(tmp_path):
    protected = [Path("_database"), Path("ai_strategy_loop/state")]
    before = {path: path.stat().st_mtime_ns for path in protected if path.exists()}

    summary, provider, evaluator = _run(tmp_path)

    assert summary["status"] == "GO_PROCESS_PROOF"
    assert summary["provider_calls"] == 3
    assert provider.proposals_seen == 12
    assert summary["rounds"] == 3
    assert summary["official_evaluations"] == 3
    assert summary["controls"] == {"positive": 1, "negative": 1}
    assert summary["ablation_valid"] is True
    assert summary["ablation_arms"] == 4
    assert summary["feedback_consumptions"] == 2
    assert summary["learning_chain_ok"] is True
    assert len(evaluator.calls) == 9

    manifests = _read_payloads(tmp_path / "isolated.sqlite", "evaluation_manifests")
    assert {manifest["role"] for manifest in manifests} == {"CL-R07", "CL-R08", "CL-R09", "CL-R10"}
    receipts = _read_payloads(tmp_path / "isolated.sqlite", "run_receipts")
    freeze = next(receipt for receipt in receipts if receipt["phase_id"] == "preregistration_frozen_at")
    first_eval = next(receipt for receipt in receipts if receipt["phase_id"] == "evaluation:primary:round_1")
    assert freeze["created_at"] < first_eval["created_at"]
    for manifest in manifests:
        assert manifest["created_at"] < first_eval["created_at"]

    consumptions = _read_payloads(tmp_path / "isolated.sqlite", "feedback_consumptions")
    assert len(consumptions) == 2
    assert all(Path(path).resolve().is_relative_to(tmp_path.resolve()) for path in summary["written_paths"])
    after = {path: path.stat().st_mtime_ns for path in protected if path.exists()}
    assert after == before


def test_wrong_profile_fails_closed_before_state_provider_or_evaluator(tmp_path):
    provider = FakeProvider()
    evaluator = FakeEvaluator()

    summary = run_mini_loop(
        MiniLoopConfig(
            strategy_db=tmp_path / "isolated.sqlite",
            evidence_dir=tmp_path / "evidence",
            profile="something_else",
        ),
        provider=provider,
        evaluator=evaluator,
        clock=FakeClock(),
    )

    assert summary["status"] == "NO_GO_PROFILE_MISMATCH"
    assert summary["stop_reason"] == "profile_mismatch"
    assert summary["provider_calls"] == 0
    assert summary["official_evaluations"] == 0
    assert summary["total_official_evaluation_spend"] == 0
    assert provider.calls == 0
    assert evaluator.calls == []
    assert not (tmp_path / "isolated.sqlite").exists()
    assert not (tmp_path / "evidence").exists()


def test_default_profile_remains_happy_path(tmp_path):
    summary, provider, evaluator = _run(tmp_path, profile=DEFAULT_PROFILE)

    assert summary["status"] == "GO_PROCESS_PROOF"
    assert provider.calls == 3
    assert len(evaluator.calls) == 9


def test_provider_budget_refuses_fourth_pack_before_extra_call(tmp_path):
    summary, provider, evaluator = _run(tmp_path, max_rounds=4)

    assert summary["status"] == "NO_GO_BUDGET_EXHAUSTED"
    assert summary["stop_reason"] == "no_go_budget_exhausted"
    assert summary["provider_calls"] == 3
    assert provider.calls == 3
    assert len(evaluator.calls) == 3


def test_official_evaluation_budget_refuses_tenth_evaluation(tmp_path):
    summary, _provider, evaluator = _run(tmp_path, force_extra_evaluation=True)

    assert summary["status"] == "NO_GO_BUDGET_EXHAUSTED"
    assert summary["stop_reason"] == "no_go_budget_exhausted"
    assert len(evaluator.calls) == 9
    assert summary["total_official_evaluation_spend"] == 9


def test_wall_clock_budget_refuses_121_minute_run(tmp_path):
    summary, provider, evaluator = _run(tmp_path, clock=FakeClock(step=121 * 60))

    assert summary["status"] == "NO_GO_BUDGET_EXHAUSTED"
    assert summary["stop_reason"] == "no_go_budget_exhausted"
    assert provider.calls == 0
    assert evaluator.calls == []


@pytest.mark.parametrize("protected", ["_database_v3k_shadow", "backup", ".omx/reports", "ai_strategy_loop/state"])
@pytest.mark.parametrize("field", ["strategy_db", "evidence_dir"])
def test_protected_roots_are_refused_for_strategy_db_and_evidence_dir(tmp_path, protected, field):
    provider = FakeProvider()
    evaluator = FakeEvaluator()
    kwargs = {
        "strategy_db": tmp_path / "isolated.sqlite",
        "evidence_dir": tmp_path / "evidence",
    }
    kwargs[field] = Path(protected) / ("loop_strategies.sqlite" if field == "strategy_db" else "evidence")

    summary = run_mini_loop(
        MiniLoopConfig(**kwargs),
        provider=provider,
        evaluator=evaluator,
        clock=FakeClock(),
    )

    assert summary["status"] == "NO_GO_OPERATING_DB_PATH_REFUSED"
    assert summary["stop_reason"] == REFUSAL_OPERATING_DB_PATH
    assert provider.calls == 0
    assert evaluator.calls == []


@pytest.mark.parametrize("field", ["strategy_db", "evidence_dir"])
def test_real_loop_state_db_paths_are_refused_before_work(tmp_path, field):
    provider = FakeProvider()
    evaluator = FakeEvaluator()
    kwargs = {
        "strategy_db": tmp_path / "isolated.sqlite",
        "evidence_dir": tmp_path / "evidence",
    }
    kwargs[field] = Path("ai_strategy_loop/state/loop_runs.db")

    summary = run_mini_loop(
        MiniLoopConfig(**kwargs),
        provider=provider,
        evaluator=evaluator,
        clock=FakeClock(),
    )

    assert summary["status"] == "NO_GO_OPERATING_DB_PATH_REFUSED"
    assert summary["stop_reason"] == REFUSAL_OPERATING_DB_PATH
    assert provider.calls == 0
    assert evaluator.calls == []


def test_operating_db_path_is_refused(tmp_path):
    summary = run_mini_loop(
        MiniLoopConfig(strategy_db=Path("_database") / "loop_strategies.db", evidence_dir=tmp_path / "evidence"),
        provider=FakeProvider(),
        evaluator=FakeEvaluator(),
        clock=FakeClock(),
    )

    assert summary["status"] == "NO_GO_OPERATING_DB_PATH_REFUSED"
    assert summary["stop_reason"] == REFUSAL_OPERATING_DB_PATH


def test_post_result_manifest_edit_stops_before_next_evaluation(tmp_path):
    summary, _provider, evaluator = _run(tmp_path, evaluator=FakeEvaluator(mutate_manifest_after_first=True))

    assert summary["status"] == "NO_GO_MANIFEST_EDITED_AFTER_FREEZE"
    assert summary["stop_reason"] == "manifest_edited_after_freeze"
    assert len(evaluator.calls) == 1
    receipts = _read_payloads(tmp_path / "isolated.sqlite", "run_receipts")
    assert any(receipt["stop_reason"] == "manifest_edited_after_freeze" for receipt in receipts)


def test_future_preregistration_manifests_predate_first_r07_result(tmp_path):
    _summary, _provider, _evaluator = _run(tmp_path)

    manifests = _read_payloads(tmp_path / "isolated.sqlite", "evaluation_manifests")
    receipts = _read_payloads(tmp_path / "isolated.sqlite", "run_receipts")
    first_eval = next(receipt for receipt in receipts if receipt["phase_id"] == "evaluation:primary:round_1")
    future_manifests = [manifest for manifest in manifests if manifest["role"] in {"CL-R08", "CL-R09", "CL-R10"}]
    assert len(future_manifests) == 3
    assert all(manifest["created_at"] < first_eval["created_at"] for manifest in future_manifests)


def test_round_selection_receipts_persist_selected_and_three_rejections_per_round(tmp_path):
    _summary, _provider, _evaluator = _run(tmp_path)

    receipts = _read_payloads(tmp_path / "isolated.sqlite", "run_receipts")
    round_receipts = [receipt for receipt in receipts if receipt["phase_id"].startswith("round_selection:")]

    assert [receipt["budget_counters"]["round_no"] for receipt in round_receipts] == [1, 2, 3]
    for receipt in round_receipts:
        counters = receipt["budget_counters"]
        assert counters["proposal_count"] == 4
        assert counters["lane_counts"] == {"discovery": 2, "repair": 2}
        assert sum(counters["family_counts"].values()) == 4
        assert counters["selected_candidate_id"]
        assert len(counters["rejection_reasons"]) == 3


def test_evidence_created_at_uses_real_utc_wall_clock_not_budget_clock(tmp_path):
    _summary, _provider, _evaluator = _run(tmp_path, clock=FakeClock(step=121 * 60))
    # Budget clock fails before evidence is opened; happy-path evidence uses the wall-clock seam.
    _summary, _provider, _evaluator = _run(tmp_path / "happy", clock=FakeClock())

    receipts = _read_payloads(tmp_path / "happy" / "isolated.sqlite", "run_receipts")
    passports = _read_payloads(tmp_path / "happy" / "isolated.sqlite", "candidate_passports")
    for created_at in (receipts[0]["created_at"], passports[0]["created_at"]):
        parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)
        assert parsed.year >= 2026
