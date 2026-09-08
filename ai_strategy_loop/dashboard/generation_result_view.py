"""Quality-aware generation result projection using the original readonly owners."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, assert_never

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard.generation_json import (
    GenerationJson,
    finite_json,
    finite_metric,
    finite_timestamp,
)
from ai_strategy_loop.dashboard.generation_result_policy import generation_policy
from ai_strategy_loop.dashboard.job_result_quality import inspect_job_result_source

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import JsonValue

    from ai_strategy_loop.dashboard.trade_csv_models import TradeQualityResult

_STORED: Final = {
    "trade_count": "trade_count",
    "total_profit_krw": "profit",
    "total_profit_pct": "total_profit_pct",
    "max_drawdown_pct": "mdd",
    "payoff_ratio": "payoff_ratio",
}


@dataclass(frozen=True, slots=True)
class GenerationOwners:
    lookup: Callable[[str, int], dict[str, JsonValue] | None]
    resolve_csv: Callable[[dict[str, JsonValue]], str | None]
    identity: Callable[[dict[str, JsonValue]], dict[str, JsonValue]]
    context: Callable[
        [dict[str, JsonValue], str, int, dict[str, JsonValue] | None],
        dict[str, JsonValue],
    ]


def generation_result(
    run_id: str,
    gen_no: int,
    t_start: int | None = None,
    t_end: int | None = None,
    *,
    owners: GenerationOwners,
    prepared_source: TradeQualityResult | None = None,
) -> GenerationJson:
    """Separate recomputed CSV diagnostics from unverified stored summaries."""
    raw = owners.lookup(run_id, gen_no)
    if raw is None:
        return GenerationJson({"available": False, "run_id": run_id, "gen_no": gen_no})
    row = GenerationJson.model_validate(raw).root
    raw_status = row.get("status")
    match raw_status:
        case str():
            status = raw_status
        case None | bool() | int() | float() | list() | dict():
            status = None
        case unreachable:
            assert_never(unreachable)
    policy = generation_policy(status)
    csv_path = owners.resolve_csv(row)
    checked = prepared_source if prepared_source is not None else inspect_job_result_source(
        Path(csv_path) if csv_path else None,
        {"metrics": {"trade_count": row.get("trade_count")}},
    )
    ready = (
        bool(csv_path) and policy.diagnostic_allowed and checked.quality.analysis_ready
    )
    result: dict[str, JsonValue] = {
        "available": True,
        "run_id": run_id,
        "gen_no": gen_no,
        "evidence_id": f"gen:{run_id}:{gen_no}",
        "source_type": "generation",
        "condition_identity": owners.identity(row),
        "status": status,
        "status_kind": status or "generation",
        "artifact_state": "openable" if csv_path else "metrics_only_csv_missing",
        "openable": True,
        "recoverable": False,
        "open_actions": ["open_result"],
        "rerun_spec": None,
        "has_csv": bool(csv_path),
        "ranged": t_start is not None or t_end is not None,
        "execution_status": policy.execution.value.lower(),
        "execution_verified": False,
        "execution_basis": policy.basis,
        "analysis_ready": ready,
        "analysis_authority": "diagnostic_legacy_generation",
        "analysis_contract": "generation_result_quality_v1",
        "data_quality": checked.quality.model_dump(mode="json"),
        "metrics": None,
        "analysis": None,
        "summary_authority": "not_evaluable",
    }
    summary: dict[str, JsonValue] | None = None
    if ready:
        bundle = analysis.full_analysis(
            None, t_start, t_end, prepared_trades=checked.trades
        )
        summary = GenerationJson.model_validate(bundle["summary"]).root
        result.update(
            analysis=bundle, metrics=summary, summary_authority="csv_diagnostic"
        )
    elif not csv_path:
        result.update(
            metrics={
                key: finite_metric(row.get(source)) for key, source in _STORED.items()
            },
            summary_authority="stored_unverified",
            message=(
                "CSV가 없어 저장된 미검증 메트릭만 표시합니다. "
                "새 분석이나 실행 성공 증거가 아닙니다."
            ),
        )
    safe_row = dict(row)
    for key in ("profit", "total_profit_pct", "mdd", "score", "created_at"):
        safe_row[key] = finite_metric(row.get(key))
    safe_row["created_at"] = finite_timestamp(row.get("created_at"))
    result["context"] = owners.context(safe_row, run_id, gen_no, summary)
    return GenerationJson.model_validate(finite_json(result))
