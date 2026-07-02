"""포트폴리오 조립 연구 패키지 (T5.2) — 연구 레인 전용 advisory 도구.

이 패키지는 니치 후보들의 일별 손익 시계열을 결합해 포트폴리오 관점 지표
(상관행렬, 상관 캡 제외, 시간밴드 상보성, 결합 profit/MDD)와 명예의 전당
벤치마크 상대 지표를 계산하는 **분석/판정 함수 모음**이다.

경계 (위반 금지):
  - 승격/export 를 실행하지 않는다. 게이트/엔진/런타임 배선 없음.
  - fitness / autopsy 모듈은 읽기 전용 import 만 한다.
  - backtest/graph/ 불가침 — 이 패키지는 결과 데이터를 쓰지 않는다.
  - 모든 산출물은 advisory 전용이며 measurement_frame 라벨을 필수로 단다.
"""
from __future__ import annotations

from ai_strategy_loop.portfolio.assembler import (
    PORTFOLIO_ASSEMBLER_SCHEMA_VERSION,
    combine_candidates,
    compare_to_benchmark,
    daily_pnl_from_trades,
    load_reference_strategies,
)
from ai_strategy_loop.portfolio.promotion_preconditions import (
    PROMOTION_PRECONDITIONS_SCHEMA_VERSION,
    evaluate_promotion_preconditions,
)

__all__ = [
    "PORTFOLIO_ASSEMBLER_SCHEMA_VERSION",
    "PROMOTION_PRECONDITIONS_SCHEMA_VERSION",
    "combine_candidates",
    "compare_to_benchmark",
    "daily_pnl_from_trades",
    "evaluate_promotion_preconditions",
    "load_reference_strategies",
]
