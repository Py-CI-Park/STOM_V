from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_ANALYSIS_UI,
    FLAG_BACKTEST_LEARNING,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_SOURCE,
    load_v3k_gui_sidecar_file,
    validate_v3k_gui_sidecar_payload,
)
from strategy.v3k_settings_surface import V3K_SETTINGS_SURFACE_VERSION  # noqa: E402


@dataclass(frozen=True)
class TempfileWriterResult:
    written: bool
    backup_created: bool
    rolled_back: bool
    diagnostics: tuple[str, ...]


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


def _payload(settings: Mapping[str, Any]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "surface_version": V3K_SETTINGS_SURFACE_VERSION,
        "settings": dict(settings),
        "updated_at": "2026-05-12T00:00:00+09:00",
        "source": V3K_GUI_SIDECAR_SOURCE,
    }


def _assert_outside_repo(target: Path) -> None:
    resolved = target.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return
    raise AssertionError(f"tempfile writer prototype must not target repo path: {resolved}")


def _write_sidecar_tempfile_only(
    target: Path,
    payload: Mapping[str, Any],
    *,
    simulate_replace_failure: bool = False,
) -> TempfileWriterResult:
    """Prototype the future writer contract inside caller-owned tempfile directories only."""

    _assert_outside_repo(target)
    validation = validate_v3k_gui_sidecar_payload(payload)
    if not validation.valid:
        return TempfileWriterResult(
            written=False,
            backup_created=False,
            rolled_back=True,
            diagnostics=("invalid payload rejected before write",) + validation.diagnostics,
        )

    backup_created = False
    if target.exists():
        existing = load_v3k_gui_sidecar_file(target)
        if not existing.valid:
            return TempfileWriterResult(
                written=False,
                backup_created=False,
                rolled_back=True,
                diagnostics=("existing sidecar corrupt; write rejected",) + existing.diagnostics,
            )
        backup = target.with_name(f"{target.name}.bak")
        shutil.copy2(target, backup)
        backup_created = backup.exists()

    tmp = target.with_name(f"{target.name}.tmp")
    before = target.read_text(encoding="utf-8") if target.exists() else None
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        if simulate_replace_failure:
            raise OSError("simulated replace failure")
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        after = target.read_text(encoding="utf-8") if target.exists() else None
        if after != before:
            raise AssertionError("rollback failed: target changed after replace failure") from exc
        return TempfileWriterResult(
            written=False,
            backup_created=backup_created,
            rolled_back=True,
            diagnostics=(f"write failed and rolled back: {exc.__class__.__name__}",),
        )

    return TempfileWriterResult(
        written=True,
        backup_created=backup_created,
        rolled_back=False,
        diagnostics=("tempfile-only atomic replace completed",),
    )


def _assert_invalid_payload_rejected(tmpdir: Path) -> None:
    target = tmpdir / "invalid.json"
    result = _write_sidecar_tempfile_only(
        target,
        {"schema_version": 999, "settings": {FLAG_ANALYSIS_UI: True}},
    )
    if result.written or target.exists() or not result.rolled_back:
        raise AssertionError(f"invalid payload must be rejected without writes: {result}")


def _assert_atomic_write_and_readback(tmpdir: Path) -> None:
    target = tmpdir / "valid.json"
    result = _write_sidecar_tempfile_only(
        target,
        _payload({FLAG_ANALYSIS_UI: True, FLAG_BACKTEST_LEARNING: "yes"}),
    )
    if not result.written or result.backup_created or not target.exists():
        raise AssertionError(f"first atomic write failed: {result}")
    loaded = load_v3k_gui_sidecar_file(target)
    if not loaded.valid:
        raise AssertionError(f"written sidecar did not validate: {loaded.diagnostics}")
    if loaded.settings[FLAG_ANALYSIS_UI] is not True:
        raise AssertionError("written sidecar did not preserve analysis UI flag")
    if loaded.settings[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("written sidecar did not normalize truthy backtest flag")


def _assert_backup_before_replace(tmpdir: Path) -> None:
    target = tmpdir / "replace.json"
    first_payload = _payload({FLAG_ANALYSIS_UI: True})
    second_payload = _payload({FLAG_ANALYSIS_UI: False, FLAG_BACKTEST_LEARNING: True})
    first = _write_sidecar_tempfile_only(target, first_payload)
    second = _write_sidecar_tempfile_only(target, second_payload)
    backup = target.with_name(f"{target.name}.bak")
    if not first.written or not second.written or not second.backup_created or not backup.exists():
        raise AssertionError(f"backup-before-replace contract failed: {first} / {second}")
    loaded_backup = load_v3k_gui_sidecar_file(backup)
    loaded_current = load_v3k_gui_sidecar_file(target)
    if not loaded_backup.valid or loaded_backup.settings[FLAG_ANALYSIS_UI] is not True:
        raise AssertionError("backup did not preserve previous valid state")
    if not loaded_current.valid or loaded_current.settings[FLAG_BACKTEST_LEARNING] is not True:
        raise AssertionError("replacement did not write current valid state")


def _assert_replace_failure_rolls_back(tmpdir: Path) -> None:
    target = tmpdir / "rollback.json"
    _write_sidecar_tempfile_only(target, _payload({FLAG_ANALYSIS_UI: True}))
    before = target.read_text(encoding="utf-8")
    result = _write_sidecar_tempfile_only(
        target,
        _payload({FLAG_ANALYSIS_UI: False, FLAG_BACKTEST_LEARNING: True}),
        simulate_replace_failure=True,
    )
    after = target.read_text(encoding="utf-8")
    if result.written or not result.rolled_back or before != after:
        raise AssertionError(f"replace failure did not roll back: {result}")
    if target.with_name(f"{target.name}.tmp").exists():
        raise AssertionError("temporary file leaked after simulated failure")


def _assert_corrupt_existing_rejected(tmpdir: Path) -> None:
    target = tmpdir / "corrupt-existing.json"
    target.write_text("{ not-json", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    result = _write_sidecar_tempfile_only(target, _payload({FLAG_ANALYSIS_UI: True}))
    after = target.read_text(encoding="utf-8")
    if result.written or not result.rolled_back or before != after:
        raise AssertionError(f"corrupt existing file must be preserved/rejected: {result}")


def main() -> None:
    before = _artifact_status()
    with tempfile.TemporaryDirectory(prefix="v3k-sidecar-writer-") as tmp:
        tmpdir = Path(tmp)
        _assert_invalid_payload_rejected(tmpdir)
        _assert_atomic_write_and_readback(tmpdir)
        _assert_backup_before_replace(tmpdir)
        _assert_replace_failure_rolls_back(tmpdir)
        _assert_corrupt_existing_rejected(tmpdir)

    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "tempfile writer prototype changed repo artifact status:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k GUI sidecar tempfile-only writer prototype smoke passed")
    print("atomic write, backup-before-replace, rollback, corruption rejection verified")


if __name__ == "__main__":
    main()
