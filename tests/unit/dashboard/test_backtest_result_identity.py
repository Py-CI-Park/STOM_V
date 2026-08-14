from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.dashboard import backtest_api  # noqa: E402
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobManager, BacktestJobSpec  # noqa: E402


def _strategy_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('INSERT INTO stockbuy VALUES (?, ?)', ('매수A', 'if A:\n    매수 = True\n'))
    con.execute('INSERT INTO stocksell VALUES (?, ?)', ('매도A', 'if B:\r\n    매도 = True\r\n'))
    con.commit()
    con.close()


def _success_command(csv_path: str):
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':7.5}}))"
    )

    def builder(spec):
        return [sys.executable, '-c', code]

    return builder


def _no_trades_command():
    def builder(spec):
        return [sys.executable, '-c', "import json; print(json.dumps({'status':'error','message':'backtest completed without metrics'})); raise SystemExit(2)"]

    return builder


def _wait_status(manager: BacktestJobManager, job_id: str, statuses: set[str]) -> dict:
    deadline = time.time() + 10
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get('status') in statuses:
            return rec
        time.sleep(0.05)
    return manager.get(job_id)


def test_condition_identity_uses_code_hash_and_legacy_confidence(monkeypatch, tmp_path: Path):
    db = tmp_path / 'strategy.db'
    _strategy_db(db)
    monkeypatch.setenv('STOM_WEBBT_STRATEGY_DB', str(db))

    identity = backtest_api._condition_identity(
        '매수A', '매도A',
        buy_code='if A:\n    매수 = True\n',
        sell_code='if B:\r\n    매도 = True\r\n',
    )
    assert identity['kind'] == 'code_hash'
    assert identity['confidence'] == 'high'
    assert identity['buy_hash']
    assert identity['sell_hash']
    assert identity['buy_hash'] == backtest_api._condition_code_hash('if A:\r\n    매수 = True')

    legacy = backtest_api._condition_identity('매수A', '매도A')
    assert legacy['kind'] == 'name_only_legacy'
    assert legacy['confidence'] == 'low'
    assert legacy['artifact_note']


def test_jobs_api_adds_evidence_identity_actions_and_preserves_result_fields(monkeypatch, tmp_path: Path):
    db = tmp_path / 'strategy.db'
    _strategy_db(db)
    monkeypatch.setenv('STOM_WEBBT_STRATEGY_DB', str(db))
    monkeypatch.setattr(backtest_api, 'REPO_ROOT', tmp_path)
    csv_path = tmp_path / 'result.csv'
    csv_path.write_text('종목코드,매수시간,매도시간,수익금\n000001,20250101090000,20250101090100,100\n', encoding='utf-8')
    manager = BacktestJobManager(
        jobs_dir=tmp_path / 'jobs',
        command_builder=_success_command(str(csv_path)),
        strategy_db=db,
    )
    monkeypatch.setattr(backtest_api, 'get_job_manager', lambda: manager)

    job_id = manager.submit(BacktestJobSpec(
        buy='매수A', sell='매도A', start=20250101, end=20250102,
        buy_code='if A:\n    매수 = True\n', sell_code='if B:\n    매도 = True\n',
    ))['job_id']
    con = sqlite3.connect(db)
    try:
        con.execute('UPDATE stockbuy SET "전략코드"=? WHERE "index"=?', ('mutated buy', '매수A'))
        con.execute('UPDATE stocksell SET "전략코드"=? WHERE "index"=?', ('mutated sell', '매도A'))
        con.commit()
    finally:
        con.close()
    _wait_status(manager, job_id, {'success', 'error', 'timeout'})

    jobs = backtest_api.list_jobs()['jobs']
    job = next(j for j in jobs if j['job_id'] == job_id)
    assert job['evidence_id'] == f'job:{job_id}'
    assert job['source_type'] == 'job'
    assert job['condition_identity']['kind'] == 'code_hash'
    assert job['condition_identity']['buy_hash'] == backtest_api._condition_code_hash('if A:\n    매수 = True\n')
    assert job['condition_identity']['sell_hash'] == backtest_api._condition_code_hash('if B:\n    매도 = True\n')
    assert job['status_kind'] == 'success'
    assert 'open_result' in job['open_actions']
    assert 'open_report' in job['open_actions']
    assert job['rerun_spec']['buy'] == '매수A'

    result = backtest_api.get_result(job_id=job_id)
    for key in ['available', 'job_id', 'status', 'metrics', 'analysis']:
        assert key in result
    assert result['evidence_id'] == f'job:{job_id}'
    assert result['condition_identity']['confidence'] == 'high'


def test_no_trades_is_openable_and_auto_detail_contract(monkeypatch, tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / 'jobs',
        command_builder=_no_trades_command(),
        strategy_db=tmp_path / 'missing_strategy.db',
    )
    monkeypatch.setattr(backtest_api, 'get_job_manager', lambda: manager)
    job_id = manager.submit(BacktestJobSpec(
        buy='매수A',
        sell='매도A',
        start=20250101,
        end=20250102,
        buy_code='if A:\n    매수 = True\n',
        sell_code='if B:\n    매도 = True\n',
    ))['job_id']
    _wait_status(manager, job_id, {'no_trades', 'error', 'timeout'})

    job = backtest_api.get_job(job_id)
    assert job['status'] == 'no_trades'
    assert job['status_kind'] == 'no_trades'
    assert job['openable'] is True
    assert 'open_result' in job['open_actions']

    frontend = (Path(PROJECT_ROOT) / 'ai_strategy_loop' / 'dashboard' / 'frontend' / 'bt-tab-run.jsx').read_text(encoding='utf-8')
    assert 'activeJob.status === "success" || activeJob.status === "no_trades"' in frontend
    assert 'open_actions' in frontend
    assert 'rerun_same_condition' in frontend
    assert 'recover_result' in frontend
    assert 'recoverJob' in frontend
    assert 'hasActionTaxonomy' in frontend
    assert 'successAutoOpen' in frontend
    assert 'hasActionTaxonomy && successAutoOpen && canOpenByTaxonomy' in frontend


def test_missing_artifact_exposes_recover_and_rerun_actions(tmp_path: Path):
    record = {
        'job_id': 'job_missing',
        'status': 'success',
        'csv_path': str(tmp_path / 'missing.csv'),
        'spec': {'buy': '매수A', 'sell': '매도A', 'start': 20250101, 'end': 20250102},
    }

    taxonomy = backtest_api._status_taxonomy(record)
    assert taxonomy['status_kind'] == 'artifact_missing'
    assert taxonomy['artifact_state'] == 'success_without_openable_artifact'
    assert taxonomy['recoverable'] is True
    assert 'recover_result' in taxonomy['open_actions']
    assert 'rerun_same_condition' in taxonomy['open_actions']
    assert taxonomy['rerun_spec']['buy'] == '매수A'


def test_artifact_resolver_is_repo_root_relative_and_bounded(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / 'repo'
    inside = repo_root / 'backtest' / 'csv' / 'result.csv'
    outside = tmp_path / 'outside.csv'
    inside.parent.mkdir(parents=True)
    inside.write_text('x\n', encoding='utf-8')
    outside.write_text('secret\n', encoding='utf-8')
    monkeypatch.setattr(backtest_api, 'REPO_ROOT', repo_root)

    assert Path(backtest_api._resolve_artifact_path('backtest/csv/result.csv')).resolve() == inside.resolve()
    assert backtest_api._resolve_artifact_path('../outside.csv') is None
    assert backtest_api._resolve_artifact_path(str(outside)) is None


def test_demo_result_exposes_phase1_additive_fields(monkeypatch):
    monkeypatch.setattr(backtest_api, '_ensure_demo_csv', lambda: None)

    result = backtest_api._demo_result()
    assert result['available'] is True
    assert result['source_type'] == 'demo'
    assert result['evidence_id'].startswith('demo:')
    assert result['condition_identity']['kind'] == 'name_only_legacy'
    assert result['status_kind'] == 'success'
    assert result['open_actions'] == ['open_result']
    assert result['rerun_spec'] is None


def test_connected_backtest_idle_never_selects_implicit_demo_result() -> None:
    frontend = (
        Path(PROJECT_ROOT)
        / "ai_strategy_loop"
        / "dashboard"
        / "frontend"
        / "bt-tab-root.jsx"
    ).read_text(encoding="utf-8")

    assert "showDemoResult" not in frontend
    assert 'effectiveJobId' not in frontend
    assert 'jobId={resultJobId}' in frontend
    assert '"__demo__"' not in frontend
