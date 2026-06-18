"""Backtest workbench self-contained HTML report — render_report (PR-Phase2 B1).

승자 리포트: 단일 HTML 문자열(외부 리소스 0 — 인라인 CSS·인라인 SVG)을 만든다.
브라우저가 fetch 없이 그대로 인쇄/저장할 수 있는 자급자족 리포트다. React 불가
(서버측 순수 문자열 조립)이므로 SVG 도 단순 직선/사각형 수준으로 직접 생성한다.

입력 payload(backtest_analysis.full_analysis + 메타) 구조:
  {
    "meta": {"title", "buy", "sell", "period", "generated_at", "source",
             "trade_count", "status", "note"?},
    "metrics": {... CLI 또는 summary 메트릭 ...} | None,
    "analysis": full_analysis() 반환 묶음 | None,
    "montecarlo": monte_carlo() 반환 | None,
  }

설계 계약(무예외):
  - 모든 헬퍼는 빈/이상 입력에도 raise 하지 않고 빈 섹션/플레이스홀더를 낸다.
  - 외부 URL(http/https///cdn) 을 절대 포함하지 않는다(자급자족 보장 — 테스트가 검증).
  - HTML escape 로 사용자 문자열(전략명 등)을 안전하게 끼운다(XSS/깨짐 방지).
  - 다크 테마, 한국어 라벨, 인쇄 친화(@media print).
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List, Optional

# SVG 캔버스 기본 치수(뷰박스 좌표계 — 반응형 width:100%).
_SVG_W = 720
_SVG_H = 240
_PAD = 40

# 다크 테마 팔레트(인라인 CSS 변수 대신 직접 색 — 자급자족·인쇄 안정).
_C_BG = "#0e1117"
_C_PANEL = "#161b22"
_C_LINE = "#272d36"
_C_INK0 = "#e6edf3"
_C_INK1 = "#aeb6bf"
_C_INK2 = "#7d8590"
_C_TEAL = "#4cd6b3"
_C_AMBER = "#f0b35a"
_C_RED = "#ff6b6b"
_C_VIOLET = "#a78bfa"
_C_GREEN = "#3fb950"

# 인사이트 severity → 색.
_SEV_COLOR = {"info": _C_TEAL, "warning": _C_AMBER, "critical": _C_RED}
_SEV_LABEL = {"info": "정보", "warning": "주의", "critical": "위험"}

# 요일 한글(0=월).
_WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


# --------------------------------------------------------------------- format
def _esc(value: Any) -> str:
    """HTML escape(사용자 문자열 안전 삽입). None/숫자도 문자열화."""
    return html.escape(str(value if value is not None else ""))


def _num(value: Any, digits: int = 0) -> str:
    """천단위 콤마 + 소수 자릿수. 비숫자/None 이면 '—'."""
    try:
        if value is None:
            return "—"
        f = float(value)
    except (TypeError, ValueError):
        return "—"
    if digits <= 0:
        return f"{f:,.0f}"
    return f"{f:,.{digits}f}"


def _pct(value: Any, digits: int = 2) -> str:
    """퍼센트 표기(+부호). 비숫자/None 이면 '—'."""
    try:
        if value is None:
            return "—"
        return f"{float(value):+.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _get(d: Optional[Dict[str, Any]], *keys: str, default: Any = None) -> Any:
    """중첩 dict 안전 접근. 중간이 dict 아니거나 키 없으면 default."""
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur


# ----------------------------------------------------------------- SVG prims
def _svg_open(width: int = _SVG_W, height: int = _SVG_H) -> str:
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="width:100%;height:auto;display:block;background:{_C_BG}">'
    )


def _svg_axes(width: int, height: int, zero_y: Optional[float] = None) -> str:
    """플롯 영역 테두리 + (선택) 0 기준선."""
    parts = [
        f'<rect x="{_PAD}" y="10" width="{width - 2 * _PAD}" height="{height - 40}" '
        f'fill="none" stroke="{_C_LINE}" stroke-width="1"/>'
    ]
    if zero_y is not None:
        parts.append(
            f'<line x1="{_PAD}" y1="{zero_y:.1f}" x2="{width - _PAD}" y2="{zero_y:.1f}" '
            f'stroke="{_C_INK2}" stroke-width="1" stroke-dasharray="3 3"/>'
        )
    return "".join(parts)


def _scale(values: List[float], lo_pad: bool = True) -> tuple[float, float]:
    """값 리스트의 (min,max) 범위. 동일값/빈값이면 보호 폭을 둔다."""
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    if lo_pad and lo > 0.0:
        lo = 0.0
    if hi <= lo:
        hi = lo + 1.0
    return lo, hi


def _empty_chart(label: str) -> str:
    """데이터 없음 플레이스홀더 SVG."""
    return (
        f'{_svg_open(_SVG_W, 80)}'
        f'<text x="{_SVG_W / 2:.0f}" y="46" fill="{_C_INK2}" font-size="13" '
        f'text-anchor="middle" font-family="monospace">{_esc(label)}</text></svg>'
    )


# --------------------------------------------------------------- chart blocks
def _equity_svg(equity: Optional[Dict[str, Any]]) -> str:
    """누적수익곡선(선) + 일별손익(막대) 결합 SVG."""
    cumulative = _get(equity, "cumulative", default=[]) or []
    daily = _get(equity, "daily", default=[]) or []
    if not cumulative:
        return _empty_chart("수익곡선 데이터 없음")

    w, h = _SVG_W, _SVG_H
    plot_w = w - 2 * _PAD
    plot_h = h - 40
    cum_vals = [float(p.get("cum_profit", 0.0) or 0.0) for p in cumulative]
    lo, hi = _scale(cum_vals, lo_pad=False)
    span = hi - lo if hi > lo else 1.0
    n = len(cum_vals)

    def _x(i: int) -> float:
        return _PAD + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)

    def _y(v: float) -> float:
        return 10 + plot_h * (1.0 - (v - lo) / span)

    zero_y = _y(0.0) if lo <= 0.0 <= hi else None

    # 일별손익 막대(중심 0 기준, daily 점 수에 맞춰 폭 산출).
    bars: List[str] = []
    if daily:
        d_vals = [float(p.get("pnl", 0.0) or 0.0) for p in daily]
        dmax = max((abs(v) for v in d_vals), default=1.0) or 1.0
        bw = max(1.0, plot_w / max(1, len(daily)) * 0.7)
        base_y = _y(0.0) if zero_y is not None else (10 + plot_h)
        for i, v in enumerate(d_vals):
            bx = _PAD + (plot_w * (i / (len(daily) - 1)) if len(daily) > 1 else plot_w / 2)
            bh = abs(v) / dmax * (plot_h * 0.28)
            by = base_y - bh if v >= 0.0 else base_y
            col = _C_GREEN if v >= 0.0 else _C_RED
            bars.append(
                f'<rect x="{bx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
                f'height="{bh:.1f}" fill="{col}" opacity="0.35"/>'
            )

    pts = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(cum_vals))
    line = (
        f'<polyline points="{pts}" fill="none" stroke="{_C_TEAL}" '
        f'stroke-width="2" stroke-linejoin="round"/>'
    )
    # y 라벨(상/하한).
    labels = (
        f'<text x="4" y="18" fill="{_C_INK2}" font-size="10" font-family="monospace">{_num(hi)}</text>'
        f'<text x="4" y="{10 + plot_h:.0f}" fill="{_C_INK2}" font-size="10" font-family="monospace">{_num(lo)}</text>'
    )
    return (
        f'{_svg_open(w, h)}{_svg_axes(w, h, zero_y)}'
        f'{"".join(bars)}{line}{labels}</svg>'
    )


def _underwater_svg(underwater: Optional[Dict[str, Any]]) -> str:
    """언더워터(고점 대비 반납액) 영역 SVG."""
    series = _get(underwater, "series", default=[]) or []
    if not series:
        return _empty_chart("언더워터 데이터 없음")
    w, h = _SVG_W, 180
    plot_w = w - 2 * _PAD
    plot_h = h - 40
    vals = [float(p.get("drawdown", 0.0) or 0.0) for p in series]
    hi = max(vals) if vals else 1.0
    hi = hi if hi > 0.0 else 1.0
    n = len(vals)

    def _x(i: int) -> float:
        return _PAD + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)

    def _y(v: float) -> float:
        # drawdown 은 0(상단)에서 hi(하단)로 — 아래로 채운다.
        return 10 + plot_h * (v / hi)

    pts = [f"{_PAD:.1f},10"]
    pts += [f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(vals)]
    pts.append(f"{_x(n - 1):.1f},10")
    area = (
        f'<polygon points="{" ".join(pts)}" fill="{_C_RED}" fill-opacity="0.22" '
        f'stroke="{_C_RED}" stroke-width="1.5"/>'
    )
    label = (
        f'<text x="4" y="{10 + plot_h:.0f}" fill="{_C_INK2}" font-size="10" '
        f'font-family="monospace">-{_num(hi)}</text>'
    )
    return f'{_svg_open(w, h)}{_svg_axes(w, h)}{area}{label}</svg>'


def _histogram_svg(distribution: Optional[Dict[str, Any]]) -> str:
    """손익(%) 히스토그램 막대 SVG."""
    hist = _get(distribution, "pnl_histogram", default=[]) or []
    if not hist:
        return _empty_chart("손익 분포 데이터 없음")
    w, h = _SVG_W, 180
    plot_w = w - 2 * _PAD
    plot_h = h - 40
    counts = [int(b.get("count", 0) or 0) for b in hist]
    cmax = max(counts) if counts else 1
    cmax = cmax if cmax > 0 else 1
    m = len(hist)
    bw = plot_w / m
    bars: List[str] = []
    for i, b in enumerate(hist):
        c = int(b.get("count", 0) or 0)
        bh = (c / cmax) * plot_h
        bx = _PAD + i * bw
        by = 10 + plot_h - bh
        mid = (float(b.get("bin_start", 0.0)) + float(b.get("bin_end", 0.0))) / 2.0
        col = _C_GREEN if mid >= 0.0 else _C_RED
        bars.append(
            f'<rect x="{bx + 1:.1f}" y="{by:.1f}" width="{max(1.0, bw - 2):.1f}" '
            f'height="{bh:.1f}" fill="{col}" opacity="0.55"/>'
        )
    return f'{_svg_open(w, h)}{_svg_axes(w, h)}{"".join(bars)}</svg>'


def _scatter_svg(points: Optional[List[Dict[str, Any]]]) -> str:
    """MAE/MFE 산점도 SVG(x=MAE, y=MFE, 색=손익부호)."""
    pts = points or []
    if not pts:
        return _empty_chart("MAE/MFE 데이터 없음")
    w, h = _SVG_W, 240
    plot_w = w - 2 * _PAD
    plot_h = h - 40
    xs = [float(p.get("mae", 0.0) or 0.0) for p in pts]
    ys = [float(p.get("mfe", 0.0) or 0.0) for p in pts]
    xlo, xhi = _scale(xs, lo_pad=False)
    ylo, yhi = _scale(ys, lo_pad=False)
    xspan = xhi - xlo if xhi > xlo else 1.0
    yspan = yhi - ylo if yhi > ylo else 1.0

    def _px(v: float) -> float:
        return _PAD + plot_w * ((v - xlo) / xspan)

    def _py(v: float) -> float:
        return 10 + plot_h * (1.0 - (v - ylo) / yspan)

    dots: List[str] = []
    for p in pts:
        col = _C_GREEN if float(p.get("pnl_pct", 0.0) or 0.0) >= 0.0 else _C_RED
        dots.append(
            f'<circle cx="{_px(float(p.get("mae", 0.0) or 0.0)):.1f}" '
            f'cy="{_py(float(p.get("mfe", 0.0) or 0.0)):.1f}" r="2.2" '
            f'fill="{col}" fill-opacity="0.5"/>'
        )
    labels = (
        f'<text x="{_PAD}" y="{h - 6}" fill="{_C_INK2}" font-size="10" font-family="monospace">MAE →</text>'
        f'<text x="6" y="20" fill="{_C_INK2}" font-size="10" font-family="monospace">MFE ↑</text>'
    )
    return f'{_svg_open(w, h)}{_svg_axes(w, h)}{"".join(dots)}{labels}</svg>'


def _heatmap_svg(heatmap: Optional[Dict[str, Any]]) -> str:
    """요일×30분 슬롯 손익 히트맵 SVG(셀 색=손익부호·강도)."""
    cells = _get(heatmap, "cells", default=[]) or []
    if not cells:
        return _empty_chart("히트맵 데이터 없음")
    # 슬롯 범위(장중) 산출.
    slots = sorted({int(c.get("slot") or 0) for c in cells})
    if not slots:
        return _empty_chart("히트맵 데이터 없음")
    slot_lo, slot_hi = slots[0], slots[-1]
    n_slot = max(1, slot_hi - slot_lo + 1)
    cell_w = max(8.0, min(28.0, (_SVG_W - 2 * _PAD) / n_slot))
    cell_h = 22.0
    w = int(_PAD + n_slot * cell_w + 20)
    h = int(30 + 7 * cell_h + 20)
    pmax = max((abs(float(c.get("profit_krw", 0.0) or 0.0)) for c in cells), default=1.0) or 1.0

    rects: List[str] = []
    for c in cells:
        wd = int(c.get("weekday") or 0)
        sl = int(c.get("slot") or 0)
        if not (0 <= wd < 7):
            continue
        prof = float(c.get("profit_krw", 0.0) or 0.0)
        inten = min(1.0, abs(prof) / pmax)
        base = _C_GREEN if prof >= 0.0 else _C_RED
        x = _PAD + (sl - slot_lo) * cell_w
        y = 30 + wd * cell_h
        rects.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_w - 1:.1f}" height="{cell_h - 1:.1f}" '
            f'fill="{base}" fill-opacity="{0.12 + 0.78 * inten:.2f}"/>'
        )
    # 요일 라벨.
    ylabels = "".join(
        f'<text x="6" y="{30 + i * cell_h + 15:.0f}" fill="{_C_INK1}" font-size="11" '
        f'font-family="monospace">{_WEEKDAY_KO[i]}</text>'
        for i in range(7)
    )
    # 시간 라벨(시작/끝 슬롯).
    xlabels = (
        f'<text x="{_PAD}" y="24" fill="{_C_INK2}" font-size="10" font-family="monospace">'
        f'{_slot_label(slot_lo)}</text>'
        f'<text x="{_PAD + (n_slot - 1) * cell_w:.0f}" y="24" fill="{_C_INK2}" font-size="10" '
        f'font-family="monospace" text-anchor="end">{_slot_label(slot_hi)}</text>'
    )
    return f'{_svg_open(w, h)}{"".join(rects)}{ylabels}{xlabels}</svg>'


def _slot_label(slot: int) -> str:
    minutes = slot * 30
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# --------------------------------------------------------------- table blocks
def _metric_cards(metrics: Optional[Dict[str, Any]], summary: Optional[Dict[str, Any]]) -> str:
    """핵심 메트릭 카드 그리드. CLI metrics 우선, 없으면 summary 로 폴백.

    CLI metrics 키(trade_count/win_rate/total_profit_pct/total_profit_krw/mdd_pct/cagr/...)와
    summary 키(payoff_ratio/profit_factor/...)를 합쳐 카드를 만든다(없으면 '—').
    """
    m = metrics or {}
    s = summary or {}

    def pick(*keys: str) -> Any:
        for k in keys:
            if k in m and m[k] is not None:
                return m[k]
            if k in s and s[k] is not None:
                return s[k]
        return None

    cards = [
        ("거래수", _num(pick("trade_count"))),
        ("승률", _pct_plain(pick("win_rate"))),
        ("총수익률", _pct(pick("total_profit_pct"))),
        ("총수익금", _num(pick("total_profit_krw")) + "원"),
        ("MDD", _pct_plain(pick("mdd_pct", "max_drawdown_pct"))),
        ("CAGR", _pct(pick("cagr")) if pick("cagr") is not None else "—"),
        ("payoff", _num(pick("payoff_ratio"), 2)),
        ("profit factor", _num(pick("profit_factor"), 2)),
    ]
    items = "".join(
        f'<div class="card"><div class="card-label">{_esc(lbl)}</div>'
        f'<div class="card-value">{_esc(val)}</div></div>'
        for lbl, val in cards
    )
    return f'<div class="cards">{items}</div>'


def _pct_plain(value: Any, digits: int = 2) -> str:
    """부호 없는 퍼센트(승률·MDD 용)."""
    try:
        if value is None:
            return "—"
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _montecarlo_block(mc: Optional[Dict[str, Any]]) -> str:
    """몬테카를로 요약 표(p5/p50/p95·파산확률)."""
    if not mc or not mc.get("n"):
        return _section("몬테카를로", '<p class="empty">몬테카를로 데이터 없음</p>')
    mdd = mc.get("mdd_krw", {}) or {}
    final = mc.get("final", {}) or {}
    ruin = float(mc.get("ruin_prob", 0.0) or 0.0)
    obs = mc.get("observed") or {}
    rows = [
        ("최종손익(원)", final.get("p5"), final.get("p50"), final.get("p95")),
        ("최대낙폭(원)", mdd.get("p5"), mdd.get("p50"), mdd.get("p95")),
    ]
    body = "".join(
        f"<tr><td>{_esc(lbl)}</td><td>{_num(p5)}</td><td>{_num(p50)}</td><td>{_num(p95)}</td></tr>"
        for lbl, p5, p50, p95 in rows
    )
    table = (
        '<table class="tbl"><thead><tr><th>지표</th><th>p5</th><th>p50</th><th>p95</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )
    meta = (
        f'<p class="mc-meta">시행 {_num(mc.get("n"))}회 · 거래일 {_num(mc.get("days"))}일 · '
        f'파산확률 <b style="color:{_C_RED if ruin >= 0.05 else _C_INK1}">{ruin * 100:.1f}%</b>'
        f'(자본 대비 -{_num(mc.get("ruin_pct"))}% 도달) · '
        f'실측 MDD {_num(_get(obs, "mdd_krw"))}원</p>'
    )
    return _section("몬테카를로 시뮬레이션", table + meta)


def _orderflow_block(orderflow: Optional[Dict[str, Any]]) -> str:
    """오더플로우 승/패 진입 분포 비교 표(separation 순위)."""
    sep = _get(orderflow, "separation", default=[]) or []
    if not sep:
        return _section("오더플로우 승패 비교", '<p class="empty">오더플로우 데이터 없음</p>')
    body = "".join(
        f"<tr><td>{_esc(r.get('label'))}</td><td>{_num(r.get('win_p50'), 2)}</td>"
        f"<td>{_num(r.get('loss_p50'), 2)}</td>"
        f'<td style="color:{_C_TEAL if float(r.get("diff", 0.0) or 0.0) > 0 else _C_AMBER}">'
        f"{_num(r.get('diff'), 2)}</td></tr>"
        for r in sep
    )
    table = (
        '<table class="tbl"><thead><tr><th>변수</th><th>승 중앙값</th><th>패 중앙값</th>'
        "<th>차이</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    return _section("오더플로우 승패 비교(진입 분포)", table)


def _exit_reason_block(exit_reasons: Optional[List[Dict[str, Any]]]) -> str:
    """매도조건(청산사유)별 거래수/총손익/승률 분해 표."""
    rows = exit_reasons or []
    if not rows:
        return _section("매도조건 분해", '<p class="empty">매도조건 데이터 없음</p>')
    body = "".join(
        f"<tr><td>{_esc(r.get('reason'))}</td><td>{_num(r.get('count'))}</td>"
        f'<td style="color:{_C_GREEN if float(r.get("total_pnl", 0.0) or 0.0) >= 0 else _C_RED}">'
        f"{_num(r.get('total_pnl'))}원</td><td>{_pct_plain(r.get('win_rate'))}</td></tr>"
        for r in rows
    )
    table = (
        '<table class="tbl"><thead><tr><th>매도조건</th><th>거래수</th><th>총손익</th>'
        "<th>승률</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    return _section("매도조건 분해", table)


def _insights_block(insights: Optional[List[Dict[str, Any]]]) -> str:
    """규칙 기반 인사이트 목록(severity 색)."""
    rows = insights or []
    if not rows:
        return _section("인사이트", '<p class="empty">인사이트 없음</p>')
    items = "".join(
        f'<li class="insight" style="border-left-color:{_SEV_COLOR.get(r.get("severity"), _C_INK2)}">'
        f'<span class="sev" style="color:{_SEV_COLOR.get(r.get("severity"), _C_INK2)}">'
        f'[{_esc(_SEV_LABEL.get(r.get("severity"), "정보"))}]</span> '
        f'<b>{_esc(r.get("title"))}</b><br><span class="detail">{_esc(r.get("detail"))}</span></li>'
        for r in rows
    )
    return _section("인사이트", f'<ul class="insights">{items}</ul>')


def _stats_block(stats: Optional[List[Dict[str, Any]]]) -> str:
    """통계검정 표(요일/시간대 버킷 평균 수익률 유의성)."""
    rows = stats or []
    if not rows:
        return _section("통계 검정", '<p class="empty">통계 검정 데이터 없음</p>')
    # 유의 + 표본 충분한 행을 위로, 나머지는 표본수 큰 순.
    ordered = sorted(rows, key=lambda r: (not r.get("significant"), -int(r.get("n", 0) or 0)))
    body = "".join(
        f'<tr><td>{_esc("요일" if r.get("kind") == "weekday" else "시간대")}</td>'
        f"<td>{_esc(r.get('label'))}</td><td>{_num(r.get('n'))}</td>"
        f"<td>{_pct(r.get('mean'))}</td>"
        f"<td>{_num(r.get('p_value'), 4) if r.get('p_value') is not None else '—'}</td>"
        f'<td style="color:{_C_TEAL if r.get("significant") else _C_INK2}">'
        f'{"유의" if r.get("significant") else ("표본부족" if r.get("underpowered") else "무의미")}</td></tr>'
        for r in ordered
    )
    table = (
        '<table class="tbl"><thead><tr><th>종류</th><th>버킷</th><th>n</th><th>평균</th>'
        "<th>p값</th><th>판정</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    return _section("통계 검정(요일·시간대 효과)", table)


def _section(title: str, inner: str) -> str:
    return (
        f'<section class="sec"><h2>{_esc(title)}</h2><div class="sec-bd">{inner}</div></section>'
    )


# --------------------------------------------------------------------- styles
def _styles() -> str:
    """인라인 CSS(외부 폰트/리소스 0 — 시스템 폰트 스택만)."""
    return (
        "*{box-sizing:border-box;margin:0;padding:0}"
        f"body{{background:{_C_BG};color:{_C_INK0};"
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',sans-serif;"
        "line-height:1.5;padding:24px;max-width:880px;margin:0 auto}"
        f"header.rpt-hd{{border-bottom:2px solid {_C_TEAL};padding-bottom:14px;margin-bottom:20px}}"
        f"header.rpt-hd h1{{font-size:22px;color:{_C_INK0};margin-bottom:6px}}"
        f"header.rpt-hd .meta{{font-size:12px;color:{_C_INK2};font-family:monospace;line-height:1.7}}"
        f".note{{background:{_C_PANEL};border:1px solid {_C_AMBER};border-radius:6px;"
        f"padding:10px 12px;margin-bottom:16px;color:{_C_AMBER};font-size:12.5px}}"
        ".cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:8px}"
        f".card{{background:{_C_PANEL};border:1px solid {_C_LINE};border-radius:8px;padding:12px}}"
        f".card-label{{font-size:11px;color:{_C_INK2};font-family:monospace;margin-bottom:4px}}"
        f".card-value{{font-size:18px;color:{_C_INK0};font-weight:600}}"
        "section.sec{margin-top:22px}"
        f"section.sec h2{{font-size:14px;color:{_C_TEAL};margin-bottom:10px;"
        f"border-bottom:1px solid {_C_LINE};padding-bottom:5px;font-family:monospace}}"
        f".sec-bd{{background:{_C_PANEL};border:1px solid {_C_LINE};border-radius:8px;padding:14px}}"
        "table.tbl{width:100%;border-collapse:collapse;font-size:12.5px}"
        f"table.tbl th{{text-align:left;color:{_C_INK2};font-family:monospace;font-weight:500;"
        f"padding:6px 8px;border-bottom:1px solid {_C_LINE}}}"
        f"table.tbl td{{padding:6px 8px;border-bottom:1px solid {_C_LINE};color:{_C_INK1};"
        "font-family:monospace}"
        "table.tbl tr:last-child td{border-bottom:0}"
        f".empty{{color:{_C_INK2};font-size:12.5px;font-family:monospace;padding:8px 0}}"
        f".mc-meta{{margin-top:10px;font-size:12px;color:{_C_INK1};font-family:monospace}}"
        ".insights{list-style:none}"
        f".insight{{border-left:3px solid {_C_INK2};padding:8px 12px;margin-bottom:8px;"
        f"background:{_C_BG};border-radius:0 5px 5px 0;font-size:12.5px}}"
        ".insight .sev{font-family:monospace;font-size:11px}"
        f".insight .detail{{color:{_C_INK1};font-size:12px}}"
        f"footer.rpt-ft{{margin-top:28px;padding-top:12px;border-top:1px solid {_C_LINE};"
        f"font-size:11px;color:{_C_INK2};font-family:monospace;text-align:center}}"
        "@media print{"
        "body{background:#fff;color:#111;padding:0}"
        ".card,.sec-bd,.insight{background:#f7f7f7 !important}"
        "section.sec h2{color:#0a7}"
        "svg{background:#fff !important}"
        "}"
    )


# --------------------------------------------------------------------- header
def _header(meta: Dict[str, Any]) -> str:
    title = meta.get("title") or "백테스트 리포트"
    buy = meta.get("buy") or "—"
    sell = meta.get("sell") or "—"
    period = meta.get("period") or "—"
    gen_at = meta.get("generated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = meta.get("source") or ""
    trade_count = meta.get("trade_count")
    lines = [
        f"매수: {_esc(buy)} · 매도: {_esc(sell)}",
        f"기간: {_esc(period)}",
        f"거래수: {_esc(_num(trade_count))} · 생성: {_esc(gen_at)}",
    ]
    if source:
        lines.append(f"출처: {_esc(source)}")
    meta_html = "<br>".join(lines)
    return (
        f'<header class="rpt-hd"><h1>{_esc(title)}</h1>'
        f'<div class="meta">{meta_html}</div></header>'
    )


# --------------------------------------------------------------- entry point
def render_report(payload: Dict[str, Any]) -> str:
    """리포트 payload → 자급자족 단일 HTML 문자열(외부 리소스 0, 무예외).

    payload 가 비거나 분석/메트릭이 None 이어도 축약 리포트(헤더 + note + 가능한
    섹션)를 낸다. 어떤 키 누락에도 raise 하지 않는다(섹션이 빈 플레이스홀더가 됨).
    """
    payload = payload if isinstance(payload, dict) else {}
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else None
    mc = payload.get("montecarlo") if isinstance(payload.get("montecarlo"), dict) else None

    summary = _get(analysis, "summary", default={}) or {}
    note = meta.get("note")
    note_html = f'<div class="note">{_esc(note)}</div>' if note else ""

    body_parts = [
        _header(meta),
        note_html,
        _metric_cards(metrics, summary),
        _section("수익곡선 · 일별손익", _equity_svg(_get(analysis, "equity"))),
        _section("언더워터(고점 대비 반납)", _underwater_svg(_get(analysis, "underwater"))),
        _section("손익 분포", _histogram_svg(_get(analysis, "distribution"))),
        _section("요일 × 시간 히트맵", _heatmap_svg(_get(analysis, "heatmap"))),
        _section("MAE / MFE 산점도", _scatter_svg(_get(analysis, "mae_mfe"))),
        _montecarlo_block(mc),
        _orderflow_block(_get(analysis, "orderflow")),
        _exit_reason_block(_get(analysis, "exit_reasons")),
        _insights_block(_get(analysis, "insights")),
        _stats_block(_get(analysis, "stats")),
        '<footer class="rpt-ft">STOM 백테스트 워크벤치 · 자급자족 리포트(외부 리소스 없음)</footer>',
    ]
    body = "".join(body_parts)
    return (
        "<!DOCTYPE html>"
        '<html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{_esc(meta.get('title') or '백테스트 리포트')}</title>"
        f"<style>{_styles()}</style></head>"
        f"<body>{body}</body></html>"
    )
