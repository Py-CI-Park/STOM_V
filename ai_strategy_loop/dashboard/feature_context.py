"""Diagnostic feature envelopes keep source quality separate from calculation state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from pydantic import ConfigDict, JsonValue, RootModel

from ai_strategy_loop.dashboard.generation_json import finite_json

if TYPE_CHECKING:
    from ai_strategy_loop.dashboard.individual_source import AnalysisSource


class FeatureStatus(StrEnum):
    READY = "READY"
    BLOCKED_SOURCE = "BLOCKED_SOURCE"
    INVALID_VARIABLE = "INVALID_VARIABLE"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    NO_STRATEGY = "NO_STRATEGY"


class FeatureResponse(RootModel[dict[str, JsonValue]]):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    def finite(self) -> FeatureResponse:
        return FeatureResponse.model_validate(finite_json(self.root))


@dataclass(frozen=True, slots=True)
class FeatureContext:
    source: AnalysisSource
    job_id: str = ""
    run_id: str = ""
    gen_no: int | None = None

    def envelope(self) -> FeatureResponse:
        source = self.source
        ready = source.analysis_ready and source.checked.snapshot is not None
        return FeatureResponse(
            {
                "job_id": self.job_id,
                "run_id": self.run_id,
                "gen_no": self.gen_no,
                "available": ready,
                "source_available": source.available,
                "analysis_ready": ready,
                "execution_verified": False,
                "execution_status": source.execution_status,
                "execution_basis": source.execution_basis,
                "analysis_authority": source.analysis_authority,
                "analysis_contract": "raw_feature_quality_v1",
                "analysis_scope": "full_source_csv",
                "data_quality": source.checked.quality.model_dump(mode="json"),
                "feature_status": (
                    FeatureStatus.READY if ready else FeatureStatus.BLOCKED_SOURCE
                ).value,
                "reason": ""
                if ready
                else "자료 품질 또는 실행 상태가 분석 준비 조건을 충족하지 않습니다.",
            }
        )


def blocked_feature(
    payload: FeatureResponse, status: FeatureStatus, reason: str
) -> FeatureResponse:
    return FeatureResponse.model_validate(
        {
            **payload.root,
            "available": False,
            "analysis_ready": False,
            "feature_status": status.value,
            "reason": reason,
        }
    ).finite()
