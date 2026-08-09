"""표본·검정력 계기판 API (페이지 31) — "지금 표본으로 무엇을 확정할 수 있나".

페이지 30(원장)이 "이 후보가 나은가"를 보여준다면, 이 화면은 **"그 판정을 믿을
만한가, 못 믿겠으면 얼마나 더 재야 하나"**를 보여준다.

두 화면을 나눈 이유: 원장에 검정력 열까지 넣으면 표가 스무 칸이 되어 아무도
안 읽는다. 판정은 판정대로, 신뢰도는 신뢰도대로 본다.

권한 계약: **읽기 전용.** 원장 DB 와 tick DB 파일 목록만 읽는다.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ai_strategy_loop.controller import power_gauge, standing, strategy_ledger as ledger
from ai_strategy_loop.labeling.lanes import LANES

power_gauge_router = APIRouter()


def trade_rate(rows: list[dict[str, Any]], lane_name: str = "tick") -> dict[str, Any]:
    """합격선의 실측 거래 빈도 — 부족분을 '며칠'로 환산하는 데 쓴다.

    분모는 **DB 에 실제로 있는 거래일**이다. 달력 일수로 나누면 주말·휴일이 섞여
    빈도가 과소평가되고, 거래가 일어난 날만 세면 과대평가된다(실측: 각각 0.34 / 1.39).
    """
    baseline = next((r for r in rows if r.get("verdict") == "BASELINE"), None)
    if not baseline or not baseline.get("trades"):
        return {"available": False, "reason": "합격선 기록이 없어 빈도를 낼 수 없다"}

    start, end = baseline.get("period_start"), baseline.get("period_end")
    lane = LANES.get(lane_name, LANES["tick"])
    days = [d for d in standing.db_days(lane)
            if (start is None or d >= start) and (end is None or d <= end)]
    if not days:
        return {"available": False, "reason": "구간에 해당하는 DB 거래일이 없다"}

    trades = int(baseline["trades"])
    return {
        "available": True,
        "baseline_id": baseline.get("candidate_id"),
        "trades": trades,
        "db_trading_days": len(days),
        "period": [start, end],
        "trades_per_day": trades / len(days),
    }


@power_gauge_router.get("/loop/power-gauge")
def power_gauge_view(lane: str = "tick") -> dict[str, Any]:
    rows = ledger.latest_per_candidate()
    rate = trade_rate(rows, lane)
    state = power_gauge.fleet(
        rows, trades_per_day=rate.get("trades_per_day") if rate.get("available") else None)

    return {
        **state,
        "lane": lane,
        "trade_rate": rate,
        "authority": "official",
        "reading_rules": [
            "**MDE(최소 검출 가능 효과)** 는 지금 표본의 눈금 폭입니다. 관측 차이가 "
            "MDE 보다 작으면 결과가 0이 아니어도 아직 잰 것이 아닙니다.",
            "**검정력**은 '이 차이가 진짜라면 잡아낼 확률'입니다. 목표는 80% 입니다.",
            "'표본 절망'은 필요 표본이 지금의 10배를 넘는다는 뜻입니다 — 더 모으는 것이 "
            "아니라 **효과 자체를 키워야** 합니다.",
            "'역방향'은 관측 차이가 0 이하라는 뜻입니다 — 표본을 늘려도 이기지 않습니다.",
            "확정(유의)과 검정력은 다른 질문입니다. 유의해도 검정력이 낮으면 "
            "'이번엔 잡았지만 다시 재면 놓칠 수 있다'는 뜻입니다.",
        ],
    }
