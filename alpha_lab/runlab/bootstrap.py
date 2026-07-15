"""Isolated runlab entry point.

Invoke only by its absolute tracked path:
    python -I -S <absolute bootstrap.py> <detached-runner|child-wrap|target> ...

Before importing project code this module preserves the interpreter's ``-I -S`` startup
roots, adds trusted site-package roots, and appends this checkout's exact repository root.
"""
from __future__ import annotations

import sys
_INITIAL_INTERPRETER_PATH = tuple(sys.path)

import importlib
from importlib.machinery import PathFinder
import runpy
import sysconfig
from pathlib import Path
from typing import Sequence


_MODES = {"detached-runner", "child-wrap", "target"}


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


def _run_target(argv: Sequence[str]) -> int:
    if not argv:
        raise SystemExit("target mode requires an absolute target script path")
    target = Path(argv[0])
    if not target.is_absolute() or not target.is_file():
        raise SystemExit("target mode requires an existing absolute target script path")
    sys.argv[:] = [str(target), *argv[1:]]
    runpy.run_path(str(target), run_name="__main__")
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
    if mode == "target":
        return _run_target(mode_args)
    module_name = ("alpha_lab.runlab.detached_runner"
                   if mode == "detached-runner"
                   else "alpha_lab.runlab.child_wrap")
    module = importlib.import_module(module_name)
    return int(module.main(mode_args))


if __name__ == "__main__":
    raise SystemExit(main())
