from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_strategy_loop.controller.research_truth_contract import ExecutionStatus
from ai_strategy_loop.controller.research_truth_models import ResearchTruth
from ai_strategy_loop.dashboard.analysis_bundle_builder import (
    AnalysisBundleBuildError,
    build_legacy_job_analysis_bundle,
)
from ai_strategy_loop.dashboard.analysis_bundle_models import (
    AnalysisBundleV2,
    seal_analysis_bundle,
)
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import project_legacy_job_truth

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "research_truth_ui"
)


def _record(name: str) -> dict[str, JsonValue]:
    value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _truth(record: dict[str, JsonValue]) -> ResearchTruth:
    return project_legacy_job_analysis_truth(record)


def project_legacy_job_analysis_truth(
    record: dict[str, JsonValue],
) -> ResearchTruth:
    return project_legacy_job_truth(
        record,
        manager_id="analysis-fixtures",
        jobs_dir=FIXTURES.as_posix(),
        log_size_bytes=None,
    )


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "trades.csv"
    path.write_text(
        "﻿종목명,매수시간,매도시간,보유시간,수익률,수익금\n"
        "알파,202504070930,202504071000,30,2.0,20000\n"
        "베타,202504071030,202504071100,30,-1.0,-10000\n"
        "감마,202504081030,202504081100,30,0.5,5000\n",
        encoding="utf-8",
    )
    return path


def test_same_inputs_produce_identical_content_and_hash(tmp_path: Path) -> None:
    record = _record("ux_fixture_success.json")
    record["finished_at"] = 1_725_000_000.0
    csv_path = _csv(tmp_path)

    first = build_legacy_job_analysis_bundle(record, _truth(record), csv_path)
    second = build_legacy_job_analysis_bundle(record, _truth(record), csv_path)

    assert first == second
    assert first.content_sha256 == second.content_sha256
    assert first.identity.job_id == "UX_FIXTURE_SUCCESS"
    assert first.identity.evidence_id.startswith("evidence_")
    assert first.source.csv_sha256 is not None
    assert first.execution.status is ExecutionStatus.SUCCESS
    assert first.execution.row_count == 3
    assert first.metrics.status == "OBSERVED"
    assert first.metrics.values["trade_count"] == 3
    assert first.series.status == "OBSERVED"
    assert first.episodes.status == "NOT_RUN"
    assert first.robustness.status == "NOT_RUN"
    assert first.evidence.generated_at == 1_725_000_000.0
    assert first.evidence.persistence == "none"


def test_content_hash_rejects_mutated_bundle(tmp_path: Path) -> None:
    record = _record("ux_fixture_success.json")
    payload = build_legacy_job_analysis_bundle(
        record,
        _truth(record),
        _csv(tmp_path),
    ).model_dump(mode="json", by_alias=True)
    metrics = payload["metrics"]
    assert isinstance(metrics, dict)
    values = metrics["values"]
    assert isinstance(values, dict)
    values["trade_count"] = 99

    with pytest.raises(ValidationError, match="analysis_bundle_content_hash_mismatch"):
        AnalysisBundleV2.model_validate_json(
            json.dumps(payload, ensure_ascii=False)
        )


def test_resealed_legacy_bundle_rejects_elevated_authority(tmp_path: Path) -> None:
    record = _record("ux_fixture_success.json")
    payload = build_legacy_job_analysis_bundle(
        record,
        _truth(record),
        _csv(tmp_path),
    ).model_dump(mode="json", by_alias=True, exclude={"content_sha256"})
    decision = payload["decision"]
    assert isinstance(decision, dict)
    decision["authority"] = "LIVE"

    with pytest.raises(
        ValidationError,
        match="legacy_analysis_bundle_forbids_elevated_authority",
    ):
        seal_analysis_bundle(payload)


def test_csv_trade_count_contradiction_fails_closed(tmp_path: Path) -> None:
    record = _record("ux_fixture_success.json")
    metrics = record["metrics"]
    assert isinstance(metrics, dict)
    metrics["trade_count"] = 4

    with pytest.raises(AnalysisBundleBuildError, match="trade_count_mismatch"):
        build_legacy_job_analysis_bundle(record, _truth(record), _csv(tmp_path))


@pytest.mark.parametrize(
    ("fixture_name", "execution", "section_status"),
    (
        ("ux_fixture_no_trades.json", ExecutionStatus.NO_TRADES, "NOT_EVALUABLE"),
        ("ux_fixture_error.json", ExecutionStatus.ERROR, "NOT_EVALUABLE"),
        ("ux_fixture_timeout.json", ExecutionStatus.TIMEOUT, "NOT_EVALUABLE"),
        ("ux_fixture_partial.json", ExecutionStatus.PARTIAL, "NOT_EVALUABLE"),
    ),
)
def test_non_success_states_do_not_synthesize_analysis(
    fixture_name: str,
    execution: ExecutionStatus,
    section_status: str,
) -> None:
    record = _record(fixture_name)

    bundle = build_legacy_job_analysis_bundle(record, _truth(record), None)

    assert bundle.execution.status is execution
    assert bundle.metrics.status == section_status
    assert bundle.metrics.values == {}
    assert bundle.series.status == section_status
    assert bundle.distribution.status == section_status
    assert bundle.decision.execution is execution
    assert bundle.source.csv_sha256 is None
