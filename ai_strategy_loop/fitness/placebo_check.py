"""C1 (2026-06-11) — V2 플라시보 검정: 후보의 분포 내 위치 자동 산출 (advisory).

플라시보 = 후보와 같은 매도식 + 무작위 진입(gen_placebo_strategy). 후보의
초과 성과가 "진입 신호" 덕인지 검정하는 대조군이다. 결정 카드의 의무 필드
(N10)로 들어가며, 어떤 판정도 바꾸지 않는다.

해석 규칙(사전선언): 후보 손익이 플라시보 전 표본을 상회하고(exceeds_all)
플라시보 중앙값이 음수이면 "진입 신호가 손익의 원천"으로 기록한다.
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional, Sequence


def placebo_profits_from_run(
    run_id: str, db_path: str, gist_prefix: str = "PLACEBO"
) -> List[Dict[str, float]]:
    """플라시보 배치 run에서 (라벨, 손익, 거래수) 목록을 읽는다. 실패는 빈 리스트."""
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT strategy_gist, profit, trade_count FROM generations"
                " WHERE run_id=? AND status='ok' AND strategy_gist LIKE ?"
                " ORDER BY gen_no",
                (run_id, f"{gist_prefix}%"),
            ).fetchall()
        finally:
            con.close()
        return [
            {"label": r["strategy_gist"], "profit": float(r["profit"] or 0.0),
             "trades": int(r["trade_count"] or 0)}
            for r in rows
        ]
    except Exception:  # noqa: BLE001 - advisory.
        return []


def placebo_position(
    candidate_profit: float, placebo_profits: Sequence[float]
) -> Optional[Dict[str, object]]:
    """후보 손익의 플라시보 분포 내 위치. 표본 3개 미만이면 None."""
    profits = sorted(float(p) for p in placebo_profits)
    n = len(profits)
    if n < 3:
        return None
    below = sum(1 for p in profits if p < candidate_profit)
    median = profits[n // 2] if n % 2 == 1 else (profits[n // 2 - 1] + profits[n // 2]) / 2
    exceeds_all = candidate_profit > profits[-1]
    out: Dict[str, object] = {
        "n_placebo": n,
        "candidate_profit": float(candidate_profit),
        "placebo_median": median,
        "placebo_best": profits[-1],
        "placebo_worst": profits[0],
        "percentile": round(below / n, 4),
        "exceeds_all": exceeds_all,
        "gap_to_best": float(candidate_profit) - profits[-1],
    }
    if exceeds_all and median < 0:
        out["interpretation"] = (
            "후보가 플라시보 전 표본 상회 + 플라시보 중앙값 음수"
            " — 손익의 원천은 진입 신호(우연/매도식 단독 아님)"
        )
    elif not exceeds_all:
        out["interpretation"] = (
            "일부 플라시보가 후보를 상회 — 진입 신호의 기여 불명확(재검토 필요)"
        )
    else:
        out["interpretation"] = "후보가 전 표본 상회(플라시보도 흑자 — 매도식 기여 큼)"
    return out
