import json

from cli.research_report import (
    build_research_report,
    render_research_report_markdown,
    save_research_report_json,
    save_research_report_markdown,
)


def _result():
    return {
        'status': 'ok',
        'baseline_csv': 'baseline.csv',
        'candidate_csv': 'candidate.csv',
        'candidate': {'expression': '체결강도 < 90', 'reason': 'weak_segment'},
        'comparison': {
            'counts': {'baseline': 100, 'candidate': 85, 'common': 80, 'excluded': 20, 'new': 5},
            'trade_count_retention': 0.85,
            'trade_count_expansion': 0.05,
            'baseline_summary': {'avg_return': -0.2, 'win_rate': 0.4},
            'candidate_summary': {
                'avg_return': 0.1,
                'win_rate': 0.48,
                'total_profit': 1500,
                'avg_mae': -0.4,
                'profit_factor': 1.8,
                'date_concentration': 0.2,
                'symbol_concentration': 0.3,
            },
            'excluded_summary': {
                'avg_return': -1.2,
                'win_rate': 0.1,
                'total_profit': -2400,
                'avg_mae': -2.0,
                'profit_factor': 0.2,
            },
            'new_summary': {
                'avg_return': 0.2,
                'win_rate': 0.6,
                'total_profit': 500,
                'avg_mae': -0.3,
                'profit_factor': 2.0,
            },
        },
        'promotion': {
            'passed': True,
            'score': 0.42,
            'reasons': [],
            'deltas': {'avg_return': 0.3, 'win_rate': 0.08},
            'gates': {'min_trade_count': True},
        },
    }


def test_build_research_report_extracts_core_sections():
    report = build_research_report(_result(), strategy_name='AutoResearch')
    assert report['strategy_name'] == 'AutoResearch'
    assert report['candidate_expression'] == '체결강도 < 90'
    assert report['trade_counts']['excluded'] == 20
    assert report['promotion']['passed'] is True


def test_build_research_report_includes_candidate_plan_and_cleanup():
    result = _result()
    result['candidate_plan'] = {'strategy_name': 'AutoResearch', 'candidate_timeout': 300}
    result['cleanup'] = {'attempted': True, 'status': 'ok', 'action': 'deleted'}

    report = build_research_report(result, strategy_name='AutoResearch')

    assert report['candidate_plan']['candidate_timeout'] == 300
    assert report['cleanup']['action'] == 'deleted'


def test_render_research_report_markdown_contains_trade_set_sections():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '# 조건식 연구 리포트: AutoResearch' in markdown
    assert '## Candidate' in markdown
    assert '## Trade Set Comparison' in markdown
    assert '## Promotion' in markdown


def test_research_report_has_no_wfo_sections():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '## WFO 검증' not in markdown
    assert '## 최종 판단' not in markdown


def test_build_research_report_does_not_include_wfo_fields():
    result = _result()
    result['wfo_result'] = {'status': 'ok'}
    result['wfo_evaluation'] = {'passed': True}
    result['combined_evaluation'] = {'passed': True}
    report = build_research_report(result, strategy_name='AutoResearch')

    assert 'wfo_result' not in report
    assert 'wfo_evaluation' not in report
    assert 'combined_evaluation' not in report


def test_render_research_report_markdown_contains_korean_decision_labels():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '거래 수' in markdown
    assert '제외 거래' in markdown
    assert '신규 거래' in markdown
    assert '승격 평가' in markdown


def test_render_research_report_markdown_contains_candidate_runtime():
    result = _result()
    result['candidate_plan'] = {
        'strategy_name': 'AutoResearch',
        'candidate_start_date': 20250101,
        'candidate_end_date': 20250102,
        'candidate_timeout': 300,
        'will_save_strategy': True,
        'will_run_backtest': True,
    }
    result['cleanup'] = {'attempted': True, 'status': 'ok', 'action': 'deleted'}

    markdown = render_research_report_markdown(build_research_report(result, strategy_name='AutoResearch'))

    assert '## Candidate Runtime' in markdown
    assert '후보 백테스트 시작일' in markdown
    assert 'candidate_timeout' in markdown
    assert 'cleanup' in markdown


def test_render_research_report_markdown_explains_skipped_cleanup():
    result = _result()
    result['candidate_plan'] = {
        'strategy_name': 'AutoResearch',
        'candidate_start_date': 20250101,
        'candidate_end_date': 20250102,
        'candidate_timeout': 300,
        'will_save_strategy': True,
        'will_run_backtest': True,
        'keep_failed_candidate': True,
    }
    result['cleanup'] = {
        'attempted': False,
        'reason': 'keep_failed_candidate',
        'strategy_name': 'AutoResearch',
    }

    markdown = render_research_report_markdown(build_research_report(result, strategy_name='AutoResearch'))

    assert 'keep_failed_candidate' in markdown
    assert 'AutoResearch' in markdown
    assert 'cleanup reason' in markdown or 'cleanup reason:' in markdown
    assert 'cleanup status' not in markdown
    assert 'cleanup action' not in markdown


def test_render_research_report_markdown_allows_missing_promotion_reasons():
    result = _result()
    result['promotion']['reasons'] = None
    markdown = render_research_report_markdown(build_research_report(result, strategy_name='AutoResearch'))
    assert '## Promotion' in markdown
    assert 'reason: None' not in markdown


def test_save_research_report_json_normalizes_non_finite_numbers(tmp_path):
    result = _result()
    result['comparison']['candidate_summary']['profit_factor'] = float('inf')
    result['comparison']['excluded_summary']['profit_factor'] = float('-inf')
    result['comparison']['new_summary']['profit_factor'] = float('nan')
    report = build_research_report(result, strategy_name='AutoResearch')
    path = tmp_path / 'research.json'

    saved = save_research_report_json(report, str(path))

    assert saved == {'status': 'ok', 'path': str(path)}
    text = path.read_text(encoding='utf-8')
    assert 'Infinity' not in text
    assert 'NaN' not in text
    parsed = json.loads(text)
    assert parsed['candidate_summary']['profit_factor'] is None
    assert parsed['excluded_summary']['profit_factor'] is None
    assert parsed['new_summary']['profit_factor'] is None


def test_save_research_report_json_and_markdown(tmp_path):
    report = build_research_report(_result(), strategy_name='AutoResearch')
    json_path = tmp_path / 'research.json'
    markdown_path = tmp_path / 'research.md'

    json_result = save_research_report_json(report, str(json_path))
    markdown_result = save_research_report_markdown(report, str(markdown_path))

    assert json_result == {'status': 'ok', 'path': str(json_path)}
    assert markdown_result == {'status': 'ok', 'path': str(markdown_path)}
    assert json.loads(json_path.read_text(encoding='utf-8'))['strategy_name'] == 'AutoResearch'
    assert markdown_path.read_text(encoding='utf-8').startswith('# 조건식 연구 리포트: AutoResearch')


def test_save_research_report_markdown_returns_error_on_write_failure(monkeypatch, tmp_path):
    def raise_write_error(self, *args, **kwargs):
        raise OSError('write blocked')

    monkeypatch.setattr('cli.research_report.Path.write_text', raise_write_error)
    path = tmp_path / 'research.md'

    result = save_research_report_markdown(build_research_report(_result()), str(path))

    assert result['status'] == 'error'
    assert result['path'] == str(path)
    assert 'write blocked' in result['error']
