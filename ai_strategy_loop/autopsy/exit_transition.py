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


def compare_official_results(
    *, baseline_job_id: str, baseline_csv: Path,
    candidate_job_id: str, candidate_csv: Path,
) -> OfficialPair:
    baseline = read_trade_rows(baseline_csv)
    candidate = read_trade_rows(candidate_csv)
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
    )
