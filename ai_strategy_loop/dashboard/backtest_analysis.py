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
import os
import struct
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 컬럼 상수 (holdout/equity_series 와 동일 헤더 계열).
# ---------------------------------------------------------------------------
COL_NAME = "종목명"
COL_BUY_TIME = "매수시간"
COL_SELL_TIME = "매도시간"
COL_HOLD_MIN = "보유시간"
COL_PROFIT_PCT = "수익률"
COL_PROFIT_KRW = "수익금"
# 진입/청산 체결금액(원) — 보유금액(holding value) 곡선 계산용(GUI 패리티 이미지2-e).
#   per-trade CSV 의 GetResultDataframe 헤더에 존재. 결측이면 None(소비측이 결측 행 제외).
COL_BUY_AMOUNT = "매수금액"
COL_SELL_AMOUNT = "매도금액"
# MAE/MFE·청산사유(D) — per-trade CSV 에 이미 존재(틱 DB 재조회 없이 CSV 만으로).
COL_MFE = "R_MFE"
COL_MAE = "R_MAE"
COL_EXIT_REASON = "매도조건"
COL_MARKET_CAP = "시가총액"
COL_BUY_PRICE = "매수가"
COL_SELL_PRICE = "매도가"
COL_CUMULATIVE_PROFIT_KRW = "수익금합계"
COL_ADDITIONAL_BUY_TIME = "추가매수시간"
# 오더플로우(2단계 C) — 진입 시점 호가/체결 스냅샷(per-trade CSV 에 존재).
COL_OF_STRENGTH = "B_체결강도"      # 체결강도(매수세 우위 지표).
COL_OF_BUY_REST = "B_매수총잔량"    # 매수 총 잔량(호가).
COL_OF_SELL_REST = "B_매도총잔량"   # 매도 총 잔량(호가).
COL_OF_PREVDAY = "B_전일동시간비"   # 전일 동시간 거래대금 비.
COL_OF_UPDOWN = "B_등락율"          # 진입 시점 등락율.

_DOWNSAMPLE_MAX = 500
_HIST_BINS = 20
_TOP_N = 10
# MAE/MFE 산점도 최대 표본(브라우저 렌더 부하 방지).
_SCATTER_MAX = 1000
# 롤링 지표 기본 창(거래 단위). 창보다 거래가 적으면 빈 시리즈(무예외).
_ROLLING_WINDOW = 20
# GUI 패리티 — back_static.PlotShow() 거래별 손익+롤링 창(수익금합계 rolling mean 창과 동일).
_GUI_ROLLING_WINDOWS = (20, 60, 120, 240, 480)
# GUI 패리티 — MDD 랜덤 곡선 시행수(PlotShow 가 30개 셔플 곡선을 메인 위에 겹친다).
_MDD_RANDOM_CURVES = 30
# GUI 패리티 — MDD 랜덤 곡선 기본 시드(재현성 — 같은 거래 시퀀스면 같은 셔플 곡선).
_DEMO_SEED_GUI = 20260613
# GUI 패리티 — 시간대별 손익 슬롯 폭(분). PlotShow 는 세션 길이로 3~30분을 고르나,
#   웹은 30분 슬롯으로 고정해 time_heatmap·통계검정 슬롯 정의와 일관되게 한다.
_HOURLY_SLOT_MIN = 30

# 한국 거래일 기준 연율화 상수(252 거래일/년).
_TRADING_DAYS_PER_YEAR = 252.0

# 몬테카를로 기본 시행수·팬차트 다운샘플 상한·기본 파산 임계(자본 대비 %).
_MC_DEFAULT_N = 2000
_MC_FAN_MAX = 200
_MC_RUIN_PCT = 30.0
# 통계 검정 유의수준·최소 표본(과신 방지).
_STAT_ALPHA = 0.05
_STAT_MIN_N = 30

# 요일 한글 라벨(0=월~6=일).
_BT_WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


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

def load_trades_csv_with_status(csv_path: Optional[str]) -> Dict[str, Any]:
    """Read one detail CSV and retain its outcome without exposing filesystem details."""
    if not csv_path:
        return {"status": "missing", "trades": []}
    trades: List[Dict[str, Any]] = []
    row_count = 0
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            if COL_SELL_TIME not in fields or COL_PROFIT_KRW not in fields:
                return {
                    "status": "error",
                    "trades": [],
                    "diagnostic": "required trade columns are missing",
                }
            for row in reader:
                row_count += 1
                trade = _normalize_row(row)
                if trade is not None:
                    trades.append(trade)
    except FileNotFoundError:
        return {"status": "missing", "trades": []}
    except UnicodeError:
        return {"status": "error", "trades": [], "diagnostic": "CSV text is not decodable"}
    except (OSError, csv.Error):
        return {"status": "error", "trades": [], "diagnostic": "CSV could not be read"}
    if row_count and not trades:
        return {"status": "error", "trades": [], "diagnostic": "trade rows are malformed"}
    return {"status": "ok" if trades else "empty", "trades": trades}


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
        "market_cap": _opt_float(row.get(COL_MARKET_CAP)),
        "buy_time": str(row.get(COL_BUY_TIME, "") or "").strip(),
        "sell_time": raw_sell,
        "day": day,
        # Existing analysis fields retain their zero-default semantics.
        "hold_min": _safe_float(row.get(COL_HOLD_MIN)),
        "hold_time": _opt_float(row.get(COL_HOLD_MIN)),
        "buy_price": _opt_float(row.get(COL_BUY_PRICE)),
        "sell_price": _opt_float(row.get(COL_SELL_PRICE)),
        "profit_pct": _safe_float(row.get(COL_PROFIT_PCT)),
        "profit_krw": profit_krw,
        "cumulative_profit_krw": _opt_float(row.get(COL_CUMULATIVE_PROFIT_KRW)),
        "additional_buy_time": str(row.get(COL_ADDITIONAL_BUY_TIME, "") or "").strip(),
        # 진입/청산 체결금액(원) — 보유금액 곡선용. 결측이면 None(소비측이 결측 행 제외).
        "buy_amount": _opt_float(row.get(COL_BUY_AMOUNT)),
        "sell_amount": _opt_float(row.get(COL_SELL_AMOUNT)),
        # MAE/MFE·청산사유(D) — 결측이면 None/빈문자(소비측이 결측 행 제외).
        "mfe": _opt_float(row.get(COL_MFE)),
        "mae": _opt_float(row.get(COL_MAE)),
        "exit_reason": str(row.get(COL_EXIT_REASON, "") or "").strip(),
        # 오더플로우(C) — 진입 호가/체결 스냅샷. 결측이면 None(소비측이 결측 제외).
        "of_strength": _opt_float(row.get(COL_OF_STRENGTH)),
        "of_buy_rest": _opt_float(row.get(COL_OF_BUY_REST)),
        "of_sell_rest": _opt_float(row.get(COL_OF_SELL_REST)),
        "of_prevday": _opt_float(row.get(COL_OF_PREVDAY)),
        "of_updown": _opt_float(row.get(COL_OF_UPDOWN)),
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

    셀 메트릭은 `수익률 합계(%)`(profit_pct_sum) 를 1차 지표로 둔다(수익금 절대액은
    종목·금액 규모에 좌우되어 시간대 비교에 부적합). 수익금 합(profit_krw)도 함께 둔다.
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
        cell = cells.setdefault(
            key, {"weekday": weekday, "slot": slot, "profit_pct_sum": 0.0, "profit_krw": 0.0, "trades": 0}
        )
        cell["profit_pct_sum"] += float(t.get("profit_pct", 0.0) or 0.0)
        cell["profit_krw"] += t["profit_krw"]
        cell["trades"] += 1

    rows = sorted(cells.values(), key=lambda c: (c["weekday"], c["slot"]))
    return {
        "cells": [
            {
                "weekday": int(c["weekday"]),
                "slot": int(c["slot"]),
                "slot_label": _slot_label(c["slot"]),
                "profit_pct_sum": float(c["profit_pct_sum"]),
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
    stats: Optional[List[Dict[str, Any]]] = None,
    mc: Optional[Dict[str, Any]] = None,
    orderflow: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """분석 결과로 규칙 기반 인사이트 리스트를 만든다 [{severity,title,detail}](무예외).

    severity: 'info'|'warning'|'critical'. 입력이 비면 빈 리스트.
    호출측이 summary/distribution/heatmap 을 미리 계산해 넘기면 재계산을 피한다.
    stats/mc/orderflow(2단계 D) 를 주면 통계검정·몬테카를로·오더플로우 인사이트도 붙인다.
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

    # 규칙 11: 통계 검정(요일/시간대 효과 유의성).
    if stats:
        sig = [s for s in stats if s.get("significant")]
        # 가장 큰 평균(양수) 유의 버킷 하나만 대표로 표기(과잉 노출 방지).
        sig_pos = sorted([s for s in sig if s.get("mean", 0.0) > 0.0], key=lambda s: s["mean"], reverse=True)
        if sig_pos:
            s0 = sig_pos[0]
            kind_ko = "요일" if s0["kind"] == "weekday" else "시간대"
            insights.append({
                "severity": "info",
                "title": "통계적으로 유의한 시점 효과",
                "detail": f"{kind_ko} '{s0['label']}' 평균 수익률 {s0['mean']:+.2f}% — 통계적으로 유의(p={s0['p_value']:.3f}, n={s0['n']}).",
            })
        sig_neg = sorted([s for s in sig if s.get("mean", 0.0) < 0.0], key=lambda s: s["mean"])
        if sig_neg:
            s1 = sig_neg[0]
            kind_ko = "요일" if s1["kind"] == "weekday" else "시간대"
            insights.append({
                "severity": "warning",
                "title": "유의한 손실 시점",
                "detail": f"{kind_ko} '{s1['label']}' 평균 수익률 {s1['mean']:+.2f}% — 통계적으로 유의한 손실(p={s1['p_value']:.3f}, n={s1['n']}).",
            })

    # 규칙 12: 몬테카를로(운 의존성 진단).
    if mc and mc.get("observed") and mc.get("n", 0) > 0:
        obs_mdd = float(mc["observed"].get("mdd_krw", 0.0) or 0.0)
        p95_mdd = float(mc.get("mdd_krw", {}).get("p95", 0.0) or 0.0)
        if obs_mdd > 0.0 and p95_mdd >= obs_mdd * 1.5:
            insights.append({
                "severity": "warning",
                "title": "운에 의존한 낙폭 구간",
                "detail": f"몬테카를로 MDD p95({p95_mdd:,.0f}원)가 실측({obs_mdd:,.0f}원)의 {p95_mdd / obs_mdd:.1f}배 — 거래 순서가 유리했을 수 있음.",
            })
        ruin = float(mc.get("ruin_prob", 0.0) or 0.0)
        if ruin >= 0.05:
            insights.append({
                "severity": "critical" if ruin >= 0.2 else "warning",
                "title": "파산 위험 노출",
                "detail": f"몬테카를로 파산확률 {ruin * 100:.0f}%(자본 대비 -{mc.get('ruin_pct', _MC_RUIN_PCT):.0f}% 도달) — 자금관리 점검 필요.",
            })

    # 규칙 13: 오더플로우(승리 진입 프로파일).
    if orderflow and orderflow.get("separation"):
        top_sep = orderflow["separation"][0]
        direction = "높음" if top_sep["diff"] > 0.0 else "낮음"
        insights.append({
            "severity": "info",
            "title": "승리 진입 오더플로우 프로파일",
            "detail": f"이기는 진입의 {top_sep['label']} 중앙값({top_sep['win_p50']:.2f})이 패배({top_sep['loss_p50']:.2f}) 대비 {direction}(차이 {top_sep['diff']:+.2f}) — 진입 필터 후보.",
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
# 9. monte_carlo — 일별 손익 시퀀스 무작위 재배열로 MDD/최종손익 분포(2단계 B).
# ---------------------------------------------------------------------------
def _quantiles(values: List[float]) -> Dict[str, float]:
    """정렬값에서 p5/p25/p50/p75/p95 백분위(선형보간). 빈 입력→0 구조."""
    if not values:
        return {"p5": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}
    ordered = sorted(values)
    n = len(ordered)

    def _pct(q: float) -> float:
        if n == 1:
            return float(ordered[0])
        pos = q * (n - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)

    return {
        "p5": _pct(0.05), "p25": _pct(0.25), "p50": _pct(0.50),
        "p75": _pct(0.75), "p95": _pct(0.95),
    }


def _mdd_of_cumulative(cum: List[float]) -> float:
    """누적 손익 시퀀스의 최대낙폭(원, 양수). peak-to-trough 절대액."""
    peak = float("-inf")
    max_dd = 0.0
    for v in cum:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
    return max(0.0, max_dd)


def _rng_seeded(seed: Optional[int]):
    """numpy Generator(가용) 또는 random.Random 폴백. seed=None 이면 os.urandom 기반."""
    actual = seed
    if actual is None:
        actual = struct.unpack("<I", os.urandom(4))[0]
    try:
        import numpy as np  # noqa: WPS433 - 선택 의존(가용 시만).

        return np.random.default_rng(int(actual)), "numpy"
    except Exception:  # noqa: BLE001 - numpy 없으면 표준 random 으로 폴백.
        import random

        return random.Random(int(actual)), "random"


def monte_carlo(
    trades: List[Dict[str, Any]],
    n: int = _MC_DEFAULT_N,
    seed: Optional[int] = None,
    ruin_pct: float = _MC_RUIN_PCT,
) -> Dict[str, Any]:
    """일별 손익 시퀀스를 무작위 재배열(복원 없이 셔플)해 MDD/최종손익 분포를 만든다.

    각 시행: 일별 손익을 셔플 → 누적곡선 → MDD/최종손익 계산.
    반환: {mdd_pct, mdd_krw, final, ruin_prob, n, fan, observed, days}.
      - mdd_pct/mdd_krw/final: {p5,p25,p50,p75,p95} 백분위.
      - ruin_prob: 누적 저점이 시작자본 대비 -ruin_pct% 도달한 시행 비율.
        자본 기준은 |일별 손익 합|+총이익으로 근사(별도 자본 입력 없음 → 보수적).
      - fan: 일자 인덱스별 누적 손익 분포 밴드(p5/p25/p50/p75/p95) 다운샘플 ≤200pt.
      - observed: 실측(셔플 없는 원래 순서) MDD/최종손익.
    seed 를 주면 재현 가능(테스트). 빈/단일 거래일 입력도 무예외(빈 구조).
    """
    days_map = _daily_pnl_map(trades)
    daily = list(days_map.values())
    days = len(daily)
    n_runs = max(0, int(n))
    empty_q = {"p5": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}
    if days == 0 or n_runs == 0:
        return {
            "mdd_pct": dict(empty_q), "mdd_krw": dict(empty_q), "final": dict(empty_q),
            "ruin_prob": 0.0, "n": 0, "days": days, "fan": [], "observed": None,
        }

    total = sum(daily)
    gross_profit = sum(p for p in daily if p > 0.0)
    # 파산 자본 기준(보수적): 총이익 규모(없으면 |총합|, 그래도 0이면 1).
    capital = gross_profit if gross_profit > 0.0 else abs(total)
    if capital <= 0.0:
        capital = 1.0
    ruin_threshold = -capital * (float(ruin_pct) / 100.0)

    rng, backend = _rng_seeded(seed)
    mdd_krws: List[float] = []
    finals: List[float] = []
    ruin_hits = 0
    # 팬: 일자별 누적 분포(각 일자에 대해 n_runs 개 누적값 수집 → 백분위).
    per_day_cum: List[List[float]] = [[] for _ in range(days)]

    for _ in range(n_runs):
        if backend == "numpy":
            order = rng.permutation(days)
            shuffled = [daily[i] for i in order]
        else:
            shuffled = list(daily)
            rng.shuffle(shuffled)
        running = 0.0
        peak = float("-inf")
        trough = float("inf")
        run_mdd = 0.0
        for di, p in enumerate(shuffled):
            running += p
            per_day_cum[di].append(running)
            if running > peak:
                peak = running
            dd = peak - running
            if dd > run_mdd:
                run_mdd = dd
            if running < trough:
                trough = running
        mdd_krws.append(run_mdd)
        finals.append(running)
        if trough <= ruin_threshold:
            ruin_hits += 1

    # MDD % = MDD_krw / capital * 100 (시행별).
    mdd_pcts = [(m / capital * 100.0) for m in mdd_krws]

    fan_full = [
        {"day_index": di, **_quantiles(per_day_cum[di])}
        for di in range(days)
    ]
    fan = _downsample(fan_full, _MC_FAN_MAX)

    obs_cum: List[float] = []
    running = 0.0
    for p in daily:
        running += p
        obs_cum.append(running)
    observed = {
        "mdd_krw": _mdd_of_cumulative(obs_cum),
        "final_krw": obs_cum[-1] if obs_cum else 0.0,
        "mdd_pct": (_mdd_of_cumulative(obs_cum) / capital * 100.0) if capital else 0.0,
    }

    return {
        "mdd_pct": _quantiles(mdd_pcts),
        "mdd_krw": _quantiles(mdd_krws),
        "final": _quantiles(finals),
        "ruin_prob": round(ruin_hits / n_runs, 6) if n_runs else 0.0,
        "ruin_pct": float(ruin_pct),
        "capital": float(capital),
        "n": n_runs,
        "days": days,
        "fan": fan,
        "observed": observed,
    }


# ---------------------------------------------------------------------------
# 10. entry_orderflow — 승/패 그룹별 진입 오더플로우 분포 비교(2단계 C).
# ---------------------------------------------------------------------------
_OF_VARS: List[Tuple[str, str]] = [
    ("strength", "체결강도"),
    ("imbalance", "호가불균형"),
    ("prevday", "전일동시간비"),
    ("updown", "등락율"),
]


def _of_value(trade: Dict[str, Any], var: str) -> Optional[float]:
    """trade 에서 오더플로우 변수 값을 뽑는다. 호가불균형=매수총잔량/매도총잔량."""
    if var == "strength":
        return trade.get("of_strength")
    if var == "prevday":
        return trade.get("of_prevday")
    if var == "updown":
        return trade.get("of_updown")
    if var == "imbalance":
        buy = trade.get("of_buy_rest")
        sell = trade.get("of_sell_rest")
        if buy is None or sell is None or sell == 0.0:
            return None
        return float(buy) / float(sell)
    return None


def _of_distribution(values: List[float]) -> Dict[str, Any]:
    """값 리스트의 quantile(p10/25/50/75/90)+평균+표본수. 빈 입력→None 구조."""
    if not values:
        return {"n": 0, "mean": None, "p10": None, "p25": None, "p50": None, "p75": None, "p90": None}
    ordered = sorted(values)
    m = len(ordered)

    def _pct(q: float) -> float:
        if m == 1:
            return float(ordered[0])
        pos = q * (m - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, m - 1)
        return float(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo))

    return {
        "n": m,
        "mean": float(sum(ordered) / m),
        "p10": _pct(0.10), "p25": _pct(0.25), "p50": _pct(0.50),
        "p75": _pct(0.75), "p90": _pct(0.90),
    }


def entry_orderflow(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """승(수익률>0)/패 그룹별 진입 오더플로우 변수 분포를 비교한다(무예외).

    변수: 체결강도·호가불균형(매수총잔량/매도총잔량)·전일동시간비·등락율.
    각 변수에 대해 승/패 그룹의 quantile/평균 분포를 산출하고, 승패 중앙값 차이를
    절대값 내림차순으로 정렬한 'separation'(분리력 순위)을 만든다.
    반환: {wins:{var:dist}, losses:{var:dist}, separation:[{var,label,win_p50,loss_p50,diff}]}.
    빈 입력/결측이면 빈/None 구조(소비측이 결측 제외).
    """
    wins_dist: Dict[str, Any] = {}
    losses_dist: Dict[str, Any] = {}
    separation: List[Dict[str, Any]] = []

    for var, label in _OF_VARS:
        win_vals: List[float] = []
        loss_vals: List[float] = []
        for t in trades:
            v = _of_value(t, var)
            if v is None:
                continue
            if float(t.get("profit_pct", 0.0) or 0.0) > 0.0:
                win_vals.append(v)
            else:
                loss_vals.append(v)
        wd = _of_distribution(win_vals)
        ld = _of_distribution(loss_vals)
        wins_dist[var] = wd
        losses_dist[var] = ld
        if wd["p50"] is not None and ld["p50"] is not None:
            diff = wd["p50"] - ld["p50"]
            separation.append({
                "var": var,
                "label": label,
                "win_p50": float(wd["p50"]),
                "loss_p50": float(ld["p50"]),
                "diff": float(diff),
            })

    separation.sort(key=lambda r: abs(r["diff"]), reverse=True)
    return {"wins": wins_dist, "losses": losses_dist, "separation": separation}


# ---------------------------------------------------------------------------
# 11. 통계 검정 — 요일/시간대 버킷 평균 수익률 차이 z/t 검정(2단계 D).
# ---------------------------------------------------------------------------
def _welch_pvalue(a: List[float], b: List[float]) -> Optional[float]:
    """두 표본 평균차의 양측 p값. scipy 가용 시 Welch t-test, 아니면 정규근사.

    표본<2 이거나 분산이 모두 0 이면 None(검정 불가).
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return None
    mean_a = sum(a) / na
    mean_b = sum(b) / nb
    var_a = sum((x - mean_a) ** 2 for x in a) / (na - 1)
    var_b = sum((x - mean_b) ** 2 for x in b) / (nb - 1)
    se2 = var_a / na + var_b / nb
    if se2 <= 0.0:
        return None
    try:
        from scipy import stats  # noqa: WPS433 - 선택 의존.

        _, pval = stats.ttest_ind(a, b, equal_var=False)
        if pval is None or (isinstance(pval, float) and math.isnan(pval)):
            return None
        return float(pval)
    except Exception:  # noqa: BLE001 - scipy 없으면 정규근사로 폴백.
        z = (mean_a - mean_b) / math.sqrt(se2)
        # 표준정규 양측 p값 = 2*(1 - Phi(|z|)), Phi 는 erf 기반.
        return float(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0)))))


def _bucket_pnl(trades: List[Dict[str, Any]], by: str) -> Dict[int, List[float]]:
    """버킷(요일|슬롯)→ 그 버킷의 수익률(%) 리스트. 매수시각 파싱 가능 행만."""
    buckets: Dict[int, List[float]] = {}
    for t in trades:
        buy = str(t.get("buy_time", "") or "")
        if len(buy) < 12:
            continue
        try:
            dt = datetime.strptime(buy[:12], "%Y%m%d%H%M")
        except ValueError:
            continue
        key = dt.weekday() if by == "weekday" else (dt.hour * 60 + dt.minute) // 30
        buckets.setdefault(key, []).append(float(t.get("profit_pct", 0.0) or 0.0))
    return buckets


def statistical_tests(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """요일/시간대 버킷의 수익률 평균을 나머지 거래와 z/t 검정한다(무예외).

    각 버킷에 대해 (버킷 평균 vs 그 외 전체 평균) 차이의 양측 p값을 구한다.
    반환: [{kind, bucket, label, n, mean, p_value, significant, underpowered}].
      - significant: p<0.05 (충분 표본일 때만 True).
      - underpowered: 표본<30(과신 방지 표기).
    scipy 유/무 모두 동작(분기). 빈 입력/단일 버킷이면 빈 리스트.
    """
    out: List[Dict[str, Any]] = []
    for by, kind in (("weekday", "weekday"), ("slot", "slot")):
        buckets = _bucket_pnl(trades, by)
        if len(buckets) < 2:
            continue
        for key, vals in sorted(buckets.items()):
            rest: List[float] = []
            for other_key, other_vals in buckets.items():
                if other_key != key:
                    rest.extend(other_vals)
            n_bucket = len(vals)
            mean_bucket = sum(vals) / n_bucket if n_bucket else 0.0
            pval = _welch_pvalue(vals, rest)
            underpowered = n_bucket < _STAT_MIN_N
            significant = (pval is not None and pval < _STAT_ALPHA and not underpowered)
            out.append({
                "kind": kind,
                "bucket": int(key),
                "label": _BT_WEEKDAY_KO[key] if kind == "weekday" and 0 <= key < 7 else _slot_label(key),
                "n": int(n_bucket),
                "mean": float(mean_bucket),
                "p_value": (round(float(pval), 6) if pval is not None else None),
                "significant": bool(significant),
                "underpowered": bool(underpowered),
            })
    return out


# ---------------------------------------------------------------------------
# 13. rolling_metrics — 거래 순서 축 롤링 승률·payoff(전체화면 인사이트, 트랙 D).
# ---------------------------------------------------------------------------
def rolling_metrics(
    trades: List[Dict[str, Any]],
    window: int = _ROLLING_WINDOW,
) -> Dict[str, Any]:
    """거래 순서(매도시간) 축으로 window 거래 롤링 승률·payoff·평균손익(%)을 만든다(무예외).

    각 점 i 는 거래 [i-window+1 .. i] 구간의 지표다(완전 채워진 창만 산출 → 첫 점은
    window-1 번째 거래에서 시작). 거래가 window 미만이면 빈 시리즈를 돌린다(점 부족).
    payoff = 창 내 평균이익 / |평균손실|(손실 없으면 0). 시계열은 다운샘플 ≤500pt.

    반환: {window, series:[{index, sell_time, win_rate, payoff, avg_pnl_pct}]}.
    """
    win = max(1, int(window))
    n = len(trades)
    if n < win:
        return {"window": win, "series": []}

    # 거래 순서 = 매도시간 오름차순(없으면 입력 순서 유지). 안정 정렬.
    ordered = sorted(
        range(n),
        key=lambda i: str(trades[i].get("sell_time", "") or ""),
    )
    seq = [trades[i] for i in ordered]
    pcts = [float(t.get("profit_pct", 0.0) or 0.0) for t in seq]
    krws = [float(t.get("profit_krw", 0.0) or 0.0) for t in seq]

    series: List[Dict[str, Any]] = []
    for end in range(win - 1, n):
        lo = end - win + 1
        w_pct = pcts[lo:end + 1]
        w_krw = krws[lo:end + 1]
        wins = [p for p in w_krw if p > 0.0]
        losses = [p for p in w_krw if p < 0.0]
        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(losses) / len(losses)) if losses else 0.0
        payoff = (avg_win / abs(avg_loss)) if avg_loss != 0.0 else 0.0
        series.append({
            "index": int(end),
            "sell_time": str(seq[end].get("sell_time", "") or ""),
            "win_rate": round(len(wins) / win * 100.0, 4),
            "payoff": float(payoff),
            "avg_pnl_pct": float(sum(w_pct) / win),
        })

    return {"window": win, "series": _downsample(series)}


# ---------------------------------------------------------------------------
# 14. monthly_calendar — 연×월 실현손익 히트맵(전체화면 인사이트, 트랙 D).
# ---------------------------------------------------------------------------
def monthly_calendar(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """매도일(YYYYMMDD) 기준 (연, 월) 셀별 실현손익/거래수/승률 히트맵을 만든다(무예외).

    반환: {years:[정렬된 연도], cells:[{year, month(1~12), profit_krw, trades, win_rate}]}.
    거래 없는 (연, 월) 셀은 생략한다(소비측이 격자에서 결측 처리). 빈 입력→빈 구조.
    매도일이 8자리 미만이면 그 거래는 제외한다(파싱 불가).
    """
    cells_map: Dict[Tuple[int, int], Dict[str, Any]] = {}
    years: set = set()
    for t in trades:
        raw_day = t.get("day")
        if raw_day is None:
            continue
        try:
            day_int = int(str(raw_day).strip())
        except (ValueError, TypeError):
            continue
        if day_int < 10000000:  # YYYYMMDD 최소 8자리.
            continue
        year = day_int // 10000
        month = (day_int // 100) % 100
        if month < 1 or month > 12:
            continue
        years.add(year)
        key = (year, month)
        cell = cells_map.setdefault(
            key, {"year": year, "month": month, "profit_krw": 0.0, "trades": 0, "wins": 0}
        )
        pnl = float(t.get("profit_krw", 0.0) or 0.0)
        cell["profit_krw"] += pnl
        cell["trades"] += 1
        if pnl > 0.0:
            cell["wins"] += 1

    cells = [
        {
            "year": int(c["year"]),
            "month": int(c["month"]),
            "profit_krw": float(c["profit_krw"]),
            "trades": int(c["trades"]),
            "win_rate": round(c["wins"] / c["trades"] * 100.0, 2) if c["trades"] else 0.0,
        }
        for c in sorted(cells_map.values(), key=lambda c: (c["year"], c["month"]))
    ]
    return {"years": sorted(years), "cells": cells}


# ---------------------------------------------------------------------------
# 15. cumulative_trades — 거래 순서 축 누적 거래수·누적 실현손익(전체화면, 트랙 D).
# ---------------------------------------------------------------------------
def cumulative_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """거래 순서(매도시간) 축으로 누적 거래수·누적 실현손익(원) 듀얼 시계열을 만든다(무예외).

    equity_series 가 거래일 단위로 묶는 것과 달리 여기선 개별 거래 단위 누적이라
    한 화면에서 체결 빈도와 자본 증가를 함께 본다. 시계열은 다운샘플 ≤500pt.

    반환: {series:[{index, sell_time, cum_trades, cum_profit_krw}]}. 빈 입력→빈 시리즈.
    """
    if not trades:
        return {"series": []}

    ordered = sorted(
        range(len(trades)),
        key=lambda i: str(trades[i].get("sell_time", "") or ""),
    )
    series: List[Dict[str, Any]] = []
    running = 0.0
    for rank, i in enumerate(ordered):
        running += float(trades[i].get("profit_krw", 0.0) or 0.0)
        series.append({
            "index": int(rank + 1),
            "sell_time": str(trades[i].get("sell_time", "") or ""),
            "cum_trades": int(rank + 1),
            "cum_profit_krw": float(running),
        })
    return {"series": _downsample(series)}


# ===========================================================================
# GUI 패리티 (B3) — back_static.py PlotShow() 2장 이미지의 웹 동등 데이터.
#
#   PlotShow 는 결과 PNG 2장을 그린다:
#     이미지1(부가정보 2×2): (a) MDD 랜덤 30곡선+메인 (b) 일별수익+누적(+지수)
#                            (c) 시간대별 손익 누적바 (d) 요일별 손익 누적바
#     이미지2(결과 2×1):     (e) 보유금액 곡선 (f) 거래별 손익+롤링 평균
#   아래 순수함수가 같은 데이터를 만든다. PlotShow 가 numpy/pandas 와 별도 보유금액
#   배열(arry_bct)·지수 데이터(yfinance)에 의존하는 부분은 per-trade CSV 만으로
#   정직하게 근사하고 그 한계를 메타로 표기한다(무예외·다운샘플 ≤500pt).
# ===========================================================================
def _trade_profit_sequence(trades: List[Dict[str, Any]]) -> List[float]:
    """거래 순서(매도시간 오름차순)의 거래별 실현손익(원) 시퀀스. 안정 정렬·무예외."""
    if not trades:
        return []
    ordered = sorted(
        range(len(trades)),
        key=lambda i: str(trades[i].get("sell_time", "") or ""),
    )
    return [float(trades[i].get("profit_krw", 0.0) or 0.0) for i in ordered]


def _cumsum(values: List[float]) -> List[float]:
    """누적합 시퀀스. 빈 입력→빈 리스트."""
    out: List[float] = []
    run = 0.0
    for v in values:
        run += v
        out.append(run)
    return out


def mdd_random_curves(
    trades: List[Dict[str, Any]],
    n_curves: int = _MDD_RANDOM_CURVES,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """거래별 손익 순서를 무작위 셔플한 n개 누적곡선 + 실제 누적곡선(PlotShow 이미지1-a).

    PlotShow 는 `수익금`(거래별 실현손익)을 30회 permutation 해 누적합 곡선을 메인
    누적곡선 위에 겹친다. 여기서도 동일하게 거래별 손익을 셔플→누적해 n개 곡선과
    실제(셔플 없는) 곡선을 만든다. 재현성을 위해 seed 를 고정한다(기본 결정적).

    반환(무예외 — 빈 입력도 빈 구조):
      {n, actual:[{index,cum}], curves:[[{index,cum}]...], actual_mdd_pct,
       random_mdd_pct:{max,min,avg}}.
    각 곡선/실제곡선은 다운샘플 ≤500pt. MDD%는 시작자본 근사(|총손익 절대합|) 대비.
    """
    seq = _trade_profit_sequence(trades)
    if not seq:
        return {
            "n": 0, "actual": [], "curves": [],
            "actual_mdd_pct": 0.0, "random_mdd_pct": {"max": 0.0, "min": 0.0, "avg": 0.0},
        }

    # 시작자본 근사(PlotShow 는 seed 자본을 쓰나 CSV 엔 없음): 총이익 규모로 보수 근사.
    gross_profit = sum(p for p in seq if p > 0.0)
    capital = gross_profit if gross_profit > 0.0 else abs(sum(seq))
    if capital <= 0.0:
        capital = 1.0

    def _to_points(cum: List[float]) -> List[Dict[str, Any]]:
        pts = [{"index": i, "cum": float(c)} for i, c in enumerate(cum)]
        return _downsample(pts)

    def _mdd_pct(cum: List[float]) -> float:
        return round(_mdd_of_cumulative(cum) / capital * 100.0, 4) if capital else 0.0

    actual_cum = _cumsum(seq)
    actual_mdd = _mdd_pct(actual_cum)

    n_runs = max(0, int(n_curves))
    rng, backend = _rng_seeded(seed if seed is not None else _DEMO_SEED_GUI)
    curves: List[List[Dict[str, Any]]] = []
    rand_mdds: List[float] = []
    for _ in range(n_runs):
        if backend == "numpy":
            order = rng.permutation(len(seq))
            shuffled = [seq[i] for i in order]
        else:
            shuffled = list(seq)
            rng.shuffle(shuffled)
        cum = _cumsum(shuffled)
        curves.append(_to_points(cum))
        rand_mdds.append(_mdd_pct(cum))

    rmax = max(rand_mdds) if rand_mdds else 0.0
    rmin = min(rand_mdds) if rand_mdds else 0.0
    ravg = round(sum(rand_mdds) / len(rand_mdds), 4) if rand_mdds else 0.0
    return {
        "n": len(curves),
        "actual": _to_points(actual_cum),
        "curves": curves,
        "actual_mdd_pct": actual_mdd,
        "random_mdd_pct": {"max": float(rmax), "min": float(rmin), "avg": float(ravg)},
    }


def daily_pnl(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """거래일별 실현손익(원) 막대 + 누적 라인(PlotShow 이미지1-b). 다운샘플 ≤500pt·무예외.

    PlotShow 는 일별 수익을 막대로, 누적수익률(%)을 라인으로 그리고 시장지수를 겹친다.
    지수 데이터는 per-trade CSV 에 없어 제공하지 않는다(정직 — index_available=False).

    반환: {series:[{date, pnl, cum}], index_available:false}.
      - pnl: 그날 실현손익(원), cum: 그날까지 누적 실현손익(원).
    """
    days_map = _daily_pnl_map(trades)
    series: List[Dict[str, Any]] = []
    run = 0.0
    for day, pnl in days_map.items():
        run += pnl
        series.append({"date": int(day), "pnl": float(pnl), "cum": float(run)})
    return {"series": _downsample(series), "index_available": False}


def hourly_pnl(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """매수시각 30분 슬롯별 이익/손실 분리 손익(원)(PlotShow 이미지1-c). 무예외.

    PlotShow 는 시간대별 이익금액(빨강)·손실금액(파랑)을 막대로 쌓는다. 여기서도 각
    슬롯의 양/음 손익을 분리 집계한다(slot=(HH*60+MM)//30). 매수시각 12자리 미만 제외.

    반환: {slots:[{slot, slot_label, profit, loss, net, trades}]}. 슬롯 오름차순.
    """
    by_slot: Dict[int, Dict[str, Any]] = {}
    for t in trades:
        buy = str(t.get("buy_time", "") or "")
        if len(buy) < 12:
            continue
        try:
            dt = datetime.strptime(buy[:12], "%Y%m%d%H%M")
        except ValueError:
            continue
        slot = (dt.hour * 60 + dt.minute) // _HOURLY_SLOT_MIN
        pnl = float(t.get("profit_krw", 0.0) or 0.0)
        cell = by_slot.setdefault(slot, {"profit": 0.0, "loss": 0.0, "trades": 0})
        if pnl >= 0.0:
            cell["profit"] += pnl
        else:
            cell["loss"] += pnl
        cell["trades"] += 1
    slots = [
        {
            "slot": int(s),
            "slot_label": _slot_label(s),
            "profit": float(c["profit"]),
            "loss": float(c["loss"]),
            "net": float(c["profit"] + c["loss"]),
            "trades": int(c["trades"]),
        }
        for s, c in sorted(by_slot.items())
    ]
    return {"slots": slots}


def weekday_pnl(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """요일(0=월~6=일)별 이익/손실 분리 손익(원)(PlotShow 이미지1-d). 무예외.

    PlotShow 는 요일별 이익금액(빨강)·손실금액(파랑)을 막대로 쌓는다(월~금, 토일은
    거래 있을 때). 매수시각 기준 요일(time_heatmap 과 일관). 12자리 미만 제외.

    반환: {days:[{weekday, label, profit, loss, net, trades}]}. 평일 항상·주말 거래 시.
    """
    by_wd: Dict[int, Dict[str, Any]] = {}
    for t in trades:
        buy = str(t.get("buy_time", "") or "")
        if len(buy) < 12:
            continue
        try:
            dt = datetime.strptime(buy[:12], "%Y%m%d%H%M")
        except ValueError:
            continue
        wd = dt.weekday()
        pnl = float(t.get("profit_krw", 0.0) or 0.0)
        cell = by_wd.setdefault(wd, {"profit": 0.0, "loss": 0.0, "trades": 0})
        if pnl >= 0.0:
            cell["profit"] += pnl
        else:
            cell["loss"] += pnl
        cell["trades"] += 1
    # 파싱 가능한 거래가 하나도 없으면 빈 구조(빈 입력 무예외 계약 — 빈 막대 격자 방지).
    if not by_wd:
        return {"days": []}
    # 평일(0~4)은 항상 표기, 주말(5~6)은 거래 있을 때만(PlotShow 와 동일).
    order = [0, 1, 2, 3, 4]
    for wd in (5, 6):
        if wd in by_wd:
            order.append(wd)
    days = [
        {
            "weekday": int(wd),
            "label": _BT_WEEKDAY_KO[wd],
            "profit": float(by_wd.get(wd, {}).get("profit", 0.0)),
            "loss": float(by_wd.get(wd, {}).get("loss", 0.0)),
            "net": float(by_wd.get(wd, {}).get("profit", 0.0) + by_wd.get(wd, {}).get("loss", 0.0)),
            "trades": int(by_wd.get(wd, {}).get("trades", 0)),
        }
        for wd in order
    ]
    return {"days": days}


def holding_curve(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """진입/청산 이벤트로 시점별 보유금액(원) 곡선을 재구성한다(PlotShow 이미지2-e). 무예외.

    PlotShow 는 별도 보유금액 배열(arry_bct)을 그리나, 그건 per-trade CSV 에 없다.
    여기선 매수시간에 +매수금액, 매도시간에 -매수금액(원금 회수) 이벤트를 시간순으로
    적용해 미청산 진입원금 합(=보유 중 투입금액) 곡선을 만든다 — GUI 보유금액의 정직
    근사(평가손익 변동·수수료 미반영, holding_basis='entry_cost' 로 명시).

    매수금액 결측 행은 제외한다(결측이면 곡선 기여 불가). 매수/매도 시각이 12자리
    미만이면 그 이벤트는 제외한다. 시계열은 다운샘플 ≤500pt.

    반환: {series:[{time, holding}], holding_basis:'entry_cost', covered, total}.
      - time: YYYYMMDDHHMM(int), holding: 그 시점 직후 보유 진입원금 합(원).
      - covered/total: 매수금액이 있어 곡선에 반영된 거래수 / 전체 거래수(한계 표기).
    """
    events: List[Tuple[int, float]] = []  # (시각, 보유금액 증감).
    covered = 0
    total = len(trades)
    for t in trades:
        amt = t.get("buy_amount")
        if amt is None:
            continue
        buy = str(t.get("buy_time", "") or "")
        sell = str(t.get("sell_time", "") or "")
        if len(buy) < 12:
            continue
        try:
            buy_key = int(buy[:12])
        except ValueError:
            continue
        amount = float(amt)
        events.append((buy_key, amount))   # 진입: 보유 +매수금액.
        if len(sell) >= 12:
            try:
                sell_key = int(sell[:12])
                events.append((sell_key, -amount))  # 청산: 보유 -매수금액(원금 회수).
            except ValueError:
                pass
        covered += 1

    if not events:
        return {"series": [], "holding_basis": "entry_cost", "covered": 0, "total": int(total)}

    # 시각 오름차순(동시각은 청산을 진입보다 먼저 적용 → 음수 증감 우선 정렬로 순간 과대 방지).
    events.sort(key=lambda e: (e[0], 0 if e[1] < 0.0 else 1))
    series: List[Dict[str, Any]] = []
    holding = 0.0
    for time_key, delta in events:
        holding += delta
        if holding < 0.0:
            holding = 0.0  # 부동소수/정렬 잔차 보호(음수 보유금액 방지).
        series.append({"time": int(time_key), "holding": float(holding)})

    return {
        "series": _downsample(series),
        "holding_basis": "entry_cost",
        "covered": int(covered),
        "total": int(total),
    }


def trade_rolling(
    trades: List[Dict[str, Any]],
    windows: Tuple[int, ...] = _GUI_ROLLING_WINDOWS,
) -> Dict[str, Any]:
    """거래별 손익(원) + 누적손익의 롤링 평균 라인들(PlotShow 이미지2-f). 무예외.

    PlotShow 는 거래별 이익금액(빨강)·손실금액(파랑) 막대에 `수익금합계`(누적손익)의
    rolling mean(창 20/60/120/240/480) 라인과 누적손익 자체를 겹친다. 여기서도 거래
    순서(매도시간) 축으로 거래별 손익·누적손익·각 창 누적손익 롤링평균을 만든다.

    창보다 거래가 적은 창은 그 구간을 None(미정의)으로 둔다(부분창 미산출). 거래별
    손익/누적은 항상 산출. 모든 시리즈는 동일 인덱스 축으로 다운샘플 ≤500pt.

    반환: {windows:[...], series:[{index, sell_time, pnl, cum, roll:{w:val|None}}]}.
    """
    if not trades:
        return {"windows": list(windows), "series": []}

    ordered = sorted(
        range(len(trades)),
        key=lambda i: str(trades[i].get("sell_time", "") or ""),
    )
    seq = [trades[i] for i in ordered]
    pnls = [float(t.get("profit_krw", 0.0) or 0.0) for t in seq]
    cum = _cumsum(pnls)
    wins = [max(1, int(w)) for w in windows]

    # 각 창의 누적손익(cum) 단순이동평균. 창 미충족 인덱스는 None(부분창 미산출).
    def _rolling_mean(values: List[float], w: int) -> List[Optional[float]]:
        out: List[Optional[float]] = []
        running = 0.0
        for idx, v in enumerate(values):
            running += v
            if idx >= w:
                running -= values[idx - w]
            out.append(round(running / w, 4) if idx >= w - 1 else None)
        return out

    roll_by_w: Dict[int, List[Optional[float]]] = {w: _rolling_mean(cum, w) for w in wins}

    series: List[Dict[str, Any]] = []
    for idx in range(len(seq)):
        series.append({
            "index": int(idx),
            "sell_time": str(seq[idx].get("sell_time", "") or ""),
            "pnl": float(pnls[idx]),
            "cum": float(cum[idx]),
            "roll": {str(w): roll_by_w[w][idx] for w in wins},
        })
    return {"windows": list(wins), "series": _downsample(series)}


def gui_parity(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """PlotShow 2장 이미지의 6개 차트 데이터 묶음(무예외).

    반환: {mdd_random, daily, hourly, weekday, holding, trade_rolling}.
    각 키는 위 동명 순수함수 결과. 빈 입력도 각 함수가 빈 구조를 돌린다.
    """
    return {
        "mdd_random": mdd_random_curves(trades),
        "daily": daily_pnl(trades),
        "hourly": hourly_pnl(trades),
        "weekday": weekday_pnl(trades),
        "holding": holding_curve(trades),
        "trade_rolling": trade_rolling(trades),
    }


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
    return full_analysis_from_trades(trades)


def full_analysis_from_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """이미 로드된 거래로 분석 묶음을 만든다(요청당 CSV 단일 로드용)."""
    summary = summary_metrics(trades)
    distribution = pnl_distribution(trades)
    heatmap = time_heatmap(trades)
    # 통계 검정(D) 은 묶음에 포함해 인사이트에 연결한다(요일/시간대 효과 유의성).
    stats = statistical_tests(trades)
    orderflow = entry_orderflow(trades)
    return {
        "trade_count": summary["trade_count"],
        "summary": summary,
        "equity": equity_series(trades),
        "distribution": distribution,
        "heatmap": heatmap,
        "underwater": underwater(trades),
        "insights": generate_insights(
            trades, summary, distribution, heatmap, stats=stats, orderflow=orderflow
        ),
        "mae_mfe": mae_mfe(trades),
        "exit_reasons": exit_reason_breakdown(trades),
        "stats": stats,
        "orderflow": orderflow,
        # 트랙 D — 전체화면 분석 모드 추가 그래프(롤링 지표·월별 캘린더·누적 거래).
        "rolling": rolling_metrics(trades),
        "monthly": monthly_calendar(trades),
        "cumulative_trades": cumulative_trades(trades),
        # B3 — STOM GUI PlotShow 2장 이미지 패리티(MDD 랜덤·일별·시간대·요일·보유·거래롤링).
        "gui_parity": gui_parity(trades),
    }


# ---------------------------------------------------------------------------
# 12. portfolio_analysis — 복수 전략 일별손익 합성(결합 곡선·MDD·상관·기여).
#
# 레이어 구분(중요): 이 함수는 **워크벤치 UI 레이어**다. per-trade CSV(또는 그에서
#   파싱한 trade dict 리스트)를 입력으로 받아 워크벤치 결과 패널이 그릴 결합 수익곡선
#   SVG·상관 히트맵·개별 기여 표를 직접 만든다. 부모 P-A 의 포트폴리오 상관 스캔
#   (fitness/portfolio.py + .omo/evidence)은 run 단위 일별손익 dict 를 받는 **선택기
#   레이어**로, 분산이득(diversification_gain)·한계 MDD 같은 advisory 판정 보조 지표를
#   낸다. 본 함수는 그 advisory 지표를 재생산하지 않고(중복 회피), 워크벤치가 한 화면에서
#   바로 시각화할 결합 곡선/상관/기여만 만든다(무예외·순수함수).
# ---------------------------------------------------------------------------
def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    """두 동일길이 시퀀스의 피어슨 상관계수. 표본<2거나 한쪽 분산 0이면 None."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0.0 or var_y <= 0.0:
        return None
    return cov / math.sqrt(var_x * var_y)


def portfolio_analysis(
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """복수 전략(잡/세대)의 일별손익을 균등 합성해 결합 분석을 만든다(무예외).

    각 item: {"label": 표시명, "trades": trade dict 리스트} 또는
             {"label": 표시명, "csv_path": per-trade CSV 경로}.
    csv_path 가 있으면 load_trades_csv 로 읽는다(trades 우선). 라벨이 비면 자동 부여.

    합성은 균등 가중(1/N 아님 — 단순 일별손익 '합산'으로, 동일 자본 N개 운용을 가정).
    날짜 축은 전 전략 거래일 합집합이며, 특정 전략에 없는 날은 0원으로 채운다. 상관은
    이 합집합 축에 정렬한 일별손익 시계열 간 피어슨 상관(결측일=0)이다.

    반환(무예외 — 빈/단일 입력도 빈 구조):
      {
        "strategies": [{label, total_profit_krw, max_drawdown_krw, trading_days,
                        contribution_pct}],          # 개별 단독 지표 + 기여 비중
        "combined": {                                # 결합(합산) 결과
            "total_profit_krw", "max_drawdown_krw", "trading_days",
            "equity": [{date, daily_pnl, cum_profit, drawdown}],   # 다운샘플 ≤500pt
        },
        "correlation": {                             # 전략 간 일별손익 상관행렬
            "labels": [label...],
            "matrix": [[r|None ...]...],             # 대각 1.0, 산출불가 None
        },
        "count": N,
      }
    입력이 2개 미만이면 correlation.matrix 는 빈/단일 구조이나 raise 하지 않는다.
    """
    # 1) 각 item → (label, day→pnl 맵). 라벨 충돌은 접미 인덱스로 유일화.
    resolved: List[Tuple[str, Dict[int, float]]] = []
    used_labels: Dict[str, int] = {}
    for idx, item in enumerate(items or []):
        raw_label = str((item or {}).get("label", "") or "").strip() or f"전략{idx + 1}"
        label = raw_label
        if label in used_labels:
            used_labels[raw_label] += 1
            label = f"{raw_label}#{used_labels[raw_label]}"
        else:
            used_labels[raw_label] = 1
        trades = (item or {}).get("trades")
        if trades is None:
            trades = load_trades_csv((item or {}).get("csv_path"))
        resolved.append((label, _daily_pnl_map(list(trades or []))))

    if not resolved:
        return {
            "strategies": [], "combined": {
                "total_profit_krw": 0.0, "max_drawdown_krw": 0.0,
                "trading_days": 0, "equity": [],
            },
            "correlation": {"labels": [], "matrix": []}, "count": 0,
        }

    # 2) 날짜 합집합 축(정렬).
    all_days = sorted({d for _, m in resolved for d in m})

    # 3) 개별 전략 단독 지표.
    strategies: List[Dict[str, Any]] = []
    per_total: List[float] = []
    for label, day_map in resolved:
        vals = list(day_map.values())  # 거래일 순(이미 _daily_pnl_map 가 정렬).
        total = sum(vals)
        cum: List[float] = []
        run = 0.0
        for v in vals:
            run += v
            cum.append(run)
        per_total.append(total)
        strategies.append({
            "label": label,
            "total_profit_krw": float(total),
            "max_drawdown_krw": float(_mdd_of_cumulative(cum)),
            "trading_days": len(day_map),
        })

    # 기여 비중(%): 단독 총손익이 결합 총손익에서 차지하는 비중. 결합 총손익이 0이면
    #   분모가 |총손익| 합(부호 무시)으로 폴백(0/0 방지). 그래도 0이면 0%.
    grand_total = sum(per_total)
    denom = grand_total if grand_total != 0.0 else sum(abs(t) for t in per_total)
    for s, total in zip(strategies, per_total):
        s["contribution_pct"] = round(total / denom * 100.0, 4) if denom != 0.0 else 0.0

    # 4) 결합 곡선(합집합 축, 결측일=0 합산).
    combined_daily: List[Dict[str, Any]] = []
    combined_cum: List[float] = []
    run = 0.0
    peak = float("-inf")
    for day in all_days:
        pnl = sum(m.get(day, 0.0) for _, m in resolved)
        run += pnl
        if run > peak:
            peak = run
        dd = max(0.0, peak - run)
        combined_cum.append(run)
        combined_daily.append({
            "date": int(day), "daily_pnl": float(pnl),
            "cum_profit": float(run), "drawdown": float(dd),
        })

    combined = {
        "total_profit_krw": float(combined_cum[-1]) if combined_cum else 0.0,
        "max_drawdown_krw": float(_mdd_of_cumulative(combined_cum)),
        "trading_days": len(all_days),
        "equity": _downsample(combined_daily),
    }

    # 5) 상관행렬 — 합집합 축에 정렬한 일별손익 시계열 간 피어슨(결측일=0).
    labels = [label for label, _ in resolved]
    aligned: List[List[float]] = [
        [day_map.get(day, 0.0) for day in all_days] for _, day_map in resolved
    ]
    matrix: List[List[Optional[float]]] = []
    for i in range(len(resolved)):
        row: List[Optional[float]] = []
        for j in range(len(resolved)):
            if i == j:
                row.append(1.0)
            else:
                r = _pearson(aligned[i], aligned[j])
                row.append(None if r is None else round(r, 6))
        matrix.append(row)

    return {
        "strategies": strategies,
        "combined": combined,
        "correlation": {"labels": labels, "matrix": matrix},
        "count": len(resolved),
    }
