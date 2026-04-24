"""Wide v1 v3 result analysis and v4 decision helpers."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path

from cli._utils import ensure_dataframe
from cli.research_compare import compare_trade_sets
from cli.research_promotion import evaluate_research_candidate


DECISION_RECHECK_CONTROL = 'RECHECK_CONTROL'
DECISION_HOLD_V3_TIE_REVIEW = 'HOLD_V3_TIE_REVIEW'
DECISION_PROCEED_TO_V4_PLAN = 'PROCEED_TO_V4_PLAN'

NEXT_COMMANDS = {
    DECISION_RECHECK_CONTROL: '$brainstorming Wide v1 v3 control score 재검증 설계',
    DECISION_HOLD_V3_TIE_REVIEW: '$brainstorming Wide v1 v3 tie-break 및 ranking 보강 설계',
    DECISION_PROCEED_TO_V4_PLAN: '$writing-plans Wide v1 v4 후보 생성 또는 selection 조정 구현 계획 작성',
}

RANK_METRIC_KEYS = (
    'adjusted_score',
    'reference_promotion_score',
    'trade_count',
    'trade_count_retention',
    'date_concentration',
    'symbol_concentration',
)


def read_runtime_json(path: str | Path) -> dict:
    file_path = Path(path)
    errors = []
    for encoding in ('utf-8-sig', 'utf-16', 'utf-16-le'):
        try:
            return json.loads(file_path.read_text(encoding=encoding))
        except (UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f'{encoding}: {exc}')
    raise ValueError(f'failed to read runtime JSON {file_path}: {"; ".join(errors)}')


def _finite_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def recompute_control_reference(wide_reference_csv: str | Path, control_csv: str | Path) -> dict:
    reference_path = Path(wide_reference_csv)
    control_path = Path(control_csv)
    if not reference_path.exists():
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'comparison': None,
            'promotion': None,
            'message': f'missing reference csv: {reference_path}',
        }
    if not control_path.exists():
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'comparison': None,
            'promotion': None,
            'message': f'missing control csv: {control_path}',
        }

    try:
        comparison = compare_trade_sets(
            ensure_dataframe(reference_path),
            ensure_dataframe(control_path),
        )
        promotion = evaluate_research_candidate(comparison)
    except Exception as exc:
        return {
            'status': 'error',
            'reference_adjusted_score': None,
            'comparison': None,
            'promotion': None,
            'message': f'control reference evaluation failed: {exc}',
        }

    score = _finite_float(promotion.get('score'))
    return {
        'status': 'ok' if score is not None else 'error',
        'reference_adjusted_score': score,
        'comparison': comparison,
        'promotion': promotion,
        'message': None if score is not None else 'control reference score is not finite',
    }


def _rank_metrics(candidate: dict) -> dict:
    rank_score = candidate.get('rank_score') or {}
    return {key: _finite_float(rank_score.get(key)) for key in RANK_METRIC_KEYS}


def _candidate_sort_key(candidate: dict, index: int) -> tuple:
    rank = candidate.get('rank')
    if rank is not None:
        return (0, int(rank), index)

    metrics = _rank_metrics(candidate)
    adjusted_score = metrics.get('adjusted_score')
    trade_count = metrics.get('trade_count')
    trade_count_retention = metrics.get('trade_count_retention')
    date_concentration = metrics.get('date_concentration')
    symbol_concentration = metrics.get('symbol_concentration')
    return (
        1,
        float('inf') if adjusted_score is None else -adjusted_score,
        float('inf') if trade_count is None else -trade_count,
        float('inf') if trade_count_retention is None else -trade_count_retention,
        float('inf') if date_concentration is None else date_concentration,
        float('inf') if symbol_concentration is None else symbol_concentration,
        index,
    )


def _sorted_candidates(candidates: list[dict]) -> list[dict]:
    return [
        candidate
        for _, candidate in sorted(
            enumerate(candidates or []),
            key=lambda item: _candidate_sort_key(item[1], item[0]),
        )
    ]


def _same_number(left: float | None, right: float | None, tolerance: float) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance


def classify_top_tie(candidates: list[dict], *, top_n: int = 10, tolerance: float = 1e-9) -> dict:
    top = _sorted_candidates(list(candidates or []))[:top_n]
    metrics = [_rank_metrics(candidate) for candidate in top]
    if len(top) < 2:
        return {
            'status': 'not_enough_candidates',
            'top_count': len(top),
            'score_tie': False,
            'metric_tie': False,
            'tie_candidate_count': 0,
            'tie_candidates': [],
            'row_set_identity_status': 'not_evaluated',
            'metrics': metrics,
            'top_candidates': [item.get('strategy_name') for item in top],
        }

    first_score = metrics[0].get('adjusted_score')
    tie_indexes = [
        index
        for index, metric in enumerate(metrics)
        if _same_number(first_score, metric.get('adjusted_score'), tolerance)
    ]
    tie_metrics = [metrics[index] for index in tie_indexes]
    tie_candidates = [top[index].get('strategy_name') for index in tie_indexes]
    score_tie = len(tie_indexes) >= 2
    metric_tie = score_tie and all(
        all(_same_number(tie_metrics[0].get(key), item.get(key), tolerance) for key in RANK_METRIC_KEYS)
        for item in tie_metrics[1:]
    )
    if metric_tie:
        status = 'rank_metric_tie'
    elif score_tie:
        status = 'ranking_tie'
    else:
        status = 'not_tied'
    return {
        'status': status,
        'top_count': len(top),
        'score_tie': score_tie,
        'metric_tie': metric_tie,
        'tie_candidate_count': len(tie_indexes) if score_tie else 0,
        'tie_candidates': tie_candidates if score_tie else [],
        'row_set_identity_status': 'not_evaluated',
        'metrics': metrics,
        'top_candidates': [item.get('strategy_name') for item in top],
    }


def _expression_key(value) -> str:
    return ' '.join(str(value or '').split())


def _count_by_family(
    candidates: list[dict],
    expression_to_type: dict[str, str],
    predicate=None,
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for candidate in candidates or []:
        if predicate is not None and not predicate(candidate):
            continue
        candidate_type = expression_to_type.get(_expression_key(candidate.get('expression')))
        if candidate_type:
            counter[candidate_type] += 1
    return dict(counter)


def _family_selection_summary(family_gate: dict) -> dict[str, str]:
    families = set()
    for key in (
        'pool_type_counts',
        'retention_observed_type_counts',
        'retention_pass_type_counts',
        'retention_fallback_type_counts',
        'selected_type_counts',
        'executed_type_counts',
    ):
        families.update((family_gate.get(key) or {}).keys())

    summary = {}
    for family in sorted(families):
        selected = (family_gate.get('selected_type_counts') or {}).get(family, 0)
        executed = (family_gate.get('executed_type_counts') or {}).get(family, 0)
        passed = (family_gate.get('retention_pass_type_counts') or {}).get(family, 0)
        fallback = (family_gate.get('retention_fallback_type_counts') or {}).get(family, 0)
        if not any((selected, executed, passed, fallback)):
            continue
        if executed:
            summary[family] = 'selected/executed'
        elif selected:
            summary[family] = 'selected only'
        elif passed and fallback:
            summary[family] = 'retention-pass/fallback only'
        elif passed:
            summary[family] = 'retention-pass only'
        elif fallback:
            summary[family] = 'retention-fallback only'
        else:
            summary[family] = 'generated only'
    return summary


def family_distribution(runtime: dict) -> dict:
    iteration_v3 = runtime.get('iteration_v3') or {}
    pool_type_counts = dict(iteration_v3.get('type_counts') or {})
    expression_to_type = {
        _expression_key(candidate.get('expression')): candidate.get('v3_candidate_type')
        for candidate in iteration_v3.get('candidates') or []
        if candidate.get('expression') and candidate.get('v3_candidate_type')
    }

    selected_candidates = (runtime.get('expression_result') or {}).get('selected_candidates')
    if selected_candidates is None:
        selected_candidates = (runtime.get('retention_selection') or {}).get('retention_candidates') or []
    retention_candidates = (runtime.get('retention_selection') or {}).get('retention_candidates') or []
    selected_type_counts = _count_by_family(selected_candidates, expression_to_type)
    retention_observed_type_counts = _count_by_family(retention_candidates, expression_to_type)
    retention_pass_type_counts = _count_by_family(
        retention_candidates,
        expression_to_type,
        predicate=lambda candidate: candidate.get('retention_filter_passed') is True,
    )
    retention_fallback_type_counts = _count_by_family(
        retention_candidates,
        expression_to_type,
        predicate=lambda candidate: candidate.get('retention_fallback_used') is True,
    )

    executed_counter: Counter[str] = Counter()
    unknown_executed = []
    for candidate in runtime.get('candidates') or []:
        candidate_type = expression_to_type.get(_expression_key(candidate.get('expression')))
        if candidate_type:
            executed_counter[candidate_type] += 1
        else:
            unknown_executed.append(candidate.get('strategy_name'))

    result = {
        'pool_type_counts': pool_type_counts,
        'retention_observed_type_counts': retention_observed_type_counts,
        'retention_pass_type_counts': retention_pass_type_counts,
        'retention_fallback_type_counts': retention_fallback_type_counts,
        'selected_type_counts': selected_type_counts,
        'executed_type_counts': dict(executed_counter),
        'unknown_executed_strategies': unknown_executed,
    }
    result['family_selection_summary'] = _family_selection_summary(result)
    return result


def _quant_validity(control_gate: dict, tie_gate: dict) -> dict:
    reasons = []
    if control_gate.get('status') != 'ok' or control_gate.get('reference_adjusted_score') is None:
        reasons.append('control_score_missing')
    if tie_gate.get('score_tie'):
        reasons.append('top_candidates_score_tie')
    if tie_gate.get('metric_tie'):
        reasons.append('top_candidates_metric_tie')
    return {
        'blocked': bool(reasons),
        'reasons': reasons,
    }


def _decision(control_gate: dict, tie_gate: dict, quant_gate: dict) -> str:
    if control_gate.get('status') != 'ok' or control_gate.get('reference_adjusted_score') is None:
        return DECISION_RECHECK_CONTROL
    if tie_gate.get('score_tie') or tie_gate.get('status') in {'rank_metric_tie', 'ranking_tie'}:
        return DECISION_HOLD_V3_TIE_REVIEW
    if quant_gate.get('blocked'):
        return DECISION_HOLD_V3_TIE_REVIEW
    return DECISION_PROCEED_TO_V4_PLAN


def _reconcile_control_score(
    runtime: dict,
    control_gate: dict,
    *,
    tolerance: float = 1e-9,
) -> dict:
    gate = dict(control_gate)
    control_candidate = ((runtime.get('iteration_v3') or {}).get('control_candidate') or {})
    stored_score = _finite_float(control_candidate.get('reference_adjusted_score'))
    recomputed_score = _finite_float(gate.get('reference_adjusted_score'))
    gate['stored_reference_adjusted_score'] = stored_score
    gate['recomputed_reference_adjusted_score'] = recomputed_score
    gate['reference_adjusted_score'] = recomputed_score

    if stored_score is None:
        gate['stored_score_status'] = 'missing'
        gate['score_match'] = None
        return gate

    score_match = recomputed_score is not None and _same_number(stored_score, recomputed_score, tolerance)
    gate['score_match'] = score_match
    if score_match:
        gate['stored_score_status'] = 'matched'
        return gate

    gate['stored_score_status'] = 'mismatched'
    if gate.get('status') == 'ok':
        gate['status'] = 'error'
        gate['message'] = (
            f'control reference score mismatch: stored={stored_score}, recomputed={recomputed_score}'
        )
    return gate


def build_v3_decision_analysis(
    *,
    runtime_path: str | Path,
    wide_reference_csv: str | Path,
    control_csv: str | Path,
) -> dict:
    runtime = read_runtime_json(runtime_path)
    candidates = runtime.get('candidates') or []
    control_gate = _reconcile_control_score(
        runtime,
        recompute_control_reference(wide_reference_csv, control_csv),
    )
    tie_gate = classify_top_tie(candidates, top_n=10)
    family_gate = family_distribution(runtime)
    quant_gate = _quant_validity(control_gate, tie_gate)
    decision = _decision(control_gate, tie_gate, quant_gate)
    return {
        'decision': decision,
        'next_command': NEXT_COMMANDS[decision],
        'runtime_path': str(runtime_path),
        'wide_reference_csv': str(wide_reference_csv),
        'control_csv': str(control_csv),
        'runtime': {
            'status': runtime.get('status'),
            'phase': runtime.get('phase'),
            'candidate_count_observed': len(candidates),
            'best_candidate': (runtime.get('best_candidate') or {}).get('strategy_name'),
        },
        'control_score_gate': control_gate,
        'tie_gate': tie_gate,
        'family_gate': family_gate,
        'quant_validity_gate': quant_gate,
    }


def _format_dict(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def render_v3_decision_markdown(analysis: dict) -> str:
    decision = analysis.get('decision')
    runtime = analysis.get('runtime') or {}
    control_gate = analysis.get('control_score_gate') or {}
    tie_gate = analysis.get('tie_gate') or {}
    family_gate = analysis.get('family_gate') or {}
    quant_gate = analysis.get('quant_validity_gate') or {}
    next_command = analysis.get('next_command')
    return f"""# Wide v1 v3 결과 분석 및 v4 여부 판단

## 1. 판단

```text
decision={decision}
next_command={next_command}
```

## 2. 입력

```text
runtime_path={analysis.get('runtime_path')}
wide_reference_csv={analysis.get('wide_reference_csv')}
control_csv={analysis.get('control_csv')}
```

## 3. runtime 요약

```text
status={runtime.get('status')}
phase={runtime.get('phase')}
candidate_count_observed={runtime.get('candidate_count_observed')}
best_candidate={runtime.get('best_candidate')}
```

## 4. Control Score Gate

```text
status={control_gate.get('status')}
stored_reference_adjusted_score={control_gate.get('stored_reference_adjusted_score')}
recomputed_reference_adjusted_score={control_gate.get('recomputed_reference_adjusted_score')}
reference_adjusted_score={control_gate.get('reference_adjusted_score')}
stored_score_status={control_gate.get('stored_score_status')}
score_match={control_gate.get('score_match')}
message={control_gate.get('message')}
```

## 5. Tie Gate

```text
status={tie_gate.get('status')}
score_tie={tie_gate.get('score_tie')}
metric_tie={tie_gate.get('metric_tie')}
row_set_identity_status={tie_gate.get('row_set_identity_status')}
top_count={tie_gate.get('top_count')}
tie_candidate_count={tie_gate.get('tie_candidate_count')}
```

## 6. Candidate Family Gate

```json
{_format_dict(family_gate)}
```

## 7. Quant Validity Gate

```json
{_format_dict(quant_gate)}
```

## 8. 다음 단계

```text
{next_command}
```
"""


def write_v3_decision_report(
    *,
    runtime_path: str | Path,
    wide_reference_csv: str | Path,
    control_csv: str | Path,
    output_path: str | Path,
) -> dict:
    analysis = build_v3_decision_analysis(
        runtime_path=runtime_path,
        wide_reference_csv=wide_reference_csv,
        control_csv=control_csv,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_v3_decision_markdown(analysis), encoding='utf-8')
    return analysis
