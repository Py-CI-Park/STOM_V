"""다년 안정성(winner_objective='multiyear') — 결과 CSV 연도분할 선택 항 (② 다년 학습).

§3.20 근거: 시드 Tick_902는 2023~25 3년 전체 +8,266,552·r²0.90의 **견고한 다년
우상향** 전략이며(2023 +4.73M r²0.95 / 2024 +3.22M r²0.82 / 2025 +0.32M r²0.20),
단일년 비관은 시드 최악의 해(2025)만 본 착시였다. 이 항은 그 "여러 해에 걸쳐
안정적으로 우상향" 형태를 보상해, 생성/refine가 단일년-과적합 조건보다 레짐-강건
조건을 선호하도록 cross-year 안정성을 gate-passed graded에 곱한다.

자기완결 CSV-슬라이스 모듈(holdout.py 스타일 — 엔진 import 없이 CSV + 산술만):
결과 CSV를 연도(YYYYMMDD//10000)별로 쪼개 per-year 우상향(r²)·흑자·수익 균등성의
cross-year 안정성을 [0,1] stability_term으로 만든다.

  stability_term = clamp01( mean(positive_frac, mean_r2, consistency, profit_even) )

하드 게이트(compute_fitness)는 건드리지 않는다 — 이 항은 **선택 전용**이며,
winner_objective!='multiyear'이면 평가조차 안 돼 기존 동작이 byte-동일 보존된다.

규칙(중요): per-year 누적손익을 연도마다 0으로 reset해 구한 **per-year MDD는 reset
artifact**라 절대 안정성 항에 섞지 않는다 — per-year r²/흑자 부호 + (전체 윈도우 MDD는
기존 하드 게이트가 책임)만 본다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ai_strategy_loop.fitness.holdout import _read_holdout_rows
from ai_strategy_loop.fitness.score import _clamp01, compute_uptrend_r2


@dataclass(frozen=True)
class YearMetrics:
    """단일 연도의 거래 집계(거래 순서 보존 cumsum 기준)."""

    year: int
    trade_count: int
    profit: float
    uptrend_r2: float
    win_rate: float


@dataclass(frozen=True)
class MultiYearStability:
    """cross-year 안정성 산출 결과 + 구성요소.

    stability_term이 gate-passed graded에 곱해지는 최종 [0,1] 값이다.
    """

    years: Tuple[YearMetrics, ...]   # 연도 오름차순 정렬.
    positive_year_count: int
    total_year_count: int
    mean_r2: float
    r2_variance: float       # per-year r²의 모분산(population variance).
    profit_cv: float         # per-year 수익의 변동계수(std/abs(mean)).
    stability_term: float    # fitness에 곱해지는 최종 [0,1] 항.


def compute_multiyear_stability(csv_path: str, config) -> Optional["MultiYearStability"]:
    """결과 CSV를 연도별로 쪼개 cross-year 안정성 [0,1] 항을 산출한다 (② 다년 학습).

    추가 백테 없이 전체 윈도우 백테 1회 CSV(여러 해 거래 포함)를 거래일(YYYYMMDD)
    앞 4자리 연도로 그룹핑한다. 각 유효 연도의 per-year 우상향(r²)·흑자·수익 균등성을
    합쳐 stability_term을 만든다.

    데이터 부족(CSV 없음/유효연도<min/파싱 오류)이면 None을 반환한다 — 호출부는 이때
    중립(term=1.0, =risk_adjusted)으로 처리하므로 missing이 페널티가 되지 않는다.

    Args:
        csv_path: 백테스트 결과 CSV(거래당 1행, 매도시간/수익금 컬럼 보유).
        config: LoopConfig (multiyear_min_years / multiyear_min_trades_per_year /
            multiyear_var_norm / multiyear_cv_norm 사용).

    Returns:
        MultiYearStability, 또는 평가 불가 시 None(→ 중립).
    """
    try:
        rows = _read_holdout_rows(csv_path)
    except Exception:  # noqa: BLE001 - CSV 문제(컬럼 없음/파일 없음/파싱)는 None(중립)으로 흡수.
        return None

    if not rows:
        return None

    # 임계값 — getattr 폴백(구 config/테스트 더블 하위호환).
    min_years = int(getattr(config, "multiyear_min_years", 2))
    min_tpy = int(getattr(config, "multiyear_min_trades_per_year", 20))
    var_norm = float(getattr(config, "multiyear_var_norm", 0.2))
    cv_norm = float(getattr(config, "multiyear_cv_norm", 1.0))
    if var_norm <= 0.0:
        var_norm = 0.2
    if cv_norm <= 0.0:
        cv_norm = 1.0

    # 연도별 수익 리스트(거래 순서 보존). dict 삽입순=등장순이지만 정렬해 결정성 확보.
    by_year: dict = {}
    for day, profit in rows:
        year = int(day) // 10000
        by_year.setdefault(year, []).append(float(profit))

    # 유효 연도만(거래수 >= min_tpy). 부분연도/희소연도 가드.
    year_metrics: List[YearMetrics] = []
    for year in sorted(by_year.keys()):
        profits = by_year[year]
        if len(profits) < min_tpy:
            continue
        # 거래 순서 cumsum → per-year 우상향 r². per-year MDD는 reset artifact라 안 본다.
        equity: List[float] = []
        running = 0.0
        for p in profits:
            running += p
            equity.append(running)
        n = len(profits)
        wins = sum(1 for p in profits if p > 0.0)
        year_metrics.append(
            YearMetrics(
                year=year,
                trade_count=n,
                profit=float(running),
                uptrend_r2=float(compute_uptrend_r2(equity)),
                win_rate=(wins / n) if n > 0 else 0.0,
            )
        )

    total = len(year_metrics)
    if total < min_years:
        return None

    # --- 집계 ---
    positive_year_count = sum(1 for ym in year_metrics if ym.profit > 0.0)
    positive_frac = positive_year_count / total

    r2_list = [ym.uptrend_r2 for ym in year_metrics]
    mean_r2 = sum(r2_list) / total
    r2_variance = sum((r2 - mean_r2) ** 2 for r2 in r2_list) / total  # 모분산.
    consistency = _clamp01(1.0 - r2_variance / var_norm)

    profits = [ym.profit for ym in year_metrics]
    mean_p = sum(profits) / total
    if abs(mean_p) < 1e-9:
        # 평균손익 ≈ 0(degenerate): 변동계수 정의 불가 → 균등성 0.
        profit_cv = 0.0
        profit_even = 0.0
    else:
        std_p = (sum((p - mean_p) ** 2 for p in profits) / total) ** 0.5
        profit_cv = std_p / abs(mean_p)
        profit_even = _clamp01(1.0 - profit_cv / cv_norm)

    stability_term = _clamp01(
        (positive_frac + mean_r2 + consistency + profit_even) / 4.0
    )

    return MultiYearStability(
        years=tuple(year_metrics),
        positive_year_count=positive_year_count,
        total_year_count=total,
        mean_r2=float(mean_r2),
        r2_variance=float(r2_variance),
        profit_cv=float(profit_cv),
        stability_term=float(stability_term),
    )
