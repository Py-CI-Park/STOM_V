"""의도-일치 게이트 (QSP1 P2) — "요청된 수정만 정확히 반영됐는가"의 기계 판정.

사용자 요구(2026-07-29): "생성된 조건식을 다시 원하는 대로 잘 생성되었는지 ai 가
검토하고 판정하여 다시 백테스트 돌리는 과정".

판정 절차(전부 결정적 — LLM 불필요):
  V1 구문/골격  : 새 코드가 파싱되고, 상수 마스킹 AST 지문이 원본과 동일(골격 불변).
  V2 diff⊆spec : 실제 변경(diff_leaves)이 명세의 (리프, 절, old→new) 와 정확히 일치
                 하고, 명세 밖 변경이 0건.
  V3 수정 상한  : 변경 절 수 ≤ max_clauses(기본 3 — analysis_to_revision 계약).
  V4 preflight  : 구문·SSOT 어휘·엔진 시그니처(기존 strategy_preflight 재사용).

결과는 GateResult(ok, violations[]) — 위반은 코드(V1~V4)와 사람이 읽는 사유를 담는다.
재백테 강제는 게이트 밖 러너(P3)의 책임이다(게이트 통과 ≠ 성능 개선).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from .hier_ast import diff_leaves, skeleton_fp

DEFAULT_MAX_CLAUSES = 3


@dataclass
class Violation:
    code: str      # V1_SKELETON | V2_OFF_SPEC | V2_MISSING | V3_TOO_MANY | V4_PREFLIGHT
    detail: str


@dataclass
class GateResult:
    ok: bool
    violations: List[Violation] = field(default_factory=list)
    diffs: List[Dict[str, Any]] = field(default_factory=list)   # 실제 변경(감사 기록용)

    @property
    def reason(self) -> str:
        return " · ".join(f"{v.code}: {v.detail}" for v in self.violations) or "ok"


def _spec_key(spec: Dict[str, Any]):
    return (tuple(spec.get("leaf") or ()), str(spec.get("clause_ident") or ""))


def verify(old_code: str, new_code: str, specs: Sequence[Dict[str, Any]], *,
           max_clauses: int = DEFAULT_MAX_CLAUSES,
           ssot: Optional[set] = None) -> GateResult:
    """원본/생성물/명세 목록 → 의도-일치 판정.

    specs 는 이 생성물이 반영해야 할 명세 전체(1개 이상). 명세에 없는 변경은 전부 위반.
    """
    violations: List[Violation] = []

    # V1 — 구문·골격.
    if skeleton_fp(new_code) is None:
        return GateResult(False, [Violation("V1_SKELETON", "생성물 구문 오류")])
    diffs, reason = diff_leaves(old_code, new_code)
    if diffs is None:
        return GateResult(False, [Violation("V1_SKELETON", reason)])

    # V2 — diff ⊆ spec (정확 일치).
    want: Dict[Any, Dict[str, Any]] = {_spec_key(s): s for s in specs}
    seen = set()
    for d in diffs:
        key = (d.leaf, d.clause_ident)
        spec = want.get(key)
        if spec is None:
            violations.append(Violation(
                "V2_OFF_SPEC",
                f"명세 밖 변경: {d.leaf} {d.clause_ident} {list(d.old)}→{list(d.new)}"))
            continue
        if [float(x) for x in d.old] != [float(x) for x in spec.get("old_consts") or []] \
                or [float(x) for x in d.new] != [float(x) for x in spec.get("new_consts") or []]:
            violations.append(Violation(
                "V2_OFF_SPEC",
                f"명세와 값 불일치: {d.leaf} {d.clause_ident} "
                f"실제 {list(d.old)}→{list(d.new)} vs 명세 "
                f"{spec.get('old_consts')}→{spec.get('new_consts')}"))
            continue
        seen.add(key)
    for key, spec in want.items():
        if key not in seen:
            violations.append(Violation(
                "V2_MISSING", f"명세 미반영: {spec.get('leaf')} {spec.get('clause_ident')}"))

    # V3 — 수정 상한.
    if len(diffs) > max_clauses:
        violations.append(Violation(
            "V3_TOO_MANY", f"변경 절 {len(diffs)}개 > 상한 {max_clauses}"))

    # V4 — preflight(구문·어휘·엔진 시그니처).
    try:
        from ai_strategy_loop.controller.strategy_preflight import validate_strategy_code  # noqa: PLC0415

        pf = validate_strategy_code(new_code, ssot=ssot)
        if not pf.ok:
            violations.append(Violation("V4_PREFLIGHT", pf.reason))
    except Exception as exc:  # noqa: BLE001 - preflight 불가 환경에서는 V4 만 생략.
        violations.append(Violation("V4_PREFLIGHT", f"preflight 실행 불가: {exc}"))

    return GateResult(
        ok=not violations,
        violations=violations,
        diffs=[{"leaf": list(d.leaf), "clause": d.clause_ident,
                "old": list(d.old), "new": list(d.new)} for d in diffs],
    )
