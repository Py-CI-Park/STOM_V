"""T5.3 승격 전제 판정 순수 모듈 단위 테스트 — fail-closed 계약 검증.

검증 계약:
  1. 5개 체크 전부 통과 시에만 passed=True (그 외 전부 False — fail-closed)
  2. 슬리피지 게이트: evaluate_slippage_gate 재사용 사유(tick2 부재/적자/비유한수) 전파
  3. OOS: 명시 통과 상태만 인정, 부재/미실행/mixed/실패/미인식 문자열 전부 실패
  4. frozen/fresh holdout: provenance 부재·오염·scope 불일치 blocker 어휘 일치
  5. measurement_frame 라벨: 부재/미지 프레임 fail-closed + 폴백 소스 인정
  6. evidence health: 필수 receipt 5종을 promotion 프리셋으로 항상 재계산
     (사전계산 overall='complete' 주장을 신뢰하지 않음)
  7. zero-generation 계약: passed 와 무관하게 can_promote/can_export/
     generation_allowed=False 고정 + authority='advisory_only' + JSON 직렬화 가능
DB/엔진/런타임 접근 없음 — 순수 dict 합성 입력만 사용한다.
"""
from __future__ import annotations

import copy
import json

from ai_strategy_loop.controller.condition_discovery import (
    EVIDENCE_COMPONENTS,
    PRESET_PROMOTION,
    build_evidence_health,
    build_validation_provenance,
)
from ai_strategy_loop.fitness.measurement_frame import (
    FRAME_NICHE_SINGLE_POSITION,
    FRAME_PORTFOLIO_MULTI_POSITION,
    MEASUREMENT_FRAME_KEY,
    annotate_frame,
)
from ai_strategy_loop.portfolio.promotion_preconditions import (
    AUTHORITY_ADVISORY_ONLY,
    CHECK_EVIDENCE_HEALTH,
    CHECK_FRESH_FROZEN_HOLDOUT,
    CHECK_MEASUREMENT_FRAME,
    CHECK_OOS_WALKFORWARD,
    CHECK_SLIPPAGE_GATE,
    PRECONDITION_CHECK_NAMES,
    check_evidence_health,
    check_fresh_frozen_holdout,
    check_measurement_frame,
    check_oos_walkforward,
    check_slippage_gate,
    evaluate_promotion_preconditions,
)


# ---------------------------------------------------------------------------
# 합성 증거 헬퍼
# ---------------------------------------------------------------------------

def _passing_slippage_profiles(total_profit: float = 1_500_000.0) -> dict:
    return {"profiles": {"tick2": {"total_profit": total_profit}}}


def _complete_receipts() -> dict:
    return {name: "present" for name in EVIDENCE_COMPONENTS}


def _passing_provenance() -> dict:
    return build_validation_provenance(
        used_for_prompt_or_allocation=False,
        frozen=True,
        fresh_holdout=True,
        evidence_health=build_evidence_health(_complete_receipts(), preset=PRESET_PROMOTION),
    )


def _passing_evidence() -> dict:
    return {
        "slippage_profiles": _passing_slippage_profiles(),
        "oos_status": "pass",
        "validation_provenance": _passing_provenance(),
        "metrics": annotate_frame({"total_profit": 2_400_000.0}, FRAME_PORTFOLIO_MULTI_POSITION),
        "evidence": _complete_receipts(),
    }


def _check_by_name(result: dict, name: str) -> dict:
    matches = [c for c in result["checks"] if c["name"] == name]
    assert len(matches) == 1
    return matches[0]


# ---------------------------------------------------------------------------
# 종합 판정 — 전부 통과 / fail-closed
# ---------------------------------------------------------------------------

def test_all_preconditions_pass_and_result_is_json_safe():
    evidence = _passing_evidence()
    snapshot = copy.deepcopy(evidence)
    result = evaluate_promotion_preconditions(evidence)

    assert result["passed"] is True
    assert result["failed_checks"] == []
    assert result["reasons"] == []
    assert result["input_status"] == "ok"
    assert [c["name"] for c in result["checks"]] == list(PRECONDITION_CHECK_NAMES)
    assert all(c["passed"] is True for c in result["checks"])
    # JSON-safe + 입력 불변
    json.dumps(result, ensure_ascii=False)
    assert evidence == snapshot


def test_zero_generation_contract_fixed_regardless_of_pass():
    for payload in (_passing_evidence(), {}):
        result = evaluate_promotion_preconditions(payload)
        contract = result["zero_generation_contract"]
        assert result["authority"] == AUTHORITY_ADVISORY_ONLY
        assert contract["can_promote"] is False
        assert contract["can_export"] is False
        assert contract["generation_allowed"] is False
        assert contract["human_approval_required"] is True


def test_empty_evidence_fails_every_check_fail_closed():
    result = evaluate_promotion_preconditions({})
    assert result["passed"] is False
    assert result["failed_checks"] == list(PRECONDITION_CHECK_NAMES)
    assert len(result["reasons"]) == len(PRECONDITION_CHECK_NAMES)
    assert all(isinstance(r, str) and r for r in result["reasons"])
    assert result["input_status"] == "ok"


def test_non_mapping_input_fails_closed_without_exception():
    for bad in (None, "evidence", 42, ["list"]):
        result = evaluate_promotion_preconditions(bad)
        assert result["passed"] is False
        assert result["input_status"] == "candidate_evidence_not_mapping"
        assert result["failed_checks"] == list(PRECONDITION_CHECK_NAMES)


def test_single_failing_check_blocks_overall_pass():
    evidence = _passing_evidence()
    evidence["oos_status"] = "failed"
    result = evaluate_promotion_preconditions(evidence)
    assert result["passed"] is False
    assert result["failed_checks"] == [CHECK_OOS_WALKFORWARD]
    assert result["reasons"] == ["oos_failed"]


# ---------------------------------------------------------------------------
# 체크 1 — 슬리피지 게이트
# ---------------------------------------------------------------------------

def test_slippage_gate_passes_on_tick2_positive_profit():
    check = check_slippage_gate({"slippage_profiles": _passing_slippage_profiles()})
    assert check["passed"] is True
    assert check["reason"] == "slippage_profile_profit_positive"
    assert check["detail"]["gate_profile"] == "tick2"
    assert check["detail"]["profile_total_profit"] == 1_500_000.0


def test_slippage_gate_fail_closed_reasons():
    cases = [
        ({}, "slippage_profiles_missing"),
        ({"slippage_profiles": {"profiles": {"tick1": {"total_profit": 10.0}}}},
         "slippage_gate_profile_missing"),
        ({"slippage_profiles": _passing_slippage_profiles(-500.0)},
         "slippage_profile_profit_not_positive"),
        ({"slippage_profiles": _passing_slippage_profiles(0.0)},
         "slippage_profile_profit_not_positive"),
        ({"slippage_profiles": {"profiles": {"tick2": {"total_profit": "nan"}}}},
         "slippage_profile_total_profit_invalid"),
        ({"slippage_profiles": "not-a-mapping"}, "slippage_profiles_missing"),
    ]
    for evidence, expected_reason in cases:
        check = check_slippage_gate(evidence)
        assert check["passed"] is False, expected_reason
        assert check["reason"] == expected_reason


def test_slippage_gate_accepts_flat_profile_mapping():
    # fitness.slippage_profiles 결과의 내부 "profiles" 컨테이너 없이
    # 프로파일 매핑 자체를 준 경우도 원 함수 계약대로 판정한다.
    check = check_slippage_gate({"slippage_profiles": {"tick2": {"total_profit": 3.0}}})
    assert check["passed"] is True


# ---------------------------------------------------------------------------
# 체크 2 — OOS/walk-forward 증거
# ---------------------------------------------------------------------------

def test_oos_passing_statuses():
    for status in ("pass", "passed", "consistent", "  PASS  "):
        check = check_oos_walkforward({"oos_status": status})
        assert check["passed"] is True, status
        assert check["reason"] == "oos_walkforward_passing"


def test_oos_fallback_key_accepted():
    check = check_oos_walkforward({"oos": "passed"})
    assert check["passed"] is True


def test_oos_fail_closed_reasons():
    cases = [
        ({}, "oos_evidence_missing"),
        ({"oos_status": ""}, "oos_evidence_missing"),
        ({"oos_status": "none"}, "oos_not_run"),
        ({"oos_status": "not_run"}, "oos_not_run"),
        ({"oos_status": "unknown"}, "oos_status_unknown"),
        ({"oos_status": "mixed"}, "oos_mixed"),
        ({"oos_status": "fail"}, "oos_failed"),
        ({"oos_status": "failed"}, "oos_failed"),
        ({"oos_status": "regression"}, "oos_failed"),
        ({"oos_status": "grade_a"}, "oos_status_unrecognized"),
    ]
    for evidence, expected_reason in cases:
        check = check_oos_walkforward(evidence)
        assert check["passed"] is False, expected_reason
        assert check["reason"] == expected_reason


# ---------------------------------------------------------------------------
# 체크 3 — frozen / fresh holdout
# ---------------------------------------------------------------------------

def test_holdout_passes_on_fresh_frozen_provenance():
    check = check_fresh_frozen_holdout({"validation_provenance": _passing_provenance()})
    assert check["passed"] is True
    assert check["reason"] == "fresh_frozen_holdout_confirmed"
    assert check["detail"]["blockers"] == []


def test_holdout_fail_closed_blocker_vocabulary():
    base = {
        "frozen": True,
        "fresh_holdout": True,
        "used_for_prompt_or_allocation": False,
        "scope": "fresh_frozen_holdout",
    }
    cases = [
        ({}, "validation_provenance_missing"),
        ({"validation_provenance": "text"}, "validation_provenance_missing"),
        ({"validation_provenance": {**base, "frozen": False}}, "validation_not_frozen"),
        ({"validation_provenance": {k: v for k, v in base.items() if k != "fresh_holdout"}},
         "validation_not_fresh_holdout"),
        ({"validation_provenance": {**base, "used_for_prompt_or_allocation": True}},
         "validation_used_for_research_learning"),
        ({"validation_provenance": {**base, "scope": "research_only"}},
         "validation_scope_research_only"),
        ({"validation_provenance": {**base, "scope": "mystery_scope"}},
         "validation_scope_not_fresh_frozen_holdout"),
    ]
    for evidence, expected_reason in cases:
        check = check_fresh_frozen_holdout(evidence)
        assert check["passed"] is False, expected_reason
        assert check["reason"] == expected_reason
        assert expected_reason in (check["detail"]["blockers"] or [expected_reason])


def test_holdout_collects_multiple_blockers():
    check = check_fresh_frozen_holdout({
        "validation_provenance": {"frozen": False, "fresh_holdout": False},
    })
    assert check["passed"] is False
    assert check["detail"]["blockers"] == [
        "validation_not_frozen",
        "validation_not_fresh_holdout",
    ]


# ---------------------------------------------------------------------------
# 체크 4 — measurement_frame 라벨
# ---------------------------------------------------------------------------

def test_measurement_frame_present_in_metrics():
    metrics = annotate_frame({"total_profit": 1.0}, FRAME_NICHE_SINGLE_POSITION)
    check = check_measurement_frame({"metrics": metrics})
    assert check["passed"] is True
    assert check["reason"] == "measurement_frame_present"
    assert check["detail"]["frame"] == FRAME_NICHE_SINGLE_POSITION
    assert check["detail"]["source"] == "metrics"


def test_measurement_frame_top_level_fallback():
    check = check_measurement_frame({MEASUREMENT_FRAME_KEY: FRAME_PORTFOLIO_MULTI_POSITION})
    assert check["passed"] is True
    assert check["detail"]["source"] == "top_level"


def test_measurement_frame_fail_closed():
    cases = [
        ({}, "measurement_frame_missing"),
        ({"metrics": {"total_profit": 1.0}}, "measurement_frame_missing"),
        ({"metrics": "not-a-mapping"}, "measurement_frame_missing"),
        ({"metrics": {MEASUREMENT_FRAME_KEY: "galaxy_frame"}}, "measurement_frame_unknown"),
    ]
    for evidence, expected_reason in cases:
        check = check_measurement_frame(evidence)
        assert check["passed"] is False, expected_reason
        assert check["reason"] == expected_reason


# ---------------------------------------------------------------------------
# 체크 5 — evidence health (필수 receipt 5종)
# ---------------------------------------------------------------------------

def test_evidence_health_passes_on_complete_receipts():
    check = check_evidence_health({"evidence": _complete_receipts()})
    assert check["passed"] is True
    assert check["reason"] == "evidence_receipts_complete"
    assert check["detail"]["overall"] == "complete"
    assert check["detail"]["source"] == "evidence"
    assert check["detail"]["required_components"] == list(EVIDENCE_COMPONENTS)


def test_evidence_health_missing_component_is_blocker():
    receipts = _complete_receipts()
    del receipts["equity"]
    check = check_evidence_health({"evidence": receipts})
    assert check["passed"] is False
    assert check["reason"] == "missing_or_invalid_equity_evidence"
    assert "missing_or_invalid_equity_evidence" in check["detail"]["blockers"]


def test_evidence_health_recomputes_from_payload_components():
    payload = build_evidence_health(_complete_receipts(), preset=PRESET_PROMOTION)
    check = check_evidence_health({"evidence_health": payload})
    assert check["passed"] is True
    assert check["detail"]["source"] == "evidence_health_components"


def test_evidence_health_does_not_trust_precomputed_overall():
    # 사전계산 payload 가 overall='complete' 를 주장해도 components 의
    # 실제 status 로 promotion 프리셋 재계산해 fail-closed 판정한다.
    forged = {
        "overall": "complete",
        "blockers": [],
        "promotion_blocked": False,
        "components": [
            {"name": name, "status": "present"} for name in EVIDENCE_COMPONENTS
            if name != "prompt"
        ] + [{"name": "prompt", "status": "missing"}],
    }
    check = check_evidence_health({"evidence_health": forged})
    assert check["passed"] is False
    assert check["reason"] == "missing_or_invalid_prompt_evidence"


def test_evidence_health_fail_closed_when_receipts_missing():
    cases = [
        ({}, "evidence_receipts_missing"),
        ({"evidence_health": {}}, "evidence_receipts_missing"),
        ({"evidence_health": {"overall": "complete"}}, "evidence_health_components_missing"),
        ({"evidence_health": {"components": ["bad"]}}, "evidence_health_components_missing"),
    ]
    for evidence, expected_reason in cases:
        check = check_evidence_health(evidence)
        assert check["passed"] is False, expected_reason
        assert check["reason"] == expected_reason


def test_evidence_health_empty_raw_receipts_fail():
    check = check_evidence_health({"evidence": {}})
    assert check["passed"] is False
    assert check["detail"]["overall"] == "evidence_blocker"


# ---------------------------------------------------------------------------
# 체크 레코드 공통 계약
# ---------------------------------------------------------------------------

def test_every_check_record_is_json_safe_with_strict_bool():
    for payload in ({}, _passing_evidence()):
        for check_fn, name in (
            (check_slippage_gate, CHECK_SLIPPAGE_GATE),
            (check_oos_walkforward, CHECK_OOS_WALKFORWARD),
            (check_fresh_frozen_holdout, CHECK_FRESH_FROZEN_HOLDOUT),
            (check_measurement_frame, CHECK_MEASUREMENT_FRAME),
            (check_evidence_health, CHECK_EVIDENCE_HEALTH),
        ):
            record = check_fn(payload)
            assert record["name"] == name
            assert isinstance(record["passed"], bool)
            assert isinstance(record["reason"], str) and record["reason"]
            json.dumps(record, ensure_ascii=False)


def test_package_reexports_promotion_preconditions():
    import ai_strategy_loop.portfolio as portfolio_pkg

    assert portfolio_pkg.evaluate_promotion_preconditions is evaluate_promotion_preconditions
    assert "evaluate_promotion_preconditions" in portfolio_pkg.__all__
