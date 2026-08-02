"""Validated FastAPI payloads for QSP7 trade-path research."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class FrozenPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AnalysisRequest(FrozenPayload):
    job_id: ShortText
    forced_liquidation_time: int | None = Field(default=None, ge=0, le=235959)
    decision_horizons: tuple[int, ...] = (30, 60, 90, 120, 180, 300)
    continuation_horizons: tuple[int, ...] = (30, 60, 120, 300, 600)

    @field_validator("decision_horizons", "continuation_horizons", mode="before")
    @classmethod
    def _tuple_horizons(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("decision_horizons", "continuation_horizons")
    @classmethod
    def _bounded_horizons(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        cleaned = tuple(sorted(set(value)))
        if not cleaned or len(cleaned) > 12 or any(item <= 0 or item > 86_400 for item in cleaned):
            raise ValueError("horizons must contain 1..12 positive seconds within one day")
        return cleaned


class ClausePayload(FrozenPayload):
    field: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    operator: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2)]
    value: float


class ExitRulePayload(FrozenPayload):
    rule_id: ShortText
    clauses: tuple[ClausePayload, ...] = Field(min_length=1, max_length=8)
    after_seconds: int = Field(default=0, ge=0, le=86_400)

    @field_validator("clauses", mode="before")
    @classmethod
    def _tuple_clauses(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class ExitPolicyPayload(FrozenPayload):
    name: ShortText
    rules: tuple[ExitRulePayload, ...] = Field(min_length=1, max_length=12)

    @field_validator("rules", mode="before")
    @classmethod
    def _tuple_rules(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class CounterfactualRequest(FrozenPayload):
    analysis_id: ShortText
    policy: ExitPolicyPayload
    trade_keys: tuple[str, ...] = Field(default=(), max_length=20_000)

    @field_validator("trade_keys", mode="before")
    @classmethod
    def _tuple_trade_keys(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


class ProposalRequest(FrozenPayload):
    analysis_id: ShortText


class OfficialPairRequest(FrozenPayload):
    baseline_job_id: ShortText
    candidate_job_id: ShortText


class MatrixCellPayload(FrozenPayload):
    job_id: ShortText
    buy: ShortText
    sell: ShortText


class MatrixRequest(FrozenPayload):
    cells: tuple[MatrixCellPayload, ...] = Field(min_length=1, max_length=36)

    @field_validator("cells", mode="before")
    @classmethod
    def _tuple_cells(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value
