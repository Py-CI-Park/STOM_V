"""Backtest 승자 리포트 + #36 allowlist + #37 회귀 테스트 (Phase2 B1+A2).

검증 범위:
  - render_report: 합성 payload → HTML 에 핵심 섹션 문자열 존재 + 외부 URL 0건 + 무예외.
  - /bt/report?job_id=...: 완료 잡 픽스처로 완전한 HTML 반환.
  - /bt/report?run_id=&gen_no=: loop_runs.db 세대 CSV 경로로 리포트(+CSV 부재 축약).
  - #36: /bt/run back_db_override allowlist(허용/차단).
  - #37: /feature_importance 가 gen_no 전달 시 NameError 없이 응답(TestClient).
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
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard import backtest_jobs as J  # noqa: E402
from ai_strategy_loop.dashboard import backtest_report as R  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


# --------------------------------------------------------------------- fixtures
def _make_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
    cur.execute(
        'CREATE TABLE formula ("수식명" TEXT, "수식코드" TEXT)'
    )
    con.commit()
    con.close()


def _make_trades_csv(path: Path, n: int = 60) -> str:
    """analysis 가 기대하는 per-trade 컬럼명으로 CSV 생성(R_MFE/R_MAE/B_* 포함)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금",
            "R_MFE", "R_MAE", "매도조건",
            "B_체결강도", "B_매수총잔량", "B_매도총잔량", "B_전일동시간비", "B_등락율",
        ])
        w.writeheader()
        for i in range(n):
            day = (i % 25) + 1
            pct = 1.2 if i % 2 == 0 else -0.7
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
                "B_체결강도": 130 + (i % 40) if pct > 0 else 80 + (i % 30),
                "B_매수총잔량": 5000 + i * 10,
                "B_매도총잔량": 4000 + i * 5,
                "B_전일동시간비": 1.5 + (i % 10) * 0.1,
                "B_등락율": 3.0 + (i % 7),
            })
    return str(path)


@pytest.fixture
def client(monkeypatch, tmp_path: Path) -> TestClient:
    """워크벤치 앱 + 임시 strategy.db + 격리 webbt_jobs + 격리 loop_runs.db."""
    db_path = tmp_path / "strategy.db"
    _make_strategy_db(db_path)
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(S, "LOOP_RUNS_DB", tmp_path / "loop_runs.db")
    # 잡 매니저 싱글톤을 테스트 격리 디렉토리로 교체(영속 충돌 방지).
    monkeypatch.setattr(J, "_manager", None)
    monkeypatch.setattr(J, "_JOBS_DIR", tmp_path / "webbt_jobs")
    from ai_strategy_loop.dashboard.app import create_app
    return authorized_dashboard_client(create_app())


def _seed_job(tmp_path: Path, csv_path: str, status: str = "success") -> str:
    """webbt_jobs 디렉토리에 완료 잡 레코드를 직접 영속해 job_id 를 돌려준다."""
    import json
    jobs_dir = tmp_path / "webbt_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_id = "20260101_000000_TESTREPORT_12345"
    rec = {
        "job_id": job_id,
        "spec": {"buy": "기존매수", "sell": "기존매도", "start": 20230101, "end": 20230131,
                 "timeframe": "min", "engines": 4, "timeout": 600,
                 "divid_mode": "종목코드별 분류", "one_code": None, "back_db_override": None},
        "status": status,
        "created_at": 1700000000.0, "started_at": 1700000001.0, "finished_at": 1700000050.0,
        "returncode": 0, "csv_path": csv_path,
        "metrics": {"trade_count": 60, "win_rate": 50.0, "total_profit_pct": 30.0,
                    "total_profit_krw": 150000, "mdd_pct": 12.0, "cagr": 88.0,
                    "payoff_ratio": 1.7, "profit_factor": 1.9},
        "message": "ok", "progress": 1.0, "phase": "done", "pid": 111,
    }
    with open(jobs_dir / f"{job_id}.json", "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False)
    return job_id


# --------------------------------------------------------------- render_report
def _full_payload():
    return {
        "meta": {"title": "리포트<X>", "buy": "B", "sell": "S", "period": "20230101~20230131",
                 "generated_at": "2026-06-12 00:00:00", "source": "job:t", "trade_count": 2},
        "metrics": {"trade_count": 2, "win_rate": 50.0, "total_profit_pct": 5.0,
                    "total_profit_krw": 1000, "mdd_pct": 3.0, "cagr": 10.0,
                    "payoff_ratio": 1.5, "profit_factor": 2.0},
        "analysis": {
            "summary": {"trade_count": 2},
            "equity": {"cumulative": [{"date": 20230101, "cum_profit": 500},
                                      {"date": 20230102, "cum_profit": 1000}],
                       "daily": [{"date": 20230101, "pnl": 500}, {"date": 20230102, "pnl": 500}]},
            "underwater": {"series": [{"date": 20230101, "drawdown": 0},
                                      {"date": 20230102, "drawdown": 0}], "max_drawdown": None},
            "distribution": {"pnl_histogram": [{"bin_start": 0, "bin_end": 5, "count": 2, "unit": "%"}]},
            "heatmap": {"cells": [{"weekday": 0, "slot": 19, "slot_label": "09:30",
                                   "profit_krw": 1000, "trades": 2}]},
            "mae_mfe": [{"mae": -1.0, "mfe": 2.0, "pnl_pct": 1.0, "hold_sec": 60, "code": "X"}],
            "orderflow": {"separation": [{"var": "strength", "label": "체결강도",
                                          "win_p50": 130.0, "loss_p50": 90.0, "diff": 40.0}]},
            "exit_reasons": [{"reason": "목표가", "count": 1, "total_pnl": 1000.0, "win_rate": 100.0}],
            "insights": [{"severity": "warning", "title": "T", "detail": "D<e>"}],
            "stats": [{"kind": "weekday", "bucket": 0, "label": "월", "n": 40, "mean": 1.0,
                       "p_value": 0.01, "significant": True, "underpowered": False}],
        },
        "montecarlo": {"n": 1000, "days": 2, "ruin_prob": 0.02, "ruin_pct": 30.0,
                       "mdd_krw": {"p5": 0, "p50": 100, "p95": 300},
                       "final": {"p5": -100, "p50": 1000, "p95": 2000},
                       "observed": {"mdd_krw": 100, "final_krw": 1000}},
    }


def test_render_report_has_all_sections():
    html = R.render_report(_full_payload())
    assert html.startswith("<!DOCTYPE html>")
    for section in ["수익곡선", "언더워터", "손익 분포", "히트맵", "MAE", "몬테카를로",
                    "오더플로우", "매도조건", "인사이트", "통계 검정"]:
        assert section in html, f"섹션 누락: {section}"
    # 메트릭 카드.
    assert "거래수" in html and "payoff" in html
    # SVG 인라인.
    assert "<svg" in html


def test_render_report_no_external_urls():
    html = R.render_report(_full_payload())
    for marker in ["http://", "https://", "//cdn", "src=\"//", "url(http"]:
        assert marker not in html, f"외부 리소스 누수: {marker}"


def test_render_report_escapes_user_strings():
    html = R.render_report(_full_payload())
    # 제목/디테일의 <> 가 escape 되어야 한다(XSS/깨짐 방지).
    assert "리포트&lt;X&gt;" in html
    assert "D&lt;e&gt;" in html


def test_render_report_empty_payload_no_raise():
    html = R.render_report({})
    assert html.startswith("<!DOCTYPE html>")
    assert "http://" not in html and "https://" not in html


# ----------------------------------------------------------------- /bt/report
def test_report_route_by_job_id(client: TestClient, tmp_path: Path):
    csv_path = _make_trades_csv(tmp_path / "trades.csv", n=60)
    job_id = _seed_job(tmp_path, csv_path, status="success")
    r = client.get("/bt/report", params={"job_id": job_id})
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert body.startswith("<!DOCTYPE html>")
    assert "수익곡선" in body and "몬테카를로" in body
    assert "http://" not in body and "https://" not in body
    # 잡 spec 메타 반영.
    assert "기존매수" in body


def test_report_route_unknown_job_returns_notice(client: TestClient):
    r = client.get("/bt/report", params={"job_id": "does_not_exist"})
    assert r.status_code == 200
    assert "생성할 수 없습니다" in r.text


def test_report_route_by_run_gen_with_csv(client: TestClient, tmp_path: Path):
    csv_path = _make_trades_csv(tmp_path / "g0.csv", n=60)
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    st.start_run(LoopConfig(), run_id="runR")
    st.record_generation("runR", 0, buy_name="AILOOP_runR_g0_buy",
                         sell_name="AILOOP_runR_g0_sell", status="evaluated",
                         score=1.0, gate_passed=True, csv_path=csv_path,
                         trade_count=60, profit=150000, total_profit_pct=30.0, mdd=12.0)
    st.close()
    r = client.get("/bt/report", params={"run_id": "runR", "gen_no": 0})
    assert r.status_code == 200
    body = r.text
    assert body.startswith("<!DOCTYPE html>")
    assert "수익곡선" in body and "몬테카를로" in body
    assert "http://" not in body


def test_report_route_by_run_gen_csv_missing_is_abbreviated(client: TestClient, tmp_path: Path):
    db = tmp_path / "loop_runs.db"
    st = LoopState(db_path=str(db), snapshot_dir=str(tmp_path / "snaps"))
    st.start_run(LoopConfig(), run_id="runM")
    # csv_path 부재 → 축약 리포트(메트릭 요약만).
    st.record_generation("runM", 1, buy_name="b", sell_name="s", status="rejected",
                         score=0.0, gate_passed=False, csv_path=None,
                         trade_count=5, profit=-3000, total_profit_pct=-2.0, mdd=8.0)
    st.close()
    r = client.get("/bt/report", params={"run_id": "runM", "gen_no": 1})
    assert r.status_code == 200
    body = r.text
    assert body.startswith("<!DOCTYPE html>")
    assert "CSV 가 없어" in body
    assert "http://" not in body


# ------------------------------------------------------- #36 back_db allowlist
def test_run_rejects_back_db_override_outside_allowlist(client: TestClient):
    # 임의 절대경로(allowlist 밖) → 무예외 error 페이로드.
    payload = {"buy": "기존매수", "sell": "기존매도", "start": 20230101, "end": 20230101,
               "timeframe": "tick", "back_db_override": "C:/Windows/system32/evil.db"}
    r = client.post("/bt/run", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert "allow" in body["message"].lower() or "허용" in body["message"]


def test_run_accepts_back_db_override_under_state(client: TestClient, tmp_path: Path):
    # ai_strategy_loop/state/ 하위 경로는 허용(잡 제출 성공 — job_id 반환).
    from ai_strategy_loop.dashboard import backtest_api as A
    allowed = Path(A._PACKAGE_DIR) / "state" / "tick_subset.db"
    payload = {"buy": "기존매수", "sell": "기존매도", "start": 20230101, "end": 20230101,
               "timeframe": "tick", "back_db_override": str(allowed)}
    r = client.post("/bt/run", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "job_id" in body
    # 정리: 제출된 잡 취소(서브프로세스 기동 방지 차원).
    client.post("/bt/job/cancel", json={"job_id": body["job_id"]})


def test_validate_back_db_override_helper():
    """allowlist 헬퍼 단위 검증 — 허용 루트 하위만 통과, 밖은 None."""
    from ai_strategy_loop.dashboard import backtest_api as A
    inside = str(Path(A._PACKAGE_DIR) / "state" / "x.db")
    inside_db = str(Path(A._DATABASE_DIR) / "y.db")
    assert A._validate_back_db_override(inside) is not None
    assert A._validate_back_db_override(inside_db) is not None
    assert A._validate_back_db_override("C:/temp/evil.db") is None
    assert A._validate_back_db_override("") is None
    # 상위 탈출(..) 우회 차단.
    assert A._validate_back_db_override(str(Path(A._PACKAGE_DIR) / "state" / ".." / ".." / "evil.db")) is None


# --------------------------------------------------- #37 feature_importance 회귀
def test_feature_importance_with_gen_no_no_nameerror(client: TestClient):
    """#37 회귀: gen_no 전달 시 NameError 없이 무예외 응답(읽기 전용)."""
    r = client.get("/feature_importance", params={"run_id": "nope", "gen_no": 3})
    assert r.status_code == 200
    body = r.json()
    # gen_no 가 응답에 반영되고(없는 run 은 error 표준화), 예외 누수 없음.
    assert isinstance(body, dict)
    assert body.get("gen_no") == 3 or "error" in body


def test_feature_importance_without_gen_no_still_works(client: TestClient):
    r = client.get("/feature_importance", params={"run_id": "nope"})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)
