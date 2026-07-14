"""Strict opt-in holdout contract tests; no runner or database access."""

import csv
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.holdout import (
    EVALUATION_INDETERMINATE,
    EVALUATION_PASS,
    EvaluationDescriptorV2,
    EvaluationRole,
    compute_holdout_verdict,
    issue_holdout_access_capability,
    validate_evaluation_descriptors,
    validate_holdout_access,
    validate_holdout_metric,
)


def _hash(character: str) -> str:
    return character * 64


def _descriptor(role, start, end, *, frozen=False):
    return EvaluationDescriptorV2(
        role=role,
        period_start=start,
        period_end=end,
        data_sha256=_hash("a") if role is EvaluationRole.TRAIN else _hash("d"),
        universe_sha256=_hash("b") if role is EvaluationRole.TRAIN else _hash("e"),
        row_sha256=_hash("c") if role is EvaluationRole.TRAIN else _hash("f"),
        metric_unit="krw",
        metric_version="v1",
        frozen=frozen,
        row_keys=(
            ("train-row-1", "train-row-2")
            if role is EvaluationRole.TRAIN
            else ("holdout-row-1", "holdout-row-2")
        ),
    )


def _disjoint_descriptors(*, frozen_holdout=False):
    return (
        _descriptor(EvaluationRole.TRAIN, 20260101, 20260131, frozen=True),
        _descriptor(EvaluationRole.HOLDOUT, 20260201, 20260228, frozen=frozen_holdout),
    )


def test_strict_descriptors_reject_period_overlap():
    train, holdout = _disjoint_descriptors()

    result = validate_evaluation_descriptors(
        train, replace(holdout, period_start=20260131)
    )

    assert result["status"] != EVALUATION_PASS
    assert "evaluation_period_overlap" in result["blockers"]
    assert result["promotion_eligible"] is False
    assert result["feedback_eligible"] is False


def test_strict_descriptors_reject_identical_row_hash():
    train, holdout = _disjoint_descriptors()

    result = validate_evaluation_descriptors(
        train, replace(holdout, row_sha256=train.row_sha256)
    )

    assert result["status"] != EVALUATION_PASS
    assert "evaluation_row_sha256_overlap" in result["blockers"]


def test_strict_descriptors_allow_shared_frozen_data_and_universe():
    train, holdout = _disjoint_descriptors()

    result = validate_evaluation_descriptors(
        train,
        replace(
            holdout,
            data_sha256=train.data_sha256,
            universe_sha256=train.universe_sha256,
        ),
    )

    assert result["status"] == EVALUATION_PASS


def test_strict_descriptors_reject_partial_row_membership_overlap():
    train, holdout = _disjoint_descriptors()

    result = validate_evaluation_descriptors(
        train,
        replace(holdout, row_keys=("holdout-row-1", "train-row-2")),
    )

    assert result["status"] != EVALUATION_PASS
    assert "evaluation_row_membership_overlap" in result["blockers"]


def test_holdout_capability_rejects_pre_freeze_issue_and_access():
    _, holdout = _disjoint_descriptors(frozen_holdout=False)

    with pytest.raises(PermissionError, match="before freeze"):
        issue_holdout_access_capability(holdout, "freeze-receipt")

    access = validate_holdout_access(holdout, None)
    assert access["status"] != EVALUATION_PASS
    assert "holdout_access_before_freeze" in access["blockers"]
    assert "holdout_access_capability_not_issued" in access["blockers"]


@pytest.mark.parametrize(
    ("metric", "actual_unit", "expected_unit", "actual_version", "expected_version", "timestamp", "expected_blocker"),
    [
        (None, "krw", "krw", "v1", "v1", datetime(2026, 1, 2, tzinfo=timezone.utc), "metric_missing"),
        (float("nan"), "krw", "krw", "v1", "v1", datetime(2026, 1, 2, tzinfo=timezone.utc), "metric_nonfinite"),
        (float("inf"), "krw", "krw", "v1", "v1", datetime(2026, 1, 2, tzinfo=timezone.utc), "metric_nonfinite"),
        (1.0, "percent", "krw", "v1", "v1", datetime(2026, 1, 2, tzinfo=timezone.utc), "metric_unit_mismatch"),
        (1.0, "krw", "krw", "v0", "v1", datetime(2026, 1, 2, tzinfo=timezone.utc), "metric_version_mismatch"),
        (1.0, "krw", "krw", "v1", "v1", datetime(2026, 1, 1, tzinfo=timezone.utc), "metric_stale"),
    ],
)
def test_invalid_strict_metrics_are_indeterminate(
    metric,
    actual_unit,
    expected_unit,
    actual_version,
    expected_version,
    timestamp,
    expected_blocker,
):
    result = validate_holdout_metric(
        metric,
        actual_unit=actual_unit,
        expected_unit=expected_unit,
        actual_version=actual_version,
        expected_version=expected_version,
        metric_timestamp=timestamp,
        max_age=timedelta(hours=12),
        now=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert result["status"] == EVALUATION_INDETERMINATE
    assert expected_blocker in result["blockers"]
    assert result["promotion_eligible"] is False
    assert result["feedback_eligible"] is False


@pytest.mark.parametrize(
    ("timestamp", "max_age", "expected_blocker"),
    [
        (datetime(2026, 1, 2), timedelta(hours=1), "metric_timestamp_timezone_missing"),
        ("2026-01-02", timedelta(hours=1), "metric_timestamp_invalid"),
        (
            datetime(2026, 1, 2, 2, tzinfo=timezone.utc),
            timedelta(hours=1),
            "metric_timestamp_future",
        ),
        (datetime(2026, 1, 2, tzinfo=timezone.utc), None, "metric_max_age_missing"),
        (
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            timedelta(hours=-1),
            "metric_max_age_invalid",
        ),
    ],
)
def test_strict_metric_rejects_ambiguous_future_or_missing_freshness(
    timestamp,
    max_age,
    expected_blocker,
):
    result = validate_holdout_metric(
        1.0,
        actual_unit="krw",
        expected_unit="krw",
        actual_version="v1",
        expected_version="v1",
        metric_timestamp=timestamp,
        max_age=max_age,
        now=datetime(2026, 1, 2, 1, tzinfo=timezone.utc),
    )

    assert result["status"] == EVALUATION_INDETERMINATE
    assert expected_blocker in result["blockers"]


def test_valid_strict_descriptor_access_and_metric_pass():
    train, holdout = _disjoint_descriptors(frozen_holdout=True)
    capability = issue_holdout_access_capability(holdout, "freeze-receipt")

    descriptor_result = validate_evaluation_descriptors(train, holdout)
    access_result = validate_holdout_access(holdout, capability)
    metric_result = validate_holdout_metric(
        1234.5,
        actual_unit="krw",
        expected_unit="krw",
        actual_version="v1",
        expected_version="v1",
        metric_timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        max_age=timedelta(hours=12),
        now=datetime(2026, 1, 2, 1, tzinfo=timezone.utc),
    )

    for result in (descriptor_result, access_result, metric_result):
        assert result["status"] == EVALUATION_PASS
        assert result["promotion_eligible"] is False
        assert result["feedback_eligible"] is False


def test_legacy_compute_holdout_verdict_remains_compatible(tmp_path):
    path = tmp_path / "legacy.csv"
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["매도시간", "수익금"])
        writer.writerows([
            ["202601011010", 1000.0],
            ["202601021010", 1000.0],
            ["202601031010", 1000.0],
            ["202601041010", 1000.0],
        ])

    verdict = compute_holdout_verdict(
        str(path),
        LoopConfig(min_trades=2, mdd_cap=35.0, holdout_recent_days=2),
    )

    assert verdict.status == "ok"
    assert verdict.passed is True
    assert verdict.holdout_days == [20260103, 20260104]
