"""Candidate cleanup helpers for research iterations."""

from __future__ import annotations

from cli.paths import DB_STRATEGY
from cli.strategy_generator import delete_strategy_from_db


_CLEANUP_SAFE_FAILURE_PHASES = {
    'candidate_backtest',
    'candidate_backtest_timeout',
    'candidate_csv_missing',
    'comparison',
}


def _cleanup_candidate_by_name(
    strategy_name: str,
    reason: str,
    *,
    delete_strategy_func=delete_strategy_from_db,
) -> dict:
    try:
        result = delete_strategy_func(DB_STRATEGY, strategy_name, 'buy')
    except Exception as e:
        return {
            'attempted': True,
            'reason': reason,
            'strategy_name': strategy_name,
            'status': 'error',
            'message': str(e),
        }
    return {
        'attempted': True,
        'reason': reason,
        'strategy_name': strategy_name,
        'status': result.get('status'),
        'message': result.get('message'),
        'action': result.get('action'),
    }


def _candidate_not_created_cleanup(strategy_name: str, reason: str = 'candidate_not_created') -> dict:
    return {
        'attempted': False,
        'reason': reason,
        'strategy_name': strategy_name,
    }


def _cleanup_summary(candidates: list[dict]) -> dict:
    summary = {
        'attempted_count': 0,
        'deleted_count': 0,
        'kept_count': 0,
        'failed_count': 0,
        'items': [],
    }
    for candidate in candidates:
        cleanup = candidate.get('cleanup') or {}
        summary['items'].append(cleanup)
        if cleanup.get('attempted') is True:
            summary['attempted_count'] += 1
            if cleanup.get('status') == 'error':
                summary['failed_count'] += 1
            elif cleanup.get('action') == 'deleted' or str(cleanup.get('reason', '')).endswith('_deleted'):
                summary['deleted_count'] += 1
        elif cleanup:
            summary['kept_count'] += 1
    return summary


def _apply_iteration_cleanup(
    config,
    candidates: list[dict],
    *,
    delete_strategy_func=delete_strategy_from_db,
) -> tuple[list[dict], dict]:
    updated_candidates = []
    for candidate in candidates:
        updated = dict(candidate)
        existing_cleanup = updated.get('cleanup')
        if existing_cleanup is not None:
            preserved = dict(existing_cleanup)
            preserved['existing'] = True
            updated['cleanup'] = preserved
            updated_candidates.append(updated)
            continue

        strategy_name = updated.get('strategy_name')
        is_best = updated.get('selected_as_best') is True
        is_failed = updated.get('status') != 'ok'

        if is_best and not config.cleanup_best_candidate:
            updated['cleanup'] = {
                'attempted': False,
                'reason': 'best_candidate_kept',
                'strategy_name': strategy_name,
            }
        elif is_best:
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'best_candidate_deleted',
                delete_strategy_func=delete_strategy_func,
            )
        elif is_failed and (
            updated.get('phase') in _CLEANUP_SAFE_FAILURE_PHASES
            or updated.get('cleanup_safe') is True
        ):
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'failed_candidate_deleted',
                delete_strategy_func=delete_strategy_func,
            )
        elif is_failed:
            updated['cleanup'] = _candidate_not_created_cleanup(strategy_name)
        elif config.keep_loser_candidates:
            updated['cleanup'] = {
                'attempted': False,
                'reason': 'loser_candidate_kept',
                'strategy_name': strategy_name,
            }
        else:
            updated['cleanup'] = _cleanup_candidate_by_name(
                strategy_name,
                'loser_candidate_deleted',
                delete_strategy_func=delete_strategy_func,
            )
        updated_candidates.append(updated)

    return updated_candidates, _cleanup_summary(updated_candidates)
