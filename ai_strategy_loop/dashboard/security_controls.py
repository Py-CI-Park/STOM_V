from __future__ import annotations

from typing import Annotated, Final, Literal, assert_never, get_type_hints

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    field_validator,
)
from pydantic_core import PydanticCustomError

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.dashboard.security import Capability


BoundedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
Sha256Text = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
_LOOP_CONFIG_ADAPTERS: Final = {
    name: TypeAdapter(annotation)
    for name, annotation in get_type_hints(LoopConfig).items()
}


class _ControlPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class LoopStartControl(_ControlPayload):
    action: Literal["start"]
    config: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("config")
    @classmethod
    def _validate_config_types(
        cls,
        config: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        for name, value in config.items():
            adapter = _LOOP_CONFIG_ADAPTERS.get(name)
            if adapter is None:
                raise PydanticCustomError(
                    "unknown_loop_config",
                    "unknown loop config field: {field}",
                    {"field": name},
                )
            try:
                adapter.validate_python(value, strict=True)
            except ValidationError as exc:
                raise PydanticCustomError(
                    "invalid_loop_config_type",
                    "invalid strict value for loop config field: {field}",
                    {"field": name},
                ) from exc
        return config


class LoopStopControl(_ControlPayload):
    action: Literal["stop"]


class FinalApprovalControl(_ControlPayload):
    action: Literal["final_approval"]
    run_id: BoundedName
    current_gen: int = Field(ge=0, le=1_000_000)
    winner_gen: int = Field(ge=0, le=1_000_000)
    user_buy: BoundedName
    user_sell: BoundedName
    review_hash: Sha256Text
    evidence_hash: Sha256Text
    buy_code_hash: Sha256Text
    sell_code_hash: Sha256Text


class DecisionRecordPayload(_ControlPayload):
    verdict: Literal["promote", "complement", "hold", "reject"]
    note: Annotated[str, StringConstraints(max_length=500)] = ""


ControlPayload = Annotated[
    LoopStartControl | LoopStopControl | FinalApprovalControl,
    Field(discriminator="action"),
]
CONTROL_PAYLOAD_ADAPTER: Final = TypeAdapter(ControlPayload)


def control_capability(message: ControlPayload) -> Capability:
    match message:
        case LoopStartControl() | LoopStopControl():
            return Capability.LOOP_CONTROL
        case FinalApprovalControl():
            return Capability.FINAL_APPROVAL
        case unreachable:
            assert_never(unreachable)
