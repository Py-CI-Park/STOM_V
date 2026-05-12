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
)
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_SOURCE  # noqa: E402
from strategy.v3k_settings_surface import V3K_SETTINGS_SURFACE_VERSION  # noqa: E402
from ui.ui_v3k_settings_bridge import attach_v3k_gui_settings_bridge  # noqa: E402
from ui.ui_v3k_settings_preview import (  # noqa: E402
    V3K_SETTINGS_PREVIEW_SIDECAR_PATH_ATTR,
    V3K_SETTINGS_PREVIEW_SIDECAR_RESULT_ATTR,
    V3K_SETTINGS_PREVIEW_SESSION_DIRTY_ATTR,
    attach_v3k_settings_preview,
    build_v3k_settings_preview_model,
    set_v3k_preview_session_flag,
)


class FakeMainWindow:
    def __init__(self, dict_set: dict[str, object] | None = None):
        if dict_set is not None:
            self.dict_set = dict_set


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
        },
        "updated_at": "2026-05-12T00:00:00+09:00",
        "source": V3K_GUI_SIDECAR_SOURCE,
    }


def _attach_preview(path: Path) -> FakeMainWindow:
    source = {"legacy_setting": "preserve-me"}
    window = FakeMainWindow(source)
    attach_v3k_gui_settings_bridge(window)
    attach_v3k_settings_preview(window, sidecar_path=path)
    if source != {"legacy_setting": "preserve-me"}:
        raise AssertionError("sidecar preview init must not mutate dict_set")
    if getattr(window, V3K_SETTINGS_PREVIEW_SIDECAR_PATH_ATTR) != str(path):
        raise AssertionError("sidecar preview init must record the read-only candidate path")
    return window


def _assert_missing_sidecar_defaults_off(tmpdir: Path) -> None:
    window = _attach_preview(tmpdir / "missing.json")
    sidecar_result = getattr(window, V3K_SETTINGS_PREVIEW_SIDECAR_RESULT_ATTR)
    if sidecar_result.valid or not sidecar_result.all_off:
        raise AssertionError("missing sidecar preview init must stay default-OFF")
    if any(row["checked"] for row in build_v3k_settings_preview_model(window)):
        raise AssertionError("missing sidecar must not enable preview rows")


def _assert_corrupt_sidecar_defaults_off(tmpdir: Path) -> None:
    path = tmpdir / "corrupt.json"
    path.write_text("{ not-json", encoding="utf-8")
    window = _attach_preview(path)
    sidecar_result = getattr(window, V3K_SETTINGS_PREVIEW_SIDECAR_RESULT_ATTR)
    if sidecar_result.valid or not sidecar_result.all_off:
        raise AssertionError("corrupt sidecar preview init must stay default-OFF")
    if any(row["checked"] for row in build_v3k_settings_preview_model(window)):
        raise AssertionError("corrupt sidecar must not enable preview rows")


def _assert_valid_sidecar_initializes_session_preview(tmpdir: Path) -> None:
    path = tmpdir / "valid.json"
    path.write_text(
        json.dumps(_valid_payload(), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    window = _attach_preview(path)
    sidecar_result = getattr(window, V3K_SETTINGS_PREVIEW_SIDECAR_RESULT_ATTR)
    if not sidecar_result.valid:
        raise AssertionError(f"valid sidecar did not initialize preview: {sidecar_result.diagnostics}")
    if window.v3k_settings[FLAG_ANALYSIS_UI] is not True:
        raise AssertionError("valid sidecar did not initialize analysis UI")
    if window.v3k_settings[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("truthy sidecar value did not initialize backtest learning")
    if getattr(window, V3K_SETTINGS_PREVIEW_SESSION_DIRTY_ATTR) is not False:
        raise AssertionError("sidecar initialization itself must not mark session as dirty")

    checked = {row["key"]: row["checked"] for row in build_v3k_settings_preview_model(window)}
    if checked[FLAG_ANALYSIS_UI] is not True or checked[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("preview model did not reflect sidecar-initialized values")

    set_v3k_preview_session_flag(window, FLAG_ANALYSIS_UI, False)
    if window.v3k_settings[FLAG_ANALYSIS_UI] is not False:
        raise AssertionError("session override must win after sidecar initialization")
    if getattr(window, V3K_SETTINGS_PREVIEW_SESSION_DIRTY_ATTR) is not True:
        raise AssertionError("session override must mark preview state as dirty")


def main() -> None:
    before = _artifact_status()
    with tempfile.TemporaryDirectory(prefix="v3k-sidecar-preview-init-") as tmp:
        tmpdir = Path(tmp)
        _assert_missing_sidecar_defaults_off(tmpdir)
        _assert_corrupt_sidecar_defaults_off(tmpdir)
        _assert_valid_sidecar_initializes_session_preview(tmpdir)
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "sidecar preview init smoke changed repo artifact status:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k GUI sidecar preview initialization smoke passed")
    print("read-only sidecar values initialize session-only preview without repo artifacts")


if __name__ == "__main__":
    main()
