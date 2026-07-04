from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "overnight-process-research-20260627"
LOG_DIR = ART / "logs"
EVENTS = ART / "anchor-fallback-events.jsonl"
SUMMARY = ART / "anchor-fallback-summary.json"
MORNING_REPORT = ROOT / "docs" / "research" / "condition_research" / "auto_reports" / "morning_20260628_process_research.md"

ENV = os.environ.copy()
ENV.setdefault("PYTHONUTF8", "1")
ENV.setdefault("PYTHONIOENCODING", "utf-8")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit(kind: str, **payload: Any) -> None:
    rec = {"ts": now(), "kind": kind, **payload}
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("[ANCHOR-FB] " + json.dumps(rec, ensure_ascii=False), flush=True)


def run_cmd(name: str, cmd: list[str], timeout: int | None = None) -> dict[str, Any]:
    emit("command_start", name=name, command=cmd)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{name}.log"
    started = time.perf_counter()
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    tail: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            tail.append(line)
            tail = tail[-30:]
            with log.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
            print(f"[{name}] {line}", flush=True)
        rc = proc.wait(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.terminate()
        try:
            rc = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = proc.wait()
    result = {"name": name, "command": cmd, "returncode": rc, "timedOut": timed_out, "elapsedSec": round(time.perf_counter() - started, 3), "log": str(log.relative_to(ROOT)), "tail": tail}
    emit("command_end", **result)
    return result


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    emit("fallback_start", reason="gpt_auth refresh token invalidated; switching to LLM-free anchor mutation/backtest research")
    results: dict[str, Any] = {"startedAt": now(), "reason": "gpt_auth_refresh_token_invalidated", "commands": []}

    results["commands"].append(run_cmd("git_status_fallback_start", ["git", "status", "--short", "--branch", "--untracked-files=no"]))
    results["anchor_mutation"] = run_cmd(
        "anchor_mutation",
        [
            sys.executable,
            "-m",
            "ai_strategy_loop.scripts.overnight_anchor_mutation",
            "--config-json",
            str(ART / "process_b_research.json"),
            "--run-prefix",
            "ovn_anchor_20260627",
            "--out",
            str(ART / "anchor.jsonl"),
            "--deadline-hhmm",
            "06:00",
            "--max-rounds",
            "0",
            "--round-timeout",
            "5400",
        ],
    )
    results["morning_report"] = run_cmd(
        "morning_report_fallback",
        [sys.executable, "-m", "ai_strategy_loop.scripts.gen_morning_report", "--out", str(MORNING_REPORT)],
    )
    for name, cmd in [
        ("nonrelease_sync_fallback_final", [sys.executable, "scripts/verify_nonrelease_sync.py"]),
        ("git_diff_check_fallback_final", ["git", "diff", "--check"]),
        ("protected_paths_fallback_final", ["git", "status", "--short", "--", "_database", "_database_v3k_shadow", "_log", "backup", "*.db", "backtest/graph", ".omx/reports", "v3k_settings*.json"]),
        ("git_status_fallback_final", ["git", "status", "--short", "--branch", "--untracked-files=no"]),
    ]:
        results["commands"].append(run_cmd(name, cmd))
    results["completedAt"] = now()
    SUMMARY.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("fallback_complete", summary=str(SUMMARY.relative_to(ROOT)), morningReport=str(MORNING_REPORT.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
