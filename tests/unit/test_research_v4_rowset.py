from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none, reportUnknownMemberType=none, reportUnusedCallResult=none

import json
from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_metrics import NUMERIC_COLUMNS
from cli.research_v4_rowset import (
    PROCEED_TO_PROMOTE_WFO_PLAN,
    build_v4_rowset_diversity_analysis,
    render_v4_rowset_diversity_markdown,
    write_v4_rowset_diversity_report,
)

JsonDict: TypeAlias = dict[str, Any]

SYMBOL_COLUMN = INSTRUMENT_COLUMNS[1]
BUY_TIME_COLUMN = REQUIRED_KEY_COLUMNS[0]
BUY_PRICE_COLUMN = OPTIONAL_KEY_COLUMNS[0]
SELL_TIME_COLUMN = NUMERIC_COLUMNS[1]
SELL_PRICE_COLUMN = NUMERIC_COLUMNS[3]
RETURN_COLUMN = NUMERIC_COLUMNS[5]
PROFIT_COLUMN = NUMERIC_COLUMNS[6]


def _row(symbol: str, buy_time: int, buy_price: int) -> JsonDict:
    return {
        SYMBOL_COLUMN: symbol,
        BUY_TIME_COLUMN: buy_time,
        BUY_PRICE_COLUMN: buy_price,
        SELL_TIME_COLUMN: buy_time + 100,
        SELL_PRICE_COLUMN: buy_price + 1,
        RETURN_COLUMN: 1.0,
        PROFIT_COLUMN: 100,
        'R_MFE': 1.2,
        'R_MAE': -0.2,
    }


def _trade_csv(path: Path, rows: list[JsonDict]) -> Path:
    pd.DataFrame(rows).to_csv(path, index=False, encoding='utf-8')
    return path


def _candidate(name: str, csv_path: Path, *, rank: int, score: float) -> JsonDict:
    return {
        'strategy_name': name,
        'candidate_csv': str(csv_path),
        'status': 'ok',
        'rank': rank,
        'rank_score': {
            'adjusted_score': score,
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
        'iteration_v4': {
            'status': 'ok',
            'mode': 'best_feature_mix_v4',
            'type_counts': {
                'v4_replace_secondary': 1,
                'v4_relax_trade_amount': 1,
                'v4_tighten_secondary': 1,
            },
        },
        'candidate_specs': [
            {
                'strategy_name': 'cand001',
                'source_candidate': {'v4_candidate_type': 'v4_replace_secondary'},
            },
            {
                'strategy_name': 'cand002',
                'source_candidate': {'v4_candidate_type': 'v4_relax_trade_amount'},
            },
            {
                'strategy_name': 'cand003',
                'source_candidate': {'v4_candidate_type': 'v4_tighten_secondary'},
            },
        ],
        'candidates': candidates,
        'best_candidate': candidates[0],
    }


def test_build_v4_rowset_diversity_analysis_uses_all_executed_candidates(tmp_path: Path):
    csv_1 = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_2 = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('C', 3, 300)])
    csv_3 = _trade_csv(tmp_path / 'cand003.csv', [_row('D', 4, 400), _row('E', 5, 500)])
    runtime_path = tmp_path / 'runtime.json'
    _ = runtime_path.write_text(
        json.dumps(
            _runtime([
                _candidate('cand001', csv_1, rank=1, score=100.0),
                _candidate('cand002', csv_2, rank=2, score=90.0),
                _candidate('cand003', csv_3, rank=3, score=80.0),
            ]),
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    analysis = build_v4_rowset_diversity_analysis(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        top_n=10,
    )

    assert analysis['decision'] == PROCEED_TO_PROMOTE_WFO_PLAN
    assert analysis['row_set_gate']['candidate_count'] == 3
    assert analysis['row_set_gate']['status'] == 'all_distinct'
    assert analysis['row_set_gate']['group_count'] == 3
    assert analysis['family_gate']['executed_type_counts'] == {
        'v4_relax_trade_amount': 1,
        'v4_replace_secondary': 1,
        'v4_tighten_secondary': 1,
    }


def test_write_v4_rowset_diversity_report_writes_v4_markdown(tmp_path: Path):
    csv_1 = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100)])
    csv_2 = _trade_csv(tmp_path / 'cand002.csv', [_row('B', 2, 200)])
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'report.md'
    _ = runtime_path.write_text(
        json.dumps(
            _runtime([
                _candidate('cand001', csv_1, rank=1, score=100.0),
                _candidate('cand002', csv_2, rank=2, score=90.0),
            ]),
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    analysis = write_v4_rowset_diversity_report(
        runtime_path=runtime_path,
        runtime_root=tmp_path,
        output_path=output_path,
        top_n=10,
    )
    markdown = output_path.read_text(encoding='utf-8')

    assert analysis['row_set_gate']['candidate_count'] == 2
    assert '# Wide v1 v4 actual row-set diversity' in markdown
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in markdown
    assert 'row_set_identity_status=all_distinct' in markdown


def test_render_v4_rowset_diversity_markdown_contains_next_command():
    markdown = render_v4_rowset_diversity_markdown({
        'decision': PROCEED_TO_PROMOTE_WFO_PLAN,
        'next_command': '$writing-plans Wide v1 v4 promote 및 WFO 검증 계획 작성',
        'runtime_path': 'runtime.json',
        'runtime_root': '.',
        'top_n': 10,
        'row_set_gate': {
            'status': 'all_distinct',
            'candidate_count': 2,
            'group_count': 2,
            'groups': [],
            'errors': [],
        },
        'family_gate': {
            'executed_type_counts': {
                'v4_replace_secondary': 1,
                'v4_relax_trade_amount': 1,
            },
        },
        'quant_interpretation': ['Actual candidate row sets are execution-distinct.'],
    })

    assert 'next_command=$writing-plans Wide v1 v4 promote 및 WFO 검증 계획 작성' in markdown
    assert 'Actual candidate row sets are execution-distinct.' in markdown
