"""다년 안정성(winner_objective='multiyear') — 결과 CSV 다년 전구간 우상향 항 (② 다년 학습).

§3.20·§3.21 + 사용자 평가기준 정정 근거:
평가 합격선은 "매 연도 흑자/일정 기울기/연도 균등성"이 **아니다**. 사용자가 명시한
기준은 **"등락과 기울기 변동이 있어도, 다년 전구간 누적곡선이 장기적으로 우상향
추세"** 하나뿐이며, 연도별 균등성(per-year evenness)·매년 흑자·일정 기울기 요구는
**명시적으로 거부**됐다.

  stability_term = clamp01( full_period_uptrend_r2 )
  full_period_uptrend_r2 = compute_uptrend_r2( 전구간 거래순서 누적손익 곡선 )

즉 연도별로 쪼개 평균/분산/변동계수를 섞지 않고, **여러 해에 걸친 단일 전체
누적곡선** 하나의 직선회귀 R²만 본다. R²는 직선 적합도라 중간 하락 구간·기울기
변동을 자연히 **허용**하면서(아래로 꺾여도 전체 추세가 우상향이면 R² 높음) "장기
우상향"을 보상한다.

다년 참여 게이트(multi-year participation gate)는 유지한다: 거래수가
multiyear_min_trades_per_year 이상인 연도 수가 multiyear_min_years 미만이면 None을
반환(중립/no-op)한다. 이는 "단일년 행운이 아니라 진짜 여러 해 데이터"임을
**균등성 요구 없이** 보장한다.

REMOVED(사용자 거부 항): positive_frac(매년 흑자), consistency(per-year r² 분산),
profit_even(per-year 수익 변동계수). 이 균등성 항들은 stability_term 산출에서
완전히 제거됐다. per-year 정보 필드(years/positive_year_count/mean_r2/r2_variance/
profit_cv)는 **보고/진단 전용**으로만 채워지며 stability_term에 영향을 주지 않는다.

하드 게이트(compute_fitness)는 건드리지 않는다 — 이 항은 **선택 전용**이며,
winner_objective!='multiyear'이면 평가조차 안 돼 기존 동작이 byte-동일 보존된다.

규칙(중요): per-year 누적손익을 연도마다 0으로 reset해 구한 **per-year MDD는 reset
artifact**라 절대 안정성 항에 섞지 않는다. 전체 윈도우 MDD는 기존 하드 게이트가
책임진다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from ai_strategy_loop.fitness.holdout import _read_holdout_rows
from ai_strategy_loop.fitness.score import _clamp01, compute_uptrend_r2


@dataclass(frozen=True)
class YearMetrics:
    """단일 연도의 거래 집계(거래 순서 보존 cumsum 기준). 보고/진단 전용."""

    year: int
    trade_count: int
    profit: float
    uptrend_r2: float
    win_rate: float


@dataclass(frozen=True)
class MultiYearStability:
    """다년 전구간 우상향 산출 결과 + 구성요소.

    stability_term이 gate-passed graded에 곱해지는 최종 [0,1] 값이며,
    full_period_uptrend_r2 와 동일하다(전구간 단일 누적곡선의 우상향 R²).

    per-year 필드(years/positive_year_count/mean_r2/r2_variance/profit_cv)는
    **보고/진단 전용**으로만 채워지며 stability_term에 영향을 주지 않는다.
    """

    years: Tuple[YearMetrics, ...]   # 연도 오름차순 정렬. 진단 전용.
    positive_year_count: int         # 진단 전용 — term에 영향 없음.
    total_year_count: int
    mean_r2: float                   # 진단 전용 — term에 영향 없음.
    r2_variance: float               # 진단 전용 — term에 영향 없음.
    profit_cv: float                 # 진단 전용 — term에 영향 없음.
    full_period_uptrend_r2: float    # 전구간 단일 누적곡선의 우상향 R²(=stability_term).
    stability_term: float            # fitness에 곱해지는 최종 [0,1] 항(=full_period_uptrend_r2 clamp).


def compute_multiyear_stability(csv_path: str, config) -> Optional["MultiYearStability"]:
    """결과 CSV로 다년 전구간 누적곡선의 우상향 [0,1] 항을 산출한다 (② 다년 학습).

    추가 백테 없이 전체 윈도우 백테 1회 CSV(여러 해 거래 포함)를 쓴다. 거래일
    (YYYYMMDD) 앞 4자리 연도로 그룹핑해 **다년 참여 게이트**만 판정한 뒤,
    stability_term은 **전구간(모든 연도) 거래순서 누적손익 곡선** 하나의 우상향 R²로
    삼는다. 연도별 균등성은 보지 않으므로 중간 하락 연도·기울기 변동을 자연히
    허용한다(사용자 평가기준: 장기 우상향만 요구).

    데이터 부족(CSV 없음/유효연도<min/파싱 오류)이면 None을 반환한다 — 호출부는 이때
    중립(term=1.0, =risk_adjusted)으로 처리하므로 missing이 페널티가 되지 않는다.

    Args:
        csv_path: 백테스트 결과 CSV(거래당 1행, 매도시간/수익금 컬럼 보유).
        config: LoopConfig (multiyear_min_years / multiyear_min_trades_per_year 만 사용 —
            다년 참여 게이트 기준. var_norm/cv_norm은 §3.21 이후 미사용).

    Returns:
        MultiYearStability, 또는 평가 불가 시 None(→ 중립).
    """
    try:
        rows = _read_holdout_rows(csv_path)
    except Exception:  # noqa: BLE001 - CSV 문제(컬럼 없음/파일 없음/파싱)는 None(중립)으로 흡수.
        return None

    if not rows:
        return None

    # 다년 참여 게이트 임계값 — getattr 폴백(구 config/테스트 더블 하위호환).
    min_years = int(getattr(config, "multiyear_min_years", 2))
    min_tpy = int(getattr(config, "multiyear_min_trades_per_year", 20))

    # 연도별 수익 리스트(거래 순서 보존). dict 삽입순=등장순이지만 정렬해 결정성 확보.
    by_year: dict = {}
    for day, profit in rows:
        year = int(day) // 10000
        by_year.setdefault(year, []).append(float(profit))

    # 유효 연도만(거래수 >= min_tpy). 부분연도/희소연도 가드 — 참여 게이트에만 쓴다.
    #   per-year 지표는 보고/진단 전용이며 stability_term에 영향을 주지 않는다.
    year_metrics: List[YearMetrics] = []
    for year in sorted(by_year.keys()):
        profits = by_year[year]
        if len(profits) < min_tpy:
            continue
        # 거래 순서 cumsum → per-year 우상향 r²(진단 전용). per-year MDD는 reset artifact라 안 본다.
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
    # 다년 참여 게이트: 유효 연도(min_tpy 이상) 수가 min_years 미만이면 중립(None).
    #   "단일년 행운이 아니라 진짜 여러 해"를 균등성 요구 없이 보장한다.
    if total < min_years:
        return None

    # --- stability_term: 전구간(모든 연도) 거래순서 누적손익 곡선의 우상향 R² ---
    #   연도별로 쪼개지 않고 CSV 전체 거래순서 cumsum 하나에 직선회귀한다. R²는 직선
    #   적합도라 중간 하락·기울기 변동을 허용하면서 "장기 우상향"을 보상한다.
    full_equity: List[float] = []
    running_all = 0.0
    for _day, profit in rows:
        running_all += float(profit)
        full_equity.append(running_all)
    full_period_uptrend_r2 = float(compute_uptrend_r2(full_equity))
    stability_term = _clamp01(full_period_uptrend_r2)

    # --- per-year 진단 집계 (보고 전용 — stability_term에 영향 없음) ---
    positive_year_count = sum(1 for ym in year_metrics if ym.profit > 0.0)

    r2_list = [ym.uptrend_r2 for ym in year_metrics]
    mean_r2 = sum(r2_list) / total
    r2_variance = sum((r2 - mean_r2) ** 2 for r2 in r2_list) / total  # 모분산(진단).

    profits = [ym.profit for ym in year_metrics]
    mean_p = sum(profits) / total
    if abs(mean_p) < 1e-9:
        profit_cv = 0.0  # 평균손익 ≈ 0(degenerate): 변동계수 정의 불가(진단).
    else:
        std_p = (sum((p - mean_p) ** 2 for p in profits) / total) ** 0.5
        profit_cv = std_p / abs(mean_p)

    return MultiYearStability(
        years=tuple(year_metrics),
        positive_year_count=positive_year_count,
        total_year_count=total,
        mean_r2=float(mean_r2),
        r2_variance=float(r2_variance),
        profit_cv=float(profit_cv),
        full_period_uptrend_r2=float(full_period_uptrend_r2),
        stability_term=float(stability_term),
    )
