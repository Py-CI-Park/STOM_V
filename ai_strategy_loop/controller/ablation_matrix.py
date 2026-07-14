"""CL-R06: 2x2 buy/sell attribution matrix (todo 12).

Pure arithmetic over PRE-COMPUTED per-arm metrics. This module does NOT run
backtests, hit the DB, or call any provider -- the caller supplies four
already-evaluated arms (A/B/C/D), all executed on an identical
manifest/profile/seed/cost so the only degree of freedom across arms is
which buy/sell condition was used.

Arm layout (fixed, not configurable -- callers must assemble arms this way):
    A = parent-buy   + parent-sell     (baseline)
    B = candidate-buy + parent-sell    (isolates the buy change)
    C = parent-buy   + candidate-sell  (isolates the sell change)
    D = candidate-buy + candidate-sell (both changes together)

Each arm metrics dict carries at least: profit, mdd, trade_count, daily_freq
(all plain numbers). Arms may instead be ``None`` or ``{'status': 'error'}``
to signal a failed/skipped evaluation -- in that case attribution is refused
entirely (no partial causal claim).

MDD sign convention: 'mdd' is stored as a non-negative drawdown magnitude
(0 == no drawdown, larger == worse). Because "lower MDD is better", every
delta for 'mdd' is computed on the sign-flipped series (t = -mdd, so a
larger t is better, matching profit/trade_count/daily_freq). Concretely:
buy_effect.mdd = A.mdd - B.mdd, sell_effect.mdd = A.mdd - C.mdd, and
interaction.mdd = B.mdd + C.mdd - A.mdd - D.mdd. With this convention a
positive number always means "improvement" for every metric in the matrix.
"""


from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, replace
from typing import Mapping, Sequence

REQUIRED_ARM_KEYS = ('A', 'B', 'C', 'D')
REQUIRED_METRIC_KEYS = ('profit', 'mdd', 'trade_count', 'daily_freq')

# Metrics where a smaller raw value is an improvement; their deltas are
# sign-flipped so "positive == better" holds uniformly across the matrix.
_LOWER_IS_BETTER_METRICS = frozenset({'mdd'})
ARM_RECEIPT_V1_SCHEMA = 'arm_receipt_v1'
ARM_STATUS_PENDING = 'PENDING'
ARM_STATUS_COMPLETED = 'COMPLETED'
ARM_STATUS_INDETERMINATE_EXTERNAL_EFFECT = 'INDETERMINATE_EXTERNAL_EFFECT'
CACHE_HIT_VALID = 'HIT_VALID'
CACHE_MISS_NO_RECEIPT = 'MISS_NO_RECEIPT'
CACHE_REJECT_NOT_COMPLETED = 'REJECT_NOT_COMPLETED'
CACHE_REJECT_ROLE_MISMATCH = 'REJECT_ROLE_MISMATCH'
CACHE_REJECT_KEY_MISMATCH = 'REJECT_CACHE_KEY_MISMATCH'
RESERVATION_RESERVED = 'RESERVED'
RESERVATION_BUDGET_EXHAUSTED = 'BUDGET_EXHAUSTED'


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    """Return the canonical, deterministic SHA-256 for a pure-contract payload."""
    encoded = json.dumps(
        payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _identity_payload(
    *,
    arm: str,
    candidate_id: str,
    parent_id: str,
    manifest_id: str,
    role: str,
    capability: str,
    engine_id: str,
    data_id: str,
    universe_id: str,
    cost_model_id: str,
    fill_model_id: str,
    capital_profile_id: str,
    session_id: str,
    buy_hash: str,
    sell_hash: str,
) -> dict[str, str]:
    return {
        'arm': arm,
        'candidate_id': candidate_id,
        'parent_id': parent_id,
        'manifest_id': manifest_id,
        'role': role,
        'capability': capability,
        'engine_id': engine_id,
        'data_id': data_id,
        'universe_id': universe_id,
        'cost_model_id': cost_model_id,
        'fill_model_id': fill_model_id,
        'capital_profile_id': capital_profile_id,
        'session_id': session_id,
        'buy_hash': buy_hash,
        'sell_hash': sell_hash,
    }


def build_arm_id(**identity: str) -> str:
    """Build an arm identity binding every evaluation-affecting input."""
    return 'arm_' + _canonical_sha256(_identity_payload(**identity))


def build_arm_cache_key(**identity: str) -> str:
    """Build a cache identity; it intentionally has the same full binding as an arm."""
    return _canonical_sha256(_identity_payload(**identity))


@dataclass(frozen=True)
class ArmReceiptV1:
    """Immutable record of one arm's pure admission, cache, and result contract."""

    schema: str
    arm_id: str
    arm: str
    candidate_id: str
    parent_id: str
    manifest_id: str
    role: str
    capability: str
    engine_id: str
    data_id: str
    universe_id: str
    cost_model_id: str
    fill_model_id: str
    capital_profile_id: str
    session_id: str
    buy_hash: str
    sell_hash: str
    reservation_id: str
    attempt_id: str
    cache_key: str
    cache_disposition: str
    status: str
    result_hash: str
    metric_verdict: str
    reason_codes: tuple[str, ...] = ()
    predecessor_ids: tuple[str, ...] = ()
    metrics: tuple[tuple[str, float], ...] = ()
    retryable: bool = True

    def metrics_dict(self) -> dict[str, float]:
        return dict(self.metrics)


@dataclass(frozen=True)
class ArmBudgetV1:
    limit: int
    reserved: int = 0


@dataclass(frozen=True)
class BudgetReservationV1:
    reservation_id: str
    arm_id: str
    status: str
    budget_limit: int
    reserved_before: int


@dataclass
class ArmBudgetAuthority:
    """In-memory one-shot issuer/consumer for evaluation reservations."""

    issued: set[str] = field(default_factory=set)
    consumed: set[str] = field(default_factory=set)
    budget_limit: int | None = None
    expected_reserved: int = 0

    def bind(self, budget: ArmBudgetV1) -> None:
        if self.budget_limit is None:
            self.budget_limit = budget.limit
        if budget.limit != self.budget_limit or budget.reserved != self.expected_reserved:
            raise ValueError('stale budget counter or mismatched budget authority')

    def issue(self, reservation_id: str, budget: ArmBudgetV1) -> None:
        self.bind(budget)
        if reservation_id in self.issued:
            raise ValueError('stale budget attempted to replay a reservation')
        self.issued.add(reservation_id)
        self.expected_reserved += 1

    def is_active(self, reservation_id: str) -> bool:
        return reservation_id in self.issued and reservation_id not in self.consumed

    def consume(self, reservation_id: str) -> None:
        if not self.is_active(reservation_id):
            raise ValueError('reservation was not issued or was already consumed')
        self.consumed.add(reservation_id)


def build_arm_receipt_v1(
    *,
    arm: str,
    candidate_id: str,
    parent_id: str,
    manifest_id: str,
    role: str,
    capability: str,
    engine_id: str,
    data_id: str,
    universe_id: str,
    cost_model_id: str,
    fill_model_id: str,
    capital_profile_id: str,
    session_id: str,
    buy_hash: str,
    sell_hash: str,
    reservation_id: str = '',
    attempt_id: str = '',
    cache_disposition: str = CACHE_MISS_NO_RECEIPT,
    status: str = ARM_STATUS_PENDING,
    result_hash: str = '',
    metric_verdict: str = '',
    reason_codes: Sequence[str] = (),
    predecessor_ids: Sequence[str] = (),
    metrics: Mapping[str, float] | None = None,
    retryable: bool = True,
) -> ArmReceiptV1:
    """Create an immutable, unbound pending receipt without touching state."""
    if (
        status != ARM_STATUS_PENDING
        or reservation_id
        or attempt_id
        or result_hash
        or metric_verdict
        or metrics
        or not retryable
    ):
        raise ValueError('new arm receipts must start as an unbound pending receipt')
    identity = _identity_payload(
        arm=arm, candidate_id=candidate_id, parent_id=parent_id,
        manifest_id=manifest_id, role=role, capability=capability,
        engine_id=engine_id, data_id=data_id, universe_id=universe_id,
        cost_model_id=cost_model_id, fill_model_id=fill_model_id,
        capital_profile_id=capital_profile_id, session_id=session_id,
        buy_hash=buy_hash, sell_hash=sell_hash,
    )
    canonical_metrics = tuple(sorted(
        (str(key), float(value)) for key, value in (metrics or {}).items()
    ))
    return ArmReceiptV1(
        schema=ARM_RECEIPT_V1_SCHEMA,
        arm_id='arm_' + _canonical_sha256(identity),
        cache_key=_canonical_sha256(identity),
        arm=arm, candidate_id=candidate_id, parent_id=parent_id,
        manifest_id=manifest_id, role=role, capability=capability,
        engine_id=engine_id, data_id=data_id, universe_id=universe_id,
        cost_model_id=cost_model_id, fill_model_id=fill_model_id,
        capital_profile_id=capital_profile_id, session_id=session_id,
        buy_hash=buy_hash, sell_hash=sell_hash, reservation_id=reservation_id,
        attempt_id=attempt_id, cache_disposition=cache_disposition, status=status,
        result_hash=result_hash, metric_verdict=metric_verdict,
        reason_codes=tuple(reason_codes), predecessor_ids=tuple(predecessor_ids),
        metrics=canonical_metrics, retryable=retryable,
    )


def reserve_arm_budget(
    budget: ArmBudgetV1,
    receipt: ArmReceiptV1,
    authority: ArmBudgetAuthority,
) -> tuple[ArmBudgetV1, BudgetReservationV1]:
    """Reserve one evaluation slot; exhausted budgets never admit an evaluator."""
    if receipt.reservation_id:
        raise ValueError('arm receipt is already reservation-bound')
    if budget.limit < 0 or budget.reserved < 0:
        raise ValueError('budget counters must be non-negative')
    reservation_id = _canonical_sha256({
        'arm_id': receipt.arm_id, 'limit': budget.limit, 'reserved': budget.reserved,
    })
    if budget.reserved >= budget.limit:
        authority.bind(budget)
        return budget, BudgetReservationV1(
            reservation_id=reservation_id,
            arm_id=receipt.arm_id,
            status=RESERVATION_BUDGET_EXHAUSTED,
            budget_limit=budget.limit,
            reserved_before=budget.reserved,
        )
    authority.issue(reservation_id, budget)
    return (
        replace(budget, reserved=budget.reserved + 1),
        BudgetReservationV1(
            reservation_id=reservation_id,
            arm_id=receipt.arm_id,
            status=RESERVATION_RESERVED,
            budget_limit=budget.limit,
            reserved_before=budget.reserved,
        ),
    )


def _completed_receipt_is_valid(receipt: ArmReceiptV1) -> bool:
    metrics = receipt.metrics_dict()
    return bool(
        receipt.status == ARM_STATUS_COMPLETED
        and receipt.reservation_id
        and receipt.attempt_id
        and receipt.result_hash
        and receipt.metric_verdict
        and not receipt.retryable
        and set(REQUIRED_METRIC_KEYS).issubset(metrics)
        and all(math.isfinite(value) for value in metrics.values())
    )


def evaluator_admitted(
    receipt: ArmReceiptV1,
    reservation: BudgetReservationV1 | None,
    authority: ArmBudgetAuthority,
) -> bool:
    """An evaluator can proceed only for an active, exact prior reservation."""
    if reservation is None:
        return False
    expected_id = _canonical_sha256({
        'arm_id': receipt.arm_id,
        'limit': reservation.budget_limit,
        'reserved': reservation.reserved_before,
    })
    return bool(
        receipt.status == ARM_STATUS_PENDING
        and receipt.retryable
        and reservation.status == RESERVATION_RESERVED
        and reservation.arm_id == receipt.arm_id
        and reservation.reservation_id == expected_id
        and reservation.budget_limit >= 0
        and 0 <= reservation.reserved_before < reservation.budget_limit
        and not receipt.reservation_id
        and authority.is_active(reservation.reservation_id)
    )


def cache_disposition(
    receipt: ArmReceiptV1, cached: ArmReceiptV1 | None,
) -> str:
    """Accept a cache hit only for an exact completed receipt in the same role."""
    if cached is None:
        return CACHE_MISS_NO_RECEIPT
    if cached.schema != ARM_RECEIPT_V1_SCHEMA:
        return CACHE_REJECT_KEY_MISMATCH
    if cached.role != receipt.role:
        return CACHE_REJECT_ROLE_MISMATCH
    if cached.cache_key != receipt.cache_key or cached.arm_id != receipt.arm_id:
        return CACHE_REJECT_KEY_MISMATCH
    if not _completed_receipt_is_valid(cached):
        return CACHE_REJECT_NOT_COMPLETED
    return CACHE_HIT_VALID


def complete_arm_receipt(
    receipt: ArmReceiptV1,
    reservation: BudgetReservationV1,
    authority: ArmBudgetAuthority,
    *,
    attempt_id: str,
    result_hash: str,
    metric_verdict: str,
    metrics: Mapping[str, float],
) -> ArmReceiptV1:
    """Produce a completed receipt only after the evaluator has been admitted."""
    if not evaluator_admitted(receipt, reservation, authority):
        raise ValueError('evaluator admission requires a prior budget reservation')
    canonical_metrics = {
        str(key): float(value) for key, value in metrics.items()
    }
    if (
        not attempt_id
        or not result_hash
        or not metric_verdict
        or not set(REQUIRED_METRIC_KEYS).issubset(canonical_metrics)
        or not all(math.isfinite(value) for value in canonical_metrics.values())
    ):
        raise ValueError('completed receipts require finite metrics and result provenance')
    authority.consume(reservation.reservation_id)
    return replace(
        receipt, reservation_id=reservation.reservation_id, attempt_id=attempt_id,
        status=ARM_STATUS_COMPLETED, result_hash=result_hash,
        metric_verdict=metric_verdict,
        metrics=tuple(sorted(canonical_metrics.items())),
        retryable=False,
    )


def crash_arm_receipt(
    receipt: ArmReceiptV1,
    reservation: BudgetReservationV1 | None = None,
    *,
    authority: ArmBudgetAuthority,
) -> ArmReceiptV1:
    """Encode crash semantics without retrying an evaluation of unknown external effect."""
    if evaluator_admitted(receipt, reservation, authority):
        authority.consume(reservation.reservation_id)
        return replace(
            receipt, reservation_id=reservation.reservation_id,
            status=ARM_STATUS_INDETERMINATE_EXTERNAL_EFFECT,
            reason_codes=tuple((*receipt.reason_codes, 'crash_after_reservation')),
            retryable=False,
        )
    return replace(
        receipt, reason_codes=tuple((*receipt.reason_codes, 'crash_before_reservation')),
        retryable=True,
    )


def compute_receipt_attribution(receipts: Mapping[str, ArmReceiptV1] | None) -> dict:
    """Attribute only a complete 2x2 set sharing one manifest and one role."""
    receipts = receipts or {}
    missing = [
        arm for arm in REQUIRED_ARM_KEYS
        if arm not in receipts or not _completed_receipt_is_valid(receipts[arm])
    ]
    if missing:
        return {
            'valid': False, 'reason': 'attribution_invalid', 'missing_arms': missing,
        }
    selected = {arm: receipts[arm] for arm in REQUIRED_ARM_KEYS}
    if any(receipt.arm != arm for arm, receipt in selected.items()):
        return {
            'valid': False, 'reason': 'attribution_identity_mismatch',
            'missing_arms': list(REQUIRED_ARM_KEYS),
        }
    shared_fields = (
        'candidate_id', 'parent_id', 'manifest_id', 'role', 'capability',
        'engine_id', 'data_id', 'universe_id', 'cost_model_id',
        'fill_model_id', 'capital_profile_id', 'session_id',
    )
    if any(
        len({getattr(receipt, field) for receipt in selected.values()}) != 1
        for field in shared_fields
    ):
        return {
            'valid': False, 'reason': 'attribution_identity_mismatch',
            'missing_arms': list(REQUIRED_ARM_KEYS),
        }
    arm_a, arm_b, arm_c, arm_d = (
        selected['A'], selected['B'], selected['C'], selected['D']
    )
    pairing_valid = (
        arm_b.sell_hash == arm_a.sell_hash
        and arm_c.buy_hash == arm_a.buy_hash
        and arm_d.buy_hash == arm_b.buy_hash
        and arm_d.sell_hash == arm_c.sell_hash
        and arm_b.buy_hash != arm_a.buy_hash
        and arm_c.sell_hash != arm_a.sell_hash
    )
    if not pairing_valid:
        return {
            'valid': False, 'reason': 'attribution_pairing_mismatch',
            'missing_arms': list(REQUIRED_ARM_KEYS),
        }
    return compute_attribution({
        arm: selected[arm].metrics_dict() for arm in REQUIRED_ARM_KEYS
    })


def _arm_is_errored(arm: object) -> bool:
    if arm is None:
        return True
    if isinstance(arm, dict) and arm.get('status') == 'error':
        return True
    return False


def _arm_metrics(arm: dict) -> dict[str, float]:
    return {key: float(arm[key]) for key in REQUIRED_METRIC_KEYS}


def compute_attribution(arms: dict) -> dict:
    """Compute buy_effect, sell_effect, and interaction across a 2x2 arm set.

    arms must contain keys 'A', 'B', 'C', 'D'; each value is either a metrics
    dict (with at minimum REQUIRED_METRIC_KEYS) or a sentinel signalling a
    missing/errored evaluation (None or {'status': 'error'}).

    Returns {'valid': True, 'buy_effect': {...}, 'sell_effect': {...},
    'interaction': {...}} on success, or {'valid': False,
    'reason': 'attribution_invalid', 'missing_arms': [...]} when any arm is
    missing/errored -- in which case no effect numbers are returned.
    """

    arms = arms or {}
    missing_arms = [
        key for key in REQUIRED_ARM_KEYS
        if key not in arms or _arm_is_errored(arms.get(key))
    ]
    if missing_arms:
        return {
            'valid': False,
            'reason': 'attribution_invalid',
            'missing_arms': missing_arms,
        }

    for key in REQUIRED_ARM_KEYS:
        arm = arms[key]
        if not isinstance(arm, dict) or any(metric not in arm for metric in REQUIRED_METRIC_KEYS):
            missing_arms.append(key)
    if missing_arms:
        return {
            'valid': False,
            'reason': 'attribution_invalid',
            'missing_arms': sorted(set(missing_arms)),
        }

    metrics_a = _arm_metrics(arms['A'])
    metrics_b = _arm_metrics(arms['B'])
    metrics_c = _arm_metrics(arms['C'])
    metrics_d = _arm_metrics(arms['D'])

    buy_effect: dict[str, float] = {}
    sell_effect: dict[str, float] = {}
    interaction: dict[str, float] = {}
    for metric in REQUIRED_METRIC_KEYS:
        a, b, c, d = metrics_a[metric], metrics_b[metric], metrics_c[metric], metrics_d[metric]
        if metric in _LOWER_IS_BETTER_METRICS:
            buy_effect[metric] = a - b
            sell_effect[metric] = a - c
            interaction[metric] = b + c - a - d
        else:
            buy_effect[metric] = b - a
            sell_effect[metric] = c - a
            interaction[metric] = d - b - c + a

    return {
        'valid': True,
        'buy_effect': buy_effect,
        'sell_effect': sell_effect,
        'interaction': interaction,
    }
