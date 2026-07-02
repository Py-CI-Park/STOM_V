"""절(clause) 단위 ablation 엔진 — 조건식 최상위 절 분해 + 거래행 기반 근사 평가.

STOM 조건식은 단일 boolean 식이 아니라 exec 되는 멀티라인 파이썬 블록이다.
(매수 = False → 중첩 if 체인 → 매수 = True → `if 매수: self.Buy(...)`)
이 모듈은 그 블록을 ast 로 파싱해 "최상위 and 절" 목록으로 평탄화하고,
백테스트 거래행의 진입 스냅샷(B_*) 컬럼으로 각 절의 통과율을 근사 평가한다.

[핵심 한계 — 반드시 이해하고 소비할 것]
  - 모든 수치는 **행 기반 근사(row-based approximation)** 다. 절을 실제로
    제거한 재백테스트는 이 모듈의 범위 밖이다. delta_trades_if_removed 는
    "주어진 거래행 풀에서 이 절 하나만이 막고 있던 행 수"의 근사일 뿐,
    재백테스트 시 실제 거래수 변화가 아니다.
  - 절이 참조하는 변수가 거래행에 없으면(파생변수, 런타임 전용 변수, STOM
    내장 함수) 추측하지 않고 'not_evaluable' 로 정직하게 라벨링한다.
  - if/elif 다중 경로(매도형)는 각 경로의 양성 테스트 결합만 취한 상한
    근사다(선행 분기의 부정 조건은 포함하지 않는다).

데이터 모양 문제로는 예외를 던지지 않는다(autopsy 관례 — status 로 반환).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import pandas as pd

# 읽기 전용 import 소비 — 진입 스냅샷 컬럼 ↔ STOM 변수명 매핑과 수익률 컬럼 정본.
from ai_strategy_loop.autopsy.analyze import B_TO_STOM_VAR, RETURN_COLUMN

# STOM 변수명 → 거래행 진입 스냅샷 컬럼(B_*) 역매핑.
STOM_VAR_TO_B_COLUMN = {var: col for col, var in B_TO_STOM_VAR.items()}

# 게이트 플래그 후보 이름(매수식/매도식 공통 관례).
FLAG_NAMES = ("매수", "매도")

# 절 평가에서 허용하는 안전 내장 함수(이 외 호출은 unsupported).
SAFE_CALL_NAMES = frozenset({"abs", "min", "max", "round"})
_SAFE_FUNCS = {"abs": abs, "min": min, "max": max, "round": round}

# 절 출처 태그.
SOURCE_FLAG_PATH = "flag_path"    # 플래그 패턴(매수/매도 = True 경로)에서 추출.
SOURCE_GUARD_IF = "guard_if"      # `if <조건>: self.Buy(...)` 직접 게이트.
SOURCE_EXPRESSION = "expression"  # 단일 boolean 식.

# 평가 status.
EVAL_STATUS_OK = "ok"
EVAL_STATUS_NOT_EVALUABLE = "not_evaluable"

# ablation 전체 status.
ABLATION_STATUS_OK = "ok"
ABLATION_STATUS_EMPTY_TRADES = "empty_trades"
ABLATION_STATUS_NO_CLAUSES = "no_clauses"
ABLATION_STATUS_NO_EVALUABLE = "no_evaluable_clause"

# 절 판정(verdict).
VERDICT_INEFFECTIVE = "ineffective"      # 이 풀에서 아무 행도 단독으로 거르지 않음.
VERDICT_HARMFUL = "harmful"              # 수익(+) 행을 단독 차단 / 손실(-) 행을 단독 유입.
VERDICT_BINDING = "binding"              # 실제 구속력 있음(손실 차단 또는 수익 기여).
VERDICT_NOT_EVALUABLE = "not_evaluable"  # 행 기반 근사 불가(정직 라벨).

# 중복(redundancy) 제안 임계 — 자카드 유사도가 이 이상이면 통합 후보.
REDUNDANCY_SUGGEST_THRESHOLD = 0.8

_ROUND_DIGITS = 6

# 평가용 식에서 허용하는 ast 노드(화이트리스트 밖이면 unsupported_syntax).
_ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or,
    ast.UnaryOp, ast.Not, ast.USub, ast.UAdd,
    ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Name, ast.Load, ast.Constant, ast.Call, ast.IfExp,
)


@dataclass(frozen=True)
class Clause:
    """조건식에서 분해된 최상위 절 하나.

    combinator:
      - 'and' : 형제 절들과 and 로 결합(단일 경로 게이트).
      - 'or'  : 형제 절들과 or 로 결합(다중 경로 게이트 — 각 경로가 한 절).
        or 그룹(`a or b`)이 and 체인 안에 있으면 그 그룹 전체가 하나의 절이다.
    """

    index: int
    text: str                              # 사람용 원문(소스 세그먼트 우선).
    expression: str                        # ast.unparse 정규화 식(평가용).
    combinator: str                        # 'and' | 'or'
    variables: Tuple[str, ...]             # 참조 이름(호출 함수명 포함, 안전 내장 제외).
    derived_variables: Tuple[str, ...]     # 조건식 내부 대입으로 만들어진 파생변수 참조.
    source: str                            # SOURCE_* 태그.


@dataclass(frozen=True)
class ClauseEvaluation:
    """절 하나의 거래행 기반 통과율 근사 평가."""

    clause_index: int
    clause_text: str
    combinator: str
    status: str                            # 'ok' | 'not_evaluable'
    reason: str = ""
    missing_variables: Tuple[str, ...] = ()
    pass_rate: Optional[float] = None      # 평가된 행 중 참 비율(평가 행 0이면 None).
    evaluated_rows: int = 0
    passed_rows: int = 0
    skipped_rows: int = 0                  # 결측/평가오류로 제외된 행 수.


@dataclass(frozen=True)
class ClauseAblation:
    """절 하나의 ablation 근사 결과(재백테스트 아님 — 행 기반 근사)."""

    clause_index: int
    clause_text: str
    combinator: str
    status: str                            # 'ok' | 'not_evaluable'
    pass_rate: Optional[float]
    delta_trades_if_removed: Optional[int]  # and: +유일차단 행수 / or: -유일기여 행수.
    blocked_avg_return: Optional[float]     # 그 유일 차단/기여 행들의 평균 수익률(%).
    redundancy: Optional[float]             # 다른 평가가능 절과의 최대 자카드 유사도.
    redundancy_partner: Optional[str]       # 최대 유사 절 텍스트.
    verdict: str
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "clause_index": self.clause_index,
            "clause_text": self.clause_text,
            "combinator": self.combinator,
            "status": self.status,
            "pass_rate": self.pass_rate,
            "delta_trades_if_removed": self.delta_trades_if_removed,
            "blocked_avg_return": self.blocked_avg_return,
            "redundancy": self.redundancy,
            "redundancy_partner": self.redundancy_partner,
            "verdict": self.verdict,
            "note": self.note,
        }


@dataclass(frozen=True)
class AblationResult:
    """ablation 전체 결과. status 로 데이터 모양 문제를 무예외 보고한다."""

    status: str
    trade_count: int
    clause_count: int
    evaluable_clause_count: int
    items: Tuple[ClauseAblation, ...] = field(default_factory=tuple)
    note: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "status": self.status,
            "trade_count": self.trade_count,
            "clause_count": self.clause_count,
            "evaluable_clause_count": self.evaluable_clause_count,
            "items": [item.to_dict() for item in self.items],
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# 1) 절 분해
# ---------------------------------------------------------------------------

def _collect_assigned_names(tree: ast.AST) -> frozenset:
    """조건식 블록 내부에서 대입으로 만들어지는 이름(파생변수) 전부."""
    names = set()
    for node in ast.walk(tree):
        targets: Sequence[ast.expr] = ()
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = (node.target,)
        elif isinstance(node, ast.NamedExpr):
            targets = (node.target,)
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return frozenset(names - set(FLAG_NAMES))


def _collect_referenced_names(node: ast.AST) -> Tuple[str, ...]:
    """절이 참조하는 이름(변수 + 호출 함수명). 안전 내장 함수는 제외."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
    return tuple(sorted(names - SAFE_CALL_NAMES))


def _contains_trade_call(node: ast.AST) -> bool:
    """서브트리에 self.Buy(...) / self.Sell(...) 호출이 있는지."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr in ("Buy", "Sell"):
                return True
    return False


def _is_flag_true_assign(stmt: ast.stmt, flag: str) -> bool:
    """`<flag> = True` 대입인지."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return False
    target = stmt.targets[0]
    if not (isinstance(target, ast.Name) and target.id == flag):
        return False
    return isinstance(stmt.value, ast.Constant) and stmt.value.value is True


def _iter_true_paths(body: Sequence[ast.stmt], flag: str,
                     tests: Tuple[ast.expr, ...]) -> List[Tuple[ast.expr, ...]]:
    """`<flag> = True` 에 도달하는 모든 경로의 (양성) if-테스트 목록.

    elif 는 orelse 안의 If 로 재귀되며, 선행 분기의 부정 조건은 포함하지
    않는다(상한 근사 — 모듈 docstring 참조).
    """
    paths: List[Tuple[ast.expr, ...]] = []
    for stmt in body:
        if _is_flag_true_assign(stmt, flag):
            paths.append(tests)
        elif isinstance(stmt, ast.If):
            paths.extend(_iter_true_paths(stmt.body, flag, tests + (stmt.test,)))
            paths.extend(_iter_true_paths(stmt.orelse, flag, tests))
    return paths


def _flatten_and(test: ast.expr) -> List[ast.expr]:
    """and 체인을 최상위 절 목록으로 평탄화. or 그룹(BoolOp Or)은 한 절."""
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        parts: List[ast.expr] = []
        for value in test.values:
            parts.extend(_flatten_and(value))
        return parts
    return [test]


def _segment(code: str, node: ast.expr) -> str:
    """사람용 절 텍스트 — 원문 소스 세그먼트 우선, 실패 시 unparse."""
    text = ast.get_source_segment(code, node)
    return text if text else ast.unparse(node)


def _make_clause(index: int, node: ast.expr, *, text: str, combinator: str,
                 assigned: frozenset, source: str) -> Clause:
    variables = _collect_referenced_names(node)
    derived = tuple(sorted(v for v in variables if v in assigned))
    return Clause(
        index=index,
        text=text,
        expression=ast.unparse(node),
        combinator=combinator,
        variables=variables,
        derived_variables=derived,
        source=source,
    )


def _find_flag_name(module: ast.Module) -> Optional[str]:
    """`if <플래그>: self.Buy/Sell(...)` 최상위 게이트에서 플래그 이름 탐지."""
    for stmt in module.body:
        if isinstance(stmt, ast.If) and isinstance(stmt.test, ast.Name):
            if _contains_trade_call(stmt):
                return stmt.test.id
    # 폴백: 관례 플래그가 False 로 초기화되어 있으면 그 이름.
    for stmt in module.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if (isinstance(target, ast.Name) and target.id in FLAG_NAMES
                    and isinstance(stmt.value, ast.Constant)
                    and stmt.value.value is False):
                return target.id
    return None


def parse_top_level_clauses(code: str) -> List[Clause]:
    """조건식 코드의 최상위 절 목록을 분해한다.

    지원 형태(정찰에서 확인한 실형태):
      1. 플래그 패턴: `매수 = False` → 중첩 if → `매수 = True` → `if 매수: self.Buy`.
         - True 도달 경로가 1개면: 경로상 모든 if 테스트의 and-절 합집합(combinator='and').
         - 경로가 여러 개면(매도형 if/elif 나열): 각 경로의 테스트 결합이 한 절
           (combinator='or' — or 그룹은 하나의 절로 취급).
      2. 직접 게이트: `if <조건>: self.Buy(...)` → 조건의 and-절 분해.
      3. 단일 boolean 식 → and-절 분해.

    파싱 불가/게이트 없음 등 데이터 모양 문제는 빈 목록 반환(무예외).
    """
    if not isinstance(code, str) or not code.strip():
        return []
    try:
        module = ast.parse(code)
    except SyntaxError:
        return []
    assigned = _collect_assigned_names(module)

    # 1) 플래그 패턴.
    flag = _find_flag_name(module)
    if flag is not None:
        paths = _iter_true_paths(module.body, flag, ())
        if len(paths) == 1:
            clauses: List[Clause] = []
            for test in paths[0]:
                for part in _flatten_and(test):
                    clauses.append(_make_clause(
                        len(clauses), part, text=_segment(code, part),
                        combinator="and", assigned=assigned, source=SOURCE_FLAG_PATH))
            return clauses
        if len(paths) > 1:
            clauses = []
            for tests in paths:
                if not tests:
                    # 무조건 True 경로(테스트 없는 경로) — 절로 만들 수 없어 건너뜀.
                    continue
                node = tests[0] if len(tests) == 1 else ast.BoolOp(
                    op=ast.And(), values=list(tests))
                ast.fix_missing_locations(node)
                text = " and ".join(_segment(code, t) for t in tests)
                clauses.append(_make_clause(
                    len(clauses), node, text=text,
                    combinator="or", assigned=assigned, source=SOURCE_FLAG_PATH))
            return clauses
        return []

    # 2) 직접 게이트: `if <조건>: ... self.Buy/Sell(...)`.
    for stmt in module.body:
        if isinstance(stmt, ast.If) and _contains_trade_call(stmt):
            clauses = []
            for part in _flatten_and(stmt.test):
                clauses.append(_make_clause(
                    len(clauses), part, text=_segment(code, part),
                    combinator="and", assigned=assigned, source=SOURCE_GUARD_IF))
            return clauses

    # 3) 단일 boolean 식.
    if len(module.body) == 1 and isinstance(module.body[0], ast.Expr):
        value = module.body[0].value
        clauses = []
        for part in _flatten_and(value):
            clauses.append(_make_clause(
                len(clauses), part, text=_segment(code, part),
                combinator="and", assigned=assigned, source=SOURCE_EXPRESSION))
        return clauses

    return []


# ---------------------------------------------------------------------------
# 2) 절 통과율 근사 평가
# ---------------------------------------------------------------------------

def _map_variable_to_column(var: str, columns: Sequence[str]) -> Optional[str]:
    """STOM 변수명 → 거래행 컬럼. 진입 스냅샷(B_*) 우선, 직접 컬럼명 폴백."""
    b_col = STOM_VAR_TO_B_COLUMN.get(var, "B_" + var)
    if b_col in columns:
        return b_col
    if var in columns:
        return var
    return None


def _unsupported_reason(node: ast.AST) -> Optional[str]:
    """평가 화이트리스트 밖 구문이 있으면 사유 문자열, 없으면 None."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if not (isinstance(func, ast.Name) and func.id in SAFE_CALL_NAMES):
                name = func.id if isinstance(func, ast.Name) else ast.unparse(func)
                return "unsupported_call:" + name
            continue
        if not isinstance(child, _ALLOWED_NODES):
            return "unsupported_syntax:" + type(child).__name__
    return None


def _evaluate_rows(clauses: Sequence[Clause],
                   trades_df: Optional[pd.DataFrame]
                   ) -> Tuple[List[ClauseEvaluation], List[Optional[List[Optional[bool]]]]]:
    """절별 행 단위 평가. 반환: (평가 요약 목록, 절별 행 결과 행렬).

    행렬 원소: True/False = 평가 결과, None = 결측/평가오류로 제외된 행.
    not_evaluable 절의 행렬은 None(행 목록 자체가 없음).
    """
    if trades_df is None:
        trades_df = pd.DataFrame()
    columns = list(trades_df.columns)
    row_count = len(trades_df)

    evaluations: List[ClauseEvaluation] = []
    matrix: List[Optional[List[Optional[bool]]]] = []

    for clause in clauses:
        col_map: Dict[str, str] = {}
        missing: List[str] = []
        for var in clause.variables:
            column = _map_variable_to_column(var, columns)
            if column is None:
                missing.append(var)
            else:
                col_map[var] = column

        if missing:
            # 정직 라벨: 거래행에 없는 변수는 추측하지 않는다.
            derived_hit = tuple(v for v in missing if v in clause.derived_variables)
            reason = "missing_variables=" + ",".join(missing)
            if derived_hit:
                reason += " (derived=" + ",".join(derived_hit) + ")"
            evaluations.append(ClauseEvaluation(
                clause_index=clause.index, clause_text=clause.text,
                combinator=clause.combinator, status=EVAL_STATUS_NOT_EVALUABLE,
                reason=reason, missing_variables=tuple(missing)))
            matrix.append(None)
            continue

        try:
            tree = ast.parse(clause.expression, mode="eval")
        except SyntaxError:
            evaluations.append(ClauseEvaluation(
                clause_index=clause.index, clause_text=clause.text,
                combinator=clause.combinator, status=EVAL_STATUS_NOT_EVALUABLE,
                reason="unparseable_expression"))
            matrix.append(None)
            continue
        unsupported = _unsupported_reason(tree)
        if unsupported:
            evaluations.append(ClauseEvaluation(
                clause_index=clause.index, clause_text=clause.text,
                combinator=clause.combinator, status=EVAL_STATUS_NOT_EVALUABLE,
                reason=unsupported))
            matrix.append(None)
            continue

        code_obj = compile(tree, "<clause_%d>" % clause.index, "eval")
        value_lists = {var: trades_df[col].tolist() for var, col in col_map.items()}
        eval_globals = {"__builtins__": {}}
        eval_globals.update(_SAFE_FUNCS)

        rows: List[Optional[bool]] = []
        passed = 0
        skipped = 0
        for i in range(row_count):
            namespace = {}
            has_null = False
            for var, values in value_lists.items():
                value = values[i]
                if pd.isna(value):
                    has_null = True
                    break
                namespace[var] = value
            if has_null:
                rows.append(None)
                skipped += 1
                continue
            try:
                result = bool(eval(code_obj, eval_globals, namespace))  # noqa: S307
            except Exception:
                # 0 나눗셈 등 행 단위 평가 오류 — 그 행만 제외(무예외 관례).
                rows.append(None)
                skipped += 1
                continue
            rows.append(result)
            if result:
                passed += 1

        evaluated = row_count - skipped
        pass_rate = (round(passed / evaluated, _ROUND_DIGITS)
                     if evaluated > 0 else None)
        evaluations.append(ClauseEvaluation(
            clause_index=clause.index, clause_text=clause.text,
            combinator=clause.combinator, status=EVAL_STATUS_OK,
            pass_rate=pass_rate, evaluated_rows=evaluated,
            passed_rows=passed, skipped_rows=skipped))
        matrix.append(rows)

    return evaluations, matrix


def evaluate_clause_pass_rates(clauses: Sequence[Clause],
                               trades_df: Optional[pd.DataFrame]
                               ) -> List[ClauseEvaluation]:
    """거래행의 진입 스냅샷(B_*) 피처로 각 절의 통과율을 근사 평가한다.

    절이 참조하는 변수가 거래행에 없으면(파생변수/런타임 변수/STOM 함수)
    'not_evaluable' 로 정직하게 표시한다 — 추측 금지.
    행 기반 근사일 뿐 재백테스트가 아니다(모듈 docstring 참조).
    """
    evaluations, _ = _evaluate_rows(clauses, trades_df)
    return evaluations


# ---------------------------------------------------------------------------
# 3) ablation (행 기반 근사)
# ---------------------------------------------------------------------------

def _jaccard(a: frozenset, b: frozenset) -> float:
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _mean_return(returns: Sequence[float], rows: Sequence[int]) -> Optional[float]:
    values = [returns[r] for r in rows if not pd.isna(returns[r])]
    if not values:
        return None
    return round(sum(values) / len(values), _ROUND_DIGITS)


def _verdict_and(delta: int, avg: Optional[float], has_returns: bool) -> Tuple[str, str]:
    """and 절 판정: 유일 차단 행의 평균 수익률로 harmful/binding 구분."""
    if delta <= 0:
        return VERDICT_INEFFECTIVE, ""
    if has_returns and avg is not None:
        if avg > 0:
            return VERDICT_HARMFUL, ""
        return VERDICT_BINDING, ""
    return VERDICT_BINDING, "수익률 부재 — harmful/binding 구분 근사 불가(binding 폴백)"


def _verdict_or(delta: int, avg: Optional[float], has_returns: bool) -> Tuple[str, str]:
    """or 절 판정: 유일 기여 행의 평균 수익률로 binding/harmful 구분."""
    if delta >= 0:
        return VERDICT_INEFFECTIVE, ""
    if has_returns and avg is not None:
        if avg > 0:
            return VERDICT_BINDING, ""
        return VERDICT_HARMFUL, ""
    return VERDICT_BINDING, "수익률 부재 — harmful/binding 구분 근사 불가(binding 폴백)"


def ablate(clauses: Sequence[Clause],
           trades_df: Optional[pd.DataFrame],
           *,
           return_column: str = RETURN_COLUMN) -> AblationResult:
    """절별 ablation 근사 — 통과율, 제거 시 거래수 변화 근사, 절 간 중복도, 판정.

    [행 기반 근사만 수행한다 — 절을 제거한 재백테스트는 이 함수의 범위 밖이다.]
    주어진 거래행 풀(보통 부모 조건 또는 완화 조건의 거래)에 대해:
      - pass_rate: 절이 참인 행 비율.
      - delta_trades_if_removed:
          and 절 → 이 절만 실패하고 나머지 평가가능 절은 전부 통과한 행 수(+).
          or 절  → 이 절만 통과하고 나머지는 전부 실패한 행 수(-, 제거 시 상실).
      - redundancy: 다른 평가가능 절과의 통과 집합 자카드 유사도 최대값.
      - verdict: 'ineffective' | 'harmful' | 'binding' | 'not_evaluable'.
        (유일 차단/기여 행들의 평균 수익률 부호로 harmful/binding 구분.)

    집합 연산(delta/redundancy)은 모든 평가가능 절이 평가된 "완전 행"으로
    제한한다. 데이터 모양 문제는 status 로 무예외 반환한다.
    """
    clause_list = list(clauses)
    if not clause_list:
        return AblationResult(
            status=ABLATION_STATUS_NO_CLAUSES, trade_count=0,
            clause_count=0, evaluable_clause_count=0)

    trade_count = 0 if trades_df is None else len(trades_df)
    if trade_count == 0:
        items = tuple(ClauseAblation(
            clause_index=c.index, clause_text=c.text, combinator=c.combinator,
            status=EVAL_STATUS_NOT_EVALUABLE, pass_rate=None,
            delta_trades_if_removed=None, blocked_avg_return=None,
            redundancy=None, redundancy_partner=None,
            verdict=VERDICT_NOT_EVALUABLE, note="empty_trades") for c in clause_list)
        return AblationResult(
            status=ABLATION_STATUS_EMPTY_TRADES, trade_count=0,
            clause_count=len(clause_list), evaluable_clause_count=0, items=items)

    evaluations, matrix = _evaluate_rows(clause_list, trades_df)
    evaluable = [i for i, rows in enumerate(matrix) if rows is not None]

    if not evaluable:
        items = tuple(ClauseAblation(
            clause_index=c.index, clause_text=c.text, combinator=c.combinator,
            status=EVAL_STATUS_NOT_EVALUABLE, pass_rate=None,
            delta_trades_if_removed=None, blocked_avg_return=None,
            redundancy=None, redundancy_partner=None,
            verdict=VERDICT_NOT_EVALUABLE,
            note=evaluations[i].reason) for i, c in enumerate(clause_list))
        return AblationResult(
            status=ABLATION_STATUS_NO_EVALUABLE, trade_count=trade_count,
            clause_count=len(clause_list), evaluable_clause_count=0, items=items)

    # 완전 행: 모든 평가가능 절이 (결측/오류 없이) 평가된 행.
    complete_rows = [r for r in range(trade_count)
                     if all(matrix[i][r] is not None for i in evaluable)]

    has_returns = (trades_df is not None and return_column in trades_df.columns)
    if has_returns:
        returns = pd.to_numeric(trades_df[return_column], errors="coerce").tolist()
    else:
        returns = []

    pass_sets = {i: frozenset(r for r in complete_rows if matrix[i][r])
                 for i in evaluable}

    items_list: List[ClauseAblation] = []
    for i, clause in enumerate(clause_list):
        evaluation = evaluations[i]
        if matrix[i] is None:
            items_list.append(ClauseAblation(
                clause_index=clause.index, clause_text=clause.text,
                combinator=clause.combinator, status=EVAL_STATUS_NOT_EVALUABLE,
                pass_rate=None, delta_trades_if_removed=None,
                blocked_avg_return=None, redundancy=None,
                redundancy_partner=None, verdict=VERDICT_NOT_EVALUABLE,
                note=evaluation.reason))
            continue

        if not complete_rows:
            items_list.append(ClauseAblation(
                clause_index=clause.index, clause_text=clause.text,
                combinator=clause.combinator, status=EVAL_STATUS_OK,
                pass_rate=evaluation.pass_rate, delta_trades_if_removed=None,
                blocked_avg_return=None, redundancy=None,
                redundancy_partner=None, verdict=VERDICT_NOT_EVALUABLE,
                note="no_complete_rows — 집합 연산 불가"))
            continue

        others = [j for j in evaluable if j != i]
        if clause.combinator == "or":
            # 이 절만 통과시킨 행 = 제거 시 상실되는 유입(근사).
            unique_rows = [r for r in complete_rows
                           if matrix[i][r] and all(not matrix[j][r] for j in others)]
            delta = -len(unique_rows)
            avg = _mean_return(returns, unique_rows) if has_returns else None
            verdict, note = _verdict_or(delta, avg, has_returns)
        else:
            # 이 절만 실패한 행 = 제거 시 추가 유입되는 거래(근사).
            unique_rows = [r for r in complete_rows
                           if not matrix[i][r] and all(matrix[j][r] for j in others)]
            delta = len(unique_rows)
            avg = _mean_return(returns, unique_rows) if has_returns else None
            verdict, note = _verdict_and(delta, avg, has_returns)

        redundancy: Optional[float] = None
        partner: Optional[str] = None
        if others:
            best = max(others, key=lambda j: (_jaccard(pass_sets[i], pass_sets[j]), -j))
            redundancy = round(_jaccard(pass_sets[i], pass_sets[best]), _ROUND_DIGITS)
            partner = clause_list[best].text

        items_list.append(ClauseAblation(
            clause_index=clause.index, clause_text=clause.text,
            combinator=clause.combinator, status=EVAL_STATUS_OK,
            pass_rate=evaluation.pass_rate, delta_trades_if_removed=delta,
            blocked_avg_return=avg, redundancy=redundancy,
            redundancy_partner=partner, verdict=verdict, note=note))

    return AblationResult(
        status=ABLATION_STATUS_OK, trade_count=trade_count,
        clause_count=len(clause_list), evaluable_clause_count=len(evaluable),
        items=tuple(items_list))


# ---------------------------------------------------------------------------
# 4) repair 프롬프트용 변이축(mutation axis) 제안
# ---------------------------------------------------------------------------

def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return format(value, "g")


def _harmful_suggestion(item: ClauseAblation) -> Dict[str, object]:
    delta = abs(item.delta_trades_if_removed or 0)
    if item.combinator == "or":
        axis = "유해 or-분기 축소/강화: " + item.clause_text
        evidence = ("이 분기 단독으로 유입된 거래 %d건, 그 평균 수익률 %s%% "
                    "(통과율 %s, 행 기반 근사)" % (
                        delta, _format_number(item.blocked_avg_return),
                        _format_number(item.pass_rate)))
        expected = "손실성 단독 유입 %d건 차단 — 평균 수익률 개선" % delta
    else:
        axis = "유해 절 완화/제거: " + item.clause_text
        evidence = ("이 절 단독으로 차단된 거래 %d건, 그 평균 수익률 %s%% "
                    "(통과율 %s, 행 기반 근사)" % (
                        delta, _format_number(item.blocked_avg_return),
                        _format_number(item.pass_rate)))
        expected = "수익성 차단 거래 %d건 회수 — 거래수/수익 증가 기대" % delta
    return {
        "mutation_axis": axis,
        "clause_text": item.clause_text,
        "clause_index": item.clause_index,
        "verdict": item.verdict,
        "evidence": evidence,
        "expected_effect": expected,
        "risk_note": "행 기반 근사 — 재백테스트 검증 전에는 확정 금지(과최적화 주의)",
    }


def _ineffective_suggestion(item: ClauseAblation) -> Dict[str, object]:
    redundant = (item.redundancy is not None
                 and item.redundancy >= REDUNDANCY_SUGGEST_THRESHOLD)
    if redundant:
        axis = "중복 절 통합/제거: " + item.clause_text
        evidence = ("통과율 %s, 단독 차단 0건, 최대 자카드 유사도 %s (파트너: %s)" % (
            _format_number(item.pass_rate), _format_number(item.redundancy),
            item.redundancy_partner))
        expected = "중복 절 제거로 조건식 단순화 — 거래 결과 변화 없음(근사)"
    else:
        axis = "무효 절 제거 검토: " + item.clause_text
        evidence = ("통과율 %s, 이 절 단독으로 거른 거래 0건 (행 기반 근사)" % (
            _format_number(item.pass_rate),))
        expected = "이 풀 기준 결과 불변 — 조건식 단순화 여지"
    return {
        "mutation_axis": axis,
        "clause_text": item.clause_text,
        "clause_index": item.clause_index,
        "verdict": item.verdict,
        "evidence": evidence,
        "expected_effect": expected,
        "risk_note": "행 기반 근사 — 다른 시장 구간에서는 구속력이 있을 수 있음",
    }


def to_mutation_axis_suggestions(ablation_result: AblationResult
                                 ) -> List[Dict[str, object]]:
    """ablation 결과를 repair 프롬프트용 변이축 제안 목록으로 변환한다.

    root-cause 형식: 절 텍스트 + 근거 수치(evidence). 우선순위:
      1. harmful (|delta| 큰 순) — 수익 차단/손실 유입의 근본 원인 후보.
      2. ineffective 중 중복(자카드 >= REDUNDANCY_SUGGEST_THRESHOLD) — 통합 대상.
      3. 나머지 ineffective — 단순화 대상.
    binding(정상 구속) / not_evaluable(근거 수치 없음) 절은 제안하지 않는다.
    """
    items = list(ablation_result.items)
    harmful = sorted(
        (it for it in items if it.verdict == VERDICT_HARMFUL),
        key=lambda it: (-abs(it.delta_trades_if_removed or 0), it.clause_index))
    ineffective = [it for it in items if it.verdict == VERDICT_INEFFECTIVE]
    redundant = sorted(
        (it for it in ineffective
         if it.redundancy is not None
         and it.redundancy >= REDUNDANCY_SUGGEST_THRESHOLD),
        key=lambda it: (-(it.redundancy or 0.0), it.clause_index))
    plain = sorted(
        (it for it in ineffective if it not in redundant),
        key=lambda it: it.clause_index)

    suggestions: List[Dict[str, object]] = []
    for item in harmful:
        suggestions.append(_harmful_suggestion(item))
    for item in redundant:
        suggestions.append(_ineffective_suggestion(item))
    for item in plain:
        suggestions.append(_ineffective_suggestion(item))
    return suggestions
