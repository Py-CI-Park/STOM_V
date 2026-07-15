"""alpha_lab 조건식 → 전략 DB 등록기 (INSERT-only, 연구 레인 전용).

scripts/register_chart_sulsa_conditions.py 의 실측 계약을 미러한다:
- 테이블: stockbuy(매수) / stocksell(매도), 컬럼 "index"(이름 TEXT), "전략코드"(TEXT).
  (utility/database_check.py 실측 DDL: CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT ))
- INSERT-only: 기존 행은 어떤 방식으로도 변형하지 않는다(UPDATE/DELETE 금지).
- 실쓰기 전 DB 파일 백업 복사를 강제한다(쓸 것이 없으면 백업도 만들지 않는다).
- 동명이 어느 한 테이블에라도 존재하면 그 항목 쌍 전체를 스킵하고 conflicts에
  기록한다(부분 삽입 금지). 따라서 재실행은 멱등(inserted 0)이다.

규율: 이름은 'ALP_' 접두 강제(연구 산출물 네임스페이스 격리). 현재시각은
호출자가 now 인자로 주입한다(내부 datetime.now() 금지). print 금지(logging).
"""

from __future__ import annotations

import ctypes
import errno
import datetime as dt
import hashlib
import json
import os
import stat
import shutil
import sqlite3
from pathlib import Path, PurePosixPath
from typing import Any

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    build_promotion_logical_delta,
    capture_sqlite_logical_state,
    validate_catalog_promotion_receipt_v2,
    validate_promotion_journal_post_v2,
    validate_promotion_journal_pre_v2,
    verify_promotion_manifest_v2,
    verify_promotion_result_v2,
)
from alpha_lab.discipline.prereg import authority_mutation_guard, recheck_authority_paths


NAME_PREFIX = "ALP_"
TABLE_BY_SIDE: dict[str, str] = {"buy": "stockbuy", "sell": "stocksell"}
NAME_COLUMN = "index"
CODE_COLUMN = "전략코드"
_EXPR_KEY_BY_TABLE: dict[str, str] = {"stockbuy": "buy_expr", "stocksell": "sell_expr"}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _promotion_result(
    *,
    passed: bool,
    evidence_id: str | None = None,
    candidates: list[dict[str, str]] | None = None,
    checks: dict[str, bool] | None = None,
    reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Return the fixed, non-throwing read-only promotion verdict shape."""
    return {
        "pass": passed,
        "schema_version": 2,
        "status": "PRE" if passed else "FAIL",
        "evidence_id": evidence_id,
        "candidates": candidates or [],
        "checks": checks or {},
        "reasons": reasons or [],
    }
def _verify_promotion_result_locked(
    result_path: Path, *, repo_root: Path, connection: sqlite3.Connection,
    locked_post_state: dict[str, Any], locked_post_sha256: str,
    allowed_reserved_sidecars: tuple[Path, Path, Path],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Strongly verify POST while its writer still owns SQLite EXCLUSIVE."""
    result, manifest, result_sha256 = verify_promotion_result_v2(
        result_path, repo_root=repo_root, target_connection=connection,
        locked_post_state=locked_post_state,
        allowed_reserved_sidecars=allowed_reserved_sidecars,
    )
    target = repo_root / Path(*PurePosixPath(result["target_db"]["path"]).parts)
    if (
        result["target_db"]["post_sha256"] != locked_post_sha256
        or hashlib.sha256(target.read_bytes()).hexdigest() != locked_post_sha256
        or capture_sqlite_logical_state(
            target, connection=connection,
            allowed_reserved_sidecars=allowed_reserved_sidecars,
        ) != locked_post_state
    ):
        raise EvidenceSchemaError("locked POST verification does not match retained SQLite state")
    return result, manifest, result_sha256




def _load_json(path: Path, field: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError(f"{field} cannot be read as JSON: {exc}") from exc


def _repo_relative_path(path: Path, repo_root: Path, field: str) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} resolves outside repo_root") from exc


class LegacyPromotionBlockedError(RuntimeError):
    """Raised when the retired unauthorised registrar entry point is used."""

def _validate_catalog_pre_receipt(
    value: object, *, evidence_id: str, manifest_path: Path, manifest_sha256: str, repo_root: Path,
) -> dict[str, Any]:
    """Require the builder's strict PRE receipt, bound to live DB and source bytes."""
    if not isinstance(value, dict) or "promotion_receipt" not in value:
        raise EvidenceSchemaError(
            "catalog receipt must be the immutable outer builder receipt with promotion_receipt"
        )
    receipt = value["promotion_receipt"]
    validated = validate_catalog_promotion_receipt_v2(receipt, repo_root=repo_root)
    if validated["phase"] != "PRE":
        raise EvidenceSchemaError("catalog receipt must be PRE authority")
    if validated["evidence_id"] != evidence_id:
        raise EvidenceSchemaError("catalog PRE receipt evidence_id does not match promotion manifest")
    expected_path = _repo_relative_path(manifest_path, repo_root, "manifest_path")
    expected_ref = {"path": expected_path, "sha256": manifest_sha256}
    if validated["promotion_manifest"] != expected_ref:
        raise EvidenceSchemaError("catalog PRE receipt does not bind exact promotion manifest bytes")
    if validated["upstream"] != {"kind": "promotion_manifest", **expected_ref}:
        raise EvidenceSchemaError("catalog PRE receipt upstream does not bind exact promotion manifest bytes")
    return validated


def _promotion_destinations(root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    """Resolve immutable destinations from the sealed authority paths only."""
    authority = manifest["authority_paths"]
    evidence_id = manifest["evidence_id"]
    return {
        "target_db": root / Path(*PurePosixPath(authority["target_db"]).parts),
        "catalog": root / Path(*PurePosixPath(authority["catalog_dir"]).parts)
        / f"{evidence_id}.pre.receipt.json",
        "pre": root / Path(*PurePosixPath(authority["journal_dir"]).parts)
        / f"{evidence_id}.pre.json",
        "anchor": root / Path(*PurePosixPath(authority["journal_dir"]).parts)
        / f"{evidence_id}.pre.sha256",
        "post": root / Path(*PurePosixPath(authority["journal_dir"]).parts)
        / f"{evidence_id}.post.json",
        "backup": root / Path(*PurePosixPath(authority["backup_dir"]).parts)
        / f"{evidence_id}.pre.sqlite",
    }


def verify_promotion_manifest(
    manifest_path: Path | str, *, repo_root: Path | str,
) -> dict[str, Any]:
    """Validate the canonical PRE chain using only sealed destinations."""
    checks: dict[str, bool] = {}
    try:
        root = Path(repo_root).resolve()
        manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
        checks.update({"manifest": True, "ledger": True, "evidence_chain": True})
        destinations = _promotion_destinations(root, manifest)
        _validate_catalog_pre_receipt(
            _load_json(destinations["catalog"], "catalog receipt"),
            evidence_id=manifest["evidence_id"], manifest_path=Path(manifest_path),
            manifest_sha256=manifest_sha256, repo_root=root,
        )
        checks["catalog_pre"] = True
        return _promotion_result(
            passed=True, evidence_id=manifest["evidence_id"],
            candidates=manifest["candidate_set"], checks=checks)
    except (EvidenceSchemaError, OSError, ValueError) as exc:
        return _promotion_result(passed=False, checks=checks, reasons=[str(exc)])


def _journal_paths(
    root: Path, manifest: dict[str, Any],
) -> tuple[Path, Path, Path, str, str, str]:
    destinations = _promotion_destinations(root, manifest)
    return (
        destinations["pre"], destinations["anchor"], destinations["post"],
        _repo_relative_path(destinations["pre"], root, "journal PRE"),
        _repo_relative_path(destinations["anchor"], root, "journal anchor"),
        _repo_relative_path(destinations["post"], root, "journal POST"),
    )


def _write_exclusive_bytes(path: Path, payload: bytes) -> None:
    """Write one immutable, durable journal entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"promotion journal already exists: {path}") from exc
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    _write_exclusive_bytes(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
    )


def _verify_pre_anchor(pre_path: Path, anchor_path: Path) -> str:
    if not anchor_path.is_file():
        raise EvidenceSchemaError("promotion journal PRE intent anchor is missing")
    pre_sha256 = hashlib.sha256(pre_path.read_bytes()).hexdigest()
    if anchor_path.read_bytes() != pre_sha256.encode("ascii"):
        raise EvidenceSchemaError("promotion journal PRE intent anchor does not bind exact PRE bytes")
    return pre_sha256


def _journal_chronology(manifest: dict[str, Any], repo_root: Path, pre_at: str) -> dict[str, str]:
    receipt = _load_json(repo_root / manifest["gate_receipt"]["path"], "gate receipt")
    usage = _load_json(repo_root / manifest["gate_claim"]["path"], "gate usage")
    seal = _load_json(repo_root / receipt["seal_manifest"]["path"], "seal manifest")
    ledger_rows = [
        json.loads(line) for line in (
            repo_root / manifest["ledger"]["path"]
        ).read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    rows = [row for row in ledger_rows if row.get("evidence_id") == manifest["evidence_id"]]
    if len(rows) != 1:
        raise EvidenceSchemaError("promotion journal cannot locate exact ledger authority row")
    return {
        "sealed_at": seal["sealed_at"], "issued_at": receipt["issued_at"],
        "consumed_at": usage["consumed_at"], "ledger_at": rows[0]["ts"], "pre_at": pre_at,
    }


def _validate_live_journal_pre(pre: dict[str, Any], *, root: Path) -> tuple[dict[str, Any], str]:
    manifest_path = root / Path(*PurePosixPath(pre["promotion_manifest"]["path"]).parts)
    manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    if (
        manifest["evidence_id"] != pre["evidence_id"]
        or manifest["candidate_set"] != pre["candidate_set"]
        or manifest["candidate_set_sha256"] != pre["candidate_set_sha256"]
        or pre["promotion_manifest"]["sha256"] != manifest_sha256
    ):
        raise EvidenceSchemaError("promotion journal PRE does not match live manifest authority")
    destinations = _promotion_destinations(root, manifest)
    if (
        pre["target_db"]["path"] != _repo_relative_path(destinations["target_db"], root, "target DB")
        or pre["backup_ref"]["path"] != _repo_relative_path(destinations["backup"], root, "backup")
    ):
        raise EvidenceSchemaError("promotion journal PRE destinations do not match sealed authority")
    catalog_path = destinations["catalog"]
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != pre["catalog_receipt"]["sha256"]:
        raise EvidenceSchemaError("promotion journal PRE catalog receipt SHA-256 does not match bytes")
    _validate_catalog_pre_receipt(
        _load_json(catalog_path, "catalog receipt"), evidence_id=pre["evidence_id"],
        manifest_path=manifest_path, manifest_sha256=manifest_sha256, repo_root=root,
    )
    return manifest, manifest_sha256


def inspect_promotion_journal_v2(
    *,
    repo_root: Path | str,
    manifest_path: Path | str,
) -> dict[str, Any]:
    """Authenticate journal and reserved backup state from sealed authority."""
    root = Path(repo_root).resolve()
    manifest, _ = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    evidence_id = manifest["evidence_id"]
    destinations = _promotion_destinations(root, manifest)
    pre_path, anchor_path, post_path, pre_relative, anchor_relative, post_relative = _journal_paths(root, manifest)
    if not pre_path.exists() and not anchor_path.exists() and not post_path.exists():
        return {"status": "ABSENT", "pre_path": pre_relative, "pre_anchor_path": anchor_relative, "post_path": post_relative}
    if not pre_path.exists():
        raise EvidenceSchemaError("promotion journal PRE intent is missing")
    _verify_pre_anchor(pre_path, anchor_path)
    pre = validate_promotion_journal_pre_v2(_load_json(pre_path, "promotion journal PRE"), repo_root=root)
    if pre["evidence_id"] != evidence_id:
        raise EvidenceSchemaError("promotion journal PRE evidence_id does not match canonical path")
    _validate_live_journal_pre(pre, root=root)
    backup = destinations["backup"]
    backup_state = {
        "path": _repo_relative_path(backup, root, "backup"),
        "exists": backup.is_file(),
        "matches_pre": backup.is_file() and hashlib.sha256(backup.read_bytes()).hexdigest() == pre["target_db"]["pre_sha256"],
    }
    target_db = destinations["target_db"]
    current_db_matches_pre = target_db.is_file() and hashlib.sha256(target_db.read_bytes()).hexdigest() == pre["target_db"]["pre_sha256"]
    if not post_path.exists():
        return {
            "status": "INCOMPLETE_REQUIRES_RECONCILIATION", "pre_path": pre_relative,
            "pre_anchor_path": anchor_relative, "post_path": post_relative, "pre": pre,
            "backup": backup_state, "current_db_matches_pre": current_db_matches_pre,
        }
    post = validate_promotion_journal_post_v2(_load_json(post_path, "promotion journal POST"), pre=pre, repo_root=root)
    result, _, result_sha256 = verify_promotion_result_v2(post_path, repo_root=root)
    if result != post or result_sha256 != hashlib.sha256(post_path.read_bytes()).hexdigest():
        raise EvidenceSchemaError("promotion journal POST verification is inconsistent")
    if not target_db.is_file() or hashlib.sha256(target_db.read_bytes()).hexdigest() != post["target_db"]["post_sha256"]:
        raise EvidenceSchemaError("promotion journal POST target DB SHA-256 does not match bytes")
    return {
        "status": "COMPLETE", "pre_path": pre_relative, "pre_anchor_path": anchor_relative,
        "post_path": post_relative, "pre": pre, "post": post, "backup": backup_state,
        "current_db_matches_pre": current_db_matches_pre,
    }


def _copy_locked_db_exclusive(db_path: Path, backup_path: Path) -> str:
    """Create the reserved backup exactly once while the SQLite writer lock is held."""
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(db_path, "rb") as source:
            descriptor = os.open(str(backup_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as destination:
                shutil.copyfileobj(source, destination)
                destination.flush()
                os.fsync(destination.fileno())
    except FileExistsError as exc:
        raise EvidenceSchemaError("reserved promotion backup already exists") from exc
    return hashlib.sha256(backup_path.read_bytes()).hexdigest()
class _SQLiteAuxiliaryReservations:
    """Windows handles reserving SQLite's auxiliary namespace until close."""

    def __init__(self, paths: tuple[Path, Path, Path], handles: tuple[int, ...]) -> None:
        self.paths = paths
        self._handles = handles
    def validate(self) -> None:
        if len(self._handles) != len(self.paths) or any(
            not path.is_file() or path.stat().st_size != 0 for path in self.paths
        ):
            raise EvidenceSchemaError("SQLite reserved sidecar contract is invalid")


    def close(self) -> None:
        if not self._handles:
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        error = 0
        for handle in reversed(self._handles):
            if not kernel32.CloseHandle(handle):
                error = ctypes.get_last_error()
        self._handles = ()
        if error:
            raise OSError(error, "CloseHandle failed for SQLite auxiliary reservation")

    def __enter__(self) -> _SQLiteAuxiliaryReservations:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def _sqlite_auxiliary_paths(db_path: Path) -> tuple[Path, Path, Path]:
    return Path(f"{db_path}-journal"), Path(f"{db_path}-wal"), Path(f"{db_path}-shm")


def _validate_sqlite_header_delete_mode(db_path: Path) -> None:
    """Reject persistent WAL state without opening SQLite or creating sidecars."""
    with open(db_path, "rb") as source:
        header = source.read(100)
    if (
        len(header) != 100
        or header[:16] != b"SQLite format 3\x00"
        or header[18] != 1
        or header[19] != 1
    ):
        raise EvidenceSchemaError("SQLite journal mode must be DELETE before promotion")


def _reserve_sqlite_auxiliary_paths(db_path: Path) -> _SQLiteAuxiliaryReservations:
    """Atomically reserve all SQLite sidecar names before opening the target DB."""
    _assert_sqlite_auxiliary_paths_absent(db_path)
    if os.name != "nt":
        raise EvidenceSchemaError("SQLite auxiliary reservations require Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handles: list[int] = []
    paths = _sqlite_auxiliary_paths(db_path)
    try:
        for path in paths:
            handle = create_file(
                str(path),
                0x80000000 | 0x00010000,  # GENERIC_READ | DELETE
                0x00000001,  # FILE_SHARE_READ: deny write and delete
                None,
                1,  # CREATE_NEW
                0x00000100 | 0x04000000,  # TEMPORARY | DELETE_ON_CLOSE
                None,
            )
            if handle == ctypes.c_void_p(-1).value:
                error = ctypes.get_last_error()
                if error in (errno.EEXIST, 80, 183):
                    raise EvidenceSchemaError(
                        "SQLite filesystem auxiliary sidecars are not promotable: " + path.name)
                raise OSError(error, "CreateFileW failed for SQLite auxiliary reservation")
            handles.append(handle)
    except BaseException:
        for handle in reversed(handles):
            kernel32.CloseHandle(handle)
        raise
    return _SQLiteAuxiliaryReservations(paths, tuple(handles))


def _assert_sqlite_auxiliary_paths_absent(
    db_path: Path, reservations: _SQLiteAuxiliaryReservations | None = None,
) -> None:
    """Reject unmanaged sidecars; reservations are the sole permitted sidecars."""
    if reservations is not None:
        reservations.validate()
    reserved = set(reservations.paths) if reservations is not None else set()
    present = [
        path.name for path in _sqlite_auxiliary_paths(db_path)
        if path.exists() and path not in reserved
    ]
    if present:
        raise EvidenceSchemaError(
            "SQLite filesystem auxiliary sidecars are not promotable: "
            + ", ".join(present)
        )


def _force_memory_journal_mode(
    con: sqlite3.Connection, db_path: Path, reservations: _SQLiteAuxiliaryReservations,
) -> None:
    """Use SQLite's connection-local in-memory rollback journal before PRE."""
    _assert_sqlite_auxiliary_paths_absent(db_path, reservations)
    row = con.execute("PRAGMA journal_mode").fetchone()
    if not row or str(row[0]).lower() != "delete":
        raise EvidenceSchemaError("SQLite journal mode must be DELETE before promotion")
    row = con.execute("PRAGMA journal_mode=MEMORY").fetchone()
    if not row or str(row[0]).lower() != "memory":
        raise EvidenceSchemaError("SQLite MEMORY journal mode is required for promotion")
    row = con.execute("PRAGMA journal_mode").fetchone()
    if not row or str(row[0]).lower() != "memory":
        raise EvidenceSchemaError("SQLite MEMORY journal mode cannot be verified for promotion")
    _assert_sqlite_auxiliary_paths_absent(db_path, reservations)


def _open_sqlite_promotion_connection(
    db_path: Path, reservations: _SQLiteAuxiliaryReservations,
) -> sqlite3.Connection:
    """Open and switch the sole promotion connection before evidence is created."""
    con = sqlite3.connect(str(db_path))
    try:
        _force_memory_journal_mode(con, db_path, reservations)
        return con
    except BaseException:
        con.close()
        raise




def _acquire_promotion_guard(lock_path: Path) -> int:
    """Atomically reserve the canonical promotion critical section."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise EvidenceSchemaError("promotion is already guarded or requires reconciliation") from exc


def _release_promotion_guard(lock_path: Path, descriptor: int) -> None:
    os.close(descriptor)
    lock_path.unlink()


def _validate_retained_target(db_path: Path, descriptor: int) -> None:
    """Require the retained strategy DB handle and its pathname to remain one inode."""
    opened = os.fstat(descriptor)
    try:
        named = os.stat(db_path, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise EvidenceSchemaError("sealed strategy DB disappeared while retained") from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or not stat.S_ISREG(named.st_mode)
        or named.st_nlink != 1
        or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise EvidenceSchemaError("sealed strategy DB identity changed or is not a single-link regular file")

def register_conditions_v2(
    items: list,
    *,
    manifest_path: Path | str,
    repo_root: Path | str,
    now,
) -> dict[str, Any]:
    """Promote only the sealed candidate set to its sealed target database."""
    root = Path(repo_root).resolve()
    verdict = verify_promotion_manifest(manifest_path, repo_root=root)
    if verdict["pass"] is not True:
        raise ValueError("v2 promotion verification failed: %s" % "; ".join(verdict["reasons"]))
    _validate_items(items)
    expected = {candidate["name"]: candidate for candidate in verdict["candidates"]}
    actual = {item["name"]: item for item in items}
    if set(actual) != set(expected):
        raise ValueError("v2 item names must exactly match promotion manifest candidates")
    for name, item in actual.items():
        candidate = expected[name]
        if (
            _sha256_text(item["buy_expr"]) != candidate["buy_sha256"]
            or _sha256_text(item["sell_expr"]) != candidate["sell_sha256"]
        ):
            raise ValueError("v2 candidate expression hash mismatch: %s" % name)
    completed_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
    try:
        completed = dt.datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("v2 promotion completed_at must be a timezone-aware ISO-8601 timestamp") from exc
    if completed.tzinfo is None or completed.utcoffset() is None:
        raise ValueError("v2 promotion completed_at must be a timezone-aware ISO-8601 timestamp")

    manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    destinations = _promotion_destinations(root, manifest)
    if recheck_authority_paths(manifest["authority_paths"], root) != manifest["authority_paths"]:
        raise EvidenceSchemaError("sealed authority paths changed before PRE")
    db_file = destinations["target_db"]
    pre_path, anchor_path, post_path, pre_relative, anchor_relative, post_relative = _journal_paths(root, manifest)
    catalog_path = destinations["catalog"]
    guard_path = pre_path.with_suffix(".lock")
    authority_guard = authority_mutation_guard(root, manifest["authority_paths"])
    mutation_guard = authority_guard.__enter__()
    target_descriptor: int | None = None
    auxiliary_reservations: _SQLiteAuxiliaryReservations | None = None
    write_con: sqlite3.Connection | None = None
    try:
        mutation_guard.hold_path(db_file)
        try:
            target_descriptor = mutation_guard.open_path(
                db_file, os.O_RDWR | getattr(os, "O_BINARY", 0))
        except FileNotFoundError as exc:
            raise FileNotFoundError("sealed strategy DB file is missing: %s" % db_file) from exc
        _validate_retained_target(db_file, target_descriptor)
        _validate_sqlite_header_delete_mode(db_file)
        auxiliary_reservations = _reserve_sqlite_auxiliary_paths(db_file)
        write_con = _open_sqlite_promotion_connection(db_file, auxiliary_reservations)
        for path in (pre_path, anchor_path, post_path, destinations["backup"], catalog_path):
            mutation_guard.hold_path(path)
        guard = _acquire_promotion_guard(guard_path)
    except BaseException:
        if write_con is not None:
            write_con.close()
        if auxiliary_reservations is not None:
            auxiliary_reservations.close()
        if target_descriptor is not None:
            os.close(target_descriptor)
        authority_guard.__exit__(None, None, None)
        raise
    try:
        rechecked_manifest, rechecked_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
        if rechecked_manifest != manifest or rechecked_sha256 != manifest_sha256:
            raise EvidenceSchemaError("promotion manifest changed before guarded PRE recheck")
        catalog_path = destinations["catalog"]
        _validate_retained_target(db_file, target_descriptor)
        _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        _validate_catalog_pre_receipt(
            _load_json(catalog_path, "catalog receipt"),
            evidence_id=manifest["evidence_id"],
            manifest_path=Path(manifest_path),
            manifest_sha256=manifest_sha256,
            repo_root=root,
        )
        existing = inspect_promotion_journal_v2(repo_root=root, manifest_path=manifest_path)
        if existing["status"] != "ABSENT" or destinations["backup"].exists():
            raise ValueError("promotion journal or reserved backup refuses rerun")
        _validate_retained_target(db_file, target_descriptor)
        _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        manifest_ref = {
            "path": _repo_relative_path(Path(manifest_path), root, "manifest_path"),
            "sha256": manifest_sha256,
        }
        catalog_ref = {
            "path": _repo_relative_path(catalog_path, root, "catalog_receipt_path"),
            "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        }
        if recheck_authority_paths(manifest["authority_paths"], root) != manifest["authority_paths"]:
            raise EvidenceSchemaError("sealed authority paths changed immediately before PRE")
        pre_sha256 = hashlib.sha256(db_file.read_bytes()).hexdigest()
        pre = {
            "schema_version": 2, "kind": "promotion_journal", "status": "PRE",
            "evidence_id": manifest["evidence_id"], "prepared_at": completed_at,
            "promotion_manifest": manifest_ref, "catalog_receipt": catalog_ref,
            "candidate_set": manifest["candidate_set"], "candidate_set_sha256": manifest["candidate_set_sha256"],
            "target_db": {"path": _repo_relative_path(db_file, root, "target_db"), "pre_sha256": pre_sha256},
            "backup_ref": {"path": _repo_relative_path(destinations["backup"], root, "backup"), "sha256": pre_sha256},
            "chronology": _journal_chronology(manifest, root, completed_at),
        }
        validate_promotion_journal_pre_v2(pre, repo_root=root)
        _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        mutation_guard.validate_file(pre_path)
        _write_exclusive_json(pre_path, pre)
        _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        pre_ref = {"path": pre_relative, "sha256": hashlib.sha256(pre_path.read_bytes()).hexdigest()}
        mutation_guard.validate_file(anchor_path)
        _write_exclusive_bytes(anchor_path, pre_ref["sha256"].encode("ascii"))
        _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        pre_anchor_ref = {"path": anchor_relative, "sha256": hashlib.sha256(anchor_path.read_bytes()).hexdigest()}
        backup_ref = pre["backup_ref"]
        _validate_retained_target(db_file, target_descriptor)
        try:
            mode = write_con.execute("PRAGMA locking_mode=EXCLUSIVE").fetchone()
            if not mode or str(mode[0]).lower() != "exclusive":
                raise EvidenceSchemaError("SQLite EXCLUSIVE locking mode is required for promotion")
            mutation_guard.validate_file(db_file)
            mutation_guard.validate_file(destinations["backup"])
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            write_con.execute("BEGIN EXCLUSIVE")
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            if recheck_authority_paths(manifest["authority_paths"], root) != manifest["authority_paths"]:
                raise EvidenceSchemaError("sealed authority paths changed under write lock")
            locked_pre_sha256 = hashlib.sha256(db_file.read_bytes()).hexdigest()
            if locked_pre_sha256 != pre_sha256:
                raise EvidenceSchemaError("target DB changed after PRE intent; reconciliation is required")
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            backup_sha256 = _copy_locked_db_exclusive(db_file, destinations["backup"])
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            if backup_sha256 != locked_pre_sha256:
                raise EvidenceSchemaError("locked target DB backup does not match defined main-file digest")
            names_by_table = {table: _existing_names(write_con, table) for table in TABLE_BY_SIDE.values()}
            to_insert, conflicts = _split_plan(items, names_by_table)
            inserted: list[dict[str, Any]] = []
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            if to_insert:
                inserted = _apply_inserts(write_con, to_insert)
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            write_con.commit()
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            post_state = capture_sqlite_logical_state(
                db_file, connection=write_con,
                allowed_reserved_sidecars=auxiliary_reservations.paths,
            )
            db_post_sha256 = hashlib.sha256(db_file.read_bytes()).hexdigest()
            logical_delta = build_promotion_logical_delta(
                capture_sqlite_logical_state(destinations["backup"]), post_state, inserted)
            post = {
                "schema_version": 2, "kind": "promotion_result", "status": "POST",
                "evidence_id": manifest["evidence_id"], "completed_at": completed_at,
                "promotion_manifest": manifest_ref, "promotion_manifest_path": manifest_ref["path"],
                "catalog_receipt": catalog_ref, "candidate_set": manifest["candidate_set"],
                "candidate_set_sha256": manifest["candidate_set_sha256"],
                "target_db": {"path": pre["target_db"]["path"], "pre_sha256": pre_sha256, "post_sha256": db_post_sha256},
                "inserted": inserted, "conflicts": conflicts, "backup_ref": backup_ref,
                "pre_intent": pre_ref, "pre_intent_anchor": pre_anchor_ref,
                "chronology": {**pre["chronology"], "post_at": completed_at},
                "logical_delta": logical_delta,
            }
            validate_promotion_journal_post_v2(post, pre=pre, repo_root=root)
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            mutation_guard.validate_file(post_path)
            _write_exclusive_json(post_path, post)
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
            verified, verified_manifest, verified_sha256 = _verify_promotion_result_locked(
                post_path, repo_root=root, connection=write_con,
                locked_post_state=post_state, locked_post_sha256=db_post_sha256,
                allowed_reserved_sidecars=auxiliary_reservations.paths,
            )
            if (
                verified != post
                or verified_manifest != manifest
                or verified_sha256 != hashlib.sha256(post_path.read_bytes()).hexdigest()
            ):
                raise EvidenceSchemaError(
                    "strong promotion verification does not match published POST bytes")
        except BaseException:
            write_con.rollback()
            raise
        finally:
            write_con.close()
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        return verified
    finally:
        try:
            _assert_sqlite_auxiliary_paths_absent(db_file, auxiliary_reservations)
        finally:
            _release_promotion_guard(guard_path, guard)
            if auxiliary_reservations is not None:
                auxiliary_reservations.close()
            os.close(target_descriptor)
            authority_guard.__exit__(None, None, None)


def _validate_items(items: list) -> None:
    """배치 전체를 사전 검증한다 — 위반 1건이라도 있으면 DB 접근 전에 ValueError.

    검사: dict 여부, 'ALP_' 접두, buy_expr/sell_expr 비어있지 않은 str,
    배치 내 이름 중복.
    """
    if not isinstance(items, list) or not items:
        raise ValueError("items는 비어있지 않은 list여야 합니다: %r" % (items,))
    seen: set[str] = set()
    for pos, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d]가 dict가 아닙니다: %r" % (pos, item))
        name = item.get("name")
        if not isinstance(name, str) or not name.startswith(NAME_PREFIX):
            raise ValueError(
                "items[%d] 이름은 %r 접두가 강제됩니다: %r" % (pos, NAME_PREFIX, name)
            )
        for key in ("buy_expr", "sell_expr"):
            expr = item.get(key)
            if not isinstance(expr, str) or not expr.strip():
                raise ValueError(
                    "items[%d](%s) %s가 비어있지 않은 str이 아닙니다: %r"
                    % (pos, name, key, expr)
                )
        if name in seen:
            raise ValueError("배치 내 이름 중복: %r" % name)
        seen.add(name)




def _existing_names(con: sqlite3.Connection, table: str) -> set:
    if table not in TABLE_BY_SIDE.values():
        raise ValueError("unexpected table: %s" % table)
    sql = 'SELECT "%s" FROM "%s"' % (NAME_COLUMN, table)
    return {row[0] for row in con.execute(sql).fetchall()}


def _split_plan(items: list, names_by_table: dict) -> tuple:
    """Skip the whole pair when either table already owns the candidate name."""
    to_insert: list = []
    conflicts: list = []
    for item in items:
        name = item["name"]
        hit_tables = sorted(
            table for table, names in names_by_table.items() if name in names
        )
        if hit_tables:
            conflicts.append(
                {"name": name, "reason": "name_exists", "existing_tables": hit_tables}
            )
        else:
            to_insert.append(item)
    return to_insert, conflicts


def _backup_db(db_path: Path, backup_dir: Path, now) -> Path:
    """Copy exact DB bytes while the caller's BEGIN IMMEDIATE lock is held."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    base = "%s.bak.alpha_lab_%s" % (db_path.name, stamp)
    candidate = backup_dir / base
    counter = 2
    while candidate.exists():
        candidate = backup_dir / ("%s-%d" % (base, counter))
        counter += 1
    shutil.copy2(db_path, candidate)
    return candidate


def _apply_inserts(con: sqlite3.Connection, to_insert: list) -> list:
    """계획된 항목만 INSERT한다(테이블별 1행씩, 쌍 단위). inserted 기록 반환."""
    inserted: list = []
    for item in to_insert:
        for table in ("stockbuy", "stocksell"):
            sql = 'INSERT INTO "%s" ("%s", "%s") VALUES (?, ?)' % (
                table, NAME_COLUMN, CODE_COLUMN,
            )
            con.execute(sql, (item["name"], item[_EXPR_KEY_BY_TABLE[table]]))
        inserted.append(
            {
                "name": item["name"],
                "tables": ["stockbuy", "stocksell"],
                "buy_sha256": _sha256_text(item["buy_expr"]),
                "sell_sha256": _sha256_text(item["sell_expr"]),
                "meta": item.get("meta"),
            }
        )
    return inserted


def register_conditions(db_path, items: list, *, backup_dir, now) -> dict:
    """Retired legacy entry point; v2 provenance is the sole write authority."""
    raise LegacyPromotionBlockedError(
        "legacy-promotion-blocked: use register_conditions_v2 with verified PRE provenance"
    )
