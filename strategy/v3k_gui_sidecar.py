from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping

from strategy.v3k_settings_surface import (
    V3K_SETTINGS_SURFACE_VERSION,
    V3KSettingsSurfaceResult,
    normalize_v3k_settings,
    v3k_settings_defaults,
)


V3K_GUI_SIDECAR_DIR = "_v3k_sidecar"
V3K_GUI_SIDECAR_FILE = "_v3k_sidecar/v3k_gui_settings.json"
V3K_GUI_SIDECAR_BACKUP_DIR = "_v3k_sidecar/backups"
V3K_GUI_SIDECAR_SCHEMA_VERSION = 1
V3K_GUI_SIDECAR_SOURCE = "v3k_gui_settings_preview"
V3K_GUI_SIDECAR_REQUIRED_FIELDS = (
    "schema_version",
    "surface_version",
    "settings",
    "updated_at",
    "source",
)


@dataclass(frozen=True)
class V3KGuiSidecarValidationResult:
    """Pure validation result for a future V3K GUI settings sidecar payload."""

    valid: bool
    settings_result: V3KSettingsSurfaceResult
    schema_version: int | None = None
    source: str = ""
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def settings(self) -> dict[str, bool]:
        return self.settings_result.settings

    @property
    def feature_flags(self) -> dict[str, bool]:
        return self.settings_result.feature_flags

    @property
    def all_off(self) -> bool:
        return self.settings_result.all_off


def _default_off_result(*diagnostics: str) -> V3KGuiSidecarValidationResult:
    settings_result = normalize_v3k_settings({})
    return V3KGuiSidecarValidationResult(
        valid=False,
        settings_result=settings_result,
        diagnostics=tuple(diagnostic for diagnostic in diagnostics if diagnostic),
    )


def _payload_from_json_text(payload: str | bytes) -> Mapping[str, Any] | None:
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        loaded = json.loads(payload)
    except Exception:
        return None
    if not isinstance(loaded, Mapping):
        return None
    return loaded


def validate_v3k_gui_sidecar_payload(
    payload: Mapping[str, Any] | str | bytes | None,
) -> V3KGuiSidecarValidationResult:
    """Validate a V3K GUI sidecar payload without reading or writing files."""

    if payload is None:
        return _default_off_result("sidecar payload missing; default-OFF fallback")

    if isinstance(payload, (str, bytes)):
        payload = _payload_from_json_text(payload)
        if payload is None:
            return _default_off_result("sidecar payload invalid JSON; default-OFF fallback")

    if not isinstance(payload, Mapping):
        return _default_off_result("sidecar payload must be a mapping; default-OFF fallback")

    schema_version = payload.get("schema_version")
    if schema_version != V3K_GUI_SIDECAR_SCHEMA_VERSION:
        return _default_off_result(
            "sidecar schema version missing or unsupported; default-OFF fallback",
        )

    surface_version = payload.get("surface_version")
    if surface_version != V3K_SETTINGS_SURFACE_VERSION:
        return _default_off_result(
            "sidecar surface version missing or unsupported; default-OFF fallback",
        )

    settings_payload = payload.get("settings")
    if not isinstance(settings_payload, Mapping):
        return _default_off_result("sidecar settings must be a mapping; default-OFF fallback")

    settings_result = normalize_v3k_settings(settings_payload)
    source = str(payload.get("source") or "")
    diagnostics = ("sidecar schema v1 payload valid",) + settings_result.diagnostics
    return V3KGuiSidecarValidationResult(
        valid=True,
        settings_result=settings_result,
        schema_version=V3K_GUI_SIDECAR_SCHEMA_VERSION,
        source=source,
        diagnostics=diagnostics,
    )


def apply_v3k_sidecar_session_override(
    sidecar_result: V3KGuiSidecarValidationResult,
    session_settings: Mapping[str, Any] | None = None,
) -> V3KSettingsSurfaceResult:
    """Merge a validated sidecar result with session-only preview overrides."""

    merged = dict(v3k_settings_defaults())
    if sidecar_result.valid:
        merged.update(sidecar_result.settings)
    if session_settings:
        merged.update(session_settings)
    return normalize_v3k_settings(merged)
