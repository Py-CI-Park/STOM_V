"""밴드 패러다임 P0 — band_compiler + seed_902_band 단위 테스트 (결정론).

검증:
  - compile_to_code 결정론: 같은 BandStrategy 두 번 컴파일 → 동일.
  - is_off: 전범위 밴드는 미emit, 좁은 밴드는 emit.
  - op enum emission: 각 op 가 올바른 부등식 문자열 생성(수기 검증).
  - 숫자 포맷: 정수 1000 은 1000, 실수 1.0 은 1.0.
  - 수기 BandStrategy → 정확한 기대 코드 문자열.
  - 시드 round-trip(논리): compile_to_code(SEED_902_BUY) 가 validate_strategy /
    check_tokens / check_variable_scope 통과 + 핵심 시드 조건이 출력에 등장.

실DB/백테 미사용: 순수 함수만 검사한다.
"""

import os
import re
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.band_compiler import (  # noqa: E402
    BandSpec,
    BandStrategy,
    FixedFragment,
    McapBlock,
    TimeBranch,
    compile_to_code,
    emit_clause,
    is_off,
)
from ai_strategy_loop.brain.seed_902_band import (  # noqa: E402
    SEED_902_BUY,
    build_seed_902_buy,
)
from ai_strategy_loop.brain.token_check import check_tokens  # noqa: E402
from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402
from cli.strategy import validate_strategy  # noqa: E402


# --------------------------------------------------------------------------
# 결정론
# --------------------------------------------------------------------------
def test_compile_is_deterministic():
    """같은 BandStrategy 를 두 번 컴파일하면 byte-identical."""
    strat = build_seed_902_buy()
    a = compile_to_code(strat)
    b = compile_to_code(strat)
    assert a == b
    # 새 객체로 빌드해도 동일.
    assert compile_to_code(build_seed_902_buy()) == a


def test_seed_singleton_matches_builder():
    """SEED_902_BUY 싱글톤은 build_seed_902_buy() 결과와 동일 컴파일."""
    assert compile_to_code(SEED_902_BUY) == compile_to_code(build_seed_902_buy())


# --------------------------------------------------------------------------
# is_off
# --------------------------------------------------------------------------
def test_is_off_inactive():
    """active=False 밴드는 off."""
    assert is_off(BandSpec("현재가", "lt_le", lo=1000, hi=50000, active=False))


def test_is_off_full_domain_emitted_vs_narrow():
    """전범위 밴드는 off, 좁은 밴드는 on."""
    # 현재가 도메인 (0, 1_000_000). lt 전범위 = hi>=1_000_000.
    assert is_off(BandSpec("현재가", "lt", hi=1_000_000.0))
    assert not is_off(BandSpec("현재가", "lt", hi=50000))
    # gt 전범위 = lo<=0.
    assert is_off(BandSpec("현재가", "gt", lo=0.0))
    assert not is_off(BandSpec("현재가", "gt", lo=1000))
    # between 전범위 양끝 = off.
    assert is_off(BandSpec("등락율", "gt_lt", lo=-30.0, hi=30.0))
    assert not is_off(BandSpec("등락율", "gt_lt", lo=1.0, hi=8.0))


def test_is_off_unknown_var_not_off():
    """도메인에 없는 변수는 (전범위 판정 불가) off 아님."""
    assert not is_off(BandSpec("미지변수", "gt", lo=5))


def test_compile_omits_off_band():
    """off 밴드는 컴파일 출력에서 빠진다."""
    strat = BandStrategy(
        kind="buy",
        timeframe="tick",
        preamble=(),
        preconditions=(
            BandSpec("현재가", "lt_le", lo=1000, hi=50000),       # on
            BandSpec("등락율", "gt_lt", lo=-30.0, hi=30.0, active=True),  # off (전범위)
        ),
        time_branches=(),
        else_false=False,
        call="if 매수:\n    self.Buy()",
    )
    code = compile_to_code(strat)
    assert "현재가 <= 50000" in code
    assert "등락율" not in code  # 전범위라 omit


# --------------------------------------------------------------------------
# op enum emission (수기 검증)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "spec, expected",
    [
        (BandSpec("현재가", "lt_le", lo=1000, hi=50000), "1000 < 현재가 <= 50000"),
        (BandSpec("체결강도", "ge_le", lo=50, hi=300), "체결강도 >= 50 and 체결강도 <= 300"),
        (BandSpec("회전율", "gt", lo=1.5), "회전율 > 1.5"),
        (BandSpec("시가총액", "lt", hi=3000), "시가총액 < 3000"),
        (BandSpec("초당순매수금액", "gt_lt", lo=1, hi=1000), "1 < 초당순매수금액 < 1000"),
        (BandSpec("시가등락율", "between_le", lo=2.0, hi=4.0), "2.0 <= 시가등락율 < 4.0"),
    ],
)
def test_emit_clause_op_enum(spec, expected):
    """각 op 가 올바른 부등식 문자열을 만든다."""
    assert emit_clause(spec) == expected


def test_emit_clause_fixed_fragment_verbatim():
    """FixedFragment 는 code 를 그대로 반환."""
    frag = FixedFragment("당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30")
    assert emit_clause(frag) == "당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30"


# --------------------------------------------------------------------------
# 숫자 포맷 (int vs float)
# --------------------------------------------------------------------------
def test_int_vs_float_formatting():
    """정수 1000 은 1000, 실수 1.0 은 1.0 (시드 리터럴 스타일)."""
    # 정수 경계 → 정수 표기.
    assert emit_clause(BandSpec("현재가", "lt_le", lo=1000, hi=50000)) == \
        "1000 < 현재가 <= 50000"
    # 실수 1.0/8.0 → 소수점 보존.
    assert emit_clause(BandSpec("등락율", "lt_le", lo=1.0, hi=8.0)) == \
        "1.0 < 등락율 <= 8.0"
    # 실수 1.5 → 일반 표기.
    assert emit_clause(BandSpec("회전율", "gt", lo=1.5)) == "회전율 > 1.5"


# --------------------------------------------------------------------------
# 가드 극성 (reject_if)
# --------------------------------------------------------------------------
def test_fixed_fragment_reject_polarity():
    """satisfied 는 'elif <expr>:', not_satisfied 는 'elif not (<expr>):'."""
    strat = BandStrategy(
        kind="buy",
        timeframe="tick",
        preamble=(),
        preconditions=(
            FixedFragment("고저평균대비등락율 > 0"),                       # not_satisfied (기본)
            FixedFragment("라운드피겨위5호가이내", reject_if="satisfied"),  # satisfied
        ),
        time_branches=(),
        else_false=False,
        call="if 매수:\n    self.Buy()",
    )
    code = compile_to_code(strat)
    assert "if not (고저평균대비등락율 > 0):" in code
    assert "elif 라운드피겨위5호가이내:" in code
    assert "elif not (라운드피겨위5호가이내):" not in code


def test_fixed_fragment_invalid_reject_if():
    """알 수 없는 reject_if 는 ValueError."""
    with pytest.raises(ValueError):
        FixedFragment("x > 0", reject_if="maybe")


def test_bandspec_invalid_op():
    """알 수 없는 op 는 ValueError."""
    with pytest.raises(ValueError):
        BandSpec("현재가", "weird_op", lo=1, hi=2)


# --------------------------------------------------------------------------
# 수기 BandStrategy → 정확한 기대 코드
# --------------------------------------------------------------------------
def test_small_handbuilt_exact_code():
    """작은 수기 전략이 정확한 기대 문자열로 컴파일된다."""
    strat = BandStrategy(
        kind="buy",
        timeframe="tick",
        preamble=("VI아래5호가 = VI가격 - VI호가단위 * 5",),
        state_init="매수 = True",
        preconditions=(FixedFragment("관심종목 == 1"),),
        time_branches=(
            TimeBranch(
                cond="시분초 < 90200",
                flat_clauses=(
                    BandSpec("현재가", "lt_le", lo=1000, hi=50000),
                    BandSpec("체결강도", "ge_le", lo=50, hi=300),
                ),
                mcap_block=None,
                branch_kind="elif",
            ),
        ),
        else_false=True,
        call="if 매수:\n    self.Buy()",
    )
    expected = (
        "VI아래5호가 = VI가격 - VI호가단위 * 5\n"
        "매수 = True\n"
        "\n"
        "if not (관심종목 == 1):\n"
        "    매수 = False\n"
        "elif 시분초 < 90200:\n"
        "    if not (1000 < 현재가 <= 50000):\n"
        "        매수 = False\n"
        "    elif not (체결강도 >= 50 and 체결강도 <= 300):\n"
        "        매수 = False\n"
        "else:\n"
        "    매수 = False\n"
        "\n"
        "if 매수:\n"
        "    self.Buy()"
    )
    assert compile_to_code(strat) == expected


def test_mcap_block_nesting_exact():
    """McapBlock 이 if 시가총액 / 내부 체인 / else 매수=False 로 emit."""
    branch = TimeBranch(
        cond="시분초 < 90200",
        flat_clauses=(BandSpec("현재가", "lt_le", lo=1000, hi=50000),),
        mcap_block=McapBlock(
            cap_lt=3000,
            clauses=(BandSpec("체결강도", "ge_le", lo=50, hi=300),),
        ),
        branch_kind="elif",
        inner_time_guard="시분초 < 90200",
        mcap_in_else=False,
    )
    strat = BandStrategy(
        kind="buy", timeframe="tick", preamble=(),
        preconditions=(), time_branches=(branch,), else_false=True,
        call="if 매수:\n    self.Buy()",
    )
    code = compile_to_code(strat)
    assert "    elif 시분초 < 90200:\n        if 시가총액 < 3000:" in code
    assert "            if not (체결강도 >= 50 and 체결강도 <= 300):" in code
    assert "        else:\n            매수 = False" in code


# --------------------------------------------------------------------------
# 시드 round-trip (논리) — P0 핵심 증명
# --------------------------------------------------------------------------
def test_seed_roundtrip_passes_gates():
    """compile_to_code(SEED_902_BUY) 가 validate/token/scope 게이트를 통과한다."""
    code = compile_to_code(SEED_902_BUY)
    # validate_strategy (compile-only 구문 검증).
    assert validate_strategy(code)["status"] == "ok"
    # check_tokens (import/exec/dunder 거부).
    ok_tok, reason = check_tokens(code)
    assert ok_tok, reason
    # check_variable_scope (tick/buy NameError 가드).
    ok_scope, offending = check_variable_scope(code, "tick", "buy")
    assert ok_scope, offending


def test_seed_roundtrip_key_conditions_present():
    """핵심 시드 조건이 컴파일 출력에 그대로 등장한다."""
    code = compile_to_code(SEED_902_BUY)
    for needle in (
        "시분초 < 90200",
        "90200 <= 시분초 < 90500",
        "1.0 < 등락율 <= 8.0",
        "시가총액 < 3000",
        "당일거래대금각도(30) > 5 and 당일거래대금각도(30) < 30",
        "체결강도 >= 50 and 체결강도 <= 300",
        "초당거래대금 > 초당거래대금N(1) * 1.0",
        "누적초당매수수량(30) * 0.5 < 누적초당매도수량(30) * 1.0",
        "if not (관심종목 == 1):",
        "elif 라운드피겨위5호가이내:",
        "if 매수:",
        "self.Buy()",
    ):
        assert needle in code, f"missing: {needle!r}"


def _normalize(text: str) -> list[str]:
    """주석/빈 줄 제거 + 공백 정규화 → 논리 라인 리스트."""
    out = []
    for ln in text.splitlines():
        i = ln.find("#")
        if i != -1:
            ln = ln[:i]
        s = ln.strip()
        if not s:
            continue
        out.append(re.sub(r"\s+", " ", s))
    return out


def test_seed_roundtrip_logic_identical_to_seed_output():
    """정규화 후 컴파일 코드의 조건 논리가 seed_strategy_output.txt BUY 와 동일."""
    code = compile_to_code(SEED_902_BUY)
    seed_path = os.path.join(PROJECT_ROOT, "seed_strategy_output.txt")
    with open(seed_path, encoding="utf-8") as fh:
        seed_full = fh.read().splitlines()
    # BUY 논리 구간: 첫 실행 preamble 라인(전일종가, line 7) ~ self.Buy() (line 131).
    seed_logic = seed_full[6:131]
    assert _normalize(code) == _normalize("\n".join(seed_logic))


def test_seed_roundtrip_compiles_as_python():
    """컴파일 코드가 실제 파이썬으로 compile 된다(구문 무결성)."""
    code = compile_to_code(SEED_902_BUY)
    compile(code, "<seed_band>", "exec")  # SyntaxError 면 실패
