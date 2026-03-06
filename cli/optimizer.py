"""파라미터 최적화 엔진 — Grid / Random 탐색."""

import os
import sys
import random
import time
from dataclasses import asdict
from itertools import product

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cli.config import BacktestConfig


_VALID_OBJECTIVES = (
    'trade_count', 'win_rate', 'total_profit_pct',
    'tpi', 'cagr', 'mdd_pct',
)


def _make_config(base_config, overrides: dict):
    """base_config를 변경하지 않고 overrides를 적용한 새 config를 반환한다."""
    base_dict = asdict(base_config) if hasattr(base_config, '__dataclass_fields__') else dict(base_config)
    merged = {**base_dict, **overrides}
    return BacktestConfig(**merged)


def _extract_score(result: dict, objective: str, maximize: bool):
    """결과에서 objective 점수를 추출한다. 없으면 -inf/inf."""
    metrics = result.get('metrics') or {}
    score = metrics.get(objective, None)
    if score is None:
        return float('-inf') if maximize else float('inf')
    return float(score)


class GridOptimizer:
    """전수 조합 (Grid Search) 최적화."""

    def __init__(self, param_space: dict, objective: str = 'tpi',
                 maximize: bool = True):
        if objective not in _VALID_OBJECTIVES:
            raise ValueError(
                f"유효하지 않은 objective: '{objective}'. "
                f"허용: {_VALID_OBJECTIVES}"
            )
        self.param_space = param_space
        self.objective = objective
        self.maximize = maximize
        self._combinations = self._generate()

    def _generate(self) -> list:
        if not self.param_space:
            return [{}]
        keys = list(self.param_space.keys())
        values = [self.param_space[k] for k in keys]
        return [dict(zip(keys, combo)) for combo in product(*values)]

    @property
    def total(self) -> int:
        return len(self._combinations)

    def combinations(self) -> list:
        return list(self._combinations)


class RandomOptimizer:
    """랜덤 샘플링 최적화."""

    def __init__(self, param_space: dict, objective: str = 'tpi',
                 maximize: bool = True, max_iter: int = 10, seed: int = None):
        if objective not in _VALID_OBJECTIVES:
            raise ValueError(
                f"유효하지 않은 objective: '{objective}'. "
                f"허용: {_VALID_OBJECTIVES}"
            )
        self.param_space = param_space
        self.objective = objective
        self.maximize = maximize
        self.max_iter = max_iter
        self._rng = random.Random(seed)

    def _sample_one(self) -> dict:
        combo = {}
        for key, values in self.param_space.items():
            combo[key] = self._rng.choice(values)
        return combo

    @property
    def total(self) -> int:
        return self.max_iter

    def combinations(self) -> list:
        return [self._sample_one() for _ in range(self.max_iter)]


def optimize(base_config, param_space: dict, objective: str = 'tpi',
             method: str = 'grid', maximize: bool = True,
             max_iter: int = 10, seed: int = None,
             run_fn=None, save_fn=None,
             on_progress=None) -> dict:
    """통합 최적화 함수.

    Args:
        base_config: BacktestConfig 기본 설정.
        param_space: {'avg_time': [60, 120], 'betting': ['1', '3']} 등.
        objective:   최적화 대상 metric.
        method:      'grid' 또는 'random'.
        maximize:    True=최대화, False=최소화 (mdd_pct 등).
        max_iter:    random 모드에서 최대 반복 횟수.
        seed:        random 시드.
        run_fn:      백테스트 실행 함수 (기본: runner.run_backtest).
        save_fn:     히스토리 저장 함수 (기본: None → 저장 안 함).
        on_progress: 진행 콜백 callable(current, total, combo, result).

    Returns:
        dict:
            status:  'ok' | 'error'
            results: 정렬된 결과 리스트 (best first)
            best:    최고 결과 dict
            total:   총 실행 횟수
            objective: 사용된 objective
            method:  사용된 method
    """
    if objective not in _VALID_OBJECTIVES:
        return {
            'status': 'error',
            'message': f"유효하지 않은 objective: '{objective}'",
        }

    if method == 'grid':
        optimizer = GridOptimizer(param_space, objective, maximize)
    elif method == 'random':
        optimizer = RandomOptimizer(param_space, objective, maximize,
                                    max_iter, seed)
    else:
        return {
            'status': 'error',
            'message': f"유효하지 않은 method: '{method}'. 'grid' 또는 'random'만 가능합니다.",
        }

    if run_fn is None:
        from cli.runner import run_backtest
        run_fn = run_backtest

    combos = optimizer.combinations()
    total = len(combos)
    results = []

    for i, combo in enumerate(combos):
        config = _make_config(base_config, combo)
        start_time = time.time()

        try:
            result = run_fn(config)
        except Exception as e:
            result = {'status': 'error', 'message': str(e), 'metrics': None}

        duration = time.time() - start_time
        score = _extract_score(result, objective, maximize)

        entry = {
            'params': combo,
            'result': result,
            'score': score,
            'duration': round(duration, 2),
        }
        results.append(entry)

        if save_fn is not None:
            try:
                save_fn(config, result, duration)
            except Exception:
                pass

        if on_progress is not None:
            on_progress(i + 1, total, combo, result)

    results.sort(key=lambda x: x['score'], reverse=maximize)

    best = results[0] if results else None

    return {
        'status': 'ok',
        'results': results,
        'best': best,
        'total': total,
        'objective': objective,
        'method': method,
    }
