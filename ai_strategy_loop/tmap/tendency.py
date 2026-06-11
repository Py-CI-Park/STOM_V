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
            "csv_path": r.get("csv_path"),  # P2 — 연도 일관성 검사 재료.
        }
        for r in pts
    ]


def center_yearly_consistency(
    curve: List[Dict[str, Any]], center_value: Any, min_positive_years: int = 2
) -> Optional[Dict[str, Any]]:
    """P2(2026-06-11) — θ* 중심점의 연도 일관성 검사 (사전선언 규칙).

    중심점 CSV의 연도별 손익에서 흑자 연도 >= min_positive_years(기본 2,
    3년 train 기준). 합산 수익이 가리는 알파 감쇠(2023 大흑자가 2025 적자를
    가리는 패턴 — 시드의 실측 문제)를 후보 선정 단계에서 차단한다.
    CSV 부재/파싱 실패는 None(검사 생략 — graceful, advisory 계약과 동일).
    """
    from ai_strategy_loop.controller._seed_relative_selection import (  # noqa: PLC0415
        yearly_profit_breakdown,
    )

    row = next((p for p in curve if p.get("value") == center_value), None)
    if not row or not row.get("csv_path"):
        return None
    breakdown = yearly_profit_breakdown(row["csv_path"])
    if not breakdown:
        return None
    years = {year: profit for year, profit in breakdown}
    positive = sum(1 for v in years.values() if v > 0)
    passed = positive >= min_positive_years
    return {
        "passed": passed,
        "years": {y: round(p) for y, p in sorted(years.items())},
        "positive_years": positive,
        "reason": "" if passed else (
            f"yearly consistency fail: 흑자 연도 {positive}/{len(years)}"
            f" < {min_positive_years}"
        ),
    }


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
        # C5′/N8(2026-06-11) — 베이스라인 중복 측정(--replicate-baseline) 시
        #   측정 노이즈 밴드(max-min)를 산출한다. 이 밴드보다 작은 절벽(cliff)은
        #   신호가 아니라 측정 흔들림으로 읽어야 한다(절벽 판독의 하한).
        reps = [float(r.get("profit") or 0.0) for r in rows
                if r["param"] == "__default__" and r.get("status") == "ok"]
        if len(reps) > 1:
            out["baseline"]["replicates"] = len(reps)
            out["baseline"]["noise_band"] = round(max(reps) - min(reps), 2)
    base_profit = abs(out["baseline"]["profit"]) if out["baseline"] else 1.0

    if base is not None and out["baseline"] is not None:
        out["baseline"]["shape"] = _shape_for_csv(base.get("csv_path"))  # P3.

    params = sorted({r["param"] for r in rows if r["param"] != "__default__"})
    for name in params:
        curve = _curve_for(rows, name)
        metrics = plateau_metrics(curve)
        plateau = metrics.get("plateau")
        score = 0.0
        center_shape = None
        if plateau:
            score = (
                metrics["positive_ratio"] * plateau["width"]
                * (plateau["mean_profit"] / max(base_profit, 1.0))
            )
            center_row = next(
                (p for p in curve if p.get("value") == plateau.get("center_value")), None
            )
            if center_row:  # P3 — θ* 근거 병기용 고원 중심점 곡선 형태(advisory).
                center_shape = _shape_for_csv(center_row.get("csv_path"))
        out["params"][name] = {
            "curve": curve,
            **metrics,
            "plateau_score": round(score, 4),
            "center_shape": center_shape,
        }
    return out


def _shape_for_csv(csv_path: Optional[str]) -> Optional[Dict[str, Any]]:
    """P3 — CSV의 일별 손익으로 우상향 품질 지표를 계산한다(실패는 None)."""
    if not csv_path:
        return None
    from ai_strategy_loop.fitness.overfit_stats import (  # noqa: PLC0415
        curve_shape_metrics,
        daily_pnl_series,
    )

    series = daily_pnl_series(csv_path)
    return curve_shape_metrics(series) if series else None


def grid_summary(run_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    """C6/P1(2026-06-11) — 2-D 격자 스윕 요약: 행렬·흑자율·최강 셀·mesa.

    mesa(고원 면) = 흑자 셀 중 존재하는 4-이웃이 전부 흑자인 셀(사전선언).
    1-D 고원 둘의 교차가 면으로도 안정적인지의 직접 증거다. 실패는 count=0.
    """
    import sqlite3  # noqa: PLC0415

    from ai_strategy_loop.tmap.template import parse_grid_label  # noqa: PLC0415

    out: Dict[str, Any] = {"run_id": run_id, "baseline": None, "param_a": None,
                           "param_b": None, "cells": [], "count": 0}
    try:
        con = sqlite3.connect(str(db_path or _runs_db_path()))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT status, profit, mdd, trade_count, strategy_gist"
                " FROM generations WHERE run_id=? ORDER BY gen_no", (run_id,),
            ).fetchall()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return out

    cells: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        gist = r["strategy_gist"] or ""
        if gist.startswith("TMAP __default__") and out["baseline"] is None:
            out["baseline"] = {"profit": float(r["profit"] or 0.0),
                               "mdd": float(r["mdd"] or 0.0),
                               "trades": int(r["trade_count"] or 0)}
            continue
        parsed = parse_grid_label(gist)
        if parsed is None:
            continue
        a, va, b, vb = parsed
        out["param_a"], out["param_b"] = a, b
        cells[(va, vb)] = {
            "a": va, "b": vb,
            "profit": float(r["profit"] or 0.0),
            "mdd": float(r["mdd"] or 0.0),
            "trades": int(r["trade_count"] or 0),
            "ok": r["status"] == "ok",
        }
    if not cells:
        return out

    a_values = sorted({k[0] for k in cells})
    b_values = sorted({k[1] for k in cells})
    positive = [c for c in cells.values() if c["ok"] and c["profit"] > 0]
    mesa = []
    for (va, vb), c in cells.items():
        if not (c["ok"] and c["profit"] > 0):
            continue
        ia, ib = a_values.index(va), b_values.index(vb)
        neighbors = []
        for da, db_ in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ja, jb = ia + da, ib + db_
            if 0 <= ja < len(a_values) and 0 <= jb < len(b_values):
                n = cells.get((a_values[ja], b_values[jb]))
                if n is not None:
                    neighbors.append(n)
        if neighbors and all(n["ok"] and n["profit"] > 0 for n in neighbors):
            mesa.append({"a": va, "b": vb, "profit": c["profit"], "mdd": c["mdd"]})
    best = max((c for c in cells.values() if c["ok"]),
               key=lambda c: c["profit"], default=None)
    out.update({
        "a_values": a_values, "b_values": b_values,
        "cells": sorted(cells.values(), key=lambda c: (c["a"], c["b"])),
        "count": len(cells),
        "positive_ratio": round(len(positive) / max(len(cells), 1), 4),
        "best_cell": best,
        "mesa_cells": sorted(mesa, key=lambda c: -c["profit"]),
    })
    return out
