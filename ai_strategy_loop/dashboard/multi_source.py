"""Shared B4-admission for multi-result surfaces (compare/overlay/portfolio).

Each compare/overlay/portfolio input is inspected once through the existing
individual-source admission; only the checked snapshot trades reach the
preserved calculators. A blocked member keeps its quality evidence but never
produces metrics, summaries, or combined curves.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from ai_strategy_loop.dashboard.individual_source import (
    AnalysisOwners,
    inspect_individual_source,
)

if TYPE_CHECKING:
    from ai_strategy_loop.dashboard.individual_source import AnalysisSource


class MemberState(StrEnum):
    READY = "ready"                    # VALID snapshot — full checked trades
    EMPTY_VERIFIED = "empty_verified"  # verified no-trades input
    BLOCKED = "blocked"                # exists but fails admission


@dataclass(frozen=True, slots=True)
class MemberAdmission:
    source: AnalysisSource
    state: MemberState
    blocked_reason: str = ""   # machine code when BLOCKED
    detail: str = ""           # human-readable reason when BLOCKED

    @property
    def admitted(self) -> bool:
        return self.state is not MemberState.BLOCKED

    def trade_dicts(self) -> list[dict[str, Any]]:
        """Checked snapshot trades in the legacy dict shape (never re-read)."""
        return [trade.model_dump() for trade in self.source.checked.trades]


def _execution_ok(source: AnalysisSource) -> bool:
    """Terminal evidence compatible with analysis — writer-ok gens stay partial."""
    if source.analysis_authority == "diagnostic_job_status":
        return source.execution_status in ("success", "no_trades")
    return source.execution_status == "partial"


def _empty_verified(source: AnalysisSource) -> bool:
    """Admit empty only with corroborating evidence — never the string alone."""
    quality = source.checked.quality
    expected = quality.expected_row_count
    if (
        quality.status == "NO_TRADES"
        and not quality.issue_codes
        and expected == 0
        and _execution_ok(source)
    ):
        return True
    # Engine-verified no-trades job without a CSV artifact: the terminal
    # classification is the execution evidence; metrics must not claim trades.
    return (
        source.analysis_authority == "diagnostic_job_status"
        and source.execution_status == "no_trades"
        and quality.status == "MISSING_ARTIFACT"
        and expected in (None, 0)
    )


def _blocked(source: AnalysisSource) -> tuple[str, str]:
    quality = source.checked.quality
    if not _execution_ok(source):
        status = source.execution_status or "unknown"
        return (
            "execution_blocked",
            f"실행 상태가 {status} 라 분석 입력으로 쓸 수 없습니다.",
        )
    if (
        source.execution_status == "no_trades"
        and quality.expected_row_count not in (None, 0)
    ):
        return (
            "no_trades_contradiction",
            "무거래 종료인데 기록된 예상 거래 수가 0이 아닙니다.",
        )
    match quality.status:
        case "MISSING_ARTIFACT":
            return "source_missing", "결과 CSV 산출물을 읽을 수 없습니다."
        case "NO_TRADES":
            return "source_empty", "무거래 근거(공식 헤더·예상 행·실행 상태)를 검증할 수 없습니다."
        case _:
            codes = ", ".join(quality.issue_codes) or quality.status
            return "source_quality_blocked", f"결과 CSV 품질 검사 실패({codes})."


def inspect_member(
    owners: AnalysisOwners,
    *,
    job_id: str = "",
    run_id: str = "",
    gen_no: int | None = None,
) -> MemberAdmission | None:
    """Resolve one compare/overlay/portfolio input through B4 admission.

    None means the selector or record itself is unresolvable — callers keep the
    legacy null/ghost semantics for that case. Everything else is explicit:
    READY (full trades), EMPTY_VERIFIED (verified no-trades), or BLOCKED with
    machine reason + human detail.
    """
    if not job_id and (not run_id or gen_no is None):
        return None
    source = inspect_individual_source(owners, job_id, run_id, gen_no)
    if not source.available:
        return None
    if source.analysis_ready:
        return MemberAdmission(source, MemberState.READY)
    if _empty_verified(source):
        return MemberAdmission(source, MemberState.EMPTY_VERIFIED)
    reason, detail = _blocked(source)
    return MemberAdmission(source, MemberState.BLOCKED, reason, detail)
