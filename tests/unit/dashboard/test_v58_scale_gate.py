"""Contracts for the isolated v5.8 dashboard scale performance gate."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "verify_dashboard_v58_scale.py"
_SPEC = importlib.util.spec_from_file_location("verify_dashboard_v58_scale", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
scale = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scale)


def test_fixture_has_locked_two_x_scale_and_is_not_under_runtime_paths(tmp_path: Path) -> None:
    paths = scale.build_fixture(tmp_path / "isolated")

    assert paths["loop_db"].is_relative_to(tmp_path)
    assert paths["evidence_root"].is_relative_to(tmp_path)
    with sqlite3.connect(paths["loop_db"]) as connection:
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == scale.RUN_COUNT == 1_054
        assert connection.execute("SELECT COUNT(*) FROM generations").fetchone()[0] == scale.GENERATION_COUNT == 10_728
    assert len(list(paths["evidence_root"].glob("*.jsonl"))) == scale.CAMPAIGN_COUNT == 34
    sidecar = json.loads(paths["docs_sidecar"].read_text(encoding="utf-8"))
    assert len(sidecar["docs"]) == scale.WIKI_METADATA_ROWS == 1_860


def test_budget_enforcement_accepts_boundary_and_rejects_overage() -> None:
    at_budget = {
        "history_cold_seconds": scale.HISTORY_COLD_BUDGET_SECONDS,
        "history_warm_seconds": scale.HISTORY_WARM_BUDGET_SECONDS,
        "wiki_cold_seconds": scale.WIKI_COLD_BUDGET_SECONDS,
        "wiki_warm_seconds": scale.WIKI_WARM_BUDGET_SECONDS,
    }
    scale._enforce_budgets(at_budget)

    too_slow = dict(at_budget, wiki_warm_seconds=scale.WIKI_WARM_BUDGET_SECONDS + 0.001)
    with pytest.raises(scale.PerformanceGateError, match="wiki_warm_seconds"):
        scale._enforce_budgets(too_slow)


def test_main_fails_closed_with_structured_json_on_gate_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fail() -> dict[str, object]:
        raise scale.PerformanceGateError("forced measurement failure")

    monkeypatch.setattr(scale, "run_gate", fail)

    assert scale.main([]) == 1
    evidence = json.loads(capsys.readouterr().out)
    assert evidence == {
        "gate": "dashboard_v58_scale",
        "passed": False,
        "performance_proved": False,
        "error": "forced measurement failure",
    }
