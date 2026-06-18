"""M4 운용 모니터 (2026-06-13) — V6 포트폴리오 챔피언-챌린저 월별 추적.

V6 결정(THETA+T2C3 2-전략 포트폴리오) 운용 전환용. 챔피언=포트폴리오(균등
가중 결합 일별 손익), 챌린저=시드(기존 운용 기준선). championship_report로
월별 비교 + 경보(champion_decay/challenger_dominance) 산출. 백테스트 baseline을
먼저 박고, 페이퍼/실측 일별 손익은 --extra-* 로 누적한다(운용 중 갱신).

읽기 전용(엔진 미접근, run DB의 csv_path만 사용). advisory — 자동 조치 없음.
사용: PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_m4_monitor [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from ai_strategy_loop.fitness.champion_challenger import championship_report  # noqa: E402
from ai_strategy_loop.fitness.overfit_stats import daily_pnl_series  # noqa: E402

RUNS_DB = REPO / "ai_strategy_loop" / "state" / "loop_runs.db"
OUT_DEFAULT = REPO / ".omo/evidence/tmap-walkforward/m4_monitor_baseline.json"

# 포트폴리오 구성원·시드의 train+OOS run/전략 (V6 결정 기준).
THETA = [("theta_star_reeval_20260611", "THETA_seed_902905_06_B"),
         ("theta_oos_2022_20260611", None), ("theta_oos_2026_20260611", None)]
T2C3 = [("t2c3_reeval_20260613", "T2C3_B"),
        ("t2c3_oos_2022_20260613", None), ("t2c3_oos_2026_20260613", None)]
SEED = [("theta_star_reeval_20260611", "Tick_B_902_905_Update_2"),
        ("theta_oos_2022_20260611", "Tick_B_902_905_Update_2"),
        ("theta_oos_2026_20260611", "Tick_B_902_905_Update_2")]
WEIGHTS = {"THETA": 0.5, "T2C3": 0.5}  # 균등가중(V6 — 최적화 금지).


def _csv(con: sqlite3.Connection, run: str, buy: str | None) -> str | None:
    q = ("SELECT csv_path FROM generations WHERE run_id=? AND buy_name=?"
         if buy else
         "SELECT csv_path FROM generations WHERE run_id=? AND strategy_gist='FROZEN'")
    args = (run, buy) if buy else (run,)
    r = con.execute(q, args).fetchone()
    return r[0] if r and r[0] else None


def _merged_daily(con: sqlite3.Connection, sources) -> dict:
    """run 목록의 일별 손익을 병합(창이 겹치지 않음 — 단순 합산)."""
    out: dict = {}
    for run, buy in sources:
        path = _csv(con, run, buy)
        if not path:
            continue
        for day, pnl in (daily_pnl_series(path) or {}).items():
            out[day] = out.get(day, 0.0) + float(pnl)
    return out


def _weighted_portfolio(theta: dict, t2c3: dict) -> dict:
    days = set(theta) | set(t2c3)
    return {d: WEIGHTS["THETA"] * theta.get(d, 0.0)
               + WEIGHTS["T2C3"] * t2c3.get(d, 0.0) for d in days}


def build_report(con: sqlite3.Connection, consecutive_alert: int = 2) -> dict:
    theta = _merged_daily(con, THETA)
    t2c3 = _merged_daily(con, T2C3)
    seed = _merged_daily(con, SEED)
    portfolio = _weighted_portfolio(theta, t2c3)
    rep = championship_report(portfolio, seed, consecutive_alert=consecutive_alert)
    return {
        "champion": "PORTFOLIO(THETA+T2C3 균등가중)",
        "challenger": "BASE_SEED(기존 운용)",
        "weights": WEIGHTS,
        "data_basis": "백테스트 baseline(train 2023~25 + OOS 2022·2026) — 페이퍼 실측은 추후 누적",
        "report": rep,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    ap.add_argument("--consecutive-alert", type=int, default=2)
    args = ap.parse_args()
    con = sqlite3.connect(str(RUNS_DB))
    try:
        out = build_report(con, args.consecutive_alert)
    finally:
        con.close()
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    rep = out["report"] or {}
    print(f"M4 모니터 — 챔피언 {out['champion']} vs 챌린저 {out['challenger']}")
    print(f"  챔피언 합계: {rep.get('champion_total'):,} / 챌린저 합계: {rep.get('challenger_total'):,}")
    print(f"  챔피언 최대 연속 적자월: {rep.get('max_champion_negative_streak')} / "
          f"챌린저 최대 연속 우세월: {rep.get('max_challenger_win_streak')}")
    print(f"  경보: {rep.get('alerts') or '없음'}")
    print(f"  월수: {len(rep.get('months', []))} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
