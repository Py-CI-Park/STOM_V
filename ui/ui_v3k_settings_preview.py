from __future__ import annotations

from dataclasses import dataclass
from types import MethodType
from typing import Any

from strategy.v3k_settings_surface import (
    normalize_v3k_settings,
    v3k_settings_contract_rows,
    v3k_settings_defaults,
)


V3K_SETTINGS_PREVIEW_VERSION = "V3K_SETTINGS_PREVIEW_SESSION_ONLY_V1"
V3K_SETTINGS_PREVIEW_METHOD = "ShowV3KSettingsPreview"
V3K_SETTINGS_PREVIEW_RESULT_ATTR = "v3k_settings_preview_result"
V3K_SETTINGS_PREVIEW_SESSION_ONLY_ATTR = "v3k_settings_preview_session_only"
V3K_SETTINGS_PREVIEW_DIALOG_ATTR = "dialog_v3k_settings_preview"


@dataclass(frozen=True)
class V3KSettingsPreviewAttachResult:
    version: str
    method_name: str
    session_only: bool
    row_count: int
    ui_row_count: int
    persistent_writes: bool = False


def _preview_rows() -> tuple[dict[str, Any], ...]:
    return tuple(row for row in v3k_settings_contract_rows() if row["ui_exposable"])


def attach_v3k_settings_preview(ui_like: Any) -> V3KSettingsPreviewAttachResult:
    """Attach a session-only V3K settings preview opener to a MainWindow-like object.

    This helper intentionally does not create a widget at startup. It only adds a
    callable dialog opener and records an inert session-only marker. The dialog
    itself is built lazily by ``ShowV3KSettingsPreview`` and mutates only
    ``v3k_settings`` / ``v3k_feature_flags`` attributes on the supplied object.
    """

    result = V3KSettingsPreviewAttachResult(
        version=V3K_SETTINGS_PREVIEW_VERSION,
        method_name=V3K_SETTINGS_PREVIEW_METHOD,
        session_only=True,
        row_count=len(v3k_settings_contract_rows()),
        ui_row_count=len(_preview_rows()),
    )
    setattr(ui_like, V3K_SETTINGS_PREVIEW_SESSION_ONLY_ATTR, True)
    setattr(ui_like, V3K_SETTINGS_PREVIEW_RESULT_ATTR, result)
    setattr(
        ui_like,
        V3K_SETTINGS_PREVIEW_METHOD,
        MethodType(lambda self: show_v3k_settings_preview(self), ui_like),
    )
    return result


def build_v3k_settings_preview_model(ui_like: Any) -> tuple[dict[str, Any], ...]:
    """Return UI rows with current session-only checked state."""

    current_settings = dict(v3k_settings_defaults())
    current_settings.update(getattr(ui_like, "v3k_settings", {}) or {})

    model: list[dict[str, Any]] = []
    for row in _preview_rows():
        model.append(
            {
                "key": row["key"],
                "group": row["group"],
                "label": row["label"],
                "description": row["description"],
                "checked": bool(current_settings.get(row["key"], False)),
                "session_only": True,
            },
        )
    return tuple(model)


def set_v3k_preview_session_flag(ui_like: Any, key: str, checked: bool) -> None:
    """Update V3K settings on the MainWindow-like object without persistence."""

    current_settings = dict(v3k_settings_defaults())
    current_settings.update(getattr(ui_like, "v3k_settings", {}) or {})
    current_settings[key] = bool(checked)

    normalized = normalize_v3k_settings(current_settings)
    setattr(ui_like, "v3k_settings", dict(normalized.settings))
    setattr(ui_like, "v3k_feature_flags", dict(normalized.feature_flags))
    setattr(ui_like, "v3k_settings_diagnostics", tuple(normalized.diagnostics))


def reset_v3k_preview_session_flags(ui_like: Any) -> None:
    """Reset the preview state to default-OFF in memory only."""

    normalized = normalize_v3k_settings({})
    setattr(ui_like, "v3k_settings", dict(normalized.settings))
    setattr(ui_like, "v3k_feature_flags", dict(normalized.feature_flags))
    setattr(ui_like, "v3k_settings_diagnostics", tuple(normalized.diagnostics))


def show_v3k_settings_preview(ui_like: Any) -> Any:
    """Create and show the session-only V3K preview dialog."""

    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import (
        QCheckBox,
        QDialog,
        QLabel,
        QPushButton,
        QScrollArea,
        QVBoxLayout,
        QWidget,
    )

    dialog = getattr(ui_like, V3K_SETTINGS_PREVIEW_DIALOG_ATTR, None)
    if dialog is not None and dialog.isVisible():
        dialog.raise_()
        dialog.activateWindow()
        return dialog

    dialog = QDialog(ui_like)
    dialog.setWindowTitle("V3K settings preview - session only")
    dialog.setModal(False)
    dialog.setMinimumWidth(520)

    root_layout = QVBoxLayout(dialog)
    notice = QLabel(
        "Session-only preview: toggles are not written to setting DB or sidecar files.",
        dialog,
    )
    notice.setWordWrap(True)
    root_layout.addWidget(notice)

    scroll = QScrollArea(dialog)
    scroll.setWidgetResizable(True)
    content = QWidget(scroll)
    content_layout = QVBoxLayout(content)
    checkboxes: list[QCheckBox] = []

    for row in build_v3k_settings_preview_model(ui_like):
        checkbox = QCheckBox(f"[{row['group']}] {row['label']}", content)
        checkbox.setToolTip(row["description"])
        checkbox.setChecked(row["checked"])
        checkbox.stateChanged.connect(
            lambda state, setting_key=row["key"]: set_v3k_preview_session_flag(
                ui_like,
                setting_key,
                state == Qt.Checked,
            ),
        )
        content_layout.addWidget(checkbox)
        checkboxes.append(checkbox)

    content_layout.addStretch(1)
    scroll.setWidget(content)
    root_layout.addWidget(scroll)

    reset_button = QPushButton("Reset all V3K preview flags to OFF", dialog)

    def reset_all() -> None:
        reset_v3k_preview_session_flags(ui_like)
        for checkbox in checkboxes:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)

    reset_button.clicked.connect(reset_all)
    root_layout.addWidget(reset_button)

    close_button = QPushButton("Close", dialog)
    close_button.clicked.connect(dialog.close)
    root_layout.addWidget(close_button)

    setattr(ui_like, V3K_SETTINGS_PREVIEW_DIALOG_ATTR, dialog)
    dialog.show()
    return dialog
