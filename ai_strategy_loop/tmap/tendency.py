"""TMAP G3 — 경향성 분석기: 변수별 응답 곡선·고원(plateau)·절벽 감지.

사용자 통찰의 형식화(2026-06-11 재설계 §0): 개선 루프의 비단조성·경로 의존성에
면역이 되려면 피크가 아니라 **고원** — 이웃 θ들도 흑자인 넓은 영역 — 을 골라야 한다.

입력: tmap_sweep이 loop_runs.db에 남긴 행들(strategy_gist='TMAP {param}={value}').
출력: 변수별 {곡선, 고원(중심/폭/평균손익), 절벽, 흑자율} + 베이스라인.
분석 전용 — 어떤 게이트/선택 규율도 바꾸지 않는다(advisory).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_strategy_loop.tmap.template import parse_point_label


def _runs_db_path() -> Path:
    from ai_strategy_loop.controller import state as _S  # noqa: PLC0415

    return Path(str(_S.LOOP_RUNS_DB))


def load_sweep_rows(run_id: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """스윕 run의 행을 (param, value 파싱 포함) 읽는다. 실패는 빈 리스트."""
    try:
        con = sqlite3.connect(str(db_path or _runs_db_path()))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT gen_no, status, gate_passed, profit, mdd, trade_count,"
                " daily_avg_trades, payoff_ratio, strategy_gist, buy_name, csv_path"
                " FROM generations WHERE run_id=? ORDER BY gen_no",
                (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return []

    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        parsed = parse_point_label(d.get("strategy_gist") or "")
        if parsed is None:
            continue
        d["param"], d["value"] = parsed
        out.append(d)
    return out


def _curve_for(rows: List[Dict[str, Any]], param: str) -> List[Dict[str, Any]]:
    pts = [r for r in rows if r["param"] == param and r["value"] is not None]
    pts.sort(key=lambda r: r["value"])
    return [
        {
            "value": r["value"],
            "profit": float(r.get("profit") or 0.0),
            "mdd": float(r.get("mdd") or 0.0),
            "trades": int(r.get("trade_count") or 0),
            "status": r.get("status"),
            "ok": r.get("status") == "ok",
        }
        for r in pts
    ]


def plateau_metrics(curve: List[Dict[str, Any]]) -> Dict[str, Any]:
    """곡선에서 고원·절벽·흑자율을 계산한다.

    - 고원: profit>0이 연속인 최장 구간 — 중심값·폭(점 수)·평균 손익.
    - 절벽: 인접 점 간 |Δprofit| 최댓값과 그 위치(과적합 경계 후보).
    - 흑자율: ok 점 중 profit>0 비율.
    """
    ok_pts = [p for p in curve if p["ok"]]
    if not ok_pts:
        return {"positive_ratio": 0.0, "plateau": None, "cliff": None, "n_points": 0}

    positive_ratio = sum(1 for p in ok_pts if p["profit"] > 0) / len(ok_pts)

    best: Optional[Dict[str, Any]] = None
    run: List[Dict[str, Any]] = []
    for p in curve:
        if p["ok"] and p["profit"] > 0:
            run.append(p)
        else:
            run = []
        if run and (best is None or len(run) > best["width"]
                    or (len(run) == best["width"]
                        and sum(q["profit"] for q in run) / len(run) > best["mean_profit"])):
            center = run[len(run) // 2]
            best = {
                "width": len(run),
                "center_value": center["value"],
                "mean_profit": sum(q["profit"] for q in run) / len(run),
                "min_profit": min(q["profit"] for q in run),
                "values": [q["value"] for q in run],
            }

    cliff = None
    for a, b in zip(curve, curve[1:]):
        if not (a["ok"] and b["ok"]):
            continue
        jump = abs(b["profit"] - a["profit"])
        if cliff is None or jump > cliff["jump"]:
            cliff = {"between": [a["value"], b["value"]], "jump": jump}

    return {
        "positive_ratio": round(positive_ratio, 4),
        "plateau": best,
        "cliff": cliff,
        "n_points": len(curve),
    }


def summarize_tendency(run_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """스윕 run 전체의 경향성 요약(베이스라인 + 변수별 곡선/고원/절벽).

    plateau_score = 흑자율 × 고원 폭 × (고원 평균손익 / max(|베이스라인 손익|, 1)) —
    '넓고, 두텁고, 베이스라인 대비 의미 있는' 고원이 높은 점수를 받는다(advisory).
    """
    rows = load_sweep_rows(run_id, db_path)
    out: Dict[str, Any] = {"run_id": run_id, "baseline": None, "params": {}, "count": len(rows)}
    if not rows:
        return out

    base = next((r for r in rows if r["param"] == "__default__"), None)
    if base is not None:
        out["baseline"] = {
            "profit": float(base.get("profit") or 0.0),
            "mdd": float(base.get("mdd") or 0.0),
            "trades": int(base.get("trade_count") or 0),
            "status": base.get("status"),
        }
    base_profit = abs(out["baseline"]["profit"]) if out["baseline"] else 1.0

    params = sorted({r["param"] for r in rows if r["param"] != "__default__"})
    for name in params:
        curve = _curve_for(rows, name)
        metrics = plateau_metrics(curve)
        plateau = metrics.get("plateau")
        score = 0.0
        if plateau:
            score = (
                metrics["positive_ratio"] * plateau["width"]
                * (plateau["mean_profit"] / max(base_profit, 1.0))
            )
        out["params"][name] = {
            "curve": curve,
            **metrics,
            "plateau_score": round(score, 4),
        }
    return out
