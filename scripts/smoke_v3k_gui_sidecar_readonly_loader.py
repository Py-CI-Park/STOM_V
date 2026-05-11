from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_ANALYSIS_UI,
    FLAG_BACKTEST_LEARNING,
    FLAG_RISK_ANALYSIS,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_SOURCE,
    apply_v3k_sidecar_session_override,
    load_v3k_gui_sidecar_file,
)
from strategy.v3k_settings_surface import V3K_SETTINGS_SURFACE_VERSION  # noqa: E402


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _artifact_status() -> str:
    return _run_git(
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
    )


def _valid_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface_version": V3K_SETTINGS_SURFACE_VERSION,
        "settings": {
            FLAG_ANALYSIS_UI: True,
            FLAG_BACKTEST_LEARNING: "yes",
            FLAG_RISK_ANALYSIS: False,
            "unknown_v3k_flag": True,
        },
        "updated_at": "2026-05-12T00:00:00+09:00",
        "source": V3K_GUI_SIDECAR_SOURCE,
    }


def _assert_missing_file_falls_back(tmpdir: Path) -> None:
    result = load_v3k_gui_sidecar_file(tmpdir / "missing.json")
    if result.valid or not result.all_off:
        raise AssertionError("missing sidecar file must fall back to default-OFF")
    if "sidecar file missing; default-OFF fallback" not in result.diagnostics:
        raise AssertionError(f"missing-file diagnostic mismatch: {result.diagnostics}")


def _assert_corrupt_file_falls_back(tmpdir: Path) -> None:
    path = tmpdir / "corrupt.json"
    path.write_text("{ not-json", encoding="utf-8")
    result = load_v3k_gui_sidecar_file(path)
    if result.valid or not result.all_off:
        raise AssertionError("corrupt sidecar file must fall back to default-OFF")
    if "sidecar payload invalid JSON; default-OFF fallback" not in result.diagnostics:
        raise AssertionError(f"corrupt-file diagnostic mismatch: {result.diagnostics}")


def _assert_valid_file_loads(tmpdir: Path) -> None:
    path = tmpdir / "valid.json"
    path.write_text(
        json.dumps(_valid_payload(), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    result = load_v3k_gui_sidecar_file(path)
    if not result.valid:
        raise AssertionError(f"valid sidecar file did not validate: {result.diagnostics}")
    if result.settings[FLAG_ANALYSIS_UI] is not True:
        raise AssertionError("valid sidecar file did not enable analysis UI")
    if result.settings[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("truthy sidecar setting did not normalize to True")
    if "unknown_v3k_flag" in result.settings:
        raise AssertionError("unknown sidecar setting leaked into normalized settings")
    if not any("unknown V3K setting ignored" in item for item in result.diagnostics):
        raise AssertionError(f"unknown-key diagnostic missing: {result.diagnostics}")

    merged = apply_v3k_sidecar_session_override(
        result,
        {
            FLAG_ANALYSIS_UI: False,
            FLAG_RISK_ANALYSIS: True,
        },
    )
    if merged.settings[FLAG_ANALYSIS_UI] is not False:
        raise AssertionError("session-only override must override loaded sidecar settings")
    if merged.settings[FLAG_RISK_ANALYSIS] is not True:
        raise AssertionError("session-only override did not enable risk analysis")
    if merged.settings[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("sidecar setting not overridden by session must be preserved")


def main() -> None:
    before = _artifact_status()
    with tempfile.TemporaryDirectory(prefix="v3k-sidecar-readonly-") as tmp:
        tmpdir = Path(tmp)
        _assert_missing_file_falls_back(tmpdir)
        _assert_corrupt_file_falls_back(tmpdir)
        _assert_valid_file_loads(tmpdir)

    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "sidecar read-only loader smoke changed repo artifact status:\n"
            f"before={before!r}\nafter={after!r}",
        )

    print("v3k gui sidecar read-only loader smoke passed")
    print("missing/corrupt/valid/session-override paths verified without repo artifacts")


if __name__ == "__main__":
    main()
