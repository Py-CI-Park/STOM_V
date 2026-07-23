"""Phase5 트랙 B 백테탭 강화 2차 — WFO·스윕 모드 + 다중 잡 오버레이 계약 테스트.

대상:
  - wfo/sweep 모드 command_builder 분기(cli/subcommands.py 인자 계약 대조).
  - submit() wfo/sweep 모드 검증(윈도우·params 필수).
  - POST /bt/run wfo/sweep 페이로드 스레딩 + allowlist 위생(sweep_params).
  - wfo/sweep 잡 finalize → mode_result 구조화 결과 + /bt/result 모드 분기.
  - GET /bt/overlay 다중 잡(2~4) 수익곡선 오버레이 응답.

모든 엔드포인트는 무예외 계약(데이터 없음/검증 실패도 HTTP 200 + 표준 페이로드)을 따른다.
실제 장기 백테는 실행하지 않는다 — 단명 가짜 커맨드로 라이프사이클만 검증하고,
커맨드 라인 정확성은 cli 인자 계약과 대조한다.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import subprocess
import time
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
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
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
    return authorized_dashboard_client(create_app())


def _spec(**kw):
    base = dict(buy="테스트매수", sell="테스트매도", start=20250407, end=20250409, timeframe="min")
    base.update(kw)
    return BacktestJobSpec(**base)


def _wait(manager, job_id, targets, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get("status") in targets:
            return rec
        time.sleep(0.1)
    return manager.get(job_id)


# ----------------------------------------------------- wfo command builder
def test_command_builder_wfo():
    cmd = default_command_builder(_spec(mode="wfo", train_window_days=60, test_window_days=20))
    assert cmd[2] == "wfo"
    # cli/subcommands.py wfo 계약: --start --end --train-window-days --test-window-days 필수.
    assert "--train-window-days" in cmd
    assert cmd[cmd.index("--train-window-days") + 1] == "60"
    assert cmd[cmd.index("--test-window-days") + 1] == "20"
    assert "--buy" in cmd and "--sell" in cmd
    assert cmd[cmd.index("--format") + 1] == "json"
    # wfo 는 --divid-mode 를 받지 않는다(cli 계약).
    assert "--divid-mode" not in cmd
    # 미지정 step_days/param_space 는 인자에 없어야 한다.
    assert "--step-days" not in cmd
    assert "--param-space" not in cmd


def test_command_builder_wfo_optional_args():
    cmd = default_command_builder(_spec(
        mode="wfo", train_window_days=60, test_window_days=20,
        step_days=10, param_space="_database/ps.json", opt_method="random", opt_objective="sharpe",
    ))
    assert cmd[cmd.index("--step-days") + 1] == "10"
    assert cmd[cmd.index("--param-space") + 1] == "_database/ps.json"
    assert cmd[cmd.index("--method") + 1] == "random"
    assert cmd[cmd.index("--objective") + 1] == "sharpe"


# --------------------------------------------------- sweep command builder
def test_command_builder_sweep_param():
    cmd = default_command_builder(_spec(mode="sweep", sweep_action="param", sweep_params="_database/sw.json"))
    assert cmd[2] == "sweep"
    assert cmd[3] == "param"
    # cli/subcommands.py sweep param 계약: --params(JSON) + --buy --sell --start --end.
    assert cmd[cmd.index("--params") + 1] == "_database/sw.json"
    assert "--buy" in cmd and "--sell" in cmd
    assert cmd[cmd.index("--format") + 1] == "json"
    assert "--divid-mode" not in cmd


def test_command_builder_sweep_rolling():
    cmd = default_command_builder(_spec(mode="sweep", sweep_action="rolling", window_days=20, step_days=5))
    assert cmd[2] == "sweep"
    assert cmd[3] == "rolling"
    # cli/subcommands.py sweep rolling 계약: --window-days --step-days + --buy --sell.
    assert cmd[cmd.index("--window-days") + 1] == "20"
    assert cmd[cmd.index("--step-days") + 1] == "5"
    assert "--buy" in cmd and "--sell" in cmd
    assert "--params" not in cmd


# --------------------------------------------------------- submit validation
def test_submit_wfo_requires_windows(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")
    bad = manager.submit(_spec(mode="wfo"))
    assert bad["status"] == "error"
    assert "train_window_days" in bad["message"]


def test_submit_wfo_accepts_valid(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")
    ok = manager.submit(_spec(mode="wfo", train_window_days=60, test_window_days=20))
    assert ok["status"] == "ok"
    manager.cancel(ok["job_id"])


def test_submit_sweep_param_requires_params(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")
    bad = manager.submit(_spec(mode="sweep", sweep_action="param"))
    assert bad["status"] == "error"
    assert "sweep_params" in bad["message"]


def test_submit_sweep_rolling_requires_windows(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")
    bad = manager.submit(_spec(mode="sweep", sweep_action="rolling"))
    assert bad["status"] == "error"
    assert "window_days" in bad["message"]


def test_submit_sweep_rejects_bad_action(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")
    bad = manager.submit(_spec(mode="sweep", sweep_action="bogus"))
    assert bad["status"] == "error"
    assert "sweep_action" in bad["message"]


# ------------------------------------------------- finalize → mode_result
def _wfo_ok_command(spec):
    """status=ok + windows/rounds/summary 구조를 즉시 뱉는 가짜 wfo 커맨드."""
    code = (
        "import json;"
        "print(json.dumps({'status':'ok','objective':'tpi','method':'grid',"
        "'windows':[{'round':1,'train_start':20250401,'train_end':20250405,"
        "'test_start':20250406,'test_end':20250409}],"
        "'rounds':[{'window':{'round':1,'train_start':20250401,'train_end':20250405,"
        "'test_start':20250406,'test_end':20250409},'best_params':{},"
        "'test_result':{'status':'success','metrics':{'trade_count':5,'total_profit_pct':2.1,"
        "'max_drawdown_pct':1.0}}}],"
        "'summary':{'round_count':1,'success_count':1,'success_rate':1.0,'metric':'tpi',"
        "'mean_oos_metric':2.1,'zero_trade_rounds':0}}))"
    )
    return [sys.executable, "-c", code]


def test_wfo_finalize_stores_mode_result(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_wfo_ok_command)
    job_id = manager.submit(_spec(mode="wfo", train_window_days=60, test_window_days=20))["job_id"]
    rec = _wait(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "success"
    mr = rec.get("mode_result")
    assert mr is not None
    assert mr["summary"]["round_count"] == 1
    assert len(mr["rounds"]) == 1
    assert mr["rounds"][0]["test_result"]["metrics"]["total_profit_pct"] == 2.1


# --------------------------------------------------------- /bt/run routing
def test_run_route_wfo_without_windows(client: TestClient):
    r = client.post("/bt/run", json={
        "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409, "mode": "wfo",
    })
    assert r.json()["status"] == "error"
    assert "train_window_days" in r.json()["message"]


def test_run_route_sweep_params_allowlist(client: TestClient):
    # allowlist 밖 절대경로 sweep_params 는 거부(param_space 와 동일 위생).
    r = client.post("/bt/run", json={
        "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
        "mode": "sweep", "sweep_action": "param", "sweep_params": "C:/Windows/evil.json",
    })
    assert r.json()["status"] == "error"
    assert "허용" in r.json()["message"]


def test_run_route_wfo_accepts_windows(client: TestClient):
    r = client.post("/bt/run", json={
        "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
        "mode": "wfo", "train_window_days": 60, "test_window_days": 20,
    })
    body = r.json()
    # 실제 백테 커맨드가 돌지만 잡은 즉시 큐잉되고 job_id 가 발급된다(라우팅 검증).
    assert body["status"] == "ok"
    assert "job_id" in body
    client.post("/bt/job/cancel", json={"job_id": body["job_id"]})


# --------------------------------------------------------- /bt/overlay
def test_overlay_requires_min_jobs(client: TestClient):
    r = client.get("/bt/overlay", params={"job_ids": "only_one"})
    body = r.json()
    assert body["status"] == "error"
    assert body["series"] == []


def test_overlay_rejects_too_many(client: TestClient):
    r = client.get("/bt/overlay", params={"job_ids": "a,b,c,d,e"})
    assert r.json()["status"] == "error"


def test_overlay_missing_jobs_fail_gracefully(client: TestClient):
    # 존재하지 않는 잡 2개 → 유효 잡 부족 error(무예외).
    r = client.get("/bt/overlay", params={"job_ids": "nope1,nope2"})
    body = r.json()
    assert body["status"] == "error"
    assert "nope1" in body["failed"] or "nope2" in body["failed"]


def test_overlay_dedup_ids(client: TestClient):
    # 중복 id 는 1개로 압축 → 2개 미만이라 error.
    r = client.get("/bt/overlay", params={"job_ids": "same,same"})
    assert r.json()["status"] == "error"


def _write_trades_csv(path: Path, rows) -> None:
    import csv
    cols = ["종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금"]
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        for name, buy, sell, hold, pct, krw in rows:
            writer.writerow({"종목명": name, "매수시간": buy, "매도시간": sell,
                             "보유시간": hold, "수익률": pct, "수익금": krw})


def _csv_success_command(csv_path: str):
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':5.0}}))"
    )

    def builder(spec):
        return [sys.executable, "-c", code]
    return builder


def test_overlay_two_valid_jobs(monkeypatch, tmp_path: Path):
    """완료 잡 2개를 거래일축 누적수익곡선으로 겹쳐 반환한다(정규화는 프론트)."""
    from ai_strategy_loop.dashboard import backtest_api as api

    csv_a = tmp_path / "a.csv"
    csv_b = tmp_path / "b.csv"
    _write_trades_csv(csv_a, [
        ("알파", "202504070930", "202504071000", 30, 2.0, 20000),
        ("알파", "202504080935", "202504081005", 30, 3.0, 30000),
    ])
    _write_trades_csv(csv_b, [
        ("베타", "202504070930", "202504071000", 30, -1.0, -10000),
        ("베타", "202504080935", "202504081005", 30, 4.0, 40000),
    ])

    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_csv_success_command(str(csv_a)))
    # 매니저 싱글톤을 테스트 매니저로 치환(API 가 get_job_manager 로 공유).
    monkeypatch.setattr(api, "get_job_manager", lambda: manager)

    id_a = manager.submit(_spec(buy="잡A"))["job_id"]
    _wait(manager, id_a, {"success", "error", "timeout"})
    manager._command_builder = _csv_success_command(str(csv_b))
    id_b = manager.submit(_spec(buy="잡B"))["job_id"]
    _wait(manager, id_b, {"success", "error", "timeout"})

    result = api.overlay_jobs(job_ids=f"{id_a},{id_b}")
    assert result["status"] == "ok"
    assert result["count"] == 2
    labels = [s["label"] for s in result["series"]]
    assert any(id_a[:8] in lbl for lbl in labels)
    # 각 시리즈는 거래일축 누적수익곡선을 갖는다.
    for s in result["series"]:
        assert "cumulative" in s
        assert isinstance(s["cumulative"], list)
        assert "summary" in s and "total_profit_pct" in s["summary"]
def test_v59_result_flow_source_contract():
    frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
    result_source = (frontend / "bt-result-area.jsx").read_text(encoding="utf-8")
    parity_source = (frontend / "bt-gui-parity.jsx").read_text(encoding="utf-8")

    for section in (
        "bt-result-summary",
        "bt-result-primary",
        "bt-result-diagnostics",
        "bt-result-evidence",
        "bt-result-grid-12",
        "bt-equal-card-grid",
        "bt-cadence-diagnostic",
    ):
        assert section in result_source
    assert "BtGuiParitySection guiParity={analysis.gui_parity} columns={2}" in result_source
    assert '<details className="evo-group bt-flow-full"' not in result_source
    assert '<details className="bt-extra-charts"' not in result_source

    for group in ("risk", "timing", "holding-trade"):
        assert f'key: "{group}"' in parity_source
    assert "partial GUI parity" in parity_source
    assert "BtMddRandomChart key=\"mdd-random\"" in parity_source
    assert "bt-equal-card-grid" in parity_source


def test_v59_chart_height_source_contract():
    frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
    equity_source = (frontend / "bt-equity-charts.jsx").read_text(encoding="utf-8")
    parity_source = (frontend / "bt-gui-parity.jsx").read_text(encoding="utf-8")
    detail_source = (frontend / "chart-backtest-detail.jsx").read_text(encoding="utf-8")

    assert equity_source.count("H = 320") == 5
    assert parity_source.count("H = 320") == 6
    assert detail_source.count("const W = 880, H = 320;") == 2
    assert "const HpH = 96;" in detail_source
    for hook in ("bt-detail-summary-rail", "bt-detail-holdings-strip", "bt-detail-primary-chart"):
        assert hook in detail_source


def test_v59_result_library_bounds_large_dom_lists():
    frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
    source = (frontend / "bt-tab-run.jsx").read_text(encoding="utf-8")

    assert "filtered.slice(0, visibleLimit).map" in source
    assert "setVisibleLimit(limit => Math.min(limit + 60, filtered.length))" in source


def test_v59_result_request_guard_rejects_superseded_sources_and_preserves_mdd_alias():
    guard_uri = (
        Path(PROJECT_ROOT)
        / "ai_strategy_loop"
        / "dashboard"
        / "frontend"
        / "bt-request-guard.mjs"
    ).resolve().as_uri()
    script = f"""
      const mod = await import('{guard_uri}');
      const oldController = new AbortController();
      const currentController = new AbortController();
      const state = {{ seq: 2 }};
      oldController.abort();
      const checks = {{
        oldAborted: mod.btRequestIsCurrent(state, 1, 'run-b/2', 'run-a/1', oldController.signal),
        oldSequence: mod.btRequestIsCurrent(state, 1, 'run-b/2', 'run-a/1', currentController.signal),
        oldSource: mod.btRequestIsCurrent(state, 2, 'run-b/2', 'run-a/1', currentController.signal),
        current: mod.btRequestIsCurrent(state, 2, 'run-b/2', 'run-b/2', currentController.signal),
        mdd: mod.btMetricValue({{ max_drawdown_pct: 17.8 }}, {{}}, 'mdd_pct'),
        explicitNull: mod.btMetricValue({{ max_drawdown_pct: null }}, {{ max_drawdown_pct: 0 }}, 'mdd_pct'),
        missingCagr: mod.btMetricValue({{}}, {{}}, 'cagr') ?? null,
      }};
      console.log(JSON.stringify(checks));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == (
        '{"oldAborted":false,"oldSequence":false,"oldSource":false,'
        '"current":true,"mdd":17.8,"explicitNull":null,"missingCagr":null}'
    )


def test_v511_result_layout_preferences_preserve_semantic_full_spans_and_discover_diagnostics():
    frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
    result_source = (frontend / "bt-result-area.jsx").read_text(encoding="utf-8")
    research_source = (frontend / "v4-research.jsx").read_text(encoding="utf-8")
    settings_source = (frontend / "v4-settings.jsx").read_text(encoding="utf-8")
    css = (frontend / "v4.css").read_text(encoding="utf-8")

    assert 'const _BT_RESULT_LAYOUT_KEY = "stom_v511_result_layout";' in result_source
    assert 'const _BT_RESULT_LAYOUTS = ["auto", "wide", "balanced", "dense"];' in result_source
    assert 'style={{ "--bt-result-columns": columns }}' in result_source
    assert '레이아웃: {layout} · 실제 {columns}열' in result_source
    assert 'if (available < 864) return 1;' in result_source
    assert 'if (layout === "wide") return 1;' in result_source
    assert 'Math.floor((available + 12) / 432)' in result_source
    assert 'available >= 3000 ? 4 : 3' in result_source
    assert 'available >= 2520 ? 4 : available >= 1680 ? 3 : 2' in result_source
    for section in ("bt-result-summary", "bt-result-primary", "bt-result-evidence", "bt-result-diagnostics"):
        assert f'className="bt-result-section {section}' in result_source
    assert '{diagnosticsOpen && (' not in result_source
    for diagnostic in ("BtHeatmap", "BtMaeMfeScatter", "BtQuantPanel", "BtExitReasonPanel",
                       "BtOrderflowPanel", "BtStatTestPanel", "BtRollingChart",
                       "BtMonthlyCalendar", "BtCumulativeTradesChart"):
        assert f"<{diagnostic}" in result_source
    assert 'stom_v511_result_diagnostics_open' in result_source
    result_css = css.split(".bt-result-flow {", 1)[1].split(".bt-diagnostic-grid.is-collapsed", 1)[0]
    assert 'repeat(var(--bt-result-columns, 2), minmax(0, 1fr))' in result_css
    assert ".bt-result-flow {\n  display: flex;" in css
    assert "grid-template-columns: repeat(auto" not in result_css

    assert '"stom_v511_result_layout"' in settings_source
    assert '"stom_v511_live_stage_density"' in settings_source
    assert "v511-result-ready" in research_source
    assert "결과 분석 열기" in research_source
    assert 'const isDemo = wsStatus === "demo";' in research_source
    assert "window.isDemoSource" not in research_source
