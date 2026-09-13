"""ANA-05 — Canonical AnalysisBundle v3 + immutable artifact store 시험."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as loop_state
from ai_strategy_loop.dashboard import analysis_bundle_api as api
from ai_strategy_loop.dashboard.analysis_bundle_builder import (
    build_legacy_job_analysis_bundle,
    build_legacy_job_analysis_bundle_v3,
)
from ai_strategy_loop.dashboard.analysis_bundle_models import (
    ANALYSIS_BUNDLE_SCHEMA_V3,
    AnalysisSectionStatus,
    project_bundle_v2_to_v3,
)
from ai_strategy_loop.dashboard.analysis_bundle_store import (
    load_bundle_by_sha,
    lookup_bundle,
    store_bundle,
)
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_api import build_truth_payload
from tests.unit.security_test_client import authorized_dashboard_client


class _FakeManager:
    def __init__(self, record: dict[str, JsonValue]) -> None:
        self._record = record

    def get(self, job_id: str, *, log_tail: int = 50) -> dict[str, JsonValue]:
        del log_tail
        if job_id != self._record["job_id"]:
            return {"available": False, "job_id": job_id}
        return {**self._record, "available": True}


CSV = (
    "﻿종목명,매수시간,매도시간,보유시간,수익률,수익금\n"
    "알파,202504070930,202504071000,30,2.0,20000\n"
    "베타,202504071030,202504071100,30,-1.0,-10000\n"
)


def _record(csv_path: Path) -> dict[str, JsonValue]:
    return {
        "job_id": "bundle-job",
        "spec": {"buy": "candidate-a", "sell": "sell-a"},
        "status": "success",
        "returncode": 0,
        "metrics": {"trade_count": 2, "total_profit_pct": 1.0},
        "csv_path": csv_path.as_posix(),
        "finished_at": 1_725_000_000.0,
        "strategy_db_snapshot_hashes": {"buy": "a" * 64},
    }


@pytest.fixture
def env(tmp_path: Path):
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(CSV, encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    record = _record(csv_path)
    truth = build_truth_payload("bundle-job", {**record, "available": True}, jobs_dir)["truth"]
    from ai_strategy_loop.controller.research_truth_models import ResearchTruth
    import json as _json
    truth = ResearchTruth.model_validate_json(_json.dumps(truth, ensure_ascii=False))
    return record, truth, csv_path


def test_v3_schema_and_new_sections(env):
    record, truth, csv_path = env
    b = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    assert b.schema_version == ANALYSIS_BUNDLE_SCHEMA_V3
    assert b.identity.bundle_version == "3.0.0"
    assert b.data_quality.status is AnalysisSectionStatus.OBSERVED
    assert b.data_quality.values["row_count_matches_execution"] is True
    # 미실행 섹션은 reason+prerequisites 를 가진다.
    for sec in (b.statistics, b.findings, b.episodes, b.counterfactual, b.robustness):
        assert sec.status is not AnalysisSectionStatus.OBSERVED
        assert sec.reason
        assert sec.prerequisites


def test_v2_to_v3_lossless_projection(env):
    record, truth, csv_path = env
    v2 = build_legacy_job_analysis_bundle(record, truth, csv_path)
    v3 = project_bundle_v2_to_v3(v2)
    # v2 섹션 값 보존.
    assert v3.metrics.values == v2.metrics.values
    assert v3.series.values == v2.series.values
    assert v3.distribution.values == v2.distribution.values
    assert v3.attribution.values == v2.attribution.values
    assert v3.decision == v2.decision
    assert v3.source == v2.source
    assert v3.execution == v2.execution
    assert v3.content_sha256 != v2.content_sha256  # 새 schema → 새 해시.


def test_v3_deterministic_same_input(env):
    record, truth, csv_path = env
    a = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    b = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    assert a.content_sha256 == b.content_sha256


def test_store_load_roundtrip_and_lookup(env, tmp_path):
    record, truth, csv_path = env
    root = tmp_path / "artifacts"
    b = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    path = store_bundle(b, root)
    assert path.is_file()
    loaded = load_bundle_by_sha(b.content_sha256, root)
    assert loaded is not None and loaded.content_sha256 == b.content_sha256
    got = lookup_bundle("bundle-job", b.identity.source_sha256, root)
    assert got is not None and got.content_sha256 == b.content_sha256


def test_store_is_immutable_and_idempotent(env, tmp_path):
    record, truth, csv_path = env
    root = tmp_path / "artifacts"
    b = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    p1 = store_bundle(b, root)
    original = p1.read_bytes()
    p2 = store_bundle(b, root)  # 같은 해시 재저장은 덮어쓰지 않는다.
    assert p1 == p2 and p1.read_bytes() == original


def test_source_change_produces_new_hash(env, tmp_path):
    record, truth, csv_path = env
    b1 = build_legacy_job_analysis_bundle_v3(record, truth, csv_path)
    # CSV 내용 변경 → 다른 source identity → 다른 content hash.
    csv_path.write_text(CSV + "감마,202504071100,202504071130,30,1.0,5000\n", encoding="utf-8")
    record2 = dict(record)
    record2["metrics"] = {"trade_count": 3, "total_profit_pct": 1.5}
    truth2 = build_truth_payload("bundle-job", {**record2, "available": True},
                                 tmp_path / "jobs")["truth"]
    from ai_strategy_loop.controller.research_truth_models import ResearchTruth
    import json as _json
    truth2 = ResearchTruth.model_validate_json(_json.dumps(truth2, ensure_ascii=False))
    b2 = build_legacy_job_analysis_bundle_v3(record2, truth2, csv_path)
    assert b2.content_sha256 != b1.content_sha256
    # 과거 번들은 그대로 읽힌다.
    root = tmp_path / "artifacts"
    store_bundle(b1, root)
    store_bundle(b2, root)
    assert load_bundle_by_sha(b1.content_sha256, root).content_sha256 == b1.content_sha256


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(CSV, encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "configured_jobs_dir", lambda: jobs_dir)
    monkeypatch.setattr(api, "get_job_manager", lambda: _FakeManager(_record(csv_path)))
    monkeypatch.setenv("STOM_ANALYSIS_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.setattr(loop_state, "CURRENT_STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(loop_state, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def test_v3_api_persists_then_reads_artifact(client: TestClient, tmp_path: Path) -> None:
    first = client.get("/analysis-bundle/job/v3", params={"job_id": "bundle-job"})
    assert first.status_code == 200
    p1 = first.json()
    assert p1["bundle_available"] is True
    assert p1["persistence"] == "immutable_artifact"
    assert p1["artifact_hit"] is False
    # 두 번째 호출은 재계산이 아니라 artifact 읽기.
    second = client.get("/analysis-bundle/job/v3", params={"job_id": "bundle-job"})
    p2 = second.json()
    assert p2["artifact_hit"] is True
    assert p2["content_sha256"] == p1["content_sha256"]
    assert p2["bundle"]["schema"] == "stom.analysis_bundle.v3"
    # artifact 파일이 실제로 존재.
    artifact = tmp_path / "artifacts" / p1["content_sha256"] / "bundle.json"
    assert artifact.is_file()


def test_v3_api_unknown_job_unavailable(client: TestClient) -> None:
    payload = client.get("/analysis-bundle/job/v3", params={"job_id": "missing"}).json()
    assert payload["bundle_available"] is False
    assert payload["reason"] == "job_not_found"
    assert payload["persistence"] == "none"
