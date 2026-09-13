"""ANA-06 — Episode/Cohort mining foundation.

거래 행 나열이 아니라 "독립 기회"를 1급 객체로 만든다:

- ``TradeFact``   : result artifact 에서 읽은 거래 사실(outcome 포함).
- ``EpisodeFact`` : 같은 candidate·symbol 의 반복 발화를 onset/reset 규칙으로
  묶은 독립 episode. outcome 필드는 Stage F projection 에서 물리적으로 제외된다.
- ``CohortCensus``/``missingness_profile``: 코호트 분산·결측 프로파일.
- ``matched_random_control`` + ``fdr_bh``: 결정론 대조군 표본과 BH-FDR.

결정론 계약: 입력 행 순서와 무관하게 동일 episode 집합이 나와야 한다
(정렬 키 = (symbol, entry_ts, trade_key)). 순차/병렬/셔플 입력 모두 동일.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence


class EpisodeMiningError(ValueError):
    """episode 입력의 typed failure — 조용한 스킵 대신 명시적 실패."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code


@dataclass(frozen=True, slots=True)
class TradeFact:
    """분석 대상 거래 사실 — outcome(pnl)은 episode 자체에는 실리지 않는다."""

    trade_key: str
    source_sha256: str
    symbol: str
    entry_ts: int
    exit_ts: int
    pnl_krw: float
    candidate: str = ""
    fold: str = ""


@dataclass(frozen=True, slots=True)
class EpisodeFact:
    """독립 episode — onset(첫 발화)과 reset(재발화 간격 초과)으로 경계 결정."""

    episode_id: str
    candidate: str
    symbol: str
    fold: str
    onset_ts: int
    reset_ts: int
    trigger_count: int
    selected_trade_key: str


def _episode_id(candidate: str, symbol: str, onset_ts: int, source: str) -> str:
    blob = f"{candidate}|{symbol}|{onset_ts}|{source}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def build_episodes(
    trades: Iterable[TradeFact],
    *,
    reset_gap_seconds: int = 86_400,
) -> tuple[EpisodeFact, ...]:
    """onset/reset 규칙으로 독립 episode를 만든다.

    - 같은 (candidate, symbol) 내에서 이전 발화와의 간격이 reset_gap_seconds
      이하면 같은 episode 의 trigger 로 누적, 초과면 새 episode onset.
    - 입력 순서 무관: (candidate, symbol, entry_ts, trade_key) 정렬 후 처리.
    - typed failure: missing symbol / exit<entry(timestamp 역전).
    """
    facts = sorted(
        trades,
        key=lambda t: (t.candidate, t.symbol, t.entry_ts, t.trade_key),
    )
    episodes: list[EpisodeFact] = []
    open_key: tuple[str, str] | None = None
    onset_ts = 0
    last_ts = 0
    first_trade_key = ""
    source_sha = ""
    count = 0

    def flush() -> None:
        nonlocal onset_ts, last_ts, first_trade_key, source_sha, count
        if open_key is None:
            return
        candidate, symbol = open_key
        episodes.append(EpisodeFact(
            episode_id=_episode_id(candidate, symbol, onset_ts, source_sha),
            candidate=candidate,
            symbol=symbol,
            fold="",
            onset_ts=onset_ts,
            reset_ts=last_ts,
            trigger_count=count,
            selected_trade_key=first_trade_key,
        ))

    for t in facts:
        if not t.symbol:
            raise EpisodeMiningError("missing_symbol", t.trade_key)
        if t.exit_ts < t.entry_ts:
            raise EpisodeMiningError("timestamp_reversal", t.trade_key)
        key = (t.candidate, t.symbol)
        if key != open_key:
            flush()
            open_key = key
            onset_ts = t.entry_ts
            last_ts = t.entry_ts
            first_trade_key = t.trade_key
            source_sha = t.source_sha256
            count = 1
        elif t.entry_ts - last_ts <= reset_gap_seconds:
            last_ts = max(last_ts, t.exit_ts)
            count += 1
        else:
            flush()
            open_key = key
            onset_ts = t.entry_ts
            last_ts = t.entry_ts
            first_trade_key = t.trade_key
            source_sha = t.source_sha256
            count = 1
    flush()
    return tuple(episodes)


# ---------------------------------------------------------------------------
# Stage F outcome-free projection — column allowlist 로 outcome 을 물리 차단.
# ---------------------------------------------------------------------------
STAGE_F_FIELDS: tuple[str, ...] = (
    "candidate", "fold", "day", "symbol", "timestamp",
    "triggered", "previous_triggered",
)
_FORBIDDEN_OUTCOME = {
    "pnl", "pnl_krw", "profit", "return", "outcome", "exit_ts",
    "selected_trade_key", "reset_ts", "trigger_count",
}


def stage_f_projection(episodes: Sequence[EpisodeFact]) -> tuple[dict[str, Any], ...]:
    """Stage F reader 전용 projection — allowlist 외 필드는 포함하지 않는다."""
    out: list[dict[str, Any]] = []
    prev_by_candidate: dict[str, int] = {}
    for ep in sorted(episodes, key=lambda e: (e.candidate, e.onset_ts, e.symbol)):
        row = {
            "candidate": ep.candidate,
            "fold": ep.fold,
            "day": ep.onset_ts // 1_000_000,
            "symbol": ep.symbol,
            "timestamp": ep.onset_ts,
            "triggered": 1,
            "previous_triggered": 1 if prev_by_candidate.get(ep.candidate) else 0,
        }
        assert not (set(row) & _FORBIDDEN_OUTCOME)
        prev_by_candidate[ep.candidate] = ep.onset_ts
        out.append(row)
    return tuple(out)


def projection_is_outcome_free(rows: Sequence[Mapping[str, Any]]) -> bool:
    """projection 결과에 금지 outcome 필드가 0개인지 검증한다."""
    return all(not (set(r) & _FORBIDDEN_OUTCOME) for r in rows)


# ---------------------------------------------------------------------------
# Missingness / cohort census / matched control / FDR
# ---------------------------------------------------------------------------
def missingness_profile(
    rows: Sequence[Mapping[str, Any]], fields: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """필드별 결측·zero-only·coverage 프로파일."""
    profile: dict[str, dict[str, Any]] = {}
    total = len(rows)
    for name in fields:
        values = [r.get(name) for r in rows]
        missing = sum(1 for v in values if v is None or v == "")
        zeros = sum(1 for v in values if v == 0 or v == 0.0)
        profile[name] = {
            "count": total,
            "missing": missing,
            "zero": zeros,
            "zero_only": bool(total) and missing + zeros == total,
            "coverage": (total - missing) / total if total else 0.0,
        }
    return profile


def cohort_census(episodes: Sequence[EpisodeFact]) -> dict[str, Any]:
    """day/symbol/candidate 분산·집중도 — cohort 편향 노출용."""
    days: dict[str, int] = {}
    symbols: dict[str, int] = {}
    candidates: dict[str, int] = {}
    for ep in episodes:
        day_key = str(ep.onset_ts // 1_000_000)
        days[day_key] = days.get(day_key, 0) + 1
        symbols[ep.symbol] = symbols.get(ep.symbol, 0) + 1
        candidates[ep.candidate] = candidates.get(ep.candidate, 0) + 1
    return {
        "n_episodes": len(episodes),
        "by_day": dict(sorted(days.items())),
        "by_symbol": dict(sorted(symbols.items())),
        "by_candidate": dict(sorted(candidates.items())),
        "max_symbol_share": (
            max(symbols.values()) / len(episodes) if episodes else 0.0
        ),
    }


def matched_random_control(
    episodes: Sequence[EpisodeFact],
    *,
    seed: int,
    n: int | None = None,
) -> dict[str, Any]:
    """결정론 대조군 표본 — seed receipt(재현 검증 근거)를 함께 돌려준다."""
    ids = sorted(ep.episode_id for ep in episodes)
    k = len(ids) if n is None else max(0, min(n, len(ids)))
    rng = random.Random(seed)
    selected = sorted(rng.sample(ids, k))
    receipt = {
        "seed": seed,
        "population": len(ids),
        "selected": k,
        "selection_sha256": hashlib.sha256(
            json.dumps(selected).encode("utf-8")
        ).hexdigest(),
    }
    return {"episode_ids": selected, "receipt": receipt}


def fdr_bh(p_values: Sequence[float]) -> list[dict[str, Any]]:
    """Benjamini–Hochberg q 값 — 발견(discovery) 가설의 다중검정 보정.

    반환: 원본 순서의 [{p, q, rank, rejected}]. q = p*m/rank 의 단조 보정.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    out = [dict(p=0.0, q=1.0, rank=0, rejected=False) for _ in range(m)]
    prev_q = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        actual_rank = m - rank + 1
        q = min(prev_q, p_values[idx] * m / actual_rank)
        prev_q = q
        out[idx] = {
            "p": p_values[idx],
            "q": q,
            "rank": actual_rank,
            "rejected": q <= 0.05,
        }
    return out


@dataclass(frozen=True, slots=True)
class Finding:
    """발견/확인 분리 계약 — role 이 discovery 면 확인 전까지 채택 근거 불가."""

    finding_id: str
    analysis_hash: str
    axis: str
    effect: float | None
    ci: tuple[float, float] | None
    q: float | None
    role: str  # discovery | confirmation
    status: str = "candidate"  # candidate | confirmed | falsified
    extra: Mapping[str, Any] = field(default_factory=dict)
