"""clause_lab — D1 챔피언 절-단위 A/B 분해 (사전등록 2026-07-12 봉인본).

봉인 사전등록: docs/research/condition_research/plans/
2026-07-12_d1_clause_ablation_preregistration.md (커밋 56564cba).

이 패키지는 챔피언 RR8_12 매수식(buy_sha 348c5181...)을 이루는 개별 가드 절을
온셋 풀 위의 단독 술어로 평가해, 챔피언 출구(L3) 실현 순손익이 절 단위로
갈리는지를 검정한다. 엔진 백테 0회 — 리플레이 라벨 재사용 + 벡터 절 평가만.

원본 tick DB 접근은 read-only URI 전용. print 금지 — logging.
"""
from __future__ import annotations

from alpha_lab.clause_lab.clauses import (
    CHAMPION_BUY_SHA256,
    CLAUSE_SPECS,
    FAMILIES,
    NAMESPACE_SYMBOLS,
    ClauseSpec,
    build_local_definitions,
    evaluate_clause_bits,
)

__all__ = [
    "CHAMPION_BUY_SHA256",
    "CLAUSE_SPECS",
    "FAMILIES",
    "NAMESPACE_SYMBOLS",
    "ClauseSpec",
    "build_local_definitions",
    "evaluate_clause_bits",
]
