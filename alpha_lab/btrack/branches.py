"""챔피언 RR8_12 매수식 가지(branch) 상수 — 봉인본 §3 매핑 정본.

원문(sha 348c5181, `clause_lab/parser.load_champion_buy`)은 시간-분리 DNF:
`매수=True` → 공통필터(관심종목==1) → 시분초 elif 3분기(902/905/else=비발화) → `if 매수: Buy`.
두 시간게이트 bit_6(`시분초<90200`)·bit_21(`90200≤시분초<90700`)이 상호배타 →
flat 39-AND=∅. 챔피언 발동 프록시의 정본 = (902 24절 AND) ∨ (905 26절 AND).

가지 → D1 39비트 매핑(전부 실재·신규 비트 0). #39≡#15 순수 중복이라 bit_15 사용.
본 상수는 봉인 §3 표의 비트 목록과 문자 그대로 일치한다(모듈 로드 시 assert).
"""
from __future__ import annotations

from typing import Dict, Tuple

__all__ = [
    "BRANCH_905_NUMS", "BRANCH_902_NUMS", "BRANCHES", "BRANCH_BITS",
    "COMMON_BACKBONE", "TIME_GATE", "branch_bit_cols",
]

# §3 표 정본 — 902 가지(24 유니크절 AND, 시분초<90200).
BRANCH_902_NUMS: Tuple[int, ...] = (
    22, 6, 17, 14, 2, 10, 4, 5, 19, 13, 1, 11, 32, 7, 15, 25, 28, 3, 35, 37, 31, 30, 9, 8)
# §3 표 정본 — 905 가지(26 유니크절 AND, 90200≤시분초<90700). #39→#15.
BRANCH_905_NUMS: Tuple[int, ...] = (
    22, 21, 16, 18, 2, 10, 4, 36, 5, 12, 20, 1, 11, 33, 7, 15, 26, 27, 3, 34, 38, 29, 24, 23, 9, 8)

# 공통 등뼈 12절(두 가지 공유). 시간게이트(상호배타).
COMMON_BACKBONE: Tuple[int, ...] = (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 15, 22)
TIME_GATE: Dict[str, int] = {"902": 6, "905": 21}

BRANCHES: Dict[str, Tuple[int, ...]] = {"902": BRANCH_902_NUMS, "905": BRANCH_905_NUMS}


def branch_bit_cols(nums: Tuple[int, ...]) -> Tuple[str, ...]:
    """절 번호 튜플 → 비트 컬럼명 튜플(순서 보존)."""
    return tuple(f"bit_{n}" for n in nums)


BRANCH_BITS: Dict[str, Tuple[str, ...]] = {
    name: branch_bit_cols(nums) for name, nums in BRANCHES.items()}

# 봉인 검산(§3) — 절 수·유니크·유효 범위·공통 등뼈·시간게이트 상호배타.
assert len(BRANCH_902_NUMS) == 24 and len(set(BRANCH_902_NUMS)) == 24, "902 가지 ≠ 24 유니크절"
assert len(BRANCH_905_NUMS) == 26 and len(set(BRANCH_905_NUMS)) == 26, "905 가지 ≠ 26 유니크절"
assert all(1 <= n <= 39 for n in BRANCH_902_NUMS + BRANCH_905_NUMS), "절 번호 범위 위반"
assert set(BRANCH_902_NUMS) & set(BRANCH_905_NUMS) == set(COMMON_BACKBONE), (
    "공통 등뼈 불일치(§3 — 12절)")
assert len(COMMON_BACKBONE) == 12
# 시간게이트: 902=6·905=21, 상호 배타(교차 부재).
assert TIME_GATE["902"] in BRANCH_902_NUMS and TIME_GATE["902"] not in BRANCH_905_NUMS
assert TIME_GATE["905"] in BRANCH_905_NUMS and TIME_GATE["905"] not in BRANCH_902_NUMS
# 902 전용 12 · 905 전용 14.
assert len(set(BRANCH_902_NUMS) - set(BRANCH_905_NUMS)) == 12
assert len(set(BRANCH_905_NUMS) - set(BRANCH_902_NUMS)) == 14
