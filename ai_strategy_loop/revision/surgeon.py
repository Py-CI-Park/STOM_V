"""리프 대수술(QSP3 P1) — drop_leaf 제안·적용·검증.

원리(사용자 방법론): "이런 매수 특징으로 매수된 것은 손실이 많구나 → 그 영역 제거".
여기서 영역 = HIER 리프(시간밴드×시총단계). 제거 후보는 **설계+홀드아웃 양쪽에서
손실**인 리프만(가짜 흑자/설계 전용 손실에 속지 않기 위해 — DROP3 프로브 실증).

빼기 추정은 후보 '순위'에만 쓴다 — 채택은 항상 엔진 재백테 실측(재유입 효과가
추정 개선의 21~38% 를 되가져간다는 실측: limitation_ledger 2026-07-31 행).

드롭 인코딩: 리프의 첫 절 `if not (...):` 줄을 `if True:  # DROP_LEAF …` 로 교체
→ 해당 리프 진입 시 항상 매수=False. hier_ast 는 이 절을 ident '?' 로 파싱하므로
"드롭된 리프 = 첫 절 ident '?'" 가 결정적 판별 규칙이 된다(파서 호환 P0 검증).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ai_strategy_loop.autopsy.label_dataset import enrich
from ai_strategy_loop.revision.hier_ast import parse_leaves
from ai_strategy_loop.revision.proposer import _leaf_key_from_labels

DROP_MARK = "DROP_LEAF"
# 제거 후보 최소 규모 — 설계 손실이 총손실의 이 비율 미만인 리프는 수술 가치 없음.
MIN_LOSS_SHARE = 0.02


def _leaf_pnl(csv_path: str) -> pd.DataFrame:
    df = enrich(pd.read_csv(csv_path, encoding="utf-8-sig")).df
    g = df.groupby(["leaf_time", "leaf_cap"]).agg(n=("수익금", "size"), pnl=("수익금", "sum"))
    return g


def is_dropped(code: str, leaf_key: Tuple[str, str]) -> bool:
    hier = parse_leaves(code)
    cl = hier.leaves.get(leaf_key) if hier.ok else None
    return bool(cl) and cl[0].ident == "?"


def propose_drops(design_csv: str, holdout_csv: str, buy_code: str, *,
                  top_k: int = 3,
                  exclude_leaves: Optional[set] = None,
                  timeframe: str = "tick") -> List[Dict[str, Any]]:
    """설계+홀드아웃 양쪽 손실 리프 → drop 명세(설계 손실 큰 순, top_k)."""
    hier = parse_leaves(buy_code)
    if not hier.ok:
        return []
    d = _leaf_pnl(design_csv)
    h = _leaf_pnl(holdout_csv)
    m = d.join(h, lsuffix="_d", rsuffix="_h", how="inner")
    total_loss = abs(float(m.loc[m["pnl_d"] < 0, "pnl_d"].sum())) or 1.0
    m = m[(m["pnl_d"] < 0) & (m["pnl_h"] < 0)].sort_values("pnl_d")
    excluded = exclude_leaves or set()
    specs: List[Dict[str, Any]] = []
    for (lt, lc), row in m.iterrows():
        if len(specs) >= top_k:
            break
        leaf_label = f"{lt}×{lc}"
        if leaf_label in excluded:
            continue
        if abs(float(row["pnl_d"])) / total_loss < MIN_LOSS_SHARE:
            continue
        leaf_key = _leaf_key_from_labels(str(lt), str(lc), hier.leaves, timeframe)
        if leaf_key is None or is_dropped(buy_code, leaf_key):
            continue
        specs.append({
            "action": "drop_leaf",
            "leaf": list(leaf_key),
            "leaf_label": leaf_label,
            "est_delta_design": -float(row["pnl_d"]),    # 제거 시 기대 이득(빼기 추정).
            "est_delta_holdout": -float(row["pnl_h"]),
            "evidence": {"n_design": int(row["n_d"]), "pnl_design": float(row["pnl_d"]),
                         "n_holdout": int(row["n_h"]), "pnl_holdout": float(row["pnl_h"]),
                         "loss_share_design": float(abs(row["pnl_d"]) / total_loss)},
            "change": f"DROP {leaf_label} (설계 {row['pnl_d']:,.0f}·{int(row['n_d'])}건 / "
                      f"홀드 {row['pnl_h']:,.0f}·{int(row['n_h'])}건 양쪽 손실)",
        })
    return specs


def apply_drop(spec: Dict[str, Any], code: str) -> Tuple[Optional[str], str]:
    """드롭 명세 적용 — 대상 리프의 첫 절 줄만 `if True:` 로 교체."""
    hier = parse_leaves(code)
    if not hier.ok:
        return None, f"hier parse 실패: {hier.reason}"
    leaf_key = tuple(spec.get("leaf") or ())
    clauses = hier.leaves.get(leaf_key)  # type: ignore[arg-type]
    if not clauses:
        return None, f"리프 없음: {leaf_key}"
    if clauses[0].ident == "?":
        return None, "이미 드롭된 리프"
    lineno = clauses[0].lineno
    lines = code.split("\n")
    if not (1 <= lineno <= len(lines)):
        return None, f"절 줄 번호 이상: {lineno}"
    old_line = lines[lineno - 1]
    indent = old_line[:len(old_line) - len(old_line.lstrip())]
    head = old_line.lstrip()
    if not (head.startswith("if ") or head.startswith("elif ")):
        return None, f"첫 절 줄 형태 예상 밖: {head[:40]}"
    kw = "elif" if head.startswith("elif") else "if"
    lines[lineno - 1] = f"{indent}{kw} True:  # {DROP_MARK} — {spec.get('leaf_label')}"
    new_code = "\n".join(lines)
    try:
        compile(new_code, "<drop>", "exec")
    except SyntaxError as e:
        return None, f"드롭 결과 구문 오류: {e}"
    return new_code, ""


def verify_drop(spec: Dict[str, Any], old_code: str, new_code: str) -> Tuple[bool, str]:
    """의도-일치 검증(드롭 전용) — diff 가 '대상 리프의 첫 절 무력화' 뿐인지.

    규칙: ① 리프 키 집합 동일 ② 대상 외 모든 리프의 (ident, consts) 열 완전 동일
         ③ 대상 리프: 새 첫 절 ident == '?', 나머지 절은 기존 2번째 이후와 동일.
    """
    old_h, new_h = parse_leaves(old_code), parse_leaves(new_code)
    if not old_h.ok or not new_h.ok:
        return False, "parse 실패"
    if set(old_h.leaves) != set(new_h.leaves):
        return False, "V_DROP: 리프 키 집합 변경"
    target = tuple(spec.get("leaf") or ())
    for key in old_h.leaves:
        o = [(c.ident, tuple(c.consts)) for c in old_h.leaves[key]]
        n = [(c.ident, tuple(c.consts)) for c in new_h.leaves[key]]
        if key == target:
            if not n or n[0][0] != "?":
                return False, "V_DROP: 대상 리프 첫 절이 무력화되지 않음"
            if n[1:] != o[1:]:
                return False, "V_DROP: 대상 리프의 나머지 절 변형"
        elif n != o:
            return False, f"V_DROP: 명세 밖 리프 변경 {key}"
    return True, ""
