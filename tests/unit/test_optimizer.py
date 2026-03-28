"""US-504: 파라미터 최적화 엔진 테스트."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cli.optimizer import (
    GridOptimizer, RandomOptimizer, optimize,
    _make_config, _extract_score, _VALID_OBJECTIVES,
)
from cli.config import BacktestConfig


# === mock run_fn ===

def _mock_run(config):
    """파라미터 기반 가짜 백테스트 결과."""
    avg = config.avg_time if isinstance(config.avg_time, int) else config.avg_time[0]
    betting = int(config.betting) if config.betting else 1
    tpi = avg * 0.01 + betting * 0.5
    return {
        'status': 'success',
        'metrics': {
            'trade_count': avg,
            'win_rate': 50.0 + betting,
            'total_profit_pct': avg * betting,
            'tpi': tpi,
            'cagr': tpi * 10,
            'mdd_pct': -5.0 - betting,
        },
    }


def _mock_run_error(config):
    return {'status': 'error', 'message': 'test error', 'metrics': None}


@pytest.fixture
def base_config():
    return BacktestConfig(
        buy_strategy='TestBuy',
        sell_strategy='TestSell',
        start_date=20250407,
        end_date=20250409,
        is_tick=False,
    )


# === GridOptimizer ===

class TestGridOptimizer:
    def test_empty_param_space(self):
        opt = GridOptimizer({}, 'tpi')
        assert opt.total == 1
        assert opt.combinations() == [{}]

    def test_single_param(self):
        opt = GridOptimizer({'avg_time': [60, 120, 180]}, 'tpi')
        assert opt.total == 3
        combos = opt.combinations()
        assert {'avg_time': 60} in combos
        assert {'avg_time': 180} in combos

    def test_multi_param(self):
        opt = GridOptimizer(
            {'avg_time': [60, 120], 'betting': ['1', '3']}, 'tpi'
        )
        assert opt.total == 4
        combos = opt.combinations()
        assert {'avg_time': 60, 'betting': '1'} in combos
        assert {'avg_time': 120, 'betting': '3'} in combos

    def test_invalid_objective(self):
        with pytest.raises(ValueError, match='유효하지 않은 objective'):
            GridOptimizer({'avg_time': [60]}, 'invalid_metric')


# === RandomOptimizer ===

class TestRandomOptimizer:
    def test_max_iter(self):
        opt = RandomOptimizer(
            {'avg_time': [60, 120, 180]}, 'tpi',
            max_iter=5, seed=42,
        )
        assert opt.total == 5
        combos = opt.combinations()
        assert len(combos) == 5

    def test_seed_reproducibility(self):
        opt1 = RandomOptimizer({'avg_time': [60, 120]}, 'tpi', max_iter=3, seed=42)
        opt2 = RandomOptimizer({'avg_time': [60, 120]}, 'tpi', max_iter=3, seed=42)
        assert opt1.combinations() == opt2.combinations()

    def test_different_seeds(self):
        opt1 = RandomOptimizer(
            {'avg_time': list(range(100))}, 'tpi', max_iter=10, seed=1
        )
        opt2 = RandomOptimizer(
            {'avg_time': list(range(100))}, 'tpi', max_iter=10, seed=2
        )
        assert opt1.combinations() != opt2.combinations()

    def test_invalid_objective(self):
        with pytest.raises(ValueError):
            RandomOptimizer({'avg_time': [60]}, 'bad')


# === optimize() ===

class TestOptimize:
    def test_grid_basic(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60, 120]},
            objective='tpi',
            method='grid',
            run_fn=_mock_run,
        )
        assert result['status'] == 'ok'
        assert result['total'] == 2
        assert result['method'] == 'grid'
        assert result['objective'] == 'tpi'
        assert len(result['results']) == 2
        assert result['best'] is not None
        # best should have higher tpi (120 > 60)
        assert result['best']['params']['avg_time'] == 120

    def test_random_basic(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60, 120, 180]},
            objective='tpi',
            method='random',
            max_iter=3,
            seed=42,
            run_fn=_mock_run,
        )
        assert result['status'] == 'ok'
        assert result['total'] == 3
        assert result['method'] == 'random'

    def test_results_sorted_descending(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60, 120, 180]},
            objective='tpi',
            maximize=True,
            run_fn=_mock_run,
        )
        scores = [r['score'] for r in result['results']]
        assert scores == sorted(scores, reverse=True)

    def test_minimize_mode(self, base_config):
        result = optimize(
            base_config,
            {'betting': ['1', '3', '5']},
            objective='mdd_pct',
            maximize=False,
            run_fn=_mock_run,
        )
        assert result['status'] == 'ok'
        scores = [r['score'] for r in result['results']]
        assert scores == sorted(scores)

    def test_invalid_objective(self, base_config):
        result = optimize(base_config, {}, objective='bad', run_fn=_mock_run)
        assert result['status'] == 'error'

    def test_invalid_method(self, base_config):
        result = optimize(
            base_config, {}, method='bayesian', run_fn=_mock_run
        )
        assert result['status'] == 'error'

    def test_on_progress_called(self, base_config):
        progress_log = []

        def on_progress(current, total, combo, result):
            progress_log.append((current, total))

        optimize(
            base_config,
            {'avg_time': [60, 120]},
            run_fn=_mock_run,
            on_progress=on_progress,
        )
        assert len(progress_log) == 2
        assert progress_log[0] == (1, 2)
        assert progress_log[1] == (2, 2)

    def test_run_fn_error_handled(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60]},
            run_fn=_mock_run_error,
        )
        assert result['status'] == 'ok'
        assert result['results'][0]['result']['status'] == 'error'

    def test_save_fn_called(self, base_config):
        saved = []

        def mock_save(config, result, duration):
            saved.append({'config': config, 'result': result})

        optimize(
            base_config,
            {'avg_time': [60, 120]},
            run_fn=_mock_run,
            save_fn=mock_save,
        )
        assert len(saved) == 2

    def test_save_fn_exception_ignored(self, base_config):
        def bad_save(config, result, duration):
            raise RuntimeError('DB error')

        result = optimize(
            base_config,
            {'avg_time': [60]},
            run_fn=_mock_run,
            save_fn=bad_save,
        )
        assert result['status'] == 'ok'

    def test_multi_param_grid(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60, 120], 'betting': ['1', '3']},
            run_fn=_mock_run,
        )
        assert result['total'] == 4

    def test_duration_tracked(self, base_config):
        result = optimize(
            base_config,
            {'avg_time': [60]},
            run_fn=_mock_run,
        )
        assert 'duration' in result['results'][0]
        assert result['results'][0]['duration'] >= 0


# === Helpers ===

class TestHelpers:
    def test_make_config(self, base_config):
        new = _make_config(base_config, {'avg_time': 120})
        assert new.avg_time == 120
        assert base_config.avg_time == 60  # 원본 불변

    def test_extract_score_success(self):
        result = {'metrics': {'tpi': 1.5}}
        assert _extract_score(result, 'tpi', True) == 1.5

    def test_extract_score_missing(self):
        result = {'metrics': {}}
        assert _extract_score(result, 'tpi', True) == float('-inf')
        assert _extract_score(result, 'tpi', False) == float('inf')

    def test_extract_score_no_metrics(self):
        result = {'metrics': None}
        assert _extract_score(result, 'tpi', True) == float('-inf')

    def test_valid_objectives(self):
        assert 'tpi' in _VALID_OBJECTIVES
        assert 'win_rate' in _VALID_OBJECTIVES
        assert 'cagr' in _VALID_OBJECTIVES
