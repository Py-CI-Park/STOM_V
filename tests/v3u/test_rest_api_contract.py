"""V3U REST API 정적 계약 + mock 응답 검증.

본 파일은 실 자격증명·실 거래소 API 호출 0건이다. 정적 import + 클래스 노출 +
mock 응답 round-trip만 검증한다.

release 전 사용자가 다음을 직접 검증해야 한다 (자동화 본질적 불가):
- C1: LS증권 모의투자 실 주문/체결/잔고
- C2: 바이낸스 테스트넷 실 주문 라이프사이클
- C3: 업비트 실 최소금액 매수/매도
- B3: LS 웹소켓 체결/호가 분리 라이브 수신
- C4: base_strategy/base_trader 1시간 무인 운영
"""
from __future__ import annotations

import importlib

import pytest

from tests.v3u.fixtures.mock_exchange import (
    BINANCE_ACCOUNT_RESPONSE,
    LS_BALANCE_RESPONSE,
    MockBinanceAPI,
    MockLsAPI,
    MockUpbitAPI,
    UPBIT_ACCOUNT_RESPONSE,
)


pytestmark = pytest.mark.contract


def test_c1_ls_rest_module_signature_static() -> None:
    """C1 정적: trade.restapi_ls 모듈이 핵심 클래스 3개를 노출한다."""
    mod = importlib.import_module("trade.restapi_ls")
    expected = ("LsRestAPI", "LsWebSocketReceiver", "LsWebSocketTrader")
    for cls_name in expected:
        assert hasattr(mod, cls_name), f"trade.restapi_ls에서 {cls_name} 미노출"
        cls = getattr(mod, cls_name)
        assert isinstance(cls, type), f"{cls_name}이 클래스가 아님"


def test_c2_binance_rest_module_signature_static() -> None:
    """C2 정적: trade.restapi_binance 모듈이 WebSocket 핵심 클래스를 노출한다."""
    mod = importlib.import_module("trade.restapi_binance")
    expected = ("BinanceWebSocketReceiver", "BinanceWebSocketTrader")
    for cls_name in expected:
        assert hasattr(mod, cls_name), f"trade.restapi_binance에서 {cls_name} 미노출"


def test_c3_upbit_rest_module_signature_static() -> None:
    """C3 정적: trade.restapi_upbit 모듈이 핵심 함수/클래스를 노출한다."""
    mod = importlib.import_module("trade.restapi_upbit")
    for name in (
        "get_symbols_info",
        "UpbitRestAPI",
        "UpbitWebSocketReceiver",
        "UpbitWebSocketTrader",
    ):
        assert hasattr(mod, name), f"trade.restapi_upbit에서 {name} 미노출"


def test_mock_ls_balance_response_shape() -> None:
    """C1 mock: LS 잔고 응답이 V3 trade 코드가 기대하는 형태다."""
    api = MockLsAPI()
    resp = api.get_balance()
    assert isinstance(resp, dict)
    assert resp.get("rsp_cd") == "00000"
    assert "t0424OutBlock1" in resp
    assert isinstance(resp["t0424OutBlock1"], list)
    assert "expcode" in resp["t0424OutBlock1"][0]
    assert api.calls == [("get_balance", (), {})]


def test_mock_binance_account_response_shape() -> None:
    """C2 mock: 바이낸스 account 응답이 balances 배열을 가진다."""
    api = MockBinanceAPI()
    resp = api.get_account()
    assert isinstance(resp, dict)
    assert "balances" in resp
    assert any(b["asset"] == "USDT" for b in resp["balances"])


def test_mock_upbit_account_response_shape() -> None:
    """C3 mock: 업비트 account 응답이 currency/balance/locked 키를 가진다."""
    api = MockUpbitAPI()
    resp = api.get_balances()
    assert isinstance(resp, list)
    assert all({"currency", "balance", "locked"} <= set(item.keys()) for item in resp)


def test_real_exchange_api_disclaimer_present() -> None:
    """본 파일이 실 자격증명·실 자금 검증을 사용자에게 위임한다는 disclaimer를 가진다."""
    import inspect

    src = inspect.getsource(__import__(__name__, fromlist=["x"]))
    for marker in ("자격증명", "실 자금", "사용자가 직접 검증"):
        assert marker in src, f"disclaimer marker 누락: {marker}"
