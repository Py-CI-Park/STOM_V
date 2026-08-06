"""레인 명세 — tick(초)·min(분) 라벨 공장을 한 코드로 돌리기 위한 매개변수 정본.

tick 상수는 label_spec 이 계속 정본이고, 여기의 TICK 은 그것을 묶은 것이다.
min 레인 수치는 lane_manifest(v2: 평가 20250407~20260227·경계 20251201)와 정합.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from ai_strategy_loop.labeling import label_spec as _tick


#: 배리어 그리드(%) — 라벨 v2. 사전 고정(사후에 "잘 나오는 값"을 고르는 것 자체가 과최적).
BARRIERS_UP: Final = (1.0, 2.0, 3.0, 5.0)
BARRIERS_DOWN: Final = (1.0, 2.0, 3.0)


@dataclass(frozen=True)
class LaneSpec:
    name: str
    time_digits: int              # index 의 시각 자릿수 — tick 14(HHMMSS), min 12(HHMM)
    horizons: tuple[int, ...]     # 시간 단위(초 또는 분) 기준 고정 horizon
    entry_start: int              # HHMMSS(tick) / HHMM(min)
    entry_end: int
    forced_exit: int
    stale_tolerance: int          # 같은 시간 단위
    close_truncated_before: int
    path_window: int
    flow_prefix: str              # "초당" | "분당"
    db_pattern: str               # _database/ 내 일별 파일 프리픽스
    design: tuple[int, int]
    holdout_start: int
    snapshot_columns: tuple[str, ...] = field(default=())
    #: v2 — 봉투 체크포인트(시간 단위). 마지막 값이 배리어 탐색 창이기도 하다.
    checkpoints: tuple[int, ...] = field(default=())

    @property
    def barrier_horizon(self) -> int:
        """배리어 탐색 창 = 마지막 체크포인트. 미도달 표기값으로도 쓴다."""
        return self.checkpoints[-1]

    def unit_of_day(self, clock: int) -> int:
        """HHMMSS→초 / HHMM→분 — 시각 산술 함정 차단."""
        if self.time_digits == 14:
            return _tick.hhmmss_to_sod(clock)
        return (clock // 100) * 60 + (clock % 100)


_TICK_SNAPSHOT = _tick.SNAPSHOT_COLUMNS
_MIN_SNAPSHOT = tuple(
    column.replace("초당", "분당") for column in _TICK_SNAPSHOT
) + ("분봉시가", "분봉고가", "분봉저가")

TICK = LaneSpec(
    name="tick", time_digits=14, horizons=_tick.HORIZONS,
    entry_start=_tick.ENTRY_START, entry_end=_tick.ENTRY_END, forced_exit=_tick.FORCED_EXIT,
    stale_tolerance=_tick.STALE_TOLERANCE_SEC,
    close_truncated_before=_tick.CLOSE_TRUNCATED_BEFORE,
    path_window=_tick.PATH_WINDOW_SEC, flow_prefix="초당",
    db_pattern="stock_tick_", design=(20240304, 20250822), holdout_start=20250825,
    snapshot_columns=_TICK_SNAPSHOT,
    checkpoints=(30, 60, 120, 300, 600),
)

# min 레인 — 전일장. horizon 은 분 단위 {5,10,30,60,close}, 진입은 15:00 까지(청산 여유),
#   전체청산 15:28. 스테일 허용 2분, 경로 라벨 창 60분.
MIN = LaneSpec(
    name="min", time_digits=12, horizons=(5, 10, 30, 60),
    entry_start=900, entry_end=1500, forced_exit=1528,
    stale_tolerance=2, close_truncated_before=1520,
    path_window=60, flow_prefix="분당",
    db_pattern="stock_min_", design=(20250407, 20251128), holdout_start=20251201,
    snapshot_columns=_MIN_SNAPSHOT,
    checkpoints=(5, 10, 30, 60),
)

LANES = {"tick": TICK, "min": MIN}
