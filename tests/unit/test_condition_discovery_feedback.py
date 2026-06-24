import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.condition_discovery_feedback import (  # noqa: E402
    build_feedback_page_data,
    build_pattern_card,
    build_persistence_state,
    normalize_hypotheses,
    strip_numeric_thresholds,
    validate_pattern_card_usage,
)


def test_persistence_state_blocks_research_when_prompt_or_equity_missing():
    cfg = LoopConfig(condition_discovery_preset="research")
    state = build_persistence_state(cfg, prompt_records=None, equity_points=None)
    assert state["status"] == "evidence_blocker"
    assert "missing_prompt_persistence" in state["blockers"]
    assert "missing_equity_persistence" in state["blockers"]

    enabled = LoopConfig(
        condition_discovery_preset="research",
        prompt_logging_enabled=True,
        equity_points_enabled=True,
    )
    ok = build_persistence_state(enabled, prompt_records=2, equity_points=10)
    assert ok["status"] == "complete"
    assert ok["blockers"] == []


def test_fast_persistence_keeps_prompt_equity_optional_when_disabled():
    cfg = LoopConfig(condition_discovery_preset="fast")
    state = build_persistence_state(cfg)
    assert state["status"] == "complete"
    assert {item["status"] for item in state["items"]} == {"not_required"}


def test_hypotheses_are_advisory_with_provenance_and_safe_status():
    payload = normalize_hypotheses(
        [
            {"id": "h1", "status": "accepted", "hypothesis": "tighten exits", "source": "autopsy", "evidence": "mdd high"},
            {"id": "h2", "status": "promote", "text": "copy winner"},
        ]
    )
    assert payload["status"] == "ok"
    assert payload["items"][0]["advisory_only"] is True
    assert payload["items"][0]["provenance"] == "mdd high"
    assert payload["items"][1]["status"] == "deferred"
    mixed = normalize_hypotheses(["raw text hypothesis"])
    assert mixed["items"][0]["hypothesis"] == "raw text hypothesis"
    assert mixed["items"][0]["status"] == "deferred"


def test_pattern_card_strips_thresholds_and_rejects_performance_truth():
    card = build_pattern_card(
        card_id="human-open-liquidity",
        source_label="human-db:sample",
        side="buy",
        expression="시분초 >= 90000 and 시분초 <= 92800 and 당일거래대금 > 1500 and 체결강도 > 120",
        pattern_summary="09:00~09:28 liquidity acceleration with 체결강도 120 이상",
        variable_families=["time", "liquidity", "orderflow"],
        composition_tags=["opening", "liquidity_accel"],
        performance={"profit": 123456, "mdd": 7.2},
    )
    assert "90000" not in card["composition_skeleton"]
    assert "1500" not in card["composition_skeleton"]
    assert "120" not in card["allowed_prompt_excerpt"]
    assert "120" not in card["pattern_summary"]
    assert card["performance_imported"] is False
    assert card["rejected_performance_fields"] == ["mdd", "profit"]
    assert card["authority"] == "creativity_seed_only_not_performance_truth"

    same = validate_pattern_card_usage(
        "시분초 >= 90000 and 시분초 <= 92800 and 당일거래대금 > 1500 and 체결강도 > 120",
        card,
    )
    assert same["status"] == "blocked"
    assert "full_expression_copy" in same["blockers"]
    assert "threshold_copy" in same["blockers"]

    structural = validate_pattern_card_usage(
        "시분초 >= 90500 and 시분초 <= 92000 and 당일거래대금 > 2100 and 체결강도 > 135",
        card,
    )
    assert structural["status"] == "ok"

    partial_copy = validate_pattern_card_usage(
        "시분초 >= 90000 and 시분초 <= 92000 and 당일거래대금 > 2100 and 체결강도 > 135",
        card,
    )
    assert partial_copy["status"] == "blocked"
    assert "threshold_copy" in partial_copy["blockers"]

    equivalent_copy = validate_pattern_card_usage(
        "체결강도 > +1.2e2 and 당일거래대금 > 1.500e3 and 시분초 <= 92800.0 and 시분초 >= 90000",
        card,
    )
    assert equivalent_copy["status"] == "blocked"
    assert "threshold_copy" in equivalent_copy["blockers"]

    perf = validate_pattern_card_usage("체결강도 > 135", card, imported_performance={"profit": 1})
    assert "performance_truth_import" in perf["blockers"]


def test_pattern_card_blocks_format_changed_full_expression_without_thresholds():
    card = build_pattern_card(
        card_id="human-orderflow",
        source_label="human-db:orderflow",
        side="buy",
        expression="체결강도상승 and 호가압력강함",
        pattern_summary="orderflow pressure confirmation",
        variable_families=["orderflow"],
    )
    copied = validate_pattern_card_usage("체결강도상승    and    호가압력강함", card)
    assert copied["status"] == "blocked"
    assert "full_expression_copy" in copied["blockers"]


def test_feedback_page_data_combines_sections_without_authority():
    cfg = LoopConfig(condition_discovery_preset="promotion", prompt_logging_enabled=True, equity_points_enabled=True)
    card = build_pattern_card(
        card_id="c1",
        source_label="human-db:x",
        side="sell",
        expression="수익률 < -2 or 보유시간 > 20",
        pattern_summary="loss cut plus time exit",
        variable_families=["return", "time"],
    )
    payload = build_feedback_page_data(
        cfg,
        prompt_records=1,
        equity_points=5,
        hypotheses=[{"id": "h1", "status": "rejected", "hypothesis": "loosen entry"}],
        pattern_cards=[card],
    )
    assert payload["schema_version"] == 1
    assert payload["persistence"]["status"] == "complete"
    assert payload["hypotheses"]["items"][0]["status"] == "rejected"
    assert payload["pattern_cards"]["items"][0]["card_id"] == "c1"
    assert "no_threshold" in payload["pattern_cards"]["authority"]


def test_strip_numeric_thresholds_removes_signed_and_decimal_numbers():
    assert strip_numeric_thresholds("수익률 <= -2.5 and 거래대금 > 1500") == "수익률 <= <N> and 거래대금 > <N>"
    assert strip_numeric_thresholds("체결강도120이상 and 거래대금1500이상") == "체결강도<N>이상 and 거래대금<N>이상"
    assert strip_numeric_thresholds("비율>.5 and 체결강도>1.2e2") == "비율><N> and 체결강도><N>"
