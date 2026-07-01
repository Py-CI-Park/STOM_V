from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "gpt-auth-process-research-20260627"
LOG_DIR = ART / "logs"
EVENTS = ART / "driver-events.jsonl"
SUMMARY = ART / "gpt-auth-research-summary.json"
MORNING_REPORT = ROOT / "docs" / "research" / "condition_research" / "auto_reports" / "morning_20260628_gpt_auth_process_research.md"

ENV = os.environ.copy()
ENV.setdefault("PYTHONUTF8", "1")
ENV.setdefault("PYTHONIOENCODING", "utf-8")
ENV.setdefault("GJC_NO_COLOR", "1")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(kind: str, **payload: Any) -> None:
    record = {"ts": utc_now(), "kind": kind, **payload}
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print("[GPT-RUN] " + json.dumps(record, ensure_ascii=False), flush=True)


def run_cmd(name: str, cmd: list[str], *, timeout: int | None = None, continue_on_timeout: bool = False) -> dict[str, Any]:
    emit("command_start", name=name, command=cmd)
    started = time.perf_counter()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{name}.log"
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    lines: list[str] = []
    timed_out = False
    try:
        assert proc.stdout is not None
        deadline = None if timeout is None else time.time() + timeout
        for line in proc.stdout:
            line = line.rstrip("\n")
            lines.append(line)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            print(f"[{name}] {line}", flush=True)
            if deadline is not None and time.time() > deadline:
                timed_out = True
                if continue_on_timeout:
                    break
                proc.terminate()
                break
        if timed_out and not continue_on_timeout:
            try:
                rc = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = proc.wait()
        elif continue_on_timeout and timed_out:
            rc = None
        else:
            rc = proc.wait(timeout=30 if timeout is not None else None)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.terminate()
        try:
            rc = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait()
    elapsed = round(time.perf_counter() - started, 3)
    result = {"name": name, "command": cmd, "returncode": rc, "timedOut": timed_out, "elapsedSec": elapsed, "log": str(log_path.relative_to(ROOT)), "tail": lines[-30:]}
    emit("command_end", **result)
    return result


def ensure_dashboard() -> dict[str, Any]:
    url = "http://127.0.0.1:8770/health"
    try:
        body = urllib.request.urlopen(url, timeout=5).read().decode("utf-8", "replace")
        emit("dashboard_health", status="ok", body=body)
        return {"status": "ok", "body": body}
    except Exception as exc:
        emit("dashboard_health", status="launching", error=str(exc))
        subprocess.Popen(["cmd.exe", "/c", "start", "", "stom_dashboard.bat"], cwd=str(ROOT), env=ENV)
        time.sleep(10)
        try:
            body = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", "replace")
            emit("dashboard_health", status="ok", body=body)
            return {"status": "ok", "body": body}
        except Exception as exc2:
            emit("dashboard_health", status="failed", error=str(exc2))
            return {"status": "failed", "error": str(exc2)}


def proxy_smoke() -> dict[str, Any]:
    code = r'''
from ai_strategy_loop.provider.chatgpt_oauth import start_proxy_sync, stop_proxy_sync
from ai_strategy_loop.provider.chatgpt_oauth.constants import get_proxy_base_url, PROXY_OPENAI_API_KEY_PLACEHOLDER
import requests
try:
    ok = start_proxy_sync(timeout_seconds=30)
    print('start_proxy', ok, get_proxy_base_url())
    if not ok:
        raise SystemExit(2)
    r = requests.post(
        get_proxy_base_url() + '/chat/completions',
        headers={'Authorization': f'Bearer {PROXY_OPENAI_API_KEY_PLACEHOLDER}', 'Content-Type': 'application/json'},
        json={'model': 'gpt-5.5', 'messages': [{'role': 'user', 'content': 'Return exactly STOM_OK'}], 'max_tokens': 16},
        timeout=120,
    )
    print('status', r.status_code)
    print(r.text[:2000])
    raise SystemExit(0 if r.status_code == 200 and 'STOM_OK' in r.text else 3)
finally:
    try:
        stop_proxy_sync(timeout_seconds=30)
    except Exception as exc:
        print('stop_error', repr(exc))
'''
    return run_cmd("gpt_auth_proxy_smoke", [sys.executable, "-c", code], timeout=180)


def phase(name: str, config: str, run_id: str) -> dict[str, Any]:
    cfg_path = ART / config
    if not cfg_path.is_file():
        emit("phase_missing_config", phase=name, config=str(cfg_path))
        return {"name": name, "status": "missing_config", "config": str(cfg_path)}
    return run_cmd(
        name,
        [sys.executable, "-m", "ai_strategy_loop.controller.loop", "--config-json", str(cfg_path), "--run-id", run_id],
    )


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    emit("gpt_auth_research_start", artifactDir=str(ART.relative_to(ROOT)))
    results: dict[str, Any] = {"startedAt": utc_now(), "artifactDir": str(ART.relative_to(ROOT)), "commands": []}
    results["dashboard"] = ensure_dashboard()
    for name, cmd in [
        ("git_status_start", ["git", "status", "--short", "--branch", "--untracked-files=no"]),
        ("oauth_status", [sys.executable, "-m", "ai_strategy_loop.provider.chatgpt_oauth.oauth_login", "status"]),
        ("nonrelease_sync_start", [sys.executable, "scripts/verify_nonrelease_sync.py"]),
        ("protected_paths_start", ["git", "status", "--short", "--", "_database", "_database_v3k_shadow", "_log", "backup", "*.db", "backtest/graph", ".omx/reports", "v3k_settings*.json"]),
    ]:
        results["commands"].append(run_cmd(name, cmd))
    results["proxy_smoke"] = proxy_smoke()
    if results["proxy_smoke"].get("returncode") != 0:
        emit("proxy_smoke_failed", returncode=results["proxy_smoke"].get("returncode"))
        results["completedAt"] = utc_now()
        results["status"] = "blocked_proxy_smoke"
        SUMMARY.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2

    phases = [
        ("smoke_generation", "process_smoke.json", "gptauth_smoke_20260627"),
        ("process_a_fast", "process_a_fast.json", "gptauth_A_fast_20260627"),
        ("process_b_research", "process_b_research.json", "gptauth_B_research_20260627"),
        ("process_c_review", "process_c_review.json", "gptauth_C_review_20260627"),
    ]
    phase_results = []
    for name, config, run_id in phases:
        phase_result = phase(name, config, run_id)
        phase_results.append(phase_result)
        if phase_result.get("returncode") not in (0, None):
            emit("phase_nonzero", phase=name, returncode=phase_result.get("returncode"), continuing=True)
    results["phases"] = phase_results

    results["morning_report"] = run_cmd(
        "morning_report",
        [sys.executable, "-m", "ai_strategy_loop.scripts.gen_morning_report", "--out", str(MORNING_REPORT)],
    )
    for name, cmd in [
        ("nonrelease_sync_final", [sys.executable, "scripts/verify_nonrelease_sync.py"]),
        ("git_diff_check_final", ["git", "diff", "--check", "--", str(ART.relative_to(ROOT)), str(MORNING_REPORT.relative_to(ROOT)), "docs/update_log/2026-06-27_gpt_auth_research_rerun_log.md"]),
        ("protected_paths_final", ["git", "status", "--short", "--", "_database", "_database_v3k_shadow", "_log", "backup", "*.db", "backtest/graph", ".omx/reports", "v3k_settings*.json"]),
        ("git_status_final", ["git", "status", "--short", "--branch", "--untracked-files=no"]),
    ]:
        results["commands"].append(run_cmd(name, cmd))
    results["completedAt"] = utc_now()
    results["status"] = "complete"
    SUMMARY.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("gpt_auth_research_complete", summary=str(SUMMARY.relative_to(ROOT)), morningReport=str(MORNING_REPORT.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
