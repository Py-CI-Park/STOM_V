"""Benchmark warm backtest engine counts for process-research runs.

This script is intentionally read/execute-only with respect to STOM runtime data: it
spawns warm backtest sessions, records timing/health evidence, and writes a JSON
artifact. It does not change strategy DBs, production exports, live wiring, or loop
state.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import ai_strategy_loop.bootstrap  # noqa: F401
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.loop import _build_warm_btconfig
from cli.warm_session import WarmBacktestSession

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIN_BUY = "C_S_3_B_902_Min"
DEFAULT_MIN_SELL = "C_S_3_S_902_Min"
DEFAULT_TICK_BUY = "Tick_B_902_905_Update_2"
DEFAULT_TICK_SELL = "Tick_S_902_905_Update_2"


@dataclass(frozen=True)
class BenchmarkDecisionPolicy:
    amortized_improvement_threshold: float = 0.15
    steady_state_improvement_threshold: float = 0.20
    baseline_engine_count: int = 32
    candidate_engine_count: int = 64


@dataclass(frozen=True)
class BenchmarkArgs:
    engines: Sequence[int]
    repeat: int
    buy: str
    sell: str
    timeframe: str
    start: int
    end: int
    start_time: int
    end_time: int
    full_session: bool
    avg_time: int
    betting: str
    timeout: int
    run_timeout: int
    process: Optional[str]
    preset: str
    out: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _finite_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _percentile(values: Sequence[float], pct: float) -> Optional[float]:
    clean = sorted(v for v in (_finite_float(v) for v in values) if v is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * pct
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return clean[int(pos)]
    return clean[lo] + (clean[hi] - clean[lo]) * (pos - lo)


def _summary(values: Sequence[float]) -> Dict[str, Optional[float]]:
    clean = [v for v in (_finite_float(v) for v in values) if v is not None]
    if not clean:
        return {"min": None, "max": None, "mean": None, "median": None, "p50": None, "p95": None}
    return {
        "min": min(clean),
        "max": max(clean),
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "p50": _percentile(clean, 0.50),
        "p95": _percentile(clean, 0.95),
    }


def _safe_status(result: Dict[str, Any]) -> str:
    return str((result or {}).get("status") or "error")


def _run_success(result: Dict[str, Any]) -> bool:
    return _safe_status(result) == "success"


def _build_loop_config(args: BenchmarkArgs, engine_count: int) -> LoopConfig:
    cfg_kwargs: Dict[str, Any] = {
        "bt_timeframe": args.timeframe,
        "bt_full_start": args.start,
        "bt_full_end": args.end,
        "bt_universe_start_time": args.start_time,
        "bt_universe_end_time": args.end_time,
        "bt_min_universe_end_time": args.end_time,
        "full_session_enabled": args.full_session,
        "bt_avg_time": args.avg_time,
        "bt_betting": args.betting,
        "bt_timeout": args.timeout,
        "bt_warm_run_timeout": args.run_timeout,
        "bt_warm_engine_count": int(engine_count),
        "condition_discovery_preset": args.preset,
    }
    if args.process:
        cfg_kwargs["condition_discovery_process"] = args.process
    return LoopConfig(**cfg_kwargs)


def _input_snapshot(args: BenchmarkArgs) -> Dict[str, Any]:
    return {
        "buy": args.buy,
        "sell": args.sell,
        "timeframe": args.timeframe,
        "start": args.start,
        "end": args.end,
        "start_time": args.start_time,
        "end_time": args.end_time,
        "full_session": args.full_session,
        "avg_time": args.avg_time,
        "betting": args.betting,
        "timeout": args.timeout,
        "run_timeout": args.run_timeout,
        "repeat": args.repeat,
        "engines": list(args.engines),
        "process": args.process,
        "preset": args.preset,
    }


def run_engine_measurement(
    args: BenchmarkArgs,
    engine_count: int,
    *,
    session_cls: Any = WarmBacktestSession,
) -> Dict[str, Any]:
    loop_config = _build_loop_config(args, engine_count)
    bt_config = _build_warm_btconfig(loop_config)
    started = time.perf_counter()
    session = session_cls(bt_config)
    prepare_result: Dict[str, Any] = {}
    runs: List[Dict[str, Any]] = []
    error: Optional[str] = None

    try:
        prepare_result = session.prepare()
        if _safe_status(prepare_result) == "ok":
            for idx in range(args.repeat):
                run_result = session.run(args.buy, args.sell, timeout=args.run_timeout)
                runs.append({
                    "index": idx + 1,
                    "status": _safe_status(run_result),
                    "success": _run_success(run_result),
                    "message": run_result.get("message"),
                    "metrics": run_result.get("metrics"),
                    "csv_path": run_result.get("csv_path"),
                    "timing": run_result.get("timing", {}),
                })
        else:
            error = str(prepare_result.get("message") or "prepare failed")
    except Exception as exc:  # noqa: BLE001 - benchmark evidence should capture failure.
        error = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            session.close()
        except Exception as exc:  # noqa: BLE001 - close failure is evidence, not crash reason.
            if error:
                error += f"; close_failed={type(exc).__name__}: {exc}"
            else:
                error = f"close_failed={type(exc).__name__}: {exc}"

    prepare_timing = prepare_result.get("timing", {}) if isinstance(prepare_result, dict) else {}
    run_elapsed = [r.get("timing", {}).get("run_elapsed") for r in runs]
    success_count = sum(1 for r in runs if r.get("success"))
    timeout_count = sum(1 for r in runs if r.get("timing", {}).get("timeout"))
    recovery_attempts = sum(int(r.get("timing", {}).get("recovery_attempts") or 0) for r in runs)
    prepare_elapsed = _finite_float(prepare_timing.get("prepare_elapsed"))
    run_stats = _summary([v for v in run_elapsed if _finite_float(v) is not None])
    amortized_total_p50 = None
    if prepare_elapsed is not None and run_stats["p50"] is not None and args.repeat > 0:
        amortized_total_p50 = (prepare_elapsed / args.repeat) + run_stats["p50"]

    return {
        "engine_count": int(engine_count),
        "status": "ok" if error is None and _safe_status(prepare_result) == "ok" else "error",
        "error": error,
        "elapsed_wall_sec": max(0.0, time.perf_counter() - started),
        "config": {
            "start_date": bt_config.start_date,
            "end_date": bt_config.end_date,
            "start_time": bt_config.start_time,
            "end_time": bt_config.end_time,
            "avg_time": bt_config.avg_time,
            "engine_count": bt_config.engine_count,
            "is_tick": bt_config.is_tick,
            "betting": bt_config.betting,
            "divid_mode": bt_config.divid_mode,
            "timeout": bt_config.timeout,
        },
        "prepare": {
            "status": _safe_status(prepare_result),
            "message": prepare_result.get("message") if isinstance(prepare_result, dict) else None,
            "back_count": prepare_result.get("back_count") if isinstance(prepare_result, dict) else None,
            "timing": prepare_timing,
        },
        "runs": runs,
        "summary": {
            "repeat_requested": int(args.repeat),
            "repeat_completed": len(runs),
            "success_count": success_count,
            "success_rate": success_count / max(1, int(args.repeat)),
            "timeout_count": timeout_count,
            "recovery_attempts": recovery_attempts,
            "prepare_elapsed_sec": prepare_elapsed,
            "run_elapsed_sec": run_stats,
            "amortized_total_p50_sec": amortized_total_p50,
        },
    }


def _improvement(baseline: Optional[float], candidate: Optional[float]) -> Optional[float]:
    if baseline is None or candidate is None or baseline <= 0:
        return None
    return (baseline - candidate) / baseline


def decide_engine_count(
    measurements: Sequence[Dict[str, Any]],
    policy: BenchmarkDecisionPolicy = BenchmarkDecisionPolicy(),
) -> Dict[str, Any]:
    by_engine = {int(m.get("engine_count")): m for m in measurements}
    baseline = by_engine.get(policy.baseline_engine_count)
    candidate = by_engine.get(policy.candidate_engine_count)
    if baseline is None or candidate is None:
        return {
            "selected_engine_count": policy.baseline_engine_count,
            "changed_default": False,
            "reason": "baseline_or_candidate_missing",
            "policy": asdict(policy),
            "comparisons": {},
        }

    base_summary = baseline.get("summary", {})
    cand_summary = candidate.get("summary", {})
    comparisons = {
        "amortized_total_p50_improvement": _improvement(
            base_summary.get("amortized_total_p50_sec"),
            cand_summary.get("amortized_total_p50_sec"),
        ),
        "run_p50_improvement": _improvement(
            base_summary.get("run_elapsed_sec", {}).get("p50"),
            cand_summary.get("run_elapsed_sec", {}).get("p50"),
        ),
        "run_p95_improvement": _improvement(
            base_summary.get("run_elapsed_sec", {}).get("p95"),
            cand_summary.get("run_elapsed_sec", {}).get("p95"),
        ),
        "success_rate_delta": (cand_summary.get("success_rate") or 0.0) - (base_summary.get("success_rate") or 0.0),
        "timeout_delta": int(cand_summary.get("timeout_count") or 0) - int(base_summary.get("timeout_count") or 0),
        "recovery_attempt_delta": int(cand_summary.get("recovery_attempts") or 0) - int(base_summary.get("recovery_attempts") or 0),
    }
    base_success_rate = float(base_summary.get("success_rate") or 0.0)
    cand_success_rate = float(cand_summary.get("success_rate") or 0.0)
    if base_success_rate <= 0.0 or cand_success_rate <= 0.0:
        return {
            "selected_engine_count": policy.baseline_engine_count,
            "changed_default": False,
            "reason": "no_successful_baseline_or_candidate_runs",
            "policy": asdict(policy),
            "comparisons": comparisons,
        }
    stable = (
        candidate.get("status") == "ok"
        and comparisons["success_rate_delta"] >= 0
        and comparisons["timeout_delta"] <= 0
        and comparisons["recovery_attempt_delta"] <= 0
    )
    amortized_pass = (
        comparisons["amortized_total_p50_improvement"] is not None
        and comparisons["amortized_total_p50_improvement"] >= policy.amortized_improvement_threshold
    )
    steady_pass = (
        comparisons["run_p50_improvement"] is not None
        and comparisons["run_p95_improvement"] is not None
        and comparisons["run_p50_improvement"] >= policy.steady_state_improvement_threshold
        and comparisons["run_p95_improvement"] >= policy.steady_state_improvement_threshold
    )
    use_candidate = bool(stable and (amortized_pass or steady_pass))
    selected = policy.candidate_engine_count if use_candidate else policy.baseline_engine_count
    if use_candidate:
        reason = "candidate_passed_threshold_without_stability_regression"
    elif not stable:
        reason = "candidate_stability_regression_or_failure"
    else:
        reason = "candidate_did_not_meet_improvement_threshold"
    return {
        "selected_engine_count": selected,
        "changed_default": selected != policy.baseline_engine_count,
        "reason": reason,
        "policy": asdict(policy),
        "comparisons": comparisons,
    }


def build_artifact(args: BenchmarkArgs, measurements: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    decision = decide_engine_count(measurements)
    return {
        "schemaVersion": 1,
        "kind": "process-research-engine-benchmark",
        "createdAt": _utc_now(),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "cpu_count": os.cpu_count(),
        },
        "inputSet": _input_snapshot(args),
        "decision": decision,
        "measurements": list(measurements),
    }


def _normalize_engines(raw: Any) -> List[int]:
    if isinstance(raw, str):
        parts = raw.replace(",", " ").split()
    else:
        parts = []
        for item in raw or []:
            parts.extend(str(item).replace(",", " ").split())
    engines = [int(part.strip()) for part in parts if part.strip()]
    if not engines:
        raise argparse.ArgumentTypeError("at least one engine count is required")
    if any(e <= 0 for e in engines):
        raise argparse.ArgumentTypeError("engine counts must be positive")
    return engines


def parse_args(argv: Optional[Sequence[str]] = None) -> BenchmarkArgs:
    defaults = LoopConfig()
    parser = argparse.ArgumentParser(description="Benchmark warm backtest engine counts for process research.")
    parser.add_argument("--engines", default=["32", "64"], nargs="+")
    parser.add_argument("--repeat", default=3, type=int)
    parser.add_argument("--buy", default=None)
    parser.add_argument("--sell", default=None)
    parser.add_argument("--timeframe", choices=["min", "tick"], default=defaults.bt_timeframe)
    parser.add_argument("--start", default=defaults.bt_full_start, type=int)
    parser.add_argument("--end", default=defaults.bt_full_end, type=int)
    parser.add_argument("--start-time", default=defaults.bt_universe_start_time, type=int)
    parser.add_argument("--end-time", default=defaults.bt_universe_end_time, type=int)
    parser.add_argument("--full-session", action="store_true")
    parser.add_argument("--avg-time", default=defaults.bt_avg_time, type=int)
    parser.add_argument("--betting", default=defaults.bt_betting)
    parser.add_argument("--timeout", default=max(defaults.bt_timeout, 600), type=int)
    parser.add_argument("--run-timeout", default=defaults.bt_warm_run_timeout, type=int)
    parser.add_argument("--process", default=None)
    parser.add_argument("--preset", default=defaults.condition_discovery_preset)
    parser.add_argument("--out", default="artifacts/process-research-engine-benchmark.json", type=Path)
    ns = parser.parse_args(argv)
    ns.engines = _normalize_engines(ns.engines)
    if ns.repeat <= 0:
        parser.error("--repeat must be positive")
    if ns.timeframe == "tick":
        buy = ns.buy or DEFAULT_TICK_BUY
        sell = ns.sell or DEFAULT_TICK_SELL
    else:
        buy = ns.buy or DEFAULT_MIN_BUY
        sell = ns.sell or DEFAULT_MIN_SELL
    return BenchmarkArgs(
        engines=ns.engines,
        repeat=int(ns.repeat),
        buy=buy,
        sell=sell,
        timeframe=ns.timeframe,
        start=int(ns.start),
        end=int(ns.end),
        start_time=int(ns.start_time),
        end_time=int(ns.end_time),
        full_session=bool(ns.full_session),
        avg_time=int(ns.avg_time),
        betting=str(ns.betting),
        timeout=int(ns.timeout),
        run_timeout=int(ns.run_timeout),
        process=ns.process,
        preset=str(ns.preset),
        out=ns.out,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    measurements = [run_engine_measurement(args, engine) for engine in args.engines]
    artifact = build_artifact(args, measurements)
    out_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "path": str(out_path),
        "selected_engine_count": artifact["decision"]["selected_engine_count"],
        "reason": artifact["decision"]["reason"],
    }, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
