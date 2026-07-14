"""Schema-v11 typed feedback resolution contracts.

This module is intentionally pure and unused by default.  It neither reads loop
state nor invokes providers/backtests.  Callers opt in by constructing immutable
``FeedbackDirective`` values and resolving them against explicit evidence hashes.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Tuple

from ai_strategy_loop.controller.evidence_contract import canonical_json, sha256_hex

__all__ = [
    "FEEDBACK_RESOLVER_SCHEMA_VERSION",
    "FEEDBACK_DIRECTIVE_SCHEMA",
    "FeedbackSide",
    "FeedbackDataRole",
    "FeedbackStatus",
    "FeedbackDirective",
    "ResolvedFeedbackDirective",
    "FeedbackResolution",
    "TypedFeedbackEnvelope",
    "FeedbackResolver",
    "compute_feedback_directive_id",
    "resolve_feedback",
    "resolve_actionable_feedback",
    "REASON_READY",
    "REASON_DESCRIPTIVE_ONLY",
    "REASON_EMPTY",
    "REASON_STALE",
    "REASON_BLOCKED_STATUS",
    "REASON_HOLDOUT",
    "REASON_EVIDENCE_MISSING",
    "REASON_EVIDENCE_HASH_MISMATCH",
    "REASON_NOT_YET_CREATED",
    "REASON_SCOPE_CONFLICT",
]

FEEDBACK_RESOLVER_SCHEMA_VERSION = 11
FEEDBACK_DIRECTIVE_SCHEMA = "feedback_directive.v11"

REASON_READY = "READY"
REASON_DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
REASON_EMPTY = "EMPTY_DIRECTIVE"
REASON_STALE = "STALE_GENERATION"
REASON_BLOCKED_STATUS = "BLOCKED_STATUS"
REASON_HOLDOUT = "HOLDOUT_EVALUATION_ONLY"
REASON_EVIDENCE_MISSING = "EVIDENCE_MISSING"
REASON_EVIDENCE_HASH_MISMATCH = "EVIDENCE_HASH_MISMATCH"
REASON_SCOPE_CONFLICT = "CONFLICTING_SCOPE_DIRECTIVE"
REASON_NOT_YET_CREATED = "NOT_YET_CREATED"


class FeedbackStatus(str, Enum):
    READY = "READY"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
    EMPTY = "EMPTY"
    BLOCKED = "BLOCKED"
    STALE = "STALE"


class FeedbackSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class FeedbackDataRole(str, Enum):
    TRAIN = "TRAIN"
    HOLDOUT = "HOLDOUT"


def _enum(value: Any, enum_type: type[Enum], field: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{field}") from exc


def _text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid_{field}")
    return _text(value).strip()


def _sha256(value: Any, field: str) -> str:
    value = _nonempty(value, field)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"invalid_{field}")
    return value


def _generation(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"invalid_{field}")
    return value
def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid_{field}")
    return value



def compute_feedback_directive_id(
    *,
    scope: str,
    side: FeedbackSide | str,
    role: FeedbackDataRole | str,
    priority: int,
    statement: str,
    evidence_id: str,
    evidence_sha256: str,
    created_generation: int,
    expires_generation: int,
    status: FeedbackStatus | str = FeedbackStatus.READY,
) -> str:
    """Return the canonical, content-addressed identity for one directive."""
    return "fd_" + sha256_hex(canonical_json({
        "schema": FEEDBACK_DIRECTIVE_SCHEMA,
        "scope": _nonempty(scope, "scope"),
        "side": _enum(side, FeedbackSide, "side").value,
        "role": _enum(role, FeedbackDataRole, "role").value,
        "priority": _integer(priority, "priority"),
        "statement": _text(statement).strip() if isinstance(statement, str) else "",
        "evidence_id": _nonempty(evidence_id, "evidence_id"),
        "evidence_sha256": _sha256(evidence_sha256, "evidence_sha256"),
        "created_generation": _generation(created_generation, "created_generation"),
        "expires_generation": _generation(expires_generation, "expires_generation"),
        "status": _enum(status, FeedbackStatus, "status").value,
    }))


@dataclass(frozen=True, slots=True)
class FeedbackDirective:
    """An evidence-bound prompt directive; no runtime authority is implied."""

    scope: str
    side: FeedbackSide
    role: FeedbackDataRole
    priority: int
    statement: str
    evidence_id: str
    evidence_sha256: str
    created_generation: int
    expires_generation: int
    status: FeedbackStatus = FeedbackStatus.READY
    directive_id: Optional[str] = None
    schema_version: int = FEEDBACK_RESOLVER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", _nonempty(self.scope, "scope"))
        object.__setattr__(self, "side", _enum(self.side, FeedbackSide, "side"))
        object.__setattr__(self, "role", _enum(self.role, FeedbackDataRole, "role"))
        object.__setattr__(self, "priority", _integer(self.priority, "priority"))
        object.__setattr__(self, "statement", _text(self.statement).strip() if isinstance(self.statement, str) else "")
        object.__setattr__(self, "evidence_id", _nonempty(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "evidence_sha256", _sha256(self.evidence_sha256, "evidence_sha256"))
        object.__setattr__(self, "created_generation", _generation(self.created_generation, "created_generation"))
        object.__setattr__(self, "expires_generation", _generation(self.expires_generation, "expires_generation"))
        if self.expires_generation < self.created_generation:
            raise ValueError("expiry_before_creation")
        object.__setattr__(self, "status", _enum(self.status, FeedbackStatus, "status"))
        if self.schema_version != FEEDBACK_RESOLVER_SCHEMA_VERSION:
            raise ValueError("unsupported_schema_version")
        expected_id = compute_feedback_directive_id(
            scope=self.scope, side=self.side, role=self.role, priority=self.priority,
            statement=self.statement, evidence_id=self.evidence_id,
            evidence_sha256=self.evidence_sha256,
            created_generation=self.created_generation,
            expires_generation=self.expires_generation, status=self.status,
        )
        if self.directive_id is not None and self.directive_id != expected_id:
            raise ValueError("directive_id_mismatch")
        object.__setattr__(self, "directive_id", expected_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "directive_id": self.directive_id,
            "scope": self.scope, "side": self.side.value, "role": self.role.value,
            "priority": self.priority, "statement": self.statement,
            "evidence_id": self.evidence_id, "evidence_sha256": self.evidence_sha256,
            "created_generation": self.created_generation,
            "expires_generation": self.expires_generation, "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class ResolvedFeedbackDirective:
    directive: FeedbackDirective
    status: FeedbackStatus
    reason_code: str

    @property
    def actionable(self) -> bool:
        return self.directive.role is FeedbackDataRole.TRAIN and self.status is FeedbackStatus.READY


@dataclass(frozen=True, slots=True)
class FeedbackResolution:
    directives: Tuple[ResolvedFeedbackDirective, ...]

    @property
    def actionable_directives(self) -> Tuple[FeedbackDirective, ...]:
        return tuple(item.directive for item in self.directives if item.actionable)


class FeedbackResolver:
    """Resolve explicit feedback against explicit evidence at one generation."""

    def __init__(self, *, generation: int, evidence_hashes: Mapping[str, str]) -> None:
        self._generation = _generation(generation, "generation")
        self._evidence_hashes = dict(evidence_hashes)

    def resolve(self, directives: Iterable[FeedbackDirective]) -> FeedbackResolution:
        # A stable id sort makes duplicate removal and all subsequent ties platform independent.
        unique = {directive.directive_id: directive for directive in directives}
        resolved = [self._classify(directive) for _, directive in sorted(unique.items())]

        # Only otherwise-ready TRAIN directives participate.  Scope and side are both
        # dimensions: a BUY instruction cannot block SELL, nor can another scope.
        winners: dict[tuple[str, FeedbackSide], ResolvedFeedbackDirective] = {}
        for item in resolved:
            if not item.actionable:
                continue
            key = (item.directive.scope, item.directive.side)
            prior = winners.get(key)
            if prior is None or self._winner_key(item.directive) < self._winner_key(prior.directive):
                winners[key] = item

        winner_ids = {item.directive.directive_id for item in winners.values()}
        final = tuple(
            replace(item, status=FeedbackStatus.BLOCKED, reason_code=REASON_SCOPE_CONFLICT)
            if item.actionable and item.directive.directive_id not in winner_ids else item
            for item in resolved
        )
        return FeedbackResolution(tuple(sorted(final, key=self._result_key)))

    @staticmethod
    def _winner_key(directive: FeedbackDirective) -> tuple[int, str]:
        return (-directive.priority, directive.directive_id or "")

    @staticmethod
    def _result_key(item: ResolvedFeedbackDirective) -> tuple[str, str, int, str]:
        directive = item.directive
        return (directive.scope, directive.side.value, -directive.priority, directive.directive_id or "")

    def _classify(self, directive: FeedbackDirective) -> ResolvedFeedbackDirective:
        if self._generation > directive.expires_generation:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.STALE, REASON_STALE)
        if self._generation < directive.created_generation:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.BLOCKED, REASON_NOT_YET_CREATED)
        if not directive.statement:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.EMPTY, REASON_EMPTY)
        if directive.status is FeedbackStatus.BLOCKED:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.BLOCKED, REASON_BLOCKED_STATUS)
        if directive.status is FeedbackStatus.DESCRIPTIVE_ONLY:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.DESCRIPTIVE_ONLY, REASON_DESCRIPTIVE_ONLY)
        if directive.status is FeedbackStatus.EMPTY:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.EMPTY, REASON_EMPTY)
        if directive.status is FeedbackStatus.STALE:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.STALE, REASON_STALE)
        actual_hash = self._evidence_hashes.get(directive.evidence_id)
        if actual_hash is None:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.BLOCKED, REASON_EVIDENCE_MISSING)
        if actual_hash != directive.evidence_sha256:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.BLOCKED, REASON_EVIDENCE_HASH_MISMATCH)
        if directive.role is FeedbackDataRole.HOLDOUT:
            return ResolvedFeedbackDirective(directive, FeedbackStatus.DESCRIPTIVE_ONLY, REASON_HOLDOUT)
        return ResolvedFeedbackDirective(directive, FeedbackStatus.READY, REASON_READY)


def resolve_feedback(
    directives: Iterable[FeedbackDirective], *, generation: int, evidence_hashes: Mapping[str, str]
) -> FeedbackResolution:
    """Convenience wrapper for deterministic full resolution."""
    return FeedbackResolver(generation=generation, evidence_hashes=evidence_hashes).resolve(directives)


def resolve_actionable_feedback(
    directives: Iterable[FeedbackDirective], *, generation: int, evidence_hashes: Mapping[str, str]
) -> Tuple[FeedbackDirective, ...]:
    """Return only evidence-valid TRAIN + READY directives, in stable order."""
    return resolve_feedback(directives, generation=generation, evidence_hashes=evidence_hashes).actionable_directives


@dataclass(frozen=True, slots=True)
class TypedFeedbackEnvelope:
    """Immutable prompt envelope that always replays the canonical resolver."""

    scope: str
    evidence_id: str
    generation: int
    directives: Tuple[FeedbackDirective, ...]
    schema: str = "typed_feedback_v2"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", _nonempty(self.scope, "scope"))
        object.__setattr__(self, "evidence_id", _sha256(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "generation", _generation(self.generation, "generation"))
        object.__setattr__(self, "directives", tuple(self.directives))
        if self.schema != "typed_feedback_v2":
            raise ValueError("unsupported_typed_feedback_schema")
        if not self.directives or not all(
            isinstance(item, FeedbackDirective) for item in self.directives
        ):
            raise ValueError("invalid_typed_feedback_directives")
        if any(
            item.evidence_id != self.evidence_id
            or item.evidence_sha256 != self.evidence_id
            for item in self.directives
        ):
            raise ValueError("typed_feedback_evidence_mismatch")

    @property
    def actionable_directives(self) -> Tuple[FeedbackDirective, ...]:
        return resolve_actionable_feedback(
            self.directives,
            generation=self.generation,
            evidence_hashes={self.evidence_id: self.evidence_id},
        )
