"""cli/history.py 단위 테스트.

대상: init_history_db, save_run, get_runs, get_best_run, compare_runs, delete_run
"""

import os
import sys
import sqlite3

import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cli.history import (
    init_history_db,
    save_run,
    get_runs,
    get_best_run,
    compare_runs,
    delete_run,
)
from cli.config import BacktestConfig


# ============================================================
# 공통 fixtures
# ============================================================

@pytest.fixture
def db(tmp_path):
    """테스트 전용 히스토리 DB 경로."""
    return str(tmp_path / 'test_history.db')


@pytest.fixture
def sample_config():
    """기본 BacktestConfig 인스턴스."""
    return BacktestConfig(
        buy_strategy='TestBuy',
        sell_strategy='TestSell',
        start_date=20250101,
        end_date=20250131,
    )


@pytest.fixture
def sample_result_success():
    """성공 백테스트 결과 dict."""
    return {
        'status': 'success',
        'message': '백테스트 완료',
        'metrics': {
            'trade_count': 100,
            'win_rate': 55.0,
            'avg_profit_pct': 0.8,
            'total_profit_pct': 10.0,
            'tpi': 1.5,
            'cagr': 12.0,
            'mdd_pct': -7.0,
        },
    }


@pytest.fixture
def sample_result_error():
    """에러 백테스트 결과 dict."""
    return {
        'status': 'error',
        'message': '전략 없음',
        'metrics': None,
    }


# ============================================================
# init_history_db
# ============================================================

class TestInitHistoryDb:
    def test_init_creates_db(self, db):
        """init_history_db 호출 후 DB 파일이 생성되어야 한다."""
        init_history_db(db)
        assert os.path.exists(db)

    def test_init_creates_runs_table(self, db):
        """init_history_db 호출 후 runs 테이블이 존재해야 한다."""
        init_history_db(db)
        con = sqlite3.connect(db)
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runs'"
        )
        result = cur.fetchone()
        con.close()
        assert result is not None, "runs 테이블이 존재해야 한다"

    def test_init_is_idempotent(self, db):
        """두 번 호출해도 오류 없이 동일한 경로를 반환해야 한다."""
        path1 = init_history_db(db)
        path2 = init_history_db(db)
        assert path1 == path2 == db

    def test_init_returns_db_path(self, db):
        """init_history_db는 사용된 db_path 문자열을 반환해야 한다."""
        result = init_history_db(db)
        assert result == db


# ============================================================
# save_run
# ============================================================

class TestSaveRun:
    def test_save_run_returns_id(self, db, sample_config, sample_result_success):
        """save_run은 양의 정수 run_id를 반환해야 한다."""
        run_id = save_run(sample_config, sample_result_success, 3.5, db_path=db)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_save_run_with_dataclass(self, db, sample_config, sample_result_success):
        """BacktestConfig dataclass 입력을 올바르게 저장해야 한다."""
        run_id = save_run(sample_config, sample_result_success, 2.0, db_path=db)
        rows = get_runs(db_path=db)
        assert len(rows) == 1
        assert rows[0]['run_id'] == run_id
        assert rows[0]['buy_strategy'] == 'TestBuy'

    def test_save_run_with_dict(self, db, sample_result_success):
        """dict 입력을 올바르게 저장해야 한다."""
        config_dict = {
            'buy_strategy': 'DictBuy',
            'sell_strategy': 'DictSell',
            'start_date': 20250201,
            'end_date': 20250228,
        }
        run_id = save_run(config_dict, sample_result_success, 1.0, db_path=db)
        rows = get_runs(db_path=db)
        assert any(r['buy_strategy'] == 'DictBuy' for r in rows)
        assert run_id > 0

    def test_save_run_stores_metrics(self, db, sample_config, sample_result_success):
        """metrics 값이 개별 컬럼에 저장되어야 한다."""
        save_run(sample_config, sample_result_success, 5.0, db_path=db)
        rows = get_runs(db_path=db)
        row = rows[0]
        assert row['trade_count'] == 100
        assert row['win_rate'] == 55.0
        assert row['tpi'] == 1.5

    def test_save_run_stores_status(self, db, sample_config, sample_result_error):
        """status 컬럼이 result['status'] 값과 일치해야 한다."""
        save_run(sample_config, sample_result_error, 0.1, db_path=db)
        rows = get_runs(db_path=db)
        assert rows[0]['status'] == 'error'

    def test_save_run_increments_id(self, db, sample_config, sample_result_success):
        """두 번 저장하면 run_id가 순차 증가해야 한다."""
        id1 = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        id2 = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        assert id2 > id1


# ============================================================
# get_runs
# ============================================================

class TestGetRuns:
    def test_get_runs_default(self, db, sample_config, sample_result_success):
        """기본 조회 시 저장된 런을 반환해야 한다."""
        save_run(sample_config, sample_result_success, 1.0, db_path=db)
        rows = get_runs(db_path=db)
        assert len(rows) == 1

    def test_get_runs_empty_db(self, db):
        """빈 DB에서 조회하면 빈 리스트를 반환해야 한다."""
        rows = get_runs(db_path=db)
        assert rows == []

    def test_get_runs_with_strategy_filter(self, db, sample_result_success):
        """strategy 필터가 buy_strategy LIKE '%strategy%' 로 동작해야 한다."""
        config_a = BacktestConfig(buy_strategy='AlphaBuy', sell_strategy='S', start_date=20250101, end_date=20250131)
        config_b = BacktestConfig(buy_strategy='BetaBuy', sell_strategy='S', start_date=20250101, end_date=20250131)
        save_run(config_a, sample_result_success, 1.0, db_path=db)
        save_run(config_b, sample_result_success, 1.0, db_path=db)

        rows = get_runs(strategy='Alpha', db_path=db)
        assert len(rows) == 1
        assert rows[0]['buy_strategy'] == 'AlphaBuy'

    def test_get_runs_with_status_filter(self, db, sample_config, sample_result_success, sample_result_error):
        """status 필터가 정확히 일치하는 행만 반환해야 한다."""
        save_run(sample_config, sample_result_success, 1.0, db_path=db)
        save_run(sample_config, sample_result_error, 0.1, db_path=db)

        success_rows = get_runs(status='success', db_path=db)
        error_rows = get_runs(status='error', db_path=db)

        assert len(success_rows) == 1
        assert len(error_rows) == 1
        assert success_rows[0]['status'] == 'success'
        assert error_rows[0]['status'] == 'error'

    def test_get_runs_limit(self, db, sample_config, sample_result_success):
        """limit 파라미터가 반환 행 수를 제한해야 한다."""
        for _ in range(5):
            save_run(sample_config, sample_result_success, 1.0, db_path=db)
        rows = get_runs(limit=3, db_path=db)
        assert len(rows) == 3

    def test_get_runs_returns_dicts(self, db, sample_config, sample_result_success):
        """각 행이 dict 타입으로 반환되어야 한다."""
        save_run(sample_config, sample_result_success, 1.0, db_path=db)
        rows = get_runs(db_path=db)
        assert all(isinstance(r, dict) for r in rows)

    def test_get_runs_ordered_by_timestamp_desc(self, db, sample_config, sample_result_success):
        """최근 순으로 정렬되어야 한다."""
        id1 = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        id2 = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        rows = get_runs(db_path=db)
        assert rows[0]['run_id'] == id2
        assert rows[1]['run_id'] == id1


# ============================================================
# get_best_run
# ============================================================

class TestGetBestRun:
    def _make_result(self, tpi, trade_count=50):
        return {
            'status': 'success',
            'metrics': {
                'trade_count': trade_count,
                'win_rate': 50.0,
                'total_profit_pct': tpi * 5,
                'tpi': tpi,
                'cagr': tpi * 8,
                'mdd_pct': -tpi,
            },
        }

    def test_get_best_run_by_tpi(self, db):
        """TPI 기준 최고 런을 반환해야 한다."""
        cfg = BacktestConfig(buy_strategy='B', sell_strategy='S', start_date=20250101, end_date=20250131)
        id1 = save_run(cfg, self._make_result(1.0), 1.0, db_path=db)
        id2 = save_run(cfg, self._make_result(2.5), 1.0, db_path=db)
        id3 = save_run(cfg, self._make_result(0.5), 1.0, db_path=db)

        best = get_best_run(metric='tpi', db_path=db)
        assert len(best) == 1
        assert best[0]['run_id'] == id2

    def test_get_best_run_invalid_metric(self, db):
        """허용되지 않은 metric은 ValueError를 발생시켜야 한다."""
        with pytest.raises(ValueError):
            get_best_run(metric='invalid_col', db_path=db)

    def test_get_best_run_only_success(self, db):
        """status='success'인 런만 포함해야 한다."""
        cfg = BacktestConfig(buy_strategy='B', sell_strategy='S', start_date=20250101, end_date=20250131)
        save_run(cfg, {'status': 'error', 'metrics': None}, 0.1, db_path=db)
        save_run(cfg, self._make_result(1.0), 1.0, db_path=db)

        best = get_best_run(metric='tpi', db_path=db)
        assert all(r['status'] == 'success' for r in best)

    def test_get_best_run_empty_db(self, db):
        """빈 DB에서 조회하면 빈 리스트를 반환해야 한다."""
        best = get_best_run(metric='tpi', db_path=db)
        assert best == []

    def test_get_best_run_limit(self, db):
        """limit 파라미터가 반환 행 수를 제한해야 한다."""
        cfg = BacktestConfig(buy_strategy='B', sell_strategy='S', start_date=20250101, end_date=20250131)
        for tpi in [1.0, 2.0, 3.0]:
            save_run(cfg, self._make_result(tpi), 1.0, db_path=db)
        best = get_best_run(metric='tpi', limit=2, db_path=db)
        assert len(best) == 2


# ============================================================
# compare_runs
# ============================================================

class TestCompareRuns:
    def _make_result(self, tpi):
        return {
            'status': 'success',
            'metrics': {
                'trade_count': 80,
                'win_rate': 55.0,
                'total_profit_pct': tpi * 5,
                'tpi': tpi,
                'cagr': tpi * 8,
                'mdd_pct': -tpi * 2,
            },
        }

    def test_compare_runs(self, db):
        """두 런 비교 시 runs 리스트와 best dict를 반환해야 한다."""
        cfg = BacktestConfig(buy_strategy='B', sell_strategy='S', start_date=20250101, end_date=20250131)
        id1 = save_run(cfg, self._make_result(1.0), 1.0, db_path=db)
        id2 = save_run(cfg, self._make_result(3.0), 1.0, db_path=db)

        result = compare_runs([id1, id2], db_path=db)
        assert 'runs' in result
        assert 'best' in result
        assert len(result['runs']) == 2
        assert result['best']['tpi'] == id2

    def test_compare_runs_empty_ids(self, db):
        """빈 run_ids면 runs=[], best={} 를 반환해야 한다."""
        result = compare_runs([], db_path=db)
        assert result == {'runs': [], 'best': {}}

    def test_compare_runs_best_contains_metric_keys(self, db):
        """best dict는 metric 이름을 키로 가져야 한다."""
        cfg = BacktestConfig(buy_strategy='B', sell_strategy='S', start_date=20250101, end_date=20250131)
        id1 = save_run(cfg, self._make_result(2.0), 1.0, db_path=db)
        result = compare_runs([id1], db_path=db)
        assert 'tpi' in result['best']


# ============================================================
# delete_run
# ============================================================

class TestDeleteRun:
    def test_delete_run_success(self, db, sample_config, sample_result_success):
        """존재하는 런을 삭제하면 True를 반환해야 한다."""
        run_id = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        assert delete_run(run_id, db_path=db) is True

    def test_delete_run_removes_row(self, db, sample_config, sample_result_success):
        """삭제 후 get_runs에서 해당 런이 조회되지 않아야 한다."""
        run_id = save_run(sample_config, sample_result_success, 1.0, db_path=db)
        delete_run(run_id, db_path=db)
        rows = get_runs(db_path=db)
        assert not any(r['run_id'] == run_id for r in rows)

    def test_delete_run_nonexistent_returns_false(self, db):
        """존재하지 않는 run_id 삭제 시 False를 반환해야 한다."""
        init_history_db(db)
        assert delete_run(99999, db_path=db) is False


# ============================================================
# save → get round-trip
# ============================================================

class TestRoundTrip:
    def test_save_and_get_round_trip(self, db):
        """저장한 값을 조회하면 동일한 값을 반환해야 한다."""
        config = BacktestConfig(
            buy_strategy='RoundTripBuy',
            sell_strategy='RoundTripSell',
            start_date=20250301,
            end_date=20250331,
        )
        result = {
            'status': 'success',
            'metrics': {
                'trade_count': 77,
                'win_rate': 62.3,
                'total_profit_pct': 8.8,
                'tpi': 1.23,
                'cagr': 10.5,
                'mdd_pct': -5.1,
            },
        }
        run_id = save_run(config, result, 4.2, db_path=db)
        rows = get_runs(db_path=db)
        assert len(rows) == 1
        row = rows[0]
        assert row['run_id'] == run_id
        assert row['buy_strategy'] == 'RoundTripBuy'
        assert row['sell_strategy'] == 'RoundTripSell'
        assert row['start_date'] == 20250301
        assert row['end_date'] == 20250331
        assert row['status'] == 'success'
        assert row['trade_count'] == 77
        assert abs(row['win_rate'] - 62.3) < 1e-6
        assert abs(row['tpi'] - 1.23) < 1e-6
        assert abs(row['duration_sec'] - 4.2) < 1e-6
