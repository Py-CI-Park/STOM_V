"""GUI parity analysis payload for an evolution-loop generation."""

from __future__ import annotations

import glob
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from ai_strategy_loop.controller import state as state_paths
from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.dashboard import backtest_analysis as analysis

REPO_ROOT = Path(__file__).resolve().parents[2]


def _empty_gui_parity() -> Dict[str, Any]:
    return analysis.full_analysis(None)["gui_parity"]


def _empty_payload(run_id: str, gen_no: int, reason: str) -> Dict[str, Any]:
    return {
        "available": False,
        "reason": reason,
        "run_id": run_id,
        "gen_no": int(gen_no),
        "csv_path_found": False,
        "gate_passed": False,
        "buy_name": None,
        "sell_name": None,
        "summary": analysis.full_analysis(None)["summary"],
        "gui_parity": _empty_gui_parity(),
    }


def _csv_by_buy_name(buy_name: Optional[str]) -> Optional[Path]:
    if not buy_name:
        return None
    files = glob.glob(str(REPO_ROOT / "backtest" / "csv" / f"stock_bt_{buy_name}_*.csv"))
    if not files:
        return None
    try:
        return Path(max(files, key=os.path.getmtime))
    except OSError:
        return None


def _resolve_csv(csv_path: Optional[str], buy_name: Optional[str]) -> Optional[Path]:
    candidate: Optional[Path] = None
    if csv_path:
        path = Path(csv_path)
        candidate = path if path.is_absolute() else REPO_ROOT / path
    if candidate is not None and candidate.is_file():
        return candidate
    fallback = _csv_by_buy_name(buy_name)
    if fallback is not None and fallback.is_file():
        return fallback
    return None


def evolution_gui_parity_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """Return GUI-parity chart data for one stored evolution generation."""
    if not run_id or gen_no < 0:
        return _empty_payload(run_id, gen_no, "invalid_request")

    found = False
    csv_path: Optional[str] = None
    buy_name: Optional[str] = None
    sell_name: Optional[str] = None
    gate_passed = False
    if not Path(state_paths.LOOP_RUNS_DB).is_file():
        return _empty_payload(run_id, gen_no, "missing_generation")
    try:
        state = LoopState(readonly=True)
        try:
            for row in state.get_generations(run_id):
                if int(row.get("gen_no", -1)) != int(gen_no):
                    continue
                found = True
                csv_path = row.get("csv_path")
                buy_name = row.get("buy_name")
                sell_name = row.get("sell_name")
                gate_passed = bool(row.get("gate_passed"))
                break
        finally:
            state.close()
    except (OSError, sqlite3.Error):
        return _empty_payload(run_id, gen_no, "state_unavailable")

    if not found:
        return _empty_payload(run_id, gen_no, "missing_generation")

    resolved = _resolve_csv(csv_path, buy_name)
    if resolved is None:
        payload = _empty_payload(run_id, gen_no, "missing_csv")
        payload.update(
            {
                "available": True,
                "gate_passed": gate_passed,
                "buy_name": buy_name,
                "sell_name": sell_name,
            }
        )
        return payload

    full = analysis.full_analysis(str(resolved))
    return {
        "available": True,
        "reason": "ok",
        "run_id": run_id,
        "gen_no": int(gen_no),
        "csv_path_found": True,
        "gate_passed": gate_passed,
        "buy_name": buy_name,
        "sell_name": sell_name,
        "summary": full.get("summary", analysis.full_analysis(None)["summary"]),
        "gui_parity": full.get("gui_parity", _empty_gui_parity()),
    }
