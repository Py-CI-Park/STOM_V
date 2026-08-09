"""표본·검정력 계기판 — "지금 표본으로 무엇을 확정할 수 있나"에 답한다.

## 왜 필요한가

원장(페이지 30)은 "이 후보가 챔피언보다 나은가"를 보여준다. 그런데 판정이
`PROMISING`/`MIXED` 로 나오면 다음 질문은 항상 같다: **"그래서 얼마나 더 재야
하나?"** 지금까지 그 답은 매번 손으로 계산했고, 그래서 "표본이 부족하다"는 말이
막연한 변명처럼 들렸다.

이 모듈은 그 막연함을 숫자로 바꾼다.

| 묻는 것 | 답하는 값 |
|---|---|
| 지금 표본으로 잡을 수 있는 **가장 작은 차이**는? | `mde_pct` |
| 지금 관측된 차이에 대한 **검정력**은? | `achieved_power` |
| 확정하려면 짝이 **몇 개** 더 필요한가? | `extra_pairs_needed` |
| 그건 거래일로 **며칠**인가? | `extra_days_needed` |

## 비유

체중계 눈금이 1kg 단위면 500g 감량은 "잰 게 아니라 안 보이는 것"이다.
`mde_pct` 가 그 눈금 폭이다. 관측된 차이가 눈금보다 작으면, 결과가 0이 아니어도
**아직 잰 게 아니다**.

## 규율

1. **표준편차를 지어내지 않는다.** 원장에 sd 열이 없으므로 신뢰구간에서 역산한다
   (`ci_high - ci_low = 2·Z_ALPHA·se`). 역산이 불가능하면 `available=False`.
2. **부호를 존중한다.** 관측 차이가 음수면 "표본을 늘리면 이긴다"고 하지 않는다.
3. **무한대를 화면에 내보내지 않는다.** 차이가 0이면 필요 표본은 정의되지 않는다
   — `None` 으로 두고 그렇게 말한다.
"""

from __future__ import annotations

import math
from typing import Any, Final, Sequence

#: engine_ladder 와 같은 값을 쓴다 — 두 곳이 어긋나면 판정과 계기판이 다른 말을 한다.
from ai_strategy_loop.labeling.engine_ladder import Z_ALPHA, Z_POWER

#: 검정력 목표. 관례값이며 라운드 중에 바꾸지 않는다.
TARGET_POWER: Final = 0.80

#: 이 배수 이상 모자라면 "이번 라운드로는 못 끝낸다"고 표시한다.
HOPELESS_SHORTFALL: Final = 10.0


def normal_cdf(z: float) -> float:
    """표준정규 누적분포. scipy 없이 — 의존성 하나를 위해 무겁게 가지 않는다."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def sd_from_ci(pairs: int, ci_low: float, ci_high: float) -> float | None:
    """신뢰구간에서 표준편차를 역산한다.

    `ci = mean ± Z_ALPHA·sd/√n` 이므로 `sd = (hi−lo)·√n / (2·Z_ALPHA)`.
    원장에 sd 열을 새로 파지 않고도 정확히 복원된다(반올림 오차만 남는다).
    """
    if pairs is None or pairs < 2 or ci_low is None or ci_high is None:
        return None
    width = float(ci_high) - float(ci_low)
    if width <= 0:
        return None
    return width * math.sqrt(pairs) / (2.0 * Z_ALPHA)


def required_pairs(sd: float, effect: float) -> float | None:
    """이만한 효과를 검정력 80%로 확정하는 데 필요한 짝 수."""
    if not effect or sd is None or sd <= 0:
        return None
    return ((Z_ALPHA + Z_POWER) * sd / abs(effect)) ** 2


def mde(sd: float, pairs: int) -> float | None:
    """최소 검출 가능 효과 — 이보다 작은 차이는 이 표본으로는 안 보인다."""
    if sd is None or sd <= 0 or not pairs or pairs < 2:
        return None
    return (Z_ALPHA + Z_POWER) * sd / math.sqrt(pairs)


def achieved_power(sd: float, pairs: int, effect: float) -> float | None:
    """관측된 효과 크기에 대해 지금 표본이 내는 검정력."""
    if sd is None or sd <= 0 or not pairs or pairs < 2 or effect is None:
        return None
    return normal_cdf(abs(float(effect)) * math.sqrt(pairs) / sd - Z_ALPHA)


def gauge(*, pairs: int | None, mean_diff_pct: float | None,
          ci_low: float | None, ci_high: float | None,
          trades_per_day: float | None = None) -> dict[str, Any]:
    """후보 하나의 계기판.

    `trades_per_day` 를 주면 부족분을 **거래일**로 환산한다 — "몇 건 더"보다
    "며칠 더"가 실제로 계획을 세울 수 있는 단위다.
    """
    sd = sd_from_ci(pairs, ci_low, ci_high) if pairs else None
    if sd is None:
        return {"available": False,
                "reason": "짝지은 신뢰구간이 없어 표준편차를 복원할 수 없다",
                "pairs": pairs}

    effect = float(mean_diff_pct) if mean_diff_pct is not None else 0.0
    need = required_pairs(sd, effect)
    detectable = mde(sd, int(pairs))
    power = achieved_power(sd, int(pairs), effect)
    significant = bool(ci_low is not None and float(ci_low) > 0)

    if significant:
        capability = "확정"
    elif need is None:
        # 차이가 정확히 0 — 필요 표본이 정의되지 않는다. 음수와 섞지 않는다.
        capability = "판정 불가"
    elif effect < 0:
        # 방향이 아래면 표본을 늘려도 이기지 않는다 — 늘리라고 권하지 않는다.
        capability = "역방향"
    elif need / pairs >= HOPELESS_SHORTFALL:
        capability = "표본 절망"
    else:
        capability = "표본 부족"

    # "얼마나 더 재야 하나"는 **더 재서 뒤집힐 수 있을 때만** 답한다.
    #   이미 확정됐거나 방향이 아래면 그 질문 자체가 무의미하다.
    #   (확정이어도 검정력이 80% 미만일 수 있다 — 유의성과 검정력은 다른 질문이다.)
    extra_pairs = None
    extra_days = None
    if capability in ("표본 부족", "표본 절망") and need > pairs:
        extra_pairs = need - float(pairs)
        if trades_per_day and trades_per_day > 0:
            extra_days = extra_pairs / float(trades_per_day)

    return {
        "available": True,
        "pairs": int(pairs),
        "sd": sd,
        "mean_diff_pct": effect,
        "significant": significant,
        # 지금 눈금 폭. 관측 차이가 이보다 작으면 아직 잰 게 아니다.
        "mde_pct": detectable,
        "effect_vs_mde": (abs(effect) / detectable) if detectable else None,
        "achieved_power": power,
        "target_power": TARGET_POWER,
        "required_pairs": need,
        "shortfall_ratio": (need / pairs) if need else None,
        "extra_pairs_needed": extra_pairs,
        "extra_days_needed": extra_days,
        "capability": capability,
        "capability_note": {
            "확정": "신뢰구간 하한이 0을 넘었다 — 통계적으로 확정됐다.",
            "표본 부족": "방향은 맞다. 표본을 늘리면 확정 가능한 범위다.",
            "표본 절망": ("필요 표본이 현재의 10배를 넘는다 — 이 효과 크기는 "
                          "표본을 늘려 확정하는 것이 현실적이지 않다. 효과를 키워야 한다."),
            "역방향": "관측 차이가 0 이하다 — 표본을 늘려도 이기지 않는다.",
            "판정 불가": "관측 차이가 정확히 0이라 필요 표본이 정의되지 않는다.",
        }[capability],
    }


def fleet(rows: Sequence[dict[str, Any]], *,
          trades_per_day: float | None = None) -> dict[str, Any]:
    """원장 전체의 계기판 — 후보별 계기 + 라운드 한 줄 요약."""
    gauges: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("verdict")) == "BASELINE":
            continue                       # 합격선은 자기 자신과 비교하지 않는다
        measured = gauge(
            pairs=row.get("paired_pairs"),
            mean_diff_pct=row.get("paired_mean_diff_pct"),
            ci_low=row.get("paired_ci_low"),
            ci_high=row.get("paired_ci_high"),
            trades_per_day=trades_per_day,
        )
        measured["candidate_id"] = row.get("candidate_id")
        measured["sell_name"] = row.get("sell_name")
        measured["verdict"] = row.get("verdict")
        gauges.append(measured)

    usable = [g for g in gauges if g.get("available")]
    confirmed = [g for g in usable if g["capability"] == "확정"]
    reachable = [g for g in usable if g["capability"] == "표본 부족"]
    # 이번 라운드를 확정으로 끝내려면 가장 많이 필요한 후보를 기준으로 잡는다.
    worst_gap = max((g["extra_days_needed"] for g in reachable
                     if g.get("extra_days_needed") is not None), default=None)

    return {
        "available": bool(usable),
        "candidates": len(gauges),
        "confirmed": len(confirmed),
        "reachable": len(reachable),
        "hopeless": sum(1 for g in usable if g["capability"] == "표본 절망"),
        "wrong_way": sum(1 for g in usable if g["capability"] == "역방향"),
        "days_to_finish_round": worst_gap,
        "trades_per_day": trades_per_day,
        "gauges": sorted(gauges, key=lambda g: (
            {"확정": 0, "표본 부족": 1, "표본 절망": 2, "역방향": 3}.get(
                g.get("capability", ""), 9),
            -(g.get("mean_diff_pct") or 0.0))),
        "note": ("MDE(최소 검출 가능 효과)는 지금 표본의 눈금 폭이다. "
                 "관측 차이가 MDE 보다 작으면 결과가 0이 아니어도 아직 잰 게 아니다."),
    }
