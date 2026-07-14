"""T2.3 절 단위 ablation 엔진 단위 테스트 (네트워크 없음, 합성 거래행만).

검증:
  - parse_top_level_clauses: 플래그 패턴(단일 경로 → and 평탄화 / 다중 경로 → or),
    직접 게이트(if ...: self.Buy), 단일 식, or 그룹 단일 절, 연쇄비교 단일 절,
    파생변수 표시, 파싱 불가 → 빈 목록(무예외).
  - evaluate_clause_pass_rates: 통과율 수기 검증, 거래행에 없는 변수 →
    'not_evaluable' 정직 라벨(missing/derived 사유), 결측·평가오류 행 제외,
    안전 내장(abs) 허용, 화이트리스트 밖 구문 거부.
  - ablate: 절별 delta_trades_if_removed(유일 차단/기여) 근사, 자카드 중복도,
    verdict(ineffective/harmful/binding/not_evaluable), status 코드(무예외),
    수익률 부재 폴백. 재백테스트가 아닌 행 기반 근사임이 계약.
  - to_mutation_axis_suggestions: harmful 우선 정렬, 절 텍스트+근거 수치 포함,
    binding/not_evaluable 제외.
  - 결정론: 동일 입력 → to_dict/제안 JSON byte-동일.
"""

import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.ablation import (  # noqa: E402
    ABLATION_CARD_SECTION_SCHEMA_V3,
    ABLATION_NONCAUSAL_NOTE,
    ABLATION_STATUS_EMPTY_TRADES,
    ABLATION_STATUS_NO_CLAUSES,
    ABLATION_STATUS_OK,
    EVAL_STATUS_NOT_EVALUABLE,
    EVAL_STATUS_OK,
    SOURCE_EXPRESSION,
    SOURCE_FLAG_PATH,
    SOURCE_GUARD_IF,
    VERDICT_BINDING,
    VERDICT_HARMFUL,
    VERDICT_INEFFECTIVE,
    VERDICT_NOT_EVALUABLE,
    ablate,
    evaluate_clause_pass_rates,
    parse_top_level_clauses,
    to_card_section_v3,
    to_mutation_axis_suggestions,
)


# 정찰에서 확인한 실형태를 단순화한 매수식(플래그 패턴 + 중첩 if + 파생변수 + or 그룹).
BUY_CODE = """
매수 = False

if 데이터길이 >= 90 and 90000 <= 시분초 < 93000:
    박스상단 = 최고현재가(30, 1)
    박스폭율 = ((박스상단 - 현재가) / 현재가) * 100

    if 1000 <= 현재가 <= 100000 and (등락율 >= 2 or 체결강도 >= 120):
        if 박스폭율 <= 1.2 and 매수총잔량 > 매도총잔량:
            매수 = True

if 매수:
    self.Buy(종목코드, 종목명, 매수수량, 현재가)
"""

# 실형태 매도식 축소판: if/elif 다중 경로(각 경로가 or-절 하나).
SELL_CODE = """
매도 = False

if 등락율 >= 25:
    매도 = True
elif 체결강도 <= 80:
    매도 = True

if 매도:
    self.Sell(종목코드, 종목명, 매도수량, 현재가)
"""


def _and_df():
    """and 절 ablation 수기 검증용 거래행(진입 스냅샷 B_* + 수익률)."""
    return pd.DataFrame({
        "B_체결강도": [120, 100, 105, 130, 90, 140],
        "B_등락율": [10, 10, 10, 25, 30, 5],
        "B_현재가": [500, 500, 500, 500, 500, 500],
        "수익률": [2.0, 1.5, 0.5, -1.0, -2.0, 1.0],
    })


def _and_clauses():
    clauses = parse_top_level_clauses("체결강도 >= 110 and 등락율 <= 20 and 현재가 > 0")
    assert len(clauses) == 3
    return clauses


# ---------------------------------------------------------------------------
# parse_top_level_clauses
# ---------------------------------------------------------------------------

def test_parse_buy_flag_pattern_flattens_nested_and():
    clauses = parse_top_level_clauses(BUY_CODE)
    texts = [c.text for c in clauses]
    assert texts == [
        "데이터길이 >= 90",
        "90000 <= 시분초 < 93000",          # 연쇄비교는 절 하나.
        "1000 <= 현재가 <= 100000",
        "등락율 >= 2 or 체결강도 >= 120",     # or 그룹은 절 하나.
        "박스폭율 <= 1.2",
        "매수총잔량 > 매도총잔량",
    ]
    assert all(c.combinator == "and" for c in clauses)
    assert all(c.source == SOURCE_FLAG_PATH for c in clauses)
    assert [c.index for c in clauses] == [0, 1, 2, 3, 4, 5]


def test_parse_marks_derived_variables():
    clauses = parse_top_level_clauses(BUY_CODE)
    by_text = {c.text: c for c in clauses}
    # 박스폭율은 조건식 내부 대입으로 만들어진 파생변수.
    assert by_text["박스폭율 <= 1.2"].derived_variables == ("박스폭율",)
    # 원시 진입변수 절은 파생 표시가 없어야 한다.
    assert by_text["매수총잔량 > 매도총잔량"].derived_variables == ()
    assert "시분초" in by_text["90000 <= 시분초 < 93000"].variables


def test_parse_sell_multi_path_becomes_or_clauses():
    clauses = parse_top_level_clauses(SELL_CODE)
    assert [c.text for c in clauses] == ["등락율 >= 25", "체결강도 <= 80"]
    assert all(c.combinator == "or" for c in clauses)


def test_parse_nested_or_path_joins_tests_with_and():
    code = (
        "매도 = False\n"
        "if 수익률 <= -2.0:\n"
        "    매도 = True\n"
        "elif 데이터길이 >= 30:\n"
        "    이탈 = 현재가 < 매수가 * 0.99\n"
        "    if 이탈 and 체결강도 <= 90:\n"
        "        매도 = True\n"
        "if 매도:\n"
        "    self.Sell(종목코드)\n"
    )
    clauses = parse_top_level_clauses(code)
    assert len(clauses) == 2
    assert clauses[0].text == "수익률 <= -2.0"
    # 중첩 경로는 경로상 테스트를 and 로 결합한 절 하나.
    assert "데이터길이 >= 30" in clauses[1].text
    assert "체결강도 <= 90" in clauses[1].text
    assert clauses[1].combinator == "or"
    assert "이탈" in clauses[1].derived_variables


def test_parse_guard_if_and_single_expression_forms():
    guard = parse_top_level_clauses(
        "if 체결강도 >= 110 and 등락율 <= 20:\n    self.Buy(종목코드, 현재가)\n")
    assert [c.text for c in guard] == ["체결강도 >= 110", "등락율 <= 20"]
    assert all(c.source == SOURCE_GUARD_IF for c in guard)

    expr = parse_top_level_clauses("체결강도 >= 110 and (등락율 >= 2 or 등락율 <= -2)")
    assert len(expr) == 2
    assert expr[1].text == "등락율 >= 2 or 등락율 <= -2"
    assert all(c.source == SOURCE_EXPRESSION for c in expr)


def test_parse_invalid_or_gateless_code_returns_empty_without_raising():
    assert parse_top_level_clauses("if 체결강도 >(:") == []      # SyntaxError.
    assert parse_top_level_clauses("x = 1\ny = 2") == []          # 게이트 없음.
    assert parse_top_level_clauses("") == []
    # 플래그는 있으나 True 경로가 없는 코드.
    assert parse_top_level_clauses(
        "매수 = False\nif 매수:\n    self.Buy(종목코드)\n") == []


def test_parse_real_v7_conditions_file():
    path = os.path.join(PROJECT_ROOT, "ai_strategy_loop", "brain", "data",
                        "chart_sulsa_v7_conditions.json")
    if not os.path.exists(path):
        pytest.skip("v7 조건 데이터 파일 없음")
    with open(path, encoding="utf-8") as f:
        conditions = json.load(f)["conditions"]
    buy = next(c for c in conditions if c["side"] == "buy")
    sell = next(c for c in conditions if c["side"] == "sell")

    buy_clauses = parse_top_level_clauses(buy["code"])
    assert len(buy_clauses) >= 10
    assert all(c.combinator == "and" for c in buy_clauses)
    # 연쇄비교가 절 하나로 유지되는지(실코드의 시분초 창).
    assert any("시분초" in c.text and c.text.count("<") >= 2 for c in buy_clauses)

    sell_clauses = parse_top_level_clauses(sell["code"])
    assert len(sell_clauses) >= 5
    assert all(c.combinator == "or" for c in sell_clauses)


# ---------------------------------------------------------------------------
# evaluate_clause_pass_rates
# ---------------------------------------------------------------------------

def test_pass_rate_hand_computed():
    evals = evaluate_clause_pass_rates(_and_clauses(), _and_df())
    assert [e.status for e in evals] == [EVAL_STATUS_OK] * 3
    assert evals[0].pass_rate == 0.5          # 체결강도>=110: {120,130,140} 3/6.
    assert evals[1].pass_rate == 0.666667     # 등락율<=20: 4/6.
    assert evals[2].pass_rate == 1.0          # 현재가>0: 전부.
    assert evals[0].evaluated_rows == 6 and evals[0].passed_rows == 3
    assert evals[0].skipped_rows == 0


def test_chained_comparison_evaluates_as_single_clause():
    clauses = parse_top_level_clauses("90000 <= 시분초 < 93000")
    df = pd.DataFrame({"B_시분초": [91000, 94000]})
    evals = evaluate_clause_pass_rates(clauses, df)
    assert evals[0].status == EVAL_STATUS_OK
    assert evals[0].pass_rate == 0.5


def test_missing_variable_is_honest_not_evaluable():
    clauses = parse_top_level_clauses(BUY_CODE)
    df = pd.DataFrame({
        "B_시분초": [91000], "B_현재가": [5000], "B_등락율": [5],
        "B_체결강도": [130], "B_매수총잔량": [100], "B_매도총잔량": [50],
    })
    evals = {e.clause_text: e for e in evaluate_clause_pass_rates(clauses, df)}
    # 데이터길이: 런타임 전용 변수 — 거래행에 없음 → 추측 없이 정직 라벨.
    e0 = evals["데이터길이 >= 90"]
    assert e0.status == EVAL_STATUS_NOT_EVALUABLE
    assert "데이터길이" in e0.missing_variables
    assert e0.pass_rate is None
    # 박스폭율: 파생변수 — 사유에 derived 명시.
    e4 = evals["박스폭율 <= 1.2"]
    assert e4.status == EVAL_STATUS_NOT_EVALUABLE
    assert "derived=박스폭율" in e4.reason
    # 원시 진입변수 절은 정상 평가.
    assert evals["매수총잔량 > 매도총잔량"].status == EVAL_STATUS_OK
    assert evals["매수총잔량 > 매도총잔량"].pass_rate == 1.0


def test_stom_function_call_clause_not_evaluable():
    clauses = parse_top_level_clauses("최고현재가(30, 1) < 현재가")
    df = pd.DataFrame({"B_현재가": [5000]})
    evals = evaluate_clause_pass_rates(clauses, df)
    assert evals[0].status == EVAL_STATUS_NOT_EVALUABLE
    assert "최고현재가" in evals[0].missing_variables


def test_unsupported_syntax_rejected_even_if_variable_exists():
    clauses = parse_top_level_clauses("체결강도[0] >= 110")
    df = pd.DataFrame({"B_체결강도": [120]})
    evals = evaluate_clause_pass_rates(clauses, df)
    assert evals[0].status == EVAL_STATUS_NOT_EVALUABLE
    assert evals[0].reason.startswith("unsupported_syntax:")


def test_nan_and_eval_error_rows_are_skipped_not_guessed():
    nan_clauses = parse_top_level_clauses("체결강도 >= 110")
    nan_df = pd.DataFrame({"B_체결강도": [120.0, None, 100.0]})
    e = evaluate_clause_pass_rates(nan_clauses, nan_df)[0]
    assert (e.evaluated_rows, e.passed_rows, e.skipped_rows) == (2, 1, 1)
    assert e.pass_rate == 0.5

    div_clauses = parse_top_level_clauses("당일거래대금 / 시가총액 > 0.5")
    div_df = pd.DataFrame({
        "B_당일거래대금": [100, 300, 300],
        "B_시가총액": [200, 0, 200],       # 0 나눗셈 행은 제외.
    })
    e = evaluate_clause_pass_rates(div_clauses, div_df)[0]
    assert (e.evaluated_rows, e.passed_rows, e.skipped_rows) == (2, 1, 1)

    # 0행(컬럼만 있는) 프레임 — 무예외, pass_rate=None.
    empty = evaluate_clause_pass_rates(
        nan_clauses, pd.DataFrame({"B_체결강도": []}))
    assert empty[0].status == EVAL_STATUS_OK
    assert empty[0].pass_rate is None and empty[0].evaluated_rows == 0


def test_safe_builtin_call_allowed():
    clauses = parse_top_level_clauses("abs(등락율) <= 25")
    df = pd.DataFrame({"B_등락율": [-10, 30]})
    e = evaluate_clause_pass_rates(clauses, df)[0]
    assert e.status == EVAL_STATUS_OK
    assert e.pass_rate == 0.5


# ---------------------------------------------------------------------------
# ablate
# ---------------------------------------------------------------------------

def test_ablate_and_clauses_harmful_binding_ineffective():
    result = ablate(_and_clauses(), _and_df())
    assert result.status == ABLATION_STATUS_OK
    assert result.trade_count == 6
    assert result.evaluable_clause_count == 3
    a, b, c = result.items

    # A(체결강도>=110): 단독 차단 r1,r2(수익률 +1.5, +0.5) → harmful.
    assert a.pass_rate == 0.5
    assert a.delta_trades_if_removed == 2
    assert a.blocked_avg_return == 1.0
    assert a.verdict == VERDICT_HARMFUL

    # B(등락율<=20): 단독 차단 r3(수익률 -1.0) → binding(손실 차단 정상 작동).
    assert b.delta_trades_if_removed == 1
    assert b.blocked_avg_return == -1.0
    assert b.verdict == VERDICT_BINDING

    # C(현재가>0): 전 행 통과, 단독 차단 0건 → ineffective.
    assert c.pass_rate == 1.0
    assert c.delta_trades_if_removed == 0
    assert c.verdict == VERDICT_INEFFECTIVE

    # 자카드 중복도 수기 검증: A-C=3/6, B-C=4/6 → 파트너는 C.
    assert a.redundancy == 0.5 and a.redundancy_partner == "현재가 > 0"
    assert b.redundancy == 0.666667 and b.redundancy_partner == "현재가 > 0"
    assert c.redundancy == 0.666667 and c.redundancy_partner == "등락율 <= 20"


def test_ablate_identical_clauses_full_redundancy():
    clauses = parse_top_level_clauses("체결강도 >= 110 and 체결강도 >= 110")
    result = ablate(clauses, _and_df())
    first, second = result.items
    # 동일 절: 서로가 서로를 완전 대체 → 단독 차단 0건 + 자카드 1.0.
    assert first.redundancy == 1.0 and second.redundancy == 1.0
    assert first.delta_trades_if_removed == 0
    assert first.verdict == VERDICT_INEFFECTIVE


def test_ablate_or_clauses_unique_contribution():
    clauses = parse_top_level_clauses(SELL_CODE)
    df = pd.DataFrame({
        "B_등락율": [30, 10, 30, 10],
        "B_체결강도": [100, 70, 70, 100],
        "수익률": [1.0, -1.0, 0.5, 2.0],
    })
    result = ablate(clauses, df)
    c0, c1 = result.items
    # c0(등락율>=25): 단독 기여 r0(+1.0) → 제거 시 상실(delta -1) → binding.
    assert c0.pass_rate == 0.5
    assert c0.delta_trades_if_removed == -1
    assert c0.blocked_avg_return == 1.0
    assert c0.verdict == VERDICT_BINDING
    # c1(체결강도<=80): 단독 기여 r1(-1.0) → 손실 유입 → harmful.
    assert c1.delta_trades_if_removed == -1
    assert c1.blocked_avg_return == -1.0
    assert c1.verdict == VERDICT_HARMFUL
    # 자카드: 교집합 {r2}, 합집합 {r0,r1,r2} → 1/3.
    assert c0.redundancy == 0.333333


def test_ablate_status_codes_without_raising():
    clauses = _and_clauses()
    empty = ablate(clauses, pd.DataFrame())
    assert empty.status == ABLATION_STATUS_EMPTY_TRADES
    assert all(it.verdict == VERDICT_NOT_EVALUABLE for it in empty.items)
    assert all(it.note == "empty_trades" for it in empty.items)

    none_df = ablate(clauses, None)
    assert none_df.status == ABLATION_STATUS_EMPTY_TRADES

    no_clauses = ablate([], _and_df())
    assert no_clauses.status == ABLATION_STATUS_NO_CLAUSES
    assert no_clauses.items == ()


def test_ablate_mixed_not_evaluable_kept_honest():
    clauses = parse_top_level_clauses("데이터길이 >= 90 and 체결강도 >= 110")
    result = ablate(clauses, _and_df())
    assert result.status == ABLATION_STATUS_OK
    assert result.evaluable_clause_count == 1
    ne, ok = result.items
    assert ne.verdict == VERDICT_NOT_EVALUABLE
    assert "데이터길이" in ne.note                     # 사유 보존.
    assert ok.status == EVAL_STATUS_OK
    # 평가가능 절이 하나뿐 → 파트너 없음, 단독 차단 = 자기 실패 행 전부(3건).
    assert ok.redundancy is None and ok.redundancy_partner is None
    assert ok.delta_trades_if_removed == 3


def test_ablate_without_return_column_falls_back_to_binding():
    df = _and_df().drop(columns=["수익률"])
    result = ablate(_and_clauses(), df)
    a, _, c = result.items
    # 수익률 없이는 harmful 판별 불가 — binding 폴백 + 사유 명시(추측 금지).
    assert a.verdict == VERDICT_BINDING
    assert a.blocked_avg_return is None
    assert "수익률 부재" in a.note
    assert c.verdict == VERDICT_INEFFECTIVE


# ---------------------------------------------------------------------------
# to_mutation_axis_suggestions
# ---------------------------------------------------------------------------

def test_suggestions_harmful_first_with_evidence_numbers():
    result = ablate(_and_clauses(), _and_df())
    suggestions = to_mutation_axis_suggestions(result)
    # harmful(A) → plain ineffective(C). binding(B)은 제외.
    assert len(suggestions) == 2
    first, second = suggestions
    assert first["verdict"] == VERDICT_HARMFUL
    assert "체결강도 >= 110" in first["mutation_axis"]
    assert "2건" in first["evidence"]                 # 근거 수치(단독 차단 행수).
    assert "1" in first["evidence"]                   # 평균 수익률 1.0.
    assert "재백테스트" in first["risk_note"]          # 행 기반 근사 경고.
    assert second["verdict"] == VERDICT_INEFFECTIVE
    assert second["clause_text"] == "현재가 > 0"
    # 제안에 binding 절이 섞이지 않는다.
    assert all("등락율 <= 20" != s["clause_text"] for s in suggestions)


def test_suggestions_redundant_clause_names_partner():
    clauses = parse_top_level_clauses("체결강도 >= 110 and 체결강도 >= 110")
    suggestions = to_mutation_axis_suggestions(ablate(clauses, _and_df()))
    assert len(suggestions) == 2
    assert suggestions[0]["mutation_axis"].startswith("중복 절 통합/제거")
    assert "자카드" in suggestions[0]["evidence"]
    assert "1" in suggestions[0]["evidence"]


def test_suggestions_or_harmful_axis():
    clauses = parse_top_level_clauses(SELL_CODE)
    df = pd.DataFrame({
        "B_등락율": [30, 10, 30, 10],
        "B_체결강도": [100, 70, 70, 100],
        "수익률": [1.0, -1.0, 0.5, 2.0],
    })
    suggestions = to_mutation_axis_suggestions(ablate(clauses, df))
    harmful = [s for s in suggestions if s["verdict"] == VERDICT_HARMFUL]
    assert len(harmful) == 1
    assert harmful[0]["mutation_axis"].startswith("유해 or-분기")
    assert "체결강도 <= 80" in harmful[0]["mutation_axis"]


# ---------------------------------------------------------------------------
# 결정론
# ---------------------------------------------------------------------------

def test_deterministic_serialization():
    def run():
        clauses = parse_top_level_clauses(BUY_CODE)
        df = pd.DataFrame({
            "B_시분초": [91000, 92000, 94000], "B_현재가": [5000, 200, 3000],
            "B_등락율": [5, 1, 10], "B_체결강도": [130, 100, 90],
            "B_매수총잔량": [100, 10, 80], "B_매도총잔량": [50, 90, 20],
            "수익률": [1.0, -0.5, 0.3],
        })
        result = ablate(clauses, df)
        return (
            json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True),
            json.dumps(to_mutation_axis_suggestions(result),
                       ensure_ascii=False, sort_keys=True),
        )

    assert run() == run()
    # to_dict 는 JSON-안전해야 한다(위 dumps 성공 자체가 검증).


# ---------------------------------------------------------------------------
# DR-05 — ablation.to_card_section_v3: row ablation은 항상 non-causal.
# ---------------------------------------------------------------------------


def test_to_card_section_v3_causal_claim_always_false():
    clauses = parse_top_level_clauses(BUY_CODE)
    df = pd.DataFrame({
        "B_시분초": [91000, 92000, 94000], "B_현재가": [5000, 200, 3000],
        "B_등락율": [5, 1, 10], "B_체결강도": [130, 100, 90],
        "B_매수총잔량": [100, 10, 80], "B_매도총잔량": [50, 90, 20],
        "수익률": [1.0, -0.5, 0.3],
    })
    result = ablate(clauses, df)
    section = to_card_section_v3(result)

    assert section["schema"] == ABLATION_CARD_SECTION_SCHEMA_V3
    assert section["causal_claim"] is False
    assert section["noncausal_note"] == ABLATION_NONCAUSAL_NOTE
    assert section["status"] == result.status
    assert section["items"] == [item.to_dict() for item in result.items]


def test_to_card_section_v3_causal_claim_false_even_for_empty_trades():
    """빈 거래행(status=empty_trades)에서도 causal_claim은 절대 True가 될 수 없다."""
    clauses = parse_top_level_clauses(BUY_CODE)
    result = ablate(clauses, pd.DataFrame())
    section = to_card_section_v3(result)
    assert section["status"] == ABLATION_STATUS_EMPTY_TRADES
    assert section["causal_claim"] is False
