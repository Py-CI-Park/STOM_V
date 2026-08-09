# -*- coding: utf-8 -*-
"""페이지 33 API 계약 테스트.

계약:
  1. `strategy.db` 는 **읽기 전용**으로만 연다 — 화면이 조건식을 고칠 수 없다.
  2. 표에 없는 테이블은 읽지 않는다(임의 테이블 조회 통로를 만들지 않는다).
  3. 목록은 우리 이름공간 + 챔피언만 — 남의 자산 4,000건을 화면에 쏟지 않는다.
  4. 없는 조건식은 없다고 답한다. 조용히 빈 비교를 내지 않는다.
  5. 판독 규칙은 항상 실려 나간다.
"""
from __future__ import annotations

import inspect

import pytest

from ai_strategy_loop.dashboard import condition_diff_api as api

LEFT = "매수 = True\nif not (회전율 > 2):\n    매수 = False\n"
RIGHT = "매수 = True\n# if not (회전율 > 2):\n# 매수 = False\n"


@pytest.fixture()
def stubbed(monkeypatch):
    store = {("buy", "A"): LEFT, ("buy", "B"): RIGHT}
    monkeypatch.setattr(api, "_names", lambda kind: ["A", "B"])
    monkeypatch.setattr(api, "_code", lambda kind, name: store.get((kind, name)))
    return store


# ---------------------------------------------------------------------------
# 안전
# ---------------------------------------------------------------------------

def test_database_is_opened_read_only():
    """★ 화면이 조건식을 고칠 수 있으면 안 된다."""
    assert "mode=ro" in inspect.getsource(api._connect)


def test_only_whitelisted_tables_are_reachable():
    """임의 테이블 조회 통로를 만들지 않는다."""
    assert set(api._TABLES) == {"buy", "sell"}
    assert api.condition_names("stockvars")["available"] is False
    assert api.condition_diff(kind="'; DROP TABLE x --")["available"] is False


def test_listing_is_scoped_to_our_namespace():
    """남의 자산 수천 건을 화면에 쏟지 않는다."""
    for kind, keep in api._PREFIXES.items():
        assert keep, kind
        assert any(p.startswith(("W", "Tick", "C_T")) for p in keep)


# ---------------------------------------------------------------------------
# 비교
# ---------------------------------------------------------------------------

def test_missing_side_is_reported(stubbed):
    payload = api.condition_diff(kind="buy", left="A", right="")
    assert payload["available"] is False and "left" in payload["reason"]
    assert payload["names"] == ["A", "B"]


def test_unknown_name_is_reported_with_the_list(stubbed):
    payload = api.condition_diff(kind="buy", left="A", right="없는것")
    assert payload["available"] is False
    assert "없는것" in payload["reason"]
    assert payload["names"] == ["A", "B"]


def test_diff_carries_both_layers(stubbed):
    payload = api.condition_diff(kind="buy", left="A", right="B")
    assert payload["available"] is True
    assert payload["changed_lines"] > 0
    assert "clause_delta" in payload and "diff" in payload
    assert payload["label"] == "매수식"


def test_context_is_clamped(stubbed):
    """문맥을 무한정 키워 파일 전체를 뿌리지 않는다."""
    wide = api.condition_diff(kind="buy", left="A", right="B", context=9999)
    narrow = api.condition_diff(kind="buy", left="A", right="B", context=-5)
    assert wide["available"] and narrow["available"]


def test_reading_rules_and_clause_legend_ship(stubbed):
    payload = api.condition_diff(kind="buy", left="A", right="B")
    assert any("절 층" in r for r in payload["reading_rules"])
    assert any("실행하지 않습니다" in r for r in payload["reading_rules"])
    assert payload["known_clauses"]


def test_names_endpoint_lists_kinds(stubbed):
    payload = api.condition_names("buy")
    assert payload["available"] is True
    assert payload["kinds"] == {"buy": "매수식", "sell": "매도식"}
