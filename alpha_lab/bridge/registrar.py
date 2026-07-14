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
import shutil
import sqlite3
from pathlib import Path, PurePosixPath
from typing import Any

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    sha256_canonical,
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
) -> None:
    if not isinstance(value, dict):
        raise EvidenceSchemaError("catalog receipt must be an object")
    status = value.get("promotion_status")
    required = {
        "schema_version", "phase", "valid", "evidence_id", "source_kind", "source_path", "source_sha256",
    }
    if not isinstance(status, dict) or set(status) != required:
        raise EvidenceSchemaError("catalog receipt promotion_status has invalid keys")
    expected_path = _repo_relative_path(manifest_path, repo_root, "manifest_path")
    if status != {
        "schema_version": 2,
        "phase": "PRE",
        "valid": True,
        "evidence_id": evidence_id,
        "source_kind": "promotion_manifest",
        "source_path": expected_path,
        "source_sha256": manifest_sha256,
    }:
        raise EvidenceSchemaError("catalog PRE promotion_status does not match promotion manifest")


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
            candidates=manifest["candidates"], checks=checks)
    except (EvidenceSchemaError, OSError, ValueError) as exc:
        return _promotion_result(passed=False, checks=checks, reasons=[str(exc)])


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
    backup_dir: Path | str,
    now,
) -> dict[str, Any]:
    """Register only candidates proven by a complete PRE promotion evidence chain."""
    verdict = verify_promotion_manifest(
        manifest_path,
        repo_root=repo_root,
        ledger_path=ledger_path,
        gate_receipt_path=gate_receipt_path,
        gate_usage_path=gate_usage_path,
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
    legacy_result = _register_conditions(db_path, items, backup_dir=backup_dir, now=now)
    try:
        manifest_relative = Path(manifest_path).resolve().relative_to(
            Path(repo_root).resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("manifest_path resolves outside repo_root") from exc
    return {
        "schema_version": 2,
        "kind": "promotion_result",
        "status": "POST",
        "completed_at": completed_at,
        "evidence_id": verdict["evidence_id"],
        "promotion_manifest_path": manifest_relative,
        "promotion_manifest_sha256": sha256_canonical(
            _load_json(Path(manifest_path), "promotion manifest")),
        **legacy_result,
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
    }
def register_conditions(db_path, items: list, *, backup_dir, now) -> dict:
    """Retired legacy entry point; v2 provenance is the sole write authority."""
    raise LegacyPromotionBlockedError(
        "legacy-promotion-blocked: use register_conditions_v2 with verified PRE provenance"
    )
