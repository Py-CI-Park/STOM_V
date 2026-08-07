from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import psutil
except Exception:  # pragma: no cover - cleanup degrades to Popen.kill.
    psutil = None

ROOT = Path(__file__).resolve().parents[4]
RUN_ROOT = Path(__file__).resolve().parent
WRAPPER = RUN_ROOT / "run_proxy_oos_wrapper_20260619.py"
PAIRS = RUN_ROOT / "pairs-proxy-oos-20260619.json"
LOG_DIR = RUN_ROOT / "logs"

RUNS = {
    "q4": ("2025q4", RUN_ROOT / "proxy-2025q4-e8-config.json", "proxy_oos_q4_e8_rerun_20260619"),
    "2022": ("2022", RUN_ROOT / "proxy-2022-e8-config.json", "proxy_oos_2022_e8_20260619"),
    "2023": ("2023", RUN_ROOT / "proxy-2023-e8-config.json", "proxy_oos_2023_e8_20260619"),
    "2024": ("2024", RUN_ROOT / "proxy-2024-e8-config.json", "proxy_oos_2024_e8_20260619"),
    "2025": ("2025", RUN_ROOT / "proxy-2025-e8-config.json", "proxy_oos_2025_e8_20260619"),
    "2026": ("2026", RUN_ROOT / "proxy-2026-e8-config.json", "proxy_oos_2026_e8_20260619"),
}


def _kill_tree(proc: subprocess.Popen[str]) -> list[int]:
    killed: list[int] = []
    if psutil is None:
        proc.kill()
        return killed
    try:
        parent = psutil.Process(proc.pid)
    except Exception:
        proc.kill()
        return killed
    children = parent.children(recursive=True)
    for child in children:
        try:
            killed.append(child.pid)
            child.terminate()
        except Exception:
            pass
    try:
        parent.terminate()
    except Exception:
        pass
    gone, alive = psutil.wait_procs(children + [parent], timeout=10)
    for item in alive:
        try:
            killed.append(item.pid)
            item.kill()
        except Exception:
            pass
    return sorted(set(killed))


def run_one(period_key: str, timeout_seconds: int) -> dict:
    period, config, run_id = RUNS[period_key]
    command = [
        sys.executable,
        str(WRAPPER),
        "--pairs-json",
        str(PAIRS),
        "--config-json",
        str(config),
        "--run-id",
        run_id,
    ]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timeout_hit = False
    killed: list[int] = []
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timeout_hit = True
        killed = _kill_tree(proc)
        stdout, stderr = proc.communicate(timeout=30)
    finished = time.time()
    stdout_path = LOG_DIR / f"{run_id}.stdout.txt"
    stderr_path = LOG_DIR / f"{run_id}.stderr.txt"
    stdout_path.write_text(stdout or "", encoding="utf-8")
    stderr_path.write_text(stderr or "", encoding="utf-8")
    entry = {
        "period": period,
        "period_key": period_key,
        "run_id": run_id,
        "command": command,
        "returncode": proc.returncode,
        "timeout_hit": timeout_hit,
        "timeout_seconds": timeout_seconds,
        "killed_pids": killed,
        "started_at": started,
        "finished_at": finished,
        "elapsed_seconds": round(finished - started, 3),
        "stdout_path": str(stdout_path.relative_to(ROOT)).replace("\\", "/"),
        "stderr_path": str(stderr_path.relative_to(ROOT)).replace("\\", "/"),
    }
    return entry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--periods", nargs="+", default=["q4"])
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()

    manifest_path = LOG_DIR / "rerun-manifest.json"
    existing = []
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in args.periods:
        if key not in RUNS:
            raise SystemExit(f"unknown period key: {key}")
        entry = run_one(key, args.timeout)
        existing.append(entry)
        manifest_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(entry, ensure_ascii=False))
        if entry["returncode"] != 0 or entry["timeout_hit"]:
            return int(entry["returncode"] or 124)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
