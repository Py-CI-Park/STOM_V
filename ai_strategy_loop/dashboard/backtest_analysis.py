"""Backtest workbench analysis — per-trade CSV → 분석 묶음 순수함수 (PR2).

이 모듈은 per-trade 백테 결과 CSV(또는 그에서 파싱한 DataFrame)를 입력받아
대시보드 워크벤치가 소비하는 분석 구조(요약 메트릭·자본곡선·분포·히트맵·언더워터·
규칙 기반 인사이트)를 만든다.

설계 계약(무예외):
  - 모든 함수는 빈/이상 입력에도 절대 raise 하지 않고 빈 구조를 돌려준다. 백테가
    no_trades 거나 CSV 컬럼이 누락돼도 대시보드가 깨지지 않게 한다(기존 컨벤션).
  - 순수함수: 입력 DataFrame(+선택 metrics dict)만 보고 결과를 만든다. I/O 없음
    (CSV 로딩은 load_trades_csv 한 곳에 격리). 단위테스트가 합성 DF로 전부 커버한다.
  - 시계열은 다운샘플 상한(max 500pt)을 둔다(브라우저 렌더 부하 방지).

per-trade CSV 컬럼(backtest/back_static.py 결과 헤더, utf-8-sig):
  종목명, 시가총액, 매수시간, 매도시간(YYYYMMDDHHMM), 보유시간(분), 매수가, 매도가,
  매수금액, 매도금액, 수익률(%), 수익금(원), 수익금합계, 매도조건, ...
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 컬럼 상수 (holdout/equity_series 와 동일 헤더 계열).
# ---------------------------------------------------------------------------
COL_NAME = "종목명"
COL_BUY_TIME = "매수시간"
COL_SELL_TIME = "매도시간"
COL_HOLD_MIN = "보유시간"
COL_PROFIT_PCT = "수익률"
COL_PROFIT_KRW = "수익금"
# MAE/MFE·청산사유(D) — per-trade CSV 에 이미 존재(틱 DB 재조회 없이 CSV 만으로).
COL_MFE = "R_MFE"
COL_MAE = "R_MAE"
COL_EXIT_REASON = "매도조건"

_DOWNSAMPLE_MAX = 500
_HIST_BINS = 20
_TOP_N = 10
# MAE/MFE 산점도 최대 표본(브라우저 렌더 부하 방지).
_SCATTER_MAX = 1000

# 한국 거래일 기준 연율화 상수(252 거래일/년).
_TRADING_DAYS_PER_YEAR = 252.0


# ---------------------------------------------------------------------------
# Trade row container — DataFrame 의존 없이 dict 리스트로 다룬다(경량·테스트 용이).
# ---------------------------------------------------------------------------
def load_trades_csv(csv_path: Optional[str]) -> List[Dict[str, Any]]:
    """per-trade 결과 CSV를 정규화된 trade dict 리스트로 읽는다(무예외).

    각 trade dict: {name, buy_time(str), sell_time(str), day(int YYYYMMDD),
                    hold_min(float), profit_pct(float), profit_krw(float)}.
    파싱 불가/빈 행은 건너뛴다. CSV 없음/컬럼 누락/IO 실패는 [] 로 흡수한다.
    """
    if not csv_path:
        return []
    trades: List[Dict[str, Any]] = []
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            if COL_SELL_TIME not in fields or COL_PROFIT_KRW not in fields:
                return []
            for row in reader:
                trade = _normalize_row(row)
                if trade is not None:
                    trades.append(trade)
    except Exception:  # noqa: BLE001 - CSV 없음/IO/파싱 실패는 빈 리스트로 흡수.
        return []
    return trades


def _normalize_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """CSV 한 행을 정규화된 trade dict 로 변환한다. 필수 필드 누락이면 None."""
    raw_sell = str(row.get(COL_SELL_TIME, "") or "").strip()
    raw_profit = row.get(COL_PROFIT_KRW, "")
    if len(raw_sell) < 8 or raw_profit is None or str(raw_profit).strip() == "":
        return None
    try:
        day = int(raw_sell[:8])
        profit_krw = float(raw_profit)
    except (ValueError, TypeError):
        return None
    return {
        "name": str(row.get(COL_NAME, "") or "").strip(),
        "buy_time": str(row.get(COL_BUY_TIME, "") or "").strip(),
        "sell_time": raw_sell,
        "day": day,
        "hold_min": _safe_float(row.get(COL_HOLD_MIN)),
        "profit_pct": _safe_float(row.get(COL_PROFIT_PCT)),
        "profit_krw": profit_krw,
        # MAE/MFE·청산사유(D) — 결측이면 None/빈문자(소비측이 결측 행 제외).
        "mfe": _opt_float(row.get(COL_MFE)),
        "mae": _opt_float(row.get(COL_MAE)),
        "exit_reason": str(row.get(COL_EXIT_REASON, "") or "").strip(),
    }


def _safe_float(value: Any) -> float:
    try:
        if value is None or str(value).strip() == "":
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _opt_float(value: Any) -> Optional[float]:
    """결측(빈/파싱불가)이면 None, 아니면 float. MAE/MFE 결측 행 제외에 쓴다."""
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def filter_trades(
    trades: List[Dict[str, Any]],
    t_start: Optional[int] = None,
    t_end: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """매수시간(YYYYMMDDHHMMSS) 범위로 trade 리스트를 거른다(순수함수·무예외).

    t_start/t_end 는 매수시간을 정수로 본 포함 경계다(둘 중 하나만 줘도 됨).
    경계가 None 이면 그쪽은 무제한. 매수시간이 정수로 파싱되지 않는 행은 제외한다.
    빈 결과여도 raise 하지 않고 [] 를 돌린다(브러시 구간이 비면 그대로 빈 분석).
    """
    if t_start is None and t_end is None:
        return list(trades)
    lo = t_start if t_start is not None else None
    hi = t_end if t_end is not None else None
    out: List[Dict[str, Any]] = []
    for t in trades:
        buy = str(t.get("buy_time", "") or "").strip()
        if not buy.isdigit():
            continue
        bt = int(buy)
        if lo is not None and bt < lo:
            continue
        if hi is not None and bt > hi:
            continue
        out.append(t)
    return out


def _downsample(series: List[Any], limit: int = _DOWNSAMPLE_MAX) -> List[Any]:
    """길이 n 시퀀스를 limit 점으로 균등 추림한다(마지막 보존). n<=limit 이면 원본."""
    n = len(series)
    if n <= limit or limit <= 0:
        return list(series)
    picks = sorted({round(k * (n - 1) / (limit - 1)) for k in range(limit)} | {n - 1})
    return [series[i] for i in picks]


def _empty_summary() -> Dict[str, Any]:
    return {
        "trade_count": 0,
        "win_count": 0,
        "loss_count": 0,
        "win_rate": 0.0,
        "total_profit_krw": 0.0,
        "total_profit_pct": 0.0,
        "avg_profit_pct": 0.0,
        "avg_win_krw": 0.0,
        "avg_loss_krw": 0.0,
        "payoff_ratio": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_krw": 0.0,
        "max_drawdown_pct": 0.0,
        "max_consecutive_wins": 0,
        "max_consecutive_losses": 0,
        "avg_hold_min": 0.0,
        "median_hold_min": 0.0,
        "trading_days": 0,
        "avg_trades_per_day": 0.0,
        "sharpe": 0.0,
        "calmar": 0.0,
    }


# ---------------------------------------------------------------------------
# 1. summary_metrics — 핵심 요약 지표.
# ---------------------------------------------------------------------------
def summary_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """trade 리스트에서 요약 메트릭을 산출한다(빈 입력→0 구조, 무예외).

    payoff ratio = 평균이익 / |평균손실|, profit factor = 총이익 / |총손실|.
    MDD 는 거래순 누적 실현손익 곡선의 peak-to-trough(원/%) 기준.
    Sharpe/Calmar 는 거래일별 손익(원) 시계열 기준(연율화).
    """
    if not trades:
        return _empty_summary()

    profits_krw = [t["profit_krw"] for t in trades]
    profits_pct = [t["profit_pct"] for t in trades]
    holds = [t["hold_min"] for t in trades]

    wins = [p for p in profits_krw if p > 0.0]
    losses = [p for p in profits_krw if p < 0.0]
    trade_count = len(trades)
    win_count = len(wins)
    loss_count = len(losses)

    total_krw = sum(profits_krw)
    total_pct = sum(profits_pct)
    avg_pct = total_pct / trade_count if trade_count else 0.0
    avg_win = sum(wins) / win_count if win_count else 0.0
    avg_loss = sum(losses) / loss_count if loss_count else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    payoff = (avg_win / abs(avg_loss)) if avg_loss != 0.0 else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0.0 else 0.0

    dd_krw, dd_pct = _drawdown_from_profits(profits_krw)
    max_win_streak, max_loss_streak = _consecutive_streaks(profits_krw)

    days_map = _daily_pnl_map(trades)
    trading_days = len(days_map)
    avg_trades_per_day = trade_count / trading_days if trading_days else 0.0

    sharpe = _sharpe(list(days_map.values()))
    calmar = _calmar(total_krw, dd_krw, trading_days)

    return {
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_count / trade_count * 100.0, 4) if trade_count else 0.0,
        "total_profit_krw": float(total_krw),
        "total_profit_pct": float(total_pct),
        "avg_profit_pct": float(avg_pct),
        "avg_win_krw": float(avg_win),
        "avg_loss_krw": float(avg_loss),
        "payoff_ratio": float(payoff),
        "profit_factor": float(profit_factor),
        "max_drawdown_krw": float(dd_krw),
        "max_drawdown_pct": float(dd_pct),
        "max_consecutive_wins": int(max_win_streak),
        "max_consecutive_losses": int(max_loss_streak),
        "avg_hold_min": float(sum(holds) / trade_count) if trade_count else 0.0,
        "median_hold_min": float(_median(holds)),
        "trading_days": int(trading_days),
        "avg_trades_per_day": float(avg_trades_per_day),
        "sharpe": float(sharpe),
        "calmar": float(calmar),
    }


def _drawdown_from_profits(profits: List[float]) -> tuple[float, float]:
    """거래순 누적 실현손익 곡선의 최대낙폭(원, %)을 반환한다.

    %는 누적 peak 기준(peak>0 일 때만 정의). peak<=0 구간은 0%로 둔다(holdout과 동일 척도).
    """
    peak = float("-inf")
    running = 0.0
    max_dd_krw = 0.0
    max_dd_pct = 0.0
    for p in profits:
        running += p
        if running > peak:
            peak = running
        dd = peak - running
        if dd > max_dd_krw:
            max_dd_krw = dd
        if peak > 0.0:
            pct = dd / peak * 100.0
            if pct > max_dd_pct:
                max_dd_pct = pct
    return max(0.0, max_dd_krw), max(0.0, max_dd_pct)


def _consecutive_streaks(profits: List[float]) -> tuple[int, int]:
    """최대 연속 승/패 횟수(거래 순서 기준). 손익 0(브레이크이븐)은 연속을 끊는다."""
    max_win = max_loss = 0
    cur_win = cur_loss = 0
    for p in profits:
        if p > 0.0:
            cur_win += 1
            cur_loss = 0
        elif p < 0.0:
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = cur_loss = 0
        max_win = max(max_win, cur_win)
        max_loss = max(max_loss, cur_loss)
    return max_win, max_loss


def _daily_pnl_map(trades: List[Dict[str, Any]]) -> Dict[int, float]:
    """거래일(YYYYMMDD)→일별 실현손익(원) 매핑(정렬은 호출측)."""
    by_day: Dict[int, float] = {}
    for t in trades:
        by_day[t["day"]] = by_day.get(t["day"], 0.0) + t["profit_krw"]
    return dict(sorted(by_day.items()))


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _sharpe(daily_pnl: List[float]) -> float:
    """일별 손익(원) 시계열의 연율화 Sharpe(무위험수익률 0 가정).

    표본 표준편차가 0(변동 없음)이거나 표본<2면 0을 돌린다(정의 불가).
    """
    n = len(daily_pnl)
    if n < 2:
        return 0.0
    mean = sum(daily_pnl) / n
    var = sum((x - mean) ** 2 for x in daily_pnl) / (n - 1)
    std = math.sqrt(var)
    if std <= 0.0:
        return 0.0
    return (mean / std) * math.sqrt(_TRADING_DAYS_PER_YEAR)


def _calmar(total_krw: float, max_dd_krw: float, trading_days: int) -> float:
    """Calmar = 연율화 손익 / 최대낙폭(원). MDD 0 이거나 거래일 0이면 0."""
    if max_dd_krw <= 0.0 or trading_days <= 0:
        return 0.0
    annualized = total_krw / trading_days * _TRADING_DAYS_PER_YEAR
    return annualized / max_dd_krw


# ---------------------------------------------------------------------------
# 2. equity_series — 누적수익곡선 + 일별손익 + 드로다운 시계열.
# ---------------------------------------------------------------------------
def equity_series(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """거래일 축 누적수익곡선/일별손익/드로다운 시계열(다운샘플 max 500pt, 무예외)."""
    if not trades:
        return {"daily": [], "cumulative": [], "drawdown": []}

    days_map = _daily_pnl_map(trades)
    daily: List[Dict[str, Any]] = []
    cumulative: List[Dict[str, Any]] = []
    drawdown: List[Dict[str, Any]] = []

    running = 0.0
    peak = float("-inf")
    for day, pnl in days_map.items():
        running += pnl
        if running > peak:
            peak = running
        dd = max(0.0, peak - running)
        daily.append({"date": int(day), "pnl": float(pnl)})
        cumulative.append({"date": int(day), "cum_profit": float(running)})
        drawdown.append({"date": int(day), "drawdown": float(dd)})

    return {
        "daily": _downsample(daily),
        "cumulative": _downsample(cumulative),
        "drawdown": _downsample(drawdown),
    }


# ---------------------------------------------------------------------------
# 3. pnl_distribution — 손익 히스토그램 + 보유시간 분포 + 종목 기여 Top/Bottom.
# ---------------------------------------------------------------------------
def pnl_distribution(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """트레이드 손익(%) 히스토그램·보유시간 분포·종목별 기여 Top/Bottom(무예외)."""
    if not trades:
        return {
            "pnl_histogram": [],
            "hold_histogram": [],
            "top_contributors": [],
            "bottom_contributors": [],
        }

    pnl_hist = _histogram([t["profit_pct"] for t in trades], _HIST_BINS, unit="%")
    hold_hist = _histogram([t["hold_min"] for t in trades], _HIST_BINS, unit="min")

    by_name: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        name = t["name"] or "(미상)"
        agg = by_name.setdefault(name, {"name": name, "profit_krw": 0.0, "trades": 0})
        agg["profit_krw"] += t["profit_krw"]
        agg["trades"] += 1

    contributors = sorted(by_name.values(), key=lambda r: r["profit_krw"], reverse=True)
    top = [_round_contrib(c) for c in contributors[:_TOP_N]]
    bottom = [_round_contrib(c) for c in contributors[-_TOP_N:] if c["profit_krw"] < 0.0]
    bottom.sort(key=lambda r: r["profit_krw"])

    return {
        "pnl_histogram": pnl_hist,
        "hold_histogram": hold_hist,
        "top_contributors": top,
        "bottom_contributors": bottom,
    }


def _round_contrib(contrib: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": contrib["name"],
        "profit_krw": float(contrib["profit_krw"]),
        "trades": int(contrib["trades"]),
    }


def _histogram(values: List[float], bins: int, *, unit: str) -> List[Dict[str, Any]]:
    """값 리스트를 균등 bin 히스토그램으로 변환한다. 빈 입력/단일값도 안전 처리."""
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi <= lo:
        # 모든 값이 동일 — 단일 bin.
        return [{"bin_start": float(lo), "bin_end": float(hi), "count": len(values), "unit": unit}]
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - lo) / width)
        if idx >= bins:
            idx = bins - 1
        elif idx < 0:
            idx = 0
        counts[idx] += 1
    return [
        {
            "bin_start": float(lo + i * width),
            "bin_end": float(lo + (i + 1) * width),
            "count": int(counts[i]),
            "unit": unit,
        }
        for i in range(bins)
    ]


# ---------------------------------------------------------------------------
# 4. time_heatmap — 요일×30분 슬롯 손익/거래수 히트맵(매수시각 기준).
# ---------------------------------------------------------------------------
def time_heatmap(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """매수시각 기준 요일(0=월~6=일)×30분 슬롯 손익/거래수 히트맵(무예외).

    매수시간이 YYYYMMDDHHMM(>=12자리)일 때만 시각 슬롯을 산출한다. 부족하면 건너뛴다.
    슬롯 인덱스: (HH*60+MM)//30 → 장중 09:00~15:30 범위를 충분히 덮는다.
    """
    cells: Dict[tuple[int, int], Dict[str, Any]] = {}
    for t in trades:
        buy = t["buy_time"]
        if len(buy) < 12:
            continue
        try:
            dt = datetime.strptime(buy[:12], "%Y%m%d%H%M")
        except ValueError:
            continue
        weekday = dt.weekday()
        slot = (dt.hour * 60 + dt.minute) // 30
        key = (weekday, slot)
        cell = cells.setdefault(key, {"weekday": weekday, "slot": slot, "profit_krw": 0.0, "trades": 0})
        cell["profit_krw"] += t["profit_krw"]
        cell["trades"] += 1

    rows = sorted(cells.values(), key=lambda c: (c["weekday"], c["slot"]))
    return {
        "cells": [
            {
                "weekday": int(c["weekday"]),
                "slot": int(c["slot"]),
                "slot_label": _slot_label(c["slot"]),
                "profit_krw": float(c["profit_krw"]),
                "trades": int(c["trades"]),
            }
            for c in rows
        ]
    }


def _slot_label(slot: int) -> str:
    minutes = slot * 30
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


# ---------------------------------------------------------------------------
# 5. underwater — 언더워터 곡선 + 최대낙폭 구간(시작/저점/회복).
# ---------------------------------------------------------------------------
def underwater(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """거래일 축 언더워터(고점 대비 반납액, 원) 곡선 + 최대낙폭 구간(무예외)."""
    if not trades:
        return {"series": [], "max_drawdown": None}

    days_map = _daily_pnl_map(trades)
    series: List[Dict[str, Any]] = []
    running = 0.0
    peak = float("-inf")
    peak_day = None

    worst_dd = 0.0
    worst_start: Optional[int] = None
    worst_trough: Optional[int] = None
    worst_drawdown = 0.0
    cur_peak_day = None

    for day, pnl in days_map.items():
        running += pnl
        if running >= peak:
            peak = running
            peak_day = day
            cur_peak_day = day
        dd = max(0.0, peak - running)
        series.append({"date": int(day), "drawdown": float(dd)})
        if dd > worst_dd:
            worst_dd = dd
            worst_start = int(cur_peak_day) if cur_peak_day is not None else int(day)
            worst_trough = int(day)
            worst_drawdown = float(dd)

    # 회복 시점: 저점 이후 누적이 그 peak를 회복(>=)한 첫 거래일.
    worst: Optional[Dict[str, Any]] = None
    if worst_start is not None and worst_trough is not None:
        peak_at_worst = _peak_before(days_map, worst_start)
        recovery = _find_recovery(days_map, worst_trough, peak_at_worst=peak_at_worst)
        worst = {
            "start_date": worst_start,
            "trough_date": worst_trough,
            "recovery_date": recovery,
            "drawdown": worst_drawdown,
        }

    return {"series": _downsample(series), "max_drawdown": worst, "peak_day": peak_day}


def _peak_before(days_map: Dict[int, float], start_date: int) -> float:
    """start_date 까지(포함)의 누적 실현손익(=낙폭 시작 peak)."""
    running = 0.0
    for day, pnl in days_map.items():
        running += pnl
        if day == start_date:
            return running
    return running


def _find_recovery(days_map: Dict[int, float], trough_date: int, peak_at_worst: float) -> Optional[int]:
    """저점 이후 누적이 peak_at_worst 를 회복한 첫 거래일. 미회복이면 None."""
    running = 0.0
    after_trough = False
    for day, pnl in days_map.items():
        running += pnl
        if day == trough_date:
            after_trough = True
            continue
        if after_trough and running >= peak_at_worst:
            return int(day)
    return None


# ---------------------------------------------------------------------------
# 6. generate_insights — 규칙 기반 한국어 인사이트(최소 8종 규칙).
# ---------------------------------------------------------------------------
def generate_insights(
    trades: List[Dict[str, Any]],
    summary: Optional[Dict[str, Any]] = None,
    distribution: Optional[Dict[str, Any]] = None,
    heatmap: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """분석 결과로 규칙 기반 인사이트 리스트를 만든다 [{severity,title,detail}](무예외).

    severity: 'info'|'warning'|'critical'. 입력이 비면 빈 리스트.
    호출측이 summary/distribution/heatmap 을 미리 계산해 넘기면 재계산을 피한다.
    """
    if not trades:
        return []
    summary = summary or summary_metrics(trades)
    distribution = distribution or pnl_distribution(trades)
    heatmap = heatmap or time_heatmap(trades)

    insights: List[Dict[str, str]] = []
    total_krw = summary["total_profit_krw"]

    # 규칙 1: 손실 시간대 집중.
    loss_slot = _worst_loss_slot(trades)
    if loss_slot is not None:
        slot_label, slot_loss, slot_total_loss, pct = loss_slot
        if pct >= 30.0:
            insights.append({
                "severity": "warning",
                "title": "손실 시간대 집중",
                "detail": f"전체 손실의 {pct:.0f}%가 {slot_label} 30분 슬롯에 집중됩니다(손실 {slot_loss:,.0f}원).",
            })

    # 규칙 2: 상위 종목 수익 집중(집중 리스크).
    top = distribution.get("top_contributors", [])
    if top and total_krw > 0.0:
        top3 = sum(c["profit_krw"] for c in top[:3] if c["profit_krw"] > 0.0)
        share = top3 / total_krw * 100.0 if total_krw else 0.0
        if share >= 50.0:
            names = ", ".join(c["name"] for c in top[:3])
            insights.append({
                "severity": "warning",
                "title": "수익 집중 리스크",
                "detail": f"상위 3종목({names})이 총수익의 {share:.0f}%를 차지합니다 — 분산 부족.",
            })

    # 규칙 3: 연속 패배 경고.
    loss_streak = summary["max_consecutive_losses"]
    if loss_streak >= 5:
        insights.append({
            "severity": "critical" if loss_streak >= 8 else "warning",
            "title": "연속 패배 구간",
            "detail": f"최대 연속 패배 {loss_streak}회 — 자금관리/중단 규칙 점검 필요.",
        })

    # 규칙 4: 추세형 프로파일(승률 낮으나 payoff 큼).
    if summary["win_rate"] < 45.0 and summary["payoff_ratio"] >= 2.0:
        insights.append({
            "severity": "info",
            "title": "추세추종형 프로파일",
            "detail": f"승률 {summary['win_rate']:.0f}%로 낮지만 payoff {summary['payoff_ratio']:.1f}배 — 소수 큰 이익형.",
        })

    # 규칙 5: 평균회귀형/스캘핑 프로파일(승률 높으나 payoff 낮음).
    if summary["win_rate"] >= 60.0 and 0.0 < summary["payoff_ratio"] < 1.0:
        insights.append({
            "severity": "info",
            "title": "고승률·저payoff 프로파일",
            "detail": f"승률 {summary['win_rate']:.0f}%이나 payoff {summary['payoff_ratio']:.2f}배 — 한 번의 큰 손실에 취약.",
        })

    # 규칙 6: profit factor 건전성.
    pf = summary["profit_factor"]
    if pf > 0.0:
        if pf < 1.0:
            insights.append({
                "severity": "critical",
                "title": "손실 우위 전략",
                "detail": f"profit factor {pf:.2f} (<1) — 총손실이 총이익을 초과합니다.",
            })
        elif pf >= 2.0:
            insights.append({
                "severity": "info",
                "title": "양호한 손익비",
                "detail": f"profit factor {pf:.2f} — 총이익이 총손실의 {pf:.1f}배.",
            })

    # 규칙 7: MDD 심각도(누적 peak 대비 %).
    dd_pct = summary["max_drawdown_pct"]
    if dd_pct >= 40.0:
        insights.append({
            "severity": "critical" if dd_pct >= 60.0 else "warning",
            "title": "최대낙폭 경고",
            "detail": f"누적수익 고점 대비 최대 {dd_pct:.0f}% 반납({summary['max_drawdown_krw']:,.0f}원) — 변동성 큼.",
        })

    # 규칙 8: 보유시간 분포 편향.
    median_hold = summary["median_hold_min"]
    avg_hold = summary["avg_hold_min"]
    if median_hold > 0.0 and avg_hold >= median_hold * 2.0:
        insights.append({
            "severity": "info",
            "title": "보유시간 우편향",
            "detail": f"평균 보유 {avg_hold:.0f}분 vs 중앙값 {median_hold:.0f}분 — 일부 장기 보유가 평균을 끌어올림.",
        })

    # 규칙 9: 거래 빈도(과매매 점검).
    if summary["avg_trades_per_day"] >= 20.0:
        insights.append({
            "severity": "info",
            "title": "고빈도 매매",
            "detail": f"일평균 {summary['avg_trades_per_day']:.0f}회 거래 — 수수료/슬리피지 영향 점검 필요.",
        })

    # 규칙 10: 종합 수익성(전반 요약).
    if total_krw > 0.0:
        insights.append({
            "severity": "info",
            "title": "순수익 달성",
            "detail": f"총 {summary['trade_count']}거래로 {total_krw:,.0f}원(수익률합 {summary['total_profit_pct']:.1f}%) 순이익.",
        })
    elif total_krw < 0.0:
        insights.append({
            "severity": "warning",
            "title": "순손실 결과",
            "detail": f"총 {summary['trade_count']}거래로 {total_krw:,.0f}원(수익률합 {summary['total_profit_pct']:.1f}%) 순손실.",
        })

    return insights


def _worst_loss_slot(trades: List[Dict[str, Any]]) -> Optional[tuple[str, float, float, float]]:
    """매수시각 30분 슬롯 중 손실이 가장 큰 슬롯과 그 비중(%)을 반환한다.

    Returns: (slot_label, slot_loss(음수합), total_loss(음수합), 손실비중%) 또는 None.
    """
    slot_loss: Dict[int, float] = {}
    total_loss = 0.0
    for t in trades:
        if t["profit_krw"] >= 0.0:
            continue
        buy = t["buy_time"]
        if len(buy) < 12:
            continue
        try:
            dt = datetime.strptime(buy[:12], "%Y%m%d%H%M")
        except ValueError:
            continue
        slot = (dt.hour * 60 + dt.minute) // 30
        slot_loss[slot] = slot_loss.get(slot, 0.0) + t["profit_krw"]
        total_loss += t["profit_krw"]
    if not slot_loss or total_loss >= 0.0:
        return None
    worst_slot = min(slot_loss.items(), key=lambda kv: kv[1])
    pct = worst_slot[1] / total_loss * 100.0 if total_loss else 0.0
    return _slot_label(worst_slot[0]), worst_slot[1], total_loss, pct


# ---------------------------------------------------------------------------
# 7. mae_mfe — MAE/MFE 산점도 포인트(R_MAE/R_MFE, 결측 제외, 최대 1000pt 샘플).
# ---------------------------------------------------------------------------
def mae_mfe(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """매수후 최저(MAE)/최고(MFE) 수익률 산점도 포인트를 만든다(무예외).

    각 포인트: {mae, mfe, pnl_pct, hold_sec, code}. R_MAE/R_MFE 둘 다 있는 행만
    쓴다(결측 제외). 1000pt 초과면 균등 다운샘플(브라우저 렌더 부하 방지).
    hold_sec 은 보유시간(분)→초 환산(차트 점 크기/색 보조용).
    """
    points: List[Dict[str, Any]] = []
    for t in trades:
        mae = t.get("mae")
        mfe = t.get("mfe")
        if mae is None or mfe is None:
            continue
        points.append({
            "mae": float(mae),
            "mfe": float(mfe),
            "pnl_pct": float(t.get("profit_pct", 0.0) or 0.0),
            "hold_sec": float(t.get("hold_min", 0.0) or 0.0) * 60.0,
            "code": str(t.get("name", "") or ""),
        })
    return _downsample(points, _SCATTER_MAX)


# ---------------------------------------------------------------------------
# 8. exit_reason_breakdown — 매도조건별 거래수/총손익/승률.
# ---------------------------------------------------------------------------
def exit_reason_breakdown(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """매도조건(청산사유)별 {reason, count, total_pnl, win_rate} 집계(무예외).

    총손익(원) 내림차순 정렬. 사유가 비면 '(미상)'. 빈 입력→[].
    """
    by_reason: Dict[str, Dict[str, Any]] = {}
    for t in trades:
        reason = str(t.get("exit_reason", "") or "").strip() or "(미상)"
        agg = by_reason.setdefault(reason, {"reason": reason, "count": 0, "total_pnl": 0.0, "wins": 0})
        agg["count"] += 1
        pnl = float(t.get("profit_krw", 0.0) or 0.0)
        agg["total_pnl"] += pnl
        if pnl > 0.0:
            agg["wins"] += 1
    rows = [
        {
            "reason": a["reason"],
            "count": int(a["count"]),
            "total_pnl": float(a["total_pnl"]),
            "win_rate": round(a["wins"] / a["count"] * 100.0, 2) if a["count"] else 0.0,
        }
        for a in by_reason.values()
    ]
    rows.sort(key=lambda r: r["total_pnl"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# 묶음 — 잡 결과 CSV 하나로 전체 분석을 한 번에 만든다(API /bt/result 가 소비).
# ---------------------------------------------------------------------------
def full_analysis(
    csv_path: Optional[str],
    t_start: Optional[int] = None,
    t_end: Optional[int] = None,
) -> Dict[str, Any]:
    """CSV 한 파일로 summary/equity/distribution/heatmap/underwater/insights 전부 산출.

    t_start/t_end(매수시간 YYYYMMDDHHMMSS) 를 주면 그 구간 거래만으로 재계산한다
    (수익곡선 브러시 → 구간 분석). 빈 구간이어도 무예외(빈 분석 구조).
    """
    trades = filter_trades(load_trades_csv(csv_path), t_start, t_end)
    summary = summary_metrics(trades)
    distribution = pnl_distribution(trades)
    heatmap = time_heatmap(trades)
    return {
        "trade_count": summary["trade_count"],
        "summary": summary,
        "equity": equity_series(trades),
        "distribution": distribution,
        "heatmap": heatmap,
        "underwater": underwater(trades),
        "insights": generate_insights(trades, summary, distribution, heatmap),
        "mae_mfe": mae_mfe(trades),
        "exit_reasons": exit_reason_breakdown(trades),
    }
