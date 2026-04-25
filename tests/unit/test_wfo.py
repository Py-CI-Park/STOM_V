import json

from cli.config import BacktestConfig
from cli.wfo import (
    generate_walk_forward_windows,
    run_walk_forward,
    save_walk_forward_report,
)


def test_generate_walk_forward_windows_basic():
    windows = generate_walk_forward_windows(
        20240101,
        20240630,
        train_window_days=60,
        test_window_days=20,
        step_days=20,
    )

    assert len(windows) >= 1
    first = windows[0]
    assert first['train_start'] == 20240101
    assert first['purge_days'] == 0
    assert first['embargo_days'] == 0
    assert first['train_end'] < first['test_start'] <= first['test_end']


def test_generate_walk_forward_windows_applies_purge_and_embargo():
    windows = generate_walk_forward_windows(
        20240101,
        20240630,
        train_window_days=30,
        test_window_days=10,
        step_days=10,
        purge_days=2,
        embargo_days=3,
    )

    first = windows[0]
    assert first['test_start'] > first['train_end']
    assert first['embargo_end'] > first['test_end']
    assert first['purge_days'] == 2
    assert first['embargo_days'] == 3


def test_run_walk_forward_uses_best_params_for_test():
    base_config = BacktestConfig(
        buy_strategy='A',
        sell_strategy='B',
        start_date=20240101,
        end_date=20240630,
    )

    def mock_optimize(config, param_space, **kwargs):
        return {
            'status': 'ok',
            'best': {'params': {'avg_time': 120, 'betting': '3'}},
            'results': [],
            'total': 1,
        }

    seen = []

    def mock_run(config):
        seen.append((config.start_date, config.end_date, config.avg_time, config.betting))
        return {'status': 'success', 'metrics': {'tpi': 1.5}}

    result = run_walk_forward(
        base_config,
        {'avg_time': [60, 120], 'betting': ['1', '3']},
        train_window_days=60,
        test_window_days=20,
        step_days=20,
        optimize_fn=mock_optimize,
        run_fn=mock_run,
    )

    assert result['status'] == 'ok'
    assert result['summary']['round_count'] >= 1
    assert result['summary']['success_count'] == len(result['rounds'])
    assert all(avg_time == 120 for _, _, avg_time, _ in seen)
    assert all(betting == '3' for _, _, _, betting in seen)


def test_run_walk_forward_accepts_base_config_dict_from_cli():
    base_config = {
        'buy_strategy': 'A',
        'sell_strategy': 'B',
        'start_date': 20240101,
        'end_date': 20240331,
    }

    def mock_optimize(config, param_space, **kwargs):
        return {
            'status': 'ok',
            'best': {'params': {}},
            'results': [],
            'total': 1,
        }

    seen = []

    def mock_run(config):
        seen.append((config.start_date, config.end_date, config.buy_strategy, config.sell_strategy))
        return {'status': 'success', 'metrics': {'tpi': 1.0, 'trade_count': 5}}

    result = run_walk_forward(
        base_config,
        {},
        train_window_days=30,
        test_window_days=10,
        step_days=30,
        optimize_fn=mock_optimize,
        run_fn=mock_run,
    )

    assert result['status'] == 'ok'
    assert result['summary']['round_count'] == 2
    assert seen[0] == (20240131, 20240209, 'A', 'B')


def test_run_walk_forward_summary_counts_zero_trade_rounds():
    base_config = BacktestConfig(
        buy_strategy='A',
        sell_strategy='B',
        start_date=20240101,
        end_date=20240331,
    )

    def mock_optimize(config, param_space, **kwargs):
        return {
            'status': 'ok',
            'best': {'params': {}},
            'results': [],
            'total': 1,
        }

    call_count = {'n': 0}

    def mock_run(config):
        call_count['n'] += 1
        if call_count['n'] == 1:
            return {'status': 'success', 'metrics': {'tpi': 1.2, 'trade_count': 0}}
        return {'status': 'success', 'metrics': {'tpi': 0.8, 'trade_count': 12}}

    result = run_walk_forward(
        base_config,
        {},
        train_window_days=30,
        test_window_days=10,
        step_days=30,
        optimize_fn=mock_optimize,
        run_fn=mock_run,
    )

    assert result['status'] == 'ok'
    assert result['summary']['round_count'] == 2
    assert result['summary']['zero_trade_rounds'] == 1
    assert result['summary']['trade_count_rounds'] == 2
    assert result['summary']['mean_trade_count'] == 6.0


def test_run_walk_forward_treats_success_without_metrics_as_zero_trade_round():
    base_config = BacktestConfig(
        buy_strategy='A',
        sell_strategy='B',
        start_date=20240101,
        end_date=20240331,
    )

    def mock_optimize(config, param_space, **kwargs):
        return {
            'status': 'ok',
            'best': {'params': {}},
            'results': [],
            'total': 1,
        }

    call_count = {'n': 0}

    def mock_run(config):
        call_count['n'] += 1
        if call_count['n'] == 1:
            return {'status': 'success', 'message': '백테스트 완료 (결과 테이블이 비어있습니다)'}
        return {'status': 'success', 'metrics': {'tpi': 0.8, 'trade_count': 12}}

    result = run_walk_forward(
        base_config,
        {},
        train_window_days=30,
        test_window_days=10,
        step_days=30,
        optimize_fn=mock_optimize,
        run_fn=mock_run,
    )

    assert result['status'] == 'ok'
    assert result['summary']['round_count'] == 2
    assert result['summary']['zero_trade_rounds'] == 1
    assert result['summary']['trade_count_rounds'] == 2
    assert result['summary']['mean_trade_count'] == 6.0


def test_save_walk_forward_report_writes_json(tmp_path):
    result = {
        'status': 'ok',
        'summary': {'round_count': 2},
        'rounds': [],
    }
    out_path = tmp_path / 'wfo_report.json'

    save_result = save_walk_forward_report(result, str(out_path))

    assert save_result['status'] == 'ok'
    saved = json.loads(out_path.read_text(encoding='utf-8'))
    assert saved['summary']['round_count'] == 2
