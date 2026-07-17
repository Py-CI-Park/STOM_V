"""챔피언 매수식 절 파서/검증기 — 원문 sha 봉인 대조 + 50원자/39유니크 구조 검증.

사전등록 §3: 절 파싱은 W5 어휘 사전(method='ast.Compare + bare-name If.test
guards')과 passport 원문 재사용, 원문 sha 봉인 대조. 본 모듈은 그 method 를 그대로
재현해 원문(sha 348c5181...)에서 원자 술어를 추출하고, 정확-문자열 중복제거 후
39 유니크가 CLAUSE_SPECS 와 일관됨을 검증한다(파싱은 read-only·설계 입력).

원자 = 모든 ast.Compare 노드 + 제어변수(매수/매도)가 아닌 bare-name If.test.
"""
from __future__ import annotations

import ast
import hashlib
from collections import Counter
from typing import Dict, List, Tuple

from alpha_lab.clause_lab.clauses import (
    CHAMPION_BUY_SHA256,
    CHAMPION_BUY_STRATEGY_NAME,
    CLAUSE_SPECS,
)
from alpha_lab.dataset.reader import connect_ro

__all__ = [
    "W5_BY_CAT",
    "extract_atomic_predicates",
    "load_champion_buy",
    "validate_clause_set",
    "verify_buy_sha",
]

# W5 어휘 사전 section1 by_cat(ALP_V4_RR8_12) 실측 — 원자 50절 카테고리 히스토그램.
W5_BY_CAT: Dict[str, int] = {
    "time_gate": 4, "cap_price": 10, "change_band": 8, "vi_round": 4,
    "surge_value": 9, "quote_qty": 9, "breakout_ma": 2, "exec_strength": 4,
}
_CONTROL_NAMES = frozenset({"매수", "매도"})


def verify_buy_sha(text: str, expected: str = CHAMPION_BUY_SHA256) -> str:
    """매수식 원문 sha256 검증 — 일치 시 hex 반환, 불일치 시 ValueError(blocked)."""
    actual = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ValueError(f"매수식 원문 sha 불일치: 실제 {actual} != 기대 {expected}")
    return actual


def load_champion_buy(
    strategy_db_path, name: str = CHAMPION_BUY_STRATEGY_NAME,
    expected_sha: str = CHAMPION_BUY_SHA256,
) -> str:
    """strategy.db stockbuy 에서 챔피언 매수식 원문을 read-only 로 읽고 sha 검증."""
    conn = connect_ro(strategy_db_path)
    try:
        row = conn.execute(
            'SELECT "전략코드" FROM stockbuy WHERE "index" = ?', (name,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or row[0] is None:
        raise ValueError(f"stockbuy 에 매수식 없음: {name!r}")
    text = str(row[0])
    verify_buy_sha(text, expected_sha)
    return text


def _normalize(node: ast.AST) -> str:
    """AST 노드 → 공백 정규화 unparse(정확-문자열 중복제거 키)."""
    return " ".join(ast.unparse(node).split())


def extract_atomic_predicates(text: str) -> List[str]:
    """매수식 원문 → 원자 술어 목록(등장 순서). W5 method 그대로.

    원자 = ast.Compare 노드 전부 + 제어변수 아닌 bare-name If.test. `if 매수:`
    같은 제어 가드는 제외. `not (A and B)` 는 내부 두 Compare 를 각각 원자로 센다.
    """
    tree = ast.parse(text)
    atoms: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            atoms.append(_normalize(node))
        elif isinstance(node, ast.If) and isinstance(node.test, ast.Name):
            if node.test.id not in _CONTROL_NAMES:
                atoms.append(_normalize(node.test))
    return atoms


def validate_clause_set(text: str) -> Dict[str, object]:
    """원문에서 원자/유니크를 추출해 사전등록 §3(50원자·39유니크) 및 CLAUSE_SPECS 정합 검증.

    반환: 구조 지표 dict. 불일치는 AssertionError(사전등록↔구현 불일치 → 중단·보고).
    """
    verify_buy_sha(text)
    atoms = extract_atomic_predicates(text)
    unique = list(dict.fromkeys(atoms))  # 정확-문자열 dedup, 순서 보존.

    n_atomic, n_unique = len(atoms), len(unique)
    assert n_atomic == 50, f"원자 술어 {n_atomic} != 50 (사전등록 §3)"
    assert n_unique == 39, f"유니크 절 {n_unique} != 39 (사전등록 §3)"

    # CLAUSE_SPECS 내부 정합.
    assert len(CLAUSE_SPECS) == 39, f"CLAUSE_SPECS {len(CLAUSE_SPECS)} != 39"
    mult_sum = sum(s.mult for s in CLAUSE_SPECS)
    assert mult_sum == 50, f"spec.mult 합 {mult_sum} != 50"
    nums = sorted(s.num for s in CLAUSE_SPECS)
    assert nums == list(range(1, 40)), f"절 # 누락/중복: {nums}"

    # 카테고리 히스토그램 = W5 by_cat(원자 기준, mult 가중).
    spec_by_cat: Counter = Counter()
    for s in CLAUSE_SPECS:
        spec_by_cat[s.cat] += s.mult
    assert dict(spec_by_cat) == W5_BY_CAT, (
        f"카테고리 히스토그램 불일치: specs {dict(spec_by_cat)} vs W5 {W5_BY_CAT}"
    )

    # 원자 등장 횟수(정확-문자열) 다중도 합 = mult 합 = 50 (dedup 무결성).
    atom_counts = Counter(atoms)
    assert sum(atom_counts.values()) == 50
    # 각 유니크 원자의 등장 횟수 최댓값(#6 시분초<90200, #5 시가총액<3000 등 mult 2 존재).
    max_mult = max(atom_counts.values())

    return {
        "buy_sha256": CHAMPION_BUY_SHA256,
        "n_atomic": n_atomic,
        "n_unique": n_unique,
        "n_specs": len(CLAUSE_SPECS),
        "spec_mult_sum": mult_sum,
        "by_cat_specs": dict(spec_by_cat),
        "by_cat_w5": W5_BY_CAT,
        "by_cat_match": dict(spec_by_cat) == W5_BY_CAT,
        "max_atom_multiplicity": max_mult,
        "unique_atoms": unique,
        "atom_multiplicity": dict(atom_counts),
    }
