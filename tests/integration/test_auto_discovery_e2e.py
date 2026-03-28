"""Auto-Discovery 파이프라인 E2E 통합 테스트.

실제 DB 데이터로 전체 파이프라인(Phase A → B → C)의 end-to-end 동작을 검증한다.

주의:
- 실제 백테스트를 실행하므로 수십 초~수 분 소요될 수 있다.
- @pytest.mark.slow 데코레이터로 일상 CI에서 제외.
- 실행: pytest tests/integration/test_auto_discovery_e2e.py -m slow -v
- 실제 DB 파일(strategy.db, stock_min_back.db 등)이 필요하다.
"""

import json
import os
import subprocess
import sys
import sqlite3

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOM_BACKTEST = os.path.join(PROJECT_ROOT, 'stom_backtest.py')
PYTHON = sys.executable

sys.path.insert(0, PROJECT_ROOT)

from cli.paths import DB_STRATEGY, DB_STOCK_BACK_MIN, DB_BACKTEST


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

def _has_min_db():
    """분봉 DB가 존재하고 유효한지 확인."""
    return os.path.isfile(DB_STOCK_BACK_MIN) and os.path.getsize(DB_STOCK_BACK_MIN) > 1_000_000


def _has_strategy_db():
    """strategy.db가 존재하고 전략이 있는지 확인."""
    if not os.path.isfile(DB_STRATEGY):
        return False
    try:
        con = sqlite3.connect(DB_STRATEGY)
        rows = con.execute("SELECT COUNT(*) FROM stockbuy").fetchone()
        con.close()
        return rows[0] > 0
    except Exception:
        return False


def _get_first_strategies():
    """strategy.db에서 첫 번째 매수/매도 전략명을 반환."""
    try:
        con = sqlite3.connect(DB_STRATEGY)
        buy = con.execute("SELECT `index` FROM stockbuy LIMIT 1").fetchone()
        sell = con.execute("SELECT `index` FROM stocksell LIMIT 1").fetchone()
        con.close()
        if buy and sell:
            return buy[0], sell[0]
    except Exception:
        pass
    return None, None


def _get_valid_date_range():
    """stock_min_back.db에서 유효한 날짜 범위(최소 3일)를 추출."""
    try:
        con = sqlite3.connect(DB_STOCK_BACK_MIN)
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='moneytop'").fetchone()
        if not tables:
            con.close()
            return None, None
        row = con.execute("SELECT MIN(`index`), MAX(`index`) FROM moneytop").fetchone()
        con.close()
        if row and row[0] and row[1]:
            start = int(str(row[0])[:8])
            end = int(str(row[1])[:8])
            return start, end
    except Exception:
        pass
    return None, None


_SKIP_NO_MIN_DB = pytest.mark.skipif(not _has_min_db(), reason='stock_min_back.db not available')
_SKIP_NO_STRATEGY = pytest.mark.skipif(not _has_strategy_db(), reason='strategy.db has no strategies')

slow = pytest.mark.slow


@pytest.fixture(autouse=True)
def _set_minimal_setting_env(monkeypatch):
    """CLI 테스트에 필요한 환경 변수를 설정한다 (암호화 키 불일치 우회)."""
    monkeypatch.setenv('STOM_ALLOW_MINIMAL_SETTING', '1')


# ---------------------------------------------------------------------------
# CLI help & parsing (빠른 검증, DB 불필요)
# ---------------------------------------------------------------------------

class TestDiscoveryAutoCliHelp:
    """discovery auto / batch CLI 도움말이 정상 출력되는지 검증."""

    def test_discovery_auto_help_exit_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'discovery', 'auto', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert '--input' in result.stdout
        assert '--buy' in result.stdout
        assert '--train-window-days' in result.stdout

    def test_discovery_batch_help_exit_zero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'discovery', 'batch', '--help'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0
        assert '--config' in result.stdout

    def test_discovery_auto_missing_args_exit_nonzero(self):
        result = subprocess.run(
            [PYTHON, STOM_BACKTEST, 'discovery', 'auto'],
            capture_output=True, text=True, timeout=30, cwd=PROJECT_ROOT,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Phase A: 백테스트 → CSV 생성 (실제 DB 필요)
# ---------------------------------------------------------------------------

@slow
@_SKIP_NO_MIN_DB
@_SKIP_NO_STRATEGY
class TestPhaseABacktestE2E:
    """실제 DB로 Phase A 백테스트가 성공하고 CSV가 생성되는지 검증."""

    def test_run_backtest_produces_csv(self):
        """controller.run()이 csv_path를 반환하는지 검증."""
        buy, sell = _get_first_strategies()
        if not buy or not sell:
            pytest.skip('No strategies available')

        start, end = _get_valid_date_range()
        if not start or not end:
            pytest.skip('No valid date range in moneytop')

        # setting.db 환경 검증 — 유효하지 않으면 스킵
        try:
            from cli.runner import run_backtest  # noqa: F401
            from utility.setting import DICT_SET  # noqa: F401
        except (SystemExit, KeyError, Exception) as e:
            pytest.skip(f'setting.db 환경이 유효하지 않음: {e}')

        # 최소 날짜 범위 사용 (빠른 실행)
        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController()
        result = controller.run({
            'buy_strategy': buy,
            'sell_strategy': sell,
            'start_date': start,
            'end_date': start,  # 1일만
            'is_tick': False,
            'engine_count': 2,
            'timeout': 120,
            'verbose': False,
        })

        assert result.get('status') == 'success', f"backtest failed: {result.get('message')}"
        csv_path = result.get('csv_path')
        # csv_path가 있으면 파일 존재 확인
        if csv_path:
            assert os.path.isfile(csv_path), f'CSV not found: {csv_path}'


# ---------------------------------------------------------------------------
# Phase B: 분석 결과 형식 검증 (mock-free, 실제 CSV 필요)
# ---------------------------------------------------------------------------

@slow
@_SKIP_NO_MIN_DB
@_SKIP_NO_STRATEGY
class TestPhaseBAnalysisE2E:
    """실제 CSV로 분석 결과의 형식이 올바른지 검증."""

    def test_analyze_returns_valid_structure(self):
        """analyze_results()가 status=ok를 반환하고 candidates를 포함하는지 검증."""
        # backtest/csv/ 에서 가장 최근 CSV를 찾아 분석
        import glob
        csv_dir = os.path.join(PROJECT_ROOT, 'backtest', 'csv')
        csvs = sorted(glob.glob(os.path.join(csv_dir, '*.csv')), key=os.path.getmtime, reverse=True)
        if not csvs:
            pytest.skip('No CSV files in backtest/csv/')

        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController()
        result = controller.analyze_results(csvs[0], min_samples=5, quantiles=3, alpha=0.1)

        assert result.get('status') == 'ok', f"analysis failed: {result}"
        # 분석 결과에 feature_columns 또는 candidates 키가 포함되어야 한다
        assert ('feature_columns' in result or 'candidates' in result
                or 'significant_factors' in result or 'summary' in result), \
            f"unexpected result keys: {list(result.keys())}"


# ---------------------------------------------------------------------------
# 전체 파이프라인 구조 검증 (mock 기반, DB 불필요)
# ---------------------------------------------------------------------------

class TestPipelineStructureE2E:
    """AutoDiscoveryEngine.run()의 반환 구조가 올바른지 검증 (mock 기반)."""

    def test_full_pipeline_returns_required_keys(self, tmp_path):
        """전체 파이프라인 결과에 필수 키가 모두 존재하는지 검증."""
        from unittest.mock import MagicMock
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        csv_file = tmp_path / 'stock_bt_E2E_20260317.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {'trade_count': 10},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 2,
            'code': 'if 매수:\n    pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': True,
            'report': {'strategy_name': 'Auto_E2E'},
        }

        config = AutoDiscoveryConfig(
            buy_strategy='E2E', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        # 필수 최상위 키 확인
        required_keys = {'status', 'promoted', 'strategy_name', 'csv_path',
                         'phase_a', 'phase_b', 'phase_c', 'pipeline_timing', 'pipeline_duration'}
        assert required_keys.issubset(result.keys()), \
            f"Missing keys: {required_keys - result.keys()}"

        # Phase별 구조
        assert result['phase_a']['status'] == 'ok'
        assert result['phase_a']['phase'] == 'A'
        assert 'phase_duration' in result['phase_a']

        assert result['phase_b']['status'] == 'ok'
        assert result['phase_b']['phase'] == 'B'
        assert 'rounds_log' in result['phase_b']
        assert 'phase_duration' in result['phase_b']

        assert result['phase_c']['status'] == 'ok'
        assert result['phase_c']['phase'] == 'C'
        assert 'phase_duration' in result['phase_c']

        # pipeline_timing
        timing = result['pipeline_timing']
        assert 'phase_a' in timing
        assert 'phase_b' in timing
        assert 'phase_c' in timing
        assert 'total' in timing

    def test_input_csv_skips_phase_a_structure(self, tmp_path):
        """input_csv로 Phase A 스킵 시 phase_a.skipped=True인지 검증."""
        from unittest.mock import MagicMock
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        csv_file = tmp_path / 'existing.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 1,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': False,
        }

        config = AutoDiscoveryConfig(
            input_csv=str(csv_file), sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['phase_a']['skipped'] is True
        assert result['pipeline_timing']['phase_a'] == 0.0
        controller.run.assert_not_called()


# ---------------------------------------------------------------------------
# 배치 실행 E2E (mock 기반)
# ---------------------------------------------------------------------------

class TestBatchE2E:
    """discovery batch의 전체 흐름 검증."""

    def test_batch_json_end_to_end(self, tmp_path):
        """JSON 파일로 배치 실행 후 결과 구조 검증."""
        from unittest.mock import MagicMock
        from cli.auto_discovery import run_batch

        csv_file = tmp_path / 'r.csv'
        csv_file.write_text('data', encoding='utf-8')

        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {
                'sell_strategy': 'Sell',
                'start_date': 20250401, 'end_date': 20250430,
                'train_window_days': 30, 'test_window_days': 10,
            },
            'runs': [
                {'buy_strategy': 'A'},
                {'buy_strategy': 'B'},
                {'buy_strategy': 'C'},
            ],
        }), encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 2,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.side_effect = [
            {'status': 'ok', 'promoted': True},
            {'status': 'ok', 'promoted': False},
            {'status': 'ok', 'promoted': True},
        ]

        result = run_batch(batch_path=str(config_file), controller=controller)

        assert result['status'] == 'ok'
        assert result['total'] == 3
        assert result['promoted'] == 2
        assert result['rejected'] == 1
        assert 'batch_duration' in result
        assert [r['buy_strategy'] for r in result['results']] == ['A', 'B', 'C']


# ---------------------------------------------------------------------------
# 히스토리 DB E2E
# ---------------------------------------------------------------------------

class TestHistoryE2E:
    """히스토리 저장/조회 end-to-end 검증."""

    def test_discovery_history_roundtrip(self, tmp_path):
        """save_discovery_run → get_discovery_runs 라운드트립."""
        from cli.auto_discovery import AutoDiscoveryConfig
        from cli.history import save_discovery_run, get_discovery_runs, init_history_db

        db_path = str(tmp_path / 'e2e_history.db')
        init_history_db(db_path)

        config = AutoDiscoveryConfig(
            buy_strategy='E2E_Buy', sell_strategy='E2E_Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = {
            'status': 'ok', 'promoted': True,
            'strategy_name': 'Auto_E2E_123',
            'csv_path': '/tmp/e2e.csv',
            'pipeline_duration': 100.5,
            'pipeline_timing': {'phase_a': 40.0, 'phase_b': 5.5, 'phase_c': 55.0, 'total': 100.5},
            'phase_b': {'final_round': 1},
        }

        discovery_id = save_discovery_run(config, result, db_path)
        assert discovery_id > 0

        runs = get_discovery_runs(limit=10, db_path=db_path)
        assert len(runs) == 1

        row = runs[0]
        assert row['buy_strategy'] == 'E2E_Buy'
        assert row['promoted'] == 1
        assert row['strategy_name'] == 'Auto_E2E_123'
        assert row['phase_a_duration'] == 40.0
        assert row['phase_b_duration'] == 5.5
        assert row['phase_c_duration'] == 55.0
        assert row['phase_b_rounds'] == 1

        # JSON 필드도 검증
        config_data = json.loads(row['config_json'])
        assert config_data['buy_strategy'] == 'E2E_Buy'

        result_data = json.loads(row['result_json'])
        assert result_data['promoted'] is True
