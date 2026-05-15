"""V3K Kiwoom V2-compat sentinel helpers (Synthesis 1 — primary S1 단독 산식).

Single responsibility: probe the three Kiwoom sentinel signals defined in
``docs/plans/2026-05-14_v3k_audit_v2_compat_kiwoom_sentinel_plan.md`` §B.1 and
emit pure dict evidence rows. The hook and audit emitter both consume from this
module so that the primary/corroborating split (§B.2) and the audit JSON
schema v2 (§B.4) stay aligned at a single source of truth.

Invariants (mirror of plan §B.3 L1–L9):
- L1. registry probe is winreg.OpenKey READ-only.
- L2. setting_base lookup is local to this module — no caller leakage.
- L3. legacy DLL probe uses Path.exists() only.
- L4. every probe catches its own exceptions and returns False — never aborts.
- L8. helper output is dict evidence, never Path coercion (Windows drive-letter safety, Rev2).
- R8. single-direction import: this module never imports the hook.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


KHOPENAPI_PROGID = "KHOPENAPI.KHOpenAPICtrl.1"
KHOPENAPI_REGISTRY_PATH = f"HKEY_CLASSES_ROOT\\{KHOPENAPI_PROGID}"

DEFAULT_LEGACY_DLL_CANDIDATES: tuple[str, ...] = (
    r"C:\OpenAPI\khopenapi.dll",
    r"C:\Kiwoom\OpenAPI\khopenapi.dll",
    r"C:\OpenAPI-W\khopenapi.dll",
)

_OPENAPI_DIRECTORY_SIGNAL_FILES: tuple[str, ...] = (
    "inicore_v2.3.42.dll",
    "inicore_v2.3.32.dll",
    "aossdk.dll",
    "astxmanager.dll",
    "absolutedown.ini",
    "default.lic",
)


def _active_x_progid_registered(progid: str = KHOPENAPI_PROGID) -> bool:
    """Return True iff the Kiwoom ActiveX ProgID is registered in HKEY_CLASSES_ROOT.

    Uses ``winreg.OpenKey`` READ-only. Returns False on non-Windows hosts or
    when the key is absent. Never raises (L4).
    """
    try:
        import winreg  # type: ignore[attr-defined]
    except ImportError:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid):
            return True
    except OSError:
        return False
    except Exception:
        return False


def _setting_base_openapi_path() -> Path | None:
    """Return the ``utility.setting_base.OPENAPI_PATH`` directory if it exists.

    Returns None if the module cannot be imported, the attribute is missing,
    or the resolved path is not a directory. Never raises (L4).
    """
    try:
        from utility.setting_base import OPENAPI_PATH  # type: ignore[attr-defined]
    except Exception:
        return None

    try:
        candidate = Path(OPENAPI_PATH)
    except (TypeError, ValueError):
        return None

    try:
        return candidate if candidate.is_dir() else None
    except OSError:
        return None


def _count_directory_signal_files(directory: Path) -> int:
    """Count how many Kiwoom OpenAPI+ signal files are present in ``directory``."""
    count = 0
    for name in _OPENAPI_DIRECTORY_SIGNAL_FILES:
        try:
            if (directory / name).is_file():
                count += 1
        except OSError:
            continue
    return count


def probe_primary_signal() -> dict[str, Any]:
    """Probe the ActiveX ProgID (S1) — the V2-compat primary signal."""
    exists = _active_x_progid_registered()
    return {
        "source": "ActiveX ProgID",
        "path": KHOPENAPI_REGISTRY_PATH,
        "exists": exists,
    }


def probe_openapi_directory_signal() -> dict[str, Any]:
    """Probe the ``OPENAPI_PATH`` directory + DLL inventory (S2 corroborating)."""
    directory = _setting_base_openapi_path()
    if directory is None:
        return {
            "source": "OPENAPI_PATH directory",
            "path": "(unresolvable)",
            "exists": False,
            "dll_count": 0,
        }
    return {
        "source": "OPENAPI_PATH directory",
        "path": str(directory),
        "exists": True,
        "dll_count": _count_directory_signal_files(directory),
    }


def probe_legacy_dll_signal(extra_candidates: tuple[str, ...] = ()) -> dict[str, Any]:
    """Probe the legacy ``khopenapi.dll`` file (S3 corroborating)."""
    candidates: list[str] = list(extra_candidates) + list(DEFAULT_LEGACY_DLL_CANDIDATES)
    for raw in candidates:
        path = Path(raw)
        try:
            if path.is_file():
                return {
                    "source": "legacy DLL",
                    "path": str(path),
                    "exists": True,
                }
        except OSError:
            continue
    return {
        "source": "legacy DLL",
        "path": candidates[0] if candidates else "",
        "exists": False,
    }


def collect_corroborating_signals(extra_legacy_candidates: tuple[str, ...] = ()) -> tuple[dict[str, Any], ...]:
    """Return the S2 + S3 corroborating evidence in audit emit order (L7)."""
    return (
        probe_openapi_directory_signal(),
        probe_legacy_dll_signal(extra_legacy_candidates),
    )


def corroboration_count(signals: tuple[dict[str, Any], ...]) -> int:
    """Count how many corroborating signals report exists=True."""
    return sum(1 for signal in signals if bool(signal.get("exists")))
