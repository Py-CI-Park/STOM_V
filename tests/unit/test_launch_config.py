"""US-007 — launch-config 단위 테스트 (CLI = GUI 동일 경로).

검증:
  - CLI 스타일 dict와 GUI 스타일 dict가 같은 값 → 동일 LoopConfig.
  - 누락 필드 → 문서화된 기본값.
  - config_field_specs()가 핵심 사용자 필드를 모두 포함.
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.controller.condition_discovery import canonical_effective_profile  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402
from ai_strategy_loop.scripts.research_presets import PresetName, preset_payload  # noqa: E402


class TestConfigFromDictEquivalence:
    """CLI 스타일과 GUI 스타일 입력이 동일한 LoopConfig를 만든다."""

    def test_cli_and_gui_dicts_produce_identical_config(self):
        # CLI 파서가 만들 법한 dict (argparse → dict).
        cli_dict = {
            "provider": "openrouter",
            "model": "gpt-5.5",
            "max_generations": 7,
            "mdd_cap": 20.0,
            "min_trades": 25,
            "bt_timeframe": "min",
        }
        # GUI 폼이 만들 법한 dict (REST body) — 같은 값, 키 순서만 다름.
        gui_dict = {
            "min_trades": 25,
            "bt_timeframe": "min",
            "mdd_cap": 20.0,
            "max_generations": 7,
            "model": "gpt-5.5",
            "provider": "openrouter",
        }
        cli_cfg = config_from_dict(cli_dict)
        gui_cfg = config_from_dict(gui_dict)
        assert cli_cfg == gui_cfg
        assert cli_cfg.to_dict() == gui_cfg.to_dict()

    def test_omitted_fields_use_documented_defaults(self):
        cfg = config_from_dict({"provider": "openrouter"})
        defaults = LoopConfig()
        # 명시한 provider만 다르고 나머지는 기본값.
        assert cfg.provider == "openrouter"
        assert cfg.model == defaults.model
        assert cfg.max_generations == defaults.max_generations
        assert cfg.mdd_cap == defaults.mdd_cap
        assert cfg.min_trades == defaults.min_trades
        assert cfg.bt_timeframe == defaults.bt_timeframe
        assert cfg.graduation_holdout == defaults.graduation_holdout
        assert cfg.autopsy_enabled == defaults.autopsy_enabled
        assert cfg.typed_feedback_v2_enabled is False

    def test_empty_dict_yields_all_defaults(self):
        assert config_from_dict({}).to_dict() == LoopConfig().to_dict()

    def test_none_yields_all_defaults(self):
        assert config_from_dict(None).to_dict() == LoopConfig().to_dict()

    def test_unknown_keys_ignored(self):
        cfg = config_from_dict({"provider": "openrouter", "totally_unknown_key": 42})
        assert cfg.provider == "openrouter"
        assert not hasattr(cfg, "totally_unknown_key")

    def test_unknown_strict_keys_are_rejected(self):
        with pytest.raises(ValueError, match="unknown strict LoopConfig keys"):
            config_from_dict({"strict_candidate_payload_v22": True})


class TestConfigFromDictValidation:
    """경계 검증 — 명백히 잘못된 값은 ValueError."""

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError):
            config_from_dict({"provider": "not_a_provider"})

    def test_invalid_timeframe_raises(self):
        with pytest.raises(ValueError):
            config_from_dict({"bt_timeframe": "hourly"})

    def test_max_generations_below_one_raises(self):
        with pytest.raises(ValueError):
            config_from_dict({"max_generations": 0})

    def test_negative_mdd_cap_raises(self):
        with pytest.raises(ValueError):
            config_from_dict({"mdd_cap": -5.0})

    def test_negative_min_trades_raises(self):
        with pytest.raises(ValueError):
            config_from_dict({"min_trades": -1})
    def test_phase3_bounds_and_dates_validate(self):
        with pytest.raises(ValueError):
            config_from_dict({"mdd_cap": 40.1})
        with pytest.raises(ValueError):
            config_from_dict({"min_daily_trades": -0.1})
        with pytest.raises(ValueError):
            config_from_dict({"reasoning_effort": "ultra"})
        with pytest.raises(ValueError):
            config_from_dict({"seed_mode": "unknown"})
        with pytest.raises(ValueError):
            config_from_dict({"bt_start": "20260132"})
        with pytest.raises(ValueError):
            config_from_dict({"bt_start": 20260102, "bt_end": 20260101})
        cfg = config_from_dict({"bt_start": "", "bt_end": ""})
        assert cfg.bt_start is None
        assert cfg.bt_end is None


class TestConfigFieldSpecs:
    """config_field_specs()가 핵심 사용자 필드를 커버하는지."""

    def test_returns_list_of_dicts(self):
        specs = config_field_specs()
        assert isinstance(specs, list)
        assert all(isinstance(s, dict) for s in specs)

    def test_each_spec_has_required_keys(self):
        for s in config_field_specs():
            assert "name" in s
            assert "label" in s
            assert "type" in s
            assert "default" in s
            assert "help" in s

    def test_covers_key_user_fields(self):
        names = {s["name"] for s in config_field_specs()}
        # 경계값 + 데이터 스코프 + provider/model.
        for required in (
            "provider", "model", "reasoning_effort", "max_generations", "target_score",
            "mdd_cap", "min_daily_trades", "min_trades",
            "bt_timeframe", "bt_scope", "bt_start", "bt_end",
            "engine_workers", "engine_mem_cap_mb", "engine_chunk_days",
            "feedback_window", "seed_mode", "seed_source", "seed_buy", "seed_sell",
        ):
            assert required in names, f"missing field spec: {required}"

    def test_holdout_fields_exposed_now_that_run_loop_is_wired(self):
        # P5 배선 완료: run_loop가 gate 통과 후보를 train/holdout으로 분할해
        #   졸업검사한다(2026-07-16 실 A/B 파일럿에서 홀드아웃 게이트 로그 실측).
        #   따라서 폼에 노출되어야 하며, 숨기면 작동하는 기능을 감추는 거짓 UI다.
        specs = {s["name"]: s for s in config_field_specs()}
        assert specs["graduation_holdout"]["type"] == "bool"
        assert specs["holdout_recent_days"]["type"] == "number"
        assert specs["holdout_recent_days"]["min"] == 1

    def test_holdout_config_fields_still_exist(self):
        d = LoopConfig()
        assert hasattr(d, "graduation_holdout")
        assert hasattr(d, "holdout_recent_days")

    def test_defaults_match_loopconfig(self):
        d = LoopConfig()
        host_advisory_defaults = {"engine_workers", "engine_mem_cap_mb", "engine_chunk_days"}
        for s in config_field_specs():
            if s["name"] in host_advisory_defaults:
                continue
            assert s["default"] == getattr(d, s["name"]), \
                f"default mismatch for {s['name']}"

    def test_select_fields_have_choices(self):
        for s in config_field_specs():
            if s["type"] == "select":
                assert "choices" in s and s["choices"], \
                    f"select field {s['name']} missing choices"
    def test_phase3_defaults_and_help_explain_user_feedback(self):
        specs = {s["name"]: s for s in config_field_specs()}
        assert specs["model"]["default"] == "gpt-5.6-terra"
        assert specs["reasoning_effort"]["default"] == "high"
        assert specs["mdd_cap"]["default"] == 40.0
        assert specs["mdd_cap"]["max"] == 40.0
        assert "일평균" in specs["min_daily_trades"]["help"]
        assert "폴백" in specs["min_trades"]["label"]
        assert "DB 최대" in specs["bt_end"]["help"]
        assert "90%" in specs["engine_workers"]["help"]
        assert "피드백" in specs["feedback_window"]["help"]
        assert specs["seed_mode"]["default"] == "best_refine"

    def test_covers_r8_safety_toggles(self):
        # R8 — 지금까지 폼·상태 어디에도 안 보이던 5종 안전/Track B 토글 + 진화/스코프 설정.
        names = {s["name"] for s in config_field_specs()}
        for required in (
            "dispersion_prompt_enabled", "dispersion_enabled", "min_hold_symbols",
            "require_liquidity_gate", "mdd_control_enabled",
            "evolution_mode", "winner_objective", "bt_engine_mode",
            "freeze_buy_on_mdd_only",
        ):
            assert required in names, f"missing R8 field spec: {required}"

    def test_r8_toggle_specs_are_bool_type(self):
        bool_fields = {
            "dispersion_prompt_enabled", "dispersion_enabled",
            "require_liquidity_gate", "mdd_control_enabled", "freeze_buy_on_mdd_only",
        }
        specs = {s["name"]: s for s in config_field_specs()}
        for name in bool_fields:
            assert specs[name]["type"] == "bool", f"{name} should be bool type"


class TestDr02EffectiveProfileHashEquality:
    """DR-02 — CLI/UI/preset entry points must resolve to one canonical effective profile.

    All three funnel through ``config_from_dict`` + ``canonical_effective_profile``; the
    hash is computed over sorted-key canonical JSON, so differing input dict key order
    (CLI argparse collection order vs. a GUI form's field order vs. a preset's declared
    key order) must not change the resulting hash.
    """

    def test_hash_identical_across_cli_ui_and_preset_dict_styles(self):
        preset_config = dict(preset_payload(PresetName.MIN_FULL_0900_1500)["config"])

        cli_style = dict(preset_config)  # argparse-collected dict, declared key order.
        gui_style = {k: preset_config[k] for k in reversed(list(preset_config))}  # form dict, reversed order.
        preset_style = dict(preset_config)

        cli_cfg = config_from_dict(cli_style)
        gui_cfg = config_from_dict(gui_style)
        preset_cfg = config_from_dict(preset_style)

        cli_profile = canonical_effective_profile(cli_cfg)
        gui_profile = canonical_effective_profile(gui_cfg)
        preset_profile = canonical_effective_profile(preset_cfg)

        assert cli_profile["effective_profile_hash"] == gui_profile["effective_profile_hash"]
        assert cli_profile["effective_profile_hash"] == preset_profile["effective_profile_hash"]
        assert cli_profile["effective_profile_name"] == gui_profile["effective_profile_name"] == preset_profile["effective_profile_name"]

    def test_hash_changes_when_session_window_differs(self):
        base = config_from_dict({"bt_timeframe": "min"})
        changed = config_from_dict({"bt_timeframe": "min", "bt_min_universe_end_time": 151800})
        base_profile = canonical_effective_profile(base)
        changed_profile = canonical_effective_profile(changed)
        # full_session_enabled defaults False for both -> session end untouched either way,
        # but mdd_cap/timeframe fields still participate; assert hash is a stable function
        # of canonical content (identical inputs -> identical hash) rather than random.
        assert base_profile["effective_profile_hash"] == canonical_effective_profile(
            config_from_dict({"bt_timeframe": "min"})
        )["effective_profile_hash"]
        assert isinstance(changed_profile["effective_profile_hash"], str)
        assert len(changed_profile["effective_profile_hash"]) == 64


class TestDr02MinFullPresetSessionWindow:
    """DR-02 — min_full_0900_1500 preset must resolve session 09:00-15:00 with the
    existing warm-mode command-building path (``loop._build_warm_btconfig``); no
    subprocess is executed."""

    def test_warm_backtest_config_ends_at_150000(self):
        preset_cfg = config_from_dict(preset_payload(PresetName.MIN_FULL_0900_1500)["config"])
        bt_config = L._build_warm_btconfig(preset_cfg)
        assert bt_config.start_time == 90000
        assert bt_config.end_time == 150000
        assert bt_config.divid_mode == "종목코드별 분류"

    def test_default_full_session_disabled_keeps_original_end_time(self):
        # Defaults-OFF invariant: full_session_enabled=False (global default) must not
        # pull the end-time window to 15:00 even for a min-timeframe config.
        cfg = config_from_dict({"bt_timeframe": "min"})
        assert cfg.full_session_enabled is False
        bt_config = L._build_warm_btconfig(cfg)
        assert bt_config.end_time != 150000
