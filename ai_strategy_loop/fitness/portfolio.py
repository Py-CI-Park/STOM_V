"""포트폴리오 결합 시뮬레이션 v0 — 분산 효과(결합 MDD 개선) 측정 advisory.

설계 원칙:
  - **분석 전용** — 판정/게이트/생성 경로 일절 수정 없음. advisory 전용.
  - **균등 가중 고정** — v0는 가중 최적화 없음(새 과적합 문 개방 방지).
    가중 최적화는 의도적으로 제외했음을 사전선언한다.
  - 순수 함수만. 입력: {이름: {YYYYMMDD: 일손익(float)}}.
  - 상관 계산은 overfit_stats.daily_correlation_matrix 재사용(중복 구현 금지).

용어:
  MDD  = Maximum DrawDown (금액 기준 peak-to-trough 최대 낙폭).
  분산 이득 (diversification_gain) = 1 - combined_mdd / mean_individual_mdd.
         분모는 개별 MDD의 **가중평균**(균등 가중 시 산술평균) — 합으로 나누면
         동일 전략 N개 결합도 1-1/N의 가짜 이득이 생긴다(2026-06-12 교정).
         동일 전략 결합 = 0, 완전 상쇄 = 1, 음수 = 결합이 오히려 불리.
  한계 MDD (marginal_mdd) = 특정 전략 제외 시 결합 MDD — '이 전략이 풀에
         기여하는 리스크 제거 효과'를 보기 위한 지표.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .overfit_stats import align_daily_matrix, daily_correlation_matrix


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _cumulative(daily_values: List[float]) -> List[float]:
    """일별 손익 리스트를 누적 합 리스트로 변환한다."""
    cum: List[float] = []
    total = 0.0
    for v in daily_values:
        total += v
        cum.append(total)
    return cum


# ---------------------------------------------------------------------------
# 공개 함수
# ---------------------------------------------------------------------------

def mdd_money(curve: List[float]) -> float:
    """누적 금액 곡선의 peak-to-trough 최대 낙폭(금액)을 반환한다.

    Args:
        curve: 누적 손익 리스트(시간순).

    Returns:
        최대 낙폭 금액(양수). 빈 리스트 또는 단일 원소면 0.0.
    """
    if len(curve) < 2:
        return 0.0
    peak = curve[0]
    max_dd = 0.0
    for v in curve:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
    return max_dd


def combined_curve(
    series: Dict[str, Dict[str, float]],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, object]:
    """전략 일별 손익 합산 결합 곡선을 만든다.

    weights=None(기본값)이면 균등 가중(1/N)을 적용한다.
    v0 설계 원칙: 가중 최적화 없음 — weights 인자는 미래 확장용 인터페이스이나,
    균등 외 값을 넘겨도 동작한다. 단, v0 사용처에서는 None만 전달한다.

    날짜는 전략 합집합을 사용하고, 특정 전략에 없는 날은 0.0으로 채운다.

    Args:
        series: {전략명: {YYYYMMDD: 일손익}} 형식.
        weights: {전략명: 가중치}. None이면 1/N 균등 가중.

    Returns:
        {"days": [날짜문자열, ...], "curve": [누적합, ...], "total": 최종합}
    """
    if not series:
        return {"days": [], "curve": [], "total": 0.0}

    names = list(series.keys())
    n = len(names)

    if weights is None:
        w = {name: 1.0 / n for name in names}
    else:
        w = dict(weights)

    all_days = sorted({d for s in series.values() for d in s})

    daily_combined: List[float] = []
    for day in all_days:
        value = sum(w.get(name, 0.0) * series[name].get(day, 0.0) for name in names)
        daily_combined.append(value)

    curve = _cumulative(daily_combined)
    total = curve[-1] if curve else 0.0

    return {
        "days": list(all_days),
        "curve": curve,
        "total": total,
    }


def portfolio_report(series: Dict[str, Dict[str, float]]) -> Dict[str, object]:
    """포트폴리오 분산 효과 전체 리포트를 반환한다.

    시리즈 2개 미만이면 분석 불가 — {"error": ...} 반환(예외 없음).

    Args:
        series: {전략명: {YYYYMMDD: 일손익}} 형식. 2개 이상 필요.

    Returns:
        {
          "names": [전략명, ...],
          "per_total": {전략명: 단독 총손익},
          "per_mdd": {전략명: 단독 MDD 금액},
          "combined_total": 결합 총손익(균등 가중),
          "combined_mdd": 결합 MDD 금액(균등 가중),
          "mean_individual_mdd": 개별 MDD 가중평균(균등 가중 = 산술평균),
          "diversification_gain": 1 - combined_mdd/mean_individual_mdd
                                  (mean_individual_mdd == 0이면 None),
          "correlation": daily_correlation_matrix 결과(또는 None),
          "marginal_mdd": {전략명: 해당 전략 제외 결합 MDD},
        }
        오류 시: {"error": 사유 문자열}
    """
    if len(series) < 2:
        return {"error": "시리즈가 2개 미만입니다 — 포트폴리오 분석에는 최소 2개 전략이 필요합니다."}

    names = list(series.keys())

    # 전략별 단독 지표
    per_total: Dict[str, float] = {}
    per_mdd: Dict[str, float] = {}
    for name, daily in series.items():
        days_sorted = sorted(daily.keys())
        vals = [daily[d] for d in days_sorted]
        curve = _cumulative(vals)
        per_total[name] = curve[-1] if curve else 0.0
        per_mdd[name] = mdd_money(curve)

    # 결합 곡선(균등 가중)
    combined = combined_curve(series, weights=None)
    combined_total = float(combined["total"])
    combined_mdd = mdd_money(combined["curve"])

    # 분산 이득 — 분모는 가중평균 MDD(균등 가중 = 산술평균). 합으로 나누면
    # 동일 전략 N개 결합도 1-1/N의 가짜 이득이 생긴다(2026-06-12 교정).
    mean_individual_mdd = sum(per_mdd.values()) / len(per_mdd)
    if mean_individual_mdd == 0.0:
        diversification_gain: Optional[float] = None
    else:
        diversification_gain = 1.0 - combined_mdd / mean_individual_mdd

    # 상관 행렬 (overfit_stats 재사용)
    corr = daily_correlation_matrix(series)

    # 한계 MDD: 각 전략 제외 시 나머지 결합 MDD
    marginal_mdd: Dict[str, float] = {}
    for name in names:
        subset = {k: v for k, v in series.items() if k != name}
        sub_combined = combined_curve(subset, weights=None)
        marginal_mdd[name] = mdd_money(sub_combined["curve"])

    return {
        "names": names,
        "per_total": per_total,
        "per_mdd": per_mdd,
        "combined_total": combined_total,
        "combined_mdd": combined_mdd,
        "mean_individual_mdd": mean_individual_mdd,
        "diversification_gain": diversification_gain,
        "correlation": corr,
        "marginal_mdd": marginal_mdd,
    }
