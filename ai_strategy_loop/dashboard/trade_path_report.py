"""Inert, source-backed diagnostic report for one completed QSP7 analysis."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ai_strategy_loop.autopsy.trade_path_analysis import cohort_summaries
from ai_strategy_loop.dashboard.report_writer import render_report_html
from ai_strategy_loop.dashboard.trade_path_jobs import trade_path_coordinator


trade_path_report_router = APIRouter()
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


@trade_path_report_router.get("/report", response_class=HTMLResponse)
def trade_path_report(analysis_id: str = "") -> HTMLResponse:
    job = trade_path_coordinator().get(analysis_id)
    result = job.result if job is not None and job.status == "success" else None
    if result is None:
        return HTMLResponse("<h1>거래 경로 분석 결과가 없습니다.</h1>", status_code=404,
                            headers={"Content-Security-Policy": _CSP})
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
