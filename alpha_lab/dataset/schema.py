"""알파 랩 피처 스키마 v1 — 25피처·라벨·메타 컬럼 봉인 정의.

이름·식·순서는 2026-07-05 신규 알파 구현 설계서(§3.2 피처 v1 화이트리스트)에서
봉인됐다. 변경은 새 사전등록(n_trials)으로만 가능하다.

npz 저장 계약(dataset 샤드 직렬화 시 준수):
    features : float32  (ALL_FEATURES 순서의 25컬럼)
    L1_60/L1_180/L1_300/L2 라벨 : int8  (L1은 {0,1}, L2는 {-1,0,1})
    t0   : int64  (int YYYYMMDDHHMMSS)
    code : '<U6'  (6자리 종목코드 문자열)
    date : int32  (int YYYYMMDD)
"""
from __future__ import annotations

from typing import Any, Dict, Mapping

__all__ = [
    "ALL_FEATURES",
    "DERIVED_FEATURES",
    "LABEL_COLUMNS",
    "META_COLUMNS",
    "RAW_FEATURES",
    "as_float",
    "derive",
]

# 원시 15 — 저장 54컬럼 중 화이트리스트(봉인 순서 그대로).
RAW_FEATURES = (
    "등락율",
    "체결강도",
    "초당매수수량",
    "초당매도수량",
    "초당거래대금",
    "거래대금증감",
    "전일비",
    "회전율",
    "전일동시간비",
    "시가총액",
    "당일거래대금",
    "고저평균대비등락율",
    "저가대비고가등락율",
    "라운드피겨위5호가이내",
    "관심종목",
)

# 파생 10 — 같은 초(같은 행) 안에서만 계산(lookahead 불가능, 봉인 순서 그대로).
DERIVED_FEATURES = (
    "잔량불균형",
    "스프레드율",
    "매수벽비율",
    "매도소진율",
    "순매수수량비",
    "고가대비위치",
    "시가대비율",
    "VI거리율",
    "최고매수가대비",
    "당일매수매도비",
)

ALL_FEATURES = RAW_FEATURES + DERIVED_FEATURES  # 25개

LABEL_COLUMNS = ("L1_60", "L1_180", "L1_300", "L2")
META_COLUMNS = ("date", "code", "t0")


def as_float(value: Any) -> float:
    """저장값 → float 강제. None/파싱 불가 값은 0.0 (결측 초와 구분되는 결측 값 규칙)."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def derive(row: Mapping[str, Any]) -> Dict[str, float]:
    """한 행(54컬럼 dict)에서 파생 10피처를 봉인 식 그대로 계산한다.

    반환 dict의 키 순서는 DERIVED_FEATURES와 동일하다. 엣지룰:
    분모는 max(...,1) 계열 가드, 고가==저가는 1e-9 가드,
    VI가격/최고매수가격이 0 이하이면 해당 피처는 0.0.
    """
    price = as_float(row.get("현재가"))
    open_ = as_float(row.get("시가"))
    high = as_float(row.get("고가"))
    low = as_float(row.get("저가"))
    ask1 = as_float(row.get("매도호가1"))
    bid1 = as_float(row.get("매수호가1"))
    ask_total = as_float(row.get("매도총잔량"))
    bid_total = as_float(row.get("매수총잔량"))
    bid_qty1 = as_float(row.get("매수잔량1"))
    ask_qty1 = as_float(row.get("매도잔량1"))
    buy_per_sec = as_float(row.get("초당매수수량"))
    sell_per_sec = as_float(row.get("초당매도수량"))
    vi_price = as_float(row.get("VI가격"))
    best_buy_price = as_float(row.get("최고매수가격"))
    day_buy_amount = as_float(row.get("당일매수금액"))
    day_sell_amount = as_float(row.get("당일매도금액"))
    return {
        "잔량불균형": (bid_total - ask_total) / max(bid_total + ask_total, 1.0),
        "스프레드율": (ask1 - bid1) / max(price, 1.0),
        "매수벽비율": bid_qty1 / max(bid_total, 1.0),
        "매도소진율": sell_per_sec / max(ask_qty1, 1.0),
        "순매수수량비": buy_per_sec / max(sell_per_sec, 1.0),
        "고가대비위치": (price - low) / max(high - low, 1e-9),
        "시가대비율": price / max(open_, 1.0) - 1.0,
        "VI거리율": price / vi_price - 1.0 if vi_price > 0.0 else 0.0,
        "최고매수가대비": price / best_buy_price - 1.0 if best_buy_price > 0.0 else 0.0,
        "당일매수매도비": day_buy_amount / max(day_sell_amount, 1.0),
    }
