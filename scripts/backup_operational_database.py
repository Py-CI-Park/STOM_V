from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BRANCH = "STOM_Version_2U_C"
ACK_ENV = "V3K_CUTOVER_USER_ACK"
BACKUP_MANIFEST = "v3k_backup_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return (path if path.is_absolute() else ROOT / path).resolve()


def current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def require_apply_guards() -> None:
    branch = current_branch()
    if branch != EXPECTED_BRANCH:
        raise SystemExit(f"refusing backup apply on branch {branch!r}; expected {EXPECTED_BRANCH!r}")
    if os.environ.get(ACK_ENV) != "1":
        raise SystemExit(f"{ACK_ENV}=1 is required for backup --apply")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sqlite_summary(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        return None
    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as con:
            tables = [
                row[0]
                for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
        return {"readable": True, "tables": tables}
    except sqlite3.DatabaseError as exc:
        return {"readable": False, "error": str(exc)}


def iter_source_files(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(path for path in source_dir.rglob("*") if path.is_file())


def build_manifest(source_dir: Path, target_dir: Path, *, mode: str) -> dict[str, Any]:
    files = []
    for path in iter_source_files(source_dir):
        rel_path = path.relative_to(source_dir).as_posix()
        if rel_path == BACKUP_MANIFEST:
            continue
        files.append(
            {
                "rel_path": rel_path,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "sqlite": sqlite_summary(path),
            }
        )

    return {
        "generated_at": utc_now(),
        "mode": mode,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "source_exists": source_dir.exists(),
        "file_count": len(files),
        "files": files,
        "policy": {
            "branch_required": EXPECTED_BRANCH,
            "ack_env_required_for_apply": ACK_ENV,
            "operating_database_write_default": False,
            "db_file_commit_allowed": False,
        },
    }


def copy_backup(source_dir: Path, target_dir: Path) -> dict[str, Any]:
    if not source_dir.is_dir():
        raise SystemExit(f"source directory does not exist: {source_dir}")
    if target_dir.exists() and any(target_dir.iterdir()):
        raise SystemExit(f"backup target must be absent or empty: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in iter_source_files(source_dir):
        rel_path = source.relative_to(source_dir)
        if rel_path.as_posix() == BACKUP_MANIFEST:
            continue
        target = target_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    manifest = build_manifest(target_dir, target_dir, mode="apply")
    manifest["original_source_dir"] = str(source_dir)
    manifest["backup_manifest"] = str(target_dir / BACKUP_MANIFEST)
    (target_dir / BACKUP_MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3K operational database backup helper. Defaults to dry-run and never writes without guards."
    )
    parser.add_argument("--source-dir", type=Path, default=Path("_database"))
    parser.add_argument("--target-dir", type=Path)
    parser.add_argument("--apply", action="store_true", help="copy source files to target after branch + ACK guards")
    parser.add_argument("--stdout", action="store_true", help="print JSON manifest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = resolve_path(args.source_dir)
    target_dir = resolve_path(args.target_dir or Path(f"_database.backup.{utc_slug()}"))

    if args.apply:
        require_apply_guards()
        manifest = copy_backup(source_dir, target_dir)
    else:
        manifest = build_manifest(source_dir, target_dir, mode="dry-run")

    if args.stdout or not args.apply:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"wrote V3K backup manifest: {target_dir / BACKUP_MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
