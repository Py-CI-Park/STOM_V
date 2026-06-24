from __future__ import annotations

import json

from ai_strategy_loop.scripts.research_presets import (
    PresetName,
    preset_names,
    preset_payload,
    write_preset,
)


def test_tick_late_preset_targets_0920_0925_discovery() -> None:
    payload = preset_payload(PresetName.TICK_LATE_0920_0925)
    config = payload["config"]

    assert "09:20~09:25" in payload["description"]
    assert config["bt_timeframe"] == "tick"
    assert config["bt_universe_end_time"] == 93000
    assert config["time_cap_bucket_generation_enabled"] is True
    assert config["time_cap_bucket_end_time"] == 93000
    assert config["classification_generation_enabled"] is True
    assert config["require_filter_gates"] is True


def test_min_full_preset_uses_min_data_until_1500() -> None:
    payload = preset_payload(PresetName.MIN_FULL_0900_1500)
    config = payload["config"]

    assert "09:00~15:00" in payload["description"]
    assert config["bt_timeframe"] == "min"
    assert config["full_session_enabled"] is True
    assert config["bt_min_universe_end_time"] == 150000
    assert config["exec_budget_prompt_enabled"] is True
    assert config["sell_exec_budget_guard_enabled"] is True


def test_write_preset_outputs_config_json(tmp_path) -> None:
    out_path = tmp_path / "preset.json"

    write_preset(PresetName.MIN_FULL_0900_1500, out_path)

    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved["bt_timeframe"] == "min"
    assert saved["full_session_enabled"] is True
    assert saved["bt_min_universe_end_time"] == 150000


def test_preset_names_are_stable_cli_values() -> None:
    assert preset_names() == [
        "tick_late_0920_0925",
        "min_full_0900_1500",
    ]
