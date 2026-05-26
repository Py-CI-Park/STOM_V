"""P4 — 메타분석 엔진.

누적된 generations(loop_runs.db, 여러 run)에서 "어떤 변경이 개선을 낳나"를
집계하고, 그 인사이트를 다음 run 생성 프롬프트에 환류한다.

  - analyze.py  : 누적 세대 집계 → MetaInsights (통과 전략 공통 조건 / 개선 유형 /
                  실패 패턴) + 영속(meta_insights.json) 저장/로드.
  - seed.py     : MetaInsights → 생성 프롬프트 주입용 NL 가이드(토글 OFF 기본).
"""

from __future__ import annotations

from .analyze import (
    MetaInsights,
    aggregate_meta_insights,
    load_meta_insights,
    save_meta_insights,
)
from .seed import build_meta_seed_text, to_page_data

__all__ = [
    "MetaInsights",
    "aggregate_meta_insights",
    "load_meta_insights",
    "save_meta_insights",
    "build_meta_seed_text",
    "to_page_data",
]
