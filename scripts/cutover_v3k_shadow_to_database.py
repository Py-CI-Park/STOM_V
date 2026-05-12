from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BRANCH = "STOM_Version_2U_C"
ACK_ENV = "V3K_CUTOVER_USER_ACK"
BACKUP_MANIFEST = "v3k_backup_manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def require_apply_guards(args: argparse.Namespace, target_dir: Path) -> None:
    branch = current_branch()
    if branch != EXPECTED_BRANCH:
        raise SystemExit(f"refusing cutover apply on branch {branch!r}; expected {EXPECTED_BRANCH!r}")
    if os.environ.get(ACK_ENV) != "1":
        raise SystemExit(f"{ACK_ENV}=1 is required for cutover --apply")
    if not args.backup_first:
        raise SystemExit("--backup-first is required for cutover --apply")
    if args.backup_dir is None:
        raise SystemExit("--backup-dir is required for cutover --apply")
    operating_target = (ROOT / "_database").resolve()
    if target_dir == operating_target and not args.allow_operating_target:
        raise SystemExit("--allow-operating-target is required to write the real _database directory")


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(child for child in path.rglob("*") if child.is_file())


def verify_backup(backup_dir: Path) -> dict[str, Any]:
    manifest_path = backup_dir / BACKUP_MANIFEST
    if not manifest_path.is_file():
        raise SystemExit(f"backup manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mismatches = []
    for item in manifest.get("files", []):
        rel_path = item["rel_path"]
        path = backup_dir / rel_path
        if not path.is_file():
            mismatches.append({"rel_path": rel_path, "error": "missing"})
            continue
        digest = sha256_file(path)
        if digest != item["sha256"]:
            mismatches.append({"rel_path": rel_path, "error": "sha256-mismatch"})
    if mismatches:
        raise SystemExit(f"backup verification failed: {mismatches}")
    return {"manifest": str(manifest_path), "file_count": len(manifest.get("files", []))}


def sqlite_sanity(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        return None
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        tables = [
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ]
    return {"readable": True, "tables": tables}


def build_dry_run(shadow_dir: Path, target_dir: Path, backup_dir: Path | None) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "mode": "dry-run",
        "shadow_dir": str(shadow_dir),
        "target_dir": str(target_dir),
        "backup_dir": str(backup_dir) if backup_dir else None,
        "shadow_exists": shadow_dir.exists(),
        "shadow_file_count": len(iter_files(shadow_dir)),
        "policy": {
            "branch_required": EXPECTED_BRANCH,
            "ack_env_required_for_apply": ACK_ENV,
            "backup_first_required": True,
            "operating_target_requires_extra_flag": True,
        },
    }


def apply_cutover(shadow_dir: Path, target_dir: Path, backup_dir: Path) -> dict[str, Any]:
    if not shadow_dir.is_dir():
        raise SystemExit(f"shadow directory does not exist: {shadow_dir}")
    backup_status = verify_backup(backup_dir)

    copied = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in iter_files(shadow_dir):
        rel_path = source.relative_to(shadow_dir)
        target = target_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"rel_path": rel_path.as_posix(), "sqlite": sqlite_sanity(target)})

    return {
        "generated_at": utc_now(),
        "mode": "apply",
        "shadow_dir": str(shadow_dir),
        "target_dir": str(target_dir),
        "backup": backup_status,
        "copied": copied,
        "file_count": len(copied),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3K shadow-to-database cutover helper. Apply is guarded; dry-run is default."
    )
    parser.add_argument("--shadow-dir", type=Path, default=Path("_database_v3k_shadow"))
    parser.add_argument("--target-dir", type=Path, default=Path("_database"))
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--backup-first", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-operating-target", action="store_true")
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    shadow_dir = resolve_path(args.shadow_dir)
    target_dir = resolve_path(args.target_dir)
    backup_dir = resolve_path(args.backup_dir) if args.backup_dir else None

    if args.apply:
        require_apply_guards(args, target_dir)
        assert backup_dir is not None
        report = apply_cutover(shadow_dir, target_dir, backup_dir)
    else:
        report = build_dry_run(shadow_dir, target_dir, backup_dir)

    if args.stdout or not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
