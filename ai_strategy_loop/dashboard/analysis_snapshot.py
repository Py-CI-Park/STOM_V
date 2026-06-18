"""Persist local research-analysis snapshots from existing backtest CSVs."""

from __future__ import annotations

import json
import math
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias, TypedDict

from fastapi import APIRouter

from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.fitness.correlation import variable_correlation_from_csvs
from ai_strategy_loop.fitness.edge_ratio import edge_report_from_csvs
from ai_strategy_loop.fitness.equity_series import parse_backtest_series
from ai_strategy_loop.fitness.feature_importance import feature_importance_from_csvs

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class StoredAnalysisBundle(TypedDict):
    persisted: bool
    db_path: str
    analysis_id: int
    run_key: str
    row_counts: dict[str, int]
    source_count: int
    pooled_trades: int


@dataclass(frozen=True, slots=True)
class AnalysisRow:
    row_kind: str
    row_key: str
    metrics: JsonObject


REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
RESEARCH_ANALYSIS_DB = REPO_ROOT / "ai_strategy_loop" / "state" / "research_analysis.db"
analysis_router = APIRouter()


def _clean_json(value: JsonValue) -> JsonValue:
    match value:
        case None | bool() | str() | int():
            return value
        case float():
            return value if math.isfinite(value) else None
        case list():
            return [_clean_json(item) for item in value]
        case dict():
            return {str(key): _clean_json(item) for key, item in value.items()}


def _json_text(value: JsonValue) -> str:
    return json.dumps(_clean_json(value), ensure_ascii=False, sort_keys=True, allow_nan=False)


def _object(value: JsonValue) -> JsonObject:
    match value:
        case dict():
            return {str(key): _clean_json(item) for key, item in value.items()}
        case _:
            return {}


def _objects(value: JsonValue) -> list[JsonObject]:
    match value:
        case list():
            return [_object(item) for item in value if _object(item)]
        case _:
            return []


def _text(row: JsonObject, key: str, fallback: str) -> str:
    value = row.get(key)
    match value:
        case str():
            return value
        case int() | float():
            return str(value)
        case _:
            return fallback


def _add_list_rows(rows: list[AnalysisRow], row_kind: str, values: JsonValue, key: str) -> None:
    for index, item in enumerate(_objects(values)):
        rows.append(AnalysisRow(row_kind=row_kind, row_key=_text(item, key, str(index)), metrics=item))


def _analysis_rows(reports: JsonObject) -> list[AnalysisRow]:
    rows: list[AnalysisRow] = []
    correlation = _object(reports.get("variable_correlation"))
    _add_list_rows(rows, "b_variable_correlation", correlation.get("outcome_correlations"), "feature")
    _add_list_rows(rows, "b_variable_range", correlation.get("range_summaries"), "feature")
    _add_list_rows(rows, "compound_feature_interaction", correlation.get("interaction_candidates"), "feature_a")
    segments = _object(correlation.get("segment_summaries"))
    _add_list_rows(rows, "time_bucket", segments.get("time"), "label")
    _add_list_rows(rows, "market_cap_band", segments.get("market_cap"), "label")
    _add_list_rows(rows, "year_segment", segments.get("year"), "label")

    edge = _object(reports.get("edge_ratio"))
    edge_global = _object(edge.get("global"))
    if edge_global:
        rows.append(AnalysisRow(row_kind="edge_global", row_key="global", metrics=edge_global))
    edge_segments = _object(edge.get("segments"))
    _add_list_rows(rows, "time_bucket_edge", edge_segments.get("time"), "label")
    _add_list_rows(rows, "market_cap_edge", edge_segments.get("market_cap"), "label")
    _add_list_rows(rows, "time_cap_edge", edge_segments.get("cross"), "label")

    feature = _object(reports.get("feature_importance"))
    _add_list_rows(rows, "feature_importance", feature.get("global"), "feature")
    _add_list_rows(rows, "generation_metric", reports.get("generation_metrics"), "gen_no")
    _add_list_rows(rows, "daily_profit_loss", reports.get("daily_profit_loss"), "date")
    return rows


def _numeric_summary(reports: JsonObject, key: str) -> int:
    values: list[int] = []
    for value in reports.values():
        row = _object(value)
        raw = row.get(key)
        match raw:
            case int() | float():
                values.append(int(raw))
            case _:
                continue
    return max(values, default=0)


def persist_analysis_bundle(
    *,
    db_path: Path,
    run_key: str,
    reports: JsonObject,
    params: dict[str, str],
) -> StoredAnalysisBundle:
    """Persist one research-only analysis bundle into local SQLite tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = _object(reports)
    rows = _analysis_rows(cleaned)
    now = time.time()
    with sqlite3.connect(db_path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS analysis_snapshots (
                analysis_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                run_key       TEXT NOT NULL,
                params_json   TEXT NOT NULL,
                payload_json  TEXT NOT NULL,
                source_count  INTEGER NOT NULL,
                pooled_trades INTEGER NOT NULL,
                created_at    REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analysis_rows (
                analysis_id  INTEGER NOT NULL,
                row_kind     TEXT NOT NULL,
                row_key      TEXT NOT NULL,
                metrics_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_analysis_rows_kind
                ON analysis_rows(analysis_id, row_kind);
            """
        )
        source_count = _numeric_summary(cleaned, "sources")
        pooled_trades = _numeric_summary(cleaned, "pooled_trades")
        cur = con.execute(
            "INSERT INTO analysis_snapshots "
            "(run_key, params_json, payload_json, source_count, pooled_trades, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_key, _json_text(params), _json_text(cleaned), source_count, pooled_trades, now),
        )
        analysis_id = int(cur.lastrowid)
        con.executemany(
            "INSERT INTO analysis_rows (analysis_id, row_kind, row_key, metrics_json) VALUES (?, ?, ?, ?)",
            [(analysis_id, row.row_kind, row.row_key, _json_text(row.metrics)) for row in rows],
        )

    return {
        "persisted": True,
        "db_path": str(db_path),
        "analysis_id": analysis_id,
        "run_key": run_key,
        "row_counts": dict(Counter(row.row_kind for row in rows)),
        "source_count": source_count,
        "pooled_trades": pooled_trades,
    }


def _target_runs(run_id: str, run_ids: str) -> list[str]:
    if run_ids.strip():
        return [item.strip() for item in run_ids.split(",") if item.strip()]
    return [run_id.strip()] if run_id.strip() else []


def _resolve_path(path_text: str) -> str:
    path = Path(path_text)
    return str(path if path.is_absolute() else REPO_ROOT / path)


def _generation_context(target_runs: list[str]) -> tuple[list[str], list[JsonObject]]:
    seen: set[str] = set()
    paths: list[str] = []
    metrics: list[JsonObject] = []
    state = LoopState()
    try:
        for run in target_runs:
            for row in state.get_generations(run):
                csv_path = str(row.get("csv_path") or "")
                metrics.append({
                    "run_id": str(row.get("run_id") or run),
                    "gen_no": int(row.get("gen_no", -1) or -1),
                    "trade_count": int(row.get("trade_count", 0) or 0),
                    "profit": float(row.get("profit", 0.0) or 0.0),
                    "mdd": float(row.get("mdd", 0.0) or 0.0),
                    "payoff_ratio": float(row.get("payoff_ratio", 0.0) or 0.0),
                    "daily_avg_trades": float(row.get("daily_avg_trades", 0.0) or 0.0),
                    "max_hold_count": float(row.get("max_hold_count", 0.0) or 0.0),
                    "csv_path": csv_path,
                })
                if csv_path and csv_path not in seen:
                    seen.add(csv_path)
                    paths.append(_resolve_path(csv_path))
    finally:
        state.close()
    return paths, metrics


def _daily_profit_loss(csv_paths: list[str]) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for csv_path in csv_paths:
        daily = _objects(_object(parse_backtest_series(csv_path)).get("daily"))
        for row in daily:
            rows.append({"csv_path": csv_path, **row})
    return rows


def _analysis_reports(csv_paths: list[str], method: str, axis: str, fine_time: bool,
                      generation_metrics: list[JsonObject]) -> JsonObject:
    return {
        "variable_correlation": variable_correlation_from_csvs(csv_paths, method=method),
        "edge_ratio": edge_report_from_csvs(csv_paths, fine_time=fine_time, min_samples=1),
        "feature_importance": feature_importance_from_csvs(
            csv_paths, axis=axis, fine_time=fine_time, min_per_group=1, min_cell=1,
        ),
        "generation_metrics": generation_metrics,
        "daily_profit_loss": _daily_profit_loss(csv_paths),
        "metric_explanations_ko": {
            "edge_ratio": "평균 MFE를 평균 |MAE|로 나눈 값입니다. 1보다 크면 진입 후 유리한 흔들림이 불리한 흔들림보다 큽니다.",
            "payoff_ratio": "평균 이익 거래 크기를 평균 손실 거래 크기로 나눈 값입니다. 낮은 승률을 큰 이익으로 보상하는지 봅니다.",
            "daily_profit_loss": "CSV 거래를 매도일 기준으로 묶은 일별 손익입니다. 전체 우상향과 손실일 회복 여부를 볼 때 씁니다.",
        },
    }


@analysis_router.get("/analysis_snapshot", response_model=None)
def analysis_snapshot(run_id: str = "", run_ids: str = "", persist: bool = False,
                      method: str = "spearman", axis: str = "time",
                      fine_time: bool = True) -> JsonObject:
    """Build and optionally persist a local research-only analysis snapshot."""
    target_runs = _target_runs(run_id, run_ids)
    if not target_runs:
        return {"ok": False, "status": "missing_run", "runs": [], "csv_count": 0,
                "persisted": False, "store": None, "analysis": {}}
    csv_paths, generation_metrics = _generation_context(target_runs)
    if not csv_paths:
        return {"ok": True, "status": "no_csv", "runs": target_runs, "csv_count": 0,
                "persisted": False, "store": None, "analysis": {}}

    reports = _analysis_reports(csv_paths, method, axis, fine_time, generation_metrics)
    store = None
    if persist:
        store = persist_analysis_bundle(
            db_path=RESEARCH_ANALYSIS_DB,
            run_key=",".join(target_runs),
            reports=reports,
            params={"method": method, "axis": axis, "fine_time": str(bool(fine_time))},
        )
    return {
        "ok": True,
        "status": "ok",
        "runs": target_runs,
        "csv_count": len(csv_paths),
        "persisted": bool(store),
        "store": store,
        "analysis": reports,
    }
