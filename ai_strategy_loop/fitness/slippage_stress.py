"""슬리피지 스트레스 advisory (V5).

per-trade 백테스트 결과 CSV만 읽어, 진입/청산이 각각 N틱씩 불리하게 체결되고
추가 수수료(bps)가 붙는 시나리오별 손익 민감도를 재계산하는 **순수 분석 도구**다.
런타임 동작/플래그/엔진/하드게이트에는 어떤 영향도 주지 않는다(advisory 전용).

per-trade 재계산:
  - 수량 역산: 수량 = 수익금 / (매도가 - 매수가). 0 나눗셈(매도가==매수가)이거나
    역산 수량 <= 0 이면 추정 폴백 없이 해당 행을 skipped로 정직 공시한다.
  - 조정수익금 = ((매도가 - N틱×tick(매도가)) - (매수가 + N틱×tick(매수가))) × 수량
                 - 추가수수료bps × (매수금액 + 매도금액) / 10000.
    매수금액/매도금액 컬럼이 없으면 가격×수량으로 보충한다.
  - MDD는 매도시간 앞 8자리(거래일)로 일별 집계 후 누적곡선의
    peak-to-trough 낙폭 **금액(원)** 이다.

CSV 컬럼/인코딩은 fitness 파서 관례(equity_series/holdout: utf-8-sig,
'매수시간'/'매도시간'='YYYYMMDDHHMMSS', '매수가'/'매도가'/'수익금')를 그대로 따른다.
결과 dict는 JSON 직렬화 가능해야 한다(비유한수 금지 — 정의 불가 값은 None).
"""
from __future__ import annotations

import csv
import math
from typing import Dict, List, Optional, Sequence, Tuple

# 결과 CSV 컬럼명 (backtest/back_static.py 결과 헤더와 동일 계열).
_SELL_TIME_COLUMN = "매도시간"
_BUY_PRICE_COLUMN = "매수가"
_SELL_PRICE_COLUMN = "매도가"
_PROFIT_COLUMN = "수익금"
_BUY_AMOUNT_COLUMN = "매수금액"
_SELL_AMOUNT_COLUMN = "매도금액"


def krx_tick_size(price: float) -> float:
    """2023년 개편 KRX 코스피/코스닥 공통 호가단위(원)를 돌려준다.

    경계: <2000:1, <5000:5, <20000:10, <50000:50, <200000:100,
          <500000:500, 그 이상:1000.
    """
    p = float(price)
    if p < 2000:
        return 1.0
    if p < 5000:
        return 5.0
    if p < 20000:
        return 10.0
    if p < 50000:
        return 50.0
    if p < 200000:
        return 100.0
    if p < 500000:
        return 500.0
    return 1000.0


def _finite_or_none(value) -> Optional[float]:
    """float 변환 후 유한수만 통과시킨다(JSON 직렬화 안전 — NaN/inf 금지)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _read_trade_rows(csv_path: str) -> Tuple[List[dict], int]:
    """결과 CSV 한 파일에서 재계산 가능한 거래 행을 추출한다.

    Returns:
        (rows, skipped):
          rows = [{"day": int, "buy_price": float, "sell_price": float,
                   "profit": float, "qty": float, "buy_amount": float,
                   "sell_amount": float}, ...]  # 거래 순서 보존.
          skipped = 수량 역산 불가(0 나눗셈/수량<=0) 또는 필드 파싱 실패 행 수.
        CSV 없음/IO 실패/필수 컬럼 누락이면 ([], 0)으로 무예외 흡수
        (equity_series._compute_holdings_series와 동일 패턴).
    """
    rows: List[dict] = []
    skipped = 0
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            fields = reader.fieldnames or []
            required = (
                _SELL_TIME_COLUMN,
                _BUY_PRICE_COLUMN,
                _SELL_PRICE_COLUMN,
                _PROFIT_COLUMN,
            )
            if any(col not in fields for col in required):
                return [], 0  # 결측 컬럼 → 재계산 불가 파일. 빈 결과(무예외).
            for row in reader:
                raw_t = str(row.get(_SELL_TIME_COLUMN, "") or "").strip()
                if len(raw_t) < 8:
                    skipped += 1
                    continue
                try:
                    day = int(raw_t[:8])
                    buy_price = float(row.get(_BUY_PRICE_COLUMN))
                    sell_price = float(row.get(_SELL_PRICE_COLUMN))
                    profit = float(row.get(_PROFIT_COLUMN))
                except (TypeError, ValueError):
                    skipped += 1
                    continue
                spread = sell_price - buy_price
                if spread == 0.0:
                    skipped += 1  # 0 나눗셈 방어 — 수량 역산 불가.
                    continue
                qty = profit / spread
                if qty <= 0.0 or not math.isfinite(qty):
                    skipped += 1  # 추정 폴백 없이 정직 공시.
                    continue
                buy_amount = _finite_or_none(row.get(_BUY_AMOUNT_COLUMN))
                sell_amount = _finite_or_none(row.get(_SELL_AMOUNT_COLUMN))
                rows.append(
                    {
                        "day": day,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "profit": profit,
                        "qty": qty,
                        # 금액 컬럼 결측이면 가격×수량으로 보충(수수료 베이스).
                        "buy_amount": buy_amount if buy_amount is not None else buy_price * qty,
                        "sell_amount": sell_amount if sell_amount is not None else sell_price * qty,
                    }
                )
    except Exception:  # noqa: BLE001 - CSV 없음/IO/파싱 실패는 빈 결과로 흡수(무예외).
        return [], 0
    return rows, skipped


def _mdd_amount(day_profit_pairs: List[Tuple[int, float]]) -> float:
    """(거래일, 손익) 목록을 일별 집계 → 누적곡선 → 최대낙폭 금액(원, >=0)."""
    daily: Dict[int, float] = {}
    for day, pnl in day_profit_pairs:
        daily[day] = daily.get(day, 0.0) + pnl
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for day in sorted(daily):
        cum += daily[day]
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _adjusted_profit(trade: dict, tick: int, fee_bps: float) -> float:
    """한 거래의 시나리오 조정수익금(원)을 계산한다."""
    buy = trade["buy_price"] + tick * krx_tick_size(trade["buy_price"])
    sell = trade["sell_price"] - tick * krx_tick_size(trade["sell_price"])
    gross = (sell - buy) * trade["qty"]
    fee = fee_bps * (trade["buy_amount"] + trade["sell_amount"]) / 10000.0
    return gross - fee


def stress_report_from_csvs(
    csv_paths: Sequence[str],
    *,
    tick_levels: Sequence[int] = (0, 1, 2),
    extra_fee_bps: Sequence[float] = (0.0, 5.0),
    betting=None,
) -> dict:
    """결과 CSV들에 틱 슬리피지 + 추가 수수료 시나리오를 적용해 집계한다.

    Args:
        csv_paths: per-trade 백테 결과 CSV 경로 목록(utf-8-sig).
        tick_levels: 진입 +N틱·청산 -N틱 동시 불리 적용할 틱 수 목록.
        extra_fee_bps: 매수금액+매도금액 합산 기준 추가 수수료(bps) 목록.
        betting: config.bt_betting(백만원 단위 '5'=500만원). 참고용으로만
            결과에 betting_krw로 실어 준다 — 수량 추정 폴백에는 쓰지 않는다.

    Returns:
        dict (JSON 직렬화 가능, 비유한수 없음):
          {
            "trade_count": int,            # 재계산에 쓰인 유효 거래 수.
            "skipped_trades": int,         # 수량 역산 불가/파싱 실패로 제외된 행 수.
            "base_total_profit": float,    # 원본 수익금 합(유효 거래 기준).
            "betting_krw": float|None,
            "csv_paths": [str, ...],
            "scenarios": [
              {"tick": int, "fee_bps": float,
               "total_profit": float,          # 시나리오 조정수익금 합.
               "profit_delta": float,          # total_profit - base_total_profit.
               "profit_retention_ratio": float|None,  # base<=0이면 None(정의 불가).
               "mdd_amount": float,            # 일별 누적곡선 최대낙폭 금액(원).
               "trade_count": int,
               "breakeven_tick": float|None},  # 수익 0 되는 틱 수(선형추정).
              ...
            ],
          }

    breakeven_tick: 조정수익금 합은 틱 수 N에 대해 정확히 선형이므로
    같은 fee 레벨의 N=0 총수익과 틱당 비용 합(Σ (tick(매수가)+tick(매도가))×수량)으로
    total(N)=0 이 되는 N을 구한다. N=0 총수익이 이미 <=0이면 0.0,
    틱당 비용이 0(거래 없음)이면 None.
    """
    trades: List[dict] = []
    skipped = 0
    for path in csv_paths:
        rows, file_skipped = _read_trade_rows(str(path))
        trades.extend(rows)
        skipped += file_skipped

    base_total = sum(t["profit"] for t in trades)
    # 틱당 비용 합(원/틱): fee와 무관 — breakeven 선형추정의 기울기.
    per_tick_cost = sum(
        (krx_tick_size(t["buy_price"]) + krx_tick_size(t["sell_price"])) * t["qty"]
        for t in trades
    )

    scenarios: List[dict] = []
    for fee in extra_fee_bps:
        fee = float(fee)
        # 같은 fee 레벨의 N=0 총수익(breakeven 선형추정 절편).
        total_at_zero_tick = sum(_adjusted_profit(t, 0, fee) for t in trades)
        if per_tick_cost > 0.0:
            if total_at_zero_tick <= 0.0:
                breakeven: Optional[float] = 0.0
            else:
                breakeven = total_at_zero_tick / per_tick_cost
        else:
            breakeven = None  # 거래 없음 — 기울기 미정의.
        for tick in tick_levels:
            tick = int(tick)
            adjusted = [_adjusted_profit(t, tick, fee) for t in trades]
            total = sum(adjusted)
            retention: Optional[float] = None
            if base_total > 0.0:
                retention = total / base_total
            mdd = _mdd_amount(
                [(t["day"], p) for t, p in zip(trades, adjusted)]
            )
            scenarios.append(
                {
                    "tick": tick,
                    "fee_bps": fee,
                    "total_profit": float(total),
                    "profit_delta": float(total - base_total),
                    "profit_retention_ratio": _finite_or_none(retention),
                    "mdd_amount": float(mdd),
                    "trade_count": len(trades),
                    "breakeven_tick": _finite_or_none(breakeven),
                }
            )

    # betting은 참고 메타로만 싣는다(수량 폴백 금지 — skipped로 정직 공시).
    from ai_strategy_loop.fitness.equity_series import _parse_betting_to_krw  # noqa: PLC0415

    return {
        "trade_count": len(trades),
        "skipped_trades": int(skipped),
        "base_total_profit": float(base_total),
        "betting_krw": _finite_or_none(_parse_betting_to_krw(betting)),
        "csv_paths": [str(p) for p in csv_paths],
        "scenarios": scenarios,
    }
