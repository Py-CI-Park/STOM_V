"""US-003 Phase 1b — token_check 가드레일 단위 테스트 (네트워크 없음).

검증:
  - import / exec / eval / open / __class__ 접근이 REJECT.
  - 정상 STOM 매수 스니펫(현재가/체결강도/매수=True/self.Buy)이 PASS.
  - dedup: 기록된 전략의 리터럴-only 변형이 중복으로 플래그.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai_strategy_loop.brain.token_check import (  # noqa: E402
    DedupTracker,
    check_tokens,
    normalized_ast_hash,
)

# 정상 STOM 매수 스니펫 (화이트리스트 변수 + 정규 형태).
VALID_BUY = """\
매수 = True
if not (3 <= 등락율 <= 25):
    매수 = False
elif not (체결강도 >= 100):
    매수 = False
elif not (현재가 > 1000):
    매수 = False

if 매수:
    self.Buy()
"""


def test_import_rejected():
    ok, reason = check_tokens("import os\n매수 = True\nif 매수:\n    self.Buy()\n")
    assert ok is False
    assert "import" in reason


def test_from_import_rejected():
    ok, reason = check_tokens("from os import path\n매수 = True\n")
    assert ok is False
    assert "import" in reason


def test_exec_rejected():
    ok, reason = check_tokens("exec('print(1)')\n매수 = True\n")
    assert ok is False
    assert "exec" in reason


def test_eval_rejected():
    ok, reason = check_tokens("x = eval('1+1')\n매수 = True\n")
    assert ok is False
    assert "eval" in reason


def test_open_rejected():
    ok, reason = check_tokens("f = open('x.txt')\n매수 = True\n")
    assert ok is False
    assert "open" in reason


def test_compile_rejected():
    ok, reason = check_tokens("compile('1', '<s>', 'eval')\n매수 = True\n")
    assert ok is False
    assert "compile" in reason


def test_dunder_attribute_rejected():
    ok, reason = check_tokens("x = (1).__class__\n매수 = True\n")
    assert ok is False
    assert "dunder" in reason or "__class__" in reason


def test_dunder_import_call_rejected():
    ok, reason = check_tokens("m = __import__('os')\n매수 = True\n")
    assert ok is False


def test_getattr_dunder_string_rejected():
    # HIGH-1: getattr(x, "__class__") 우회 — 함수명 + dunder 문자열 둘 다 막힌다.
    ok, reason = check_tokens("x = getattr(현재가, '__class__')\n매수 = True\n")
    assert ok is False


def test_globals_rejected():
    ok, reason = check_tokens("g = globals()\n매수 = True\n")
    assert ok is False
    assert "globals" in reason


def test_setattr_rejected():
    ok, reason = check_tokens("setattr(self, 'x', 1)\n매수 = True\n")
    assert ok is False
    assert "setattr" in reason


def test_breakpoint_rejected():
    ok, reason = check_tokens("breakpoint()\n매수 = True\n")
    assert ok is False
    assert "breakpoint" in reason


def test_vars_rejected():
    ok, reason = check_tokens("v = vars()\n매수 = True\n")
    assert ok is False
    assert "vars" in reason


def test_dunder_string_literal_rejected():
    # 함수가 막혀도 dunder 문자열 리터럴 자체를 어디에 쓰든 거부.
    ok, reason = check_tokens("name = '__class__'\n매수 = True\n")
    assert ok is False


def test_clean_strategy_still_passes_after_hardening():
    # 가드 강화 후에도 정상 스니펫은 통과해야 한다(거짓 양성 방지).
    ok, reason = check_tokens(VALID_BUY)
    assert ok is True, f"강화 후 정상 스니펫이 거부됨: {reason}"


def test_valid_buy_snippet_passes():
    ok, reason = check_tokens(VALID_BUY)
    assert ok is True, f"정상 스니펫이 거부됨: {reason}"
    assert reason == ""


def test_single_underscore_name_allowed():
    # 단일 밑줄 포함 정상 변수명(forbidden.md 주석)은 허용.
    code = "매도 = False\nif 변동성기반_동적청산(60):\n    매도 = True\nif 매도:\n    self.Sell()\n"
    ok, reason = check_tokens(code)
    assert ok is True, f"단일 밑줄 변수명이 거부됨: {reason}"


def test_empty_code_rejected():
    ok, reason = check_tokens("")
    assert ok is False


def test_dedup_flags_literal_only_variant():
    tracker = DedupTracker(k=5)
    tracker.record(VALID_BUY)

    # 리터럴(임계값)만 바꾼 변형 — 구조 동일.
    variant = VALID_BUY.replace("3 <= 등락율 <= 25", "5 <= 등락율 <= 30").replace(
        "체결강도 >= 100", "체결강도 >= 120"
    )
    assert variant != VALID_BUY
    assert tracker.is_duplicate(variant) is True


def test_dedup_distinct_structure_not_flagged():
    tracker = DedupTracker(k=5)
    tracker.record(VALID_BUY)

    different = "매수 = True\nif 현재가 < 500:\n    매수 = False\nif 매수:\n    self.Buy()\n"
    assert tracker.is_duplicate(different) is False


def test_normalized_hash_ignores_literals_and_formatting():
    a = "매수 = True\nif 등락율 >= 3:\n    매수 = False\n"
    # 리터럴 변경 + 공백 변경.
    b = "매수   =   True\nif 등락율 >= 99:\n    매수 = False\n"
    assert normalized_ast_hash(a) == normalized_ast_hash(b)


def test_dedup_k_bound():
    tracker = DedupTracker(k=2)
    s1 = "매수 = True\nif 현재가 < 1:\n    매수 = False\n"
    s2 = "매수 = True\nif 현재가 < 2:\n    매수 = False\n"  # 다른 구조? 리터럴만 → 동일 구조
    # s1, s2는 리터럴만 다르므로 동일 정규화 해시 → k=2여도 같은 한 칸.
    tracker.record(s1)
    s3 = "매수 = True\nif 체결강도 > 1:\n    매수 = False\n"
    s4 = "매도 = False\nif 등락율 > 1:\n    매도 = True\n"
    tracker.record(s3)
    tracker.record(s4)
    # s1과 s3, s4가 들어왔고 maxlen=2이므로 s1은 밀려남.
    assert tracker.is_duplicate(s2) is False  # s1 변형인데 s1이 밀려났으므로 not dup
    assert tracker.is_duplicate(s3) is True
