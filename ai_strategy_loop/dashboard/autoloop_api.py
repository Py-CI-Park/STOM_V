"""자율 루프 관제 API (페이지 26) — 세대별 가설·판정·수정 원장·예산 잔량.

배경(마스터 웨이브 W2): 자율 루프는 사람 승인 없이 돌아간다. 그렇다면 최소한
**무엇을 가정하고, 그 가정이 맞았는지, 예산을 얼마나 썼는지**는 관측 가능해야
한다. 이 라우터가 그 관측면을 공급한다.

핵심 계약:
  - **읽기 전용**. `LoopState(readonly=True)` 로 보호된 loop_runs.db 를 열어
    mkdir/PRAGMA/DDL 없이 조회만 한다 (결과 데이터 오염 금지).
  - **가설 원장 예산**: 아이디어(run) 당 수정 횟수 상한(기본 15). 초과분은
    `over_budget=True` 로 표시한다 — 선택 편의를 키우는 무한 수정 차단.
  - **선택 편의 차감**: 설계 구간 성적은 실측 보정 계수(0.6225%p)를 뺀 값을
    함께 제시한다. 원값만 보면 항상 낙관 편향이 된다(QSP13 실측).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Annotated, Any, Final

from fastapi import APIRouter
from pydantic import StringConstraints

from ai_strategy_loop.controller.state import LOOP_RUNS_DB, LoopState

autoloop_router = APIRouter()

#: 아이디어당 수정 상한 — 이 값을 넘기면 그 가설은 폐기하고 기록한다(웨이브 W2).
REVISION_BUDGET: Final = 15

#: 선택 편의 보정 계수(%p) — QSP13 워크포워드 30폴드 실측.
SELECTION_BIAS_PCT: Final = 0.6225

RunId = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)]


def _rows(query: str, params: tuple = ()) -> list[dict[str, Any]]:
    """보호된 DB 를 읽기 전용으로 조회한다. 없거나 스키마가 낮으면 빈 목록."""
    try:
        state = LoopState(readonly=True)
    except sqlite3.Error:
        return []
    try:
        cursor = state._con.execute(query, params)  # noqa: SLF001 - readonly 조회 관례
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        try:
            state._con.close()  # noqa: SLF001
        except sqlite3.Error:
            pass


def _hypotheses(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return []
    return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []


@autoloop_router.get("/loop/autonomy/runs")
def autonomy_runs(limit: int = 20) -> dict[str, Any]:
    """자율 루프 run 목록 — 각 run 이 하나의 '아이디어'이자 예산 단위."""
    limit = max(1, min(int(limit), 100))
    rows = _rows(
        "SELECT run_id, COUNT(*) AS generations, MAX(created_at) AS last_at, "
        "       SUM(CASE WHEN gate_passed THEN 1 ELSE 0 END) AS gate_passed "
        "FROM generations GROUP BY run_id ORDER BY last_at DESC LIMIT ?",
        (limit,),
    )
    runs = []
    for row in rows:
        used = int(row.get("generations") or 0)
        runs.append({
            **row,
            "revisions_used": used,
            "revision_budget": REVISION_BUDGET,
            "budget_remaining": max(0, REVISION_BUDGET - used),
            "over_budget": used > REVISION_BUDGET,
        })
    return {"available": bool(runs), "authority": "observation_only",
            "db": str(LOOP_RUNS_DB), "runs": runs}


@autoloop_router.get("/loop/autonomy/generations")
def autonomy_generations(run_id: RunId = "", limit: int = 60) -> dict[str, Any]:
    """세대별 가설·판정·실측 델타 — 자율 루프가 무엇을 바꿨고 맞았는지."""
    limit = max(1, min(int(limit), 300))
    query = (
        "SELECT run_id, gen_no, parent_gen, diff_from_parent, status, gate_passed, reason, "
        "       score, trade_count, mdd, profit, daily_avg_trades, payoff_ratio, "
        "       d_graded, d_mdd, d_profit, d_daily_trades, hypotheses_json, created_at "
        "FROM generations "
    )
    params: tuple = ()
    if run_id:
        query += "WHERE run_id = ? "
        params = (run_id,)
    query += "ORDER BY gen_no DESC LIMIT ?"
    rows = _rows(query, (*params, limit))

    generations = []
    verdict_counts = {"accepted": 0, "rejected": 0, "inconclusive": 0, "untested": 0}
    for row in rows:
        hypotheses = _hypotheses(row.pop("hypotheses_json", None))
        for item in hypotheses:
            verdict = str(item.get("verdict") or "untested")
            if verdict in verdict_counts:
                verdict_counts[verdict] += 1
        generations.append({**row, "hypotheses": hypotheses,
                            "hypothesis_count": len(hypotheses)})

    judged = verdict_counts["accepted"] + verdict_counts["rejected"]
    return {
        "available": bool(generations),
        "authority": "observation_only",
        "run_id": run_id,
        "generations": generations,
        "hypothesis_verdicts": verdict_counts,
        # 가정 적중률 — 부검→가정→개선 루프가 실제로 학습하는지 보는 지표.
        "hypothesis_hit_rate": (verdict_counts["accepted"] / judged) if judged else None,
    }


@autoloop_router.get("/loop/autonomy/ledger")
def autonomy_ledger(run_id: RunId = "") -> dict[str, Any]:
    """가설 원장(W2) — 수정 1건 = 가설 1건. 폐기된 가설도 남는다.

    예산의 **정본**은 세대 수가 아니라 이 원장이다. 세대 없이 폐기된 수정도
    예산을 소모했으므로, 원장이 있으면 그것을 우선해서 읽는다.
    """
    from ai_strategy_loop.controller import hypothesis_ledger as ledger  # noqa: PLC0415

    rows = ledger.read_ledger()
    if run_id:
        rows = [row for row in rows if row.get("run_id") == run_id]
    summary = ledger.run_summary(run_id) if run_id else None
    return {
        "available": bool(rows),
        "authority": "observation_only",
        "run_id": run_id,
        "records": rows[-200:],
        "summary": summary,
        "revision_budget": ledger.DEFAULT_REVISION_BUDGET,
        "selection_bias_pct": ledger.SELECTION_BIAS_PCT,
    }


@autoloop_router.get("/loop/autonomy/budget")
def autonomy_budget(run_id: RunId = "") -> dict[str, Any]:
    """예산·편의 차감 요약 — 이 화면의 결론 칸."""
    runs = autonomy_runs(limit=100)["runs"]
    target = next((r for r in runs if r["run_id"] == run_id), None) if run_id else (runs[0] if runs else None)
    if target is None:
        return {"available": False, "reason": "no_run_records",
                "revision_budget": REVISION_BUDGET,
                "selection_bias_pct": SELECTION_BIAS_PCT}

    generations = autonomy_generations(run_id=target["run_id"], limit=300)["generations"]
    best = None
    for row in generations:
        score = row.get("score")
        if score is None:
            continue
        if best is None or score > best.get("score", float("-inf")):
            best = row

    design_pct = None
    if best is not None and best.get("trade_count"):
        # 건당 수익률(%) 근사 — 원장 표기는 항상 편의 차감본과 함께 읽는다.
        profit = best.get("profit") or 0.0
        design_pct = float(profit) / float(best["trade_count"]) / 10_000.0 if best["trade_count"] else None

    # 예산의 정본은 가설 원장(W2)이다 — 세대 없이 폐기된 수정도 예산을 썼다.
    #   원장에 기록이 있으면 그것을 우선하고, 없으면 세대 수로 근사한다.
    from ai_strategy_loop.controller import hypothesis_ledger as ledger  # noqa: PLC0415

    ledger_state = ledger.budget_state(target["run_id"])
    from_ledger = ledger_state["revisions_used"] > 0
    revisions_used = ledger_state["revisions_used"] if from_ledger else target["revisions_used"]
    budget_remaining = (
        ledger_state["budget_remaining"] if from_ledger else target["budget_remaining"]
    )
    over_budget = ledger_state["exhausted"] if from_ledger else target["over_budget"]

    return {
        "available": True,
        "authority": "observation_only",
        "run_id": target["run_id"],
        "budget_source": "hypothesis_ledger" if from_ledger else "generation_count",
        "revisions_used": revisions_used,
        "revision_budget": REVISION_BUDGET,
        "budget_remaining": budget_remaining,
        "over_budget": over_budget,
        "selection_bias_pct": SELECTION_BIAS_PCT,
        "best_generation": best,
        "design_per_trade_pct": design_pct,
        "bias_adjusted_pct": (design_pct - SELECTION_BIAS_PCT) if design_pct is not None else None,
        "note": "설계 구간 성적은 선택 편의 0.6225%p 를 뺀 값으로 읽는다 (QSP13 30폴드 실측).",
    }


@autoloop_router.get("/loop/standing")
def standing(out_name: str = "", lane: str = "tick",
             today: int = 0, max_age_days: int = 0) -> dict[str, Any]:
    """상설화 현황 (W5) — 백필 계획 + 후보 재검증 계획.

    `today` 를 인자로 받는 이유: 서버 시각을 함수 안에서 읽으면 화면이 무엇을
    기준으로 "오래됐다"고 말하는지 검증할 수 없다. 0 이면 재검증 계획을 만들지
    않고 백필만 답한다.
    """
    from ai_strategy_loop.controller import standing as st  # noqa: PLC0415

    if lane not in ("tick", "min"):
        return {"available": False, "reason": "unknown_lane", "lane": lane}

    records = _standing_candidates()
    # 기본값을 여기서 문자열로 박지 않는다 — 정본 라벨 세트는 controller 가 안다.
    payload = st.standing_status(out_name or st.DEFAULT_OUT_NAME, lane,
                                 records=records, today=today)
    if today and max_age_days:
        payload["revalidation"] = st.revalidation_plan(
            records, today=today, max_age_days=max_age_days)
    payload["available"] = True
    payload["candidate_count"] = len(records)
    return payload


def _standing_candidates() -> list[dict[str, Any]]:
    """재검증 대상 후보 — 루프가 남긴 run 기록에서 뽑는다.

    기록이 없으면 빈 목록이다. 후보를 지어내지 않는다.
    """
    rows = _rows(
        "SELECT run_id, MAX(created_at) AS last_at FROM runs GROUP BY run_id "
        "ORDER BY last_at DESC LIMIT 50"
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        stamp = str(row.get("last_at") or "")
        digits = "".join(ch for ch in stamp if ch.isdigit())[:8]
        candidates.append({
            "name": row.get("run_id"),
            "last_verdict_day": int(digits) if len(digits) == 8 else None,
        })
    return candidates
