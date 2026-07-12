"""Deterministic, hermetic, executed Chrome UAT for the V4 dashboard."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import sys
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

TABS: Final = ("research", "backtest", "replay", "history", "lab", "workbench", "audit", "context")
EXPECTED_FAILURE: Final = {"method": "GET", "path": "/run_state", "status": 503, "reason": "fixture archive unavailable"}


@dataclass(slots=True)
class Observation:
    console_errors: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    request_failures: list[str] = field(default_factory=list)
    unexpected_responses: list[str] = field(default_factory=list)
    expected_failures: list[dict[str, str | int]] = field(default_factory=list)
    expected_console_errors: list[str] = field(default_factory=list)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fixture_app(run_id: str, ws_events: list[dict[str, str | int]]):
    raise RuntimeError("synthetic UI fixtures are rejected; serve the current product build")


def _product_fixture_app(frontend: Path, run_id: str, ws_events: list[dict[str, object]], journey_events: list[dict[str, object]]):
    """Serve the current product V4 assets with only hermetic backend seams."""
    from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    # Postponed annotations on nested route functions resolve against module globals.
    # Publish these names only after --execute reaches fixture construction so --help
    # remains independent of FastAPI startup cost.
    globals().update(
        FastAPI=FastAPI,
        Request=Request,
        WebSocket=WebSocket,
        WebSocketDisconnect=WebSocketDisconnect,
        FileResponse=FileResponse,
        JSONResponse=JSONResponse,
        StaticFiles=StaticFiles,
    )

    app = FastAPI()
    binding = {"available": True, "run_id": run_id, "current_gen": 2, "winner_gen": 2, "winner_buy": "fixture_buy_g2", "winner_sell": "fixture_sell_g2", "review_hash": "a" * 64, "evidence_hash": "b" * 64, "buy_code_hash": "c" * 64, "sell_code_hash": "d" * 64}
    state = {"contract_version": 2, "run_id": run_id, "status": "idle", "current_gen": -1, "max_generations": 2, "provider": "fixture", "bt_timeframe": "min", "best": None, "winner": None, "generations": [], "latest": {"phase": "idle", "current_step": "not started", "message": "idle"}, "cumulative": {"tokens": 0, "cost_or_count": 0}, "page_data": {}, "updated_at": "2026-07-11T00:00:00Z"}
    research_state = {"complete": False}
    jobs: dict[str, dict[str, object]] = {}

    @app.get("/ui/v4/")
    def ui() -> FileResponse:
        return FileResponse(frontend / "v4.html")

    @app.get("/health")
    def health() -> dict[str, str | int]:
        return {"status": "ok", "contract_version": 2}

    @app.get("/status")
    def status() -> dict[str, object]:
        return state

    @app.get("/config/spec")
    def config_spec() -> dict[str, list[dict[str, str]]]:
        return {"fields": [{"name": "target_score", "type": "number", "default": ""}]}

    @app.get("/runs")
    def runs() -> dict[str, object]:
        return {"runs": [{"run_id": "ARCHIVE_FAIL", "status": "complete", "current_gen": 2, "updated_at": "2026-07-11T00:00:00Z"}]}

    @app.get("/freeze_verdict")
    def freeze_verdict() -> dict[str, dict[str, str | int | bool]]:
        return {"approval_binding": binding if research_state["complete"] else {"available": False, "reason": "winner pending"}}

    @app.get("/run_state")
    def archive_fail() -> JSONResponse:
        return JSONResponse({"reason": EXPECTED_FAILURE["reason"]}, status_code=503)

    @app.get("/bt/health")
    def bt_health() -> dict[str, object]:
        return {"status": "ok", "api_version": 1}

    @app.get("/bt/strategies")
    def bt_strategies(kind: str) -> dict[str, object]:
        name = "fixture_buy_g2" if kind == "buy" else "fixture_sell_g2"
        return {"items": [{"name": name, "kind": kind, "active": True}]}

    @app.get("/bt/data_range")
    def bt_data_range() -> dict[str, object]:
        return {"available": True, "min_date": "20260101", "max_date": "20261231"}

    @app.post("/bt/run")
    async def bt_run(request: Request) -> dict[str, object]:
        payload = await request.json()
        job_id = "uat-success" if not jobs else "uat-cancel"
        jobs[job_id] = {"available": True, "job_id": job_id, "status": "pending", "progress": 0, "phase": "queued", "message": "queued", "log_tail": [], "spec": payload}
        response = {"status": "ok", "job_id": job_id}
        journey_events.append({"kind": "bt_run", "job_id": job_id, "payload": payload, "response": response})
        return response

    @app.get("/bt/jobs")
    def bt_jobs() -> dict[str, object]:
        return {"jobs": list(jobs.values())}

    @app.get("/bt/job")
    def bt_job(job_id: str) -> dict[str, object]:
        return jobs.get(job_id, {"available": False, "job_id": job_id})

    @app.get("/bt/result")
    def bt_result(job_id: str = "__demo__") -> dict[str, object]:
        journey_events.append({"kind": "bt_result", "job_id": job_id})
        if job_id == "__demo__":
            return {"available": False, "job_id": job_id}
        return {"available": True, "job_id": job_id, "status": "success", "metrics": {"total_profit_pct": 12.5, "mdd_pct": -2.0, "win_rate": 60.0, "trade_count": 3}, "equity": [{"t": "20260101", "value": 10000000}, {"t": "20260102", "value": 11250000}], "daily": [], "trades": []}

    @app.post("/bt/job/cancel")
    async def bt_cancel(request: Request) -> dict[str, object]:
        payload = await request.json(); job_id = str(payload.get("job_id", ""))
        if job_id in jobs:
            jobs[job_id].update({"status": "cancelled", "progress": 0.1, "phase": "cancelled", "message": "cancelled", "artifact_state": "none"})
        response = {"status": "ok", "job_id": job_id}
        journey_events.append({"kind": "bt_cancel", "job_id": job_id, "response": response})
        return response

    @app.websocket("/bt/ws_job")
    async def bt_ws_job(ws: WebSocket, job_id: str) -> None:
        import anyio
        await ws.accept(); journey_events.append({"kind": "bt_ws_open", "job_id": job_id})
        if job_id == "uat-success":
            jobs[job_id].update({"status": "success", "progress": 1.0, "phase": "done", "message": "result ready", "artifact_state": "openable"})
            try:
                journey_events.append({"kind": "bt_ws_terminal", "job_id": job_id, "payload": {**jobs[job_id], "terminal": True}})
                await ws.send_json({**jobs[job_id], "terminal": True})
            except WebSocketDisconnect as exc:
                journey_events.append({"kind": "bt_ws_expected_client_close", "job_id": job_id, "code": exc.code})
        else:
            jobs[job_id].update({"status": "running", "progress": 0.1, "phase": "backtest", "message": "running", "artifact_state": "pending"})
            await ws.send_json({**jobs[job_id], "terminal": False})
            with anyio.move_on_after(5):
                while jobs[job_id]["status"] != "cancelled":
                    await anyio.sleep(0.02)
            try:
                journey_events.append({"kind": "bt_ws_terminal", "job_id": job_id, "payload": {**jobs[job_id], "terminal": True}})
                await ws.send_json({**jobs[job_id], "terminal": True})
            except WebSocketDisconnect as exc:
                journey_events.append({"kind": "bt_ws_expected_client_close", "job_id": job_id, "code": exc.code})
        try:
            await ws.close()
        except RuntimeError as exc:
            if "once a close message has been sent" not in str(exc):
                raise
            journey_events.append({"kind": "bt_ws_expected_client_close", "job_id": job_id, "reason": str(exc)})

    @app.get("/sim/health")
    def sim_health() -> dict[str, object]:
        return {"status": "ok", "api_version": 1}

    @app.get("/sim/days")
    def sim_days(src: str = "min") -> dict[str, object]:
        return {"days": ["20250102"], "src": src}

    @app.get("/sim/stocks")
    def sim_stocks(date: str, src: str = "min") -> dict[str, object]:
        return {"stocks": [{"code": "005930", "name": "fixture", "change": 1.2}], "date": date, "src": src}

    @app.get("/sim/signals")
    def sim_signals() -> dict[str, object]:
        return {"signals": []}

    @app.get("/sim/demo")
    def sim_demo(src: str = "min", mode: str = "latest") -> dict[str, object]:
        journey_events.append({"kind": "sim_demo", "mode": mode})
        return {"available": True, "date": 20250102, "code": "005930", "name": "fixture", "src": src}

    @app.websocket("/sim/ws")
    async def sim_ws(ws: WebSocket) -> None:
        await ws.accept(); journey_events.append({"kind": "sim_ws_open"})
        frames = [(90000, 0), (90100, 60), (93000, 1800), (130000, 14400)]
        try:
            while True:
                payload = await ws.receive_json(); journey_events.append({"kind": "sim_action", "payload": payload})
                action = payload.get("action")
                if action == "start":
                    message = {"type": "meta", "codes": ["005930"], "bars_total": 4, "session_range": [90000, 130000], "total_elapsed_seconds": 14400}
                    journey_events.append({"kind": "sim_frame", "payload": message}); await ws.send_json(message)
                    for index, (stamp, elapsed) in enumerate(frames):
                        bar = {"code": "005930", "o": 100 + index, "h": 102 + index, "l": 99 + index, "c": 101 + index, "vol": 1000 + index}
                        message = {"type": "bars", "index": index, "frame_count": index + 1, "t": stamp, "elapsed_seconds": elapsed, "items": [bar]}
                        journey_events.append({"kind": "sim_frame", "payload": message}); await ws.send_json(message)
                elif action == "seek_index":
                    index = int(payload.get("index", 0)); stamp, elapsed = frames[index]
                    bars = [{"t": t, "o": 100 + i, "h": 102 + i, "l": 99 + i, "c": 101 + i, "vol": 1000 + i} for i, (t, _) in enumerate(frames[:index + 1])]
                    message = {"type": "history", "index": index, "frame_count": index + 1, "t": stamp, "elapsed_seconds": elapsed, "items_by_code": {"005930": bars}}
                    journey_events.append({"kind": "sim_frame", "payload": message}); await ws.send_json(message)
                elif action == "stop":
                    await ws.send_json({"type": "done"})
        except WebSocketDisconnect:
            return

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        await ws.send_json(state)
        try:
            while True:
                payload = await ws.receive_json()
                ws_events.append(payload)
                if payload.get("action") == "start":
                    import anyio
                    journey_events.append({"kind": "research_start", "payload": payload})
                    state.update({"status": "running", "current_gen": 0, "latest": {"phase": "generation", "current_step": "generate", "message": "generation started"}})
                    journey_events.append({"kind": "research_frame", "phase": "running", "payload": dict(state)})
                    await ws.send_json(dict(state)); await anyio.sleep(0.05)
                    state.update({"current_gen": 2, "generations": [{"gen_no": 2, "status": "ok", "gate_passed": True, "score": 42.0}], "latest": {"phase": "grading", "current_step": "winner", "message": "generation complete"}})
                    journey_events.append({"kind": "research_frame", "phase": "generation", "payload": dict(state)})
                    await ws.send_json(dict(state)); await anyio.sleep(0.05)
                    state.update({"status": "complete", "best": {"gen": 2, "graded_score": 42.0}, "winner": {"gen": 2, "score": 42.0, "buy_name": "fixture_buy_g2", "sell_name": "fixture_sell_g2"}, "latest": {"phase": "complete", "current_step": "winner selected", "message": "winner ready"}})
                    journey_events.append({"kind": "research_frame", "phase": "winner", "payload": dict(state)})
                    research_state["complete"] = True; await ws.send_json(dict(state))
                elif payload.get("action") == "final_approval":
                    await ws.close(code=4403, reason="capability_disabled")
                    return
                await ws.send_json({"status": "ok", "action": payload.get("action")})
        except WebSocketDisconnect:
            return

    app.mount("/ui", StaticFiles(directory=frontend, html=True), name="ui")

    @app.get("/{path:path}")
    def safe_reads(path: str) -> JSONResponse:
        if path.startswith("bt/strategies"):
            return JSONResponse([{"name": "fixture_buy_g2"}, {"name": "fixture_sell_g2"}])
        if path.startswith("sim/days"):
            return JSONResponse(["20250102"])
        if path.startswith("sim/stocks"):
            return JSONResponse([{"code": "005930", "name": "fixture"}])
        return JSONResponse({})

    return app


def _capture(page, out: Path, tab: str, run_id: str, started_ns: int, before_events: int) -> dict[str, str | int | bool]:
    path = out / f"{run_id}-{tab}.png"
    page.screenshot(path=str(path))
    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    after_events = int(page.locator("body").get_attribute("data-events"))
    marker = page.locator("body").get_attribute("data-run-id")
    valid = stat.st_size > 100 and stat.st_mtime_ns >= started_ns and marker == run_id and after_events > before_events
    return {"tab": tab, "path": str(path), "sha256": digest, "size": stat.st_size, "captured_at_ns": stat.st_mtime_ns, "run_id": marker, "dom_state_changed": after_events > before_events, "event_counter": after_events, "valid": valid}


def archive_outcome_valid(receipt: dict[str, object]) -> bool:
    return (
        receipt.get("active_tab") == "history"
        and receipt.get("panel_visible") is True
        and receipt.get("alert_visible") is True
        and receipt.get("alert_text") == "아카이브 run 로드 실패 · ARCHIVE_FAIL · HTTP 503"
        and receipt.get("alert_in_viewport") is True
    )


def default_off_denial_valid(payload: dict[str, object], close: dict[str, object]) -> bool:
    return (
        payload.get("action") == "final_approval"
        and bool(payload.get("run_id"))
        and close.get("code") == 4403
        and close.get("reason") == "capability_disabled"
        and str(close.get("url", "")).startswith(("ws://", "wss://"))
    )


def _keyboard_receipt(page, key: str, tab: str) -> dict[str, object]:
    state = page.evaluate("""tab => {
        const control = document.querySelector('#v4-tab-' + tab);
        const panel = document.querySelector('#v4-panel-' + tab);
        return {
            focus_id: document.activeElement?.id || null,
            selected: control?.getAttribute('aria-selected'),
            url_tab: new URL(location.href).searchParams.get('tab'),
            panel_id: panel?.id || null,
            panel_hidden: panel?.hidden ?? null,
        };
    }""", tab)
    expected_focus = f"v4-tab-{tab}"
    expected_panel = f"v4-panel-{tab}"
    state.update(
        key=key,
        tab=tab,
        valid=(
            state.get("focus_id") == expected_focus
            and state.get("selected") == "true"
            and state.get("url_tab") == tab
            and state.get("panel_id") == expected_panel
            and state.get("panel_hidden") is False
        ),
    )
    return state


def _observe(page, obs: Observation) -> None:
    page.on("console", lambda msg: obs.console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda error: obs.page_errors.append(str(error)))
    page.on("requestfailed", lambda request: obs.request_failures.append(f"{request.method} {request.url}: {request.failure}"))

    def response(resp) -> None:
        if resp.status < 400:
            return
        request = resp.request
        if request.method == EXPECTED_FAILURE["method"] and resp.status == EXPECTED_FAILURE["status"] and urlsplit(resp.url).path == EXPECTED_FAILURE["path"]:
            obs.expected_failures.append({"url": resp.url, "method": request.method, "status": resp.status, "reason": str(EXPECTED_FAILURE["reason"])})
        else:
            obs.unexpected_responses.append(f"{request.method} {resp.url} {resp.status}")

    page.on("response", response)


def execute(out: Path) -> tuple[dict[str, object], bool]:
    run_id = f"uat-{uuid.uuid4().hex[:12]}"
    started_ns = time.time_ns()
    runtime = Path(tempfile.mkdtemp(prefix="stom-v4-uat-"))
    db = runtime / "strategy.sqlite3"
    ledger = runtime / "decisions.jsonl"
    profile = runtime / "chrome-profile"
    port = _free_port()
    ws_events: list[dict[str, str | int]] = []
    journey_events: list[dict[str, object]] = []
    cleanup = {"page_closed": False, "context_closed": False, "browser_closed": False, "server_stopped": False, "port_released": False, "temp_db_removed": False, "ledger_removed": False, "profile_removed": False, "temp_root_removed": False, "jobs_stopped": False, "children_stopped": False}
    report: dict[str, object] = {"run_id": run_id, "status": "failed", "executed": False, "started_at_ns": started_ns, "browser": {"channel": "chrome", "fallback": False}, "fixture": {"port": port, "strategy_db": str(db), "decision_ledger": str(ledger), "profile": str(profile), "external_network": False, "provider_enabled": False, "final_approval_enabled": False}}
    report["journey_events"] = journey_events
    report["screenshots"] = []
    report["outcome_screenshots"] = []
    browser = context = page = server = thread = playwright = None
    try:
        out.mkdir(parents=True, exist_ok=False)
        profile.mkdir()
        sqlite3.connect(db).execute("create table strategy(id integer primary key, name text not null)").connection.close()
        ledger.write_text("", encoding="utf-8")
        root = Path(__file__).resolve().parents[1]
        frontend_source = root / "ai_strategy_loop" / "dashboard" / "frontend"
        webui_source = root / "ai_strategy_loop" / "dashboard" / "webui-build"
        dashboard_copy = runtime / "dashboard"
        frontend_copy = dashboard_copy / "frontend"
        webui_copy = dashboard_copy / "webui-build"
        shutil.copytree(frontend_source, frontend_copy)
        shutil.copytree(webui_source, webui_copy, ignore=shutil.ignore_patterns("node_modules"))
        shutil.copytree(webui_source / "node_modules", webui_copy / "node_modules", copy_function=os.link)
        build = subprocess.run(["node", "build-app.mjs"], cwd=webui_copy, check=False, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        if build.returncode != 0:
            raise RuntimeError(f"temp product build failed: {build.stderr[-2000:]}")
        research_source = frontend_source / "v4-research.jsx"
        bundle = frontend_copy / "bundle" / "app.js"
        source_hash = hashlib.sha256(research_source.read_bytes()).hexdigest()
        bundle_hash = hashlib.sha256(bundle.read_bytes()).hexdigest()
        bundle_text = bundle.read_text(encoding="utf-8")
        strict_markers = all(marker in bundle_text for marker in ("winner_gen", "review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"))
        report["product_identity"] = {"frontend": str(frontend_source), "research_source_sha256": source_hash, "bundle_sha256": bundle_hash, "temp_build": True, "strict_approval_markers": strict_markers, "synthetic_ui": False, "build_stdout": build.stdout[-1000:]}
        import uvicorn
        from playwright.sync_api import sync_playwright

        server = uvicorn.Server(uvicorn.Config(_product_fixture_app(frontend_copy, run_id, ws_events, journey_events), host="127.0.0.1", port=port, log_level="error"))
        server_errors: list[str] = []
        def run_server() -> None:
            try:
                server.run()
            except BaseException as exc:  # noqa: BROAD_EXCEPT_OK - cross-thread startup receipt.
                server_errors.append(f"{type(exc).__name__}: {exc}")
        thread = threading.Thread(target=run_server, name=f"uat-server-{run_id}", daemon=True)
        thread.start()
        deadline = time.monotonic() + 8
        while not server.started and time.monotonic() < deadline:
            thread.join(0.02)
        if not server.started:
            raise RuntimeError(f"fixture server did not start: {server_errors}")
        playwright = sync_playwright().start()
        if True:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.add_init_script(f"""(() => {{ const run={json.dumps(run_id)}; localStorage.setItem('stom.sim.demoSeen.v1','1'); localStorage.setItem('stom.sim.engine.v1','live'); const NativeWebSocket=window.WebSocket; window.__uatWsCloses=[]; window.WebSocket=function(...args){{const ws=new NativeWebSocket(...args); const url=String(args[0]); ws.addEventListener('close', event=>window.__uatWsCloses.push({{url,code:event.code,reason:event.reason,wasClean:event.wasClean}})); return ws}}; window.WebSocket.prototype=NativeWebSocket.prototype; for(const key of ['CONNECTING','OPEN','CLOSING','CLOSED']) Object.defineProperty(window.WebSocket,key,{{value:NativeWebSocket[key]}}); window.__uatCanvasDraws=0; for (const name of ['fillRect','stroke','fill']) {{ const original=CanvasRenderingContext2D.prototype[name]; CanvasRenderingContext2D.prototype[name]=function(...args){{window.__uatCanvasDraws++; return original.apply(this,args)}}; }} addEventListener('DOMContentLoaded', () => {{ document.body.dataset.runId=run; document.body.dataset.events='0'; new MutationObserver(() => document.body.dataset.events=String(Number(document.body.dataset.events||0)+1)).observe(document.getElementById('root'), {{subtree:true,childList:true,attributes:true}}); }}); }})()""")
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            obs = Observation()
            _observe(page, obs)
            report["errors"] = {"console": obs.console_errors, "expected_console": obs.expected_console_errors, "page": obs.page_errors, "request_failed": obs.request_failures, "unexpected_response": obs.unexpected_responses, "expected_fixture_failures": obs.expected_failures}
            page.goto(f"http://127.0.0.1:{port}/ui/v4/", wait_until="domcontentloaded", timeout=15_000)
            page.wait_for_function("() => document.querySelectorAll('[role=tab]').length === 8 && document.querySelector('.v4-root')", timeout=15_000)
            prewinner_binding = page.evaluate("async () => (await fetch('/freeze_verdict')).json()")
            keyboard_matrix: list[dict[str, str | bool]] = []
            page.locator("#v4-tab-research").focus()
            for tab in TABS[1:]:
                page.keyboard.press("ArrowRight")
                page.wait_for_function("name => document.activeElement?.id === 'v4-tab-' + name && document.querySelector('#v4-tab-' + name)?.getAttribute('aria-selected') === 'true' && !document.querySelector('#v4-panel-' + name)?.hidden && new URL(location.href).searchParams.get('tab') === name", arg=tab, timeout=3_000)
                keyboard_matrix.append(_keyboard_receipt(page, "ArrowRight", tab))
            page.keyboard.press("ArrowRight"); page.wait_for_function("() => document.activeElement?.id === 'v4-tab-research'")
            keyboard_matrix.append(_keyboard_receipt(page, "ArrowRight-wrap", "research"))
            page.keyboard.press("ArrowLeft"); page.wait_for_function("() => document.activeElement?.id === 'v4-tab-context'")
            keyboard_matrix.append(_keyboard_receipt(page, "ArrowLeft-wrap", "context"))
            page.keyboard.press("Home"); page.wait_for_function("() => document.activeElement?.id === 'v4-tab-research'")
            keyboard_matrix.append(_keyboard_receipt(page, "Home", "research"))
            page.keyboard.press("End"); page.wait_for_function("() => document.activeElement?.id === 'v4-tab-context'")
            keyboard_matrix.append(_keyboard_receipt(page, "End", "context"))
            screenshots = []
            for tab in TABS:
                before = int(page.locator("body").get_attribute("data-events"))
                page.locator(f"#v4-tab-{tab}").click()
                page.locator(f"#v4-panel-{tab}").wait_for(state="visible")
                screenshots.append(_capture(page, out, tab, run_id, started_ns, before))
            report["screenshots"] = screenshots
            page.locator("#v4-tab-backtest").click()
            report["stage"] = "backtest_wait_strategies"
            bt_selects = page.locator(".v4-backtest-workspace select.select")
            page.wait_for_function("() => [...document.querySelectorAll('.v4-backtest-workspace select.select')].slice(0,2).every(s => s.options.length > 1)", timeout=8_000)
            bt_selects.nth(0).select_option("fixture_buy_g2"); bt_selects.nth(1).select_option("fixture_sell_g2")
            bt_inputs = page.locator(".v4-backtest-workspace input.input")
            bt_inputs.nth(0).fill("20260101"); bt_inputs.nth(1).fill("20261231")
            report["stage"] = "backtest_run_job_1"
            bt_run = page.locator(".v4-backtest-workspace button.btn.primary").first
            bt_run.click()
            page.wait_for_function("() => document.querySelector('.v4-backtest-workspace')?.textContent.includes('uat-success')", timeout=8_000)
            report["stage"] = "backtest_open_result_job_1"
            page.wait_for_function("() => document.querySelector('.v4-backtest-workspace')?.textContent.includes('12.5')", timeout=8_000)
            bt_run.click()
            report["stage"] = "backtest_run_job_2"
            page.wait_for_function("() => document.querySelector('.v4-backtest-workspace')?.textContent.includes('uat-cancel')", timeout=8_000)
            page.locator(".v4-backtest-workspace button.btn.danger").first.click()
            report["stage"] = "backtest_cancel_job_2"
            deadline_cancel = time.monotonic() + 5
            while not any(event.get("kind") == "bt_cancel" for event in journey_events) and time.monotonic() < deadline_cancel:
                page.wait_for_timeout(50)
            while not any(event.get("kind") == "bt_ws_terminal" and event.get("job_id") == "uat-cancel" for event in journey_events) and time.monotonic() < deadline_cancel:
                page.wait_for_timeout(50)
            bt_outcome = _capture(page, out, "backtest-outcome", run_id, started_ns, -1)
            report["outcome_screenshots"].append(bt_outcome)
            bt_runs = [event for event in journey_events if event.get("kind") == "bt_run"]
            bt_cancel_events = [event for event in journey_events if event.get("kind") == "bt_cancel"]
            bt_result_events = [event for event in journey_events if event.get("kind") == "bt_result" and event.get("job_id") == "uat-success"]
            report["stage"] = "replay_start"
            page.locator("#v4-tab-replay").click()
            page.locator("#v4-panel-replay button", has_text="최근 거래일").first.click()
            page.wait_for_function("() => document.querySelector('#v4-panel-replay input[type=range]')?.max === '3'", timeout=8_000)
            replay_slider = page.locator("#v4-panel-replay input[type=range]").first
            page.keyboard.press("Space")
            replay_slider.fill("0")
            page.wait_for_function("() => document.querySelector('#v4-panel-replay')?.textContent.includes('09:00')", timeout=5_000)
            replay_slider.fill("3")
            page.wait_for_function("() => document.querySelector('#v4-panel-replay')?.textContent.includes('13:00')", timeout=5_000)
            editable_actions = len([event for event in journey_events if event.get("kind") == "sim_action"])
            page.keyboard.press("Space")
            editable_after = len([event for event in journey_events if event.get("kind") == "sim_action"])
            editable_keyboard_receipt = {"context": "range-input", "keys": ["Space"], "before_actions": editable_actions, "after_actions": editable_after, "delta": editable_after - editable_actions}
            editable_keyboard_ignored = editable_keyboard_receipt["delta"] == 0
            page.locator("#v4-panel-replay .chart-wrap").first.click()
            page.keyboard.press("ArrowRight"); page.keyboard.press("Space")
            deadline_keys = time.monotonic() + 3
            while not any(event.get("kind") == "sim_action" and event.get("payload", {}).get("action") == "resume" for event in journey_events) and time.monotonic() < deadline_keys:
                page.wait_for_timeout(20)
            replay_canvas = page.locator("#v4-panel-replay .chart-wrap canvas").first
            replay_pixels = replay_canvas.evaluate("c => [...c.getContext('2d').getImageData(0,0,c.width,c.height).data].filter((v,i)=>i%4!==3&&v!==0).length")
            replay_draw_events = page.evaluate("() => window.__uatCanvasDraws")
            replay_outcome = _capture(page, out, "replay-outcome", run_id, started_ns, -1)
            report["outcome_screenshots"].append(replay_outcome)
            page.keyboard.press("Escape")
            deadline_stop = time.monotonic() + 3
            while not any(event.get("kind") == "sim_action" and event.get("payload", {}).get("action") == "stop" for event in journey_events) and time.monotonic() < deadline_stop:
                page.wait_for_timeout(20)
            sim_actions = [event.get("payload", {}) for event in journey_events if event.get("kind") == "sim_action"]
            report["stage"] = "history_archive_failure"
            page.locator("#v4-tab-history").click()
            page.evaluate("() => { const main=document.querySelector('main'); main.tabIndex=-1; main.focus(); }")
            hidden_action_count = len(sim_actions); page.keyboard.press("Space"); page.keyboard.press("ArrowRight")
            hidden_after = len([event for event in journey_events if event.get("kind") == "sim_action"])
            hidden_keyboard_receipt = {"context": "hidden-replay-panel", "keys": ["Space", "ArrowRight"], "before_actions": hidden_action_count, "after_actions": hidden_after, "delta": hidden_after - hidden_action_count}
            hidden_keyboard_ignored = hidden_keyboard_receipt["delta"] == 0
            run_selector = page.locator("select.v4-runsel-select")
            run_selector.select_option("ARCHIVE_FAIL")
            archive_alert = page.locator("main [role=alert]").first
            archive_alert.wait_for(state="visible", timeout=8_000)
            archive_text = archive_alert.inner_text()
            archive_alert.scroll_into_view_if_needed()
            archive_receipt = page.evaluate("""() => {
                const tab = document.querySelector('#v4-tab-history');
                const panel = document.querySelector('#v4-panel-history');
                const alert = document.querySelector('main [role=alert]');
                const box = alert?.getBoundingClientRect();
                return {
                    active_tab: tab?.getAttribute('aria-selected') === 'true' ? 'history' : null,
                    panel_visible: Boolean(panel && !panel.hidden),
                    alert_visible: Boolean(alert && getComputedStyle(alert).visibility !== 'hidden' && getComputedStyle(alert).display !== 'none'),
                    alert_text: alert?.textContent?.trim() || '',
                    alert_in_viewport: Boolean(box && box.top >= 0 && box.bottom <= innerHeight && box.left >= 0 && box.right <= innerWidth),
                    scroll_y: scrollY,
                    alert_box: box ? {top: box.top, bottom: box.bottom, left: box.left, right: box.right} : null,
                };
            }""")
            archive_outcome = _capture(page, out, "archive-failure", run_id, started_ns, -1)
            report["outcome_screenshots"].append(archive_outcome)
            expected_console = "Failed to load resource: the server responded with a status of 503 (Service Unavailable)"
            if len(obs.expected_failures) == 1 and expected_console in obs.console_errors:
                obs.console_errors.remove(expected_console); obs.expected_console_errors.append(expected_console)
            run_selector.select_option("")
            page.wait_for_function("() => document.querySelector('.v4-view-title')?.textContent.includes('LIVE')", timeout=5_000)
            page.locator("#v4-tab-research").click()
            report["stage"] = "research_start"
            page.locator(".v4-runbar button.btn.primary").click()
            start_modal = page.locator(".modal"); start_modal.wait_for(state="visible", timeout=5_000)
            start_submit = start_modal.locator("button.btn.primary.lg")
            page.wait_for_function("() => !document.querySelector('.modal button.btn.primary.lg')?.disabled", timeout=5_000)
            start_submit.click()
            page.wait_for_function("() => document.querySelector('.v4-research')?.textContent.includes('fixture_buy_g2') && document.querySelector('.v4-research-live-summary')?.textContent.includes('complete')", timeout=8_000)
            research_start_events = [event for event in journey_events if event.get("kind") == "research_start"]
            research_outcome = _capture(page, out, "research-winner", run_id, started_ns, -1)
            report["outcome_screenshots"].append(research_outcome)
            binding_receipt = page.evaluate("async () => (await fetch('/freeze_verdict')).json()")
            binding_required = {"available", "run_id", "current_gen", "winner_gen", "winner_buy", "winner_sell", "review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"}
            if not binding_required.issubset(binding_receipt.get("approval_binding", {})):
                raise RuntimeError("freeze_verdict fixture binding is incomplete")
            report["approval_preclick"] = {"binding": binding_receipt["approval_binding"], "rendered_blockers": page.locator(".v4-research-error").all_inner_texts()}
            page.wait_for_function("() => !document.querySelector('.v4-research-error')", timeout=3_000)
            approval_button = page.locator(".v4-research button.btn.primary", has_text="Export").first
            report["approval_preclick"].update({"button_text": approval_button.inner_text(), "enabled": approval_button.is_enabled()})
            approval_button.wait_for(state="visible", timeout=10_000); approval_button.click()
            modal = page.locator(".modal"); modal.wait_for(state="visible")
            inputs = modal.locator("input"); inputs.nth(2).fill("승인")
            modal.locator("button.btn.primary").click()
            page.wait_for_function("() => document.querySelector('.v4-research')", timeout=5_000)
            deadline_ws = time.monotonic() + 5
            while not ws_events and time.monotonic() < deadline_ws:
                page.wait_for_timeout(50)
            approval = next((event for event in ws_events if event.get("action") == "final_approval"), {})
            page.wait_for_function("() => window.__uatWsCloses.some(item => item.code === 4403 && item.reason === 'capability_disabled')", timeout=5_000)
            approval_close = page.evaluate("() => window.__uatWsCloses.find(item => item.code === 4403 && item.reason === 'capability_disabled') || {}")
            page.locator("#v4-tab-research").focus(); page.keyboard.press("End"); keyboard = page.locator("#v4-tab-context").get_attribute("aria-selected") == "true"
            errors = {"console": obs.console_errors, "expected_console": obs.expected_console_errors, "page": obs.page_errors, "request_failed": obs.request_failures, "unexpected_response": obs.unexpected_responses, "expected_fixture_failures": obs.expected_failures}
            required = {"run_id", "current_gen", "winner_gen", "user_buy", "user_sell", "review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"}
            replay_seek = [action for action in sim_actions if action.get("action") == "seek_index"]
            research_frames = [event for event in journey_events if event.get("kind") == "research_frame"]
            backtest_receipts = [event for event in journey_events if str(event.get("kind", "")).startswith("bt_")]
            replay_frames = [event for event in journey_events if event.get("kind") == "sim_frame"]
            replay_bar_frames = [event["payload"] for event in replay_frames if event.get("payload", {}).get("type") == "bars"]
            replay_history_frames = [event["payload"] for event in replay_frames if event.get("payload", {}).get("type") == "history"]
            replay_frame_contract = (
                [frame.get("t") for frame in replay_bar_frames] == [90000, 90100, 93000, 130000]
                and [frame.get("elapsed_seconds") for frame in replay_bar_frames] == [0, 60, 1800, 14400]
                and {frame.get("index") for frame in replay_history_frames} == {0, 3}
            )
            outcome_receipts = [research_outcome, bt_outcome, replay_outcome, archive_outcome]
            assertions = {"current_product_bundle": strict_markers and bool(page.locator(".v4-root")), "eight_tabs_dom_keyboard": keyboard and len(keyboard_matrix) == 11 and all(bool(item["valid"]) for item in keyboard_matrix), "screenshots_fresh": len(screenshots) == 8 and all(bool(item["valid"]) for item in screenshots) and len({str(item["sha256"]) for item in screenshots}) == 8, "journey_outcome_screenshots_fresh": all(bool(item["valid"]) for item in outcome_receipts) and len({str(item["sha256"]) for item in outcome_receipts}) == 4, "actual_product_research_start_generation_winner": len(research_start_events) == 1 and [frame.get("phase") for frame in research_frames] == ["running", "generation", "winner"] and prewinner_binding.get("approval_binding", {}).get("available") is False, "actual_ui_full_approval_payload": required.issubset(approval) and approval.get("run_id") == run_id, "actual_ui_default_off_denial": default_off_denial_valid(approval, approval_close) and db.stat().st_size > 0, "actual_product_backtest_result": len(bt_runs) == 2 and bool(bt_result_events) and bt_runs[0].get("job_id") == "uat-success" and any(event.get("kind") == "bt_ws_terminal" and event.get("job_id") == "uat-success" for event in backtest_receipts), "actual_product_backtest_distinct_cancel": bool(bt_cancel_events) and bt_cancel_events[-1].get("job_id") == "uat-cancel" and any(event.get("kind") == "bt_ws_terminal" and event.get("job_id") == "uat-cancel" for event in backtest_receipts), "actual_product_replay_canvas_ws_seek": int(replay_pixels) > 0 and int(replay_draw_events) > 0 and replay_frame_contract and {int(action.get("index", -1)) for action in replay_seek} == {0, 3} and any(action.get("action") == "start" for action in sim_actions), "replay_keyboard_editable_hidden_boundaries": editable_keyboard_ignored and hidden_keyboard_ignored and any(action.get("action") == "resume" for action in sim_actions) and any(action.get("action") == "stop" for action in sim_actions), "actual_product_archive_failure": archive_outcome_valid(archive_receipt) and len(obs.expected_failures) == 1, "browser_errors_classified": not obs.console_errors and not obs.page_errors and not obs.request_failures and not obs.unexpected_responses}
            report.update({"executed": True, "browser": {"channel": "chrome", "version": browser.version, "fallback": False}, "tabs": list(TABS), "keyboard_matrix": keyboard_matrix, "journeys": {"research_prewinner_binding": prewinner_binding, "research_frames": research_frames, "research_actual_ui_approval_payload": approval, "default_off_close": approval_close, "backtest_receipts": backtest_receipts, "replay_frames": replay_frames, "editable_keyboard_receipt": editable_keyboard_receipt, "hidden_keyboard_receipt": hidden_keyboard_receipt, "events": journey_events, "research_outcome_screenshot": research_outcome, "backtest_outcome_screenshot": bt_outcome, "replay_outcome_screenshot": replay_outcome, "replay_pixels": replay_pixels, "replay_draw_events": replay_draw_events, "archive_alert": archive_text, "archive_receipt": archive_receipt, "archive_outcome_screenshot": archive_outcome}, "assertions": assertions, "errors": errors, "screenshots": screenshots})
            report["stage"] = "complete"
            report["status"] = "executed" if all(assertions.values()) else "failed"
    except Exception as exc:  # noqa: BROAD_EXCEPT_OK - top-level UAT boundary must emit cleanup evidence.
        report["failure"] = {"type": type(exc).__name__, "reason": str(exc)}
        report["status"] = "failed"
    finally:
        if page is not None:
            page.close(); cleanup["page_closed"] = page.is_closed()
        if context is not None:
            context.close(); cleanup["context_closed"] = all(item.is_closed() for item in context.pages)
        if browser is not None:
            browser.close(); cleanup["browser_closed"] = not browser.is_connected()
        if playwright is not None:
            playwright.stop()
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(5); cleanup["server_stopped"] = not thread.is_alive()
        terminal_jobs = {str(event.get("job_id")): event.get("payload", {}).get("status") for event in journey_events if event.get("kind") == "bt_ws_terminal"}
        cleanup["jobs_stopped"] = cleanup["server_stopped"] and (not terminal_jobs or terminal_jobs == {"uat-success": "success", "uat-cancel": "cancelled"})
        cleanup["children_stopped"] = cleanup["server_stopped"] and (thread is None or not thread.is_alive()) and ("build" in locals() and build.returncode == 0)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                cleanup["port_released"] = False
        except OSError:
            cleanup["port_released"] = True
        shutil.rmtree(runtime, ignore_errors=False)
        cleanup.update({"temp_db_removed": not db.exists(), "ledger_removed": not ledger.exists(), "profile_removed": not profile.exists(), "temp_root_removed": not runtime.exists()})
        report["cleanup"] = cleanup
        report["completed_at_ns"] = time.time_ns()
    clean = all(cleanup.values())
    if not clean:
        report["status"] = "failed"
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report, clean


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="required: run the complete real-browser scenario")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if not args.execute:
        print("ERROR: --execute is required; non-executed UAT cannot pass", file=sys.stderr)
        return 2
    out = Path(args.out)
    if out.exists():
        print("ERROR: --out must be a fresh, non-existing directory", file=sys.stderr)
        return 2
    try:
        report, clean = execute(out)
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if report.get("status") == "executed" and clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
