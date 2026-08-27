"""Read-only REST and WebSocket surface for legacy research truth."""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Final, cast

import anyio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ConfigDict, TypeAdapter, ValidationError

from ai_strategy_loop.dashboard.backtest_jobs import get_job_manager
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import (
    LegacyJobProjectionError,
    project_legacy_job_truth,
)
from ai_strategy_loop.dashboard.security import Capability, close_websocket_failure

research_truth_router = APIRouter(
    prefix="/research-truth",
    tags=["research-truth"],
)

_API_SCHEMA: Final = "stom.research_truth.api.v1"
_TERMINAL: Final = frozenset({"success", "no_trades", "error", "timeout", "cancelled"})
_JOB_ID_RE: Final = re.compile(r"^[0-9A-Za-z가-힣_.-]{1,160}$")
_JSON_OBJECT = TypeAdapter(
    dict[str, JsonValue],
    config=ConfigDict(strict=True),
)
_WS_INTERVAL_SECONDS: Final = 1.0
_SETTING_TABLES: Final = frozenset({
    "main", "stock", "coin", "sacc", "cacc", "telegram",
    "stockbuyorder", "stocksellorder", "coinbuyorder", "coinsellorder",
    "etc", "back",
})


def configured_jobs_dir() -> Path:
    override = os.environ.get("STOM_WEBBT_JOBS_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "state" / "webbt_jobs"


def _runtime_path(environment_name: str, default_name: str) -> Path:
    value = os.environ.get(environment_name)
    return Path(value) if value else Path(__file__).resolve().parents[2] / "_database" / default_name


def _setting_schema_ok(path: Path) -> bool:
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            rows = cast(
                list[tuple[str]],
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall(),
            )
            tables = {row[0] for row in rows}
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return False
    return _SETTING_TABLES.issubset(tables)


@research_truth_router.get("/runtime-authority")
def research_runtime_authority() -> dict[str, JsonValue]:
    setting = _runtime_path("STOM_CLI_DB_SETTING", "setting.db").resolve()
    return {
        "schema": "stom.research_runtime_authority.v1",
        "jobs_dir": configured_jobs_dir().resolve().as_posix(),
        "setting_db": setting.as_posix(),
        "strategy_db": _runtime_path(
            "STOM_WEBBT_JOB_STRATEGY_DB", "strategy.db"
        ).resolve().as_posix(),
        "stock_tick_db": _runtime_path(
            "STOM_CLI_DB_STOCK_BACK_TICK", "stock_tick_back.db"
        ).resolve().as_posix(),
        "setting_schema_ok": _setting_schema_ok(setting),
    }


def _base_response(job_id: str) -> dict[str, JsonValue]:
    return {
        "schema": _API_SCHEMA,
        "job_id": job_id,
        "truth_available": False,
        "truth": None,
        "persistence": "none",
    }


def _unavailable(job_id: str, reason: str) -> dict[str, JsonValue]:
    response = _base_response(job_id)
    response["reason"] = reason
    return response


def _log_size(jobs_dir: Path, job_id: str) -> int | None:
    if _JOB_ID_RE.fullmatch(job_id) is None:
        return None
    path = jobs_dir / f"{job_id}.log"
    try:
        return path.stat().st_size
    except OSError:
        return None


def _record(job_id: str) -> dict[str, JsonValue]:
    raw = get_job_manager().get(job_id, log_tail=50)
    try:
        return _JSON_OBJECT.validate_python(raw)
    except ValidationError:
        return {"available": False, "job_id": job_id}


def build_truth_payload(
    job_id: str,
    record: dict[str, JsonValue],
    jobs_dir: Path,
) -> dict[str, JsonValue]:
    if record.get("available") is not True:
        return _unavailable(job_id, "job_not_found")
    status = record.get("status")
    if not isinstance(status, str) or status not in _TERMINAL:
        response = _unavailable(job_id, "job_not_terminal")
        response["terminal"] = False
        return response
    try:
        truth = project_legacy_job_truth(
            record,
            manager_id=jobs_dir.name,
            jobs_dir=jobs_dir.as_posix(),
            log_size_bytes=_log_size(jobs_dir, job_id),
        )
    except LegacyJobProjectionError as exc:
        response = _unavailable(job_id, str(exc))
        response["terminal"] = True
        return response
    response = _base_response(job_id)
    response["truth_available"] = True
    response["truth"] = _JSON_OBJECT.validate_python(truth.model_dump(mode="json"))
    response["terminal"] = True
    return response


def current_truth_payload(job_id: str) -> dict[str, JsonValue]:
    return build_truth_payload(job_id, _record(job_id), configured_jobs_dir())


@research_truth_router.get("/job")
def research_truth_job(job_id: str) -> dict[str, JsonValue]:
    return current_truth_payload(job_id)


@research_truth_router.websocket("/ws_job")
async def research_truth_ws(websocket: WebSocket, job_id: str = "") -> None:
    security = websocket.app.state.dashboard_security
    failure = security.authorize_websocket(websocket, Capability.SAFE_BACKTEST)
    if failure is not None:
        await close_websocket_failure(websocket, failure)
        return
    await websocket.accept()
    try:
        while True:
            payload = current_truth_payload(job_id)
            await websocket.send_json(payload)
            if (
                payload.get("terminal") is True
                or payload.get("reason") == "job_not_found"
            ):
                await websocket.close()
                return
            await anyio.sleep(_WS_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
