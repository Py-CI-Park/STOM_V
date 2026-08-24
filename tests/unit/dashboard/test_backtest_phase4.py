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
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


def _make_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute(
        'INSERT INTO stockbuy VALUES (?, ?)',
        ("Vars매수", "self.vars = {0: [[10, 30, 10], 20], 1: [[1.5, 2.5, 0.5], 2.0]}"),
    )
    cur.execute(
        'INSERT INTO stockbuy VALUES (?, ?)',
        ("BackFinderOK", "self.tickcols = ['현재가', '등락율']\nself.tickdata = [현재가, 등락율]"),
    )
    cur.execute(
        'INSERT INTO stockbuy VALUES (?, ?)',
        ("BackFinderBad", "self.tickcols = ['현재가', '등락율']\nself.tickdata = [현재가]"),
    )
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
    monkeypatch.setenv("STOM_DASHBOARD_ALLOW_STRATEGY_WRITE", "1")
    from ai_strategy_loop.dashboard.app import create_app
    return authorized_dashboard_client(create_app())


def _spec(**kw):
    base = dict(
        buy="테스트매수", sell="테스트매도",
        buy_code="매수 = True", sell_code="매도 = False",
        start=20250407, end=20250409, timeframe="min",
    )
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

    # tags 타입 검증 — Pydantic 모델(JobMetaPayload)이 FastAPI 계층에서 422 로 거부.
    rb = client.post("/bt/job/meta", json={"job_id": "x", "tags": "문자열"})
    assert rb.status_code == 422
    assert "tags" in rb.text

    # job_id 누락 — Pydantic 필수 필드 위반으로 422.
    rc = client.post("/bt/job/meta", json={"favorite": True})
    assert rc.status_code == 422


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
    for key in ("equity", "distribution", "heatmap", "underwater", "insights", "rolling", "monthly", "gui_parity"):
        assert key in body["analysis"]
    # B3 — GUI 패리티 6 차트 데이터가 데모에서 모두 채워진다(빈 화면 금지).
    gp = body["analysis"]["gui_parity"]
    assert set(gp.keys()) == {"mdd_random", "daily", "hourly", "weekday", "holding", "trade_rolling"}
    assert gp["mdd_random"]["n"] > 0 and gp["mdd_random"]["actual"]
    assert gp["daily"]["series"] and gp["daily"]["index_available"] is False
    assert gp["weekday"]["days"]
    # 데모 CSV 에 매수금액이 있어 보유금액 곡선이 전부 반영된다.
    assert gp["holding"]["covered"] == gp["holding"]["total"] and gp["holding"]["series"]
    assert gp["trade_rolling"]["windows"] == [20, 60, 120, 240, 480]


def test_demo_result_sentinel_job_id(client: TestClient):
    # 프론트가 BtResultArea 에 싣는 sentinel job_id 도 데모로 라우팅된다(charts 무수정).
    r = client.get("/bt/result", params={"job_id": "__demo__"})
    body = r.json()
    assert body["available"] is True and body["is_demo"] is True


def test_gui_parity_route_empty_job_no_raise(client: TestClient):
    # B3 — 잡 미지정 GUI 패리티 라우트는 빈 구조를 200 으로 돌린다(무예외 계약).
    r = client.get("/bt/analysis/gui_parity", params={"job_id": ""})
    assert r.status_code == 200
    gp = r.json()["gui_parity"]
    assert set(gp.keys()) == {"mdd_random", "daily", "hourly", "weekday", "holding", "trade_rolling"}
    assert gp["mdd_random"]["n"] == 0 and gp["daily"]["series"] == []
    assert gp["holding"]["series"] == [] and gp["trade_rolling"]["series"] == []


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


# -------------------------------------------------------- legacy self.vars / BackFinder
def test_legacy_self_vars_preview_route_is_reversible_and_no_exec(client: TestClient):
    r = client.get("/bt/legacy/self_vars", params={"kind": "buy", "name": "Vars매수"})
    body = r.json()
    assert body["available"] is True
    assert body["adapter"] == "self.vars-range-preview"
    assert body["reversible"] is True
    assert body["exec_used"] is False
    assert body["refs"] == ["self.vars[0]", "self.vars[1]"]
    assert body["rows"][0] == {"index": 0, "name": "self.vars[0]", "min": 10, "max": 30, "step": 10, "default": 20}
    assert body["rows"][1]["min"] == 1.5
    assert body["rows"][1]["max"] == 2.5
    assert body["rows"][1]["step"] == 0.5
    assert body["roundtrip_available"] is True
    assert body["roundtrip_code"] == "self.vars = {0: [[10, 30, 10], 20], 1: [[1.5, 2.5, 0.5], 2.0]}"

def test_legacy_self_vars_preview_rejects_nonliteral_without_exec(client: TestClient, tmp_path: Path, monkeypatch):
    db_path = tmp_path / "strategy_malicious.db"
    _make_strategy_db(db_path)
    con = sqlite3.connect(str(db_path))
    con.execute(
        'INSERT INTO stockbuy VALUES (?, ?)',
        ("Vars악성", "self.vars = {0: __import__('os').system('echo should-not-run')}"),
    )
    con.commit()
    con.close()
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))

    body = client.get("/bt/legacy/self_vars", params={"kind": "buy", "name": "Vars악성"}).json()
    assert body["available"] is False
    assert body["exec_used"] is False
    assert body["reversible"] is False
    assert body["roundtrip_available"] is False
    assert body["roundtrip_code"] == ""
    assert body["rows"] == []


def test_legacy_self_vars_preview_missing_or_invalid_is_no_raise(client: TestClient):
    r = client.get("/bt/legacy/self_vars", params={"kind": "buy", "name": "기존매수"})
    body = r.json()
    assert r.status_code == 200
    assert body["available"] is False
    assert body["rows"] == []
    assert body["exec_used"] is False


def test_backfinder_preflight_ok_and_mismatch_are_staged_only(client: TestClient):
    ok = client.get("/bt/backfinder/preflight", params={"kind": "buy", "name": "BackFinderOK"}).json()
    assert ok["available"] is True
    assert ok["precondition_ok"] is True
    assert ok["has_tickcols"] is True
    assert ok["has_tickdata"] is True
    assert ok["cols_count"] == 2
    assert ok["data_count"] == 2
    assert ok["run_enabled"] is False
    assert "안전 점검만 제공" in ok["message"]

    bad = client.get("/bt/backfinder/preflight", params={"kind": "buy", "name": "BackFinderBad"}).json()
    assert bad["available"] is True
    assert bad["precondition_ok"] is False
    assert bad["cols_count"] == 2
    assert bad["data_count"] == 1
    assert bad["run_enabled"] is False
    assert "일치하지 않습니다" in bad["message"]


def test_backfinder_preflight_missing_strategy_is_no_raise(client: TestClient):
    body = client.get("/bt/backfinder/preflight", params={"kind": "buy", "name": "없음"}).json()
    assert body["available"] is False
    assert body["status"] == "missing"
    assert body["reason"] == "strategy_not_found"
    assert body["precondition_ok"] is False
    assert body["run_enabled"] is False


def test_legacy_preview_routes_report_db_lookup_failures(client: TestClient, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(tmp_path / "missing" / "strategy.db"))

    vars_body = client.get("/bt/legacy/self_vars", params={"kind": "buy", "name": "Vars매수"}).json()
    assert vars_body["available"] is False
    assert vars_body["status"] == "error"
    assert vars_body["reason"] == "strategy_db_unavailable"
    assert "전략 DB 조회 실패" in vars_body["message"]

    bf_body = client.get("/bt/backfinder/preflight", params={"kind": "buy", "name": "BackFinderOK"}).json()
    assert bf_body["available"] is False
    assert bf_body["status"] == "error"
    assert bf_body["reason"] == "strategy_db_unavailable"
    assert "전략 DB 조회 실패" in bf_body["message"]

def test_strategy_library_routes_report_db_lookup_failures(client: TestClient, monkeypatch, tmp_path: Path):
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(tmp_path / "missing" / "strategy.db"))

    list_body = client.get("/bt/strategies", params={"kind": "buy"}).json()
    assert list_body["status"] == "error"
    assert list_body["reason"] == "strategy_db_unavailable"
    assert "전략 DB 조회 실패" in list_body["message"]
    assert list_body["items"] == []

    one_body = client.get("/bt/strategy", params={"kind": "buy", "name": "기존매수"}).json()
    assert one_body["available"] is False
    assert one_body["status"] == "error"
    assert one_body["reason"] == "strategy_db_unavailable"
    assert "전략 DB 조회 실패" in one_body["message"]
