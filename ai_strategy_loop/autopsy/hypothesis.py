"""가정(Hypothesis) 루프 코어 (P2a) — 부검 방향성 예측을 1급 객체로.

배경/철학(§3.16-D 천장 의심): 사용자는 "실행→분석→**가정**→개선→실행" 과학적
방법 루프를 원한다. 부검(summarize)은 이미 방향성 예측을 만든다
(gate_failure_directive: "MDD 초과→매도 손절강화", "손익 음수→진입품질↑",
"거래 부족→진입완화"; _discriminator_line: std_mean_diff 부호로 기준↑/↓). 그러나
이 예측이 NL 문자열로 즉시 소모되고 **채택/기각 판정이 없어** refine가 같은
빗나간 가정을 반복한다.

이 모듈은 그 방향성 예측을 **1급 Hypothesis 객체**로 만들고, 이미 영속되는 부모
대비 숫자 델타(P1b, generations.d_mdd/d_profit/d_daily_trades/d_graded 등)로
**자동 채택/기각**한다(추가 백테 0회). 즉 다음 세대의 실측 델타가 직전 세대가 세운
가정을 검증하는 결정론 오라클이 된다.

설계 원칙(CLAUDE.md 단순설계):
  - 순수 데이터·순수 함수만(엔진/하드게이트/백테 무관, 부작용 없음, 단위테스트 가능).
  - gate_failure_directive의 분기 조건을 **그대로** 미러한다(부검과 가정이 같은
    원인에서 출발). 단일 지표 매핑이 모호한 discriminator-수준 가정은 P2a 범위 제외.
  - 입력 불변(immutability) — adjudicate는 새 리스트를 반환하고 입력을 변형하지 않는다.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# 판정(verdict) 상태 — 직렬화에 그대로 쓰이는 리터럴.
#   untested      : 아직 다음 세대 델타로 검증되지 않음(방출 직후 기본값).
#   accepted      : 실측 델타 부호가 기대 방향과 일치(가정이 맞았다).
#   rejected      : 실측 델타 부호가 기대 방향과 반대(가정이 빗나갔다).
#   inconclusive  : 델타가 없거나(부모 없음/키 누락) eps 이하라 가를 수 없다.
VERDICT_UNTESTED = "untested"
VERDICT_ACCEPTED = "accepted"
VERDICT_REJECTED = "rejected"
VERDICT_INCONCLUSIVE = "inconclusive"

# target_metric → P1b 델타 키 매핑. 가정이 겨냥하는 지표를 다음 세대의 부모 대비
#   숫자 델타(deltas dict)에서 어떤 키로 읽을지 정의한다.
_METRIC_TO_DELTA_KEY: Dict[str, str] = {
    "mdd": "d_mdd",
    "profit": "d_profit",
    "daily_avg_trades": "d_daily_trades",
    "graded": "d_graded",
}

# 판정 임계 — 부동소수 잡음(0 근방)을 inconclusive로 처리하는 절대 하한.
_EPS = 1e-9


@dataclass
class Hypothesis:
    """루프가 세운 단일 가정(사람이 읽는 한 줄 + 기계가 판정하는 메타).

    side             : 'buy'|'sell'|'both' — 이 가정이 어느 측 전략을 고치려는가.
    text             : 사람이 읽는 한 줄 가정(NL).
    target_metric    : 'mdd'|'profit'|'daily_avg_trades'|'graded' — 판정 대상 지표.
    expected_direction: +1(증가 기대) | -1(감소 기대) — 다음 세대에서 이 지표가
                        어느 쪽으로 움직여야 가정이 맞은 것인가.
    source           : 'gate_mdd'|'gate_profit'|'gate_trades'|'refine_baseline' —
                        가정의 출처(부검 분기/베이스라인).
    basis            : 근거 수치 한 줄(예: 'MDD 18.2 > cap 12'). 비어 있을 수 있다.
    verdict          : 'untested'|'accepted'|'rejected'|'inconclusive'.
    observed_delta   : 판정에 쓰인 실측 델타(부호 포함). 미판정/델타없음이면 None.
    """

    side: str
    text: str
    target_metric: str
    expected_direction: int
    source: str
    basis: str = ""
    verdict: str = VERDICT_UNTESTED
    observed_delta: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화용 dict (hypotheses_json 영속에 사용)."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hypothesis":
        """to_dict 역변환. 알 수 없는 키는 무시한다(스키마 진화에 안전)."""
        known = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**filtered)


def build_hypotheses(
    *,
    gate_passed: bool,
    mdd: float,
    mdd_cap: float,
    total_profit: float,
    trade_count: int,
    min_trades: int,
    is_refine: bool,
) -> List[Hypothesis]:
    """이 세대의 결과에서 다음 세대용 가정 목록을 세운다.

    gate_failure_directive(summarize.py)의 분기 조건을 그대로 미러한다 — 부검이
    "이 원인을 겨냥하라"고 NL로 지시하는 바로 그 지점에서, 같은 원인을 1급
    Hypothesis로도 방출한다. 그래서 부검 NL과 가정이 항상 같은 원인에서 출발한다.

    규칙:
      - is_refine(부모 있는 세대)면 항상 baseline 가정 1개(refine로 graded 개선 기대).
      - gate 실패면 실패 원인별로(거래 부족/MDD 초과/손익 음수) 각각 가정 1개.
      - gate 통과면 gate 실패 가정은 없다(원인이 없으므로).

    discriminator-수준 가정(어느 진입 변수의 기준을 올려라/내려라)은 단일 지표
    매핑이 모호해 P2a 범위에서 제외한다. baseline + gate 원인만 다룬다.
    """
    hyps: List[Hypothesis] = []

    # refine(부모 있는 세대)는 항상 "직전 대비 graded 개선"을 기대한다(베이스라인).
    if is_refine:
        hyps.append(Hypothesis(
            side="both",
            text="refine로 직전 세대 대비 graded 개선 기대",
            target_metric="graded",
            expected_direction=+1,
            source="refine_baseline",
        ))

    if not gate_passed:
        # gate_failure_directive와 동일 조건/순서(거래 부족 → MDD 초과 → 손익 음수).
        if min_trades > 0 and trade_count < min_trades:
            hyps.append(Hypothesis(
                side="buy",
                text="진입 완화로 일평균 거래 증가 기대",
                target_metric="daily_avg_trades",
                expected_direction=+1,
                source="gate_trades",
                basis=f"{trade_count}<{min_trades}",
            ))
        if mdd_cap > 0 and abs(mdd) > mdd_cap:
            hyps.append(Hypothesis(
                side="sell",
                text="매도 손절 강화로 MDD 감소 기대",
                target_metric="mdd",
                expected_direction=-1,
                source="gate_mdd",
                basis=f"MDD {abs(mdd):.4g}>cap {mdd_cap:.4g}",
            ))
        if total_profit < 0:
            hyps.append(Hypothesis(
                side="buy",
                text="진입 품질 향상으로 총손익 흑자전환 기대",
                target_metric="profit",
                expected_direction=+1,
                source="gate_profit",
                basis=f"손익 {total_profit:,.0f}",
            ))

    return hyps


def adjudicate(
    hyps: List[Hypothesis],
    deltas: Optional[Dict[str, float]],
) -> List[Hypothesis]:
    """다음 세대의 부모 대비 델타(P1b)로 각 가정을 채택/기각/판정불가한다.

    deltas는 _build_parent_diff_and_deltas가 만든 dict
    ({"d_mdd":.., "d_profit":.., "d_daily_trades":.., "d_graded":.., ...}).
    None이거나 target_metric에 대응하는 키가 없으면 inconclusive(부모 없는 세대 등).

    판정 규칙(가정별):
      - observed = deltas[_METRIC_TO_DELTA_KEY[target_metric]].
        없음/deltas None → verdict=inconclusive, observed_delta=None.
      - abs(observed) < eps → inconclusive(움직임 없음), observed_delta=observed.
      - (observed>0) == (expected_direction>0) → accepted, else rejected.

    불변성: 입력 hyps를 변형하지 않고 **새 Hypothesis 리스트**를 반환한다
    (프로젝트 immutability 선호). dataclasses.replace로 verdict/observed_delta만 바꾼다.
    """
    out: List[Hypothesis] = []
    for h in hyps:
        delta_key = _METRIC_TO_DELTA_KEY.get(h.target_metric)
        observed = None
        if deltas is not None and delta_key is not None and delta_key in deltas:
            raw = deltas.get(delta_key)
            if raw is not None:
                observed = float(raw)

        if observed is None:
            verdict = VERDICT_INCONCLUSIVE
        elif abs(observed) < _EPS:
            verdict = VERDICT_INCONCLUSIVE
        elif (observed > 0) == (h.expected_direction > 0):
            verdict = VERDICT_ACCEPTED
        else:
            verdict = VERDICT_REJECTED

        out.append(dataclasses.replace(
            h, verdict=verdict, observed_delta=observed,
        ))
    return out
