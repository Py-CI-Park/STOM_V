import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller.condition_discovery import (  # noqa: E402
    build_evidence_health,
    effective_condition_discovery_runtime_config,
    merge_condition_discovery_page_data,
    normalize_condition_discovery_preset,
    normalize_condition_discovery_process,
    resolve_condition_discovery_process_projection,
    resolve_condition_discovery_policy,
    resolve_time_window_policy,
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
    assert [entry["code"] for entry in payload["process_catalog"]] == [
        "fast-discovery",
        "process-research",
        "promotion-review",
    ]

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
