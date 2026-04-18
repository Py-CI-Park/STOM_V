from dataclasses import fields

import pandas as pd

from cli import research_loop
from cli.research_loop import ResearchLoopConfig, run_research_once


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


def test_run_research_iteration_normalizes_single_candidate_default():
    result = research_loop.run_research_iteration(
        ResearchLoopConfig(run_candidates=True),
        DummyController(None),
    )

    assert result['phase'] == 'candidate_iteration'
    assert result['phase'] != 'run_candidate_and_run_candidates_conflict'
    assert result['config']['run_candidate'] is False
    assert result['config']['run_candidates'] is True


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
    assert plan['effective_top_n'] == 3
    assert plan['candidate_start_date'] == 20250102
    assert plan['candidate_end_date'] == 20250103
    assert plan['candidate_timeout'] == 120
    assert plan['cleanup_best_candidate'] is True
    assert plan['keep_loser_candidates'] is True
    assert plan['keep_failed_candidate'] is True


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
