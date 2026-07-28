"""Self-contained operating summary for the backtest HTML report."""

from __future__ import annotations

import html
from typing import Any, Mapping


def _pick(metrics: Mapping[str, Any], summary: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if metrics.get(key) is not None:
            return metrics[key]
        if summary.get(key) is not None:
            return summary[key]
    return None


def _number(value: Any, digits: int = 0) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:,.{digits}f}"


def _percent(value: Any, *, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:.2f}%"


def _number_with_unit(value: Any, unit: str, digits: int = 0) -> str:
    rendered = _number(value, digits)
    return rendered if rendered == "—" else rendered + unit


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _bar(label: str, value: Any, color: str) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    width = max(3.0, min(100.0, abs(number)))
    return (
        '<div style="display:grid;grid-template-columns:130px 1fr 90px;gap:10px;align-items:center;margin:7px 0">'
        f'<span>{_escape(label)}</span><i style="display:block;height:12px;background:#0e1117;border:1px solid #272d36;border-radius:7px;overflow:hidden">'
        f'<b style="display:block;width:{width:.1f}%;height:100%;background:{color}"></b></i>'
        f'<strong style="text-align:right">{_escape(_percent(number, signed=label != "MDD"))}</strong></div>'
    )


def _hold(seconds: Any) -> str:
    """보유시간(초) → 사람이 읽는 문자열. 엔진 CSV 단위(tick=초/min=분)는 서버가 이미 초로 정규화."""
    try:
        if seconds is None:
            return "미발행"
        sec = float(seconds)
    except (TypeError, ValueError):
        return "미발행"
    if sec <= 0:
        return "미발행"
    if sec < 60:
        return f"{sec:.0f}초"
    if sec < 3600:
        return f"{sec / 60:.1f}분"
    return f"{sec / 3600:.1f}시간"


def render_metric_summary(
    metrics: Mapping[str, Any] | None,
    summary: Mapping[str, Any] | None,
) -> str:
    """Render cards, visual bars, and a text table from published values only."""
    m = metrics or {}
    s = summary or {}
    rows = [
        ("거래수", _number(_pick(m, s, "trade_count")), "trade_count"),
        ("승률", _percent(_pick(m, s, "win_rate", "win_rate_pct")), "win_rate"),
        # v5.13.2 — 자본 대비 수익률과 '거래별 수익률의 단순 합'은 전혀 다른 값이다.
        #   한 이름(총수익률)으로 섞여 32.71% vs 65.36% 처럼 보이던 혼선을 분리한다.
        ("자본대비 수익률", _percent(_pick(m, s, "return_on_capital_pct"), signed=True), "return_on_capital_pct"),
        ("거래수익률 합(참고)", _percent(_pick(m, s, "sum_trade_return_pct", "total_profit_pct", "return_pct"), signed=True), "sum_trade_return_pct"),
        ("총수익금", _number_with_unit(_pick(m, s, "total_profit_krw", "profit"), "원"), "total_profit_krw"),
        ("MDD", _percent(_pick(m, s, "mdd_pct", "max_drawdown_pct")), "mdd_pct"),
        ("연평균 수익률", _percent(_pick(m, s, "annual_return_pct", "cagr", "cagr_pct"), signed=True), "annual_return_pct"),
        ("보유시간(중앙)", _hold(_pick(m, s, "median_hold_sec")), "median_hold_sec"),
        ("일평균 거래", _number_with_unit(_pick(m, s, "daily_avg_trades", "avg_trades_per_day"), "회", 2), "daily_avg_trades"),
        ("하루 최대 보유", _number_with_unit(_pick(m, s, "max_hold_count", "max_holdings", "max_concurrent_positions"), "종목"), "max_hold_count"),
        ("payoff", _number(_pick(m, s, "payoff_ratio"), 2), "payoff_ratio"),
        ("profit factor", _number(_pick(m, s, "profit_factor"), 2), "profit_factor"),
    ]
    cards = "".join(
        f'<div class="card"><div class="card-label">{_escape(label)}</div><div class="card-value">{_escape(value)}</div></div>'
        for label, value, _ in rows
    )
    table_rows = "".join(
        f"<tr><th>{_escape(label)}</th><td>{_escape(value)}</td><td><code>{_escape(key)}</code></td></tr>"
        for label, value, key in rows
    )
    annual = _pick(m, s, "annual_return_pct", "cagr", "cagr_pct")
    total_return = _pick(m, s, "total_profit_pct", "return_pct")
    mdd = _pick(m, s, "mdd_pct", "max_drawdown_pct")
    bars = "".join((
        _bar("연평균 수익률", annual, "#4cd6b3"),
        _bar("총수익률", total_return, "#a78bfa"),
        _bar("MDD", mdd, "#ff6b6b"),
    )) or '<p class="empty">시각화 가능한 운영 성과 지표 미발행</p>'
    return (
        '<section class="section"><h2>결과 Summary</h2>'
        f'<div class="cards">{cards}</div>'
        f'<div style="margin:14px 0;padding:12px;border:1px solid #272d36;border-radius:8px;background:#0e1117">{bars}</div>'
        '<table class="tbl"><thead><tr><th>지표</th><th>값</th><th>원천 필드</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></section>"
    )
