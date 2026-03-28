"""자동 조건식 탐색용 조건 코드 생성기 (library-only)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def _format_value(value):
    if value is None:
        return 'None'
    if isinstance(value, bool):
        return 'True' if value else 'False'
    if isinstance(value, int):
        return f'{value:,}'.replace(',', '_')
    if isinstance(value, float):
        if value.is_integer():
            return f'{int(value):,}'.replace(',', '_')
        return f'{value:.6f}'.rstrip('0').rstrip('.')
    return repr(value)


def _normalize_feature_name(feature: str, runtime_context: bool = False) -> str:
    if runtime_context and feature.startswith('B_'):
        return feature[2:]
    return feature


def candidate_to_expression(candidate: dict, runtime_context: bool = False) -> str:
    feature = _normalize_feature_name(candidate['feature'], runtime_context=runtime_context)
    operator = candidate.get('operator')
    threshold = candidate.get('threshold')
    lower = candidate.get('lower_bound')
    upper = candidate.get('upper_bound')

    if operator == 'between':
        return f"{_format_value(lower)} <= {feature} < {_format_value(upper)}"
    if operator in ('<', '<=', '>', '>='):
        return f"{feature} {operator} {_format_value(threshold)}"
    raise ValueError(f'unsupported operator: {operator}')


def candidate_to_comment(candidate: dict) -> str:
    source = candidate.get('source', 'unknown')
    count = candidate.get('count', 0)
    mean_return = candidate.get('mean_return')
    win_rate = candidate.get('win_rate')
    parts = [f'source={source}', f'n={count}']
    if mean_return is not None:
        parts.append(f'mean_return={mean_return:.4f}')
    if win_rate is not None:
        parts.append(f'win_rate={win_rate:.4f}')
    label = candidate.get('label')
    if label:
        parts.append(f'label={label}')
    p_value_adj = candidate.get('p_value_adj')
    if p_value_adj is not None:
        parts.append(f'fdr={p_value_adj:.6f}')
    return ' | '.join(parts)


def generate_condition_code(
    candidates: list[dict],
    buy_var: str = '매수',
    header_title: str = '자동 생성 필터',
    created_at: str | None = None,
    runtime_context: bool = True,
) -> str:
    created_at = created_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f'# {header_title}',
        f'# created_at: {created_at}',
        '# NOTE: B_* feature only, S_* / R_* excluded to avoid leakage',
    ]

    for index, candidate in enumerate(candidates, start=1):
        lines.append(f'# candidate {index}: {candidate_to_comment(candidate)}')
        lines.append(f'if {candidate_to_expression(candidate, runtime_context=runtime_context)}: {buy_var} = False')
    return '\n'.join(lines)


def select_candidates(
    analysis_result: dict,
    top_n: int = 5,
    include_sources: tuple[str, ...] = ('market_cap', 'time_of_day', 'quantile', 'ttest'),
    feature_whitelist: list[str] | None = None,
    feature_importance_map: dict | None = None,
    ml_weight: float = 0.0,
) -> list[dict]:
    recommended = [
        candidate for candidate in analysis_result.get('recommended_candidates', [])
        if candidate.get('source') in include_sources
    ]
    if feature_whitelist is not None:
        allowed = set(feature_whitelist)
        recommended = [candidate for candidate in recommended if candidate.get('feature') in allowed]
    ranked = []
    feature_importance_map = feature_importance_map or {}
    for candidate in recommended:
        item = dict(candidate)
        base_score = float(item.get('score', 0.0) or 0.0)
        ml_importance = float(feature_importance_map.get(item.get('feature'), 0.0) or 0.0)
        item['base_score'] = base_score
        item['ml_importance'] = ml_importance
        item['combined_score'] = base_score + ml_weight * ml_importance
        ranked.append(item)
    ranked.sort(key=lambda item: item['combined_score'], reverse=True)
    return ranked[:max(top_n, 0)]


def generate_condition_expressions(candidates: list[dict], runtime_context: bool = True) -> list[str]:
    return [candidate_to_expression(candidate, runtime_context=runtime_context) for candidate in candidates]


def generate_condition_expressions_from_analysis(
    analysis_result: dict,
    top_n: int = 5,
    include_sources: tuple[str, ...] = ('market_cap', 'time_of_day', 'quantile', 'ttest'),
    feature_whitelist: list[str] | None = None,
    feature_importance_map: dict | None = None,
    ml_weight: float = 0.0,
    runtime_context: bool = True,
) -> dict:
    selected = select_candidates(
        analysis_result,
        top_n=top_n,
        include_sources=include_sources,
        feature_whitelist=feature_whitelist,
        feature_importance_map=feature_importance_map,
        ml_weight=ml_weight,
    )
    expressions = generate_condition_expressions(selected, runtime_context=runtime_context)
    return {
        'status': 'ok',
        'selected_candidates': selected,
        'expressions': expressions,
        'candidate_count': len(selected),
    }


def generate_conditions_from_analysis(
    analysis_result: dict,
    top_n: int = 5,
    buy_var: str = '매수',
    include_sources: tuple[str, ...] = ('market_cap', 'time_of_day', 'quantile', 'ttest'),
    feature_whitelist: list[str] | None = None,
    feature_importance_map: dict | None = None,
    ml_weight: float = 0.0,
    runtime_context: bool = True,
) -> dict:
    selected = select_candidates(
        analysis_result,
        top_n=top_n,
        include_sources=include_sources,
        feature_whitelist=feature_whitelist,
        feature_importance_map=feature_importance_map,
        ml_weight=ml_weight,
    )
    code = generate_condition_code(selected, buy_var=buy_var, runtime_context=runtime_context)
    return {
        'status': 'ok',
        'selected_candidates': selected,
        'code': code,
        'candidate_count': len(selected),
    }


def save_condition_code(code: str, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(code, encoding='utf-8')
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
