from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none, reportUnknownMemberType=none, reportUnusedCallResult=none

from pathlib import Path
from typing import Any, TypeAlias

import pandas as pd

from cli.research_compare import INSTRUMENT_COLUMNS, OPTIONAL_KEY_COLUMNS, REQUIRED_KEY_COLUMNS
from cli.research_iteration_v5 import (
    apply_actual_rowset_selection,
    planned_v5_execution_count,
    select_actual_rowset_representatives,
)
from cli.research_metrics import NUMERIC_COLUMNS

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


def _candidate(name: str, csv_path: Path, *, rank: int) -> JsonDict:
    return {
        'strategy_name': name,
        'candidate_csv': str(csv_path),
        'status': 'ok',
        'rank': rank,
        'selected_as_best': rank == 1,
        'rank_score': {
            'adjusted_score': 100.0 - rank,
            'trade_count': 2.0,
            'trade_count_retention': 1.0,
            'date_concentration': 0.5,
            'symbol_concentration': 0.5,
        },
    }


def test_planned_v5_execution_count_oversamples_with_available_cap() -> None:
    assert planned_v5_execution_count(requested_count=10, eligible_count=17) == 17
    assert planned_v5_execution_count(requested_count=10, eligible_count=30) == 20
    assert planned_v5_execution_count(requested_count=1, eligible_count=10) == 3
    assert planned_v5_execution_count(requested_count=0, eligible_count=10) == 0


def test_select_actual_rowset_representatives_keeps_one_ranked_member_per_group(tmp_path: Path) -> None:
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100), _row('B', 2, 200)])
    csv_c = _trade_csv(tmp_path / 'cand003.csv', [_row('C', 3, 300), _row('D', 4, 400)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
        _candidate('cand003', csv_c, rank=3),
    ]

    selected, summary = select_actual_rowset_representatives(
        ranked,
        runtime_root=tmp_path,
        requested_count=2,
    )

    assert [item['strategy_name'] for item in selected] == ['cand001', 'cand003']
    assert summary['status'] == 'ok'
    assert summary['row_set_identity_status'] == 'all_distinct'
    assert summary['executed_count'] == 3
    assert summary['actual_group_count'] == 2
    assert summary['selected_count'] == 2
    assert summary['duplicate_actual_rowset_count'] == 1
    assert summary['skipped_duplicate_actual_count'] == 1
    assert summary['duplicate_groups'][0]['members'] == ['cand001', 'cand002']


def test_select_actual_rowset_representatives_reports_shortfall(tmp_path: Path) -> None:
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('A', 1, 100)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
    ]

    selected, summary = select_actual_rowset_representatives(
        ranked,
        runtime_root=tmp_path,
        requested_count=2,
    )

    assert [item['strategy_name'] for item in selected] == ['cand001']
    assert summary['status'] == 'shortfall'
    assert summary['row_set_identity_status'] == 'partially_distinct'
    assert summary['selected_count'] == 1
    assert summary['requested_count'] == 2


def test_apply_actual_rowset_selection_moves_best_to_first_selected_representative(tmp_path: Path) -> None:
    csv_a = _trade_csv(tmp_path / 'cand001.csv', [_row('A', 1, 100)])
    csv_b = _trade_csv(tmp_path / 'cand002.csv', [_row('B', 2, 200)])
    ranked = [
        _candidate('cand001', csv_a, rank=1),
        _candidate('cand002', csv_b, rank=2),
    ]
    selection = {
        'selected_strategy_names': ['cand002'],
    }

    updated, best = apply_actual_rowset_selection(ranked, selection)

    assert best['strategy_name'] == 'cand002'
    assert [item['selected_as_best'] for item in updated] == [False, True]
    assert [item['actual_rowset_selected'] for item in updated] == [False, True]
