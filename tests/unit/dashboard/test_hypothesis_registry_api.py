"""ANA-08 — 가설 레지스트리 API 시험: 상태머신 게이트가 HTTP 경계에서도 유지된다."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as loop_state
from ai_strategy_loop.dashboard import hypothesis_registry_api as api
from ai_strategy_loop.dashboard.app import create_app
from tests.unit.security_test_client import authorized_dashboard_client


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(api, "_STORE_DIR", tmp_path / "hypreg")
    monkeypatch.setattr(api, "_EVENTS_FILE", tmp_path / "hypreg" / "events.jsonl")
    monkeypatch.setattr(loop_state, "CURRENT_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(loop_state, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


_FINDING = {
    "finding_id": "f-1", "bundle_sha256": "b" * 64, "axis": "exit_timing",
    "role": "train", "effect": 0.4, "ci": [0.1, 0.7], "q": 0.03, "n": 50,
}

_HYP = {
    "finding": _FINDING,
    "failure_explained": "조기청산", "falsifiable_prediction": "연장이 손실 감소",
    "entry_time_vars": ["entry_price"], "forbidden_vars": ["exit_pnl"],
    "data_requirement": "n>=30", "leakage_risk": "매도 결과 유입 가능성",
    "negative_controls": ["placebo"], "budget": "2 runs", "normal_stop": "q>0.1",
}


def _accepted_hypothesis_id(client: TestClient) -> str:
    hid = client.post("/hypothesis-registry/hypotheses", json=_HYP).json()["hypothesis"]["hypothesis_id"]
    res = client.post(f"/hypothesis-registry/hypotheses/{hid}/review",
                      json={"decision": "ACCEPTED_FOR_PREREG", "reviewer": "park"})
    assert res.status_code == 200
    return hid


def test_state_empty_then_machine_readable(client: TestClient) -> None:
    state = client.get("/hypothesis-registry/state").json()
    assert state["available"] is True and state["hypotheses"] == []
    assert state["schema"] == "stom.hypothesis_registry.api.v1"


def test_draft_and_deterministic_id(client: TestClient) -> None:
    r1 = client.post("/hypothesis-registry/hypotheses", json=_HYP).json()
    r2 = client.post("/hypothesis-registry/hypotheses", json=_HYP).json()
    assert r1["hypothesis"]["hypothesis_id"] == r2["hypothesis"]["hypothesis_id"]
    assert r2.get("deduplicated") is True


def test_oos_finding_rejected_as_directive(client: TestClient) -> None:
    body = dict(_HYP, finding=dict(_FINDING, role="oos"))
    res = client.post("/hypothesis-registry/hypotheses", json=body)
    assert res.status_code == 409 and res.json()["code"] == "role_forbids_directive"


def test_review_requires_reviewer(client: TestClient) -> None:
    hid = client.post("/hypothesis-registry/hypotheses", json=_HYP).json()["hypothesis"]["hypothesis_id"]
    res = client.post(f"/hypothesis-registry/hypotheses/{hid}/review",
                      json={"decision": "ACCEPTED_FOR_PREREG", "reviewer": ""})
    assert res.status_code == 409 and res.json()["code"] == "reviewer_required"


def test_seal_blocked_without_human_approval(client: TestClient) -> None:
    hid = _accepted_hypothesis_id(client)
    client.post(f"/hypothesis-registry/hypotheses/{hid}/prereg-draft")
    res = client.post(f"/hypothesis-registry/preregs/{hid}/seal",
                      json={"approval_evidence": "", "approver": ""})
    assert res.status_code == 409 and res.json()["code"] == "seal_requires_human_approval"


def test_full_lifecycle_to_sealed(client: TestClient) -> None:
    hid = _accepted_hypothesis_id(client)
    pre = client.post(f"/hypothesis-registry/hypotheses/{hid}/prereg-draft").json()["prereg"]
    assert pre["status"] == "PREREG_DRAFT"
    sealed = client.post(f"/hypothesis-registry/preregs/{hid}/seal",
                         json={"approval_evidence": "meeting-1", "approver": "park"}).json()["prereg"]
    assert sealed["status"] == "PREREG_SEALED" and sealed["sealed_sha256"]
    state = client.get("/hypothesis-registry/state").json()
    assert state["counts"].get("ACCEPTED_FOR_PREREG") == 1


def test_queue_rejects_unaccepted(client: TestClient) -> None:
    hid = client.post("/hypothesis-registry/hypotheses", json=_HYP).json()["hypothesis"]["hypothesis_id"]
    res = client.post("/hypothesis-registry/queue",
                      json={"hypothesis_id": hid, "item_id": "i1", "deadline": 9999999999})
    assert res.status_code == 409 and res.json()["code"] == "queue_requires_accepted_hypothesis"


def test_queue_cancel_receipt_persists(client: TestClient) -> None:
    hid = _accepted_hypothesis_id(client)
    client.post("/hypothesis-registry/queue",
                json={"hypothesis_id": hid, "item_id": "i1", "deadline": 9999999999})
    client.post("/hypothesis-registry/queue/i1/attempt")
    client.post("/hypothesis-registry/queue/i1/cancel", json={"reason": "예산"})
    state = client.get("/hypothesis-registry/state").json()
    item = next(q for q in state["queue"] if q["item_id"] == "i1")
    assert item["status"] == "cancelled" and item["attempts"] == 1
    res = client.post("/hypothesis-registry/queue/i1/attempt")
    assert res.status_code == 409
