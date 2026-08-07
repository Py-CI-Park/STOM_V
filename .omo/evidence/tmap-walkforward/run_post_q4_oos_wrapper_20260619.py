from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EVID = ROOT / ".omo" / "evidence" / "tmap-walkforward"
STRATEGY_SQLITE = EVID / "post-q4-oos-strategy-20260619.sqlite"
RUNS_SQLITE = EVID / "post-q4-oos-loop-runs-20260619.sqlite"
SNAPSHOTS = EVID / "post-q4-oos-snapshots-20260619"
CURRENT_STATE = EVID / "post-q4-oos-current-state-20260619.json"
STOP_FLAG = EVID / "post-q4-oos-STOP-20260619"


def main() -> int:
    os.environ.setdefault("PYTHONUTF8", "1")
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
