import pytest

from ai_strategy_loop.revision.execution_contract import (
    AUTHORITY,
    check_runtime_symbols,
    evaluate_execution_contract,
)


OLD_G2 = """\
매수 = True
if not (현재가 < VI아래5호가):
    매수 = False
if 매수:
    self.Buy()
"""

FIXED_G2 = """\
VI아래5호가 = VI가격 - VI호가단위 * 5
매수 = True
if not (현재가 < VI아래5호가):
    매수 = False
if 매수:
    self.Buy()
"""


def test_runtime_symbol_check_reproduces_old_g2_name_error():
    result = check_runtime_symbols(OLD_G2)
    assert result.ok is False
    assert result.undefined == ("VI아래5호가",)


def test_runtime_symbol_check_accepts_prior_derived_assignment():
    result = check_runtime_symbols(FIXED_G2)
    assert result.ok is True
    assert "VI아래5호가" in result.assigned


def test_execution_contract_accepts_fixed_source_without_adoption_authority():
    result = evaluate_execution_contract(FIXED_G2)
    assert result.ok is True
    assert result.reasons == ()
    assert result.authority == AUTHORITY
    assert result.can_adopt is False


def test_execution_contract_rejects_unknown_function():
    source = "매수 = True\nif 매수:\n    dangerous()\n"
    result = evaluate_execution_contract(source)
    assert result.ok is False
    assert "disallowed_function" in result.reasons
    assert "undefined_runtime_symbol" in result.reasons


def test_execution_contract_rejects_work_over_budget():
    result = evaluate_execution_contract(FIXED_G2, max_estimated_work=0)
    assert result.ok is False
    assert "estimated_work_exceeded" in result.reasons


def test_runtime_symbol_check_rejects_assignment_after_use():
    source = "매수 = 조건\n조건 = True\n"
    result = check_runtime_symbols(source, allowed_symbols=())
    assert result.ok is False
    assert result.undefined == ("조건",)


def test_runtime_symbol_check_rejects_invalid_python():
    with pytest.raises(SyntaxError):
        check_runtime_symbols("if 조건\n    pass")
