"""Read-only dashboard observability payload builders."""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional


_COMPLETED_PHASES = {"generation_done", "complete"}
_LOG_LIMIT = 50


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bounded_done_units(
    *, status: str, phase: str, current_gen: int, total_units: Optional[int]
) -> Optional[int]:
    if current_gen < 0:
        return None
    done_units = current_gen
    if status == "complete" or phase in _COMPLETED_PHASES:
        done_units = current_gen + 1
    if total_units is None:
        return max(0, done_units)
    return max(0, min(done_units, total_units))


def _percent(done_units: Optional[int], total_units: Optional[int]) -> Optional[float]:
    if done_units is None or total_units is None or total_units <= 0:
        return None
    return round((float(done_units) / float(total_units)) * 100.0, 1)


def _eta(elapsed_sec: Optional[float], done_units: Optional[int], total_units: Optional[int]) -> Optional[float]:
    if elapsed_sec is None or done_units is None or total_units is None:
        return None
    if done_units <= 0 or total_units <= done_units:
        return None
    per_unit = elapsed_sec / float(done_units)
    return round(per_unit * float(total_units - done_units), 1)


def _progress_source_label(source: str) -> str:
    if source == "loop_generation":
        return "generation_level"
    if source in {"runner_counter", "engine_internal"}:
        return "engine_internal"
    if source:
        return source
    return "phase_level"


def _timeout_from_config(config: Any) -> Optional[int]:
    if config is None:
        return None
    mode = str(getattr(config, "bt_engine_mode", "") or "")
    if mode == "warm":
        timeout = _int_or_none(getattr(config, "bt_warm_run_timeout", None))
        if timeout is not None:
            return timeout
    return _int_or_none(getattr(config, "bt_timeout", None))


def build_backtest_progress(
    *,
    config: Any = None,
    latest: Mapping[str, Any],
    status: str,
    current_gen: int,
    max_generations: int,
    phase: str,
    phase_started_at: float,
    bt_timeframe: str,
    now: float,
) -> Dict[str, Any]:
    """Build an honest dashboard progress payload without fake tick counters."""
    explicit = _mapping(latest.get("backtest_progress"))
    total_units = _int_or_none(explicit.get("total_units"))
    if total_units is None and max_generations > 0:
        total_units = max_generations
    done_units = _int_or_none(explicit.get("done_units"))
    if done_units is None:
        done_units = _bounded_done_units(
            status=status, phase=phase, current_gen=current_gen, total_units=total_units
        )
    percent = _float_or_none(explicit.get("percent"))
    if percent is None:
        percent = _percent(done_units, total_units)
    elapsed_sec = _float_or_none(explicit.get("elapsed_sec"))
    if elapsed_sec is None and phase_started_at > 0.0:
        elapsed_sec = round(max(0.0, now - phase_started_at), 1)
    eta_sec = _float_or_none(explicit.get("eta_sec"))
    if eta_sec is None:
        eta_sec = _eta(elapsed_sec, done_units, total_units)

    source = str(explicit.get("source") or "")
    if not source:
        source = "loop_generation" if total_units is not None else "unavailable"
    progress_source = str(explicit.get("progress_source") or "")
    if not progress_source:
        progress_source = _progress_source_label(source)
    timeout_sec = _int_or_none(explicit.get("timeout_sec"))
    if timeout_sec is None:
        timeout_sec = _timeout_from_config(config)
    timeout_deadline_epoch = _float_or_none(explicit.get("timeout_deadline_epoch"))
    if timeout_deadline_epoch is None and timeout_sec is not None and phase_started_at > 0.0:
        timeout_deadline_epoch = round(phase_started_at + float(timeout_sec), 1)

    return {
        "source": source,
        "progress_source": progress_source,
        "phase": phase,
        "current_gen": current_gen,
        "max_generations": max_generations,
        "done_units": done_units,
        "total_units": total_units,
        "percent": percent,
        "elapsed_sec": elapsed_sec,
        "eta_sec": eta_sec,
        "timeout_sec": timeout_sec,
        "timeout_deadline_epoch": timeout_deadline_epoch,
        "timeframe": bt_timeframe,
        "message": str(latest.get("message", "") or ""),
    }


def _recent_logs(latest: Mapping[str, Any]) -> list[str]:
    raw = latest.get("recent_logs", [])
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw[-_LOG_LIMIT:]]


def build_engine_state(
    *,
    config: Any,
    latest: Mapping[str, Any],
    active_config: Mapping[str, Any],
    status: str,
    current_gen: int,
    phase: str,
) -> Dict[str, Any]:
    """Build dashboard engine settings/state without touching engine behavior."""
    explicit = _mapping(latest.get("engine_state"))
    bt_engine_mode = str(getattr(config, "bt_engine_mode", "") or "")
    bt_timeframe = str(getattr(config, "bt_timeframe", "") or "")
    bt_engine_count = _int_or_none(getattr(config, "bt_engine_count", None))
    bt_warm_engine_count = _int_or_none(getattr(config, "bt_warm_engine_count", None))
    if bt_engine_mode == "warm":
        effective_engine_count = bt_warm_engine_count
    else:
        effective_engine_count = bt_engine_count
    timeout_sec = _int_or_none(explicit.get("timeout_sec"))
    if timeout_sec is None:
        timeout_sec = _timeout_from_config(config)

    payload: Dict[str, Any] = {
        "status": status,
        "phase": phase,
        "current_gen": current_gen,
        "cpu_count": os.cpu_count() or 1,
        "bt_timeout": _int_or_none(getattr(config, "bt_timeout", None)),
        "bt_warm_run_timeout": _int_or_none(getattr(config, "bt_warm_run_timeout", None)),
        "timeout_sec": timeout_sec,
        "bt_engine_count": bt_engine_count,
        "bt_warm_engine_count": bt_warm_engine_count,
        "effective_engine_count": effective_engine_count,
        "bt_engine_mode": bt_engine_mode,
        "bt_timeframe": bt_timeframe,
        "is_tick": bt_timeframe == "tick",
        "bt_full_start": getattr(config, "bt_full_start", None),
        "bt_full_end": getattr(config, "bt_full_end", None),
        "bt_universe_start_time": getattr(config, "bt_universe_start_time", None),
        "bt_universe_end_time": getattr(config, "bt_universe_end_time", None),
        "period_start": getattr(config, "bt_full_start", None),
        "period_end": getattr(config, "bt_full_end", None),
        "start_time": getattr(config, "bt_universe_start_time", None),
        "end_time": getattr(config, "bt_universe_end_time", None),
        "buy_start_time": getattr(config, "bt_universe_start_time", None),
        "buy_end_time": getattr(config, "bt_universe_end_time", None),
        "warm_prepared": bool(explicit.get("warm_prepared", False)),
        "back_count": explicit.get("back_count"),
        "run_id": explicit.get("run_id"),
        "recent_logs": _recent_logs(latest),
        "active_config": dict(active_config),
    }
    for key, value in explicit.items():
        if key not in payload:
            payload[str(key)] = value
    return payload
