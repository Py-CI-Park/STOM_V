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
    }


def sha256_file(path: Path) -> str:
    """파일 sha256 — 대용량(parquet 수 MB)도 청크 단위로 안전하게."""
    with open(path, "rb") as handle:
        return _sha256_handle(handle.fileno())


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


def _read_verified_bytes(path: Path, label: str) -> tuple[bytes, str]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        _retained_regular_file(path, descriptor, label)
        chunks: list[bytes] = []
        h = hashlib.sha256()
        while chunk := os.read(descriptor, 1 << 20):
            chunks.append(chunk)
            h.update(chunk)
        _retained_regular_file(path, descriptor, label)
        return b"".join(chunks), h.hexdigest()
    finally:
        os.close(descriptor)


def snapshot_sources(
    run_dir: Path, destination: Path, expected: Dict[str, str],
) -> Path:
    """Copy manifest sources from retained handles after checking their sealed bytes."""
    snapshot_dir = Path(tempfile.mkdtemp(prefix=".catalog-sources.", dir=destination))
    try:
        for rel, expected_sha256 in expected.items():
            source = Path(run_dir) / rel
            payload, digest = _read_verified_bytes(source, f"catalog source '{rel}'")
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
    """원천 파일 1건을 영수증 sources에 기록(동일 경로 중복 기록 방지)."""
    rel = rel_to(run_dir, path)
    for entry in receipt["sources"]:
        if entry.get("path") == rel:
            return
    entry: Dict[str, Any] = {"path": rel, "status": status}
    if note:
        entry["note"] = note
    if sha256 is not None:
        entry["sha256"] = sha256
        entry["size_bytes"] = size_bytes
    elif path.is_file():
        entry["sha256"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size
    receipt["sources"].append(entry)


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
