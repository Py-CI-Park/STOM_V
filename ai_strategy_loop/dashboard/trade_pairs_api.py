"""거래 짝 뷰어 API (페이지 34) — 짝지은 검정의 **개별 거래**를 연다.

짝지은 검정은 "+0.1974%p [−0.084, +0.479]" 한 줄을 준다. 그 한 줄로는 **왜**
그런지 알 수 없다. W7 에서 실제로 막힌 지점이 그것이다:

> 시간손절이 자르는 거래에 "되살아났을 거래"가 섞여 있다 — 고 추측했지만,
> 그 거래를 직접 본 적은 없다.

이 화면이 그 거래를 꺼낸다.

후보를 고르면 원장에서 그 후보와 **합격선**의 job_id 를 찾아 두 체결 기록을
1:1 로 맞춘다. 사람이 job_id 를 외울 필요가 없다.

권한 계약: **읽기 전용.** `backtest.db` 를 `mode=ro` 로 연다.
"""

from __future__ import annotations

import os
from typing import Any, Final

import pandas as pd
from fastapi import APIRouter

from ai_strategy_loop.controller import strategy_ledger as ledger
from ai_strategy_loop.controller import trade_pairs as tpairs
from ai_strategy_loop.labeling.run_engine_ladder import _tables, resolve_table

trade_pairs_router = APIRouter()

_BT_DB: Final = os.path.join(
    os.path.dirname(__file__), "..", "..", "_database", "backtest.db")

_COLUMNS: Final = "매수시간, 종목명, 수익률, 수익금, 보유시간, 매도조건"


def _load(table: str) -> pd.DataFrame:
    path = os.path.abspath(_BT_DB)
    import sqlite3
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return pd.read_sql(f'SELECT {_COLUMNS} FROM "{table}"', con)
    finally:
        con.close()


def _candidates() -> list[dict[str, Any]]:
    """짝지을 수 있는 후보만 — 매도 계열이고 job_id 가 있어야 한다.

    진입 계열은 뺀다: 진입이 다르면 짝이 성립하지 않는다(공유 거래는 매도가
    같아 차이가 정확히 0, 늘어난 거래는 짝이 없다).
    """
    rows = ledger.latest_per_candidate()
    return [{"candidate_id": r["candidate_id"], "sell_name": r["sell_name"],
             "verdict": r["verdict"], "trades": r["trades"],
             "avg_profit_pct": r["avg_profit_pct"]}
            for r in rows
            if r.get("family") == "exit" and r.get("job_id")
            and r.get("verdict") != "BASELINE"]


def _baseline_row() -> dict[str, Any] | None:
    return next((r for r in ledger.latest_per_candidate()
                 if r.get("verdict") == "BASELINE" and r.get("job_id")), None)


@trade_pairs_router.get("/loop/trade-pairs")
def trade_pairs(candidate: str = "", limit: int = tpairs.DEFAULT_LIMIT) -> dict[str, Any]:
    picks = _candidates()
    base_row = _baseline_row()
    common = {"candidates": picks,
              "baseline": (base_row or {}).get("candidate_id"),
              "reading_rules": [
                  "같은 진입을 1:1 로 맞췄으므로 차이는 **순수하게 매도 규칙의 결과**입니다.",
                  "**청산 사유** 표가 '어디서 이기고 어디서 지는가'에 직접 답합니다.",
                  "**상위 10건 비중**이 1에 가까우면 소수 거래가 결과를 지배한다는 뜻입니다 "
                  "— 평균만 보고 판단하면 안 됩니다.",
                  "진입 계열 후보는 목록에 없습니다 — 진입이 다르면 짝이 성립하지 않습니다.",
              ]}
    if base_row is None:
        return {"available": False, "reason": "합격선 기록이 없다", **common}
    if not candidate:
        return {"available": False, "reason": "후보를 고르세요", **common}

    row = next((r for r in ledger.latest_per_candidate()
                if r["candidate_id"] == candidate), None)
    if row is None or not row.get("job_id"):
        return {"available": False, "reason": f"후보 기록이 없다: {candidate}", **common}

    tables = _tables(os.path.abspath(_BT_DB))
    base_table = resolve_table(tables, str(base_row.get("buy_name") or ""),
                               str(base_row["job_id"]))
    chal_table = resolve_table(tables, str(row.get("buy_name") or ""),
                               str(row["job_id"]))
    if not (base_table and chal_table):
        return {"available": False, "reason": "체결 기록 테이블을 찾을 수 없다", **common}

    view = tpairs.analyze(_load(base_table), _load(chal_table),
                          limit=max(1, min(limit, 100)))
    return {**view, **common, "candidate": candidate,
            "candidate_label": row.get("sell_name") or candidate,
            "baseline_label": base_row.get("sell_name") or base_row["candidate_id"],
            "verdict": row.get("verdict")}
