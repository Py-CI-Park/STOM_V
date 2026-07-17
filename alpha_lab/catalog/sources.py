"""원천 파일 접근·빌드 영수증 헬퍼 — 전 원천 read-only, sha256 지문 기록.

원칙: 원본 파일은 절대 변형하지 않는다. 누락/파싱 실패는 예외로 죽이지 않고
영수증(receipt dict)에 기록한 뒤 빌드를 계속한다(계획 §3 — 원본이 정본,
DB는 카탈로그 계층일 뿐이므로 부분 적재가 전체 실패보다 낫다).
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager
from typing import Iterator
from dataclasses import dataclass


def new_receipt(run_dir: Path, db_path: Path) -> Dict[str, Any]:
    """빌드 영수증 뼈대 — 테이블별 건수·원천 sha256·누락/스킵·생성시각."""
    return {
        "kind": "research_assets_build_receipt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "db_path": str(db_path),
        "table_counts": {},
        "sources": [],
        "missing": [],
        "skipped": [],
        "notes": [],
        "gitignore": None,
        "inventory": [],
    }


def sha256_file(path: Path) -> str:
    """Hash through an active retained descriptor when this is a snapshot source."""
    _, digest = _read_verified_bytes(path, f"catalog source '{path}'")
    return digest


def _sha256_handle(descriptor: int) -> str:
    h = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while chunk := os.read(descriptor, 1 << 20):
        h.update(chunk)
    return h.hexdigest()


def _retained_regular_file(path: Path, descriptor: int, label: str) -> os.stat_result:
    opened = os.fstat(descriptor)
    named = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or not stat.S_ISREG(named.st_mode)
        or named.st_nlink != 1
        or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise OSError(f"{label} identity changed or is not a single-link regular file")
    return opened
@dataclass(frozen=True)
class VerifiedFileObservation:
    """The frozen identity and metadata of one retained snapshot file."""
    sha256: str
    size_bytes: int
    mtime_utc: str

class RetainedSourceSnapshots:
    """Keep every snapshot source bound to its opened single-link file identity."""

    def __init__(self, snapshot_dir: Path):
        self.snapshot_dir = Path(snapshot_dir)
        self.descriptors: dict[Path, int] = {}
        self._write_deny_guard: Any | None = None
    def __enter__(self) -> "RetainedSourceSnapshots":
        from alpha_lab.discipline.prereg import _WindowsAuthorityGuard

        self._write_deny_guard = _WindowsAuthorityGuard(
            self.snapshot_dir.parent.resolve(), {}, ())
        try:
            for path in sorted(self.snapshot_dir.rglob("*")):
                if not path.is_file():
                    continue
                self._write_deny_guard.hold_write_denied_file(path)
                descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                try:
                    _retained_regular_file(path, descriptor, f"catalog snapshot '{path}'")
                except BaseException:
                    os.close(descriptor)
                    self.close()
                    raise
                self.descriptors[path.resolve()] = descriptor
        except BaseException:
            self.close()
            raise
        return self

    def descriptor_for(self, path: Path) -> int | None:
        return self.descriptors.get(Path(path).resolve())

    def observation_for_relative(self, rel: str) -> VerifiedFileObservation | None:
        """Return metadata from the retained snapshot, never from its live source."""
        path = (self.snapshot_dir / rel).resolve()
        descriptor = self.descriptor_for(path)
        if descriptor is None:
            return None
        opened = _retained_regular_file(path, descriptor, f"catalog snapshot '{path}'")
        return VerifiedFileObservation(
            sha256=_sha256_handle(descriptor),
            size_bytes=opened.st_size,
            mtime_utc=datetime.fromtimestamp(
                opened.st_mtime, tz=timezone.utc).isoformat(),
        )

    def contains_relative_path(self, rel: str) -> bool:
        """Whether a retained snapshot contains this path or descendants of it."""
        prefix = (self.snapshot_dir / rel).resolve()
        return any(path == prefix or prefix in path.parents for path in self.descriptors)

    def validate(self) -> None:
        for path, descriptor in self.descriptors.items():
            _retained_regular_file(path, descriptor, f"catalog snapshot '{path}'")

    def close(self) -> None:
        for descriptor in self.descriptors.values():
            os.close(descriptor)
        self.descriptors.clear()
        if self._write_deny_guard is not None:
            self._write_deny_guard.close()
            self._write_deny_guard = None

    def __exit__(self, *args: object) -> None:
        self.close()


_ACTIVE_RETAINED_SNAPSHOTS: RetainedSourceSnapshots | None = None


@contextmanager
def retain_snapshot_sources(snapshot_dir: Path) -> Iterator[RetainedSourceSnapshots]:
    """Expose retained snapshot descriptors to all catalog readers for one build."""
    global _ACTIVE_RETAINED_SNAPSHOTS
    if _ACTIVE_RETAINED_SNAPSHOTS is not None:
        raise RuntimeError("catalog source retention is already active")
    retained = RetainedSourceSnapshots(snapshot_dir)
    _ACTIVE_RETAINED_SNAPSHOTS = retained.__enter__()
    try:
        yield retained
    finally:
        _ACTIVE_RETAINED_SNAPSHOTS = None
        retained.close()


def validate_retained_snapshot_sources() -> None:
    """Fail closed if any source parsed through the active snapshot was replaced."""
    if _ACTIVE_RETAINED_SNAPSHOTS is not None:
        _ACTIVE_RETAINED_SNAPSHOTS.validate()


def _active_descriptor(path: Path) -> int | None:
    if _ACTIVE_RETAINED_SNAPSHOTS is None:
        return None
    return _ACTIVE_RETAINED_SNAPSHOTS.descriptor_for(path)



def _read_verified_bytes_with_stat(
    path: Path, label: str,
) -> tuple[bytes, str, os.stat_result]:
    """Read bytes and return the stat metadata from the same verified identity."""
    descriptor = _active_descriptor(path)
    close_descriptor = descriptor is None
    if descriptor is None:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        _retained_regular_file(path, descriptor, label)
        os.lseek(descriptor, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        h = hashlib.sha256()
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
            h.update(chunk)
        opened = _retained_regular_file(path, descriptor, label)
        return b"".join(chunks), h.hexdigest(), opened
    finally:
        if close_descriptor:
            os.close(descriptor)


def _read_verified_bytes(path: Path, label: str) -> tuple[bytes, str]:
    payload, digest, _ = _read_verified_bytes_with_stat(path, label)
    return payload, digest


def snapshot_sources(
    run_dir: Path, destination: Path, expected: Dict[str, str],
) -> Path:
    """Copy manifest sources from retained handles after checking their sealed bytes."""
    snapshot_dir = Path(tempfile.mkdtemp(prefix=".catalog-sources.", dir=destination))
    try:
        for rel, expected_sha256 in expected.items():
            source = Path(run_dir) / rel
            payload, digest, source_stat = _read_verified_bytes_with_stat(
                source, f"catalog source '{rel}'")
            if digest != expected_sha256:
                raise ValueError(f"catalog source '{rel}' does not match manifest sha256")
            target = snapshot_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
            try:
                view = memoryview(payload)
                while view:
                    written = os.write(descriptor, view)
                    if written == 0:
                        raise OSError("catalog source snapshot write made no progress")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.utime(target, ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns))
            metadata_descriptor = os.open(
                target, os.O_RDWR | getattr(os, "O_BINARY", 0))
            try:
                os.fsync(metadata_descriptor)
            finally:
                os.close(metadata_descriptor)
        return snapshot_dir
    except BaseException:
        for path in sorted(snapshot_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        snapshot_dir.rmdir()
        raise


def rel_to(run_dir: Path, path: Path) -> str:
    """run 디렉토리 기준 상대 경로(불가하면 절대 경로 문자열)."""
    try:
        return path.resolve().relative_to(Path(run_dir).resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def record_source(
    receipt: Dict[str, Any], run_dir: Path, path: Path,
    status: str = "loaded", note: str = "", *, sha256: Optional[str] = None,
    size_bytes: Optional[int] = None,
) -> None:
    """Record one source and reject a duplicate path with different verified bytes."""
    rel = rel_to(run_dir, path)
    if sha256 is None and path.is_file():
        payload, sha256 = _read_verified_bytes(path, f"catalog source '{rel}'")
        size_bytes = len(payload)
    for entry in receipt["sources"]:
        if entry.get("path") != rel:
            continue
        if entry.get("sha256") != sha256 or entry.get("size_bytes") != size_bytes:
            raise ValueError(f"catalog source '{rel}' was recorded with different bytes")
        return
    entry: Dict[str, Any] = {"path": rel, "status": status}
    if note:
        entry["note"] = note
    if sha256 is not None:
        entry["sha256"] = sha256
        entry["size_bytes"] = size_bytes
    receipt["sources"].append(entry)
def record_inventory(
    receipt: Dict[str, Any], run_dir: Path, path: Path, *,
    asset_id: str, exists_on_disk: bool, sha256: Optional[str] = None,
    size_bytes: Optional[int] = None, mtime_utc: Optional[str] = None,
) -> None:
    """Record registry/output inventory without enlarging the sealed source set."""
    entry: Dict[str, Any] = {
        "asset_id": asset_id,
        "path": rel_to(run_dir, path),
        "exists_on_disk": exists_on_disk,
    }
    if sha256 is not None:
        entry["sha256"] = sha256
    if size_bytes is not None:
        entry["size_bytes"] = size_bytes
    if mtime_utc is not None:
        entry["mtime_utc"] = mtime_utc
    receipt.setdefault("inventory", []).append(entry)


def read_json(receipt: Dict[str, Any], run_dir: Path, rel: str) -> Optional[dict]:
    """Retain, hash, and parse one JSON source from the exact same bytes."""
    path = Path(run_dir) / rel
    try:
        payload, digest = _read_verified_bytes(path, f"catalog json source '{rel}'")
    except FileNotFoundError:
        receipt["missing"].append(rel)
        receipt["sources"].append({"path": rel, "status": "missing"})
        return None
    except OSError as exc:
        receipt["skipped"].append({"path": rel, "reason": f"json 원천 확인 실패: {exc}"})
        return None
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        receipt["skipped"].append({"path": rel, "reason": f"json 파싱 실패: {exc}"})
        return None
    record_source(receipt, run_dir, path, sha256=digest, size_bytes=len(payload))
    return data if isinstance(data, dict) else {"_root": data}


def add_note(receipt: Dict[str, Any], msg: str) -> None:
    """영수증 notes에 방어적 파싱 관찰 사항을 남긴다."""
    receipt["notes"].append(msg)
