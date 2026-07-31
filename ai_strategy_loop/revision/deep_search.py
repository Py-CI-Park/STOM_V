"""깊이 탐색 엔진(QSP5) — 조건식의 실제 깊이만큼 조합을 탐색한다.

배경(사용자 지적): 실제 조건식은 리프당 8~10절이고 양측범위(a<x≤b)를 48개나 쓰는데,
기존 탐색기는 라운드당 단측 임계 1개만 발굴했다. 반면 깊이를 그냥 늘리면 과최적이
폭발한다는 것도 실측됐다(B1×소형 리프: 깊이1 표본외 유지율 5% · 깊이1.5 양측범위
**−11%(부호 반전)** · 깊이2 두변수 AND 26%).

그래서 이 엔진의 설계 원칙은 **"깊이당 지불"**이다:
    절을 하나 더 붙이려면, 그 절이 **표본외 건당 엣지를 개선**해야 한다.
설계구간 성적만 좋아지는 확장은 그 자리에서 기각한다. 여기에 다중 폴드 재현
(autopsy.folds)을 얹어 '특정 국면 산물'을 걸러낸다.

문법(조건식으로 그대로 옮길 수 있는 형태만):
    · 단측      : `변수 > t`, `변수 <= t`
    · 양측범위  : `lo < 변수 <= hi`
    · AND 결합  : 위 절들을 리프 절 체인에 순차 추가(엔진에서 자연히 AND)
구간함수(체결강도평균 등)는 창 인자 문법이 필요해 v1 에서 제외한다(filtersmith 와 동일).
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from ai_strategy_loop.autopsy import folds as _folds
from ai_strategy_loop.revision.filtersmith import (
    MIN_KEEP_N, QUANTS, _leaf_frames, _runtime_var)
from ai_strategy_loop.revision.hier_ast import parse_leaves
from ai_strategy_loop.revision.proposer import _leaf_key_from_labels, _round_sig

BEAM_WIDTH = 6          # 각 깊이에서 남길 후보 수.
MAX_DEPTH = 3           # 리프당 추가 절 상한(실제 조건식 8~10절 대비 보수적 시작).
MIN_HOLDOUT_GAIN = 0.0  # 깊이당 지불: 표본외 건당 엣지가 이만큼은 좋아져야 채택.


def _clause_mask(df: pd.DataFrame, cl: Dict[str, Any]) -> pd.Series:
    v = pd.to_numeric(df[cl["feature"]], errors="coerce")
    if cl["kind"] == "band":
        return (v > cl["lo"]) & (v <= cl["hi"])
    return (v > cl["t"]) if cl["op"] == ">" else (v <= cl["t"])


def _combo_mask(df: pd.DataFrame, combo: Sequence[Dict[str, Any]]) -> pd.Series:
    m = pd.Series(True, index=df.index)
    for cl in combo:
        m &= _clause_mask(df, cl).fillna(False)
    return m


def _clause_text(cl: Dict[str, Any]) -> str:
    if cl["kind"] == "band":
        return f"{cl['lo']} < {cl['var']} <= {cl['hi']}"
    return f"{cl['var']} {cl['op']} {cl['t']}"


def _eval(sub_d, sub_h, combo) -> Optional[Dict[str, Any]]:
    kd = _combo_mask(sub_d, combo)
    kh = _combo_mask(sub_h, combo)
    n_d, n_h = int(kd.sum()), int(kh.sum())
    if n_d < MIN_KEEP_N or n_h < MIN_KEEP_N:
        return None
    p_d = float(pd.to_numeric(sub_d.loc[kd, "수익금"], errors="coerce").sum())
    p_h = float(pd.to_numeric(sub_h.loc[kh, "수익금"], errors="coerce").sum())
    return {"n_d": n_d, "n_h": n_h, "pnl_d": p_d, "pnl_h": p_h,
            "pt_d": p_d / n_d, "pt_h": p_h / n_h, "kept_d": kd, "kept_h": kh}


def _atoms(sub_d: pd.DataFrame, feats: Sequence[str],
           used_vars: Sequence[str]) -> List[Dict[str, Any]]:
    """탐색 원자 절 목록 — 단측 + 양측범위."""
    out: List[Dict[str, Any]] = []
    for f in feats:
        var = _runtime_var(f)
        if var is None or var in used_vars:
            continue
        v = pd.to_numeric(sub_d[f], errors="coerce")
        qs = sorted({_round_sig(float(v.quantile(q))) for q in QUANTS})
        for t in qs:
            out.append({"kind": "side", "feature": f, "var": var, "op": ">", "t": t})
            out.append({"kind": "side", "feature": f, "var": var, "op": "<=", "t": t})
        for lo, hi in itertools.combinations(qs, 2):
            out.append({"kind": "band", "feature": f, "var": var, "lo": lo, "hi": hi})
    return out


def search_leaf(sub_d: pd.DataFrame, sub_h: pd.DataFrame, feats: Sequence[str], *,
                beam: int = BEAM_WIDTH, max_depth: int = MAX_DEPTH,
                min_holdout_gain: float = MIN_HOLDOUT_GAIN) -> List[Dict[str, Any]]:
    """한 리프 안에서 빔서치 — 깊이를 늘릴 때마다 표본외 지불을 요구한다."""
    base = _eval(sub_d, sub_h, [])
    if base is None:
        return []
    frontier: List[Tuple[List[Dict[str, Any]], Dict[str, Any]]] = [([], base)]
    accepted: List[Dict[str, Any]] = []
    for depth in range(1, max_depth + 1):
        nxt: List[Tuple[List[Dict[str, Any]], Dict[str, Any]]] = []
        for combo, prev in frontier:
            used = [c["var"] for c in combo]
            for atom in _atoms(sub_d, feats, used):
                cand = combo + [atom]
                ev = _eval(sub_d, sub_h, cand)
                if ev is None:
                    continue
                # 깊이당 지불: 설계·표본외 **양쪽** 건당 엣지가 직전보다 좋아져야 한다.
                if ev["pt_d"] <= prev["pt_d"] or ev["pt_h"] <= prev["pt_h"] + min_holdout_gain:
                    continue
                nxt.append((cand, ev))
        if not nxt:
            break
        # 표본외 건당 엣지 기준 상위 beam 개만 남긴다(설계 기준으로 고르면 과최적).
        nxt.sort(key=lambda ce: ce[1]["pt_h"], reverse=True)
        nxt = nxt[:beam]
        for combo, ev in nxt:
            if ev["pnl_d"] > 0 and ev["pnl_h"] > 0:
                rep_d = _folds.fold_report(sub_d.loc[ev["kept_d"]])
                rep_h = _folds.fold_report(sub_h.loc[ev["kept_h"]])
                accepted.append({"depth": depth, "clauses": combo, "eval": ev,
                                 "folds_design": rep_d, "folds_holdout": rep_h,
                                 "folds_ok": bool(rep_d["passed"])})
        frontier = nxt
    return accepted


def propose_deep(design_csv: str, holdout_csv: str, buy_code: str, *,
                 top_k: int = 3, exclude: Optional[set] = None,
                 timeframe: str = "tick", max_depth: int = MAX_DEPTH,
                 beam: int = BEAM_WIDTH) -> List[Dict[str, Any]]:
    """손실 리프들에 깊이 탐색을 돌려 add_filter_deep 명세를 만든다."""
    hier = parse_leaves(buy_code)
    if not hier.ok:
        return []
    df_d, leaves_d = _leaf_frames(design_csv)
    _, leaves_h = _leaf_frames(holdout_csv)
    feats = [c for c in df_d.columns if _runtime_var(c)]
    excluded = exclude or set()
    specs: List[Dict[str, Any]] = []
    for (lt, lc), sub in sorted(leaves_d.items(), key=lambda kv: kv[1]["수익금"].sum()):
        if float(sub["수익금"].sum()) >= 0:
            continue
        leaf_label = f"{lt}×{lc}"
        if leaf_label in excluded:
            continue
        leaf_key = _leaf_key_from_labels(str(lt), str(lc), hier.leaves, timeframe)
        if leaf_key is None:
            continue
        clauses = hier.leaves[leaf_key]
        if clauses and clauses[0].ident == "?":
            continue
        sub_h = leaves_h.get((lt, lc))
        if sub_h is None or sub_h.empty:
            continue
        found = search_leaf(sub, sub_h, feats, beam=beam, max_depth=max_depth)
        ok = [f for f in found if f["folds_ok"]]
        if not ok:
            continue
        # 리프당 최선 1개 — 표본외 건당 엣지 최대(동률이면 얕은 깊이 우선).
        best = max(ok, key=lambda f: (f["eval"]["pt_h"], -f["depth"]))
        ev = best["eval"]
        specs.append({
            "action": "add_filter_deep", "leaf": list(leaf_key), "leaf_label": leaf_label,
            "depth": best["depth"],
            "clauses": [{k: v for k, v in c.items()} for c in best["clauses"]],
            "rescue": True,
            "est_delta_design": -float(pd.to_numeric(
                sub.loc[~ev["kept_d"], "수익금"], errors="coerce").sum()),
            "est_delta_holdout": -float(pd.to_numeric(
                sub_h.loc[~ev["kept_h"], "수익금"], errors="coerce").sum()),
            "evidence": {
                "kept_n_design": ev["n_d"], "kept_n_holdout": ev["n_h"],
                "kept_pnl_design": ev["pnl_d"], "kept_pnl_holdout": ev["pnl_h"],
                "kept_per_trade_design": ev["pt_d"], "kept_per_trade_holdout": ev["pt_h"],
                "folds_design": _folds.summarize(best["folds_design"]),
                "folds_holdout": _folds.summarize(best["folds_holdout"]),
            },
            "change": (f"DEEP(d{best['depth']}) {leaf_label} · "
                       + " AND ".join(_clause_text(c) for c in best["clauses"])
                       + f" — 잔존 설계 {ev['pt_d']:+,.0f}원/건({ev['n_d']}건)"
                       f" · 표본외 {ev['pt_h']:+,.0f}원/건({ev['n_h']}건)"
                       f" · 폴드 {_folds.summarize(best['folds_design'])}"),
        })
        if len(specs) >= top_k:
            break
    return specs


def apply_deep(spec: Dict[str, Any], code: str) -> Tuple[Optional[str], str]:
    """깊이 명세를 리프 절 체인 끝에 N줄로 삽입(각 절이 AND 로 연결된다)."""
    hier = parse_leaves(code)
    if not hier.ok:
        return None, f"hier parse 실패: {hier.reason}"
    leaf_key = tuple(spec.get("leaf") or ())
    clauses = hier.leaves.get(leaf_key)  # type: ignore[arg-type]
    if not clauses:
        return None, f"리프 없음: {leaf_key}"
    if clauses[0].ident == "?":
        return None, "드롭된 리프에는 필터 추가 불가"
    last = clauses[-1]
    lines = code.split("\n")
    head_line = lines[last.lineno - 1]
    indent = head_line[:len(head_line) - len(head_line.lstrip())]
    insert_at = last.lineno + 1
    if insert_at > len(lines) or "매수" not in lines[insert_at - 1]:
        return None, f"마지막 절 본문 형태 예상 밖(줄 {insert_at})"
    new_lines: List[str] = []
    for cl in spec["clauses"]:
        new_lines.append(f"{indent}elif not ({_clause_text(cl)}):  # DEEP_FILTER — QSP5")
        new_lines.append(f"{indent}    매수 = False")
    lines[insert_at:insert_at] = new_lines
    new_code = "\n".join(lines)
    try:
        compile(new_code, "<deep>", "exec")
    except SyntaxError as e:
        return None, f"깊이 필터 구문 오류: {e}"
    return new_code, ""


def verify_deep(spec: Dict[str, Any], old_code: str, new_code: str) -> Tuple[bool, str]:
    """검증 — 삽입 줄 수 == 절 수×2, 그 외 diff 0, 대상 리프 절만 증가."""
    old_h, new_h = parse_leaves(old_code), parse_leaves(new_code)
    if not old_h.ok or not new_h.ok:
        return False, "parse 실패"
    if set(old_h.leaves) != set(new_h.leaves):
        return False, "V_DEEP: 리프 키 집합 변경"
    n_cl = len(spec.get("clauses") or [])
    old_lines, new_lines = old_code.split("\n"), new_code.split("\n")
    if len(new_lines) != len(old_lines) + n_cl * 2:
        return False, f"V_DEEP: 삽입 줄 수 ≠ {n_cl * 2}"
    ins_at = next((i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b),
                  len(old_lines))
    inserted = new_lines[ins_at:ins_at + n_cl * 2]
    if old_lines[ins_at:] != new_lines[ins_at + n_cl * 2:]:
        return False, "V_DEEP: 삽입 외 라인 변경 존재"
    for i in range(0, len(inserted), 2):
        if "DEEP_FILTER" not in inserted[i] or inserted[i + 1].strip() != "매수 = False":
            return False, "V_DEEP: 삽입 줄 형태 불일치"
    target = tuple(spec.get("leaf") or ())
    for key in old_h.leaves:
        o = [(c.ident, tuple(c.consts)) for c in old_h.leaves[key]]
        n = [(c.ident, tuple(c.consts)) for c in new_h.leaves[key]]
        if key == target:
            if len(n) != len(o) + n_cl or n[:len(o)] != o:
                return False, "V_DEEP: 기존 절 변형 또는 삽입 위치 이상"
        elif n != o:
            return False, f"V_DEEP: 명세 밖 리프 변경 {key}"
    return True, ""
