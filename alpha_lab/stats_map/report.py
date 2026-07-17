"""빌드 결과 → 사람이 읽을 분석 조각(상위/하위·함정·L0 대 L1·양EV 유무).

DB나 요약 JSON에 담을 파생 뷰만 만든다(원 통계는 stats.py). 판정은 하지 않고
정직한 정렬·매칭·필터만 제공한다 — 해석은 리포트 저자·감독이 한다.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from alpha_lab.stats_map import config

_CELL_KEY = ("time_label", "updown_q", "mktcap_b")


def select(rows: List[Dict[str, object]], *, axis_set: str, h: int,
           judged_only: bool = True) -> List[Dict[str, object]]:
    """축집합·지평으로 셀을 거른다. judged_only면 n>0·insufficient 아님만."""
    out = [r for r in rows if r["axis_set"] == axis_set and r["h"] == h]
    if judged_only:
        out = [r for r in out if r["n"] and not r["insufficient"]
               and r["mean_net"] is not None]
    return out


def top_bottom(rows: List[Dict[str, object]], k: int = 5
               ) -> Dict[str, List[Dict[str, object]]]:
    """mean_net 상위·하위 k 셀(요약 뷰)."""
    ordered = sorted(rows, key=lambda r: r["mean_net"])  # type: ignore[arg-type]
    return {"bottom": [_view(r) for r in ordered[:k]],
            "top": [_view(r) for r in ordered[-k:][::-1]]}


def positive_ev(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """비용차감 mean_net>0 셀(있으면 나열, 없으면 빈 목록 — 함정 지도 확인)."""
    return [_view(r) for r in rows if (r["mean_net"] or 0.0) > 0.0]


def ci_positive(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """CI 하한>0 셀(부트스트랩상 유의 양EV) — 가장 강한 후보 신호."""
    return [_view(r) for r in rows
            if r["ci_low"] is not None and r["ci_low"] > 0.0]


def trap_cells(rows: List[Dict[str, object]], k: int = 5
               ) -> List[Dict[str, object]]:
    """확률 높은데 EV 음수인 함정 셀 — P(net≥0) 최상위 중 mean_net<0."""
    losers = [r for r in rows if (r["mean_net"] or 0.0) < 0.0
              and r["p_net_ge0"] is not None]
    losers.sort(key=lambda r: r["p_net_ge0"], reverse=True)  # type: ignore[arg-type]
    return [_view(r) for r in losers[:k]]


def l0_vs_l1(l0_rows: List[Dict[str, object]], l1_rows: List[Dict[str, object]],
             *, axis_set: str, h: int) -> Dict[str, object]:
    """동일 셀에서 L0 대 L1 mean_net 비교(온셋이 지형보다 나은가)."""
    l0 = {_key(r): r for r in select(l0_rows, axis_set=axis_set, h=h)}
    l1 = {_key(r): r for r in select(l1_rows, axis_set=axis_set, h=h)}
    shared = sorted(set(l0) & set(l1))
    diffs: List[Dict[str, object]] = []
    better = 0
    for key in shared:
        d = float(l1[key]["mean_net"]) - float(l0[key]["mean_net"])  # type: ignore[arg-type]
        better += int(d > 0.0)
        diffs.append({"cell": key, "l0_mean_net": l0[key]["mean_net"],
                      "l1_mean_net": l1[key]["mean_net"], "l1_minus_l0": d,
                      "l1_n": l1[key]["n"]})
    diffs.sort(key=lambda x: x["l1_minus_l0"], reverse=True)  # type: ignore[arg-type]
    return {"n_shared_cells": len(shared), "l1_better_count": better,
            "diffs": diffs}


def pooled_mean_net(rows: List[Dict[str, object]], *, axis_set: str, h: int
                    ) -> Optional[float]:
    """축집합·지평의 후보가중 pooled mean_net(전체 지형 평균)."""
    sel = select(rows, axis_set=axis_set, h=h)
    total_n = sum(int(r["n"]) for r in sel)
    if total_n == 0:
        return None
    return sum(float(r["mean_net"]) * int(r["n"]) for r in sel) / total_n


def _key(row: Dict[str, object]) -> Tuple:
    return tuple(row[k] for k in _CELL_KEY)


def _view(row: Dict[str, object]) -> Dict[str, object]:
    """요약 JSON·표에 담을 셀 축약 뷰."""
    keys = ("time_label", "updown_q", "mktcap_b", "h", "n", "mean_net",
            "p_net_ge0", "p_net_ge1", "ci_low", "ci_high", "censor_rate",
            "winrate", "payoff", "year2022_sign")
    return {k: row[k] for k in keys}
