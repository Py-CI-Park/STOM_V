"""조건식 성과 원장 API (페이지 30) — 지금까지 만든 후보 전부를 한 표에.

지금까지 후보 성과가 세션 로그와 JSON 에 흩어져 있어서 "뭐가 제일 좋았나"에
답하려면 매번 파일을 뒤져야 했다. 이 화면이 그 누적을 맡는다.

권한 계약: **읽기 전용.** 원장 DB 는 러너가 쓰고 화면은 읽기만 한다.
판정 계약: 판정은 절대 기준이 아니라 **챔피언 대비**다. 화면이 그 사실을 말한다.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter

from ai_strategy_loop.controller import strategy_ledger as ledger

strategy_ledger_router = APIRouter()

#: 판정별 사람 말 — 화면과 API 가 같은 문구를 쓰게 한 곳에 둔다.
VERDICT_LABEL: Final = {
    "BASELINE": "합격선(챔피언)",
    "PASS": "승격 후보",
    "PROMISING": "유망 · 표본 부족",
    "MIXED": "혼합 · 자본 대비 미달",
    "REJECT": "폐기",
}


def _decorate(row: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    """행 하나에 사람이 읽을 값을 붙인다 — 계산은 하되 원장을 고치지 않는다."""
    out = dict(row)
    out["verdict_label"] = VERDICT_LABEL.get(str(row.get("verdict")), str(row.get("verdict")))
    out["is_baseline"] = row.get("verdict") == "BASELINE"

    cagr, mdd = row.get("cagr"), row.get("mdd_pct")
    out["calmar"] = (float(cagr) / float(mdd)) if (cagr is not None and mdd) else None

    if baseline and not out["is_baseline"]:
        for key in ("avg_profit_pct", "total_profit_pct", "cagr", "mdd_pct", "seed_capital"):
            mine, base = row.get(key), baseline.get(key)
            out[f"delta_{key}"] = (float(mine) - float(base)) \
                if (mine is not None and base is not None) else None
        base_calmar = (float(baseline["cagr"]) / float(baseline["mdd_pct"])) \
            if (baseline.get("cagr") is not None and baseline.get("mdd_pct")) else None
        out["delta_calmar"] = (out["calmar"] - base_calmar) \
            if (out["calmar"] is not None and base_calmar is not None) else None
    return out


def _source(db_path: Path, reason: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"kind": "sqlite", "path": str(db_path)}
    if reason:
        payload["reason"] = reason
    return payload


def _unavailable_state(reason: str = "source_missing") -> dict[str, Any]:
    db_path = Path(ledger._path(None))  # read-only dashboard surface over the runner-owned DB
    return {
        "available": False,
        "authority": "official",
        "reason": reason,
        "source_missing": reason == "source_missing",
        "source": _source(db_path, reason),
        "candidates": 0,
        "records": 0,
        "verdicts": {verdict: 0 for verdict in ledger.VERDICTS},
        "baseline": None,
        "best_by_avg_profit": None,
        "promoted": 0,
        "note": "원장 SQLite 파일이 아직 없습니다. 쓰기/수집 경로가 생성한 뒤 읽습니다.",
    }


def _connect_readonly() -> tuple[sqlite3.Connection | None, str]:
    db_path = Path(ledger._path(None))
    if not db_path.is_file():
        return None, "source_missing"
    try:
        connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None, "source_unavailable"
    connection.row_factory = sqlite3.Row
    return connection, ""


def _read_all(connection: sqlite3.Connection, *, limit: int = 500) -> list[dict[str, Any]]:
    rows = connection.execute(
        "SELECT * FROM candidates ORDER BY row_id DESC LIMIT ?", (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def _latest_per_candidate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        seen.setdefault(str(row["candidate_id"]), row)
    return list(seen.values())


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest = _latest_per_candidate(rows)
    counts: dict[str, int] = {verdict: 0 for verdict in ledger.VERDICTS}
    for row in latest:
        counts[str(row["verdict"])] = counts.get(str(row["verdict"]), 0) + 1

    graded = [
        row for row in latest
        if row["verdict"] != "BASELINE" and row["avg_profit_pct"] is not None
    ]
    baseline = next((row for row in latest if row["verdict"] == "BASELINE"), None)
    return {
        "available": bool(latest),
        "authority": "official",
        "reason": "",
        "source_missing": False,
        "source": _source(Path(ledger._path(None))),
        "candidates": len(latest),
        "records": len(rows),
        "verdicts": counts,
        "baseline": baseline,
        "best_by_avg_profit": max(graded, key=lambda row: row["avg_profit_pct"], default=None),
        "promoted": counts.get("PASS", 0),
        "note": ("판정은 챔피언 대비다. PROMISING 은 합격이 아니라 "
                 "'방향은 맞는데 표본이 얇다'는 뜻이다."),
    }


@strategy_ledger_router.get("/loop/strategy-ledger")
def strategy_ledger(limit: int = 200, history: bool = False) -> dict[str, Any]:
    """후보별 최신 기록(기본) 또는 전체 이력(`history=true`).

    원장은 append-only 라 같은 후보의 과거 판정도 남아 있다. 기본 보기는 최신만
    보여주되, 이력을 감추지는 않는다.
    """
    connection, reason = _connect_readonly()
    if connection is None:
        state = _unavailable_state(reason)
        rows: list[dict[str, Any]] = []
    else:
        try:
            all_rows = _read_all(connection, limit=5000)
            state = _summary(all_rows)
            rows = _read_all(connection, limit=limit) if history else _latest_per_candidate(all_rows)
        except sqlite3.Error:
            state = _unavailable_state("source_unavailable")
            rows = []
        finally:
            connection.close()
    baseline = state.get("baseline")
    decorated = [_decorate(r, baseline) for r in rows]
    # 합격선을 맨 위에, 그 아래는 건당 수익률 내림차순.
    decorated.sort(key=lambda r: (not r["is_baseline"],
                                  -(r.get("avg_profit_pct") or float("-inf"))))

    return {
        "available": state["available"],
        "authority": state["authority"],
        "reason": state["reason"],
        "source_missing": state["source_missing"],
        "source": state["source"],
        "history": history,
        "candidates": state["candidates"],
        "records": state["records"],
        "verdicts": state["verdicts"],
        "verdict_labels": VERDICT_LABEL,
        "promoted": state["promoted"],
        "rows": decorated,
        "note": state["note"],
        "reading_rules": [
            "판정은 절대 기준이 아니라 **챔피언 대비**입니다. 챔피언이 떨어지는 "
            "기준은 후보가 아니라 기준이 틀린 것입니다.",
            "총수익금만 보면 자본을 더 쓴 후보가 항상 이깁니다 — 총수익률(=수익금/필요자금)을 "
            "함께 보세요.",
            "PROMISING·MIXED 는 합격이 아닙니다. 승격(PASS)은 챔피언 이상이면서 "
            "통계적으로 확정된 경우뿐입니다.",
            "원장은 append-only 입니다 — 폐기된 후보도 남습니다(같은 실험을 두 번 하지 않기 위해).",
        ],
    }
