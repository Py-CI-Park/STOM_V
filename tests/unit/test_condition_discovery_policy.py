import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.condition_discovery import (  # noqa: E402
    RESEARCH_ANALYSIS_CARD_VERSION,
    assess_discovery_novelty,
    build_evidence_health,
    build_insight_score,
    build_research_analysis_card,
    build_research_observability_contract,
    build_validation_provenance,
    effective_condition_discovery_runtime_config,
    merge_condition_discovery_page_data,
    normalize_condition_discovery_preset,
    normalize_condition_discovery_process,
    resolve_condition_discovery_process_projection,
    resolve_condition_discovery_policy,
    resolve_hybrid_research_slots,
    resolve_time_window_policy,
    score_research_lane,
    validation_promotion_blockers,
)
from ai_strategy_loop.controller.state import build_active_config  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402


def test_condition_discovery_preset_validation_and_field_spec():
    assert normalize_condition_discovery_preset("Research") == "research"
    with pytest.raises(ValueError):
        normalize_condition_discovery_preset("live")
    with pytest.raises(ValueError):
        config_from_dict({"condition_discovery_preset": "live"})

    cfg = config_from_dict({"condition_discovery_preset": "promotion"})
    assert cfg.condition_discovery_preset == "promotion"
    specs = {s["name"]: s for s in config_field_specs()}
    assert specs["condition_discovery_preset"]["choices"] == ["fast", "research", "promotion"]
    assert specs["condition_discovery_preset"]["default"] == LoopConfig().condition_discovery_preset

    assert normalize_condition_discovery_process("1") == "fast-discovery"
    assert normalize_condition_discovery_process("process-research") == "process-research"
    assert resolve_condition_discovery_process_projection("3") == {
        "process": "promotion-review",
        "preset": "promotion",
    }
    assert specs["condition_discovery_process"]["choices"] == [
        "fast-discovery",
        "process-research",
        "promotion-review",
    ]
    fast_entry = next(entry for entry in resolve_condition_discovery_policy(LoopConfig())["process_catalog"] if entry["number"] == 1)
    research_entry = next(entry for entry in resolve_condition_discovery_policy(LoopConfig())["process_catalog"] if entry["number"] == 2)
    assert "smoke_or_full_period_backtest" in fast_entry["research_actions"]
    assert "full_period_validation" in research_entry["research_actions"]
    assert "production_promote" in research_entry["blocked_actions"]
    assert "전체기간" in research_entry["quick_start"]
    assert specs["condition_discovery_process"]["default"] is None


def test_condition_discovery_process_selector_and_preset_projection():
    preset_only = config_from_dict({"condition_discovery_preset": "research"})
    assert preset_only.condition_discovery_process == "process-research"
    assert preset_only.condition_discovery_preset == "research"

    selector_only = config_from_dict({"condition_discovery_process": "2"})
    assert selector_only.condition_discovery_process == "process-research"
    assert selector_only.condition_discovery_preset == "research"

    code_selector = config_from_dict({"condition_discovery_process": "promotion-review"})
    assert code_selector.condition_discovery_process == "promotion-review"
    assert code_selector.condition_discovery_preset == "promotion"

    explicit_match = config_from_dict({
        "condition_discovery_process": "1",
        "condition_discovery_preset": "fast",
    })
    assert explicit_match.condition_discovery_process == "fast-discovery"
    assert explicit_match.condition_discovery_preset == "fast"

    with pytest.raises(ValueError, match="condition_discovery_process"):
        config_from_dict({
            "condition_discovery_process": "1",
            "condition_discovery_preset": "research",
        })

    snapshot = build_active_config(selector_only)
    assert snapshot["condition_discovery_process"] == "process-research"
    assert snapshot["condition_discovery_preset"] == "research"


def test_research_tick_policy_uses_opening_window_and_staged_mdd():
    cfg = LoopConfig(condition_discovery_preset="research", bt_timeframe="tick", mdd_cap=40.0)
    payload = resolve_condition_discovery_policy(cfg)
    assert payload["preset"] == "research"
    assert payload["time_window"]["start_time"] == 90000
    assert payload["time_window"]["end_time"] == 92800
    assert payload["hard_gates"]["mdd"]["cap"] == 25.0
    assert payload["authority"]["performance_score_100"] == "advisory_only"
    assert payload["current_process"]["code"] == "process-research"
    assert payload["process"]["code"] == "process-research"
    assert payload["capabilities"]["can_promote"] is False
    assert payload["capabilities"]["can_export"] is False
    assert payload["capabilities"]["can_live"] is False
    assert payload["capabilities"]["research_execution_allowed"] is True
    assert payload["capabilities"]["full_period_research_allowed"] is True
    assert payload["capabilities"]["condition_generation_allowed"] is True
    assert payload["capabilities"]["condition_improvement_allowed"] is True
    assert [entry["code"] for entry in payload["process_catalog"]] == [
        "fast-discovery",
        "process-research",
        "promotion-review",
    ]

def test_tick_research_window_default_stays_fixed_without_subband_override():
    cfg = LoopConfig(condition_discovery_preset="research", bt_timeframe="tick", mdd_cap=40.0)
    window = resolve_time_window_policy(cfg)
    assert window["start_time"] == 90000
    assert window["end_time"] == 92800
    assert window["source"] == "condition_discovery_tick_research_window"
    assert window["boundary_status"] == "fixed"

    effective = effective_condition_discovery_runtime_config(cfg)
    assert effective.bt_universe_start_time == 90000
    assert effective.bt_universe_end_time == 92800


def test_tick_research_window_applies_valid_subband_for_research_preset():
    cfg = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        mdd_cap=40.0,
        condition_discovery_tick_window_start=90500,
        condition_discovery_tick_window_end=92000,
    )
    window = resolve_time_window_policy(cfg)
    assert window["start_time"] == 90500
    assert window["end_time"] == 92000
    assert window["source"] == "condition_discovery_tick_research_subband"
    assert window["boundary_status"] == "configured_subband"
    assert window["full_session_required"] is False

    effective = effective_condition_discovery_runtime_config(cfg)
    assert effective.bt_universe_start_time == 90500
    assert effective.bt_universe_end_time == 92000

    payload = resolve_condition_discovery_policy(cfg)
    assert payload["time_window"]["start_time"] == 90500
    assert payload["time_window"]["end_time"] == 92000
    assert payload["capabilities"]["can_promote"] is False


def test_tick_research_window_partial_override_and_lattice_band_max_end():
    start_only = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        condition_discovery_tick_window_start=91000,
    )
    window = resolve_time_window_policy(start_only)
    assert (window["start_time"], window["end_time"]) == (91000, 92800)
    assert window["boundary_status"] == "configured_subband"

    # 격자(seeds/lattice.py TICK_BANDS)의 마지막 밴드 상한 93000까지 허용.
    max_end = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        condition_discovery_tick_window_end=93000,
    )
    effective = effective_condition_discovery_runtime_config(max_end)
    assert effective.bt_universe_start_time == 90000
    assert effective.bt_universe_end_time == 93000


def test_tick_research_window_rejects_out_of_band_or_reversed_subband():
    invalid_windows = (
        (85900, 92000),  # 90000 미만 시작
        (90000, 93100),  # 93000 초과 종료
        (92000, 91000),  # 역전 창
        (91500, 91500),  # 빈 창
    )
    for start, end in invalid_windows:
        cfg = LoopConfig(
            condition_discovery_preset="research",
            bt_timeframe="tick",
            condition_discovery_tick_window_start=start,
            condition_discovery_tick_window_end=end,
        )
        with pytest.raises(ValueError, match="condition_discovery_tick_window"):
            resolve_time_window_policy(cfg)
        with pytest.raises(ValueError, match="condition_discovery_tick_window"):
            effective_condition_discovery_runtime_config(cfg)

    non_numeric = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        condition_discovery_tick_window_start="open",
    )
    with pytest.raises(ValueError, match="condition_discovery_tick_window"):
        resolve_time_window_policy(non_numeric)


def test_tick_research_window_rejects_float_truncation_and_bool():
    # 소수부가 있는 float 는 int() 묵시 절단 없이 fail-closed 거부한다.
    for start, end in ((90500.7, 92000), (90500, 92000.5)):
        cfg = LoopConfig(
            condition_discovery_preset="research",
            bt_timeframe="tick",
            condition_discovery_tick_window_start=start,
            condition_discovery_tick_window_end=end,
        )
        with pytest.raises(ValueError, match="condition_discovery_tick_window"):
            resolve_time_window_policy(cfg)

    bool_cfg = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        condition_discovery_tick_window_start=True,
    )
    with pytest.raises(ValueError, match="condition_discovery_tick_window"):
        resolve_time_window_policy(bool_cfg)

    # 정수값 float(90500.0)은 손실이 없으므로 허용된다.
    lossless = LoopConfig(
        condition_discovery_preset="research",
        bt_timeframe="tick",
        condition_discovery_tick_window_start=90500.0,
        condition_discovery_tick_window_end=92000.0,
    )
    window = resolve_time_window_policy(lossless)
    assert (window["start_time"], window["end_time"]) == (90500, 92000)


def test_tick_research_window_rejects_invalid_hhmmss_minute_second():
    # 범위([90000, 93000])는 지나지만 분·초가 60 이상인 HHMMSS 를 거부한다.
    invalid_windows = (
        (90090, 92000),  # start 초=90
        (90000, 92999),  # end 분=29, 초=99
        (90060, 92000),  # start 초=60 경계
    )
    for start, end in invalid_windows:
        cfg = LoopConfig(
            condition_discovery_preset="research",
            bt_timeframe="tick",
            condition_discovery_tick_window_start=start,
            condition_discovery_tick_window_end=end,
        )
        with pytest.raises(ValueError, match="condition_discovery_tick_window"):
            resolve_time_window_policy(cfg)
        with pytest.raises(ValueError, match="condition_discovery_tick_window"):
            effective_condition_discovery_runtime_config(cfg)


def test_tick_window_override_is_ignored_for_fast_and_promotion_presets():
    for preset in ("fast", "promotion"):
        cfg = LoopConfig(
            condition_discovery_preset=preset,
            bt_timeframe="tick",
            mdd_cap=40.0,
            condition_discovery_tick_window_start=90500,
            condition_discovery_tick_window_end=92000,
        )
        window = resolve_time_window_policy(cfg)
        assert window["start_time"] == 90000
        assert window["end_time"] == 92800
        assert window["source"] == "condition_discovery_tick_research_window"
        assert window["boundary_status"] == "fixed"

        effective = effective_condition_discovery_runtime_config(cfg)
        assert effective.bt_universe_start_time == 90000
        assert effective.bt_universe_end_time == 92800


def test_fast_policy_and_stricter_configured_mdd_are_pinned():
    fast = resolve_condition_discovery_policy(
        LoopConfig(condition_discovery_preset="fast", bt_timeframe="tick", mdd_cap=40.0)
    )
    assert fast["policy"]["oos_mode"] == "disabled"
    assert fast["policy"]["promotion_candidate_allowed"] is False
    assert fast["policy"]["human_approval_required"] is True
    assert fast["hard_gates"]["mdd"]["cap"] == 35.0

    stricter = resolve_condition_discovery_policy(
        LoopConfig(condition_discovery_preset="research", bt_timeframe="tick", mdd_cap=10.0)
    )
    assert stricter["hard_gates"]["mdd"]["preset_cap"] == 25.0
    assert stricter["hard_gates"]["mdd"]["configured_cap"] == 10.0
    assert stricter["hard_gates"]["mdd"]["cap"] == 10.0


def test_promotion_min_policy_requires_full_session_boundary_candidate():
    cfg = LoopConfig(
        condition_discovery_preset="promotion",
        bt_timeframe="min",
        bt_min_universe_end_time=151900,
        mdd_cap=20.0,
    )
    window = resolve_time_window_policy(cfg)
    assert window["full_session_required"] is True
    assert window["start_time"] == 90000
    assert window["end_time"] == 151900
    assert window["boundary_status"] == "verified_candidate"

    payload = resolve_condition_discovery_policy(cfg)
    assert payload["hard_gates"]["mdd"]["cap"] == 15.0
    assert payload["policy"]["human_approval_required"] is True
    assert payload["current_process"]["code"] == "promotion-review"
    assert payload["capabilities"]["can_promote"] is False
    assert payload["capabilities"]["promotion_review_allowed"] is True
    assert payload["capabilities"]["research_execution_allowed"] is False
    assert payload["capabilities"]["full_period_research_allowed"] is False
    assert payload["capabilities"]["promotion_requirements"] == {
        "frozen_snapshot_required": True,
        "evidence_health_required": True,
        "hard_gates_required": True,
        "human_approval_required": True,
    }
    assert "requires_frozen_snapshot" in payload["capabilities"]["blockers"]
    assert "requires_human_approval" in payload["capabilities"]["blockers"]
def test_effective_runtime_policy_applies_staged_mdd_oos_and_min_full_session():
    raw = LoopConfig(
        condition_discovery_preset="promotion",
        bt_timeframe="min",
        mdd_cap=35.0,
        research_oos_mode="disabled",
        full_session_enabled=False,
        bt_universe_end_time=92800,
        bt_min_universe_end_time=151900,
    )
    effective = effective_condition_discovery_runtime_config(raw)
    assert raw.mdd_cap == 35.0
    assert effective.mdd_cap == 15.0
    assert effective.condition_discovery_configured_mdd_cap == 35.0
    assert effective.research_oos_mode == "promotion_only"
    assert effective.full_session_enabled is True
    assert effective.bt_universe_start_time == 90000
    assert effective.bt_universe_end_time == 151900

    payload = resolve_condition_discovery_policy(effective)
    assert payload["hard_gates"]["mdd"]["configured_cap"] == 35.0
    assert payload["hard_gates"]["mdd"]["cap"] == 15.0



def test_evidence_health_blocks_promotion_but_keeps_fast_prompt_optional():
    fast = build_evidence_health({"csv": True, "trades": True, "validation": True}, preset="fast")
    assert fast["overall"] == "complete"
    prompt = next(c for c in fast["components"] if c["name"] == "prompt")
    assert prompt["required"] is False
    assert prompt["status"] == "not_required"
    assert fast["blockers"] == []

    promotion = build_evidence_health({"csv": True, "trades": True, "validation": True}, preset="promotion")
    assert promotion["overall"] == "evidence_blocker"
    assert "missing_or_invalid_prompt_evidence" in promotion["blockers"]
    assert "missing_or_invalid_equity_evidence" in promotion["blockers"]
    assert promotion["promotion_blocked"] is True

    bypass_attempt = build_evidence_health(
        {
            "csv": True,
            "trades": True,
            "validation": True,
            "prompt": "not_required",
            "equity": {"status": "not_required"},
        },
        preset="promotion",
    )
    assert bypass_attempt["overall"] == "evidence_blocker"
    assert "missing_or_invalid_prompt_evidence" in bypass_attempt["blockers"]
    assert "missing_or_invalid_equity_evidence" in bypass_attempt["blockers"]


def test_condition_discovery_page_data_merge_is_additive_and_null_safe():
    cfg = LoopConfig(condition_discovery_preset="fast")
    merged = merge_condition_discovery_page_data({"autopsy": {"status": "ok"}}, cfg)
    assert merged["autopsy"] == {"status": "ok"}
    assert merged["condition_discovery"]["schema_version"] == 1
    assert merged["condition_discovery"]["evidence_health"]["overall"] == "evidence_blocker"

    empty = merge_condition_discovery_page_data(None, cfg, evidence={"csv": True, "trades": True, "validation": True})
    assert set(empty) == {"condition_discovery"}
    assert empty["condition_discovery"]["evidence_health"]["overall"] == "complete"


def _complete_research_evidence():
    return {
        "csv": True,
        "trades": True,
        "equity": True,
        "prompt": True,
        "validation": True,
    }


def _candidate(
    candidate_id,
    lane,
    *,
    profit,
    mdd,
    parent_profit=1000,
    parent_mdd=10,
    insight_score=70,
    prompt_score=70,
    evidence=None,
    oos_status="none",
    **extra,
):
    payload = {
        "candidate_id": candidate_id,
        "lane": lane,
        "metrics": {"profit": profit, "mdd": mdd},
        "parent_metrics": {"profit": parent_profit, "mdd": parent_mdd},
        "insight_score": insight_score,
        "prompt_score": prompt_score,
        "evidence": _complete_research_evidence() if evidence is None else evidence,
        "oos_status": oos_status,
    }
    payload.update(extra)
    return payload


def test_research_loop_policy_payload_is_additive_and_safe():
    payload = resolve_condition_discovery_policy(LoopConfig(condition_discovery_preset="research"))

    assert payload["research_loop"]["slots_total"] == 4
    assert payload["research_loop"]["default_slots"] == {"repair": 2, "discovery": 2}
    assert payload["research_loop"]["max_slot_shift"] == 1
    assert payload["capabilities"]["can_promote"] is False
    assert payload["capabilities"]["can_export"] is False
    assert payload["capabilities"]["can_live"] is False
    assert payload["authority"]["performance_score_100"] == "advisory_only"


def test_research_observability_contract_pins_context_pack_and_promotion_authority():
    research_payload = resolve_condition_discovery_policy(
        LoopConfig(condition_discovery_process="process-research", condition_discovery_preset="research")
    )
    research_obs = research_payload["research_observability"]

    assert research_obs["mode_authority"]["generation_allowed"] is True
    assert research_obs["mode_authority"]["promotion_review_zero_generation"] is False
    assert research_obs["context_pack_health"]["fail_closed_budget_tokens"] == 250000
    assert "context_pack_id" in research_obs["context_pack_health"]["required_fields"]
    assert "context_pack_sha256" in research_obs["context_pack_health"]["required_fields"]
    assert "multi_hypothesis_candidate_pack" in [
        step["step"] for step in research_obs["branch_tree"]
    ]
    assert research_obs["candidate_pack"]["min_candidates"] == 2
    assert research_obs["candidate_pack"]["recommended_candidates"] == "2-3+"
    assert research_obs["candidate_pack"]["fallback_source"] == "diagnostic_deterministic_candidate_fallback"
    assert research_obs["analysis_cards"]["schema"] == RESEARCH_ANALYSIS_CARD_VERSION
    assert "official_backtest_result" in research_obs["prompt_receipts"]["required_fields"]
    assert research_obs["promotion_blockers"]["authority"].startswith("promotion_requires_")

    promotion_payload = resolve_condition_discovery_policy(
        LoopConfig(condition_discovery_process="promotion-review", condition_discovery_preset="promotion")
    )
    promotion_obs = promotion_payload["research_observability"]

    assert promotion_obs["mode_authority"]["generation_allowed"] is False
    assert promotion_obs["mode_authority"]["promotion_review_zero_generation"] is True
    assert promotion_obs["promotion_blockers"]["generation_allowed"] is False
    assert "requires_frozen_snapshot" in promotion_obs["promotion_blockers"]["blockers"]
    assert promotion_payload["capabilities"]["condition_generation_allowed"] is False



def test_research_lane_scoring_and_hybrid_slot_allocation():
    repair_lane = score_research_lane([
        _candidate("repair-win", "repair", profit=1290, mdd=12),
    ])
    discovery_lane = score_research_lane([
        _candidate("discovery-lag", "discovery", profit=1140, mdd=12),
    ])

    assert repair_lane["lane_score"] == pytest.approx(34.0)
    assert discovery_lane["lane_score"] == pytest.approx(19.0)
    allocation = resolve_hybrid_research_slots({
        "repair_lane": repair_lane,
        "discovery_lane": discovery_lane,
    })
    assert allocation["slots_by_lane"] == {"repair": 3, "discovery": 1}
    assert allocation["decision_reason"] == "lane_score_advantage"

    discovery_win = score_research_lane([
        _candidate("discovery-win", "discovery", profit=1400, mdd=9, insight_score=85, prompt_score=85),
    ])
    allocation = resolve_hybrid_research_slots({
        "repair_lane": repair_lane,
        "discovery_lane": discovery_win,
    })
    assert allocation["slots_by_lane"] == {"repair": 1, "discovery": 3}
    assert allocation["better_lane"] == "discovery"


def test_research_lane_scoring_blocks_or_caps_bad_evidence_and_mdd():
    missing_evidence = score_research_lane([
        _candidate("missing-evidence", "repair", profit=1300, mdd=8, evidence={"csv": True}),
    ])
    assert missing_evidence["lane_score"] == -10000.0
    assert "missing_or_invalid_required_evidence" in missing_evidence["blockers"]

    no_metrics = score_research_lane([
        {"candidate_id": "no-metrics", "lane": "repair", "evidence": _complete_research_evidence()},
    ])
    assert no_metrics["lane_score"] == -9000.0
    assert no_metrics["best_candidate_score_detail"]["failure_reason"] == "no_official_metrics"

    severe_mdd = score_research_lane([
        _candidate("severe-mdd", "repair", profit=1500, mdd=32),
    ])
    assert severe_mdd["lane_score"] == -5000.0
    assert "severe_mdd_veto_cap_multiplier" in severe_mdd["blockers"]

    capped = score_research_lane([
        _candidate("capped-mdd", "repair", profit=1600, mdd=28, parent_mdd=24),
    ])
    assert capped["advantage_capped"] is True
    assert capped["lane_score"] == 0.0
    assert "mdd_cap_pressure_advantage_capped" in capped["caps_applied"]

    allocation = resolve_hybrid_research_slots({
        "repair_lane": capped,
        "discovery_lane": score_research_lane([]),
    })
    assert allocation["slots_by_lane"] == {"repair": 2, "discovery": 2}
    assert allocation["decision_reason"] == "only_eligible_lane_advantage_capped"


def test_research_lane_tiebreaks_include_oos_and_mdd_quality():
    clean = score_research_lane([
        _candidate("clean", "repair", profit=1290, mdd=12),
    ])
    oos_failed = score_research_lane([
        _candidate("oos-failed", "discovery", profit=1290, mdd=12, oos_status="fail"),
    ])
    assert clean["lane_score"] > oos_failed["lane_score"]

    lower_mdd = score_research_lane([
        _candidate("lower-mdd", "repair", profit=1210, mdd=10, parent_mdd=10),
    ])
    higher_mdd = score_research_lane([
        _candidate("higher-mdd", "discovery", profit=1210, mdd=14, parent_mdd=10),
    ])
    allocation = resolve_hybrid_research_slots({
        "repair_lane": lower_mdd,
        "discovery_lane": higher_mdd,
    })
    assert allocation["better_lane"] == "repair"
    assert allocation["decision_reason"] in {"lane_score_advantage", "mdd_delta_tiebreak"}


def test_insight_score_caps_and_research_analysis_card():
    weak = build_insight_score({})
    assert weak["score"] == 0
    assert {"cap": 20, "reason": "no_official_metrics"} in weak["caps_applied"]

    card = build_research_analysis_card(
        analysis_id="analysis-1",
        candidate_id="candidate-1",
        lane="repair",
        metrics={"profit": 1000, "mdd": 8},
        parent_comparison={"profit_delta": 50, "mdd_delta_pp": -1},
        root_cause={"primary": "late exits"},
        segment_contribution={"open": 0.8},
        next_recommendation="tighten only the late-exit condition",
        context_pack_id="rcp-1",
        parent_buy_id="buy-parent",
        parent_buy_code="if 현재가 > 시가:\n    self.Buy()",
        parent_sell_id="sell-parent",
        parent_sell_code="if 수익률 < -1:\n    self.Sell()",
        segment_heatmap=[{"time": "0900", "cap": "small", "profit": -5}],
        feature_importance={"top": [{"feature": "체결강도", "direction": "high"}]},
        edge_ratio={"edge_ratio": 1.4},
        mfe_mae={"mfe": 2.1, "mae": -0.8},
        correlation_redundancy={"redundant_groups": [["체결강도", "체결강도평균"]]},
        avoid_zones=["small-open-loss"],
        prefer_zones=["mid-morning-positive"],
        mutation_axis="sell_trailing_only",
        expected_effect="reduce giveback",
        risk_note="may reduce trades",
        evidence_health=build_evidence_health(_complete_research_evidence(), preset="research"),
    )
    assert card["insight_score"]["score"] == 100
    assert card["authority"] == "research_analysis_card_only"
    assert card["safety_flags"]["can_promote"] is False
    assert card["analysis_card_version"] == RESEARCH_ANALYSIS_CARD_VERSION
    assert card["context_pack_id"] == "rcp-1"
    assert card["official_metrics"] == {"profit": 1000, "mdd": 8}
    assert card["parent_conditions"]["buy"]["id"] == "buy-parent"
    assert card["parent_conditions"]["buy"]["sha256"]
    assert card["parent_conditions"]["sell"]["id"] == "sell-parent"
    assert card["analysis_inputs"]["segment_heatmap"][0]["cap"] == "small"
    assert card["analysis_inputs"]["correlation_redundancy"]["redundant_groups"][0][0] == "체결강도"
    assert card["mutation_contract"]["mutation_axis"] == "sell_trailing_only"
    assert card["research_authority_flags"]["can_final_promote"] is False

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-smuggle",
            candidate_id="candidate-smuggle",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            research_authority_flags={"can_live": True},
        )

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-production-ready",
            candidate_id="candidate-production-ready",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            research_authority_flags={"production_ready": True},
        )

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-safety-smuggle",
            candidate_id="candidate-safety-smuggle",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            safety_flags={"research_only": False, "can_export": True},
        )

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-nested-smuggle",
            candidate_id="candidate-nested-smuggle",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            safety_flags={"nested": {"can_live": True}},
        )

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-root-cause-smuggle",
            candidate_id="candidate-root-cause-smuggle",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            root_cause={"nested": {"can_live": True}},
        )

    with pytest.raises(ValueError, match="research_authority_smuggling"):
        build_research_analysis_card(
            analysis_id="analysis-validation-smuggle",
            candidate_id="candidate-validation-smuggle",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            validation_provenance={"promotion_claim": True},
        )

    safe_provenance_card = build_research_analysis_card(
        analysis_id="analysis-safe-provenance",
        candidate_id="candidate-safe-provenance",
        lane="repair",
        metrics={"profit": 1000, "mdd": 8},
        validation_provenance=build_validation_provenance(
            used_for_prompt_or_allocation=True,
            frozen=False,
            fresh_holdout=False,
        ),
    )
    assert safe_provenance_card["validation_provenance"]["promotion_eligible"] is False

    with pytest.raises(ValueError, match="parent_condition_hash_mismatch"):
        build_research_analysis_card(
            analysis_id="analysis-bad-hash",
            candidate_id="candidate-bad-hash",
            lane="repair",
            metrics={"profit": 1000, "mdd": 8},
            parent_buy_code="if 현재가 > 시가:\n    self.Buy()",
            parent_buy_sha256="not-the-real-sha",
        )


def test_discovery_novelty_requires_structure_coverage_family_and_evidence():
    comparator = {
        "candidate_id": "existing",
        "structural_fingerprint": "fingerprint-a",
        "coverage_bucket_keys": ["opening-momentum"],
        "entry_exit_family": "breakout",
    }
    novel = assess_discovery_novelty(
        {
            "candidate_id": "new",
            "structural_fingerprint": "fingerprint-b",
            "coverage_bucket_keys": ["turnover-reversal"],
            "entry_exit_family": "reversal",
            "evidence": _complete_research_evidence(),
        },
        [comparator],
    )
    assert novel["passes_discovery_credit"] is True
    assert novel["failed_dimensions"] == []

    duplicate = assess_discovery_novelty(
        {
            "candidate_id": "dup",
            "structural_fingerprint": "fingerprint-a",
            "coverage_bucket_keys": ["opening-momentum"],
            "entry_exit_family": "breakout",
            "evidence": {"csv": True},
        },
        [comparator],
    )
    assert duplicate["passes_discovery_credit"] is False
    assert set(duplicate["failed_dimensions"]) == {
        "structural_fingerprint",
        "coverage_regime",
        "entry_exit_family",
        "complete_research_evidence",
    }

    explicit_empty_evidence = assess_discovery_novelty(
        {
            "candidate_id": "empty-evidence",
            "structural_fingerprint": "fingerprint-c",
            "coverage_bucket_keys": ["gap"],
            "entry_exit_family": "mean-reversion",
            "evidence": _complete_research_evidence(),
        },
        [comparator],
        evidence={},
    )
    assert explicit_empty_evidence["passes_discovery_credit"] is False
    assert "complete_research_evidence" in explicit_empty_evidence["failed_dimensions"]


def test_validation_provenance_blocks_research_fed_promotion_and_allows_fresh_holdout():
    contaminated = build_validation_provenance(
        used_for_prompt_or_allocation=True,
        frozen=True,
        fresh_holdout=True,
        artifact_ids=["research-oos"],
    )
    contaminated_blockers = validation_promotion_blockers(contaminated)
    assert contaminated["scope"] == "research_only"
    assert contaminated_blockers["blocked"] is True
    assert "validation_used_for_research_learning" in contaminated_blockers["blockers"]
    assert "validation_scope_research_only" in contaminated_blockers["blockers"]

    missing_evidence_holdout = build_validation_provenance(
        used_for_prompt_or_allocation=False,
        frozen=True,
        fresh_holdout=True,
        scope="fresh_frozen_holdout",
        artifact_ids=["fresh-holdout"],
    )
    missing_evidence_blockers = validation_promotion_blockers(missing_evidence_holdout)
    assert missing_evidence_blockers["blocked"] is True
    assert "validation_evidence_incomplete" in missing_evidence_blockers["blockers"]

    fresh_holdout = build_validation_provenance(
        used_for_prompt_or_allocation=False,
        frozen=True,
        fresh_holdout=True,
        scope="fresh_frozen_holdout",
        evidence_health=build_evidence_health(_complete_research_evidence(), preset="promotion"),
        artifact_ids=["fresh-holdout"],
    )
    blockers = validation_promotion_blockers(fresh_holdout)
    assert blockers["blocked"] is False
    assert blockers["promotion_eligible"] is True

    forged_without_evidence = validation_promotion_blockers({
        "scope": "fresh_frozen_holdout",
        "used_for_prompt_or_allocation": False,
        "frozen": True,
        "fresh_holdout": True,
        "promotion_eligible": True,
    })
    assert forged_without_evidence["blocked"] is True
    assert forged_without_evidence["promotion_eligible"] is False
    assert "validation_evidence_incomplete" in forged_without_evidence["blockers"]
