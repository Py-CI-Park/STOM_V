from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
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


def require_apply_guards(target_dir: Path, *, allow_operating_target: bool) -> None:
    branch = current_branch()
    if branch != EXPECTED_BRANCH:
        raise SystemExit(f"refusing rollback apply on branch {branch!r}; expected {EXPECTED_BRANCH!r}")
    if os.environ.get(ACK_ENV) != "1":
        raise SystemExit(f"{ACK_ENV}=1 is required for rollback --apply")
    operating_target = (ROOT / "_database").resolve()
    if target_dir == operating_target and not allow_operating_target:
        raise SystemExit("--allow-operating-target is required to write the real _database directory")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_verify_backup(backup_dir: Path, *, verify_checksum: bool) -> dict[str, Any]:
    manifest_path = backup_dir / BACKUP_MANIFEST
    if not manifest_path.is_file():
        raise SystemExit(f"backup manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if verify_checksum:
        mismatches = []
        for item in manifest.get("files", []):
            path = backup_dir / item["rel_path"]
            if not path.is_file():
                mismatches.append({"rel_path": item["rel_path"], "error": "missing"})
                continue
            if sha256_file(path) != item["sha256"]:
                mismatches.append({"rel_path": item["rel_path"], "error": "sha256-mismatch"})
        if mismatches:
            raise SystemExit(f"backup verification failed: {mismatches}")
    return manifest


def apply_rollback(backup_dir: Path, target_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    restored = []
    for item in manifest.get("files", []):
        rel_path = Path(item["rel_path"])
        source = backup_dir / rel_path
        target = target_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        restored.append({"rel_path": rel_path.as_posix(), "sha256": sha256_file(target)})
    return {
        "generated_at": utc_now(),
        "mode": "apply",
        "backup_dir": str(backup_dir),
        "target_dir": str(target_dir),
        "restored": restored,
        "file_count": len(restored),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="V3K cutover rollback helper. Apply is guarded; dry-run is default."
    )
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, default=Path("_database"))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--no-verify-checksum", action="store_true")
    parser.add_argument("--allow-operating-target", action="store_true")
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    backup_dir = resolve_path(args.backup_dir)
    target_dir = resolve_path(args.target_dir)
    manifest = load_and_verify_backup(backup_dir, verify_checksum=not args.no_verify_checksum)
    if args.apply:
        require_apply_guards(target_dir, allow_operating_target=args.allow_operating_target)
        report = apply_rollback(backup_dir, target_dir, manifest)
    else:
        report = {
            "generated_at": utc_now(),
            "mode": "dry-run",
            "backup_dir": str(backup_dir),
            "target_dir": str(target_dir),
            "file_count": len(manifest.get("files", [])),
            "policy": {
                "branch_required": EXPECTED_BRANCH,
                "ack_env_required_for_apply": ACK_ENV,
                "operating_target_requires_extra_flag": True,
            },
        }

    if args.stdout or not args.apply:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
