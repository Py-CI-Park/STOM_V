"""QSP7 레인 manifest — tick/min 기준선·기간·경계의 단일 정본(P6).

값은 이 모듈(=git 이력)로 고정된다. 후보 실행 콘솔(P1)은 기간·경계를 여기서
자동 주입하며, 수기 입력 경로를 두지 않는다. 전략 해시는 요청 시점의
strategy DB 실물에서 계산해 "이름은 같은데 코드가 바뀐" 드리프트를 드러낸다.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final


_REPO_ROOT: Final = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class LanePeriod:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class LaneManifest:
    lane: str
    timeframe: str
    baseline_buy: str
    baseline_sell: str
    design: LanePeriod
    oos: LanePeriod
    session_start: int
    session_end: int
    forced_liquidation_time: int
    cost_policy: str
    decision_status: str
    notes: tuple[str, ...]


# 분할 근거: docs/research/quant_scoring_pipeline/2026-08-03_qsp7_dual_lane_validation_and_research_plan.md §2
LANE_MANIFESTS: Final[dict[str, LaneManifest]] = {
    "tick": LaneManifest(
        lane="tick",
        timeframe="tick",
        baseline_buy="ResearchTest_Tick_B_090000_092800_Wide_20260419",
        baseline_sell="ResearchTest_Tick_S_090000_092800_Wide_20260419",
        design=LanePeriod(20220401, 20240331),
        oos=LanePeriod(20240401, 20260227),
        session_start=90000,
        session_end=92800,
        forced_liquidation_time=92800,
        cost_policy="GetKiwoomPgSgSp(세0.18%+수수료0.015%×2, 왕복≈0.21%) — 수익금에 이미 반영",
        decision_status="확정(기존 QSP 연구 계열 승계)",
        notes=(
            "tick DB는 매일 09:00:00~09:30:00 구간만 존재(4년·952거래일)",
            "기존 tick control CSV(37열)는 legacy — 신규 실행은 modern 54열(P0-8 재발급)",
        ),
    ),
    "min": LaneManifest(
        lane="min",
        timeframe="min",
        baseline_buy="Min_B_Study_251227",
        baseline_sell="Min_S_Study_251227",
        design=LanePeriod(20250407, 20251128),
        oos=LanePeriod(20251201, 20260227),
        session_start=90000,
        session_end=152800,
        forced_liquidation_time=152800,
        cost_policy="GetKiwoomPgSgSp(세0.18%+수수료0.015%×2, 왕복≈0.21%) — 수익금에 이미 반영",
        decision_status="분할안 A 확정(설계 8개월/OOS 3개월) — 2026-08-03 사용자 전체 진행 지시로 확정",
        notes=(
            "min DB는 2025-04-07~2026-02-27 총 11개월(213거래일)이 전부 — OOS 3개월이 구조적 상한",
            "기존 min control(20260802_063342)은 전 기간 사용이라 OOS 자격 없음(limitation_ledger 2026-08-03)",
        ),
    ),
}


def _strategy_db_path() -> Path:
    override = os.environ.get("STOM_WEBBT_STRATEGY_DB")
    return Path(override) if override else _REPO_ROOT / "_database" / "strategy.db"


def _strategy_sha256(kind: str, name: str) -> str:
    """strategy DB 실물 코드의 SHA256. 부재·오류는 빈 문자열(fail-soft, 표시용)."""
    table = "stockbuy" if kind == "buy" else "stocksell"
    path = _strategy_db_path()
    if not path.is_file():
        return ""
    try:
        uri = f"file:{path.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute(
                f'SELECT 전략코드 FROM {table} WHERE "index" = ?', (name,)
            ).fetchone()
    except sqlite3.Error:
        return ""
    if row is None or row[0] is None:
        return ""
    return hashlib.sha256(str(row[0]).encode("utf-8")).hexdigest()


def lane_manifest_payload(lane: str) -> dict[str, object]:
    manifest = LANE_MANIFESTS.get(lane)
    if manifest is None:
        return {"available": False, "reason": "unknown_lane", "lanes": sorted(LANE_MANIFESTS)}
    buy_sha = _strategy_sha256("buy", manifest.baseline_buy)
    sell_sha = _strategy_sha256("sell", manifest.baseline_sell)
    overlap = not (
        manifest.design.end < manifest.oos.start or manifest.oos.end < manifest.design.start
    )
    return {
        "available": True,
        "authority": "official",
        "manifest": asdict(manifest),
        "baseline_buy_sha256": buy_sha,
        "baseline_sell_sha256": sell_sha,
        "baseline_registered": bool(buy_sha) and bool(sell_sha),
        "design_oos_overlap": overlap,
    }
