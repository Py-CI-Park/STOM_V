"""Ranking helpers for research candidate results."""

from __future__ import annotations

import math
from typing import Any

from cli.research_retention import apply_retention_penalty


def _numeric_value(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        normalized = float(value)
        if not math.isfinite(normalized):
            return default
        return normalized
    except (TypeError, ValueError):
        return default

def _research_metadata_value(candidate: dict, key: str):
    value = candidate.get(key)
    if value not in (None, ''):
        return value
    for container_name in ('research_contract', 'prompt_receipt', 'analysis_card', 'source_candidate'):
        container = candidate.get(container_name)
        if isinstance(container, dict):
            value = container.get(key)
            if value not in (None, ''):
                return value
    return None


def _has_research_metadata(candidate: dict) -> bool:
    return any(
        _research_metadata_value(candidate, key) not in (None, '')
        for key in (
            'context_pack_id',
            'candidate_pack_id',
            'hypothesis_id',
            'mutation_axis',
            'fallback_used',
            'prompt_maturity_credit_allowed',
        )
    ) or isinstance(candidate.get('prompt_receipt'), dict) or isinstance(candidate.get('research_contract'), dict)


def _advisory_rank_reason(candidate: dict, score: dict) -> str:
    strict_validation = _research_metadata_value(candidate, 'strict_response_validation')
    if isinstance(strict_validation, dict) and strict_validation.get('valid') is False:
        return 'prompt_validation_invalid'
    if _research_metadata_value(candidate, 'fallback_used') is True:
        return 'diagnostic_fallback_ranked_without_prompt_credit'
    if not score.get('promotion_passed'):
        return 'official_backtest_research_candidate_not_promotion_passed'
    return 'official_backtest_research_candidate_ranked_advisory_only'


def _rank_score(candidate: dict) -> dict:
    incremental_promotion = candidate.get('promotion') or {}
    incremental_comparison = candidate.get('comparison') or {}
    reference_promotion = candidate.get('reference_promotion') or {}
    reference_comparison = candidate.get('reference_comparison') or {}
    use_reference = bool(reference_promotion and reference_comparison)
    promotion = reference_promotion if use_reference else incremental_promotion
    comparison = reference_comparison if use_reference else incremental_comparison
    candidate_summary = comparison.get('candidate_summary') or {}
    score = {
        'promotion_passed': promotion.get('passed') is True,
        'promotion_score': _numeric_value(promotion.get('score')),
        'trade_count': _numeric_value(candidate_summary.get('trade_count')),
        'trade_count_retention': _numeric_value(comparison.get('trade_count_retention')),
        'date_concentration': _numeric_value(
            candidate_summary.get('date_concentration'),
            default=float('inf'),
        ),
        'symbol_concentration': _numeric_value(
            candidate_summary.get('symbol_concentration'),
            default=float('inf'),
        ),
    }
    research_lane_score = candidate.get('research_lane_score')
    if research_lane_score is None:
        detail = candidate.get('research_score_detail') or {}
        if isinstance(detail, dict):
            research_lane_score = detail.get('candidate_score')
    if research_lane_score is not None:
        score['research_lane'] = candidate.get('research_lane')
        score['research_lane_score'] = _numeric_value(research_lane_score)
        score['research_score_authority'] = 'advisory_research_budget_only'
    if use_reference:
        score['score_basis'] = 'reference'
        score['incremental_promotion_score'] = _numeric_value(incremental_promotion.get('score'))
        score['reference_promotion_score'] = _numeric_value(reference_promotion.get('score'))
    if _has_research_metadata(candidate):
        for key in (
            'context_pack_id',
            'context_pack_sha256',
            'candidate_pack_id',
            'candidate_contract_id',
            'hypothesis_id',
            'mutation_axis',
            'fallback_used',
            'fallback_reason',
            'prompt_maturity_credit_allowed',
            'downstream_result',
        ):
            value = _research_metadata_value(candidate, key)
            if value not in (None, ''):
                score[key] = value
        novelty = candidate.get('discovery_novelty') or _research_metadata_value(candidate, 'novelty')
        if novelty:
            score['novelty'] = novelty
        strict_validation = (
            candidate.get('strict_response_validation')
            or _research_metadata_value(candidate, 'strict_response_validation')
        )
        if strict_validation:
            score['prompt_validation'] = strict_validation
        candidate_result = candidate.get('candidate_result') or {}
        score['official_backtest_result'] = {
            'status': candidate_result.get('status') or candidate.get('status'),
            'promotion_passed': score['promotion_passed'],
            'promotion_score': score['promotion_score'],
            'trade_count': score['trade_count'],
            'trade_count_retention': score['trade_count_retention'],
            'candidate_csv': candidate.get('candidate_csv') or candidate_result.get('csv_path'),
        }
        score['advisory_rank_reason'] = _advisory_rank_reason(candidate, score)
    return score


def _rank_key(candidate: dict) -> tuple:
    score = candidate.get('rank_score') or _rank_score(candidate)
    passed_rank = 0 if score['promotion_passed'] else 1
    score_value = score.get('adjusted_score', score['promotion_score'])
    return (
        passed_rank,
        -score_value,
        -score['trade_count'],
        -score['trade_count_retention'],
        score['date_concentration'],
        score['symbol_concentration'],
        int(candidate.get('index') or 0),
    )


def _rank_candidate_results(
    candidates: list[dict],
    config=None,
) -> tuple[list[dict], dict | None]:
    ranked_candidates = [dict(candidate) for candidate in candidates]
    for candidate in ranked_candidates:
        rank_score = _rank_score(candidate)
        if config is not None and config.use_retention_penalty:
            rank_score = apply_retention_penalty(
                rank_score,
                config.min_estimated_retention,
            )
        candidate['rank'] = None
        candidate['rank_score'] = rank_score
        candidate['selected_as_best'] = False

    eligible_indexes = [
        index
        for index, candidate in enumerate(ranked_candidates)
        if candidate.get('status') == 'ok'
    ]
    ordered_indexes = sorted(
        eligible_indexes,
        key=lambda index: _rank_key(ranked_candidates[index]),
    )

    best_candidate = None
    for rank, candidate_index in enumerate(ordered_indexes, start=1):
        candidate = ranked_candidates[candidate_index]
        candidate['rank'] = rank
        candidate['selected_as_best'] = rank == 1
        if rank == 1:
            best_candidate = candidate

    return ranked_candidates, best_candidate
