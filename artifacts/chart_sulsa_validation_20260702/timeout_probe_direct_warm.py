"""DB-write-free warm backtest probe for CSS_V7 timeout diagnosis.

# --- How to run ---
# python artifacts/chart_sulsa_validation_20260702/timeout_probe_direct_warm.py \
#   --config artifacts/chart_sulsa_validation_20260702/timeout_probe_tick_valid_micro_config.json \
#   --pairs artifacts/chart_sulsa_validation_20260702/timeout_probe_comparator_tick_pair.json \
#   --pairs artifacts/chart_sulsa_validation_20260702/timeout_probe_css_tick_pair.json \
#   --output artifacts/chart_sulsa_validation_20260702/timeout_probe_direct_warm_valid_micro_summary.json \
#   --log artifacts/chart_sulsa_validation_20260702/timeout_probe_direct_warm_valid_micro.log
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import sys
import time
from glob import glob
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from ai_strategy_loop.controller.loop import (
    _build_warm_btconfig,
    _score_outcome,
    _warm_to_outcome,
)
from ai_strategy_loop.launch_config import config_from_dict
from cli.warm_session import WarmBacktestSession


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _emit(log_path: Path, line: str) -> None:
    print(line, flush=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def _load_pairs(paths: list[Path]):
    pairs = []
    for path in paths:
        loaded = _read_json(path)
        if not isinstance(loaded, list):
            raise TypeError(f"pairs JSON must be a list: {path}")  # noqa: GENERIC_ERR_OK
        pairs.extend(loaded)
    return pairs


def _fitness_record(outcome, config):
    fit, graded, fit_err = _score_outcome(outcome, config)
    if fit is None or graded is None:
        return {"fitness_error": fit_err}
    return {
        "fitness_error": fit_err,
        "fitness": {
            "score": graded.graded,
            "gate_passed": fit.gate_passed,
            "reason": fit.reason,
            "trade_count": fit.trade_count,
            "daily_avg_trades": fit.daily_avg_trades,
            "mdd": graded.mdd,
            "profit": graded.total_profit,
            "payoff_ratio": graded.payoff_ratio,
            "give_back_rate": graded.give_back_rate,
        },
    }


def _run_pair(session: WarmBacktestSession, config, pair):
    label = pair.get("label", "")
    buy = pair["buy"]
    sell = pair["sell"]
    started = time.time()
    raw = session.run(buy, sell, timeout=config.bt_warm_run_timeout)
    elapsed = round(time.time() - started, 3)
    outcome = _warm_to_outcome(raw)
    record = {
        "label": label,
        "buy": buy,
        "sell": sell,
        "elapsed_sec": elapsed,
        "raw_status": raw.get("status") if isinstance(raw, dict) else None,
        "raw_message": raw.get("message") if isinstance(raw, dict) else None,
        "ok": bool(outcome.ok),
        "status": outcome.status,
        "reason": outcome.reason,
        "csv_path": outcome.csv_path,
        "metrics": outcome.metrics,
    }
    if outcome.ok:
        record.update(_fitness_record(outcome, config))
    return record


def run_probe(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    output_path = Path(args.output)
    log_path = Path(args.log)
    pair_paths = [Path(raw) for raw in args.pairs]
    if log_path.exists():
        log_path.unlink()

    config = config_from_dict(_read_json(config_path))
    warm = _build_warm_btconfig(config)
    pairs = _load_pairs(pair_paths)
    before_csv = set(glob("backtest/csv/*.csv"))
    summary = {
        "status": "running",
        "config_path": str(config_path),
        "warm_config": {
            "start_date": int(warm.start_date),
            "end_date": int(warm.end_date),
            "start_time": int(warm.start_time),
            "end_time": int(warm.end_time),
            "engine_count": int(warm.engine_count),
            "is_tick": bool(warm.is_tick),
            "timeout": int(warm.timeout),
            "run_timeout": int(config.bt_warm_run_timeout),
            "divid_mode": str(warm.divid_mode),
        },
        "pairs": [],
    }

    _emit(log_path, "[PROBE] prepare start")
    session = WarmBacktestSession(warm)
    try:
        started = time.time()
        prep = session.prepare()
        summary["prepare"] = {"elapsed_sec": round(time.time() - started, 3), **prep}
        _emit(
            log_path,
            "[PROBE] prepare "
            f"status={prep.get('status')} back_count={prep.get('back_count')} "
            f"elapsed={summary['prepare']['elapsed_sec']}",
        )
        if prep.get("status") != "ok":
            summary["status"] = "prepare_error"
            return 2

        for pair in pairs:
            _emit(log_path, f"[PROBE] run start label={pair.get('label')}")
            record = _run_pair(session, config, pair)
            summary["pairs"].append(record)
            _emit(
                log_path,
                "[PROBE] run done "
                f"label={record.get('label')} ok={record.get('ok')} "
                f"raw_status={record.get('raw_status')} elapsed={record.get('elapsed_sec')} "
                f"reason={record.get('reason')}",
            )
        summary["status"] = "complete"
        return 0
    finally:
        close_started = time.time()
        session.close()
        summary["close"] = {"status": "ok", "elapsed_sec": round(time.time() - close_started, 3)}
        after_csv = set(glob("backtest/csv/*.csv"))
        summary["new_csv_files"] = sorted(after_csv - before_csv)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _emit(log_path, f"[PROBE] summary={output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--pairs", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log", required=True)
    return parser.parse_args()


def main() -> int:
    multiprocessing.freeze_support()
    return run_probe(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
