"""연속 백테스트 — 파라미터 스윕 + 날짜 롤링."""

import os
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli.config import BacktestConfig
from cli.runner import run_backtest


def _int_to_date(d):
    return datetime.strptime(str(d), '%Y%m%d')


def _date_to_int(d):
    return int(d.strftime('%Y%m%d'))


def generate_combinations(sweep_params: dict) -> list:
    """모든 파라미터 조합을 생성한다.

    Args:
        sweep_params: {'avg_time': [60, 120], 'betting': ['1', '3']} 형태의 dict.

    Returns:
        각 조합을 나타내는 dict의 리스트.
    """
    if not sweep_params:
        return [{}]

    keys = list(sweep_params.keys())
    values = [sweep_params[k] for k in keys]

    combos = []
    for combo_values in product(*values):
        combos.append(dict(zip(keys, combo_values)))
    return combos


def generate_rolling_windows(start_date: int, end_date: int,
                             window_days: int, step_days: int) -> list:
    """롤링 날짜 윈도우를 생성한다.

    Args:
        start_date: 시작일자 YYYYMMDD 정수.
        end_date:   종료일자 YYYYMMDD 정수.
        window_days: 윈도우 길이 (일수).
        step_days:   스텝 크기 (일수).

    Returns:
        (window_start, window_end) 정수 튜플의 리스트.
        window_end = window_start + window_days - 1 (포함).
    """
    current = _int_to_date(start_date)
    end = _int_to_date(end_date)

    windows = []
    while current <= end:
        window_end = current + timedelta(days=window_days - 1)
        windows.append((_date_to_int(current), _date_to_int(window_end)))
        current += timedelta(days=step_days)
    return windows


def run_sweep(base_config, sweep_params: dict, on_progress=None) -> list:
    """파라미터 조합별로 백테스트를 실행한다.

    base_config는 절대 변경하지 않는다 (불변성).

    Args:
        base_config: BacktestConfig 인스턴스 (원본).
        sweep_params: 스윕할 파라미터 dict.
        on_progress: 진행 콜백 callable(current, total, combo) — 선택.

    Returns:
        각 조합의 백테스트 결과 dict 리스트. 각 결과에 'params' 키 추가.
    """
    combos = generate_combinations(sweep_params)
    total = len(combos)
    results = []

    base_dict = asdict(base_config)

    for i, combo in enumerate(combos):
        overrides = {**base_dict, **combo}
        new_config = BacktestConfig(**overrides)

        result = run_backtest(new_config)
        result = {**result, 'params': combo}
        results.append(result)

        if on_progress is not None:
            on_progress(i + 1, total, combo)

    return results


def run_rolling(base_config, window_days: int, step_days: int,
                on_progress=None) -> list:
    """롤링 윈도우별로 백테스트를 실행한다.

    base_config는 절대 변경하지 않는다 (불변성).

    Args:
        base_config: BacktestConfig 인스턴스 (원본).
        window_days: 윈도우 길이 (일수).
        step_days:   스텝 크기 (일수).
        on_progress: 진행 콜백 callable(current, total, window) — 선택.

    Returns:
        각 윈도우의 백테스트 결과 dict 리스트. 각 결과에 'window' 키 추가.
    """
    windows = generate_rolling_windows(
        base_config.start_date, base_config.end_date, window_days, step_days
    )
    total = len(windows)
    results = []

    base_dict = asdict(base_config)

    for i, (win_start, win_end) in enumerate(windows):
        overrides = {**base_dict, 'start_date': win_start, 'end_date': win_end}
        new_config = BacktestConfig(**overrides)

        result = run_backtest(new_config)
        result = {**result, 'window': (win_start, win_end)}
        results.append(result)

        if on_progress is not None:
            on_progress(i + 1, total, (win_start, win_end))

    return results
