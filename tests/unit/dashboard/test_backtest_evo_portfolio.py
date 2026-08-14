"""Backtest 워크벤치 PR3 — 진화 세대 분석 + 포트폴리오 결합 API 테스트.

검증 범위:
  - GET /bt/evo_gens?run_id=: loop_runs.db(읽기 전용) 세대 목록(gen_no·이름·trade·gate·has_csv).
  - GET /bt/result?run_id=&gen_no=: 잡과 동일 스키마(CSV 있으면 풀 분석, 부재면 축약).
  - POST /bt/portfolio: 잡/세대 2~6개 결합(개수 경계·해석 실패·합성 결과).
모두 무예외 계약(데이터 없음/충돌도 HTTP 200 + 표준 페이로드).
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api  # noqa: E402
from ai_strategy_loop.dashboard import backtest_jobs as J  # noqa: E402


# --------------------------------------------------------------------- fixtures
def _make_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
    cur.execute('CREATE TABLE formula ("수식명" TEXT, "수식코드" TEXT)')
    con.commit()
    con.close()


def _make_trades_csv(path: Path, n: int = 60, *, sign: int = 1) -> str:
    """analysis 가 기대하는 per-trade 컬럼명으로 CSV 생성.

    sign=+1 이면 짝수 인덱스 이익(전반 흑자), sign=-1 이면 부호 반전(전반 적자) —
    포트폴리오 상관/기여 테스트가 서로 다른 손익 패턴을 만들 수 있게 한다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금",
            "R_MFE", "R_MAE", "매도조건",
        ])
        w.writeheader()
        for i in range(n):
            day = (i % 25) + 1
            base = 1.2 if i % 2 == 0 else -0.7
            pct = base * sign
            w.writerow({
                "종목명": f"종목{i % 5}",
                "매수시간": f"202301{day:02d}0930{(i % 50):02d}",
                "매도시간": f"202301{day:02d}094500",
                "보유시간": 15 + (i % 30),
                "수익률": pct,
                "수익금": 12000 if pct > 0 else -7000,
                "R_MFE": abs(pct) + 0.6,
                "R_MAE": -(abs(pct) + 0.4),
                "매도조건": "목표가" if pct > 0 else "손절",
            })
    return str(path)


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "strategy.db"
    _make_strategy_db(db_path)
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(J, "_manager", None)
    monkeypatch.setattr(J, "_JOBS_DIR", tmp_path / "webbt_jobs")
    from ai_strategy_loop.dashboard.app import create_app
    return authorized_dashboard_client(create_app())


def _seed_gen(tmp_path: Path, run_id: str, gen_no: int, *, csv_path=None,
              status: str = "ok", gate: bool = True, trades: int = 60,
              profit: float = 150000.0) -> None:
    """loop_runs.db 에 세대 한 줄을 영속한다(쓰기 — 일반 LoopState)."""
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.start_run(LoopConfig(), run_id=run_id)
        st.record_generation(
            run_id, gen_no, buy_name=f"AILOOP_{run_id}_g{gen_no}_buy",
            sell_name=f"AILOOP_{run_id}_g{gen_no}_sell", status=status,
            score=1.0, gate_passed=gate, csv_path=csv_path,
            trade_count=trades, mdd=12.0, profit=profit, total_profit_pct=30.0,
        )
    finally:
        st.close()


def _seed_job(tmp_path: Path, csv_path: str | None, job_id: str, status: str = "success") -> str:
    import json
    jobs_dir = tmp_path / "webbt_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "job_id": job_id,
        "spec": {"buy": "기존매수", "sell": "기존매도", "start": 20230101, "end": 20230131,
                 "timeframe": "min", "engines": 4, "timeout": 600,
                 "divid_mode": "종목코드별 분류", "one_code": None, "back_db_override": None},
        "status": status,
        "created_at": 1700000000.0, "started_at": 1700000001.0, "finished_at": 1700000050.0,
        "returncode": 0, "csv_path": csv_path,
        "metrics": {"trade_count": 60, "win_rate": 50.0, "total_profit_pct": 30.0,
                    "total_profit_krw": 150000, "mdd_pct": 12.0, "cagr": 88.0},
        "message": "ok", "progress": 1.0, "phase": "done", "pid": 111,
    }
    with open(jobs_dir / f"{job_id}.json", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False)
    return job_id


# ----------------------------------------------------------------- evo_gens
def test_evo_gens_lists_generations(client: TestClient, tmp_path: Path):
    csv_path = _make_trades_csv(tmp_path / "g0.csv", n=60)
    _seed_gen(tmp_path, "runE", 0, csv_path=csv_path, gate=True, trades=60)
    _seed_gen(tmp_path, "runE", 1, csv_path=None, gate=False, status="rejected", trades=0)

    r = client.get("/bt/evo_gens", params={"run_id": "runE"})
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "runE"
    assert body["count"] == 2
    by_gen = {it["gen_no"]: it for it in body["items"]}
    assert by_gen[0]["has_csv"] is True
    assert by_gen[0]["gate_passed"] is True
    assert by_gen[0]["trade_count"] == 60
    assert by_gen[1]["has_csv"] is False        # csv_path=None → 축약만 가능.
    assert by_gen[1]["gate_passed"] is False


def test_evo_gens_empty_run_no_raise(client: TestClient):
    r = client.get("/bt/evo_gens", params={"run_id": ""})
    assert r.status_code == 200
    assert r.json() == {"items": [], "count": 0, "run_id": ""}


def test_evo_gens_unknown_run_empty(client: TestClient):
    r = client.get("/bt/evo_gens", params={"run_id": "does_not_exist"})
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [] and body["count"] == 0


# --------------------------------------------------------- result by run/gen
def test_result_by_run_gen_with_csv(client: TestClient, tmp_path: Path):
    csv_path = _make_trades_csv(tmp_path / "g0.csv", n=60)
    _seed_gen(tmp_path, "runR", 0, csv_path=csv_path)
    r = client.get("/bt/result", params={"run_id": "runR", "gen_no": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["has_csv"] is True
    # 잡 결과와 동일 스키마: metrics + analysis 묶음(차트 데이터 포함).
    assert body["metrics"]["trade_count"] == 60
    assert "summary" in body["analysis"]
    assert "equity" in body["analysis"]
    assert body["analysis"]["equity"]["cumulative"]  # 곡선 비어있지 않음.


def test_job_result_reads_relative_artifact_from_repo_root_not_cwd(
    client: TestClient, monkeypatch, tmp_path: Path
):
    repo_root = tmp_path / "repo"
    rel_csv = "backtest/csv/relative_result.csv"
    _make_trades_csv(repo_root / rel_csv, n=12)
    _seed_job(tmp_path, rel_csv, "20260101_000000_REL_00001")
    other_cwd = tmp_path / "not_repo_cwd"
    other_cwd.mkdir()
    monkeypatch.setattr(backtest_api, "REPO_ROOT", repo_root)
    monkeypatch.chdir(other_cwd)

    r = client.get("/bt/result", params={"job_id": "20260101_000000_REL_00001"})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["analysis"]["summary"]["trade_count"] == 12
    report_payload = backtest_api._report_payload_for_job("20260101_000000_REL_00001", None, None)
    assert report_payload["analysis"]["summary"]["trade_count"] == 12


def test_result_by_run_gen_csv_missing_abbreviated(client: TestClient, tmp_path: Path):
    _seed_gen(tmp_path, "runM", 1, csv_path=None, status="rejected", gate=False,
              trades=0, profit=-5000.0)
    r = client.get("/bt/result", params={"run_id": "runM", "gen_no": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True
    assert body["has_csv"] is False
    # CSV 부재 → generations 행 메트릭 요약 + 빈 분석(차트 없음, 무예외).
    assert body["metrics"]["total_profit_krw"] == -5000.0
    assert body["metrics"]["max_drawdown_pct"] == 12.0
    assert body["artifact_state"] == "metrics_only_csv_missing"
    assert body["analysis"]["summary"]["trade_count"] == 0
    assert "message" in body


def test_result_unknown_run_gen_unavailable(client: TestClient):
    r = client.get("/bt/result", params={"run_id": "nope", "gen_no": 9})
    assert r.status_code == 200
    assert r.json()["available"] is False


# ----------------------------------------------------------------- portfolio
def test_portfolio_two_jobs_combines(client: TestClient, tmp_path: Path):
    csv_a = _make_trades_csv(tmp_path / "a.csv", n=60, sign=1)
    csv_b = _make_trades_csv(tmp_path / "b.csv", n=60, sign=-1)
    _seed_job(tmp_path, csv_a, "20260101_000000_JOBA_00001")
    _seed_job(tmp_path, csv_b, "20260101_000000_JOBB_00002")

    r = client.post("/bt/portfolio", json={"items": [
        {"job_id": "20260101_000000_JOBA_00001", "label": "전략A"},
        {"job_id": "20260101_000000_JOBB_00002", "label": "전략B"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    pf = body["portfolio"]
    assert pf["count"] == 2
    assert len(pf["strategies"]) == 2
    assert {s["label"] for s in pf["strategies"]} == {"전략A", "전략B"}
    # 결합 곡선/MDD 존재.
    assert pf["combined"]["equity"]
    assert pf["combined"]["trading_days"] > 0
    # 상관행렬 2x2, 대각 1.0.
    mat = pf["correlation"]["matrix"]
    assert len(mat) == 2 and len(mat[0]) == 2
    assert mat[0][0] == 1.0 and mat[1][1] == 1.0


def test_portfolio_run_gen_items(client: TestClient, tmp_path: Path):
    csv0 = _make_trades_csv(tmp_path / "g0.csv", n=40, sign=1)
    csv1 = _make_trades_csv(tmp_path / "g1.csv", n=40, sign=1)
    _seed_gen(tmp_path, "runP", 0, csv_path=csv0)
    # 같은 run 의 두 세대를 self-포트폴리오로 결합(완전 동일 → 상관 ~1).
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.record_generation("runP", 1, buy_name="b", sell_name="s", status="ok",
                             score=1.0, gate_passed=True, csv_path=csv1, trade_count=40)
    finally:
        st.close()

    r = client.post("/bt/portfolio", json={"items": [
        {"run_id": "runP", "gen_no": 0},
        {"run_id": "runP", "gen_no": 1},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["portfolio"]["count"] == 2


def test_portfolio_rejects_too_few(client: TestClient, tmp_path: Path):
    # 스키마 레벨(_MutationPayload) 이 2~6 개수 경계를 강제 — 위반 시 핸들러 진입 전
    # 422 로 즉시 거부한다(구버전 200+status:error 바디는 폐지된 계약).
    csv_a = _make_trades_csv(tmp_path / "a.csv", n=10)
    _seed_job(tmp_path, csv_a, "20260101_000000_JOBA_00001")
    r = client.post("/bt/portfolio", json={"items": [
        {"job_id": "20260101_000000_JOBA_00001"},
    ]})
    assert r.status_code == 422


def test_portfolio_rejects_too_many(client: TestClient):
    # 스키마 레벨 max_length=6 강제 — 초과 시 422.
    items = [{"job_id": f"x{i}"} for i in range(7)]
    r = client.post("/bt/portfolio", json={"items": items})
    assert r.status_code == 422


def test_portfolio_unresolved_items_reported(client: TestClient, tmp_path: Path):
    csv_a = _make_trades_csv(tmp_path / "a.csv", n=20, sign=1)
    csv_b = _make_trades_csv(tmp_path / "b.csv", n=20, sign=-1)
    _seed_job(tmp_path, csv_a, "20260101_000000_JOBA_00001")
    _seed_job(tmp_path, csv_b, "20260101_000000_JOBB_00002")
    # 3개 요청 중 1개는 존재하지 않는 잡 → 부분 합성하지 않고 실패 인덱스/사유를 반환.
    r = client.post("/bt/portfolio", json={"items": [
        {"job_id": "20260101_000000_JOBA_00001"},
        {"job_id": "MISSING_JOB"},
        {"job_id": "20260101_000000_JOBB_00002"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["failed"] == [1]
    assert body["failed_reasons"] == [{"index": 1, "reason": "job_not_found"}]
    assert body["resolved_count"] == 2


def test_portfolio_missing_csv_artifact_fails_with_reason(client: TestClient, tmp_path: Path):
    csv_a = _make_trades_csv(tmp_path / "a.csv", n=20, sign=1)
    _seed_job(tmp_path, csv_a, "20260101_000000_JOBA_00001")
    _seed_job(tmp_path, str(tmp_path / "missing.csv"), "20260101_000000_JOBM_00002")

    r = client.post("/bt/portfolio", json={"items": [
        {"job_id": "20260101_000000_JOBA_00001"},
        {"job_id": "20260101_000000_JOBM_00002"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["failed"] == [1]
    assert body["failed_reasons"] == [{"index": 1, "reason": "job_csv_missing"}]
    assert body["resolved_count"] == 1


def test_portfolio_missing_generation_csv_fails_with_reason(client: TestClient, tmp_path: Path):
    csv_a = _make_trades_csv(tmp_path / "g0.csv", n=20, sign=1)
    _seed_gen(tmp_path, "runMissingCsv", 0, csv_path=csv_a)
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    try:
        st.record_generation("runMissingCsv", 1, buy_name="b", sell_name="s", status="ok",
                             score=1.0, gate_passed=True,
                             csv_path=str(tmp_path / "missing_gen.csv"), trade_count=20)
    finally:
        st.close()

    r = client.post("/bt/portfolio", json={"items": [
        {"run_id": "runMissingCsv", "gen_no": 0},
        {"run_id": "runMissingCsv", "gen_no": 1},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["failed"] == [1]
    assert body["failed_reasons"] == [{"index": 1, "reason": "generation_csv_missing"}]


def test_portfolio_no_trades_job_is_explicit_empty_input(client: TestClient, tmp_path: Path):
    csv_a = _make_trades_csv(tmp_path / "a.csv", n=20, sign=1)
    _seed_job(tmp_path, csv_a, "20260101_000000_JOBA_00001")
    _seed_job(tmp_path, None, "20260101_000000_JOBN_00002", status="no_trades")

    r = client.post("/bt/portfolio", json={"items": [
        {"job_id": "20260101_000000_JOBA_00001"},
        {"job_id": "20260101_000000_JOBN_00002"},
    ]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["failed"] == []
    assert body["portfolio"]["count"] == 2


def test_portfolio_items_not_list_no_raise(client: TestClient):
    # 스키마 레벨 타입 검증 — items 가 list 가 아니면 핸들러 진입 전 422.
    r = client.post("/bt/portfolio", json={"items": "nope"})
    assert r.status_code == 422
