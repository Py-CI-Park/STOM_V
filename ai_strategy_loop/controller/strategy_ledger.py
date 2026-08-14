"""조건식 성과 원장 — 후보 하나하나의 **엔진 실측**을 영구 기록한다.

## 왜 필요한가

지금까지 후보 성과는 세션 로그와 JSON 파일에 흩어져 있었다. 그래서
"지금까지 만든 후보 중 뭐가 제일 좋았나"에 답하려면 매번 파일을 뒤져야 했고,
같은 후보를 두 번 재는 일도 생겼다. 원장이 없으면 **누적이 안 된다.**

## 설계 원칙

1. **append-only.** 기록을 고치지 않는다. 판정이 바뀌면 새 행을 쌓는다
   (폐기된 후보도 남아야 "이건 이미 해 봤다"를 알 수 있다).
2. **별도 DB.** `_database/strategy_ledger.db` 를 쓴다. 운영 DB(`strategy.db`,
   `backtest.db`)를 건드리지 않는다 — 연구 기록이 운영 자산을 오염시키면 안 된다.
3. **엔진 실측만 적는다.** 지도 추정치는 참고 열(`map_expectancy_pct`)로만 두고,
   판정 열은 전부 엔진에서 온다.
4. **자본을 함께 적는다.** 총수익금만 적으면 자본을 더 쓴 후보가 항상 이긴다.
5. **불확실성을 적는다.** 짝지은 신뢰구간·필요 표본을 함께 적어야 "확정"과
   "아직 모름"을 구분할 수 있다.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any, Final

_DEFAULT_DB: Final = os.path.join(
    os.path.dirname(__file__), "..", "..", "_database", "strategy_ledger.db")

#: 원장 스키마 버전 — 열이 늘면 올린다(기존 행은 그대로 둔다).
SCHEMA_VERSION: Final = 1

#: 판정 세 갈래. 절대 기준이 아니라 **챔피언 대비**로 매긴다.
VERDICTS: Final = ("PASS", "PROMISING", "MIXED", "REJECT", "BASELINE")

_DDL: Final = """
CREATE TABLE IF NOT EXISTS candidates (
    row_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version      INTEGER NOT NULL,
    recorded_at         TEXT    NOT NULL,
    candidate_id        TEXT    NOT NULL,
    family              TEXT    NOT NULL,   -- entry | exit | pair
    source              TEXT    NOT NULL,   -- human | ai | optimizer
    lane                TEXT    NOT NULL,
    buy_name            TEXT,
    sell_name           TEXT,
    period_start        INTEGER,
    period_end          INTEGER,
    job_id              TEXT,
    result_table        TEXT,
    -- 엔진 실측 (판정 근거)
    trades              INTEGER,
    win_rate            REAL,
    avg_profit_pct      REAL,
    total_profit_krw    REAL,
    seed_capital        REAL,
    total_profit_pct    REAL,
    cagr                REAL,
    mdd_pct             REAL,
    tpi                 REAL,
    avg_hold_sec        REAL,
    max_hold_count      INTEGER,
    -- 챔피언 대비 (짝지은 비교)
    baseline_id         TEXT,
    paired_pairs        INTEGER,
    paired_mean_diff_pct REAL,
    paired_ci_low       REAL,
    paired_ci_high      REAL,
    paired_significant  INTEGER,
    paired_required     REAL,
    regime_positive     INTEGER,
    regime_baseline     INTEGER,
    -- 참고 (판정 근거 아님)
    map_expectancy_pct  REAL,
    transfer_ratio      REAL,
    -- 판정
    verdict             TEXT    NOT NULL,
    verdict_reason      TEXT,
    notes               TEXT
);
CREATE INDEX IF NOT EXISTS idx_candidate ON candidates(candidate_id);
CREATE INDEX IF NOT EXISTS idx_verdict   ON candidates(verdict);
"""


@dataclass
class CandidateRecord:
    """원장 한 행. 엔진 실측이 없는 후보는 원장에 들어오지 않는다."""

    candidate_id: str
    family: str
    source: str
    lane: str
    verdict: str
    recorded_at: str
    buy_name: str | None = None
    sell_name: str | None = None
    period_start: int | None = None
    period_end: int | None = None
    job_id: str | None = None
    result_table: str | None = None
    trades: int | None = None
    win_rate: float | None = None
    avg_profit_pct: float | None = None
    total_profit_krw: float | None = None
    seed_capital: float | None = None
    total_profit_pct: float | None = None
    cagr: float | None = None
    mdd_pct: float | None = None
    tpi: float | None = None
    avg_hold_sec: float | None = None
    max_hold_count: int | None = None
    baseline_id: str | None = None
    paired_pairs: int | None = None
    paired_mean_diff_pct: float | None = None
    paired_ci_low: float | None = None
    paired_ci_high: float | None = None
    paired_significant: bool | None = None
    paired_required: float | None = None
    regime_positive: int | None = None
    regime_baseline: int | None = None
    map_expectancy_pct: float | None = None
    transfer_ratio: float | None = None
    verdict_reason: str | None = None
    notes: str | None = None
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"알 수 없는 판정: {self.verdict} (가능: {VERDICTS})")
        if self.family not in ("entry", "exit", "pair"):
            raise ValueError(f"알 수 없는 계열: {self.family}")


def _path(db_path: str | None) -> str:
    return os.path.abspath(db_path or _DEFAULT_DB)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(_path(db_path))
    con.row_factory = sqlite3.Row
    con.executescript(_DDL)
    return con


def append(record: CandidateRecord, *, db_path: str | None = None) -> int:
    """행 하나를 쌓는다. **덮어쓰지 않는다** — 같은 후보를 다시 재면 새 행이다."""
    payload = asdict(record)
    payload.pop("extra", None)
    payload["schema_version"] = SCHEMA_VERSION
    if payload.get("paired_significant") is not None:
        payload["paired_significant"] = int(bool(payload["paired_significant"]))
    columns = ", ".join(payload)
    holes = ", ".join("?" for _ in payload)
    con = connect(db_path)
    try:
        cur = con.execute(f"INSERT INTO candidates ({columns}) VALUES ({holes})",
                          tuple(payload.values()))
        con.commit()
        return int(cur.lastrowid)
    finally:
        con.close()


def read_all(*, db_path: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    """최근 기록부터. 없으면 빈 목록(원장을 지어내지 않는다)."""
    try:
        con = connect(db_path)
    except sqlite3.Error:
        return []
    try:
        rows = con.execute(
            "SELECT * FROM candidates ORDER BY row_id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def latest_per_candidate(*, db_path: str | None = None) -> list[dict[str, Any]]:
    """후보마다 **가장 최근** 기록 하나씩 — 화면 기본 보기.

    과거 기록은 남아 있다(append-only). 여기서는 최신만 골라 보여준다.
    """
    rows = read_all(db_path=db_path, limit=5000)
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:                       # 이미 최신순이라 첫 등장이 최신이다
        seen.setdefault(str(row["candidate_id"]), row)
    return list(seen.values())


def summary(*, db_path: str | None = None) -> dict[str, Any]:
    """원장 한 장 요약 — 무엇이 확정이고 무엇이 아직인가."""
    latest = latest_per_candidate(db_path=db_path)
    counts: dict[str, int] = {v: 0 for v in VERDICTS}
    for row in latest:
        counts[str(row["verdict"])] = counts.get(str(row["verdict"]), 0) + 1

    graded = [r for r in latest if r["verdict"] != "BASELINE"
              and r["avg_profit_pct"] is not None]
    best = max(graded, key=lambda r: r["avg_profit_pct"], default=None)
    baseline = next((r for r in latest if r["verdict"] == "BASELINE"), None)

    return {
        "available": bool(latest),
        "authority": "official",          # 엔진 실측만 들어온다
        "candidates": len(latest),
        "records": len(read_all(db_path=db_path, limit=5000)),
        "verdicts": counts,
        "baseline": baseline,
        "best_by_avg_profit": best,
        # 확정된 승격 후보가 하나도 없다는 사실 자체가 중요한 정보다.
        "promoted": counts.get("PASS", 0),
        "note": ("판정은 챔피언 대비다. PROMISING 은 합격이 아니라 "
                 "'방향은 맞는데 표본이 얇다'는 뜻이다."),
    }
