from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_strategy_loop.controller import state as S
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard import research_program_api as api
from tests.unit.security_test_client import authorized_dashboard_client


def _write(root: Path, evidence_id: str, payload: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / api._EVIDENCE_FILES[evidence_id]).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    evidence = tmp_path / "evidence"
    monkeypatch.setattr(api, "_EVIDENCE_ROOT", evidence)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    for evidence_id in ("d1_manifest", "d2_manifest"):
        phase = "D1" if evidence_id.startswith("d1") else "D2"
        _write(evidence, evidence_id, {
            "candidates": [{
                "candidate_id": f"{phase}_A",
                "family": f"{phase}_FAMILY",
                "source_sha256": "a" * 64,
                "execution_ok": True,
            }]
        })
    for evidence_id in ("d1_screen", "d2_screen"):
        phase = "D1" if evidence_id.startswith("d1") else "D2"
        _write(evidence, evidence_id, {
            "rows": [{
                "candidate_id": f"{phase}_A",
                "metrics": {"trade_count": 20},
                "screen": {"advance": True},
                "source_snapshot_match": True,
            }]
        })
    _write(evidence, "d1_folds", {"verdict": "NO_DEVELOPMENT_ROBUST_CANDIDATE", "rows": [{"fold_id": "D1F"}]})
    _write(evidence, "d2_folds", {"verdict": "NO_ROBUST_FAMILY", "rows": [{"fold_id": "D2F"}]})
    _write(evidence, "paired_folds", {
        "verdict": "NO_ROBUST_ENTRY_EXIT_PAIR",
        "recovered_terminal_rows": 1,
        "rows": [{"fold_id": "PF", "status": "success"}],
    })
    _write(evidence, "platform_audit", {"verdict": "PASS", "passed": 20, "total": 20})
    _write(evidence, "d1_determinism", {"verdict": "DETERMINISTIC_REPRESENTATIVES"})
    _write(evidence, "paired_screen", {"verdict": "PAIR_SCREEN_COMPLETED", "rows": []})
    return authorized_dashboard_client(create_app()), evidence


def _assert_authority(payload: dict) -> None:
    assert payload["authority"] == api.AUTHORITY
    assert payload["can_adopt"] is False
    assert payload["oos_claim"] == "none"
    assert payload["persistence"] == "none"


def test_summary_separates_platform_and_economic_status(monkeypatch, tmp_path):
    client, _ = _client(monkeypatch, tmp_path)
    response = client.get("/research-program/summary")
    assert response.status_code == 200
    payload = response.json()
    _assert_authority(payload)
    assert payload["platform"]["verdict"] == "PASS"
    assert payload["economic"]["verdict"] == "NO_ROBUST_ENTRY_EXIT_PAIR"
    assert payload["economic"]["robust_candidates"] == 0
    assert payload["funnel"]["generated"] == 2


def test_registry_fold_failure_and_health_projections(monkeypatch, tmp_path):
    client, _ = _client(monkeypatch, tmp_path)
    families = client.get("/research-program/families").json()
    assert {row["family"] for row in families["families"]} == {"D1_FAMILY", "D2_FAMILY"}
    folds = client.get("/research-program/folds").json()
    assert folds["row_count"] == 3
    failures = client.get("/research-program/failures").json()
    assert {row["state"] for row in failures["failures"]} >= {"PROVEN", "REFUTED", "FIXED", "OPEN", "LIMITATION"}
    health = client.get("/research-program/jobs/health").json()
    assert health["engine_terminal_counts"] == {"success": 1}
    assert health["runtime_queue"] == "not_started"


def test_missing_and_malformed_evidence_are_typed_without_creation(monkeypatch, tmp_path):
    client, evidence = _client(monkeypatch, tmp_path)
    expected = evidence / api._EVIDENCE_FILES["mcap_census"]
    assert not expected.exists()
    missing = client.get("/research-program/market-cap-census").json()
    assert missing["available"] is False
    assert missing["reason"] == "source_missing"
    assert not expected.exists()

    path = evidence / api._EVIDENCE_FILES["d2_folds"]
    path.write_text("{broken", encoding="utf-8")
    malformed = client.get("/research-program/evidence/d2_folds").json()
    assert malformed["available"] is False
    assert malformed["reason"] == "source_unavailable"


def test_evidence_lookup_is_allowlisted(monkeypatch, tmp_path):
    client, _ = _client(monkeypatch, tmp_path)
    assert client.get("/research-program/evidence/paired_folds").status_code == 200
    assert client.get("/research-program/evidence/..%2F..%2F_database").status_code == 404
    assert client.get("/research-program/evidence/not_registered").status_code == 404


def _preview_payload():
    return {
        "family_id": "ABSORPTION_REVERSAL",
        "compute_hours": 36,
        "entry_variables": 8,
        "exit_variables": 6,
        "bands": [dict(item) for item in api._MCAP_BANDS],
    }


def test_preregistration_preview_accepts_exact_bands_without_persistence(monkeypatch, tmp_path):
    client, evidence = _client(monkeypatch, tmp_path)
    before = sorted(path.name for path in evidence.iterdir())
    response = client.post("/research-program/preregistration/preview", json=_preview_payload())
    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_authority(payload)
    assert payload["accepted"] is True
    assert len(payload["preview_sha256"]) == 64
    assert before == sorted(path.name for path in evidence.iterdir())


def test_preregistration_preview_rejects_band_drift_and_budget_outside_contract(monkeypatch, tmp_path):
    client, _ = _client(monkeypatch, tmp_path)
    payload = _preview_payload()
    payload["bands"][0]["upper"] = 2999
    assert client.post("/research-program/preregistration/preview", json=payload).status_code == 422
    payload = _preview_payload()
    payload["compute_hours"] = 49
    assert client.post("/research-program/preregistration/preview", json=payload).status_code == 422
