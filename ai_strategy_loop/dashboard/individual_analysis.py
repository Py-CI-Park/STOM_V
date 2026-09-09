"""Admission-aware projections of existing individual analysis operators."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Final, assert_never

from pydantic import ConfigDict, JsonValue, RootModel

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard.generation_json import finite_json

if TYPE_CHECKING:
    from ai_strategy_loop.dashboard.individual_source import AnalysisSource


class Operation(StrEnum):
    SUMMARY = "summary"
    EQUITY = "equity"
    DISTRIBUTION = "distribution"
    HEATMAP = "heatmap"
    UNDERWATER = "underwater"
    INSIGHTS = "insights"
    MAE_MFE = "mae_mfe"
    EXIT_REASONS = "exit_reasons"
    ORDERFLOW = "orderflow"
    GUI_PARITY = "gui_parity"
    MONTECARLO = "montecarlo"


@dataclass(frozen=True, slots=True)
class MonteCarloOptions:
    n: int = 2000
    seed: int | None = None
    ruin_pct: float = 30.0
    method: str = "shuffle"
    block_length: int = 5


class IndividualResult(RootModel[dict[str, JsonValue]]):
    """Versioned diagnostic envelope; neither a Bundle nor an execution receipt."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)


DEFAULT_MC: Final = MonteCarloOptions()


def individual_result(
    source: AnalysisSource,
    operation: Operation,
    job_id: str,
    run_id: str = "",
    gen_no: int | None = None,
    t_start: int | None = None,
    t_end: int | None = None,
    mc: MonteCarloOptions = DEFAULT_MC,
) -> IndividualResult:
    payload: dict[str, JsonValue] = {
        "job_id": job_id,
        "run_id": run_id,
        "gen_no": gen_no,
        "available": source.available,
        "analysis_ready": source.analysis_ready,
        "execution_status": source.execution_status,
        "execution_verified": False,
        "execution_basis": source.execution_basis,
        "analysis_authority": source.analysis_authority,
        "analysis_contract": "individual_result_quality_v1",
        "data_quality": source.checked.quality.model_dump(mode="json"),
        operation.value: None,
    }
    if not source.analysis_ready:
        return IndividualResult(payload)
    trades = analysis.filter_trades(
        [row.model_dump() for row in source.checked.trades],
        t_start,
        t_end,
    )
    match operation:
        case Operation.SUMMARY:
            value = analysis.summary_metrics(trades)
        case Operation.EQUITY:
            value = analysis.equity_series(trades)
        case Operation.DISTRIBUTION:
            value = analysis.pnl_distribution(trades)
        case Operation.HEATMAP:
            value = analysis.time_heatmap(trades)
        case Operation.UNDERWATER:
            value = analysis.underwater(trades)
        case Operation.INSIGHTS:
            value = analysis.generate_insights(trades)
        case Operation.MAE_MFE:
            value = analysis.mae_mfe(trades)
        case Operation.EXIT_REASONS:
            value = analysis.exit_reason_breakdown(trades)
        case Operation.ORDERFLOW:
            value = analysis.entry_orderflow(trades)
        case Operation.GUI_PARITY:
            value = analysis.gui_parity(trades)
        case Operation.MONTECARLO:
            value = analysis.monte_carlo(
                trades,
                n=mc.n,
                seed=mc.seed,
                ruin_pct=mc.ruin_pct,
                method=mc.method,
                block_length=mc.block_length,
            )
        case unreachable:
            assert_never(unreachable)
    projected = IndividualResult.model_validate({**payload, operation.value: value})
    return IndividualResult.model_validate(finite_json(projected.root))
