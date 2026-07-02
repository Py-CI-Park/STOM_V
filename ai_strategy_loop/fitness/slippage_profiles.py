"""슬리피지 다중 프로파일(tick0/1/2/3) advisory 지표 (Phase 0 T0.2).

slippage_stress.py의 KRX 호가단위/일별 MDD 계산을 재사용해, 진입 +N틱·매도
-N틱 불리 체결 프로파일별 총손익과 건당 조정치를 재계산하는 **순수 분석
도구**다. 런타임 동작/플래그/엔진/승격 흐름에는 어떤 영향도 주지 않는다
(advisory 전용 — 승격 hard gate 판정은 controller/condition_discovery.py의
순수 함수가 이 결과 dict를 입력으로만 읽는다).

거래행 스키마는 per-trade 결과 CSV(한국어 컬럼, backtest/back_static.py 헤더)를
그대로 따른다: '매수가'/'매도가'/'수익금' 필수, '매도시간'(YYYYMMDDHHMMSS)은
MDD 일별 집계용, '매수금액'은 수량 역산 정밀화용(있으면 우선 사용).

수량 역산 규칙(엔진 손익 모델 정합 — utility/static.py GetKiwoomPgSgSp):
  - '수익금'은 세금 0.18% + 매수/매도 수수료 각 0.015%가 반영된 **순손익**이다.
  - '매수금액'이 있으면 수량 = 매수금액 / 매수가 (정확, 편향 없음).
  - 없으면 수량 = 수익금 / 순스프레드,
    순스프레드 = 매도가×(1-세금-수수료) - 매수가×(1+수수료).
    총스프레드(매도가-매수가)로 나누던 종전 방식은 수익 거래의 수량을
    과소 추정해 tick 페널티를 낮게 잡고(관대 편향), 수수료 역전 한계
    거래(스프레드>0인데 수익금<0, 매도가==매수가)를 통째로 버렸다.
  - 수익금 부호와 순스프레드 부호가 정반대인 모순 행, 역산 불가 행은
    추정 폴백 없이 skipped로 정직 공시한다.

틱 조정은 호가단위 밴드를 한 틱씩 단계 통과(step)하며 계산한다
(예: 매수 1999 +2틱 = 2005, 선형 1999+2×1=2001 아님). 조정손익 =
원 수익금 - 수량×(매수측 상승분 + 매도측 하락분). 슬리피지로 매도가가
낮아질 때의 세금 감소분은 환급하지 않는다(보수적 — hard gate 안전 방향).
MDD는 유효 거래 전부의 거래일을 알 수 있을 때만 계산하고 불가하면 None.
결과 dict는 JSON 직렬화 가능해야 한다(비유한수 금지 — 정의 불가 값은 None).
"""
from __future__ import annotations

import csv
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

# 기존 슬리피지 코드 재사용(재구축 금지) — 같은 패키지의 검증된 구현을 공유한다.
from ai_strategy_loop.fitness.slippage_stress import (  # noqa: PLC2701
    _BUY_AMOUNT_COLUMN,
    _BUY_PRICE_COLUMN,
    _PROFIT_COLUMN,
    _SELL_PRICE_COLUMN,
    _SELL_TIME_COLUMN,
    _finite_or_none,
    _mdd_amount,
    krx_tick_size,
)

__all__ = [
    "DEFAULT_SLIPPAGE_TICKS",
    "SLIPPAGE_PROFILES_SCHEMA_VERSION",
    "compute_slippage_profiles",
    "krx_tick_size",
    "slippage_profiles_from_csv",
]

SLIPPAGE_PROFILES_SCHEMA_VERSION = 1
DEFAULT_SLIPPAGE_TICKS = (0, 1, 2, 3)

# 엔진 손익 모델 상수 — utility/static.py GetKiwoomPgSgSp와 동일 출처.
_KIWOOM_TAX_RATE = 0.0018   # 매도금액 기준 거래세.
_KIWOOM_FEE_RATE = 0.00015  # 매수/매도 각각의 수수료율.


def _net_spread(buy_price: float, sell_price: float) -> float:
    """키움 순손익 모델 기준 주당 순스프레드(원) — 수익금 == 수량×순스프레드."""
    sell_net = sell_price * (1.0 - _KIWOOM_TAX_RATE - _KIWOOM_FEE_RATE)
    return sell_net - buy_price * (1.0 + _KIWOOM_FEE_RATE)


def _tick_size_below(price: float) -> float:
    """가격 바로 아래 호가의 단위(원). 밴드 경계에서는 하단 밴드 단위를 쓴다."""
    return krx_tick_size(price - 1.0) if price > 1.0 else 1.0


def _adverse_fill_prices(buy_price: float, sell_price: float, tick: int) -> tuple:
    """진입 +N틱·매도 -N틱 불리 체결가. 호가단위 밴드를 한 틱씩 단계 통과한다."""
    buy = float(buy_price)
    sell = float(sell_price)
    for _ in range(max(int(tick), 0)):
        buy += krx_tick_size(buy)
        sell = max(sell - _tick_size_below(sell), 0.0)
    return buy, sell


def _estimate_quantity(buy_price: float, profit: float, net_spread: float,
                       buy_amount: Optional[float]) -> Optional[float]:
    """거래 수량을 추정한다(불가하면 None — 추정 폴백 금지).

    '매수금액'이 있으면 매수금액/매수가(정확). 없으면 순손익 모델 역산
    수익금/순스프레드 — 수수료 역전 한계 거래(순스프레드<0·수익금<0)도
    수량>0으로 정상 복원된다.
    """
    if buy_amount is not None and buy_amount > 0.0:
        qty = buy_amount / buy_price
    elif net_spread != 0.0:
        qty = profit / net_spread
    else:
        return None
    if qty <= 0.0 or not math.isfinite(qty):
        return None
    return qty


def _normalize_trade_row(row: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """한국어 결과행 하나를 재계산용 정규화 행으로 바꾼다(불가하면 None).

    '매도시간'이 없어도 손익 재계산은 가능하므로 day=None으로 유지한다
    (그 경우 MDD만 None 처리 — 추측 금지).
    """
    try:
        buy_price = float(row.get(_BUY_PRICE_COLUMN))
        sell_price = float(row.get(_SELL_PRICE_COLUMN))
        profit = float(row.get(_PROFIT_COLUMN))
    except (TypeError, ValueError):
        return None
    if buy_price <= 0.0 or sell_price <= 0.0:
        return None
    if not all(math.isfinite(v) for v in (buy_price, sell_price, profit)):
        return None
    net_spread = _net_spread(buy_price, sell_price)
    if profit * net_spread < 0.0:
        return None  # 수익금 부호가 순손익 모델과 모순 — 역산 신뢰 불가.
    qty = _estimate_quantity(
        buy_price, profit, net_spread, _finite_or_none(row.get(_BUY_AMOUNT_COLUMN))
    )
    if qty is None:
        return None  # 추정 폴백 없이 skipped로 정직 공시.
    day: Optional[int] = None
    raw_t = str(row.get(_SELL_TIME_COLUMN, "") or "").strip()
    if len(raw_t) >= 8:
        try:
            day = int(raw_t[:8])
        except ValueError:
            day = None
    return {
        "day": day,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "profit": profit,
        "qty": qty,
    }


def _slippage_delta(trade: Mapping[str, Any], tick: int) -> float:
    """틱 슬리피지로 거래 1건이 추가로 잃는 금액(원, <=0)."""
    buy_adv, sell_adv = _adverse_fill_prices(trade["buy_price"], trade["sell_price"], tick)
    per_share_cost = (buy_adv - trade["buy_price"]) + (trade["sell_price"] - sell_adv)
    return -per_share_cost * trade["qty"]


def _profile_entry(
    trades: List[dict],
    tick: int,
    base_total: float,
    mdd_available: bool,
) -> Dict[str, Any]:
    """단일 틱 프로파일의 JSON-safe 항목을 만든다."""
    adjusted = [t["profit"] + _slippage_delta(t, tick) for t in trades]
    total = float(sum(adjusted))
    delta = total - base_total
    retention = total / base_total if base_total > 0.0 else None
    per_trade = delta / len(trades) if trades else None
    mdd: Optional[float] = None
    if mdd_available:
        mdd = float(_mdd_amount([(t["day"], p) for t, p in zip(trades, adjusted)]))
    return {
        "tick": int(tick),
        "total_profit": total,
        "profit_delta": float(delta),
        # 건당 조정치(원/거래): 틱 슬리피지로 거래 1건이 평균적으로 잃는 금액(<=0).
        "per_trade_adjustment": _finite_or_none(per_trade),
        "profit_retention_ratio": _finite_or_none(retention),
        "mdd_amount": mdd,
        "profit_positive": total > 0.0,
    }


def _profiles_from_trades(trades: List[dict], skipped: int, ticks: Sequence[int]) -> Dict[str, Any]:
    """정규화된 거래행 목록에서 프로파일 report dict를 조립한다."""
    base_total = float(sum(t["profit"] for t in trades))
    # 유효 거래 전부의 거래일을 알 때만 일별 MDD 재집계가 가능하다(부분 추측 금지).
    mdd_available = bool(trades) and all(t.get("day") is not None for t in trades)
    tick_list = [int(t) for t in ticks]
    profiles = {
        f"tick{n}": _profile_entry(trades, n, base_total, mdd_available)
        for n in tick_list
    }
    return {
        "schema_version": SLIPPAGE_PROFILES_SCHEMA_VERSION,
        "authority": "advisory_only",
        "trade_count": len(trades),
        "skipped_trades": int(skipped),
        "base_total_profit": base_total,
        "ticks": tick_list,
        "profiles": profiles,
    }


def compute_slippage_profiles(
    trade_rows: Sequence[Mapping[str, Any]],
    ticks: Sequence[int] = DEFAULT_SLIPPAGE_TICKS,
) -> Dict[str, Any]:
    """거래행(한국어 컬럼 dict) 목록에 틱 프로파일별 손익 재계산을 적용한다.

    Args:
        trade_rows: per-trade 결과행 목록. '매수가'/'매도가'/'수익금' 필수,
            '매수금액'은 수량 정밀 역산용(있으면 우선), '매도시간'은 MDD
            일별 집계용(없으면 mdd_amount=None).
        ticks: 진입 +N틱·매도 -N틱 동시 불리 적용할 틱 수 목록(기본 0/1/2/3).

    Returns:
        dict (JSON 직렬화 가능): {schema_version, authority, trade_count,
        skipped_trades, base_total_profit, ticks, profiles: {"tick0": {...}, ...}}.
        각 프로파일 = {tick, total_profit, profit_delta, per_trade_adjustment,
        profit_retention_ratio(base<=0이면 None), mdd_amount(불가 시 None),
        profit_positive}.
    """
    trades: List[dict] = []
    skipped = 0
    for row in trade_rows or ():
        normalized = _normalize_trade_row(row) if isinstance(row, Mapping) else None
        if normalized is None:
            skipped += 1
        else:
            trades.append(normalized)
    return _profiles_from_trades(trades, skipped, ticks)


def _read_csv_rows(csv_path: str) -> List[dict]:
    """결과 CSV(utf-8-sig)의 원시 행 목록. 파일 없음/IO 실패는 빈 목록(무예외)."""
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:  # noqa: BLE001 - CSV 없음/IO 실패는 빈 결과로 흡수(무예외).
        return []


def slippage_profiles_from_csv(
    csv_path: str,
    ticks: Sequence[int] = DEFAULT_SLIPPAGE_TICKS,
) -> Dict[str, Any]:
    """결과 CSV(utf-8-sig) 한 파일에서 프로파일 report를 만든다.

    행 정규화/스킵 규칙은 compute_slippage_profiles와 완전히 동일하다
    (같은 논리 데이터 → 같은 결과). 필수 컬럼이 없는 스키마 불량 CSV는
    전 행이 skipped로 집계되어 진짜 빈 결과(trade_count=0, skipped=0)와
    구분된다. 파일 없음/IO 실패만 무예외 빈 report가 된다.
    """
    report = compute_slippage_profiles(_read_csv_rows(str(csv_path)), ticks)
    return {**report, "csv_path": str(csv_path)}
