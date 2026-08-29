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
from ai_strategy_loop.dashboard.research_sidecar import ResearchSidecar
from ai_strategy_loop.dashboard.trade_path_ledger import TradePathLedger
from ai_strategy_loop.dashboard.trade_path_source import ResolvedTradePathSource

# P4 — 메모리에 유지하는 완료 분석 결과 상한. 초과분은 결과만 비우고
#   sidecar 에서 투명 복원한다(get 이 자동 재적재).
_MAX_RESULTS_IN_MEMORY = 8


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
    def __init__(
        self, *, ledger: TradePathLedger, sidecar: ResearchSidecar | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trade-path")
        self._sidecar = sidecar or ResearchSidecar()
        self._jobs: dict[str, TradePathJob] = {}
        self._cancel: dict[str, threading.Event] = {}
        self._counterfactual: dict[str, object] = {}
        self._official_pairs: list[object] = []
        self._candidate_runs: list[dict[str, object]] = []
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
            try:
                self._sidecar.ingest_analysis(result)
            except (OSError, ValueError) as exc:  # 저장 실패는 분석 성공을 되돌리지 않는다.
                self._ledger.append(
                    event="sidecar_ingest_failed", authority="diagnostic",
                    payload={"analysis_id": analysis_id, "reason": str(exc)},
                )
            self._evict_over_cap(keep=analysis_id)
            try:
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
            except OSError as exc:
                self._replace(analysis_id, status="error", progress=1.0, error=f"analysis_success_ledger_failed: {exc}", result=result)
                return
            self._replace(analysis_id, status="success", progress=1.0, result=result)

    def _replace(self, analysis_id: str, **changes: object) -> None:
        with self._lock:
            current = self._jobs.get(analysis_id)
            if current is not None:
                self._jobs[analysis_id] = replace(current, **changes)

    def _evict_over_cap(self, *, keep: str) -> None:
        """완료 결과가 상한을 넘으면 오래된 것부터 결과만 비운다(sidecar 복원 전제)."""
        with self._lock:
            loaded = [
                analysis_id for analysis_id, job in self._jobs.items()
                if job.result is not None and analysis_id != keep
            ]
            for analysis_id in loaded[: max(0, len(loaded) - (_MAX_RESULTS_IN_MEMORY - 1))]:
                self._jobs[analysis_id] = replace(self._jobs[analysis_id], result=None)

    def get(self, analysis_id: str) -> TradePathJob | None:
        with self._lock:
            job = self._jobs.get(analysis_id)
        if job is not None and (job.status != "success" or job.result is not None):
            return job
        # P4 — 재시작·상한 축출 후에도 sidecar 에서 투명 복원한다.
        try:
            restored = self._sidecar.load_analysis(analysis_id)
        except (OSError, ValueError):
            restored = None
        if restored is None:
            return job
        revived = TradePathJob(
            analysis_id, "success",
            1.0, restored.totals.trade_count, restored.totals.trade_count, "", restored,
        )
        with self._lock:
            self._jobs[analysis_id] = revived
        self._evict_over_cap(keep=analysis_id)
        return revived

    def sidecar(self) -> ResearchSidecar:
        return self._sidecar

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

    def add_candidate_run(self, payload: dict[str, object]) -> dict[str, object]:
        """후보↔공식 job 귀속(P1-4). pair/OOS 게이트가 드롭다운 수기 선택 대신 사용한다."""
        record = dict(payload)
        with self._lock:
            self._candidate_runs.insert(0, record)
            del self._candidate_runs[200:]
        self._ledger.append(
            event="candidate_run_attributed",
            authority="official",
            payload=record,
        )
        return record

    def candidate_runs(self, lane: str = "") -> tuple[dict[str, object], ...]:
        with self._lock:
            rows = tuple(self._candidate_runs)
        if not lane:
            return rows
        return tuple(row for row in rows if row.get("lane") == lane)

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
