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
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402


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

    def test_empty_dict_yields_all_defaults(self):
        assert config_from_dict({}).to_dict() == LoopConfig().to_dict()

    def test_none_yields_all_defaults(self):
        assert config_from_dict(None).to_dict() == LoopConfig().to_dict()

    def test_unknown_keys_ignored(self):
        cfg = config_from_dict({"provider": "openrouter", "totally_unknown_key": 42})
        assert cfg.provider == "openrouter"
        assert not hasattr(cfg, "totally_unknown_key")


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
            "provider", "model", "max_generations", "target_score",
            "mdd_cap", "min_trades",
            "bt_timeframe", "bt_scope",
        ):
            assert required in names, f"missing field spec: {required}"

    def test_holdout_fields_excluded_until_wired(self):
        # MEDIUM-5: holdout 토글은 run_loop 미배선(no-op)이라 폼에서 제외한다.
        #   LoopConfig 필드 자체는 보존(아래 별도 확인).
        names = {s["name"] for s in config_field_specs()}
        assert "graduation_holdout" not in names
        assert "holdout_recent_days" not in names

    def test_holdout_config_fields_still_exist(self):
        # 폼에서 빠졌어도 LoopConfig 필드는 유지된다(후속 배선 대비).
        d = LoopConfig()
        assert hasattr(d, "graduation_holdout")
        assert hasattr(d, "holdout_recent_days")

    def test_defaults_match_loopconfig(self):
        d = LoopConfig()
        for s in config_field_specs():
            assert s["default"] == getattr(d, s["name"]), \
                f"default mismatch for {s['name']}"

    def test_select_fields_have_choices(self):
        for s in config_field_specs():
            if s["type"] == "select":
                assert "choices" in s and s["choices"], \
                    f"select field {s['name']} missing choices"
