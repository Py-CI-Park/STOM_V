"""Validated FastAPI payloads for QSP7 trade-path research."""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator,
)


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


class CandidateRunRequest(FrozenPayload):
    """후보↔공식 job 귀속(P1-4). candidate_id="baseline" 은 기준선 실행 귀속."""

    candidate_id: ShortText
    lane: Annotated[str, StringConstraints(pattern="^(tick|min)$")]
    role: Annotated[str, StringConstraints(pattern="^(design|oos)$")]
    job_id: ShortText
    sell_name: ShortText
    family: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] = ""
    # R2 — 어느 축을 바꾼 실행인지. buy 축이면 sell_name 은 기준선 매도식이다.
    axis: Annotated[str, StringConstraints(pattern="^(sell|buy)$")] = "sell"
    buy_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=128)] = ""


ResearchAxis = Annotated[str, StringConstraints(pattern="^(sell|buy)$")]


class PeriodPayload(FrozenPayload):
    """평가 프로토콜 v2 — 연속 1회 런 CSV 를 자르는 거래일 구간(양끝 포함)."""

    t_start: int = Field(ge=19000101, le=29991231)
    t_end: int = Field(ge=19000101, le=29991231)

    @model_validator(mode="after")
    def _ordered(self) -> "PeriodPayload":
        if self.t_start > self.t_end:
            raise ValueError("t_start must not exceed t_end")
        return self


class OfficialPairRequest(FrozenPayload):
    baseline_job_id: ShortText
    candidate_job_id: ShortText
    # 한 라운드 한 축(R2-1): 바꾼 축만 달라야 하고 반대 축은 고정이어야 한다.
    axis: ResearchAxis = "sell"
    # v2: 지정하면 그 기간 거래만 비교한다. 미지정이면 런 전체.
    period: PeriodPayload | None = None


class PromotionGateRequest(FrozenPayload):
    """두 모드를 지원한다 — 섞어 보내면 어떤 판정인지 모호하므로 거부한다.

    - `4job_independent` (기존): 설계/OOS 를 **각각 독립 런**으로 돌린 4개 job.
    - `2job_split` (v2): 연속 1회 런 job 한 쌍을 **기간으로 갈라** 판정한다.
      연속 런은 자본이 이어지므로 "OOS" 가 아니라 **홀드아웃**이라 부른다.
    """

    design_baseline_job_id: ShortText | None = None
    design_candidate_job_id: ShortText | None = None
    oos_baseline_job_id: ShortText | None = None
    oos_candidate_job_id: ShortText | None = None
    baseline_job_id: ShortText | None = None
    candidate_job_id: ShortText | None = None
    design_period: PeriodPayload | None = None
    holdout_period: PeriodPayload | None = None
    axis: ResearchAxis = "sell"

    @property
    def mode(self) -> str:
        return "2job_split" if self.baseline_job_id else "4job_independent"

    @model_validator(mode="after")
    def _exactly_one_mode(self) -> "PromotionGateRequest":
        four = (self.design_baseline_job_id, self.design_candidate_job_id,
                self.oos_baseline_job_id, self.oos_candidate_job_id)
        two = (self.baseline_job_id, self.candidate_job_id,
               self.design_period, self.holdout_period)
        if any(four) and any(two):
            raise ValueError("do not mix 4-job and 2-job promotion gate fields")
        if any(two):
            if not all(two):
                raise ValueError(
                    "2-job mode needs baseline_job_id, candidate_job_id, "
                    "design_period and holdout_period"
                )
            return self
        if not all(four):
            raise ValueError("4-job mode needs all four job ids")
        return self


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
