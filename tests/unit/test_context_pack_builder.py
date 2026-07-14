"""T2.1 Context Pack 생산자 승격 + research_loop opt-in 배선 계약 테스트.

계약:
  - build_research_context_pack(sources)는 brain.prompt 의 기존 Context Pack
    계약(전체 STOM 규칙 원천, 부모 전문+sha256, 250k 예산 fail-closed)을
    그대로 사용한다 (test_research_prompt_contracts 계약 재사용).
  - research_loop 배선은 opt-in(기본 OFF) + additive 키만 — 소스 부족 시
    진행을 막지 않고 context_pack_error 만 기록한다.
"""

import hashlib
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.brain.prompt as prompt_mod  # noqa: E402
import cli.research_loop as research_loop  # noqa: E402
from ai_strategy_loop.controller.context_pack_builder import (  # noqa: E402
    DEFAULT_CONTEXT_PACK_MODE,
    build_candidate_generation_context,
    build_context_pack_receipt,
    build_research_context_pack,
    produce_research_candidate_pack,
)
from cli.research_loop import ResearchLoopConfig  # noqa: E402

PARENT_BUY = "if 현재가 > 시가:\n    self.Buy()"
PARENT_SELL = "if 수익률 < -1:\n    self.Sell()"


def _sources(**overrides):
    base = {
        "mode": "process-research",
        "timeframe": "tick",
        "parent_buy_id": "buy-1",
        "parent_buy_code": PARENT_BUY,
        "parent_sell_id": "sell-1",
        "parent_sell_code": PARENT_SELL,
        "official_metrics": {"profit": 1000, "mdd": 8, "trades": 42},
        "analysis_card": {
            "analysis_id": "A_ctx_pack_test",
            "candidate_id": "cond-1",
            "root_cause": {"primary": "open giveback"},
            "feature_importance": {"top": [{"feature": "체결강도"}]},
        },
        "coverage_gap": {
            "coverage_gap_id": "gap-1",
            "coverage_bucket_keys": ["strength_high", "open_0900_0910"],
        },
        "novelty_context": {"recent_axes": ["turnover_min_902"]},
        "validation_provenance": {"research_only": True},
    }
    base.update(overrides)
    return base


def test_build_research_context_pack_includes_parent_sha_and_full_sources():
    pack = build_research_context_pack(_sources())

    assert pack["parents"]["buy"]["id"] == "buy-1"
    assert pack["parents"]["buy"]["code"] == PARENT_BUY
    assert pack["parents"]["buy"]["sha256"] == hashlib.sha256(PARENT_BUY.encode("utf-8")).hexdigest()
    assert pack["parents"]["sell"]["sha256"] == hashlib.sha256(PARENT_SELL.encode("utf-8")).hexdigest()
    assert pack["parents"]["delivery_policy"] == "full_condition_code_required_not_id_only"
    asset_names = set(pack["stom_sources"]["asset_names"])
    assert {"strategy", "rules", "system_prompt", "variables_reference", "forbidden", "examples"}.issubset(asset_names)
    assert pack["mode"] == "process-research"
    assert DEFAULT_CONTEXT_PACK_MODE == "process-research"  # mode 미지정 시 기본값 계약.
    assert pack["authority"]["scope"] == "research_only"
    assert pack["authority"]["can_export"] is False
    assert pack["authority"]["can_live"] is False
    assert pack["authority"]["can_final_promote"] is False
    assert pack["budget"]["within_limit"] is True
    # 분석 카드/coverage_gap 은 extra_context 로 전달된다.
    assert pack["extra_context"]["analysis_card"]["analysis_id"] == "A_ctx_pack_test"
    assert pack["extra_context"]["coverage_gap"]["coverage_gap_id"] == "gap-1"
    # root_cause 는 analysis_card 에서 승계된다.
    assert pack["analysis"]["root_cause_summary"] == {"primary": "open giveback"}
    assert pack["analysis"]["feature_importance"] == {"top": [{"feature": "체결강도"}]}


def test_build_research_context_pack_budget_fail_closed():
    with pytest.raises(ValueError, match="research_context_pack_budget_exceeded"):
        build_research_context_pack(_sources(max_tokens=10))


def test_build_research_context_pack_clamps_max_tokens_to_fail_closed_ceiling():
    # 데이터로 250k fail-closed 예산을 상향할 수 없다 (min 클램프).
    from ai_strategy_loop.brain.prompt import MAX_RESEARCH_CONTEXT_PACK_TOKENS

    inflated = build_research_context_pack(_sources(max_tokens=999_999_999))
    assert inflated["budget"]["max_tokens"] == MAX_RESEARCH_CONTEXT_PACK_TOKENS
    # 하향은 계속 허용된다 (기존 예산 fail-closed 테스트와 정합).
    lowered = build_research_context_pack(_sources(max_tokens=249_999))
    assert lowered["budget"]["max_tokens"] == 249_999


def test_build_research_context_pack_fails_closed_when_stom_source_missing(monkeypatch):
    missing = prompt_mod._REPO_ROOT / "utility" / "ai_agent" / "__missing_required_source__.txt"
    monkeypatch.setattr(prompt_mod, "_FULL_STOM_SOURCE_ASSETS", (("missing_source", missing),))
    with pytest.raises(ValueError, match="research_context_pack_sources_missing"):
        build_research_context_pack(_sources())


def test_build_research_context_pack_requires_parent_full_code():
    with pytest.raises(ValueError, match="context_pack_parent_sources_missing"):
        build_research_context_pack(_sources(parent_sell_code=""))
    with pytest.raises(ValueError, match="context_pack_parent_sources_missing: buy,sell"):
        build_research_context_pack(_sources(parent_buy_code="", parent_sell_code="  "))
    with pytest.raises(ValueError, match="context_pack_sources_not_object"):
        build_research_context_pack(None)


def test_build_research_context_pack_optional_axis_priors_and_principle_docs():
    plain = build_research_context_pack(_sources())
    assert "axis_priors" not in plain["extra_context"]
    assert "principle_docs" not in plain["extra_context"]

    enriched = build_research_context_pack(_sources(
        axis_prompt_lines=["axis turnover_min_902: 2 trials, 0 wins"],
        principle_docs_enabled=True,
    ))
    assert enriched["extra_context"]["axis_priors"] == ["axis turnover_min_902: 2 trials, 0 wins"]
    docs = enriched["extra_context"]["principle_docs"]
    assert set(docs) == {"principles", "constraints_checklist", "idiom_dictionary"}
    for record in docs.values():
        assert record["content"].strip()
        assert record["sha256"] == hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
    assert enriched["budget"]["within_limit"] is True


def test_build_research_context_pack_rejects_authority_smuggling():
    with pytest.raises(ValueError, match="research_context_authority_smuggling"):
        build_research_context_pack(_sources(extra_context={"nested": {"can_live": True}}))


def test_build_context_pack_receipt_traces_id_and_sha_without_full_text():
    pack = build_research_context_pack(_sources())
    receipt = build_context_pack_receipt(pack)
    assert receipt["context_pack_id"] == pack["context_pack_id"]
    assert receipt["context_pack_sha256"] == pack["budget"]["rendered_sha256"]
    assert receipt["full_stom_sources_included"] is True
    assert receipt["prompt_budget_estimated_tokens"] == pack["budget"]["estimated_tokens"]
    assert PARENT_BUY not in str(receipt)
    assert build_context_pack_receipt(None)["context_pack_id"] == ""


def test_build_candidate_generation_context_matches_pack_producer_shape():
    pack = build_research_context_pack(_sources())
    context = build_candidate_generation_context(_sources(kind="buy", round_id="r1", prompt_score=3), context_pack=pack)
    assert context["kind"] == "buy"
    assert context["timeframe"] == "tick"
    assert context["parents"]["buy"]["code"] == PARENT_BUY
    assert context["parents"]["sell"]["code"] == PARENT_SELL
    assert context["research_context_pack"]["context_pack_id"] == pack["context_pack_id"]
    assert context["analysis_card"]["analysis_id"] == "A_ctx_pack_test"
    assert context["coverage_gap"]["coverage_gap_id"] == "gap-1"
    assert context["novelty_context"] == {"recent_axes": ["turnover_min_902"]}
    assert context["round_id"] == "r1"
    assert context["prompt_score"] == 3


def test_produce_research_candidate_pack_returns_none_on_terminal_failures():
    # 소스 부족(부모 전문 없음) → None → 결정론 폴백 자연 발동.
    assert produce_research_candidate_pack(_sources(parent_buy_code=""), lambda messages: "") is None
    # provider 예외는 terminal → None (재시도 없음 규약).
    def _raising_provider(messages):
        raise RuntimeError("provider down")
    assert produce_research_candidate_pack(_sources(), _raising_provider) is None
    # provider 미호출 가능 → None.
    assert produce_research_candidate_pack(_sources(), None) is None


def test_research_loop_config_context_pack_default_off():
    config = ResearchLoopConfig()
    assert config.context_pack_enabled is False
    from dataclasses import asdict
    assert asdict(config)["context_pack_enabled"] is False


def test_apply_research_context_pack_disabled_returns_same_object():
    config = ResearchLoopConfig()
    analysis_result = {"status": "ok", "recommended_candidates": []}
    out = research_loop._apply_research_context_pack(config, analysis_result, "base.csv")
    assert out is analysis_result  # 기본 OFF: 주입도 복사도 없다(byte-동일).


def test_apply_research_context_pack_records_error_without_blocking():
    # base_buy_strategy/sell_strategy 미지정 → 부모 전문 소스 부족 → 에러만 기록.
    config = ResearchLoopConfig(context_pack_enabled=True)
    analysis_result = {"status": "ok", "row_count": 10, "recommended_candidates": []}
    out = research_loop._apply_research_context_pack(config, analysis_result, "base.csv")
    assert out is not analysis_result
    assert "context_pack_parent_sources_missing" in out["context_pack_error"]
    assert "research_context_pack" not in out
    assert "context_pack_id" not in out
    assert out["status"] == "ok"
    assert out["row_count"] == 10
    assert "context_pack_error" not in analysis_result  # 입력 불변.


def test_apply_research_context_pack_injects_receipt_only_without_full_pack(monkeypatch):
    codes = {("B1", "buy"): PARENT_BUY, ("S1", "sell"): PARENT_SELL}
    monkeypatch.setattr(
        research_loop,
        "_load_condition_code",
        lambda name, strategy_type: codes.get((name, strategy_type), ""),
    )
    config = ResearchLoopConfig(
        context_pack_enabled=True,
        base_buy_strategy="B1",
        sell_strategy="S1",
        is_tick=True,
    )
    analysis_result = {"status": "ok", "row_count": 10, "recommended_candidates": [{"feature": "체결강도"}]}
    out = research_loop._apply_research_context_pack(config, analysis_result, "base.csv")
    # 관측/영수증 전용 — 팩 전문(최대 250k 토큰)은 결과에 영속하지 않는다.
    assert "research_context_pack" not in out
    receipt = out["research_context_pack_receipt"]
    assert set(receipt) == {
        "context_pack_id",
        "context_pack_sha256",
        "full_stom_sources_included",
        "prompt_budget_estimated_tokens",
    }
    assert out["context_pack_id"] == receipt["context_pack_id"]
    assert out["context_pack_sha256"] == receipt["context_pack_sha256"]
    assert receipt["context_pack_id"]
    assert receipt["context_pack_sha256"]
    assert receipt["full_stom_sources_included"] is True
    assert receipt["prompt_budget_estimated_tokens"] > 0
    assert "context_pack_error" not in out
    assert out["status"] == "ok"
    assert "research_context_pack_receipt" not in analysis_result  # 입력 불변.
    # 영수증 sha 는 동일 소스로 조립한 팩의 rendered_sha256 과 일치한다.
    sources = research_loop._context_pack_sources(config, analysis_result, "base.csv")
    pack = build_research_context_pack(sources)
    assert pack["parents"]["buy"]["sha256"] == hashlib.sha256(PARENT_BUY.encode("utf-8")).hexdigest()
    assert pack["timeframe"] == "tick"
    assert pack["mode"] == "fast-discovery"  # 기본 프리셋(fast) projection 의 process 값.
    assert out["context_pack_sha256"] == pack["budget"]["rendered_sha256"]
    assert pack["validation_provenance"]["baseline_csv"] == "base.csv"
    assert pack["validation_provenance"]["research_only"] is True


def test_build_result_promotes_context_pack_trace_fields_additively():
    enabled = ResearchLoopConfig(context_pack_enabled=True)
    result = research_loop._build_result(enabled, {
        "status": "ok",
        "analysis_result": {"status": "ok", "context_pack_id": "rcp_x", "context_pack_sha256": "sha_x"},
    })
    assert result["context_pack_id"] == "rcp_x"
    assert result["context_pack_sha256"] == "sha_x"

    # 기존 키가 항상 우선(additive 계약).
    result_existing = research_loop._build_result(enabled, {
        "status": "ok",
        "context_pack_id": "existing",
        "analysis_result": {"status": "ok", "context_pack_id": "rcp_x"},
    })
    assert result_existing["context_pack_id"] == "existing"

    disabled = ResearchLoopConfig()
    result_off = research_loop._build_result(disabled, {
        "status": "ok",
        "analysis_result": {"status": "ok", "context_pack_id": "rcp_x"},
    })
    assert "context_pack_id" not in result_off

    error_case = research_loop._build_result(enabled, {
        "status": "ok",
        "analysis_result": {"status": "ok", "context_pack_error": "boom"},
    })
    assert error_case["context_pack_error"] == "boom"


# ===================================================================
# DR-04 -- final-owner wiring threaded through produce_research_candidate_pack.
# ===================================================================


def test_produce_research_candidate_pack_final_owner_disabled_by_default(monkeypatch):
    import ai_strategy_loop.controller.context_pack_builder as ctx_mod

    captured = {}

    def _fake_produce_candidate_pack(context, provider, *, lanes=None, axis_prompt_lines=None):
        captured["called_plain"] = True
        return {"schema_version": 1, "candidates": []}

    def _fake_produce_candidate_pack_result(context, provider, **kwargs):
        captured["kwargs"] = kwargs
        return {"candidate_pack": {"schema_version": 1, "candidates": []}}

    monkeypatch.setattr(ctx_mod, "produce_candidate_pack", _fake_produce_candidate_pack)
    monkeypatch.setattr(ctx_mod, "produce_candidate_pack_result", _fake_produce_candidate_pack_result)

    pack = produce_research_candidate_pack(_sources(), lambda messages: "ignored")
    assert captured.get("called_plain") is True
    assert "kwargs" not in captured
    assert pack == {"schema_version": 1, "candidates": []}


def test_produce_research_candidate_pack_final_owner_enabled_routes_through_result(monkeypatch):
    import ai_strategy_loop.controller.context_pack_builder as ctx_mod

    captured = {}

    def _fake_produce_candidate_pack_result(context, provider, **kwargs):
        captured["kwargs"] = kwargs
        return {
            "candidate_pack": {
                "schema_version": 1,
                "candidates": [],
                "final_owner_selection": {"selected": {"candidate_id": "x"}, "pool_blockers": []},
            },
        }

    monkeypatch.setattr(ctx_mod, "produce_candidate_pack_result", _fake_produce_candidate_pack_result)

    pack = produce_research_candidate_pack(
        _sources(), lambda messages: "ignored", final_owner_enabled=True, methodology_version="clr04_v1",
    )
    assert captured["kwargs"]["final_owner_enabled"] is True
    assert captured["kwargs"]["methodology_version"] == "clr04_v1"
    assert pack["final_owner_selection"]["selected"]["candidate_id"] == "x"


def test_research_loop_config_final_owner_selection_default_off():
    config = ResearchLoopConfig()
    assert config.final_owner_selection_enabled is False
    from dataclasses import asdict
    assert asdict(config)["final_owner_selection_enabled"] is False
