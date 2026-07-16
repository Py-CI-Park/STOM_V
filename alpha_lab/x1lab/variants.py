"""X1 매수식 역생산 절 삭제 변형 생성·검증 (봉인본 §4·§14-F5·§14-F6).

원문(stockbuy ALP_V4_RR8_12, sha 348c5181) 정독 결과 = 시분초 상호배타 2가지
(902 `시분초<90200` / 905 `90200≤시분초<90700`)의 DNF. 후보 4종:

  DROP15 = 회전율>1.5 (902 `1.5<회전율` + 905 `회전율>1.5`, 양 가지 공통 가드)  → 라인 삭제(양쪽)
  DROP29 = 매도총잔량*0.1<매수총잔량 (905 단독 단순 라인)                         → 라인 삭제
  DROP31 = 매도총잔량>매수총잔량*0.1 (902 단독, #30과 AND 복합 라인)             → 라인 내 편집(#30 보존, §14-F6)
  DROP5  = 시가총액<3000 (902·905 공통 게이트 `if…else 매수=False`)             → 게이트 무력화(if True + else 제거, §14-F5)

시너지 보호(삭제 금지, §3): #16·#17(현재가 대역 족, 16×37·16×38 시너지).

각 변형: 원문 대비 **예상 편집만**(bit-diff 화이트리스트 — 화이트리스트 밖 변경 시
예외) + sha256 + 컴파일 검증(엔진 GetBuyStg 미러: 주석·self.indicator 제거 후 compile).
엔진 백테 0회·DB 미접촉(원문은 read-only 로드). 실 strategy.db 등록은 orchestrate 소관.
"""
from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from alpha_lab.clause_lab.clauses import (
    CHAMPION_BUY_SHA256,
    CHAMPION_BUY_STRATEGY_NAME,
)
from alpha_lab.clause_lab.parser import load_champion_buy

__all__ = [
    "CANDIDATES",
    "CANDIDATE_META",
    "VariantResult",
    "VariantError",
    "champion_buy_text",
    "compile_check",
    "generate_variant",
    "generate_all",
    "sha256_of",
    "strategy_name",
]

CANDIDATES: Tuple[str, ...] = ("DROP5", "DROP15", "DROP29", "DROP31")

# 절 번호(D1)·설명 — 리포트/원장 메타.
CANDIDATE_META: Dict[str, Dict[str, object]] = {
    "DROP5": {"clause": 5, "desc": "시가총액<3000 게이트(902·905 공통)",
              "branch": "902+905", "kind": "gate_disable",
              "d1_delta_pp": -0.125, "n_unsat": 528237, "inflow": "large"},
    "DROP15": {"clause": 15, "desc": "회전율>1.5 가드(902·905 공통)",
               "branch": "902+905", "kind": "line_delete",
               "d1_delta_pp": -0.120, "n_unsat": 377733, "inflow": "large"},
    "DROP29": {"clause": 29, "desc": "매도총잔량*0.1<매수총잔량(905 단독)",
               "branch": "905", "kind": "line_delete",
               "d1_delta_pp": -0.167, "n_unsat": 3687, "inflow": "sparse"},
    "DROP31": {"clause": 31, "desc": "매도총잔량>매수총잔량*0.1(902 단독, #30 보존)",
               "branch": "902", "kind": "line_edit",
               "d1_delta_pp": -0.238, "n_unsat": 2122, "inflow": "sparse"},
}

_BODY_STRIP = "매수 = False"


class VariantError(Exception):
    """변형 생성/검증 실패 — 화이트리스트 밖 변경·미매칭·컴파일 오류."""


@dataclass
class VariantResult:
    candidate: str
    text: str
    sha256: str
    removed_lines: List[str] = field(default_factory=list)
    added_lines: List[str] = field(default_factory=list)
    ops: List[str] = field(default_factory=list)
    compile_ok: bool = False


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strategy_name(candidate: str) -> str:
    """변형 전략명 — 절 번호 기준 `ALP_X1_DROP<절번호>`(레지스트라 ALP_ 접두 강제)."""
    return f"ALP_X1_{candidate}"


def champion_buy_text(strategy_db_path) -> str:
    """챔피언 매수식 원문 로드 + sha 348c5181 검증(clause_lab.parser 재사용, read-only)."""
    return load_champion_buy(strategy_db_path, CHAMPION_BUY_STRATEGY_NAME,
                             CHAMPION_BUY_SHA256)


# ---------------------------------------------------------------------------
# 라인 단위 편집 원자 연산 — stripped 내용으로 매칭, 원 들여쓰기 보존.
# ---------------------------------------------------------------------------

def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" "))]


def _find_unique(lines: List[str], stripped: str, *, expected: int = 1) -> List[int]:
    """stripped 내용이 정확히 일치하는 라인 인덱스 — 등장 수가 expected 와 다르면 예외."""
    idxs = [i for i, ln in enumerate(lines) if ln.strip() == stripped]
    if len(idxs) != expected:
        raise VariantError(
            f"매칭 라인 수 불일치: {stripped!r} 기대 {expected} 실제 {len(idxs)}")
    return idxs


def _op_remove_guard(lines: List[str], elif_stripped: str,
                     removed: List[str]) -> List[str]:
    """`elif not (P):` + 다음 `매수 = False` 2줄 삭제(단순 가드). 등장 1회 강제."""
    idxs = _find_unique(lines, elif_stripped, expected=1)
    i = idxs[0]
    if i + 1 >= len(lines) or lines[i + 1].strip() != _BODY_STRIP:
        raise VariantError(f"가드 body 미검출: {elif_stripped!r} 다음 줄")
    if len(_indent_of(lines[i + 1])) <= len(_indent_of(lines[i])):
        raise VariantError(f"body 들여쓰기 이상: {elif_stripped!r}")
    removed.extend([lines[i], lines[i + 1]])
    return lines[:i] + lines[i + 2:]


def _op_edit_line(lines: List[str], old_stripped: str, new_stripped: str,
                  removed: List[str], added: List[str]) -> List[str]:
    """라인 내 편집(들여쓰기 보존) — old→new. 등장 1회 강제."""
    idxs = _find_unique(lines, old_stripped, expected=1)
    i = idxs[0]
    new_line = _indent_of(lines[i]) + new_stripped
    removed.append(lines[i])
    added.append(new_line)
    out = list(lines)
    out[i] = new_line
    return out


def _op_disable_gate(lines: List[str], gate_stripped: str,
                     removed: List[str], added: List[str]) -> List[str]:
    """게이트 `if 시가총액<3000:` → `if True:` + 짝 `else:`/`매수=False` 제거(§14-F5).

    두 가지(902·905) 모두 처리. 짝 else = if 와 같은 들여쓰기의 다음 else(그 사이
    더 깊은 블록만) — 구조상 각 게이트 바로 뒤 최초 동일-들여쓰기 else.
    """
    gate_idxs = _find_unique(lines, gate_stripped, expected=2)
    work = list(lines)
    # 뒤에서부터 처리(앞 인덱스 안정성).
    for gi in sorted(gate_idxs, reverse=True):
        indent = _indent_of(work[gi])
        # 짝 else: gi 이후, 동일 들여쓰기, stripped=="else:" 인 최초 라인.
        else_i = None
        for j in range(gi + 1, len(work)):
            ind_j = _indent_of(work[j])
            if work[j].strip() == "" :
                continue
            if len(ind_j) < len(indent):
                break  # 블록 이탈(게이트보다 얕음) — 짝 else 없음.
            if len(ind_j) == len(indent) and work[j].strip() == "else:":
                else_i = j
                break
        if else_i is None:
            raise VariantError(f"게이트 짝 else 미검출: idx {gi}")
        if else_i + 1 >= len(work) or work[else_i + 1].strip() != _BODY_STRIP:
            raise VariantError(f"게이트 else body 미검출: else idx {else_i}")
        if len(_indent_of(work[else_i + 1])) <= len(indent):
            raise VariantError(f"else body 들여쓰기 이상: else idx {else_i}")
        # else + body 제거.
        removed.extend([work[else_i], work[else_i + 1]])
        work = work[:else_i] + work[else_i + 2:]
        # if 시가총액<3000: → if True: (들여쓰기 보존).
        new_if = indent + "if True:"
        removed.append(work[gi])
        added.append(new_if)
        work[gi] = new_if
    return work


# 후보별 변형 생성기(원문 lines → 변형 lines, removed/added 기록).
def _gen_drop15(lines, removed, added):
    lines = _op_remove_guard(lines, "elif not (1.5 < 회전율):", removed)   # 902
    lines = _op_remove_guard(lines, "elif not (회전율 > 1.5):", removed)   # 905(#39)
    return lines


def _gen_drop29(lines, removed, added):
    return _op_remove_guard(
        lines, "elif not (매도총잔량 * 0.10 < 매수총잔량 * 1.0):", removed)  # 905


def _gen_drop31(lines, removed, added):
    return _op_edit_line(
        lines,
        "elif not (매도총잔량 > 매수총잔량 * 0.10 and 매도총잔량 < 매수총잔량 * 2.0):",
        "elif not (매도총잔량 < 매수총잔량 * 2.0):",  # #30 보존
        removed, added)


def _gen_drop5(lines, removed, added):
    return _op_disable_gate(lines, "if 시가총액 < 3000:", removed, added)


_GENERATORS: Dict[str, Callable] = {
    "DROP5": _gen_drop5,
    "DROP15": _gen_drop15,
    "DROP29": _gen_drop29,
    "DROP31": _gen_drop31,
}


# ---------------------------------------------------------------------------
# bit-diff 화이트리스트 검증 — 실제 diff 가 ops 기록과 정확히 일치해야.
# ---------------------------------------------------------------------------

def _verify_bitdiff(original: str, variant: str,
                    removed: List[str], added: List[str]) -> None:
    """difflib 라인 diff 가 ops 가 기록한 removed/added 와 정확히 일치하는지 검증.

    화이트리스트 밖 변경(예상 외 삭제/추가)이 하나라도 있으면 VariantError.
    """
    diff = list(difflib.unified_diff(
        original.splitlines(), variant.splitlines(), lineterm="", n=0))
    diff_removed = [d[1:] for d in diff
                    if d.startswith("-") and not d.startswith("---")]
    diff_added = [d[1:] for d in diff
                  if d.startswith("+") and not d.startswith("+++")]
    if sorted(diff_removed) != sorted(removed):
        raise VariantError(
            f"bit-diff 삭제 불일치: diff={diff_removed} ops={removed}")
    if sorted(diff_added) != sorted(added):
        raise VariantError(
            f"bit-diff 추가 불일치: diff={diff_added} ops={added}")
    if variant == original:
        raise VariantError("변형이 원문과 동일(편집 미적용)")


def compile_check(buy_text: str) -> bool:
    """엔진 GetBuyStg(backtest/back_static.py) 미러 — 주석·self.indicator 제거 후 compile.

    구문 오류 시 VariantError. 이름 미정의(현재가 등)는 compile 대상 아님(런타임).
    """
    src_lines = [ln for ln in buy_text.split("\n") if ln and ln[0] != "#"]
    buystg = "\n".join(ln for ln in src_lines if "self.indicator" not in ln)
    if not buystg.strip():
        raise VariantError("컴파일 대상 비어있음(전 라인 주석/indicator)")
    try:
        compile(buystg, "<x1_buy>", "exec")
    except SyntaxError as exc:  # noqa: PERF203
        raise VariantError(f"변형 매수식 컴파일 실패(SyntaxError): {exc}") from exc
    return True


def generate_variant(candidate: str, original_text: str) -> VariantResult:
    """후보 1종 변형 생성 + bit-diff 화이트리스트 검증 + 컴파일 검증."""
    if candidate not in _GENERATORS:
        raise VariantError(f"알 수 없는 후보: {candidate!r}")
    removed: List[str] = []
    added: List[str] = []
    lines = original_text.split("\n")
    new_lines = _GENERATORS[candidate](lines, removed, added)
    variant = "\n".join(new_lines)
    _verify_bitdiff(original_text, variant, removed, added)
    ok = compile_check(variant)
    return VariantResult(
        candidate=candidate, text=variant, sha256=sha256_of(variant),
        removed_lines=removed, added_lines=added,
        ops=[f"{candidate}:{CANDIDATE_META[candidate]['kind']}"], compile_ok=ok)


def generate_all(original_text: str) -> Dict[str, VariantResult]:
    """후보 4종 전부 생성·검증. 원문 sha 재확인은 호출측(champion_buy_text)."""
    return {c: generate_variant(c, original_text) for c in CANDIDATES}
