"""Baseline/candidate trade-set comparison."""

from __future__ import annotations

import math

import pandas as pd

from cli.research_metrics import normalize_trade_frame, summarize_trade_frame


INSTRUMENT_COLUMNS = ('종목코드', '종목명')
REQUIRED_KEY_COLUMNS = ('매수시간',)
OPTIONAL_KEY_COLUMNS = ('매수가',)
TRADE_KEY_COLUMNS = INSTRUMENT_COLUMNS + REQUIRED_KEY_COLUMNS + OPTIONAL_KEY_COLUMNS


def _is_usable(value) -> bool:
    if pd.isna(value):
        return False
    return not (isinstance(value, str) and value.strip() == '')


def _format_key_part(value) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def _first_usable(row, columns: tuple[str, ...]):
    for column in columns:
        if column in row.index and _is_usable(row[column]):
            return row[column]
    return None


def make_trade_key(row) -> str:
    """Build a stable trade key from currently available result columns."""
    instrument = _first_usable(row, INSTRUMENT_COLUMNS)
    buy_time = _first_usable(row, REQUIRED_KEY_COLUMNS)
    if instrument is None or buy_time is None:
        raise ValueError('trade row lacks required identity fields')

    parts = [_format_key_part(instrument), _format_key_part(buy_time)]
    for column in OPTIONAL_KEY_COLUMNS:
        if column in row.index and _is_usable(row[column]):
            parts.append(_format_key_part(row[column]))
    return '|'.join(parts)


def _with_trade_key(data) -> pd.DataFrame:
    df = normalize_trade_frame(data)
    if df.empty:
        df['_trade_key'] = []
        df['_trade_occurrence'] = []
        return df
    df['_trade_key'] = df.apply(make_trade_key, axis=1)
    df['_trade_occurrence'] = df.groupby('_trade_key').cumcount()
    return df


def _trade_id_pairs(df: pd.DataFrame) -> set[tuple[str, int]]:
    if df.empty:
        return set()
    return set(zip(df['_trade_key'], df['_trade_occurrence']))


def _subset_by_trade_ids(df: pd.DataFrame, trade_ids: set[tuple[str, int]]) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    row_ids = pd.Series(zip(df['_trade_key'], df['_trade_occurrence']), index=df.index)
    return df[row_ids.isin(trade_ids)].copy()


def compare_trade_sets(baseline_data, candidate_data) -> dict:
    """Compare baseline and candidate trade result frames."""
    baseline = _with_trade_key(baseline_data)
    candidate = _with_trade_key(candidate_data)
    baseline_ids = _trade_id_pairs(baseline)
    candidate_ids = _trade_id_pairs(candidate)
    common_ids = baseline_ids & candidate_ids
    excluded_ids = baseline_ids - candidate_ids
    new_ids = candidate_ids - baseline_ids
    common = _subset_by_trade_ids(candidate, common_ids)
    excluded = _subset_by_trade_ids(baseline, excluded_ids)
    new = _subset_by_trade_ids(candidate, new_ids)
    baseline_count = len(baseline)
    return {
        'baseline_summary': summarize_trade_frame(baseline),
        'candidate_summary': summarize_trade_frame(candidate),
        'common_summary': summarize_trade_frame(common),
        'excluded_summary': summarize_trade_frame(excluded),
        'new_summary': summarize_trade_frame(new),
        'counts': {
            'baseline': baseline_count,
            'candidate': len(candidate),
            'common': len(common),
            'excluded': len(excluded),
            'new': len(new),
        },
        'trade_count_retention': 0.0 if baseline_count == 0 else len(candidate) / baseline_count,
        'trade_count_expansion': 0.0 if baseline_count == 0 else len(new) / baseline_count,
        'matching_key_columns': [
            column for column in TRADE_KEY_COLUMNS
            if column in baseline.columns or column in candidate.columns
        ],
    }


# ---------------------------------------------------------------------------
# T3.4 라운드 교차비교 매트릭스 (additive — 기존 compare_trade_sets 계약 불변).
# 라운드 결과 dict(candidates/baseline_result)를 후보×지표 매트릭스로 요약하고
# 각 후보의 부모(baseline) 대비 delta로 변이 귀속을 남긴다. 순수 함수 — 파일
# 저장/시계/네트워크 부작용 없음(아티팩트 저장은 호출자 몫).
# ---------------------------------------------------------------------------

ROUND_MATRIX_SCHEMA_VERSION = 1
ROUND_MATRIX_AUTHORITY = 'research_observability_only'
ROUND_MATRIX_METRIC_COLUMNS = (
    'profit',
    'mdd',
    'trade_count',
    'win_rate',
    'slippage_tick2_profit',
    'slippage_tick2_retention',
)
_ROUND_MATRIX_DELTA_COLUMNS = (
    'delta_profit',
    'delta_mdd',
    'delta_trades',
    'delta_win_rate',
)
_PROFIT_KEYS = ('total_profit', 'profit')
# 실 컨트롤러 run metrics 는 'mdd_pct'(cli/runner.py) — 1순위. 'mdd'/'max_drawdown'
# 은 합성/구형 페이로드 폴백.
_MDD_KEYS = ('mdd_pct', 'mdd', 'max_drawdown')
_MUTATION_METADATA_CONTAINERS = ('research_contract', 'prompt_receipt', 'source_candidate')


def _finite_number(mapping, keys: tuple[str, ...]) -> float | None:
    """dict에서 첫 유한 수치를 뽑는다 (bool 제외, 미확보 None)."""
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return float(value)
    return None


def _candidate_metadata_value(candidate: dict, key: str):
    """후보 최상위 → 연구 메타데이터 컨테이너 순으로 값을 찾는다."""
    value = candidate.get(key)
    if value not in (None, ''):
        return value
    for container_name in _MUTATION_METADATA_CONTAINERS:
        container = candidate.get(container_name)
        if isinstance(container, dict):
            value = container.get(key)
            if value not in (None, ''):
                return value
    return None


def _candidate_lane(candidate: dict):
    lane = _candidate_metadata_value(candidate, 'research_lane')
    if lane in (None, ''):
        lane = candidate.get('lane')
    return None if lane in (None, '') else str(lane)


def _candidate_mutation(candidate: dict) -> dict:
    """변이 귀속 식별자 — 축/파라미터/변경 전후 값(미확보 None)."""
    axis = _candidate_metadata_value(candidate, 'mutation_axis')
    return {
        'axis': None if axis in (None, '') else str(axis),
        'param': _candidate_metadata_value(candidate, 'mutation_param'),
        'from_value': _candidate_metadata_value(candidate, 'mutation_from'),
        'to_value': _candidate_metadata_value(candidate, 'mutation_to'),
    }


def _slippage_tick2_metrics(candidate: dict) -> tuple[float | None, float | None]:
    """slippage_profiles가 있으면 tick2 프로파일의 (총손익, 보존율)."""
    report = candidate.get('slippage_profiles')
    if not isinstance(report, dict):
        return None, None
    tick2 = (report.get('profiles') or {}).get('tick2') if isinstance(report.get('profiles'), dict) else None
    if not isinstance(tick2, dict):
        return None, None
    return (
        _finite_number(tick2, ('total_profit',)),
        _finite_number(tick2, ('profit_retention_ratio',)),
    )


def _candidate_mdd(candidate: dict, candidate_summary: dict) -> float | None:
    metrics = (candidate.get('candidate_result') or {})
    metrics = metrics.get('metrics') if isinstance(metrics, dict) else None
    value = _finite_number(metrics, _MDD_KEYS)
    if value is None:
        value = _finite_number(candidate_summary, _MDD_KEYS)
    return value


def _delta_or_none(candidate_value: float | None, baseline_value: float | None) -> float | None:
    if candidate_value is None or baseline_value is None:
        return None
    return candidate_value - baseline_value


def _matrix_row(candidate: dict, round_baseline_metrics: dict) -> dict:
    """후보 1건의 매트릭스 행 — 지표 + 부모 대비 delta(변이 귀속)."""
    comparison = candidate.get('comparison') if isinstance(candidate.get('comparison'), dict) else {}
    baseline_summary = comparison.get('baseline_summary') if isinstance(comparison.get('baseline_summary'), dict) else {}
    candidate_summary = comparison.get('candidate_summary') if isinstance(comparison.get('candidate_summary'), dict) else {}
    evaluated = candidate.get('status') == 'ok'

    profit = _finite_number(candidate_summary, _PROFIT_KEYS)
    trade_count = _finite_number(candidate_summary, ('trade_count',))
    win_rate = _finite_number(candidate_summary, ('win_rate',))
    mdd = _candidate_mdd(candidate, candidate_summary)
    slippage_profit, slippage_retention = _slippage_tick2_metrics(candidate)

    base_profit = _finite_number(baseline_summary, _PROFIT_KEYS)
    base_trades = _finite_number(baseline_summary, ('trade_count',))
    base_win_rate = _finite_number(baseline_summary, ('win_rate',))
    base_mdd = _finite_number(round_baseline_metrics, _MDD_KEYS)
    if base_mdd is None:
        base_mdd = _finite_number(baseline_summary, _MDD_KEYS)

    delta_profit = _delta_or_none(profit, base_profit)
    promotion = candidate.get('promotion') if isinstance(candidate.get('promotion'), dict) else {}
    return {
        'candidate_id': str(candidate.get('strategy_name') or ''),
        'status': candidate.get('status'),
        'evaluated': evaluated,
        'rank': candidate.get('rank'),
        'selected_as_best': candidate.get('selected_as_best') is True,
        'lane': _candidate_lane(candidate),
        'mutation': _candidate_mutation(candidate),
        'metrics': {
            'profit': profit,
            'mdd': mdd,
            'trade_count': trade_count,
            'win_rate': win_rate,
            'slippage_tick2_profit': slippage_profit,
            'slippage_tick2_retention': slippage_retention,
        },
        # 변이 귀속: 이 후보(=부모에 변이축 1개 적용)의 부모 대비 효과.
        'delta_vs_parent': {
            'delta_profit': delta_profit,
            'delta_mdd': _delta_or_none(mdd, base_mdd),
            'delta_trades': _delta_or_none(trade_count, base_trades),
            'delta_win_rate': _delta_or_none(win_rate, base_win_rate),
        },
        'promotion_passed': promotion.get('passed') is True,
        # 개선 판정: 평가 완료 + 부모 대비 profit delta 양수 (미확보는 미개선).
        'improved_over_baseline': bool(evaluated and delta_profit is not None and delta_profit > 0),
    }


def _round_baseline_block(round_result: dict, round_baseline_metrics: dict) -> dict:
    """라운드 공통 baseline 지표 스냅샷 (baseline_result.metrics 우선,
    없으면 첫 후보 comparison.baseline_summary로 보충)."""
    candidates = [c for c in (round_result.get('candidates') or []) if isinstance(c, dict)]
    first_summary: dict = {}
    for candidate in candidates:
        comparison = candidate.get('comparison') if isinstance(candidate.get('comparison'), dict) else {}
        summary = comparison.get('baseline_summary')
        if isinstance(summary, dict) and summary:
            first_summary = summary
            break
    def _pick(keys: tuple[str, ...]) -> float | None:
        value = _finite_number(round_baseline_metrics, keys)
        return _finite_number(first_summary, keys) if value is None else value
    return {
        'profit': _pick(_PROFIT_KEYS),
        'mdd': _pick(_MDD_KEYS),
        'trade_count': _pick(('trade_count',)),
        'win_rate': _pick(('win_rate',)),
    }


def build_round_comparison_matrix(round_result) -> dict:
    """라운드 결과 dict를 후보×지표 교차비교 매트릭스로 요약한다.

    입력은 run_research_iteration 결과 골격(candidates/baseline_result/
    strategy_name)이면 충분하다. 반환 dict는 순수 데이터 — 저장은 호출자 몫.
    """
    round_result = round_result if isinstance(round_result, dict) else {}
    baseline_result = round_result.get('baseline_result')
    round_baseline_metrics = (
        baseline_result.get('metrics')
        if isinstance(baseline_result, dict) and isinstance(baseline_result.get('metrics'), dict)
        else {}
    )
    rows = [
        _matrix_row(candidate, round_baseline_metrics)
        for candidate in (round_result.get('candidates') or [])
        if isinstance(candidate, dict)
    ]
    evaluated_count = sum(1 for row in rows if row['evaluated'])
    improved_count = sum(1 for row in rows if row['improved_over_baseline'])
    return {
        'schema_version': ROUND_MATRIX_SCHEMA_VERSION,
        'authority': ROUND_MATRIX_AUTHORITY,
        'strategy_name': str(round_result.get('strategy_name') or ''),
        'metric_columns': list(ROUND_MATRIX_METRIC_COLUMNS),
        'delta_columns': list(_ROUND_MATRIX_DELTA_COLUMNS),
        'baseline': _round_baseline_block(round_result, round_baseline_metrics),
        'rows': rows,
        'candidate_count': len(rows),
        'evaluated_count': evaluated_count,
        'improved_over_baseline_count': improved_count,
    }


def _format_matrix_cell(value) -> str:
    if value is None:
        return '-'
    if isinstance(value, bool):
        return 'Y' if value else 'N'
    if isinstance(value, (int, float)):
        numeric = float(value)
        if not math.isfinite(numeric):
            return '-'
        if numeric.is_integer():
            return str(int(numeric))
        formatted = f'{numeric:.4f}'.rstrip('0').rstrip('.')
        return formatted or '0'
    text = str(value).strip()
    return text if text else '-'


def _matrix_md_row_order(rows: list[dict]) -> list[dict]:
    """랭크 오름차순(무랭크는 뒤, candidate_id 순) — 결정론 렌더."""
    return sorted(
        rows,
        key=lambda row: (
            row.get('rank') is None,
            row.get('rank') if row.get('rank') is not None else 0,
            str(row.get('candidate_id') or ''),
        ),
    )


def render_matrix_md(matrix) -> str:
    """build_round_comparison_matrix 결과의 사람용 Markdown 렌더."""
    matrix = matrix if isinstance(matrix, dict) else {}
    baseline = matrix.get('baseline') if isinstance(matrix.get('baseline'), dict) else {}
    rows = [row for row in (matrix.get('rows') or []) if isinstance(row, dict)]
    lines = [
        f"# 라운드 교차비교 매트릭스: {matrix.get('strategy_name') or '(unnamed)'}",
        '',
        f"- 후보 수: {_format_matrix_cell(matrix.get('candidate_count'))} "
        f"(평가 완료 {_format_matrix_cell(matrix.get('evaluated_count'))})",
        f"- baseline 대비 개선 후보 수: {_format_matrix_cell(matrix.get('improved_over_baseline_count'))}",
        f"- baseline: profit={_format_matrix_cell(baseline.get('profit'))}, "
        f"mdd={_format_matrix_cell(baseline.get('mdd'))}, "
        f"trades={_format_matrix_cell(baseline.get('trade_count'))}, "
        f"win_rate={_format_matrix_cell(baseline.get('win_rate'))}",
        f"- authority: {matrix.get('authority') or ROUND_MATRIX_AUTHORITY}",
        '',
        '| 후보 | 랭크 | 레인 | 변이축 | profit | Δprofit | mdd | Δmdd | trades | Δtrades '
        '| win_rate | Δwin_rate | slip_t2_profit | slip_t2_ret | 개선 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in _matrix_md_row_order(rows):
        metrics = row.get('metrics') if isinstance(row.get('metrics'), dict) else {}
        deltas = row.get('delta_vs_parent') if isinstance(row.get('delta_vs_parent'), dict) else {}
        mutation = row.get('mutation') if isinstance(row.get('mutation'), dict) else {}
        name = _format_matrix_cell(row.get('candidate_id'))
        if row.get('selected_as_best'):
            name = f'**{name}**'
        lines.append(
            '| ' + ' | '.join([
                name,
                _format_matrix_cell(row.get('rank')),
                _format_matrix_cell(row.get('lane')),
                _format_matrix_cell(mutation.get('axis')),
                _format_matrix_cell(metrics.get('profit')),
                _format_matrix_cell(deltas.get('delta_profit')),
                _format_matrix_cell(metrics.get('mdd')),
                _format_matrix_cell(deltas.get('delta_mdd')),
                _format_matrix_cell(metrics.get('trade_count')),
                _format_matrix_cell(deltas.get('delta_trades')),
                _format_matrix_cell(metrics.get('win_rate')),
                _format_matrix_cell(deltas.get('delta_win_rate')),
                _format_matrix_cell(metrics.get('slippage_tick2_profit')),
                _format_matrix_cell(metrics.get('slippage_tick2_retention')),
                _format_matrix_cell(row.get('improved_over_baseline')),
            ]) + ' |'
        )
    return '\n'.join(lines) + '\n'
