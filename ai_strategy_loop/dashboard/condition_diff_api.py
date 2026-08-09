"""조건식 비교 API (페이지 33) — "그래서 정확히 뭐가 다른가".

원장(30)이 "어느 후보가 나은가"를 답하고, 계기판(31)이 "믿을 만한가",
응답면(32)이 "표본 밖에서 살아남는가"를 답한다. 이 화면은 그 앞의 질문에
답한다: **두 조건식이 무엇이 다른가.**

지금까지 그 답은 커밋 메시지와 문서에 손으로 적혀 있었다. 손으로 적으면
어긋난다 — "조기 청산 한 줄만 얹었다"가 맞는지 매번 눈으로 확인해야 했다.

권한 계약: **읽기 전용.** `strategy.db` 를 `mode=ro` 로 연다.
안전 계약: 조건식을 **실행하지 않는다**(`condition_diff` 가 텍스트만 읽는다).
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Final

from fastapi import APIRouter

from ai_strategy_loop.controller import condition_diff as cdiff

condition_diff_router = APIRouter()

_STRATEGY_DB: Final = os.path.join(
    os.path.dirname(__file__), "..", "..", "_database", "strategy.db")

#: 종류 → (테이블, 화면 이름). 이 표 밖의 테이블은 읽지 않는다.
_TABLES: Final = {"buy": ("stockbuy", "매수식"), "sell": ("stocksell", "매도식")}

#: 화면 기본 목록에 올릴 이름공간 — 남의 자산을 기본값으로 올리지 않는다.
_PREFIXES: Final = {
    "buy": ("Tick_B_902_905", "W7_B_", "C_T_902_905"),
    "sell": ("Tick_S_902_905", "W4_S_", "W6_S_"),
}


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{os.path.abspath(_STRATEGY_DB)}?mode=ro", uri=True)


def _names(kind: str) -> list[str]:
    table, _ = _TABLES[kind]
    con = _connect()
    try:
        rows = con.execute(f'SELECT "index" FROM {table}').fetchall()
    finally:
        con.close()
    keep = _PREFIXES[kind]
    return sorted(str(r[0]) for r in rows if str(r[0]).startswith(keep))


def _code(kind: str, name: str) -> str | None:
    table, _ = _TABLES[kind]
    con = _connect()
    try:
        row = con.execute(f'SELECT 전략코드 FROM {table} WHERE "index"=?',
                          (name,)).fetchone()
    finally:
        con.close()
    return str(row[0]) if row else None


@condition_diff_router.get("/loop/condition-names")
def condition_names(kind: str = "buy") -> dict[str, Any]:
    if kind not in _TABLES:
        return {"available": False, "reason": f"알 수 없는 종류: {kind}"}
    names = _names(kind)
    return {"available": bool(names), "kind": kind,
            "label": _TABLES[kind][1], "names": names,
            "kinds": {k: v[1] for k, v in _TABLES.items()}}


@condition_diff_router.get("/loop/condition-diff")
def condition_diff(kind: str = "buy", left: str = "", right: str = "",
                   context: int = 2) -> dict[str, Any]:
    """두 조건식의 절 층 + 줄 층 대조."""
    if kind not in _TABLES:
        return {"available": False, "reason": f"알 수 없는 종류: {kind}"}
    if not (left and right):
        return {"available": False, "reason": "left·right 를 모두 지정하세요",
                "names": _names(kind), "kind": kind}

    left_code, right_code = _code(kind, left), _code(kind, right)
    missing = [n for n, c in ((left, left_code), (right, right_code)) if c is None]
    if missing:
        return {"available": False, "reason": f"조건식을 찾을 수 없다: {missing}",
                "names": _names(kind), "kind": kind}

    view = cdiff.compare(left, left_code, right, right_code,
                         context=max(0, min(context, 10)))
    return {
        **view, "kind": kind, "label": _TABLES[kind][1],
        "names": _names(kind),
        "known_clauses": cdiff.known_clauses(),
        "reading_rules": [
            "**절 층**은 이름이 등록된 절만 봅니다. 임계만 바꾼 변화는 여기에 안 잡히니 "
            "**줄 층**을 함께 보세요.",
            "`주석 처리`는 제거 실험의 흔적입니다 — 지우지 않고 남겨 두어 무엇을 뺐는지 "
            "조건식만 봐도 알 수 있게 합니다.",
            "**주석 처리뿐** 배지가 뜨면 실행되는 코드는 줄어들기만 했다는 뜻입니다 "
            "— 한 변수 실험이 성립합니다.",
            "이 화면은 조건식을 **실행하지 않습니다**. 텍스트만 읽습니다.",
        ],
    }
