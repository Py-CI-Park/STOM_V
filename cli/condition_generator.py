"""자동 조건식 탐색용 조건 코드 생성기 (library-only)."""

from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path

MULTI_HYPOTHESIS_CANDIDATE_PACK_VERSION = 'multi_hypothesis_candidate_pack_v1'
_LLM_RESEARCH_SOURCE = 'llm_multi_hypothesis_candidate_pack'
_DIAGNOSTIC_FALLBACK_SOURCE = 'diagnostic_deterministic_candidate_fallback'
_PROHIBITED_AUTHORITY_KEYS = frozenset({
    'can_promote',
    'can_export',
    'can_live',
    'can_final_promote',
    'promotion_eligible',
    'promotion_claim',
    'export_eligible',
    'live_eligible',
    'final_promotion',
    'production_ready',
})
_RESEARCH_LANES = ('repair', 'discovery')
_LEAKY_EXPRESSION_PREFIXES = ('R_', 'S_')



def _truthy_authority_paths(value, path=''):
    paths = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f'{path}.{key_text}' if path else key_text
            if key_text in _PROHIBITED_AUTHORITY_KEYS and bool(nested):
                paths.append(nested_path)
            paths.extend(_truthy_authority_paths(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            paths.extend(_truthy_authority_paths(nested, f'{path}[{index}]'))
    return paths

def _pack_authority_scope(candidate_pack: dict) -> dict:
    """Return pack-level fields only so unsafe siblings can still be isolated per candidate."""

    return {key: value for key, value in candidate_pack.items() if key != 'candidates'}

def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _parent_condition_from_pack(candidate_pack: dict, side: str) -> dict[str, str]:
    parents = candidate_pack.get('parents') if isinstance(candidate_pack.get('parents'), dict) else {}
    parent = parents.get(side) if isinstance(parents.get(side), dict) else {}
    code = (
        parent.get('code')
        or parent.get(f'{side}_code')
        or candidate_pack.get(f'parent_{side}_code')
        or candidate_pack.get(f'{side}_code')
        or ''
    )
    parent_id = (
        parent.get('id')
        or candidate_pack.get(f'parent_{side}_id')
        or candidate_pack.get(f'{side}_id')
        or ''
    )
    sha256 = (
        parent.get('sha256')
        or candidate_pack.get(f'parent_{side}_sha256')
        or (_sha256_text(str(code)) if code else '')
    )
    return {'id': str(parent_id or ''), 'code': str(code or ''), 'sha256': str(sha256 or '')}


def _candidate_with_parent_condition_context(candidate: dict, candidate_pack: dict) -> dict:
    """Merge full parent buy/sell condition text from the pack into a candidate."""

    enriched = dict(candidate)
    if enriched.get('parent_code') and not enriched.get('parent_buy_code'):
        enriched['parent_buy_code'] = enriched['parent_code']
    for side in ('buy', 'sell'):
        parent = _parent_condition_from_pack(candidate_pack, side)
        id_key = f'parent_{side}_id'
        code_key = f'parent_{side}_code'
        sha_key = f'parent_{side}_sha256'
        if not enriched.get(id_key) and parent['id']:
            enriched[id_key] = parent['id']
        if not enriched.get(code_key) and parent['code']:
            enriched[code_key] = parent['code']
        if enriched.get(code_key) and not enriched.get(sha_key):
            enriched[sha_key] = _sha256_text(str(enriched[code_key]))
        elif not enriched.get(sha_key) and parent['sha256']:
            enriched[sha_key] = parent['sha256']
    if not enriched.get('parent_id') and enriched.get('parent_buy_id'):
        enriched['parent_id'] = enriched['parent_buy_id']
    return enriched



def _expression_leakage_reasons(expression: str) -> list[str]:
    """Return result/sell diagnostic prefixes that must not appear in generated buy expressions."""

    return [
        f'expression_uses_{prefix.rstrip("_")}_diagnostic'
        for prefix in _LEAKY_EXPRESSION_PREFIXES
        if prefix in expression
    ]



def _candidate_failure_reasons(candidate: dict, seen_expressions: set[str]) -> list[str]:
    reasons: list[str] = []
    lane = candidate.get('lane')
    expression = str(candidate.get('expression') or '').strip()
    if lane not in _RESEARCH_LANES:
        reasons.append('invalid_lane')
    if not expression:
        reasons.append('missing_expression')
    else:
        if expression in seen_expressions:
            reasons.append('duplicate_expression')
        reasons.extend(_expression_leakage_reasons(expression))
    if not candidate.get('hypothesis_id'):
        reasons.append('missing_hypothesis_id')
    if not (candidate.get('intended_hypothesis') or candidate.get('hypothesis')):
        reasons.append('missing_intended_hypothesis')
    if not candidate.get('mutation_axis'):
        reasons.append('missing_mutation_axis')
    if not candidate.get('expected_effect'):
        reasons.append('missing_expected_effect')
    if not candidate.get('risk_note'):
        reasons.append('missing_risk_note')
    if _truthy_authority_paths(candidate):
        reasons.append('authority_smuggling')
    if lane == 'repair':
        if not (candidate.get('parent_buy_id') or candidate.get('parent_id')):
            reasons.append('missing_repair_parent_reference')
        if not str(candidate.get('parent_buy_code') or '').strip():
            reasons.append('missing_repair_parent_buy_code')
        if not str(candidate.get('parent_sell_code') or '').strip():
            reasons.append('missing_repair_parent_sell_code')
        if not candidate.get('analysis_card_id'):
            reasons.append('missing_repair_analysis_card_reference')
        if candidate.get('preserves_parent_structure') is False:
            reasons.append('repair_parent_structure_not_preserved')
    if lane == 'discovery':
        target_coverage = candidate.get('discovery_target_coverage') or candidate.get('coverage_bucket_keys')
        novelty = candidate.get('novelty') if isinstance(candidate.get('novelty'), dict) else {}
        if not target_coverage:
            reasons.append('missing_discovery_target_coverage')
        if not (candidate.get('novelty_rationale') or novelty.get('novelty_rationale')):
            reasons.append('missing_discovery_novelty_rationale')
        if not any(novelty.get(key) for key in ('coverage_regime', 'feature_family', 'market_segment')):
            reasons.append('missing_discovery_novelty_axis')
    return reasons


def validate_multi_hypothesis_candidate_pack(candidate_pack: dict, *, min_candidates: int = 2) -> dict:
    """Validate a side-effect-free LLM multi-hypothesis candidate pack."""

    if not isinstance(candidate_pack, dict):
        return {
            'schema_version': 1,
            'candidate_pack_version': MULTI_HYPOTHESIS_CANDIDATE_PACK_VERSION,
            'candidate_pack_id': '',
            'valid': False,
            'failure_reasons': ['candidate_pack_not_object'],
            'valid_candidates': [],
            'invalid_candidates': [],
            'valid_candidate_count': 0,
            'invalid_candidate_count': 0,
            'lane_counts': {lane: 0 for lane in _RESEARCH_LANES},
            'authority': 'research_only_no_export_live_or_final_promotion',
        }

    candidates = candidate_pack.get('candidates') or []
    valid_candidates = []
    invalid_candidates = []
    seen_expressions: set[str] = set()
    pack_id = candidate_pack.get('candidate_pack_id') or candidate_pack.get('pack_id') or ''
    pack_blockers = []
    if candidate_pack.get('schema_version') not in (1, '1', None):
        pack_blockers.append('unsupported_schema_version')
    if _truthy_authority_paths(_pack_authority_scope(candidate_pack)):
        pack_blockers.append('pack_authority_smuggling')
    if not isinstance(candidates, list):
        candidates = []
        pack_blockers.append('candidates_not_list')

    for index, raw_candidate in enumerate(candidates, start=1):
        candidate = _candidate_with_parent_condition_context(
            dict(raw_candidate or {}) if isinstance(raw_candidate, dict) else {},
            candidate_pack,
        )
        reasons = _candidate_failure_reasons(candidate, seen_expressions)
        expression = str(candidate.get('expression') or '').strip()
        if reasons:
            invalid_candidates.append({
                'index': index,
                'candidate': candidate,
                'failure_reasons': reasons,
            })
            continue
        seen_expressions.add(expression)
        pack_context = {
            key: candidate_pack.get(key)
            for key in (
                'context_pack_id',
                'context_pack_sha256',
                'full_stom_sources_included',
                'prompt_budget_estimated_tokens',
                'mode_authority',
                'generation_allowed',
            )
            if candidate_pack.get(key) not in (None, '')
        }
        candidate_contract_id = (
            candidate.get('candidate_contract_id')
            or f'{pack_id}::{candidate.get("hypothesis_id")}'
            if pack_id and candidate.get('hypothesis_id')
            else candidate.get('candidate_contract_id')
        )
        normalized = {
            **candidate,
            'candidate_pack_id': pack_id,
            **{key: value for key, value in pack_context.items() if key not in candidate},
            'candidate_contract_id': candidate_contract_id,
            'source': _LLM_RESEARCH_SOURCE,
            'fallback_used': False,
            'prompt_maturity_credit_allowed': True,
        }
        valid_candidates.append(normalized)

    lane_counts = {lane: sum(1 for item in valid_candidates if item.get('lane') == lane) for lane in _RESEARCH_LANES}
    failure_reasons = list(pack_blockers)
    if len(valid_candidates) < int(min_candidates):
        failure_reasons.append('insufficient_valid_candidates')
    if lane_counts['repair'] < 1:
        failure_reasons.append('missing_repair_candidate')
    if lane_counts['discovery'] < 1:
        failure_reasons.append('missing_discovery_candidate')
    return {
        'schema_version': 1,
        'candidate_pack_version': MULTI_HYPOTHESIS_CANDIDATE_PACK_VERSION,
        'candidate_pack_id': pack_id,
        'valid': not failure_reasons,
        'failure_reasons': failure_reasons,
        'valid_candidates': valid_candidates,
        'invalid_candidates': invalid_candidates,
        'valid_candidate_count': len(valid_candidates),
        'invalid_candidate_count': len(invalid_candidates),
        'lane_counts': lane_counts,
        'authority': 'research_only_no_export_live_or_final_promotion',
    }


def expression_result_from_candidate_pack(candidate_pack: dict, *, planned_count: int = 3, min_candidates: int = 2) -> dict:
    validation = validate_multi_hypothesis_candidate_pack(candidate_pack, min_candidates=min_candidates)
    if not validation['valid']:
        return {
            'status': 'error',
            'source': _LLM_RESEARCH_SOURCE,
            'fallback_used': False,
            'fallback_reason': ','.join(validation['failure_reasons']),
            'candidate_pack_validation': validation,
            'expressions': [],
            'selected_candidates': [],
            'candidate_count': 0,
        }
    selected = validation['valid_candidates'][:max(int(planned_count), 0)]
    return {
        'status': 'ok',
        'source': _LLM_RESEARCH_SOURCE,
        'fallback_used': False,
        'fallback_reason': '',
        'candidate_pack_id': validation['candidate_pack_id'],
        'candidate_pack_validation': validation,
        'selected_candidates': selected,
        'expressions': [candidate['expression'] for candidate in selected],
        'candidate_count': len(selected),
        'prompt_maturity_credit_allowed': True,
    }


def mark_diagnostic_fallback(expression_result: dict, *, reason: str) -> dict:
    """Label deterministic analysis candidates as diagnostic fallback, not prompt maturity evidence."""

    marked = dict(expression_result)
    unsafe_expressions = [
        expression
        for expression in marked.get('expressions') or []
        if _expression_leakage_reasons(str(expression))
    ]
    if unsafe_expressions:
        marked['status'] = 'error'
        marked['expressions'] = []
        marked['selected_candidates'] = []
        marked['candidate_count'] = 0
        marked['source'] = _DIAGNOSTIC_FALLBACK_SOURCE
        marked['fallback_used'] = True
        marked['fallback_reason'] = f'{reason},diagnostic_fallback_expression_leakage'
        marked['prompt_maturity_credit_allowed'] = False
        marked['message'] = 'diagnostic fallback generated result/sell diagnostic expressions'
        marked['unsafe_expressions'] = unsafe_expressions
        return marked

    selected = []
    for candidate in marked.get('selected_candidates') or []:
        item = dict(candidate)
        item['source'] = _DIAGNOSTIC_FALLBACK_SOURCE
        item['fallback_used'] = True
        item['fallback_reason'] = reason
        item['prompt_maturity_credit_allowed'] = False
        item['prompt_maturity_score'] = 0
        selected.append(item)
    marked['selected_candidates'] = selected
    marked['source'] = _DIAGNOSTIC_FALLBACK_SOURCE
    marked['fallback_used'] = True
    marked['fallback_reason'] = reason
    marked['prompt_maturity_credit_allowed'] = False
    return marked


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
        if (
            candidate.get('source') in include_sources
            and isinstance(candidate.get('feature'), str)
            and candidate.get('feature').startswith('B_')
        )
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
