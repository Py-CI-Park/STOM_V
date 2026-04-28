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
