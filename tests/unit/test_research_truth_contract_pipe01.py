from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pytest

from ai_strategy_loop.controller import research_truth_contract as sut


@dataclass(frozen=True, slots=True)
class PipeCase:
    name: str
    raw_status: str
    return_code: int
    metrics_present: bool
    trade_count: int | None
    total_profit_pct: float | None
    process_event_count: int
    last_checkpoint: str | None
    source_checkpoints: tuple[str, ...]
    message: str
    execution: sut.ExecutionStatus
    economic: sut.EconomicStatus
    cause: sut.FailureCause
    action: sut.NextAction
    correction_applied: bool = False
    process_diagnostics_present: bool | None = True
    log_size_bytes: int | None = 1


PIPE_01_CASES = (
    PipeCase(
        "absorption_success", "success", 0, True, 2, -1.67, 210,
        "backtest_child_completed", ("engine_backtest_completed",), "ok",
        sut.ExecutionStatus.SUCCESS, sut.EconomicStatus.INCONCLUSIVE,
        sut.FailureCause.NONE, sut.NextAction.REPRODUCE,
    ),
    PipeCase(
        "absorption_data_timeout", "error", 3, False, None, None, 0, None, (),
        "engine_data_response_timeout expected=1 received=0 missing=1",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT, sut.NextAction.DEBUG,
    ),
    PipeCase(
        "failed_breakout_masked_99651", "no_trades", 2, False, None, None, 19,
        "engine_strategy_exception", ("engine_strategy_exception",),
        "TypeError: list indices must be integers or slices, not str",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_STRATEGY_EXCEPTION_TYPE_ERROR_LIST_STRING_INDEX,
        sut.NextAction.DEBUG, True,
    ),
    PipeCase(
        "failed_breakout_masked_1293", "no_trades", 2, False, None, None, 17,
        "backtest_child_mq_first_received", ("engine_strategy_exception",),
        "백테중지 TypeError: list indices must be integers or slices, not str",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_STRATEGY_EXCEPTION_TYPE_ERROR_LIST_STRING_INDEX,
        sut.NextAction.DEBUG, True,
    ),
    PipeCase(
        "compression_success", "success", 0, True, 4, -1.93, 210,
        "backtest_child_completed", ("engine_backtest_completed",), "ok",
        sut.ExecutionStatus.SUCCESS, sut.EconomicStatus.INCONCLUSIVE,
        sut.FailureCause.NONE, sut.NextAction.REPRODUCE,
    ),
    PipeCase(
        "compression_data_timeout", "error", 3, False, None, None, 0, None, (),
        "engine_data_response_timeout expected=1 received=0 missing=1",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT, sut.NextAction.DEBUG,
    ),
    PipeCase(
        "flow_data_timeout", "error", 3, False, None, None, 0, None, (),
        "engine_data_response_timeout expected=1 received=0 missing=1",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT, sut.NextAction.DEBUG,
    ),
    PipeCase(
        "flow_watchdog_timeout", "timeout", 1, False, None, None, 0, None, (),
        "timeout (>210s)", sut.ExecutionStatus.TIMEOUT,
        sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY,
        sut.NextAction.DEBUG, False, False, 0,
    ),
    PipeCase(
        "opening_data_timeout", "error", 3, False, None, None, 0, None, (),
        "engine_data_response_timeout expected=1 received=0 missing=1",
        sut.ExecutionStatus.ERROR, sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.ENGINE_DATA_RESPONSE_TIMEOUT, sut.NextAction.DEBUG,
    ),
    PipeCase(
        "opening_watchdog_timeout", "timeout", 1, False, None, None, 0, None, (),
        "timeout (>210s)", sut.ExecutionStatus.TIMEOUT,
        sut.EconomicStatus.NOT_EVALUABLE,
        sut.FailureCause.WATCHDOG_HARD_TIMEOUT_NO_PROTOCOL_TELEMETRY,
        sut.NextAction.DEBUG, False, False, 0,
    ),
)


def _identity(
    jobs_dir: str,
    job_id: str,
    candidate_id: str,
    source_sha256: str,
) -> sut.EvidenceIdentity:
    return sut.EvidenceIdentity(
        manager_id=jobs_dir.removeprefix("webbt_jobs") or "default",
        jobs_dir=f"ai_strategy_loop/state/{jobs_dir}",
        job_id=job_id,
        candidate_id=candidate_id,
        source_sha256=source_sha256,
        identity_status=sut.EvidenceIdentityStatus.LEGACY_INCOMPLETE,
        engine_identity=None,
        config_identity=None,
        data_identity=None,
    )


PIPE_IDENTITIES = {
    "absorption_success": _identity(
        "webbt_jobs",
        "20260815_170623_D3ABSORPTIONREVERSALMCAP_83877",
        "D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_cb7275dfee",
        "91a666673ceb5488c64bc8647855ec62700a722093bb4b373c4cddb466f93277",
    ),
    "absorption_data_timeout": _identity(
        "webbt_jobs_8780",
        "20260815_170623_D3ABSORPTIONREVERSALMCAP_83878",
        "D3_ABSORPTION_REVERSAL_MCAP_A_LT3000_7cc938d0ce",
        "2d08df2aa9e0af2e84c22ab3747349141b3c39a63d9bbdc4e2c2ecc27e46a2f5",
    ),
    "failed_breakout_masked_99651": _identity(
        "webbt_jobs",
        "20260815_170959_D3FAILEDBREAKOUTRETURNMC_99651",
        "D3_FAILED_BREAKOUT_RETURN_MCAP_A_LT3000_cc12f7a023",
        "35f8d350c98649d56314445da341ed2757e5099cc50056c961d9b5fc39995dc5",
    ),
    "failed_breakout_masked_1293": _identity(
        "webbt_jobs_8780",
        "20260815_171141_D3FAILEDBREAKOUTRETURNMC_1293",
        "D3_FAILED_BREAKOUT_RETURN_MCAP_A_LT3000_8432eb62ad",
        "d67263bc6c5c4e4a3a220ecf5dd75d171ce4e90477a37ba95007d9e76ccf263b",
    ),
    "compression_success": _identity(
        "webbt_jobs",
        "20260815_171608_D3COMPRESSIONCONFIRMEDBR_68279",
        "D3_COMPRESSION_CONFIRMED_BREAKOUT_MCAP_A_LT3000_f6320dda9d",
        "89be531494ca51a4e729f7d522aee5a1b3ccabcc4522375d20847c2d13e6d10e",
    ),
    "compression_data_timeout": _identity(
        "webbt_jobs_8780",
        "20260815_171628_D3COMPRESSIONCONFIRMEDBR_88215",
        "D3_COMPRESSION_CONFIRMED_BREAKOUT_MCAP_A_LT3000_c467ae6049",
        "ce319e33ab2e0381c1b7f7d887928772da8a1fce1ba4d46bff916dd0fcc9a5cc",
    ),
    "flow_data_timeout": _identity(
        "webbt_jobs",
        "20260815_172055_D3FLOWPRICEDIVERGENCEMCA_55325",
        "D3_FLOW_PRICE_DIVERGENCE_MCAP_A_LT3000_0d4702a73a",
        "a971831a8bf0d47748960a694248cec9fe5a8958c9663ea9a5ee22adeecd14ce",
    ),
    "flow_watchdog_timeout": _identity(
        "webbt_jobs_8780",
        "20260815_172100_D3FLOWPRICEDIVERGENCEMCA_60475",
        "D3_FLOW_PRICE_DIVERGENCE_MCAP_A_LT3000_f3a20122f8",
        "cc82a8b6b880aaced78d5ca6a6366887cac8e5b9b249a7d33ddbfe507e10ffbd",
    ),
    "opening_data_timeout": _identity(
        "webbt_jobs",
        "20260815_172557_D3OPENINGOVERREACTIONMEA_57938",
        "D3_OPENING_OVERREACTION_MEAN_REVERT_MCAP_A_LT3000_329183a66b",
        "1d928b896b384183cbc29192ba2b276664374b6ae5625bd6075e1c8571994c1b",
    ),
    "opening_watchdog_timeout": _identity(
        "webbt_jobs_8780",
        "20260815_172603_D3OPENINGOVERREACTIONMEA_63314",
        "D3_OPENING_OVERREACTION_MEAN_REVERT_MCAP_A_LT3000_7c32ce3533",
        "f177172e7718bd229a23e1615788af76345f1ed3a27b8ff0619f196fa6e774dc",
    ),
}


def _project(case: PipeCase) -> sut.ResearchTruth:
    return sut.derive_research_truth(
        sut.LegacyTruthInput(
            identity=PIPE_IDENTITIES[case.name],
            raw_status=case.raw_status,
            return_code=case.return_code,
            metrics_present=case.metrics_present,
            trade_count=case.trade_count,
            total_profit_pct=case.total_profit_pct,
            sample_adequate=False,
            process_event_count=case.process_event_count,
            process_diagnostics_present=case.process_diagnostics_present,
            log_size_bytes=case.log_size_bytes,
            last_checkpoint=case.last_checkpoint,
            source_checkpoints=case.source_checkpoints,
            message=case.message,
        )
    )


@pytest.mark.parametrize("case", PIPE_01_CASES, ids=tuple(c.name for c in PIPE_01_CASES))
def test_pipe_01_cases_are_projected_into_independent_truth_axes(case: PipeCase) -> None:
    truth = _project(case)

    assert truth.execution is case.execution
    assert truth.economic is case.economic
    assert truth.failure_cause is case.cause
    assert truth.next_action is case.action
    assert truth.authority is sut.EvidenceAuthority.FEASIBILITY
    assert truth.correction_applied is case.correction_applied
    assert truth.legacy_raw_status == case.raw_status
    assert truth.identity == PIPE_IDENTITIES[case.name]


def test_pipe_01_corrected_aggregate_is_complete() -> None:
    truths = tuple(_project(case) for case in PIPE_01_CASES)
    counts = Counter(truth.execution for truth in truths)

    assert counts == {
        sut.ExecutionStatus.SUCCESS: 2,
        sut.ExecutionStatus.ERROR: 6,
        sut.ExecutionStatus.TIMEOUT: 2,
    }
    assert counts[sut.ExecutionStatus.NO_TRADES] == 0
    assert len({truth.identity.evidence_id for truth in truths}) == 10
    assert len({truth.legacy_input_sha256 for truth in truths}) == 10
