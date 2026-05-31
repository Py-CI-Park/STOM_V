"""US-006 Phase 3 — 부검 분석기 (working-window 거래 통계 → 다음세대 프롬프트 피드백).

직전 세대의 백테스트 결과 CSV에서 **진입 시점(B_*)** 조건이 수익 거래와 손실
거래를 얼마나 갈랐는지(표준화 평균차, Cohen's-d 류)를 계산하고, 그 결과를
다음 세대 프롬프트에 주입할 한국어 자연어 가이드로 변환한다.

구성:
  - analyze   : analyze_trades(csv_path) -> AutopsyResult (거래 통계 + 변별 변수).
  - summarize : summarize(result, config) -> str (다음 세대용 NL 피드백).

부검은 반드시 working/train 거래에서만 돈다(holdout 금지, RV2-4/A5).
analyze_trades(is_holdout=True)는 ValueError를 던진다.
"""

from __future__ import annotations

from .analyze import (
    AutopsyResult,
    Discriminator,
    ExitAutopsyResult,
    SellRuleStat,
    analyze_exits,
    analyze_trades,
)
from .segment import (
    MultiYearSegmentResult,
    SegmentAutopsyResult,
    SegmentStat,
    StableCell,
    ThresholdStat,
    YearSegments,
    analyze_segments,
    analyze_segments_by_year,
    multiyear_to_page_data,
    to_page_data,
)
from .summarize import (
    backtest_error_feedback,
    backtest_error_history_line,
    cap_feedback,
    classify_backtest_error,
    gate_failure_directive,
    summarize,
    summarize_exits,
    summarize_segments,
)

__all__ = [
    "AutopsyResult",
    "Discriminator",
    "ExitAutopsyResult",
    "SellRuleStat",
    "analyze_trades",
    "analyze_exits",
    "summarize",
    "summarize_exits",
    "gate_failure_directive",
    "classify_backtest_error",
    "backtest_error_feedback",
    "backtest_error_history_line",
    # 세그먼트 강화 부검 (P1).
    "SegmentAutopsyResult",
    "SegmentStat",
    "ThresholdStat",
    "analyze_segments",
    "to_page_data",
    "summarize_segments",
    "cap_feedback",
    # 연도-분할 cross-tab + cross-year 안정성 (Phase C-1).
    "MultiYearSegmentResult",
    "YearSegments",
    "StableCell",
    "analyze_segments_by_year",
    "multiyear_to_page_data",
]
