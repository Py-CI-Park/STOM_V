"""Contract tests for cli/condition_fingerprint.py (CL-R04 sub-slice 9a).

Pure-stdlib fingerprinting + B-only ingestion validation + threshold
provenance contract. No DB/network/backtest/provider imports anywhere in
this module or the module under test.
"""

from __future__ import annotations

import dataclasses

import pytest

from cli.condition_fingerprint import (
    FingerprintError,
    ThresholdEstimator,
    ThresholdProvenance,
    ast_fingerprint,
    rowset_fingerprint,
    validate_b_only,
)


# ---------------------------------------------------------------------------
# ast_fingerprint
# ---------------------------------------------------------------------------


def test_ast_fingerprint_ignores_whitespace_and_parens():
    a = ast_fingerprint('체결강도>100', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('  ( 체결강도 > 100 ) ', timeframe='min', methodology_version='v1')
    assert a == b


def test_ast_fingerprint_commutative_and_reorder_matches():
    a = ast_fingerprint('체결강도 > 100 and 등락율 < 5', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('등락율 < 5 and 체결강도 > 100', timeframe='min', methodology_version='v1')
    assert a == b


def test_ast_fingerprint_commutative_or_reorder_matches():
    a = ast_fingerprint('체결강도 > 100 or 등락율 < 5', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('등락율 < 5 or 체결강도 > 100', timeframe='min', methodology_version='v1')
    assert a == b


def test_ast_fingerprint_equivalent_numeric_literal_matches():
    a = ast_fingerprint('체결강도 >= 1.0', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('체결강도 >= 1', timeframe='min', methodology_version='v1')
    assert a == b


def test_ast_fingerprint_different_expression_differs():
    a = ast_fingerprint('체결강도 > 100', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('체결강도 > 101', timeframe='min', methodology_version='v1')
    assert a != b


def test_ast_fingerprint_sensitive_to_timeframe():
    a = ast_fingerprint('체결강도 > 100', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('체결강도 > 100', timeframe='tick', methodology_version='v1')
    assert a != b


def test_ast_fingerprint_sensitive_to_methodology_version():
    a = ast_fingerprint('체결강도 > 100', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('체결강도 > 100', timeframe='min', methodology_version='v2')
    assert a != b


def test_ast_fingerprint_returns_full_sha256_hex():
    value = ast_fingerprint('체결강도 > 100', timeframe='min', methodology_version='v1')
    assert isinstance(value, str)
    assert len(value) == 64
    int(value, 16)  # must be valid hex


@pytest.mark.parametrize(
    'expression',
    [
        '체결강도.strip()',
        'abs(체결강도)',
        '체결강도[0] > 1',
        '체결강도.foo',
        'lambda x: x',
        '[x for x in range(1)]',
    ],
)
def test_ast_fingerprint_rejects_forbidden_nodes(expression):
    with pytest.raises(FingerprintError):
        ast_fingerprint(expression, timeframe='min', methodology_version='v1')


def test_ast_fingerprint_accepts_arithmetic_and_is_commutative_canonical():
    """사칙 BinOp 허용(실전 조건식의 스케일/비율 비교) + 가환 연산 정준화."""
    a = ast_fingerprint('체결강도 + 1 > 100', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('1 + 체결강도 > 100', timeframe='min', methodology_version='v1')
    assert a == b
    # 비가환(sub/div)은 순서가 의미를 가지므로 구분된다.
    c = ast_fingerprint('체결강도 - 1 > 100', timeframe='min', methodology_version='v1')
    d = ast_fingerprint('1 - 체결강도 > 100', timeframe='min', methodology_version='v1')
    assert c != d
    with pytest.raises(FingerprintError):
        ast_fingerprint('체결강도 ** 2 > 100', timeframe='min', methodology_version='v1')


def test_ast_fingerprint_accepts_statement_form_snippet():
    """pack_producer가 발행하는 `if 조건: self.Buy()` 문장형 후보를 수용한다."""
    bare = ast_fingerprint('현재가 > 시가 and 등락율 > 3', timeframe='min', methodology_version='v1')
    stmt = ast_fingerprint(
        'if 현재가 > 시가 and 등락율 > 3:\n    self.Buy()',
        timeframe='min', methodology_version='v1',
    )
    assert bare == stmt
    with pytest.raises(FingerprintError):
        ast_fingerprint('매수 = True', timeframe='min', methodology_version='v1')


def test_ast_fingerprint_rejects_unparseable():
    with pytest.raises(FingerprintError):
        ast_fingerprint('체결강도 >', timeframe='min', methodology_version='v1')



def test_ast_fingerprint_accepts_signed_numeric_literal():
    # regression: unary minus/plus over a numeric constant (e.g. `등락율 < -3`)
    # must fingerprint, not raise FingerprintError.
    value = ast_fingerprint('등락율 < -3', timeframe='min', methodology_version='v1')
    assert isinstance(value, str)
    int(value, 16)


def test_ast_fingerprint_signed_literal_decimal_equivalence():
    a = ast_fingerprint('등락율 < -3', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('등락율 < -3.0', timeframe='min', methodology_version='v1')
    assert a == b


def test_ast_fingerprint_signed_literal_differs_from_unsigned():
    a = ast_fingerprint('등락율 >= -2', timeframe='min', methodology_version='v1')
    b = ast_fingerprint('등락율 >= 2', timeframe='min', methodology_version='v1')
    assert a != b


def test_ast_fingerprint_unary_not_still_works():
    value = ast_fingerprint('not (체결강도 > 100 and 등락율 < 5)', timeframe='min', methodology_version='v1')
    assert isinstance(value, str)
    int(value, 16)


@pytest.mark.parametrize(
    'expression',
    [
        '-체결강도 > 1',
        '-abs(체결강도) > 1',
        '+체결강도 > 1',
    ],
)
def test_ast_fingerprint_rejects_unary_minus_over_non_constant(expression):
    with pytest.raises(FingerprintError):
        ast_fingerprint(expression, timeframe='min', methodology_version='v1')


# ---------------------------------------------------------------------------
# rowset_fingerprint
# ---------------------------------------------------------------------------


def test_rowset_fingerprint_sensitive_to_dataset_and_window_and_rows():
    base = rowset_fingerprint(dataset_sha='a' * 64, window='2026-01', row_keys=['r1', 'r2'])
    diff_dataset = rowset_fingerprint(dataset_sha='b' * 64, window='2026-01', row_keys=['r1', 'r2'])
    diff_window = rowset_fingerprint(dataset_sha='a' * 64, window='2026-02', row_keys=['r1', 'r2'])
    diff_rows = rowset_fingerprint(dataset_sha='a' * 64, window='2026-01', row_keys=['r1', 'r3'])
    assert len({base, diff_dataset, diff_window, diff_rows}) == 4


def test_rowset_fingerprint_stable_under_row_order():
    a = rowset_fingerprint(dataset_sha='a' * 64, window='2026-01', row_keys=['r2', 'r1'])
    b = rowset_fingerprint(dataset_sha='a' * 64, window='2026-01', row_keys=['r1', 'r2'])
    assert a == b


def test_rowset_fingerprint_returns_full_sha256_hex():
    value = rowset_fingerprint(dataset_sha='a' * 64, window='2026-01', row_keys=['r1'])
    assert len(value) == 64
    int(value, 16)


# ---------------------------------------------------------------------------
# validate_b_only
# ---------------------------------------------------------------------------


def test_validate_b_only_passes_approved_expression():
    reasons = validate_b_only('체결강도 > 100', timeframe='min', kind='buy')
    assert reasons == []


def test_validate_b_only_rejects_result_prefix():
    reasons = validate_b_only('R_MFE < 0', timeframe='min', kind='buy')
    assert any(r.startswith('leaky_result_variable:R_MFE') for r in reasons)


def test_validate_b_only_rejects_sell_diagnostic_prefix():
    reasons = validate_b_only('S_보유시간 > 10', timeframe='min', kind='buy')
    assert any(r.startswith('leaky_result_variable:S_') for r in reasons)


def test_validate_b_only_rejects_bare_result_names():
    for expression in ('result > 0', 'R > 0', 'S > 0'):
        reasons = validate_b_only(expression, timeframe='min', kind='buy')
        assert any(r.startswith('leaky_result_variable:') for r in reasons), expression


def test_validate_b_only_rejects_non_approved_variable():
    reasons = validate_b_only('완전히_존재하지않는_변수 > 1', timeframe='min', kind='buy')
    assert any(r.startswith('non_approved_variable:완전히_존재하지않는_변수') for r in reasons)


def test_validate_b_only_rejects_forbidden_call_node():
    reasons = validate_b_only('abs(체결강도) > 1', timeframe='min', kind='buy')
    assert any(r.startswith('forbidden_node:') for r in reasons)


def test_validate_b_only_rejects_unparseable_expression():
    reasons = validate_b_only('체결강도 >', timeframe='min', kind='buy')
    assert 'unparseable_expression' in reasons


# ---------------------------------------------------------------------------
# ThresholdEstimator / ThresholdProvenance
# ---------------------------------------------------------------------------


def _provenance(**overrides):
    kwargs = dict(
        estimator=ThresholdEstimator.QUANTILE,
        parameters={'q': 0.9},
        fit_role='train',
        period='2026-01..2026-03',
        row_count=100,
        row_signature='sig-1',
        dataset_sha='a' * 64,
        fold_id='fold-1',
        source_receipt='receipt-1',
    )
    kwargs.update(overrides)
    return ThresholdProvenance(**kwargs)


def test_threshold_provenance_accepts_valid_train_role():
    provenance = _provenance()
    assert provenance.fit_role == 'train'
    assert provenance.to_dict()['estimator'] == 'quantile'


@pytest.mark.parametrize('fit_role', ['full_baseline', 'oos', 'validation'])
def test_threshold_provenance_rejects_full_baseline_style_roles(fit_role):
    with pytest.raises(ValueError):
        _provenance(fit_role=fit_role)


def test_threshold_provenance_rejects_non_hex_dataset_sha():
    with pytest.raises(ValueError):
        _provenance(dataset_sha='not-hex-' + 'z' * 56)


def test_threshold_provenance_rejects_short_dataset_sha():
    with pytest.raises(ValueError):
        _provenance(dataset_sha='abc123')


def test_threshold_provenance_rejects_nonpositive_row_count():
    with pytest.raises(ValueError):
        _provenance(row_count=0)
    with pytest.raises(ValueError):
        _provenance(row_count=-5)


def test_threshold_provenance_rejects_unknown_estimator():
    with pytest.raises((ValueError, TypeError)):
        _provenance(estimator='quantile')  # must be enum member, not raw str


def test_threshold_provenance_rejects_empty_required_strings():
    for field in ('fit_role', 'period', 'row_signature', 'fold_id', 'source_receipt'):
        with pytest.raises(ValueError):
            _provenance(**{field: ''})


def test_threshold_provenance_is_frozen():
    provenance = _provenance()
    with pytest.raises(dataclasses.FrozenInstanceError):
        provenance.row_count = 200


def test_threshold_provenance_to_dict_roundtrip_shape():
    provenance = _provenance()
    payload = provenance.to_dict()
    assert payload['fit_role'] == 'train'
    assert payload['dataset_sha'] == 'a' * 64
    assert payload['row_count'] == 100
    assert payload['estimator'] == 'quantile'


# ---------------------------------------------------------------------------
# cli/condition_generator.py ingestion integration (CL-R04 9a additive gate)
# ---------------------------------------------------------------------------


def _fingerprint_gate_pack(extra_candidates):
    base_candidates = [
        {
            'hypothesis_id': 'A',
            'lane': 'repair',
            'expression': '체결강도 > 100 and 등락율 < 5',
            'intended_hypothesis': 'conservative repair',
            'mutation_axis': 'entry_strength',
            'expected_effect': 'reduce weak entries',
            'risk_note': 'may reduce trades',
            'parent_buy_id': 'buy-parent',
            'analysis_card_id': 'analysis-1',
            'preserves_parent_structure': True,
        },
        {
            'hypothesis_id': 'B',
            'lane': 'discovery',
            'expression': '거래대금증감 > 1000',
            'intended_hypothesis': 'discover liquidity regime',
            'mutation_axis': 'liquidity_regime',
            'expected_effect': 'find new coverage',
            'risk_note': 'may overtrade liquid names',
            'coverage_bucket_keys': ['liquidity-midday'],
            'novelty': {'coverage_regime': 'midday-liquidity'},
            'novelty_rationale': 'new market segment and feature family',
        },
    ]
    return {
        'schema_version': 1,
        'candidate_pack_id': 'fingerprint-gate-pack',
        'parents': {
            'buy': {'id': 'buy-parent', 'code': 'if 체결강도 > 90:\n    매수 = True'},
            'sell': {'id': 'sell-parent', 'code': 'if 수익률 < -1:\n    매도 = True'},
        },
        'candidates': base_candidates + extra_candidates,
    }


def test_ingestion_flags_and_reordered_semantic_duplicate():
    from cli.condition_generator import validate_multi_hypothesis_candidate_pack

    reordered_duplicate = {
        'hypothesis_id': 'C',
        'lane': 'discovery',
        # Same semantic content as candidate A ('체결강도 > 100 and 등락율 < 5')
        # with AND operands reordered and extra whitespace -- raw-string
        # duplicate detection misses this, AST fingerprinting must not.
        'expression': '  등락율<5   and   체결강도>100  ',
        'intended_hypothesis': 'reordered duplicate of A',
        'mutation_axis': 'entry_strength',
        'expected_effect': 'reduce weak entries',
        'risk_note': 'may reduce trades',
        'coverage_bucket_keys': ['dup'],
        'novelty': {'feature_family': 'dup'},
        'novelty_rationale': 'dup',
    }
    pack = _fingerprint_gate_pack([reordered_duplicate])

    validation = validate_multi_hypothesis_candidate_pack(pack)

    assert validation['valid_candidate_count'] == 2
    assert validation['invalid_candidate_count'] == 1
    invalid = validation['invalid_candidates'][0]
    assert invalid['candidate']['hypothesis_id'] == 'C'
    assert invalid['failure_reasons'] == ['semantic_duplicate_expression']
    # Sanity: the raw-string check alone would NOT have caught this (different text).
    assert reordered_duplicate['expression'] not in {'체결강도 > 100 and 등락율 < 5'}


def test_ingestion_flags_injected_leaky_and_unapproved_variable_candidate():
    from cli.condition_generator import validate_multi_hypothesis_candidate_pack

    leaky_candidate = {
        'hypothesis_id': 'D',
        'lane': 'discovery',
        'expression': 'S_보유시간 > 10',
        'intended_hypothesis': 'injected leaky diagnostic',
        'mutation_axis': 'leak_probe',
        'expected_effect': 'should never validate',
        'risk_note': 'diagnostic leakage probe',
        'coverage_bucket_keys': ['leak-probe'],
        'novelty': {'feature_family': 'leak-probe'},
        'novelty_rationale': 'leak probe',
    }
    pack = _fingerprint_gate_pack([leaky_candidate])

    validation = validate_multi_hypothesis_candidate_pack(pack)

    invalid = validation['invalid_candidates'][0]
    assert invalid['candidate']['hypothesis_id'] == 'D'
    # AST-based leaky-variable guard (stricter than the legacy substring check)
    # fires alongside the pre-existing substring-based leakage guard.
    assert 'leaky_result_variable:S_보유시간' in invalid['failure_reasons']
    assert 'expression_uses_S_diagnostic' in invalid['failure_reasons']


def test_ingestion_flags_forbidden_call_node_candidate():
    from cli.condition_generator import validate_multi_hypothesis_candidate_pack

    forbidden_candidate = {
        'hypothesis_id': 'E',
        'lane': 'discovery',
        'expression': 'abs(체결강도) > 1',
        'intended_hypothesis': 'injected forbidden node',
        'mutation_axis': 'node_probe',
        'expected_effect': 'should never validate',
        'risk_note': 'forbidden-node probe',
        'coverage_bucket_keys': ['node-probe'],
        'novelty': {'feature_family': 'node-probe'},
        'novelty_rationale': 'node probe',
    }
    pack = _fingerprint_gate_pack([forbidden_candidate])

    validation = validate_multi_hypothesis_candidate_pack(pack)

    invalid = validation['invalid_candidates'][0]
    assert invalid['candidate']['hypothesis_id'] == 'E'
    assert 'forbidden_node:Call' in invalid['failure_reasons']


def test_condition_generator_ingestion_has_no_controller_or_provider_imports():
    """The ingestion gate must be a pure function: no controller/provider/backtest wiring.

    This statically proves validate_multi_hypothesis_candidate_pack() cannot
    perform provider/backtest calls -- the module it lives in never imports
    those subsystems.
    """

    import ast as _ast
    import pathlib

    import cli.condition_generator as condition_generator_module

    source = pathlib.Path(condition_generator_module.__file__).read_text(encoding='utf-8')
    tree = _ast.parse(source)

    forbidden_substrings = ('ai_controller', 'research_provider', 'backtest', 'research_loop')
    imported_modules = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, _ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    offending = [m for m in imported_modules if any(token in m for token in forbidden_substrings)]
    assert offending == []
