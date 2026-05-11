from __future__ import annotations

from typing import Any, Mapping

from strategy.v3k_settings_surface import (
    V3KSettingsBridgeResult,
    bridge_v3k_settings_into_dict_set,
)


V3K_GUI_SETTINGS_VERSION_ATTR = "v3k_settings_surface_version"
V3K_GUI_SETTINGS_ATTR = "v3k_settings"
V3K_GUI_FEATURE_FLAGS_ATTR = "v3k_feature_flags"
V3K_GUI_DIAGNOSTICS_ATTR = "v3k_settings_diagnostics"
V3K_GUI_BRIDGED_DICT_SET_ATTR = "v3k_settings_bridge_dict_set"
V3K_GUI_BRIDGE_RESULT_ATTR = "v3k_settings_bridge_result"

V3K_GUI_BRIDGE_ATTRS: tuple[str, ...] = (
    V3K_GUI_SETTINGS_VERSION_ATTR,
    V3K_GUI_SETTINGS_ATTR,
    V3K_GUI_FEATURE_FLAGS_ATTR,
    V3K_GUI_DIAGNOSTICS_ATTR,
    V3K_GUI_BRIDGED_DICT_SET_ATTR,
    V3K_GUI_BRIDGE_RESULT_ATTR,
)


def attach_v3k_gui_settings_bridge(
    ui_like: Any,
    raw_settings: Mapping[str, Any] | None = None,
    *,
    replace_dict_set: bool = False,
) -> V3KSettingsBridgeResult:
    """Attach V3K settings state to a MainWindow-like object without GUI/DB I/O.

    The helper is intentionally small and no-GUI. It reuses the Phase C1
    dict_set bridge, stores normalized V3K settings/feature flags on the
    supplied object, and avoids persistent setting DB writes. The existing
    ``dict_set`` attribute is not replaced unless ``replace_dict_set`` is
    explicitly requested; even then, a copied in-memory dict is assigned.
    """

    source_dict_set = getattr(ui_like, "dict_set", None)
    result = bridge_v3k_settings_into_dict_set(source_dict_set, raw_settings)

    setattr(ui_like, V3K_GUI_SETTINGS_VERSION_ATTR, result.version)
    setattr(ui_like, V3K_GUI_SETTINGS_ATTR, dict(result.settings))
    setattr(ui_like, V3K_GUI_FEATURE_FLAGS_ATTR, dict(result.feature_flags))
    setattr(ui_like, V3K_GUI_DIAGNOSTICS_ATTR, tuple(result.diagnostics))
    setattr(ui_like, V3K_GUI_BRIDGED_DICT_SET_ATTR, dict(result.dict_set))
    setattr(ui_like, V3K_GUI_BRIDGE_RESULT_ATTR, result)

    if replace_dict_set:
        setattr(ui_like, "dict_set", dict(result.dict_set))

    return result
