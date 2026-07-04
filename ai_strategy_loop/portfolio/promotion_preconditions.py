"""승격 전제 판정 순수 모듈 (T5.3) — 연구 레인 전용 advisory 판정기.

동결 후보의 승격 전제(precondition) 5종을 **판정만** 하는 순수 함수 모음이다.
이 모듈은 승격/export/generation 을 절대 실행하지 않는다(zero-generation 계약):

  - 판정 결과가 전부 통과여도 can_promote / can_export / generation_allowed 는
    항상 False 로 고정된다 (controller.condition_discovery 의 promotion-review
    zero-generation 계약과 동일 — 최종 승격은 인간 승인 별도 절차).
  - 결과는 authority='advisory_only' 라벨이 붙은 JSON-safe dict 일 뿐이며,
    게이트/엔진/런타임 어디에도 배선되지 않는다.
  - backtest/graph/ 불가침 — 파일/DB 접근이 전혀 없다.

판정 5종 (전부 fail-closed — 증거 부재/판정 불가 = passed False + 사유):
  1. slippage_gate            : controller.condition_discovery.evaluate_slippage_gate
                                읽기 전용 재사용(promotion 프리셋 tick2 total_profit>0).
  2. oos_walkforward_evidence : oos_status 가 명시적 통과 상태여야 한다.
                                연구 점수(OOS_PENALTIES)에서는 'none'(미실행)이
                                무벌점이지만 승격 전제에서는 증거 부재라 실패다.
  3. fresh_frozen_holdout     : validation_provenance 의 frozen=True,
                                fresh_holdout=True, 연구 재사용(오염) 없음.
  4. measurement_frame_label  : 지표 dict 에 유효한 measurement_frame 라벨 존재
                                (fitness.measurement_frame 정본 read-only 재사용).
  5. evidence_health          : 필수 receipt 5종(csv/trades/equity/prompt/validation)
                                이 promotion 프리셋 기준 전부 present —
                                build_evidence_health 읽기 전용 재사용으로 재계산.

입력 계약 — candidate_evidence(Mapping) 필드(전부 선택; 없으면 해당 체크 실패):
  - slippage_profiles      : fitness.slippage_profiles 결과 dict 또는 프로파일 매핑
  - oos_status (또는 oos)  : OOS/walk-forward 판정 상태 문자열
  - validation_provenance  : build_validation_provenance 페이로드(또는 동일 필드 dict)
  - metrics                : measurement_frame 라벨이 붙은 지표 dict
                             (탑레벨 measurement_frame 필드도 폴백으로 인정)
  - evidence               : {component: status} 원시 receipt 매핑 (우선 재계산 소스)
  - evidence_health        : build_evidence_health 페이로드 (evidence 부재 시
                             components 목록에서 status 를 추출해 재계산)
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from ai_strategy_loop.controller.condition_discovery import (
    EVIDENCE_COMPONENTS,
    OOS_PENALTIES,
    PRESET_PROMOTION,
    VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT,
    VALIDATION_SCOPE_RESEARCH_ONLY,
    build_evidence_health,
    evaluate_slippage_gate,
)
from ai_strategy_loop.fitness.measurement_frame import (
    MEASUREMENT_FRAME_KEY,
    VALID_MEASUREMENT_FRAMES,
    resolve_frame,
)

__all__ = [
    "PROMOTION_PRECONDITIONS_SCHEMA_VERSION",
    "AUTHORITY_ADVISORY_ONLY",
    "CHECK_SLIPPAGE_GATE",
    "CHECK_OOS_WALKFORWARD",
    "CHECK_FRESH_FROZEN_HOLDOUT",
    "CHECK_MEASUREMENT_FRAME",
    "CHECK_EVIDENCE_HEALTH",
    "PRECONDITION_CHECK_NAMES",
    "OOS_PASSING_STATUSES",
    "check_slippage_gate",
    "check_oos_walkforward",
    "check_fresh_frozen_holdout",
    "check_measurement_frame",
    "check_evidence_health",
    "evaluate_promotion_preconditions",
]

PROMOTION_PRECONDITIONS_SCHEMA_VERSION = 1

AUTHORITY_ADVISORY_ONLY = "advisory_only"

CHECK_SLIPPAGE_GATE = "slippage_gate"
CHECK_OOS_WALKFORWARD = "oos_walkforward_evidence"
CHECK_FRESH_FROZEN_HOLDOUT = "fresh_frozen_holdout"
CHECK_MEASUREMENT_FRAME = "measurement_frame_label"
CHECK_EVIDENCE_HEALTH = "evidence_health"
PRECONDITION_CHECK_NAMES = (
    CHECK_SLIPPAGE_GATE,
    CHECK_OOS_WALKFORWARD,
    CHECK_FRESH_FROZEN_HOLDOUT,
    CHECK_MEASUREMENT_FRAME,
    CHECK_EVIDENCE_HEALTH,
)

# OOS/walk-forward 통과로 인정하는 상태 — OOS_PENALTIES 에서 벌점 0 인 상태 중
# 'none'(미실행)은 의도적으로 제외한다. 연구 점수에서는 미실행이 중립이지만,
# 승격 전제에서는 "실행되고 통과한 증거"가 있어야 하므로 부재는 실패다(fail-closed).
OOS_PASSING_STATUSES = ("pass", "passed", "consistent")

# 명시적으로 인식하는 비통과 상태 → 사유 코드 매핑(그 외 문자열은 미인식 실패).
_OOS_FAILING_REASONS = {
    "none": "oos_not_run",
    "not_run": "oos_not_run",
    "unknown": "oos_status_unknown",
    "mixed": "oos_mixed",
    "fail": "oos_failed",
    "failed": "oos_failed",
    "regression": "oos_failed",
}

# 승격 오염 차단 어휘 — controller.condition_discovery 의 blocker 명칭과 동일하게
# 유지한다(소비자가 두 모듈의 사유 코드를 같은 사전으로 해석할 수 있도록).
_BLOCKER_NOT_FROZEN = "validation_not_frozen"
_BLOCKER_NOT_FRESH_HOLDOUT = "validation_not_fresh_holdout"
_BLOCKER_RESEARCH_REUSE = "validation_used_for_research_learning"
_BLOCKER_SCOPE_RESEARCH_ONLY = "validation_scope_research_only"
_BLOCKER_SCOPE_UNRECOGNIZED = "validation_scope_not_fresh_frozen_holdout"


def _check_record(
    name: str,
    passed: bool,
    reason: str,
    detail: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """단일 체크 레코드(JSON-safe)를 만든다. passed 는 항상 엄격한 bool."""
    return {
        "name": name,
        "passed": bool(passed),
        "reason": str(reason),
        "detail": dict(detail or {}),
    }


def _as_mapping(value: Any) -> Dict[str, Any]:
    """Mapping 이 아니면 빈 dict 로 강등한다(fail-closed 입력 정규화, 무예외)."""
    return dict(value) if isinstance(value, Mapping) else {}


# ---------------------------------------------------------------------------
# 체크 1 — 슬리피지 hard gate (tick2 흑자)
# ---------------------------------------------------------------------------

def check_slippage_gate(candidate_evidence: Any) -> Dict[str, Any]:
    """promotion 프리셋 슬리피지 게이트(tick2 total_profit>0) 판정.

    판정 자체는 controller.condition_discovery.evaluate_slippage_gate 순수
    함수를 읽기 전용으로 재사용한다. evidence 부재/프로파일 누락/비유한수는
    원 함수의 fail-closed 사유를 그대로 전파하고, passed 는 verdict.passed 가
    정확히 True 일 때만 True 다(None 포함 그 외 전부 실패).
    """
    evidence = _as_mapping(candidate_evidence)
    profiles = evidence.get("slippage_profiles")
    verdict = evaluate_slippage_gate(
        PRESET_PROMOTION,
        profiles if isinstance(profiles, Mapping) else None,
    )
    passed = verdict.get("passed") is True
    return _check_record(
        CHECK_SLIPPAGE_GATE,
        passed,
        str(verdict.get("reason") or "slippage_gate_verdict_missing"),
        detail=verdict,
    )


# ---------------------------------------------------------------------------
# 체크 2 — OOS/walk-forward 증거
# ---------------------------------------------------------------------------

def check_oos_walkforward(candidate_evidence: Any) -> Dict[str, Any]:
    """OOS/walk-forward 증거 존재+통과 판정 (oos_status, 폴백 oos).

    통과 상태(OOS_PASSING_STATUSES) 외에는 전부 실패다: 부재/빈 문자열은
    'oos_evidence_missing', 미실행('none'/'not_run')·mixed·fail 계열은 각 사유,
    미인식 문자열은 'oos_status_unrecognized'(추측 금지 fail-closed).
    """
    evidence = _as_mapping(candidate_evidence)
    raw = evidence.get("oos_status")
    if raw is None:
        raw = evidence.get("oos")
    status = str(raw).strip().lower() if raw is not None else ""
    detail = {
        "oos_status": status or None,
        "passing_statuses": list(OOS_PASSING_STATUSES),
        "recognized_statuses": sorted(OOS_PENALTIES),
    }
    if not status:
        return _check_record(
            CHECK_OOS_WALKFORWARD, False, "oos_evidence_missing", detail
        )
    if status in OOS_PASSING_STATUSES:
        return _check_record(
            CHECK_OOS_WALKFORWARD, True, "oos_walkforward_passing", detail
        )
    reason = _OOS_FAILING_REASONS.get(status, "oos_status_unrecognized")
    return _check_record(CHECK_OOS_WALKFORWARD, False, reason, detail)


# ---------------------------------------------------------------------------
# 체크 3 — frozen / fresh holdout 검증 계보
# ---------------------------------------------------------------------------

def check_fresh_frozen_holdout(candidate_evidence: Any) -> Dict[str, Any]:
    """validation_provenance 의 동결/신선 holdout·연구 오염 여부 판정.

    build_validation_provenance 페이로드(또는 동일 필드 dict)를 받아
    frozen is True, fresh_holdout is True, used_for_prompt_or_allocation 미해당,
    scope(있다면) == fresh_frozen_holdout 을 전부 요구한다. blocker 명칭은
    controller.condition_discovery 어휘를 그대로 쓴다.
    """
    evidence = _as_mapping(candidate_evidence)
    provenance = evidence.get("validation_provenance")
    if not isinstance(provenance, Mapping) or not provenance:
        return _check_record(
            CHECK_FRESH_FROZEN_HOLDOUT,
            False,
            "validation_provenance_missing",
            {"blockers": ["validation_provenance_missing"]},
        )

    blockers: List[str] = []
    if provenance.get("used_for_prompt_or_allocation") is True:
        blockers.append(_BLOCKER_RESEARCH_REUSE)
    if provenance.get("frozen") is not True:
        blockers.append(_BLOCKER_NOT_FROZEN)
    if provenance.get("fresh_holdout") is not True:
        blockers.append(_BLOCKER_NOT_FRESH_HOLDOUT)
    scope_raw = provenance.get("scope")
    scope = str(scope_raw).strip().lower() if scope_raw is not None else None
    if scope is not None and scope != VALIDATION_SCOPE_FRESH_FROZEN_HOLDOUT:
        blockers.append(
            _BLOCKER_SCOPE_RESEARCH_ONLY
            if scope == VALIDATION_SCOPE_RESEARCH_ONLY
            else _BLOCKER_SCOPE_UNRECOGNIZED
        )

    detail = {
        "frozen": provenance.get("frozen") is True,
        "fresh_holdout": provenance.get("fresh_holdout") is True,
        "used_for_prompt_or_allocation": provenance.get("used_for_prompt_or_allocation") is True,
        "scope": scope,
        "blockers": blockers,
    }
    if blockers:
        return _check_record(CHECK_FRESH_FROZEN_HOLDOUT, False, blockers[0], detail)
    return _check_record(
        CHECK_FRESH_FROZEN_HOLDOUT, True, "fresh_frozen_holdout_confirmed", detail
    )


# ---------------------------------------------------------------------------
# 체크 4 — 측정계 프레임 라벨
# ---------------------------------------------------------------------------

def check_measurement_frame(candidate_evidence: Any) -> Dict[str, Any]:
    """지표 dict 의 measurement_frame 라벨 존재+유효성 판정.

    1순위 metrics dict 의 라벨, 폴백으로 candidate_evidence 탑레벨의
    measurement_frame 필드를 인정한다. 라벨 부재는 'measurement_frame_missing',
    유효 프레임 목록 밖 값은 'measurement_frame_unknown'(fail-closed).
    특정 프레임을 강제하지는 않는다 — 프레임 간 비교 가능성 판정은
    fitness.measurement_frame 의 assert_* 계열 몫이다.
    """
    evidence = _as_mapping(candidate_evidence)
    metrics = evidence.get("metrics")
    frame = None
    source = None
    if isinstance(metrics, Mapping):
        frame = resolve_frame(metrics)
        if frame is not None:
            source = "metrics"
    if frame is None:
        top_level = evidence.get(MEASUREMENT_FRAME_KEY)
        frame = resolve_frame(top_level)
        if frame is not None:
            source = "top_level"
    detail = {
        "frame": frame,
        "source": source,
        "valid_frames": list(VALID_MEASUREMENT_FRAMES),
    }
    if frame is None:
        return _check_record(
            CHECK_MEASUREMENT_FRAME, False, "measurement_frame_missing", detail
        )
    if frame not in VALID_MEASUREMENT_FRAMES:
        return _check_record(
            CHECK_MEASUREMENT_FRAME, False, "measurement_frame_unknown", detail
        )
    return _check_record(
        CHECK_MEASUREMENT_FRAME, True, "measurement_frame_present", detail
    )


# ---------------------------------------------------------------------------
# 체크 5 — evidence health (필수 receipt 5종)
# ---------------------------------------------------------------------------

def _receipt_statuses(evidence: Mapping[str, Any]) -> tuple[Optional[Dict[str, Any]], str]:
    """receipt status 매핑과 그 출처를 해석한다(없으면 (None, 사유))."""
    raw = evidence.get("evidence")
    if isinstance(raw, Mapping):
        return dict(raw), "evidence"
    payload = evidence.get("evidence_health")
    if not isinstance(payload, Mapping) or not payload:
        return None, "evidence_receipts_missing"
    components = payload.get("components")
    if not isinstance(components, list):
        return None, "evidence_health_components_missing"
    statuses: Dict[str, Any] = {}
    for component in components:
        if isinstance(component, Mapping) and component.get("name"):
            statuses[str(component["name"])] = component.get("status")
    if not statuses:
        return None, "evidence_health_components_missing"
    return statuses, "evidence_health_components"


def check_evidence_health(candidate_evidence: Any) -> Dict[str, Any]:
    """필수 receipt 5종(csv/trades/equity/prompt/validation) 건강 판정.

    사전계산된 overall 값은 신뢰하지 않는다 — 원시 receipt status 매핑
    (evidence 필드 우선, 폴백으로 evidence_health.components 에서 추출)을
    controller.condition_discovery.build_evidence_health(promotion 프리셋)로
    항상 **재계산**해 overall=='complete' 를 요구한다. receipt 소스 자체가
    없으면 'evidence_receipts_missing' 으로 실패한다(fail-closed).
    """
    evidence = _as_mapping(candidate_evidence)
    statuses, source = _receipt_statuses(evidence)
    if statuses is None:
        return _check_record(
            CHECK_EVIDENCE_HEALTH,
            False,
            source,
            {"required_components": list(EVIDENCE_COMPONENTS)},
        )
    health = build_evidence_health(statuses, preset=PRESET_PROMOTION)
    blockers = list(health.get("blockers") or [])
    overall = str(health.get("overall") or "missing")
    passed = overall == "complete" and not blockers
    if passed:
        reason = "evidence_receipts_complete"
    elif blockers:
        reason = blockers[0]
    else:
        reason = f"evidence_health_{overall}"
    detail = {
        "source": source,
        "overall": overall,
        "blockers": blockers,
        "components": health.get("components"),
        "required_components": list(EVIDENCE_COMPONENTS),
    }
    return _check_record(CHECK_EVIDENCE_HEALTH, passed, reason, detail)


# ---------------------------------------------------------------------------
# 종합 판정
# ---------------------------------------------------------------------------

_CHECK_FUNCTIONS = (
    check_slippage_gate,
    check_oos_walkforward,
    check_fresh_frozen_holdout,
    check_measurement_frame,
    check_evidence_health,
)


def _zero_generation_contract() -> Dict[str, Any]:
    """zero-generation 계약 필드 — 판정 결과와 무관하게 항상 False 고정.

    controller.condition_discovery 의 promotion-review 계약(can_promote=False,
    can_export=False, generation_allowed=False, 인간 승인 필수)을 그대로
    문서화한다. 이 모듈의 어떤 반환값도 승격/export 를 실행하지 않는다.
    """
    return {
        "can_promote": False,
        "can_export": False,
        "generation_allowed": False,
        "human_approval_required": True,
        "note": (
            "전제 판정 전부 통과여도 승격/export 는 실행되지 않는다 — "
            "동결 후보의 인간 승인 절차가 별도로 필요하다."
        ),
    }


def evaluate_promotion_preconditions(candidate_evidence: Any) -> Dict[str, Any]:
    """승격 전제 5종을 fail-closed 로 판정한 JSON-safe advisory 결과를 만든다.

    반환 dict:
      - passed          : 5개 체크가 전부 통과일 때만 True (그 외 False —
                          판정 불가/증거 부재도 False, 추측 금지 fail-closed).
      - checks          : 체크별 {name, passed, reason, detail} 5개 레코드.
      - failed_checks   : 실패 체크 name 목록 / reasons: 실패 사유 코드 목록.
      - input_status    : candidate_evidence 가 Mapping 이 아니면
                          'candidate_evidence_not_mapping'(전 체크 실패), 아니면 'ok'.
      - authority       : 'advisory_only' — 판정일 뿐 어떤 실행 권한도 없다.
      - zero_generation_contract : can_promote/can_export/generation_allowed
                          항상 False + 인간 승인 필수(결과와 무관 고정).

    입력은 절대 변경하지 않는다(원본 불변). 예외를 던지지 않는다 — 잘못된
    입력 형태도 fail-closed 실패 결과로 공시한다(게이트 판정기가 예외로
    우회되는 것을 막기 위한 의도적 설계).
    """
    is_mapping = isinstance(candidate_evidence, Mapping)
    input_status = "ok" if is_mapping else "candidate_evidence_not_mapping"
    source = candidate_evidence if is_mapping else {}

    checks = [check(source) for check in _CHECK_FUNCTIONS]
    failed = [c for c in checks if c["passed"] is not True]
    return {
        "schema_version": PROMOTION_PRECONDITIONS_SCHEMA_VERSION,
        "preset": PRESET_PROMOTION,
        "passed": not failed,
        "checks": checks,
        "failed_checks": [c["name"] for c in failed],
        "reasons": [c["reason"] for c in failed],
        "input_status": input_status,
        "authority": AUTHORITY_ADVISORY_ONLY,
        "zero_generation_contract": _zero_generation_contract(),
    }
