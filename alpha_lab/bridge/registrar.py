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

import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import sqlite3
from pathlib import Path, PurePosixPath
from typing import Any

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    sha256_canonical,
    validate_catalog_promotion_receipt_v2,
    validate_promotion_journal_post_v2,
    validate_promotion_journal_pre_v2,
    verify_promotion_manifest_v2,
)

logger = logging.getLogger(__name__)

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
    receipt = value.get("promotion_receipt") if isinstance(value, dict) else None
    if receipt is None:
        receipt = value
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


def verify_promotion_manifest(
    manifest_path: Path | str,
    *,
    repo_root: Path | str,
    ledger_path: Path | str,
    gate_receipt_path: Path | str,
    gate_usage_path: Path | str,
    catalog_receipt_path: Path | str,
) -> dict[str, Any]:
    """Validate the canonical PRE chain and the catalog's PRE provenance."""
    checks: dict[str, bool] = {}
    try:
        root = Path(repo_root).resolve()
        manifest, manifest_sha256 = verify_promotion_manifest_v2(
            manifest_path, repo_root=root)
        checks.update({"manifest": True, "ledger": True, "evidence_chain": True})
        for supplied, ref, field in (
            (ledger_path, manifest["ledger"], "ledger_path"),
            (gate_receipt_path, manifest["gate_receipt"], "gate_receipt_path"),
            (gate_usage_path, manifest["gate_claim"], "gate_usage_path"),
        ):
            if _repo_relative_path(Path(supplied), root, field) != ref["path"]:
                raise EvidenceSchemaError(f"{field} does not match promotion manifest")
        _validate_catalog_pre_receipt(
            _load_json(Path(catalog_receipt_path), "catalog receipt"),
            evidence_id=manifest["evidence_id"], manifest_path=Path(manifest_path),
            manifest_sha256=manifest_sha256, repo_root=root,
        )
        checks["catalog_pre"] = True
        return _promotion_result(
            passed=True, evidence_id=manifest["evidence_id"],
            candidates=manifest["candidate_set"], checks=checks)
    except (EvidenceSchemaError, OSError, ValueError) as exc:
        return _promotion_result(passed=False, checks=checks, reasons=[str(exc)])


def _journal_paths(repo_root: Path, journal_dir: Path | str, evidence_id: str) -> tuple[Path, Path, str, str]:
    directory = Path(journal_dir)
    if directory.is_absolute():
        raise ValueError("journal_dir must be repository-relative")
    root = repo_root.resolve()
    journal_root = (root / directory).resolve()
    try:
        journal_relative = journal_root.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("journal_dir resolves outside repo_root") from exc
    if not journal_relative or journal_relative == ".":
        raise ValueError("journal_dir must not be repo_root")
    return (
        journal_root / f"{evidence_id}.pre.json",
        journal_root / f"{evidence_id}.post.json",
        f"{journal_relative}/{evidence_id}.pre.json",
        f"{journal_relative}/{evidence_id}.post.json",
    )


def _write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    """Append-only journal write: no replacement and durable file bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    try:
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError(f"promotion journal already exists: {path}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        raise


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
        "sealed_at": seal["sealed_at"],
        "issued_at": receipt["issued_at"],
        "consumed_at": usage["consumed_at"],
        "ledger_at": rows[0]["ts"],
        "pre_at": pre_at,
    }


def inspect_promotion_journal_v2(
    *, repo_root: Path | str, journal_dir: Path | str, evidence_id: str,
) -> dict[str, Any]:
    """Read journal state without touching a strategy DB or attempting recovery."""
    root = Path(repo_root).resolve()
    pre_path, post_path, pre_relative, post_relative = _journal_paths(root, journal_dir, evidence_id)
    if not pre_path.exists() and not post_path.exists():
        return {"status": "ABSENT", "pre_path": pre_relative, "post_path": post_relative}
    if not pre_path.exists():
        raise EvidenceSchemaError("promotion journal POST exists without PRE intent")
    pre = validate_promotion_journal_pre_v2(_load_json(pre_path, "promotion journal PRE"))
    if pre["evidence_id"] != evidence_id:
        raise EvidenceSchemaError("promotion journal PRE evidence_id does not match canonical path")
    if not post_path.exists():
        return {
            "status": "INCOMPLETE_REQUIRES_RECONCILIATION",
            "pre_path": pre_relative,
            "post_path": post_relative,
            "pre": pre,
        }
    post = validate_promotion_journal_post_v2(
        _load_json(post_path, "promotion journal POST"), pre=pre)
    return {
        "status": "COMPLETE", "pre_path": pre_relative, "post_path": post_relative,
        "pre": pre, "post": post,
    }


def register_conditions_v2(
    db_path: Path | str,
    items: list,
    *,
    manifest_path: Path | str,
    repo_root: Path | str,
    ledger_path: Path | str,
    gate_receipt_path: Path | str,
    gate_usage_path: Path | str,
    catalog_receipt_path: Path | str,
    journal_dir: Path | str,
    backup_dir: Path | str,
    now,
) -> dict[str, Any]:
    """Persist PRE intent before any DB access, then record an exclusive POST outcome."""
    root = Path(repo_root).resolve()
    verdict = verify_promotion_manifest(
        manifest_path, repo_root=root, ledger_path=ledger_path,
        gate_receipt_path=gate_receipt_path, gate_usage_path=gate_usage_path,
        catalog_receipt_path=catalog_receipt_path,
    )
    if verdict["pass"] is not True:
        raise ValueError("v2 promotion verification failed: %s" % "; ".join(verdict["reasons"]))
    _validate_items(items)
    expected = {candidate["name"]: candidate for candidate in verdict["candidates"]}
    actual = {item["name"]: item for item in items}
    if set(actual) != set(expected):
        raise ValueError("v2 item names must exactly match promotion manifest candidates")
    for name, item in actual.items():
        candidate = expected[name]
        if (_sha256_text(item["buy_expr"]) != candidate["buy_sha256"]
                or _sha256_text(item["sell_expr"]) != candidate["sell_sha256"]):
            raise ValueError("v2 candidate expression hash mismatch: %s" % name)

    completed_at = now.isoformat() if hasattr(now, "isoformat") else str(now)
    try:
        completed = dt.datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("v2 promotion completed_at must be a timezone-aware ISO-8601 timestamp") from exc
    if completed.tzinfo is None or completed.utcoffset() is None:
        raise ValueError("v2 promotion completed_at must be a timezone-aware ISO-8601 timestamp")

    manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    catalog_path = Path(catalog_receipt_path).resolve()
    catalog_receipt = _validate_catalog_pre_receipt(
        _load_json(catalog_path, "catalog receipt"), evidence_id=manifest["evidence_id"],
        manifest_path=Path(manifest_path), manifest_sha256=manifest_sha256, repo_root=root,
    )
    db_relative = _repo_relative_path(Path(db_path), root, "db_path")
    if any(db_relative == protected or db_relative.startswith(f"{protected}/")
           for protected in ("_database", "_database_v3k_shadow")):
        raise ValueError("v2 promotion refuses protected strategy DB")
    _repo_relative_path(Path(backup_dir), root, "backup_dir")
    pre_path, post_path, pre_relative, post_relative = _journal_paths(
        root, journal_dir, manifest["evidence_id"])
    existing = inspect_promotion_journal_v2(
        repo_root=root, journal_dir=journal_dir, evidence_id=manifest["evidence_id"])
    if existing["status"] != "ABSENT":
        raise ValueError(f"promotion journal refuses rerun: {existing['status']}")

    manifest_ref = {"path": _repo_relative_path(Path(manifest_path), root, "manifest_path"),
                    "sha256": manifest_sha256}
    catalog_ref = {"path": _repo_relative_path(catalog_path, root, "catalog_receipt_path"),
                   "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest()}
    pre_at = completed_at
    pre = {
        "schema_version": 2, "kind": "promotion_journal", "status": "PRE",
        "evidence_id": manifest["evidence_id"], "prepared_at": pre_at,
        "promotion_manifest": manifest_ref, "catalog_receipt": catalog_ref,
        "candidate_set": manifest["candidate_set"],
        "candidate_set_sha256": manifest["candidate_set_sha256"],
        "chronology": _journal_chronology(manifest, root, pre_at),
    }
    validate_promotion_journal_pre_v2(pre)
    _write_exclusive_json(pre_path, pre)

    legacy_result = _register_conditions(db_path, items, backup_dir=backup_dir, now=now)
    backup_ref = None
    if legacy_result["backup_path"] is not None:
        backup = Path(legacy_result["backup_path"])
        backup_ref = {
            "path": _repo_relative_path(backup, root, "backup_path"),
            "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        }
    post = {
        "schema_version": 2, "kind": "promotion_journal", "status": "POST",
        "evidence_id": manifest["evidence_id"], "completed_at": completed_at,
        "promotion_manifest": manifest_ref, "catalog_receipt": catalog_ref,
        "candidate_set_sha256": manifest["candidate_set_sha256"],
        "inserted": legacy_result["inserted"], "conflicts": legacy_result["conflicts"],
        "backup_ref": backup_ref, "db_pre_sha256": legacy_result["db_pre_sha256"],
        "db_post_sha256": legacy_result["db_post_sha256"],
        "chronology": {**pre["chronology"], "post_at": completed_at},
    }
    validate_promotion_journal_post_v2(post, pre=pre)
    _write_exclusive_json(post_path, post)
    return {
        **post,
        "journal_pre_path": pre_relative,
        "journal_post_path": post_relative,
    }


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


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """존재 확인용 연결은 read-only URI로 열어 변형 가능성 자체를 차단한다."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _existing_names(con: sqlite3.Connection, table: str) -> set:
    if table not in TABLE_BY_SIDE.values():
        raise ValueError("unexpected table: %s" % table)
    sql = 'SELECT "%s" FROM "%s"' % (NAME_COLUMN, table)
    return {row[0] for row in con.execute(sql).fetchall()}


def _split_plan(items: list, names_by_table: dict) -> tuple:
    """(to_insert, conflicts)로 나눈다. 동명이 한 테이블에라도 있으면 conflict."""
    to_insert: list = []
    conflicts: list = []
    for item in items:
        name = item["name"]
        hit_tables = sorted(
            table for table, names in names_by_table.items() if name in names
        )
        if hit_tables:
            conflicts.append(
                {"name": name, "reason": "name_exists", "tables": hit_tables}
            )
        else:
            to_insert.append(item)
    return to_insert, conflicts


def _backup_db(db_path: Path, backup_dir: Path, now) -> Path:
    """실쓰기 직전 DB 파일 사본을 backup_dir에 만든다(동명 충돌 시 suffix)."""
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
    con.commit()
    return inserted


def _register_conditions(db_path, items: list, *, backup_dir, now) -> dict:
    """조건식 배치를 전략 DB에 INSERT-only로 등록한다.

    items: [{name, buy_expr, sell_expr, meta}] — name은 'ALP_' 접두 강제.
    buy_expr→stockbuy, sell_expr→stocksell에 같은 이름으로 쌍 저장한다.
    동명이 어느 테이블에든 이미 있으면 쌍 전체 스킵 + conflicts 기록(멱등).
    실쓰기 전 backup_dir에 DB 파일 백업을 강제한다(삽입 0건이면 백업 생략).
    now: 호출자 주입 datetime(백업 파일명 스탬프에만 사용).

    반환: {"inserted": [...], "conflicts": [...], "backup_path": str | None}
    """
    _validate_items(items)
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError("전략 DB 파일이 없습니다: %s" % db_file)
    db_pre_sha256 = hashlib.sha256(db_file.read_bytes()).hexdigest()

    read_con = _open_readonly(db_file)
    try:
        names_by_table = {
            table: _existing_names(read_con, table)
            for table in TABLE_BY_SIDE.values()
        }
    finally:
        read_con.close()

    to_insert, conflicts = _split_plan(items, names_by_table)
    backup_path = None
    inserted: list = []
    if to_insert:
        backup_path = _backup_db(db_file, Path(backup_dir), now)
        write_con = sqlite3.connect(str(db_file))
        try:
            inserted = _apply_inserts(write_con, to_insert)
        finally:
            write_con.close()
    logger.info(
        "register_conditions db=%s inserted=%d conflicts=%d backup=%s",
        db_file, len(inserted), len(conflicts), backup_path,
    )
    return {
        "inserted": inserted,
        "conflicts": conflicts,
        "backup_path": str(backup_path) if backup_path else None,
        "db_pre_sha256": db_pre_sha256,
        "db_post_sha256": hashlib.sha256(db_file.read_bytes()).hexdigest(),
    }
def register_conditions(db_path, items: list, *, backup_dir, now) -> dict:
    """Retired legacy entry point; v2 provenance is the sole write authority."""
    raise LegacyPromotionBlockedError(
        "legacy-promotion-blocked: use register_conditions_v2 with verified PRE provenance"
    )
