"""Bounded offline dashboard telemetry contract.

This module is intentionally small and side-effect free: it validates and stores
only in-memory/status payload events for the AI evolution loop and the official
backtest CLI wrapper. It does not open broker, trade, Kiwoom, V3K, final approval,
or protected operating database paths.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, Iterable, List, Mapping, Optional

TELEMETRY_MAX_EVENTS = 50
TELEMETRY_MESSAGE_LIMIT = 240
TELEMETRY_ID_LIMIT = 96

TELEMETRY_EVENT_TYPES = (
    "research_start",
    "generation_start",
    "strategy_generated",
    "backtest_queued",
    "backtest_started",
    "backtest_progress",
    "backtest_done",
    "decision_recorded",
    "error",
)

TELEMETRY_SOURCE_ALLOWLIST = (
    "ai_evolution_loop",
    "official_backtest_cli",
)

OPTIONAL_TELEMETRY_KEYS = (
    "percent",
    "processed",
    "total",
    "symbol",
    "code",
)

_TELEMETRY_OUTPUT_KEYS = (
    "event_type",
    "run_id",
    "gen_no",
    "seed",
    "stage",
    "timestamp",
    "message",
    "source",
    "trace_id",
    *OPTIONAL_TELEMETRY_KEYS,
)
TELEMETRY_OUTPUT_KEYS = _TELEMETRY_OUTPUT_KEYS

# These markers define origins that must not become telemetry producers. They are
# matched against source/stage/message so accidental wiring from protected surfaces
# fails closed during tests and runtime normalization.
TELEMETRY_EXCLUDED_MARKERS = (
    "trade/",
    "trade\\",
    "trade.",
    "broker",
    "kiwoom",
    "khopenapi",
    "v3k",
    "final_approval",
    "final approval",
    "export_winner",
    "protected db",
    "_database",
    "_database_v3k_shadow",
    "strategy.db",
    "live order",
    "live_order",
)

_STAGE_EVENT_MAP = {
    "loop_start": "research_start",
    "ga_init": "research_start",
    "warm_prepare_start": "research_start",
    "generate_start": "generation_start",
    "ga_breed_start": "generation_start",
    "generate_done": "strategy_generated",
    "ga_generation_done": "strategy_generated",
    "backtest_start": "backtest_started",
    "ga_evaluate_start": "backtest_started",
    "backtest_end": "backtest_done",
    "score_done": "decision_recorded",
}


def telemetry_contract() -> Dict[str, Any]:
    """Return the closed telemetry contract exposed through dashboard status."""

    return {
        "schema_version": 1,
        "max_events": TELEMETRY_MAX_EVENTS,
        "event_types": list(TELEMETRY_EVENT_TYPES),
        "source_allowlist": list(TELEMETRY_SOURCE_ALLOWLIST),
        "required_keys": [
            "event_type",
            "run_id",
            "gen_no",
            "seed",
            "stage",
            "timestamp",
            "message",
            "source",
            "trace_id",
        ],
        "optional_keys": list(OPTIONAL_TELEMETRY_KEYS),
        "excluded_markers": list(TELEMETRY_EXCLUDED_MARKERS),
        "storage": "bounded_memory_status_ws_log_projection",
        "persistent_event_db": False,
    }


def event_type_for_stage(stage: str, *, status: str = "") -> Optional[str]:
    """Map loop/backtest phases onto the closed telemetry enum."""

    stage_value = str(stage or "")
    if status == "error" or stage_value.endswith("_error"):
        return "error"
    if stage_value in _STAGE_EVENT_MAP:
        return _STAGE_EVENT_MAP[stage_value]
    if stage_value.endswith("_start") and "backtest" in stage_value:
        return "backtest_started"
    if stage_value.endswith("_end") and "backtest" in stage_value:
        return "backtest_done"
    if stage_value.endswith("_done") and "generate" in stage_value:
        return "strategy_generated"
    return None


def _bounded_text(value: Any, *, limit: int = TELEMETRY_ID_LIMIT) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\x00", " ").replace("\r", " ").replace("\n", " ").strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _safe_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0.0:
        return 0.0
    if number > 100.0:
        return 100.0
    return round(number, 4)


def _safe_nonnegative_int(value: Any) -> Optional[int]:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, number)


def _contains_excluded_marker(*values: Any) -> bool:
    text = " ".join(str(value or "") for value in values).lower()
    return any(marker.lower() in text for marker in TELEMETRY_EXCLUDED_MARKERS)


def build_telemetry_event(
    event_type: str,
    *,
    run_id: Any = None,
    gen_no: Any = None,
    seed: Any = None,
    stage: Any = "",
    timestamp: Optional[float] = None,
    message: Any = "",
    source: str,
    trace_id: Any = None,
    percent: Any = None,
    processed: Any = None,
    total: Any = None,
    symbol: Any = None,
    code: Any = None,
) -> Dict[str, Any]:
    """Build one validated telemetry event.

    Unknown event types, non-allowlisted sources, and protected-origin markers are
    rejected instead of being silently projected into dashboard status.
    """

    if event_type not in TELEMETRY_EVENT_TYPES:
        raise ValueError(f"unknown telemetry event_type: {event_type!r}")
    if source not in TELEMETRY_SOURCE_ALLOWLIST:
        raise ValueError(f"source is not telemetry-allowlisted: {source!r}")
    if _contains_excluded_marker(source, stage, message, symbol, code, run_id, trace_id):
        raise ValueError("telemetry event references an excluded live/protected origin")

    event: Dict[str, Any] = {
        "event_type": event_type,
        "run_id": _bounded_text(run_id),
        "gen_no": _safe_int(gen_no),
        "seed": _bounded_text(seed),
        "stage": _bounded_text(stage),
        "timestamp": float(timestamp if timestamp is not None else time.time()),
        "message": _bounded_text(message, limit=TELEMETRY_MESSAGE_LIMIT),
        "source": source,
        "trace_id": _bounded_text(trace_id or uuid.uuid4().hex),
    }

    pct = _safe_float(percent)
    if pct is not None:
        event["percent"] = pct
    processed_value = _safe_nonnegative_int(processed)
    if processed_value is not None:
        event["processed"] = processed_value
    total_value = _safe_nonnegative_int(total)
    if total_value is not None:
        event["total"] = total_value
    symbol_value = _bounded_text(symbol)
    if symbol_value:
        event["symbol"] = symbol_value
    code_value = _bounded_text(code)
    if code_value:
        event["code"] = code_value

    # Closed payload: never leak arbitrary caller keys.
    return {key: event[key] for key in _TELEMETRY_OUTPUT_KEYS if key in event}


def normalize_telemetry_events(
    events: Optional[Iterable[Mapping[str, Any]]],
    *,
    max_events: int = TELEMETRY_MAX_EVENTS,
) -> List[Dict[str, Any]]:
    """Normalize a raw event list to the closed, bounded dashboard payload."""

    if not events:
        return []
    normalized: List[Dict[str, Any]] = []
    for raw in events:
        if not isinstance(raw, Mapping):
            continue
        try:
            normalized.append(build_telemetry_event(
                str(raw.get("event_type") or raw.get("event") or ""),
                run_id=raw.get("run_id"),
                gen_no=raw.get("gen_no"),
                seed=raw.get("seed"),
                stage=raw.get("stage"),
                timestamp=raw.get("timestamp"),
                message=raw.get("message"),
                source=str(raw.get("source") or ""),
                trace_id=raw.get("trace_id"),
                percent=raw.get("percent"),
                processed=raw.get("processed"),
                total=raw.get("total"),
                symbol=raw.get("symbol"),
                code=raw.get("code"),
            ))
        except (TypeError, ValueError):
            continue
    limit = max(1, min(int(max_events or TELEMETRY_MAX_EVENTS), TELEMETRY_MAX_EVENTS))
    return normalized[-limit:]


def attach_telemetry_to_status(
    payload: Dict[str, Any],
    events: Optional[Iterable[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Attach bounded telemetry events and contract metadata to a LoopState payload."""

    latest = payload.setdefault("latest", {})
    if not isinstance(latest, dict):
        latest = {}
        payload["latest"] = latest
    current = normalize_telemetry_events(latest.get("telemetry_events", []))
    extra = normalize_telemetry_events(events)
    latest["telemetry_events"] = (current + extra)[-TELEMETRY_MAX_EVENTS:]
    latest["telemetry_contract"] = telemetry_contract()
    return payload


def telemetry_log_line(event: Mapping[str, Any]) -> str:
    """Project an event into the existing bounded recent log stream."""

    event_type = str(event.get("event_type") or "unknown")
    source = str(event.get("source") or "unknown")
    stage = str(event.get("stage") or "")
    message = str(event.get("message") or "")
    run_id = str(event.get("run_id") or "")
    gen_no = event.get("gen_no", -1)
    return _bounded_text(
        f"[telemetry:{event_type}] source={source} run={run_id} gen={gen_no} stage={stage} {message}",
        limit=TELEMETRY_MESSAGE_LIMIT,
    )


class TelemetryRing:
    """Thread-safe bounded in-memory telemetry ring."""

    def __init__(self, maxlen: int = TELEMETRY_MAX_EVENTS) -> None:
        self._maxlen = max(1, min(int(maxlen or TELEMETRY_MAX_EVENTS), TELEMETRY_MAX_EVENTS))
        self._events: Deque[Dict[str, Any]] = deque(maxlen=self._maxlen)
        self._lock = threading.RLock()

    def append(self, event_type: str, **payload: Any) -> Dict[str, Any]:
        allowed = {
            "run_id", "gen_no", "seed", "stage", "timestamp", "message", "source",
            "trace_id", "percent", "processed", "total", "symbol", "code",
        }
        event = build_telemetry_event(
            event_type,
            **{key: value for key, value in payload.items() if key in allowed},
        )
        with self._lock:
            self._events.append(event)
        return event

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


_DASHBOARD_TELEMETRY = TelemetryRing()


def dashboard_telemetry() -> TelemetryRing:
    """Return the dashboard-process in-memory telemetry ring."""

    return _DASHBOARD_TELEMETRY
