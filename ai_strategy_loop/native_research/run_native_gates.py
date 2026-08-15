"""Run import/path/isolation gates for the five native research tool boundaries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from .adapter import NativeResearchAdapter
from .contracts import NativeRunSpec, NativeTool

_TOOL_TARGETS = {
    NativeTool.BACKFINDER: ("backtest.backfinder", "BackFinder"),
    NativeTool.CONDITIONS: ("backtest.optimiz_conditions", "OptimizeConditions"),
    NativeTool.OPTIMIZE: ("backtest.optimiz", "Optimize"),
    NativeTool.GENETIC: ("backtest.optimiz_genetic_algorithm", "OptimizeGeneticAlgorithm"),
    NativeTool.RWFT: ("backtest.rolling_walk_forward_test", "RollingWalkForwardTest"),
}


def _probe(module: str, symbol: str) -> str:
    return (
        "import os\n"
        "from pathlib import Path\n"
        "from utility import setting_base as s\n"
        f"from {module} import {symbol}\n"
        f"assert {symbol}.__name__ == {symbol!r}\n"
        "assert Path(s.DB_STRATEGY).resolve() == Path(os.environ['STOM_CLI_DB_STRATEGY']).resolve()\n"
        "assert Path(s.DB_BACKTEST).resolve() == Path(os.environ['STOM_CLI_DB_BACKTEST']).resolve()\n"
        "assert Path(s.DB_SETTING).resolve() == Path(os.environ['STOM_CLI_DB_SETTING']).resolve()\n"
        "assert Path(s.DB_STOCK_TICK_BACK).resolve() == Path(os.environ['STOM_CLI_DB_STOCK_BACK_TICK']).resolve()\n"
        "print('NATIVE_GATE_PASS')\n"
    )


def run_gates(*, output_root: Path, output: Path) -> dict:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed_dir = output_root / f"_gate_seed_{timestamp}"
    seed_dir.mkdir(parents=True, exist_ok=False)
    for name in ("backtest.db", "optuna.db"):
        connection = sqlite3.connect(seed_dir / name)
        connection.execute("CREATE TABLE gate_seed (id INTEGER PRIMARY KEY)")
        connection.commit()
        connection.close()
    rows = []
    for tool, (module, symbol) in _TOOL_TARGETS.items():
        run_id = f"N0-{tool.value}-{timestamp}"
        spec = NativeRunSpec(
            run_id=run_id, tool=tool,
            strategy_db="_database/strategy.db", backtest_db=str(seed_dir / "backtest.db"),
            setting_db="_database/setting.db", optuna_db=str(seed_dir / "optuna.db"),
            market_db_paths=("_database/stock_tick_back.db",), output_root=str(output_root),
        )
        adapter = NativeResearchAdapter(spec)
        prepared = adapter.prepare_run()
        completed = adapter.run_subprocess([sys.executable, "-c", _probe(module, symbol)], timeout_seconds=120)
        receipt_bytes = adapter.receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        rows.append({
            "tool": tool.value, "module": module, "symbol": symbol,
            "run_id": run_id, "status": "connector_gate_pass",
            "subprocess_status": receipt["status"], "returncode": completed.returncode,
            "config_sha256": prepared["config_sha256"],
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "operational_unchanged": (
                receipt["operational_fingerprints_before"] == receipt["operational_fingerprints_after"]
                and receipt["sidefiles_before"] == receipt["sidefiles_after"]
            ),
            "stdout_tail": receipt.get("stdout_tail", ""),
        })
    report = {
        "schema": "stom.native_research.gates.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authority": "connector_isolation_only_no_research_result_no_adoption",
        "rows": rows,
        "passed": sum(row["status"] == "connector_gate_pass" and row["operational_unchanged"] for row in rows),
        "total": len(rows),
        "verdict": "NATIVE_GATES_PASS" if all(
            row["status"] == "connector_gate_pass" and row["operational_unchanged"] for row in rows
        ) else "NATIVE_GATES_FAIL",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("ai_strategy_loop/state/native_research"))
    parser.add_argument("--output", type=Path, default=Path("docs/research/quant_scoring_pipeline/evidence/2026-08-15_n0_native_gates.json"))
    args = parser.parse_args()
    report = run_gates(output_root=args.output_root, output=args.output)
    print(json.dumps({"verdict": report["verdict"], "passed": report["passed"], "total": report["total"]}, ensure_ascii=False))
    return 0 if report["verdict"] == "NATIVE_GATES_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
