"""SQLite source-data access that cannot create or mutate database side files."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from typing import Any
from urllib.parse import quote

_SAMPLE_BYTES = 1024 * 1024


def connect_existing_db_readonly(path: str | Path, *, immutable: bool = True) -> sqlite3.Connection:
    db_path = Path(path).expanduser().resolve(strict=True)
    if not db_path.is_file():
        raise FileNotFoundError(db_path)
    uri_path = quote(db_path.as_posix(), safe="/:")
    query = "mode=ro"
    if immutable:
        query += "&immutable=1"
    connection = sqlite3.connect(f"file:{uri_path}?{query}", uri=True)
    connection.execute("PRAGMA query_only = ON")
    return connection


def sqlite_sidefile_snapshot(path: str | Path) -> dict[str, dict[str, Any]]:
    db_path = Path(path).expanduser().resolve()
    result: dict[str, dict[str, Any]] = {}
    for suffix in ("-wal", "-shm", "-journal"):
        side = Path(str(db_path) + suffix)
        stat = side.stat() if side.exists() else None
        result[suffix] = {
            "exists": stat is not None,
            "size": stat.st_size if stat else None,
            "mtime_ns": stat.st_mtime_ns if stat else None,
        }
    return result


def assert_sqlite_sidefiles_unchanged(path: str | Path, before: dict[str, dict[str, Any]]) -> None:
    after = sqlite_sidefile_snapshot(path)
    if after != before:
        raise RuntimeError(f"SQLite side files changed for {Path(path)}: before={before!r}, after={after!r}")


def sqlite_fingerprint(path: str | Path, *, full_hash_limit: int = 64 * 1024 * 1024) -> dict[str, Any]:
    db_path = Path(path).expanduser().resolve(strict=True)
    stat = db_path.stat()
    digest = hashlib.sha256()
    mode = "full" if stat.st_size <= full_hash_limit else "sampled_v1"
    with db_path.open("rb") as stream:
        if mode == "full":
            while chunk := stream.read(_SAMPLE_BYTES):
                digest.update(chunk)
        else:
            offsets = (0, max(0, stat.st_size // 2 - _SAMPLE_BYTES // 2), max(0, stat.st_size - _SAMPLE_BYTES))
            digest.update(str(stat.st_size).encode("ascii"))
            for offset in offsets:
                stream.seek(offset)
                digest.update(offset.to_bytes(8, "big"))
                digest.update(stream.read(_SAMPLE_BYTES))
    return {
        "path": str(db_path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": digest.hexdigest(),
        "hash_mode": mode,
    }
