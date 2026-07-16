"""cli.research_history_projection의 빌더/퍼블리셔 계약 테스트.

condition_history_v1 리드모델의 유일한 빌더(build_campaign_condition_history_projection)와
유일한 퍼블리셔(publish_condition_history)가 계약대로 동작하는지 검증한다:
원자적 쓰기, 안전하지 않은 캠페인 이름 거부, 동일 입력에 대한 결정론적 출력,
레거시 입력의 최소 유효 노드, 동일 입력 재발행 시 바이트 동일성.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cli.condition_history_schema import SCHEMA_VERSION, validate_research_node
from cli.research_history_projection import (
    PROJECTION_OWNER,
    build_campaign_condition_history_projection,
    publish_condition_history,
)


def _sample_inputs() -> dict:
    return {
        "campaign": "seed-tree-01",
        "report": {
            "research_id": "research-001",
            "stages": [
                {
                    "stage_id": "stage-tick",
                    "conditions": [
                        {
                            "condition_id": "cond-a",
                            "evaluations": [
                                {
                                    "evaluation_id": "eval-1",
                                    "status": "success",
                                    "metrics": {"score": 1.5},
                                }
                            ],
                        }
                    ],
                }
            ],
        },
        "runtime_checkpoints": [
            {"evaluation_id": "eval-1", "checkpoint_id": "cp-1", "tick": 90100}
        ],
        "leaderboard_rows": [
            {"condition_id": "cond-a", "rank": 1, "run_id": "run-9"}
        ],
        "source_artifacts": {"report.json": "a" * 64, "leaderboard.csv": "b" * 64},
        "repo_commit": "deadbeefcafef00d",
    }


def _legacy_inputs() -> dict:
    return {
        "campaign": "legacy-campaign",
        "report": {},
        "source_artifacts": {},
        "repo_commit": "cafed00d",
    }


# ---------------------------------------------------------------------------
# build_campaign_condition_history_projection
# ---------------------------------------------------------------------------


def test_build_projection_composes_tree_with_provenance():
    projection = build_campaign_condition_history_projection(_sample_inputs())

    assert projection["schema_version"] == SCHEMA_VERSION
    assert projection["projection_owner"] == PROJECTION_OWNER
    assert projection["campaign"] == "seed-tree-01"
    assert projection["condition_tree_status"] == "available"
    assert projection["provenance"]["repo_commit"] == "deadbeefcafef00d"
    assert projection["provenance"]["source_artifacts"] == {
        "report.json": "a" * 64,
        "leaderboard.csv": "b" * 64,
    }

    research = projection["research"]
    assert research["research_id"] == "research-001"
    assert research["coverage_status"] == "success"
    stage = research["stages"][0]
    assert stage["stage_id"] == "stage-tick"
    assert stage["coverage_status"] == "success"
    condition = stage["conditions"][0]
    assert condition["condition_id"] == "cond-a"
    assert condition["coverage_status"] == "success"
    evaluation = condition["evaluations"][0]
    assert evaluation["evaluation_id"] == "eval-1"
    assert evaluation["status"] == "success"
    assert evaluation["metrics"]["score"] == 1.5
    assert evaluation["metrics"]["runtime_tick"] == 90100.0
    assert evaluation["metrics"]["leaderboard_rank"] == 1.0

    assert validate_research_node(research) == []


def test_build_projection_requires_campaign():
    inputs = _sample_inputs()
    del inputs["campaign"]
    with pytest.raises(ValueError):
        build_campaign_condition_history_projection(inputs)


def test_build_projection_legacy_inputs_produce_minimal_valid_node():
    projection = build_campaign_condition_history_projection(_legacy_inputs())

    assert projection["condition_tree_status"] == "legacy_unavailable"
    research = projection["research"]
    assert research["research_id"] == "legacy-campaign"
    assert research["stages"] == []
    assert validate_research_node(research) == []


def test_build_projection_unknown_evaluation_status_becomes_typed_missing():
    inputs = _sample_inputs()
    inputs["report"]["stages"][0]["conditions"][0]["evaluations"][0]["status"] = "not-a-real-status"
    projection = build_campaign_condition_history_projection(inputs)
    evaluation = projection["research"]["stages"][0]["conditions"][0]["evaluations"][0]
    assert evaluation["status"] == "missing"
    assert validate_research_node(projection["research"]) == []


def test_build_projection_deterministic_for_same_inputs():
    first = build_campaign_condition_history_projection(_sample_inputs())
    second = build_campaign_condition_history_projection(_sample_inputs())
    assert first == second


def test_build_projection_deterministic_regardless_of_insertion_order():
    inputs_a = _sample_inputs()
    inputs_b = _sample_inputs()
    extra_condition = {"condition_id": "cond-b", "evaluations": []}
    inputs_b["report"]["stages"][0]["conditions"].append(dict(extra_condition))
    inputs_a["report"]["stages"][0]["conditions"].append(dict(extra_condition))
    first = build_campaign_condition_history_projection(inputs_a)
    second = build_campaign_condition_history_projection(inputs_b)
    assert first == second
    assert [c["condition_id"] for c in first["research"]["stages"][0]["conditions"]] == [
        "cond-a",
        "cond-b",
    ]


# ---------------------------------------------------------------------------
# publish_condition_history
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../escape",
        "nested/path",
        "nested\\path",
        "",
        "a" * 121,
        "bad name",
        "bad*name",
    ],
)
def test_publish_rejects_unsafe_campaign_names(tmp_path: Path, unsafe_name: str):
    projection = build_campaign_condition_history_projection(_sample_inputs())
    with pytest.raises(ValueError):
        publish_condition_history(unsafe_name, projection, tmp_path)
    # 안전하지 않은 이름 시도로 인해 evidence_dir에 어떤 파일도 생기지 않아야 한다.
    assert list(tmp_path.iterdir()) == []


def test_publish_rejects_database_evidence_dir(tmp_path: Path):
    projection = build_campaign_condition_history_projection(_sample_inputs())
    forbidden_dir = tmp_path / "_database"
    with pytest.raises(ValueError):
        publish_condition_history("seed-tree-01", projection, forbidden_dir)
    assert not forbidden_dir.exists()


def test_publish_writes_expected_file(tmp_path: Path):
    projection = build_campaign_condition_history_projection(_sample_inputs())
    target = publish_condition_history("seed-tree-01", projection, tmp_path)

    assert target == tmp_path / "seed-tree-01_condition_history_v1.json"
    assert target.exists()
    on_disk = json.loads(target.read_text(encoding="utf-8"))
    assert on_disk == projection
    # 임시 파일이 남아있지 않아야 한다.
    leftovers = [p for p in tmp_path.iterdir() if p != target]
    assert leftovers == []


def test_publish_is_atomic_no_partial_file_on_replace_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    projection = build_campaign_condition_history_projection(_sample_inputs())
    target = tmp_path / "seed-tree-01_condition_history_v1.json"

    def _boom(_src, _dst):
        raise OSError("simulated os.replace failure")

    monkeypatch.setattr(os, "replace", _boom)

    with pytest.raises(OSError):
        publish_condition_history("seed-tree-01", projection, tmp_path)

    assert not target.exists()
    # 임시 파일도 정리되어 남아있지 않아야 한다.
    assert list(tmp_path.iterdir()) == []


def test_publish_is_byte_identical_on_republish_of_identical_inputs(tmp_path: Path):
    inputs = _sample_inputs()
    projection_a = build_campaign_condition_history_projection(inputs)
    target_a = publish_condition_history("seed-tree-01", projection_a, tmp_path)
    bytes_a = target_a.read_bytes()

    other_dir = tmp_path / "second-publish"
    projection_b = build_campaign_condition_history_projection(_sample_inputs())
    target_b = publish_condition_history("seed-tree-01", projection_b, other_dir)
    bytes_b = target_b.read_bytes()

    assert bytes_a == bytes_b


def test_publish_creates_evidence_dir_if_missing(tmp_path: Path):
    projection = build_campaign_condition_history_projection(_legacy_inputs())
    evidence_dir = tmp_path / "nested" / "evidence"
    target = publish_condition_history("legacy-campaign", projection, evidence_dir)
    assert target.exists()
    assert target.parent == evidence_dir
