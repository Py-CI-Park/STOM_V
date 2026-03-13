import json

from cli.discovery_report import (
    build_discovery_report,
    render_discovery_report_markdown,
    save_discovery_report_json,
    save_discovery_report_markdown,
)


def _sample_result():
    return {
        'status': 'ok',
        'promoted': True,
        'feature_whitelist': ['B_등락율'],
        'ml_analysis_result': {
            'top_features': [
                {'feature': 'B_등락율', 'importance': 0.3},
                {'feature': 'B_체결강도', 'importance': 0.2},
            ]
        },
        'expression_result': {'candidate_count': 2, 'expressions': ['등락율 <= 2', '체결강도 < 90']},
        'walk_forward': {'summary': {'round_count': 3, 'success_rate': 1.0, 'zero_trade_rounds': 0, 'mean_trade_count': 120.0}},
        'promotion_evaluation': {'passed': True, 'preset': 'balanced', 'reasons': [], 'summary': {'zero_trade_rounds': 0, 'avg_trade_count': 120.0}},
        'strategy_result': {'name': 'Auto_B_Test', 'action': 'created'},
        'saved_code': {'status': 'ok', 'path': 'generated.py'},
    }


def test_build_discovery_report_extracts_summary():
    report = build_discovery_report(_sample_result())
    assert report['strategy_name'] == 'Auto_B_Test'
    assert report['promoted'] is True
    assert report['promotion_preset'] == 'balanced'
    assert report['candidate_count'] == 2
    assert report['expressions'] == ['등락율 <= 2', '체결강도 < 90']
    assert report['walk_forward_summary']['zero_trade_rounds'] == 0


def test_render_discovery_report_markdown_contains_sections():
    markdown = render_discovery_report_markdown(build_discovery_report(_sample_result()))
    assert '# 자동 조건식 탐색 리포트' in markdown
    assert '## Walk-Forward Summary' in markdown
    assert '## Promotion Evaluation' in markdown
    assert '## ML Top Features' in markdown
    assert '## Candidate Expressions' in markdown


def test_render_discovery_report_markdown_contains_auto_relax_history():
    result = _sample_result()
    result['auto_relax_history'] = [
        {'step': 0, 'top_n': 5, 'zero_trade_rounds': 2, 'total_rounds': 2},
        {'step': 1, 'top_n': 4, 'zero_trade_rounds': 0, 'total_rounds': 2},
    ]
    markdown = render_discovery_report_markdown(build_discovery_report(result))
    assert '## Auto-Relax History' in markdown
    assert 'top_n: 5' in markdown


def test_save_discovery_report_json_and_markdown(tmp_path):
    report = build_discovery_report(_sample_result())
    json_path = tmp_path / 'report.json'
    md_path = tmp_path / 'report.md'

    json_result = save_discovery_report_json(report, str(json_path))
    md_result = save_discovery_report_markdown(report, str(md_path))

    assert json_result['status'] == 'ok'
    assert md_result['status'] == 'ok'
    saved = json.loads(json_path.read_text(encoding='utf-8'))
    assert saved['strategy_name'] == 'Auto_B_Test'
    assert md_path.read_text(encoding='utf-8').startswith('# 자동 조건식 탐색 리포트')
