"""N4 (2026-06-11) — 시간 무결성(미래참조) 정적 가드.

근거: 함수 시간 의미론 감사(docs/research/condition_research/
2026-06-11_time_semantics_and_market_integrity_audit.md). base_strategy의
파라미터 함수들은 indexn(현재 틱) 기준 과거 슬라이스를 쓰므로 정상 인자에선
안전하지만, **인자 검증이 없어** 다음 두 패턴이 미래 인덱스 접근이 된다:

  - 윈도우 인자 tick <= 0:  sidx = indexn+1-tick → 미래 (감사 §4.2)
  - 시프트 인자 pre < -1:   ridx = indexn - pre → 미래 (감사 §4.1)
    (-1은 매수 시점 인덱스(indexb) 지정 센티널이라 허용)

리터럴 인자만 정적으로 판정한다(변수 인자는 판정 불가 — 통과, compile/scope
가드는 별도). 백테스트 흑자·실거래 붕괴의 근원 차단이 목적이다.
"""
from __future__ import annotations

import ast
from typing import List, Optional

# 첫 번째 위치 인자가 '윈도우(틱/봉 수)'인 파라미터 함수들 — 감사 표 기준.
WINDOW_FUNCS = frozenset({
    "이동평균", "최고현재가", "최저현재가", "초당거래대금평균", "등락율각도",
    "최고분봉고가", "최저분봉저가", "분봉이동평균", "초당체결강도평균",
    "초당매수수량평균", "초당매도수량평균", "당일거래대금각도",
})


def _literal_number(node: ast.AST) -> Optional[float]:
    """리터럴 숫자(음수 단항 포함)면 값을, 아니면 None을 반환한다."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))):
        return -float(node.operand.value)
    return None


def check_time_integrity(code: str) -> List[str]:
    """미래참조가 되는 리터럴 인자 패턴을 찾는다. 통과면 빈 리스트."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # 구문 오류는 compile 가드 담당 — 중복 보고하지 않는다.
    errors: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        else:
            continue
        values = [_literal_number(a) for a in node.args]
        if name in WINDOW_FUNCS:
            if values and values[0] is not None and values[0] < 1:
                errors.append(
                    f"time_integrity: {name}() 윈도우 인자 {values[0]:g} < 1"
                    " — 미래 인덱스 접근(감사 §4.2)"
                )
            for v in values[1:]:
                if v is not None and v < -1:
                    errors.append(
                        f"time_integrity: {name}() 시프트 인자 {v:g} < -1"
                        " — 미래 인덱스 접근(감사 §4.1)"
                    )
        elif name.endswith("N"):  # 현재가N·체결강도N·전일동시간비N 등 N-계열.
            for v in values:
                if v is not None and v < -1:
                    errors.append(
                        f"time_integrity: {name}() 인자 {v:g} < -1"
                        " — 미래 인덱스 접근(감사 §4.1, -1은 매수시점 센티널 허용)"
                    )
    return errors
