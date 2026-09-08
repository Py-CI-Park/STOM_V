"""Report-only projections of existing checked sources; no result persistence."""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard.generation_json import GenerationJson, finite_json

if TYPE_CHECKING:
    from pydantic import JsonValue

    from ai_strategy_loop.dashboard.trade_csv_models import TradeQualityResult


def job_report(
    record: dict[str, JsonValue], checked: TradeQualityResult,
    meta: dict[str, JsonValue], t_start: int | None, t_end: int | None,
) -> dict[str, JsonValue]:
    ready = record.get("status") == "success" and checked.quality.analysis_ready
    bundle = analysis.full_analysis(
        None, t_start, t_end, prepared_trades=checked.trades,
    ) if ready else None
    summary = bundle["summary"] if bundle else None
    metrics = (summary if t_start is not None or t_end is not None
               else record.get("metrics") or summary) if ready else None
    payload: dict[str, JsonValue] = {
        "meta": {**meta, "trade_count": summary["trade_count"] if summary else None,
                 "note": "" if ready else "자료 품질 또는 실행 상태 미충족으로 분석을 보류합니다."},
        "metrics": metrics, "analysis": bundle, "analysis_ready": ready,
        "execution_status": record.get("status"),
        "analysis_contract": "job_result_quality_v1",
        "data_quality": checked.quality.model_dump(mode="json"),
    }
    return finish_report(payload, checked, t_start, t_end)


def finish_report(
    payload: dict[str, JsonValue], checked: TradeQualityResult,
    t_start: int | None = None, t_end: int | None = None,
) -> dict[str, JsonValue]:
    """Both metrics and diagnostic MC consume the same already checked snapshot."""
    mc = None
    if payload.get("analysis_ready") is True:
        trades = analysis.filter_trades(
            [row.model_dump() for row in checked.trades], t_start, t_end,
        )
        mc = analysis.monte_carlo(trades, n=2000)
    return GenerationJson.model_validate(finite_json({**payload, "montecarlo": mc})).root


def quality_html(payload: dict[str, JsonValue]) -> str:
    """Escaped human labels and finite machine evidence from one projection."""
    quality = payload.get("data_quality")
    if not isinstance(quality, dict):
        return ""
    keys = ("data_quality", "analysis_ready", "execution_status", "execution_verified",
            "execution_basis", "analysis_contract", "analysis_authority", "summary_authority")
    evidence = {key: payload[key] for key in keys if key in payload}
    encoded = json.dumps(finite_json(evidence), ensure_ascii=False, allow_nan=False)
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    label = "CSV 분석 준비 충족" if payload.get("analysis_ready") is True else "분석 보류"
    if payload.get("summary_authority") == "stored_unverified":
        label = "저장된 미검증 요약 · CSV 가 없어 재계산하지 않음"
    rows = [("판정", label), ("자료 품질", quality.get("status")),
            ("실행 상태", payload.get("execution_status")),
            ("원본 행", quality.get("raw_count")), ("정상 행", quality.get("accepted_count")),
            ("거부 행", quality.get("rejected_count")), ("예상 행", quality.get("expected_row_count")),
            ("CSV SHA256", quality.get("source_sha256"))]
    cells = "".join(f"<dt>{html.escape(key)}</dt><dd>{html.escape(str(value)) if value is not None else '—'}</dd>"
                    for key, value in rows)
    return ('<section id="sec-quality"><h2>자료 품질 · 실행 상태</h2><dl>' + cells +
            '</dl><p>자료 진단이며 경제적 유효성·자동채택 승인이 아닙니다.</p></section>' +
            f'<script type="application/json" id="stom-report-quality">{encoded}</script>')
