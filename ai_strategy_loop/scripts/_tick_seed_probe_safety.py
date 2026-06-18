from __future__ import annotations

import tempfile
from pathlib import Path

import psutil

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]

FORBIDDEN_TOKENS = ("final_approval", "export_winner", "khopenapi", "v3k", "taskkill")
PROTECTED_DIR_NAMES = {
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "graph",
    "_v3k_sidecar",
    "state",
}


def assert_safe_command(command: list[str]) -> None:
    joined = " ".join(command).lower()
    found = [token for token in FORBIDDEN_TOKENS if token in joined]
    if found:
        raise RuntimeError(f"forbidden token in diagnostic command: {found}")


def assert_safe_output_path(path: Path, *, repo_root: Path) -> Path:
    resolved = path.resolve()
    if _is_protected_output_path(resolved):
        raise RuntimeError(f"diagnostic output path targets protected runtime area: {resolved}")
    if not _is_allowed_output_root(resolved, repo_root=repo_root):
        raise RuntimeError(f"diagnostic output path must be under .omo or temp: {resolved}")
    return resolved


def terminate_process_tree(pid: int, *, grace_seconds: int) -> JsonObject:
    try:
        parent = psutil.Process(pid)
    except psutil.Error as exc:
        return {
            "parent_pid": pid,
            "descendant_pids": [],
            "terminated_pids": [],
            "killed_pids": [],
            "errors": [f"process lookup failed: {exc}"],
        }

    descendants = parent.children(recursive=True)
    targets = [*descendants, parent]
    terminated_pids: list[int] = []
    killed_pids: list[int] = []
    errors: list[str] = []

    for proc in targets:
        try:
            proc.terminate()
            terminated_pids.append(int(proc.pid))
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as exc:
            errors.append(f"terminate failed for {int(proc.pid)}: {exc}")

    _, alive = psutil.wait_procs(targets, timeout=grace_seconds)
    for proc in alive:
        try:
            proc.kill()
            killed_pids.append(int(proc.pid))
        except psutil.NoSuchProcess:
            continue
        except psutil.Error as exc:
            errors.append(f"kill failed for {int(proc.pid)}: {exc}")

    if alive:
        psutil.wait_procs(alive, timeout=grace_seconds)

    return {
        "parent_pid": pid,
        "descendant_pids": [int(proc.pid) for proc in descendants],
        "terminated_pids": terminated_pids,
        "killed_pids": killed_pids,
        "errors": errors,
    }


def _is_allowed_output_root(path: Path, *, repo_root: Path) -> bool:
    roots = [repo_root.resolve() / ".omo", Path(tempfile.gettempdir()).resolve()]
    for root in roots:
        if _is_relative_to(path, root):
            return True
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _is_protected_output_path(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    if path.suffix.lower() == ".db":
        return True
    if path.name.lower().startswith("v3k_settings") and path.suffix.lower() == ".json":
        return True
    if "backtest" in parts and "graph" in parts:
        return True
    return any(part in PROTECTED_DIR_NAMES for part in parts)
