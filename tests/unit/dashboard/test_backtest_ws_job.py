"""라이브 잡 WS(/bt/ws_job) + 분석 범위/MAE·MFE/청산사유 API 계약 테스트 (1단계).

- WS /bt/ws_job: TestClient websocket 으로 진행 push → 터미널 도달 시 close.
  잡 매니저는 가짜(_FakeJobManager)로 주입(실백테 미실행).
- /bt/analysis/mae_mfe·exit_reasons + 범위 쿼리(t_start/t_end): 가짜 매니저 +
  실제 command_builder 가짜 잡 대신 합성 per-trade CSV 로 검증.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api as BA  # noqa: E402


# 실CSV 와 동형(필요 컬럼만): 종목명/매수시간/매도시간/보유시간/수익률/수익금
#   + 청산사유(매도조건)·R_MAE/R_MFE.
_CSV_FIELDS = [
    "종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금",
    "매도조건", "R_MAE", "R_MFE",
]


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> str:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(path)


def _sample_csv(path: Path) -> str:
    rows = [
        {"종목명": "알파", "매수시간": "20250407093000", "매도시간": "20250407100000",
         "보유시간": 30, "수익률": 2.0, "수익금": 20000, "매도조건": "익절", "R_MAE": -0.5, "R_MFE": 2.4},
        {"종목명": "베타", "매수시간": "20250407103000", "매도시간": "20250407110000",
         "보유시간": 30, "수익률": -1.0, "수익금": -10000, "매도조건": "손절", "R_MAE": -1.3, "R_MFE": 0.2},
        {"종목명": "감마", "매수시간": "20250408133000", "매도시간": "20250408140000",
         "보유시간": 30, "수익률": 3.0, "수익금": 30000, "매도조건": "익절", "R_MAE": -0.1, "R_MFE": 3.1},
    ]
    return _write_csv(path, rows)


class _FakeJobManager:
    """get/result_csv_path/list_jobs 만 제공하는 가짜 매니저(실백테 미실행)."""

    def __init__(self, record: Dict[str, Any], csv_path: str = "") -> None:
        self._record = record
        self._csv = csv_path

    def get(self, job_id: str, log_tail: int = 0) -> Dict[str, Any]:
        out = dict(self._record)
        out.setdefault("job_id", job_id)
        out["log_tail"] = ["line A", "line B"][:log_tail] if log_tail else []
        return out

    def result_csv_path(self, job_id: str) -> str:
        return self._csv

    def list_jobs(self) -> Dict[str, Any]:
        return {"jobs": [], "count": 0}


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    from ai_strategy_loop.dashboard.app import create_app
    return TestClient(create_app())


# ------------------------------------------------------------------- WS /ws_job
class TestWsJob:
    def test_terminal_job_pushes_then_closes(self, monkeypatch, client):
        rec = {"available": True, "status": "success", "progress": 1.0,
               "phase": "done", "started_at": 100.0, "finished_at": 130.0, "message": "ok"}
        monkeypatch.setattr(BA, "get_job_manager", lambda: _FakeJobManager(rec))
        with client.websocket_connect("/bt/ws_job?job_id=J1") as ws:
            m = ws.receive_json()
            assert m["job_id"] == "J1"
            assert m["status"] == "success"
            assert m["terminal"] is True
            assert m["elapsed"] == 30.0
            assert isinstance(m["log_tail"], list)

    def test_missing_job_id_errors(self, client):
        with client.websocket_connect("/bt/ws_job") as ws:
            m = ws.receive_json()
            assert "error" in m

    def test_unknown_job_errors(self, monkeypatch, client):
        monkeypatch.setattr(
            BA, "get_job_manager",
            lambda: _FakeJobManager({"available": False}),
        )
        with client.websocket_connect("/bt/ws_job?job_id=nope") as ws:
            m = ws.receive_json()
            assert "error" in m

    def test_running_then_terminal(self, monkeypatch, client):
        """첫 폴은 running, 다음 폴은 success — 두 페이로드 후 close."""
        seq = [
            {"available": True, "status": "running", "progress": 0.4, "phase": "running",
             "started_at": 100.0, "finished_at": None, "message": ""},
            {"available": True, "status": "success", "progress": 1.0, "phase": "done",
             "started_at": 100.0, "finished_at": 110.0, "message": "ok"},
        ]
        calls = {"n": 0}

        class _Seq(_FakeJobManager):
            def get(self, job_id: str, log_tail: int = 0) -> Dict[str, Any]:
                rec = seq[min(calls["n"], len(seq) - 1)]
                calls["n"] += 1
                out = dict(rec)
                out["job_id"] = job_id
                out["log_tail"] = []
                return out

        monkeypatch.setattr(BA, "get_job_manager", lambda: _Seq({}))
        # WS push 간격을 0 에 가깝게(테스트 속도).
        monkeypatch.setattr(BA, "_WS_JOB_INTERVAL_SEC", 0.01)
        with client.websocket_connect("/bt/ws_job?job_id=J2") as ws:
            first = ws.receive_json()
            assert first["status"] == "running"
            assert first["terminal"] is False
            second = ws.receive_json()
            assert second["status"] == "success"
            assert second["terminal"] is True


# --------------------------------------------------------- analysis range / D
class TestAnalysisRangeAndMaeMfe:
    def _patch_manager(self, monkeypatch, csv_path: str) -> None:
        rec = {"available": True, "status": "success", "csv_path": csv_path}
        monkeypatch.setattr(BA, "get_job_manager", lambda: _FakeJobManager(rec, csv_path))

    def test_mae_mfe_endpoint(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _sample_csv(tmp_path / "bt.csv"))
        r = client.get("/bt/analysis/mae_mfe", params={"job_id": "J1"})
        body = r.json()
        assert r.status_code == 200
        pts = body["mae_mfe"]
        assert len(pts) == 3
        assert set(pts[0].keys()) == {"mae", "mfe", "pnl_pct", "hold_sec", "code"}

    def test_exit_reasons_endpoint(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _sample_csv(tmp_path / "bt.csv"))
        r = client.get("/bt/analysis/exit_reasons", params={"job_id": "J1"})
        rows = r.json()["exit_reasons"]
        reasons = {x["reason"] for x in rows}
        assert reasons == {"익절", "손절"}

    def test_range_filter_on_summary(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _sample_csv(tmp_path / "bt.csv"))
        # day1(20250407) 거래만(매수시간 < 20250408).
        r = client.get("/bt/analysis/summary",
                       params={"job_id": "J1", "t_end": 20250407999999})
        summary = r.json()["summary"]
        assert summary["trade_count"] == 2

    def test_result_ranged_metrics_use_summary(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _sample_csv(tmp_path / "bt.csv"))
        r = client.get("/bt/result",
                       params={"job_id": "J1", "t_start": 20250408000000})
        body = r.json()
        assert body["ranged"] is True
        assert body["analysis"]["trade_count"] == 1
        # 구간 분석 시 metrics 는 구간 summary 로 대체.
        assert body["metrics"]["trade_count"] == 1
