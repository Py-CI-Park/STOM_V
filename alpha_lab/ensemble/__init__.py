"""alpha_lab.ensemble — 레짐-적응 챔피언 앙상블 서브패키지 (알파 랩 v4, research-only).

검증된 챔피언(엔진 OOS 실증분) 4~5종을 레짐-적응 앙상블로 조립한다. R0(특성화)가
만든 발견창 월별 P&L을 입력으로 받아, R1(단일 적응형 바닥)·R2(앙상블 조립·파라미터
봉인)가 이 패키지의 순수 함수만으로 오프라인(엔진 0회) 완결된다. 엔진 기동·strategy.db
등록·백테 실행은 이 패키지 밖의 일이다(R0/R3 연구 스크립트가 담당).
"""

from alpha_lab.ensemble.portfolio import (
    RiskMetrics,
    adaptive_sum,
    align_monthly_series,
    regime_rotation,
    risk_adjusted_metrics,
    static_equal,
)

__all__ = [
    "RiskMetrics",
    "risk_adjusted_metrics",
    "align_monthly_series",
    "static_equal",
    "adaptive_sum",
    "regime_rotation",
]
