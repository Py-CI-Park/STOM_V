"""결정론 힐클라임 뮤테이터 — 절 임계 분위 스텝 + 절 추가/제거 + 수락 규칙.

봉인 근거(preregistration_v3.json hillclimb 절, sha 50d3d38a):
  mutator: "절 임계 ±분위 스텝(2/5%p), 절 추가/제거(43 화이트리스트 내),
            매도식 고정(hard-stop 계열 sha 8ef01e0e)"
  accept:  "profit>0 AND ((profit up AND mdd<=) OR calmar up)"

설계 원칙:
  - 순수 함수만 — 엔진 호출·파일 I/O·난수 없음(결정론). 유일한 입력은 규칙
    (Clause 3-튜플 시퀀스)과 호출측이 미리 로드한 피처 분포(정렬된 배열)다.
  - Rule은 항상 (feature, op, threshold) 3-튜플의 튜플 — alpha_lab.translate.
    codegen이 받는 "결합(AND) 규칙" 계약과 그대로 호환된다.
  - generate_moves()의 반환 순서는 고정(threshold 이동 → 절 제거 → 절 추가)
    이며, 각 하위 순서도 입력 rule/화이트리스트 순서를 그대로 따른다 — 같은
    입력에 대해 항상 바이트 동일한 이동 리스트를 낸다(결정론 요구사항).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

__all__ = [
    "QUANTILE_STEPS_PP",
    "Clause",
    "Metrics",
    "Move",
    "Rule",
    "accept",
    "addition_moves",
    "generate_moves",
    "quantile_rank",
    "quantile_value",
    "removal_moves",
    "shift_threshold",
    "threshold_moves",
]

# 봉인 분위 스텝(%p) — 절 임계 이동 폭. 순서 고정(작은 스텝 먼저 — 출발점 원칙:
# 시드에서 최소로 벗어나는 이동을 먼저 시도한다).
QUANTILE_STEPS_PP: Tuple[float, ...] = (2.0, 5.0)

# 절 추가 시 결정론 기본 분위(고정폭 좁힘/넓힘 이웃 — 임의성 없음).
_ADD_HIGH_Q = 0.70
_ADD_LOW_Q = 0.30

# 힐클라임 임계값 내부 반올림(부동소수 노이즈 제거용 — 번역 시 round_digits=1이
# 다시 적용되므로 여기서는 유효숫자만 보존).
_THRESHOLD_ROUND_NDIGITS = 6

Clause = Tuple[str, str, float]
Rule = Tuple[Clause, ...]


@dataclass(frozen=True)
class Move:
    """생성된 이웃 하나 — kind는 진단/보고용, rule이 실제 다음 평가 대상."""

    kind: str  # "threshold" | "remove" | "add"
    rule: Rule
    desc: str


@dataclass(frozen=True)
class Metrics:
    """엔진 평가 1회의 결과(가공된 형태) — evaluate_fn의 반환 계약.

    profit_pct/mdd는 퍼센트 단위(예: 3.2, 14.18). status != "ok"는 엔진
    실패/무거래(no_trades/error)를 뜻하며 accept()는 이를 항상 거부한다.
    """

    status: str
    profit_pct: float = 0.0
    mdd: float = 0.0
    calmar: float = 0.0
    trade_count: int = 0
    daily_avg_trades: float = 0.0
    gate_passed: bool = False
    reason: str = ""


def quantile_rank(sorted_values: np.ndarray, threshold: float) -> float:
    """threshold 이하 값의 경험적 비율(0~1) — sorted_values는 오름차순 가정."""
    n = len(sorted_values)
    if n == 0:
        raise ValueError("빈 분포로는 분위를 계산할 수 없다")
    idx = int(np.searchsorted(sorted_values, threshold, side="right"))
    return idx / float(n)


def quantile_value(sorted_values: np.ndarray, q: float) -> float:
    """분위 q(0~1, clip)의 값 — sorted_values는 오름차순 가정."""
    if len(sorted_values) == 0:
        raise ValueError("빈 분포로는 분위 값을 구할 수 없다")
    q_clipped = min(max(q, 0.0), 1.0)
    return float(np.quantile(sorted_values, q_clipped))


def shift_threshold(sorted_values: np.ndarray, threshold: float, delta_pp: float) -> float:
    """threshold를 경험분포 분위 delta_pp(%p)만큼 이동한 새 임계값.

    현재 threshold의 분위 순위를 구하고 delta_pp/100을 더한 뒤 [0.0005, 0.9995]
    로 clip해 재매핑한다(극단 분위 폭주 방지 — 표본 최솟/최댓값 바로 안쪽).
    """
    rank = quantile_rank(sorted_values, threshold)
    new_rank = min(max(rank + delta_pp / 100.0, 0.0005), 0.9995)
    return round(quantile_value(sorted_values, new_rank), _THRESHOLD_ROUND_NDIGITS)


def threshold_moves(rule: Rule, distributions: Mapping[str, np.ndarray]) -> List[Move]:
    """절별 임계 분위 이동 이웃 — 순서: 절 인덱스 → %p(2,5) → 부호(+,-).

    분포가 없거나 비어있는 피처의 절은 스킵(정직 — 조용한 가짜 이웃 생성 금지).
    이동 결과가 원래 임계값과 같으면(경계 포화) 스킵한다.
    """
    moves: List[Move] = []
    for i, (feat, op, thr) in enumerate(rule):
        values = distributions.get(feat)
        if values is None or len(values) == 0:
            continue
        for pp in QUANTILE_STEPS_PP:
            for sign in (1.0, -1.0):
                new_thr = shift_threshold(values, float(thr), sign * pp)
                if new_thr == thr:
                    continue
                new_rule = rule[:i] + ((feat, op, new_thr),) + rule[i + 1:]
                moves.append(
                    Move(
                        "threshold",
                        new_rule,
                        f"clause[{i}] {feat}{op}{thr:.6g}->{new_thr:.6g}"
                        f"({sign * pp:+.0f}pp)",
                    )
                )
    return moves


def removal_moves(rule: Rule) -> List[Move]:
    """절 제거 이웃 — 규칙이 절 1개뿐이면(공규칙 방지) 생성하지 않는다."""
    if len(rule) <= 1:
        return []
    moves: List[Move] = []
    for i in range(len(rule)):
        new_rule = rule[:i] + rule[i + 1:]
        feat, op, thr = rule[i]
        moves.append(Move("remove", new_rule, f"remove clause[{i}] {feat}{op}{thr:.6g}"))
    return moves


def addition_moves(
    rule: Rule,
    whitelist: Sequence[str],
    distributions: Mapping[str, np.ndarray],
    max_candidates: int = 4,
) -> List[Move]:
    """절 추가 이웃 — 화이트리스트 순서로 미사용 피처를 최대 max_candidates개까지

    시도한다(각 피처당 강한 쪽 q0.70 초과/약한 쪽 q0.30 이하 2후보). 이미
    규칙에 있는 피처는 건너뛴다(중복 절 방지).
    """
    used = {feat for feat, _, _ in rule}
    moves: List[Move] = []
    tried_features = 0
    for feat in whitelist:
        if feat in used:
            continue
        values = distributions.get(feat)
        if values is None or len(values) == 0:
            continue
        hi = round(quantile_value(values, _ADD_HIGH_Q), _THRESHOLD_ROUND_NDIGITS)
        lo = round(quantile_value(values, _ADD_LOW_Q), _THRESHOLD_ROUND_NDIGITS)
        moves.append(Move("add", rule + ((feat, ">", hi),), f"add {feat}>{hi:.6g}(q{_ADD_HIGH_Q:.2f})"))
        moves.append(Move("add", rule + ((feat, "<=", lo),), f"add {feat}<={lo:.6g}(q{_ADD_LOW_Q:.2f})"))
        tried_features += 1
        if tried_features >= max_candidates:
            break
    return moves


def generate_moves(
    rule: Rule,
    whitelist: Sequence[str],
    distributions: Mapping[str, np.ndarray],
    max_add_candidates: int = 4,
) -> List[Move]:
    """현재 규칙의 결정론 이웃 전체 — threshold_moves + removal_moves + addition_moves.

    호출 순서·내용이 항상 고정(같은 인자 → 같은 리스트, 실행마다 재현 가능)이라
    루프가 "라운드 완주 시 수락 0건 → 로컬 최적" 조기중단을 결정적으로 판정한다.
    """
    return (
        threshold_moves(rule, distributions)
        + removal_moves(rule)
        + addition_moves(rule, whitelist, distributions, max_add_candidates)
    )


def accept(current: Metrics, candidate: Metrics) -> bool:
    """수락 규칙(봉인): profit>0 AND ((profit 상승 AND mdd 비악화) OR calmar 상승).

    candidate.status가 "ok"가 아니면(엔진 오류/무거래) 항상 거부한다.
    """
    if candidate.status != "ok":
        return False
    if not (candidate.profit_pct > 0):
        return False
    profit_up = candidate.profit_pct > current.profit_pct
    mdd_not_worse = candidate.mdd <= current.mdd
    calmar_up = candidate.calmar > current.calmar
    return (profit_up and mdd_not_worse) or calmar_up
