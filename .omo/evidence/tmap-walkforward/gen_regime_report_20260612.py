"""갭3 첫 실측 (2026-06-12) — 시장 레짐 라벨 + THETA/시드 레짐 분해 리포트.

regime_advisory 모듈(오늘 신설)의 첫 실데이터 적용. 시장 활성 지표는
moneytop 거래대금순위(초당 코드 랭킹)의 **일별 고유 종목 수(breadth)** —
활성 장은 랭킹 회전이 커서 고유 종목이 많다. 금액 컬럼이 없는 현 스키마에서
계산 가능한 가장 정직한 활성 프록시.

advisory 전용 — 판정 무관. 틱 DB는 읽기 전용(mode=ro)으로만 연다.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/gen_regime_report_20260612.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: E402
from ai_strategy_loop.fitness.regime_advisory import (  # noqa: E402
    label_regimes,
    monthly_aggregate,
    regime_breakdown,
)

EVID = Path(__file__).resolve().parent
TICK_DB = REPO / "_database/stock_tick_back.db"
RUNS_DB = REPO / "ai_strategy_loop/state/loop_runs.db"
OUT = EVID / "regime_report_20260612.json"

# THETA·시드의 train+OOS 행 — 같은 측정계(run DB csv_path)에서 일별 손익 수집.
PNL_SOURCES = {
    "THETA": [("theta_star_reeval_20260611", "THETA_seed_902905_06_B"),
              ("theta_oos_2022_20260611", "THETA_seed_902905_06_B"),
              ("theta_oos_2026_20260611", "THETA_seed_902905_06_B")],
    "SEED": [("theta_star_reeval_20260611", "Tick_B_902_905_Update_2"),
             ("theta_oos_2022_20260611", "Tick_B_902_905_Update_2"),
             ("theta_oos_2026_20260611", "Tick_B_902_905_Update_2")],
}


def daily_breadth(con: sqlite3.Connection) -> dict:
    """일별 고유 종목 수 — moneytop 전 행 1회 순회(읽기 전용)."""
    per_day: dict = {}
    cur = con.execute("SELECT [index], 거래대금순위 FROM moneytop")
    for ts, ranks in cur:
        day = str(ts)[:8]
        s = per_day.setdefault(day, set())
        if ranks:
            s.update(ranks.split(";"))
    return {day: {"breadth": float(len(codes))} for day, codes in per_day.items()}


def collect_daily_pnl(con: sqlite3.Connection, pairs) -> dict:
    """run DB에서 csv_path를 찾아 일별 손익을 병합(창이 서로 겹치지 않음)."""
    merged: dict = {}
    for run_id, buy_name in pairs:
        row = con.execute(
            "SELECT csv_path FROM generations WHERE run_id=? AND buy_name=?"
            " AND status='ok' ORDER BY gen_no LIMIT 1", (run_id, buy_name)
        ).fetchone()
        if not row or not row[0]:
            continue
        series = daily_pnl_series(row[0]) or {}
        for day, pnl in series.items():
            merged[day] = merged.get(day, 0.0) + float(pnl)
    return merged


def main() -> int:
    tick = sqlite3.connect(f"file:{TICK_DB.as_posix()}?mode=ro", uri=True)
    try:
        daily = daily_breadth(tick)
    finally:
        tick.close()
    monthly = monthly_aggregate(daily)
    regimes = label_regimes(monthly, metric="breadth")

    runs = sqlite3.connect(str(RUNS_DB))
    try:
        breakdowns = {
            name: regime_breakdown(collect_daily_pnl(runs, pairs), regimes)
            for name, pairs in PNL_SOURCES.items()
        }
    finally:
        runs.close()

    report = {
        "metric": "breadth(일별 고유 종목 수, moneytop 랭킹 회전)",
        "n_days": len(daily),
        "monthly_breadth": {m: round(v["breadth"], 1) for m, v in sorted(monthly.items())},
        "regime_by_month": dict(sorted(regimes.items())),
        "breakdowns": breakdowns,
        "note": "advisory 전용 — 판정 미사용. v0 중앙값 2분할(사전선언).",
    }
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2,
                   default=lambda o: sorted(o) if isinstance(o, set) else str(o)),
        encoding="utf-8",
    )

    n_active = sum(1 for v in regimes.values() if v == "active")
    print(f"OK days={len(daily)} months={len(regimes)} active={n_active} "
          f"contracted={len(regimes) - n_active} -> {OUT}")
    for name, b in breakdowns.items():
        print(f"  {name}: active={b.get('active')} contracted={b.get('contracted')} "
              f"concentration={b.get('concentration')} warning={b.get('warning')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
