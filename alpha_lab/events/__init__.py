"""alpha_lab.events — P2 이벤트 스터디: E1~E5 인과 감지·결과 측정·층화·플라시보.

- detectors: 정렬된 (t0, row) 1회 순회 인과 상태기계 detect_events (E1~E5,
  사건족별 독립 refractory 120초/종목).
- outcomes: P1 동일 비용 모형(labels.adverse_fill·net_rate 재사용) 결과 측정,
  시총×시간밴드×등락율 층화, min_n·일 블록 부트스트랩·BH-FDR 셀 통계,
  플라시보 2종(random_time_matched / shift_plus_60) 동일 파이프 비교.
"""
from alpha_lab.events.detectors import (
    EVENT_FAMILIES,
    REFRACTORY_SEC,
    SURGE_K,
    datetime_to_ts,
    detect_events,
    ts_shift,
    ts_to_datetime,
)
from alpha_lab.events.outcomes import (
    DEFAULT_HORIZONS,
    MIN_N,
    PLACEBO_SHIFT_SEC,
    aggregate_cells,
    attach_cells,
    compare_with_placebo,
    measure_event_outcomes,
    random_time_matched,
    shift_plus_60,
    stratify,
)

__all__ = [
    "DEFAULT_HORIZONS",
    "EVENT_FAMILIES",
    "MIN_N",
    "PLACEBO_SHIFT_SEC",
    "REFRACTORY_SEC",
    "SURGE_K",
    "aggregate_cells",
    "attach_cells",
    "compare_with_placebo",
    "datetime_to_ts",
    "detect_events",
    "measure_event_outcomes",
    "random_time_matched",
    "shift_plus_60",
    "stratify",
    "ts_shift",
    "ts_to_datetime",
]
