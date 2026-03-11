"""Walk-Forward Optimization orchestration (library-only)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from cli.config import BacktestConfig


def _int_to_date(d: int) -> datetime:
    return datetime.strptime(str(d), '%Y%m%d')


def _date_to_int(d: datetime) -> int:
    return int(d.strftime('%Y%m%d'))


def generate_walk_forward_windows(
    start_date: int,
    end_date: int,
    train_window_days: int,
    test_window_days: int,
    step_days: int | None = None,
    purge_days: int = 0,
    embargo_days: int = 0,
) -> list[dict]:
    if train_window_days < 1 or test_window_days < 1:
        raise ValueError('train_window_days와 test_window_days는 1 이상이어야 합니다.')
    if purge_days < 0 or embargo_days < 0:
        raise ValueError('purge_days와 embargo_days는 0 이상이어야 합니다.')

    step_days = step_days or test_window_days
    if step_days < 1:
        raise ValueError('step_days는 1 이상이어야 합니다.')

    start = _int_to_date(start_date)
    end = _int_to_date(end_date)
    cursor = start
    windows = []
    round_no = 1

    while True:
        train_start = cursor
        train_end = train_start + timedelta(days=train_window_days - 1)
        test_start = train_end + timedelta(days=1 + purge_days)
        test_end = test_start + timedelta(days=test_window_days - 1)
        embargo_end = test_end + timedelta(days=embargo_days)

        if test_end > end:
            break

        windows.append({
            'round': round_no,
            'train_start': _date_to_int(train_start),
            'train_end': _date_to_int(train_end),
            'test_start': _date_to_int(test_start),
            'test_end': _date_to_int(test_end),
            'purge_days': purge_days,
            'embargo_days': embargo_days,
            'embargo_end': _date_to_int(embargo_end),
        })
        round_no += 1
        cursor += timedelta(days=step_days)

    return windows


def _make_config(base_config, overrides: dict):
    base_dict = asdict(base_config) if hasattr(base_config, '__dataclass_fields__') else dict(base_config)
    merged = {**base_dict, **overrides}
    return BacktestConfig(**merged)


def run_walk_forward(
    base_config,
    param_space: dict,
    train_window_days: int,
    test_window_days: int,
    step_days: int | None = None,
    purge_days: int = 0,
    embargo_days: int = 0,
    objective: str = 'tpi',
    method: str = 'grid',
    maximize: bool = True,
    max_iter: int = 10,
    optimize_fn=None,
    run_fn=None,
    on_progress=None,
) -> dict:
    if optimize_fn is None:
        from cli.optimizer import optimize as optimize_fn
    if run_fn is None:
        from cli.runner import run_backtest as run_fn

    windows = generate_walk_forward_windows(
        base_config.start_date,
        base_config.end_date,
        train_window_days=train_window_days,
        test_window_days=test_window_days,
        step_days=step_days,
        purge_days=purge_days,
        embargo_days=embargo_days,
    )

    rounds = []
    for index, window in enumerate(windows, start=1):
        train_config = _make_config(base_config, {
            'start_date': window['train_start'],
            'end_date': window['train_end'],
        })
        optimization = optimize_fn(
            train_config,
            param_space,
            objective=objective,
            method=method,
            maximize=maximize,
            max_iter=max_iter,
        )
        best = optimization.get('best') or {'params': {}}
        best_params = best.get('params', {})

        test_config = _make_config(base_config, {
            'start_date': window['test_start'],
            'end_date': window['test_end'],
            **best_params,
        })
        test_result = run_fn(test_config)
        round_result = {
            'window': window,
            'train_optimization': optimization,
            'best_params': best_params,
            'test_result': test_result,
        }
        rounds.append(round_result)
        if on_progress is not None:
            on_progress(index, len(windows), round_result)

    metric_name = objective
    valid_scores = []
    success_count = 0
    trade_counts = []
    for round_result in rounds:
        test_result = round_result['test_result']
        if test_result.get('status') == 'success':
            success_count += 1
        metrics = test_result.get('metrics') or {}
        metric_value = metrics.get(metric_name)
        if metric_value is not None:
            valid_scores.append(float(metric_value))
        trade_count = metrics.get('trade_count')
        if trade_count is not None:
            trade_counts.append(float(trade_count))

    zero_trade_rounds = sum(1 for trade_count in trade_counts if trade_count <= 0)

    summary = {
        'round_count': len(rounds),
        'success_count': success_count,
        'success_rate': (success_count / len(rounds)) if rounds else 0.0,
        'metric': metric_name,
        'mean_oos_metric': (sum(valid_scores) / len(valid_scores)) if valid_scores else None,
        'best_oos_metric': max(valid_scores) if valid_scores and maximize else (min(valid_scores) if valid_scores else None),
        'trade_count_rounds': len(trade_counts),
        'zero_trade_rounds': zero_trade_rounds,
        'mean_trade_count': (sum(trade_counts) / len(trade_counts)) if trade_counts else None,
    }

    return {
        'status': 'ok',
        'objective': objective,
        'method': method,
        'windows': windows,
        'rounds': rounds,
        'summary': summary,
    }


def save_walk_forward_report(result: dict, path: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(result, fp, ensure_ascii=False, indent=2)
        return {'status': 'ok', 'path': path}
    except Exception as e:
        return {'status': 'error', 'path': path, 'error': str(e)}
