"""Manual offline research-tool APIs for the V4 dashboard.

These endpoints expose deterministic diagnostic/proposal primitives only.  They do
not read loop state, strategy databases, market data, labels, or export targets;
all adoption/export authority remains outside this router.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Annotated, Any, Final, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from ai_strategy_loop.revision import bayesian_sequential as bayes
from ai_strategy_loop.revision import condition_ast
from ai_strategy_loop.revision import condition_denoising as denoise
from ai_strategy_loop.revision import execution_contract
from ai_strategy_loop.revision import qmc_pareto as qmc

AUTHORITY: Final = "no_adoption"
MAX_SOURCE_CHARS: Final = 20_000
MAX_OBSERVATION_COUNT: Final = 100_000
MAX_BAYESIAN_PRIOR: Final = 1_000_000.0
MAX_ALLOWED_FUNCTIONS: Final = 64
MAX_FUNCTION_NAME_CHARS: Final = 96
MAX_CLAUSES: Final = 256
MAX_LOOKBACK: Final = 1_000_000.0
MAX_UNKNOWN_LINES: Final = 256
MAX_QMC_BUDGET: Final = 256
MAX_QMC_ARCHIVE_BUDGET: Final = 512
MAX_QMC_DIMENSIONS: Final = 8
MAX_QMC_CATEGORIES: Final = 32
MAX_QMC_OBJECTIVES: Final = 8
MAX_QMC_TRIALS: Final = 512
MAX_QMC_SKIP: Final = 100_000
MAX_SEED: Final = (1 << 63) - 1
MAX_NUMERIC_DELTA: Final = 1_000_000.0

SourceText = Annotated[str, StringConstraints(min_length=1, max_length=MAX_SOURCE_CHARS)]
BoundedName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=96)]
FunctionName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_FUNCTION_NAME_CHARS)]
TrialKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


_TOOL_CATALOG: Final = (
    {
        "id": "bayesian",
        "label": "Bayesian sequential boundary",
        "method": "POST",
        "path": "/loop/research-tools/bayesian",
        "scope": "manual_counts_statistical_boundary_only",
    },
    {
        "id": "ast",
        "label": "Condition AST static check",
        "method": "POST",
        "path": "/loop/research-tools/ast",
        "scope": "manual_source_parse_static_limits_only",
    },
    {
        "id": "qmc",
        "label": "QMC candidate proposal and Pareto archive",
        "method": "POST",
        "path": "/loop/research-tools/qmc",
        "scope": "manual_bounded_candidate_proposal_only",
    },
    {
        "id": "denoise",
        "label": "Condition denoising corruption/repair evaluation",
        "method": "POST",
        "path": "/loop/research-tools/denoise",
        "scope": "manual_deterministic_repair_diagnostic_only",
    },
)

_BAYESIAN_DECISION_LABELS: Final = {
    bayes.Decision.APPROVE.value: "statistical_boundary_only_not_strategy_approval",
    bayes.Decision.REJECT.value: "statistical_boundary_only_not_strategy_rejection",
    bayes.Decision.CONTINUE.value: "continue_sampling_boundary_only",
    bayes.Decision.MAX_SAMPLE.value: "max_sample_boundary_only",
}


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        _jsonable(dict(payload)),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _receipt(schema: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = {"schema": schema, **dict(payload)}
    return {**body, "sha256": _sha256(body)}


def _api_receipt() -> dict[str, Any]:
    return _receipt(
        "research_tools_api_receipt_v1",
        {
            "authority": AUTHORITY,
            "tool_ids": [tool["id"] for tool in _TOOL_CATALOG],
            "bounds": {
                "max_source_chars": MAX_SOURCE_CHARS,
                "max_observation_count": MAX_OBSERVATION_COUNT,
                "max_bayesian_sample": MAX_OBSERVATION_COUNT,
                "max_qmc_budget": MAX_QMC_BUDGET,
                "max_qmc_dimensions": MAX_QMC_DIMENSIONS,
            },
            "persistence": "none",
        },
    )


def _base_response(*, receipts: Mapping[str, Any] | None = None, available: bool = True) -> dict[str, Any]:
    return {
        "available": available,
        "authority": AUTHORITY,
        "can_adopt": False,
        "persistence": "none",
        "receipts": _jsonable(receipts or {"api": _api_receipt()}),
    }


def _error_payload(code: str, message: str, *, receipts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        **_base_response(receipts=receipts, available=False),
        "ok": False,
        "code": code,
        "message": message,
    }


def _bad_request(code: str, message: str, *, receipts: Mapping[str, Any] | None = None) -> None:
    raise HTTPException(status_code=400, detail=_error_payload(code, message, receipts=receipts))


def _validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        clean = {key: value for key, value in error.items() if key != "input"}
        if isinstance(clean.get("ctx"), Mapping):
            clean["ctx"] = {str(key): str(value) for key, value in clean["ctx"].items()}
        errors.append(_jsonable(clean))
    return errors


class _ResearchToolsRoute(APIRoute):
    """Keep validation/domain failures inside the no-adoption response envelope."""

    def get_route_handler(self):  # type: ignore[override]
        original = super().get_route_handler()

        async def _handler(request: Request):
            try:
                return await original(request)
            except RequestValidationError as exc:
                return JSONResponse(
                    status_code=422,
                    content={
                        **_error_payload("validation_error", "request payload failed validation"),
                        "detail": _validation_errors(exc),
                    },
                )
            except HTTPException as exc:
                if isinstance(exc.detail, Mapping) and exc.detail.get("authority") == AUTHORITY:
                    return JSONResponse(status_code=exc.status_code, content=_jsonable(dict(exc.detail)))
                raise

        return _handler


research_tools_router = APIRouter(
    prefix="/loop/research-tools",
    tags=["research-tools"],
    route_class=_ResearchToolsRoute,
)


class _Payload(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
    )


class BayesianConfigPayload(_Payload):
    prior_alpha: float = Field(gt=0.0, le=MAX_BAYESIAN_PRIOR)
    prior_beta: float = Field(gt=0.0, le=MAX_BAYESIAN_PRIOR)
    rope_lower: float = Field(gt=0.0, lt=1.0)
    approve_prob_threshold: float = Field(gt=0.0, lt=1.0)
    reject_prob_threshold: float = Field(gt=0.0, lt=1.0)
    max_sample: int = Field(ge=1, le=MAX_OBSERVATION_COUNT)
    credible_mass: float = Field(gt=0.0, lt=1.0)

    @model_validator(mode="after")
    def _thresholds_leave_decision_gap(self) -> "BayesianConfigPayload":
        if self.approve_prob_threshold + self.reject_prob_threshold <= 1.0:
            raise ValueError("approve_prob_threshold + reject_prob_threshold must exceed 1.0")
        return self


class BayesianCountsPayload(_Payload):
    successes: int = Field(ge=0, le=MAX_OBSERVATION_COUNT)
    failures: int = Field(ge=0, le=MAX_OBSERVATION_COUNT)


class BayesianPayload(_Payload):
    config: BayesianConfigPayload
    counts: BayesianCountsPayload

    @model_validator(mode="after")
    def _counts_fit_config_sample(self) -> "BayesianPayload":
        sample_size = self.counts.successes + self.counts.failures
        if sample_size > MAX_OBSERVATION_COUNT:
            raise ValueError(f"successes + failures cannot exceed {MAX_OBSERVATION_COUNT}")
        if sample_size > self.config.max_sample:
            raise ValueError("successes + failures cannot exceed config.max_sample")
        return self


class AstLimitsPayload(_Payload):
    max_clauses: int = Field(ge=0, le=MAX_CLAUSES)
    max_lookback: float = Field(ge=0.0, le=MAX_LOOKBACK)
    max_unknown_lines: int = Field(ge=0, le=MAX_UNKNOWN_LINES)


class AstStaticConfigPayload(_Payload):
    allowed_functions: list[FunctionName] = Field(min_length=0, max_length=MAX_ALLOWED_FUNCTIONS)
    limits: AstLimitsPayload

    @field_validator("allowed_functions")
    @classmethod
    def _allowed_functions_unique(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("allowed_functions must be unique")
        return value


class AstPayload(AstStaticConfigPayload):
    source: SourceText
    runtime_profile: Literal["none", "stock_tick"] = "none"


class QmcDimensionPayload(_Payload):
    name: BoundedName
    kind: Literal["continuous", "integer", "categorical"]
    low: int | float | None = None
    high: int | float | None = None
    categories: list[JsonValue] | None = Field(default=None, min_length=1, max_length=MAX_QMC_CATEGORIES)

    @model_validator(mode="after")
    def _dimension_shape_matches_kind(self) -> "QmcDimensionPayload":
        if self.kind == "categorical":
            if self.low is not None or self.high is not None:
                raise ValueError("categorical dimensions cannot include low/high")
            if not self.categories:
                raise ValueError("categorical dimensions require categories")
            for index, item in enumerate(self.categories):
                if any(item == prior for prior in self.categories[:index]):
                    raise ValueError("categorical categories must be unique")
            return self

        if self.categories is not None:
            raise ValueError("numeric dimensions cannot include categories")
        if self.low is None or self.high is None:
            raise ValueError(f"{self.kind} dimensions require low and high")
        if self.kind == "integer":
            if not isinstance(self.low, int) or isinstance(self.low, bool):
                raise ValueError("integer low must be an integer")
            if not isinstance(self.high, int) or isinstance(self.high, bool):
                raise ValueError("integer high must be an integer")
        if float(self.high) < float(self.low):
            raise ValueError("dimension high must be >= low")
        return self


class QmcObjectivePayload(_Payload):
    name: BoundedName
    direction: Literal["maximize", "minimize"]


class QmcTrialPayload(_Payload):
    key: TrialKey
    scores: dict[str, float] = Field(min_length=1, max_length=MAX_QMC_OBJECTIVES)
    payload: dict[str, JsonValue] = Field(default_factory=dict, max_length=32)

    @field_validator("scores")
    @classmethod
    def _scores_are_finite(cls, value: dict[str, float]) -> dict[str, float]:
        for name, score in value.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("score names must be non-empty strings")
            if isinstance(score, bool) or not math.isfinite(float(score)):
                raise ValueError("scores must be finite numbers")
        return value


class QmcParetoPayload(_Payload):
    budget: int = Field(ge=0, le=MAX_QMC_ARCHIVE_BUDGET)
    objectives: list[QmcObjectivePayload] = Field(min_length=1, max_length=MAX_QMC_OBJECTIVES)
    trials: list[QmcTrialPayload] = Field(default_factory=list, max_length=MAX_QMC_TRIALS)

    @model_validator(mode="after")
    def _archive_is_bounded(self) -> "QmcParetoPayload":
        names = [item.name for item in self.objectives]
        if len(set(names)) != len(names):
            raise ValueError("objective names must be unique")
        if len(self.trials) > self.budget:
            raise ValueError("pareto.trials cannot exceed pareto.budget")
        return self


class QmcPayload(_Payload):
    seed: int = Field(default=0, ge=0, le=MAX_SEED)
    budget: int = Field(ge=1, le=MAX_QMC_BUDGET)
    scramble: bool = True
    skip: int = Field(default=0, ge=0, le=MAX_QMC_SKIP)
    dimensions: list[QmcDimensionPayload] = Field(min_length=1, max_length=MAX_QMC_DIMENSIONS)
    pareto: QmcParetoPayload | None = None

    @field_validator("dimensions")
    @classmethod
    def _dimension_names_unique(cls, value: list[QmcDimensionPayload]) -> list[QmcDimensionPayload]:
        names = [item.name for item in value]
        if len(set(names)) != len(names):
            raise ValueError("dimension names must be unique")
        return value


DenoiseOperator = Literal[
    "mask_one_clause",
    "insert_exact_duplicate",
    "perturb_numeric_threshold",
    "reorder_independent_consecutive_guards",
]


class DenoisePayload(_Payload):
    source: SourceText
    seed: int = Field(default=0, ge=0, le=MAX_SEED)
    operator: DenoiseOperator = "mask_one_clause"
    clause_index: int | None = Field(default=None, ge=0, le=MAX_CLAUSES)
    literal_index: int | None = Field(default=None, ge=0, le=MAX_CLAUSES)
    max_delta: float | None = Field(default=None, gt=0.0, le=MAX_NUMERIC_DELTA)
    static_check: AstStaticConfigPayload | None = None

    @model_validator(mode="after")
    def _operator_arguments_present(self) -> "DenoisePayload":
        if self.operator == "perturb_numeric_threshold" and self.max_delta is None:
            raise ValueError("max_delta is required for perturb_numeric_threshold")
        if self.operator != "perturb_numeric_threshold" and self.literal_index is not None:
            raise ValueError("literal_index is only valid for perturb_numeric_threshold")
        return self


@research_tools_router.get("")
@research_tools_router.get("/status")
def research_tools_status() -> dict[str, Any]:
    tools = [
        {
            **tool,
            "authority": AUTHORITY,
            "can_adopt": False,
            "persistence": "none",
            "manual_only": True,
        }
        for tool in _TOOL_CATALOG
    ]
    return {
        **_base_response(),
        "tool_count": len(tools),
        "tools": tools,
        "bounds": {
            "max_source_chars": MAX_SOURCE_CHARS,
            "max_observation_count": MAX_OBSERVATION_COUNT,
            "max_bayesian_sample": MAX_OBSERVATION_COUNT,
            "max_qmc_budget": MAX_QMC_BUDGET,
            "max_qmc_dimensions": MAX_QMC_DIMENSIONS,
            "max_qmc_archive_budget": MAX_QMC_ARCHIVE_BUDGET,
        },
        "reading_rules": [
            "APPROVE is a statistical boundary label only; authority remains no_adoption.",
            "QMC candidates are proposals only; this API performs no strategy evaluation.",
            "AST and denoising endpoints inspect supplied source only.",
            "No endpoint reads dashboard state, market data, labels, DBs, or export targets.",
        ],
    }


@research_tools_router.post("/bayesian")
def bayesian_boundary(payload: BayesianPayload) -> dict[str, Any]:
    try:
        config = bayes.SequentialConfig(**payload.config.model_dump())
        result = bayes.evaluate(
            config,
            successes=payload.counts.successes,
            failures=payload.counts.failures,
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        _bad_request("invalid_bayesian_input", str(exc))

    receipts = {
        "api": _api_receipt(),
        "config": _jsonable(result.config_receipt),
        "seed": _jsonable(result.seed_receipt),
        "looks": [_jsonable(item) for item in result.look_receipt],
    }
    return {
        **_base_response(receipts=receipts),
        "ok": True,
        "tool": "bayesian",
        "decision": result.decision.value,
        "decision_label": _BAYESIAN_DECISION_LABELS[result.decision.value],
        "decision_authority": "statistical_boundary_only",
        "counts": {
            "successes": result.successes,
            "failures": result.failures,
            "sample_size": result.sample_size,
        },
        "posterior": {
            "alpha": result.posterior_alpha,
            "beta": result.posterior_beta,
            "mean": result.posterior_mean,
            "credible_interval": list(result.credible_interval),
            "probability_above_rope": result.probability_above_rope,
            "probability_below_rope": result.probability_below_rope,
        },
        "module_authority": result.adoption_authority,
        "module_can_adopt": result.can_adopt,
    }


@research_tools_router.post("/ast")
def ast_static_check(payload: AstPayload) -> dict[str, Any]:
    try:
        result = condition_ast.static_check_condition_source(
            payload.source,
            allowed_functions=payload.allowed_functions,
            max_clauses=payload.limits.max_clauses,
            max_lookback=payload.limits.max_lookback,
            max_unknown_lines=payload.limits.max_unknown_lines,
        )
    except (TypeError, ValueError, SyntaxError) as exc:
        _bad_request("invalid_ast_input", str(exc))

    result_payload = result.to_dict(include_original_source=False)
    runtime_result = (
        execution_contract.evaluate_execution_contract(
            payload.source,
            allowed_functions=payload.allowed_functions,
            max_clauses=payload.limits.max_clauses,
            max_lookback=payload.limits.max_lookback,
            max_unknown_lines=payload.limits.max_unknown_lines,
        )
        if payload.runtime_profile == "stock_tick"
        else None
    )
    receipts = {
        "api": _api_receipt(),
        "config": result_payload["config_receipt"],
        "seed": result_payload["seed_receipt"],
    }
    return {
        **_base_response(receipts=receipts),
        "ok": bool(result.ok and (runtime_result is None or runtime_result.ok)),
        "tool": "ast",
        "violations": result_payload["violations"],
        "estimated_work": result_payload["estimated_work"],
        "estimated_work_basis": result_payload["estimated_work_basis"],
        "parsed": result_payload["parsed"],
        "static_check": result_payload,
        "runtime_profile": payload.runtime_profile,
        "execution_contract": _jsonable(runtime_result) if runtime_result is not None else None,
    }


@research_tools_router.post("/qmc")
def qmc_candidates(payload: QmcPayload) -> dict[str, Any]:
    try:
        dimensions = tuple(_dimension_spec(item) for item in payload.dimensions)
        batch = qmc.propose_initial_candidates(
            dimensions,
            payload.budget,
            seed=payload.seed,
            scramble=payload.scramble,
            skip=payload.skip,
        )
        archive_payload = _pareto_archive(payload.pareto, seed=payload.seed) if payload.pareto else None
    except qmc.QmcParetoError as exc:
        _bad_request("invalid_qmc_input", str(exc))

    proposal_receipt = _jsonable(batch.receipt)
    receipts: dict[str, Any] = {
        "api": _api_receipt(),
        "proposal": proposal_receipt,
        "seed": _receipt(
            "qmc_seed_receipt_v1",
            {
                "seed": payload.seed,
                "scramble": payload.scramble,
                "skip": payload.skip,
                "proposal_receipt_schema": proposal_receipt.get("schema"),
            },
        ),
    }
    if archive_payload is not None:
        receipts["pareto"] = archive_payload["receipt"]

    response = {
        **_base_response(receipts=receipts),
        "ok": True,
        "tool": "qmc",
        "candidate_count": len(batch.candidates),
        "candidates": [_candidate_payload(item) for item in batch.candidates],
        "proposal_receipt": proposal_receipt,
        "module_authority": batch.adoption_authority,
        "module_oos_claim": batch.oos_claim,
    }
    if archive_payload is not None:
        response["pareto"] = archive_payload
    return response


@research_tools_router.post("/denoise")
def denoise_evaluation(payload: DenoisePayload) -> dict[str, Any]:
    try:
        clean_ast = condition_ast.parse_condition_source(payload.source)
    except Exception as exc:  # noqa: BLE001 - source diagnostics are surfaced as 400.
        _bad_request("invalid_denoise_source", str(exc))

    corruption = _corrupt(clean_ast, payload)
    if not corruption.ok or corruption.ast is None:
        _bad_request(
            "corruption_failed",
            corruption.reason,
            receipts={"api": _api_receipt(), "corruption": _jsonable(corruption.receipt)},
        )

    repair = denoise.repair_masked_and_duplicate(corruption.ast, clean_ast, seed=payload.seed)
    candidate_ast = repair.ast if repair.ast is not None else corruption.ast
    static_result = _optional_static_check(candidate_ast, payload.static_check)
    static_valid = bool(static_result.ok) if static_result is not None else False
    static_valid_source = "explicit_static_check" if static_result is not None else "not_checked"
    summary = denoise.evaluate_repair(
        clean_ast,
        candidate_ast,
        syntax_valid=True,
        static_valid=static_valid,
        seed=payload.seed,
    )

    receipts = {
        "api": _api_receipt(),
        "corruption": _jsonable(corruption.receipt),
        "repair": _jsonable(repair.receipt),
        "evaluation": _jsonable(summary.receipt),
    }
    if static_result is not None:
        receipts["static_check"] = _jsonable(static_result.config_receipt)

    return {
        **_base_response(receipts=receipts),
        "ok": bool(corruption.ok),
        "tool": "denoise",
        "operator": payload.operator,
        "corruption": _corruption_payload(corruption),
        "repair": _repair_payload(repair),
        "evaluation": _jsonable(summary),
        "static_valid_source": static_valid_source,
        "static_check": (
            static_result.to_dict(include_original_source=False) if static_result is not None else None
        ),
    }


def _dimension_spec(payload: QmcDimensionPayload) -> qmc.DimensionSpec:
    if payload.kind == "continuous":
        return qmc.DimensionSpec.continuous(payload.name, float(payload.low), float(payload.high))
    if payload.kind == "integer":
        return qmc.DimensionSpec.integer(payload.name, int(payload.low), int(payload.high))
    return qmc.DimensionSpec.categorical(payload.name, tuple(payload.categories or ()))


def _pareto_archive(payload: QmcParetoPayload, *, seed: int) -> dict[str, Any]:
    objectives = tuple((item.name, item.direction) for item in payload.objectives)
    archive = qmc.ParetoArchive(objectives, budget=payload.budget, seed=seed)
    add_results = []
    for trial in payload.trials:
        result = archive.add(trial.key, trial.scores, payload=trial.payload)
        add_results.append(_jsonable(result))
    snapshot = archive.snapshot()
    snapshot_payload = _jsonable(snapshot)
    return {
        "trial_count": len(payload.trials),
        "add_results": add_results,
        "snapshot": snapshot_payload,
        "entries": snapshot_payload["entries"],
        "receipt": snapshot_payload["receipt"],
        "adoption_authority": snapshot_payload["adoption_authority"],
        "oos_claim": snapshot_payload["oos_claim"],
    }


def _candidate_payload(candidate: qmc.ProposedCandidate) -> dict[str, Any]:
    return {
        "trial_index": candidate.trial_index,
        "unit_sample": list(candidate.unit_sample),
        "parameters": _jsonable(candidate.parameters),
        "adoption_authority": candidate.adoption_authority,
        "oos_claim": candidate.oos_claim,
    }


def _corrupt(clean_ast: condition_ast.ConditionAst, payload: DenoisePayload) -> denoise.CorruptionResult:
    if payload.operator == "mask_one_clause":
        return denoise.mask_one_clause(clean_ast, seed=payload.seed, clause_index=payload.clause_index)
    if payload.operator == "insert_exact_duplicate":
        return denoise.insert_exact_duplicate(clean_ast, seed=payload.seed, clause_index=payload.clause_index)
    if payload.operator == "perturb_numeric_threshold":
        return denoise.perturb_numeric_threshold(
            clean_ast,
            max_delta=float(payload.max_delta),
            seed=payload.seed,
            clause_index=payload.clause_index,
            literal_index=payload.literal_index,
        )
    return denoise.reorder_independent_consecutive_guards(
        clean_ast,
        seed=payload.seed,
        first_clause_index=payload.clause_index,
    )


def _optional_static_check(
    candidate_ast: condition_ast.ConditionAst,
    payload: AstStaticConfigPayload | None,
) -> condition_ast.StaticCheckResult | None:
    if payload is None:
        return None
    return condition_ast.static_check_condition_source(
        candidate_ast,
        allowed_functions=payload.allowed_functions,
        max_clauses=payload.limits.max_clauses,
        max_lookback=payload.limits.max_lookback,
        max_unknown_lines=payload.limits.max_unknown_lines,
    )


def _corruption_payload(result: denoise.CorruptionResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "operator": result.operator,
        "source": result.source,
        "target": _jsonable(result.target),
        "reason": result.reason,
        "original_literal": result.original_literal,
        "new_literal": result.new_literal,
        "absolute_delta": result.absolute_delta,
        "receipt": _jsonable(result.receipt),
    }


def _repair_payload(result: denoise.RepairResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "source": result.source,
        "actions": [_jsonable(item) for item in result.actions],
        "reason": result.reason,
        "receipt": _jsonable(result.receipt),
    }


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
