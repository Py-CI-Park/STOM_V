"""거래소 mock 응답 픽스처.

Constraint: 실 자격증명·실 자금 의존 0. 모든 응답은 결정적 합성 데이터.
Constraint: 실 거래소 API 호출 0건 — release 전 사용자 수동 검증(C1~C4·B3) 필수.
"""
from __future__ import annotations

from typing import Any


# ============ LS증권 mock ============
LS_BALANCE_RESPONSE: dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상",
    "t0424OutBlock1": [
        {"expcode": "005930", "jangb": "0", "janqty": "10",
         "mdposqt": "0", "pamt": "78000", "appamt": "780000"},
    ],
}

LS_ORDER_RESPONSE: dict[str, Any] = {
    "rsp_cd": "00000",
    "rsp_msg": "정상처리",
    "OrderNo": "00012345",
}


# ============ 바이낸스 mock ============
BINANCE_ACCOUNT_RESPONSE: dict[str, Any] = {
    "balances": [
        {"asset": "USDT", "free": "1000.00000000", "locked": "0.00000000"},
        {"asset": "BTC", "free": "0.01000000", "locked": "0.00000000"},
    ],
}

BINANCE_ORDER_RESPONSE: dict[str, Any] = {
    "symbol": "BTCUSDT",
    "orderId": 123456789,
    "status": "FILLED",
    "type": "LIMIT",
    "side": "BUY",
    "executedQty": "0.001",
    "cummulativeQuoteQty": "78.0",
}


# ============ 업비트 mock ============
UPBIT_ACCOUNT_RESPONSE: list[dict[str, Any]] = [
    {"currency": "KRW", "balance": "1000000.0", "locked": "0.0"},
    {"currency": "BTC", "balance": "0.01", "locked": "0.0"},
]

UPBIT_ORDER_RESPONSE: dict[str, Any] = {
    "uuid": "abc-1234",
    "side": "bid",
    "ord_type": "limit",
    "state": "done",
    "market": "KRW-BTC",
    "executed_volume": "0.001",
}


class MockLsAPI:
    """LsRestAPI 인터페이스 호환 mock."""

    def __init__(self, *_args, **_kwargs):
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def _stub(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return LS_BALANCE_RESPONSE if "balance" in name.lower() else LS_ORDER_RESPONSE
        return _stub


class MockUpbitAPI:
    """UpbitRestAPI 인터페이스 호환 mock."""

    def __init__(self, *_args, **_kwargs):
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def _stub(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if "account" in name.lower() or "balance" in name.lower():
                return UPBIT_ACCOUNT_RESPONSE
            return UPBIT_ORDER_RESPONSE
        return _stub


class MockBinanceAPI:
    """바이낸스 client 인터페이스 호환 mock (sync)."""

    def __init__(self, *_args, **_kwargs):
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def _stub(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if "account" in name.lower():
                return BINANCE_ACCOUNT_RESPONSE
            return BINANCE_ORDER_RESPONSE
        return _stub
