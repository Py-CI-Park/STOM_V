"""Isolated runlab entry point.

Invoke only by its absolute tracked path:
    python -I -S <absolute bootstrap.py> <detached-runner|child-wrap|target> ...

Before importing project code this module preserves the interpreter's ``-I -S`` startup
roots, adds trusted site-package roots, and appends this checkout's exact repository root.
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
_INITIAL_INTERPRETER_PATH = tuple(sys.path)

import importlib
from contextlib import AbstractContextManager
import importlib.abc
import importlib.util
from importlib.machinery import PathFinder
import runpy
import sysconfig
from pathlib import Path
from typing import Sequence


_MODES = {"detached-runner", "child-wrap", "target"}
_RUNNER_SOURCE_FILES = (
    "alpha_lab/__init__.py",
    "alpha_lab/runlab/__init__.py",
    "alpha_lab/runlab/bootstrap.py",
    "alpha_lab/runlab/child_wrap.py",
    "alpha_lab/runlab/detached_runner.py",
    "alpha_lab/runlab/sealed_execution.py",
    "alpha_lab/runlab/contract.py",
    "alpha_lab/runlab/watchdog.py",
    "alpha_lab/discipline/__init__.py",
    "alpha_lab/discipline/evidence.py",
    "alpha_lab/discipline/prereg.py",
)
_RUNNER_SOURCE_SHA256 = {
    "alpha_lab/__init__.py": "09f4bc71af7a3ea87743b2fde48b040c0cb6e8e02214606637214c22f51f13c6",
    "alpha_lab/runlab/__init__.py": "529d7083064981e855fa107e162440bd231cbef176a1f10eaac318ea6d893b4c",
    "alpha_lab/runlab/child_wrap.py": "ec686e945a1451d9bf71c96bf284bb93ff15b374ee60a909a16f7595abfb43c9",
    "alpha_lab/runlab/detached_runner.py": "ab2c58e632576e5ddb5d9bc093e0e0fe9bfd1108f819a5ff077395ba9a2ab5ae",
    "alpha_lab/runlab/sealed_execution.py": "675e0f340faec15f0e67ca654adf78a3f1e36260533174f73920e64e4dc41a7c",
    "alpha_lab/runlab/contract.py": "696c970d4cc54b856f41fb6f70ed7e0c038941c7008fb75bf2ef5066e3fba284",
    "alpha_lab/runlab/watchdog.py": "ee54c8c0c06d3d38bc34bdb99a5fd7291a3e115ec22aadfd4f630c69eb359d1d",
    "alpha_lab/discipline/__init__.py": "7b61a8fdc21fd783d3a9e298863f57b3dd51fba62de35705c03bf1cccb84e787",
    "alpha_lab/discipline/evidence.py": "fdb03d25767be9c7cafb1ac4c9098583b8b46ef7ecec788f0084e0b5ae7f428f",
    "alpha_lab/discipline/prereg.py": "afce02815291d879660385fb39c5b2067f471ee55fd6f0ca1c913878416e74ce",
}


class _RunnerSourceLocks(AbstractContextManager["_RunnerSourceLocks"]):
    """Retain the externally trusted runner sources before importing runlab code."""

    def __init__(self, root: Path):
        self._paths = tuple(root / item for item in _RUNNER_SOURCE_FILES)
        self._handles = []
        self._close_handle = None

    @staticmethod
    def _retained_sha256(kernel32, handle) -> str:
        seek = kernel32.SetFilePointerEx
        seek.argtypes = (ctypes.c_void_p, ctypes.c_longlong,
                         ctypes.POINTER(ctypes.c_longlong), ctypes.c_ulong)
        seek.restype = ctypes.c_int
        read = kernel32.ReadFile
        read.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong,
                         ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p)
        read.restype = ctypes.c_int
        if not seek(handle, 0, None, 0):
            raise OSError(ctypes.get_last_error(), "cannot seek retained runner source")
        digest = __import__("hashlib").sha256()
        buffer = ctypes.create_string_buffer(65536)
        count = ctypes.c_ulong()
        while True:
            if not read(handle, buffer, len(buffer), ctypes.byref(count), None):
                raise OSError(ctypes.get_last_error(), "cannot read retained runner source")
            if not count.value:
                return digest.hexdigest()
            digest.update(buffer.raw[:count.value])

    @staticmethod
    def _handle_info(kernel32, handle):
        class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("dwFileAttributes", ctypes.c_ulong), ("ftCreationTimeLow", ctypes.c_ulong),
                ("ftCreationTimeHigh", ctypes.c_ulong), ("ftLastAccessTimeLow", ctypes.c_ulong),
                ("ftLastAccessTimeHigh", ctypes.c_ulong), ("ftLastWriteTimeLow", ctypes.c_ulong),
                ("ftLastWriteTimeHigh", ctypes.c_ulong), ("dwVolumeSerialNumber", ctypes.c_ulong),
                ("nFileSizeHigh", ctypes.c_ulong), ("nFileSizeLow", ctypes.c_ulong),
                ("nNumberOfLinks", ctypes.c_ulong), ("nFileIndexHigh", ctypes.c_ulong),
                ("nFileIndexLow", ctypes.c_ulong),
            ]
        get_info = kernel32.GetFileInformationByHandle
        get_info.argtypes = (ctypes.c_void_p, ctypes.POINTER(BY_HANDLE_FILE_INFORMATION))
        get_info.restype = ctypes.c_int
        info = BY_HANDLE_FILE_INFORMATION()
        if not get_info(handle, ctypes.byref(info)):
            raise OSError(ctypes.get_last_error(), "cannot inspect retained runner source")
        return info
    def __enter__(self) -> "_RunnerSourceLocks":
        if os.name != "nt":
            raise RuntimeError("bootstrap requires Windows retained source locks")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p,
        )
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
        expected_keys = set(_RUNNER_SOURCE_FILES) - {"alpha_lab/runlab/bootstrap.py"}
        if set(_RUNNER_SOURCE_SHA256) != expected_keys:
            raise RuntimeError("runner source hash manifest is incomplete")
        try:
            for raw_path in self._paths:
                path = raw_path.resolve()
                relative = path.relative_to(Path(__file__).resolve().parents[2]).as_posix()
                info = path.lstat()
                before_hash = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
                if path.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise RuntimeError(f"runner source is a link/reparse point: {path}")
                if info.st_nlink != 1:
                    raise RuntimeError(f"runner source has hardlink aliases: {path}")
                handle = create_file(str(path), 0x80000000, 0x00000001, None, 3,
                                     0x00200000, None)
                if handle is None or handle == invalid:
                    raise OSError(ctypes.get_last_error(), f"cannot lock runner source: {path}")
                self._handles.append(handle)
                opened = self._handle_info(kernel32, handle)
                opened_index = opened.nFileIndexHigh << 32 | opened.nFileIndexLow
                if (opened.dwFileAttributes & 0x400 or opened.nNumberOfLinks != 1
                        or opened_index != info.st_ino
                        or (opened.nFileSizeHigh << 32 | opened.nFileSizeLow) != info.st_size):
                    raise RuntimeError(f"runner source opened-handle identity changed: {path}")
                retained_hash = self._retained_sha256(kernel32, handle)
                if retained_hash != before_hash:
                    raise RuntimeError(f"runner source changed between precheck and lock: {path}")
                expected_hash = _RUNNER_SOURCE_SHA256.get(relative)
                if expected_hash is not None and retained_hash != expected_hash:
                    raise RuntimeError(f"runner source does not match trusted hash: {path}")
                size = get_final(handle, None, 0, 0)
                buffer = ctypes.create_unicode_buffer(size + 1)
                if not size or not get_final(handle, buffer, len(buffer), 0):
                    raise OSError(ctypes.get_last_error(), f"cannot identify runner source: {path}")
                if Path(buffer.value.removeprefix("\\\\?\\")).resolve() != path:
                    raise RuntimeError(f"runner source identity changed: {path}")
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._close_handle is not None:
            for handle in reversed(self._handles):
                self._close_handle(handle)
        self._handles.clear()


def _lock_runner_sources(root: Path) -> _RunnerSourceLocks:
    return _RunnerSourceLocks(root)
class _RunnerSourceLoader(importlib.abc.Loader):
    """Execute locked runner source bytes directly; bytecode caches are never consulted."""

    def __init__(self, fullname: str, path: Path, is_package: bool):
        self._fullname = fullname
        self._path = path
        self._is_package = is_package

    def create_module(self, spec):
        return None

    def exec_module(self, module) -> None:
        source = self._path.read_bytes()
        relative = self._path.relative_to(repo_root()).as_posix()
        expected = _RUNNER_SOURCE_SHA256.get(relative)
        if expected is not None and __import__("hashlib").sha256(source).hexdigest() != expected:
            raise ImportError(f"trusted runner source hash changed: {relative}")
        module.__file__ = str(self._path)
        if self._is_package:
            module.__path__ = [str(self._path.parent)]
        exec(compile(source, str(self._path), "exec"), module.__dict__)


class _RunnerSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, root: Path):
        self._mapping = {}
        for relative in _RUNNER_SOURCE_FILES:
            path = root / relative
            parts = Path(relative).with_suffix("").parts
            is_package = parts[-1] == "__init__"
            name = ".".join(parts[:-1] if is_package else parts)
            self._mapping[name] = (path, is_package)

    def find_spec(self, fullname, path=None, target=None):
        entry = self._mapping.get(fullname)
        if entry is None:
            return None
        source, is_package = entry
        return importlib.util.spec_from_loader(
            fullname, _RunnerSourceLoader(fullname, source, is_package),
            is_package=is_package)


class _RunnerSourceImports(AbstractContextManager["_RunnerSourceImports"]):
    def __init__(self, root: Path):
        self._finder = _RunnerSourceFinder(root)
        self._names = frozenset(self._finder._mapping)

    def __enter__(self) -> "_RunnerSourceImports":
        preloaded = self._names.intersection(sys.modules) - {"__main__"}
        if preloaded:
            raise RuntimeError("runner modules were loaded before trusted source import")
        sys.dont_write_bytecode = True
        sys.meta_path.insert(0, self._finder)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._finder in sys.meta_path:
            sys.meta_path.remove(self._finder)


def _runner_source_imports(root: Path) -> _RunnerSourceImports:
    return _RunnerSourceImports(root)


def _absolute_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path).resolve()
    if not path.is_absolute():
        raise RuntimeError(f"unresolved trusted {label} path: {raw_path!r}")
    return path


def _absolute_directory(raw_path: str, label: str) -> Path:
    path = _absolute_path(raw_path, label)
    if not path.is_dir():
        raise RuntimeError(f"unresolved trusted {label} directory: {raw_path!r}")
    return path


def trusted_import_roots() -> tuple[Path, ...]:
    """Preserve isolated startup roots and append interpreter site-package roots."""
    roots = []
    for raw_path in _INITIAL_INTERPRETER_PATH:
        if not raw_path:
            continue
        path = _absolute_path(raw_path, "startup")
        if path not in roots:
            roots.append(path)
    for label in ("purelib", "platlib"):
        raw_path = sysconfig.get_paths().get(label)
        if not raw_path:
            raise RuntimeError(f"unresolved trusted {label} path")
        path = _absolute_directory(raw_path, label)
        if path not in roots:
            roots.append(path)
    return tuple(roots)


def repo_root() -> Path:
    """Derive the checkout root solely from this tracked bootstrap path."""
    root = Path(__file__).resolve().parents[2]
    if not (root / "alpha_lab" / "runlab" / "bootstrap.py").samefile(__file__):
        raise RuntimeError("bootstrap path does not resolve to the tracked runlab file")
    return root


def _package_exists(package: str, paths: Sequence[Path]) -> bool:
    """Resolve one package against only the supplied sealed roots."""
    return PathFinder.find_spec(package, [str(path) for path in paths]) is not None


def seal_import_path() -> tuple[str, ...]:
    """Replace caller-derived import paths with trusted roots and this checkout."""
    root = repo_root()
    trusted = trusted_import_roots()
    if root in trusted or any(root.is_relative_to(path) or path.is_relative_to(root)
                               for path in trusted):
        raise RuntimeError("local and interpreter import roots are ambiguous")
    if not _package_exists("alpha_lab", (root,)):
        raise RuntimeError("unresolved local alpha_lab package")
    if _package_exists("alpha_lab", trusted):
        raise RuntimeError("local and external alpha_lab packages are ambiguous")
    sealed = tuple(str(path) for path in (*trusted, root))
    if len(sealed) != len(set(sealed)):
        raise RuntimeError("local and interpreter import roots are ambiguous")
    sys.path[:] = list(sealed)
    return sealed


def _run_target(argv: Sequence[str], sealed_execution) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.py target")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--claim", required=True)
    parser.add_argument("--stage-root", required=True)
    parser.add_argument("--target-ready-handle", default=None)
    parser.add_argument("target")
    parser.add_argument("target_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    WindowsEvent = sealed_execution.WindowsEvent
    locked_execution = sealed_execution.locked_execution
    manifest_import_gate = sealed_execution.manifest_import_gate
    stage_root = Path(args.stage_root).resolve()
    target = Path(args.target).resolve()
    if not target.is_relative_to(stage_root):
        raise SystemExit("target mode requires a target inside the sealed stage")
    trusted = trusted_import_roots()
    if stage_root in trusted or any(stage_root.is_relative_to(path)
                                    or path.is_relative_to(stage_root)
                                    for path in trusted):
        raise SystemExit("stage and interpreter import roots are ambiguous")
    target_ready = WindowsEvent.inherited(args.target_ready_handle)
    with locked_execution(
        args.repo_root, args.receipt, args.claim, stage_root, target,
    ) as evidence:
        for name, module in tuple(sys.modules.items()):
            if name == "__main__":
                continue
            module_file = getattr(module, "__file__", None)
            if module_file:
                try:
                    if Path(module_file).resolve().is_relative_to(repo_root()):
                        del sys.modules[name]
                except OSError:
                    del sys.modules[name]
        sys.path[:] = [*(str(path) for path in trusted), str(stage_root)]
        sys.dont_write_bytecode = True
        sys.argv[:] = [str(target), *args.target_args]
        if target_ready is not None:
            target_ready.set()
        previous_cwd = Path.cwd()
        os.chdir(stage_root)
        try:
            with manifest_import_gate(stage_root, evidence, trusted):
                runpy.run_path(str(target), run_name="__main__")
        finally:
            os.chdir(previous_cwd)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Seal paths, then dispatch a runlab component without ``-m`` imports."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in _MODES:
        raise SystemExit("usage: bootstrap.py <detached-runner|child-wrap|target> ...")
    if not sys.flags.isolated or not sys.flags.no_site:
        raise SystemExit("bootstrap requires python -I -S")
    seal_import_path()
    mode, mode_args = args[0], args[1:]
    with _lock_runner_sources(repo_root()):
        with _runner_source_imports(repo_root()):
            for fullname in (
                "alpha_lab",
                "alpha_lab.runlab",
                "alpha_lab.discipline",
                "alpha_lab.discipline.evidence",
                "alpha_lab.discipline.prereg",
                "alpha_lab.runlab.contract",
                "alpha_lab.runlab.watchdog",
                "alpha_lab.runlab.sealed_execution",
                "alpha_lab.runlab.child_wrap",
                "alpha_lab.runlab.detached_runner",
            ):
                importlib.import_module(fullname)
            sealed_execution = sys.modules["alpha_lab.runlab.sealed_execution"]
            if mode != "target":
                module_name = ("alpha_lab.runlab.detached_runner"
                               if mode == "detached-runner"
                               else "alpha_lab.runlab.child_wrap")
                module = sys.modules[module_name]
        if mode == "target":
            return _run_target(mode_args, sealed_execution)
        return int(module.main(mode_args))


if __name__ == "__main__":
    raise SystemExit(main())
