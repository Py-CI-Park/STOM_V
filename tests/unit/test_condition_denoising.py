from __future__ import annotations

import dataclasses

from ai_strategy_loop.revision import condition_ast as C
from ai_strategy_loop.revision import condition_denoising as D


_SOURCE = """\
매수 = True
if not (등락율 >= 1.5):
    매수 = False
elif not (체결강도 >= 100):
    매수 = False
elif not (전일동시간비 > 0):
    매수 = False
elif not (거래대금 >= 500):
    매수 = False
"""


def _ast() -> C.ConditionAst:
    return C.parse_condition_source(_SOURCE)


def test_mask_corruption_is_seed_deterministic_and_receipted() -> None:
    parsed = _ast()

    first = D.mask_one_clause(parsed, seed=17)
    second = D.mask_one_clause(parsed, seed=17)

    assert first.ok, first.reason
    assert second.ok, second.reason
    assert first.source == second.source
    assert first.target == second.target
    assert D.MASK_TOKEN in first.source
    assert first.receipt.config_hash == second.receipt.config_hash
    assert first.receipt.adoption_authority is False
    assert first.receipt.authority_scope == "none"


def test_numeric_perturbation_stays_inside_declared_delta_bound() -> None:
    result = D.perturb_numeric_threshold(
        _ast(),
        max_delta=0.25,
        seed=3,
        clause_index=1,
        literal_index=0,
    )

    assert result.ok, result.reason
    assert result.original_literal == "100"
    assert result.new_literal is not None
    assert result.absolute_delta is not None
    assert 0 < abs(float(result.new_literal) - float(result.original_literal)) <= 0.25
    assert 0 < result.absolute_delta <= 0.25


def test_exact_duplicate_is_removed_against_clean_template() -> None:
    clean = _ast()
    duplicated = D.insert_exact_duplicate(clean, clause_index=2)

    assert duplicated.ok, duplicated.reason
    assert duplicated.ast is not None
    assert duplicated.source.count("전일동시간비") == _SOURCE.count("전일동시간비") + 1

    repaired = D.repair_masked_and_duplicate(duplicated.ast, clean, seed=5)
    assert repaired.ok, repaired.reason
    assert repaired.ast is not None
    summary = D.evaluate_repair(clean, repaired.ast, syntax_valid=True, static_valid=True, seed=5)

    assert [action.kind for action in repaired.actions] == ["duplicate_removed"]
    assert summary.canonical_equal is True
    assert summary.complexity_delta == 0
    assert repaired.receipt.adoption_authority is False


def test_reorder_accepts_only_safe_consecutive_elif_guards() -> None:
    parsed = _ast()

    unsafe_first_pair = D.reorder_independent_consecutive_guards(parsed, first_clause_index=0)
    safe_elif_pair = D.reorder_independent_consecutive_guards(parsed, first_clause_index=1)

    assert not unsafe_first_pair.ok
    assert unsafe_first_pair.reason == "selected_pair_is_not_independent_consecutive_elif_guards"
    assert safe_elif_pair.ok, safe_elif_pair.reason
    assert safe_elif_pair.source.index("전일동시간비") < safe_elif_pair.source.index("체결강도")


def test_masked_clause_repairs_from_clean_template_and_reports_caller_flags() -> None:
    clean = _ast()
    masked = D.mask_one_clause(clean, clause_index=1, seed=11)
    assert masked.ok, masked.reason
    assert masked.ast is not None

    repaired = D.repair_masked_and_duplicate(masked.ast, clean, seed=11)
    assert repaired.ok, repaired.reason
    assert repaired.ast is not None
    summary = D.evaluate_repair(clean, repaired.ast, syntax_valid=True, static_valid=False, seed=11)

    assert [action.kind for action in repaired.actions] == ["mask_replaced"]
    assert D.MASK_TOKEN not in repaired.source
    assert summary.canonical_equal is True
    assert summary.syntax_valid is True
    assert summary.static_valid is False
    assert summary.complexity_delta == 0
    assert summary.receipt.adoption_authority is False


def test_shuffled_template_negative_control_reduces_exact_repair() -> None:
    clean = _ast()
    masked = D.mask_one_clause(clean, clause_index=1, seed=19)
    shuffled = D.shuffled_template_negative_control(clean, seed=19)

    assert masked.ok, masked.reason
    assert masked.ast is not None
    assert shuffled.ok, shuffled.reason
    assert shuffled.ast is not None
    assert shuffled.source != _SOURCE
    assert shuffled.receipt.adoption_authority is False

    repaired = D.repair_masked_and_duplicate(masked.ast, shuffled.ast, seed=19)
    assert repaired.ok, repaired.reason
    assert repaired.ast is not None
    summary = D.evaluate_repair(clean, repaired.ast, syntax_valid=True, static_valid=True, seed=19)

    assert summary.canonical_equal is False


def test_fixed_seed_experiment_compares_clean_and_shuffled_exact_rates() -> None:
    first = D.run_fixed_seed_experiment([_SOURCE], seed=23)
    second = D.run_fixed_seed_experiment([_SOURCE], seed=23)

    assert first == second
    assert first.case_count == 2
    assert first.clean_template_exact_repair_rate == 1.0
    assert first.shuffled_template_exact_repair_rate < first.clean_template_exact_repair_rate
    assert first.receipt.adoption_authority is False


def test_public_payloads_do_not_expose_strategy_outcome_fields() -> None:
    banned = ("pnl", "profit", "sharpe", "drawdown", "mdd", "win_rate", "label", "future", "tick", "backtest")
    public_names = [name for name in dir(D) if not name.startswith("_")]
    payload_field_names = []
    for name in public_names:
        value = getattr(D, name)
        if dataclasses.is_dataclass(value):
            payload_field_names.extend(field.name for field in dataclasses.fields(value))

    lowered = [*map(str.lower, public_names), *map(str.lower, payload_field_names)]
    assert not [name for name in lowered for token in banned if token in name]

    summary = D.run_fixed_seed_experiment([_SOURCE], seed=29)
    assert summary.receipt.adoption_authority is False
    assert summary.receipt.authority_scope == "none"
