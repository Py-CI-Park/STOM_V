"""Offline QMC candidate proposals and Pareto archive primitives.

The functions in this module only propose/archive candidates.  They do not read
runtime state, do not evaluate strategies, and carry no OOS or adoption authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import numbers
from types import MappingProxyType
from typing import Any, Final, Hashable, Mapping, Sequence

NO_ADOPTION_AUTHORITY: Final = "none"
NO_OOS_CLAIM: Final = "none"
DISCOVERY_SCOPE: Final = "offline_candidate_proposal_only"

KIND_CONTINUOUS: Final = "continuous"
KIND_INTEGER: Final = "integer"
KIND_CATEGORICAL: Final = "categorical"
VALID_DIMENSION_KINDS: Final = frozenset({KIND_CONTINUOUS, KIND_INTEGER, KIND_CATEGORICAL})

DIRECTION_MAXIMIZE: Final = "maximize"
DIRECTION_MINIMIZE: Final = "minimize"
VALID_DIRECTIONS: Final = frozenset({DIRECTION_MAXIMIZE, DIRECTION_MINIMIZE})

_DUPLICATE_RULE: Final = "latest_duplicate_key_replaces_prior_record_preserving_first_order"
_TIE_RULE: Final = "equal_objective_vectors_do_not_dominate_front_order_is_first_trial_order"
_QMC_SCHEMA: Final = "qmc_halton_candidate_batch_v1"
_PARETO_SCHEMA: Final = "pareto_archive_v1"
_HASH_PERSON: Final = "ai_strategy_loop.revision.qmc_pareto.v1"
_MAX_SAFE_INTEGER_MAPPING_SPAN: Final = 1 << 53


class QmcParetoError(ValueError):
    """Base error for invalid offline discovery inputs."""


class TrialBudgetExceeded(QmcParetoError):
    """Raised when a Pareto archive receives more trials than its budget."""


@dataclass(frozen=True, slots=True)
class DimensionSpec:
    """One declared search-space dimension.

    ``continuous`` and ``integer`` bounds are inclusive.  ``categorical`` values
    are selected by partitioning the unit interval into equal-width buckets.
    """

    name: str
    kind: str
    low: float | int | None = None
    high: float | int | None = None
    categories: tuple[Any, ...] = ()

    @classmethod
    def continuous(cls, name: str, low: float, high: float) -> "DimensionSpec":
        return cls(name=name, kind=KIND_CONTINUOUS, low=low, high=high)

    @classmethod
    def integer(cls, name: str, low: int, high: int) -> "DimensionSpec":
        return cls(name=name, kind=KIND_INTEGER, low=low, high=high)

    @classmethod
    def categorical(cls, name: str, categories: Sequence[Any]) -> "DimensionSpec":
        return cls(name=name, kind=KIND_CATEGORICAL, categories=tuple(categories))

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise QmcParetoError("dimension name must be a non-empty string")
        if self.kind not in VALID_DIMENSION_KINDS:
            raise QmcParetoError(f"invalid dimension kind: {self.kind!r}")

        if self.kind == KIND_CONTINUOUS:
            low = _finite_float(self.low, "continuous low")
            high = _finite_float(self.high, "continuous high")
            if high < low:
                raise QmcParetoError("continuous high must be >= low")
            _continuous_span(low, high)
            object.__setattr__(self, "low", low)
            object.__setattr__(self, "high", high)
            object.__setattr__(self, "categories", ())
            return

        if self.kind == KIND_INTEGER:
            low = _integral(self.low, "integer low")
            high = _integral(self.high, "integer high")
            if high < low:
                raise QmcParetoError("integer high must be >= low")
            _validate_integer_mapping_range(low, high)
            object.__setattr__(self, "low", low)
            object.__setattr__(self, "high", high)
            object.__setattr__(self, "categories", ())
            return

        categories = tuple(self.categories)
        if not categories:
            raise QmcParetoError("categorical dimension requires at least one category")
        for idx, value in enumerate(categories):
            if any(value == prior for prior in categories[:idx]):
                raise QmcParetoError("categorical categories must be unique")
        object.__setattr__(self, "low", None)
        object.__setattr__(self, "high", None)
        object.__setattr__(self, "categories", categories)

    def map_unit(self, unit_value: float) -> Any:
        """Map one finite unit value into this dimension's declared bounds."""

        u = _unit_float(unit_value, "unit value")
        if self.kind == KIND_CONTINUOUS:
            low = float(self.low)
            high = float(self.high)
            span = _continuous_span(low, high)
            if u == 0.0:
                mapped = low
            elif u == 1.0:
                mapped = high
            else:
                mapped = low + span * u
            return _validate_continuous_mapping_value(mapped, low, high)
        if self.kind == KIND_INTEGER:
            low = int(self.low)
            high = int(self.high)
            span = _integer_span(low, high)
            if u == 1.0:
                mapped = high
            else:
                mapped = low + min(span - 1, int(math.floor(u * span)))
            return _validate_integer_mapping_value(mapped, low, high)
        index = min(len(self.categories) - 1, int(math.floor(u * len(self.categories))))
        return self.categories[index]


@dataclass(frozen=True, slots=True)
class QmcReceipt:
    """Deterministic replay receipt for low-discrepancy candidate proposals."""

    seed: int
    scramble: bool
    scramble_method: str
    bases: tuple[int, ...]
    skip: int
    budget: int
    dimensions: tuple[str, ...]
    schema: str = _QMC_SCHEMA
    scope: str = DISCOVERY_SCOPE
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class UnitSampleBatch:
    samples: tuple[tuple[float, ...], ...]
    receipt: QmcReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class ProposedCandidate:
    trial_index: int
    unit_sample: tuple[float, ...]
    parameters: Mapping[str, Any]
    receipt: QmcReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class CandidateBatch:
    candidates: tuple[ProposedCandidate, ...]
    receipt: QmcReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class ObjectiveSpec:
    name: str
    direction: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise QmcParetoError("objective name must be a non-empty string")
        if self.direction not in VALID_DIRECTIONS:
            raise QmcParetoError(f"invalid objective direction: {self.direction!r}")


@dataclass(frozen=True, slots=True)
class ParetoReceipt:
    budget: int
    objectives: tuple[tuple[str, str], ...]
    trials_used: int
    remaining_budget: int
    seed: int = 0
    schema: str = _PARETO_SCHEMA
    duplicate_rule: str = _DUPLICATE_RULE
    tie_rule: str = _TIE_RULE
    scope: str = DISCOVERY_SCOPE
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class ArchivedTrial:
    key: Hashable
    scores: Mapping[str, float]
    payload: Mapping[str, Any]
    first_trial_index: int
    last_trial_index: int
    receipt: ParetoReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class ArchiveAddResult:
    trial: ArchivedTrial
    front: tuple[ArchivedTrial, ...]
    receipt: ParetoReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


@dataclass(frozen=True, slots=True)
class ParetoArchiveSnapshot:
    entries: tuple[ArchivedTrial, ...]
    trials_used: int
    remaining_budget: int
    receipt: ParetoReceipt
    adoption_authority: str = NO_ADOPTION_AUTHORITY
    oos_claim: str = NO_OOS_CLAIM


def halton_unit_samples(
    dimension_count: int,
    count: int,
    *,
    seed: int = 0,
    scramble: bool = True,
    bases: Sequence[int] | None = None,
    skip: int = 0,
    dimension_names: Sequence[str] | None = None,
) -> UnitSampleBatch:
    """Return deterministic Halton samples in ``[0, 1)`` with replay receipt."""

    dims = _non_negative_int(dimension_count, "dimension_count")
    budget = _non_negative_int(count, "count")
    seed_value = _integral(seed, "seed")
    skip_value = _non_negative_int(skip, "skip")
    names = _dimension_names(dims, dimension_names)
    resolved_bases = _resolve_bases(dims, bases)
    permutations = tuple(_scramble_permutation(base, seed_value, idx, names[idx]) for idx, base in enumerate(resolved_bases))
    shifts = tuple(_scramble_shift(seed_value, idx, base, names[idx]) for idx, base in enumerate(resolved_bases))
    samples: list[tuple[float, ...]] = []
    for offset in range(budget):
        halton_index = skip_value + offset + 1
        values: list[float] = []
        for dim_index, base in enumerate(resolved_bases):
            value = _radical_inverse(halton_index, base, permutations[dim_index] if scramble else None)
            if scramble:
                value = (value + shifts[dim_index]) % 1.0
            values.append(value)
        samples.append(tuple(values))

    receipt = QmcReceipt(
        seed=seed_value,
        scramble=bool(scramble),
        scramble_method="fixed_zero_digit_permutation_plus_cranley_patterson_shift" if scramble else "none",
        bases=resolved_bases,
        skip=skip_value,
        budget=budget,
        dimensions=names,
    )
    return UnitSampleBatch(samples=tuple(samples), receipt=receipt)


def map_unit_sample(dimensions: Sequence[DimensionSpec], unit_sample: Sequence[float]) -> Mapping[str, Any]:
    """Map a unit-vector sample into declared dimension bounds."""

    specs = _dimension_specs(dimensions)
    values = tuple(unit_sample)
    if len(specs) != len(values):
        raise QmcParetoError("unit sample dimension mismatch")
    mapped = {spec.name: spec.map_unit(value) for spec, value in zip(specs, values)}
    return MappingProxyType(mapped)


def propose_initial_candidates(
    dimensions: Sequence[DimensionSpec],
    budget: int,
    *,
    seed: int = 0,
    scramble: bool = True,
    bases: Sequence[int] | None = None,
    skip: int = 0,
) -> CandidateBatch:
    """Propose deterministic offline candidates from a declared search space.

    The return value is candidate-proposal-only and carries no OOS/adoption claim.
    """

    specs = _dimension_specs(dimensions)
    budget_value = _non_negative_int(budget, "budget")
    names = tuple(spec.name for spec in specs)
    sample_batch = halton_unit_samples(
        len(specs),
        budget_value,
        seed=seed,
        scramble=scramble,
        bases=bases,
        skip=skip,
        dimension_names=names,
    )
    candidates = tuple(
        ProposedCandidate(
            trial_index=index,
            unit_sample=sample,
            parameters=map_unit_sample(specs, sample),
            receipt=sample_batch.receipt,
        )
        for index, sample in enumerate(sample_batch.samples, start=1)
    )
    return CandidateBatch(candidates=candidates, receipt=sample_batch.receipt)


def dominates(
    lhs_scores: Mapping[str, float],
    rhs_scores: Mapping[str, float],
    objectives: Mapping[str, str] | Sequence[ObjectiveSpec | tuple[str, str] | Mapping[str, str]],
) -> bool:
    """Return whether ``lhs_scores`` Pareto-dominate ``rhs_scores``."""

    specs = _objective_specs(objectives)
    lhs = _validated_scores(lhs_scores, specs)
    rhs = _validated_scores(rhs_scores, specs)
    return _dominates_clean(lhs, rhs, specs)


class ParetoArchive:
    """Deterministic Pareto archive with explicit objective directions.

    Trial budget is counted per accepted ``add`` call, including duplicate-key
    replacements.  Duplicate keys replace the prior record while preserving the
    first trial index used for stable front ordering.
    """

    def __init__(
        self,
        objectives: Mapping[str, str] | Sequence[ObjectiveSpec | tuple[str, str] | Mapping[str, str]],
        budget: int | None = None,
        *,
        trial_budget: int | None = None,
        seed: int = 0,
    ) -> None:
        if budget is None and trial_budget is None:
            raise QmcParetoError("trial budget is required")
        if budget is not None and trial_budget is not None and budget != trial_budget:
            raise QmcParetoError("budget and trial_budget disagree")
        resolved_budget = trial_budget if budget is None else budget
        self._objectives = _objective_specs(objectives)
        self._budget = _non_negative_int(resolved_budget, "budget")
        self._seed = _integral(seed, "seed")
        self._trials_used = 0
        self._records: dict[Hashable, ArchivedTrial] = {}

    @property
    def budget(self) -> int:
        return self._budget

    @property
    def trials_used(self) -> int:
        return self._trials_used

    @property
    def remaining_budget(self) -> int:
        return self._budget - self._trials_used

    @property
    def objective_directions(self) -> tuple[tuple[str, str], ...]:
        return tuple((item.name, item.direction) for item in self._objectives)

    @property
    def entries(self) -> tuple[ArchivedTrial, ...]:
        return self._front()

    def add(
        self,
        key: Hashable,
        scores: Mapping[str, float],
        payload: Mapping[str, Any] | None = None,
    ) -> ArchiveAddResult:
        """Add one evaluated trial and return the current non-dominated front."""

        _validate_key(key)
        if self.remaining_budget <= 0:
            raise TrialBudgetExceeded("trial budget exceeded")
        clean_scores = _validated_scores(scores, self._objectives)
        clean_payload = MappingProxyType(dict(payload or {}))

        self._trials_used += 1
        prior = self._records.get(key)
        first_trial_index = prior.first_trial_index if prior is not None else self._trials_used
        trial = ArchivedTrial(
            key=key,
            scores=MappingProxyType(dict(clean_scores)),
            payload=clean_payload,
            first_trial_index=first_trial_index,
            last_trial_index=self._trials_used,
            receipt=self._receipt(),
        )
        self._records[key] = trial
        return ArchiveAddResult(trial=trial, front=self._front(), receipt=self._receipt())

    def add_trial(
        self,
        key: Hashable,
        payload: Mapping[str, Any] | None,
        scores: Mapping[str, float],
    ) -> ArchiveAddResult:
        """Compatibility wrapper for call sites that pass payload before scores."""

        return self.add(key=key, scores=scores, payload=payload)

    def snapshot(self) -> ParetoArchiveSnapshot:
        receipt = self._receipt()
        return ParetoArchiveSnapshot(
            entries=self._front(),
            trials_used=self._trials_used,
            remaining_budget=self.remaining_budget,
            receipt=receipt,
        )

    def _front(self) -> tuple[ArchivedTrial, ...]:
        records = tuple(self._records.values())
        front = [
            candidate
            for candidate in records
            if not any(
                other.key != candidate.key and _dominates_clean(other.scores, candidate.scores, self._objectives)
                for other in records
            )
        ]
        front.sort(key=lambda item: item.first_trial_index)
        return tuple(front)

    def _receipt(self) -> ParetoReceipt:
        return ParetoReceipt(
            budget=self._budget,
            objectives=self.objective_directions,
            trials_used=self._trials_used,
            remaining_budget=self.remaining_budget,
            seed=self._seed,
        )


# ---------------------------------------------------------------------------
# Validation and deterministic number generation helpers


def _dimension_specs(dimensions: Sequence[DimensionSpec]) -> tuple[DimensionSpec, ...]:
    specs = tuple(dimensions)
    if not specs:
        raise QmcParetoError("at least one dimension is required")
    if not all(isinstance(spec, DimensionSpec) for spec in specs):
        raise QmcParetoError("dimensions must be DimensionSpec instances")
    names = [spec.name for spec in specs]
    if len(set(names)) != len(names):
        raise QmcParetoError("dimension names must be unique")
    return specs


def _dimension_names(dimension_count: int, dimension_names: Sequence[str] | None) -> tuple[str, ...]:
    if dimension_names is None:
        return tuple(f"dim_{idx}" for idx in range(dimension_count))
    names = tuple(dimension_names)
    if len(names) != dimension_count:
        raise QmcParetoError("dimension_names length must match dimension_count")
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise QmcParetoError("dimension names must be non-empty strings")
    if len(set(names)) != len(names):
        raise QmcParetoError("dimension names must be unique")
    return names


def _objective_specs(
    objectives: Mapping[str, str] | Sequence[ObjectiveSpec | tuple[str, str] | Mapping[str, str]],
) -> tuple[ObjectiveSpec, ...]:
    if isinstance(objectives, Mapping):
        specs = tuple(ObjectiveSpec(str(name), direction) for name, direction in objectives.items())
    else:
        converted: list[ObjectiveSpec] = []
        for item in objectives:
            if isinstance(item, ObjectiveSpec):
                converted.append(item)
            elif isinstance(item, Mapping):
                converted.append(ObjectiveSpec(str(item["name"]), str(item["direction"])))
            else:
                name, direction = item
                converted.append(ObjectiveSpec(str(name), str(direction)))
        specs = tuple(converted)
    if not specs:
        raise QmcParetoError("at least one objective is required")
    names = [item.name for item in specs]
    if len(set(names)) != len(names):
        raise QmcParetoError("objective names must be unique")
    return specs


def _validated_scores(scores: Mapping[str, float], objectives: Sequence[ObjectiveSpec]) -> Mapping[str, float]:
    if not isinstance(scores, Mapping):
        raise QmcParetoError("scores must be a mapping")
    expected = {item.name for item in objectives}
    actual = set(scores.keys())
    missing = sorted(expected - actual, key=str)
    extra = sorted(actual - expected, key=str)
    if missing:
        raise QmcParetoError(f"missing objective score: {missing[0]}")
    if extra:
        raise QmcParetoError(f"undeclared objective score: {extra[0]}")
    return MappingProxyType({item.name: _finite_float(scores[item.name], f"score {item.name}") for item in objectives})


def _dominates_clean(
    lhs_scores: Mapping[str, float],
    rhs_scores: Mapping[str, float],
    objectives: Sequence[ObjectiveSpec],
) -> bool:
    strictly_better = False
    for objective in objectives:
        lhs = lhs_scores[objective.name]
        rhs = rhs_scores[objective.name]
        if objective.direction == DIRECTION_MAXIMIZE:
            if lhs < rhs:
                return False
            strictly_better = strictly_better or lhs > rhs
        else:
            if lhs > rhs:
                return False
            strictly_better = strictly_better or lhs < rhs
    return strictly_better


def _validate_key(key: Hashable) -> None:
    if key is None:
        raise QmcParetoError("trial key is required")
    try:
        hash(key)
    except TypeError as exc:
        raise QmcParetoError("trial key must be hashable") from exc


def _resolve_bases(dimension_count: int, bases: Sequence[int] | None) -> tuple[int, ...]:
    if dimension_count == 0:
        return ()
    resolved = _first_primes(dimension_count) if bases is None else tuple(_integral(base, "base") for base in bases)
    if len(resolved) != dimension_count:
        raise QmcParetoError("bases must provide exactly one prime per dimension")
    if len(set(resolved)) != len(resolved):
        raise QmcParetoError("Halton bases must be unique primes")
    for base in resolved:
        if not _is_prime(base):
            raise QmcParetoError(f"Halton base must be prime: {base}")
    return resolved


def _first_primes(count: int) -> tuple[int, ...]:
    primes: list[int] = []
    candidate = 2
    while len(primes) < count:
        if _is_prime(candidate):
            primes.append(candidate)
        candidate += 1
    return tuple(primes)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value == 2:
        return True
    if value % 2 == 0:
        return False
    divisor = 3
    limit = int(math.sqrt(value))
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _radical_inverse(index: int, base: int, permutation: Sequence[int] | None) -> float:
    value = 0.0
    inverse = 1.0 / base
    n = index
    while n > 0:
        digit = n % base
        if permutation is not None:
            digit = permutation[digit]
        value += digit * inverse
        n //= base
        inverse /= base
    return value


def _scramble_permutation(base: int, seed: int, dim_index: int, dim_name: str) -> tuple[int, ...]:
    digits = list(range(base))
    for idx in range(base - 1, 1, -1):
        swap = 1 + (_hash_int("perm", seed, dim_index, dim_name, base, idx) % idx)
        digits[idx], digits[swap] = digits[swap], digits[idx]
    return tuple(digits)


def _scramble_shift(seed: int, dim_index: int, base: int, dim_name: str) -> float:
    return _hash_int("shift", seed, dim_index, dim_name, base) / float(1 << 64)


def _hash_int(*parts: object) -> int:
    text = "|".join(str(part) for part in (_HASH_PERSON, *parts))
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def _unit_float(value: object, label: str) -> float:
    number = _finite_float(value, label)
    if number < 0.0 or number > 1.0:
        raise QmcParetoError(f"{label} must be in [0, 1]")
    return number


def _continuous_span(low: float, high: float) -> float:
    span = high - low
    if not math.isfinite(span):
        raise QmcParetoError("continuous range is too wide for finite unit mapping")
    return span


def _validate_continuous_mapping_value(value: float, low: float, high: float) -> float:
    if not math.isfinite(value) or value < low or value > high:
        raise QmcParetoError("mapped continuous value must be finite and in bounds")
    return value


def _integer_span(low: int, high: int) -> int:
    _validate_integer_mapping_range(low, high)
    return high - low + 1


def _validate_integer_mapping_range(low: int, high: int) -> None:
    _finite_integer_mapping_bound(low, "integer low")
    _finite_integer_mapping_bound(high, "integer high")
    span = high - low + 1
    if span > _MAX_SAFE_INTEGER_MAPPING_SPAN:
        raise QmcParetoError("integer range is too wide for safe unit mapping")


def _finite_integer_mapping_bound(value: int, label: str) -> None:
    try:
        number = float(value)
    except OverflowError as exc:
        raise QmcParetoError(f"{label} is too large for finite unit mapping") from exc
    if not math.isfinite(number):
        raise QmcParetoError(f"{label} is too large for finite unit mapping")


def _validate_integer_mapping_value(value: int, low: int, high: int) -> int:
    try:
        number = float(value)
    except OverflowError as exc:
        raise QmcParetoError("mapped integer value must be finite and in bounds") from exc
    if not math.isfinite(number) or value < low or value > high:
        raise QmcParetoError("mapped integer value must be finite and in bounds")
    return value


def _finite_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise QmcParetoError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise QmcParetoError(f"{label} must be a finite number")
    return number


def _integral(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise QmcParetoError(f"{label} must be an integer")
    return int(value)


def _non_negative_int(value: object, label: str) -> int:
    number = _integral(value, label)
    if number < 0:
        raise QmcParetoError(f"{label} must be >= 0")
    return number
