"""State and leaderboard helpers for Wide v2 optimizer runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WideV2OptimizerConfig:
    name: str = 'WideV2AutoLoop'
    baseline_csv: str | None = None
    score_reference_csv: str | None = None
    base_buy_strategy: str = ''
    sell_strategy: str = ''
    seed_candidate: str = ''
    seed_expression: str = ''
    start_date: int = 0
    end_date: int = 0
    is_tick: bool = True
    betting: str = '1'
    avg_time: object = 60
    start_time: int = 90000
    end_time: int = 152800
    engine_count: int = 4
    top_n: int = 1
    min_samples: int = 30
    quantiles: int = 10
    alpha: float = 0.05
    candidate_count: int = 10
    candidate_timeout: int | None = None
    cleanup_best_candidate: bool = False
    keep_loser_candidates: bool = False
    keep_failed_candidate: bool = False
    min_estimated_retention: float = 0.40
    allow_retention_fallback: bool = True
    use_retention_penalty: bool = True
    candidate_pool_multiplier: int = 3
    iteration_v2_mode: str = 'best_feature_mix_v5'
    iteration_v2_primary_feature: str = 'B_시가총액'
    iteration_v2_trade_amount_feature: str = 'B_당일거래대금'
    iteration_v2_secondary_features: str = ''
    iteration_v2_include_secondary_only: bool = True
    iteration_v2_max_secondary_only: int = 1
    iteration_v2_duplicate_retention_tolerance: float = 0.02
    max_rounds: int = 3
    min_improvement: float = 0.01
    stop_after_no_improvement: int = 2
    max_consecutive_candidate_failures: int = 3
    runtime_output_path: str | None = None
    leaderboard_output_path: str | None = None
    summary_output_path: str | None = None
    report_path: str | None = None

    @property
    def run_id(self) -> str:
        return self.name


@dataclass(frozen=True)
class WideV2RoundState:
    round_index: int
    status: str
    stop_reason: str | None
    source_candidate: str
    runtime_json_path: str | None
    round_best_candidate: dict[str, Any] | None


@dataclass(frozen=True)
class WideV2OptimizerResult:
    status: str
    run_id: str
    stop_reason: str
    rounds: list[dict[str, Any]]
    leaderboard: list[dict[str, Any]]
    final_best_candidate: dict[str, Any] | None
    wfo_candidate: dict[str, Any] | None
    summary_output_path: str | None = None
    leaderboard_output_path: str | None = None
    report_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return json_safe_value(asdict(self))


def json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, list):
        return [json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe_value(item) for key, item in value.items()}
    return str(value)


def _path_with_suffix(path: str, suffix: str) -> str:
    original = Path(path)
    updated = original.with_name(f'{original.stem}_{suffix}{original.suffix or ".json"}')
    return str(updated)


def round_runtime_output_path(config: WideV2OptimizerConfig, round_index: int) -> str | None:
    if not config.runtime_output_path:
        return None
    return _path_with_suffix(config.runtime_output_path, f'round{round_index:03d}')


def default_summary_output_path(config: WideV2OptimizerConfig) -> str | None:
    if config.summary_output_path:
        return config.summary_output_path
    if config.runtime_output_path:
        return _path_with_suffix(config.runtime_output_path, 'summary')
    return None


def default_leaderboard_output_path(config: WideV2OptimizerConfig) -> str | None:
    if config.leaderboard_output_path:
        return config.leaderboard_output_path
    if config.runtime_output_path:
        return _path_with_suffix(config.runtime_output_path, 'leaderboard')
    return None


def _score_dict(candidate: dict[str, Any]) -> dict[str, Any] | None:
    score = candidate.get('rank_score')
    return score if isinstance(score, dict) else None


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _optional_float_value(value: Any) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _score_field(score: dict[str, Any] | None, key: str, fallback: Any = None) -> Any:
    if score is not None and key in score:
        return score.get(key)
    return fallback


def _candidate_score(candidate_or_entry: dict[str, Any]) -> float | None:
    if 'adjusted_score' in candidate_or_entry:
        return _optional_float_value(candidate_or_entry.get('adjusted_score'))
    if 'promotion_score' in candidate_or_entry:
        return _optional_float_value(candidate_or_entry.get('promotion_score'))
    score = _score_dict(candidate_or_entry)
    if score is not None and 'adjusted_score' in score:
        return _optional_float_value(score.get('adjusted_score'))
    if score is not None and 'promotion_score' in score:
        return _optional_float_value(score.get('promotion_score'))
    return None


def _candidate_type(candidate: dict[str, Any]) -> str | None:
    for key in ('v5_candidate_type', 'v4_candidate_type', 'v3_candidate_type', 'v2_candidate_type'):
        if candidate.get(key):
            return str(candidate[key])
    return None


def _candidate_csv_path(candidate: dict[str, Any]) -> str | None:
    if candidate.get('candidate_csv'):
        return str(candidate['candidate_csv'])
    candidate_result = candidate.get('candidate_result') or {}
    csv_path = candidate_result.get('csv_path') or candidate_result.get('output_csv')
    return str(csv_path) if csv_path else None


def build_leaderboard_entries(
    *,
    run_id: str,
    round_index: int,
    round_result: dict[str, Any],
    source_baseline: str,
    source_candidate: str,
    runtime_json_path: str | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for position, candidate in enumerate(round_result.get('candidates') or [], start=1):
        score = _score_dict(candidate)
        comparison = candidate.get('comparison') or {}
        candidate_summary = comparison.get('candidate_summary') or {}
        promotion_score = _optional_float_value(_score_field(score, 'promotion_score'))
        adjusted_score = _optional_float_value(
            _score_field(score, 'adjusted_score', promotion_score)
        )
        entry = {
            'run_id': run_id,
            'round_index': round_index,
            'candidate_index': int(candidate.get('index') or position),
            'strategy_name': candidate.get('strategy_name'),
            'expression': candidate.get('expression'),
            'source_baseline': source_baseline,
            'source_candidate': source_candidate,
            'candidate_type': _candidate_type(candidate),
            'status': candidate.get('status'),
            'promotion_passed': bool(score.get('promotion_passed') is True) if score is not None else False,
            'promotion_score': promotion_score,
            'adjusted_score': adjusted_score,
            'score_basis': _score_field(score, 'score_basis', 'incremental'),
            'trade_count': _optional_float_value(
                _score_field(score, 'trade_count', candidate_summary.get('trade_count'))
            ),
            'trade_count_retention': _optional_float_value(
                _score_field(score, 'trade_count_retention', comparison.get('trade_count_retention'))
            ),
            'date_concentration': _optional_float_value(
                _score_field(score, 'date_concentration', candidate_summary.get('date_concentration'))
            ),
            'symbol_concentration': _optional_float_value(
                _score_field(score, 'symbol_concentration', candidate_summary.get('symbol_concentration'))
            ),
            'actual_rowset_selected': candidate.get('actual_rowset_selected') is True,
            'selected_as_round_best': candidate.get('selected_as_best') is True,
            'selected_as_global_best': False,
            'runtime_json_path': runtime_json_path,
            'candidate_csv_path': _candidate_csv_path(candidate),
            'failure_phase': candidate.get('phase') if candidate.get('status') != 'ok' else None,
            'failure_message': candidate.get('message') if candidate.get('status') != 'ok' else None,
            'rank': candidate.get('rank'),
            'rank_score': score,
            'retention_penalty': _optional_float_value(_score_field(score, 'retention_penalty')),
            'reference_promotion_score': _optional_float_value(_score_field(score, 'reference_promotion_score')),
            'incremental_promotion_score': _optional_float_value(_score_field(score, 'incremental_promotion_score')),
        }
        entries.append(json_safe_value(entry))
    return entries


def select_global_best_candidate(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [entry for entry in entries if entry.get('status') == 'ok']
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda entry: (
            entry.get('promotion_passed') is not True,
            -(_candidate_score(entry) if _candidate_score(entry) is not None else float('-inf')),
            -_float_value(entry.get('trade_count')),
            -_float_value(entry.get('trade_count_retention')),
            _float_value(entry.get('date_concentration'), default=float('inf')),
            _float_value(entry.get('symbol_concentration'), default=float('inf')),
            int(entry.get('round_index') or 0),
            int(entry.get('candidate_index') or 0),
        ),
    )


def mark_global_best(
    entries: list[dict[str, Any]],
    global_best: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not global_best:
        return [{**entry, 'selected_as_global_best': False} for entry in entries]
    return [
        {
            **entry,
            'selected_as_global_best': (
                entry.get('round_index') == global_best.get('round_index')
                and entry.get('candidate_index') == global_best.get('candidate_index')
                and entry.get('strategy_name') == global_best.get('strategy_name')
            ),
        }
        for entry in entries
    ]


def compute_improvement(
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> float | None:
    if not current or not previous:
        return None
    current_score = _candidate_score(current)
    previous_score = _candidate_score(previous)
    if current_score is None or previous_score is None:
        return None
    return round(current_score - previous_score, 10)
