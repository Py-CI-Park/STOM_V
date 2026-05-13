from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_FILE,
    V3K_GUI_SIDECAR_SCHEMA_VERSION,
    V3K_GUI_SIDECAR_SOURCE,
    validate_v3k_gui_sidecar_payload,
)
from strategy.v3k_settings_surface import (  # noqa: E402
    V3K_SETTINGS_SURFACE_VERSION,
    v3k_settings_defaults,
)

PAYLOAD_PREVIEW_VERSION = "GUI_SIDECAR_DEFAULT_OFF_PAYLOAD_PREVIEW_V1"
DEFAULT_PREVIEW_UPDATED_AT = "2026-05-13T00:00:00+09:00"

FORBIDDEN_ARTIFACT_PATHS = (
    "_v3k_sidecar",
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
)


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


def build_default_off_payload() -> dict[str, Any]:
    """Build the first GUI sidecar payload candidate without writing it."""

    return {
        "schema_version": V3K_GUI_SIDECAR_SCHEMA_VERSION,
        "surface_version": V3K_SETTINGS_SURFACE_VERSION,
        "settings": v3k_settings_defaults(),
        "updated_at": DEFAULT_PREVIEW_UPDATED_AT,
        "source": V3K_GUI_SIDECAR_SOURCE,
        "approval_state": "preview-only-user-approval-required",
        "target": V3K_GUI_SIDECAR_FILE,
        "preview_version": PAYLOAD_PREVIEW_VERSION,
    }


def assert_default_off_payload(payload: Mapping[str, Any]) -> None:
    result = validate_v3k_gui_sidecar_payload(payload)
    if not result.valid:
        raise AssertionError(f"default-OFF payload preview failed validation: {result.diagnostics}")
    if not result.all_off:
        raise AssertionError("default-OFF payload preview unexpectedly enables V3K flags")
    if any(bool(value) for value in result.feature_flags.values()):
        raise AssertionError("default-OFF payload preview unexpectedly enables feature flags")


def assert_artifact_status_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden artifact status is not clean:\n{status}")
    if (ROOT / V3K_GUI_SIDECAR_FILE).exists():
        raise AssertionError(f"preview must not create actual sidecar file: {V3K_GUI_SIDECAR_FILE}")


def _format_markdown(payload: Mapping[str, Any]) -> str:
    settings = payload["settings"]
    enabled = [key for key, value in settings.items() if value]
    return "\n".join(
        (
            "# V3K GUI sidecar default-OFF payload preview",
            "",
            f"- preview_version: `{PAYLOAD_PREVIEW_VERSION}`",
            f"- target: `{V3K_GUI_SIDECAR_FILE}`",
            "- mode: preview-only; no file write; USER_ACK required before actual write",
            f"- setting_count: `{len(settings)}`",
            f"- enabled_settings: `{enabled}`",
            "",
            "```json",
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            "```",
        )
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview the first V3K GUI sidecar default-OFF payload without writing artifacts."
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format for the preview payload.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    before = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    payload = build_default_off_payload()
    assert_default_off_payload(payload)
    assert_artifact_status_clean()
    after = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if before != after:
        raise AssertionError(f"payload preview changed artifact status: before={before!r}, after={after!r}")

    if args.format == "markdown":
        print(_format_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
