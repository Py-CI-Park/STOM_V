"""P3 — 연구 데이터 파이프라인: 계보 트리 + 버전 diff + run 비교.

`loop_runs.db`(controller/state.py)에 누적된 generations를 위에 얹는 **읽기 전용
조회 레이어**다. 세 가지를 제공한다:

  1. 계보 트리(build_lineage_tree): generations의 parent_gen 체인을 따라
     시드→best 경로를 추적한다. "어느 세대가 어느 세대를 개선했나"를 트리로.
  2. 버전 diff(diff_generations): 두 세대의 전략 코드를 namespaced 이름으로
     조회해 텍스트 diff를 내고, 지표(graded/MDD/수익/거래) diff를 함께 낸다.
     **코드 전문을 DB에 복제 저장하지 않는다** — stockbuy/stocksell에 namespaced로
     이미 존재하는 코드를 loop._read_strategy_code로 재조회한다(M5 역정규화 제거).
  3. run 비교(compare_runs): loop_runs.db의 여러 run을 지표/우승전략으로 비교한다.
     **cli/history.py(compare_runs)는 backtest_history.db용이라 여기 못 쓴다**(Critic M5)
     — loop_runs.db 위에 직접 구현한다.

설계 원칙(SIMPLICITY): 읽기 전용·무예외 계약(데이터 모양 문제는 빈 결과/note로
표준화). 작은 함수. 한국어 주석.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ai_strategy_loop.controller.state import LoopState


# =====================================================================
# 1. 계보 트리 — parent_gen 체인으로 시드→best 추적.
# =====================================================================
@dataclass
class LineageNode:
    """계보 트리의 한 세대 노드(대시보드/조회용 요약)."""

    gen_no: int
    parent_gen: Optional[int]
    graded_score: float
    gate_passed: bool
    trade_count: int
    mdd: float
    profit: float
    gist: str
    diff_from_parent: str
    children: List[int] = field(default_factory=list)


def build_lineage_tree(state: LoopState, run_id: str) -> Dict[str, Any]:
    """한 run의 세대들을 parent_gen 체인으로 묶어 계보 요약을 만든다.

    각 세대 노드는 부모(parent_gen)와 자식(children) 링크를 가진다. best 세대
    (graded 최고)에서 부모 체인을 거슬러 올라가는 best_path(시드→best 경로)도 낸다.

    Args:
        state: LoopState(SQLite). 읽기 전용으로만 쓴다.
        run_id: 조회할 run.

    Returns:
        {
          "run_id": str,
          "nodes": [LineageNode dict ...]  (gen_no 순),
          "best_gen": int,                 (graded 최고 세대; 없으면 -1),
          "best_path": [int ...],          (시드→best 의 gen_no 경로),
          "roots": [int ...],              (parent_gen 없는 세대들),
        }
    """
    gens = state.get_generations(run_id)
    if not gens:
        return {"run_id": run_id, "nodes": [], "best_gen": -1, "best_path": [], "roots": []}

    # gen_no → 노드. parent_gen은 None이거나 같은 run의 다른 gen_no.
    by_gen: Dict[int, LineageNode] = {}
    for g in gens:
        gen_no = int(g.get("gen_no", -1))
        parent = g.get("parent_gen")
        by_gen[gen_no] = LineageNode(
            gen_no=gen_no,
            parent_gen=(None if parent is None else int(parent)),
            graded_score=float(g.get("score", 0.0) or 0.0),
            gate_passed=bool(g.get("gate_passed")),
            trade_count=int(g.get("trade_count", 0) or 0),
            mdd=float(g.get("mdd", 0.0) or 0.0),
            profit=float(g.get("profit", 0.0) or 0.0),
            gist=str(g.get("strategy_gist", "") or ""),
            diff_from_parent=str(g.get("diff_from_parent", "") or ""),
        )

    # 자식 링크 채우기(부모가 같은 run에 존재할 때만).
    roots: List[int] = []
    for gen_no, node in by_gen.items():
        if node.parent_gen is not None and node.parent_gen in by_gen:
            by_gen[node.parent_gen].children.append(gen_no)
        else:
            roots.append(gen_no)

    # best = graded 최고 세대.
    best_gen = max(by_gen, key=lambda gn: by_gen[gn].graded_score)

    # best_path: best에서 parent_gen 체인을 거슬러 올라간 뒤 뒤집어 시드→best 순.
    path: List[int] = []
    seen = set()
    cur: Optional[int] = best_gen
    while cur is not None and cur in by_gen and cur not in seen:
        path.append(cur)
        seen.add(cur)
        cur = by_gen[cur].parent_gen
    path.reverse()

    nodes = [_node_to_dict(by_gen[gn]) for gn in sorted(by_gen)]
    return {
        "run_id": run_id,
        "nodes": nodes,
        "best_gen": best_gen,
        "best_path": path,
        "roots": sorted(roots),
    }


def _node_to_dict(n: LineageNode) -> Dict[str, Any]:
    """LineageNode를 JSON-직렬화 가능한 dict로(page_data/조회용)."""
    return {
        "gen_no": n.gen_no,
        "parent_gen": n.parent_gen,
        "graded_score": round(n.graded_score, 6),
        "gate_passed": n.gate_passed,
        "trade_count": n.trade_count,
        "mdd": round(n.mdd, 4),
        "profit": round(n.profit, 2),
        "gist": n.gist,
        "diff_from_parent": n.diff_from_parent,
        "children": sorted(n.children),
    }


# =====================================================================
# 2. 버전 diff — 두 세대의 코드(namespaced 재조회) + 지표 diff.
# =====================================================================
def diff_generations(
    state: LoopState,
    run_id: str,
    gen_a: int,
    gen_b: int,
    *,
    kind: str = "buy",
) -> Dict[str, Any]:
    """두 세대(gen_a→gen_b) 사이의 코드 텍스트 diff + 지표 diff를 낸다.

    코드는 generations 행의 buy_name/sell_name(namespaced)을 통해
    stockbuy/stocksell에서 재조회한다(loop._read_strategy_code). **코드 전문을
    loop_runs.db에 복제 저장하지 않으므로** 여기서 namespaced 이름으로 가져온다.

    Args:
        state: LoopState(SQLite).
        run_id: 조회 run.
        gen_a: 비교 기준(이전) 세대 번호.
        gen_b: 비교 대상(이후) 세대 번호.
        kind: 'buy' | 'sell'. 어느 쪽 전략 코드를 diff할지.

    Returns:
        {
          "run_id", "gen_a", "gen_b", "kind",
          "code_diff": str,        (unified diff; 코드 조회 실패면 빈 문자열),
          "metrics_diff": {지표: {a, b, delta}},
          "note": str,             (조회 실패/누락 사유; 정상이면 ""),
        }
    """
    from ai_strategy_loop.controller.loop import _read_strategy_code  # noqa: PLC0415

    rows = {int(g.get("gen_no", -1)): g for g in state.get_generations(run_id)}
    ra = rows.get(gen_a)
    rb = rows.get(gen_b)
    if ra is None or rb is None:
        missing = [str(g) for g, r in ((gen_a, ra), (gen_b, rb)) if r is None]
        return {
            "run_id": run_id, "gen_a": gen_a, "gen_b": gen_b, "kind": kind,
            "code_diff": "", "metrics_diff": {},
            "note": f"세대 미존재: gen {', '.join(missing)}",
        }

    name_key = "buy_name" if kind == "buy" else "sell_name"
    code_a = _read_strategy_code(ra.get(name_key), kind) or ""
    code_b = _read_strategy_code(rb.get(name_key), kind) or ""

    note = ""
    if not code_a or not code_b:
        # 코드 조회 실패(namespaced 이름이 DB에 없음 등) — diff는 비우고 사유만.
        note = "전략 코드 조회 실패(namespaced 이름 미존재 가능) — 지표 diff만 제공."
    code_diff = _unified_diff(code_a, code_b, gen_a, gen_b, kind) if (code_a and code_b) else ""

    metrics_diff = _metrics_delta(ra, rb)
    return {
        "run_id": run_id, "gen_a": gen_a, "gen_b": gen_b, "kind": kind,
        "code_diff": code_diff, "metrics_diff": metrics_diff, "note": note,
    }


def _unified_diff(code_a: str, code_b: str, gen_a: int, gen_b: int, kind: str) -> str:
    """두 코드 문자열의 unified diff 텍스트를 만든다."""
    diff = difflib.unified_diff(
        code_a.splitlines(),
        code_b.splitlines(),
        fromfile=f"gen{gen_a}_{kind}",
        tofile=f"gen{gen_b}_{kind}",
        lineterm="",
    )
    return "\n".join(diff)


# 지표 diff에 노출할 컬럼(작은 수치 집합). score=graded.
_METRIC_KEYS = ("score", "trade_count", "mdd", "profit", "calmar", "uptrend_r2")


def _metrics_delta(ra: Dict[str, Any], rb: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """두 세대 행의 지표 a→b 델타를 낸다(b - a)."""
    out: Dict[str, Dict[str, float]] = {}
    for key in _METRIC_KEYS:
        a = float(ra.get(key, 0.0) or 0.0)
        b = float(rb.get(key, 0.0) or 0.0)
        out[key] = {"a": round(a, 6), "b": round(b, 6), "delta": round(b - a, 6)}
    return out


# =====================================================================
# 3. run 비교 — loop_runs.db의 여러 run을 직접 비교(cli/history.py 아님).
# =====================================================================
def compare_runs(
    state: LoopState,
    run_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """loop_runs.db의 여러 run을 지표/우승전략으로 비교한다(누적 관찰).

    각 run의 세대 수·best graded·게이트 통과 세대 수·우승(하드게이트 통과 중
    최고) 전략을 한 행으로 요약한다. cli/history.py(backtest_history.db용)와는
    무관한 신규 구현이다(loop_runs.db 직접 조회).

    Args:
        state: LoopState(SQLite).
        run_ids: 비교할 run id 목록. None이면 모든 run.

    Returns:
        {"runs": [run 요약 dict ...], "count": int}
    """
    all_runs = {r["run_id"]: r for r in state.list_runs()}
    target_ids = run_ids if run_ids is not None else list(all_runs.keys())

    summaries: List[Dict[str, Any]] = []
    for rid in target_ids:
        run_row = all_runs.get(rid)
        gens = state.get_generations(rid)
        summaries.append(_summarize_run(rid, run_row, gens))
    return {"runs": summaries, "count": len(summaries)}


def _summarize_run(
    run_id: str,
    run_row: Optional[Dict[str, Any]],
    gens: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """한 run의 비교용 요약 행을 만든다(지표 + 우승전략)."""
    gen_count = len(gens)
    gate_passed = [g for g in gens if bool(g.get("gate_passed"))]
    best_graded = max((float(g.get("score", 0.0) or 0.0) for g in gens), default=0.0)

    # 우승전략: 하드게이트 통과 세대 중 graded 최고(없으면 None).
    winner = None
    if gate_passed:
        w = max(gate_passed, key=lambda g: float(g.get("score", 0.0) or 0.0))
        winner = {
            "gen_no": int(w.get("gen_no", -1)),
            "buy_name": w.get("buy_name"),
            "sell_name": w.get("sell_name"),
            "graded_score": round(float(w.get("score", 0.0) or 0.0), 6),
            "mdd": round(float(w.get("mdd", 0.0) or 0.0), 4),
            "profit": round(float(w.get("profit", 0.0) or 0.0), 2),
            "trade_count": int(w.get("trade_count", 0) or 0),
        }

    return {
        "run_id": run_id,
        "status": (run_row or {}).get("status"),
        "started_at": (run_row or {}).get("started_at"),
        "gen_count": gen_count,
        "best_graded": round(best_graded, 6),
        "gate_passed_count": len(gate_passed),
        "winner": winner,
    }


# =====================================================================
# page_data 직렬화(LIVE 계보 패널용).
# =====================================================================
def to_page_data(state: LoopState, run_id: str, *, top_nodes: int = 12) -> Dict[str, Any]:
    """현재 run의 계보 요약을 대시보드 LIVE 패널용 page_data["lineage"]로 만든다.

    계보 트리 전체가 크면 페이로드가 커지므로 best_path + 최근 top_nodes개만 노출한다.
    JSON-직렬화 가능한 기본 타입만 담는다.
    """
    tree = build_lineage_tree(state, run_id)
    nodes = tree["nodes"]
    # 최근 세대 우선(gen_no 큰 순) top_nodes개만 + best_path는 항상 포함.
    recent = sorted(nodes, key=lambda n: n["gen_no"], reverse=True)[:top_nodes]
    recent_by_gen = {n["gen_no"] for n in recent}
    best_path_set = set(tree["best_path"])
    shown = [n for n in nodes if n["gen_no"] in recent_by_gen or n["gen_no"] in best_path_set]
    return {
        "status": "ok",
        "run_id": run_id,
        "best_gen": tree["best_gen"],
        "best_path": tree["best_path"],
        "node_count": len(nodes),
        "nodes": shown,
    }
