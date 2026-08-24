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
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


# 실CSV 와 동형(필요 컬럼만): 종목명/매수시간/매도시간/보유시간/수익률/수익금
#   + 청산사유(매도조건)·R_MAE/R_MFE + 오더플로우(2단계 C) 컬럼.
_CSV_FIELDS = [
    "종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금",
    "매도조건", "R_MAE", "R_MFE",
    "B_체결강도", "B_매수총잔량", "B_매도총잔량", "B_전일동시간비", "B_등락율",
]


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> str:
    # 누락 컬럼은 빈칸(restval), 미정의 키는 무시(extrasaction) — 부분 행 허용.
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return str(path)


def _orderflow_csv(path: Path) -> str:
    """승/패 분리가 명확한 오더플로우 합성 CSV — 다일·다요일(검정 표본 확보)."""
    rows: List[Dict[str, Any]] = []
    for i in range(20):
        rows.append({
            "종목명": "승", "매수시간": f"2025040{(i % 4) + 7}093000",
            "매도시간": f"2025040{(i % 4) + 7}100000", "보유시간": 30,
            "수익률": 2.0, "수익금": 20000, "매도조건": "익절", "R_MAE": -0.2, "R_MFE": 2.5,
            "B_체결강도": 130.0, "B_매수총잔량": 9000, "B_매도총잔량": 2000,
            "B_전일동시간비": 320.0, "B_등락율": 5.0,
        })
    for i in range(20):
        rows.append({
            "종목명": "패", "매수시간": f"2025040{(i % 4) + 7}113000",
            "매도시간": f"2025040{(i % 4) + 7}120000", "보유시간": 30,
            "수익률": -1.5, "수익금": -15000, "매도조건": "손절", "R_MAE": -1.8, "R_MFE": 0.3,
            "B_체결강도": 55.0, "B_매수총잔량": 2000, "B_매도총잔량": 9000,
            "B_전일동시간비": 140.0, "B_등락율": 1.0,
        })
    return _write_csv(path, rows)


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
    return authorized_dashboard_client(create_app())


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
        monkeypatch.setattr(BA, "REPO_ROOT", Path(csv_path).resolve().parent)

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

    def test_result_exposes_bounded_process_diagnostics(self, monkeypatch, client, tmp_path):
        csv_path = _sample_csv(tmp_path / "bt.csv")
        record = {
            "available": True, "status": "success", "csv_path": csv_path,
            "metrics": {"trade_count": 3},
            "process_diagnostics": {
                "event_count": 2,
                "last_checkpoint": "backtest_child_mq_first_received",
                "last_by_source": {"BackTest": "backtest_child_mq_first_received"},
            },
        }
        monkeypatch.setattr(BA, "get_job_manager", lambda: _FakeJobManager(record, csv_path))
        body = client.get("/bt/result", params={"job_id": "J1"}).json()
        assert body["process_diagnostics"] == record["process_diagnostics"]


# --------------------------------------------- 2단계 B/C — montecarlo·orderflow
class TestMonteCarloAndOrderflow:
    def _patch_manager(self, monkeypatch, csv_path: str) -> None:
        rec = {"available": True, "status": "success", "csv_path": csv_path}
        monkeypatch.setattr(BA, "get_job_manager", lambda: _FakeJobManager(rec, csv_path))
        monkeypatch.setattr(BA, "REPO_ROOT", Path(csv_path).resolve().parent)

    def test_montecarlo_endpoint_shape(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _orderflow_csv(tmp_path / "of.csv"))
        r = client.get("/bt/analysis/montecarlo", params={"job_id": "J1", "n": 300, "seed": 5})
        assert r.status_code == 200
        mc = r.json()["montecarlo"]
        assert mc["n"] == 300
        for key in ("mdd_pct", "mdd_krw", "final"):
            assert set(mc[key].keys()) == {"p5", "p25", "p50", "p75", "p95"}
        assert 0.0 <= mc["ruin_prob"] <= 1.0
        assert len(mc["fan"]) <= 200

    def test_montecarlo_n_capped(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _orderflow_csv(tmp_path / "of.csv"))
        r = client.get("/bt/analysis/montecarlo", params={"job_id": "J1", "n": 999999, "seed": 1})
        assert r.json()["montecarlo"]["n"] == BA._MC_MAX_N

    def test_orderflow_endpoint_separation(self, monkeypatch, client, tmp_path):
        self._patch_manager(monkeypatch, _orderflow_csv(tmp_path / "of.csv"))
        r = client.get("/bt/analysis/orderflow", params={"job_id": "J1"})
        of = r.json()["orderflow"]
        assert "separation" in of and of["separation"]
        # 체결강도 승(130) > 패(55) → diff +75.
        sep = {s["var"]: s for s in of["separation"]}
        assert abs(sep["strength"]["diff"] - 75.0) < 1e-6


# ------------------------------------------------------------ 2단계 A — compare
class TestCompare:
    def _patch_two_jobs(self, monkeypatch, csv_a: str, csv_b: str) -> None:
        """job_a/job_b 를 서로 다른 CSV·메트릭으로 매핑하는 가짜 매니저."""

        class _TwoJobManager:
            def get(self, job_id, log_tail=0):
                if job_id == "A":
                    return {"available": True, "status": "success", "csv_path": csv_a,
                            "metrics": {"total_profit_pct": 10.0}, "job_id": "A"}
                if job_id == "B":
                    return {"available": True, "status": "success", "csv_path": csv_b,
                            "metrics": {"total_profit_pct": 25.0}, "job_id": "B"}
                return {"available": False, "job_id": job_id}

            def result_csv_path(self, job_id):
                return csv_a if job_id == "A" else (csv_b if job_id == "B" else None)

        monkeypatch.setattr(BA, "get_job_manager", lambda: _TwoJobManager())

    def test_compare_two_jobs(self, monkeypatch, client, tmp_path):
        self._patch_two_jobs(monkeypatch, _sample_csv(tmp_path / "a.csv"), _orderflow_csv(tmp_path / "b.csv"))
        r = client.get("/bt/compare", params={"job_a": "A", "job_b": "B"})
        assert r.status_code == 200
        body = r.json()
        assert body["a"] is not None and body["b"] is not None
        assert body["a"]["job_id"] == "A" and body["b"]["job_id"] == "B"
        # CLI 메트릭 우선.
        assert body["a"]["metrics"]["total_profit_pct"] == 10.0
        assert body["b"]["metrics"]["total_profit_pct"] == 25.0
        # equity 누적곡선 존재.
        assert "cumulative" in body["a"]["equity"]
        # delta 는 summary 기준(b-a) — trade_count 차이 산출.
        assert "delta" in body
        assert "trade_count" in body["delta"]

    def test_compare_missing_side_null(self, monkeypatch, client, tmp_path):
        self._patch_two_jobs(monkeypatch, _sample_csv(tmp_path / "a.csv"), _orderflow_csv(tmp_path / "b.csv"))
        r = client.get("/bt/compare", params={"job_a": "A", "job_b": "ghost"})
        body = r.json()
        assert body["a"] is not None
        assert body["b"] is None
        assert body["delta"] == {}

    def test_compare_self_compare(self, monkeypatch, client, tmp_path):
        # 동일 잡 self-compare 허용(스모크 게이트 4번) — delta 전부 0.
        self._patch_two_jobs(monkeypatch, _sample_csv(tmp_path / "a.csv"), _orderflow_csv(tmp_path / "b.csv"))
        r = client.get("/bt/compare", params={"job_a": "A", "job_b": "A"})
        body = r.json()
        assert body["a"]["job_id"] == "A" and body["b"]["job_id"] == "A"
        assert all(abs(v) < 1e-9 for v in body["delta"].values())
