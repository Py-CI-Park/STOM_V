from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder
from ai_strategy_loop.autopsy.trade_path_analysis_models import (
    AnalysisTotals,
    TradePathAnalysis,
)
from ai_strategy_loop.autopsy.trade_path_models import RunSource, Timeframe
from ai_strategy_loop.dashboard import trade_path_jobs
from ai_strategy_loop.dashboard.research_sidecar import ResearchSidecar
from ai_strategy_loop.dashboard.trade_path_jobs import TradePathCoordinator
from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger
from ai_strategy_loop.dashboard.trade_path_source import ResolvedTradePathSource

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def _append_record(
    ledger: TradePathLedger, *, event: str, authority: str,
    payload: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    record: dict[str, JsonValue] = {
        "schema_version": "stom-trade-path-ledger-v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "authority": authority,
        "payload": payload,
    }
    ledger.path.parent.mkdir(parents=True, exist_ok=True)
    with ledger.path.open("a", encoding="utf-8", newline="\n") as handle:
        _ = handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _analysis(analysis_id: str) -> TradePathAnalysis:
    return TradePathAnalysis(
        analysis_id=analysis_id,
        source=RunSource(
            run_id="job-1",
            csv_path="result.csv",
            csv_sha256="a" * 64,
            timeframe=Timeframe.TICK,
            forced_liquidation_time=90300,
        ),
        rows=(),
        episodes=(),
        exclusions=(),
        totals=AnalysisTotals(0, 0, 0, 0, 0, 0),
        decision_horizons=(30,),
        continuation_horizons=(60,),
    )


def _resolved(tmp_path: Path) -> ResolvedTradePathSource:
    return ResolvedTradePathSource(
        source=_analysis("source").source,
        database_dir=tmp_path / "database",
        code_info_db=tmp_path / "code_info.db",
        boundary_source="job_spec_end_time",
        boundary_confidence="official",
    )


def _submit(
    coordinator: TradePathCoordinator, resolved: ResolvedTradePathSource
) -> str:
    job = coordinator.submit(
        resolved=resolved,
        decision_horizons=(30,),
        continuation_horizons=(60,),
    )
    return job.analysis_id


def _fake_analysis(
    *, analysis_id: str, source: RunSource, builder: EpisodeBuilder,
    decision_horizons: tuple[int, ...], continuation_horizons: tuple[int, ...],
    progress: Callable[[int, int], None], cancelled: Callable[[], bool],
) -> TradePathAnalysis:
    del source, builder, decision_horizons, continuation_horizons, progress, cancelled
    return _analysis(analysis_id)


def test_success_is_not_visible_until_success_ledger_append_finishes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledger = TradePathLedger(tmp_path / "ledger.jsonl")
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def append(
        *, event: str, authority: str, payload: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        if event == "analysis_success":
            started.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test barrier timed out")
        record = _append_record(
            ledger, event=event, authority=authority, payload=payload
        )
        if event == "analysis_success":
            finished.set()
        return record

    monkeypatch.setattr(ledger, "append", append)
    coordinator = TradePathCoordinator(
        ledger=ledger, sidecar=ResearchSidecar(tmp_path / "sidecar.db")
    )
    monkeypatch.setattr(
        trade_path_jobs,
        "analyze_trade_paths",
        _fake_analysis,
    )

    analysis_id = _submit(coordinator, _resolved(tmp_path))

    assert started.wait(timeout=5)
    blocked = coordinator.get(analysis_id)
    assert blocked is not None
    assert blocked.status == "running"
    assert "analysis_success" not in {
        row["event"] for row in coordinator.history_records()
    }

    release.set()
    assert finished.wait(timeout=5)
    completed = coordinator.get(analysis_id)
    assert completed is not None
    assert completed.status == "success"
    assert "analysis_success" in {
        row["event"] for row in coordinator.history_records()
    }


def test_success_ledger_failure_ends_as_error_not_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ledger = TradePathLedger(tmp_path / "ledger.jsonl")
    attempted = threading.Event()

    def append(
        *, event: str, authority: str, payload: dict[str, JsonValue]
    ) -> dict[str, JsonValue]:
        if event == "analysis_success":
            attempted.set()
            raise OSError("ledger unavailable")
        return _append_record(
            ledger, event=event, authority=authority, payload=payload
        )

    monkeypatch.setattr(ledger, "append", append)
    coordinator = TradePathCoordinator(
        ledger=ledger, sidecar=ResearchSidecar(tmp_path / "sidecar.db")
    )
    monkeypatch.setattr(
        trade_path_jobs,
        "analyze_trade_paths",
        _fake_analysis,
    )

    analysis_id = _submit(coordinator, _resolved(tmp_path))

    assert attempted.wait(timeout=5)
    failed = coordinator.get(analysis_id)
    assert failed is not None
    assert failed.status == "error"
    assert failed.error.startswith("analysis_success_ledger_failed:")
