"""ALP_V2SEED_01~10 힐클라임 시드 — 실명 스펙 동결값 + 번역 헬퍼.

출처(동결값 그대로 전사 — 변경 금지, 새 사전등록 없이는 불변):
  docs/research/condition_research/plans/
  2026-07-06_alpha_lab_seed_handoff_to_hillclimb.md §1 시드 10건 표.
  (v2 최종 판정 — 부분 성공, 원장 v2_seed_feedback_receipt.jsonl 봉인 dcac7492)

P2(v3 EV 채굴) 생존 후보가 0건이므로(v3_mining_report.json final_candidates=0,
go=false) preregistration_v3.json hillclimb.seeds "P2 생존 후보 + ALP_V2SEED_01
~10"에 따라 본 10건이 힐클라임의 유일 시드 집합이다.

소비 규율(핸드오프 문서 §2, 그대로 적용):
  1) 시드는 출발점이지 완성품이 아님 — 힐클라임 변이 대상.
  2) 번역은 alpha_lab.translate.codegen 재사용 + 표본화 월드 가드 동반
     (SAMPLE_TIME_GUARD, UNIVERSE_GUARD_MONEYTOP_PROXY) — ρ게이트 재판정
     실측 요인.
  3) 매도식은 검증 hard-stop 계열 고정(sha 8ef01e0e) — 이 모듈은 매수식만
     다루고 매도식은 alpha_lab.hillclimb.sell_policy가 담당한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from alpha_lab.hillclimb.features_v3 import TranslationResult43, translate_leaf_rule_43
from alpha_lab.translate.codegen import SAMPLE_TIME_GUARD, UNIVERSE_GUARD_MONEYTOP_PROXY

__all__ = [
    "SEED_META",
    "SEED_RULES",
    "SEED_ORDER",
    "translate_seed",
]


@dataclass(frozen=True)
class SeedMeta:
    lift: float
    support: int
    year_repro_2023: float
    year_repro_2024: float


# 시드 10건 규칙 원문(핸드오프 문서 표 그대로, 소수 표기 보존). 순서는 표 순서
# (lift 내림차순)와 동일 — SEED_ORDER가 힐클라임 실행 순서 계약이다.
SEED_RULES: Dict[str, Tuple[Tuple[str, str, float], ...]] = {
    "ALP_V2SEED_01": (
        ("초당매수수량", ">", 101.5),
        ("전일비", "<=", 4.995),
        ("전일동시간비", ">", 869.9),
    ),
    "ALP_V2SEED_02": (
        ("초당거래대금", ">", 6.5),
        ("전일비", "<=", 5.045),
        ("전일동시간비", ">", 837.8),
    ),
    "ALP_V2SEED_03": (
        ("전일비", "<=", 1.705),
        ("시가총액", "<=", 35682.5),
        ("거래대금증감", "<=", -2.065e11),
    ),
    "ALP_V2SEED_04": (
        ("전일비", ">", 4.525),
        ("시가총액", ">", 19441.0),
        ("거래대금증감", "<=", -3.958e11),
        ("체결강도", "<=", 102.1),
    ),
    "ALP_V2SEED_05": (
        ("초당매수수량", ">", 101.5),
        ("전일비", "<=", 1.485),
        ("전일동시간비", "<=", 869.9),
    ),
    "ALP_V2SEED_06": (
        ("전일비", ">", 1.705),
        ("전일비", "<=", 4.525),
        ("시가총액", "<=", 47315.0),
        ("거래대금증감", "<=", -4.148e11),
    ),
    "ALP_V2SEED_07": (
        ("순매수수량비", ">", 0.0504),
        ("전일비", "<=", 4.735),
        ("등락율", ">", 1.565),
        ("저가대비고가등락율", "<=", 1.775),
    ),
    "ALP_V2SEED_08": (
        ("초당거래대금", ">", 6.5),
        ("전일비", "<=", 2.095),
        ("전일동시간비", "<=", 837.8),
    ),
    "ALP_V2SEED_09": (
        ("초당거래대금", "<=", 6.5),
        ("당일거래대금", "<=", 1290.5),
        ("등락율", ">", 2.055),
    ),
    "ALP_V2SEED_10": (
        ("전일비", "<=", 1.705),
        ("시가총액", "<=", 35682.5),
        ("거래대금증감", ">", -2.065e11),
    ),
}

SEED_ORDER: Tuple[str, ...] = tuple(SEED_RULES)

SEED_META: Dict[str, SeedMeta] = {
    "ALP_V2SEED_01": SeedMeta(3.242, 2038, 3.75, 2.58),
    "ALP_V2SEED_02": SeedMeta(3.199, 2012, 3.55, 2.69),
    "ALP_V2SEED_03": SeedMeta(3.098, 2000, 2.76, 3.50),
    "ALP_V2SEED_04": SeedMeta(2.648, 2000, 2.28, 2.87),
    "ALP_V2SEED_05": SeedMeta(2.630, 4004, 2.34, 3.03),
    "ALP_V2SEED_06": SeedMeta(2.523, 2000, 2.16, 2.82),
    "ALP_V2SEED_07": SeedMeta(2.486, 6760, 2.26, 2.83),
    "ALP_V2SEED_08": SeedMeta(2.330, 8038, 2.09, 2.65),
    "ALP_V2SEED_09": SeedMeta(2.225, 3382, 2.20, 2.25),
    "ALP_V2SEED_10": SeedMeta(2.210, 6579, 1.94, 2.60),
}

assert set(SEED_META) == set(SEED_RULES), "시드 메타/규칙 키 불일치"


def translate_seed(
    seed_name: str, *, round_digits: int = 1, use_repo_gate: bool = True
) -> TranslationResult43:
    """시드 하나를 표본화 월드 가드 동반 매수식으로 번역한다(43피처 번역기 재사용).

    가드는 핸드오프 문서 §2-2 권장 그대로: SAMPLE_TIME_GUARD
    (90001<=시분초<=92500) + UNIVERSE_GUARD_MONEYTOP_PROXY(관심종목>0).
    """
    rule = SEED_RULES[seed_name]
    return translate_leaf_rule_43(
        rule,
        time_guard=SAMPLE_TIME_GUARD,
        universe_guard=UNIVERSE_GUARD_MONEYTOP_PROXY,
        round_digits=round_digits,
        use_repo_gate=use_repo_gate,
    )
