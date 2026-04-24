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


def _iteration_result():
    result = _result()
    result.update({
        'phase': 'candidates_evaluated',
        'iteration_plan': {
            'candidate_count': 2,
            'candidate_name_prefix': 'Batch',
            'candidate_start_date': 20250101,
            'candidate_end_date': 20250102,
            'candidate_timeout': 300,
            'cleanup_best_candidate': False,
            'keep_loser_candidates': False,
        },
        'candidates': [
            {
                'index': 1,
                'rank': 1,
                'strategy_name': 'Batch__cand001',
                'expression': 'strength < 90',
                'status': 'ok',
                'comparison': {
                    'counts': {'candidate': 42},
                    'trade_count_retention': 0.84,
                },
                'promotion': {'passed': True, 'score': 0.73},
                'cleanup': {
                    'attempted': False,
                    'reason': 'best_candidate_kept',
                    'strategy_name': 'Batch__cand001',
                },
                'selected_as_best': True,
            },
            {
                'index': 2,
                'rank': 2,
                'strategy_name': 'Batch__cand002',
                'expression': 'volume > 1000',
                'status': 'ok',
                'comparison': {
                    'counts': {'candidate': 21},
                    'trade_count_retention': 0.42,
                },
                'promotion': {'passed': False, 'score': None},
                'cleanup': {
                    'attempted': True,
                    'reason': 'loser_candidate_deleted',
                    'strategy_name': 'Batch__cand002',
                    'status': 'ok',
                    'action': 'deleted',
                },
            },
        ],
        'best_candidate': {
            'rank': 1,
            'strategy_name': 'Batch__cand001',
            'expression': 'strength < 90',
            'status': 'ok',
            'promotion': {'passed': True, 'score': 0.73},
        },
        'cleanup_summary': {
            'attempted_count': 1,
            'deleted_count': 1,
            'kept_count': 1,
            'failed_count': 0,
            'items': [
                {
                    'attempted': False,
                    'reason': 'best_candidate_kept',
                    'strategy_name': 'Batch__cand001',
                },
                {
                    'attempted': True,
                    'reason': 'loser_candidate_deleted',
                    'strategy_name': 'Batch__cand002',
                    'status': 'ok',
                    'action': 'deleted',
                },
            ],
        },
    })
    return result


def test_build_research_report_includes_iteration_fields():
    report = build_research_report(_iteration_result(), strategy_name='Batch')

    assert report['phase'] == 'candidates_evaluated'
    assert report['iteration_plan']['candidate_count'] == 2
    assert report['candidates'][0]['strategy_name'] == 'Batch__cand001'
    assert report['best_candidate']['strategy_name'] == 'Batch__cand001'
    assert report['cleanup_summary']['deleted_count'] == 1


def test_build_research_report_includes_retention_selection():
    result = _result()
    result['retention_selection'] = {'selected_count': 5, 'fallback_count': 2}

    report = build_research_report(result, strategy_name='RetentionResearch')

    assert report['retention_selection']['selected_count'] == 5
    assert report['retention_selection']['fallback_count'] == 2


def test_render_research_report_markdown_contains_iteration_sections():
    markdown = render_research_report_markdown(build_research_report(_iteration_result(), strategy_name='Batch'))

    assert '## Candidate Iteration' in markdown
    assert '## Candidate Ranking' in markdown
    assert '## Cleanup Summary' in markdown
    assert '| rank | strategy | expression | status | passed | score | trade_count | retention | cleanup |' in markdown
    assert 'Batch__cand001' in markdown
    assert 'strength < 90' in markdown
    assert 'loser_candidate_deleted' in markdown

    all_failed = _iteration_result()
    all_failed['phase'] = 'candidate_iteration'
    all_failed['best_candidate'] = None
    all_failed['candidates'][0]['rank'] = None
    all_failed['candidates'][0]['promotion'] = None
    all_failed['candidates'][0]['comparison'] = None
    all_failed['cleanup_summary']['items'].append(None)

    failed_markdown = render_research_report_markdown(build_research_report(all_failed, strategy_name='Batch'))

    assert '## Candidate Ranking' in failed_markdown


def test_render_research_report_markdown_contains_retention_sections():
    report = build_research_report({
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'strategy_name': 'RetentionResearch',
        'baseline_csv': 'baseline.csv',
        'iteration_plan': {'candidate_count': 1},
        'retention_selection': {
            'pool_count': 3,
            'selected_count': 1,
            'passed_count': 1,
            'fallback_count': 0,
            'min_estimated_retention': 0.4,
        },
        'candidates': [{
            'rank': 1,
            'strategy_name': 'RetentionResearch__cand001',
            'expression': 'capital <= 2000',
            'status': 'ok',
            'retention_estimate': {'estimated_retention': 0.6},
            'retention_filter_passed': True,
            'retention_fallback_used': False,
            'promotion': {'passed': False, 'score': 100.0},
            'comparison': {
                'candidate_summary': {'trade_count': 10},
                'trade_count_retention': 0.3,
            },
            'rank_score': {
                'promotion_score': 100.0,
                'trade_count_retention': 0.3,
                'retention_penalty': 0.75,
                'adjusted_score': 75.0,
            },
            'cleanup': {'reason': 'best_candidate_deleted'},
        }],
        'best_candidate': {
            'strategy_name': 'RetentionResearch__cand001',
            'expression': 'capital <= 2000',
            'promotion': {'passed': False},
        },
        'cleanup_summary': {'deleted_count': 1, 'kept_count': 0, 'failed_count': 0},
    }, strategy_name='RetentionResearch')

    markdown = render_research_report_markdown(report)

    assert '## Retention-Aware Candidate Selection' in markdown
    assert '## Retention-Penalized Ranking' in markdown
    assert 'estimated_retention' in markdown
    assert 'adjusted_score' in markdown
    assert 'selected_count: 1' in markdown
    assert 'passed_count: 1' in markdown
    assert 'fallback_count: 0' in markdown
    assert '| RetentionResearch__cand001 | capital <= 2000 | 0.6 | True | False |' in markdown
    assert '| 1 | RetentionResearch__cand001 | 100.0 | 0.3 | 0.75 | 75.0 |' in markdown


def test_report_renders_score_baseline_comparability_section():
    result = {
        'status': 'ok',
        'strategy_name': 'WideV1IterationV2',
        'baseline_csv': 'cand003.csv',
        'iteration_plan': {'score_reference_csv': 'wide.csv'},
        'candidates': [{
            'rank': 1,
            'strategy_name': 'Cand005',
            'expression': 'A and B',
            'status': 'ok',
            'promotion': {'passed': True, 'score': 2554.7},
            'reference_promotion': {'passed': True, 'score': 13497.6},
            'rank_score': {
                'score_basis': 'reference',
                'promotion_score': 13497.6,
                'incremental_promotion_score': 2554.7,
                'reference_promotion_score': 13497.6,
                'trade_count': 36096,
                'trade_count_retention': 0.8817,
                'retention_penalty': 1.0,
                'adjusted_score': 13497.6,
            },
            'comparison': {'trade_count_retention': 0.9777, 'counts': {'candidate': 36096}},
            'reference_comparison': {'trade_count_retention': 0.8817, 'counts': {'candidate': 36096}},
        }],
        'best_candidate': {'strategy_name': 'Cand005', 'expression': 'A and B'},
    }

    report = build_research_report(result, strategy_name='WideV1IterationV2')
    markdown = render_research_report_markdown(report)

    assert '## Score Baseline Comparability' in markdown
    assert 'score_reference_csv: wide.csv' in markdown
    assert 'score_basis: reference' in markdown
    assert 'incremental_promotion_score' in markdown
    assert 'reference_promotion_score' in markdown
    assert 'adjusted_score values are directly comparable only when score_reference_csv is identical' in markdown


def test_render_research_report_markdown_contains_iteration_v2_section():
    report = build_research_report({
        'status': 'ok',
        'strategy_name': 'V2Run',
        'iteration_v2': {
            'status': 'ok',
            'mode': 'best_feature_mix',
            'primary_feature': 'B_시가총액',
            'secondary_features': ['B_체결강도', 'B_등락율'],
            'candidate_count': 3,
            'type_counts': {
                'primary_variant': 1,
                'primary_secondary_combo': 1,
                'secondary_only': 1,
            },
        },
    }, strategy_name='V2Run')

    markdown = render_research_report_markdown(report)

    assert '## Iteration Loop v2 Candidate Generation' in markdown
    assert 'best_feature_mix' in markdown
    assert 'B_시가총액' in markdown
    assert 'primary_secondary_combo' in markdown


def test_render_research_report_markdown_contains_iteration_v3_section():
    markdown = render_research_report_markdown({
        'status': 'ok',
        'name': 'WideV1IterationV3_20260423',
        'baseline_csv': 'cand005.csv',
        'score_reference_csv': 'wide.csv',
        'trade_counts': {'baseline': 36096, 'candidate': 35000, 'common': 34000},
        'iteration_v3': {
            'status': 'ok',
            'mode': 'best_feature_mix_v3',
            'primary_feature': 'B_시가총액',
            'trade_amount_feature': 'B_당일거래대금',
            'secondary_features': ['B_체결강도', 'B_등락율', 'B_당일거래대금'],
            'candidate_count': 10,
            'type_counts': {
                'v3_tighten_secondary': 4,
                'v3_repair_trade_amount': 3,
                'v3_replace_secondary': 3,
                'v3_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': (
                    '66.999 <= 시가총액 < 2_580 and '
                    '1805.7 <= 당일거래대금 < 3654.4'
                ),
                'reference_adjusted_score': 13497.662902097409,
                'skip_backtest': True,
            },
        },
    })

    assert '## Iteration Loop v3 Candidate Generation' in markdown
    assert '- mode: best_feature_mix_v3' in markdown
    assert 'v3_tighten_secondary: 4' in markdown
    assert 'v3_control_keep_best: 1' in markdown
    assert 'control_strategy_name: WideV1IterationV2_20260423__cand005' in markdown
    assert 'control_skip_backtest: True' in markdown


def test_render_research_report_markdown_contains_iteration_v4_section():
    result = {
        'status': 'ok',
        'strategy_name': 'WideV1IterationV4_20260424',
        'baseline_csv': 'cand005.csv',
        'iteration_v4': {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'primary_feature': 'B_시가총액',
            'trade_amount_feature': 'B_당일거래대금',
            'secondary_features': ['B_체결강도', 'B_등락율'],
            'candidate_count': 10,
            'type_counts': {
                'v4_tighten_secondary': 3,
                'v4_repair_trade_amount': 2,
                'v4_replace_secondary': 3,
                'v4_relax_trade_amount': 2,
                'v4_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': (
                    '66.999 <= 시가총액 < 2_580 and '
                    '1805.7 <= 당일거래대금 < 3654.4'
                ),
                'reference_adjusted_score': 13497.662902097409,
                'skip_backtest': True,
            },
        },
        'retention_selection': {
            'phase': 'rowset_diverse_candidates_selected',
            'proxy_group_count': 4,
            'skipped_duplicate_proxy_count': 6,
            'quota_summary': {
                'v4_repair_trade_amount': {'target': 2, 'selected': 2, 'shortfall': 0},
                'v4_replace_secondary': {'target': 2, 'selected': 2, 'shortfall': 0},
            },
        },
    }

    report = build_research_report(result, strategy_name='WideV1IterationV4_20260424')
    markdown = render_research_report_markdown(report)

    assert report['iteration_v4']['mode'] == 'best_feature_mix_v4'
    assert '## Iteration Loop v4 Row-Set Diversity' in markdown
    assert '- mode: best_feature_mix_v4' in markdown
    assert 'v4_repair_trade_amount: 2' in markdown
    assert '- proxy_group_count: 4' in markdown
    assert '- skipped_duplicate_proxy_count: 6' in markdown
    assert 'quota v4_repair_trade_amount: target=2, selected=2, shortfall=0' in markdown
    assert 'control_strategy_name: WideV1IterationV2_20260423__cand005' in markdown


def test_render_research_report_markdown_omits_disabled_iteration_v2_section():
    report = build_research_report({
        'status': 'ok',
        'strategy_name': 'DefaultRun',
        'iteration_v2': {'status': 'disabled', 'mode': ''},
    }, strategy_name='DefaultRun')

    markdown = render_research_report_markdown(report)

    assert '## Iteration Loop v2 Candidate Generation' not in markdown


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
