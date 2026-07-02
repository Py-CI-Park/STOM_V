"""Condition-discovery preset, gate, and evidence policy helpers.

The helpers compute JSON-safe policy payloads and the matching runtime-safe
configuration overlay used by the loop. They never touch live/export paths or
grant winner/promotion authority; hard gates remain evidence-bound.
"""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass, replace
from typing import Any, Dict, Mapping, Optional
import copy
import hashlib
import json
import math

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
RESEARCH_LOOP_SCHEMA_VERSION = 1
LANE_REPAIR = "repair"
LANE_DISCOVERY = "discovery"
RESEARCH_LANES = (LANE_REPAIR, LANE_DISCOVERY)
VALIDATION_SCOPE_RESEARCH_ONLY = "research_only"
VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT = "fresh_frozen_holdout"

DEFAULT_TOTAL_SLOTS = 4
DEFAULT_REPAIR_SLOTS = 2
DEFAULT_DISCOVERY_SLOTS = 2
MIN_SLOTS_PER_LANE = 1
MAX_SLOT_SHIFT = 1

LANE_ADVANTAGE_THRESHOLD_POINTS = 5.0
PROFIT_TIE_EPSILON_PCT = 0.02
MDD_TIE_EPSILON_PP = 2.0
INSIGHT_TIE_EPSILON_POINTS = 10
RESEARCH_ANALYSIS_CARD_VERSION = "analysis_card_v2"

HARD_BLOCKER_SCORE = -10000.0
NO_METRICS_SCORE = -9000.0
SEVERE_MDD_VETO_SCORE = -5000.0
CAPPED_ADVANTAGE_MAX_SCORE = 0.0

PROFIT_POINTS_MIN = -100.0
PROFIT_POINTS_MAX = 100.0

MDD_DELTA_PENALTY_PER_PP = 2.0
MDD_CAP_EXCESS_PENALTY_PER_PP = 4.0
SEVERE_MDD_CAP_MULTIPLIER = 1.25
SEVERE_MDD_DELTA_PP = 10.0
MDD_ADVANTAGE_CAP_DELTA_PP = 5.0

OOS_PENALTIES = {
    "pass": 0.0,
    "passed": 0.0,
    "consistent": 0.0,
    "none": 0.0,
    "not_run": 10.0,
    "unknown": 10.0,
    "mixed": 20.0,
    "fail": 40.0,
    "failed": 40.0,
    "regression": 40.0,
}

PROMPT_MATURITY_POINTS_MIN = -15.0
PROMPT_MATURITY_POINTS_MAX = 10.0



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
    # 승격 슬리피지 hard gate가 참조할 프로파일 키(예: 'tick2'). 빈 문자열이면
    # 게이트 미설정. 기본 ''이라 기존 프리셋 정의/동작은 키 추가 외 불변(하위호환).
    # 판정 자체는 evaluate_slippage_gate 순수 함수에서만 수행한다(흐름 미배선).
    slippage_gate_profile: str = ""

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
            "slippage_gate_profile": self.slippage_gate_profile,
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
        # 승격 검토는 tick2 프로파일 손익>0을 hard gate 요건으로 선언한다.
        # (판정 함수만 제공 — 승격 레인은 zero-generation이라 흐름 배선 없음.)
        slippage_gate_profile="tick2",
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


def evaluate_slippage_gate(
    preset: Any,
    slippage_profiles: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """승격 슬리피지 hard gate 판정(순수 함수 — 기존 승격/생성 흐름에는 배선하지 않는다).

    프리셋의 slippage_gate_profile(예: promotion='tick2')이 설정된 경우
    해당 프로파일의 total_profit > 0 이어야 통과한다. evidence 부재·프로파일
    누락·비유한수 값은 hard gate 원칙대로 통과 실패로 처리한다(추측 금지).
    게이트 미설정 프리셋은 enabled=False, passed=None(판정 없음)을 돌려준다.

    slippage_profiles는 fitness/slippage_profiles.compute_slippage_profiles
    결과 dict(내부 "profiles" 컨테이너) 또는 프로파일 매핑 자체를 받는다.
    """
    policy = preset_policy(preset)
    gate_profile = policy.slippage_gate_profile
    verdict: Dict[str, Any] = {
        "schema_version": 1,
        "preset": policy.preset,
        "gate_profile": gate_profile,
        "enabled": bool(gate_profile),
        "passed": None,
        "reason": "slippage_gate_not_configured",
        "profile_total_profit": None,
    }
    if not gate_profile:
        return verdict
    if not isinstance(slippage_profiles, Mapping) or not slippage_profiles:
        return {**verdict, "passed": False, "reason": "slippage_profiles_missing"}
    container = slippage_profiles.get("profiles")
    if not isinstance(container, Mapping):
        container = slippage_profiles
    entry = container.get(gate_profile)
    if not isinstance(entry, Mapping):
        return {**verdict, "passed": False, "reason": "slippage_gate_profile_missing"}
    try:
        total = float(entry.get("total_profit"))
    except (TypeError, ValueError):
        total = float("nan")
    if not math.isfinite(total):
        return {**verdict, "passed": False, "reason": "slippage_profile_total_profit_invalid"}
    passed = total > 0.0
    return {
        **verdict,
        "passed": passed,
        "reason": (
            "slippage_profile_profit_positive"
            if passed
            else "slippage_profile_profit_not_positive"
        ),
        "profile_total_profit": total,
    }


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


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(max(float(value), lo), hi)


def _float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _int_score(value: Any, default: int = 0) -> int:
    number = _float_or_none(value)
    if number is None:
        return int(default)
    return int(round(_clamp(number, 0.0, 100.0)))


def _score_band(score: int) -> str:
    if score >= 85:
        return "85_100"
    if score >= 70:
        return "70_84"
    if score >= 50:
        return "50_69"
    if score >= 30:
        return "30_49"
    return "0_29"


def _evidence_is_complete(value: Any) -> bool:
    if isinstance(value, Mapping):
        return value.get("overall") == "complete"
    return bool(value)


def build_validation_provenance(
    *,
    used_for_prompt_or_allocation: bool,
    frozen: bool,
    fresh_holdout: bool,
    evidence_health: Optional[Mapping[str, Any]] = None,
    artifact_ids: Optional[list[str]] = None,
    scope: Optional[str] = None,
) -> Dict[str, Any]:
    """Describe whether validation can ever support promotion.

    Research-fed validation is intentionally useful for learning but becomes
    promotion-ineligible. This helper is JSON-safe and carries no runtime side
    effects or promotion authority.
    """

    blockers: list[str] = []
    evidence_payload = evidence_health if evidence_health is not None else {"overall": "missing"}
    evidence_complete = _evidence_is_complete(evidence_payload)
    if used_for_prompt_or_allocation:
        resolved_scope = VALIDATION_SCOPE_RESEARCH_ONLY
        blockers.append("validation_used_for_research_learning")
    else:
        resolved_scope = scope or (
            VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT
            if frozen and fresh_holdout
            else VALIDATION_SCOPE_RESEARCH_ONLY
        )
    if not frozen:
        blockers.append("validation_not_frozen")
    if not fresh_holdout:
        blockers.append("validation_not_fresh_holdout")
    if not evidence_complete:
        blockers.append("validation_evidence_incomplete")
    promotion_eligible = (
        not used_for_prompt_or_allocation
        and resolved_scope == VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT
        and frozen
        and fresh_holdout
        and evidence_complete
    )
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "scope": resolved_scope,
        "used_for_prompt_or_allocation": bool(used_for_prompt_or_allocation),
        "frozen": bool(frozen),
        "fresh_holdout": bool(fresh_holdout),
        "evidence_health": dict(evidence_payload),
        "promotion_eligible": bool(promotion_eligible),
        "promotion_blockers": blockers,
        "artifact_ids": list(artifact_ids or []),
        "authority": "validation_provenance_blocks_contaminated_promotion",
    }


def validation_promotion_blockers(provenance: Mapping[str, Any]) -> Dict[str, Any]:
    """Return promotion blockers from a validation provenance payload."""

    blockers = list(provenance.get("promotion_blockers") or [])
    if provenance.get("scope") == VALIDATION_SCOPE_RESEARCH_ONLY:
        blockers.append("validation_scope_research_only")
    if provenance.get("used_for_prompt_or_allocation"):
        blockers.append("validation_used_for_research_learning")
    if provenance.get("frozen") is not True:
        blockers.append("validation_not_frozen")
    if provenance.get("fresh_holdout") is not True:
        blockers.append("validation_not_fresh_holdout")
    evidence_health = provenance.get("evidence_health")
    if not isinstance(evidence_health, Mapping) or evidence_health.get("overall") != "complete":
        blockers.append("validation_evidence_incomplete")
    deduped = list(dict.fromkeys(blockers))
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "blocked": bool(deduped),
        "blockers": deduped,
        "promotion_eligible": not deduped and provenance.get("promotion_eligible") is True,
        "authority": "fresh_frozen_holdout_required_for_promotion",
    }


def build_insight_score(analysis: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build an actionability score for research analysis cards, not promotion."""

    data = analysis or {}
    evidence = _int_score(data.get("evidence_completeness"), 20 if data.get("metrics") else 0)
    root = _int_score(data.get("root_cause_specificity"), 25 if data.get("root_cause") or data.get("root_cause_decomposition") else 0)
    segment = _int_score(data.get("segment_contribution_quality"), 20 if data.get("segment_contribution") or data.get("segment_notes") else 0)
    parent = _int_score(data.get("parent_comparison_quality"), 15 if data.get("parent_comparison") else 0)
    action = _int_score(data.get("next_actionability"), 20 if data.get("next_recommendation") or data.get("next_action") else 0)
    score = min(evidence, 20) + min(root, 25) + min(segment, 20) + min(parent, 15) + min(action, 20)
    caps: list[dict[str, Any]] = []

    metrics = data.get("metrics") or {}
    if not isinstance(metrics, Mapping) or _float_or_none(metrics.get("profit")) is None or _float_or_none(metrics.get("mdd")) is None:
        caps.append({"cap": 20, "reason": "no_official_metrics"})
    evidence_health = data.get("evidence_health")
    if isinstance(evidence_health, Mapping) and evidence_health.get("overall") != "complete":
        caps.append({"cap": 40, "reason": "missing_required_research_evidence"})
    if not data.get("next_recommendation") and not data.get("next_action"):
        caps.append({"cap": 50, "reason": "missing_next_recommendation"})
    if not data.get("segment_contribution") and not data.get("segment_notes"):
        caps.append({"cap": 65, "reason": "no_segment_contribution"})
    if data.get("lane") == LANE_REPAIR and not data.get("parent_comparison"):
        caps.append({"cap": 60, "reason": "no_repair_parent_comparison"})
    if data.get("promotion_claim") is True:
        caps.append({"cap": 30, "reason": "promotion_claim_contradiction"})

    for cap in caps:
        score = min(score, int(cap["cap"]))
    score = _int_score(score)
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "score": score,
        "band": _score_band(score),
        "components": {
            "evidence_completeness": min(evidence, 20),
            "root_cause_specificity": min(root, 25),
            "segment_contribution_quality": min(segment, 20),
            "parent_comparison_quality": min(parent, 15),
            "next_actionability": min(action, 20),
        },
        "caps_applied": caps,
        "action": (
            "strong_input" if score >= 85
            else "actionable_input" if score >= 70
            else "cautious_repair" if score >= 50
            else "analysis_repair" if score >= 30
            else "discard_or_manual_review"
        ),
        "authority": "research_actionability_only",
    }


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True)
        return value
    except (TypeError, ValueError):
        return str(value)

def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_RESEARCH_ONLY_FALSE_FLAGS = frozenset({
    "can_promote",
    "can_export",
    "can_live",
    "can_final_promote",
    "promotion_eligible",
    "promotion_claim",
    "export_eligible",
    "live_eligible",
    "final_promotion",
    "production_ready",
})
_RESEARCH_ONLY_TRUE_FLAGS = frozenset({
    "research_only",
    "promotion_review_requires_fresh_frozen_holdout",
})
_PROHIBITED_RESEARCH_AUTHORITY_KEYS = _RESEARCH_ONLY_FALSE_FLAGS


def _condition_source_record(
    *,
    condition_id: Optional[str],
    code: str,
    sha256: Optional[str] = None,
) -> Dict[str, Any]:
    computed = _sha256_text(code) if code else ""
    if code and sha256 and sha256 != computed:
        raise ValueError("parent_condition_hash_mismatch")
    return {
        "id": condition_id or "",
        "code": code,
        "sha256": computed or (sha256 or ""),
        "characters": len(code),
        "present": bool(code.strip()),
    }


def _authority_smuggling_paths(value: Any, path: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            nested_path = f"{path}.{key_text}" if path else key_text
            if key_text in _PROHIBITED_RESEARCH_AUTHORITY_KEYS and bool(nested):
                paths.append(nested_path)
            paths.extend(_authority_smuggling_paths(nested, nested_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            paths.extend(_authority_smuggling_paths(nested, f"{path}[{index}]"))
    return paths

def _research_only_flags(overrides: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    source = dict(overrides or {})
    blocked = _authority_smuggling_paths(source)
    for key in _RESEARCH_ONLY_TRUE_FLAGS:
        if key in source and source.get(key) is not True:
            blocked.append(key)
    if blocked:
        raise ValueError("research_authority_smuggling: " + ",".join(sorted(set(blocked))))
    flags = {
        "research_only": True,
        "can_promote": False,
        "can_export": False,
        "can_live": False,
        "can_final_promote": False,
        "promotion_review_requires_fresh_frozen_holdout": True,
    }
    for key, value in source.items():
        if key not in _RESEARCH_ONLY_FALSE_FLAGS and key not in _RESEARCH_ONLY_TRUE_FLAGS:
            flags[key] = value
    return flags

def build_research_analysis_card(
    *,
    analysis_id: str,
    candidate_id: str,
    lane: str,
    metrics: Mapping[str, Any],
    parent_id: Optional[str] = None,
    round_id: Optional[str] = None,
    slot_id: Optional[str] = None,
    context_pack_id: Optional[str] = None,
    parent_comparison: Optional[Mapping[str, Any]] = None,
    root_cause: Optional[Mapping[str, Any] | str] = None,
    segment_contribution: Optional[Mapping[str, Any] | list[Any]] = None,
    next_recommendation: Optional[str] = None,
    evidence_health: Optional[Mapping[str, Any]] = None,
    validation_provenance: Optional[Mapping[str, Any]] = None,
    prompt_receipt: Optional[Mapping[str, Any]] = None,
    safety_flags: Optional[Mapping[str, Any]] = None,
    parent_buy_id: Optional[str] = None,
    parent_buy_code: str = "",
    parent_buy_sha256: Optional[str] = None,
    parent_sell_id: Optional[str] = None,
    parent_sell_code: str = "",
    parent_sell_sha256: Optional[str] = None,
    daily_rows_summary: Optional[Any] = None,
    regime_summaries: Optional[Mapping[str, Any]] = None,
    segment_heatmap: Optional[Any] = None,
    feature_importance: Optional[Any] = None,
    edge_ratio: Optional[Mapping[str, Any]] = None,
    mfe_mae: Optional[Mapping[str, Any]] = None,
    correlation_redundancy: Optional[Any] = None,
    avoid_zones: Optional[Any] = None,
    prefer_zones: Optional[Any] = None,
    mutation_axis: Optional[str] = None,
    expected_effect: Optional[str] = None,
    risk_note: Optional[str] = None,
    research_authority_flags: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a JSON-safe research Analysis Card v2."""

    model_visible_card_inputs = {
        "metrics": metrics,
        "parent_comparison": parent_comparison or {},
        "root_cause": root_cause or {},
        "segment_contribution": segment_contribution or {},
        "evidence_health": evidence_health or {},
        "validation_provenance": validation_provenance or {},
        "prompt_receipt": prompt_receipt or {},
        "daily_rows_summary": daily_rows_summary or {},
        "regime_summaries": regime_summaries or {},
        "segment_heatmap": segment_heatmap or {},
        "feature_importance": feature_importance or {},
        "edge_ratio": edge_ratio or {},
        "mfe_mae": mfe_mae or {},
        "correlation_redundancy": correlation_redundancy or {},
        "avoid_zones": avoid_zones or [],
        "prefer_zones": prefer_zones or [],
        "research_authority_flags": research_authority_flags or {},
        "safety_flags": safety_flags or {},
    }
    blocked_authority_paths = _authority_smuggling_paths(model_visible_card_inputs)
    if blocked_authority_paths:
        raise ValueError("research_authority_smuggling: " + ",".join(sorted(set(blocked_authority_paths))))
    parent_conditions = {
        "buy": _condition_source_record(
            condition_id=parent_buy_id or parent_id,
            code=parent_buy_code,
            sha256=parent_buy_sha256,
        ),
        "sell": _condition_source_record(
            condition_id=parent_sell_id,
            code=parent_sell_code,
            sha256=parent_sell_sha256,
        ),
    }
    authority_flags = _research_only_flags(research_authority_flags)
    safe_safety_flags = _research_only_flags(safety_flags)
    card = {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "analysis_card_version": RESEARCH_ANALYSIS_CARD_VERSION,
        "analysis_id": analysis_id,
        "candidate_id": candidate_id,
        "context_pack_id": context_pack_id or "",
        "parent_id": parent_id,
        "lane": lane,
        "round_id": round_id,
        "slot_id": slot_id,
        "metrics": dict(metrics),
        "official_metrics": dict(metrics),
        "parent_conditions": parent_conditions,
        "parent_comparison": dict(parent_comparison or {}),
        "root_cause": root_cause,
        "segment_contribution": segment_contribution,
        "analysis_inputs": {
            "daily_rows_summary": _json_safe(daily_rows_summary or {}),
            "regime_summaries": dict(regime_summaries or {}),
            "segment_heatmap": _json_safe(segment_heatmap or {}),
            "feature_importance": _json_safe(feature_importance or {}),
            "edge_ratio": dict(edge_ratio or {}),
            "mfe_mae": dict(mfe_mae or {}),
            "correlation_redundancy": _json_safe(correlation_redundancy or {}),
            "avoid_zones": _json_safe(avoid_zones or []),
            "prefer_zones": _json_safe(prefer_zones or []),
        },
        "mutation_contract": {
            "mutation_axis": mutation_axis or "",
            "expected_effect": expected_effect or "",
            "risk_note": risk_note or "",
            "single_axis_required": lane == LANE_REPAIR,
            "discovery_requires_novel_coverage_family_or_segment": lane == LANE_DISCOVERY,
        },
        "next_recommendation": next_recommendation or "",
        "evidence_health": dict(evidence_health or build_evidence_health(None, preset=PRESET_RESEARCH)),
        "validation_provenance": dict(validation_provenance or {}),
        "prompt_receipt": dict(prompt_receipt or {}),
        "safety_flags": safe_safety_flags,
        "research_authority_flags": authority_flags,
        "authority": "research_analysis_card_only",
    }
    card["insight_score"] = build_insight_score(card)
    return card


def _coverage_keys(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        value = value.get("coverage_bucket_keys")
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    try:
        return {str(item) for item in value if str(item)}
    except TypeError:
        return {str(value)}


def assess_discovery_novelty(
    candidate: Mapping[str, Any],
    comparators: Optional[list[Mapping[str, Any]]],
    evidence: Optional[Mapping[str, Any]] = None,
    *,
    preset: Any = PRESET_RESEARCH,
) -> Dict[str, Any]:
    """Assess deterministic novelty for discovery credit."""

    comparator_items = list(comparators or [])
    candidate_fingerprint = str(candidate.get("structural_fingerprint") or candidate.get("fingerprint") or "")
    comparator_fingerprints = {
        str(item.get("structural_fingerprint") or item.get("fingerprint") or "")
        for item in comparator_items
        if item.get("structural_fingerprint") or item.get("fingerprint")
    }
    candidate_coverage = _coverage_keys(candidate.get("coverage_bucket_keys") or candidate.get("coverage"))
    comparator_coverage = set().union(*[_coverage_keys(item.get("coverage_bucket_keys") or item.get("coverage")) for item in comparator_items]) if comparator_items else set()
    candidate_family = str(candidate.get("entry_exit_family") or candidate.get("family") or "")
    comparator_families = {
        str(item.get("entry_exit_family") or item.get("family") or "")
        for item in comparator_items
        if item.get("entry_exit_family") or item.get("family")
    }
    evidence_health = build_evidence_health(
        evidence if evidence is not None else candidate.get("evidence"),
        preset=preset,
    )

    structural_ok = bool(candidate_fingerprint) and candidate_fingerprint not in comparator_fingerprints
    coverage_ok = bool(candidate_coverage) and (not comparator_coverage or not candidate_coverage.issubset(comparator_coverage))
    family_ok = bool(candidate_family) and candidate_family not in comparator_families
    evidence_ok = evidence_health["overall"] == "complete"
    dimensions = {
        "structural_fingerprint": structural_ok,
        "coverage_regime": coverage_ok,
        "entry_exit_family": family_ok,
        "complete_research_evidence": evidence_ok,
    }
    failed = [name for name, ok in dimensions.items() if not ok]
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "candidate_id": candidate.get("candidate_id"),
        "lane": LANE_DISCOVERY,
        "comparator_ids": [item.get("candidate_id") for item in comparator_items if item.get("candidate_id")],
        "fingerprint_source": {
            "source_type": "candidate_structural_fingerprint",
            "source_id": candidate.get("candidate_id"),
            "normalization_version": "v1",
        },
        "dimensions": dimensions,
        "coverage_bucket_keys": sorted(candidate_coverage),
        "entry_exit_family": candidate_family,
        "entry_exit_family_taxonomy_version": "v1",
        "evidence_health": evidence_health,
        "passes_discovery_credit": not failed,
        "failed_dimensions": failed,
        "authority": "research_discovery_credit_only",
    }


def _candidate_metric(candidate: Mapping[str, Any], name: str) -> Optional[float]:
    metrics = candidate.get("metrics") or {}
    if isinstance(metrics, Mapping) and name in metrics:
        return _float_or_none(metrics.get(name))
    return _float_or_none(candidate.get(name))


def _prompt_points(score: Any) -> float:
    number = _float_or_none(score)
    if number is None:
        return -10.0
    if number >= 85:
        return 5.0
    if number >= 70:
        return 3.0
    if number >= 50:
        return 0.0
    if number >= 30:
        return -5.0
    return -10.0


def _insight_points(score: Any) -> float:
    number = _float_or_none(score)
    if number is None:
        return -10.0
    if number >= 85:
        return 10.0
    if number >= 70:
        return 6.0
    if number >= 50:
        return 2.0
    if number >= 30:
        return -5.0
    return -10.0


def _downstream_points(result: Any) -> float:
    normalized = str(result or "neutral").strip().lower()
    if normalized == "improved":
        return 5.0
    if normalized in {"degraded"}:
        return -5.0
    if normalized in {"rejected", "invalid"}:
        return -10.0
    return 0.0


def _candidate_evidence_health(candidate: Mapping[str, Any], preset: Any) -> Dict[str, Any]:
    health = candidate.get("evidence_health")
    if isinstance(health, Mapping):
        return dict(health)
    return build_evidence_health(candidate.get("evidence"), preset=preset)


def _candidate_provenance_blockers(candidate: Mapping[str, Any]) -> list[str]:
    if not (
        "validation_provenance" in candidate
        or candidate.get("validation_provenance_required")
        or candidate.get("validation")
    ):
        return []
    provenance = candidate.get("validation_provenance")
    if not isinstance(provenance, Mapping):
        return ["missing_validation_provenance"]
    if provenance.get("used_for_prompt_or_allocation") and provenance.get("promotion_eligible"):
        return ["invalid_validation_provenance"]
    return []


def _score_research_candidate(
    candidate: Mapping[str, Any],
    *,
    preset: Any,
    effective_mdd_cap: float,
) -> Dict[str, Any]:
    lane = str(candidate.get("lane") or LANE_REPAIR)
    evidence_health = _candidate_evidence_health(candidate, preset)
    blockers = list(evidence_health.get("blockers") or [])
    if evidence_health.get("overall") != "complete":
        blockers.insert(0, "missing_or_invalid_required_evidence")
    blockers.extend(_candidate_provenance_blockers(candidate))

    profit = _candidate_metric(candidate, "profit")
    mdd = _candidate_metric(candidate, "mdd")
    parent_profit = _float_or_none(candidate.get("parent_profit"))
    parent_mdd = _float_or_none(candidate.get("parent_mdd"))
    parent_metrics = candidate.get("parent_metrics") or {}
    if isinstance(parent_metrics, Mapping):
        parent_profit = parent_profit if parent_profit is not None else _float_or_none(parent_metrics.get("profit"))
        parent_mdd = parent_mdd if parent_mdd is not None else _float_or_none(parent_metrics.get("mdd"))
    parent_profit = parent_profit if parent_profit is not None else 0.0
    parent_mdd = parent_mdd if parent_mdd is not None else 0.0

    if profit is None or mdd is None:
        blockers.append("no_official_metrics")
        return {
            "candidate_id": candidate.get("candidate_id"),
            "eligible_for_lane_advantage": False,
            "candidate_score": NO_METRICS_SCORE,
            "raw_score": NO_METRICS_SCORE,
            "profit_delta": None,
            "profit_delta_pct": None,
            "profit_delta_points": None,
            "mdd_delta_pp": None,
            "mdd_penalty": None,
            "oos_advisory_penalty": None,
            "insight_score": candidate.get("insight_score"),
            "insight_score_points": None,
            "prompt_score": candidate.get("prompt_score"),
            "prompt_maturity_points": None,
            "blockers": list(dict.fromkeys(blockers)),
            "caps_applied": [],
            "failure_reason": "no_official_metrics",
        }

    if blockers:
        return {
            "candidate_id": candidate.get("candidate_id"),
            "eligible_for_lane_advantage": False,
            "candidate_score": HARD_BLOCKER_SCORE,
            "raw_score": HARD_BLOCKER_SCORE,
            "profit_delta": profit - parent_profit,
            "profit_delta_pct": (profit - parent_profit) / max(abs(parent_profit), 1.0),
            "profit_delta_points": None,
            "mdd_delta_pp": mdd - parent_mdd,
            "mdd_penalty": None,
            "oos_advisory_penalty": None,
            "insight_score": candidate.get("insight_score"),
            "insight_score_points": None,
            "prompt_score": candidate.get("prompt_score"),
            "prompt_maturity_points": None,
            "blockers": list(dict.fromkeys(blockers)),
            "caps_applied": [],
            "failure_reason": "missing_or_invalid_required_evidence",
        }

    profit_delta = profit - parent_profit
    profit_delta_pct = profit_delta / max(abs(parent_profit), 1.0)
    profit_delta_points = _clamp(profit_delta_pct * 100.0, PROFIT_POINTS_MIN, PROFIT_POINTS_MAX)
    mdd_delta_pp = mdd - parent_mdd
    severe_blockers = []
    if mdd >= effective_mdd_cap * SEVERE_MDD_CAP_MULTIPLIER:
        severe_blockers.append("severe_mdd_veto_cap_multiplier")
    if mdd_delta_pp >= SEVERE_MDD_DELTA_PP:
        severe_blockers.append("severe_mdd_veto_delta")
    if severe_blockers:
        return {
            "candidate_id": candidate.get("candidate_id"),
            "eligible_for_lane_advantage": False,
            "candidate_score": SEVERE_MDD_VETO_SCORE,
            "raw_score": SEVERE_MDD_VETO_SCORE,
            "profit_delta": profit_delta,
            "profit_delta_pct": profit_delta_pct,
            "profit_delta_points": profit_delta_points,
            "mdd_delta_pp": mdd_delta_pp,
            "mdd_penalty": None,
            "oos_advisory_penalty": None,
            "insight_score": candidate.get("insight_score"),
            "insight_score_points": None,
            "prompt_score": candidate.get("prompt_score"),
            "prompt_maturity_points": None,
            "blockers": severe_blockers,
            "caps_applied": [],
            "failure_reason": "severe_mdd_veto",
        }

    mdd_penalty = max(0.0, mdd_delta_pp) * MDD_DELTA_PENALTY_PER_PP
    mdd_penalty += max(0.0, mdd - effective_mdd_cap) * MDD_CAP_EXCESS_PENALTY_PER_PP
    oos_status = str(candidate.get("oos_status") or candidate.get("oos") or "none").strip().lower()
    oos_penalty = OOS_PENALTIES.get(oos_status, OOS_PENALTIES["unknown"])
    insight_score = candidate.get("insight_score")
    if isinstance(insight_score, Mapping):
        insight_score = insight_score.get("score")
    insight_points = _insight_points(insight_score)
    prompt_score = candidate.get("prompt_score")
    if prompt_score is None:
        receipt = candidate.get("prompt_receipt") or {}
        if isinstance(receipt, Mapping):
            prompt_score = receipt.get("prompt_score")
    prompt_maturity_points = _clamp(
        _prompt_points(prompt_score) + _downstream_points(candidate.get("downstream_result")),
        PROMPT_MATURITY_POINTS_MIN,
        PROMPT_MATURITY_POINTS_MAX,
    )
    raw_score = profit_delta_points - mdd_penalty - oos_penalty + insight_points + prompt_maturity_points
    caps = []
    if mdd > effective_mdd_cap:
        caps.append("mdd_cap_pressure_advantage_capped")
    if mdd_delta_pp >= MDD_ADVANTAGE_CAP_DELTA_PP:
        caps.append("mdd_delta_advantage_capped")
    novelty = candidate.get("discovery_novelty") or candidate.get("novelty")
    if lane == LANE_DISCOVERY and isinstance(novelty, Mapping) and novelty.get("passes_discovery_credit") is not True:
        caps.append("discovery_credit_failed_advantage_capped")
    candidate_score = min(raw_score, CAPPED_ADVANTAGE_MAX_SCORE) if caps else raw_score
    return {
        "candidate_id": candidate.get("candidate_id"),
        "eligible_for_lane_advantage": True,
        "candidate_score": float(candidate_score),
        "raw_score": float(raw_score),
        "profit_delta": float(profit_delta),
        "profit_delta_pct": float(profit_delta_pct),
        "profit_delta_points": float(profit_delta_points),
        "mdd_delta_pp": float(mdd_delta_pp),
        "mdd_penalty": float(mdd_penalty),
        "oos_advisory_penalty": float(oos_penalty),
        "insight_score": insight_score,
        "insight_score_points": float(insight_points),
        "prompt_score": prompt_score,
        "prompt_maturity_points": float(prompt_maturity_points),
        "blockers": [],
        "caps_applied": caps,
        "failure_reason": str(candidate.get("failure_reason") or ""),
    }


def score_research_lane(
    candidates: list[Mapping[str, Any]],
    *,
    preset: Any = PRESET_RESEARCH,
) -> Dict[str, Any]:
    """Score one repair/discovery lane for advisory research-budget steering."""

    normalized_preset = normalize_condition_discovery_preset(preset)
    policy = preset_policy(normalized_preset)
    lane = str(candidates[0].get("lane") if candidates else LANE_REPAIR)
    effective_mdd_cap = float(policy.staged_mdd_cap)
    scored = [
        _score_research_candidate(candidate, preset=normalized_preset, effective_mdd_cap=effective_mdd_cap)
        for candidate in candidates
    ]
    best = max(scored, key=lambda item: item["candidate_score"], default=None)
    eligible_count = sum(1 for item in scored if item["eligible_for_lane_advantage"])
    best = best or {
        "candidate_id": None,
        "eligible_for_lane_advantage": False,
        "candidate_score": HARD_BLOCKER_SCORE,
        "raw_score": HARD_BLOCKER_SCORE,
        "profit_delta": None,
        "profit_delta_pct": None,
        "mdd_delta_pp": None,
        "blockers": ["no_candidates"],
        "caps_applied": [],
    }
    blockers = list(dict.fromkeys(reason for item in scored for reason in item.get("blockers", [])))
    caps = list(dict.fromkeys(reason for item in scored for reason in item.get("caps_applied", [])))
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "lane": lane,
        "preset": normalized_preset,
        "candidate_count": len(candidates),
        "eligible_candidate_count": eligible_count,
        "best_candidate_id": best.get("candidate_id"),
        "lane_score": best.get("candidate_score"),
        "lane_profit_delta": best.get("profit_delta"),
        "lane_profit_delta_pct": best.get("profit_delta_pct"),
        "lane_mdd_delta_pp": best.get("mdd_delta_pp"),
        "effective_mdd_cap": effective_mdd_cap,
        "advantage_capped": bool(best.get("caps_applied")),
        "blockers": blockers,
        "caps_applied": caps,
        "best_candidate_score_detail": best,
        "candidate_scores": scored,
        "authority": "advisory_research_budget_only",
    }


def _valid_slots(slots: Mapping[str, Any]) -> bool:
    repair = int(slots.get(LANE_REPAIR, 0) or 0)
    discovery = int(slots.get(LANE_DISCOVERY, 0) or 0)
    return repair + discovery == DEFAULT_TOTAL_SLOTS and repair >= MIN_SLOTS_PER_LANE and discovery >= MIN_SLOTS_PER_LANE


def _lane_winner(repair: Mapping[str, Any], discovery: Mapping[str, Any]) -> tuple[Optional[str], str, list[str]]:
    tie_breaks: list[str] = []
    repair_eligible = int(repair.get("eligible_candidate_count") or 0)
    discovery_eligible = int(discovery.get("eligible_candidate_count") or 0)
    repair_capped = bool(repair.get("advantage_capped"))
    discovery_capped = bool(discovery.get("advantage_capped"))
    if repair_eligible == 0 and discovery_eligible == 0:
        return None, "no_eligible_lane_keep_default", tie_breaks
    if repair_eligible > 0 and discovery_eligible == 0:
        return (None, "only_eligible_lane_advantage_capped", tie_breaks) if repair_capped else (LANE_REPAIR, "only_repair_eligible", tie_breaks)
    if discovery_eligible > 0 and repair_eligible == 0:
        return (None, "only_eligible_lane_advantage_capped", tie_breaks) if discovery_capped else (LANE_DISCOVERY, "only_discovery_eligible", tie_breaks)
    if repair_capped and discovery_capped:
        return None, "both_lanes_advantage_capped", tie_breaks
    if repair_capped != discovery_capped:
        return (LANE_DISCOVERY, "opposing_lane_advantage_capped", tie_breaks) if repair_capped else (LANE_REPAIR, "opposing_lane_advantage_capped", tie_breaks)

    repair_score = float(repair.get("lane_score") or 0.0)
    discovery_score = float(discovery.get("lane_score") or 0.0)
    diff = repair_score - discovery_score
    if abs(diff) >= LANE_ADVANTAGE_THRESHOLD_POINTS:
        return (LANE_REPAIR if diff > 0 else LANE_DISCOVERY), "lane_score_advantage", tie_breaks

    tie_breaks.append("profit_delta_pct")
    repair_profit = _float_or_none(repair.get("lane_profit_delta_pct")) or 0.0
    discovery_profit = _float_or_none(discovery.get("lane_profit_delta_pct")) or 0.0
    if abs(repair_profit - discovery_profit) >= PROFIT_TIE_EPSILON_PCT:
        return (LANE_REPAIR if repair_profit > discovery_profit else LANE_DISCOVERY), "profit_delta_tiebreak", tie_breaks

    tie_breaks.append("mdd_delta_pp")
    repair_mdd = _float_or_none(repair.get("lane_mdd_delta_pp")) or 0.0
    discovery_mdd = _float_or_none(discovery.get("lane_mdd_delta_pp")) or 0.0
    if abs(repair_mdd - discovery_mdd) >= MDD_TIE_EPSILON_PP:
        return (LANE_REPAIR if repair_mdd < discovery_mdd else LANE_DISCOVERY), "mdd_delta_tiebreak", tie_breaks

    tie_breaks.append("insight_score")
    repair_insight = _float_or_none((repair.get("best_candidate_score_detail") or {}).get("insight_score")) or 0.0
    discovery_insight = _float_or_none((discovery.get("best_candidate_score_detail") or {}).get("insight_score")) or 0.0
    if abs(repair_insight - discovery_insight) >= INSIGHT_TIE_EPSILON_POINTS:
        return (LANE_REPAIR if repair_insight > discovery_insight else LANE_DISCOVERY), "insight_score_tiebreak", tie_breaks
    return None, "no_material_lane_advantage", tie_breaks


def resolve_hybrid_research_slots(previous_round_summary: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Resolve next repair/discovery slot allocation for a 4-slot research round."""

    summary = previous_round_summary or {}
    previous_slots = dict(summary.get("previous_slots_by_lane") or summary.get("slots_by_lane") or {
        LANE_REPAIR: DEFAULT_REPAIR_SLOTS,
        LANE_DISCOVERY: DEFAULT_DISCOVERY_SLOTS,
    })
    if not _valid_slots(previous_slots):
        previous_slots = {LANE_REPAIR: DEFAULT_REPAIR_SLOTS, LANE_DISCOVERY: DEFAULT_DISCOVERY_SLOTS}
    repair = summary.get("repair_lane") or summary.get(LANE_REPAIR) or {}
    discovery = summary.get("discovery_lane") or summary.get(LANE_DISCOVERY) or {}
    better_lane, reason, tie_breaks = _lane_winner(repair, discovery) if repair or discovery else (None, "default_allocation", [])
    slots = {LANE_REPAIR: int(previous_slots[LANE_REPAIR]), LANE_DISCOVERY: int(previous_slots[LANE_DISCOVERY])}
    shift = {"from": None, "to": None, "count": 0}
    if better_lane == LANE_REPAIR and slots[LANE_DISCOVERY] > MIN_SLOTS_PER_LANE:
        slots[LANE_REPAIR] += MAX_SLOT_SHIFT
        slots[LANE_DISCOVERY] -= MAX_SLOT_SHIFT
        shift = {"from": LANE_DISCOVERY, "to": LANE_REPAIR, "count": MAX_SLOT_SHIFT}
    elif better_lane == LANE_DISCOVERY and slots[LANE_REPAIR] > MIN_SLOTS_PER_LANE:
        slots[LANE_DISCOVERY] += MAX_SLOT_SHIFT
        slots[LANE_REPAIR] -= MAX_SLOT_SHIFT
        shift = {"from": LANE_REPAIR, "to": LANE_DISCOVERY, "count": MAX_SLOT_SHIFT}
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "slots_total": DEFAULT_TOTAL_SLOTS,
        "previous_slots_by_lane": previous_slots,
        "slots_by_lane": slots,
        "better_lane": better_lane,
        "shift_applied": shift,
        "decision_reason": reason,
        "repair_lane_score": repair.get("lane_score"),
        "discovery_lane_score": discovery.get("lane_score"),
        "tie_breaks_used": tie_breaks,
        "blockers": [],
        "authority": "research_budget_steering_only",
    }


def build_research_loop_policy() -> Dict[str, Any]:
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "lanes": list(RESEARCH_LANES),
        "default_slots": {LANE_REPAIR: DEFAULT_REPAIR_SLOTS, LANE_DISCOVERY: DEFAULT_DISCOVERY_SLOTS},
        "slots_total": DEFAULT_TOTAL_SLOTS,
        "max_slot_shift": MAX_SLOT_SHIFT,
        "min_slots_per_lane": MIN_SLOTS_PER_LANE,
        "lane_score_constants": {
            "lane_advantage_threshold_points": LANE_ADVANTAGE_THRESHOLD_POINTS,
            "profit_tie_epsilon_pct": PROFIT_TIE_EPSILON_PCT,
            "mdd_tie_epsilon_pp": MDD_TIE_EPSILON_PP,
            "severe_mdd_cap_multiplier": SEVERE_MDD_CAP_MULTIPLIER,
            "severe_mdd_delta_pp": SEVERE_MDD_DELTA_PP,
            "mdd_advantage_cap_delta_pp": MDD_ADVANTAGE_CAP_DELTA_PP,
        },
        "insight_score": {
            "authority": "research_actionability_only",
            "caps": {
                "no_official_metrics": 20,
                "missing_required_research_evidence": 40,
                "missing_next_recommendation": 50,
                "no_segment_contribution": 65,
                "no_repair_parent_comparison": 60,
                "promotion_claim_contradiction": 30,
            },
        },
        "validation_scopes": [VALIDATION_SCOPE_RESEARCH_ONLY, VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT],
        "authority": "research_budget_steering_only",
    }


def build_research_observability_contract(process: ProcessCatalogEntry, evidence_health: Mapping[str, Any]) -> Dict[str, Any]:
    """Describe the research-process artifacts the dashboard/static pages should expose."""

    promotion_process = process.preset == PRESET_PROMOTION
    return {
        "schema_version": RESEARCH_LOOP_SCHEMA_VERSION,
        "mode_authority": {
            "process": process.code,
            "preset": process.preset,
            "generation_allowed": not promotion_process,
            "promotion_review_zero_generation": promotion_process,
            "authority": "research_observability_only",
        },
        "context_pack_health": {
            "status": "required",
            "required_fields": [
                "context_pack_id",
                "context_pack_sha256",
                "full_stom_sources_included",
                "prompt_budget_estimated_tokens",
                "parent_buy_id",
                "parent_sell_id",
            ],
            "fail_closed_budget_tokens": 250000,
            "evidence_health": evidence_health.get("overall"),
        },
        "branch_tree": [
            {"step": "baseline_official_backtest", "output": "official_metrics"},
            {"step": "analysis_card_v2", "output": "root_cause_segment_contribution"},
            {"step": "multi_hypothesis_candidate_pack", "output": "repair_repair_discovery_branches"},
            {"step": "official_candidate_backtests", "output": "candidate_results"},
            {"step": "research_only_ranking", "output": "advisory_rank_reason"},
        ],
        "candidate_pack": {
            "required_fields": [
                "candidate_pack_id",
                "hypothesis_id",
                "mutation_axis",
                "expected_effect",
                "risk_note",
                "novelty",
            ],
            "min_candidates": 2,
            "recommended_candidates": "2-3+",
            "fallback_source": "diagnostic_deterministic_candidate_fallback",
        },
        "analysis_cards": {
            "schema": RESEARCH_ANALYSIS_CARD_VERSION,
            "required_fields": ["context_pack_id", "root_cause", "segment_contribution", "insight_score"],
        },
        "prompt_receipts": {
            "required_fields": [
                "context_pack_id",
                "candidate_pack_id",
                "candidate_contract_id",
                "strict_response_validation",
                "downstream_result",
                "official_backtest_result",
            ],
            "prompt_maturity_authority": "research_prompt_maturity_only",
        },
        "promotion_blockers": {
            "generation_allowed": False if promotion_process else None,
            "blockers": list(_capability_flags(process, evidence_health)["blockers"]),
            "authority": "promotion_requires_fresh_frozen_holdout_oos_wf_slippage_advisory_and_human_approval",
        },
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
        "research_loop": build_research_loop_policy(),
        "research_observability": build_research_observability_contract(process, evidence_health),
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
    "RESEARCH_ANALYSIS_CARD_VERSION",
    "effective_condition_discovery_runtime_config",
    "build_evidence_health",
    "build_insight_score",
    "build_research_analysis_card",
    "build_research_observability_contract",
    "build_validation_provenance",
    "validation_promotion_blockers",
    "assess_discovery_novelty",
    "merge_condition_discovery_page_data",
    "normalize_condition_discovery_preset",
    "normalize_condition_discovery_process",
    "process_entry_for_preset",
    "process_entry_for_selector",
    "preset_policy",
    "resolve_condition_discovery_process_projection",
    "resolve_condition_discovery_policy",
    "resolve_hybrid_research_slots",
    "score_research_lane",
    "build_research_loop_policy",
    "resolve_time_window_policy",
]
