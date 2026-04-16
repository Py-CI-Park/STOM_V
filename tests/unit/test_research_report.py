from cli.research_report import build_research_report, render_research_report_markdown


def _result():
    return {
        'status': 'ok',
        'baseline_csv': 'baseline.csv',
        'candidate_csv': 'candidate.csv',
        'candidate': {'expression': '체결강도 < 90', 'reason': 'weak_segment'},
        'comparison': {
            'counts': {'baseline': 100, 'candidate': 85, 'common': 80, 'excluded': 20, 'new': 5},
            'baseline_summary': {'avg_return': -0.2, 'win_rate': 0.4},
            'candidate_summary': {'avg_return': 0.1, 'win_rate': 0.48},
            'excluded_summary': {'avg_return': -1.2, 'win_rate': 0.1},
            'new_summary': {'avg_return': 0.2, 'win_rate': 0.6},
        },
        'promotion': {'passed': True, 'score': 0.42, 'reasons': []},
    }


def test_build_research_report_extracts_core_sections():
    report = build_research_report(_result(), strategy_name='AutoResearch')
    assert report['strategy_name'] == 'AutoResearch'
    assert report['candidate_expression'] == '체결강도 < 90'
    assert report['trade_counts']['excluded'] == 20
    assert report['promotion']['passed'] is True


def test_render_research_report_markdown_contains_trade_set_sections():
    markdown = render_research_report_markdown(build_research_report(_result(), strategy_name='AutoResearch'))
    assert '# 조건식 연구 리포트: AutoResearch' in markdown
    assert '## Candidate' in markdown
    assert '## Trade Set Comparison' in markdown
    assert '## Promotion' in markdown
