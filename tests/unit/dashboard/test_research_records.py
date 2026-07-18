"""Research records and governed research index contracts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.dashboard import research_index, research_records  # noqa: E402
from ai_strategy_loop.dashboard.app import create_app  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402


def _write_campaign(root: Path, name: str = "campaign_alpha") -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}_summary.json").write_text(
        json.dumps({"best_overall": {"label": "alpha", "profit": 1200, "mdd": 3.4}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / f"{name}.jsonl").write_text(
        json.dumps({"event": "cand", "label": "alpha", "profit": 1200, "mdd": 3.4, "trades": 8}) + "\n",
        encoding="utf-8",
    )


def _write_registry(repo_root: Path) -> None:
    path = repo_root / ".omo" / "evidence" / "stom-reorg-20260618" / "research-registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "campaigns": [
                    {
                        "campaign_id": "campaign_alpha",
                        "display_alias": "알파 캠페인",
                        "evidence_type": "official_oos",
                        "status": "complete",
                        "source_files": ["docs/update_log/2026-01-01_alpha.md"],
                        "dashboard_record": "campaign_alpha",
                        "next_action": "review",
                    }
                ],
                "candidates": [
                    {
                        "machine_name": "alpha_candidate",
                        "display_alias": "알파 후보",
                        "candidate_family": "seed",
                        "evidence_type": "csv_reanalysis",
                        "oos_status": "official_oos_pending",
                        "promotion_status": "queued_not_promoted",
                        "source_files": ["docs/research/condition_research/alpha.md"],
                        "related_dashboard_record": "campaign_alpha",
                        "next_action": "run official OOS",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (path.parent / "research-source-inventory.md").write_text("# Source inventory\n", encoding="utf-8")


def _write_docs(repo_root: Path) -> None:
    doc = repo_root / "docs" / "research" / "condition_research" / "alpha.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("# Alpha Doc\nBody", encoding="utf-8")
    update = repo_root / "docs" / "update_log" / "2026-01-01_alpha.md"
    update.parent.mkdir(parents=True, exist_ok=True)
    update.write_text("# Alpha Update\nBody", encoding="utf-8")


def _write_governance_sources(repo_root: Path) -> None:
    ref = repo_root / "ai_strategy_loop" / "dashboard" / "reference_strategies.json"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(json.dumps([{"label": "Human Champion", "total_return_krw": 1000}], ensure_ascii=False), encoding="utf-8")
    decisions = repo_root / ".omo" / "evidence" / "decisions.jsonl"
    decisions.parent.mkdir(parents=True, exist_ok=True)
    decisions.write_text(
        json.dumps({"decision": "Approve alpha", "source_files": ["docs/update_log/2026-01-01_alpha.md"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    artifact = repo_root / ".omo" / "evidence" / "tmap-walkforward" / "manual_evidence.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({"artifact": "manual"}, ensure_ascii=False), encoding="utf-8")


def test_research_records_lists_campaigns(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    _write_campaign(evidence)

    payload = research_records.list_research_records(evidence)

    assert payload["count"] == 1
    campaign = payload["campaigns"][0]
    assert campaign["name"] == "campaign_alpha"
    assert campaign["candidate_count"] == 1
    assert campaign["best"]["label"] == "alpha"
    assert research_records.research_record_detail("../bad", evidence) == {
        "available": False,
        "reason": "invalid_campaign",
    }

def test_research_records_root_is_a_safe_logical_label(tmp_path: Path) -> None:
    evidence = (tmp_path / "private-parent" / "campaign-evidence").resolve()
    _write_campaign(evidence)

    payload = research_records.list_research_records(evidence)

    assert payload["root"] == "research-records"
    assert not Path(payload["root"]).is_absolute()
    assert str(evidence) not in payload["root"]
    assert str(evidence.parent) not in payload["root"]
    assert payload["count"] == 1
    assert payload["campaigns"][0]["name"] == "campaign_alpha"

    missing = (tmp_path / "private-parent" / "missing-evidence").resolve()
    missing_payload = research_records.list_research_records(missing)

    assert missing_payload["root"] == "research-records"
    assert not Path(missing_payload["root"]).is_absolute()
    assert str(missing) not in missing_payload["root"]
    assert str(missing.parent) not in missing_payload["root"]
    assert missing_payload["count"] == 0
    assert missing_payload["campaigns"] == []


def test_governed_index_has_namespaced_rows_and_safe_detail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    evidence = repo / ".omo" / "evidence" / "tmap-walkforward"
    _write_campaign(evidence)
    _write_docs(repo)
    _write_registry(repo)
    _write_governance_sources(repo)

    payload = research_index.list_research_index(repo, evidence)
    ids = {row["id"] for row in payload["records"]}

    assert "campaign:campaign_alpha" in ids
    assert "doc:docs/research/condition_research/alpha.md" in ids
    assert "update_log:docs/update_log/2026-01-01_alpha.md" in ids
    assert "registry:alpha_candidate" in ids
    assert "registry:campaign:campaign_alpha" in ids
    assert "hof:reference-strategies" in ids
    assert "decision:1" in ids
    assert any(row_id.startswith("evidence:") for row_id in ids)
    candidate = next(row for row in payload["records"] if row["id"] == "registry:alpha_candidate")
    assert candidate["canonicality"] == "candidate"
    assert candidate["source_authority"] == "registry_entry"
    assert "campaign:campaign_alpha" in candidate["related_ids"]
    assert candidate["trace_status"] == "linked"
    assert candidate["exact_link"] == "research-index://registry:alpha_candidate"
    campaign = next(row for row in payload["records"] if row["id"] == "campaign:campaign_alpha")
    assert campaign["source_path"] == ".omo/evidence/tmap-walkforward/campaign_alpha_summary.json"
    assert not Path(campaign["source_path"]).is_absolute()
    assert str(evidence) not in campaign["source_path"]
    assert campaign["trace_status"] == "unlinked"
    doc = next(row for row in payload["records"] if row["id"] == "doc:docs/research/condition_research/alpha.md")
    assert doc["trace_status"] == "unknown"
    assert all(row["trace_status"] in research_index.TRACE_STATUS_VALUES for row in payload["records"])
    decision = next(row for row in payload["records"] if row["id"] == "decision:1")
    assert decision["trace_status"] == "linked"
    assert "update_log:docs/update_log/2026-01-01_alpha.md" in decision["related_ids"]
    hof = next(row for row in payload["records"] if row["id"] == "hof:reference-strategies")
    assert hof["source_authority"] == "hall_of_fame"

    assert research_index.research_index_detail("doc:../secret", repo, evidence)["reason"] == "invalid_id"
    assert research_index.research_index_detail("unknown:thing", repo, evidence)["reason"] == "invalid_id"
    detail = research_index.research_index_detail("registry:alpha_candidate", repo, evidence)
    assert detail["available"] is True
    assert detail["registry_entry"]["machine_name"] == "alpha_candidate"

def test_governed_index_reports_malformed_sources_and_stronger_invalid_ids(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    evidence = repo / ".omo" / "evidence" / "tmap-walkforward"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "bad_summary.json").write_text("{not-json", encoding="utf-8")
    (evidence / "bad.jsonl").write_text("{not-json\n", encoding="utf-8")
    registry = repo / ".omo" / "evidence" / "stom-reorg-20260618" / "research-registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text("{not-json", encoding="utf-8")

    payload = research_index.list_research_index(repo, evidence)
    errors = {(item["source_path"], item["reason"]) for item in payload["errors"]}

    assert any(path == "bad_summary.json" and reason.startswith("json:") for path, reason in errors)
    assert any(path == "bad.jsonl" and reason.startswith("line1:json:") for path, reason in errors)
    assert any(path.endswith("research-registry.json") and reason == "JSONDecodeError" for path, reason in errors)
    for bad_id in (
        "doc:/absolute/secret.md",
        r"doc:\absolute\secret.md",
        "doc:docs/research/condition_research/../../secret.md",
        "update_log:docs/update_log/../../secret.md",
        "campaign:../bad",
    ):
        detail = research_index.research_index_detail(bad_id, repo, evidence)
        assert detail["available"] is False
        assert detail["reason"] in {"invalid_id", "missing_id"}

def test_governed_index_cache_invalidates_on_file_add_remove_and_mtime(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    evidence = repo / ".omo" / "evidence" / "tmap-walkforward"
    _write_campaign(evidence, "campaign_one")
    _write_docs(repo)
    _write_registry(repo)

    first = research_index.list_research_index(repo, evidence)
    assert first["cache"]["hit"] is False
    second = research_index.list_research_index(repo, evidence)
    assert second["cache"]["hit"] is True

    _write_campaign(evidence, "campaign_two")
    third = research_index.list_research_index(repo, evidence)
    assert third["cache"]["hit"] is False
    assert "campaign:campaign_two" in {row["id"] for row in third["records"]}

    (evidence / "campaign_two_summary.json").unlink()
    (evidence / "campaign_two.jsonl").unlink()
    fourth = research_index.list_research_index(repo, evidence)
    assert fourth["cache"]["hit"] is False
    assert "campaign:campaign_two" not in {row["id"] for row in fourth["records"]}


def test_research_index_routes_are_available(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    client = authorized_dashboard_client(create_app())

    response = client.get("/research_index")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    ids = {row["id"] for row in body["records"]}
    assert any(item.startswith("registry:") for item in ids)
    assert any(item.startswith("doc:") for item in ids)
    assert any(item.startswith("update_log:") for item in ids)

    detail_id = next(item for item in ids if item.startswith("registry:"))
    detail = client.get("/research_index/detail", params={"id": detail_id})
    assert detail.status_code == 200
    assert detail.json()["available"] is True
