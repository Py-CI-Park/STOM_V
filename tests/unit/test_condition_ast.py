from __future__ import annotations

import builtins
import inspect

from ai_strategy_loop.revision import condition_ast as C


_SNIPPET = """\
# 진입 필터
매수 = True

if not (체결강도 >= 체결강도평균(30) + 5):  # 강도 확인
    매수 = False
elif not (현재가 > 현재가N(1)):
    매수 = False
"""


def test_parse_preserves_comments_korean_names_and_roundtrip_source() -> None:
    parsed = C.parse_condition_source(_SNIPPET)

    assert parsed.round_trip_source() == _SNIPPET
    assert parsed.to_dict()["original_source"] == _SNIPPET
    assert [line.kind for line in parsed.lines] == [
        "comment",
        "assignment",
        "blank",
        "clause",
        "assignment",
        "clause",
        "assignment",
    ]
    assert parsed.lines[0].comment == "# 진입 필터"
    assert parsed.lines[3].comment == "# 강도 확인"
    assert parsed.lines[1].target == "매수"
    assert parsed.lines[3].normalized.startswith("not ")
    assert "체결강도평균(30)" in parsed.lines[3].normalized
    assert parsed.complexity.assignment_count == 3
    assert parsed.complexity.clause_count == 2
    assert parsed.complexity.comment_count == 1
    assert parsed.complexity.blank_count == 1
    assert parsed.complexity.unknown_line_count == 0
    assert parsed.authority == C.AUTHORITY
    assert parsed.no_adoption_authority is True
    assert parsed.config_receipt["sha256"]
    assert parsed.seed_receipt["random_used"] is False


def test_extracts_called_functions_and_numeric_lookbacks() -> None:
    parsed = C.parse_condition_source(_SNIPPET)

    assert parsed.called_functions == ("체결강도평균", "현재가N")
    assert [
        (item.function, item.argument_index, item.value, item.line_no)
        for item in parsed.numeric_lookbacks
    ] == [("체결강도평균", 0, 30, 4), ("현재가N", 0, 1, 6)]
    assert parsed.complexity.function_call_count == 2
    assert parsed.complexity.numeric_lookback_count == 2
    assert parsed.complexity.max_numeric_lookback == 30.0


def test_canonical_hash_is_stable_for_whitespace_only_changes() -> None:
    compact = """\
매수=True
if not (체결강도>=체결강도평균(30)+5):
    매수=False
"""
    spaced = """\
매수 = True
if  not ( 체결강도 >= 체결강도평균(30) + 5 ) :
    매수 = False
"""

    compact_ast = C.parse_condition_source(compact)
    spaced_ast = C.parse_condition_source(spaced)

    assert compact_ast.canonical_text == spaced_ast.canonical_text
    assert compact_ast.canonical_sha256 == spaced_ast.canonical_sha256
    assert compact_ast.original_sha256 != spaced_ast.original_sha256


def test_static_check_passes_with_explicit_allowlist_and_diagnostic_work() -> None:
    result = C.static_check_condition_source(
        _SNIPPET,
        allowed_functions={"체결강도평균", "현재가N"},
        max_clauses=2,
        max_lookback=30,
        max_unknown_lines=0,
    )

    assert result.ok is True
    assert result.violations == ()
    assert result.estimated_work == 2.31
    assert result.estimated_work_basis.startswith("diagnostic_only:")
    assert result.authority == C.AUTHORITY
    assert result.no_adoption_authority is True
    assert result.config_receipt["allowed_functions"] == ["체결강도평균", "현재가N"]
    assert result.seed_receipt["seed"] == C.SEED_VALUE


def test_unknown_lines_fail_closed_when_not_explicitly_allowed() -> None:
    source = "매수 = True\n검토 필요\n"

    result = C.static_check_condition_source(
        source,
        allowed_functions=set(),
        max_clauses=1,
        max_lookback=1,
        max_unknown_lines=0,
    )

    assert result.ok is False
    assert result.parsed.lines[1].kind == "unknown"
    assert result.parsed.lines[1].raw == "검토 필요"
    assert {violation.code for violation in result.violations} == {
        "unknown_lines_exceeded"
    }


def test_static_check_reports_disallowed_functions_and_limits() -> None:
    source = """\
if 위험함수(120) > 0:
    매수 = False
elif 현재가N(2) > 0:
    매수 = False
"""

    result = C.static_check_condition_source(
        source,
        allowed_functions={"현재가N"},
        max_clauses=1,
        max_lookback=60,
        max_unknown_lines=0,
    )

    codes = {violation.code for violation in result.violations}
    assert result.ok is False
    assert "disallowed_function" in codes
    assert "clauses_exceeded" in codes
    assert "lookback_exceeded" in codes
    assert result.parsed.called_functions == ("위험함수", "현재가N")


def test_parser_does_not_use_dynamic_execution(monkeypatch) -> None:
    def bomb(*_args, **_kwargs):
        raise AssertionError("dynamic evaluation must not be used")

    monkeypatch.setattr(builtins, "eval", bomb)
    module_source = inspect.getsource(C)

    assert "eval(" not in module_source
    assert "exec(" not in module_source

    source = "__import__('os').system('echo should_not_run')\n"
    parsed = C.parse_condition_source(source)
    result = C.static_check_condition_source(
        parsed,
        allowed_functions=set(),
        max_clauses=0,
        max_lookback=0,
        max_unknown_lines=0,
    )

    assert parsed.lines[0].kind == "unknown"
    assert result.ok is False
    assert "unknown_lines_exceeded" in {item.code for item in result.violations}
