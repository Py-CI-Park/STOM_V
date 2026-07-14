"""B-ext 가지 파스 + 절→비트 매핑 + 절 컴파일 (봉인본 §4·§5·§14).

- enumerate_branches: 매수식 원문(엔진 idiom `매수=True` → if/elif 가드 → `if 매수: Buy`)의 생존 경로를
  저자 분기 단위로 열거. 각 분기 = (원자, negated) 목록 + conjunctive 플래그. 챔피언에서 902(24)/905(26)
  재현(테스트). negated = 만족 방향이 원자의 부정(bare kill-가드 `elif Y: 매수=False` → 만족=¬Y).
  비-conjunctive(가드에 OR·NOT(AND)) 분기는 제외(비트 AND 표현 불가).
- map_atom_to_bit: 원자 → 챔피언 39비트(정규화 + 연산 flip + bare `not` 스트립). D1 비트가 만족 극성을
  이미 인코딩하므로 bare 가드도 raw 원자로 매핑하면 극성이 맞다(챔피언 #4 라운드피겨 = ¬라운드피겨).
- compile_clause: 신규 절을 온셋 네임스페이스 위 벡터 술어로 컴파일(연쇄 비교 &·구간함수 call 재작성).
  가용 심볼(NAMESPACE_SYMBOLS + 구간함수 화이트리스트)만 → 아니면 U-보류.

read-only ast 파스. 엔진 0회.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional, Tuple

import numpy as np

from alpha_lab.clause_lab.clauses import NAMESPACE_SYMBOLS, RAW_EXPR

__all__ = [
    "AVAILABLE_SYMBOLS", "CALL_SYMBOL_MAP", "Branch", "ClauseInfo",
    "compile_clause", "enumerate_branches", "map_atom_to_bit", "normalize_atom",
]

CALL_SYMBOL_MAP: Dict[Tuple[str, Tuple], str] = {
    ("당일거래대금각도", (30,)): "당일거래대금각도30",
    ("초당거래대금평균", (30,)): "초당거래대금평균30",
    ("누적초당매수수량", (30,)): "누적초당매수수량30",
    ("누적초당매도수량", (30,)): "누적초당매도수량30",
    ("초당거래대금N", (1,)): "초당거래대금N1",
}
AVAILABLE_SYMBOLS = frozenset(NAMESPACE_SYMBOLS) | frozenset(CALL_SYMBOL_MAP.values())


def _norm(node: ast.AST) -> str:
    return " ".join(ast.unparse(node).split())


# ---------------------------------------------------------------------------
# 가지 열거 — 생존 경로(저자 분기), (원자, negated) + conjunctive.
# ---------------------------------------------------------------------------

@dataclass
class Branch:
    """생존 분기 하나. atoms = (원자 텍스트, negated) 목록(dedup). conjunctive = 비트 AND 표현 가능."""

    atoms: List[Tuple[str, bool]] = field(default_factory=list)
    conjunctive: bool = True


def _pos_atoms(node: ast.AST) -> Tuple[List[str], bool]:
    """진입/통과 조건의 만족 원자(positive) — And/Compare/Name만 conjunctive. Or → 비-conjunctive."""
    out: List[str] = []
    conj = [True]

    def rec(n: ast.AST) -> None:
        if isinstance(n, ast.BoolOp):
            if isinstance(n.op, ast.Or):
                conj[0] = False
            for v in n.values:
                rec(v)
        elif isinstance(n, (ast.Compare, ast.Name)):
            out.append(_norm(n))
        else:
            out.append(_norm(n))

    rec(node)
    return out, conj[0]


def _kill_guard_atoms(test: ast.AST) -> Tuple[List[Tuple[str, bool]], bool]:
    """kill-가드(`if test: 매수=False`)의 생존(¬test) 만족 원자 + conjunctive.

    - test = not(inner): 만족 = inner → positive 원자(negated=False). inner And → 다중 positive.
    - test = bare Name / 단일 Compare: 만족 = ¬test → negated=True 원자 1개.
    - test = A or B: ¬(A∨B)=¬A∧¬B → 각 operand negated=True(conjunctive).
    - test = A and B: ¬(A∧B) 비-conjunctive → conj=False.
    """
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        atoms, conj = _pos_atoms(test.operand)
        return [(a, False) for a in atoms], conj
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        out: List[Tuple[str, bool]] = []
        for v in test.values:
            if isinstance(v, (ast.Compare, ast.Name)):
                out.append((_norm(v), True))
            else:
                return [], False
        return out, True
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return [], False       # ¬(A∧B) 비-conjunctive.
    if isinstance(test, (ast.Compare, ast.Name)):
        return [(_norm(test), True)], True
    return [(_norm(test), True)], True


def _buy_assign(stmt: ast.AST) -> Optional[bool]:
    if (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == "매수"
            and isinstance(stmt.value, ast.Constant)):
        return bool(stmt.value.value)
    return None


def _is_buy_call(stmt: ast.AST) -> bool:
    return isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Name) and stmt.test.id == "매수"


def _is_kill(block: List[ast.AST]) -> bool:
    return len(block) == 1 and _buy_assign(block[0]) is False


_Leaf = Tuple[List[Tuple[str, bool]], bool, Optional[bool]]  # (atoms, conjunctive, buy).


def _walk_block(stmts: List[ast.AST], acc: List[Tuple[str, bool]], conj: bool,
                buy: Optional[bool]) -> List[_Leaf]:
    results: List[_Leaf] = [(list(acc), conj, buy)]
    for stmt in stmts:
        nxt: List[_Leaf] = []
        for atoms, cj, b in results:
            ba = _buy_assign(stmt)
            if ba is not None:
                nxt.append((atoms, cj, ba))
            elif _is_buy_call(stmt):
                nxt.append((atoms, cj, b))
            elif isinstance(stmt, ast.If):
                nxt.extend(_walk_if(stmt, atoms, cj, b))
            else:
                nxt.append((atoms, cj, b))
        results = nxt
    return results


def _walk_if(node: ast.If, atoms: List[Tuple[str, bool]], conj: bool,
             buy: Optional[bool]) -> List[_Leaf]:
    out: List[_Leaf] = []
    body_kill = _is_kill(node.body)
    if body_kill:
        # BODY(test True) = kill(dead) — 필터됨(수집 무의미).
        out.extend(_walk_block(node.body, atoms, conj, buy))
        # ORELSE(test False) = 생존(가드 통과) → ¬test 만족 원자 수집.
        gatoms, gconj = _kill_guard_atoms(node.test)
        out.extend(_walk_block(node.orelse or [], atoms + gatoms, conj and gconj, buy))
    else:
        # dispatch/nested: BODY(test True) 진입 → positive 수집; ORELSE(skip) → 미수집(함의).
        patoms, pconj = _pos_atoms(node.test)
        out.extend(_walk_block(node.body, atoms + [(a, False) for a in patoms],
                               conj and pconj, buy))
        out.extend(_walk_block(node.orelse or [], atoms, conj, buy))
    return out


def enumerate_branches(text: str) -> List[Branch]:
    """매수식 원문 → 생존 분기 목록(Branch). 원자 dedup(순서 보존)."""
    leaves = _walk_block(ast.parse(text).body, [], True, None)
    branches: List[Branch] = []
    for atoms, conj, buy in leaves:
        if buy is not True:
            continue
        seen: Dict[Tuple[str, bool], None] = {}
        for a in atoms:
            seen.setdefault(a, None)
        branches.append(Branch(atoms=list(seen.keys()), conjunctive=conj))
    return branches


# ---------------------------------------------------------------------------
# 원자 → 챔피언 39비트 매핑.
# ---------------------------------------------------------------------------

def _rewrite_calls(node: ast.AST) -> ast.AST:
    class _T(ast.NodeTransformer):
        def visit_Call(self, n: ast.Call) -> ast.AST:  # noqa: N802
            self.generic_visit(n)
            if isinstance(n.func, ast.Name):
                args = tuple(a.value for a in n.args if isinstance(a, ast.Constant))
                key = (n.func.id, args)
                if key in CALL_SYMBOL_MAP:
                    return ast.copy_location(ast.Name(id=CALL_SYMBOL_MAP[key], ctx=ast.Load()), n)
            return n
    return _T().visit(node)


def _canon(expr: str) -> Optional[str]:
    try:
        tree = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return None
    return " ".join(ast.unparse(_rewrite_calls(tree)).split())


def _flip(expr: str) -> Optional[str]:
    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return None
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1):
        return None
    flip_op = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}
    op = type(node.ops[0])
    if op not in flip_op:
        return None
    flipped = ast.Compare(left=node.comparators[0], ops=[flip_op[op]()], comparators=[node.left])
    return _canon(ast.unparse(flipped))


def _build_bit_index() -> Dict[str, int]:
    idx: Dict[str, int] = {}
    for num, expr in RAW_EXPR.items():
        for key in (_canon(expr), _flip(expr)):
            if key and key not in idx:
                idx[key] = num
        stripped = expr[4:].strip() if expr.startswith("not ") else None
        if stripped:
            for key in (_canon(stripped), _flip(stripped)):
                if key and key not in idx:
                    idx[key] = num
    return idx


_BIT_INDEX = _build_bit_index()


def normalize_atom(atom: str) -> Optional[str]:
    return _canon(atom)


def map_atom_to_bit(atom: str) -> Optional[int]:
    """원자 → 챔피언 절#(기존 비트) 또는 None(신규 절)."""
    for key in (_canon(atom), _flip(atom)):
        if key and key in _BIT_INDEX:
            return _BIT_INDEX[key]
    return None


# ---------------------------------------------------------------------------
# 신규 절 컴파일(벡터 술어) + U-보류.
# ---------------------------------------------------------------------------

def _expand_chained(node: ast.AST) -> ast.AST:
    """연쇄 비교 a<b<c → (a<b) & (b<c) (BitAnd — numpy 벡터 안전)."""
    class _T(ast.NodeTransformer):
        def visit_Compare(self, n: ast.Compare) -> ast.AST:  # noqa: N802
            self.generic_visit(n)
            if len(n.ops) <= 1:
                return n
            operands = [n.left] + list(n.comparators)
            parts = [ast.Compare(left=operands[i], ops=[n.ops[i]], comparators=[operands[i + 1]])
                     for i in range(len(n.ops))]
            wrapped = parts[0]
            for p in parts[1:]:
                wrapped = ast.BinOp(left=wrapped, op=ast.BitAnd(), right=p)
            return ast.copy_location(wrapped, n)
    return _T().visit(node)


def _division_denoms(node: ast.AST) -> List[ast.AST]:
    """절 내 나눗셈 분모 노드 목록(챔피언 _ratio_gt: 분모>0 else 미충족 semantics)."""
    return [n.right for n in ast.walk(node) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]


class ClauseInfo:
    """신규 절 하나 — 원자·negated·가용성·심볼·벡터 술어(분모>0 가드 = 챔피언 semantics)."""

    def __init__(self, atom: str, negated: bool = False):
        self.atom = atom
        self.negated = negated
        self.symbols: Tuple[str, ...] = ()
        self.evaluable: bool = False
        self.reason: str = ""
        self._code = None
        self._raw_code = None
        self._denom_codes: List = []
        self._compile()

    def _compile(self) -> None:
        try:
            raw = ast.parse(self.atom, mode="eval").body
        except SyntaxError as exc:
            self.reason = f"파스 실패: {exc}"
            return
        raw = _expand_chained(_rewrite_calls(raw))
        denoms = _division_denoms(raw)
        # base = raw ∧ (분모>0 …) — 분모<=0 이면 미충족(챔피언 _ratio_gt).
        base: ast.AST = raw
        for d in denoms:
            guard = ast.Compare(left=d, ops=[ast.Gt()], comparators=[ast.Constant(value=0)])
            base = ast.BinOp(left=base, op=ast.BitAnd(), right=guard)
        node = ast.UnaryOp(op=ast.Invert(), operand=base) if self.negated else base
        names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        self.symbols = tuple(sorted(names))
        missing = names - AVAILABLE_SYMBOLS
        if missing:
            self.reason = f"U-보류(미가용 심볼: {sorted(missing)})"
            return
        if any(isinstance(n, (ast.Call, ast.Attribute, ast.Subscript)) for n in ast.walk(node)):
            self.reason = "U-보류(미허용 노드)"
            return
        try:
            self._code = compile(ast.Expression(body=ast.fix_missing_locations(node)), "<clause>", "eval")
            self._raw_code = compile(ast.Expression(body=ast.fix_missing_locations(
                ast.parse(self.atom, mode="eval").body)), "<raw>", "eval")
            self._denom_codes = [
                compile(ast.Expression(body=ast.fix_missing_locations(_rewrite_calls(d))), "<d>", "eval")
                for d in _division_denoms(_rewrite_calls(ast.parse(self.atom, mode="eval").body))]
        except Exception as exc:  # noqa: BLE001
            self.reason = f"컴파일 실패: {exc}"
            return
        self.evaluable = True

    def predicate(self, ns: Mapping[str, np.ndarray]) -> np.ndarray:
        if not self.evaluable:
            raise RuntimeError(f"평가 불가: {self.atom} ({self.reason})")
        env = {k: np.asarray(ns[k]) for k in self.symbols if k in ns}
        with np.errstate(divide="ignore", invalid="ignore"):
            val = eval(self._code, {"__builtins__": {}}, env)  # noqa: S307 — 화이트리스트 심볼만.
        return np.asarray(val, dtype=bool)

    def scalar_eval(self, env: Mapping[str, float]) -> bool:
        """독립 스칼라 경로(파이썬 연쇄비교/분모>0 가드/not) — 패리티 대조용."""
        if not self.evaluable:
            raise RuntimeError(f"평가 불가: {self.atom}")
        g = {k: float(env[k]) for k in self.symbols if k in env}
        try:
            for dc in self._denom_codes:
                if float(eval(dc, {"__builtins__": {}}, g)) <= 0.0:  # noqa: S307
                    base = False
                    break
            else:
                base = bool(eval(self._raw_code, {"__builtins__": {}}, g))  # noqa: S307
        except ZeroDivisionError:
            base = False
        return (not base) if self.negated else base


def compile_clause(atom: str, negated: bool = False) -> ClauseInfo:
    return ClauseInfo(atom, negated=negated)
