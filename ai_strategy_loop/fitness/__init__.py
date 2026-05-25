"""US-004 Phase 2a — 복합 적합도(composite fitness) + holdout 분할.

이 패키지는 백테스트 결과(엔진이 산출한 metrics dict + per-trade 누적수익 곡선)를
하나의 스칼라 적합도 점수로 환산한다. 엔진은 건드리지 않으며, 엔진이 이미 계산한
CAGR/MDD를 그대로 재사용한다.

  composite = Calmar(CAGR/MDD) x 우상향도(uptrend R²) x gate

- Calmar      : working/validation 윈도우 CAGR ÷ MDD (MDD≈0 안전 처리)
- 우상향도    : 누적수익 곡선(`수익금합계`)을 직선에 회귀한 R² (0..1)
- gate        : 거래수/MDD/총수익 조건을 모두 통과하면 1, 아니면 0 (=거절)

holdout(RV2-4)은 단일 train/holdout 날짜 분할 토글이며 기본 OFF다. 분할 로직과
토글만 여기서 제공하고, 루프 배선(점수 적용)은 US-005에서 한다.
"""

from .holdout import HoldoutSplit, split_window
from .score import (
    FitnessResult,
    GradedResult,
    compute_calmar,
    compute_fitness,
    compute_graded_fitness,
    compute_uptrend_r2,
    load_equity_series_from_csv,
)

__all__ = [
    "FitnessResult",
    "GradedResult",
    "compute_fitness",
    "compute_graded_fitness",
    "compute_calmar",
    "compute_uptrend_r2",
    "load_equity_series_from_csv",
    "HoldoutSplit",
    "split_window",
]
