"""Inert, source-backed diagnostic report for one completed QSP7 analysis."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ai_strategy_loop.autopsy.trade_path_analysis import cohort_summaries
from ai_strategy_loop.autopsy.trade_path_analysis_models import (
    AnalysisTotals,
    EpisodeSummary,
    ExcludedTrade,
    TradePathAnalysis,
)
from ai_strategy_loop.autopsy.trade_path_models import RunSource, Timeframe, TradeResultRow
from ai_strategy_loop.dashboard.report_writer import render_report_html
from ai_strategy_loop.dashboard.trade_path_jobs import TradePathJob, trade_path_coordinator


trade_path_report_router = APIRouter()
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def _sidecar_source(path: Path, reason: str = "") -> dict[str, object]:
    payload: dict[str, object] = {"kind": "sqlite", "path": str(path)}
    if reason:
        payload["reason"] = reason
    return payload


def _sidecar_connect_readonly(path: Path) -> tuple[sqlite3.Connection | None, str]:
    if not path.is_file():
        return None, "source_missing"
    try:
        return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True), ""
    except sqlite3.Error:
        return None, "source_unavailable"


def _load_sidecar_analysis_readonly(
    path: Path, analysis_id: str,
) -> tuple[TradePathAnalysis | None, str]:
    connection, reason = _sidecar_connect_readonly(path)
    if connection is None:
        return None, reason
    try:
        row = connection.execute(
            "SELECT source_json, totals_json, episodes_json, exclusions_json,"
            " rows_json, decision_horizons, continuation_horizons"
            " FROM analyses WHERE analysis_id = ?",
            (analysis_id,),
        ).fetchone()
    except sqlite3.Error:
        return None, "source_unavailable"
    finally:
        connection.close()
    if row is None:
        return None, "analysis_not_found"
    try:
        source_data = json.loads(row[0])
        source_data["timeframe"] = Timeframe(source_data["timeframe"])
        return TradePathAnalysis(
            analysis_id=analysis_id,
            source=RunSource(**source_data),
            rows=tuple(TradeResultRow(**item) for item in json.loads(row[4])),
            episodes=tuple(EpisodeSummary(**item) for item in json.loads(row[2])),
            exclusions=tuple(ExcludedTrade(**item) for item in json.loads(row[3])),
            totals=AnalysisTotals(**json.loads(row[1])),
            decision_horizons=tuple(json.loads(row[5])),
            continuation_horizons=tuple(json.loads(row[6])),
        ), ""
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None, "source_unavailable"


def _readonly_trade_path_job(analysis_id: str) -> tuple[TradePathJob | None, str, Path]:
    coordinator = trade_path_coordinator()
    sidecar_path = coordinator.sidecar().path
    if not analysis_id:
        return None, "analysis_not_found", sidecar_path
    job = next((item for item in coordinator.list_jobs() if item.analysis_id == analysis_id), None)
    if job is not None and (job.status != "success" or job.result is not None):
        return job, "", sidecar_path
    restored, reason = _load_sidecar_analysis_readonly(sidecar_path, analysis_id)
    if restored is None:
        return job, reason, sidecar_path
    return TradePathJob(
        analysis_id, "success",
        1.0, restored.totals.trade_count, restored.totals.trade_count, "", restored,
    ), "", sidecar_path


def _unavailable_headers(reason: str) -> dict[str, str]:
    return {
        "Content-Security-Policy": _CSP,
        "Cache-Control": "no-store",
        "X-STOM-Authority": "diagnostic",
        "X-STOM-Available": "false",
        "X-STOM-Unavailable-Reason": reason,
        "X-STOM-Source-Reason": reason,
        "X-STOM-Source-Missing": str(reason == "source_missing").lower(),
    }


@trade_path_report_router.get("/report", response_class=HTMLResponse)
def trade_path_report(analysis_id: str = "") -> HTMLResponse:
    job, reason, _ = _readonly_trade_path_job(analysis_id)
    result = job.result if job is not None and job.status == "success" else None
    if result is None:
        reason = reason or ("analysis_not_ready" if job is not None else "analysis_not_found")
        return HTMLResponse("<h1>거래 경로 분석 결과가 없습니다.</h1>", status_code=404,
                            headers=_unavailable_headers(reason))
    totals = result.totals
    spec = {
        "research_id": analysis_id,
        "run_id": result.source.run_id,
        "step_id": "trade-path",
        "title": f"QSP7 거래 경로·매도 연구 — {result.source.run_id}",
        "template_id": "quant_research",
        "theme": "dark",
        "purpose": "실제 매도 이후부터 전체청산 경계까지의 잔여경로와 매도 후보를 진단",
        "hypothesis": "매도조건별 손실은 제거가 아니라 동일 진입의 대체 청산 경로로 평가해야 한다.",
        "method": (
            f"{result.source.timeframe.value} DB read-only · 전체청산 {result.source.forced_liquidation_time:06d} · "
            f"horizon {list(result.continuation_horizons)}초"
        ),
        "results": [
            f"대상 {totals.trade_count}건 · 분석 {totals.analyzed_count}건 · 제외 {totals.excluded_count}건",
            f"경계 전 손실회복 {totals.recovered_count}건 · 검열 outcome {totals.censored_outcome_count}건",
            f"분석 거래 실제 순손익 {totals.actual_profit_krw:,}원",
        ],
        "analysis": [
            f"{row.key}: {row.count}건 · 실제손익 {row.actual_profit_krw:,}원 · 회복 {row.recovered_count}건"
            for row in cohort_summaries(result)
        ],
        "conclusion": "이 문서는 DIAGNOSTIC입니다. 후보 채택은 공식 baseline/candidate pair 재백테스트 결과로만 결정합니다.",
        "limitations": [
            "전체청산 이후 가격은 조회하지 않음",
            "고정 진입 가상 재생은 이후 재진입·자본 재배분을 바꾸지 못함",
            "분할 체결 event ledger가 없는 거래는 가상 재생 승격 불가",
        ],
        "provenance": f"csv_sha256={result.source.csv_sha256}",
        "trust": "diagnostic",
        "kpis": {
            "분석 거래": totals.analyzed_count,
            "제외": totals.excluded_count,
            "경계 전 회복": totals.recovered_count,
            "실제 순손익(원)": totals.actual_profit_krw,
        },
    }
    return HTMLResponse(render_report_html(spec), headers={
        "Content-Security-Policy": _CSP,
        "Cache-Control": "no-store",
        "X-STOM-Authority": "diagnostic",
    })
