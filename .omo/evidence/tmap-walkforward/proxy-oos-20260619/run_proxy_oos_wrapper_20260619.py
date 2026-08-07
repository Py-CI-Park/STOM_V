from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUN_ROOT = Path(__file__).resolve().parent
STRATEGY_SQLITE = RUN_ROOT / "proxy-oos-strategy-20260619.sqlite"
RUNS_SQLITE = RUN_ROOT / "proxy-oos-loop-runs-20260619.sqlite"
SNAPSHOTS = RUN_ROOT / "snapshots"
CURRENT_STATE = RUN_ROOT / "current-state.json"
STOP_FLAG = RUN_ROOT / "STOP"


def _assert_run_owned(path: Path) -> None:
    resolved = path.resolve()
    root = RUN_ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise RuntimeError(f"mutable path is outside proxy run root: {resolved}")


def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
    for path in [STRATEGY_SQLITE, RUNS_SQLITE, SNAPSHOTS, CURRENT_STATE, STOP_FLAG]:
        _assert_run_owned(path)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    os.environ["STOM_CLI_DB_STRATEGY"] = str(STRATEGY_SQLITE)

    import ai_strategy_loop.controller.state as state

    state.LOOP_RUNS_DB = RUNS_SQLITE
    state._SNAPSHOT_DIR = SNAPSHOTS
    state.CURRENT_STATE_FILE = CURRENT_STATE
    state.STOP_FLAG_FILE = STOP_FLAG

    sys.argv = [
        "ai_strategy_loop.scripts.claude_candidate_batch_eval",
        *sys.argv[1:],
    ]
    runpy.run_module("ai_strategy_loop.scripts.claude_candidate_batch_eval", run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
