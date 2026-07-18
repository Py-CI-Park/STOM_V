from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    csv_path = tmp_path / 'result.csv'
    csv_path.write_text('종목코드,매수시간,매도시간,수익금\n000001,20250101090000,20250101090100,100\n', encoding='utf-8')
    manager = BacktestJobManager(jobs_dir=tmp_path / 'jobs', command_builder=_success_command(str(csv_path)))
    monkeypatch.setattr(backtest_api, 'get_job_manager', lambda: manager)

    job_id = manager.submit(BacktestJobSpec(
        buy='매수A', sell='매도A', start=20250101, end=20250102,
        buy_code='if A:\n    매수 = True\n', sell_code='if B:\n    매도 = True\n',
    ))['job_id']
    _wait_status(manager, job_id, {'success', 'error', 'timeout'})

    jobs = backtest_api.list_jobs()['jobs']
    job = next(j for j in jobs if j['job_id'] == job_id)
    assert job['evidence_id'] == f'job:{job_id}'
    assert job['source_type'] == 'job'
    assert job['condition_identity']['kind'] == 'code_hash'
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
    manager = BacktestJobManager(jobs_dir=tmp_path / 'jobs', command_builder=_no_trades_command())
    monkeypatch.setattr(backtest_api, 'get_job_manager', lambda: manager)
    job_id = manager.submit(BacktestJobSpec(buy='매수A', sell='매도A', start=20250101, end=20250102))['job_id']
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
class _ResultManager:
    def __init__(self, record):
        self.record = record

    def get(self, job_id, log_tail=0):
        return dict(self.record, available=job_id == self.record["job_id"])


def test_result_trade_detail_page_preserves_columns_bounds_and_context(monkeypatch, tmp_path: Path):
    csv_path = tmp_path / "result.csv"
    csv_path.write_text(
        "종목명,시가총액,매수시간,매도시간,보유시간,매수가,매도가,매수금액,매도금액,수익률,수익금,수익금합계,매도조건,추가매수시간\n"
        "알파,1000,202501010900,202501010930,30,10,12,100,120,20,20,20,익절,202501010910\n"
        "베타,,202501011000,202501011030,,20,18,,,,-10,10,손절,\n",
        encoding="utf-8",
    )
    record = {
        "job_id": "job_detail",
        "status": "success",
        "csv_path": str(csv_path),
        "metrics": {},
        "spec": {
            "start": 20250101, "end": 20250102, "timeframe": "tick", "engines": 2,
            "betting": "1000000", "secret_path": str(tmp_path), "buy_code": "hidden",
        },
    }
    monkeypatch.setattr(backtest_api, "get_job_manager", lambda: _ResultManager(record))

    default = backtest_api.get_result(job_id="job_detail")
    assert "trade_details" not in default
    assert set(default["run_context"]) == {"start", "end", "timeframe", "engines", "betting"}

    calls = 0
    real_loader = backtest_api.analysis.load_trades_csv_with_status

    def load_once(path):
        nonlocal calls
        calls += 1
        return real_loader(path)

    monkeypatch.setattr(backtest_api.analysis, "load_trades_csv_with_status", load_once)
    monkeypatch.setattr(
        backtest_api.analysis,
        "full_analysis",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("detail-only recomputed analysis")),
    )
    monkeypatch.setattr(
        backtest_api.analysis,
        "full_analysis_from_trades",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("detail-only recomputed analysis")),
    )
    detail = backtest_api.get_result(
        job_id="job_detail", detail_only=True, detail_limit=100, detail_offset=0,
    )
    page = detail["trade_details"]
    assert calls == 1
    assert set(detail) == {
        "available", "job_id", "status", "evidence_id", "source_type",
        "condition_identity", "run_context", "trade_details",
    }
    assert "analysis" not in detail and "metrics" not in detail
    assert page["status"] == "ok"
    assert page["total"] == 2 and page["limit"] == 100
    assert page["next_offset"] is None and page["has_more"] is False
    assert list(page["items"][0])[:14] == [
        "name", "market_cap", "buy_time", "sell_time", "day", "hold_min", "hold_time",
        "buy_price", "sell_price", "profit_pct", "profit_krw", "cumulative_profit_krw",
        "additional_buy_time", "buy_amount",
    ]
    assert page["items"][0]["name"] == "알파"
    assert page["items"][0]["market_cap"] == 1000.0
    assert page["items"][0]["additional_buy_time"] == "202501010910"
    assert page["items"][1]["hold_time"] is None
    assert page["items"][1]["buy_amount"] is None
    assert str(csv_path) not in json.dumps(detail, ensure_ascii=False)

    boundary = backtest_api._trade_detail_envelope(page["items"], offset=1, limit=1, status="ok")
    assert [item["name"] for item in boundary["items"]] == ["베타"]
    assert boundary["next_offset"] is None and boundary["has_more"] is False

    optimize_record = dict(record, spec={**record["spec"], "mode": "optimize"})
    monkeypatch.setattr(backtest_api, "get_job_manager", lambda: _ResultManager(optimize_record))
    app = FastAPI()
    app.include_router(backtest_api.backtest_router)
    client = TestClient(app)
    unavailable = client.get("/bt/result", params={
        "job_id": "job_detail", "detail_only": "true", "detail_limit": 50,
    })
    assert unavailable.status_code == 200
    assert unavailable.json()["trade_details"]["status"] == "unavailable"
    pending_record = dict(record, status="running")
    monkeypatch.setattr(backtest_api, "get_job_manager", lambda: _ResultManager(pending_record))
    monkeypatch.setattr(
        backtest_api.analysis,
        "load_trades_csv_with_status",
        lambda path: (_ for _ in ()).throw(AssertionError("running artifact must not be read")),
    )
    pending = client.get("/bt/result", params={
        "job_id": "job_detail", "detail_only": "true", "detail_limit": 50,
    })
    assert pending.status_code == 200
    assert pending.json()["trade_details"]["status"] == "unavailable"
    zero_limit = client.get("/bt/result", params={
        "job_id": "job_detail", "detail_only": "true", "detail_limit": 0,
    })
    assert zero_limit.status_code == 422
    over_limit = client.get("/bt/result", params={
        "job_id": "job_detail", "detail_only": "true", "detail_limit": 101,
    })
    assert over_limit.status_code == 422


def test_result_detail_only_distinguishes_empty_missing_and_errors(monkeypatch, tmp_path: Path):
    missing = tmp_path / "missing.csv"
    record = {
        "job_id": "job_missing_detail",
        "status": "success",
        "csv_path": str(missing),
        "metrics": {},
        "spec": {"start": 20250101, "end": 20250102, "timeframe": "min"},
    }
    monkeypatch.setattr(backtest_api, "get_job_manager", lambda: _ResultManager(record))
    missing_page = backtest_api.get_result(
        job_id="job_missing_detail", detail_only=True, detail_limit=50,
    )["trade_details"]
    assert missing_page == {
        "items": [], "total": 0, "offset": 0, "limit": 50, "next_offset": None,
        "has_more": False, "status": "missing",
    }

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("매도시간,수익금\n", encoding="utf-8")
    monkeypatch.setattr(
        backtest_api,
        "get_job_manager",
        lambda: _ResultManager({**record, "job_id": "job_empty_detail", "csv_path": str(empty_csv)}),
    )
    empty_page = backtest_api.get_result(
        job_id="job_empty_detail", detail_only=True, detail_limit=50,
    )["trade_details"]
    assert empty_page["status"] == "empty" and empty_page["items"] == []

    malformed_csv = tmp_path / "malformed.csv"
    malformed_csv.write_text("매도시간,수익률\n20250101100000,1\n", encoding="utf-8")
    monkeypatch.setattr(
        backtest_api,
        "get_job_manager",
        lambda: _ResultManager({**record, "job_id": "job_bad_detail", "csv_path": str(malformed_csv)}),
    )
    error_result = backtest_api.get_result(
        job_id="job_bad_detail", detail_only=True, detail_limit=50,
    )
    error_page = error_result["trade_details"]
    assert error_page["status"] == "error"
    assert error_page["diagnostic"] == "required trade columns are missing"
    assert str(malformed_csv) not in json.dumps(error_result, ensure_ascii=False)

    malformed_rows = tmp_path / "malformed_rows.csv"
    malformed_rows.write_text("매도시간,수익금\nnot-a-time,10\n", encoding="utf-8")
    monkeypatch.setattr(
        backtest_api,
        "get_job_manager",
        lambda: _ResultManager({**record, "job_id": "job_bad_rows", "csv_path": str(malformed_rows)}),
    )
    malformed_page = backtest_api.get_result(
        job_id="job_bad_rows", detail_only=True, detail_limit=50,
    )["trade_details"]
    assert malformed_page["status"] == "error"
    assert malformed_page["diagnostic"] == "trade rows are malformed"

    mixed_rows = tmp_path / "mixed_rows.csv"
    mixed_rows.write_text(
        "매도시간,수익금\n20250101100000,10\nnot-a-time,5\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        backtest_api,
        "get_job_manager",
        lambda: _ResultManager({**record, "job_id": "job_mixed_rows", "csv_path": str(mixed_rows)}),
    )
    mixed_page = backtest_api.get_result(
        job_id="job_mixed_rows", detail_only=True, detail_limit=50,
    )["trade_details"]
    assert mixed_page["status"] == "error"
    assert mixed_page["items"] == []

    nonfinite = tmp_path / "nonfinite.csv"
    nonfinite.write_text("매도시간,수익금\n20250101100000,NaN\n", encoding="utf-8")
    monkeypatch.setattr(
        backtest_api,
        "get_job_manager",
        lambda: _ResultManager({**record, "job_id": "job_nonfinite", "csv_path": str(nonfinite)}),
    )
    nonfinite_page = backtest_api.get_result(
        job_id="job_nonfinite", detail_only=True, detail_limit=50,
    )["trade_details"]
    assert nonfinite_page["status"] == "error"

    frontend = (Path(PROJECT_ROOT) / "ai_strategy_loop/dashboard/frontend/bt-result-area.jsx").read_text(encoding="utf-8")
    assert "<details" in frontend and "onToggle={onToggle}" in frontend
    assert "detail_only=true&detail_limit=" in frontend
    assert "sourceGenerationRef" in frontend and "generation !== sourceGenerationRef.current" in frontend
    assert "controller.abort()" in frontend and "requestAbortRef.current = null" in frontend
    assert "run_context || {}).timeframe" in frontend
    primary_loader = frontend.split("const load = useCallback_btc", 1)[1].split("const loadMc", 1)[0]
    assert "resultRequestAbortRef" in frontend and "resultGenerationRef" in frontend
    assert "resultRequestAbortRef.current.abort()" in primary_loader
    assert "_btFetchJson(url, 8000, controller.signal)" in primary_loader
    assert primary_loader.count("generation !== resultGenerationRef.current") == 2
    assert "generation === resultGenerationRef.current" in primary_loader
    assert frontend.count('unit: key === "avg_hold_time" ? (runTimeframe === "tick" ? "초" : "분") : null') == 2
    assert "fmt: (v, unit) => v.toFixed(1) + (unit || \"분\")" in frontend
    assert 'role="status" aria-live="polite">거래 상세 로딩 중…' in frontend
    assert 'role="alert"' in frontend
    assert 'aria-label="거래 상세 목록"' in frontend
    assert "<caption>거래 상세 — 원본 CSV 순서</caption>" in frontend
    assert '<th key={key} scope="col">{label}</th>' in frontend
