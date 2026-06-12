"""Phase4 트랙 B 백테스트 탭 재설계 — 신규 백엔드 계약 테스트.

대상:
  - 잡 메타(태그/메모/즐겨찾기) update_meta + POST /bt/job/meta.
  - optimize 모드 command_builder 분기 + submit 검증(param_space 필수).
  - 데모 합성 결과 /bt/result?demo=1 · sentinel job_id="__demo__".
  - 변수 SSOT /bt/variables · /bt/extract_vars(한글 변수 추출 + 화이트리스트 대조).

모든 엔드포인트는 무예외 계약(데이터 없음/검증 실패도 HTTP 200 + 표준 페이로드)을 따른다.
"""

from __future__ import annotations

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
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.dashboard.backtest_jobs import (  # noqa: E402
    BacktestJobManager,
    BacktestJobSpec,
    default_command_builder,
)


def _make_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
    cur.execute(
        'CREATE TABLE formula ("수식명" TEXT, "차트표시" TEXT, "전략연산" TEXT, "팩터명" TEXT, '
        '"표시형태" TEXT, "색상" TEXT, "크기" TEXT, "라인타입" TEXT, "수식코드" TEXT)'
    )
    con.commit()
    con.close()


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    db_path = tmp_path / "strategy.db"
    _make_strategy_db(db_path)
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    from ai_strategy_loop.dashboard.app import create_app
    return TestClient(create_app())


def _spec(**kw):
    base = dict(buy="테스트매수", sell="테스트매도", start=20250407, end=20250409, timeframe="min")
    base.update(kw)
    return BacktestJobSpec(**base)


# --------------------------------------------------------------- job meta
def _success_command(csv_path: str):
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':3.0}}))"
    )

    def builder(spec):
        return [sys.executable, "-c", code]
    return builder


def _wait(manager, job_id, targets, timeout=15.0):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get("status") in targets:
            return rec
        time.sleep(0.1)
    return manager.get(job_id)


def test_update_meta_partial_and_persist(tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs", command_builder=_success_command("backtest/csv/m.csv")
    )
    job_id = manager.submit(_spec())["job_id"]
    _wait(manager, job_id, {"success", "error", "timeout"})

    # 태그·메모·즐겨찾기 설정.
    r = manager.update_meta(job_id, tags=["좋음", " 후보 ", "좋음"], memo="검토 완료", favorite=True)
    assert r["available"] is True
    assert r["tags"] == ["좋음", "후보"]  # 공백 제거·중복 제거·정렬.
    assert r["memo"] == "검토 완료"
    assert r["favorite"] is True

    # 부분 업데이트(메모만) — 태그/즐겨찾기 미변경.
    r2 = manager.update_meta(job_id, memo="재검토")
    assert r2["tags"] == ["좋음", "후보"]
    assert r2["memo"] == "재검토"
    assert r2["favorite"] is True

    # 영속 후 재시작 복원.
    manager2 = BacktestJobManager(
        jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv")
    )
    rec = manager2.get(job_id)
    assert rec["tags"] == ["좋음", "후보"]
    assert rec["favorite"] is True


def test_update_meta_missing_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.update_meta("nope", favorite=True)["available"] is False


def test_job_meta_route(client: TestClient):
    # 잡이 없어도 무예외 error.
    r = client.post("/bt/job/meta", json={"job_id": "없는잡", "favorite": True})
    assert r.status_code == 200
    assert r.json()["status"] == "error"

    # tags 타입 검증.
    rb = client.post("/bt/job/meta", json={"job_id": "x", "tags": "문자열"})
    assert rb.json()["status"] == "error"

    # job_id 누락.
    rc = client.post("/bt/job/meta", json={"favorite": True})
    assert rc.json()["status"] == "error"


# --------------------------------------------------------------- optimize mode
def test_command_builder_backtest_default():
    cmd = default_command_builder(_spec())
    assert "optimize" not in cmd
    assert "--buy" in cmd and "--quiet" in cmd


def test_command_builder_optimize():
    cmd = default_command_builder(_spec(mode="optimize", param_space="_database/ps.json", opt_method="random"))
    assert cmd[2] == "optimize"
    assert "--param-space" in cmd
    assert cmd[cmd.index("--param-space") + 1] == "_database/ps.json"
    assert cmd[cmd.index("--method") + 1] == "random"
    assert "--quiet" not in cmd  # optimize 는 quiet 미사용(JSON 결과 필요).


def test_submit_optimize_requires_param_space(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    bad = manager.submit(_spec(mode="optimize"))
    assert bad["status"] == "error"
    assert "param_space" in bad["message"]


def test_submit_rejects_bad_mode(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(mode="sweep"))["status"] == "error"


def test_run_route_optimize_without_param_space(client: TestClient):
    r = client.post("/bt/run", json={
        "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409, "mode": "optimize",
    })
    assert r.json()["status"] == "error"
    assert "param_space" in r.json()["message"]


def test_run_route_optimize_param_space_allowlist(client: TestClient):
    # allowlist 밖 절대경로는 거부(back_db_override 와 동일 위생).
    r = client.post("/bt/run", json={
        "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
        "mode": "optimize", "param_space": "C:/Windows/evil.json",
    })
    assert r.json()["status"] == "error"
    assert "허용" in r.json()["message"]


# --------------------------------------------------------------- demo result
def test_demo_result_route(client: TestClient):
    r = client.get("/bt/result", params={"demo": 1})
    body = r.json()
    assert body["available"] is True
    assert body["is_demo"] is True
    assert body["status"] == "success"
    # 합성 거래로 분석 묶음 전 키가 채워진다.
    assert body["analysis"]["summary"]["trade_count"] > 0
    for key in ("equity", "distribution", "heatmap", "underwater", "insights", "rolling", "monthly"):
        assert key in body["analysis"]


def test_demo_result_sentinel_job_id(client: TestClient):
    # 프론트가 BtResultArea 에 싣는 sentinel job_id 도 데모로 라우팅된다(charts 무수정).
    r = client.get("/bt/result", params={"job_id": "__demo__"})
    body = r.json()
    assert body["available"] is True and body["is_demo"] is True


# --------------------------------------------------------------- variables SSOT
def test_variables_route_has_vocabulary(client: TestClient):
    r = client.get("/bt/variables")
    body = r.json()
    assert body["count"] > 100  # SSOT 화이트리스트 181 + 스칼라.
    assert "이동평균" in body["variables"]
    assert "현재가" in body["variables"]


def test_extract_vars_known_unknown(client: TestClient):
    r = client.post("/bt/extract_vars", json={"code": "if 현재가 > 이동평균(20):\n    매수 = True\n없는변수칩 = 1"})
    body = r.json()
    known_names = [k["name"] for k in body["known"]]
    unknown_names = [k["name"] for k in body["unknown"]]
    assert "현재가" in known_names
    assert "이동평균" in known_names
    assert "없는변수칩" in unknown_names


def test_extract_vars_empty(client: TestClient):
    r = client.post("/bt/extract_vars", json={"code": "x = 1 + 2"})
    body = r.json()
    assert body["known"] == []
    assert body["unknown"] == []


def test_extract_vars_counts_repeats(client: TestClient):
    r = client.post("/bt/extract_vars", json={"code": "현재가 + 현재가 + 현재가"})
    body = r.json()
    hit = next(k for k in body["known"] if k["name"] == "현재가")
    assert hit["count"] == 3
