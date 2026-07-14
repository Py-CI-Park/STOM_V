"""T3.1 LLM 후보팩 생산자(pack_producer) 단위 테스트.

핵심 검증:
  - mock provider(유효 응답)로 만든 팩이 cli/condition_generator 의
    validate_multi_hypothesis_candidate_pack / expression_result_from_candidate_pack
    검증을 통과한다 (LLM 실호출 없음).
  - 불량 응답은 레인당 최대 2회 재시도 후, 미달이면 shortfall 정직 기록.
  - provider 예외는 terminal: candidate_pack=None + 실패 사유 리스트
    (research_loop 결정론 폴백 자연 발동 경로).
  - axis_prompt_lines 는 repair 프롬프트 분석 컨텍스트에만 주입 (원본 불변).
  - 영수증/팩 결정론: 같은 입력·같은 응답 → 동일 팩/영수증 (모듈 내 시계 없음).
  - 거부 응답 metadata 의 권한 키가 팩 내장 영수증으로 재밀반입되지 않음.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.pack_producer import (  # noqa: E402
    CANDIDATE_PACK_VERSION,
    produce_candidate_pack,
    produce_candidate_pack_result,
)
from ai_strategy_loop.brain.prompt import (  # noqa: E402
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
)
from cli.condition_generator import (  # noqa: E402
    expression_result_from_candidate_pack,
    validate_multi_hypothesis_candidate_pack,
)

PARENT_BUY_CODE = "if 현재가 > 시가 and 거래대금 > 10000:\n    self.Buy()"
PARENT_SELL_CODE = "if 수익률 < -1:\n    self.Sell()"
REPAIR_CODE_1 = "if 현재가 > 시가 and 거래대금 > 30000:\n    self.Buy()"
REPAIR_CODE_2 = "if 현재가 > 시가 and 체결강도 > 120:\n    self.Buy()"
DISCOVERY_CODE_1 = "if 등락율 > 3 and 회전율 > 1.5:\n    self.Buy()"
DISCOVERY_CODE_2 = "if 고가 > 시가 * 1.02 and 전일비 > 150:\n    self.Buy()"
GARBAGE_RESPONSE = "코드 블록 없는 잡담 응답"


def _response(metadata, code):
    return (
        f"```python\n{code}\n```\n"
        f"```json\n{json.dumps(metadata, ensure_ascii=False)}\n```"
    )


def _repair_metadata(**extra):
    payload = {
        "schema_version": 1,
        "lane": "repair",
        "prompt_version": REPAIR_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "parent_id": "parent-1",
        "analysis_card_id": "analysis-1",
        "intended_hypothesis": "turnover 임계만 완화",
        "risk_note": "노이즈 진입 증가 위험",
        "mutation_axis": "turnover_min_902 1.5 -> 3.0",
        "expected_effect": "거래수 +20% 기대",
        "hypothesis_id": "rh1",
    }
    payload.update(extra)
    return payload


def _discovery_metadata(**extra):
    payload = {
        "schema_version": 1,
        "lane": "discovery",
        "prompt_version": DISCOVERY_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "min",
        "coverage_gap_id": "gap-1",
        "discovery_target_coverage": ["cap:small|time:0900"],
        "intended_hypothesis": "회전율 반전 계열 신규 탐색",
        "novelty_rationale": "기존 팩과 다른 feature family",
        "risk_note": "한산장 미체결 위험",
        "mutation_axis": "feature_family:회전율",
        "expected_effect": "커버리지 공백 채움",
        "hypothesis_id": "dh1",
        "novelty": {"feature_family": "회전율_reversal"},
    }
    payload.update(extra)
    return payload


def _valid_repair_responses():
    return [
        _response(_repair_metadata(hypothesis_id="rh1"), REPAIR_CODE_1),
        _response(_repair_metadata(hypothesis_id="rh2"), REPAIR_CODE_2),
    ]


def _valid_discovery_responses():
    return [
        _response(_discovery_metadata(hypothesis_id="dh1"), DISCOVERY_CODE_1),
        _response(_discovery_metadata(hypothesis_id="dh2"), DISCOVERY_CODE_2),
    ]


class QueueProvider:
    """레인별 응답 큐 mock provider — 호출 메시지를 기록한다."""

    def __init__(self, repair=(), discovery=()):
        self.queues = {"repair": list(repair), "discovery": list(discovery)}
        self.calls = []

    def __call__(self, messages):
        user_text = messages[1]["content"]
        lane = "repair" if "repair 후보" in user_text else "discovery"
        self.calls.append({"lane": lane, "user_text": user_text})
        queue = self.queues[lane]
        assert queue, f"unexpected extra {lane} provider call"
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _context(**overrides):
    base = {
        "kind": "buy",
        "timeframe": "min",
        "round_id": "round-1",
        "parents": {
            "buy": {"id": "parent-1", "code": PARENT_BUY_CODE},
            "sell": {"id": "sell-1", "code": PARENT_SELL_CODE},
        },
        "analysis_card": {
            "analysis_id": "analysis-1",
            "candidate_id": "parent-1",
            "root_cause": "too strict near open",
            "mutation_axis": "turnover_min_902 1.5 -> 3.0",
        },
        "coverage_gap": {
            "coverage_gap_id": "gap-1",
            "coverage_bucket_keys": ["cap:small|time:0900"],
        },
        "novelty_context": {
            "coverage_regime": "open_30min",
            "existing_fingerprints": ["fp-a"],
        },
    }
    return {**base, **overrides}


# ------------------------------------------------------------- full pack


def test_full_pack_passes_condition_generator_validation():
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert result["shortfall"] == {}
    assert result["provider_call_count"] == 4
    assert result["lane_accepted_counts"] == {"repair": 2, "discovery": 2}

    pack = result["candidate_pack"]
    assert pack["schema_version"] == 1
    assert pack["candidate_pack_version"] == CANDIDATE_PACK_VERSION
    assert pack["candidate_pack_id"].startswith("cpk_")
    assert len(pack["candidates"]) == 4

    validation = validate_multi_hypothesis_candidate_pack(pack, min_candidates=2)
    assert validation["valid"] is True
    assert validation["failure_reasons"] == []
    assert validation["lane_counts"] == {"repair": 2, "discovery": 2}

    expr_result = expression_result_from_candidate_pack(pack, planned_count=4, min_candidates=2)
    assert expr_result["status"] == "ok"
    assert expr_result["source"] == "llm_multi_hypothesis_candidate_pack"
    assert expr_result["prompt_maturity_credit_allowed"] is True
    assert len(expr_result["expressions"]) == 4
    first = expr_result["selected_candidates"][0]
    assert first["candidate_contract_id"] == f"{pack['candidate_pack_id']}::{first['hypothesis_id']}"


def test_candidate_lane_contract_fields():
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    pack = produce_candidate_pack(_context(), provider)

    repair = [c for c in pack["candidates"] if c["lane"] == "repair"]
    discovery = [c for c in pack["candidates"] if c["lane"] == "discovery"]
    assert len(repair) == 2 and len(discovery) == 2
    for candidate in pack["candidates"]:
        for key in (
            "expression", "hypothesis_id", "intended_hypothesis",
            "mutation_axis", "expected_effect", "risk_note",
        ):
            assert candidate[key], f"missing {key} on {candidate['lane']}"
    for candidate in repair:
        assert candidate["parent_buy_id"] == "parent-1"
        assert candidate["parent_buy_code"] == PARENT_BUY_CODE
        assert candidate["parent_sell_code"] == PARENT_SELL_CODE
        assert candidate["analysis_card_id"] == "analysis-1"
        assert candidate["preserves_parent_structure"] is True
    for candidate in discovery:
        assert candidate["coverage_bucket_keys"] == ["cap:small|time:0900"]
        assert candidate["novelty_rationale"]
        assert candidate["novelty"] == {"feature_family": "회전율_reversal"}
    expressions = [c["expression"] for c in pack["candidates"]]
    assert len(expressions) == len(set(expressions))


def test_metadata_fallbacks_axis_effect_novelty_and_hypothesis_id():
    repair_meta = _repair_metadata()
    for key in ("mutation_axis", "expected_effect", "hypothesis_id"):
        repair_meta.pop(key)
    discovery_meta = _discovery_metadata()
    for key in ("novelty", "mutation_axis", "hypothesis_id"):
        discovery_meta.pop(key)
    provider = QueueProvider(
        repair=[_response(repair_meta, REPAIR_CODE_1)],
        discovery=[_response(discovery_meta, DISCOVERY_CODE_1)],
    )
    result = produce_candidate_pack_result(
        _context(), provider, lanes={"repair": 1, "discovery": 1}
    )

    assert result["status"] == "ok"
    repair = next(c for c in result["candidate_pack"]["candidates"] if c["lane"] == "repair")
    discovery = next(c for c in result["candidate_pack"]["candidates"] if c["lane"] == "discovery")
    # 분석 카드의 mutation_axis 로 폴백 (Analysis Card v2 는 변이축을 명명).
    assert repair["mutation_axis"] == "turnover_min_902 1.5 -> 3.0"
    assert repair["expected_effect"].startswith("intended_hypothesis 기반")
    assert repair["hypothesis_id"].startswith("repair_h_")
    # novelty_context 의 화이트리스트 축으로 폴백.
    assert discovery["novelty"] == {"coverage_regime": "open_30min"}
    assert discovery["mutation_axis"] == "novelty:coverage_regime=open_30min"
    assert discovery["hypothesis_id"].startswith("discovery_h_")

    validation = validate_multi_hypothesis_candidate_pack(result["candidate_pack"])
    assert validation["valid"] is True


# ------------------------------------------------------------- retry / shortfall


def test_invalid_response_retried_then_lane_filled():
    provider = QueueProvider(
        repair=[GARBAGE_RESPONSE, *_valid_repair_responses()],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert result["provider_call_count"] == 5
    assert any(reason.startswith("repair_attempt_1:") for reason in result["failure_reasons"])
    invalid_receipts = [
        receipt for receipt in result["prompt_receipts"]
        if receipt["downstream_result"] == "invalid"
    ]
    assert len(invalid_receipts) == 1
    assert "zero_code_blocks" in invalid_receipts[0]["failure_reason"]
    assert result["candidate_pack"]["production_failures"] == result["failure_reasons"]


def test_lane_shortfall_recorded_honestly_and_triggers_downstream_fallback():
    provider = QueueProvider(
        repair=_valid_repair_responses(),
        discovery=[GARBAGE_RESPONSE] * 4,  # 요구 2 + 재시도 2 전부 소진
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "partial"
    assert result["shortfall"] == {
        "discovery": {"requested": 2, "accepted": 0, "missing": 2},
    }
    pack = result["candidate_pack"]
    assert pack["shortfall"] == result["shortfall"]
    assert pack["lane_accepted_counts"] == {"repair": 2, "discovery": 0}

    validation = validate_multi_hypothesis_candidate_pack(pack)
    assert validation["valid"] is False
    assert "missing_discovery_candidate" in validation["failure_reasons"]
    expr_result = expression_result_from_candidate_pack(pack)
    assert expr_result["status"] == "error"  # research_loop 결정론 폴백 자연 발동 경로


def test_duplicate_expression_rejected_within_pack():
    provider = QueueProvider(
        repair=[
            _response(_repair_metadata(hypothesis_id="rh1"), REPAIR_CODE_1),
            _response(_repair_metadata(hypothesis_id="rh_dup"), REPAIR_CODE_1),
            _response(_repair_metadata(hypothesis_id="rh2"), REPAIR_CODE_2),
        ],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert any("duplicate_expression" in reason for reason in result["failure_reasons"])
    expressions = [c["expression"] for c in result["candidate_pack"]["candidates"]]
    assert len(expressions) == len(set(expressions)) == 4


def test_leaky_diagnostic_expression_rejected_then_retried():
    leaky_code = "if R_수익률 > 0:\n    self.Buy()"
    provider = QueueProvider(
        repair=[
            _response(_repair_metadata(hypothesis_id="rh_leak"), leaky_code),
            *_valid_repair_responses(),
        ],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert any("code_uses_R_diagnostic" in reason for reason in result["failure_reasons"])
    assert all("R_" not in c["expression"] for c in result["candidate_pack"]["candidates"])


def test_preserves_parent_structure_false_rejected():
    provider = QueueProvider(
        repair=[
            _response(
                _repair_metadata(hypothesis_id="rh_bad", preserves_parent_structure=False),
                REPAIR_CODE_1,
            ),
            *_valid_repair_responses(),
        ],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert any(
        "repair_parent_structure_not_preserved" in reason
        for reason in result["failure_reasons"]
    )
    assert validate_multi_hypothesis_candidate_pack(result["candidate_pack"])["valid"] is True


# ------------------------------------------------------------- terminal failures


def test_provider_exception_is_terminal_none_pack_with_reasons():
    provider = QueueProvider(
        repair=[_valid_repair_responses()[0], RuntimeError("boom")],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "error"
    assert result["candidate_pack"] is None
    assert any(
        reason.startswith("repair_provider_exception:") and "boom" in reason
        for reason in result["failure_reasons"]
    )
    # 예외 즉시 terminal — discovery 레인은 호출조차 안 된다.
    assert [call["lane"] for call in provider.calls] == ["repair", "repair"]
    # 예외 이전 성공 attempt 의 영수증은 보존된다 (pack id 는 미확정 None).
    assert len(result["prompt_receipts"]) == 1
    assert result["prompt_receipts"][0]["candidate_pack_id"] is None

    thin_provider = QueueProvider(repair=[RuntimeError("boom")])
    assert produce_candidate_pack(_context(), thin_provider) is None


def test_zero_valid_responses_returns_error_envelope():
    provider = QueueProvider(repair=[GARBAGE_RESPONSE] * 4, discovery=[GARBAGE_RESPONSE] * 4)
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "error"
    assert result["candidate_pack"] is None
    assert "no_valid_candidates_produced" in result["failure_reasons"]
    assert result["provider_call_count"] == 8
    assert len(result["prompt_receipts"]) == 8
    assert result["shortfall"]["repair"]["missing"] == 2
    assert result["shortfall"]["discovery"]["missing"] == 2


def test_input_validation_errors_before_any_provider_call():
    provider = QueueProvider()

    no_timeframe = produce_candidate_pack_result(_context(timeframe=None), provider)
    assert no_timeframe["status"] == "error"
    assert no_timeframe["candidate_pack"] is None
    assert "invalid_timeframe" in no_timeframe["failure_reasons"]

    unknown_lane = produce_candidate_pack_result(_context(), provider, lanes={"export": 1})
    assert "unknown_lane:export" in unknown_lane["failure_reasons"]

    no_card = produce_candidate_pack_result(_context(analysis_card=None), provider)
    assert "missing_analysis_card" in no_card["failure_reasons"]

    zero_lanes = produce_candidate_pack_result(
        _context(), provider, lanes={"repair": 0, "discovery": 0}
    )
    assert "no_candidates_requested" in zero_lanes["failure_reasons"]

    assert provider.calls == []  # 입력 위반 시 provider 호출 자체가 없다.


# ------------------------------------------------------------- axis prompt lines


def test_axis_prompt_lines_injected_into_repair_prompt_only():
    axis_lines = [
        "## 변이축 사전확률 (원장 기반, 부모 대비 효과)",
        "- turnover_min_902: 반복 악화. 이 축 재시도는 지양",
    ]
    original_card = {
        "analysis_id": "analysis-1",
        "candidate_id": "parent-1",
        "mutation_axis": "turnover_min_902 1.5 -> 3.0",
    }
    context = _context(analysis_card=original_card)
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    result = produce_candidate_pack_result(context, provider, axis_prompt_lines=axis_lines)

    assert result["status"] == "ok"
    repair_prompts = [call["user_text"] for call in provider.calls if call["lane"] == "repair"]
    discovery_prompts = [call["user_text"] for call in provider.calls if call["lane"] == "discovery"]
    assert all("변이축 사전확률" in text for text in repair_prompts)
    assert all("turnover_min_902: 반복 악화" in text for text in repair_prompts)
    assert all("변이축 사전확률" not in text for text in discovery_prompts)
    # 원본 분석 카드는 불변 (사본에만 주입).
    assert "axis_priors" not in original_card
    assert "axis_priors" not in context["analysis_card"]


def test_sell_kind_repair_prompt_embeds_sell_parent_code():
    """sell repair 프롬프트의 수리 대상 부모 전문은 SELL 코드다 (BUY 아님)."""
    sell_repair_code = "if 수익률 < -2:\n    self.Sell()"
    provider = QueueProvider(repair=[
        _response(_repair_metadata(kind="sell", hypothesis_id="rh_sell"), sell_repair_code),
    ])
    result = produce_candidate_pack_result(
        _context(kind="sell"), provider, lanes={"repair": 1}
    )

    assert result["status"] == "ok"
    repair_prompts = [c["user_text"] for c in provider.calls if c["lane"] == "repair"]
    assert repair_prompts
    for text in repair_prompts:
        assert PARENT_SELL_CODE in text
        assert PARENT_BUY_CODE not in text

    # buy kind 는 기존대로 BUY 부모를 수리 대상으로 내장한다.
    buy_provider = QueueProvider(repair=[_valid_repair_responses()[0]])
    buy_result = produce_candidate_pack_result(_context(), buy_provider, lanes={"repair": 1})
    assert buy_result["status"] == "ok"
    buy_text = buy_provider.calls[0]["user_text"]
    assert PARENT_BUY_CODE in buy_text
    assert PARENT_SELL_CODE not in buy_text


# ------------------------------------------------------------- determinism / authority


def test_pack_and_receipts_deterministic_for_same_inputs():
    def _run():
        provider = QueueProvider(
            repair=_valid_repair_responses(), discovery=_valid_discovery_responses()
        )
        return produce_candidate_pack_result(_context(), provider)

    first, second = _run(), _run()
    assert first["candidate_pack"]["candidate_pack_id"] == second["candidate_pack"]["candidate_pack_id"]
    assert first["prompt_receipts"] == second["prompt_receipts"]
    assert first["prompt_payload_shas"] == second["prompt_payload_shas"]
    assert first["candidate_pack"] == second["candidate_pack"]
    assert all(receipt["receipt_id"].startswith("rr_") for receipt in first["prompt_receipts"])
    # 팩은 JSON 직렬화 가능해야 한다 (원시 데이터 계약).
    assert json.loads(json.dumps(first["candidate_pack"], ensure_ascii=False))


def test_rejected_metadata_authority_keys_do_not_contaminate_pack():
    smuggled = _repair_metadata(hypothesis_id="rh_smuggle", can_promote=True)
    provider = QueueProvider(
        repair=[_response(smuggled, REPAIR_CODE_1), *_valid_repair_responses()],
        discovery=_valid_discovery_responses(),
    )
    result = produce_candidate_pack_result(_context(), provider)

    assert result["status"] == "ok"
    assert any(
        "metadata_authority_smuggling" in reason for reason in result["failure_reasons"]
    )
    pack = result["candidate_pack"]
    # 거부 응답의 원문 metadata 는 팩 내장 영수증에서 제외된다 — 권한 키 재밀반입 차단.
    assert "can_promote" not in json.dumps(pack, ensure_ascii=False)
    rejected = [r for r in pack["prompt_receipts"] if r["downstream_result"] == "invalid"]
    assert rejected and rejected[0]["strict_response_validation"]["raw_metadata_excluded"] is True
    assert "metadata" not in rejected[0]["strict_response_validation"]

    validation = validate_multi_hypothesis_candidate_pack(pack)
    assert validation["valid"] is True
    assert "pack_authority_smuggling" not in validation["failure_reasons"]


def test_context_pack_trace_propagates_to_pack_and_receipts():
    context_pack = {
        "context_pack_id": "rcp_test16",
        "parents": {
            "buy": {"id": "parent-1", "code": PARENT_BUY_CODE, "sha256": "sha-buy"},
            "sell": {"id": "sell-1", "code": PARENT_SELL_CODE, "sha256": "sha-sell"},
        },
        "stom_sources": {"all_available_sources_included": True},
    }
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    result = produce_candidate_pack_result(
        _context(research_context_pack=context_pack), provider
    )

    pack = result["candidate_pack"]
    assert pack["context_pack_id"] == "rcp_test16"
    assert pack["context_pack_sha256"]
    assert pack["full_stom_sources_included"] is True
    assert all(
        receipt["context_pack_id"] == "rcp_test16" for receipt in pack["prompt_receipts"]
    )
    # 팩 레벨 컨텍스트 키는 정규화 후보에도 전파된다 (condition_generator 계약).
    validation = validate_multi_hypothesis_candidate_pack(pack)
    assert validation["valid"] is True
    assert all(
        item["context_pack_id"] == "rcp_test16" for item in validation["valid_candidates"]
    )


# ===================================================================
# DR-04 -- final-owner wiring (default OFF via final_owner_enabled).
# ===================================================================


def test_final_owner_disabled_by_default_is_byte_identical():
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    result = produce_candidate_pack_result(_context(), provider)
    assert "final_owner_selection" not in result
    assert "final_owner_selection" not in result["candidate_pack"]


def test_final_owner_enabled_routes_full_round_through_select_official_candidate():
    provider = QueueProvider(repair=_valid_repair_responses(), discovery=_valid_discovery_responses())
    result = produce_candidate_pack_result(_context(), provider, final_owner_enabled=True)

    assert result["status"] == "ok"
    assert "final_owner_selection" in result
    selection = result["final_owner_selection"]
    assert selection["selected"] is not None
    assert selection["pool_blockers"] == []
    # exactly one candidate is promoted to official; the pack keeps all 4.
    assert len(result["candidate_pack"]["candidates"]) == 4
    assert result["candidate_pack"]["final_owner_selection"] == selection
    # the selected candidate_id is one of this round's real hypothesis_ids.
    hypothesis_ids = {c["hypothesis_id"] for c in result["candidate_pack"]["candidates"]}
    assert selection["selected"]["candidate_id"] in hypothesis_ids


def test_final_owner_enabled_skips_selection_when_round_is_a_shortfall_partial():
    """A partial round (missing a lane slot) must not be force-fed into
    select_official_candidate's strict 2/2 4-proposal contract."""
    provider = QueueProvider(
        repair=_valid_repair_responses(),
        discovery=[_valid_discovery_responses()[0], GARBAGE_RESPONSE, GARBAGE_RESPONSE, GARBAGE_RESPONSE],
    )
    result = produce_candidate_pack_result(_context(), provider, final_owner_enabled=True)
    assert result["status"] == "partial"
    assert "final_owner_selection" not in result
