"""최소 토큰 가드 + 정규화 AST 해시 기반 dedup (US-003 Phase 1b).

RV2-5 결정: 무거운 AST allowlist 샌드박스는 만들지 않는다. 전략 코드는 이미
`cli.strategy.validate_strategy`로 compile-only 검증되고, 백테스트는 격리된
엔진 프로세스에서 실행된다. 여기서는 값싼 보험만 둔다:

  - check_tokens(code): import / exec·eval·open·compile·__import__ 호출 / dunder
    접근을 AST로 거부. forbidden.md (b) 규칙과 일치.
  - normalized_ast_hash(code): docstring/상수 리터럴을 placeholder로 치환하고
    포매팅 차이를 무시한 정규화 AST를 sha256으로 해시 → 리터럴만 다른 변형 탐지.
  - DedupTracker(k): 최근 K개 정규화 해시를 기억하고 중복을 판정.
"""

from __future__ import annotations

import ast
import hashlib
from collections import deque
from typing import Deque, Tuple

# forbidden.md (b)의 호출 금지 이름. 이름 호출(open(...))과 속성 접근 모두 차단.
# getattr/setattr/... 계열은 dunder 문자열 리터럴로 가드를 우회할 수 있어 추가한다
# (예: getattr(현재가, "__class__")). 아래 _DUNDER_IN_STRING 검사가 그 문자열 경로도 막는다.
_FORBIDDEN_CALL_NAMES = frozenset(
    {
        "exec", "eval", "open", "compile", "__import__",
        "getattr", "setattr", "delattr",
        "globals", "locals", "vars",
        "breakpoint", "memoryview",
    }
)


def check_tokens(code: str) -> Tuple[bool, str]:
    """전략 코드의 안전 토큰을 AST로 검사한다.

    거부 대상 (forbidden.md (b)):
      - import / from ... import (Import, ImportFrom)
      - exec / eval / open / compile / __import__ 호출
      - 연속 이중 밑줄(`__`)을 포함하는 이름·속성 접근 (dunder)

    Args:
        code: 전략 코드 문자열.

    Returns:
        (ok, reason). ok=True면 통과(reason=""), ok=False면 거부 사유 문자열.
    """
    if not code or not code.strip():
        return False, "빈 전략 코드"

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"구문 오류: {exc}"

    for node in ast.walk(tree):
        # import 금지
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "import 금지 토큰 사용"

        # 위험 호출 금지 (이름 호출 + 속성 호출 둘 다)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _FORBIDDEN_CALL_NAMES:
                return False, f"금지 호출: {func.id}()"
            if isinstance(func, ast.Attribute) and func.attr in _FORBIDDEN_CALL_NAMES:
                return False, f"금지 호출: .{func.attr}()"

        # dunder 접근 금지 (속성: obj.__class__ / 이름: __dict__ 등).
        # forbidden.md 주석: 단일 밑줄 변수명은 허용, 연속 `__` 만 차단.
        if isinstance(node, ast.Attribute) and "__" in node.attr:
            return False, f"dunder 속성 접근 금지: .{node.attr}"
        if isinstance(node, ast.Name) and "__" in node.id:
            return False, f"dunder 이름 사용 금지: {node.id}"

        # dunder 문자열 리터럴 금지. getattr 같은 함수가 막혀도 다른 경로(또는
        #   허용 함수)에 "__class__" 같은 문자열을 넘기는 우회를 봉쇄한다.
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            return False, f"dunder 문자열 리터럴 금지: {node.value!r}"

    return True, ""


class _NormalizeTransformer(ast.NodeTransformer):
    """상수/docstring을 placeholder로 치환하여 '구조'만 남긴 AST로 정규화한다.

    리터럴만 다른 전략(예: 임계값 `4.83` → `3.535`)이 동일 구조로 묶이도록 한다.
    """

    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802 (ast API)
        # 모든 상수를 단일 placeholder 문자열로 치환 (숫자/문자/불리언/None 통합).
        return ast.copy_location(ast.Constant(value="<C>"), node)


def normalized_ast_hash(code: str) -> str:
    """정규화 AST의 sha256 해시를 반환한다.

    - docstring/상수 리터럴 → 단일 placeholder (리터럴 차이 무시).
    - ast.dump(annotate_fields=False)로 포매팅/주석/공백 차이 무시.

    Args:
        code: 전략 코드 문자열.

    Returns:
        64자리 hex sha256 해시.

    Raises:
        SyntaxError: 코드가 파싱 불가일 때 (호출자가 먼저 compile 검증하는 전제).
    """
    tree = ast.parse(code)
    tree = _NormalizeTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    normalized = ast.dump(tree, annotate_fields=False, include_attributes=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DedupTracker:
    """최근 K개 정규화 해시를 기억하여 중복 전략을 탐지한다."""

    def __init__(self, k: int = 5) -> None:
        if k < 1:
            raise ValueError("k는 1 이상이어야 합니다")
        self.k = k
        self._hashes: Deque[str] = deque(maxlen=k)

    def is_duplicate(self, code: str) -> bool:
        """code의 정규화 해시가 최근 K개 안에 있으면 True.

        파싱 불가 코드는 중복으로 보지 않는다(상위 compile 게이트가 먼저 거른다).
        """
        try:
            h = normalized_ast_hash(code)
        except SyntaxError:
            return False
        return h in self._hashes

    def record(self, code: str) -> None:
        """code의 정규화 해시를 기록한다. 파싱 불가면 무시."""
        try:
            h = normalized_ast_hash(code)
        except SyntaxError:
            return
        self._hashes.append(h)
