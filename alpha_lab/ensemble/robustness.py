"""알파 랩 v4.1 시간창 견고성 검정 — walk-forward 슬라이스·서브기간 분할·몬테카를로 calmar.

봉인 근거(v4_1_robustness_preregistration.json, sha256 db829ed9...): sealed_tests
T1_diversification_mdd / T2_riskadj_median / T3_montecarlo_oos / T4_oos_subperiod의
정의를 그대로 구현한다. 임계값(>=3/4 창, >=0.60 확률 등)과 T1·T2·T3·T4의 **최종 결합**
(robust_verdict_rule)은 이 모듈이 아니라 호출측(계산 스크립트)이 sealed_tests 문자열을
그대로 적용해 판정한다 — 이 모듈은 판정에 필요한 창별/반기별 raw 지표(1/N vs 단일
RiskMetrics)와 부트스트랩 확률만 순수 계산하고, T1/T2 "그 창 하나의 pass 여부"만
공용 함수로 노출한다(평균 vs 중앙값 혼동 같은 실수를 막기 위해 사전등록 문구 그대로
단위 테스트로 봉인).

재사용(재구현 금지): alpha_lab.ensemble.portfolio.{risk_adjusted_metrics, static_equal,
align_monthly_series} — MDD/calmar 관례와 1/N 앙상블 계산은 그 모듈이 유일 원본이다.
이 모듈은 그 위에 **창 슬라이스 / walk-forward 반복 / 서브기간 분할 / 몬테카를로
재표집**만 새로 정의한다(신규 지표 도입 아님).

설계 원칙:
  - 순수 함수만 — 엔진 호출·파일 I/O 없음(결정론, 오프라인 요구사항).
  - monte_carlo_calmar만 난수를 쓰며 seed는 필수 키워드(재현성 규율,
    stats_common.day_block_bootstrap과 동일 계약 — 같은 seed면 bit-동일 출력).
  - '블록'은 이 파이프라인의 최소 관측 단위인 월(月)이다: 매 반복 동일한 재표집
    월 인덱스를 전 챔피언에 동시 적용해 그 달의 챔피언간 동시움직임(co-movement)을
    보존한다 — stats_common.day_block_bootstrap이 일(day) 단위로 (mask, y) 쌍을
    함께 재표집하는 것과 동일한 설계 원리를 월 단위 패널에 적용한 것뿐, 새 부트스트랩
    알고리즘이 아니다.
  - monte_carlo_calmar는 1/N calmar와 단일 calmar 중앙값을 **매 반복 재표집 데이터로부터
    둘 다 다시 계산**한다(고정된 원본 중앙값과 비교하는 것보다 보수적 — 양쪽 다
    표집오차를 반영).
"""

from __future__ import annotations

from statistics import mean, median
from typing import Dict, List, Sequence, Tuple

import numpy as np

from alpha_lab.ensemble.portfolio import (
    RiskMetrics,
    align_monthly_series,
    risk_adjusted_metrics,
    static_equal,
)

__all__ = [
    "slice_window",
    "window_report",
    "walk_forward",
    "subperiod_split",
    "t1_diversification_pass",
    "t2_riskadj_pass",
    "monte_carlo_calmar",
]

# [(ym, pnl), ...] 하나의 챔피언 월별 시퀀스(원본, 미정렬 가능).
_MonthlyPairs = Sequence[Tuple[str, float]]
# [(label, [(ym,pnl),...]), ...] 여러 챔피언(원본, portfolio.align_monthly_series 입력과 동일 계약).
_ChampionsRaw = Sequence[Tuple[str, _MonthlyPairs]]
# [(label, [pnl,...]), ...] 정렬 완료(월 라벨 제거, 값만) — portfolio.align_monthly_series 출력.
_AlignedSeries = Sequence[Tuple[str, Sequence[float]]]


def slice_window(
    champions: _ChampionsRaw, start_ym: str, end_ym: str
) -> List[Tuple[str, List[Tuple[str, float]]]]:
    """챔피언별 (ym, pnl) 목록 → [start_ym, end_ym] 포함구간만 남긴 동일 구조.

    월 라벨(YYYYMM) 문자열 비교로 포함 여부를 판정한다 — 같은 6자리 형식이면
    사전(lexicographic) 비교가 곧 시간순 비교와 같다(v4_characterization.json의
    "2022..2024"와 v4_oos_verdict.json의 "2025..2026"을 이어붙여도 안전). 원본이
    이미 시간순이라는 전제(정렬은 하지 않음 — 필터만).
    """
    out: List[Tuple[str, List[Tuple[str, float]]]] = []
    for label, months in champions:
        sliced = [(ym, float(v)) for ym, v in months if start_ym <= ym <= end_ym]
        out.append((label, sliced))
    return out


def window_report(aligned: _AlignedSeries) -> Dict[str, object]:
    """정렬된 (label, seq) 목록 → {"n_months", "oneN": RiskMetrics, "singles": {label: RiskMetrics}}.

    1/N 앙상블(static_equal)과 각 단일 챔피언의 위험조정지표(risk_adjusted_metrics)를
    모두 계산한다 — portfolio.py 재사용, 재구현 아님. 길이 불일치·빈 입력은
    static_equal/risk_adjusted_metrics의 기존 검증에 위임(ValueError 그대로 전파).
    """
    aligned = list(aligned)
    blend = static_equal(aligned)
    singles = {label: risk_adjusted_metrics(seq) for label, seq in aligned}
    return {
        "n_months": len(blend),
        "oneN": risk_adjusted_metrics(blend),
        "singles": singles,
    }


def walk_forward(
    champions: _ChampionsRaw, windows: Sequence[Tuple[str, str, str]]
) -> Dict[str, Dict[str, object]]:
    """windows=[(win_name, start_ym, end_ym), ...] → {win_name: window_report(...), ...}.

    각 창을 slice_window로 잘라 align_monthly_series로 정렬 검증한 뒤 window_report를
    적용한다 — 한 창 안에서 챔피언별 개월수가 달라지면(그 구간에 일부만 데이터 존재)
    align_monthly_series의 ValueError가 그대로 전파된다(무음 오정렬 방지).
    """
    result: Dict[str, Dict[str, object]] = {}
    for win_name, start_ym, end_ym in windows:
        sliced = slice_window(champions, start_ym, end_ym)
        _, aligned = align_monthly_series(sliced)
        result[win_name] = window_report(aligned)
    return result


def subperiod_split(
    champions: _ChampionsRaw, split_at: int
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """정렬된 월별 시퀀스를 앞 split_at개월 / 나머지로 나눠 두 window_report를 돌려준다.

    split_at: 전반부 개월 수(예: OOS 14개월 중 7 → 전7/후7, T4_oos_subperiod). 0 <
    split_at < 전체개월수여야 한다(양쪽 다 최소 1개월 필요) — 아니면 ValueError.
    시간순은 원본 월 라벨 오름차순 전제(align_monthly_series가 순서 그대로 정렬,
    재정렬하지 않음).
    """
    _, aligned = align_monthly_series(champions)
    n = len(aligned[0][1])
    if not (0 < split_at < n):
        raise ValueError(f"split_at은 0과 {n} 사이여야 합니다(양쪽 절반 모두 비어있지 않게): {split_at}")
    first = [(label, list(seq[:split_at])) for label, seq in aligned]
    second = [(label, list(seq[split_at:])) for label, seq in aligned]
    return window_report(first), window_report(second)


def t1_diversification_pass(report: Dict[str, object]) -> bool:
    """T1_diversification_mdd: 그 창에서 1/N MDD < 단일챔피언 MDD **평균**.

    엄격부등호 — 완전 동일 챔피언처럼 다각화 이득이 전혀 없으면(1/N==단일) FAIL이 맞다.
    """
    singles: Dict[str, RiskMetrics] = report["singles"]  # type: ignore[assignment]
    oneN: RiskMetrics = report["oneN"]  # type: ignore[assignment]
    mean_single_mdd = mean(m.mdd for m in singles.values())
    return oneN.mdd < mean_single_mdd


def t2_riskadj_pass(report: Dict[str, object]) -> bool:
    """T2_riskadj_median: 그 창에서 1/N calmar > 단일챔피언 calmar **중앙값**.

    엄격부등호 — T1과 마찬가지로 완전 동률은 FAIL(다각화 이득 없음).
    """
    singles: Dict[str, RiskMetrics] = report["singles"]  # type: ignore[assignment]
    oneN: RiskMetrics = report["oneN"]  # type: ignore[assignment]
    median_single_calmar = median(m.calmar for m in singles.values())
    return oneN.calmar > median_single_calmar


def _calmar_indicator(matrix: np.ndarray, cols: np.ndarray) -> float:
    """(n_champions, n_months) 패널에서 cols(재표집 월 인덱스, 반복 허용)로 뽑은
    부분패널의 1/N calmar가 단일 calmar 중앙값보다 큰지(1.0/0.0)를 계산한다.

    같은 cols를 전 챔피언 행에 동시 적용해 그 달의 챔피언간 동시움직임을 보존한다
    (전 챔피언이 같은 재표집 달을 공유 — 독립적으로 각자 재표집하지 않음).
    """
    resampled = matrix[:, cols]  # (n_champions, len(cols))
    blend = resampled.mean(axis=0).tolist()
    blend_calmar = risk_adjusted_metrics(blend).calmar
    single_calmars = [risk_adjusted_metrics(resampled[i].tolist()).calmar for i in range(resampled.shape[0])]
    return 1.0 if blend_calmar > median(single_calmars) else 0.0


def monte_carlo_calmar(oos_monthly: _ChampionsRaw, *, n: int = 10000, seed: int) -> Dict[str, object]:
    """T3_montecarlo_oos: 월 단위 블록 복원 재표집(N=n) → P(1/N calmar > 단일 calmar 중앙값).

    n_months개월을 통째로 n_months개월 복원추출하되, 같은 재표집 월 인덱스를 전
    챔피언에 동시 적용한다(그 달의 챔피언간 동시움직임 보존 — stats_common.
    day_block_bootstrap이 일 단위로 (mask,y) 쌍을 함께 재표집하는 것과 동일 설계
    원리). 매 반복 1/N calmar와 단일 calmar 중앙값을 **그 반복의 재표집 데이터로
    부터 둘 다 다시 계산**해 비교한다(고정된 원본 중앙값과 비교하는 것보다 보수적).

    seed는 필수 키워드(재현성 규율, day_block_bootstrap과 동일 계약) — 같은 seed면
    bit-동일 결과.

    Returns:
        {
          "point": 원본(무재표집) 데이터에서의 판정(1.0/0.0) — 감사용,
          "prob": n회 재표집 중 판정이 참인 비율 (T3_prob),
          "n": 재표집 횟수, "n_months": 원본 개월수, "labels": 챔피언 라벨 순서,
        }
    """
    _, aligned = align_monthly_series(oos_monthly)
    labels = [label for label, _ in aligned]
    matrix = np.array([seq for _, seq in aligned], dtype=np.float64)  # (n_champions, n_months)
    n_months = matrix.shape[1]
    if n_months < 1:
        raise ValueError("월별 시퀀스가 비어 있습니다 — 최소 1개월 필요")

    point = _calmar_indicator(matrix, np.arange(n_months))

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_months, size=(n, n_months))
    hits = sum(_calmar_indicator(matrix, idx[b]) for b in range(n))
    prob = hits / n

    return {
        "point": point,
        "prob": float(prob),
        "n": n,
        "n_months": n_months,
        "labels": labels,
    }
