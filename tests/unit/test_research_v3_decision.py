from __future__ import annotations

import json
import runpy
from pathlib import Path
import sys

import pandas as pd
import pytest

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_metrics import NUMERIC_COLUMNS
from cli.research_v3_decision import (
    DECISION_HOLD_V3_TIE_REVIEW,
    DECISION_PROCEED_TO_V4_PLAN,
    DECISION_RECHECK_CONTROL,
    build_v3_decision_analysis,
    classify_top_tie,
    family_distribution,
    read_runtime_json,
    recompute_control_reference,
    render_v3_decision_markdown,
    write_v3_decision_report,
)

SYMBOL_COLUMN = INSTRUMENT_COLUMNS[1]
BUY_TIME_COLUMN = REQUIRED_KEY_COLUMNS[0]
BUY_PRICE_COLUMN = OPTIONAL_KEY_COLUMNS[0]
SELL_TIME_COLUMN = NUMERIC_COLUMNS[1]
SELL_PRICE_COLUMN = NUMERIC_COLUMNS[3]
RETURN_COLUMN = NUMERIC_COLUMNS[5]
PROFIT_COLUMN = NUMERIC_COLUMNS[6]


def _trade_csv(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _rows():
    return [
        {
            SYMBOL_COLUMN: 'A',
            BUY_TIME_COLUMN: 20250101090000,
            SELL_TIME_COLUMN: 20250101090100,
            BUY_PRICE_COLUMN: 100,
            SELL_PRICE_COLUMN: 101,
            RETURN_COLUMN: 1.0,
            PROFIT_COLUMN: 1000,
            'R_MFE': 1.2,
            'R_MAE': -0.2,
        },
        {
            SYMBOL_COLUMN: 'B',
            BUY_TIME_COLUMN: 20250101090200,
            SELL_TIME_COLUMN: 20250101090300,
            BUY_PRICE_COLUMN: 200,
            SELL_PRICE_COLUMN: 198,
            RETURN_COLUMN: -1.0,
            PROFIT_COLUMN: -2000,
            'R_MFE': 0.1,
            'R_MAE': -1.3,
        },
    ]


def _candidate(
    strategy_name: str,
    expression: str,
    score: float,
    retention: float = 1.0,
    *,
    rank: int | None = None,
    trade_count: float = 2.0,
    date_concentration: float = 0.5,
    symbol_concentration: float = 0.5,
):
    candidate = {
        'strategy_name': strategy_name,
        'expression': expression,
        'candidate_csv': f'backtest/csv/{strategy_name}.csv',
        'rank_score': {
            'adjusted_score': score,
            'reference_promotion_score': score,
            'trade_count': trade_count,
            'trade_count_retention': retention,
            'date_concentration': date_concentration,
            'symbol_concentration': symbol_concentration,
        },
    }
    if rank is not None:
        candidate['rank'] = rank
    return candidate


def _runtime(candidates: list[dict], *, control_score=None, selected_candidates=None):
    if selected_candidates is None:
        selected_candidates = list(candidates)
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'iteration_v3': {
            'type_counts': {
                'v3_tighten_secondary': 2,
                'v3_repair_trade_amount': 1,
                'v3_replace_secondary': 1,
                'v3_control_keep_best': 1,
            },
            'control_candidate': {
                'strategy_name': 'WideV1IterationV2_20260423__cand005',
                'expression': '66.999 <= market_cap < 2_580 and 1805.7 <= day_volume < 3654.4',
                'reference_adjusted_score': control_score,
                'skip_backtest': True,
            },
            'candidates': [
                {
                    'expression': 'base and tighten',
                    'v3_candidate_type': 'v3_tighten_secondary',
                },
                {
                    'expression': 'base and repair',
                    'v3_candidate_type': 'v3_repair_trade_amount',
                },
            ],
        },
        'retention_selection': {
            'retention_candidates': [
                {
                    'expression': 'base and tighten',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and repair',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
        'expression_result': {
            'selected_candidates': selected_candidates,
        },
        'candidates': candidates,
        'best_candidate': candidates[0] if candidates else None,
    }


def test_read_runtime_json_accepts_utf16_artifact(tmp_path):
    path = tmp_path / 'runtime.json'
    path.write_text(json.dumps({'status': 'ok'}, ensure_ascii=False), encoding='utf-16')

    assert read_runtime_json(path) == {'status': 'ok'}


def test_read_runtime_json_accepts_utf8_sig_artifact(tmp_path):
    path = tmp_path / 'runtime_utf8_sig.json'
    path.write_text(json.dumps({'status': 'utf8-sig'}, ensure_ascii=False), encoding='utf-8-sig')

    assert read_runtime_json(path) == {'status': 'utf8-sig'}


def test_read_runtime_json_accepts_utf16_le_artifact(tmp_path):
    path = tmp_path / 'runtime_utf16_le.json'
    path.write_text(json.dumps({'status': 'utf16-le'}, ensure_ascii=False), encoding='utf-16-le')

    assert read_runtime_json(path) == {'status': 'utf16-le'}


def test_recompute_control_reference_returns_non_null_score(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])

    result = recompute_control_reference(reference_csv, control_csv)

    assert result['status'] == 'ok'
    assert result['reference_adjusted_score'] is not None
    assert result['comparison']['counts']['baseline'] == 2
    assert result['comparison']['counts']['candidate'] == 1


def test_recompute_control_reference_reports_missing_csv(tmp_path):
    result = recompute_control_reference(tmp_path / 'missing-reference.csv', tmp_path / 'missing-control.csv')

    assert result['status'] == 'error'
    assert result['reference_adjusted_score'] is None
    assert 'missing-reference.csv' in result['message']


def test_classify_top_tie_detects_score_and_metric_tie():
    candidates = [
        _candidate('cand001', 'base and tighten', 13497.6, retention=0.88),
        _candidate('cand002', 'base and repair', 13497.6, retention=0.88),
    ]

    result = classify_top_tie(candidates, top_n=10)

    assert result['status'] == 'rank_metric_tie'
    assert result['score_tie'] is True
    assert result['metric_tie'] is True
    assert result['top_count'] == 2
    assert result['tie_candidate_count'] == 2
    assert result['row_set_identity_status'] == 'not_evaluated'


def test_classify_top_tie_detects_ranking_tie_when_secondary_metrics_differ():
    candidates = [
        _candidate('cand001', 'base and tighten', 13497.6, retention=0.88),
        _candidate('cand002', 'base and repair', 13497.6, retention=0.75),
    ]

    result = classify_top_tie(candidates, top_n=10)

    assert result['status'] == 'ranking_tie'
    assert result['score_tie'] is True
    assert result['metric_tie'] is False
    assert result['tie_candidate_count'] == 2
    assert result['row_set_identity_status'] == 'not_evaluated'


def test_classify_top_tie_detects_best_score_cohort_tie_with_lower_ranked_candidates_present():
    candidates = [
        _candidate('cand001', 'base and tighten', 10.0, retention=0.88),
        _candidate('cand002', 'base and repair', 10.0, retention=0.88),
        _candidate('cand003', 'base and replace', 9.0, retention=0.70),
    ]

    result = classify_top_tie(candidates, top_n=10)

    assert result['status'] == 'rank_metric_tie'
    assert result['top_count'] == 3
    assert result['score_tie'] is True
    assert result['metric_tie'] is True
    assert result['tie_candidate_count'] == 2
    assert result['tie_candidates'] == ['cand001', 'cand002']
    assert result['row_set_identity_status'] == 'not_evaluated'


def test_classify_top_tie_returns_not_enough_candidates_for_single_candidate():
    result = classify_top_tie([
        _candidate('cand001', 'base and tighten', 13497.6),
    ])

    assert result['status'] == 'not_enough_candidates'
    assert result['top_count'] == 1
    assert result['score_tie'] is False
    assert result['metric_tie'] is False
    assert result['row_set_identity_status'] == 'not_evaluated'


def test_classify_top_tie_returns_not_tied_when_scores_differ():
    result = classify_top_tie([
        _candidate('cand001', 'base and tighten', 13498.0),
        _candidate('cand002', 'base and repair', 13497.0),
    ])

    assert result['status'] == 'not_tied'
    assert result['top_count'] == 2
    assert result['score_tie'] is False
    assert result['metric_tie'] is False
    assert result['row_set_identity_status'] == 'not_evaluated'


def test_classify_top_tie_sorts_by_rank_before_detecting_best_score_tie():
    result = classify_top_tie([
        _candidate('cand003', 'base and replace', 9.0, rank=3),
        _candidate('cand001', 'base and tighten', 10.0, rank=1),
        _candidate('cand002', 'base and repair', 10.0, rank=2),
    ])

    assert result['status'] == 'rank_metric_tie'
    assert result['top_candidates'][:3] == ['cand001', 'cand002', 'cand003']
    assert result['score_tie'] is True
    assert result['tie_candidate_count'] == 2
    assert result['tie_candidates'] == ['cand001', 'cand002']


def test_family_distribution_maps_executed_candidates_by_expression():
    runtime = _runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ])

    result = family_distribution(runtime)

    assert result['pool_type_counts']['v3_tighten_secondary'] == 2
    assert result['executed_type_counts']['v3_tighten_secondary'] == 1
    assert result['executed_type_counts']['v3_repair_trade_amount'] == 1
    assert result['retention_pass_type_counts'] == {
        'v3_tighten_secondary': 1,
        'v3_repair_trade_amount': 1,
    }


def test_family_distribution_tracks_selected_counts_and_unknown_executed():
    runtime = _runtime(
        [
            _candidate('cand001', 'base and tighten', 13497.6),
            _candidate('cand999', 'base and replace', 13496.0),
        ],
        selected_candidates=[
            _candidate('cand001', 'base and tighten', 13497.6),
            _candidate('cand002', 'base and repair', 13497.0),
        ],
    )

    result = family_distribution(runtime)

    assert result['selected_type_counts'] == {
        'v3_tighten_secondary': 1,
        'v3_repair_trade_amount': 1,
    }
    assert result['unknown_executed_strategies'] == ['cand999']


def test_family_distribution_prefers_expression_result_selected_candidates():
    runtime = _runtime(
        [
            _candidate('cand001', 'base and tighten', 13497.6),
            _candidate('cand002', 'base and repair', 13497.0),
        ],
        selected_candidates=[
            _candidate('cand001', 'base and tighten', 13497.6),
        ],
    )

    result = family_distribution(runtime)

    assert result['selected_type_counts'] == {
        'v3_tighten_secondary': 1,
    }


def test_family_distribution_reports_retention_pass_fallback_and_summary():
    runtime = _runtime(
        [
            _candidate('cand001', 'base and tighten', 13497.6),
        ],
        selected_candidates=[
            _candidate('cand001', 'base and tighten', 13497.6),
        ],
    )
    runtime['retention_selection']['retention_candidates'] = [
        {
            'expression': 'base and tighten',
            'retention_filter_passed': True,
            'retention_fallback_used': False,
        },
        {
            'expression': 'base and repair',
            'retention_filter_passed': True,
            'retention_fallback_used': False,
        },
        {
            'expression': 'base and replace',
            'retention_filter_passed': False,
            'retention_fallback_used': True,
        },
    ]
    runtime['iteration_v3']['candidates'].append({
        'expression': 'base and replace',
        'v3_candidate_type': 'v3_replace_secondary',
    })
    runtime['iteration_v3']['type_counts']['v3_replace_secondary'] = 1

    result = family_distribution(runtime)

    assert result['retention_pass_type_counts'] == {
        'v3_tighten_secondary': 1,
        'v3_repair_trade_amount': 1,
    }
    assert result['retention_fallback_type_counts'] == {
        'v3_replace_secondary': 1,
    }
    assert result['family_selection_summary'] == {
        'v3_repair_trade_amount': 'retention-pass only',
        'v3_replace_secondary': 'retention-fallback only',
        'v3_tighten_secondary': 'selected/executed',
    }


def test_build_v3_decision_analysis_prioritizes_recheck_control_when_control_fails(tmp_path):
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=tmp_path / 'missing-reference.csv',
        control_csv=tmp_path / 'missing-control.csv',
    )

    assert analysis['decision'] == DECISION_RECHECK_CONTROL
    assert analysis['control_score_gate']['status'] == 'error'


def test_build_v3_decision_analysis_holds_on_top10_tie(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert analysis['tie_gate']['score_tie'] is True
    assert analysis['quant_validity_gate']['reasons'] == [
        'top_candidates_score_tie',
        'top_candidates_metric_tie',
    ]
    assert analysis['control_score_gate']['stored_score_status'] == 'missing'
    assert analysis['control_score_gate']['status'] == 'ok'


def test_build_v3_decision_analysis_uses_score_tie_reason_without_ranking_reason(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6, retention=0.88),
        _candidate('cand002', 'base and repair', 13497.6, retention=0.75),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert analysis['tie_gate']['status'] == 'ranking_tie'
    assert analysis['quant_validity_gate']['reasons'] == ['top_candidates_score_tie']


def test_build_v3_decision_analysis_holds_when_best_score_cohort_ties_and_lower_scores_follow(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 10.0, retention=0.88),
        _candidate('cand002', 'base and repair', 10.0, retention=0.88),
        _candidate('cand003', 'base and replace', 9.0, retention=0.70),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert analysis['tie_gate']['score_tie'] is True
    assert analysis['tie_gate']['tie_candidate_count'] == 2


def test_build_v3_decision_analysis_sorts_unsorted_runtime_candidates_before_holding(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime = _runtime([
        _candidate('cand003', 'base and replace', 9.0, rank=3),
        _candidate('cand001', 'base and tighten', 10.0, rank=1),
        _candidate('cand002', 'base and repair', 10.0, rank=2),
    ])
    runtime['best_candidate'] = runtime['candidates'][1]
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert analysis['tie_gate']['score_tie'] is True
    assert analysis['tie_gate']['tie_candidate_count'] == 2
    assert analysis['tie_gate']['top_candidates'][:3] == ['cand001', 'cand002', 'cand003']


def test_build_v3_decision_analysis_rechecks_when_stored_control_score_mismatches_recomputed(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13498.0),
        _candidate('cand002', 'base and repair', 13497.0),
    ], control_score=999.0), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_RECHECK_CONTROL
    assert analysis['control_score_gate']['status'] == 'error'
    assert analysis['control_score_gate']['stored_score_status'] == 'mismatched'
    assert analysis['control_score_gate']['score_match'] is False
    assert 'control reference score mismatch' in analysis['control_score_gate']['message']


def test_build_v3_decision_analysis_allows_v4_when_control_passes_and_tie_is_absent(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13498.0),
        _candidate('cand002', 'base and repair', 13497.0),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_PROCEED_TO_V4_PLAN
    assert analysis['tie_gate']['score_tie'] is False
    assert analysis['control_score_gate']['status'] == 'ok'
    assert analysis['control_score_gate']['stored_score_status'] == 'missing'
    assert analysis['control_score_gate']['score_match'] is None


def test_build_v3_decision_analysis_accepts_missing_stored_control_score_when_recomputed_is_valid(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13498.0),
        _candidate('cand002', 'base and repair', 13497.0),
    ], control_score=None), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
    )

    assert analysis['decision'] == DECISION_PROCEED_TO_V4_PLAN
    assert analysis['control_score_gate']['status'] == 'ok'
    assert analysis['control_score_gate']['stored_reference_adjusted_score'] is None
    assert analysis['control_score_gate']['recomputed_reference_adjusted_score'] is not None
    assert analysis['control_score_gate']['stored_score_status'] == 'missing'


def test_render_v3_decision_markdown_contains_decision_and_next_command():
    analysis = {
        'decision': DECISION_RECHECK_CONTROL,
        'runtime': {'status': 'ok', 'phase': 'candidates_evaluated'},
        'control_score_gate': {'status': 'error', 'reference_adjusted_score': None, 'message': 'missing csv'},
        'tie_gate': {'status': 'rank_metric_tie', 'row_set_identity_status': 'not_evaluated'},
        'family_gate': {'pool_type_counts': {}, 'executed_type_counts': {}},
        'quant_validity_gate': {'blocked': True, 'reasons': ['control_score_missing']},
        'next_command': '$brainstorming Wide v1 v3 control score 재검증 설계',
    }

    markdown = render_v3_decision_markdown(analysis)

    assert '# Wide v1 v3 결과 분석 및 v4 여부 판단' in markdown
    assert 'decision=RECHECK_CONTROL' in markdown
    assert 'status=rank_metric_tie' in markdown
    assert 'row_set_identity_status=not_evaluated' in markdown
    assert '$brainstorming Wide v1 v3 control score 재검증 설계' in markdown


def test_write_v3_decision_report_writes_markdown(tmp_path):
    reference_csv = _trade_csv(tmp_path / 'reference.csv', _rows())
    control_csv = _trade_csv(tmp_path / 'control.csv', _rows()[:1])
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'decision.md'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', 'base and tighten', 13497.6),
        _candidate('cand002', 'base and repair', 13497.6),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = write_v3_decision_report(
        runtime_path=runtime_path,
        wide_reference_csv=reference_csv,
        control_csv=control_csv,
        output_path=output_path,
    )

    assert analysis['decision'] == DECISION_HOLD_V3_TIE_REVIEW
    assert output_path.read_text(encoding='utf-8').startswith('# Wide v1 v3 결과 분석')


def test_analyze_wide_v1_v3_decision_script_uses_defaults_and_prints_summary(monkeypatch, capsys, tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v3_decision.py'
    output_path = tmp_path / 'generated.md'
    captured = {}

    def fake_write_v3_decision_report(**kwargs):
        captured.update(kwargs)
        Path(kwargs['output_path']).write_text('# generated\n', encoding='utf-8')
        return {
            'decision': DECISION_PROCEED_TO_V4_PLAN,
            'next_command': '$writing-plans next step',
        }

    monkeypatch.setattr('cli.research_v3_decision.write_v3_decision_report', fake_write_v3_decision_report)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert captured == {
        'runtime_path': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json'),
        'wide_reference_csv': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv'),
        'control_csv': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv'),
        'output_path': output_path,
    }
    assert 'decision=PROCEED_TO_V4_PLAN' in stdout
    assert 'next_command=$writing-plans next step' in stdout
    assert f'wrote={output_path}' in stdout
