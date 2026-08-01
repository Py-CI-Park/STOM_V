"""Single-worker background coordinator for expensive trade-path analysis."""

from __future__ import annotations

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder
from ai_strategy_loop.autopsy.trade_path_analysis import analyze_trade_paths
from ai_strategy_loop.autopsy.trade_path_analysis_models import TradePathAnalysis
from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger
from ai_strategy_loop.dashboard.trade_path_source import ResolvedTradePathSource


@dataclass(frozen=True, slots=True)
class TradePathJob:
    analysis_id: str
    status: str
    progress: float
    processed: int
    total: int
    error: str
    result: TradePathAnalysis | None


class TradePathCoordinator:
    def __init__(self, *, ledger: TradePathLedger) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trade-path")
        self._jobs: dict[str, TradePathJob] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._counterfactual: dict[str, object] = {}
        self._official_pairs: list[object] = []
        self._ledger = ledger

    def submit(
        self, *, resolved: ResolvedTradePathSource,
        decision_horizons: tuple[int, ...], continuation_horizons: tuple[int, ...],
    ) -> TradePathJob:
        analysis_id = f"tp-{uuid.uuid4().hex[:16]}"
        job = TradePathJob(analysis_id, "queued", 0.0, 0, 0, "", None)
        event = threading.Event()
        with self._lock:
            self._jobs[analysis_id] = job
            self._cancel[analysis_id] = event
        self._ledger.append(
            event="analysis_queued",
            authority="diagnostic",
            payload={
                "analysis_id": analysis_id,
                "source": asdict(resolved.source),
                "decision_horizons": list(decision_horizons),
                "continuation_horizons": list(continuation_horizons),
            },
        )
        self._executor.submit(
            self._run, analysis_id, resolved, decision_horizons,
            continuation_horizons, event,
        )
        return job

    def _run(
        self, analysis_id: str, resolved: ResolvedTradePathSource,
        decision_horizons: tuple[int, ...], continuation_horizons: tuple[int, ...],
        event: threading.Event,
    ) -> None:
        self._replace(analysis_id, status="running")
        builder = EpisodeBuilder(
            repository=MarketPathRepository(database_dir=resolved.database_dir),
            code_info_db=resolved.code_info_db,
        )

        def progress(processed: int, total: int) -> None:
            self._replace(
                analysis_id,
                processed=processed,
                total=total,
                progress=(processed / total if total else 1.0),
            )

        try:
            result = analyze_trade_paths(
                analysis_id=analysis_id,
                source=resolved.source,
                builder=builder,
                decision_horizons=decision_horizons,
                continuation_horizons=continuation_horizons,
                progress=progress,
                cancelled=event.is_set,
            )
        except RuntimeError as exc:
            status = "cancelled" if str(exc) == "analysis_cancelled" else "error"
            self._replace(analysis_id, status=status, error=str(exc))
            self._ledger.append(
                event=f"analysis_{status}", authority="diagnostic",
                payload={"analysis_id": analysis_id, "reason": str(exc)},
            )
        except (OSError, ValueError) as exc:
            self._replace(analysis_id, status="error", error=str(exc))
            self._ledger.append(
                event="analysis_error", authority="diagnostic",
                payload={"analysis_id": analysis_id, "reason": str(exc)},
            )
        else:
            self._replace(analysis_id, status="success", progress=1.0, result=result)
            self._ledger.append(
                event="analysis_success",
                authority="diagnostic",
                payload={
                    "analysis_id": analysis_id,
                    "source": asdict(result.source),
                    "summary": asdict(result.totals),
                    "exclusion_reasons": sorted({row.reason for row in result.exclusions}),
                },
            )

    def _replace(self, analysis_id: str, **changes: object) -> None:
        with self._lock:
            current = self._jobs.get(analysis_id)
            if current is not None:
                self._jobs[analysis_id] = replace(current, **changes)

    def get(self, analysis_id: str) -> TradePathJob | None:
        with self._lock:
            return self._jobs.get(analysis_id)

    def list_jobs(self) -> tuple[TradePathJob, ...]:
        with self._lock:
            return tuple(reversed(tuple(self._jobs.values())))

    def cancel(self, analysis_id: str) -> bool:
        with self._lock:
            event = self._cancel.get(analysis_id)
        if event is None:
            return False
        event.set()
        return True

    def set_counterfactual(self, analysis_id: str, payload: object) -> None:
        with self._lock:
            self._counterfactual[analysis_id] = payload
        if isinstance(payload, dict):
            outcomes = payload.get("outcomes")
            failures = payload.get("failures")
            self._ledger.append(
                event="counterfactual_completed",
                authority="advisory",
                payload={
                    "analysis_id": analysis_id,
                    "outcome_count": len(outcomes) if isinstance(outcomes, list) else 0,
                    "failure_count": len(failures) if isinstance(failures, list) else 0,
                    "total_delta_profit_krw": payload.get("total_delta_profit_krw", 0),
                    "transitions": payload.get("transitions", []),
                },
            )

    def get_counterfactual(self, analysis_id: str) -> object | None:
        with self._lock:
            return self._counterfactual.get(analysis_id)

    def add_official_pair(self, payload: object) -> None:
        with self._lock:
            self._official_pairs.insert(0, payload)
            del self._official_pairs[50:]
        if isinstance(payload, dict):
            pair = payload.get("pair")
            self._ledger.append(
                event="official_pair_compared",
                authority="official",
                payload=pair if isinstance(pair, dict) else {"available": False},
            )

    def add_proposals(self, analysis_id: str, payload: dict[str, object]) -> None:
        rows = payload.get("proposals")
        proposals = rows if isinstance(rows, list) else []
        self._ledger.append(
            event="proposals_generated",
            authority="advisory",
            payload={
                "analysis_id": analysis_id,
                "saved": False,
                "proposal_count": len(proposals),
                "proposals": proposals,
            },
        )

    def official_pairs(self) -> tuple[object, ...]:
        with self._lock:
            return tuple(self._official_pairs)

    def history_records(self, limit: int = 200) -> tuple[dict[str, object], ...]:
        return self._ledger.tail(limit)


_LEDGER_PATH = Path(
    os.environ.get("STOM_TRADE_PATH_LEDGER")
    or Path(__file__).resolve().parents[1] / "state" / "trade_path_records.jsonl"
)
_COORDINATOR = TradePathCoordinator(ledger=TradePathLedger(_LEDGER_PATH))


def trade_path_coordinator() -> TradePathCoordinator:
    return _COORDINATOR
