"""Condition-discovery preset, gate, and evidence policy helpers.

The helpers compute JSON-safe policy payloads and the matching runtime-safe
configuration overlay used by the loop. They never touch live/export paths or
grant winner/promotion authority; hard gates remain evidence-bound.
"""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass, replace
from typing import Any, Dict, Mapping, Optional
import copy

PRESET_FAST = "fast"
PRESET_RESEARCH = "research"
PRESET_PROMOTION = "promotion"
VALID_PRESETS = (PRESET_FAST, PRESET_RESEARCH, PRESET_PROMOTION)
PROCESS_FAST_DISCOVERY = "fast-discovery"
PROCESS_RESEARCH = "process-research"
PROCESS_PROMOTION_REVIEW = "promotion-review"
PROCESS_NUMERIC_ALIASES = {
    "1": PROCESS_FAST_DISCOVERY,
    "2": PROCESS_RESEARCH,
    "3": PROCESS_PROMOTION_REVIEW,
}

TIMEFRAME_TICK = "tick"
TIMEFRAME_MIN = "min"

EVIDENCE_CSV = "csv"
EVIDENCE_TRADES = "trades"
EVIDENCE_EQUITY = "equity"
EVIDENCE_PROMPT = "prompt"
EVIDENCE_VALIDATION = "validation"
EVIDENCE_COMPONENTS = (
    EVIDENCE_CSV,
    EVIDENCE_TRADES,
    EVIDENCE_EQUITY,
    EVIDENCE_PROMPT,
    EVIDENCE_VALIDATION,
)

STATUS_PRESENT = "present"
STATUS_MISSING = "missing"
STATUS_UNAVAILABLE = "unavailable"
STATUS_FAILED = "failed"
STATUS_NOT_REQUIRED = "not_required"
_VALID_EVIDENCE_STATUSES = {
    STATUS_PRESENT,
    STATUS_MISSING,
    STATUS_UNAVAILABLE,
    STATUS_FAILED,
    STATUS_NOT_REQUIRED,
}
_BLOCKING_STATUSES = {STATUS_MISSING, STATUS_UNAVAILABLE, STATUS_FAILED}

TICK_RESEARCH_START = 90000
TICK_RESEARCH_END = 92800
MIN_FULL_SESSION_START = 90000
MIN_FULL_SESSION_END_CANDIDATES = (151800, 151900)


@dataclass(frozen=True)
class PresetPolicy:
    """Static policy attached to a condition-discovery preset."""

    preset: str
    label: str
    purpose: str
    staged_mdd_cap: float
    min_daily_trades: float
    prompt_logging_required: bool
    equity_points_required: bool
    oos_mode: str
    promotion_candidate_allowed: bool
    human_approval_required: bool
    required_evidence: tuple[str, ...]

    def to_dict(self, *, configured_mdd_cap: Optional[float] = None) -> Dict[str, Any]:
        configured = None if configured_mdd_cap is None else max(0.0, float(configured_mdd_cap))
        effective = self.staged_mdd_cap if configured is None else min(configured, self.staged_mdd_cap)
        return {
            "preset": self.preset,
            "label": self.label,
            "purpose": self.purpose,
            "staged_mdd_cap": self.staged_mdd_cap,
            "configured_mdd_cap": configured,
            "effective_mdd_cap": effective,
            "min_daily_trades": self.min_daily_trades,
            "prompt_logging_required": self.prompt_logging_required,
            "equity_points_required": self.equity_points_required,
            "oos_mode": self.oos_mode,
            "promotion_candidate_allowed": self.promotion_candidate_allowed,
            "human_approval_required": self.human_approval_required,
            "required_evidence": list(self.required_evidence),
        }


@dataclass(frozen=True)
class ProcessCatalogEntry:
    """Single-authority projection from a user-facing process selector to a preset."""

    number: int
    code: str
    preset: str
    label: str
    description: str
    research_actions: tuple[str, ...] = ()
    blocked_actions: tuple[str, ...] = ()
    quick_start: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "code": self.code,
            "preset": self.preset,
            "label": self.label,
            "description": self.description,
            "aliases": [str(self.number), self.code],
            "authority": "advisory_research" if self.preset != PRESET_PROMOTION else "separate_frozen_promotion_review",
            "research_actions": list(self.research_actions),
            "blocked_actions": list(self.blocked_actions),
            "quick_start": self.quick_start,
        }


_PRESET_POLICIES: Dict[str, PresetPolicy] = {
    PRESET_FAST: PresetPolicy(
        preset=PRESET_FAST,
        label="Fast discovery",
        purpose="빠르게 후보 구조를 탐색한다. 점수와 evidence는 설명용이며 승격 후보가 아니다.",
        staged_mdd_cap=35.0,
        min_daily_trades=0.5,
        prompt_logging_required=False,
        equity_points_required=False,
        oos_mode="disabled",
        promotion_candidate_allowed=False,
        human_approval_required=True,
        required_evidence=(EVIDENCE_CSV, EVIDENCE_TRADES, EVIDENCE_VALIDATION),
    ),
    PRESET_RESEARCH: PresetPolicy(
        preset=PRESET_RESEARCH,
        label="Research discovery",
        purpose="프롬프트·손익곡선·검증 evidence를 보존하며 후보를 연구한다.",
        staged_mdd_cap=25.0,
        min_daily_trades=0.5,
        prompt_logging_required=True,
        equity_points_required=True,
        oos_mode="advisory",
        promotion_candidate_allowed=False,
        human_approval_required=True,
        required_evidence=EVIDENCE_COMPONENTS,
    ),
    PRESET_PROMOTION: PresetPolicy(
        preset=PRESET_PROMOTION,
        label="Promotion review",
        purpose="동결 후보를 승격 검토한다. hard gate와 evidence blocker가 점수보다 우선한다.",
        staged_mdd_cap=15.0,
        min_daily_trades=0.5,
        prompt_logging_required=True,
        equity_points_required=True,
        oos_mode="promotion_only",
        promotion_candidate_allowed=True,
        human_approval_required=True,
        required_evidence=EVIDENCE_COMPONENTS,
    ),
}


PROCESS_CATALOG = (
    ProcessCatalogEntry(
        number=1,
        code=PROCESS_FAST_DISCOVERY,
        preset=PRESET_FAST,
        label="Fast discovery",
        description="빠른 후보 발굴과 즉시 연구 시작용 projection입니다. 전체기간 테스트·분석·개선 루프는 research advisory로 허용됩니다.",
        research_actions=(
            "candidate_generation",
            "smoke_or_full_period_backtest",
            "edge_ratio_analysis",
            "condition_improvement_loop",
        ),
        blocked_actions=("production_promote", "export", "live"),
        quick_start="1번은 빠르게 후보를 만들고 곧바로 전체기간/스모크 연구를 반복합니다.",
    ),
    ProcessCatalogEntry(
        number=2,
        code=PROCESS_RESEARCH,
        preset=PRESET_RESEARCH,
        label="Process research",
        description="전체기간 분석과 evidence 보존을 중심으로 조건식을 연구·개선하는 projection입니다.",
        research_actions=(
            "full_period_validation",
            "candidate_generation",
            "evidence_preservation",
            "edge_ratio_segment_analysis",
            "condition_improvement_loop",
        ),
        blocked_actions=("clean_oos_promotion_claim", "production_promote", "export", "live"),
        quick_start="2번은 전체기간 백테스트→분석→조건식 개선을 반복하는 연구 루틴입니다.",
    ),
    ProcessCatalogEntry(
        number=3,
        code=PROCESS_PROMOTION_REVIEW,
        preset=PRESET_PROMOTION,
        label="Promotion review",
        description="동결 후보를 운영 승격 전 별도 리뷰로 검토하는 projection입니다.",
        research_actions=("frozen_candidate_review", "evidence_health_review", "hard_gate_review"),
        blocked_actions=("final_promotion_without_human_approval", "export_without_approval", "live_without_approval"),
        quick_start="3번은 연구 실행이 아니라 동결 후보의 승격 가능성을 따로 검토합니다.",
    ),
)
_PROCESS_BY_CODE = {entry.code: entry for entry in PROCESS_CATALOG}
_PROCESS_BY_PRESET = {entry.preset: entry for entry in PROCESS_CATALOG}
_PROCESS_SELECTOR_ALIASES = {
    **PROCESS_NUMERIC_ALIASES,
    **{entry.code: entry.code for entry in PROCESS_CATALOG},
}


def normalize_condition_discovery_preset(value: Any) -> str:
    """Return a supported preset name or raise ValueError."""

    preset = str(value or PRESET_FAST).strip().lower()
    if preset not in _PRESET_POLICIES:
        raise ValueError(
            "condition_discovery_preset은 "
            f"{VALID_PRESETS} 중 하나여야 합니다 (받음: {value!r})"
        )
    return preset


def normalize_condition_discovery_process(value: Any) -> str:
    """Return canonical process code from numeric alias or code name."""

    selector = str(value or PROCESS_FAST_DISCOVERY).strip().lower()
    code = _PROCESS_SELECTOR_ALIASES.get(selector)
    if code is None:
        raise ValueError(
            "condition_discovery_process는 "
            "1|2|3 또는 fast-discovery|process-research|promotion-review 중 하나여야 "
            f"합니다 (받음: {value!r})"
        )
    return code


def process_entry_for_preset(preset: Any) -> ProcessCatalogEntry:
    return _PROCESS_BY_PRESET[normalize_condition_discovery_preset(preset)]


def process_entry_for_selector(selector: Any) -> ProcessCatalogEntry:
    return _PROCESS_BY_CODE[normalize_condition_discovery_process(selector)]


def resolve_condition_discovery_process_projection(
    selector: Any = None,
    preset: Any = None,
) -> Dict[str, str]:
    """Resolve selector and preset as one authority, rejecting mismatches."""

    has_selector = selector is not None and str(selector).strip() != ""
    has_preset = preset is not None and str(preset).strip() != ""
    if has_selector:
        process = process_entry_for_selector(selector)
        if has_preset:
            normalized_preset = normalize_condition_discovery_preset(preset)
            if process.preset != normalized_preset:
                raise ValueError(
                    "condition_discovery_process와 condition_discovery_preset이 일치해야 합니다 "
                    f"(process={process.code!r}->{process.preset!r}, preset={normalized_preset!r})"
                )
        return {"process": process.code, "preset": process.preset}

    normalized_preset = normalize_condition_discovery_preset(preset if has_preset else PRESET_FAST)
    process = process_entry_for_preset(normalized_preset)
    return {"process": process.code, "preset": normalized_preset}


def preset_policy(preset: Any) -> PresetPolicy:
    return _PRESET_POLICIES[normalize_condition_discovery_preset(preset)]


def _coerce_time(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def resolve_time_window_policy(config: Any) -> Dict[str, Any]:
    """Resolve tick/min session-window policy for the configured preset.

    The payload is descriptive and JSON-safe. It does not mutate ``config`` or change
    the backtest engine. Dashboard consumers can display the same payload; runtime
    wiring remains explicit and testable.
    """

    preset = normalize_condition_discovery_preset(getattr(config, "condition_discovery_preset", PRESET_FAST))
    timeframe = str(getattr(config, "bt_timeframe", TIMEFRAME_MIN) or TIMEFRAME_MIN).lower()
    if timeframe == TIMEFRAME_TICK:
        return {
            "timeframe": TIMEFRAME_TICK,
            "start_time": TICK_RESEARCH_START,
            "end_time": TICK_RESEARCH_END,
            "full_session_required": False,
            "source": "condition_discovery_tick_research_window",
            "boundary_status": "fixed",
            "notes": "Tick research/promotion uses the approved 09:00-09:28 opening window.",
        }

    end_time = _coerce_time(getattr(config, "bt_min_universe_end_time", 151900), 151900)
    if preset in (PRESET_RESEARCH, PRESET_PROMOTION):
        full_session_required = True
        boundary_status = "verified_candidate" if end_time in MIN_FULL_SESSION_END_CANDIDATES else "requires_boundary_verification"
        source = "condition_discovery_min_full_session"
    else:
        full_session_required = bool(getattr(config, "full_session_enabled", False))
        boundary_status = "not_required_for_fast"
        source = "configured_min_window"

    return {
        "timeframe": TIMEFRAME_MIN,
        "start_time": MIN_FULL_SESSION_START,
        "end_time": end_time if full_session_required else _coerce_time(getattr(config, "bt_universe_end_time", 92800), 92800),
        "full_session_required": full_session_required,
        "source": source,
        "boundary_status": boundary_status,
        "end_time_candidates": list(MIN_FULL_SESSION_END_CANDIDATES),
        "notes": "Research/promotion MIN requires full-session coverage; 15:18 vs 15:19 remains an explicit boundary check.",
    }


def _normalize_evidence_status(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("status")
    if value is True:
        return STATUS_PRESENT
    if value is False or value is None:
        return STATUS_MISSING
    status = str(value).strip().lower()
    if status in _VALID_EVIDENCE_STATUSES:
        return status
    return STATUS_FAILED


def build_evidence_health(
    evidence: Optional[Mapping[str, Any]],
    *,
    preset: Any = PRESET_FAST,
) -> Dict[str, Any]:
    """Normalize CSV/trade/equity/prompt/validation evidence into blockers."""

    policy = preset_policy(preset)
    raw = evidence or {}
    required = set(policy.required_evidence)
    components = []
    blockers = []
    for name in EVIDENCE_COMPONENTS:
        status = _normalize_evidence_status(raw.get(name))
        is_required = name in required
        if not is_required and name not in raw:
            status = STATUS_NOT_REQUIRED
        if is_required and status == STATUS_NOT_REQUIRED:
            status = STATUS_MISSING
        blocker_reason = ""
        if is_required and status in _BLOCKING_STATUSES:
            blocker_reason = f"missing_or_invalid_{name}_evidence"
            blockers.append(blocker_reason)
        components.append({
            "name": name,
            "status": status,
            "required": is_required,
            "blocker_reason": blocker_reason,
        })

    if blockers:
        overall = "evidence_blocker"
    elif all(c["status"] in (STATUS_PRESENT, STATUS_NOT_REQUIRED) for c in components):
        overall = "complete"
    else:
        overall = "partial"

    return {
        "overall": overall,
        "components": components,
        "blockers": blockers,
        "promotion_blocked": bool(blockers),
        "authority": "evidence_blockers_override_advisory_scores",
    }


def _capability_flags(process: ProcessCatalogEntry, evidence_health: Mapping[str, Any]) -> Dict[str, Any]:
    promotion_process = process.preset == PRESET_PROMOTION
    blockers = []
    if not promotion_process:
        blockers.append("advisory_process_only")
    blockers.extend([
        "requires_frozen_snapshot",
        "requires_hard_gates",
        "requires_human_approval",
    ])
    if evidence_health.get("overall") != "complete":
        blockers.append("requires_complete_evidence_health")
    return {
        "can_promote": False,
        "can_export": False,
        "can_live": False,
        "research_execution_allowed": not promotion_process,
        "full_period_research_allowed": not promotion_process,
        "condition_generation_allowed": not promotion_process,
        "condition_improvement_allowed": not promotion_process,
        "promotion_review_allowed": promotion_process,
        "promotion_requirements": {
            "frozen_snapshot_required": promotion_process,
            "evidence_health_required": promotion_process,
            "hard_gates_required": promotion_process,
            "human_approval_required": promotion_process,
        },
        "blockers": blockers,
        "authority": "advisory_until_frozen_review_evidence_hard_gates_and_human_approval",
    }


def effective_condition_discovery_runtime_config(config: Any) -> Any:
    """Return a config clone with condition-discovery hard policy applied.

    The original configured values are retained as ad-hoc attributes for
    status/page-data projection. This keeps one runtime policy for scoring,
    backtest windows, hypotheses, OOS mode, and dashboard hard-gate display.
    """

    effective = replace(config) if is_dataclass(config) else copy.copy(config)
    projection = resolve_condition_discovery_process_projection(
        getattr(config, "condition_discovery_process", None),
        getattr(config, "condition_discovery_preset", PRESET_FAST),
    )
    preset = projection["preset"]
    setattr(effective, "condition_discovery_process", projection["process"])
    setattr(effective, "condition_discovery_preset", preset)
    policy = preset_policy(preset)

    configured_mdd = max(0.0, float(getattr(config, "mdd_cap", policy.staged_mdd_cap) or 0.0))
    effective_mdd = min(configured_mdd, policy.staged_mdd_cap)
    setattr(effective, "condition_discovery_configured_mdd_cap", configured_mdd)
    setattr(effective, "condition_discovery_effective_mdd_cap", effective_mdd)
    setattr(effective, "mdd_cap", effective_mdd)

    configured_min_daily = float(getattr(config, "min_daily_trades", 0.0) or 0.0)
    effective_min_daily = max(configured_min_daily, policy.min_daily_trades)
    setattr(effective, "condition_discovery_configured_min_daily_trades", configured_min_daily)
    setattr(effective, "condition_discovery_effective_min_daily_trades", effective_min_daily)
    setattr(effective, "min_daily_trades", effective_min_daily)

    # Preset OOS semantics are advisory/promotion gates, never live/export wiring.
    setattr(effective, "research_oos_mode", policy.oos_mode)

    timeframe = str(getattr(config, "bt_timeframe", TIMEFRAME_MIN) or TIMEFRAME_MIN).lower()
    setattr(
        effective,
        "bt_universe_start_time",
        TICK_RESEARCH_START if timeframe == TIMEFRAME_TICK else MIN_FULL_SESSION_START,
    )
    if timeframe == TIMEFRAME_TICK:
        setattr(effective, "bt_universe_end_time", TICK_RESEARCH_END)
    elif preset in (PRESET_RESEARCH, PRESET_PROMOTION):
        setattr(effective, "full_session_enabled", True)
        end_time = _coerce_time(
            getattr(config, "bt_min_universe_end_time", MIN_FULL_SESSION_END_CANDIDATES[-1]),
            MIN_FULL_SESSION_END_CANDIDATES[-1],
        )
        setattr(effective, "bt_min_universe_end_time", end_time)
        setattr(effective, "bt_universe_end_time", end_time)

    return effective


def resolve_condition_discovery_policy(
    config: Any,
    *,
    evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the additive condition-discovery payload for status/page_data."""

    projection = resolve_condition_discovery_process_projection(
        getattr(config, "condition_discovery_process", None),
        getattr(config, "condition_discovery_preset", PRESET_FAST),
    )
    preset = projection["preset"]
    process = process_entry_for_selector(projection["process"])
    policy = preset_policy(preset).to_dict(
        configured_mdd_cap=getattr(config, "condition_discovery_configured_mdd_cap", getattr(config, "mdd_cap", None))
    )
    evidence_health = build_evidence_health(evidence, preset=preset)
    return {
        "schema_version": 1,
        "status": "ok",
        "preset": preset,
        "policy": policy,
        "time_window": resolve_time_window_policy(config),
        "hard_gates": {
            "mdd": {
                "cap": policy["effective_mdd_cap"],
                "preset_cap": policy["staged_mdd_cap"],
                "configured_cap": policy["configured_mdd_cap"],
                "authority": "hard_gate",
            },
            "minimum_daily_trades": {
                "value": policy["min_daily_trades"],
                "authority": "hard_gate_or_existing_frequency_gate",
            },
            "evidence": {
                "required": policy["required_evidence"],
                "authority": "promotion_blocker",
            },
        },
        "evidence_health": evidence_health,
        "process_catalog": [entry.to_dict() for entry in PROCESS_CATALOG],
        "current_process": process.to_dict(),
        "process": process.to_dict(),
        "capabilities": _capability_flags(process, evidence_health),
        "authority": {
            "performance_score_100": "advisory_only",
            "condition_quality_score_100": "advisory_only",
            "promotion": "requires_hard_gates_complete_evidence_and_human_approval",
            "export_live_db": "out_of_scope_without_explicit_approval",
        },
    }


def merge_condition_discovery_page_data(
    page_data: Optional[Mapping[str, Any]],
    config: Any,
    *,
    evidence: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return page_data plus the condition_discovery section, preserving peers."""

    merged = dict(page_data or {})
    merged["condition_discovery"] = resolve_condition_discovery_policy(config, evidence=evidence)
    return merged


__all__ = [
    "EVIDENCE_COMPONENTS",
    "PRESET_FAST",
    "PRESET_PROMOTION",
    "PRESET_RESEARCH",
    "VALID_PRESETS",
    "PROCESS_CATALOG",
    "PROCESS_FAST_DISCOVERY",
    "PROCESS_PROMOTION_REVIEW",
    "PROCESS_RESEARCH",
    "effective_condition_discovery_runtime_config",
    "build_evidence_health",
    "merge_condition_discovery_page_data",
    "normalize_condition_discovery_preset",
    "normalize_condition_discovery_process",
    "process_entry_for_preset",
    "process_entry_for_selector",
    "preset_policy",
    "resolve_condition_discovery_process_projection",
    "resolve_condition_discovery_policy",
    "resolve_time_window_policy",
]
