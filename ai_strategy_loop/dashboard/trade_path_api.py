"""QSP7 trade-path, exit counterfactual, and official pair API."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from ai_strategy_loop.autopsy.exit_counterfactual import evaluate_policy
from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder, read_trade_rows
from ai_strategy_loop.autopsy.trade_path_analysis import cohort_summaries
from ai_strategy_loop.autopsy.trade_path_clock import liquidation_timestamp
from ai_strategy_loop.autopsy.trade_path_models import Clause, ExitPolicy, ExitRule
from ai_strategy_loop.dashboard.trade_path_api_models import AnalysisRequest, CounterfactualRequest, ProposalRequest
from ai_strategy_loop.dashboard.trade_path_jobs import TradePathJob, trade_path_coordinator
from ai_strategy_loop.dashboard.trade_path_official_api import official_trade_path_router
from ai_strategy_loop.dashboard.trade_path_report import trade_path_report_router
from ai_strategy_loop.dashboard.trade_path_source import resolve_job_source
from ai_strategy_loop.dashboard.trade_contract_api import trade_contract_router
from ai_strategy_loop.revision.sell_proposer import propose_sell_conditions


trade_path_router = APIRouter(prefix="/bt/trade-path", tags=["trade-path"])
trade_path_router.include_router(official_trade_path_router)
trade_path_router.include_router(trade_path_report_router)
trade_path_router.include_router(trade_contract_router)


def _job_payload(job: TradePathJob | None) -> dict[str, object]:
    if job is None:
        return {"available": False, "reason": "analysis_not_found"}
    payload: dict[str, object] = {
        "available": True,
        "analysis_id": job.analysis_id,
        "status": job.status,
        "progress": job.progress,
        "processed": job.processed,
        "total": job.total,
        "error": job.error,
        "authority": "diagnostic",
    }
    if job.result is not None:
        payload["summary"] = asdict(job.result.totals)
        payload["source"] = asdict(job.result.source)
    return jsonable_encoder(payload)


def _require_result(analysis_id: str):
    job = trade_path_coordinator().get(analysis_id)
    return job.result if job is not None and job.status == "success" else None


def _builder_for_result(result):
    resolved = resolve_job_source(
        result.source.run_id,
        forced_liquidation_time=result.source.forced_liquidation_time,
    )
    return EpisodeBuilder(
        repository=MarketPathRepository(database_dir=resolved.database_dir),
        code_info_db=resolved.code_info_db,
    )


def _episode(result, row_id: int, builder: EpisodeBuilder):
    row = next((item for item in result.rows if item.row_id == row_id), None)
    if row is None:
        raise ValueError("trade_not_found")
    return builder.build(
        run_id=result.source.run_id,
        row=row,
        timeframe=result.source.timeframe,
        forced_liquidation_time=result.source.forced_liquidation_time,
        decision_horizons=result.decision_horizons,
        continuation_horizons=result.continuation_horizons,
    )


def _exit_after_boundary_count(resolved, rows) -> int:
    unit = 1_000_000 if resolved.source.timeframe.value == "tick" else 10_000
    return sum(
        1 for row in rows
        if row.sell_time > liquidation_timestamp(
            row.buy_time // unit,
            resolved.source.forced_liquidation_time,
            resolved.source.timeframe,
        )
    )


@trade_path_router.get("/preflight")
def preflight(
    job_id: str = "", forced_liquidation_time: int | None = None,
) -> dict[str, object]:
    try:
        resolved = resolve_job_source(job_id, forced_liquidation_time=forced_liquidation_time)
        rows = read_trade_rows(Path(resolved.source.csv_path))
    except (OSError, ValueError) as exc:
        return {"available": False, "reason": str(exc), "authority": "diagnostic"}
    dates = {
        row.buy_time // (1_000_000 if resolved.source.timeframe.value == "tick" else 10_000)
        for row in rows
    }
    covered = sum(
        1 for date in dates
        if MarketPathRepository(database_dir=resolved.database_dir).database_path(
            date, resolved.source.timeframe,
        ) is not None
    )
    after_boundary = _exit_after_boundary_count(resolved, rows)
    boundary_payload = {
        "forced_liquidation_time": resolved.source.forced_liquidation_time,
        "boundary_source": resolved.boundary_source,
        "boundary_confidence": resolved.boundary_confidence,
    }
    if after_boundary:
        return jsonable_encoder({
            "available": False,
            "authority": "diagnostic",
            "reason": "actual_exit_after_forced_liquidation",
            "source": asdict(resolved.source),
            "trade_count": len(rows),
            "date_count": len(dates),
            "covered_date_count": covered,
            "exit_after_boundary_count": after_boundary,
            **boundary_payload,
        })
    return jsonable_encoder({
        "available": True,
        "authority": "diagnostic",
        "source": asdict(resolved.source),
        "trade_count": len(rows),
        "date_count": len(dates),
        "covered_date_count": covered,
        "counterfactual_limit": "forced_liquidation_boundary",
        **boundary_payload,
    })


@trade_path_router.post("/jobs")
def start_analysis(payload: AnalysisRequest) -> dict[str, object]:
    try:
        resolved = resolve_job_source(
            payload.job_id,
            forced_liquidation_time=payload.forced_liquidation_time,
        )
        rows = read_trade_rows(Path(resolved.source.csv_path))
    except (OSError, ValueError) as exc:
        return {"available": False, "status": "error", "reason": str(exc)}
    after_boundary = _exit_after_boundary_count(resolved, rows)
    if after_boundary:
        return {
            "available": False,
            "status": "error",
            "reason": "actual_exit_after_forced_liquidation",
            "exit_after_boundary_count": after_boundary,
        }
    job = trade_path_coordinator().submit(
        resolved=resolved,
        decision_horizons=payload.decision_horizons,
        continuation_horizons=payload.continuation_horizons,
    )
    return _job_payload(job)


@trade_path_router.get("/jobs/{analysis_id}")
def analysis_job(analysis_id: str) -> dict[str, object]:
    return _job_payload(trade_path_coordinator().get(analysis_id))


@trade_path_router.post("/jobs/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str) -> dict[str, object]:
    accepted = trade_path_coordinator().cancel(analysis_id)
    return {"available": accepted, "analysis_id": analysis_id, "status": "cancelling" if accepted else "missing"}


@trade_path_router.get("/summary")
def summary(analysis_id: str = "") -> dict[str, object]:
    result = _require_result(analysis_id)
    if result is None:
        return {"available": False, "reason": "analysis_not_ready"}
    return jsonable_encoder({
        "available": True, "authority": "diagnostic",
        "analysis_id": analysis_id, "summary": asdict(result.totals),
        "source": asdict(result.source), "exclusions": [asdict(row) for row in result.exclusions],
    })


@trade_path_router.get("/cohorts")
def cohorts(analysis_id: str = "") -> dict[str, object]:
    result = _require_result(analysis_id)
    rows = () if result is None else cohort_summaries(result)
    return jsonable_encoder({"available": result is not None, "authority": "diagnostic",
                             "cohorts": [asdict(row) for row in rows]})


@trade_path_router.get("/trades")
def trades(analysis_id: str = "", offset: int = 0, limit: int = 100,
           exit_reason: str = "") -> dict[str, object]:
    result = _require_result(analysis_id)
    if result is None:
        return {"available": False, "trades": []}
    rows = [row for row in result.episodes if not exit_reason or row.exit_reason == exit_reason]
    start, size = max(0, offset), max(1, min(500, limit))
    return jsonable_encoder({"available": True, "authority": "diagnostic", "total": len(rows),
                             "trades": [asdict(row) for row in rows[start:start + size]]})


@trade_path_router.get("/trade/{trade_key}")
def trade_detail(trade_key: str, analysis_id: str = "") -> dict[str, object]:
    result = _require_result(analysis_id)
    summary_row = None if result is None else next(
        (row for row in result.episodes if row.trade_key == trade_key), None,
    )
    if result is None or summary_row is None:
        return {"available": False, "reason": "trade_not_found"}
    try:
        episode = _episode(result, summary_row.row_id, _builder_for_result(result))
    except (OSError, ValueError) as exc:
        return {"available": False, "reason": str(exc)}
    return jsonable_encoder({"available": True, "episode": asdict(episode),
                             "authority": "diagnostic"})


@trade_path_router.post("/counterfactual")
def counterfactual(payload: CounterfactualRequest) -> dict[str, object]:
    result = _require_result(payload.analysis_id)
    if result is None:
        return {"available": False, "reason": "analysis_not_ready"}
    policy = ExitPolicy(payload.policy.name, tuple(
        ExitRule(rule.rule_id, tuple(Clause(item.field, item.operator, item.value)
                                     for item in rule.clauses), rule.after_seconds)
        for rule in payload.policy.rules
    ))
    wanted = set(payload.trade_keys)
    builder = _builder_for_result(result)
    outcomes, failures = [], []
    actual_reasons = {row.trade_key: row.exit_reason for row in result.episodes}
    for row in result.episodes:
        if wanted and row.trade_key not in wanted:
            continue
        try:
            outcomes.append(evaluate_policy(_episode(result, row.row_id, builder), policy))
        except (OSError, ValueError) as exc:
            failures.append({"trade_key": row.trade_key, "reason": str(exc)})
    transitions = Counter((actual_reasons[row.trade_key], row.triggered_rule_id) for row in outcomes)
    response = jsonable_encoder({
        "available": True, "authority": "advisory", "analysis_id": payload.analysis_id,
        "outcomes": [asdict(row) for row in outcomes], "failures": failures,
        "total_delta_profit_krw": sum(row.delta_profit_krw for row in outcomes),
        "transitions": [{"actual_reason": key[0], "candidate_reason": key[1], "count": count}
                        for key, count in sorted(transitions.items())],
    })
    trade_path_coordinator().set_counterfactual(payload.analysis_id, response)
    return response


@trade_path_router.get("/counterfactual/{analysis_id}")
def counterfactual_result(analysis_id: str) -> dict[str, object]:
    payload = trade_path_coordinator().get_counterfactual(analysis_id)
    return payload if isinstance(payload, dict) else {"available": False, "reason": "counterfactual_not_run"}


@trade_path_router.get("/transitions")
def transitions(analysis_id: str = "") -> dict[str, object]:
    payload = counterfactual_result(analysis_id)
    return {"available": payload.get("available", False), "authority": "advisory",
            "transitions": payload.get("transitions", [])}


@trade_path_router.post("/proposals")
def proposals(payload: ProposalRequest) -> dict[str, object]:
    result = _require_result(payload.analysis_id)
    rows = () if result is None else propose_sell_conditions(result)
    response = jsonable_encoder({"available": result is not None, "authority": "advisory",
                                 "saved": False, "proposals": [asdict(row) for row in rows]})
    if result is not None:
        trade_path_coordinator().add_proposals(payload.analysis_id, response)
    return response


@trade_path_router.get("/history")
def analysis_history() -> dict[str, object]:
    coordinator = trade_path_coordinator()
    return {"available": True, "analyses": [_job_payload(job) for job in coordinator.list_jobs()],
            "official_pairs": list(coordinator.official_pairs()),
            "records": list(coordinator.history_records())}
