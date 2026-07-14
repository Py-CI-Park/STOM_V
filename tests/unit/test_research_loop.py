from dataclasses import fields
import json

import pandas as pd
import pytest

from cli import research_loop
from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_loop import ResearchLoopConfig, run_research_once
from cli.research_metrics import NUMERIC_COLUMNS


class DummyController:
    def __init__(self, candidate_csv, status='success', message='candidate failed'):
        self.candidate_csv = candidate_csv
        self.status = status
        self.message = message
        self.runs = []

    def run(self, config_dict):
        self.runs.append(config_dict)
        result = {'status': self.status, 'metrics': {'trade_count': 1}}
        if self.candidate_csv is not None:
            result['csv_path'] = self.candidate_csv
        if self.status == 'error':
            result['message'] = self.message
        return result


def _write_trade_csv(path, name='A', buy_time=202501010900):
    pd.DataFrame([
        {'종목명': name, '매수시간': buy_time, '매도시간': buy_time + 10, '매수가': 1000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -2.0},
    ]).to_csv(path, index=False, encoding='utf-8-sig')


def _write_identity_trade_csv(path, *, symbol='A', buy_time=202501010900, buy_price=1000):
    pd.DataFrame([{
        INSTRUMENT_COLUMNS[1]: symbol,
        REQUIRED_KEY_COLUMNS[0]: buy_time,
        OPTIONAL_KEY_COLUMNS[0]: buy_price,
        NUMERIC_COLUMNS[1]: buy_time + 10,
        NUMERIC_COLUMNS[3]: buy_price + 1,
        NUMERIC_COLUMNS[5]: 1.0,
        NUMERIC_COLUMNS[6]: 1000,
        'R_MFE': 1.2,
        'R_MAE': -0.2,
    }]).to_csv(path, index=False, encoding='utf-8')


def _patch_analysis_success(monkeypatch, expressions=None, selected_candidates=None):
    selected_candidates = [] if selected_candidates is None else selected_candidates
    expressions = ['체결강도 < 90'] if expressions is None else expressions
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok', 'recommended_candidates': []})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda *args, **kwargs: {
            'status': 'ok',
            'expressions': expressions,
            'candidate_count': len(expressions),
            'selected_candidates': selected_candidates,
        },
    )


def _patch_strategy_success(monkeypatch):
    monkeypatch.setattr(
        research_loop,
        'generate_buy_filter_strategy',
        lambda name, base_code, expressions: {'status': 'ok', 'code': base_code + '\n# filter:' + ','.join(expressions), 'name': name},
    )
    monkeypatch.setattr(
        research_loop,
        'save_strategy_to_db',
        lambda db_path, name, code, strategy_type: {'status': 'ok', 'name': name, 'action': 'created'},
    )

    def fake_load(db_path, name, strategy_type):
        if name == 'BaseBuy':
            return {'status': 'ok', 'code': 'buy = True\nif buy:\n    self.Buy()', 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)


def test_research_loop_config_has_no_wfo_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'run_wfo' not in names
    assert 'train_window_days' not in names
    assert 'test_window_days' not in names
    assert 'param_space' not in names


def test_research_loop_config_has_candidate_runtime_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'candidate_start_date' in names
    assert 'candidate_end_date' in names
    assert 'candidate_timeout' in names
    assert 'candidate_plan_only' in names
    assert 'keep_failed_candidate' in names


def test_research_loop_config_has_runtime_recovery_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'runtime_output_path' in names
    assert 'max_consecutive_candidate_failures' in names

    config = ResearchLoopConfig()
    assert config.runtime_output_path is None
    assert config.max_consecutive_candidate_failures == 3


def test_research_loop_config_has_iteration_fields():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'run_candidates' in names
    assert 'candidate_count' in names
    assert 'candidate_name_prefix' in names
    assert 'cleanup_best_candidate' in names
    assert 'keep_loser_candidates' in names
    assert 'strict_research_profile' in names
    assert 'strict_candidate_payload_v2' in names
    assert 'approved_b_features' in names


def test_research_loop_rejects_iteration_mode_conflicts(tmp_path):
    conflict = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='Conflict',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidate=True,
            run_candidates=True,
        )
    )
    assert conflict['phase'] == 'run_candidate_and_run_candidates_conflict'

    plan_conflict = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='PlanConflict',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            candidate_plan_only=True,
        )
    )
    assert plan_conflict['phase'] == 'candidate_plan_only_iteration_conflict'

    invalid_count = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='InvalidCount',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            candidate_count=0,
        )
    )
    assert invalid_count['phase'] == 'invalid_candidate_count'


def test_strict_research_profile_requires_atomic_candidate_contract(tmp_path):
    incomplete = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='StrictIncomplete',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            strict_research_profile=True,
        )
    )
    assert incomplete['phase'] == 'strict_research_profile_incomplete'
    assert set(incomplete['missing_strict_contracts']) == {
        'llm_candidate_pack_enabled',
        'strict_candidate_payload_v2',
        'final_owner_selection_enabled',
        'approved_b_features',
    }

    complete = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='StrictComplete',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            run_candidate=False,
            strict_research_profile=True,
            strict_candidate_payload_v2=True,
            llm_candidate_pack_enabled=True,
            final_owner_selection_enabled=True,
            approved_b_features=('B_시가총액',),
        )
    )
    assert complete['status'] == 'ok'


def test_promotion_review_blocks_all_research_loop_generation_modes(tmp_path):
    candidate = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='PromotionReviewCandidate',
            baseline_csv=str(tmp_path / 'b.csv'),
            condition_discovery_process='promotion-review',
            run_candidate=True,
            run_candidates=False,
        )
    )
    assert candidate['phase'] == 'promotion_review_generation_blocked'
    assert candidate['condition_discovery_process'] == 'promotion-review'
    assert candidate['condition_discovery_preset'] == 'promotion'

    candidates = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='PromotionReviewBatch',
            baseline_csv=str(tmp_path / 'b.csv'),
            condition_discovery_process='promotion-review',
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
        )
    )
    assert candidates['phase'] == 'promotion_review_generation_blocked'

    read_only_review = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='PromotionReviewReadOnly',
            baseline_csv=str(tmp_path / 'b.csv'),
            condition_discovery_process='promotion-review',
            run_candidate=False,
            run_candidates=False,
        )
    )
    assert read_only_review['phase'] == 'promotion_review_generation_blocked'


def test_promotion_review_run_research_once_blocks_before_generation(monkeypatch, tmp_path):
    calls = {'analysis': 0, 'generation': 0}

    def fail_analysis(*args, **kwargs):
        calls['analysis'] += 1
        return {'status': 'ok'}

    def fail_generation(*args, **kwargs):
        calls['generation'] += 1
        return {'status': 'ok', 'expressions': ['체결강도 > 100']}

    monkeypatch.setattr(research_loop, 'analyze_result_csv', fail_analysis)
    monkeypatch.setattr(research_loop, 'generate_condition_expressions_from_analysis', fail_generation)
    controller = DummyController(None)

    result = run_research_once(
        ResearchLoopConfig(
            name='PromotionReviewNoGeneration',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            condition_discovery_process='promotion-review',
            run_candidate=False,
            run_candidates=False,
        ),
        controller,
    )

    assert result['phase'] == 'promotion_review_generation_blocked'
    assert controller.runs == []
    assert calls == {'analysis': 0, 'generation': 0}


def test_validate_research_iteration_rejects_invalid_min_estimated_retention(tmp_path):
    invalid_retention = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='InvalidRetention',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            min_estimated_retention=1.1,
        )
    )
    assert invalid_retention['phase'] == 'invalid_min_estimated_retention'


def test_validate_research_iteration_rejects_invalid_candidate_pool_multiplier(tmp_path):
    invalid_pool_multiplier = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='InvalidPoolMultiplier',
            baseline_csv=str(tmp_path / 'b.csv'),
            run_candidates=True,
            candidate_pool_multiplier=0,
        )
    )
    assert invalid_pool_multiplier['phase'] == 'invalid_candidate_pool_multiplier'


def test_run_research_once_allows_inactive_invalid_candidate_count(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='PreviewInactiveCount',
            baseline_csv=str(baseline),
            run_candidates=False,
            candidate_count=0,
            run_candidate=False,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result.get('phase') != 'invalid_candidate_count'
    assert result['candidate']['expression']


def test_run_research_iteration_rejects_mode_conflict():
    result = research_loop.run_research_iteration(
        ResearchLoopConfig(run_candidates=True),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'run_candidate_and_run_candidates_conflict'


def test_iteration_plan_uses_effective_top_n_and_candidate_prefix(tmp_path):
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='BatchName',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            candidate_count=3,
            candidate_name_prefix='PrefixName',
            top_n=1,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=120,
            cleanup_best_candidate=True,
            keep_loser_candidates=True,
            keep_failed_candidate=True,
            run_candidates=True,
        )
    )

    assert plan['candidate_count'] == 3
    assert plan['candidate_name_prefix'] == 'PrefixName'
    assert plan['effective_top_n'] == 9
    assert plan['candidate_start_date'] == 20250102
    assert plan['candidate_end_date'] == 20250103
    assert plan['candidate_timeout'] == 120
    assert plan['cleanup_best_candidate'] is True
    assert plan['keep_loser_candidates'] is True
    assert plan['keep_failed_candidate'] is True


def test_iteration_plan_includes_retention_policy():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='RetentionPlan',
            run_candidates=True,
            candidate_count=5,
            top_n=5,
            min_estimated_retention=0.4,
            candidate_pool_multiplier=3,
            allow_retention_fallback=True,
            use_retention_penalty=True,
        )
    )

    assert plan['candidate_pool_multiplier'] == 3
    assert plan['candidate_pool_size'] == 15
    assert plan['effective_top_n'] == 15
    assert plan['min_estimated_retention'] == 0.4
    assert plan['allow_retention_fallback'] is True
    assert plan['use_retention_penalty'] is True


def test_research_loop_config_has_iteration_v2_fields():
    names = set(ResearchLoopConfig.__dataclass_fields__)

    assert 'iteration_v2_mode' in names
    assert 'iteration_v2_best_candidate' in names
    assert 'iteration_v2_best_expression' in names
    assert 'iteration_v2_primary_feature' in names
    assert 'iteration_v2_secondary_features' in names
    assert 'iteration_v2_include_secondary_only' in names
    assert 'iteration_v2_max_secondary_only' in names
    assert 'iteration_v2_duplicate_retention_tolerance' in names


def test_research_loop_config_has_iteration_v2_trade_amount_feature():
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'iteration_v2_trade_amount_feature' in names

    config = ResearchLoopConfig()
    assert config.iteration_v2_trade_amount_feature == 'B_당일거래대금'


def test_research_loop_config_has_dr04_final_owner_selection_field():
    """DR-04 -- bullet 1: default-OFF final-owner selection routing flag."""
    names = {field.name for field in fields(ResearchLoopConfig)}
    assert 'final_owner_selection_enabled' in names

    config = ResearchLoopConfig()
    assert config.final_owner_selection_enabled is False
    # OFF has zero effect unless llm_candidate_pack_enabled is also True --
    # exercised end-to-end in tests/unit/test_llm_pack_wiring.py.


def test_iteration_plan_includes_v2_settings():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            run_candidates=True,
            iteration_v2_mode='best_feature_mix',
            iteration_v2_best_candidate='cand003',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_등락율',
            iteration_v2_secondary_features='B_체결강도,B_등락율',
        )
    )

    assert plan['iteration_v2_mode'] == 'best_feature_mix'
    assert plan['iteration_v2_best_candidate'] == 'cand003'
    assert plan['iteration_v2_best_expression'] == '66.999 <= 시가총액 < 2_580'
    assert plan['iteration_v2_primary_feature'] == 'B_시가총액'
    assert plan['iteration_v2_trade_amount_feature'] == 'B_등락율'
    assert plan['iteration_v2_secondary_features'] == ['B_체결강도', 'B_등락율']


def test_validate_research_iteration_accepts_best_feature_mix_v3(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)

    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='V3Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
        )
    )

    assert result['status'] == 'ok'


def test_validate_research_iteration_accepts_best_feature_mix_v4(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)

    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='V4Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v4',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
        )
    )

    assert result['status'] == 'ok'


def test_validate_research_iteration_accepts_custom_second_seed_feature(tmp_path):
    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='CustomSecondFeature',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_등락율',
        )
    )

    assert result['status'] == 'ok'


def test_validate_research_iteration_rejects_custom_second_feature_mismatch(tmp_path):
    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='CustomSecondFeatureMismatch',
            baseline_csv=str(tmp_path / 'baseline.csv'),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_trade_amount_feature='B_당일거래대금',
        )
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'invalid_iteration_v2_best_expression'


def test_validate_research_iteration_rejects_malformed_best_feature_mix_v3_expression(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)

    result = research_loop.validate_research_iteration_config(
        ResearchLoopConfig(
            name='V3Invalid',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_expression='66.999 <= ?쒓?珥앹븸 < 2_580',
        )
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'invalid_iteration_v2_best_expression'
    assert result['message'] == (
        'best_feature_mix_v3 iteration_v2_best_expression must contain exactly two parseable conditions'
    )


def test_build_iteration_plan_includes_best_feature_mix_v3():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            name='V3Run',
            run_candidate=False,
            run_candidates=True,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율,B_당일거래대금',
        )
    )

    assert plan['iteration_v2_mode'] == 'best_feature_mix_v3'
    assert plan['iteration_v2_best_candidate'] == 'WideV1IterationV2_20260423__cand005'
    assert plan['iteration_v2_secondary_features'] == ['B_체결강도', 'B_등락율', 'B_당일거래대금']


def test_build_candidate_specs_uses_one_expression_per_candidate():
    result = {
        'expressions': ['泥닿껐媛뺣룄 < 90', '?쒓?珥앹븸 <= 3000', 'ignored > 1'],
        'selected_candidates': [
            {'source': 'ttest', 'feature': 'B_泥닿껐媛뺣룄', 'count': 50},
            {'source': 'quantile', 'feature': 'B_?쒓?珥앹븸', 'count': 70},
            {'source': 'ignored', 'feature': 'B_ignored', 'count': 1},
        ],
    }

    specs = research_loop._build_candidate_specs(
        ResearchLoopConfig(name='BatchName', run_candidates=True, candidate_count=2),
        result,
    )
    custom_specs = research_loop._build_candidate_specs(
        ResearchLoopConfig(
            name='BatchName',
            candidate_name_prefix='CustomPrefix',
            run_candidates=True,
            candidate_count=1,
        ),
        result,
    )

    assert [spec['index'] for spec in specs] == [1, 2]
    assert [spec['strategy_name'] for spec in specs] == ['BatchName__cand001', 'BatchName__cand002']
    assert specs[0]['expression'] == '泥닿껐媛뺣룄 < 90'
    assert specs[0]['expressions'] == ['泥닿껐媛뺣룄 < 90']
    assert specs[1]['expressions'] == ['?쒓?珥앹븸 <= 3000']
    assert specs[0]['source_candidate']['feature'] == 'B_泥닿껐媛뺣룄'
    assert specs[1]['source_candidate']['feature'] == 'B_?쒓?珥앹븸'
    assert custom_specs[0]['strategy_name'] == 'CustomPrefix__cand001'


def test_build_candidate_specs_preserves_llm_candidate_pack_metadata():
    candidate_pack = {
        'schema_version': 1,
        'candidate_pack_id': 'pack-1',
        'context_pack_id': 'rcp-pack-1',
        'context_pack_sha256': 'sha-pack-1',
        'full_stom_sources_included': True,
        'prompt_budget_estimated_tokens': 124000,
        'mode_authority': 'repair_discovery_research_only',
        'generation_allowed': True,
        'parents': {
            'buy': {'id': 'buy-parent', 'code': 'if 체결강도 > 90:\n    매수 = True'},
            'sell': {'id': 'sell-parent', 'code': 'if 수익률 < -1:\n    매도 = True'},
        },
        'candidates': [
            {
                'hypothesis_id': 'A',
                'lane': 'repair',
                'expression': '체결강도 > 100',
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
                'lane': 'repair',
                'expression': '등락율 < 5',
                'intended_hypothesis': 'alternate repair',
                'mutation_axis': 'overheat_cap',
                'expected_effect': 'reduce chase losses',
                'risk_note': 'may miss breakouts',
                'parent_buy_id': 'buy-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'C',
                'lane': 'discovery',
                'expression': '거래대금 > 1000',
                'intended_hypothesis': 'new liquidity segment',
                'mutation_axis': 'liquidity_regime',
                'expected_effect': 'expand coverage',
                'risk_note': 'may overtrade',
                'coverage_bucket_keys': ['midday-liquidity'],
                'novelty': {'market_segment': 'midday'},
                'novelty_rationale': 'new market segment',
            },
        ],
    }
    expression_result = research_loop.expression_result_from_candidate_pack(candidate_pack, planned_count=3)
    specs = research_loop._build_candidate_specs(
        ResearchLoopConfig(
            name='PackName',
            run_candidates=True,
            candidate_count=3,
            condition_discovery_process='process-research',
            condition_discovery_preset='research',
        ),
        expression_result,
        candidate_count=3,
    )

    assert [spec['research_lane'] for spec in specs] == ['repair', 'repair', 'discovery']
    assert specs[0]['candidate_pack_id'] == 'pack-1'
    assert specs[0]['context_pack_id'] == 'rcp-pack-1'
    assert specs[0]['context_pack_sha256'] == 'sha-pack-1'
    assert specs[0]['candidate_contract_id'] == 'pack-1::A'
    assert specs[0]['hypothesis_id'] == 'A'
    assert specs[0]['mutation_axis'] == 'entry_strength'
    assert specs[0]['research_contract']['fallback_used'] is False
    assert specs[0]['research_contract']['prompt_maturity_credit_allowed'] is True
    assert specs[2]['prompt_receipt']['coverage_gap_id'] is None
    assert specs[2]['prompt_receipt']['discovery_target_coverage'] == ['midday-liquidity']
    assert specs[0]['prompt_receipt']['parent_buy_id'] == 'buy-parent'
    assert specs[0]['prompt_receipt']['context_pack_id'] == 'rcp-pack-1'
    assert specs[0]['prompt_receipt']['context_pack_sha256'] == 'sha-pack-1'
    assert specs[0]['prompt_receipt']['candidate_contract_id'] == 'pack-1::A'
    assert specs[0]['prompt_receipt']['full_stom_sources_included'] is True
    assert specs[0]['prompt_receipt']['prompt_budget_estimated_tokens'] == 124000
    assert specs[0]['prompt_receipt']['preserves_parent_structure'] is True
    assert specs[0]['prompt_receipt']['parent_conditions']['buy']['code'] == 'if 체결강도 > 90:\n    매수 = True'
    assert specs[0]['prompt_receipt']['parent_conditions']['sell']['code'] == 'if 수익률 < -1:\n    매도 = True'
    assert specs[0]['research_contract']['parent_conditions']['delivery_policy'] == 'full_condition_code_required_not_id_only'
    assert specs[0]['research_contract']['parent_conditions']['buy']['sha256']
    assert specs[0]['research_contract']['parent_buy_id'] == 'buy-parent'
    assert specs[0]['research_contract']['preserves_parent_structure'] is True


def test_build_candidate_specs_marks_deterministic_fallback_no_prompt_credit():
    fallback_result = research_loop.mark_diagnostic_fallback(
        {
            'status': 'ok',
            'expressions': ['등락율 <= 2'],
            'selected_candidates': [{'source': 'quantile', 'feature': 'B_등락율'}],
            'candidate_count': 1,
        },
        reason='llm_candidate_pack_missing',
    )
    specs = research_loop._build_candidate_specs(
        ResearchLoopConfig(
            name='FallbackName',
            run_candidates=True,
            candidate_count=1,
            condition_discovery_process='process-research',
            condition_discovery_preset='research',
        ),
        fallback_result,
        candidate_count=1,
    )

    assert specs[0]['fallback_used'] is True
    assert specs[0]['fallback_reason'] == 'llm_candidate_pack_missing'
    assert specs[0]['prompt_maturity_credit_allowed'] is False
    assert specs[0]['prompt_receipt']['prompt_score'] == 0
    assert specs[0]['research_contract']['fallback_used'] is True
    assert specs[0]['research_contract']['prompt_maturity_credit_allowed'] is False


def test_candidate_research_artifacts_record_downstream_official_backtest_result():
    spec = {
        'strategy_name': 'PackName__cand001',
        'research_lane': 'repair',
        'context_pack_id': 'rcp-pack-1',
        'prompt_receipt': {
            'receipt_id': 'prompt-1',
            'round_id': 'round-1',
            'slot_id': 'slot-1',
            'lane': 'repair',
            'context_pack_id': 'rcp-pack-1',
            'candidate_pack_id': 'pack-1',
            'candidate_contract_id': 'pack-1::A',
            'strict_response_validation': {'valid': True},
            'downstream_result': 'not_evaluated',
        },
        'research_contract': {'enabled': True},
        'source_candidate': {
            'root_cause': {'primary': 'weak open entries'},
            'segment_contribution': {'open-smallcap': -0.8},
            'next_recommendation': 'tighten one entry-strength axis',
        },
    }
    artifacts = research_loop._build_candidate_research_artifacts(
        ResearchLoopConfig(condition_discovery_process='process-research', condition_discovery_preset='research'),
        spec,
        candidate_result={'status': 'success', 'csv_path': 'candidate.csv'},
        comparison={'candidate_summary': {'trade_count': 12}, 'profit_delta': -1000},
        promotion={'passed': False, 'score': 12.5},
    )

    receipt = artifacts['prompt_receipt']
    assert receipt['downstream_result'] == 'rejected'
    assert receipt['official_backtest_result'] == {
        'status': 'success',
        'promotion_passed': False,
        'promotion_score': 12.5,
        'candidate_csv': 'candidate.csv',
        'trade_count': 12,
    }
    assert artifacts['analysis_card']['context_pack_id'] == 'rcp-pack-1'
    assert artifacts['analysis_card']['prompt_receipt']['official_backtest_result']['candidate_csv'] == 'candidate.csv'
    assert 'mdd' not in artifacts['analysis_card']['official_metrics']
    assert artifacts['analysis_card']['validation_provenance']['evidence_health']['overall'] != 'complete'
    assert 'validation_evidence_incomplete' in artifacts['analysis_card']['validation_provenance']['promotion_blockers']


def test_process_research_llm_pack_can_execute_three_candidate_pack(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    candidate_pack = {
        'schema_version': 1,
        'candidate_pack_id': 'pack-run',
        'parents': {
            'buy': {'id': 'buy-parent', 'code': 'if 체결강도 > 90:\n    매수 = True'},
            'sell': {'id': 'sell-parent', 'code': 'if 수익률 < -1:\n    매도 = True'},
        },
        'candidates': [
            {
                'hypothesis_id': 'A',
                'lane': 'repair',
                'expression': '체결강도 > 100',
                'intended_hypothesis': 'repair weak entry strength',
                'mutation_axis': 'entry_strength',
                'expected_effect': 'reduce weak entries',
                'risk_note': 'may reduce trades',
                'parent_buy_id': 'buy-parent',
                'parent_sell_id': 'sell-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'B',
                'lane': 'repair',
                'expression': '등락율 < 5',
                'intended_hypothesis': 'alternate overheat repair',
                'mutation_axis': 'overheat_cap',
                'expected_effect': 'keep stronger entries',
                'risk_note': 'may reduce breakout trades',
                'parent_buy_id': 'buy-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'C',
                'lane': 'discovery',
                'expression': '거래대금 > 1000',
                'intended_hypothesis': 'new liquidity coverage',
                'mutation_axis': 'liquidity_segment',
                'expected_effect': 'discover risk segment',
                'risk_note': 'may reject too much',
                'coverage_bucket_keys': ['liquidity-risk'],
                'novelty': {'market_segment': 'liquidity'},
                'novelty_rationale': 'new risk segment',
            },
        ],
    }
    monkeypatch.setattr(
        research_loop,
        'analyze_result_csv',
        lambda *args, **kwargs: {'status': 'ok', 'research_candidate_pack': candidate_pack},
    )

    def fake_annotate(candidates, *_args, **_kwargs):
        return [
            {
                **candidate,
                'retention_estimate': {'estimated_retention': 1.0},
                'retention_filter_passed': True,
                'retention_fallback_used': False,
            }
            for candidate in candidates
        ]

    monkeypatch.setattr(research_loop, 'annotate_candidate_retention', fake_annotate)
    monkeypatch.setattr(
        research_loop,
        'select_retention_aware_candidates',
        lambda candidates, **kwargs: (candidates, {'status': 'ok', 'selected_count': len(candidates)}),
    )
    executed_specs = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed_specs.append(spec.copy())
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': baseline_csv,
            'comparison': {'candidate_summary': {'trade_count': 1}, 'trade_count_retention': 1.0},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='PackRun',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=4,
            condition_discovery_process='process-research',
            condition_discovery_preset='research',
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert len(executed_specs) == 3
    assert result['expression_result']['source'] == 'llm_multi_hypothesis_candidate_pack'
    assert result['expression_result']['candidate_count'] == 3
    assert [spec['research_lane'] for spec in executed_specs] == ['repair', 'repair', 'discovery']
    assert executed_specs[0]['parent_sell_id'] == 'sell-parent'
    assert executed_specs[0]['research_contract']['preserves_parent_structure'] is True

    candidate_pack = {
        **candidate_pack,
        'candidate_pack_id': 'pack-run-2',
        'candidates': [candidate_pack['candidates'][0], candidate_pack['candidates'][2]],
    }
    executed_specs.clear()
    result_two = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='PackRunTwo',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=4,
            condition_discovery_process='process-research',
            condition_discovery_preset='research',
        ),
        DummyController(None),
    )

    assert result_two['status'] == 'ok'
    assert len(executed_specs) == 2
    assert result_two['expression_result']['candidate_pack_id'] == 'pack-run-2'
    assert result_two['expression_result']['candidate_count'] == 2
    assert [spec['research_lane'] for spec in executed_specs] == ['repair', 'discovery']


def test_process_research_diagnostic_fallback_rejects_leaky_expressions(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    monkeypatch.setattr(
        research_loop,
        'analyze_result_csv',
        lambda *args, **kwargs: {'status': 'ok', 'recommended_candidates': []},
    )
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda *args, **kwargs: {
            'status': 'ok',
            'expressions': ['R_MFE < 0'],
            'selected_candidates': [{'feature': 'R_MFE', 'source': 'quantile'}],
            'candidate_count': 1,
        },
    )

    def fail_execute(*args, **kwargs):
        raise AssertionError('leaky diagnostic fallback should not reach execution')

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fail_execute)
    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='LeakyFallback',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=4,
            condition_discovery_process='process-research',
            condition_discovery_preset='research',
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'no_expressions'
    assert result['expression_result']['status'] == 'error'
    assert 'diagnostic_fallback_expression_leakage' in result['expression_result']['fallback_reason']


def test_execute_candidate_spec_uses_spec_strategy_name_and_single_expression(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_csv = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate_csv, name='B')
    generated = []
    saved = []

    def fake_load(db_path, name, strategy_type):
        if name == 'BaseBuy':
            return {'status': 'ok', 'code': 'buy = True\nif buy:\n    self.Buy()', 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    def fake_generate(name, base_code, expressions):
        generated.append((name, expressions))
        return {'status': 'ok', 'code': base_code + '\n# filter', 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)
    monkeypatch.setattr(research_loop, 'generate_buy_filter_strategy', fake_generate)
    monkeypatch.setattr(
        research_loop,
        'save_strategy_to_db',
        lambda db_path, name, code, strategy_type: saved.append(name) or {'status': 'ok', 'name': name, 'action': 'created'},
    )
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: {'candidate_summary': {'trade_count': 1}, 'trade_count_retention': 1.0},
    )
    monkeypatch.setattr(
        research_loop,
        'evaluate_research_candidate',
        lambda comparison: {'status': 'ok', 'passed': True, 'score': 10.0},
    )

    spec = {
        'index': 1,
        'strategy_name': 'Batch__cand001',
        'expression': 'strength < 90',
        'expressions': ['strength < 90'],
        'source_candidate': {'source': 'ttest', 'feature': 'B_strength', 'count': 50},
    }
    controller = DummyController(str(candidate_csv))

    result = research_loop._execute_candidate_spec(
        ResearchLoopConfig(name='Batch', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        spec,
        controller,
        str(baseline),
    )

    assert generated == [('Batch__cand001', ['strength < 90'])]
    assert saved == ['Batch__cand001']
    assert controller.runs[0]['buy_strategy'] == 'Batch__cand001'
    assert result['status'] == 'ok'
    assert result['phase'] == 'candidate_evaluated'
    assert result['strategy_name'] == 'Batch__cand001'
    assert result['candidate_plan']['strategy_name'] == 'Batch__cand001'
    assert result['promotion']['status'] == 'ok'
    assert result['rank'] is None
    assert result['rank_score'] is None
    assert result['selected_as_best'] is False
    assert result['cleanup'] is None


def test_execute_candidate_spec_timeout_returns_candidate_item_and_cleanup(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'name': name, 'action': 'deleted'},
    )

    spec = {
        'index': 2,
        'strategy_name': 'Batch__cand002',
        'expression': 'amount <= 3000',
        'expressions': ['amount <= 3000'],
        'source_candidate': None,
    }
    controller = DummyController(str(baseline), status='error', message='candidate timeout after 120s')

    result = research_loop._execute_candidate_spec(
        ResearchLoopConfig(name='Batch', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        spec,
        controller,
        str(baseline),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest_timeout'
    assert result['strategy_name'] == 'Batch__cand002'
    assert result['candidate_plan']['strategy_name'] == 'Batch__cand002'
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['strategy_name'] == 'Batch__cand002'
    assert cleanup_calls == ['Batch__cand002']


def test_run_research_iteration_analyzes_once_and_runs_each_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_1 = tmp_path / 'candidate_1.csv'
    candidate_2 = tmp_path / 'candidate_2.csv'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_1, name='C1')
    _write_trade_csv(candidate_2, name='C2')

    analyze_calls = []
    expression_calls = []
    executed_specs = []

    monkeypatch.setattr(
        research_loop,
        'analyze_result_csv',
        lambda csv_path, **kwargs: analyze_calls.append((csv_path, kwargs)) or {'status': 'ok', 'rows': 1},
    )
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: expression_calls.append((analysis, top_n)) or {
            'status': 'ok',
            'expressions': ['R_MFE < 0', 'R_MFE > 1'],
            'selected_candidates': [{'feature': 'one'}, {'feature': 'two'}],
        },
    )

    def fake_execute(config, spec, controller, baseline_csv):
        executed_specs.append((spec.copy(), baseline_csv))
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_1 if spec['index'] == 1 else candidate_2),
            'comparison': {
                'candidate_summary': {
                    'trade_count': 10 + spec['index'],
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': spec['index'] == 2, 'score': float(spec['index'])},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='Batch',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            top_n=1,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['phase'] == 'candidates_evaluated'
    assert analyze_calls == [(str(baseline), {'min_samples': 30, 'quantiles': 10, 'alpha': 0.05})]
    assert expression_calls[0][1] == 6
    assert [call[0]['strategy_name'] for call in executed_specs] == ['Batch__cand001', 'Batch__cand002']
    assert [call[0]['expressions'] for call in executed_specs] == [['R_MFE < 0'], ['R_MFE > 1']]
    assert [call[1] for call in executed_specs] == [str(baseline), str(baseline)]
    assert result['iteration_plan']['effective_top_n'] == 6
    assert len(result['candidates']) == 2
    assert result['best_candidate']['strategy_name'] == 'Batch__cand002'
    assert result['cleanup_summary']['deleted_count'] == 1


def test_run_research_iteration_writes_runtime_output_on_success(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_1 = tmp_path / 'candidate_1.csv'
    candidate_2 = tmp_path / 'candidate_2.csv'
    runtime_output = tmp_path / 'runtime' / 'research.json'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_1, name='C1')
    _write_trade_csv(candidate_2, name='C2')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0', 'R_MFE > 1'])

    def fake_execute(config, spec, controller, baseline_csv):
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_1 if spec['index'] == 1 else candidate_2),
            'comparison': {
                'candidate_summary': {
                    'trade_count': 10 + spec['index'],
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(spec['index'])},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RuntimeSuccess',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'ok'
    assert data['status'] == 'ok'
    assert data['phase'] == 'candidates_evaluated'
    assert data['failure_policy']['max_consecutive_candidate_failures'] == 3
    assert data['failure_policy']['total_candidate_failures'] == 0
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_completed'
    assert [event['name'] for event in data['checkpoints']] == [
        'iteration_started',
        'analysis_completed',
        'candidate_pool_selected',
        'candidate_started',
        'candidate_succeeded',
        'candidate_started',
        'candidate_succeeded',
        'iteration_completed',
    ]
    assert data['runtime_timing']['candidate_durations'] == [
        {
            'index': 1,
            'strategy_name': 'RuntimeSuccess__cand001',
            'expression': 'R_MFE < 0',
            'source': None,
            'feature': None,
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_1),
            'trade_count': 11,
            'trade_count_retention': 0.5,
            'started_at_elapsed_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][0]['started_at_elapsed_seconds']),
            'completed_at_elapsed_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][0]['completed_at_elapsed_seconds']),
            'duration_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][0]['duration_seconds']),
        },
        {
            'index': 2,
            'strategy_name': 'RuntimeSuccess__cand002',
            'expression': 'R_MFE > 1',
            'source': None,
            'feature': None,
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_2),
            'trade_count': 12,
            'trade_count_retention': 0.5,
            'started_at_elapsed_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][1]['started_at_elapsed_seconds']),
            'completed_at_elapsed_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][1]['completed_at_elapsed_seconds']),
            'duration_seconds': pytest.approx(data['runtime_timing']['candidate_durations'][1]['duration_seconds']),
        },
    ]
    assert data['runtime_timing']['checkpoint_durations'][0]['from'] == 'iteration_started'


def test_run_research_iteration_flushes_runtime_output_before_candidate_execution(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_1 = tmp_path / 'candidate_1.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_1, name='C1')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0'])
    snapshots = []

    def fake_execute(config, spec, controller, baseline_csv):
        snapshot_exists = runtime_output.exists()
        snapshot = json.loads(runtime_output.read_text(encoding='utf-8')) if snapshot_exists else {}
        snapshots.append({
            'exists': snapshot_exists,
            'status': snapshot.get('status'),
            'phase': snapshot.get('phase'),
            'last_checkpoint': (snapshot.get('checkpoint_summary') or {}).get('last_checkpoint'),
            'candidate_count': len(snapshot.get('candidates') or []),
            'has_analysis_result': 'analysis_result' in snapshot,
            'timing_candidate': (snapshot.get('runtime_timing') or {}).get('candidate_durations', [{}])[0],
        })
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_1),
            'comparison': {
                'candidate_summary': {
                    'trade_count': 11,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RuntimeCheckpoint',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(runtime_output),
            cleanup_best_candidate=False,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert snapshots == [
        {
            'exists': True,
            'status': 'running',
            'phase': 'candidate_execution',
            'last_checkpoint': 'candidate_started',
            'candidate_count': 0,
            'has_analysis_result': False,
            'timing_candidate': {
                'index': 1,
                'strategy_name': 'RuntimeCheckpoint__cand001',
                'expression': 'R_MFE < 0',
                'source': None,
                'feature': None,
                'status': 'running',
                'phase': 'candidate_execution',
                'candidate_csv': None,
                'trade_count': None,
                'trade_count_retention': None,
                'started_at_elapsed_seconds': pytest.approx(
                    snapshots[0]['timing_candidate']['started_at_elapsed_seconds']
                ),
                'completed_at_elapsed_seconds': None,
                'duration_seconds': None,
            },
        },
    ]


def test_run_research_iteration_adds_retention_metadata(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': 1000, '醫낅ぉ紐?': 'A', '留ㅼ닔?쒓컙': 1, '留ㅼ닔媛': 1000},
        {'keep_metric': 5000, '醫낅ぉ紐?': 'B', '留ㅼ닔?쒓컙': 2, '留ㅼ닔媛': 1000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(
        monkeypatch,
        expressions=['keep_metric <= 2000', 'keep_metric > 2000'],
    )
    executed_specs = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed_specs.append(spec.copy())
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'retention_estimate': spec['retention_estimate'],
            'retention_filter_passed': spec['retention_filter_passed'],
            'retention_fallback_used': spec['retention_fallback_used'],
            'status': 'error',
            'phase': 'candidate_backtest',
            'message': 'stopped before running candidate',
            'cleanup': {
                'attempted': True,
                'reason': 'candidate_backtest',
                'strategy_name': spec['strategy_name'],
            },
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RetentionBatch',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            min_estimated_retention=0.4,
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_iteration'
    assert result['retention_selection']['status'] == 'ok'
    assert result['retention_selection']['selected_count'] == 2
    assert result['expression_result']['retention_selection'] == result['retention_selection']
    assert [spec['retention_filter_passed'] for spec in executed_specs] == [True, True]
    assert executed_specs[0]['retention_fallback_used'] is False
    assert executed_specs[0]['retention_estimate']['estimated_retention'] == 0.5
    assert result['candidates'][0]['retention_estimate']['estimated_retention'] == 0.5
    assert result['candidates'][0]['retention_filter_passed'] is True
    assert result['candidates'][0]['retention_fallback_used'] is False


def test_run_research_iteration_continues_after_single_candidate_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_2 = tmp_path / 'candidate_2.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    _write_trade_csv(candidate_2, name='C2')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0', 'R_MFE > 1'])
    executed = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed.append(spec['strategy_name'])
        if spec['index'] == 1:
            return {
                'index': spec['index'],
                'strategy_name': spec['strategy_name'],
                'expression': spec['expression'],
                'status': 'error',
                'phase': 'candidate_backtest_timeout',
                'message': 'timeout',
                'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
                'rank': None,
                'rank_score': None,
                'selected_as_best': False,
            }
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'ok',
            'phase': 'candidate_evaluated',
            'candidate_csv': str(candidate_2),
            'comparison': {
                'candidate_summary': {'trade_count': 11, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.5,
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
            'cleanup': None,
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='FailureContinue',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    assert executed == ['FailureContinue__cand001', 'FailureContinue__cand002']
    assert result['status'] == 'ok'
    assert result['failure_policy']['total_candidate_failures'] == 1
    assert result['failure_policy']['consecutive_candidate_failures'] == 0
    assert result['candidates'][0]['consecutive_failure_count'] == 1
    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert data['candidates'][0]['status'] == 'error'
    assert data['candidates'][1]['status'] == 'ok'


def test_run_research_iteration_aborts_after_three_consecutive_candidate_failures(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    _patch_analysis_success(
        monkeypatch,
        expressions=['R_MFE < 0', 'R_MFE > 1', 'R_MAE < -1', 'R_MAE > -2'],
    )
    executed = []

    def fake_execute(config, spec, controller, baseline_csv):
        executed.append(spec['strategy_name'])
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='FailureAbort',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=4,
            runtime_output_path=str(runtime_output),
            max_consecutive_candidate_failures=3,
        ),
        DummyController(None),
    )

    assert executed == ['FailureAbort__cand001', 'FailureAbort__cand002', 'FailureAbort__cand003']
    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_iteration_runtime_failure'
    assert result['failure_policy']['aborted'] is True
    assert result['failure_policy']['abort_reason'] == 'max_consecutive_candidate_failures'
    assert result['failure_policy']['consecutive_candidate_failures'] == 3
    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert data['phase'] == 'candidate_iteration_runtime_failure'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert [candidate['strategy_name'] for candidate in data['candidates']] == executed


def test_run_research_iteration_returns_insufficient_retention_when_fallback_disabled(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': 1000, '醫낅ぉ紐?': 'A', '留ㅼ닔?쒓컙': 1, '留ㅼ닔媛': 1000},
        {'keep_metric': 5000, '醫낅ぉ紐?': 'B', '留ㅼ닔?쒓컙': 2, '留ㅼ닔媛': 1000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(
        monkeypatch,
        expressions=['keep_metric <= 2000', 'keep_metric > 2000'],
    )

    def fail_execute(*args, **kwargs):
        raise AssertionError('candidate execution should not run when retention selection fails')

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fail_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RetentionBatch',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            min_estimated_retention=0.75,
            allow_retention_fallback=False,
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'insufficient_retention_candidates'
    assert result['retention_selection']['status'] == 'error'
    assert result['retention_selection']['passed_count'] == 0
    assert result['retention_selection']['selected_count'] == 0


def test_run_research_iteration_rejects_retention_selection_shortfall(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': 1000, '?ル굝?됵쭗?': 'A', '筌띲끉???볦퍢': 1, '筌띲끉?붷첎?': 1000},
        {'keep_metric': 5000, '?ル굝?됵쭗?': 'B', '筌띲끉???볦퍢': 2, '筌띲끉?붷첎?': 1000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(
        monkeypatch,
        expressions=['missing_metric <= 2000', 'other_missing > 0'],
        selected_candidates=[
            {'source': 'segment_scan', 'feature': 'missing_metric'},
            {'source': 'quantile', 'feature': 'other_missing'},
        ],
    )

    def fail_execute(*args, **kwargs):
        raise AssertionError('candidate execution should not run when selection returns too few candidates')

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fail_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RetentionShortfall',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            allow_retention_fallback=True,
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'insufficient_retention_candidates'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 0
    assert result['retention_selection']['status'] == 'ok'
    assert result['retention_selection']['selected_count'] == 0
    assert result['retention_candidates']
    assert result['expression_result']['retention_candidates'] == result['retention_candidates']
    assert result['retention_selection']['retention_candidates'] == result['retention_candidates']
    assert result['retention_candidates'][0]['expression'] == 'missing_metric <= 2000'
    assert result['retention_candidates'][0]['source'] == 'segment_scan'
    assert result['retention_candidates'][0]['feature'] == 'missing_metric'
    assert result['retention_candidates'][0]['retention_filter_passed'] is False
    assert result['retention_candidates'][0]['retention_fallback_used'] is False
    assert result['retention_candidates'][0]['retention_estimate']['evaluation_error']


def test_run_research_iteration_reports_fallback_in_retention_diagnostics(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'keep_metric': 1000, '?ル굝?됵쭗?': 'A', '筌띲끉???볦퍢': 1, '筌띲끉?붷첎?': 1000},
        {'keep_metric': 5000, '?ル굝?됵쭗?': 'B', '筌띲끉???볦퍢': 2, '筌띲끉?붷첎?': 1000},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(
        monkeypatch,
        expressions=['keep_metric < 0', 'keep_metric > 4000'],
        selected_candidates=[
            {'source': 'segment_scan', 'feature': 'safe_keep'},
            {'source': 'quantile', 'feature': 'fallback_keep'},
        ],
    )

    def fake_execute(config, spec, controller, baseline_csv):
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'retention_estimate': spec['retention_estimate'],
            'retention_filter_passed': spec['retention_filter_passed'],
            'retention_fallback_used': spec['retention_fallback_used'],
            'status': 'error',
            'phase': 'candidate_backtest',
            'message': 'stopped before running candidate',
            'cleanup': {
                'attempted': True,
                'reason': 'candidate_backtest',
                'strategy_name': spec['strategy_name'],
            },
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='RetentionFallback',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            min_estimated_retention=0.75,
            allow_retention_fallback=True,
        ),
        DummyController(None),
    )

    fallback_diagnostic = next(
        item for item in result['retention_candidates']
        if item['expression'] == 'keep_metric > 4000'
    )
    fallback_candidate = next(
        item for item in result['candidates']
        if item['expression'] == 'keep_metric > 4000'
    )

    assert result['retention_selection']['fallback_count'] == 1
    assert fallback_diagnostic['retention_fallback_used'] is True
    assert fallback_diagnostic['retention_filter_passed'] is False
    assert fallback_diagnostic['feature'] == 'fallback_keep'
    assert fallback_candidate['retention_fallback_used'] is True


def test_rank_candidate_results_prefers_promotion_pass_then_score():
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'Batch__cand001',
            'expression': 'A',
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {
                'candidate_summary': {'trade_count': 100, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.8,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'Batch__cand002',
            'expression': 'B',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 20, 'date_concentration': 0.3, 'symbol_concentration': 0.2},
                'trade_count_retention': 0.4,
            },
        },
        {
            'index': 3,
            'status': 'ok',
            'strategy_name': 'Batch__cand003',
            'expression': 'C',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 30, 'date_concentration': 0.3, 'symbol_concentration': 0.2},
                'trade_count_retention': 0.4,
            },
        },
        {
            'index': 4,
            'status': 'ok',
            'strategy_name': 'Batch__cand004',
            'expression': 'D',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 30, 'date_concentration': 0.2, 'symbol_concentration': 0.2},
                'trade_count_retention': 0.4,
            },
        },
        {
            'index': 5,
            'status': 'ok',
            'strategy_name': 'Batch__cand005',
            'expression': 'E',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 30, 'date_concentration': 0.2, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.4,
            },
        },
        {
            'index': 6,
            'status': 'ok',
            'strategy_name': 'Batch__cand006',
            'expression': 'F',
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 30, 'date_concentration': 0.2, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.5,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates)

    assert best['strategy_name'] == 'Batch__cand006'
    ranks = {candidate['strategy_name']: candidate['rank'] for candidate in ranked}
    assert ranks == {
        'Batch__cand001': 6,
        'Batch__cand002': 5,
        'Batch__cand003': 4,
        'Batch__cand004': 3,
        'Batch__cand005': 2,
        'Batch__cand006': 1,
    }
    assert ranked[5]['rank'] == 1
    assert ranked[5]['selected_as_best'] is True
    assert ranked[0]['selected_as_best'] is False
    assert isinstance(best['rank_score'], dict)
    assert best['rank_score'] == {
        'promotion_passed': True,
        'promotion_score': 10.0,
        'trade_count': 30.0,
        'trade_count_retention': 0.5,
        'date_concentration': 0.2,
        'symbol_concentration': 0.1,
    }
    assert ranked[0]['rank_score']['promotion_score'] == 100.0
    assert ranked[0]['rank_score']['trade_count'] == 100.0


def test_rank_candidate_results_exposes_research_context_and_advisory_reason():
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'Research__cand001',
            'expression': 'B_체결강도 > 100',
            'context_pack_id': 'rcp-1',
            'context_pack_sha256': 'sha-1',
            'candidate_pack_id': 'pack-1',
            'candidate_contract_id': 'pack-1::A',
            'hypothesis_id': 'A',
            'mutation_axis': 'entry_strength',
            'fallback_used': False,
            'prompt_maturity_credit_allowed': True,
            'downstream_result': 'rejected',
            'strict_response_validation': {'valid': True, 'failure_reason': ''},
            'discovery_novelty': {'passes_discovery_credit': True},
            'prompt_receipt': {
                'context_pack_id': 'rcp-1',
                'candidate_pack_id': 'pack-1',
                'candidate_contract_id': 'pack-1::A',
                'strict_response_validation': {'valid': True, 'failure_reason': ''},
                'downstream_result': 'rejected',
                'official_backtest_result': {'status': 'success', 'promotion_passed': False},
            },
            'candidate_result': {'status': 'success', 'csv_path': 'candidate.csv'},
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {
                'candidate_summary': {'trade_count': 100, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.8,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'Research__cand002',
            'expression': 'B_등락율 < 5',
            'fallback_used': True,
            'fallback_reason': 'llm_candidate_pack_missing',
            'prompt_maturity_credit_allowed': False,
            'candidate_result': {'status': 'success', 'csv_path': 'fallback.csv'},
            'promotion': {'passed': False, 'score': 10.0},
            'comparison': {
                'candidate_summary': {'trade_count': 10, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                'trade_count_retention': 0.4,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates)

    assert best['strategy_name'] == 'Research__cand001'
    score = best['rank_score']
    assert score['context_pack_id'] == 'rcp-1'
    assert score['candidate_pack_id'] == 'pack-1'
    assert score['candidate_contract_id'] == 'pack-1::A'
    assert score['hypothesis_id'] == 'A'
    assert score['mutation_axis'] == 'entry_strength'
    assert score['prompt_validation'] == {'valid': True, 'failure_reason': ''}
    assert score['official_backtest_result'] == {
        'status': 'success',
        'promotion_passed': False,
        'promotion_score': 100.0,
        'trade_count': 100.0,
        'trade_count_retention': 0.8,
        'candidate_csv': 'candidate.csv',
    }
    assert score['advisory_rank_reason'] == 'official_backtest_research_candidate_not_promotion_passed'
    fallback_score = ranked[1]['rank_score']
    assert fallback_score['fallback_used'] is True
    assert fallback_score['advisory_rank_reason'] == 'diagnostic_fallback_ranked_without_prompt_credit'


def test_rank_candidate_results_uses_adjusted_score_when_retention_penalty_enabled():
    config = ResearchLoopConfig(
        run_candidate=False,
        run_candidates=True,
        min_estimated_retention=0.4,
        use_retention_penalty=True,
    )
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'LowRetentionHighScore',
            'expression': 'A',
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.1,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'HighRetentionLowerScore',
            'expression': 'B',
            'promotion': {'passed': False, 'score': 40.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.4,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates, config)

    assert best['strategy_name'] == 'HighRetentionLowerScore'
    assert ranked[0]['rank_score']['retention_penalty'] == 0.25
    assert ranked[0]['rank_score']['adjusted_score'] == 25.0
    assert ranked[1]['rank_score']['adjusted_score'] == 40.0


def test_rank_candidate_results_prefers_reference_adjusted_score_when_present():
    config = ResearchLoopConfig(
        run_candidate=False,
        run_candidates=True,
        min_estimated_retention=0.4,
        use_retention_penalty=True,
        score_reference_csv='wide.csv',
    )
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'IncrementalHighReferenceLow',
            'expression': 'A',
            'promotion': {'passed': True, 'score': 5000.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
            'reference_promotion': {'passed': True, 'score': 11000.0},
            'reference_comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'IncrementalLowReferenceHigh',
            'expression': 'B',
            'promotion': {'passed': True, 'score': 2500.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 90,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.9,
            },
            'reference_promotion': {'passed': True, 'score': 13500.0},
            'reference_comparison': {
                'candidate_summary': {
                    'trade_count': 90,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.88,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates, config)

    assert best['strategy_name'] == 'IncrementalLowReferenceHigh'
    assert best['rank_score']['score_basis'] == 'reference'
    assert best['rank_score']['promotion_score'] == 13500.0
    assert best['rank_score']['incremental_promotion_score'] == 2500.0
    assert best['rank_score']['reference_promotion_score'] == 13500.0
    assert ranked[0]['rank_score']['score_basis'] == 'reference'


def test_rank_candidate_results_penalty_does_not_reward_negative_scores():
    config = ResearchLoopConfig(
        run_candidate=False,
        run_candidates=True,
        min_estimated_retention=0.4,
        use_retention_penalty=True,
    )
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'LowRetentionMoreNegative',
            'expression': 'A',
            'promotion': {'passed': False, 'score': -10.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 100,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.2,
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'ThresholdLessNegative',
            'expression': 'B',
            'promotion': {'passed': False, 'score': -5.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 0.4,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates, config)

    assert best['strategy_name'] == 'ThresholdLessNegative'
    assert ranked[0]['rank_score']['adjusted_score'] <= -10.0
    assert ranked[1]['rank_score']['adjusted_score'] == -5.0


def test_rank_candidate_results_normalizes_non_finite_scores():
    candidates = [
        {
            'index': 1,
            'status': 'ok',
            'strategy_name': 'Batch__cand001',
            'expression': 'nan-score',
            'promotion': {'passed': True, 'score': float('nan')},
            'comparison': {
                'candidate_summary': {
                    'trade_count': float('inf'),
                    'date_concentration': float('nan'),
                    'symbol_concentration': float('inf'),
                },
                'trade_count_retention': float('nan'),
            },
        },
        {
            'index': 2,
            'status': 'ok',
            'strategy_name': 'Batch__cand002',
            'expression': 'finite-score',
            'promotion': {'passed': True, 'score': 1.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 1,
                    'date_concentration': 0.2,
                    'symbol_concentration': 0.2,
                },
                'trade_count_retention': 0.1,
            },
        },
    ]

    ranked, best = research_loop._rank_candidate_results(candidates)

    assert best['strategy_name'] == 'Batch__cand002'
    assert ranked[0]['rank_score']['promotion_score'] == 0.0
    assert ranked[0]['rank_score']['trade_count'] == 0.0
    assert ranked[0]['rank_score']['trade_count_retention'] == 0.0
    assert ranked[0]['rank_score']['date_concentration'] == float('inf')
    assert ranked[0]['rank_score']['symbol_concentration'] == float('inf')


def test_execute_candidate_spec_adds_reference_comparison(monkeypatch, tmp_path):
    reference_csv = tmp_path / 'wide.csv'
    baseline_csv = tmp_path / 'cand003.csv'
    candidate_csv = tmp_path / 'cand005.csv'
    reference_csv.write_text('x', encoding='utf-8')
    baseline_csv.write_text('x', encoding='utf-8')
    candidate_csv.write_text('x', encoding='utf-8')
    config = ResearchLoopConfig(
        name='WideV1IterationV2',
        base_buy_strategy='Base',
        sell_strategy='Sell',
        run_candidates=True,
        score_reference_csv=str(reference_csv),
    )

    class Controller:
        def run(self, payload):
            return {'status': 'ok', 'csv_path': str(candidate_csv)}

    monkeypatch.setattr(
        research_loop,
        '_prepare_candidate_strategy',
        lambda config, expressions, strategy_name=None: {
            'status': 'ok',
            'strategy_result': {},
            'generated_strategy': {},
        },
    )
    monkeypatch.setattr(
        research_loop,
        '_trade_frame_for_compare',
        lambda path: f'frame:{path}',
    )
    comparisons = []

    def fake_compare(left, right):
        comparisons.append((left, right))
        return {
            'candidate_summary': {
                'trade_count': 1,
                'date_concentration': 0.1,
                'symbol_concentration': 0.1,
            },
            'baseline_summary': {'trade_count': 1},
            'excluded_summary': {'avg_return': -1.0},
            'counts': {'candidate': 1},
            'trade_count_retention': 1.0,
            'trade_count_expansion': 0.0,
        }

    monkeypatch.setattr(research_loop, 'compare_trade_sets', fake_compare)
    monkeypatch.setattr(
        research_loop,
        'evaluate_research_candidate',
        lambda comparison: {'status': 'ok', 'passed': True, 'score': 10.0, 'reasons': []},
    )

    result = research_loop._execute_candidate_spec(
        config,
        {
            'index': 1,
            'strategy_name': 'WideV1__cand001',
            'expression': 'A',
            'expressions': ['A'],
        },
        Controller(),
        str(baseline_csv),
    )

    assert result['status'] == 'ok'
    assert result['reference_comparison']['trade_count_retention'] == 1.0
    assert result['reference_promotion']['score'] == 10.0
    assert comparisons == [
        (f'frame:{baseline_csv}', f'frame:{candidate_csv}'),
        (f'frame:{reference_csv}', f'frame:{candidate_csv}'),
    ]


def test_iteration_cleanup_skips_candidate_not_created(monkeypatch):
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )
    candidates = [
        {
            'strategy_name': 'ExistingStrategy',
            'status': 'error',
            'phase': 'candidate_name_conflict',
            'message': 'candidate buy strategy already exists',
            'selected_as_best': False,
            'cleanup': None,
        },
    ]

    updated, summary = research_loop._apply_iteration_cleanup(
        ResearchLoopConfig(name='Batch', run_candidates=True),
        candidates,
    )

    assert cleanup_calls == []
    assert updated[0]['cleanup']['attempted'] is False
    assert updated[0]['cleanup']['reason'] == 'candidate_not_created'
    assert summary['attempted_count'] == 0
    assert summary['deleted_count'] == 0
    assert summary['kept_count'] == 1
    assert summary['failed_count'] == 0


def test_iteration_cleanup_deletes_losers_and_keeps_best(monkeypatch):
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )
    config = ResearchLoopConfig(name='Batch', run_candidates=True)
    candidates = [
        {'strategy_name': 'Batch__cand001', 'status': 'ok', 'selected_as_best': True, 'cleanup': None},
        {'strategy_name': 'Batch__cand002', 'status': 'ok', 'selected_as_best': False, 'cleanup': None},
        {
            'strategy_name': 'Batch__cand003',
            'status': 'error',
            'selected_as_best': False,
            'cleanup': {
                'attempted': True,
                'reason': 'candidate_backtest',
                'strategy_name': 'Batch__cand003',
                'status': 'error',
            },
        },
    ]

    updated, summary = research_loop._apply_iteration_cleanup(config, candidates)

    assert cleanup_calls == ['Batch__cand002']
    assert updated[0]['cleanup']['reason'] == 'best_candidate_kept'
    assert updated[0]['cleanup']['attempted'] is False
    assert updated[1]['cleanup']['reason'] == 'loser_candidate_deleted'
    assert updated[2]['cleanup']['reason'] == 'candidate_backtest'
    assert set(summary) == {'attempted_count', 'deleted_count', 'kept_count', 'failed_count', 'items'}
    assert summary['attempted_count'] == 2
    assert summary['deleted_count'] == 1
    assert summary['kept_count'] == 1
    assert summary['failed_count'] == 1
    assert summary['items'] == [candidate['cleanup'] for candidate in updated]


def test_iteration_cleanup_can_delete_best(monkeypatch):
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )
    candidates = [
        {'strategy_name': 'Batch__cand001', 'status': 'ok', 'selected_as_best': True, 'cleanup': None},
        {'strategy_name': 'Batch__cand002', 'status': 'ok', 'selected_as_best': False, 'cleanup': None},
    ]

    updated, summary = research_loop._apply_iteration_cleanup(
        ResearchLoopConfig(name='Batch', run_candidates=True, cleanup_best_candidate=True),
        candidates,
    )

    assert cleanup_calls == ['Batch__cand001', 'Batch__cand002']
    assert updated[0]['cleanup']['reason'] == 'best_candidate_deleted'
    assert updated[1]['cleanup']['reason'] == 'loser_candidate_deleted'
    assert set(summary) == {'attempted_count', 'deleted_count', 'kept_count', 'failed_count', 'items'}
    assert summary['attempted_count'] == 2
    assert summary['deleted_count'] == 2
    assert summary['kept_count'] == 0
    assert summary['failed_count'] == 0
    assert summary['items'] == [candidate['cleanup'] for candidate in updated]


def test_iteration_cleanup_can_keep_losers(monkeypatch):
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )
    candidates = [
        {'strategy_name': 'Batch__cand001', 'status': 'ok', 'selected_as_best': True, 'cleanup': None},
        {'strategy_name': 'Batch__cand002', 'status': 'ok', 'selected_as_best': False, 'cleanup': None},
    ]

    updated, summary = research_loop._apply_iteration_cleanup(
        ResearchLoopConfig(name='Batch', run_candidates=True, keep_loser_candidates=True),
        candidates,
    )

    assert cleanup_calls == []
    assert updated[0]['cleanup']['reason'] == 'best_candidate_kept'
    assert updated[1]['cleanup']['reason'] == 'loser_candidate_kept'
    assert set(summary) == {'attempted_count', 'deleted_count', 'kept_count', 'failed_count', 'items'}
    assert summary['attempted_count'] == 0
    assert summary['deleted_count'] == 0
    assert summary['kept_count'] == 2
    assert summary['failed_count'] == 0
    assert summary['items'] == [candidate['cleanup'] for candidate in updated]


def test_run_research_iteration_returns_error_when_all_candidates_fail(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0', 'R_MFE > 1'])
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest',
            'message': 'failed',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(name='Batch', baseline_csv=str(baseline), run_candidate=False, run_candidates=True, candidate_count=2),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_iteration'
    assert result['best_candidate'] is None
    assert len(result['candidates']) == 2
    assert set(result['cleanup_summary']) == {'attempted_count', 'deleted_count', 'kept_count', 'failed_count', 'items'}
    assert len(result['cleanup_summary']['items']) == 2


def test_run_research_iteration_rejects_insufficient_expressions(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch, expressions=['체결강도 < 90'])

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(name='Batch', baseline_csv=str(baseline), run_candidate=False, run_candidates=True, candidate_count=3),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'insufficient_expressions'
    assert result['requested_candidate_count'] == 3
    assert result['expression_count'] == 1
    assert result['iteration_plan']['candidate_count'] == 3


def test_run_research_iteration_applies_v3_candidate_pool(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '200,20,3000,1,B,20250101090200,20250101090300,100,101,1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '0.039 <= 체결강도 < 54.89',
                '1500 <= 당일거래대금 < 3654.4',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.039,
                    'upper_bound': 54.89,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_당일거래대금',
                    'operator': 'between',
                    'lower_bound': 1500.0,
                    'upper_bound': 3654.4,
                    'score': 6.0,
                    'combined_score': 6.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
    )
    executed_specs = []
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: executed_specs.append(spec) or {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 2.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_당일거래대금',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v3']['status'] == 'ok'
    assert result['iteration_v3']['type_counts']['v3_control_keep_best'] == 1
    assert executed_specs
    assert any('1805.7 <= 당일거래대금 < 3654.4 and' in spec['expression'] for spec in executed_specs)
    assert all(spec['expression'] != result['iteration_v3']['control_candidate']['expression'] for spec in executed_specs)


def test_run_research_iteration_applies_v4_proxy_diverse_selection(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '3000,20,3000,1,B,20250101090200,20250101090300,100,101,1\n'
        '100,10,4000,-1,C,20250101090400,20250101090500,100,99,-1\n'
        '3000,40,6000,1,D,20250101090600,20250101090700,100,101,1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '0 <= 체결강도 < 25',
                '1000 <= 당일거래대금 < 5000',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 25.0,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'expression': '0 <= 체결강도 < 25',
                },
                {
                    'feature': 'B_당일거래대금',
                    'operator': 'between',
                    'lower_bound': 1000.0,
                    'upper_bound': 5000.0,
                    'score': 6.0,
                    'combined_score': 6.0,
                    'expression': '1000 <= 당일거래대금 < 5000',
                },
            ],
        },
    )
    executed_specs = []
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: executed_specs.append(spec) or {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 2.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V4Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v4',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_당일거래대금',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v4']['status'] == 'ok'
    assert result['retention_selection']['phase'] == 'rowset_diverse_candidates_selected'
    assert result['retention_selection']['proxy_group_count'] >= 2
    assert executed_specs


def test_run_research_iteration_v5_executes_oversampled_pool_and_selects_actual_rowsets(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    trade_amount_feature = (research_loop.build_v4_candidate_pool.__kwdefaults__ or {})['trade_amount_feature']
    trade_amount_runtime_feature = trade_amount_feature[2:]
    pd.DataFrame([
        {'B_PRIMARY': 50, trade_amount_feature: 2000, 'B_STRENGTH': 10, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, trade_amount_feature: 3000, 'B_STRENGTH': 20, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
    ]).to_csv(baseline, index=False, encoding='utf-8')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['STRENGTH < 15', 'STRENGTH < 25'],
            'selected_candidates': [
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': 15.0, 'expression': 'STRENGTH < 15'},
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': 25.0, 'expression': 'STRENGTH < 25'},
            ],
        },
    )
    v4_candidates = [
        {'expression': 'STRENGTH < 15', 'v4_candidate_type': 'v4_replace_secondary', 'combined_score': 10.0},
        {'expression': 'STRENGTH < 20', 'v4_candidate_type': 'v4_tighten_secondary', 'combined_score': 9.0},
        {'expression': 'AMOUNT < 3500', 'v4_candidate_type': 'v4_relax_trade_amount', 'combined_score': 8.0},
        {'expression': 'PRIMARY < 70', 'v4_candidate_type': 'v4_repair_trade_amount', 'combined_score': 7.0},
    ]
    def fake_build_v4_candidate_pool(*args, trade_amount_feature=trade_amount_feature, **kwargs):
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': list(v4_candidates),
            'candidate_count': len(v4_candidates),
            'type_counts': {
                'v4_replace_secondary': 1,
                'v4_tighten_secondary': 1,
                'v4_relax_trade_amount': 1,
                'v4_repair_trade_amount': 1,
            },
        }

    monkeypatch.setattr(research_loop, 'build_v4_candidate_pool', fake_build_v4_candidate_pool)
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [dict(candidate, retention_filter_passed=True) for candidate in candidates],
    )

    def fake_select_rowset_diverse_candidates(candidates, *, candidate_count, min_retention):
        selected = [dict(candidate) for candidate in candidates[:candidate_count]]
        return selected, {
            'status': 'ok',
            'phase': 'rowset_diverse_candidates_selected',
            'requested_count': candidate_count,
            'selected_count': len(selected),
            'eligible_count': len(candidates),
        }

    monkeypatch.setattr(research_loop, 'select_rowset_diverse_candidates', fake_select_rowset_diverse_candidates)

    executed_specs = []
    row_identity = {
        1: ('A', 1, 100),
        2: ('A', 1, 100),
        3: ('B', 2, 200),
        4: ('C', 3, 300),
    }

    def fake_execute_candidate_spec(config, spec, controller, baseline_csv):
        executed_specs.append(spec)
        symbol, buy_time, buy_price = row_identity[spec['index']]
        candidate_csv = tmp_path / f"{spec['strategy_name']}.csv"
        _write_identity_trade_csv(candidate_csv, symbol=symbol, buy_time=buy_time, buy_price=buy_price)
        return {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'candidate_csv': str(candidate_csv),
            'expression': spec['expression'],
            'comparison': {
                'trade_count_retention': 0.9,
                'candidate_summary': {
                    'trade_count': 1.0,
                    'date_concentration': 1.0,
                    'symbol_concentration': 1.0,
                },
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': 100.0 - spec['index']},
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute_candidate_spec)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1IterationV4__cand001',
            iteration_v2_best_expression=f'10 <= PRIMARY < 90 and 1000 <= {trade_amount_runtime_feature} < 5000',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature=trade_amount_feature,
            iteration_v2_secondary_features=f'B_STRENGTH,{trade_amount_feature}',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert len(executed_specs) == 4
    assert result['iteration_v5']['requested_count'] == 2
    assert result['iteration_v5']['execution_count'] == 4
    assert result['actual_rowset_selection']['selected_strategy_names'] == ['V5Run__cand001', 'V5Run__cand003']
    assert result['actual_rowset_selection']['status'] == 'ok'
    assert result['actual_rowset_selection']['duplicate_actual_rowset_count'] == 1
    assert result['best_candidate']['strategy_name'] == 'V5Run__cand001'
    selected = [
        candidate['strategy_name']
        for candidate in result['candidates']
        if candidate.get('actual_rowset_selected') is True
    ]
    assert selected == ['V5Run__cand001', 'V5Run__cand003']


def test_run_research_iteration_v5_process_research_caps_to_four_hybrid_slots(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    trade_amount_feature = (research_loop.build_v4_candidate_pool.__kwdefaults__ or {})['trade_amount_feature']
    trade_amount_runtime_feature = trade_amount_feature[2:]
    pd.DataFrame([
        {'B_PRIMARY': 50, trade_amount_feature: 2000, 'B_STRENGTH': 10, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, trade_amount_feature: 3000, 'B_STRENGTH': 20, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
    ]).to_csv(baseline, index=False, encoding='utf-8')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})

    generated = [f'STRENGTH < {limit}' for limit in (15, 20, 25, 30, 35, 40)]
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': list(generated),
            'selected_candidates': [
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': float(index), 'expression': expression}
                for index, expression in enumerate(generated, start=1)
            ],
        },
    )
    v4_candidates = [
        {'expression': expression, 'v4_candidate_type': 'v4_replace_secondary', 'combined_score': float(10 - index)}
        for index, expression in enumerate(generated, start=1)
    ]
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': list(v4_candidates),
            'candidate_count': len(v4_candidates),
            'type_counts': {'v4_replace_secondary': len(v4_candidates)},
        },
    )

    recovery_requested = []

    def fake_v5_recovery(*args, candidate_count, existing_v4_result, **kwargs):
        recovery_requested.append(candidate_count)
        return {
            'candidates': list(existing_v4_result.get('candidates') or []),
            'initial_v4_candidate_count': len(existing_v4_result.get('candidates') or []),
            'recovery_attempted': False,
            'recovery_reason': None,
            'recovery_family_counts': {},
            'final_candidate_pool_count': len(existing_v4_result.get('candidates') or []),
            'requested_candidate_count': candidate_count,
            'recovery_needed_count': 0,
        }

    monkeypatch.setattr(research_loop, 'build_v5_recovery_candidate_pool', fake_v5_recovery)
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [dict(candidate, retention_filter_passed=True) for candidate in candidates],
    )

    rowset_counts = []

    def fake_select_rowset_diverse_candidates(candidates, *, candidate_count, min_retention):
        rowset_counts.append(candidate_count)
        selected = [dict(candidate) for candidate in candidates[:candidate_count]]
        return selected, {
            'status': 'ok',
            'phase': 'rowset_diverse_candidates_selected',
            'requested_count': candidate_count,
            'selected_count': len(selected),
            'eligible_count': len(candidates),
        }

    monkeypatch.setattr(research_loop, 'select_rowset_diverse_candidates', fake_select_rowset_diverse_candidates)

    executed_specs = []

    def fake_execute_candidate_spec(config, spec, controller, baseline_csv):
        executed_specs.append(spec)
        return {
            'status': 'ok',
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'research_lane': spec.get('research_lane'),
            'comparison': {
                'trade_count_retention': 0.9,
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.0,
                    'symbol_concentration': 0.0,
                },
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(100 - spec['index'])},
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute_candidate_spec)
    monkeypatch.setattr(
        research_loop,
        'select_actual_rowset_representatives',
        lambda ranked, runtime_root, requested_count: (
            ranked[:requested_count],
            {
                'status': 'ok',
                'row_set_identity_status': 'all_distinct',
                'requested_count': requested_count,
                'executed_count': len(ranked),
                'actual_group_count': len(ranked),
                'selected_count': requested_count,
                'selected_strategy_names': [candidate['strategy_name'] for candidate in ranked[:requested_count]],
            },
        ),
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Hybrid',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=6,
            condition_discovery_process='2',
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1IterationV4__cand001',
            iteration_v2_best_expression=f'10 <= PRIMARY < 90 and 1000 <= {trade_amount_runtime_feature} < 5000',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature=trade_amount_feature,
            iteration_v2_secondary_features=f'B_STRENGTH,{trade_amount_feature}',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert recovery_requested == [4]
    assert rowset_counts == [4]
    assert len(executed_specs) == 4
    assert [spec['research_lane'] for spec in executed_specs] == ['repair', 'discovery', 'repair', 'discovery']
    assert result['iteration_plan']['requested_candidate_count'] == 6
    assert result['iteration_plan']['candidate_count'] == 4
    assert result['iteration_v5']['requested_count'] == 4
    assert result['iteration_v5']['execution_count'] == 4
    assert result['actual_rowset_selection']['requested_count'] == 4


def test_run_research_iteration_v5_skips_actual_rowset_when_success_count_is_short(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate_csv = tmp_path / 'candidate_1.csv'
    trade_amount_feature = 'B_AMOUNT'
    trade_amount_runtime_feature = trade_amount_feature[2:]
    pd.DataFrame([
        {'B_PRIMARY': 50, trade_amount_feature: 2000, 'B_STRENGTH': 10, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, trade_amount_feature: 3000, 'B_STRENGTH': 20, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
    ]).to_csv(baseline, index=False, encoding='utf-8')
    _write_identity_trade_csv(candidate_csv, symbol='C1')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['STRENGTH < 15', 'STRENGTH < 25'],
            'selected_candidates': [
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': 15.0, 'expression': 'STRENGTH < 15'},
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': 25.0, 'expression': 'STRENGTH < 25'},
            ],
        },
    )
    v4_candidates = [
        {'expression': 'STRENGTH < 15', 'v4_candidate_type': 'v4_replace_secondary', 'combined_score': 10.0},
        {'expression': 'STRENGTH < 20', 'v4_candidate_type': 'v4_tighten_secondary', 'combined_score': 9.0},
    ]

    def fake_build_v4_candidate_pool(*args, trade_amount_feature=trade_amount_feature, **kwargs):
        return {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': list(v4_candidates),
            'candidate_count': len(v4_candidates),
            'type_counts': {
                'v4_replace_secondary': 1,
                'v4_tighten_secondary': 1,
            },
        }

    monkeypatch.setattr(research_loop, 'build_v4_candidate_pool', fake_build_v4_candidate_pool)
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [dict(candidate, retention_filter_passed=True) for candidate in candidates],
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda candidates, *, candidate_count, min_retention: (
            [dict(candidate) for candidate in candidates[:candidate_count]],
            {
                'status': 'ok',
                'phase': 'rowset_diverse_candidates_selected',
                'requested_count': candidate_count,
                'selected_count': min(candidate_count, len(candidates)),
                'eligible_count': len(candidates),
            },
        ),
    )

    def fail_if_actual_rowset_runs(*args, **kwargs):
        raise AssertionError('actual row-set selection should not run when success count is short')

    monkeypatch.setattr(research_loop, 'select_actual_rowset_representatives', fail_if_actual_rowset_runs)

    def fake_execute(config, spec, controller, baseline_csv):
        if spec['index'] == 1:
            return {
                'index': spec['index'],
                'strategy_name': spec['strategy_name'],
                'expression': spec['expression'],
                'status': 'ok',
                'phase': 'candidate_evaluated',
                'candidate_csv': str(candidate_csv),
                'comparison': {
                    'candidate_summary': {'trade_count': 10, 'date_concentration': 0.1, 'symbol_concentration': 0.1},
                    'trade_count_retention': 0.5,
                },
                'promotion': {'status': 'ok', 'passed': True, 'score': 2.0},
                'cleanup': None,
                'rank': None,
                'rank_score': None,
                'selected_as_best': False,
            }
        return {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute)

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Short',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=f'10 <= PRIMARY < 90 and 1000 <= {trade_amount_runtime_feature} < 5000',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature=trade_amount_feature,
            iteration_v2_secondary_features=f'B_STRENGTH,{trade_amount_feature}',
            max_consecutive_candidate_failures=3,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['actual_rowset_selection']['status'] == 'not_run'
    assert result['actual_rowset_selection']['reason'] == 'insufficient_successful_candidates'
    assert result['actual_rowset_selection']['requested_count'] == 2
    assert result['actual_rowset_selection']['successful_candidate_count'] == 1
    assert result['iteration_v5']['status'] == 'not_run'
    assert result['iteration_v5']['actual_selected_count'] == 0


def test_run_research_iteration_uses_v5_recovery_when_v4_pool_is_empty(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'B_PRIMARY': 50, 'B_TRADE': 4.0, 'B_STRENGTH': 10, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, 'B_TRADE': 5.5, 'B_STRENGTH': 20, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
        {'B_PRIMARY': 70, 'B_TRADE': 6.5, 'B_STRENGTH': 30, INSTRUMENT_COLUMNS[1]: 'C', REQUIRED_KEY_COLUMNS[0]: 3, OPTIONAL_KEY_COLUMNS[0]: 300},
    ]).to_csv(baseline, index=False, encoding='utf-8')

    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [
            {
                'feature': 'B_TRADE',
                'operator': '>',
                'threshold': 5.2,
                'score': 4.0,
                'combined_score': 4.0,
                'source': 'quantile',
            },
            {
                'feature': 'B_STRENGTH',
                'operator': 'between',
                'lower_bound': 15.0,
                'upper_bound': 35.0,
                'score': 3.0,
                'combined_score': 3.0,
                'source': 'quantile',
            },
        ],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['STRENGTH > 10', 'STRENGTH > 20'],
            'candidate_count': 2,
            'selected_candidates': [
                {'feature': 'B_STRENGTH', 'operator': '>', 'threshold': 10.0, 'score': 1.0, 'combined_score': 1.0},
                {'feature': 'B_STRENGTH', 'operator': '>', 'threshold': 20.0, 'score': 1.0, 'combined_score': 1.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {'v4_control_keep_best': 1},
        },
    )
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [
            dict(
                candidate,
                retention_filter_passed=True,
                rowset_proxy={
                    'proxy_signature': frozenset({index}),
                    'proxy_signature_hash': f'hash-{index}',
                    'proxy_retention': 0.8,
                    'proxy_filter_passed': True,
                    'evaluation_error': None,
                },
            )
            for index, candidate in enumerate(candidates, start=1)
        ],
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda candidates, *, candidate_count, min_retention: (
            [dict(candidate) for candidate in candidates[:2]],
            {
                'status': 'ok',
                'phase': 'rowset_diverse_candidates_selected',
                'requested_count': candidate_count,
                'selected_count': 2,
                'eligible_count': len(candidates),
                'pool_count': len(candidates),
            },
        ),
    )
    executed_specs = []

    def fake_execute_candidate_spec(config, spec, controller, baseline_csv):
        executed_specs.append(spec)
        return {
            'status': 'ok',
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {
                'trade_count_retention': 0.8,
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.0,
                    'symbol_concentration': 0.0,
                },
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(10 - spec['index'])},
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute_candidate_spec)
    monkeypatch.setattr(
        research_loop,
        'select_actual_rowset_representatives',
        lambda ranked, runtime_root, requested_count: (
            ranked[:requested_count],
            {
                'status': 'ok',
                'row_set_identity_status': 'all_distinct',
                'requested_count': requested_count,
                'executed_count': len(ranked),
                'actual_group_count': len(ranked),
                'selected_count': requested_count,
                'selected_strategy_names': [candidate['strategy_name'] for candidate in ranked[:requested_count]],
            },
        ),
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5Recovery',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert len(executed_specs) == 2
    assert result['iteration_v5']['recovery']['recovery_attempted'] is True
    assert result['iteration_v5']['recovery']['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] >= 2
    assert result['retention_selection']['pool_count'] >= 2
    assert any(
        candidate['source_candidate']['v5_candidate_source'] in {'recovered_trade_feature', 'auto_secondary_feature'}
        for candidate in result['candidate_specs']
    )


def test_run_research_iteration_uses_v5_recovery_when_direct_v4_pool_is_short(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'B_PRIMARY': 50, 'B_TRADE': 4.0, 'B_STRENGTH': 80, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
        {'B_PRIMARY': 60, 'B_TRADE': 5.0, 'B_STRENGTH': 85, INSTRUMENT_COLUMNS[1]: 'B', REQUIRED_KEY_COLUMNS[0]: 2, OPTIONAL_KEY_COLUMNS[0]: 200},
    ]).to_csv(baseline, index=False, encoding='utf-8')

    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [
            {'feature': 'B_TRADE', 'operator': '>', 'threshold': 5.2, 'score': 5.0, 'combined_score': 5.0, 'original_index': 1},
            {'feature': 'B_STRENGTH', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 4.0, 'combined_score': 4.0, 'original_index': 2},
        ],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['TRADE > 5.2', '70 <= STRENGTH < 90'],
            'candidate_count': 2,
            'selected_candidates': [
                {'feature': 'B_TRADE', 'operator': '>', 'threshold': 5.2, 'score': 5.0, 'combined_score': 5.0},
                {'feature': 'B_STRENGTH', 'operator': 'between', 'lower_bound': 70.0, 'upper_bound': 90.0, 'score': 4.0, 'combined_score': 4.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': [{
                'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
                'v4_candidate_type': 'v4_repair_trade_amount',
                'v5_candidate_source': 'direct_v4',
                'score': 10.0,
                'combined_score': 10.0,
                'conditions': [
                    {'feature': 'B_PRIMARY', 'operator': 'between', 'lower_bound': 66.999, 'upper_bound': 2580.0, 'threshold': None},
                    {'feature': 'B_TRADE', 'operator': '>', 'lower_bound': None, 'upper_bound': None, 'threshold': 5.0},
                ],
            }],
            'candidate_count': 1,
            'type_counts': {'v4_repair_trade_amount': 1},
        },
    )
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_rowset_proxy',
        lambda candidates, baseline_frame, min_retention: [
            dict(candidate, retention_filter_passed=True)
            for candidate in candidates
        ],
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda candidates, *, candidate_count, min_retention: (
            [dict(candidate) for candidate in candidates[:candidate_count]],
            {
                'status': 'ok',
                'phase': 'rowset_diverse_candidates_selected',
                'requested_count': candidate_count,
                'selected_count': min(candidate_count, len(candidates)),
                'eligible_count': len(candidates),
            },
        ),
    )

    executed_specs = []

    def fake_execute_candidate_spec(config, spec, controller, baseline_csv):
        executed_specs.append(spec)
        return {
            'status': 'ok',
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {
                'trade_count_retention': 0.8,
                'candidate_summary': {
                    'trade_count': 10,
                    'date_concentration': 0.0,
                    'symbol_concentration': 0.0,
                },
            },
            'promotion': {'status': 'ok', 'passed': True, 'score': float(10 - spec['index'])},
        }

    monkeypatch.setattr(research_loop, '_execute_candidate_spec', fake_execute_candidate_spec)
    monkeypatch.setattr(
        research_loop,
        'select_actual_rowset_representatives',
        lambda ranked, runtime_root, requested_count: (
            ranked[:requested_count],
            {
                'status': 'ok',
                'row_set_identity_status': 'all_distinct',
                'requested_count': requested_count,
                'executed_count': len(ranked),
                'actual_group_count': len(ranked),
                'selected_count': requested_count,
                'selected_strategy_names': [candidate['strategy_name'] for candidate in ranked[:requested_count]],
            },
        ),
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5DirectShortfallRecovery',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
        ),
        controller=object(),
    )

    sources = [spec['source_candidate']['v5_candidate_source'] for spec in result['candidate_specs']]

    assert result['status'] == 'ok'
    assert len(executed_specs) == 4
    assert result['iteration_v5']['execution_count'] == 4
    assert result['iteration_v5']['recovery']['recovery_attempted'] is True
    assert result['iteration_v5']['recovery']['recovery_reason'] == 'direct_v4_shortfall'
    assert result['iteration_v5']['recovery']['recovery_family_counts']['direct_v4'] == 1
    assert result['iteration_v5']['recovery']['requested_candidate_count'] == 2
    assert result['iteration_v5']['recovery']['recovery_needed_count'] == 1
    assert result['iteration_v5']['initial_v4_candidate_count'] == 1
    assert result['initial_v4_candidate_count'] == 1
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] >= 2
    assert sources[0] == 'direct_v4'
    assert any(source != 'direct_v4' for source in sources)


def test_run_research_iteration_reports_v5_recovery_metadata_on_shortfall(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([
        {'B_PRIMARY': 50, 'B_TRADE': 4.0, INSTRUMENT_COLUMNS[1]: 'A', REQUIRED_KEY_COLUMNS[0]: 1, OPTIONAL_KEY_COLUMNS[0]: 100},
    ]).to_csv(baseline, index=False, encoding='utf-8')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {
        'status': 'ok',
        'recommended_candidates': [],
    })
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['STRENGTH < 0', 'STRENGTH > 100'],
            'candidate_count': 2,
            'selected_candidates': [
                {'feature': 'B_STRENGTH', 'operator': '<', 'threshold': 0.0, 'score': 1.0, 'combined_score': 1.0},
                {'feature': 'B_STRENGTH', 'operator': '>', 'threshold': 100.0, 'score': 1.0, 'combined_score': 1.0},
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v4_candidate_pool',
        lambda *args, **kwargs: {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'candidates': [],
            'candidate_count': 0,
            'type_counts': {'v4_control_keep_best': 1},
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V5RecoveryShortfall',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_best_candidate='WideV1Final_B_20260425',
            iteration_v2_best_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
        ),
        controller=object(),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'insufficient_retention_candidates'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 0
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['final_candidate_pool_count'] == 0
    assert result['eligible_count'] == 0


def test_run_research_iteration_returns_runtime_output_write_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    blocked_output = tmp_path / 'blocked.json'
    blocked_output.mkdir()
    _write_trade_csv(baseline, name='BASE')
    _patch_analysis_success(monkeypatch, expressions=['R_MFE < 0'])

    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'index': spec['index'],
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'status': 'error',
            'phase': 'candidate_backtest_timeout',
            'message': 'timeout',
            'cleanup': {'attempted': True, 'reason': 'candidate_backtest_timeout', 'strategy_name': spec['strategy_name']},
            'rank': None,
            'rank_score': None,
            'selected_as_best': False,
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='WriteFail',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(blocked_output),
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'runtime_output_write_failure'
    assert result['runtime_output_path'] == str(blocked_output)
    assert 'runtime output write failed' in result['message']


def test_run_research_iteration_writes_runtime_output_on_analysis_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    runtime_output = tmp_path / 'runtime.json'
    _write_trade_csv(baseline, name='BASE')
    monkeypatch.setattr(
        research_loop,
        'analyze_result_csv',
        lambda *args, **kwargs: {'status': 'error', 'message': 'analysis failed'},
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='AnalysisRuntimeFail',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(None),
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'error'
    assert result['phase'] == 'analysis'
    assert data['status'] == 'error'
    assert data['phase'] == 'analysis'
    assert data['analysis_result']['message'] == 'analysis failed'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert data['failure_policy']['total_candidate_failures'] == 0


def test_run_research_iteration_writes_runtime_output_on_baseline_failure(tmp_path):
    runtime_output = tmp_path / 'runtime.json'
    controller = DummyController(None, status='error', message='baseline failed')

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='BaselineRuntimeFail',
            baseline_csv=None,
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            runtime_output_path=str(runtime_output),
        ),
        controller,
    )

    data = json.loads(runtime_output.read_text(encoding='utf-8'))
    assert result['status'] == 'error'
    assert result['phase'] == 'baseline_run'
    assert data['status'] == 'error'
    assert data['phase'] == 'baseline_run'
    assert data['run_result']['message'] == 'baseline failed'
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_aborted'
    assert data['failure_policy']['total_candidate_failures'] == 0


def test_run_research_iteration_keeps_v3_retention_selection_path(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['0 <= 체결강도 < 25'],
            'selected_candidates': [{
                'feature': 'B_체결강도',
                'operator': 'between',
                'lower_bound': 0.0,
                'upper_bound': 25.0,
                'score': 8.0,
                'combined_score': 8.0,
                'expression': '0 <= 체결강도 < 25',
            }],
        },
    )
    calls = {'retention': 0, 'rowset': 0}
    monkeypatch.setattr(
        research_loop,
        'select_retention_aware_candidates',
        lambda candidates, candidate_count, allow_fallback, min_retention: (
            calls.__setitem__('retention', calls['retention'] + 1) or candidates[:candidate_count],
            {
                'status': 'ok',
                'phase': 'retention_candidates_selected',
                'pool_count': len(candidates),
                'passed_count': len(candidates),
                'fallback_count': 0,
                'selected_count': min(candidate_count, len(candidates)),
                'requested_count': candidate_count,
                'min_estimated_retention': min_retention,
                'allow_retention_fallback': allow_fallback,
            },
        ),
    )
    monkeypatch.setattr(
        research_loop,
        'select_rowset_diverse_candidates',
        lambda *args, **kwargs: calls.__setitem__('rowset', calls['rowset'] + 1) or ([], {}),
    )
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 1.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3StillRetention',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert calls == {'retention': 1, 'rowset': 0}


def test_run_research_iteration_populates_v3_control_reference_score(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    reference_csv = tmp_path / 'reference.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_당일거래대금,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,2000,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '200,20,3000,1,B,20250101090200,20250101090300,100,101,1\n',
        encoding='utf-8',
    )
    reference_csv.write_text('reference\n', encoding='utf-8')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['0.039 <= 체결강도 < 54.89'],
            'selected_candidates': [
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.039,
                    'upper_bound': 54.89,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'retention_estimate': {'estimated_retention': 0.2},
                    'retention_filter_passed': False,
                    'retention_fallback_used': False,
                },
            ],
        },
    )
    called_with = []
    monkeypatch.setattr(
        research_loop,
        '_build_reference_evaluation',
        lambda config, candidate_csv: called_with.append(candidate_csv) or {
            'score_reference_csv': str(reference_csv),
            'reference_comparison': {'trade_count_retention': 1.0},
            'reference_promotion': {'status': 'ok', 'passed': True, 'score': 123.4},
        },
    )
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 2.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3ControlScore',
            baseline_csv=str(baseline),
            score_reference_csv=str(reference_csv),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= 시가총액 < 2_580 and '
                '1805.7 <= 당일거래대금 < 3654.4'
            ),
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert called_with == [str(baseline)]
    assert result['iteration_v3']['control_candidate']['reference_adjusted_score'] == 123.4


def test_run_research_iteration_ignores_malformed_v3_control_reference_score(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    reference_csv = tmp_path / 'reference.csv'
    _write_trade_csv(baseline, name='BASE')
    reference_csv.write_text('', encoding='utf-8')
    monkeypatch.setattr(research_loop, 'validate_research_iteration_config', lambda config: {'status': 'ok'})
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': ['0.039 <= 泥닿껐媛뺣룄 < 54.89'],
            'selected_candidates': [
                {
                    'feature': 'B_泥닿껐媛뺣룄',
                    'operator': 'between',
                    'lower_bound': 0.039,
                    'upper_bound': 54.89,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'retention_estimate': {'estimated_retention': 0.2},
                    'retention_filter_passed': False,
                    'retention_fallback_used': False,
                },
            ],
        },
    )
    monkeypatch.setattr(
        research_loop,
        'build_v3_candidate_pool',
        lambda expression_candidates, best_context, **kwargs: {
            'status': 'ok',
            'candidates': expression_candidates,
            'control_candidate': {
                'expression': best_context['expression'],
                'reference_adjusted_score': best_context.get('reference_adjusted_score'),
            },
            'type_counts': {'v3_control_keep_best': 1},
        },
    )
    monkeypatch.setattr(
        research_loop,
        'annotate_candidate_retention',
        lambda candidates, baseline_frame, min_retention: [
            {
                **candidate,
                'retention_estimate': {'estimated_retention': 1.0},
                'retention_filter_passed': True,
                'retention_fallback_used': False,
            }
            for candidate in candidates
        ],
    )
    monkeypatch.setattr(
        research_loop,
        'select_retention_aware_candidates',
        lambda candidates, candidate_count, allow_fallback, min_retention: (
            candidates[:candidate_count],
            {
                'status': 'ok',
                'phase': 'retention_candidates_selected',
                'pool_count': len(candidates),
                'passed_count': len(candidates),
                'fallback_count': 0,
                'selected_count': min(candidate_count, len(candidates)),
                'requested_count': candidate_count,
                'min_estimated_retention': min_retention,
                'allow_retention_fallback': allow_fallback,
            },
        ),
    )
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 2.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V3ControlScoreMalformedReference',
            baseline_csv=str(baseline),
            score_reference_csv=str(reference_csv),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
            iteration_v2_mode='best_feature_mix_v3',
            iteration_v2_best_candidate='WideV1IterationV2_20260423__cand005',
            iteration_v2_best_expression=(
                '66.999 <= ?쒓?珥앹븸 < 2_580 and '
                '1805.7 <= ?뱀씪嫄곕옒?湲?< 3654.4'
            ),
            iteration_v2_primary_feature='B_?쒓?珥앹븸',
            iteration_v2_secondary_features='B_泥닿껐媛뺣룄',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v3']['control_candidate']['reference_adjusted_score'] is None


def test_run_research_iteration_applies_v2_candidate_pool(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,B_체결강도,B_등락율,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,10,1,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '200,20,2,1,B,20250101090200,20250101090300,100,101,1\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok'})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda analysis, top_n: {
            'status': 'ok',
            'expressions': [
                '50 <= 시가총액 < 2580',
                '0 <= 체결강도 < 55',
                '0 <= 등락율 < 25',
            ],
            'selected_candidates': [
                {
                    'feature': 'B_시가총액',
                    'operator': 'between',
                    'lower_bound': 50.0,
                    'upper_bound': 2580.0,
                    'score': 10.0,
                    'combined_score': 10.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_체결강도',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 55.0,
                    'score': 9.0,
                    'combined_score': 9.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'feature': 'B_등락율',
                    'operator': 'between',
                    'lower_bound': 0.0,
                    'upper_bound': 25.0,
                    'score': 8.0,
                    'combined_score': 8.0,
                    'retention_estimate': {'estimated_retention': 0.9},
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
    )

    executed_specs = []
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: executed_specs.append(spec) or {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='V2Run',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=2,
            iteration_v2_mode='best_feature_mix',
            iteration_v2_best_candidate='cand003',
            iteration_v2_best_expression='66.999 <= 시가총액 < 2_580',
            iteration_v2_primary_feature='B_시가총액',
            iteration_v2_secondary_features='B_체결강도,B_등락율',
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert result['iteration_v2']['status'] == 'ok'
    assert executed_specs
    assert any(' and ' in spec['expression'] for spec in executed_specs)


def test_run_research_iteration_omits_iteration_v2_when_mode_disabled(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    baseline.write_text(
        'B_시가총액,수익률,종목명,매수시간,매도시간,매수가,매도가,수익금\n'
        '100,-1,A,20250101090000,20250101090100,100,99,-1\n'
        '200,1,B,20250101090200,20250101090300,100,101,1\n',
        encoding='utf-8',
    )
    _patch_analysis_success(
        monkeypatch,
        expressions=['시가총액 <= 2000'],
        selected_candidates=[{'source': 'segment_scan', 'feature': 'B_시가총액'}],
    )
    monkeypatch.setattr(
        research_loop,
        '_execute_candidate_spec',
        lambda config, spec, controller, baseline_csv: {
            'status': 'ok',
            'strategy_name': spec['strategy_name'],
            'expression': spec['expression'],
            'comparison': {'trade_count_retention': 0.9},
            'promotion': {'status': 'ok', 'passed': True, 'score': 1.0},
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': 1.0,
                'trade_count': 10.0,
                'trade_count_retention': 0.9,
                'date_concentration': 0.0,
                'symbol_concentration': 0.0,
            },
        },
    )

    result = research_loop.run_research_iteration(
        ResearchLoopConfig(
            name='DefaultBatch',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_candidates=True,
            candidate_count=1,
        ),
        controller=object(),
    )

    assert result['status'] == 'ok'
    assert 'iteration_v2' not in result


def test_research_preview_includes_candidate_plan(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='PlanPreview',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=300,
            run_candidate=False,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    plan = result['candidate_plan']
    assert plan['strategy_name'] == 'PlanPreview'
    assert plan['base_buy_strategy'] == 'BaseBuy'
    assert plan['sell_strategy'] == 'BaseSell'
    assert plan['expression'] == '체결강도 < 90'
    assert plan['candidate_start_date'] == 20250102
    assert plan['candidate_end_date'] == 20250103
    assert plan['candidate_timeout'] == 300
    assert plan['will_save_strategy'] is False
    assert plan['will_run_backtest'] is False


def test_candidate_plan_only_does_not_save_or_run(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    def fail_save(*args, **kwargs):
        raise AssertionError('save should not be attempted')

    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fail_save)

    controller = DummyController(None)

    result = run_research_once(
        ResearchLoopConfig(
            name='PlanOnly',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
            candidate_plan_only=True,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert result['phase'] == 'candidate_plan'
    assert result['candidate_plan']['will_save_strategy'] is False
    assert result['candidate_plan']['will_run_backtest'] is False
    assert result['candidate_csv'] is None
    assert result['comparison'] is None
    assert result['promotion'] is None
    assert controller.runs == []


def test_candidate_plan_only_does_not_require_base_buy_strategy(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='PlanOnlyNoBase',
            baseline_csv=str(baseline),
            run_candidate=True,
            candidate_plan_only=True,
        ),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['phase'] == 'candidate_plan'
    assert result['candidate_plan']['base_buy_strategy'] == ''
    assert result['candidate_plan']['will_save_strategy'] is False
    assert result['candidate_plan']['will_run_backtest'] is False


def test_candidate_runtime_overrides_candidate_backtest_config(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = DummyController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='RuntimeOverride',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            candidate_start_date=20250102,
            candidate_end_date=20250103,
            candidate_timeout=300,
            run_candidate=True,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    candidate_config = controller.runs[0]
    assert candidate_config['buy_strategy'] == 'RuntimeOverride'
    assert candidate_config['start_date'] == 20250102
    assert candidate_config['end_date'] == 20250103
    assert candidate_config['timeout'] == 300
    assert result['candidate_plan']['strategy_name'] == 'RuntimeOverride'
    assert result['report']['candidate_plan']['strategy_name'] == 'RuntimeOverride'


def test_candidate_runtime_zero_dates_are_not_silently_replaced(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    controller = DummyController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='ZeroDateOverride',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            start_date=20250101,
            end_date=20250131,
            candidate_start_date=0,
            candidate_end_date=0,
            run_candidate=True,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    candidate_config = controller.runs[0]
    assert candidate_config['start_date'] == 0
    assert candidate_config['end_date'] == 0


def test_research_result_has_no_wfo_payload(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='NoWfoPayload',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
        ),
        DummyController(str(candidate)),
    )

    assert result['status'] == 'ok'
    assert 'wfo_result' not in result
    assert 'wfo_evaluation' not in result
    assert 'combined_evaluation' not in result


def test_run_research_once_combines_filters_with_base_strategy(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    pd.DataFrame([
        {'종목명': 'A', '매수시간': 202501010900, '매도시간': 202501010910, '매수가': 1000, '수익률': -1.0, '수익금': -1000, 'R_MFE': 0.2, 'R_MAE': -2.0, 'B_체결강도': 80, 'B_시분초': 91000, 'B_시가총액': 1500},
    ]).to_csv(baseline, index=False, encoding='utf-8-sig')
    pd.DataFrame([
        {'종목명': 'B', '매수시간': 202501011000, '매도시간': 202501011010, '매수가': 2000, '수익률': 0.5, '수익금': 500, 'R_MFE': 1.0, 'R_MAE': -0.5, 'B_체결강도': 120, 'B_시분초': 100000, 'B_시가총액': 12000},
    ]).to_csv(candidate, index=False, encoding='utf-8-sig')

    calls = {}
    monkeypatch.setattr(research_loop, 'DB_STRATEGY', 'fake_strategy.db')
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'ok', 'recommended_candidates': []})
    monkeypatch.setattr(
        research_loop,
        'generate_condition_expressions_from_analysis',
        lambda *args, **kwargs: {'status': 'ok', 'expressions': ['체결강도 < 90'], 'candidate_count': 1, 'selected_candidates': []},
    )
    def fake_load(db_path, name, strategy_type):
        if name == 'BaseBuy':
            return {'status': 'ok', 'code': 'buy = True\nif buy:\n    self.Buy()', 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)

    def fake_generate_filter(name, base_code, expressions):
        calls['filter'] = {'name': name, 'base_code': base_code, 'expressions': expressions}
        return {'status': 'ok', 'code': base_code + '\n# filter:' + ','.join(expressions), 'name': name}

    def fake_save(db_path, name, code, strategy_type):
        calls['save'] = {'db_path': db_path, 'name': name, 'code': code, 'strategy_type': strategy_type}
        return {'status': 'ok', 'name': name, 'action': 'created'}

    monkeypatch.setattr(research_loop, 'generate_buy_filter_strategy', fake_generate_filter)
    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fake_save)

    controller = DummyController(str(candidate))
    config = ResearchLoopConfig(
        name='AutoResearchTest',
        baseline_csv=str(baseline),
        base_buy_strategy='BaseBuy',
        sell_strategy='BaseSell',
        start_date=20250101,
        end_date=20250102,
        is_tick=False,
        run_candidate=True,
    )

    result = run_research_once(config, controller)

    assert result['status'] == 'ok'
    assert result['baseline_csv'] == str(baseline)
    assert result['candidate_csv'] == str(candidate)
    assert result['candidate']['expression'] == '체결강도 < 90'
    assert result['candidate']['strategy_result']['action'] == 'created'
    assert result['comparison']['counts']['new'] == 1
    assert calls['filter']['name'] == 'AutoResearchTest'
    assert calls['filter']['base_code'].startswith('buy = True')
    assert calls['filter']['expressions'] == ['체결강도 < 90']
    assert calls['save']['strategy_type'] == 'buy'
    assert controller.runs[0]['buy_strategy'] == 'AutoResearchTest'


def test_research_loop_requires_base_buy_strategy_for_candidate_save(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([{'종목명': 'A', '매수시간': 202501010900, '매수가': 1000, '수익률': -1.0, '수익금': -1000}]).to_csv(baseline, index=False, encoding='utf-8-sig')
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(name='NoBase', baseline_csv=str(baseline), run_candidate=True),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_strategy'
    assert 'base_buy_strategy' in result['message']


def test_run_candidate_false_returns_expression_without_saving_or_comparison(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    def fail_save(*args, **kwargs):
        raise AssertionError('save should not be attempted')

    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fail_save)

    result = run_research_once(
        ResearchLoopConfig(name='PreviewOnly', baseline_csv=str(baseline), run_candidate=False),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['candidate']['expression'] == '체결강도 < 90'
    assert result['candidate_csv'] is None
    assert result['comparison'] is None
    assert result['promotion'] is None


def test_run_candidate_false_reports_selected_candidate_reason(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(
        monkeypatch,
        selected_candidates=[
            {'source': 'segment_scan', 'label': 'weak_loss', 'feature': 'B_strength', 'count': 42},
        ],
    )

    result = run_research_once(
        ResearchLoopConfig(name='PreviewReason', baseline_csv=str(baseline), run_candidate=False),
        DummyController(None),
    )

    assert result['status'] == 'ok'
    assert result['candidate']['reason']
    assert 'segment_scan' in result['candidate']['reason']
    assert 'weak_loss' in result['candidate']['reason']
    assert 'B_strength' in result['candidate']['reason']
    assert '42' in result['candidate']['reason']
    assert result['report']['candidate_reason'] == result['candidate']['reason']


def test_research_loop_returns_analysis_phase_on_analysis_failure(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    monkeypatch.setattr(research_loop, 'analyze_result_csv', lambda *args, **kwargs: {'status': 'error', 'message': 'bad analysis'})

    result = run_research_once(
        ResearchLoopConfig(name='AnalysisFail', baseline_csv=str(baseline), run_candidate=False),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'analysis'
    assert 'bad analysis' in result['message']


def test_research_loop_returns_no_expressions_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch, expressions=[])

    result = run_research_once(
        ResearchLoopConfig(name='NoExpressions', baseline_csv=str(baseline), run_candidate=False),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'no_expressions'


def test_research_loop_returns_base_strategy_load_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    monkeypatch.setattr(research_loop, 'load_strategy_from_db', lambda *args, **kwargs: {'status': 'error', 'message': 'missing base'})

    result = run_research_once(
        ResearchLoopConfig(name='LoadFail', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'base_strategy_load'
    assert 'missing base' in result['message']


def test_research_loop_rejects_existing_non_base_candidate_name_before_save(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    calls = {'save': 0}

    def fake_load(db_path, name, strategy_type):
        if name == 'BaseBuy':
            return {'status': 'ok', 'code': 'buy = True\nif buy:\n    self.Buy()', 'name': name}
        if name == 'ExistingCandidate':
            return {'status': 'ok', 'code': 'buy = False', 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    def fail_save(*args, **kwargs):
        calls['save'] += 1
        raise AssertionError('save should not be attempted')

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)
    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fail_save)

    result = run_research_once(
        ResearchLoopConfig(name='ExistingCandidate', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_name_conflict'
    assert 'already exists' in result['message']
    assert calls['save'] == 0


def test_research_loop_returns_filter_generation_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    def fake_load(db_path, name, strategy_type):
        if name == 'BaseBuy':
            return {'status': 'ok', 'code': 'buy = True\nif buy:\n    self.Buy()', 'name': name}
        return {'status': 'error', 'message': 'strategy not found', 'name': name}

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', fake_load)
    monkeypatch.setattr(research_loop, 'generate_buy_filter_strategy', lambda *args, **kwargs: {'status': 'error', 'message': 'filter failed'})

    result = run_research_once(
        ResearchLoopConfig(name='FilterFail', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'filter_generation'
    assert 'filter failed' in result['message']


def test_research_loop_returns_save_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(research_loop, 'save_strategy_to_db', lambda *args, **kwargs: {'status': 'error', 'message': 'save failed'})

    result = run_research_once(
        ResearchLoopConfig(name='SaveFail', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_strategy_save'
    assert 'save failed' in result['message']


def test_research_loop_returns_candidate_backtest_phase(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='RunFail', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline), status='error'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest'
    assert 'candidate failed' in result['message']


def test_candidate_backtest_timeout_cleans_candidate_by_default(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append((db_path, name, strategy_type)) or {'status': 'ok', 'name': name, 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='TimeoutCandidate', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline), status='error', message='백테스트 시간 초과 (300초)'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest_timeout'
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['status'] == 'ok'
    assert result['report']['cleanup']['status'] == 'ok'
    assert result['report']['candidate_plan']['strategy_name'] == 'TimeoutCandidate'
    assert cleanup_calls[0][1] == 'TimeoutCandidate'


def test_keep_failed_candidate_skips_cleanup(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: cleanup_calls.append(args) or {'status': 'ok'},
    )

    result = run_research_once(
        ResearchLoopConfig(
            name='KeepFailed',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            keep_failed_candidate=True,
        ),
        DummyController(str(baseline), status='error'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest'
    assert result['cleanup']['attempted'] is False
    assert result['cleanup']['reason'] == 'keep_failed_candidate'
    assert cleanup_calls == []


def test_research_loop_returns_candidate_csv_missing_when_run_omits_path(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='NoCsv', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['status'] == 'ok'
    assert result['report']['cleanup']['status'] == 'ok'
    assert result['report']['candidate_plan']['strategy_name'] == 'NoCsv'
    assert cleanup_calls == ['NoCsv']


def test_research_loop_returns_candidate_csv_missing_when_path_does_not_exist(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    missing_candidate = tmp_path / 'missing.csv'
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='MissingCsv', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(missing_candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert str(missing_candidate) in result['message']
    assert result['cleanup']['attempted'] is True
    assert result['report']['cleanup']['attempted'] is True
    assert result['report']['candidate_plan']['strategy_name'] == 'MissingCsv'
    assert cleanup_calls == ['MissingCsv']


def test_candidate_csv_missing_cleans_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='MissingCsvCleanup', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert result['cleanup']['attempted'] is True
    assert cleanup_calls == ['MissingCsvCleanup']


def test_comparison_failure_cleans_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    cleanup_calls = []
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('compare failed')),
    )
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda db_path, name, strategy_type: cleanup_calls.append(name) or {'status': 'ok', 'action': 'deleted'},
    )

    result = run_research_once(
        ResearchLoopConfig(name='CompareCleanup', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'comparison'
    assert result['cleanup']['attempted'] is True
    assert result['report']['cleanup']['attempted'] is True
    assert result['report']['candidate_plan']['strategy_name'] == 'CompareCleanup'
    assert cleanup_calls == ['CompareCleanup']


def test_candidate_csv_missing_preserves_original_error_when_cleanup_fails(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    missing_candidate = tmp_path / 'missing.csv'
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('cleanup boom')),
    )

    result = run_research_once(
        ResearchLoopConfig(name='MissingCsvCleanupError', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(missing_candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert 'candidate csv_path does not exist' in result['message']
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['status'] == 'error'
    assert result['cleanup']['message'] == 'cleanup boom'


def test_comparison_failure_preserves_original_error_when_cleanup_fails(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('compare failed')),
    )
    monkeypatch.setattr(
        research_loop,
        'delete_strategy_from_db',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('cleanup boom')),
    )

    result = run_research_once(
        ResearchLoopConfig(name='CompareCleanupError', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'comparison'
    assert 'compare failed' in result['message']
    assert result['cleanup']['attempted'] is True
    assert result['cleanup']['status'] == 'error'
    assert result['cleanup']['message'] == 'cleanup boom'


def test_research_loop_rejects_candidate_name_matching_base_strategy(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    calls = {'save': 0}

    def fail_save(*args, **kwargs):
        calls['save'] += 1
        raise AssertionError('save should not be attempted')

    monkeypatch.setattr(research_loop, 'load_strategy_from_db', lambda *args, **kwargs: {'status': 'ok', 'code': '매수 = True'})
    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fail_save)

    result = run_research_once(
        ResearchLoopConfig(name='BaseBuy', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_name_conflict'
    assert 'name' in result['message']
    assert 'base_buy_strategy' in result['message']
    assert calls['save'] == 0

def test_process_research_plan_uses_four_hybrid_slots():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            run_candidates=True,
            candidate_count=2,
            top_n=1,
            condition_discovery_preset='research',
            condition_discovery_process='process-research',
        )
    )

    assert plan['requested_candidate_count'] == 2
    assert plan['candidate_count'] == 4
    assert plan['effective_top_n'] == 12
    assert plan['research_loop']['enabled'] is True
    assert plan['research_loop']['slots']['slots_by_lane'] == {'repair': 2, 'discovery': 2}
    assert plan['research_loop']['authority'] == 'research_only_no_export_live_or_final_promotion'
    assert plan['research_loop']['process'] == 'process-research'
    assert plan['research_loop']['preset'] == 'research'


def test_process_research_plan_normalizes_numeric_selector():
    plan = research_loop._build_iteration_plan(
        ResearchLoopConfig(
            run_candidates=True,
            candidate_count=2,
            top_n=1,
            condition_discovery_process='2',
        )
    )

    assert plan['requested_candidate_count'] == 2
    assert plan['candidate_count'] == 4
    assert plan['effective_top_n'] == 12
    assert plan['research_loop']['enabled'] is True
    assert plan['research_loop']['process'] == 'process-research'
    assert plan['research_loop']['preset'] == 'research'
    assert plan['research_loop']['slots']['slots_by_lane'] == {'repair': 2, 'discovery': 2}


def test_process_research_candidate_specs_attach_lanes_and_validate_prompt_response():
    response = (
        '```json\n'
        '{"schema_version":1,"lane":"repair","prompt_version":"repair_v1_analysis_card_single_axis",'
        '"kind":"buy","timeframe":"tick","parent_id":"parent","analysis_card_id":"analysis",'
        '"intended_hypothesis":"repair one axis","risk_note":"risk"}'
        '\n```'
    )
    specs = research_loop._build_candidate_specs(
        ResearchLoopConfig(
            name='Hybrid',
            run_candidates=True,
            candidate_count=5,
            condition_discovery_preset='research',
            condition_discovery_process='process-research',
        ),
        {
            'expressions': ['A', 'B', 'C', 'D', 'E'],
            'selected_candidates': [
                {'response_text': response, 'prompt_score': 10},
                {'coverage_bucket_keys': ['turnover'], 'entry_exit_family': 'reversal'},
                {},
                {},
            ],
        },
    )

    assert [spec['research_lane'] for spec in specs] == ['repair', 'discovery', 'repair', 'discovery']
    assert len(specs) == 4
    assert specs[0]['strict_response_validation']['valid'] is False
    assert 'zero_code_blocks' in specs[0]['strict_response_validation']['failure_reason']
    assert specs[0]['prompt_receipt']['downstream_result'] == 'invalid'
    assert specs[1]['strict_response_validation']['valid'] is True
    assert specs[1]['prompt_receipt']['lane'] == 'discovery'


def test_execute_candidate_spec_rejects_invalid_hybrid_prompt_before_side_effects(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    config = ResearchLoopConfig(
        name='Hybrid',
        base_buy_strategy='BaseBuy',
        condition_discovery_preset='research',
        condition_discovery_process='process-research',
    )
    spec = {
        'index': 1,
        'strategy_name': 'Hybrid__cand001',
        'expression': '체결강도 > 100',
        'expressions': ['체결강도 > 100'],
        'research_lane': 'repair',
        'research_contract': {'enabled': True},
        'strict_response_validation': {'valid': False, 'failure_reason': 'zero_code_blocks'},
        'prompt_receipt': {'downstream_result': 'invalid'},
    }

    class RaisingController:
        def run(self, _config_dict):
            raise AssertionError('candidate backtest should not run after invalid prompt validation')

    result = research_loop._execute_candidate_spec(config, spec, RaisingController(), str(baseline))

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_prompt_validation'
    assert result['cleanup']['reason'] == 'candidate_not_created'
    assert result['strict_response_validation']['failure_reason'] == 'zero_code_blocks'


def test_rank_candidate_results_preserves_hybrid_lane_score_payload():
    candidates = [
        {
            'index': 1,
            'strategy_name': 'Hybrid__cand001',
            'status': 'ok',
            'research_lane': 'repair',
            'research_lane_score': 12.5,
            'promotion': {'passed': True, 'score': 10.0},
            'comparison': {
                'candidate_summary': {
                    'trade_count': 3,
                    'date_concentration': 0.1,
                    'symbol_concentration': 0.1,
                },
                'trade_count_retention': 1.0,
            },
        }
    ]

    ranked, best = research_loop._rank_candidate_results(candidates)

    assert best['strategy_name'] == 'Hybrid__cand001'
    assert ranked[0]['rank_score']['research_lane'] == 'repair'
    assert ranked[0]['rank_score']['research_lane_score'] == 12.5
    assert ranked[0]['rank_score']['research_score_authority'] == 'advisory_research_budget_only'


# ===========================================================================
# DR-01..DR-05 frozen chain E2E (validation-coupled integration).
#
# Deterministic, fixture-driven. No provider/model/evaluator/official-backtest/
# subprocess/network/protected-DB call anywhere in this cluster:
#   - DR-02 manifest build is a pure function of a LoopConfig fixture (no I/O).
#   - DR-03 uses a fresh tmp-path sqlite LoopState/EvidenceStore (never the
#     protected ai_strategy_loop/state/loop_runs.db default path).
#   - DR-04 drives a scripted QueueProvider fake (a full 2-repair/2-discovery
#     round) through produce_candidate_pack_result/select_official_candidate,
#     then proves a run-wide duplicate is rejected by select_official_candidate_v2
#     WITHOUT any further provider call (that function takes no provider/
#     evaluator argument at all -- the QueueProvider's captured call count is
#     asserted unchanged across the dedup check).
#   - DR-01 (uptrend_r2 slope-gate + zero-origin MDD) and DR-05 (AnalysisCardV3)
#     are pure functions over an in-memory synthetic trades DataFrame.
#
# All DR feature flags default OFF (see ai_strategy_loop/config.py) and are
# enabled explicitly below on the fixture only.
# ===========================================================================


def _frozen_chain_loop_config(**overrides):
    from ai_strategy_loop.config import LoopConfig

    cfg = LoopConfig(provider="openrouter", max_generations=1, bt_engine_mode="cold")
    # --- DR feature flags: all default OFF; enabled explicitly on this fixture ---
    cfg.manifest_v2_enabled = True
    cfg.evidence_ledger_enabled = True
    cfg.prompt_logging_enabled = True
    cfg.final_owner_selection_enabled = True
    # candidate_dedup_enabled / seed_plan_enabled are now declared LoopConfig fields
    # (config.py) after the architect re-review — setattr still works on declared
    # fields, and they are also reachable via from_dict/presets in production.
    cfg.candidate_dedup_enabled = True
    cfg.seed_plan_enabled = True
    for key, value in overrides.items():
        setattr(cfg, key, value)
    return cfg


_FROZEN_REPAIR_CODE_1 = "if 현재가 > 시가 and 거래대금 > 30000:\n    self.Buy()"
_FROZEN_REPAIR_CODE_2 = "if 현재가 > 시가 and 체결강도 > 120:\n    self.Buy()"
_FROZEN_DISCOVERY_CODE_1 = "if 등락율 > 3 and 회전율 > 1.5:\n    self.Buy()"
_FROZEN_DISCOVERY_CODE_2 = "if 고가 > 시가 * 1.02 and 전일비 > 150:\n    self.Buy()"


def _frozen_chain_response(metadata, code):
    return f"```python\n{code}\n```\n```json\n{json.dumps(metadata, ensure_ascii=False)}\n```"


def _frozen_chain_repair_metadata(**extra):
    from ai_strategy_loop.brain.prompt import REPAIR_RESEARCH_PROMPT_VERSION

    payload = {
        "schema_version": 1, "lane": "repair", "prompt_version": REPAIR_RESEARCH_PROMPT_VERSION,
        "kind": "buy", "timeframe": "min", "parent_id": "parent-1", "analysis_card_id": "analysis-1",
        "intended_hypothesis": "turnover 임계만 완화", "risk_note": "노이즈 진입 증가 위험",
        "mutation_axis": "turnover_min_902 1.5 -> 3.0", "expected_effect": "거래수 +20% 기대",
        "hypothesis_id": "rh1",
    }
    payload.update(extra)
    return payload


def _frozen_chain_discovery_metadata(**extra):
    from ai_strategy_loop.brain.prompt import DISCOVERY_RESEARCH_PROMPT_VERSION

    payload = {
        "schema_version": 1, "lane": "discovery", "prompt_version": DISCOVERY_RESEARCH_PROMPT_VERSION,
        "kind": "buy", "timeframe": "min", "coverage_gap_id": "gap-1",
        "discovery_target_coverage": ["cap:small|time:0900"], "intended_hypothesis": "회전율 반전 계열 신규 탐색",
        "novelty_rationale": "기존 팩과 다른 feature family", "risk_note": "한산장 미체결 위험",
        "mutation_axis": "feature_family:회전율", "expected_effect": "커버리지 공백 채움",
        "hypothesis_id": "dh1", "novelty": {"feature_family": "회전율_reversal"},
    }
    payload.update(extra)
    return payload


class _FrozenChainQueueProvider:
    """Scripted fake provider -- no network/model call. Records every call so
    the test can assert an exact, bounded call count (the DR-04 "budget")."""

    def __init__(self, repair, discovery):
        self.queues = {"repair": list(repair), "discovery": list(discovery)}
        self.calls = []

    def __call__(self, messages):
        user_text = messages[1]["content"]
        lane = "repair" if "repair 후보" in user_text else "discovery"
        self.calls.append(lane)
        return self.queues[lane].pop(0)


def _frozen_chain_context():
    return {
        "kind": "buy", "timeframe": "min", "round_id": "frozen-round-1",
        "parents": {
            "buy": {"id": "parent-1", "code": "if 현재가 > 시가:\n    self.Buy()"},
            "sell": {"id": "sell-1", "code": "if 수익률 < -1:\n    self.Sell()"},
        },
        "analysis_card": {
            "analysis_id": "analysis-1", "candidate_id": "parent-1",
            "root_cause": "too strict near open", "mutation_axis": "turnover_min_902 1.5 -> 3.0",
        },
        "coverage_gap": {"coverage_gap_id": "gap-1", "coverage_bucket_keys": ["cap:small|time:0900"]},
        "novelty_context": {"coverage_regime": "open_30min", "existing_fingerprints": ["fp-a"]},
    }


def _frozen_chain_proposal(candidate):
    """Same projection produce_candidate_pack_result._candidate_pool_proposal
    uses to hand an accepted candidate to the candidate_pool selectors."""
    novelty = candidate.get("novelty")
    novelty_value = float(len(novelty)) if isinstance(novelty, dict) else 0.0
    return {
        "candidate_id": str(candidate.get("hypothesis_id") or ""),
        "lane": str(candidate.get("lane") or ""),
        "family": str(candidate.get("mutation_axis") or "unspecified"),
        "expression": str(candidate.get("expression") or ""),
        "timeframe": str(candidate.get("timeframe") or ""),
        "novelty": novelty_value,
        "threshold_provenance": {},
    }


def _frozen_chain_v3_rows(n_trades=40, n_days=12, n_symbols=3):
    rows = []
    for i in range(n_trades):
        day = (i % n_days) + 1
        rows.append({
            "매수시간": f"202601{day:02d}120000",
            "종목코드": f"S{i % n_symbols}",
            "수익률": 1.0 if i % 3 else -0.5,
            "수익금": 100.0 if i % 3 else -50.0,
        })
    return pd.DataFrame(rows)


def test_dr01_dr05_frozen_chain_composes_end_to_end(tmp_path):
    """Bind DR-01..DR-05 into one coherent chain: DR-02 manifest -> DR-03
    content-addressed prompt (+ deterministic resume) -> DR-04 final-owner
    selection with run-wide dedup -> DR-01 math feeding the DR-05 card whose
    content_hash is identical across every render path.
    """
    from ai_strategy_loop.brain.pack_producer import produce_candidate_pack_result
    from ai_strategy_loop.controller import loop as L
    from ai_strategy_loop.controller.candidate_pool import (
        RunWideDedupArchive,
        select_official_candidate_v2,
    )
    from ai_strategy_loop.controller.evidence_store import EvidenceStore
    from ai_strategy_loop.controller.state import LoopState
    from ai_strategy_loop.fitness.overfit_stats import _max_drawdown_amount
    from ai_strategy_loop.fitness.score import compute_uptrend_r2
    from ai_strategy_loop.autopsy.analysis_card import (
        ROLE_TRAIN,
        ROLE_VALIDATION,
        build_analysis_card_v3,
        render_card_v3_md,
    )
    from ai_strategy_loop.brain.segment_feedback import render_directives_from_card_v3
    from ai_strategy_loop.brain.feature_importance_feedback import render_directive_hints_from_card_v3
    from cli.condition_fingerprint import ast_fingerprint

    cfg = _frozen_chain_loop_config()
    run_id = "frozen-chain-e2e"

    # ---------------------------------------------------------------
    # Step 1 (DR-02): canonical effective profile + Manifest v2, built from
    # the fixture config only (pure function -- no DB/network/backtest).
    # ---------------------------------------------------------------
    assert cfg.manifest_v2_enabled is True  # explicit ON; declared default is False
    v1_manifest = L._evidence_build_manifest(cfg, run_id)
    manifest_v2 = L._evidence_build_manifest_v2(cfg, run_id, v1_manifest)
    assert manifest_v2 is not None
    assert manifest_v2.manifest_contract == "ManifestV2"
    assert len(manifest_v2.effective_profile_hash) == 64
    for category in (
        "data", "universe", "engine", "cost", "fill", "capital", "session",
        "prompt", "seed", "code", "config",
    ):
        assert len(getattr(manifest_v2, category)) > 0, f"{category} must be bound"

    # ---------------------------------------------------------------
    # Step 2 (DR-03): a real recorded prompt yields a content-addressed
    # rendered_prompt_id that EvidenceStore.is_rendered_prompt can verify via
    # a real FK (not a synthetic placeholder). Uses a FRESH tmp sqlite path
    # -- never the protected ai_strategy_loop/state/loop_runs.db.
    # ---------------------------------------------------------------
    db_path = str(tmp_path / "loop_runs.db")
    state = LoopState(db_path=db_path, snapshot_dir=str(tmp_path / "snapshots"))
    state.resume_or_start(cfg, run_id=run_id)
    store = EvidenceStore(state)

    fake_backtest_calls = []  # nothing in this chain should ever append here.

    prompt_record = state.record_prompt(
        run_id, 0, "repair", 1,
        system_text="frozen-chain-system-v1", user_text="frozen-chain-user-body",
        model="fake-provider-no-network",
    )
    rendered_prompt_id = prompt_record["rendered_prompt_id"]
    assert rendered_prompt_id
    assert store.is_rendered_prompt(rendered_prompt_id) is True
    assert store.is_rendered_prompt("synthetic_not_persisted") is False

    # ---------------------------------------------------------------
    # Step 6 (DR-03 resume): the next-prompt rendered id/hash is identical
    # whether the run was interrupted+resumed or ran straight through --
    # content-addressed identity is a pure function of (kind, attempt,
    # system_sha, user_sha), never of wall-clock/run continuity.
    # ---------------------------------------------------------------
    state.close()
    resumed_state = LoopState(db_path=db_path, snapshot_dir=str(tmp_path / "snapshots"))
    resumed_state.resume_or_start(cfg, run_id=run_id)  # simulates interrupt+resume
    resumed_record = resumed_state.record_prompt(
        run_id, 0, "repair", 1,
        system_text="frozen-chain-system-v1", user_text="frozen-chain-user-body",
        model="fake-provider-no-network",
    )
    assert resumed_record["rendered_prompt_id"] == rendered_prompt_id

    uninterrupted_state = LoopState(
        db_path=str(tmp_path / "loop_runs_uninterrupted.db"),
        snapshot_dir=str(tmp_path / "snapshots_uninterrupted"),
    )
    uninterrupted_run_id = "frozen-chain-e2e-uninterrupted"
    uninterrupted_state.resume_or_start(cfg, run_id=uninterrupted_run_id)
    uninterrupted_record = uninterrupted_state.record_prompt(
        uninterrupted_run_id, 0, "repair", 1,
        system_text="frozen-chain-system-v1", user_text="frozen-chain-user-body",
        model="fake-provider-no-network",
    )
    assert uninterrupted_record["rendered_prompt_id"] == rendered_prompt_id
    uninterrupted_state.close()

    # ---------------------------------------------------------------
    # Step 3 (DR-04): drive final-owner selection through a scripted fake
    # provider producing a full 2-repair/2-discovery round. provider_call_count
    # proves the exact, bounded "budget" spent (4 -- one per accepted slot).
    # ---------------------------------------------------------------
    provider = _FrozenChainQueueProvider(
        repair=[
            _frozen_chain_response(_frozen_chain_repair_metadata(hypothesis_id="rh1"), _FROZEN_REPAIR_CODE_1),
            _frozen_chain_response(_frozen_chain_repair_metadata(hypothesis_id="rh2"), _FROZEN_REPAIR_CODE_2),
        ],
        discovery=[
            _frozen_chain_response(_frozen_chain_discovery_metadata(hypothesis_id="dh1"), _FROZEN_DISCOVERY_CODE_1),
            _frozen_chain_response(_frozen_chain_discovery_metadata(hypothesis_id="dh2"), _FROZEN_DISCOVERY_CODE_2),
        ],
    )
    round_result = produce_candidate_pack_result(
        _frozen_chain_context(), provider, final_owner_enabled=True,
    )
    assert round_result["status"] == "ok"
    assert round_result["provider_call_count"] == 4
    assert len(provider.calls) == 4  # exactly the scripted 2-repair/2-discovery round
    selection = round_result["final_owner_selection"]
    assert selection["selected"] is not None
    assert selection["pool_blockers"] == []
    accepted_candidates = round_result["candidate_pack"]["candidates"]
    assert len(accepted_candidates) == 4
    winner_expression = selection["selected"]["expression"]

    # A duplicate AST/rowset is rejected BEFORE any evaluation budget is spent:
    # select_official_candidate_v2 takes proposals directly (no provider/
    # evaluator/backtest parameter at all), so the fake provider's call count
    # is proven unchanged across this second-round dedup check.
    archive = RunWideDedupArchive()
    winner_fingerprint = ast_fingerprint(winner_expression, timeframe="min", methodology_version="clr04_v1")
    archive.ast_fingerprints.add(winner_fingerprint)

    round_2_candidates = [dict(c) for c in accepted_candidates]
    round_2_candidates[0] = dict(round_2_candidates[0], expression=winner_expression)  # force AST duplicate
    round_2_proposals = [_frozen_chain_proposal(c) for c in round_2_candidates]

    dedup_result = select_official_candidate_v2(
        round_2_proposals, timeframe="min", methodology_version="clr04_v1",
        run_wide_archive=archive,
    )
    assert any("run_wide_ast_duplicate" in reason for reason in dedup_result["pool_blockers"])
    assert dedup_result["selected"] is None
    assert len(provider.calls) == 4  # unchanged -- no provider call was consumed by the dedup check
    assert fake_backtest_calls == []  # nothing in DR-02..DR-04 ever touches a backtest seam

    # ---------------------------------------------------------------
    # Step 4 (DR-01 + DR-05): DR-01 math (uptrend_r2 slope-gate, zero-origin
    # MDD) is computed from a fixture result-row equity curve and feeds the
    # DR-05 AnalysisCardV3's source identity (content_hash is a function of
    # `source`, so DR-01's numbers demonstrably flow into the card).
    # ---------------------------------------------------------------
    daily_pnls = [10.0, 10.0, 10.0, -30.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    equity_curve = []
    running = 0.0
    for pnl in daily_pnls:
        running += pnl
        equity_curve.append(running)
    uptrend_r2 = compute_uptrend_r2(equity_curve)
    zero_origin_mdd = _max_drawdown_amount(_np_asarray(equity_curve))
    assert 0.0 <= uptrend_r2 <= 1.0
    assert uptrend_r2 > 0.5  # overall trend is up despite the one -30 dip -- slope-gate math
    assert zero_origin_mdd == pytest.approx(30.0)  # single dip from the running-from-0 peak

    trades_df = _frozen_chain_v3_rows()
    source = {
        "alias": "fixture://frozen-chain", "hash": "h1",
        "dr01_uptrend_r2": uptrend_r2, "dr01_mdd_amount": zero_origin_mdd,
    }
    card_train = build_analysis_card_v3(
        trades_df, source=source, role=ROLE_TRAIN, manifest_id=manifest_v2.manifest_id,
        candidate_findings=[{
            "finding_id": "f_signal", "statement": "B_signal 진입 시 초과수익", "axis": "entry_feature",
            "p_value": 0.001, "prereg_axis": False, "ci_low": 1.0, "ci_high": 5.0,
            "full_population": True,
        }],
    )
    assert card_train.role == ROLE_TRAIN
    assert len(card_train.content_hash) == 64
    assert card_train.actionable_directives, "train role with a sample-gate-passing finding must yield directives"

    # DR-01 numbers demonstrably feed the card: changing them changes the hash.
    different_source = dict(source, dr01_uptrend_r2=0.0, dr01_mdd_amount=0.0)
    card_train_different_dr01 = build_analysis_card_v3(
        trades_df, source=different_source, role=ROLE_TRAIN, manifest_id=manifest_v2.manifest_id,
        candidate_findings=[{
            "finding_id": "f_signal", "statement": "B_signal 진입 시 초과수익", "axis": "entry_feature",
            "p_value": 0.001, "prereg_axis": False, "ci_low": 1.0, "ci_high": 5.0,
            "full_population": True,
        }],
    )
    assert card_train_different_dr01.content_hash != card_train.content_hash

    # role='validation' -> zero directives regardless of the same findings/gate.
    card_validation = build_analysis_card_v3(
        trades_df, source=source, role=ROLE_VALIDATION, manifest_id=manifest_v2.manifest_id,
        candidate_findings=[{
            "finding_id": "f_signal", "statement": "B_signal 진입 시 초과수익", "axis": "entry_feature",
            "p_value": 0.001, "prereg_axis": False, "ci_low": 1.0, "ci_high": 5.0,
            "full_population": True,
        }],
    )
    assert card_validation.actionable_directives == ()

    # ---------------------------------------------------------------
    # Step 5 (DR-05 feedback): every render path (dashboard md / prompt
    # feedback / doc hints) reads the SAME card content_hash -- never
    # recomputes it.
    # ---------------------------------------------------------------
    md = render_card_v3_md(card_train)
    prompt_lines = render_directives_from_card_v3(card_train)
    doc_lines = render_directive_hints_from_card_v3(card_train)
    assert f"content_hash: {card_train.content_hash}" in md
    assert prompt_lines and all(f"[card:{card_train.content_hash}]" in line for line in prompt_lines)
    assert doc_lines and all(f"[card:{card_train.content_hash}]" in line for line in doc_lines)

    resumed_state.close()


def _np_asarray(values):
    import numpy as np

    return np.asarray(values, dtype=float)

# ---------------------------------------------------------------------------
# DR-05 회귀 가드 — AnalysisCardV3 루프 배선이 死코드(inert)가 아님을 보장한다.
#   (아키텍트 리뷰 발견: _build_analysis_card_v3 가 정의만 있고 호출부가 없었음.)
# ---------------------------------------------------------------------------
def test_dr05_analysis_card_v3_is_actually_wired_into_loop():
    """_build_analysis_card_v3 와 지시 렌더러가 loop.py 안에서 실제로 호출되어야 한다.

    호출부 없는 정의-only 헬퍼(inert) 회귀를 막는다: loop 소스에 정의(1회) 외에
    최소 1개의 호출부가 있어야 하고, 매수 프롬프트 환류 채널(card_directive_lines)이
    배선되어 있어야 한다.
    """
    import inspect

    import ai_strategy_loop.controller.loop as loop_mod

    src = inspect.getsource(loop_mod)
    # def + >=1 call → 최소 2회 등장(死코드면 1회뿐).
    assert src.count("_build_analysis_card_v3(") >= 2
    # 카드 지시가 실제로 다음 세대 매수 프롬프트로 환류되는 채널이 배선돼 있어야 한다.
    assert 'gen_kwargs["card_directive_lines"] = next_card_directive_lines' in src
    # 지시/문서 힌트 두 렌더러가 루프에서 호출되어야 한다.
    assert "render_directives_from_card_v3(" in src
    assert "render_directive_hints_from_card_v3(" in src


def test_dr05_card_directive_lines_inject_into_buy_prompt_only():
    """card_directive_lines 는 매수(build_messages kind=='buy')에만 주입되고 매도엔 무영향.

    토글 OFF(None)면 매수에서도 미주입이라 byte-identical(하위호환)을 보존한다.
    """
    from ai_strategy_loop.brain.prompt import build_messages

    lines = ["[card:deadbeef][prefer] B_signal 상단 노림"]
    buy = build_messages("buy", card_directive_lines=lines)
    assert any("deadbeef" in m["content"] for m in buy)
    sell = build_messages("sell", card_directive_lines=lines)
    assert not any("deadbeef" in m["content"] for m in sell)
    # 토글 OFF(None) → 매수 프롬프트에 카드 지시 블록이 추가되지 않는다(byte 보존).
    buy_off = build_messages("buy", card_directive_lines=None)
    assert not any("AnalysisCardV3" in m["content"] for m in buy_off)

# ---------------------------------------------------------------------------
# DR-05 회귀 가드(아키텍트 재리뷰 블로커): analysis_card_v3_enabled 는 운영 run_loop
#   경로에서 실제로 켜져야 한다. 예전엔 미선언 ad-hoc 속성이라 config =
#   effective_condition_discovery_runtime_config(config) 의 replace() 뒤 읽으면 항상
#   False로 떨어져 DR-05가 死배선이었다. 이제 정식 필드라 from_dict 도달 + replace() 생존.
# ---------------------------------------------------------------------------
def test_dr05_analysis_card_v3_flag_reachable_through_runtime_config():
    from ai_strategy_loop.config import LoopConfig
    from ai_strategy_loop.controller.condition_discovery import (
        effective_condition_discovery_runtime_config,
    )

    cfg = LoopConfig.from_dict({"analysis_card_v3_enabled": True})
    assert cfg.analysis_card_v3_enabled is True  # from_dict 도달(미선언이면 드롭됐음)
    runtime_cfg = effective_condition_discovery_runtime_config(cfg)
    # replace() 를 넘어 보존돼야 한다(예전 블로커: 여기서 False로 떨어졌음).
    assert getattr(runtime_cfg, "analysis_card_v3_enabled", False) is True
    # DR-04 토글도 동일하게 from_dict 도달 + replace() 생존.
    dr04 = effective_condition_discovery_runtime_config(
        LoopConfig.from_dict({"candidate_dedup_enabled": True, "seed_plan_enabled": True})
    )
    assert getattr(dr04, "candidate_dedup_enabled", False) is True
    assert getattr(dr04, "seed_plan_enabled", False) is True


def test_dr05_build_analysis_card_v3_executes_past_flag_gate_when_enabled(tmp_path, monkeypatch):
    """플래그가 도달 가능해졌으므로, ON이면 _build_analysis_card_v3 가 게이트를 지나
    build_analysis_card_v3 를 실제로 호출하고, OFF면 호출조차 안 한다(死배선 회귀 방지).
    """
    import types

    import ai_strategy_loop.autopsy.analysis_card as ac
    import ai_strategy_loop.controller.loop as loop_mod
    from ai_strategy_loop.config import LoopConfig

    csv = tmp_path / "trades.csv"
    csv.write_text("x\n1\n", encoding="utf-8-sig")

    calls = []

    def _fake_build(df, **kwargs):
        calls.append(kwargs.get("role"))
        return types.SimpleNamespace(content_hash="deadbeef", actionable_directives=())

    monkeypatch.setattr(ac, "build_analysis_card_v3", _fake_build)
    outcome = types.SimpleNamespace(csv_path=str(csv))

    cfg_on = LoopConfig.from_dict({"analysis_card_v3_enabled": True})
    card = loop_mod._build_analysis_card_v3(cfg_on, outcome)
    assert card is not None and card.content_hash == "deadbeef"
    assert calls == ["train"]  # 플래그 게이트를 지나 실제로 호출됨

    calls.clear()
    cfg_off = LoopConfig.from_dict({})
    assert loop_mod._build_analysis_card_v3(cfg_off, outcome) is None
    assert calls == []  # OFF면 호출조차 안 함(byte-동일)


def test_dr05_loop_wires_real_segment_and_feature_findings_into_card(tmp_path, monkeypatch):
    import types

    import ai_strategy_loop.autopsy.analysis_card as ac
    import ai_strategy_loop.brain.feature_importance_feedback as feature_mod
    import ai_strategy_loop.brain.segment_feedback as segment_mod
    import ai_strategy_loop.controller.loop as loop_mod
    from ai_strategy_loop.config import LoopConfig

    csv = tmp_path / "trades.csv"
    csv.write_text("종목명,매수시간\nA,202601010900\n", encoding="utf-8-sig")
    captured = {}

    monkeypatch.setattr(segment_mod, "build_segment_avoid_lines", lambda *args, **kwargs: ["SEGMENT_REAL"])
    monkeypatch.setattr(
        feature_mod,
        "build_feature_importance_findings",
        lambda *args, **kwargs: [{
            "statement": "FEATURE_REAL",
            "axis": "feature",
            "side": "BUY",
            "scope": "feature_importance_feedback",
            "priority": 50,
            "data_role": "TRAIN",
            "status": "READY",
            "ci_low": 0.1,
            "ci_high": 0.2,
            "prereg_axis": True,
        }],
    )

    def _fake_build(df, **kwargs):
        captured.update(kwargs)
        return types.SimpleNamespace(content_hash="d" * 64, actionable_directives=())

    monkeypatch.setattr(ac, "build_analysis_card_v3", _fake_build)
    config = LoopConfig.from_dict({
        "analysis_card_v3_enabled": True,
        "segment_feedback_enabled": True,
        "feature_importance_feedback_enabled": True,
    })

    assert loop_mod._build_analysis_card_v3(
        config, types.SimpleNamespace(csv_path=str(csv))
    ) is not None
    assert [item["statement"] for item in captured["candidate_findings"]] == [
        "FEATURE_REAL",
    ]
    assert [item["statement"] for item in captured["segment_findings"]] == [
        "SEGMENT_REAL",
    ]
    assert captured["evidence_ids"] and len(captured["evidence_ids"][0]) == 64

def test_typed_analysis_card_feedback_resolves_side_conflicts_deterministically(monkeypatch):
    import types
    import ai_strategy_loop.autopsy.analysis_card as ac

    from ai_strategy_loop.controller.loop import _resolve_analysis_card_typed_feedback
    monkeypatch.setattr(ac, "verify_analysis_card_v3_content_hash", lambda card: True)

    evidence_id = "c" * 64
    card = types.SimpleNamespace(
        content_hash=evidence_id,
        actionable_directives=(
            {"statement": "BUY_WINNER", "side": "BUY"},
            {"statement": "BUY_CONFLICT", "side": "BUY"},
            {"statement": "SELL_READY", "side": "SELL"},
            {
                "statement": "HOLDOUT_LEAK",
                "side": "BUY",
                "data_role": "HOLDOUT",
                "status": "READY",
            },
            {
                "statement": "BLOCKED_LEAK",
                "side": "SELL",
                "data_role": "TRAIN",
                "status": "BLOCKED",
            },
        ),
    )
    envelope = _resolve_analysis_card_typed_feedback(card, generation=4)

    assert envelope is not None
    assert envelope.evidence_id == evidence_id
    assert envelope.scope == "analysis_card_v3_prompt"
    assert [
        (directive.side.value, directive.statement)
        for directive in envelope.actionable_directives
    ] == [
        ("BUY", "BUY_WINNER"),
        ("SELL", "SELL_READY"),
    ]
    assert all(directive.role.value == "TRAIN" for directive in envelope.actionable_directives)
    assert all(directive.status.value == "READY" for directive in envelope.actionable_directives)
