from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_settings_surface import (  # noqa: E402
    V3K_SETTINGS_SURFACE_VERSION,
    assert_v3k_settings_contract_aligned,
    v3k_setting_contract_keys,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_BACKUP_DIR,
    V3K_GUI_SIDECAR_DIR,
    V3K_GUI_SIDECAR_FILE,
    V3K_GUI_SIDECAR_REQUIRED_FIELDS,
    V3K_GUI_SIDECAR_SCHEMA_VERSION,
    load_v3k_gui_sidecar_file,
    validate_v3k_gui_sidecar_payload,
)


SIDECAR_DIR = V3K_GUI_SIDECAR_DIR
SIDECAR_FILE = V3K_GUI_SIDECAR_FILE
SIDECAR_BACKUP_DIR = V3K_GUI_SIDECAR_BACKUP_DIR
SIDECAR_SCHEMA_VERSION = V3K_GUI_SIDECAR_SCHEMA_VERSION
SIDECAR_REQUIRED_FIELDS = V3K_GUI_SIDECAR_REQUIRED_FIELDS

REQUIRED_DOCS = (
    "docs/update_log/2026-05-12_v3k_phase_e1_gui_sidecar_persistence_design.md",
    "docs/update_log/2026-05-12_v3k_phase_e2_gui_sidecar_schema_validator.md",
    "docs/update_log/2026-05-12_v3k_phase_e3_gui_sidecar_readonly_loader.md",
    "docs/plans/2026-05-12_v3k_page_020_phase_e1_gui_sidecar_persistence_design_plan.md",
    "docs/plans/2026-05-12_v3k_page_021_phase_e2_gui_sidecar_schema_validator_plan.md",
    "docs/plans/2026-05-12_v3k_page_022_phase_e3_gui_sidecar_readonly_loader_plan.md",
)

FORBIDDEN_RUNTIME_WRITE_MARKERS = (
    "v3k_gui_settings.json",
    "_v3k_sidecar",
    "SIDECAR_FILE",
    "open(",
    "write_text(",
)

RUNTIME_FILES_THAT_MUST_NOT_WRITE_SIDECAR = (
    "ui/ui_v3k_settings_preview.py",
    "ui/ui_v3k_settings_bridge.py",
    "ui/ui_v3k_settings_preview.py",
    "strategy/v3k_settings_surface.py",
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


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing sidecar design docs: {missing}")


def _assert_gitignore_contract() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="replace")
    if f"{SIDECAR_DIR}/" not in gitignore:
        raise AssertionError(f".gitignore must ignore {SIDECAR_DIR}/")
    print("v3k sidecar gitignore contract ok")


def _assert_sidecar_schema_contract() -> None:
    if SIDECAR_SCHEMA_VERSION != 1:
        raise AssertionError("sidecar schema version must start at 1")
    if not SIDECAR_FILE.startswith(f"{SIDECAR_DIR}/"):
        raise AssertionError("sidecar file must stay under the ignored sidecar dir")
    if not SIDECAR_BACKUP_DIR.startswith(f"{SIDECAR_DIR}/"):
        raise AssertionError("sidecar backup dir must stay under the ignored sidecar dir")
    if "settings" not in SIDECAR_REQUIRED_FIELDS:
        raise AssertionError("sidecar schema must include settings")
    if not v3k_setting_contract_keys():
        raise AssertionError("V3K setting contract keys must not be empty")
    print("v3k sidecar schema contract ok")


def _assert_default_off_and_corruption_fallback_contract() -> None:
    assert_v3k_settings_contract_aligned()
    missing = validate_v3k_gui_sidecar_payload(None)
    if missing.valid or not missing.all_off:
        raise AssertionError("missing sidecar payload must fall back to default-OFF")
    print(
        "v3k sidecar default-OFF fallback contract ok "
        f"({V3K_SETTINGS_SURFACE_VERSION})",
    )


def _assert_readonly_loader_contract() -> None:
    missing = load_v3k_gui_sidecar_file(ROOT / "__missing_v3k_gui_sidecar__.json")
    if missing.valid or not missing.all_off:
        raise AssertionError("missing sidecar file must fall back to default-OFF")
    if "sidecar file missing; default-OFF fallback" not in missing.diagnostics:
        raise AssertionError(f"missing sidecar file diagnostic mismatch: {missing.diagnostics}")
    print("v3k sidecar read-only loader contract ok")


def _assert_runtime_preview_remains_session_only() -> None:
    preview = (ROOT / "ui" / "ui_v3k_settings_preview.py").read_text(
        encoding="utf-8",
        errors="replace",
    )
    required = (
        "V3K_SETTINGS_PREVIEW_SESSION_ONLY_V1",
        "Session-only preview",
        "not written to setting DB or sidecar files",
        "persistent_writes: bool = False",
    )
    missing = [marker for marker in required if marker not in preview]
    if missing:
        raise AssertionError(f"session-only preview contract missing: {missing}")
    print("v3k sidecar session-only preview boundary ok")


def _assert_no_runtime_sidecar_write_implementation() -> None:
    hits: list[str] = []
    for rel_path in RUNTIME_FILES_THAT_MUST_NOT_WRITE_SIDECAR:
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if SIDECAR_FILE in text or SIDECAR_DIR in text or "write_text(" in text:
            hits.append(rel_path)
    if hits:
        raise AssertionError(f"sidecar write implementation is not allowed yet: {hits}")
    print("v3k sidecar no runtime write implementation ok")


def _assert_no_sidecar_or_db_artifacts_exist() -> None:
    status = _run_git(
        "status",
        "--short",
        "--",
        SIDECAR_DIR,
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
    )
    if status:
        raise AssertionError(f"runtime/sidecar artifact status is not clean:\n{status}")
    if (ROOT / SIDECAR_FILE).exists():
        raise AssertionError(f"sidecar file must not be created in design phase: {SIDECAR_FILE}")
    print("v3k sidecar no artifact status ok")


def main() -> None:
    _assert_required_docs_exist()
    _assert_gitignore_contract()
    _assert_sidecar_schema_contract()
    _assert_default_off_and_corruption_fallback_contract()
    _assert_readonly_loader_contract()
    _assert_runtime_preview_remains_session_only()
    _assert_no_runtime_sidecar_write_implementation()
    _assert_no_sidecar_or_db_artifacts_exist()

    print("V3K GUI sidecar persistence design audit passed")
    print(f"Sidecar file candidate: {SIDECAR_FILE}")
    print(f"Sidecar backup dir candidate: {SIDECAR_BACKUP_DIR}")
    print(f"Sidecar schema version: {SIDECAR_SCHEMA_VERSION}")


if __name__ == "__main__":
    main()
