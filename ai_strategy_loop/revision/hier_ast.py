"""QSP HIER 계층 조건식의 AST 해부 — 리프 좌표계 추출과 골격 지문.

계층 골격(hierarchy_preservation.md 정본):

    elif 시분초 < 90200:                # ── 시간밴드 문맥
        if 시가총액 < 3000:              # ── 시총단계 문맥
            if not (0.5 <= 등락율 <= 25.0):        # ── 리프 절(경계값 = 가변)
                매수 = False
            elif not (-3.0 <= 시가등락율 < 10.0):
                ...

이 모듈이 제공하는 두 가지:
  parse_leaves(code) : 리프 좌표(밴드×시총)별 절 목록 [(절 식별자, 경계 상수들)].
                       절 식별자 = 비교식의 변수 부분 텍스트(상수 마스킹) — 골격의 일부.
  skeleton_fp(code)  : 상수를 마스킹한 AST 지문(SHA1). 골격 불변 검증의 근거 —
                       숫자 경계 외 무엇이든 바뀌면 지문이 달라진다.

의도-일치 게이트(intent_gate)와 제안 적용(proposer.apply)이 공유한다.
무예외 지향: 파싱 실패는 빈 구조/None 으로 반환하고 호출측이 판정한다.
"""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 밴드/시총 문맥을 식별하는 변수명(QSP 골격 계약).
_BAND_VAR = "시분초"
_CAP_VAR = "시가총액"


@dataclass
class LeafClause:
    """리프 안 절 하나 — 식별자(골격)와 경계 상수(가변)."""

    ident: str                 # 상수 마스킹된 비교식 텍스트(예: "?<=등락율<=?")
    consts: Tuple[float, ...]  # 경계 상수들(등장 순서)
    lineno: int                # 원본 코드 시작 줄(적용/디프 표시용)


@dataclass
class HierMap:
    """계층 해부 결과."""

    leaves: Dict[Tuple[str, str], List[LeafClause]] = field(default_factory=dict)
    band_edges: List[int] = field(default_factory=list)
    cap_edges: List[int] = field(default_factory=list)
    ok: bool = False
    reason: str = ""


class _ConstMask(ast.NodeTransformer):
    def visit_Constant(self, node):  # noqa: N802
        return ast.copy_location(ast.Constant(value=None), node)


def skeleton_fp(code: str) -> Optional[str]:
    """상수 마스킹 AST 지문. 구문 오류면 None."""
    try:
        tree = ast.parse(str(code or ""))
    except SyntaxError:
        return None
    masked = _ConstMask().visit(tree)
    return hashlib.sha1(ast.dump(masked).encode()).hexdigest()


def _expr_ident(node: ast.expr) -> Tuple[str, Tuple[float, ...]]:
    """비교식 → (상수 마스킹 식별자, 상수 목록). 골격/가변 분리의 핵심."""
    consts: List[float] = []

    class _Collect(ast.NodeTransformer):
        def visit_Constant(self, n):  # noqa: N802
            if isinstance(n.value, (int, float)):
                consts.append(float(n.value))
                return ast.copy_location(ast.Constant(value="?"), n)
            return n

    masked = _Collect().visit(ast.parse(ast.unparse(node)).body[0].value)  # type: ignore[attr-defined]
    ident = ast.unparse(masked).replace("'?'", "?").replace(" ", "")
    return ident, tuple(consts)


def _band_label(test: ast.expr) -> Optional[str]:
    """시분초 비교식 → 밴드 라벨("<90200" / "90200<=..<90500" 식 정규화)."""
    try:
        text = ast.unparse(test).replace(" ", "")
    except Exception:  # noqa: BLE001
        return None
    return text if _BAND_VAR in text else None


def _cap_label(test: ast.expr) -> Optional[str]:
    try:
        text = ast.unparse(test).replace(" ", "")
    except Exception:  # noqa: BLE001
        return None
    return text if _CAP_VAR in text else None


def _iter_if_chain(node: ast.If):
    """if/elif 사다리를 (test, body) 순서로 평탄화."""
    cur: Optional[ast.stmt] = node
    while isinstance(cur, ast.If):
        yield cur.test, cur.body
        nxt = cur.orelse
        cur = nxt[0] if len(nxt) == 1 and isinstance(nxt[0], ast.If) else None
        if cur is None and nxt and not isinstance(nxt[0], ast.If):
            yield None, nxt  # else 블록
            return


def _leaf_clauses(body: List[ast.stmt]) -> List[LeafClause]:
    """리프(시총 분기 본문)의 `if not (...)` 절 사다리 → LeafClause 목록."""
    out: List[LeafClause] = []
    for stmt in body:
        if not isinstance(stmt, ast.If):
            continue
        for test, _ in _iter_if_chain(stmt):
            if test is None:
                continue
            inner = test
            if isinstance(inner, ast.UnaryOp) and isinstance(inner.op, ast.Not):
                inner = inner.operand
            ident, consts = _expr_ident(inner)
            out.append(LeafClause(ident=ident, consts=consts, lineno=test.lineno))
    return out


def parse_leaves(code: str) -> HierMap:
    """HIER 매수식 → 리프 좌표별 절 목록. 골격이 계약과 다르면 ok=False."""
    result = HierMap()
    try:
        tree = ast.parse(str(code or ""))
    except SyntaxError as exc:
        result.reason = f"syntax: {exc}"
        return result

    # 최상위 if/elif 사다리에서 밴드 분기를 찾는다.
    top_ifs = [n for n in tree.body if isinstance(n, ast.If)]
    if not top_ifs:
        result.reason = "no top-level if chain"
        return result
    found_band = False
    for top in top_ifs:
        for test, body in _iter_if_chain(top):
            if test is None:
                continue
            band = _band_label(test)
            if band is None:
                continue
            found_band = True
            # 밴드 본문에서 시총 사다리를 찾는다.
            for stmt in body:
                if not isinstance(stmt, ast.If):
                    continue
                for cap_test, cap_body in _iter_if_chain(stmt):
                    if cap_test is None:
                        continue
                    cap = _cap_label(cap_test)
                    if cap is None:
                        continue
                    result.leaves[(band, cap)] = _leaf_clauses(cap_body)
    if not found_band:
        result.reason = "no band branches (시분초)"
        return result
    if not result.leaves:
        result.reason = "no cap leaves (시가총액)"
        return result
    result.ok = True
    return result


@dataclass
class ConstDiff:
    """두 코드 사이 상수 변경 1건 — 어느 리프의 어느 절에서 무엇이 바뀌었나."""

    leaf: Tuple[str, str]
    clause_ident: str
    old: Tuple[float, ...]
    new: Tuple[float, ...]


def diff_leaves(old_code: str, new_code: str) -> Tuple[Optional[List[ConstDiff]], str]:
    """골격 동일 전제 하에 리프 절 경계 변경 목록을 만든다.

    반환 (diffs, reason). 골격이 다르면 (None, 사유) — 게이트가 즉시 위반 처리.
    """
    if skeleton_fp(old_code) is None or skeleton_fp(new_code) is None:
        return None, "syntax error"
    if skeleton_fp(old_code) != skeleton_fp(new_code):
        return None, "skeleton changed (구조 변경 — 골격 불변 위반)"
    old_map, new_map = parse_leaves(old_code), parse_leaves(new_code)
    if not (old_map.ok and new_map.ok):
        return None, f"hier parse 실패: old={old_map.reason} new={new_map.reason}"
    diffs: List[ConstDiff] = []
    for leaf, old_clauses in old_map.leaves.items():
        new_clauses = new_map.leaves.get(leaf, [])
        for oc, nc in zip(old_clauses, new_clauses):
            if oc.ident != nc.ident:      # 골격 동일이면 발생 불가(방어).
                return None, f"clause ident mismatch at {leaf}"
            if oc.consts != nc.consts:
                diffs.append(ConstDiff(leaf=leaf, clause_ident=oc.ident,
                                       old=oc.consts, new=nc.consts))
    return diffs, "ok"
