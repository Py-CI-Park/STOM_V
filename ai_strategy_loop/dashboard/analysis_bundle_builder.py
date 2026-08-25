"""Build a deterministic AnalysisBundle v2 from immutable legacy job evidence."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, TypeAdapter, ValidationError

from ai_strategy_loop.controller.research_truth_models import (
    ExecutionStatus,
    ResearchTruth,
)
from ai_strategy_loop.dashboard import backtest_analysis
from ai_strategy_loop.dashboard.analysis_bundle_artifacts import (
    AnalysisBundleBuildError,
    canonical_sha256,
    file_identity,
)
from ai_strategy_loop.dashboard.analysis_bundle_models import (
    ANALYSIS_BUNDLE_SCHEMA,
    AnalysisBundleV2,
    AnalysisSectionStatus,
    BundleAnalysisSection,
    BundleDecision,
    BundleEvidence,
    BundleExecution,
    BundleIdentity,
    BundlePreregistration,
    BundleSource,
    PreregistrationStatus,
    seal_analysis_bundle,
)
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue

_JSON_OBJECT = TypeAdapter(
    dict[str, JsonValue],
    config=ConfigDict(strict=True),
)


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        return {}
    try:
        return _JSON_OBJECT.validate_python(value)
    except ValidationError as exc:
        raise AnalysisBundleBuildError("analysis_bundle_invalid_json_object") from exc


def _number(value: JsonValue) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _integer(value: JsonValue) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _elapsed(record: dict[str, JsonValue]) -> float | None:
    started = _number(record.get("started_at"))
    finished = _number(record.get("finished_at"))
    if started is None or finished is None or finished < started:
        return None
    return finished - started


def _unavailable(status: AnalysisSectionStatus, reason: str) -> BundleAnalysisSection:
    return BundleAnalysisSection(status=status, reason=reason, values={})


def _observed(values: dict[str, JsonValue]) -> BundleAnalysisSection:
    return BundleAnalysisSection(
        status=AnalysisSectionStatus.OBSERVED,
        reason=None,
        values=values,
    )


def _analysis_sections(
    record: dict[str, JsonValue],
    truth: ResearchTruth,
    csv_path: Path | None,
) -> tuple[
    BundleAnalysisSection,
    BundleAnalysisSection,
    BundleAnalysisSection,
    BundleAnalysisSection,
    int | None,
]:
    if truth.execution is not ExecutionStatus.SUCCESS:
        reason = f"execution_{truth.execution.value.lower()}"
        unavailable = _unavailable(AnalysisSectionStatus.NOT_EVALUABLE, reason)
        return unavailable, unavailable, unavailable, unavailable, None
    if csv_path is None:
        metrics = _object(record.get("metrics"))
        return (
            _observed(metrics),
            _unavailable(AnalysisSectionStatus.NOT_RUN, "trade_csv_missing"),
            _unavailable(AnalysisSectionStatus.NOT_RUN, "trade_csv_missing"),
            _unavailable(AnalysisSectionStatus.NOT_RUN, "trade_csv_missing"),
            None,
        )
    try:
        full = _JSON_OBJECT.validate_python(
            backtest_analysis.full_analysis(csv_path.as_posix())
        )
    except ValidationError as exc:
        raise AnalysisBundleBuildError("analysis_bundle_analysis_not_json") from exc
    row_count = full.get("trade_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool):
        raise AnalysisBundleBuildError("analysis_bundle_trade_count_missing")
    if truth.trade_count != row_count:
        raise AnalysisBundleBuildError("analysis_bundle_trade_count_mismatch")
    metrics = _object(full.get("summary"))
    series = {
        key: full[key]
        for key in ("equity", "underwater", "rolling", "monthly", "cumulative_trades")
        if key in full
    }
    distribution = {
        key: full[key]
        for key in ("distribution", "mae_mfe", "exit_reasons")
        if key in full
    }
    attribution = {
        key: full[key]
        for key in ("heatmap", "orderflow", "insights")
        if key in full
    }
    return (
        _observed(metrics),
        _observed(series),
        _observed(distribution),
        _observed(attribution),
        row_count,
    )


def build_legacy_job_analysis_bundle(
    record: dict[str, JsonValue],
    truth: ResearchTruth,
    csv_path: Path | None,
) -> AnalysisBundleV2:
    """Build one read-only bundle; never writes the record, CSV, or a database."""
    spec = _object(record.get("spec"))
    hashes = _object(record.get("strategy_db_snapshot_hashes"))
    strategy_hashes = {
        key: value for key, value in hashes.items() if isinstance(value, str)
    }
    csv_sha256, csv_size = file_identity(csv_path)
    metrics, series, distribution, attribution, row_count = _analysis_sections(
        record,
        truth,
        csv_path,
    )
    diagnostics = _object(record.get("process_diagnostics"))
    event_count = _integer(diagnostics.get("event_count")) or 0
    checkpoint = diagnostics.get("last_checkpoint")
    finished_at = _number(record.get("finished_at"))
    artifact_paths = tuple(
        value
        for value in (
            csv_path.resolve().as_posix() if csv_path is not None else None,
            record.get("strategy_db_snapshot_path"),
            record.get("backtest_db_snapshot_path"),
        )
        if isinstance(value, str) and value
    )
    artifact_hashes = {"legacy_truth_input": truth.legacy_input_sha256}
    if csv_sha256 is not None:
        artifact_hashes["csv"] = csv_sha256

    payload: dict[str, JsonValue] = {
        "schema": ANALYSIS_BUNDLE_SCHEMA,
        "identity": BundleIdentity(
            job_id=truth.identity.job_id,
            candidate_id=truth.identity.candidate_id,
            parent_id=None,
            evidence_id=truth.identity.evidence_id,
            source_sha256=truth.identity.source_sha256,
            identity_status=truth.identity.identity_status,
        ).model_dump(mode="json"),
        "source": BundleSource(
            strategy_snapshot_hashes=strategy_hashes,
            legacy_spec_sha256=canonical_sha256(spec),
            csv_path=csv_path.resolve().as_posix() if csv_path is not None else None,
            csv_sha256=csv_sha256,
            csv_size_bytes=csv_size,
            engine_identity=truth.identity.engine_identity,
            config_identity=truth.identity.config_identity,
            data_identity=truth.identity.data_identity,
            git_commit=None,
        ).model_dump(mode="json"),
        "preregistration": BundlePreregistration(
            status=PreregistrationStatus.NOT_OBSERVED,
        ).model_dump(mode="json"),
        "execution": BundleExecution(
            status=truth.execution,
            failure_cause=truth.failure_cause,
            legacy_raw_status=truth.legacy_raw_status,
            return_code=_integer(record.get("returncode")),
            terminal_reason=str(record.get("message") or ""),
            elapsed_seconds=_elapsed(record),
            heartbeat_seconds=None,
            checkpoint=checkpoint if isinstance(checkpoint, str) else None,
            event_count=event_count,
            row_count=row_count,
            trade_count=truth.trade_count,
            correction_applied=truth.correction_applied,
            correction_reason=truth.correction_reason,
        ).model_dump(mode="json"),
        "metrics": metrics.model_dump(mode="json"),
        "series": series.model_dump(mode="json"),
        "distribution": distribution.model_dump(mode="json"),
        "episodes": _unavailable(
            AnalysisSectionStatus.NOT_RUN,
            "preregistered_episode_cohort_missing",
        ).model_dump(mode="json"),
        "attribution": attribution.model_dump(mode="json"),
        "counterfactual": _unavailable(
            AnalysisSectionStatus.NOT_RUN,
            "counterfactual_not_run",
        ).model_dump(mode="json"),
        "robustness": _unavailable(
            AnalysisSectionStatus.NOT_RUN,
            "fold_control_fdr_posterior_not_run",
        ).model_dump(mode="json"),
        "decision": BundleDecision(
            execution=truth.execution,
            economic=truth.economic,
            authority=truth.authority,
            next_action=truth.next_action,
            robustness_passed=truth.robustness_passed,
        ).model_dump(mode="json"),
        "evidence": BundleEvidence(
            artifact_paths=artifact_paths,
            artifact_hashes=artifact_hashes,
            generated_at=finished_at,
            generated_at_source=(
                "legacy_finished_at" if finished_at is not None else "not_observed"
            ),
        ).model_dump(mode="json"),
    }
    return seal_analysis_bundle(payload)
