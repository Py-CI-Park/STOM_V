from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none, reportUnknownArgumentType=none, reportUnknownMemberType=none, reportUnknownVariableType=none, reportUnusedCallResult=none

import json
import runpy
from pathlib import Path
import sys
from typing import Any, TypeAlias

import pandas as pd
import pytest

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_metrics import NUMERIC_COLUMNS
from cli.research_v3_tiebreak import (
    HOLD_ROW_SET_EQUIVALENCE,
    HOLD_SELECTION_DIVERSITY_REVIEW,
    PROCEED_TO_V4_PLAN,
    analyze_tie_row_sets,
    build_v3_tie_break_analysis,
    choose_representative,
    render_v3_tie_break_markdown,
    resolve_candidate_csv_path,
    write_v3_tie_break_report,
)

JsonDict: TypeAlias = dict[str, Any]

ROW_SET_DIVERSITY_COMMAND = '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계'
SELECTION_DIVERSITY_COMMAND = '$brainstorming Wide v1 v3 selection diversity 보강 설계'
V4_PLAN_COMMAND = '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성'
NO_TIE_MESSAGE = 'No tie-break analysis was needed because fewer than 2 candidates were available.'

SYMBOL_COLUMN = INSTRUMENT_COLUMNS[1]
BUY_TIME_COLUMN = REQUIRED_KEY_COLUMNS[0]
BUY_PRICE_COLUMN = OPTIONAL_KEY_COLUMNS[0]
SELL_TIME_COLUMN = NUMERIC_COLUMNS[1]
SELL_PRICE_COLUMN = NUMERIC_COLUMNS[3]
RETURN_COLUMN = NUMERIC_COLUMNS[5]
PROFIT_COLUMN = NUMERIC_COLUMNS[6]


def _trade_csv(path: Path, rows: list[JsonDict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _row(symbol: str, buy_time: int, buy_price: int, profit: int = 100) -> JsonDict:
    return {
        SYMBOL_COLUMN: symbol,
        BUY_TIME_COLUMN: buy_time,
        BUY_PRICE_COLUMN: buy_price,
        SELL_TIME_COLUMN: buy_time + 100,
        SELL_PRICE_COLUMN: buy_price + 1,
        RETURN_COLUMN: 1.0,
        PROFIT_COLUMN: profit,
        'R_MFE': 1.2,
        'R_MAE': -0.2,
    }


def _candidate(
    name: str,
    csv_path: str,
    expression: str,
    *,
    rank: int,
    adjusted_score: float = 100.0,
) -> JsonDict:
    return {
        'strategy_name': name,
        'candidate_csv': csv_path,
        'expression': expression,
        'rank': rank,
        'rank_score': {
            'adjusted_score': adjusted_score,
            'reference_promotion_score': adjusted_score,
            'trade_count': 2.0,
            'trade_count_retention': 1.0,
            'date_concentration': 0.5,
            'symbol_concentration': 0.5,
        },
    }


def _runtime(candidates: list[JsonDict]) -> JsonDict:
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'iteration_v3': {
            'type_counts': {
                'v3_repair_trade_amount': 1,
                'v3_replace_secondary': 1,
                'v3_tighten_secondary': 1,
                'v3_control_keep_best': 1,
            },
            'candidates': [
                {
                    'expression': 'base',
                    'v3_candidate_type': 'v3_control_keep_best',
                },
                {
                    'expression': 'base and repair',
                    'v3_candidate_type': 'v3_repair_trade_amount',
                },
                {
                    'expression': 'base and replace',
                    'v3_candidate_type': 'v3_replace_secondary',
                },
                {
                    'expression': 'base and tighten and extra',
                    'v3_candidate_type': 'v3_tighten_secondary',
                },
            ],
        },
        'retention_selection': {
            'retention_candidates': [
                {
                    'expression': 'base and repair',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and replace',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
                {
                    'expression': 'base and tighten and extra',
                    'retention_filter_passed': True,
                    'retention_fallback_used': False,
                },
            ],
        },
        'expression_result': {
            'selected_candidates': [
                {
                    'expression': 'base and tighten and extra',
                },
            ],
        },
        'candidates': candidates,
        'best_candidate': candidates[0] if candidates else None,
    }


def test_resolve_candidate_csv_path_uses_runtime_root_for_relative_paths(tmp_path: Path):
    path = resolve_candidate_csv_path(tmp_path, {'candidate_csv': 'backtest/csv/cand001.csv'})

    assert path == tmp_path / 'backtest' / 'csv' / 'cand001.csv'


def test_analyze_tie_row_sets_groups_identical_candidate_csvs(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'all_identical'
    assert result['group_count'] == 1
    assert result['groups'][0]['row_count'] == 2
    assert result['groups'][0]['members'] == ['cand001', 'cand002']
    assert result['groups'][0]['representative'] == 'cand002'


def test_analyze_tie_row_sets_groups_partially_distinct_candidate_csvs(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_c = _trade_csv(tmp_path / 'cand003.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
        _candidate('cand003', str(csv_c), 'base and replace', rank=3),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'partially_distinct'
    assert result['group_count'] == 2
    assert result['groups'][0]['representative'] == 'cand002'
    assert result['groups'][0]['members'] == ['cand001', 'cand002']
    assert result['groups'][1]['representative'] == 'cand003'


def test_analyze_tie_row_sets_reports_missing_csv(tmp_path: Path):
    runtime = _runtime([
        _candidate('cand001', str(tmp_path / 'missing.csv'), 'base and tighten and extra', rank=1),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'error'
    assert result['errors']
    assert 'missing.csv' in result['errors'][0]['message']


def test_analyze_tie_row_sets_marks_single_candidate_as_not_evaluated(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
    ])

    result = analyze_tie_row_sets(runtime, runtime_root=tmp_path, top_n=10)

    assert result['status'] == 'not_evaluated'
    assert result['group_count'] == 1


def test_build_v3_tie_break_analysis_treats_single_candidate_as_no_tie(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['row_set_gate']['status'] == 'not_evaluated'
    assert analysis['decision'] == HOLD_SELECTION_DIVERSITY_REVIEW
    assert 'all_distinct' not in analysis['quant_interpretation']
    assert NO_TIE_MESSAGE in analysis['quant_interpretation']


def test_choose_representative_prefers_fewer_conditions_then_family_priority():
    members: list[JsonDict] = [
        {
            'strategy_name': 'tighten',
            'expression': 'base and tighten and extra',
            'v3_candidate_type': 'v3_tighten_secondary',
            'rank': 1,
            'index': 0,
        },
        {
            'strategy_name': 'replace',
            'expression': 'base and replace',
            'v3_candidate_type': 'v3_replace_secondary',
            'rank': 1,
            'index': 1,
        },
        {
            'strategy_name': 'repair',
            'expression': 'base and repair',
            'v3_candidate_type': 'v3_repair_trade_amount',
            'rank': 9,
            'index': 2,
        },
    ]

    representative = choose_representative(members)

    assert representative['strategy_name'] == 'repair'


def test_build_v3_tie_break_analysis_routes_identical_rows_to_hold(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == HOLD_ROW_SET_EQUIVALENCE
    assert analysis['row_set_gate']['status'] == 'all_identical'
    assert analysis['next_command'] == ROW_SET_DIVERSITY_COMMAND


def test_build_v3_tie_break_analysis_holds_distinct_rows_when_selection_stays_one_family(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == HOLD_SELECTION_DIVERSITY_REVIEW
    assert analysis['row_set_gate']['status'] == 'all_distinct'
    assert analysis['next_command'] == SELECTION_DIVERSITY_COMMAND


def test_build_v3_tie_break_analysis_routes_distinct_rows_to_v4(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    runtime = _runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ])
    runtime['expression_result']['selected_candidates'] = [
        {'expression': 'base and tighten and extra'},
        {'expression': 'base and repair'},
    ]
    runtime_path = tmp_path / 'runtime.json'
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False), encoding='utf-8')

    analysis = build_v3_tie_break_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == PROCEED_TO_V4_PLAN
    assert analysis['row_set_gate']['status'] == 'all_distinct'
    assert analysis['next_command'] == V4_PLAN_COMMAND


def test_render_v3_tie_break_markdown_contains_decision_and_group_count():
    markdown = render_v3_tie_break_markdown({
        'decision': HOLD_ROW_SET_EQUIVALENCE,
        'next_command': ROW_SET_DIVERSITY_COMMAND,
        'runtime_path': 'runtime.json',
        'runtime_root': '.',
        'top_n': 10,
        'row_set_gate': {
            'status': 'all_identical',
            'group_count': 1,
            'candidate_count': 2,
            'groups': [
                {
                    'group_id': 1,
                    'representative': 'cand002',
                    'members': ['cand001', 'cand002'],
                    'row_count': 2,
                },
            ],
        },
        'family_gate': {
            'selected_type_counts': {'v3_tighten_secondary': 2},
            'executed_type_counts': {'v3_tighten_secondary': 2},
        },
        'quant_interpretation': [
            'cand001 is not a unique winner',
        ],
    })

    assert '# Wide v1 v3 tie-break and ranking reinforcement' in markdown
    assert 'decision=HOLD_ROW_SET_EQUIVALENCE' in markdown
    assert 'group_count=1' in markdown
    assert ROW_SET_DIVERSITY_COMMAND in markdown


def test_render_v3_tie_break_markdown_uses_no_tie_sentence_for_single_candidate():
    markdown = render_v3_tie_break_markdown({
        'decision': HOLD_SELECTION_DIVERSITY_REVIEW,
        'next_command': SELECTION_DIVERSITY_COMMAND,
        'runtime_path': 'runtime.json',
        'runtime_root': '.',
        'top_n': 10,
        'row_set_gate': {
            'status': 'not_evaluated',
            'group_count': 1,
            'candidate_count': 1,
            'groups': [],
        },
        'family_gate': {
            'selected_type_counts': {'v3_tighten_secondary': 1},
            'executed_type_counts': {'v3_tighten_secondary': 1},
        },
        'quant_interpretation': [NO_TIE_MESSAGE],
    })

    assert 'row_set_identity_status=not_evaluated' in markdown
    assert NO_TIE_MESSAGE in markdown
    assert 'all_distinct' not in markdown


def test_write_v3_tie_break_report_writes_markdown_and_returns_analysis(tmp_path: Path):
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'reports' / 'tie_break.md'
    runtime_path.write_text(json.dumps(_runtime([
        _candidate('cand001', str(csv_a), 'base and tighten and extra', rank=1),
        _candidate('cand002', str(csv_b), 'base and repair', rank=2),
    ]), ensure_ascii=False), encoding='utf-8')

    analysis = write_v3_tie_break_report(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        output_path=output_path,
        top_n=10,
    )

    assert analysis['decision'] == HOLD_ROW_SET_EQUIVALENCE
    assert output_path.exists()
    assert output_path.read_text(encoding='utf-8').startswith('# Wide v1 v3 tie-break and ranking reinforcement')


def test_analyze_wide_v1_v3_tie_break_script_uses_defaults_and_prints_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
):
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v3_tie_break.py'
    output_path = tmp_path / 'generated.md'
    captured: dict[str, Any] = {}

    def fake_write_v3_tie_break_report(**kwargs: Any) -> JsonDict:
        captured.update(kwargs)
        Path(kwargs['output_path']).write_text('# generated\n', encoding='utf-8')
        return {
            'decision': HOLD_ROW_SET_EQUIVALENCE,
            'next_command': '$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계',
        }

    monkeypatch.setattr('cli.research_v3_tiebreak.write_v3_tie_break_report', fake_write_v3_tie_break_report)
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--output',
            str(output_path),
            '--top-n',
            '7',
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert captured == {
        'runtime_path': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3\backtest\temp\wide_v1_iteration_v3_20260423.json'),
        'runtime_root': Path(r'C:\System_Trading\STOM\STOM_V.wt-wide-v3'),
        'output_path': output_path,
        'top_n': 7,
    }
    assert 'decision=HOLD_ROW_SET_EQUIVALENCE' in stdout
    assert 'next_command=$brainstorming Wide v1 v4 row-set diversity 후보 생성 설계' in stdout
    assert f'wrote={output_path}' in stdout
