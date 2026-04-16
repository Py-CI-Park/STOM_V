import pandas as pd

from cli import research_loop
from cli.research_loop import ResearchLoopConfig, run_research_once


class DummyController:
    def __init__(self, candidate_csv):
        self.candidate_csv = candidate_csv
        self.runs = []

    def run(self, config_dict):
        self.runs.append(config_dict)
        return {'status': 'success', 'csv_path': self.candidate_csv, 'metrics': {'trade_count': 1}}


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
    monkeypatch.setattr(
        research_loop,
        'load_strategy_from_db',
        lambda db_path, name, strategy_type: {'status': 'ok', 'code': '매수 = True\nif 매수:\n    self.Buy()', 'name': name},
    )

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
    assert calls['filter']['base_code'].startswith('매수 = True')
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
