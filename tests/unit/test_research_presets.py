from __future__ import annotations

import json

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller import loop as L
from ai_strategy_loop.launch_config import config_from_dict
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


def test_min_full_preset_warm_command_ends_at_150000() -> None:
    """DR-02 — resolve the preset through the real command-building path
    (loop._build_warm_btconfig), not just the raw preset dict; no subprocess runs."""
    preset_config = preset_payload(PresetName.MIN_FULL_0900_1500)["config"]
    cfg = config_from_dict(preset_config)

    bt_config = L._build_warm_btconfig(cfg)

    assert bt_config.start_time == 90000
    assert bt_config.end_time == 150000


def test_min_full_preset_defaults_off_baseline() -> None:
    # Defaults-OFF invariant: the preset opts research toggles in explicitly; a bare
    # LoopConfig (v11 default, no preset applied) must keep them OFF.
    defaults = LoopConfig()
    assert defaults.full_session_enabled is False
    assert defaults.exec_budget_prompt_enabled is False
    assert defaults.sell_exec_budget_guard_enabled is False
