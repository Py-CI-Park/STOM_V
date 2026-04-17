import pandas as pd

from cli import research_loop
from cli.research_loop import ResearchLoopConfig, run_research_once


class DummyController:
    def __init__(self, candidate_csv, status='success'):
        self.candidate_csv = candidate_csv
        self.status = status
        self.runs = []

    def run(self, config_dict):
        self.runs.append(config_dict)
        result = {'status': self.status, 'metrics': {'trade_count': 1}}
        if self.candidate_csv is not None:
            result['csv_path'] = self.candidate_csv
        if self.status == 'error':
            result['message'] = 'candidate failed'
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


def _passing_comparison():
    return {
        'baseline_summary': {'trade_count': 40, 'avg_return': -0.45, 'win_rate': 0.25, 'avg_mae': -2.0, 'total_profit': -18000, 'date_concentration': 0.25, 'symbol_concentration': 0.50},
        'candidate_summary': {'trade_count': 30, 'avg_return': 0.50, 'win_rate': 1.00, 'avg_mae': -0.5, 'total_profit': 15000, 'date_concentration': 0.25, 'symbol_concentration': 0.50},
        'excluded_summary': {'trade_count': 10, 'avg_return': -1.20, 'win_rate': 0.00, 'avg_mae': -2.5},
        'new_summary': {'trade_count': 0, 'avg_return': 0.0, 'win_rate': 0.0, 'avg_mae': 0.0},
        'trade_count_retention': 0.75,
        'trade_count_expansion': 0.0,
    }


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


def test_research_loop_requires_base_buy_strategy_for_candidate_save(tmp_path):
    baseline = tmp_path / 'baseline.csv'
    pd.DataFrame([{'종목명': 'A', '매수시간': 202501010900, '매수가': 1000, '수익률': -1.0, '수익금': -1000}]).to_csv(baseline, index=False, encoding='utf-8-sig')

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

    result = run_research_once(
        ResearchLoopConfig(name='RunFail', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(baseline), status='error'),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_backtest'
    assert 'candidate failed' in result['message']


def test_research_loop_returns_candidate_csv_missing_when_run_omits_path(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(name='NoCsv', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'


def test_research_loop_returns_candidate_csv_missing_when_path_does_not_exist(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    missing_candidate = tmp_path / 'missing.csv'
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(name='MissingCsv', baseline_csv=str(baseline), base_buy_strategy='BaseBuy'),
        DummyController(str(missing_candidate)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'candidate_csv_missing'
    assert str(missing_candidate) in result['message']


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


def test_research_loop_rejects_wfo_without_candidate(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='WfoNeedsCandidate',
            baseline_csv=str(baseline),
            run_candidate=False,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        DummyController(None),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'run_candidate' in result['message']


def test_research_loop_rejects_wfo_without_train_or_test_windows(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    _write_trade_csv(baseline)
    _patch_analysis_success(monkeypatch)

    result = run_research_once(
        ResearchLoopConfig(
            name='WfoNeedsWindows',
            baseline_csv=str(baseline),
            run_candidate=True,
            base_buy_strategy='BaseBuy',
            run_wfo=True,
        ),
        DummyController(str(baseline)),
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'train_window_days' in result['message']
    assert 'test_window_days' in result['message']


class WfoController(DummyController):
    def __init__(self, candidate_csv, wfo_result=None, wfo_eval=None):
        super().__init__(candidate_csv)
        self.walk_forward_calls = []
        self.eval_calls = []
        self.wfo_result = wfo_result or {'status': 'ok', 'summary': {'round_count': 2, 'success_rate': 1.0, 'mean_oos_metric': 0.5, 'mean_trade_count': 30, 'zero_trade_rounds': 0}, 'rounds': []}
        self.wfo_eval = wfo_eval or {'status': 'ok', 'passed': True, 'reasons': [], 'summary': {'round_count': 2, 'success_rate': 1.0, 'mean_oos_metric': 0.5, 'avg_trade_count': 30, 'zero_trade_rounds': 0}}

    def walk_forward(self, config_dict, param_space, **settings):
        self.walk_forward_calls.append({'config': config_dict, 'param_space': param_space, 'settings': settings})
        return self.wfo_result

    def evaluate_walk_forward_result(self, walk_forward_result, **criteria):
        self.eval_calls.append({'result': walk_forward_result, 'criteria': criteria})
        return self.wfo_eval


def _run_invalid_wfo_config(monkeypatch, tmp_path, **config_kwargs):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    save_calls = {'count': 0}

    def fake_save(db_path, name, code, strategy_type):
        save_calls['count'] += 1
        return {'status': 'ok', 'name': name, 'action': 'created'}

    monkeypatch.setattr(research_loop, 'save_strategy_to_db', fake_save)
    controller = WfoController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='InvalidWfoConfig',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
            **config_kwargs,
        ),
        controller,
    )
    return result, save_calls, controller


def test_research_loop_rejects_unknown_wfo_preset_before_candidate_side_effects(monkeypatch, tmp_path):
    result, save_calls, controller = _run_invalid_wfo_config(
        monkeypatch,
        tmp_path,
        promotion_preset='missing',
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'promotion_preset' in result['message']
    assert save_calls['count'] == 0
    assert controller.runs == []
    assert controller.walk_forward_calls == []


def test_research_loop_rejects_non_dict_wfo_criteria_before_candidate_side_effects(monkeypatch, tmp_path):
    result, save_calls, controller = _run_invalid_wfo_config(
        monkeypatch,
        tmp_path,
        promotion_criteria=['min_rounds'],
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'promotion_criteria' in result['message']
    assert save_calls['count'] == 0
    assert controller.runs == []
    assert controller.walk_forward_calls == []


def test_research_loop_rejects_non_numeric_wfo_criteria_before_candidate_side_effects(monkeypatch, tmp_path):
    result, save_calls, controller = _run_invalid_wfo_config(
        monkeypatch,
        tmp_path,
        promotion_criteria={'min_rounds': 'many'},
    )

    assert result['status'] == 'error'
    assert result['phase'] == 'wfo_config'
    assert 'min_rounds' in result['message']
    assert save_calls['count'] == 0
    assert controller.runs == []
    assert controller.walk_forward_calls == []


def test_research_loop_runs_wfo_and_combines_success(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: _passing_comparison(),
    )

    controller = WfoController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoCandidate',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            start_date=20250101,
            end_date=20250131,
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
            param_space={'avg_time': [60]},
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert result['wfo_result']['status'] == 'ok'
    assert result['wfo_evaluation']['passed'] is True
    assert result['combined_evaluation']['mode'] == 'research_plus_wfo'
    assert result['combined_evaluation']['passed'] is True
    assert controller.walk_forward_calls[0]['config']['buy_strategy'] == 'WfoCandidate'
    assert controller.walk_forward_calls[0]['config']['sell_strategy'] == 'BaseSell'
    assert controller.walk_forward_calls[0]['param_space'] == {'avg_time': [60]}
    assert controller.walk_forward_calls[0]['settings']['train_window_days'] == 20
    assert controller.walk_forward_calls[0]['settings']['test_window_days'] == 5
    assert controller.eval_calls[0]['criteria'] == {
        'min_rounds': 2,
        'min_success_rate': 0.60,
        'min_mean_oos_metric': 0.00,
        'min_avg_trade_count': 50.0,
    }


def test_research_loop_combined_evaluation_fails_when_wfo_fails(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: _passing_comparison(),
    )

    controller = WfoController(
        str(candidate),
        wfo_eval={'status': 'ok', 'passed': False, 'reasons': ['mean_oos_metric<0.0'], 'summary': {'zero_trade_rounds': 0}},
    )
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoReject',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert result['wfo_evaluation']['passed'] is False
    assert result['combined_evaluation']['passed'] is False
    assert 'wfo:mean_oos_metric<0.0' in result['combined_evaluation']['reasons']


def test_research_loop_passes_override_wfo_criteria_to_evaluator(monkeypatch, tmp_path):
    baseline = tmp_path / 'baseline.csv'
    candidate = tmp_path / 'candidate.csv'
    _write_trade_csv(baseline, name='A')
    _write_trade_csv(candidate, name='B')
    _patch_analysis_success(monkeypatch)
    _patch_strategy_success(monkeypatch)
    monkeypatch.setattr(
        research_loop,
        'compare_trade_sets',
        lambda *args, **kwargs: _passing_comparison(),
    )

    controller = WfoController(str(candidate))
    result = run_research_once(
        ResearchLoopConfig(
            name='WfoOverrideCriteria',
            baseline_csv=str(baseline),
            base_buy_strategy='BaseBuy',
            sell_strategy='BaseSell',
            run_candidate=True,
            run_wfo=True,
            train_window_days=20,
            test_window_days=5,
            promotion_criteria={
                'min_rounds': 4,
                'min_success_rate': 0.75,
                'min_mean_oos_metric': 0.2,
                'min_avg_trade_count': 80.0,
            },
        ),
        controller,
    )

    assert result['status'] == 'ok'
    assert controller.eval_calls[0]['criteria'] == {
        'min_rounds': 4,
        'min_success_rate': 0.75,
        'min_mean_oos_metric': 0.2,
        'min_avg_trade_count': 80.0,
    }
