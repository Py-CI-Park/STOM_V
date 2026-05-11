from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_ANALYSIS_UI,
    FLAG_BACKTEST_LEARNING,
    FLAG_REALTIME_LEARNING,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_SCHEMA_VERSION,
    V3K_GUI_SIDECAR_SOURCE,
    apply_v3k_sidecar_session_override,
    validate_v3k_gui_sidecar_payload,
)
from strategy.v3k_settings_surface import V3K_SETTINGS_SURFACE_VERSION  # noqa: E402


def _artifact_status() -> str:
    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "_v3k_sidecar",
            "_database",
            "_database_v3k_shadow",
            "_log",
            "backup",
            "*.db",
            "backtest/graph",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _valid_payload(settings: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema_version": V3K_GUI_SIDECAR_SCHEMA_VERSION,
        "surface_version": V3K_SETTINGS_SURFACE_VERSION,
        "settings": dict(settings or {}),
        "updated_at": "2026-05-12T00:00:00+09:00",
        "source": V3K_GUI_SIDECAR_SOURCE,
    }


def _assert_valid_mapping_payload() -> None:
    result = validate_v3k_gui_sidecar_payload(
        _valid_payload(
            {
                FLAG_ANALYSIS_UI: True,
                FLAG_BACKTEST_LEARNING: "yes",
                FLAG_REALTIME_LEARNING: 0,
            },
        ),
    )

    assert result.valid
    assert result.schema_version == V3K_GUI_SIDECAR_SCHEMA_VERSION
    assert result.source == V3K_GUI_SIDECAR_SOURCE
    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert result.settings[FLAG_BACKTEST_LEARNING] is True
    assert result.settings[FLAG_REALTIME_LEARNING] is False
    assert result.feature_flags[FLAG_ANALYSIS_UI] is True
    assert result.diagnostics[0] == "sidecar schema v1 payload valid"
    print("v3k sidecar valid mapping payload ok")


def _assert_valid_json_payload() -> None:
    result = validate_v3k_gui_sidecar_payload(
        json.dumps(_valid_payload({FLAG_ANALYSIS_UI: True}), ensure_ascii=False),
    )

    assert result.valid
    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert result.diagnostics[0] == "sidecar schema v1 payload valid"
    print("v3k sidecar valid JSON payload ok")


def _assert_missing_and_corrupt_payloads_fallback() -> None:
    cases = (
        (None, "sidecar payload missing; default-OFF fallback"),
        ("{invalid-json", "sidecar payload invalid JSON; default-OFF fallback"),
        ([], "sidecar payload must be a mapping; default-OFF fallback"),
        ({}, "sidecar schema version missing or unsupported; default-OFF fallback"),
        (
            {**_valid_payload(), "schema_version": 999},
            "sidecar schema version missing or unsupported; default-OFF fallback",
        ),
        (
            {**_valid_payload(), "surface_version": "UNKNOWN"},
            "sidecar surface version missing or unsupported; default-OFF fallback",
        ),
        (
            {**_valid_payload(), "settings": "not-a-dict"},
            "sidecar settings must be a mapping; default-OFF fallback",
        ),
    )

    for payload, diagnostic in cases:
        result = validate_v3k_gui_sidecar_payload(payload)  # type: ignore[arg-type]
        assert not result.valid
        assert result.all_off
        assert result.settings[FLAG_ANALYSIS_UI] is False
        assert result.diagnostics == (diagnostic,)
    print("v3k sidecar missing/corrupt payload default-OFF fallback ok")


def _assert_unknown_key_is_diagnostic_only() -> None:
    result = validate_v3k_gui_sidecar_payload(
        _valid_payload(
            {
                FLAG_ANALYSIS_UI: True,
                "unknown_v3k_flag": True,
            },
        ),
    )

    assert result.valid
    assert result.settings[FLAG_ANALYSIS_UI] is True
    assert "unknown_v3k_flag" not in result.settings
    assert "unknown V3K setting ignored: unknown_v3k_flag" in result.diagnostics
    print("v3k sidecar unknown key diagnostic ok")


def _assert_session_override_has_priority() -> None:
    sidecar = validate_v3k_gui_sidecar_payload(
        _valid_payload(
            {
                FLAG_ANALYSIS_UI: True,
                FLAG_BACKTEST_LEARNING: False,
            },
        ),
    )
    merged = apply_v3k_sidecar_session_override(
        sidecar,
        {
            FLAG_ANALYSIS_UI: False,
            FLAG_BACKTEST_LEARNING: True,
        },
    )

    assert sidecar.valid
    assert sidecar.settings[FLAG_ANALYSIS_UI] is True
    assert merged.settings[FLAG_ANALYSIS_UI] is False
    assert merged.settings[FLAG_BACKTEST_LEARNING] is True
    assert merged.feature_flags[FLAG_ANALYSIS_UI] is False
    assert merged.feature_flags[FLAG_BACKTEST_LEARNING] is True
    print("v3k sidecar session override priority ok")


def main() -> None:
    before = _artifact_status()
    _assert_valid_mapping_payload()
    _assert_valid_json_payload()
    _assert_missing_and_corrupt_payloads_fallback()
    _assert_unknown_key_is_diagnostic_only()
    _assert_session_override_has_priority()
    after = _artifact_status()
    assert before == after, f"runtime artifact status changed: before={before!r} after={after!r}"
    print("v3k GUI sidecar schema validator smoke passed")


if __name__ == "__main__":
    main()
