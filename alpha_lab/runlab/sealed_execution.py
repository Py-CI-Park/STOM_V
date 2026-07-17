"""Evidence-bound, manifest-only staging for isolated runlab execution."""
from __future__ import annotations

import ctypes
import hashlib
import importlib.abc
import importlib.machinery
import json
import os
import shutil
import sys
import stat
import tempfile
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from alpha_lab.discipline.evidence import validate_gate_receipt, validate_gate_usage
from alpha_lab.discipline.prereg import _parse_contract


_WAIT_OBJECT_0 = 0
_WAIT_TIMEOUT = 258


class WindowsEvent(AbstractContextManager["WindowsEvent"]):
    """Small inherited Win32 event wrapper used only for locked runner handoffs."""

    def __init__(self, handle: int, *, owned: bool):
        self.handle = handle
        self._owned = owned

    @classmethod
    def create(cls) -> "WindowsEvent":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create = kernel32.CreateEventW
        create.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p)
        create.restype = ctypes.c_void_p
        handle = create(None, False, False, None)
        if handle is None:
            raise OSError(ctypes.get_last_error(), "CreateEventW failed")
        set_info = kernel32.SetHandleInformation
        set_info.argtypes = (ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong)
        set_info.restype = ctypes.c_int
        if not set_info(handle, 1, 1):
            close = kernel32.CloseHandle
            close.argtypes = (ctypes.c_void_p,)
            close.restype = ctypes.c_int
            close(handle)
            raise OSError(ctypes.get_last_error(), "SetHandleInformation failed")
        return cls(handle, owned=True)

    @classmethod
    def inherited(cls, raw_handle: str | int | None) -> "WindowsEvent | None":
        if raw_handle is None:
            return None
        try:
            handle = int(raw_handle)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("invalid inherited event handle") from exc
        if handle <= 0:
            raise RuntimeError("invalid inherited event handle")
        return cls(handle, owned=False)

    def set(self) -> None:
        set_event = ctypes.WinDLL("kernel32", use_last_error=True).SetEvent
        set_event.argtypes = (ctypes.c_void_p,)
        set_event.restype = ctypes.c_int
        if not set_event(self.handle):
            raise OSError(ctypes.get_last_error(), "SetEvent failed")

    def wait(self, timeout_ms: int) -> bool:
        wait = ctypes.WinDLL("kernel32", use_last_error=True).WaitForSingleObject
        wait.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
        wait.restype = ctypes.c_ulong
        result = wait(self.handle, timeout_ms)
        if result == _WAIT_OBJECT_0:
            return True
        if result == _WAIT_TIMEOUT:
            return False
        raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")

    def __enter__(self) -> "WindowsEvent":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._owned:
            close = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            close.argtypes = (ctypes.c_void_p,)
            close.restype = ctypes.c_int
            close(self.handle)


class WindowsJob(AbstractContextManager["WindowsJob"]):
    """Temporary job used to kill the wrapper tree before handoff completes."""

    def __init__(self):
        self.handle = None

    def __enter__(self) -> "WindowsJob":
        create = ctypes.WinDLL("kernel32", use_last_error=True).CreateJobObjectW
        create.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p)
        create.restype = ctypes.c_void_p
        self.handle = create(None, None)
        if self.handle is None:
            raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")
        return self

    def assign(self, process_handle: int) -> None:
        assign = ctypes.WinDLL("kernel32", use_last_error=True).AssignProcessToJobObject
        assign.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
        assign.restype = ctypes.c_int
        if not assign(self.handle, process_handle):
            raise OSError(ctypes.get_last_error(), "AssignProcessToJobObject failed")

    def terminate(self) -> None:
        terminate = ctypes.WinDLL("kernel32", use_last_error=True).TerminateJobObject
        terminate.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        terminate.restype = ctypes.c_int
        if self.handle and not terminate(self.handle, 1):
            raise OSError(ctypes.get_last_error(), "TerminateJobObject failed")

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.handle:
            close = ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle
            close.argtypes = (ctypes.c_void_p,)
            close.restype = ctypes.c_int
            close(self.handle)
            self.handle = None


def inherited_handle_startupinfo(handles: tuple[int, ...]):
    """Return Popen startupinfo that inherits exactly the supplied Win32 handles."""
    import subprocess
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.lpAttributeList = {"handle_list": list(handles)}
    return startupinfo
@dataclass(frozen=True)
class ExecutionEvidence:
    repo_root: Path
    receipt_path: Path
    claim_path: Path
    receipt: dict[str, Any]
    claim: dict[str, Any]
    dependency_roots: frozenset[str]


def _canonical_path(raw_path: str | Path, expected: Path, label: str) -> Path:
    if raw_path is None:
        raise RuntimeError(f"{label} is required")
    path = Path(raw_path).resolve()
    if path != expected:
        raise RuntimeError(f"{label} must be the canonical path: {expected}")
    return path


def _load_json(path: Path, label: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label} must be readable canonical JSON") from exc


def _is_reparse(path: Path) -> bool:
    return bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)


def _require_regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RuntimeError(f"{label} is not readable: {path}") from exc
    if path.is_symlink() or _is_reparse(path) or not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"{label} must be a regular non-link file: {path}")


def _manifest_path(repo_root: Path, relative: str, label: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise RuntimeError(f"{label} has an unsafe manifest path: {relative!r}")
    path = repo_root.joinpath(*posix.parts)
    if path.resolve() != path:
        raise RuntimeError(f"{label} resolves outside its canonical repository path")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_paths(evidence: ExecutionEvidence) -> frozenset[str]:
    return frozenset(item["path"] for item in evidence.receipt["code_manifest"])


def _load_execution_evidence(repo_root: str | Path, receipt_path: str | Path,
                             claim_path: str | Path) -> ExecutionEvidence:
    """Validate and parse only files already retained by the caller."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"repo root is not a directory: {root}")
    raw_receipt = _load_json(Path(receipt_path), "receipt")
    try:
        receipt = validate_gate_receipt(raw_receipt, repo_root=root)
    except Exception as exc:
        raise RuntimeError(f"invalid gate receipt: {exc}") from exc
    receipt_id = receipt["receipt_id"]
    receipt_file = _canonical_path(receipt_path, root / "receipts" / f"{receipt_id}.json", "receipt")
    claim_file = _canonical_path(claim_path, root / "claims" / f"{receipt_id}.json", "claim")
    try:
        claim = validate_gate_usage(_load_json(claim_file, "claim"), receipt=receipt)
    except Exception as exc:
        raise RuntimeError(f"invalid gate claim: {exc}") from exc
    try:
        seal = _load_json(_manifest_path(root, receipt["seal_manifest"]["path"], "seal manifest"), "seal manifest")
        contract = _parse_contract(
            _manifest_path(root, seal["sealed_doc"]["path"], "sealed prereg").read_text(encoding="utf-8"), root)
        roots = frozenset(contract["dependency_roots"])
    except Exception as exc:
        raise RuntimeError(f"invalid sealed prereg contract: {exc}") from exc
    return ExecutionEvidence(root, receipt_file, claim_file, receipt, claim, roots)


def load_execution_evidence(repo_root: str | Path, receipt_path: str | Path,
                            claim_path: str | Path) -> ExecutionEvidence:
    """Return a fully revalidated evidence snapshot without retaining execution locks."""
    with locked_execution(repo_root, receipt_path, claim_path) as evidence:
        return evidence


def _target_relative(evidence: ExecutionEvidence, target: str | Path) -> str:
    path = Path(target)
    if not path.is_absolute():
        path = evidence.repo_root / path
    try:
        relative = path.resolve().relative_to(evidence.repo_root).as_posix()
    except ValueError as exc:
        raise RuntimeError("target must be inside the repository") from exc
    if relative not in evidence.dependency_roots:
        raise RuntimeError("target must be an exact sealed dependency_roots entry")
    return relative


def _validate_stage_tree(stage: Path, manifest: frozenset[str]) -> None:
    expected_files = {stage.joinpath(*PurePosixPath(path).parts) for path in manifest}
    expected_dirs = {stage}
    for path in expected_files:
        parent = path.parent
        while True:
            expected_dirs.add(parent)
            if parent == stage:
                break
            try:
                parent = parent.relative_to(stage).parent
                parent = stage / parent
            except ValueError as exc:
                raise RuntimeError("manifest stage path escapes stage root") from exc
    actual_files: set[Path] = set()
    actual_dirs: set[Path] = set()
    for root, dirs, files in os.walk(stage, topdown=True, followlinks=False):
        directory = Path(root)
        if directory.is_symlink() or _is_reparse(directory):
            raise RuntimeError(f"stage directory must not be a link/reparse point: {directory}")
        actual_dirs.add(directory)
        for name in [*dirs, *files]:
            candidate = directory / name
            if candidate.is_symlink() or _is_reparse(candidate):
                raise RuntimeError(f"stage must not contain a link/reparse point: {candidate}")
        for name in files:
            candidate = directory / name
            _require_regular(candidate, "staged code manifest")
            actual_files.add(candidate)
    if actual_files != expected_files or actual_dirs != expected_dirs:
        raise RuntimeError("stage must contain exactly the manifest files and directories")


def stage_execution(run_dir: str | Path, evidence: ExecutionEvidence,
                    target: str | Path) -> tuple[Path, Path]:
    """Copy verified manifest files into a unique stage with no ambient source tree."""
    target_relative = _target_relative(evidence, target)
    run_path = Path(run_dir).resolve()
    run_path.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="sealed-stage-", dir=run_path))
    manifest = _manifest_paths(evidence)
    try:
        for item in evidence.receipt["code_manifest"]:
            source = _manifest_path(evidence.repo_root, item["path"], "code manifest")
            destination = stage.joinpath(*PurePosixPath(item["path"]).parts)
            _require_regular(source, "code manifest source")
            if _sha256(source) != item["sha256"]:
                raise RuntimeError(f"code manifest source hash changed: {item['path']}")
            if destination.exists() or destination.is_symlink():
                raise RuntimeError(f"code manifest destination collision: {item['path']}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            _require_regular(destination, "staged code manifest")
            if _sha256(destination) != item["sha256"]:
                raise RuntimeError(f"staged code manifest hash changed: {item['path']}")
            destination.chmod(stat.S_IREAD)
        for directory in {stage, *(path.parent for path in (stage.joinpath(*PurePosixPath(p).parts) for p in manifest))}:
            directory.chmod(stat.S_IREAD | stat.S_IEXEC)
        _validate_stage_tree(stage, manifest)
        return stage, stage.joinpath(*PurePosixPath(target_relative).parts)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _validate_staged_evidence(evidence: ExecutionEvidence, stage_root: str | Path,
                              target: str | Path) -> ExecutionEvidence:
    stage = Path(stage_root).resolve()
    if not stage.is_dir() or stage.is_symlink() or _is_reparse(stage):
        raise RuntimeError("stage root must be a non-link directory")
    expected_targets = {stage.joinpath(*PurePosixPath(p).parts).resolve()
                        for p in evidence.dependency_roots}
    if Path(target).resolve() not in expected_targets:
        raise RuntimeError("target must be the exact staged dependency root")
    manifest = _manifest_paths(evidence)
    _validate_stage_tree(stage, manifest)
    for item in evidence.receipt["code_manifest"]:
        source = _manifest_path(evidence.repo_root, item["path"], "code manifest")
        staged = stage.joinpath(*PurePosixPath(item["path"]).parts)
        _require_regular(source, "code manifest source")
        _require_regular(staged, "staged code manifest")
        if _sha256(source) != item["sha256"] or _sha256(staged) != item["sha256"]:
            raise RuntimeError(f"code manifest hash changed: {item['path']}")
    return evidence


def validate_staged_execution(repo_root: str | Path, receipt_path: str | Path,
                              claim_path: str | Path, stage_root: str | Path,
                              target: str | Path) -> ExecutionEvidence:
    """Revalidate evidence, all live/staged hashes, exact tree, and target binding."""
    with locked_execution(repo_root, receipt_path, claim_path, stage_root, target) as evidence:
        return evidence


class StageLocks(AbstractContextManager["StageLocks"]):
    """Retain read-only Windows handles for the complete execution snapshot."""

    def __init__(self, stage_root: str | Path, manifest: frozenset[str],
                 extra_paths: tuple[Path, ...] = (), *, include_stage: bool = True):
        self._stage = Path(stage_root).resolve()
        files = [self._stage.joinpath(*PurePosixPath(item).parts) for item in manifest]
        directories = {self._stage} if include_stage else set()
        for file_path in files:
            parent = file_path.parent
            while parent != self._stage:
                directories.add(parent)
                parent = parent.parent
        self._paths = list(dict.fromkeys(
            [*sorted(directories, key=str), *sorted(files, key=str), *extra_paths]))
        self._handles: list[Any] = []
        self._close_handle = None

    def __enter__(self) -> "StageLocks":
        if os.name != "nt":
            raise RuntimeError("sealed execution requires Windows retained-handle locking")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                ctypes.c_void_p)
        create_file.restype = ctypes.c_void_p
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        close_handle.restype = ctypes.c_int
        get_final = kernel32.GetFinalPathNameByHandleW
        get_final.argtypes = (ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_ulong,
                              ctypes.c_ulong)
        get_final.restype = ctypes.c_ulong
        self._close_handle = close_handle
        invalid = ctypes.c_void_p(-1).value
        try:
            for raw_path in self._paths:
                path = raw_path.resolve()
                flags = 0x00200000 | (0x02000000 if path.is_dir() else 0)
                handle = create_file(str(path), 0x80000000, 0x00000001, None, 3,
                                     flags, None)
                if handle is None or handle == invalid:
                    raise OSError(ctypes.get_last_error(), f"cannot lock path: {path}")
                self._handles.append(handle)
                size = get_final(handle, None, 0, 0)
                buffer = ctypes.create_unicode_buffer(size + 1)
                if not size or not get_final(handle, buffer, len(buffer), 0):
                    raise OSError(ctypes.get_last_error(), f"cannot identify locked path: {path}")
                final = Path(buffer.value.removeprefix("\\\\?\\")).resolve()
                if final != path or _is_reparse(path):
                    raise RuntimeError(f"locked path identity changed: {path}")
                if path.is_file() and path.stat(follow_symlinks=False).st_nlink != 1:
                    raise RuntimeError(f"locked file has hardlink aliases: {path}")
        except Exception:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._close_handle is not None:
            for handle in reversed(self._handles):
                self._close_handle(handle)
        self._handles.clear()


def lock_stage(stage_root: str | Path, evidence: ExecutionEvidence,
               extra_paths: tuple[Path, ...] = ()) -> StageLocks:
    return StageLocks(stage_root, _manifest_paths(evidence), extra_paths)


class _LockedExecution(AbstractContextManager[ExecutionEvidence]):
    """Hold authority, live manifest, and runner inputs through revalidation."""

    def __init__(self, repo_root: str | Path, receipt_path: str | Path,
                 claim_path: str | Path, stage_root: str | Path | None = None,
                 target: str | Path | None = None):
        self._root = Path(repo_root).resolve()
        self._receipt_path = Path(receipt_path).resolve()
        self._claim_path = Path(claim_path).resolve()
        self._stage_root = None if stage_root is None else Path(stage_root).resolve()
        self._target = target
        self._locks: StageLocks | None = None
        self._stage_locks: StageLocks | None = None

    def __enter__(self) -> ExecutionEvidence:
        preliminary = _load_json(self._receipt_path, "receipt")
        if not isinstance(preliminary, dict) or not isinstance(preliminary.get("receipt_id"), str):
            raise RuntimeError("receipt must contain a receipt_id")
        receipt = _canonical_path(self._receipt_path,
                                  self._root / "receipts" / f"{preliminary['receipt_id']}.json",
                                  "receipt")
        claim = _canonical_path(self._claim_path,
                                self._root / "claims" / f"{preliminary['receipt_id']}.json",
                                "claim")
        seal_ref = preliminary.get("seal_manifest")
        if not isinstance(seal_ref, dict) or not isinstance(seal_ref.get("path"), str):
            raise RuntimeError("receipt must contain a seal manifest path")
        seal_path = _manifest_path(self._root, seal_ref["path"], "seal manifest")
        seal = _load_json(seal_path, "seal manifest")
        if not isinstance(seal, dict) or not isinstance(seal.get("sealed_doc"), dict):
            raise RuntimeError("seal manifest must contain a sealed prereg path")
        prereg_path = _manifest_path(self._root, seal["sealed_doc"].get("path"), "sealed prereg")
        manifest = preliminary.get("code_manifest")
        live = () if not isinstance(manifest, list) else tuple(
            _manifest_path(self._root, item["path"], "code manifest")
            for item in manifest if isinstance(item, dict) and isinstance(item.get("path"), str))
        runner_root = Path(__file__).resolve().parents[2]
        runner = tuple(runner_root / path for path in (
            "alpha_lab/__init__.py", "alpha_lab/runlab/__init__.py",
            "alpha_lab/runlab/bootstrap.py", "alpha_lab/runlab/child_wrap.py",
            "alpha_lab/runlab/detached_runner.py", "alpha_lab/runlab/sealed_execution.py",
            "alpha_lab/runlab/contract.py", "alpha_lab/runlab/watchdog.py",
            "alpha_lab/discipline/__init__.py", "alpha_lab/discipline/evidence.py",
            "alpha_lab/discipline/prereg.py"))
        self._locks = StageLocks(self._root, frozenset(),
                                 (receipt, claim, seal_path, prereg_path, *live, *runner),
                                 include_stage=False)
        self._locks.__enter__()
        try:
            evidence = _load_execution_evidence(self._root, receipt, claim)
            if self._stage_root is not None:
                if self._target is None:
                    raise RuntimeError("stage lock requires a target")
                self._stage_locks = StageLocks(self._stage_root, _manifest_paths(evidence))
                self._stage_locks.__enter__()
                evidence = _load_execution_evidence(self._root, receipt, claim)
                _validate_staged_evidence(evidence, self._stage_root, self._target)
            return evidence
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._stage_locks is not None:
            self._stage_locks.__exit__(exc_type, exc, traceback)
        if self._locks is not None:
            self._locks.__exit__(exc_type, exc, traceback)


def locked_execution(repo_root: str | Path, receipt_path: str | Path,
                     claim_path: str | Path, stage_root: str | Path | None = None,
                     target: str | Path | None = None) -> _LockedExecution:
    return _LockedExecution(repo_root, receipt_path, claim_path, stage_root, target)


class _ManifestFinder(importlib.abc.MetaPathFinder):
    def __init__(self, stage_root: Path, manifest: frozenset[str],
                 trusted_import_roots: tuple[Path, ...] = ()):
        self._stage = stage_root.resolve()
        self._manifest = manifest
        self._trusted = tuple(path.resolve() for path in trusted_import_roots)

    def _allowed_root(self, path: Path) -> bool:
        return path == self._stage or path.is_relative_to(self._stage) or any(
            path == root or path.is_relative_to(root) for root in self._trusted)

    def find_spec(self, fullname, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.origin in ("built-in", "frozen"):
            return spec
        if spec.origin is None:
            locations = spec.submodule_search_locations
            if locations is None or any(not self._allowed_root(Path(item).resolve())
                                        for item in locations):
                raise ImportError(f"untrusted namespace import rejected: {fullname}")
            return spec
        origin = Path(spec.origin).resolve()
        if not self._allowed_root(origin):
            raise ImportError(f"untrusted import origin rejected: {fullname}")
        try:
            relative = origin.relative_to(self._stage).as_posix()
        except ValueError:
            return spec
        if relative not in self._manifest:
            raise ImportError(f"unmanifested staged import rejected: {fullname}")
        return spec


class ManifestImportGate(AbstractContextManager["ManifestImportGate"]):
    """Reject imports whose resolved staged source is absent from the receipt manifest."""
    def __init__(self, stage_root: str | Path, evidence: ExecutionEvidence,
                 trusted_import_roots: tuple[Path, ...] = ()):
        self._finder = _ManifestFinder(Path(stage_root), _manifest_paths(evidence),
                                       trusted_import_roots)

    def __enter__(self) -> "ManifestImportGate":
        import sys
        sys.meta_path.insert(0, self._finder)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        import sys
        if self._finder in sys.meta_path:
            sys.meta_path.remove(self._finder)


def manifest_import_gate(stage_root: str | Path, evidence: ExecutionEvidence,
                         trusted_import_roots: tuple[Path, ...] = ()) -> ManifestImportGate:
    return ManifestImportGate(stage_root, evidence, trusted_import_roots)
