"""Official baseline/candidate result matching and exit-reason transitions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ai_strategy_loop.autopsy.trade_episode import read_trade_rows


@dataclass(frozen=True, slots=True)
class ExitTransition:
    baseline_reason: str
    candidate_reason: str
    count: int
    delta_profit_krw: int


@dataclass(frozen=True, slots=True)
class OfficialPair:
    baseline_job_id: str
    candidate_job_id: str
    matched_count: int
    baseline_only_count: int
    candidate_only_count: int
    baseline_profit_krw: int
    candidate_profit_krw: int
    delta_profit_krw: int
    transitions: tuple[ExitTransition, ...]
    authority: str = "official"
    # R2-1 — 축(axis)에 따라 같은 숫자를 다르게 읽는다.
    #   sell: 진입 고정이므로 matched 가 곧 전량, only 는 이상신호.
    #   buy : 진입이 바뀌는 것이 정상이므로 baseline_only = 필터로 제거된 진입,
    #         candidate_only = 새로 생긴 진입. 판정은 총손익뿐 아니라
    #         건당 엣지(delta_per_trade_krw)를 함께 본다(QSP3 교훈: 거래 축소만으로도
    #         총손익은 개선되지만 건당 엣지는 나빠질 수 있다).
    axis: str = "sell"
    baseline_trade_count: int = 0
    candidate_trade_count: int = 0
    baseline_per_trade_krw: float = 0.0
    candidate_per_trade_krw: float = 0.0
    delta_per_trade_krw: float = 0.0


def _buy_date(buy_time: int) -> int:
    """매수시간 앞 8자리 = 거래일. tick(14자리)/min(12자리) 모두 같은 규칙."""
    return int(str(int(buy_time))[:8])


def _within(rows, period: tuple[int, int] | None):
    """평가 프로토콜 v2 — 연속 1회 런 CSV 를 매수일 기준으로 자른다(양끝 포함)."""
    if period is None:
        return list(rows)
    start, end = period
    return [row for row in rows if start <= _buy_date(row.buy_time) <= end]


def compare_official_results(
    *, baseline_job_id: str, baseline_csv: Path,
    candidate_job_id: str, candidate_csv: Path, axis: str = "sell",
    period: tuple[int, int] | None = None,
) -> OfficialPair:
    baseline = _within(read_trade_rows(baseline_csv), period)
    candidate = _within(read_trade_rows(candidate_csv), period)
    baseline_map = {(row.name, row.buy_time, row.entry_sequence): row for row in baseline}
    candidate_map = {(row.name, row.buy_time, row.entry_sequence): row for row in candidate}
    shared = sorted(set(baseline_map) & set(candidate_map))
    counts: Counter[tuple[str, str]] = Counter()
    deltas: Counter[tuple[str, str]] = Counter()
    for key in shared:
        left, right = baseline_map[key], candidate_map[key]
        pair = (left.exit_reason or "미분류", right.exit_reason or "미분류")
        counts[pair] += 1
        deltas[pair] += right.profit_krw - left.profit_krw
    transitions = tuple(
        ExitTransition(left, right, count, deltas[(left, right)])
        for (left, right), count in sorted(counts.items())
    )
    baseline_profit = sum(row.profit_krw for row in baseline)
    candidate_profit = sum(row.profit_krw for row in candidate)
    baseline_per_trade = baseline_profit / len(baseline) if baseline else 0.0
    candidate_per_trade = candidate_profit / len(candidate) if candidate else 0.0
    return OfficialPair(
        baseline_job_id=baseline_job_id,
        candidate_job_id=candidate_job_id,
        matched_count=len(shared),
        baseline_only_count=len(set(baseline_map) - set(candidate_map)),
        candidate_only_count=len(set(candidate_map) - set(baseline_map)),
        baseline_profit_krw=baseline_profit,
        candidate_profit_krw=candidate_profit,
        delta_profit_krw=candidate_profit - baseline_profit,
        transitions=transitions,
        axis=axis,
        baseline_trade_count=len(baseline),
        candidate_trade_count=len(candidate),
        baseline_per_trade_krw=round(baseline_per_trade, 2),
        candidate_per_trade_krw=round(candidate_per_trade, 2),
        delta_per_trade_krw=round(candidate_per_trade - baseline_per_trade, 2),
    )
