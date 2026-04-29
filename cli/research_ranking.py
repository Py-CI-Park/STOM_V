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
    if use_reference:
        score['score_basis'] = 'reference'
        score['incremental_promotion_score'] = _numeric_value(incremental_promotion.get('score'))
        score['reference_promotion_score'] = _numeric_value(reference_promotion.get('score'))
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
