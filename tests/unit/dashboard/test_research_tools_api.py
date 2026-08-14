from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_strategy_loop.controller import state as S
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard.research_tools_api import AUTHORITY, MAX_QMC_BUDGET, MAX_SOURCE_CHARS
from ai_strategy_loop.dashboard.security import HTTP_CAPABILITIES
from ai_strategy_loop.dashboard.security_capabilities import Capability
from tests.unit.security_test_client import authorized_dashboard_client


_SOURCE = """\
매수 = True
if not (등락율 >= 1.5):
    매수 = False
elif not (체결강도 >= 100):
    매수 = False
elif not (전일동시간비 > 0):
    매수 = False
"""


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def _assert_no_authority(payload: dict[str, object]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert payload["authority"] == AUTHORITY
    assert payload["can_adopt"] is False
    assert payload["persistence"] == "none"
    assert "receipts" in payload
    assert "strategy approval" not in serialized
    assert '"can_adopt": true' not in serialized
    assert '"adoption_authority": true' not in serialized


def _bayesian_payload(**overrides):
    payload = {
        "config": {
            "prior_alpha": 1.0,
            "prior_beta": 1.0,
            "rope_lower": 0.5,
            "approve_prob_threshold": 0.95,
            "reject_prob_threshold": 0.95,
            "max_sample": 20,
            "credible_mass": 0.95,
        },
        "counts": {"successes": 18, "failures": 0},
    }
    for key, value in overrides.items():
        if key in payload and isinstance(payload[key], dict) and isinstance(value, dict):
            payload[key].update(value)
        else:
            payload[key] = value
    return payload


def _ast_payload(**overrides):
    payload = {
        "source": _SOURCE,
        "allowed_functions": [],
        "limits": {"max_clauses": 4, "max_lookback": 200.0, "max_unknown_lines": 0},
    }
    payload.update(overrides)
    return payload


def _qmc_payload(**overrides):
    payload = {
        "seed": 17,
        "budget": 4,
        "scramble": False,
        "skip": 0,
        "dimensions": [
            {"name": "threshold", "kind": "continuous", "low": 10.0, "high": 20.0},
            {"name": "bucket", "kind": "integer", "low": 1, "high": 3},
            {"name": "lane", "kind": "categorical", "categories": ["early", "mid", "late"]},
        ],
        "pareto": {
            "budget": 3,
            "objectives": [
                {"name": "score", "direction": "maximize"},
                {"name": "risk", "direction": "minimize"},
            ],
            "trials": [
                {"key": "a", "scores": {"score": 1.0, "risk": 2.0}, "payload": {"note": "manual"}},
                {"key": "b", "scores": {"score": 2.0, "risk": 3.0}, "payload": {}},
            ],
        },
    }
    payload.update(overrides)
    return payload


def _denoise_payload(**overrides):
    payload = {
        "source": _SOURCE,
        "seed": 11,
        "operator": "mask_one_clause",
        "clause_index": 1,
        "static_check": {
            "allowed_functions": [],
            "limits": {"max_clauses": 4, "max_lookback": 200.0, "max_unknown_lines": 0},
        },
    }
    payload.update(overrides)
    return payload


def test_status_lists_four_manual_no_adoption_tools(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get("/loop/research-tools/status")

    assert response.status_code == 200
    payload = response.json()
    _assert_no_authority(payload)
    assert [tool["id"] for tool in payload["tools"]] == ["bayesian", "ast", "qmc", "denoise"]
    assert all(tool["authority"] == AUTHORITY and tool["manual_only"] is True for tool in payload["tools"])
    assert "APPROVE is a statistical boundary label only" in " ".join(payload["reading_rules"])


def test_research_tool_posts_are_classified_as_manual_diagnostic_capability() -> None:
    for path in (
        "/loop/research-tools/bayesian",
        "/loop/research-tools/ast",
        "/loop/research-tools/qmc",
        "/loop/research-tools/denoise",
    ):
        assert HTTP_CAPABILITIES[("POST", path)] is Capability.RESEARCH_DIAGNOSTIC


def test_bayesian_success_labels_approve_as_statistical_boundary_only(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post("/loop/research-tools/bayesian", json=_bayesian_payload())

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_no_authority(payload)
    assert payload["ok"] is True
    assert payload["decision"] == "APPROVE"
    assert payload["decision_label"] == "statistical_boundary_only_not_strategy_approval"
    assert payload["decision_authority"] == "statistical_boundary_only"
    assert payload["counts"] == {"successes": 18, "failures": 0, "sample_size": 18}
    assert payload["receipts"]["config"]["digest"]
    assert payload["receipts"]["seed"]["purpose"] == "external_observations_no_rng"


def test_ast_success_parses_static_checks_and_keeps_source_out_of_parsed_payload(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post("/loop/research-tools/ast", json=_ast_payload())

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_no_authority(payload)
    assert payload["ok"] is True
    assert payload["violations"] == []
    assert payload["parsed"]["complexity"]["clause_count"] == 3
    assert "original_source" not in payload["parsed"]
    assert payload["receipts"]["config"]["allowed_functions"] == []
    assert payload["receipts"]["seed"]["random_used"] is False


def test_qmc_success_proposes_bounded_candidates_and_optional_pareto_archive(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post("/loop/research-tools/qmc", json=_qmc_payload())

    assert response.status_code == 200, response.text
    payload = response.json()
    _assert_no_authority(payload)
    assert payload["ok"] is True
    assert payload["candidate_count"] == 4
    assert payload["proposal_receipt"]["budget"] == 4
    assert payload["proposal_receipt"]["seed"] == 17
    assert payload["candidates"][0]["parameters"] == {"threshold": 15.0, "bucket": 2, "lane": "early"}
    assert payload["pareto"]["trial_count"] == 2
    assert payload["pareto"]["receipt"]["remaining_budget"] == 1
    assert payload["pareto"]["adoption_authority"] == "none"
    assert payload["pareto"]["oos_claim"] == "none"


def test_denoise_success_runs_one_deterministic_corruption_repair_evaluation(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    first = client.post("/loop/research-tools/denoise", json=_denoise_payload())
    second = client.post("/loop/research-tools/denoise", json=_denoise_payload())

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    payload = first.json()
    _assert_no_authority(payload)
    assert payload == second.json()
    assert payload["ok"] is True
    assert payload["corruption"]["ok"] is True
    assert payload["repair"]["ok"] is True
    assert payload["evaluation"]["canonical_equal"] is True
    assert payload["evaluation"]["syntax_valid"] is True
    assert payload["static_valid_source"] == "explicit_static_check"
    assert payload["receipts"]["corruption"]["authority_scope"] == "none"


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/loop/research-tools/bayesian", _bayesian_payload(counts={"successes": 21, "failures": 0})),
        ("/loop/research-tools/ast", _ast_payload(source="x" * (MAX_SOURCE_CHARS + 1))),
        ("/loop/research-tools/qmc", _qmc_payload(budget=MAX_QMC_BUDGET + 1)),
        ("/loop/research-tools/denoise", _denoise_payload(source="not a guard block")),
    ],
)
def test_invalid_bounds_source_and_budget_fail_honestly(monkeypatch, tmp_path: Path, path: str, payload: dict[str, object]) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.post(path, json=payload)

    assert response.status_code in {400, 422}
    body = response.json()
    _assert_no_authority(body)
    assert body["ok"] is False
    assert body.get("code") in {"validation_error", "corruption_failed"}


def test_endpoints_do_not_persist_or_touch_loop_state(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    responses = [
        client.post("/loop/research-tools/bayesian", json=_bayesian_payload()),
        client.post("/loop/research-tools/ast", json=_ast_payload()),
        client.post("/loop/research-tools/qmc", json=_qmc_payload(pareto=None)),
        client.post("/loop/research-tools/denoise", json=_denoise_payload()),
    ]

    assert all(response.status_code == 200 for response in responses)
    for response in responses:
        _assert_no_authority(response.json())
    assert (tmp_path / "current_state.json").exists() is False
    assert (tmp_path / "STOP").exists() is False
    assert [path.name for path in tmp_path.iterdir()] == []
