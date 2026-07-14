import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.brain.prompt as prompt_mod  # noqa: E402
from ai_strategy_loop.brain.prompt import (  # noqa: E402
    DISCOVERY_RESEARCH_PROMPT_VERSION,
    REPAIR_RESEARCH_PROMPT_VERSION,
    build_discovery_research_messages,
    build_repair_research_messages,
    build_research_prompt_receipt,
    build_research_context_pack,
    estimate_research_context_pack_budget,
    render_research_context_pack,
    extract_code,
    validate_research_candidate_response,
)
from ai_strategy_loop.brain.candidate_output_contract import (  # noqa: E402
    BUY_EXCLUSION_EXPR,
    FULL_STRATEGY,
    RESEARCH_FILTER_CONSUMER,
    STRATEGY_SAVER_CONSUMER,
    make_candidate_payload,
    validate_candidate_payload,
)

def _payload_response(**kwargs):
    import json

    return f"```json\n{json.dumps(make_candidate_payload(**kwargs).as_dict(), ensure_ascii=False)}\n```"


def test_candidate_payload_v2_rejects_cross_kind_side_timeframe_and_hash_before_admission():
    common = {
        "output_kind": FULL_STRATEGY,
        "side": "buy",
        "timeframe": "tick",
        "body": "매수 = False\nif 매수:\n    self.Buy()",
        "expected_consumer": STRATEGY_SAVER_CONSUMER,
    }
    response = _payload_response(**common)
    assert validate_candidate_payload(
        response,
        expected_output_kind=FULL_STRATEGY,
        expected_side="buy",
        expected_timeframe="tick",
        expected_consumer=STRATEGY_SAVER_CONSUMER,
    )["valid"] is True

    cases = [
        (BUY_EXCLUSION_EXPR, "buy", "tick", RESEARCH_FILTER_CONSUMER, "candidate_payload_output_kind_mismatch"),
        (FULL_STRATEGY, "sell", "tick", STRATEGY_SAVER_CONSUMER, "candidate_payload_side_mismatch"),
        (FULL_STRATEGY, "buy", "min", STRATEGY_SAVER_CONSUMER, "candidate_payload_timeframe_mismatch"),
        (FULL_STRATEGY, "buy", "tick", RESEARCH_FILTER_CONSUMER, "candidate_payload_cross_kind_consumer"),
    ]
    for output_kind, side, timeframe, consumer, reason in cases:
        result = validate_candidate_payload(
            _payload_response(
                output_kind=output_kind, side=side, timeframe=timeframe,
                body=common["body"], expected_consumer=consumer,
            ),
            expected_output_kind=FULL_STRATEGY,
            expected_side="buy",
            expected_timeframe="tick",
            expected_consumer=STRATEGY_SAVER_CONSUMER,
        )
        assert reason in result["failure_reason"]

    drift = make_candidate_payload(**common).as_dict()
    drift["canonical_body_sha256"] = "0" * 64
    result = validate_candidate_payload(
        f"```json\n{__import__('json').dumps(drift, ensure_ascii=False)}\n```",
        expected_output_kind=FULL_STRATEGY, expected_side="buy",
        expected_timeframe="tick", expected_consumer=STRATEGY_SAVER_CONSUMER,
    )
    assert "candidate_payload_body_sha256_mismatch" in result["failure_reason"]


def test_candidate_payload_v2_rejects_extra_content_duplicate_keys_and_unsafe_predicates():
    common = {
        "output_kind": BUY_EXCLUSION_EXPR,
        "side": "buy",
        "timeframe": "min",
        "body": "B_거래대금 > 100",
        "expected_consumer": RESEARCH_FILTER_CONSUMER,
    }
    valid = _payload_response(**common)
    kwargs = {
        "expected_output_kind": BUY_EXCLUSION_EXPR,
        "expected_side": "buy",
        "expected_timeframe": "min",
        "expected_consumer": RESEARCH_FILTER_CONSUMER,
    }

    assert "candidate_payload_missing_or_extra_content" in validate_candidate_payload(
        "설명\n" + valid, **kwargs
    )["failure_reason"]

    payload_json = json.dumps(make_candidate_payload(**common).as_dict(), ensure_ascii=False)
    duplicate = payload_json.replace(
        '"schema_version": 11',
        '"schema_version": 11, "schema_version": 11',
        1,
    )
    assert "candidate_payload_duplicate_key" in validate_candidate_payload(
        f"```json\n{duplicate}\n```", **kwargs
    )["failure_reason"]

    for unsafe_body in ("self.Buy()", "B_거래대금", "__import__('os').system('echo unsafe')"):
        assert "candidate_payload_invalid_boolean_predicate" in validate_candidate_payload(
            _payload_response(**{**common, "body": unsafe_body}),
            **kwargs,
        )["failure_reason"]


def test_v2_prompt_contract_is_rendered_consistently_in_system_and_user_messages():
    messages = prompt_mod.build_messages(
        "sell", timeframe="min", strict_candidate_payload_v2=True,
    )
    for message in messages:
        assert "CandidatePayloadV2 output contract (mandatory)" in message["content"]
        assert "output_kind must be 'full_strategy'; side must be 'sell'; timeframe must be 'min'." in message["content"]

    repair = build_repair_research_messages(
        "buy", timeframe="tick", parent_code="매수 = False",
        analysis_card={"analysis_id": "a", "candidate_id": "p"},
        strict_candidate_payload_v2=True,
    )
    for message in repair:
        assert "output_kind must be 'buy_exclusion_expr'; side must be 'buy'; timeframe must be 'tick'." in message["content"]
        assert "eval-mode Boolean predicate" in message["content"]
def test_research_context_pack_includes_full_stom_sources_and_parent_hashes():
    parent_buy = "if 현재가 > 시가:\n    self.Buy()"
    parent_sell = "if 수익률 < -1:\n    self.Sell()"

    pack = build_research_context_pack(
        mode="process-research",
        timeframe="tick",
        parent_buy_id="buy-1",
        parent_buy_code=parent_buy,
        parent_sell_id="sell-1",
        parent_sell_code=parent_sell,
        official_metrics={"profit": 1000, "mdd": 8, "trades": 42, "daily": 1.2},
        segment_heatmap=[{"time_bucket": "0900", "cap_bucket": "small", "profit": -10}],
        feature_importance={"top": [{"feature": "체결강도", "direction": "high"}]},
        edge_ratio={"edge_ratio": 1.2},
        mfe_mae={"mae": -1.1, "mfe": 2.3},
        correlation_redundancy={"groups": [["체결강도", "체결강도평균"]]},
        avoid_zones=["0900-small-loss"],
        prefer_zones=["0910-mid-positive"],
        root_cause_summary={"primary": "open giveback"},
    )

    asset_names = set(pack["stom_sources"]["asset_names"])
    assert {
        "strategy",
        "rules",
        "system_prompt",
        "variables_reference",
        "forbidden",
        "examples",
    }.issubset(asset_names)
    assert pack["parents"]["buy"]["id"] == "buy-1"
    assert pack["parents"]["buy"]["sha256"]
    assert pack["parents"]["sell"]["id"] == "sell-1"
    assert pack["parents"]["delivery_policy"] == "full_condition_code_required_not_id_only"
    assert pack["parents"]["buy"]["code"] == parent_buy
    assert pack["parents"]["sell"]["code"] == parent_sell
    assert pack["analysis"]["segment_heatmap"][0]["cap_bucket"] == "small"
    assert pack["analysis"]["correlation_redundancy"]["groups"][0][0] == "체결강도"
    assert pack["authority"]["scope"] == "research_only"
    assert pack["authority"]["can_export"] is False
    assert pack["budget"]["within_limit"] is True
    rendered = render_research_context_pack(pack)
    budget = estimate_research_context_pack_budget(rendered)
    assert budget["estimated_tokens"] > 0
    assert "strategy.txt" in rendered
    assert "rules.txt" in rendered
    assert "Parent 매수 condition full code" in rendered
    assert parent_buy in rendered
    assert parent_sell in rendered


def test_research_context_pack_fails_closed_when_prompt_budget_exceeded():
    with pytest.raises(ValueError, match="research_context_pack_budget_exceeded"):
        build_research_context_pack(
            mode="process-research",
            timeframe="tick",
            parent_buy_code="x" * 200,
            max_tokens=10,
        )

def test_research_context_pack_fails_closed_when_required_source_missing(monkeypatch):
    missing = prompt_mod._REPO_ROOT / "utility" / "ai_agent" / "__missing_required_source__.txt"
    monkeypatch.setattr(prompt_mod, "_FULL_STOM_SOURCE_ASSETS", (("missing_source", missing),))
    with pytest.raises(ValueError, match="research_context_pack_sources_missing"):
        build_research_context_pack(
            mode="process-research",
            timeframe="tick",
        )

def test_research_context_pack_rejects_authority_smuggling_context():
    with pytest.raises(ValueError, match="research_context_authority_smuggling"):
        build_research_context_pack(
            mode="process-research",
            timeframe="tick",
            extra_context={"nested": {"can_live": True}},
        )

    with pytest.raises(ValueError, match="research_context_authority_smuggling"):
        build_research_context_pack(
            mode="process-research",
            timeframe="tick",
            candidate_hypotheses=[{"hypothesis_id": "h1", "production_ready": True}],
        )

    with pytest.raises(ValueError, match="research_context_authority_smuggling"):
        build_research_context_pack(
            mode="process-research",
            timeframe="tick",
            extra_context={"can_final_promote": True},
        )


VALID_CODE = "if 현재가 > 시가:\n    self.Buy()"


def _response(metadata, *, code=VALID_CODE):
    import json

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
        "timeframe": "tick",
        "parent_id": "parent-1",
        "analysis_card_id": "analysis-1",
        "intended_hypothesis": "loosen only the turnover threshold",
        "risk_note": "may increase noisy entries",
    }
    payload.update(extra)
    return payload


def _discovery_metadata(**extra):
    payload = {
        "schema_version": 1,
        "lane": "discovery",
        "prompt_version": DISCOVERY_RESEARCH_PROMPT_VERSION,
        "kind": "buy",
        "timeframe": "tick",
        "coverage_gap_id": "gap-1",
        "discovery_target_coverage": ["turnover-reversal"],
        "intended_hypothesis": "test a new turnover reversal family",
        "novelty_rationale": "new structural fingerprint and coverage bucket",
        "risk_note": "may undertrade in quiet markets",
    }
    payload.update(extra)
    return payload


def test_repair_and_discovery_message_builders_preserve_strict_contracts():
    context_pack = {
        "parents": {
            "buy": {"id": "parent-1", "code": "if 현재가 > 시가:\n    self.Buy()", "sha256": "sha-buy"},
            "sell": {"id": "sell-1", "code": "if 수익률 < -1:\n    self.Sell()", "sha256": "sha-sell"},
        }
    }
    repair_messages = build_repair_research_messages(
        "buy",
        timeframe="tick",
        parent_code="if 현재가 > 시가:\n    self.Buy()",
        research_context_pack=context_pack,
        analysis_card={
            "analysis_id": "analysis-1",
            "candidate_id": "parent-1",
            "root_cause": "too strict near open",
        },
    )
    repair_user = repair_messages[1]["content"]
    assert "python 코드 블록 1개" in repair_user
    assert REPAIR_RESEARCH_PROMPT_VERSION in repair_user
    assert "parent_id" in repair_user
    assert "analysis_card_id" in repair_user
    assert "Research Prompt Context Pack" in repair_user
    assert "ID는 추적용일 뿐" in repair_user
    assert "if 현재가 > 시가" in repair_user

    discovery_messages = build_discovery_research_messages(
        "buy",
        timeframe="tick",
        coverage_gap={"coverage_gap_id": "gap-1", "coverage_bucket_keys": ["turnover-reversal"]},
        novelty_context={"existing_fingerprints": ["a", "b"]},
        research_context_pack=context_pack,
    )
    discovery_user = discovery_messages[1]["content"]
    assert "기존 후보 복제 금지" in discovery_user
    assert DISCOVERY_RESEARCH_PROMPT_VERSION in discovery_user
    assert "coverage_gap_id" in discovery_user
    assert "novelty_rationale" in discovery_user
    assert "Research Prompt Context Pack" in discovery_user
    assert "if 수익률 < -1" in discovery_user


@pytest.mark.parametrize("lane,version,metadata_factory", [
    ("repair", REPAIR_RESEARCH_PROMPT_VERSION, _repair_metadata),
    ("discovery", DISCOVERY_RESEARCH_PROMPT_VERSION, _discovery_metadata),
])
def test_validate_research_candidate_response_accepts_one_code_and_metadata_block(lane, version, metadata_factory):
    result = validate_research_candidate_response(
        _response(metadata_factory()),
        expected_lane=lane,
        expected_prompt_version=version,
        expected_kind="buy",
        expected_timeframe="tick",
    )

    assert result["valid"] is True
    assert result["code"] == VALID_CODE
    assert result["metadata_present"] is True
    assert result["metadata_json_safe"] is True
    assert result["failure_reason"] == ""
    assert extract_code(_response(metadata_factory())) == VALID_CODE


def test_validate_research_candidate_response_rejects_missing_or_multiple_code_blocks():
    no_code = validate_research_candidate_response(
        "```json\n{}\n```",
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert no_code["valid"] is False
    assert "zero_code_blocks" in no_code["failure_reason"]

    two_codes = validate_research_candidate_response(
        "```python\nx = 1\n```\n```python\ny = 2\n```\n```json\n{}\n```",
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert two_codes["valid"] is False
    assert "multiple_candidate_code_blocks" in two_codes["failure_reason"]

    empty_code = validate_research_candidate_response(
        _response(_repair_metadata(), code="   "),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert empty_code["valid"] is False
    assert "empty_candidate_code_block" in empty_code["failure_reason"]

    bare_json_only = validate_research_candidate_response(
        "```\n"
        "{\"schema_version\":1,\"lane\":\"repair\",\"prompt_version\":\"repair_v1_analysis_card_single_axis\","
        "\"kind\":\"buy\",\"timeframe\":\"tick\",\"parent_id\":\"parent-1\","
        "\"analysis_card_id\":\"analysis-1\",\"intended_hypothesis\":\"repair\","
        "\"risk_note\":\"risk\"}"
        "\n```",
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert bare_json_only["valid"] is False
    assert "zero_code_blocks" in bare_json_only["failure_reason"]


def test_validate_research_candidate_response_rejects_prompt_metadata_mismatches():
    bad = validate_research_candidate_response(
        _response(_repair_metadata(lane="discovery", prompt_version=DISCOVERY_RESEARCH_PROMPT_VERSION, candidates=["a", "b"])),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )

    assert bad["valid"] is False
    assert "lane_mismatch" in bad["failure_reason"]
    assert "prompt_version_mismatch" in bad["failure_reason"]
    assert "multiple_alternatives" in bad["failure_reason"]

    multiple_metadata = validate_research_candidate_response(
        _response(_repair_metadata()) + "\n```json\n{\"extra\": true}\n```",
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert multiple_metadata["valid"] is False
    assert "multiple_metadata_blocks" in multiple_metadata["failure_reason"]
    assert multiple_metadata["metadata_block_count"] == 2

    smuggled_authority = validate_research_candidate_response(
        _response(_repair_metadata(can_promote=True, nested={"can_live": True})),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert smuggled_authority["valid"] is False
    assert "metadata_authority_smuggling" in smuggled_authority["failure_reason"]
    smuggled_final_authority = validate_research_candidate_response(
        _response(_repair_metadata(can_final_promote=True)),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert smuggled_final_authority["valid"] is False
    assert "metadata_authority_smuggling" in smuggled_final_authority["failure_reason"]

    leaky_code = validate_research_candidate_response(
        _response(_repair_metadata(), code="if R_MFE < 0:\n    self.Buy()"),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert leaky_code["valid"] is False
    assert "code_uses_R_diagnostic" in leaky_code["failure_reason"]

    leaky_sell_code = validate_research_candidate_response(
        _response(_repair_metadata(), code="if S_보유시간 > 10:\n    self.Buy()"),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert leaky_sell_code["valid"] is False
    assert "code_uses_S_diagnostic" in leaky_sell_code["failure_reason"]


def test_validate_research_candidate_response_requires_lane_specific_fields():
    missing_parent = validate_research_candidate_response(
        _response(_repair_metadata(parent_id="")),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert "missing_repair_parent_reference" in missing_parent["failure_reason"]
    missing_analysis = validate_research_candidate_response(
        _response(_repair_metadata(analysis_card_id="")),
        expected_lane="repair",
        expected_prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert "missing_repair_analysis_card_reference" in missing_analysis["failure_reason"]


    missing_novelty = validate_research_candidate_response(
        _response(_discovery_metadata(novelty_rationale="")),
        expected_lane="discovery",
        expected_prompt_version=DISCOVERY_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert "missing_discovery_novelty_rationale" in missing_novelty["failure_reason"]

    missing_coverage = validate_research_candidate_response(
        _response(_discovery_metadata(coverage_gap_id="", discovery_target_coverage=[])),
        expected_lane="discovery",
        expected_prompt_version=DISCOVERY_RESEARCH_PROMPT_VERSION,
        expected_kind="buy",
        expected_timeframe="tick",
    )
    assert "missing_discovery_coverage_gap_reference" in missing_coverage["failure_reason"]
    assert "missing_discovery_target_coverage" in missing_coverage["failure_reason"]


def test_build_research_prompt_receipt_carries_maturity_and_downstream_failure_reason():
    receipt = build_research_prompt_receipt(
        receipt_id="receipt-1",
        round_id="round-1",
        slot_id="slot-1",
        lane="repair",
        prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
        prompt_score=87,
        intended_hypothesis="single-axis repair",
        parent_id="parent-1",
        analysis_card_id="analysis-1",
        parent_buy_code="if 현재가 > 시가:\n    self.Buy()",
        parent_sell_id="sell-1",
        parent_sell_code="if 수익률 < -1:\n    self.Sell()",
        risk_note="may increase trades",
        output_candidate_id="candidate-1",
        strict_response_validation={"valid": True},
        downstream_result="improved",
    )
    assert receipt["prompt_score_band"] == "85_100"
    assert receipt["authority"] == "research_prompt_maturity_only"
    assert receipt["strict_response_validation"] == {"valid": True}
    assert receipt["parent_conditions"]["delivery_policy"] == "full_condition_code_required_not_id_only"
    assert receipt["parent_conditions"]["buy"]["code"] == "if 현재가 > 시가:\n    self.Buy()"
    assert receipt["parent_conditions"]["sell"]["code"] == "if 수익률 < -1:\n    self.Sell()"
    assert receipt["parent_conditions"]["buy"]["sha256"]

    with pytest.raises(ValueError, match="failure_reason"):
        build_research_prompt_receipt(
            receipt_id="receipt-2",
            round_id="round-1",
            slot_id="slot-2",
            lane="repair",
            prompt_version=REPAIR_RESEARCH_PROMPT_VERSION,
            prompt_score=20,
            intended_hypothesis="bad repair",
            strict_response_validation={"valid": False},
            downstream_result="rejected",
        )
