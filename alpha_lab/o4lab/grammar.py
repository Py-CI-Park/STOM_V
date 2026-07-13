"""O-4 생성 문법 — 후보 열거·족 태깅 (봉인본 §3·§14).

슬롯(각 결과 관측 전 봉인 — §14-F2/F5/F6):
  F1 초당순매수금액(압력)          : 부재 | `1 < 초당순매수금액`      (o4_netbuy_gt1, 신규)
  F2 라운드피겨(압력/회피)         : 부재 | `라운드피겨위5호가이내==False`(bit_4, d1 재사용)
  F3 VI 상대가(압력/회피)          : 부재 | `현재가 < VI아래5호가`     (bit_10, d1 재사용)
  F4 초당매수수량 vs 매도총잔량(압력): 부재 | *0.22 | *0.35 | *0.50    (o4_qty_022/035/050, 신규)
  G  현재가 대역 가드(조건부)       : 부재 | <=30000(bit_16) | <=50000(bit_17) — **F4 present 시만**
  A  함정 회피(선택)               : 부재 | `시가등락율 < 8.0`        (o4_avoid_gap_lt8, 신규)

제약: ① ≥1 압력(F1~F4) present · ② G present ⟹ F4 present(유일 시너지 족=현재가대역×초당매수수량, §14-F5).

닫힌 수식(§3.2):  N = { (1+k₁)(1+k₂)(1+k₃)·[ k₄·(1+k_g) + 1 ] − 1 }·(1+a)
확정 격자(k₁=k₂=k₃=1·k₄=3·k_g=2·a=1) → N = {8·[3·3+1] − 1}·2 = 79·2 = **158**(= type-b 상한).

임계 재도출 비대칭(정직 문서화): F4 는 챔피언 원-임계 0.2/0.3 을 **회피**해 재도출(0.22/0.35/0.5)
하나(과적합 계승 방지·§14-F2), 가드 G 는 시너지가 **측정된 좌표**(현재가<=30000/50000, 16×37·16×38)
그대로 재사용한다(재도출하면 측정 시너지 근거와의 연결이 끊김·§14-F5). 둘 다 봉인 결정이다.

족(§8): 임계를 무시한 슬롯 구조(같은 present 슬롯 집합 = 1족) — 근접 중복 인플레 차단.
후보 1 = 시행 1(type-b). 기존 파일 무수정 — 신규 5비트는 bits.py, bit_4/10/16/17 은 d1 parquet 재사용.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

__all__ = [
    "CANDIDATES",
    "CHAMPION_AND_BITS",
    "N_CANDIDATES",
    "NEW_BITS",
    "REUSED_BITS",
    "Candidate",
    "enumerate_candidates",
    "families",
    "family_of",
]

# 확정 후보 상한(§14-F1) — 열거 결과가 이 값과 다르면 문법 봉인 위반(모듈 로드 시 assert).
N_CANDIDATES = 158

# 신규 비트(bits.py 가 발견창 온셋 위에서 산출) — threshold_id → 정규화 술어 텍스트(§14-F2/F6).
NEW_BITS: Dict[str, str] = {
    "o4_netbuy_gt1": "1 < 초당순매수금액",          # F1 — 원-절 `1<X<1000` 상한 제거 단측형(실재).
    "o4_qty_022": "초당매수수량 > 매도총잔량 * 0.22",  # F4 — 원-임계 0.2 회피 재도출.
    "o4_qty_035": "초당매수수량 > 매도총잔량 * 0.35",  # F4.
    "o4_qty_050": "초당매수수량 > 매도총잔량 * 0.50",  # F4.
    "o4_avoid_gap_lt8": "시가등락율 < 8.0",          # A — 상방 극단 갭 추격 회피(O-1G 갭+20% 최악).
}

# d1 비트 재사용(재산출 금지 — §14-F7·A-2 지시).
REUSED_BITS: Tuple[str, ...] = ("bit_4", "bit_10", "bit_16", "bit_17")

# 챔피언 발동 AND 프록시(§7·§14-F8) — 39절 플랫 AND(발화 과소추정 → overlap 하한).
CHAMPION_AND_BITS: Tuple[str, ...] = tuple(f"bit_{n}" for n in range(1, 40))

# 슬롯 옵션(present 만; 부재는 열거에서 None). (라벨, 비트 컬럼).
_F1: Tuple[Tuple[str, str], ...] = (("F1", "o4_netbuy_gt1"),)
_F2: Tuple[Tuple[str, str], ...] = (("F2", "bit_4"),)
_F3: Tuple[Tuple[str, str], ...] = (("F3", "bit_10"),)
_F4: Tuple[Tuple[str, str], ...] = (
    ("F4@0.22", "o4_qty_022"), ("F4@0.35", "o4_qty_035"), ("F4@0.50", "o4_qty_050"))
_G: Tuple[Tuple[str, str], ...] = (("G@30000", "bit_16"), ("G@50000", "bit_17"))
_A: Tuple[Tuple[str, str], ...] = (("A", "o4_avoid_gap_lt8"),)


@dataclass(frozen=True)
class Candidate:
    """후보 1개 = 슬롯 선택의 곱. cid = 라벨 결합, bits = AND 할 비트 컬럼(정렬)."""

    cid: str                       # 예: "F2+F4@0.22+G@30000+A".
    bits: Tuple[str, ...]          # AND 대상 비트 컬럼명(정렬 — 발화 = 전 비트 논리곱).
    slots: Tuple[str, ...]         # present 슬롯 라벨(임계 포함).
    family: str                    # 족 태그 = 임계 무시 슬롯 구조(§8).
    has_f4: bool = field(default=False)
    new_bits: Tuple[str, ...] = field(default=())   # 이 후보가 쓰는 신규 비트(부분집합).


def family_of(present_slot_names: Tuple[str, ...]) -> str:
    """족 태그 = 임계를 무시한 present 슬롯 구조(§8 — 임계만 다른 후보 = 1족).

    슬롯 라벨의 접두(F1/F2/F3/F4/G/A)만 정렬 결합한다(F4@0.22·F4@0.35 → 'F4').
    """
    prefixes = []
    for name in present_slot_names:
        p = name.split("@", 1)[0]
        if p not in prefixes:
            prefixes.append(p)
    return "|".join(sorted(prefixes))


def enumerate_candidates() -> Tuple[Candidate, ...]:
    """§3 닫힌 문법 전수 열거(제약 강제) → 후보 튜플. 결정론(정렬 안정)."""
    out: List[Candidate] = []
    for f1 in (None,) + _F1:
        for f2 in (None,) + _F2:
            for f3 in (None,) + _F3:
                for f4 in (None,) + _F4:
                    # 제약②: 가드 G 는 F4 present 일 때만 부재∪G_OPTS, 아니면 부재만.
                    g_choices = ((None,) + _G) if f4 is not None else (None,)
                    for g in g_choices:
                        for a in (None,) + _A:
                            present = tuple(x for x in (f1, f2, f3, f4, g, a) if x is not None)
                            # 제약①: ≥1 압력(F1~F4) present.
                            if not any(x is not None for x in (f1, f2, f3, f4)):
                                continue
                            labels = tuple(x[0] for x in present)
                            bits = tuple(sorted(x[1] for x in present))
                            new_bits = tuple(b for b in bits if b in NEW_BITS)
                            out.append(Candidate(
                                cid="+".join(labels), bits=bits, slots=labels,
                                family=family_of(labels), has_f4=f4 is not None,
                                new_bits=new_bits))
    return tuple(out)


CANDIDATES: Tuple[Candidate, ...] = enumerate_candidates()

# 봉인 검산(§14-F1) — 후보 수·중복·비트 사용 무결성.
assert len(CANDIDATES) == N_CANDIDATES, (
    f"후보 수 {len(CANDIDATES)} ≠ 봉인 {N_CANDIDATES}(§3.2 수식 위반)")
assert len({c.cid for c in CANDIDATES}) == N_CANDIDATES, "후보 ID 중복(열거 결함)"
for _c in CANDIDATES:
    assert not (any(b.startswith("bit_1") and b in ("bit_16", "bit_17") for b in _c.bits)
                and not _c.has_f4), f"가드 present인데 F4 부재({_c.cid}) — 제약② 위반"
    assert set(_c.bits) <= (set(NEW_BITS) | set(REUSED_BITS)), (
        f"미봉인 비트 사용({_c.cid}: {_c.bits})")


def families() -> Dict[str, Tuple[str, ...]]:
    """족 → 소속 후보 ID(§8 계상 단위)."""
    fam: Dict[str, List[str]] = {}
    for c in CANDIDATES:
        fam.setdefault(c.family, []).append(c.cid)
    return {k: tuple(v) for k, v in fam.items()}
