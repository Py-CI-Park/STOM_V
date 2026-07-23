from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_chart_frame_requires_visible_metadata_and_bounded_table_fallback() -> None:
    source = _source("chart-frame.jsx")

    for label in ("단위", "기간", "표본", "신선도", "기준", "출처"):
        assert f'"{label}"' in source
    assert "chart-frame-state" in source
    assert "chart-frame-fallback" in source
    assert "<details" in source
    assert "<table>" in source
    assert "maxRows = 40" in source
    assert "displayRows" in source
    assert 'derivedState === "malformed"' in source
    assert 'stale: "차트 데이터의 최신 상태' in source

def test_v58_chart_data_contracts_fail_closed_and_key_selection_responses() -> None:
    frame = _source("chart-frame.jsx")
    detail = _source("chart-backtest-detail.jsx")
    equity = _source("chart-equity.jsx")
    history = _source("history-viz.jsx")

    assert '!["loading", "malformed", "error"].includes(state) && children' in frame
    assert "_backtestDetailRows" in detail
    assert "date !== cumulativeDate" in detail
    assert "requestRef.current.key !== key" in detail
    assert "AbortController" in detail
    assert 'evidence: "holding"' in detail
    assert "(!runId || curve.run_id === runId)" in detail
    assert "_validChartDate(date)" in detail
    assert "date <= rows[index - 1].date" in detail
    assert "status={detailStatus}" in detail
    assert "durationRequestRef" in detail
    assert "setPeriodInfo(null);" in detail
    assert "AbortSignal.any([controller.signal, AbortSignal.timeout(4000)])" in detail
    assert "durationRequestRef.current.key !== key || controller.signal.aborted" in detail
    assert "setPeriodInfo(first ? { runId, period: first.period, timeframe: first.timeframe } : null);" in detail
    assert "const periodMatchesRun = periodInfo && periodInfo.runId === runId;" in detail
    assert "period={periodMatchesRun && periodInfo.period" in detail
    assert "rawRows.length > 0 && !rows.length" in equity
    assert "_finiteChartValue" in equity
    assert "state && _finiteChartValue(state.max_generations)" in equity
    assert "Malformed or incomplete history page" in history
    assert "Truncated history page sequence" in history
    assert history.count("rowsRequestRef") >= 4
    assert "_hvHoldoutEvidence" in history
    assert 'includes("holdout_passed=true")' in history
    assert "typeof row.holdout_passed === \"boolean\"" in history
    assert "selectedRows = rowsMatchSelection ? rows : []" in history
    assert "setRowsLoading(true);\n    setRows([]);" in history
    assert "pairsRequestRef" in history
    assert "Object.values(sideRequestRef.current).forEach(request => request.controller.abort())" in history
    assert "pairsRequestRef.current.key !== key || controller.signal.aborted" in history
    assert "prev && items.some(item => item.research_id === prev)" in history


def test_v58_chart_fail_closed_source_contracts() -> None:
    frame = _source("chart-frame.jsx")
    detail = _source("chart-backtest-detail.jsx")
    equity = _source("chart-equity.jsx")
    history = _source("history-viz.jsx")

    assert "flatMap(row => Object.keys(row))" in frame
    assert "typeof curve.gate_passed === \"boolean\"" in detail
    assert "gate_passed === true" in detail
    assert "point_index, equity" in detail
    assert "_finiteChartNumber(summary.trade_count) && summary.trade_count === 0" in detail
    assert "setData(null); setErr(null); setHover(null); setLoading(false);" in detail
    assert "rawGens.every" in equity
    assert "g.gate_passed === true" in equity
    assert "_QUALITY_METRICS.every(m => g[m.key] == null || _finiteChartValue(g[m.key]))" in equity
    assert "typeof hasMore === \"boolean\"" in history
    assert "!hasMore && j.next_cursor != null" in history
    assert "holdout_passed === true" in history
    assert "Number.isFinite(metrics[key])" in history
    assert "}, [loadRows]);" in history
    assert 'status={rowsMatchSelection && rowsErr ? "malformed" : rowsMatchSelection && rowsLoading ? "stale"' in history

def test_core_live_history_backtest_charts_use_chart_frame_contract() -> None:
    owners = (
        "chart-equity.jsx",
        "v4-charts.jsx",
        "history-viz.jsx",
        "chart-backtest-detail.jsx",
        "bt-equity-charts.jsx",
        "bt-distribution-charts.jsx",
        "bt-gui-parity.jsx",
    )
    for name in owners:
        source = _source(name)
        assert 'from "./chart-frame.jsx"' in source, name
        assert "<ChartFrame" in source, name
        separator = ":" if "WithEvidence(" in source else "="
        for prop in ("unit", "period", "sampleCount", "freshness", "threshold", "source", "rows"):
            assert f"{prop}{separator}" in source, f"{name}: missing {prop}"
        if separator == "=":
            assert "status=" in source, f"{name}: missing status"


def test_chart_frame_styles_preserve_responsive_owned_scroll_region() -> None:
    css = _source("v4.css")

    assert ".chart-meta" in css
    assert ".chart-frame-state" in css
    assert ".chart-frame-fallback" in css
    assert ".chart-frame-table-wrap" in css
    assert "overflow-x: auto" in css
