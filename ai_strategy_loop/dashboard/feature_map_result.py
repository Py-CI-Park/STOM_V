"""Checked raw-feature map admission, including the existing B/D axis catalog."""

from __future__ import annotations

from enum import StrEnum
from typing import assert_never

from ai_strategy_loop.autopsy import feature_map as maps
from ai_strategy_loop.dashboard.feature_context import (
    FeatureContext,
    FeatureResponse,
    FeatureStatus,
    blocked_feature,
)
from ai_strategy_loop.dashboard.feature_snapshot import (
    SnapshotFrameError,
    snapshot_dataset,
)


class MapMode(StrEnum):
    GRID = "grid"
    REGIONS = "regions"


def map_result(
    context: FeatureContext, x: str, y: str, bins: int, mode: str, top: int
) -> FeatureResponse:
    payload = FeatureResponse(
        {**context.envelope().root, "variables": None, "grid": None, "regions": None}
    )
    snapshot = context.source.checked.snapshot
    if not context.source.analysis_ready or snapshot is None:
        return payload
    try:
        selected = MapMode(mode)
    except ValueError:
        selected = MapMode.GRID  # Existing unknown-mode behavior falls back to grid.
    try:
        frame = snapshot_dataset(snapshot).df
        variables = maps.available_variables(frame)
        payload = FeatureResponse.model_validate(
            {**payload.root, "variables": variables}
        )
        count = max(2, min(10, bins))
        match selected:
            case MapMode.REGIONS:
                regions = maps.loss_regions(
                    snapshot.path, bins=count, top=max(1, min(50, top)), df=frame
                )
                return FeatureResponse.model_validate(
                    {**payload.root, "variables": variables, "regions": regions}
                ).finite()
            case MapMode.GRID:
                if x and (x not in variables or (y and y not in variables)):
                    return blocked_feature(
                        payload,
                        FeatureStatus.INVALID_VARIABLE,
                        "기존 표본·분산 요건을 충족한 B_/D_ 변수 카탈로그에서 축을 선택하세요. S_/R_/결과 라벨은 사용할 수 없습니다.",
                    )
                grid = (
                    maps.grid(snapshot.path, x, y or None, bins=count, df=frame)
                    if x
                    else None
                )
                return FeatureResponse.model_validate(
                    {
                        **payload.root,
                        "variables": variables,
                        "grid": grid,
                        "regions": [],
                    }
                ).finite()
            case unreachable:
                assert_never(unreachable)
    except SnapshotFrameError as exc:
        return blocked_feature(payload, FeatureStatus.PROCESSING_ERROR, str(exc))
    except (
        ValueError,
        TypeError,
        KeyError,
        ArithmeticError,
    ) as exc:
        return blocked_feature(
            payload,
            FeatureStatus.PROCESSING_ERROR,
            f"피처 맵을 완료하지 못했습니다 ({type(exc).__name__}).",
        )
