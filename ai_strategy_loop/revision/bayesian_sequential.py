"""Offline Beta-Binomial sequential decision receipts.

The ``APPROVE`` decision here is only a posterior-probability contract result.  This
module has no authority to adopt, export, deploy, or promote a strategy.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Final, Iterable


SCHEMA_VERSION: Final = 1
NO_ADOPTION_AUTHORITY: Final = "none_offline_statistical_receipt_only"
_CALCULATION_METHOD: Final = "beta_binomial_regularized_incomplete_beta_v1"
_GENESIS_LOOK_DIGEST: Final = "GENESIS"
_BETACF_MAX_ITER: Final = 400
_BETACF_EPS: Final = 3.0e-14
_FPMIN: Final = 1.0e-300
_QUANTILE_ITERATIONS: Final = 80


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CONTINUE = "CONTINUE"
    MAX_SAMPLE = "MAX_SAMPLE"


APPROVE: Final = Decision.APPROVE
REJECT: Final = Decision.REJECT
CONTINUE: Final = Decision.CONTINUE
MAX_SAMPLE: Final = Decision.MAX_SAMPLE


def _digest(payload: dict[str, object]) -> str:
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _require_finite_float(name: str, value: object) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a finite number")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _require_probability_open(name: str, value: object) -> float:
    number = _require_finite_float(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError(f"{name} must be between 0 and 1, exclusive")
    return number


def _require_probability_closed(name: str, value: object) -> float:
    number = _require_finite_float(name, value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return number


def _require_non_negative_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _require_positive_int(name: str, value: object) -> int:
    number = _require_non_negative_int(name, value)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _clamp_probability(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


@dataclass(frozen=True, slots=True)
class SequentialConfig:
    prior_alpha: float = 1.0
    prior_beta: float = 1.0
    rope_lower: float = 0.5
    approve_prob_threshold: float = 0.95
    reject_prob_threshold: float = 0.95
    max_sample: int = 100
    credible_mass: float = 0.95

    def __post_init__(self) -> None:
        prior_alpha = _require_finite_float("prior_alpha", self.prior_alpha)
        prior_beta = _require_finite_float("prior_beta", self.prior_beta)
        if prior_alpha <= 0.0:
            raise ValueError("prior_alpha must be positive")
        if prior_beta <= 0.0:
            raise ValueError("prior_beta must be positive")
        rope_lower = _require_probability_open("rope_lower", self.rope_lower)
        approve_prob_threshold = _require_probability_open(
            "approve_prob_threshold", self.approve_prob_threshold,
        )
        reject_prob_threshold = _require_probability_open(
            "reject_prob_threshold", self.reject_prob_threshold,
        )
        if approve_prob_threshold + reject_prob_threshold <= 1.0:
            raise ValueError(
                "approve_prob_threshold + reject_prob_threshold must exceed 1.0",
            )
        max_sample = _require_positive_int("max_sample", self.max_sample)
        credible_mass = _require_probability_open("credible_mass", self.credible_mass)
        object.__setattr__(self, "prior_alpha", prior_alpha)
        object.__setattr__(self, "prior_beta", prior_beta)
        object.__setattr__(self, "rope_lower", rope_lower)
        object.__setattr__(self, "approve_prob_threshold", approve_prob_threshold)
        object.__setattr__(self, "reject_prob_threshold", reject_prob_threshold)
        object.__setattr__(self, "max_sample", max_sample)
        object.__setattr__(self, "credible_mass", credible_mass)

    def receipt(self) -> "ConfigReceipt":
        return ConfigReceipt.from_config(self)


@dataclass(frozen=True, slots=True)
class ConfigReceipt:
    schema_version: int
    method: str
    prior_alpha: float
    prior_beta: float
    rope_lower: float
    approve_prob_threshold: float
    reject_prob_threshold: float
    max_sample: int
    credible_mass: float
    quantile_iterations: int
    digest: str = ""

    @classmethod
    def from_config(cls, config: SequentialConfig) -> "ConfigReceipt":
        if not isinstance(config, SequentialConfig):
            raise TypeError("config must be a SequentialConfig")
        return cls(
            schema_version=SCHEMA_VERSION,
            method=_CALCULATION_METHOD,
            prior_alpha=config.prior_alpha,
            prior_beta=config.prior_beta,
            rope_lower=config.rope_lower,
            approve_prob_threshold=config.approve_prob_threshold,
            reject_prob_threshold=config.reject_prob_threshold,
            max_sample=config.max_sample,
            credible_mass=config.credible_mass,
            quantile_iterations=_QUANTILE_ITERATIONS,
        )

    def __post_init__(self) -> None:
        schema_version = _require_positive_int("schema_version", self.schema_version)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        if self.method != _CALCULATION_METHOD:
            raise ValueError(f"method must be {_CALCULATION_METHOD}")
        prior_alpha = _require_finite_float("prior_alpha", self.prior_alpha)
        prior_beta = _require_finite_float("prior_beta", self.prior_beta)
        if prior_alpha <= 0.0:
            raise ValueError("prior_alpha must be positive")
        if prior_beta <= 0.0:
            raise ValueError("prior_beta must be positive")
        approve_prob_threshold = _require_probability_open(
            "approve_prob_threshold",
            self.approve_prob_threshold,
        )
        reject_prob_threshold = _require_probability_open(
            "reject_prob_threshold",
            self.reject_prob_threshold,
        )
        if approve_prob_threshold + reject_prob_threshold <= 1.0:
            raise ValueError(
                "approve_prob_threshold + reject_prob_threshold must exceed 1.0",
            )
        object.__setattr__(self, "prior_alpha", prior_alpha)
        object.__setattr__(self, "prior_beta", prior_beta)
        object.__setattr__(self, "rope_lower", _require_probability_open("rope_lower", self.rope_lower))
        object.__setattr__(
            self,
            "approve_prob_threshold",
            approve_prob_threshold,
        )
        object.__setattr__(
            self,
            "reject_prob_threshold",
            reject_prob_threshold,
        )
        object.__setattr__(self, "max_sample", _require_positive_int("max_sample", self.max_sample))
        object.__setattr__(
            self,
            "credible_mass",
            _require_probability_open("credible_mass", self.credible_mass),
        )
        object.__setattr__(
            self,
            "quantile_iterations",
            _require_positive_int("quantile_iterations", self.quantile_iterations),
        )
        expected = _digest(self._payload())
        if self.digest:
            if self.digest != expected:
                raise ValueError("config receipt digest does not match payload")
        else:
            object.__setattr__(self, "digest", expected)

    def _payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "method": self.method,
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
            "rope_lower": self.rope_lower,
            "approve_prob_threshold": self.approve_prob_threshold,
            "reject_prob_threshold": self.reject_prob_threshold,
            "max_sample": self.max_sample,
            "credible_mass": self.credible_mass,
            "quantile_iterations": self.quantile_iterations,
        }


@dataclass(frozen=True, slots=True)
class SeedReceipt:
    schema_version: int
    purpose: str
    seed: int | None
    digest: str = ""

    @classmethod
    def create(cls, *, purpose: str, seed: int | None) -> "SeedReceipt":
        return cls(schema_version=SCHEMA_VERSION, purpose=purpose, seed=seed)

    def __post_init__(self) -> None:
        schema_version = _require_positive_int("schema_version", self.schema_version)
        if schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        if not isinstance(self.purpose, str) or not self.purpose.strip():
            raise ValueError("purpose must be a non-empty string")
        object.__setattr__(self, "purpose", self.purpose.strip())
        if self.seed is not None:
            seed = _require_non_negative_int("seed", self.seed)
            object.__setattr__(self, "seed", seed)
        expected = _digest(self._payload())
        if self.digest:
            if self.digest != expected:
                raise ValueError("seed receipt digest does not match payload")
        else:
            object.__setattr__(self, "digest", expected)

    def _payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "purpose": self.purpose,
            "seed": self.seed,
        }


NO_RNG_SEED_RECEIPT: Final = SeedReceipt.create(
    purpose="external_observations_no_rng",
    seed=None,
)


@dataclass(frozen=True, slots=True)
class LookReceipt:
    look_index: int
    look_successes: int
    look_failures: int
    cumulative_successes: int
    cumulative_failures: int
    sample_size: int
    decision: Decision
    posterior_mean: float
    credible_interval: tuple[float, float]
    probability_above_rope: float
    probability_below_rope: float
    config_digest: str
    seed_digest: str
    previous_receipt_digest: str
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    can_adopt: bool = False
    receipt_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "look_index", _require_positive_int("look_index", self.look_index))
        look_successes = _require_non_negative_int("look_successes", self.look_successes)
        look_failures = _require_non_negative_int("look_failures", self.look_failures)
        cumulative_successes = _require_non_negative_int(
            "cumulative_successes", self.cumulative_successes,
        )
        cumulative_failures = _require_non_negative_int(
            "cumulative_failures", self.cumulative_failures,
        )
        sample_size = _require_non_negative_int("sample_size", self.sample_size)
        if look_successes + look_failures <= 0:
            raise ValueError("look must contain at least one observation")
        if sample_size != cumulative_successes + cumulative_failures:
            raise ValueError("sample_size must equal cumulative successes plus failures")
        if not isinstance(self.decision, Decision):
            object.__setattr__(self, "decision", Decision(self.decision))
        mean = _require_probability_closed("posterior_mean", self.posterior_mean)
        low, high = _validate_interval(self.credible_interval)
        above = _require_probability_closed("probability_above_rope", self.probability_above_rope)
        below = _require_probability_closed("probability_below_rope", self.probability_below_rope)
        if not self.config_digest:
            raise ValueError("config_digest must be present")
        if not self.seed_digest:
            raise ValueError("seed_digest must be present")
        if not self.previous_receipt_digest:
            raise ValueError("previous_receipt_digest must be present")
        if self.adoption_authority != NO_ADOPTION_AUTHORITY:
            raise ValueError("look receipts cannot carry adoption authority")
        if self.can_adopt:
            raise ValueError("look receipts cannot adopt")
        object.__setattr__(self, "posterior_mean", mean)
        object.__setattr__(self, "credible_interval", (low, high))
        object.__setattr__(self, "probability_above_rope", above)
        object.__setattr__(self, "probability_below_rope", below)
        expected = _digest(self._payload())
        if self.receipt_digest:
            if self.receipt_digest != expected:
                raise ValueError("look receipt digest does not match payload")
        else:
            object.__setattr__(self, "receipt_digest", expected)

    def _payload(self) -> dict[str, object]:
        return {
            "look_index": self.look_index,
            "look_successes": self.look_successes,
            "look_failures": self.look_failures,
            "cumulative_successes": self.cumulative_successes,
            "cumulative_failures": self.cumulative_failures,
            "sample_size": self.sample_size,
            "decision": self.decision.value,
            "posterior_mean": self.posterior_mean,
            "credible_interval": list(self.credible_interval),
            "probability_above_rope": self.probability_above_rope,
            "probability_below_rope": self.probability_below_rope,
            "config_digest": self.config_digest,
            "seed_digest": self.seed_digest,
            "previous_receipt_digest": self.previous_receipt_digest,
            "adoption_authority": self.adoption_authority,
            "can_adopt": self.can_adopt,
        }


@dataclass(frozen=True, slots=True)
class SequentialState:
    config: SequentialConfig
    successes: int = 0
    failures: int = 0
    looks: tuple[LookReceipt, ...] = ()
    seed_receipt: SeedReceipt = NO_RNG_SEED_RECEIPT
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    can_adopt: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.config, SequentialConfig):
            raise TypeError("config must be a SequentialConfig")
        successes = _require_non_negative_int("successes", self.successes)
        failures = _require_non_negative_int("failures", self.failures)
        if successes + failures > self.config.max_sample:
            raise ValueError("sample size cannot exceed config.max_sample")
        try:
            looks = tuple(self.looks)
        except TypeError as exc:
            raise TypeError("looks must contain LookReceipt instances") from exc
        if not all(isinstance(look, LookReceipt) for look in looks):
            raise TypeError("looks must contain LookReceipt instances")
        if not isinstance(self.seed_receipt, SeedReceipt):
            raise TypeError("seed_receipt must be a SeedReceipt")
        if self.adoption_authority != NO_ADOPTION_AUTHORITY:
            raise ValueError("state cannot carry adoption authority")
        if self.can_adopt:
            raise ValueError("state cannot adopt")

        config_digest = self.config.receipt().digest
        previous_digest = _GENESIS_LOOK_DIGEST
        for expected_index, look in enumerate(looks, start=1):
            if look.look_index != expected_index:
                raise ValueError("look indices must be contiguous and append-only")
            if look.config_digest != config_digest:
                raise ValueError("look receipt config digest does not match state config")
            if look.seed_digest != self.seed_receipt.digest:
                raise ValueError("look receipt seed digest does not match state seed")
            if look.previous_receipt_digest != previous_digest:
                raise ValueError("look receipt chain is not append-only")
            previous_digest = look.receipt_digest
        if looks:
            latest = looks[-1]
            if latest.cumulative_successes != successes or latest.cumulative_failures != failures:
                raise ValueError("state counts must match the latest look receipt")
        object.__setattr__(self, "successes", successes)
        object.__setattr__(self, "failures", failures)
        object.__setattr__(self, "looks", looks)

    @property
    def config_receipt(self) -> ConfigReceipt:
        return self.config.receipt()


@dataclass(frozen=True, slots=True)
class _PosteriorStats:
    posterior_alpha: float
    posterior_beta: float
    posterior_mean: float
    credible_interval: tuple[float, float]
    probability_above_rope: float
    probability_below_rope: float
    decision: Decision


@dataclass(frozen=True, slots=True)
class SequentialEvaluation:
    decision: Decision
    successes: int
    failures: int
    sample_size: int
    posterior_alpha: float
    posterior_beta: float
    posterior_mean: float
    credible_interval: tuple[float, float]
    probability_above_rope: float
    probability_below_rope: float
    look_receipt: tuple[LookReceipt, ...]
    config_receipt: ConfigReceipt
    seed_receipt: SeedReceipt
    state: SequentialState
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    can_adopt: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.decision, Decision):
            object.__setattr__(self, "decision", Decision(self.decision))
        if self.adoption_authority != NO_ADOPTION_AUTHORITY:
            raise ValueError("evaluation cannot carry adoption authority")
        if self.can_adopt:
            raise ValueError("evaluation cannot adopt")


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    true_success_rate: float
    simulations: int
    decision_counts: tuple[tuple[str, int], ...]
    false_approval_count: int
    false_approval_rate: float
    mean_sample_size: float
    min_sample_size: int
    max_sample_size: int


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    config_receipt: ConfigReceipt
    seed_receipt: SeedReceipt
    simulations_per_rate: int
    look_size: int
    summaries: tuple[CalibrationSummary, ...]
    total_false_approvals: int
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    can_adopt: bool = False
    note: str = (
        "Fixed-seed calibration is offline simulated error probing only; "
        "it has no production adoption authority."
    )

    def __post_init__(self) -> None:
        if not isinstance(self.config_receipt, ConfigReceipt):
            raise TypeError("config_receipt must be a ConfigReceipt")
        if not isinstance(self.seed_receipt, SeedReceipt):
            raise TypeError("seed_receipt must be a SeedReceipt")
        if self.adoption_authority != NO_ADOPTION_AUTHORITY:
            raise ValueError("calibration cannot carry adoption authority")
        if self.can_adopt:
            raise ValueError("calibration cannot adopt")


def _validate_interval(value: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise TypeError("credible_interval must be a two-item tuple")
    low = _require_probability_closed("credible_interval[0]", value[0])
    high = _require_probability_closed("credible_interval[1]", value[1])
    if low > high:
        raise ValueError("credible interval lower bound cannot exceed upper bound")
    return low, high


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for iteration in range(1, _BETACF_MAX_ITER + 1):
        m2 = 2 * iteration
        aa = iteration * (b - iteration) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + iteration) * (qab + iteration) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= _BETACF_EPS:
            return h
    raise ArithmeticError("regularized beta approximation failed to converge")


def _regularized_beta_cdf(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_bt = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    bt = math.exp(log_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return _clamp_probability(bt * _beta_continued_fraction(a, b, x) / a)
    return _clamp_probability(1.0 - bt * _beta_continued_fraction(b, a, 1.0 - x) / b)


def _beta_quantile(probability: float, a: float, b: float) -> float:
    if probability <= 0.0:
        return 0.0
    if probability >= 1.0:
        return 1.0
    low = 0.0
    high = 1.0
    for _ in range(_QUANTILE_ITERATIONS):
        middle = (low + high) / 2.0
        if _regularized_beta_cdf(middle, a, b) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _posterior_stats(config: SequentialConfig, successes: int, failures: int) -> _PosteriorStats:
    posterior_alpha = config.prior_alpha + successes
    posterior_beta = config.prior_beta + failures
    posterior_mean = posterior_alpha / (posterior_alpha + posterior_beta)
    tail = (1.0 - config.credible_mass) / 2.0
    credible_interval = (
        _beta_quantile(tail, posterior_alpha, posterior_beta),
        _beta_quantile(1.0 - tail, posterior_alpha, posterior_beta),
    )
    probability_below_rope = _regularized_beta_cdf(
        config.rope_lower,
        posterior_alpha,
        posterior_beta,
    )
    probability_above_rope = _clamp_probability(1.0 - probability_below_rope)
    probability_below_rope = _clamp_probability(probability_below_rope)
    sample_size = successes + failures
    if probability_above_rope >= config.approve_prob_threshold:
        decision = Decision.APPROVE
    elif probability_below_rope >= config.reject_prob_threshold:
        decision = Decision.REJECT
    elif sample_size >= config.max_sample:
        decision = Decision.MAX_SAMPLE
    else:
        decision = Decision.CONTINUE
    return _PosteriorStats(
        posterior_alpha=posterior_alpha,
        posterior_beta=posterior_beta,
        posterior_mean=posterior_mean,
        credible_interval=credible_interval,
        probability_above_rope=probability_above_rope,
        probability_below_rope=probability_below_rope,
        decision=decision,
    )


def _evaluation_for_state(state: SequentialState) -> SequentialEvaluation:
    stats = _posterior_stats(state.config, state.successes, state.failures)
    return SequentialEvaluation(
        decision=stats.decision,
        successes=state.successes,
        failures=state.failures,
        sample_size=state.successes + state.failures,
        posterior_alpha=stats.posterior_alpha,
        posterior_beta=stats.posterior_beta,
        posterior_mean=stats.posterior_mean,
        credible_interval=stats.credible_interval,
        probability_above_rope=stats.probability_above_rope,
        probability_below_rope=stats.probability_below_rope,
        look_receipt=state.looks,
        config_receipt=state.config.receipt(),
        seed_receipt=state.seed_receipt,
        state=state,
    )


def initial_state(
    config: SequentialConfig,
    *,
    seed_receipt: SeedReceipt = NO_RNG_SEED_RECEIPT,
) -> SequentialState:
    return SequentialState(config=config, seed_receipt=seed_receipt)


def evaluate(
    config: SequentialConfig,
    *,
    successes: int = 0,
    failures: int = 0,
    seed_receipt: SeedReceipt = NO_RNG_SEED_RECEIPT,
) -> SequentialEvaluation:
    state = SequentialState(
        config=config,
        successes=successes,
        failures=failures,
        seed_receipt=seed_receipt,
    )
    return _evaluation_for_state(state)


def evaluate_state(state: SequentialState) -> SequentialEvaluation:
    if not isinstance(state, SequentialState):
        raise TypeError("state must be a SequentialState")
    return _evaluation_for_state(state)


def update(state: SequentialState, *, successes: int, failures: int) -> SequentialEvaluation:
    if not isinstance(state, SequentialState):
        raise TypeError("state must be a SequentialState")
    look_successes = _require_non_negative_int("successes", successes)
    look_failures = _require_non_negative_int("failures", failures)
    if look_successes + look_failures <= 0:
        raise ValueError("update must include at least one observation")
    current = _evaluation_for_state(state)
    if current.decision is not Decision.CONTINUE:
        raise ValueError("cannot append a look after a terminal decision")
    cumulative_successes = state.successes + look_successes
    cumulative_failures = state.failures + look_failures
    if cumulative_successes + cumulative_failures > state.config.max_sample:
        raise ValueError("update would exceed config.max_sample")
    stats = _posterior_stats(state.config, cumulative_successes, cumulative_failures)
    previous_digest = state.looks[-1].receipt_digest if state.looks else _GENESIS_LOOK_DIGEST
    receipt = LookReceipt(
        look_index=len(state.looks) + 1,
        look_successes=look_successes,
        look_failures=look_failures,
        cumulative_successes=cumulative_successes,
        cumulative_failures=cumulative_failures,
        sample_size=cumulative_successes + cumulative_failures,
        decision=stats.decision,
        posterior_mean=stats.posterior_mean,
        credible_interval=stats.credible_interval,
        probability_above_rope=stats.probability_above_rope,
        probability_below_rope=stats.probability_below_rope,
        config_digest=state.config.receipt().digest,
        seed_digest=state.seed_receipt.digest,
        previous_receipt_digest=previous_digest,
    )
    new_state = SequentialState(
        config=state.config,
        successes=cumulative_successes,
        failures=cumulative_failures,
        looks=state.looks + (receipt,),
        seed_receipt=state.seed_receipt,
    )
    return _evaluation_for_state(new_state)


def calibrate_fixed_seed(
    config: SequentialConfig,
    *,
    seed: int,
    true_success_rates: Iterable[float],
    simulations_per_rate: int = 100,
    look_size: int = 1,
) -> CalibrationReport:
    if not isinstance(config, SequentialConfig):
        raise TypeError("config must be a SequentialConfig")
    seed_value = _require_non_negative_int("seed", seed)
    simulations = _require_positive_int("simulations_per_rate", simulations_per_rate)
    batch = _require_positive_int("look_size", look_size)
    if batch > config.max_sample:
        raise ValueError("look_size cannot exceed config.max_sample")
    if isinstance(true_success_rates, (str, bytes)):
        raise TypeError("true_success_rates must be an iterable of probabilities")
    try:
        rates = tuple(
            _require_probability_closed(f"true_success_rates[{index}]", value)
            for index, value in enumerate(true_success_rates)
        )
    except TypeError as exc:
        raise TypeError("true_success_rates must be an iterable of probabilities") from exc
    if not rates:
        raise ValueError("true_success_rates must not be empty")

    rng = random.Random(seed_value)
    seed_receipt = SeedReceipt.create(purpose="fixed_seed_calibration", seed=seed_value)
    summaries: list[CalibrationSummary] = []
    total_false_approvals = 0
    for true_rate in rates:
        counts = {decision: 0 for decision in Decision}
        sample_sizes: list[int] = []
        false_approvals = 0
        for _ in range(simulations):
            state = initial_state(config, seed_receipt=seed_receipt)
            result = _evaluation_for_state(state)
            while result.decision is Decision.CONTINUE:
                remaining = config.max_sample - result.sample_size
                take = min(batch, remaining)
                look_successes = sum(1 for _ in range(take) if rng.random() < true_rate)
                result = update(
                    result.state,
                    successes=look_successes,
                    failures=take - look_successes,
                )
            counts[result.decision] += 1
            sample_sizes.append(result.sample_size)
            if true_rate <= config.rope_lower and result.decision is Decision.APPROVE:
                false_approvals += 1
        total_false_approvals += false_approvals
        summaries.append(
            CalibrationSummary(
                true_success_rate=true_rate,
                simulations=simulations,
                decision_counts=tuple((decision.value, counts[decision]) for decision in Decision),
                false_approval_count=false_approvals,
                false_approval_rate=false_approvals / simulations,
                mean_sample_size=sum(sample_sizes) / len(sample_sizes),
                min_sample_size=min(sample_sizes),
                max_sample_size=max(sample_sizes),
            ),
        )
    return CalibrationReport(
        config_receipt=config.receipt(),
        seed_receipt=seed_receipt,
        simulations_per_rate=simulations,
        look_size=batch,
        summaries=tuple(summaries),
        total_false_approvals=total_false_approvals,
    )


__all__ = [
    "CalibrationReport",
    "CalibrationSummary",
    "APPROVE",
    "CONTINUE",
    "ConfigReceipt",
    "Decision",
    "LookReceipt",
    "MAX_SAMPLE",
    "NO_ADOPTION_AUTHORITY",
    "NO_RNG_SEED_RECEIPT",
    "REJECT",
    "SeedReceipt",
    "SequentialConfig",
    "SequentialEvaluation",
    "SequentialState",
    "calibrate_fixed_seed",
    "evaluate",
    "evaluate_state",
    "initial_state",
    "update",
]
