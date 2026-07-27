"""strategy_preflight — 조건식 사전 검증기(결함 A/B fail-fast 게이트) 단위 테스트.

2026-07-28 실측 재현 케이스를 고정한다:
  - 결함 A: elelif 구문 오류 → 종전 엔진 600초 정지, 이제 preflight 가 즉시 잡는다.
  - 결함 B: SSOT 밖·할당 없는 미정의 변수(`강제청산`) → NameError 무한 정지의 원인.
"""

from __future__ import annotations

import sqlite3

from ai_strategy_loop.controller.strategy_preflight import (
    PreflightResult,
    load_loop_strategy_code,
    preflight_pair,
    validate_strategy_code,
)

_SSOT = {"관심종목", "현재가", "수익률", "보유시간", "시분초", "체결강도", "등락율"}


def test_clean_code_passes():
    code = (
        "매수 = True\n"
        "if not (관심종목 == 1):\n"
        "    매수 = False\n"
        "elif not (체결강도 >= 120):\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )
    result = validate_strategy_code(code, ssot=_SSOT)
    assert result.ok, result.reason


def test_syntax_error_fails_fast_defect_a():
    # 실측 결함 A 재현: 'elif' 가 'elelif' 로 깨진 코드는 구문 단계에서 즉시 탈락해야 한다.
    code = (
        "매수 = True\n"
        "if not (관심종목 == 1):\n"
        "    매수 = False\n"
        "elelif not (체결강도 >= 120):\n"
        "    매수 = False\n"
    )
    result = validate_strategy_code(code, ssot=_SSOT)
    assert not result.ok
    assert result.issues[0].kind == "syntax"


def test_undefined_variable_fails_fast_defect_b():
    # 실측 결함 B 재현: CSS_V7 매도식의 `강제청산` — SSOT 밖 + 로컬 할당 없음.
    code = (
        "매도 = False\n"
        "if 강제청산 == 1:\n"
        "    매도 = True\n"
        "if 매도:\n"
        "    self.Sell()\n"
    )
    result = validate_strategy_code(code, ssot=_SSOT)
    assert not result.ok
    assert result.issues[0].kind == "undefined"
    assert "강제청산" in result.issues[0].detail


def test_locally_assigned_derived_variable_is_not_flagged():
    # 파생 지표(로컬 할당)는 SSOT 밖이어도 정상이다 — Min_B_Study/anchor 계열 관례.
    code = (
        "전일종가 = 현재가 / (1 + (등락율 / 100))\n"
        "매수 = True\n"
        "if not (전일종가 > 0):\n"
        "    매수 = False\n"
        "if 매수:\n"
        "    self.Buy()\n"
    )
    result = validate_strategy_code(code, ssot=_SSOT)
    assert result.ok, result.reason


def test_empty_vocab_does_not_false_positive():
    # SSOT 로드 실패(빈 집합) 시 미정의 검사는 침묵해야 한다(구문 검사만 유지 — 오탐 방지).
    code = "매수 = True\nif 아무변수 > 0:\n    매수 = False\n"
    result = validate_strategy_code(code, ssot=set())
    assert result.ok


def test_preflight_pair_reports_missing_strategy(tmp_path):
    db = tmp_path / "loop_strategies.db"
    con = sqlite3.connect(db)
    con.execute('CREATE TABLE stockbuy ("index" TEXT, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
    con.execute('INSERT INTO stockbuy VALUES (?, ?)', ("B_ok", "매수 = True\nif 매수:\n    self.Buy()\n"))
    con.commit(); con.close()

    result = preflight_pair("B_ok", "S_missing", db_path=db)
    assert not result.ok
    assert "S_missing" in result.reason

    assert load_loop_strategy_code("buy", "B_ok", db_path=db) is not None
    assert load_loop_strategy_code("sell", "S_missing", db_path=db) is None


def test_result_reason_is_human_readable():
    result = PreflightResult(False, [])
    assert isinstance(result.reason, str)
