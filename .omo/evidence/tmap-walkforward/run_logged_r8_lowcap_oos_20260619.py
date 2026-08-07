from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVID = ROOT / ".omo" / "evidence" / "tmap-walkforward"
WRAPPER = EVID / "run_post_q4_oos_wrapper_20260619.py"
PAIRS = EVID / "pairs-post-q4-r8-lowcap-oos-20260619.json"
LOG_DIR = EVID / "post-q4-oos-logs-20260619"
RUNS = [
    ("2025q4", EVID / "oos-2025-q4-e32-config.json", "post_q4_r8_lowcap_oos_2025q4_logged_20260619"),
    ("2022", EVID / "oos-2022-e32-config.json", "post_q4_r8_lowcap_oos_2022_logged_20260619"),
    ("2023", EVID / "oos-2023-e32-config.json", "post_q4_r8_lowcap_oos_2023_logged_20260619"),
    ("2024", EVID / "oos-2024-e32-config.json", "post_q4_r8_lowcap_oos_2024_logged_20260619"),
    ("2025", EVID / "oos-2025-e32-config.json", "post_q4_r8_lowcap_oos_2025_logged_20260619"),
    ("2026", EVID / "oos-2026-e32-config.json", "post_q4_r8_lowcap_oos_2026_logged_20260619"),
]


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for period, config, run_id in RUNS:
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
        started = time.time()
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=3600,
        )
        finished = time.time()
        stdout_path = LOG_DIR / f"{run_id}.stdout.txt"
        stderr_path = LOG_DIR / f"{run_id}.stderr.txt"
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        entry = {
            "period": period,
            "run_id": run_id,
            "command": command,
            "returncode": result.returncode,
            "started_at": started,
            "finished_at": finished,
            "elapsed_seconds": round(finished - started, 3),
            "stdout_path": str(stdout_path.relative_to(ROOT)).replace("\\\\", "/"),
            "stderr_path": str(stderr_path.relative_to(ROOT)).replace("\\\\", "/"),
        }
        manifest.append(entry)
        print(json.dumps(entry, ensure_ascii=False))
        if result.returncode != 0:
            (LOG_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            return result.returncode
    (LOG_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
