"""Canonical schemas and validators for the discipline v2 evidence chain."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, TypedDict


_FULL_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA1 = re.compile(r"[0-9a-f]{40}\Z")


class EvidenceSchemaError(ValueError):
    """A v2 evidence object is malformed or no longer matches its inputs."""


class PreregSealV2(TypedDict):
    schema_version: int
    kind: str
    status: str
    sealed_at: str
    sealed_doc: dict[str, str]
    ledger_path: str
    authority_paths: dict[str, str]
    code_manifest: list[dict[str, str]]


class EvidenceIdentityV2(TypedDict):
    prereg_sha256: str
    seal_manifest_sha256: str
    code_manifest_sha256: str
    gate_receipt_id: str
    gate_receipt_sha256: str
    gate_usage_sha256: str
    input_artifacts: list[dict[str, str]]
    result_artifacts: list[dict[str, str]]
    candidate_set: list[dict[str, str]]
    candidate_set_sha256: str
    negative_or_kill: bool


def canonical_json_bytes(value: object) -> bytes:
    """Return the stable UTF-8 representation used by v2 identities."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_canonical(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def require_full_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not _FULL_SHA256.fullmatch(value):
        raise EvidenceSchemaError(f"{field} must be a lowercase 64-character SHA-256")
    return value


def _require_exact_keys(value: object, keys: set[str], field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise EvidenceSchemaError(f"{field} has invalid keys: {actual!r}")
    return value


def parse_timestamp(value: object, field: str) -> dt.datetime:
    """Parse one timezone-aware ISO-8601 timestamp for evidence chronology."""
    if not isinstance(value, str) or not value:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    return parsed


def _require_timestamp(value: object, field: str) -> str:
    parse_timestamp(value, field)
    return value


def require_timestamp_order(*timestamps: tuple[str, object]) -> None:
    """Require the supplied causal timestamps to be in nondecreasing order."""
    parsed = [(field, parse_timestamp(value, field)) for field, value in timestamps]
    for (previous_field, previous), (field, current) in zip(parsed, parsed[1:]):
        if current < previous:
            raise EvidenceSchemaError(f"{field} must not precede {previous_field}")


def _repo_path(value: object, field: str, repo_root: Path) -> tuple[str, Path]:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise EvidenceSchemaError(f"{field} must be a non-empty repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise EvidenceSchemaError(f"{field} must be a safe repository-relative POSIX path")
    candidate = (repo_root / Path(*path.parts)).resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} resolves outside repo_root") from exc
    return path.as_posix(), candidate


def _hash_file(path: Path, field: str) -> str:
    if not path.is_file():
        raise EvidenceSchemaError(f"{field} does not name a file")
    return hashlib.sha256(path.read_bytes()).hexdigest()
def _hash_retained_file(guard: Any, path: Path, field: str) -> str:
    """Hash bytes through a held authority pathname without a direct pathname reopen."""
    digest = hashlib.sha256()
    try:
        fd = guard.open_path(path, os.O_RDONLY)
        with os.fdopen(fd, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceSchemaError(f"{field} cannot be read through its retained authority handle") from exc
    return digest.hexdigest()



def _validate_file_ref(value: object, field: str, repo_root: Path, *, verify_files: bool) -> dict[str, str]:
    item = _require_exact_keys(value, {"path", "sha256"}, field)
    path, resolved = _repo_path(item["path"], f"{field}.path", repo_root)
    digest = require_full_sha256(item["sha256"], f"{field}.sha256")
    if verify_files and _hash_file(resolved, field) != digest:
        raise EvidenceSchemaError(f"{field} SHA-256 does not match on-disk bytes")
    return {"path": path, "sha256": digest}


def _validate_manifest(value: object, field: str, repo_root: Path, *, verify_files: bool) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise EvidenceSchemaError(f"{field} must be a non-empty list")
    manifest = [_validate_file_ref(item, f"{field}[{index}]", repo_root, verify_files=verify_files) for index, item in enumerate(value)]
    paths = [item["path"] for item in manifest]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise EvidenceSchemaError(f"{field} paths must be sorted and unique")
    return manifest
def validate_measurement_bindings(
    *,
    input_artifacts: object,
    result_artifacts: object,
    candidate_set: object,
    negative_or_kill: object,
    repo_root: Path | str,
    verify_files: bool = True,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], str]:
    """Validate immutable measurement artifacts and the canonical candidate set."""
    root = Path(repo_root).resolve()
    inputs = _validate_manifest(input_artifacts, "input_artifacts", root, verify_files=verify_files)
    results = _validate_manifest(result_artifacts, "result_artifacts", root, verify_files=verify_files)
    if not isinstance(candidate_set, list):
        raise EvidenceSchemaError("candidate_set must be a list")
    candidates: list[dict[str, str]] = []
    for index, item in enumerate(candidate_set):
        candidate = _require_exact_keys(
            item, {"name", "buy_sha256", "sell_sha256"}, f"candidate_set[{index}]"
        )
        name = candidate["name"]
        if not isinstance(name, str) or not name.strip():
            raise EvidenceSchemaError(f"candidate_set[{index}].name must be non-empty")
        candidates.append({
            "name": name,
            "buy_sha256": require_full_sha256(
                candidate["buy_sha256"], f"candidate_set[{index}].buy_sha256"
            ),
            "sell_sha256": require_full_sha256(
                candidate["sell_sha256"], f"candidate_set[{index}].sell_sha256"
            ),
        })
    names = [candidate["name"] for candidate in candidates]
    if names != sorted(names) or len(names) != len(set(names)):
        raise EvidenceSchemaError("candidate_set names must be sorted and unique")
    if not isinstance(negative_or_kill, bool):
        raise EvidenceSchemaError("negative_or_kill must be boolean")
    if not candidates and not negative_or_kill:
        raise EvidenceSchemaError("candidate_set may be empty only for a negative_or_kill measurement")
    return inputs, results, candidates, sha256_canonical(candidates)


def _validate_prereg_seal_authority(result: PreregSealV2, root: Path) -> None:
    """Bind a live seal manifest to the sealed document's derived closure and paths."""
    document = root / Path(*PurePosixPath(result["sealed_doc"]["path"]).parts)
    text = document.read_text(encoding="utf-8")
    if "> 지위: **SEALED**" not in text:
        raise EvidenceSchemaError("sealed_doc is not explicitly SEALED")
    if any(marker in text for marker in ("봉인 전 초안", "(기입)", "(미주입")):
        raise EvidenceSchemaError("sealed_doc retains draft marker")
    from alpha_lab.discipline.prereg import _parse_contract, derive_prereg_code_manifest

    contract = _parse_contract(text, root)
    if result["ledger_path"] != contract["ledger_path"]:
        raise EvidenceSchemaError("seal ledger_path does not match sealed contract")
    if result["authority_paths"] != contract["authority_paths"]:
        raise EvidenceSchemaError("seal authority_paths do not match sealed contract")
    expected = sorted(derive_prereg_code_manifest(text, root))
    actual = [item["path"] for item in result["code_manifest"]]
    if actual != expected:
        raise EvidenceSchemaError("code_manifest must equal the sealed document's derived dependency closure")


def validate_prereg_seal(value: object, *, repo_root: Path | str, verify_files: bool = True) -> PreregSealV2:
    root = Path(repo_root).resolve()
    seal = _require_exact_keys(value, {"schema_version", "kind", "status", "sealed_at", "sealed_doc", "ledger_path", "authority_paths", "code_manifest"}, "prereg seal")
    if seal["schema_version"] != 2 or seal["kind"] != "prereg_seal" or seal["status"] != "SEALED":
        raise EvidenceSchemaError("prereg seal must be schema_version=2, kind=prereg_seal, status=SEALED")
    from alpha_lab.discipline.prereg import _contract_authority_paths, _contract_ledger_path
    result: PreregSealV2 = {
        "schema_version": 2,
        "kind": "prereg_seal",
        "status": "SEALED",
        "sealed_at": _require_timestamp(seal["sealed_at"], "sealed_at"),
        "sealed_doc": _validate_file_ref(seal["sealed_doc"], "sealed_doc", root, verify_files=verify_files),
        "ledger_path": _contract_ledger_path(seal["ledger_path"], root),
        "authority_paths": _contract_authority_paths(seal["authority_paths"], root),
        "code_manifest": _validate_manifest(seal["code_manifest"], "code_manifest", root, verify_files=verify_files),
    }
    if verify_files:
        _validate_prereg_seal_authority(result, root)
    return result


def _validate_authoritative_checks(checks: object, *, repo_root: Path, prereg: Mapping[str, str],
                                   manifest: list[dict[str, str]]) -> dict[str, Any]:
    required = {"repo", "sealed_doc", "code_clean", "sha_seal"}
    if not isinstance(checks, dict) or set(checks) != required:
        raise EvidenceSchemaError("checks must contain authoritative repo, sealed_doc, code_clean, and sha_seal results")
    if not all(isinstance(checks[name], dict) and checks[name].get("pass") is True for name in required):
        raise EvidenceSchemaError("all authoritative checks must explicitly pass")
    repo = checks["repo"]
    if repo.get("detail") != "true" or repo.get("reason") != "":
        raise EvidenceSchemaError("repo check is not an authoritative clean work-tree result")
    sealed_doc = checks["sealed_doc"]
    if sealed_doc.get("rel") != prereg["path"] or not _GIT_SHA1.fullmatch(sealed_doc.get("last_commit", "")):
        raise EvidenceSchemaError("sealed_doc check does not bind the sealed preregistration")
    code_clean = checks["code_clean"]
    expected_paths = {str(repo_root / Path(*PurePosixPath(item["path"]).parts)) for item in manifest}
    files = code_clean.get("files")
    if not isinstance(files, dict) or set(files) != expected_paths or code_clean.get("reasons") != []:
        raise EvidenceSchemaError("code_clean check does not cover the complete code manifest")
    for path, item in files.items():
        if not isinstance(item, dict) or item.get("tracked") is not True or item.get("clean") is not True:
            raise EvidenceSchemaError(f"code_clean check is not authoritative for {path}")
        if not _GIT_SHA1.fullmatch(item.get("last_commit", "")) or item.get("reason") != "":
            raise EvidenceSchemaError(f"code_clean check lacks committed provenance for {path}")
    sha_seal = checks["sha_seal"]
    sha_files = sha_seal.get("files")
    if sha_seal.get("checked") is not True or not isinstance(sha_files, dict) or set(sha_files) != expected_paths:
        raise EvidenceSchemaError("sha_seal check must cover the complete code manifest")
    expected_sha = {
        str(repo_root / Path(*PurePosixPath(item["path"]).parts)): item["sha256"]
        for item in manifest
    }
    for path, item in sha_files.items():
        if not isinstance(item, dict) or item.get("expected") != expected_sha[path]:
            raise EvidenceSchemaError(f"sha_seal expected hash does not bind {path}")
        if item.get("actual") != expected_sha[path] or item.get("match") is not True or item.get("reason") != "":
            raise EvidenceSchemaError(f"sha_seal check is not authoritative for {path}")
    return dict(checks)


def validate_gate_receipt(value: object, *, repo_root: Path | str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    keys = {"schema_version", "kind", "status", "receipt_id", "issued_at", "nonce", "repo_head", "seal_manifest", "prereg", "code_manifest_sha256", "code_manifest", "checks"}
    receipt = _require_exact_keys(value, keys, "gate receipt")
    if receipt["schema_version"] != 2 or receipt["kind"] != "measure_gate_receipt" or receipt["status"] != "PASS":
        raise EvidenceSchemaError("gate receipt must be schema_version=2, kind=measure_gate_receipt, status=PASS")
    issued_at = _require_timestamp(receipt["issued_at"], "issued_at")
    if not isinstance(receipt["nonce"], str) or not receipt["nonce"]:
        raise EvidenceSchemaError("nonce must be non-empty")
    if not isinstance(receipt["repo_head"], str) or not _GIT_SHA1.fullmatch(receipt["repo_head"]):
        raise EvidenceSchemaError("repo_head must be a lowercase 40-character git SHA")
    seal_manifest = _validate_file_ref(receipt["seal_manifest"], "seal_manifest", root, verify_files=False)
    seal_path = root / Path(*PurePosixPath(seal_manifest["path"]).parts)
    try:
        seal_value = json.loads(seal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("seal_manifest must be readable canonical JSON") from exc
    if sha256_canonical(seal_value) != seal_manifest["sha256"]:
        raise EvidenceSchemaError("seal_manifest SHA-256 does not match canonical contents")
    seal = validate_prereg_seal(seal_value, repo_root=root, verify_files=True)
    canonical_seal = (
        root / Path(*PurePosixPath(seal["authority_paths"]["seal_dir"]).parts)
        / f"{seal['sealed_doc']['sha256']}.seal.json"
    )
    if seal_path != canonical_seal:
        raise EvidenceSchemaError("seal_manifest path is not the sealed contract canonical path")
    require_timestamp_order(("sealed_at", seal["sealed_at"]), ("issued_at", issued_at))
    prereg = _validate_file_ref(receipt["prereg"], "prereg", root, verify_files=True)
    if prereg != seal["sealed_doc"]:
        raise EvidenceSchemaError("receipt prereg does not match seal manifest")
    manifest = _validate_manifest(receipt["code_manifest"], "code_manifest", root, verify_files=True)
    if manifest != seal["code_manifest"]:
        raise EvidenceSchemaError("receipt code manifest does not match seal manifest")
    code_manifest_sha256 = require_full_sha256(receipt["code_manifest_sha256"], "code_manifest_sha256")
    if code_manifest_sha256 != sha256_canonical(manifest):
        raise EvidenceSchemaError("code_manifest_sha256 does not match code_manifest")
    checks = _validate_authoritative_checks(
        receipt["checks"], repo_root=root, prereg=prereg, manifest=manifest
    )
    expected_id = sha256_canonical({"issued_at": issued_at, "nonce": receipt["nonce"], "repo_head": receipt["repo_head"], "seal_manifest": seal_manifest, "prereg": prereg, "code_manifest_sha256": code_manifest_sha256})
    if require_full_sha256(receipt["receipt_id"], "receipt_id") != expected_id:
        raise EvidenceSchemaError("receipt_id does not match receipt identity")
    result = dict(receipt)
    result["checks"] = checks
    return result


def validate_gate_usage(value: object, *, receipt: Mapping[str, Any]) -> dict[str, Any]:
    usage = _require_exact_keys(
        value,
        {"schema_version", "kind", "issuer", "claim", "consumer", "consumed_at"},
        "gate usage",
    )
    if usage["schema_version"] != 2 or usage["kind"] != "measure_gate_usage":
        raise EvidenceSchemaError("gate usage must be schema_version=2 and kind=measure_gate_usage")
    receipt_id = require_full_sha256(receipt.get("receipt_id"), "receipt.receipt_id")
    receipt_sha256 = sha256_canonical(dict(receipt))
    issuer = _require_exact_keys(
        usage["issuer"], {"receipt_id", "receipt_sha256", "issued_at", "repo_head"}, "gate usage issuer"
    )
    if require_full_sha256(issuer["receipt_id"], "issuer.receipt_id") != receipt_id:
        raise EvidenceSchemaError("gate usage issuer receipt_id does not match receipt")
    if require_full_sha256(issuer["receipt_sha256"], "issuer.receipt_sha256") != receipt_sha256:
        raise EvidenceSchemaError("gate usage issuer receipt_sha256 does not match receipt")
    if _require_timestamp(issuer["issued_at"], "issuer.issued_at") != receipt.get("issued_at"):
        raise EvidenceSchemaError("gate usage issuer issued_at does not match receipt")
    if issuer["repo_head"] != receipt.get("repo_head"):
        raise EvidenceSchemaError("gate usage issuer repo_head does not match receipt")
    claim = _require_exact_keys(usage["claim"], {"receipt_id", "path"}, "gate usage claim")
    if require_full_sha256(claim["receipt_id"], "claim.receipt_id") != receipt_id:
        raise EvidenceSchemaError("gate usage claim receipt_id does not match receipt")
    expected_claim_path = f"claims/{receipt_id}.json"
    if claim["path"] != expected_claim_path:
        raise EvidenceSchemaError("gate usage claim path is not the canonical receipt claim path")
    if not isinstance(usage["consumer"], str) or not usage["consumer"]:
        raise EvidenceSchemaError("consumer must be non-empty")
    consumed_at = _require_timestamp(usage["consumed_at"], "consumed_at")
    issued_at = _require_timestamp(receipt.get("issued_at"), "receipt.issued_at")
    require_timestamp_order(("issued_at", issued_at), ("consumed_at", consumed_at))
    return dict(usage)


def build_evidence_identity(
    receipt: Mapping[str, Any],
    usage: Mapping[str, Any],
    *,
    input_artifacts: object,
    result_artifacts: object,
    candidate_set: object,
    negative_or_kill: object,
    repo_root: Path | str,
) -> tuple[str, EvidenceIdentityV2]:
    """Build an evidence identity bound to gate, measurement artifacts, and candidates."""
    receipt_dict = dict(receipt)
    usage_dict = validate_gate_usage(usage, receipt=receipt_dict)
    inputs, results, candidates, candidate_set_sha256 = validate_measurement_bindings(
        input_artifacts=input_artifacts,
        result_artifacts=result_artifacts,
        candidate_set=candidate_set,
        negative_or_kill=negative_or_kill,
        repo_root=repo_root,
    )
    identity: EvidenceIdentityV2 = {
        "prereg_sha256": require_full_sha256(receipt_dict.get("prereg", {}).get("sha256") if isinstance(receipt_dict.get("prereg"), dict) else None, "prereg_sha256"),
        "seal_manifest_sha256": require_full_sha256(receipt_dict.get("seal_manifest", {}).get("sha256") if isinstance(receipt_dict.get("seal_manifest"), dict) else None, "seal_manifest_sha256"),
        "code_manifest_sha256": require_full_sha256(receipt_dict.get("code_manifest_sha256"), "code_manifest_sha256"),
        "gate_receipt_id": require_full_sha256(receipt_dict.get("receipt_id"), "gate_receipt_id"),
        "gate_receipt_sha256": sha256_canonical(receipt_dict),
        "gate_usage_sha256": sha256_canonical(usage_dict),
        "input_artifacts": inputs,
        "result_artifacts": results,
        "candidate_set": candidates,
        "candidate_set_sha256": candidate_set_sha256,
        "negative_or_kill": negative_or_kill,
    }
    return sha256_canonical(identity), identity
class PromotionManifestV2(TypedDict):
    schema_version: int
    kind: str
    status: str
    created_at: str
    evidence_id: str
    ledger: dict[str, Any]
    gate_receipt: dict[str, str]
    gate_claim: dict[str, str]
    input_artifacts: list[dict[str, str]]
    result_artifacts: list[dict[str, str]]
    candidate_set: list[dict[str, str]]
    candidate_set_sha256: str
    authority_paths: dict[str, str]


class PromotionResultV2(TypedDict):
    """The sole durable POST record for a v2 promotion."""

    schema_version: int
    kind: str
    status: str
    evidence_id: str
    completed_at: str
    promotion_manifest: dict[str, str]
    promotion_manifest_path: str
    catalog_receipt: dict[str, str]
    candidate_set: list[dict[str, str]]
    candidate_set_sha256: str
    target_db: dict[str, str]
    inserted: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    backup_ref: dict[str, str] | None
    pre_intent: dict[str, str]
    pre_intent_anchor: dict[str, str]
    chronology: dict[str, str]
    logical_delta: dict[str, Any]



def _canonical_ledger_path(root: Path, receipt: Mapping[str, Any]) -> Path:
    """Derive the contract-owned v2 ledger path from a validated gate receipt."""
    try:
        seal = _load_json_file(root, receipt["seal_manifest"], "seal_manifest")
        document = root / Path(*PurePosixPath(seal["sealed_doc"]["path"]).parts)
        from alpha_lab.discipline.prereg import _parse_contract

        contract = _parse_contract(document.read_text(encoding="utf-8"), root)
    except (OSError, KeyError, TypeError, EvidenceSchemaError) as exc:
        raise EvidenceSchemaError(f"cannot derive canonical ledger path from sealed contract: {exc}") from exc
    return (root / Path(*PurePosixPath(contract["ledger_path"]).parts)).resolve()


def _canonical_authority_paths(root: Path, receipt: Mapping[str, Any]) -> dict[str, str]:
    try:
        seal = _load_json_file(root, receipt["seal_manifest"], "seal_manifest")
        validated = validate_prereg_seal(seal, repo_root=root, verify_files=True)
    except (EvidenceSchemaError, KeyError, TypeError) as exc:
        raise EvidenceSchemaError(f"cannot derive canonical authority paths from sealed contract: {exc}") from exc
    return dict(validated["authority_paths"])


def issue_promotion_manifest_v2(
    repo_root: Path | str,
    *,
    gate_receipt_path: Path | str,
    gate_claim_path: Path | str,
    ledger_path: Path | str,
    evidence_id: str,
    created_at: str,
    output_dir: Path | str | None = None,
) -> PromotionManifestV2:
    """Issue the only canonical PRE manifest from sealed authorities and one ledger row."""
    root = Path(repo_root).resolve()
    receipt_file, claim_file, source_ledger = (Path(gate_receipt_path).resolve(), Path(gate_claim_path).resolve(), Path(ledger_path).resolve())
    try:
        receipt = validate_gate_receipt(json.loads(receipt_file.read_text(encoding="utf-8")), repo_root=root)
        receipt_id = require_full_sha256(receipt["receipt_id"], "receipt_id")
        if receipt_file != root / "receipts" / f"{receipt_id}.json" or claim_file != root / "claims" / f"{receipt_id}.json":
            raise EvidenceSchemaError("gate receipt or claim path is not canonical")
        usage = validate_gate_usage(json.loads(claim_file.read_text(encoding="utf-8")), receipt=receipt)
    except (OSError, json.JSONDecodeError, EvidenceSchemaError) as exc:
        raise EvidenceSchemaError(f"invalid canonical gate authority: {exc}") from exc
    canonical_ledger = _canonical_ledger_path(root, receipt)
    if source_ledger != canonical_ledger:
        raise EvidenceSchemaError("ledger_path is not the sealed contract ledger_path")
    authority_paths = _canonical_authority_paths(root, receipt)
    output = root / Path(*PurePosixPath(authority_paths["promotions_dir"]).parts)
    if output_dir is not None and Path(output_dir).resolve() != output:
        raise EvidenceSchemaError("output_dir must equal the sealed contract promotions_dir")
    evidence_id, created_at = require_full_sha256(evidence_id, "evidence_id"), _require_timestamp(created_at, "created_at")
    from alpha_lab.discipline import ledger as authority_ledger
    try:
        rows = authority_ledger.read_all(canonical_ledger)
    except authority_ledger.LedgerSchemaError as exc:
        raise EvidenceSchemaError(f"ledger authority validation failed: {exc}") from exc
    matches = [
        (ordinal, row)
        for ordinal, row in enumerate(rows, start=1)
        if row.get("schema_version") == 2 and row["evidence_id"] == evidence_id
    ]
    if len(matches) != 1:
        raise EvidenceSchemaError("canonical ledger must contain exactly one v2 row for evidence_id")
    row_ordinal, row = matches[0]
    identity = row["evidence"]
    reconstructed_id, reconstructed = build_evidence_identity(
        receipt, usage, input_artifacts=identity["input_artifacts"],
        result_artifacts=identity["result_artifacts"], candidate_set=identity["candidate_set"],
        negative_or_kill=identity["negative_or_kill"], repo_root=root,
    )
    if reconstructed_id != evidence_id or reconstructed != identity or identity["negative_or_kill"]:
        raise EvidenceSchemaError("ledger row does not authorize a promotable gate-bound evidence identity")
    require_timestamp_order(
        ("sealed_at", _load_json_file(root, receipt["seal_manifest"], "seal_manifest")["sealed_at"]),
        ("issued_at", receipt["issued_at"]), ("consumed_at", usage["consumed_at"]),
        ("ledger.ts", row["ts"]), ("PRE.created_at", created_at),
    )
    def ref(path: Path) -> dict[str, str]:
        return {"path": path.relative_to(root).as_posix(), "sha256": _hash_file(path, str(path))}
    manifest: PromotionManifestV2 = {
        "schema_version": 2, "kind": "promotion_manifest", "status": "PRE", "created_at": created_at,
        "evidence_id": evidence_id, "ledger": {
            "path": canonical_ledger.relative_to(root).as_posix(),
            "row_ordinal": row_ordinal,
            "record_sha256": sha256_canonical(row),
            "evidence_id": evidence_id,
        },
        "gate_receipt": ref(receipt_file), "gate_claim": ref(claim_file),
        "input_artifacts": identity["input_artifacts"], "result_artifacts": identity["result_artifacts"],
        "candidate_set": identity["candidate_set"], "candidate_set_sha256": identity["candidate_set_sha256"],
        "authority_paths": authority_paths,
    }
    output_file = output / f"{evidence_id}.pre.json"
    validated = validate_promotion_manifest_v2(manifest, repo_root=root, verify_files=True)
    from alpha_lab.discipline.prereg import authority_mutation_guard
    with authority_mutation_guard(root, authority_paths, fields=("promotions_dir",)) as guard:
        guard.hold_path(output_file)
        guard.validate_file(output_file)
        if output_file.exists():
            raise FileExistsError("canonical promotion manifest cannot be reused or overwritten")
        fd = guard.open_path(output_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(canonical_json_bytes(validated).decode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        guard.validate_file(output_file)
        verified, _ = verify_promotion_manifest_v2(output_file, repo_root=root)
        if verified != validated:
            raise EvidenceSchemaError("issued promotion manifest failed self-validation")
    return validated

def validate_promotion_manifest_v2(
    value: object, *, repo_root: Path | str, verify_files: bool = True,
) -> PromotionManifestV2:
    """Validate a PRE promotion authority and its immutable direct bindings."""
    root = Path(repo_root).resolve()
    keys = {
        "schema_version", "kind", "status", "created_at", "evidence_id", "ledger",
        "gate_receipt", "gate_claim", "input_artifacts", "result_artifacts",
        "candidate_set", "candidate_set_sha256", "authority_paths",
    }
    manifest = _require_exact_keys(value, keys, "promotion manifest")
    if (manifest["schema_version"], manifest["kind"], manifest["status"]) != (2, "promotion_manifest", "PRE"):
        raise EvidenceSchemaError("promotion manifest must be strict PRE v2")
    ledger = _require_exact_keys(
        manifest["ledger"], {"path", "row_ordinal", "record_sha256", "evidence_id"}, "ledger"
    )
    ledger_path, _ = _repo_path(ledger["path"], "ledger.path", root)
    row_ordinal = ledger["row_ordinal"]
    if isinstance(row_ordinal, bool) or not isinstance(row_ordinal, int) or row_ordinal < 1:
        raise EvidenceSchemaError("ledger.row_ordinal must be a positive integer")
    result: PromotionManifestV2 = {
        "schema_version": 2, "kind": "promotion_manifest", "status": "PRE",
        "created_at": _require_timestamp(manifest["created_at"], "created_at"),
        "evidence_id": require_full_sha256(manifest["evidence_id"], "evidence_id"),
        "ledger": {
            "path": ledger_path,
            "row_ordinal": row_ordinal,
            "record_sha256": require_full_sha256(
                ledger["record_sha256"], "ledger.record_sha256"
            ),
            "evidence_id": require_full_sha256(ledger["evidence_id"], "ledger.evidence_id"),
        },
        "gate_receipt": _validate_file_ref(manifest["gate_receipt"], "gate_receipt", root, verify_files=verify_files),
        "gate_claim": _validate_file_ref(manifest["gate_claim"], "gate_claim", root, verify_files=verify_files),
        "input_artifacts": _validate_manifest(manifest["input_artifacts"], "input_artifacts", root, verify_files=verify_files),
        "result_artifacts": _validate_manifest(manifest["result_artifacts"], "result_artifacts", root, verify_files=verify_files),
        "candidate_set": manifest["candidate_set"],
        "candidate_set_sha256": require_full_sha256(manifest["candidate_set_sha256"], "candidate_set_sha256"),
        "authority_paths": manifest["authority_paths"],
    }
    _, _, candidates, candidate_hash = validate_measurement_bindings(
        input_artifacts=result["input_artifacts"], result_artifacts=result["result_artifacts"],
        candidate_set=manifest["candidate_set"], negative_or_kill=False, repo_root=root,
        verify_files=verify_files,
    )
    if result["ledger"]["evidence_id"] != result["evidence_id"]:
        raise EvidenceSchemaError("ledger.evidence_id must match promotion manifest evidence_id")
    result["candidate_set"] = candidates
    if result["candidate_set_sha256"] != candidate_hash:
        raise EvidenceSchemaError("candidate_set_sha256 does not match candidate_set")
    receipt_id = _load_json_file(root, result["gate_receipt"], "gate_receipt").get("receipt_id")
    receipt_id = require_full_sha256(receipt_id, "gate_receipt.receipt_id")
    if result["gate_receipt"]["path"] != f"receipts/{receipt_id}.json":
        raise EvidenceSchemaError("gate_receipt path is not canonical")
    receipt = validate_gate_receipt(
        _load_json_file(root, result["gate_receipt"], "gate_receipt"), repo_root=root)
    authority_paths = _canonical_authority_paths(root, receipt)
    if result["authority_paths"] != authority_paths:
        raise EvidenceSchemaError("promotion manifest authority_paths do not match sealed contract")
    if result["gate_claim"]["path"] != f"claims/{receipt_id}.json":
        raise EvidenceSchemaError("gate_claim path is not canonical")
    return result


def _load_json_file(root: Path, ref: Mapping[str, str], field: str) -> dict[str, Any]:
    path = root / Path(*PurePosixPath(ref["path"]).parts)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError(f"{field} must be readable JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceSchemaError(f"{field} must be a JSON object")
    return value


def verify_promotion_manifest_v2(
    manifest_path: Path | str, *, repo_root: Path | str,
) -> tuple[PromotionManifestV2, str]:
    """Verify the complete PRE authority chain, including live artifact bytes."""
    root = Path(repo_root).resolve()
    manifest_file = Path(manifest_path).resolve()
    try:
        manifest_rel = manifest_file.relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError("promotion manifest resolves outside repo_root") from exc
    try:
        raw = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("promotion manifest must be readable JSON") from exc
    manifest = validate_promotion_manifest_v2(raw, repo_root=root, verify_files=True)
    expected_manifest_path = (
        root / Path(*PurePosixPath(manifest["authority_paths"]["promotions_dir"]).parts)
        / f"{manifest['evidence_id']}.pre.json"
    )
    if manifest_file != expected_manifest_path:
        raise EvidenceSchemaError("promotion manifest path is not canonical")
    receipt = validate_gate_receipt(
        _load_json_file(root, manifest["gate_receipt"], "gate_receipt"), repo_root=root
    )
    usage = validate_gate_usage(_load_json_file(root, manifest["gate_claim"], "gate_claim"), receipt=receipt)
    evidence_id, identity = build_evidence_identity(
        receipt, usage, input_artifacts=manifest["input_artifacts"],
        result_artifacts=manifest["result_artifacts"], candidate_set=manifest["candidate_set"],
        negative_or_kill=False, repo_root=root,
    )
    if evidence_id != manifest["evidence_id"]:
        raise EvidenceSchemaError("promotion manifest evidence_id does not reconstruct")
    from alpha_lab.discipline import ledger as authority_ledger

    ledger_path = root / Path(*PurePosixPath(manifest["ledger"]["path"]).parts)
    canonical_ledger = _canonical_ledger_path(root, receipt)
    if ledger_path.resolve() != canonical_ledger:
        raise EvidenceSchemaError("promotion manifest ledger is not the sealed contract ledger_path")
    try:
        authority_rows = authority_ledger.read_all(ledger_path)
    except authority_ledger.LedgerSchemaError as exc:
        raise EvidenceSchemaError(f"ledger authority validation failed: {exc}") from exc
    row_ordinal = manifest["ledger"]["row_ordinal"]
    if row_ordinal > len(authority_rows):
        raise EvidenceSchemaError("promotion manifest ledger row_ordinal is outside the canonical ledger")
    row = authority_rows[row_ordinal - 1]
    if (
        row.get("schema_version") != 2
        or row.get("evidence_id") != evidence_id
        or sha256_canonical(row) != manifest["ledger"]["record_sha256"]
    ):
        raise EvidenceSchemaError("promotion manifest does not bind its committed ledger row")
    if row["evidence"] != identity:
        raise EvidenceSchemaError("ledger evidence does not match promotion evidence")
    require_timestamp_order(("ledger.ts", row["ts"]), ("PRE.created_at", manifest["created_at"]))
    return manifest, _hash_file(manifest_file, "promotion manifest")


def _validate_promotion_outcomes(
    *, inserted: object, conflicts: object, candidates: list[dict[str, str]], field: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(inserted, list) or not isinstance(conflicts, list):
        raise EvidenceSchemaError(f"{field} outcomes must be lists")
    expected = {candidate["name"]: candidate for candidate in candidates}
    accounted: set[str] = set()
    normalized_inserted: list[dict[str, Any]] = []
    for index, value in enumerate(inserted):
        item = _require_exact_keys(
            value, {"name", "tables", "buy_sha256", "sell_sha256", "meta"},
            f"{field}.inserted[{index}]",
        )
        candidate = expected.get(item["name"])
        if (
            candidate is None
            or item["tables"] != ["stockbuy", "stocksell"]
            or require_full_sha256(item["buy_sha256"], f"{field}.inserted[{index}].buy_sha256")
            != candidate["buy_sha256"]
            or require_full_sha256(item["sell_sha256"], f"{field}.inserted[{index}].sell_sha256")
            != candidate["sell_sha256"]
            or item["name"] in accounted
        ):
            raise EvidenceSchemaError(f"{field} inserted does not bind a PRE candidate")
        accounted.add(item["name"])
        normalized_inserted.append(dict(item))
    normalized_conflicts: list[dict[str, Any]] = []
    for index, value in enumerate(conflicts):
        item = _require_exact_keys(
            value, {"name", "reason", "existing_tables"}, f"{field}.conflicts[{index}]",
        )
        tables = item["existing_tables"]
        if (
            item["name"] not in expected
            or item["name"] in accounted
            or item["reason"] != "name_exists"
            or not isinstance(tables, list)
            or not tables
            or len(tables) != len(set(tables))
            or any(table not in {"stockbuy", "stocksell"} for table in tables)
        ):
            raise EvidenceSchemaError(f"{field} conflict does not bind a PRE candidate")
        accounted.add(item["name"])
        normalized_conflicts.append({
            "name": item["name"], "reason": "name_exists",
            "existing_tables": sorted(tables),
        })
    if accounted != set(expected):
        raise EvidenceSchemaError(f"{field} must account for every PRE candidate exactly once")
    return normalized_inserted, normalized_conflicts
def _sqlite_sidecars(db_path: Path) -> tuple[Path, Path, Path]:
    return (
        Path(f"{db_path}-journal"),
        Path(f"{db_path}-wal"),
        Path(f"{db_path}-shm"),
    )


def _sqlite_value(value: object) -> dict[str, str]:
    if value is None:
        return {"type": "null", "value": ""}
    if isinstance(value, bytes):
        return {"type": "blob", "value": value.hex()}
    if isinstance(value, str):
        return {"type": "text", "value": value}
    return {"type": type(value).__name__, "value": str(value)}


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def capture_sqlite_logical_state(
    db_path: Path | str, *, connection: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Read a stable snapshot; only a supplied retained writer may use MEMORY mode."""
    path = Path(db_path).resolve()
    journal_path, wal_path, shm_path = _sqlite_sidecars(path)
    if journal_path.exists() or wal_path.exists() or shm_path.exists():
        raise EvidenceSchemaError("SQLite filesystem sidecar state is not verifiable")
    owns_connection = connection is None
    try:
        con = connection or sqlite3.connect(
            f"{path.as_uri()}?mode=ro", uri=True, isolation_level=None,
        )
    except sqlite3.Error as exc:
        raise EvidenceSchemaError(f"target SQLite DB cannot be opened read-only: {exc}") from exc
    try:
        if owns_connection:
            con.execute("BEGIN")
        mode = con.execute("PRAGMA journal_mode").fetchone()
        allowed_modes = {"delete"} if owns_connection else {"delete", "memory"}
        if not mode or str(mode[0]).lower() not in allowed_modes:
            if owns_connection:
                raise EvidenceSchemaError("SQLite journal mode must be DELETE for verification")
            raise EvidenceSchemaError(
                "retained SQLite connection journal mode must be DELETE or MEMORY for verification"
            )
        if journal_path.exists() or wal_path.exists() or shm_path.exists():
            raise EvidenceSchemaError("SQLite filesystem sidecar state is not verifiable")
        persistent_state = {
            "user_version": con.execute("PRAGMA user_version").fetchone()[0],
            "application_id": con.execute("PRAGMA application_id").fetchone()[0],
            "encoding": con.execute("PRAGMA encoding").fetchone()[0],
            "auto_vacuum": con.execute("PRAGMA auto_vacuum").fetchone()[0],
            "page_size": con.execute("PRAGMA page_size").fetchone()[0],
            "schema_version": con.execute("PRAGMA schema_version").fetchone()[0],
        }
        schema = [
            {"type": row[0], "name": row[1], "table": row[2], "sql": row[3]}
            for row in con.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_master "
                "WHERE type IN ('table', 'index', 'trigger', 'view') ORDER BY type, name"
            )
        ]
        tables: dict[str, Any] = {}
        for entry in schema:
            if entry["type"] != "table":
                continue
            table = entry["name"]
            columns = [
                row[1] for row in con.execute(f"PRAGMA table_xinfo({_quote_identifier(table)})")
                if row[6] == 0
            ]
            select = ", ".join(_quote_identifier(column) for column in columns)
            order = ", ".join(_quote_identifier(column) for column in columns)
            rows = con.execute(
                f"SELECT {select} FROM {_quote_identifier(table)} ORDER BY {order}"
            ).fetchall()
            tables[table] = {
                "columns": columns,
                "rows": [[_sqlite_value(value) for value in row] for row in rows],
            }
        if wal_path.exists() or shm_path.exists():
            raise EvidenceSchemaError("SQLite WAL/SHM sidecar state is not verifiable")
        return {"persistent_state": persistent_state, "schema": schema, "tables": tables}
    except sqlite3.Error as exc:
        raise EvidenceSchemaError(f"target SQLite DB cannot be read logically: {exc}") from exc
    finally:
        if owns_connection:
            try:
                con.execute("COMMIT")
            except sqlite3.Error:
                pass
            con.close()
        if wal_path.exists() or shm_path.exists():
            raise EvidenceSchemaError("SQLite WAL/SHM sidecar state is not verifiable")


def build_promotion_logical_delta(
    pre_state: Mapping[str, Any], post_state: Mapping[str, Any], inserted: list[dict[str, Any]],
) -> dict[str, Any]:
    """Prove that only the declared candidate pair rows changed from the canonical pre-state."""
    expected = {item["name"]: item for item in inserted}
    if pre_state.get("schema") != post_state.get("schema"):
        raise EvidenceSchemaError("promotion changed SQLite schema or schema state")
    if pre_state.get("persistent_state") != post_state.get("persistent_state"):
        raise EvidenceSchemaError("promotion changed persistent SQLite pragma state")
    changes: list[dict[str, Any]] = []
    if set(pre_state.get("tables", {})) != set(post_state.get("tables", {})):
        raise EvidenceSchemaError("promotion changed SQLite table state")
    for table in sorted(pre_state["tables"]):
        before, after = pre_state["tables"][table], post_state["tables"][table]
        if before["columns"] != after["columns"]:
            raise EvidenceSchemaError("promotion changed SQLite table columns")
        before_rows = Counter(canonical_json_bytes(row).decode("utf-8") for row in before["rows"])
        after_rows = Counter(canonical_json_bytes(row).decode("utf-8") for row in after["rows"])
        removed, added = before_rows - after_rows, after_rows - before_rows
        if removed:
            raise EvidenceSchemaError("promotion removed existing SQLite rows")
        if not added:
            continue
        if table not in {"stockbuy", "stocksell"}:
            raise EvidenceSchemaError("promotion inserted unauthorized SQLite rows")
        name_index = before["columns"].index("index") if "index" in before["columns"] else -1
        code_index = before["columns"].index("전략코드") if "전략코드" in before["columns"] else -1
        if name_index < 0 or code_index < 0:
            raise EvidenceSchemaError("promotion target table lacks canonical columns")
        added_rows = [
            json.loads(encoded) for encoded, count in added.items() for _ in range(count)
        ]
        detail_rows: list[dict[str, str]] = []
        for row in added_rows:
            name_cell, code_cell = row[name_index], row[code_index]
            if name_cell["type"] != "text" or code_cell["type"] != "text":
                raise EvidenceSchemaError("promotion inserted an invalid candidate row")
            name = name_cell["value"]
            item = expected.get(name)
            if item is None:
                raise EvidenceSchemaError("promotion inserted an unauthorized candidate row")
            expected_hash = item["buy_sha256"] if table == "stockbuy" else item["sell_sha256"]
            if hashlib.sha256(code_cell["value"].encode("utf-8")).hexdigest() != expected_hash:
                raise EvidenceSchemaError("promotion inserted an unauthorized candidate row")
            detail_rows.append({"name": name, "code_sha256": expected_hash})
        changes.append({"table": table, "inserted": sorted(detail_rows, key=lambda row: row["name"])})
    expected_tables = {
        "stockbuy": sorted(item["name"] for item in inserted),
        "stocksell": sorted(item["name"] for item in inserted),
    }
    actual_tables = {
        change["table"]: [row["name"] for row in change["inserted"]] for change in changes
    }
    if actual_tables != {table: names for table, names in expected_tables.items() if names}:
        raise EvidenceSchemaError("promotion logical delta does not match declared inserted candidates")
    details = {"schema_unchanged": True, "table_changes": changes}
    return {
        "pre_state_sha256": sha256_canonical(pre_state),
        "post_state_sha256": sha256_canonical(post_state),
        "details": details,
        "details_sha256": sha256_canonical(details),
    }


def _validate_logical_delta(value: object) -> dict[str, Any]:
    delta = _require_exact_keys(
        value, {"pre_state_sha256", "post_state_sha256", "details", "details_sha256"},
        "promotion result logical_delta",
    )
    details = _require_exact_keys(delta["details"], {"schema_unchanged", "table_changes"}, "promotion result logical_delta.details")
    if details["schema_unchanged"] is not True or not isinstance(details["table_changes"], list):
        raise EvidenceSchemaError("promotion result logical_delta details are invalid")
    normalized_changes: list[dict[str, Any]] = []
    for index, change in enumerate(details["table_changes"]):
        item = _require_exact_keys(change, {"table", "inserted"}, f"promotion result logical_delta.details.table_changes[{index}]")
        if item["table"] not in {"stockbuy", "stocksell"} or not isinstance(item["inserted"], list):
            raise EvidenceSchemaError("promotion result logical_delta table change is invalid")
        rows = [_require_exact_keys(row, {"name", "code_sha256"}, "promotion result logical_delta row") for row in item["inserted"]]
        normalized_changes.append({"table": item["table"], "inserted": rows})
    normalized_details = {"schema_unchanged": True, "table_changes": normalized_changes}
    if sha256_canonical(normalized_details) != require_full_sha256(delta["details_sha256"], "promotion result logical_delta.details_sha256"):
        raise EvidenceSchemaError("promotion result logical_delta details digest does not match details")
    return {
        "pre_state_sha256": require_full_sha256(delta["pre_state_sha256"], "promotion result logical_delta.pre_state_sha256"),
        "post_state_sha256": require_full_sha256(delta["post_state_sha256"], "promotion result logical_delta.post_state_sha256"),
        "details": normalized_details,
        "details_sha256": delta["details_sha256"],
    }


def validate_promotion_result_v2(
    value: object, *, repo_root: Path | str,
) -> PromotionResultV2:
    """Validate the canonical durable POST envelope without translating it."""
    root = Path(repo_root).resolve()
    keys = {
        "schema_version", "kind", "status", "evidence_id", "completed_at",
        "promotion_manifest", "promotion_manifest_path", "catalog_receipt",
        "candidate_set", "candidate_set_sha256", "target_db", "inserted",
        "conflicts", "backup_ref", "pre_intent", "pre_intent_anchor", "chronology",
        "logical_delta",
    }
    result = _require_exact_keys(value, keys, "promotion result")
    if (result["schema_version"], result["kind"], result["status"]) != (2, "promotion_result", "POST"):
        raise EvidenceSchemaError("promotion result must be strict canonical POST v2")
    manifest = _validate_file_ref(result["promotion_manifest"], "promotion result promotion_manifest", root, verify_files=False)
    manifest_path, _ = _repo_path(result["promotion_manifest_path"], "promotion_manifest_path", root)
    if manifest_path != manifest["path"]:
        raise EvidenceSchemaError("promotion_manifest_path must match promotion_manifest.path")
    catalog = _validate_file_ref(result["catalog_receipt"], "promotion result catalog_receipt", root, verify_files=False)
    candidates = result["candidate_set"]
    _, _, normalized_candidates, candidate_hash = validate_measurement_bindings(
        input_artifacts=[manifest], result_artifacts=[catalog], candidate_set=candidates,
        negative_or_kill=False, repo_root=root, verify_files=False,
    )
    if require_full_sha256(result["candidate_set_sha256"], "candidate_set_sha256") != candidate_hash:
        raise EvidenceSchemaError("candidate_set_sha256 does not match candidate_set")
    target_db = _require_exact_keys(
        result["target_db"], {"path", "pre_sha256", "post_sha256"}, "promotion result target_db")
    target_path, _ = _repo_path(target_db["path"], "promotion result target_db.path", root)
    target = {
        "path": target_path,
        "pre_sha256": require_full_sha256(target_db["pre_sha256"], "promotion result target_db.pre_sha256"),
        "post_sha256": require_full_sha256(target_db["post_sha256"], "promotion result target_db.post_sha256"),
    }
    pre_intent = _validate_file_ref(result["pre_intent"], "promotion result pre_intent", root, verify_files=False)
    pre_intent_anchor = _validate_file_ref(
        result["pre_intent_anchor"], "promotion result pre_intent_anchor", root, verify_files=False)
    backup_ref = result["backup_ref"]
    if backup_ref is not None:
        backup_ref = _validate_file_ref(backup_ref, "promotion result backup_ref", root, verify_files=False)
        if backup_ref["sha256"] != target["pre_sha256"]:
            raise EvidenceSchemaError("promotion result backup SHA-256 must equal target DB pre-state")
    chronology = _require_exact_keys(
        result["chronology"], {"sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at", "post_at"},
        "promotion result chronology",
    )
    require_timestamp_order(*[(name, chronology[name]) for name in (
        "sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at", "post_at"
    )])
    if result["completed_at"] != chronology["post_at"]:
        raise EvidenceSchemaError("promotion result completed_at must equal chronology.post_at")
    normalized_inserted, normalized_conflicts = _validate_promotion_outcomes(
        inserted=result["inserted"], conflicts=result["conflicts"],
        candidates=normalized_candidates, field="promotion result",
    )
    logical_delta = _validate_logical_delta(result["logical_delta"])
    return {
        "schema_version": 2, "kind": "promotion_result", "status": "POST",
        "evidence_id": require_full_sha256(result["evidence_id"], "promotion result evidence_id"),
        "completed_at": _require_timestamp(result["completed_at"], "promotion result completed_at"),
        "promotion_manifest": manifest, "promotion_manifest_path": manifest_path,
        "catalog_receipt": catalog, "candidate_set": normalized_candidates,
        "candidate_set_sha256": candidate_hash, "target_db": target,
        "inserted": normalized_inserted, "conflicts": normalized_conflicts,
        "backup_ref": backup_ref, "pre_intent": pre_intent,
        "pre_intent_anchor": pre_intent_anchor, "chronology": dict(chronology),
        "logical_delta": logical_delta,
    }


def verify_promotion_result_v2(
    result_path: Path | str, *, repo_root: Path | str,
    target_connection: sqlite3.Connection | None = None,
    locked_post_state: Mapping[str, Any] | None = None,
) -> tuple[PromotionResultV2, PromotionManifestV2, str]:
    """Verify the canonical POST, its exact PRE anchor, and live byte authorities."""
    if (target_connection is None) != (locked_post_state is None):
        raise EvidenceSchemaError(
            "retained target connection and locked POST state must be supplied together")
    root = Path(repo_root).resolve()
    source = Path(result_path).resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("promotion result must be readable JSON") from exc
    result = validate_promotion_result_v2(raw, repo_root=root)
    evidence_id = result["evidence_id"]
    manifest_path = root / Path(*PurePosixPath(result["promotion_manifest_path"]).parts)
    manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    if result["promotion_manifest"] != {
        "path": manifest_path.relative_to(root).as_posix(),
        "sha256": manifest_sha256,
    } or evidence_id != manifest["evidence_id"]:
        raise EvidenceSchemaError("promotion result does not bind the exact PRE manifest")
    destinations = _promotion_authority_paths(root, manifest, evidence_id)
    expected_pre = destinations["pre"]
    expected_anchor = destinations["anchor"]
    expected_post = destinations["post"]
    if (
        result["pre_intent"]["path"] != expected_pre
        or result["pre_intent_anchor"]["path"] != expected_anchor
        or result["target_db"]["path"] != destinations["target_db"]
        or source != root / Path(*PurePosixPath(expected_post).parts)
    ):
        raise EvidenceSchemaError("promotion result destinations are not sealed authority paths")
    pre_relative = PurePosixPath(expected_pre)

    pre_path = root / Path(*pre_relative.parts)
    if _hash_file(pre_path, "promotion result pre_intent") != result["pre_intent"]["sha256"]:
        raise EvidenceSchemaError("promotion result pre_intent SHA-256 does not match bytes")
    pre = validate_promotion_journal_pre_v2(
        _load_json_file(root, result["pre_intent"], "promotion result pre_intent"), repo_root=root)
    if (
        pre["evidence_id"] != evidence_id
        or pre["promotion_manifest"] != result["promotion_manifest"]
        or pre["catalog_receipt"] != result["catalog_receipt"]
        or pre["candidate_set"] != result["candidate_set"]
        or pre["candidate_set_sha256"] != result["candidate_set_sha256"]
        or pre["candidate_set"] != manifest["candidate_set"]
        or pre["candidate_set_sha256"] != manifest["candidate_set_sha256"]
        or pre["target_db"]["path"] != result["target_db"]["path"]
        or pre["target_db"]["pre_sha256"] != result["target_db"]["pre_sha256"]
        or pre["backup_ref"]["path"] != destinations["backup"]
        or pre["backup_ref"]["sha256"] != result["target_db"]["pre_sha256"]
        or (result["backup_ref"] is not None and result["backup_ref"] != pre["backup_ref"])
        or pre["chronology"] != {key: result["chronology"][key] for key in pre["chronology"]}
    ):
        raise EvidenceSchemaError("promotion result does not preserve its exact PRE intent")
    anchor_path = root / Path(*PurePosixPath(expected_anchor).parts)
    if _hash_file(anchor_path, "promotion result pre_intent_anchor") != result["pre_intent_anchor"]["sha256"]:
        raise EvidenceSchemaError("promotion result pre_intent_anchor SHA-256 does not match bytes")
    if anchor_path.read_bytes() != result["pre_intent"]["sha256"].encode("ascii"):
        raise EvidenceSchemaError("promotion result pre_intent_anchor does not bind exact PRE bytes")

    catalog_path = root / Path(*PurePosixPath(result["catalog_receipt"]["path"]).parts)
    if _hash_file(catalog_path, "promotion result catalog_receipt") != result["catalog_receipt"]["sha256"]:
        raise EvidenceSchemaError("promotion result catalog receipt SHA-256 does not match bytes")
    outer_catalog_receipt = _load_json_file(
        root, result["catalog_receipt"], "promotion result catalog_receipt")
    if not isinstance(outer_catalog_receipt, dict) or "promotion_receipt" not in outer_catalog_receipt:
        raise EvidenceSchemaError("promotion result catalog receipt must be a research assets build receipt")
    catalog = validate_catalog_promotion_receipt_v2(
        outer_catalog_receipt["promotion_receipt"], repo_root=root)
    if (
        catalog["phase"] != "PRE"
        or catalog["evidence_id"] != evidence_id
        or catalog["promotion_manifest"] != result["promotion_manifest"]
        or catalog["upstream"] != {"kind": "promotion_manifest", **result["promotion_manifest"]}
    ):
        raise EvidenceSchemaError("promotion result does not bind the exact PRE catalog receipt")

    receipt = validate_gate_receipt(
        _load_json_file(root, manifest["gate_receipt"], "gate_receipt"), repo_root=root)
    usage = validate_gate_usage(
        _load_json_file(root, manifest["gate_claim"], "gate_claim"), receipt=receipt)
    seal = validate_prereg_seal(
        _load_json_file(root, receipt["seal_manifest"], "seal_manifest"), repo_root=root)
    from alpha_lab.discipline import ledger as authority_ledger

    ledger_path = root / Path(*PurePosixPath(manifest["ledger"]["path"]).parts)
    try:
        rows = authority_ledger.read_all(ledger_path)
    except authority_ledger.LedgerSchemaError as exc:
        raise EvidenceSchemaError(f"ledger authority validation failed: {exc}") from exc
    row_ordinal = manifest["ledger"]["row_ordinal"]
    if row_ordinal > len(rows):
        raise EvidenceSchemaError("promotion result ledger row_ordinal is outside the canonical ledger")
    row = rows[row_ordinal - 1]
    if (
        row.get("schema_version") != 2
        or row.get("evidence_id") != evidence_id
        or sha256_canonical(row) != manifest["ledger"]["record_sha256"]
    ):
        raise EvidenceSchemaError("promotion result cannot revalidate its committed ledger row")
    expected_chronology = {
        "sealed_at": seal["sealed_at"],
        "issued_at": receipt["issued_at"],
        "consumed_at": usage["consumed_at"],
        "ledger_at": row["ts"],
        "pre_at": pre["prepared_at"],
        "post_at": result["completed_at"],
    }
    if result["chronology"] != expected_chronology:
        raise EvidenceSchemaError("promotion result chronology does not match live authorities")
    require_timestamp_order(*list(expected_chronology.items()))

    if result["backup_ref"] is None:
        raise EvidenceSchemaError("promotion result requires the canonical pre-backup")
    backup = root / Path(*PurePosixPath(result["backup_ref"]["path"]).parts)
    if _hash_file(backup, "promotion result backup_ref") != result["backup_ref"]["sha256"]:
        raise EvidenceSchemaError("promotion result backup SHA-256 does not match bytes")
    target = root / Path(*PurePosixPath(result["target_db"]["path"]).parts)
    pre_state = capture_sqlite_logical_state(backup)
    if target_connection is None:
        post_state = capture_sqlite_logical_state(target)
    else:
        main_path = next(
            (Path(row[2]).resolve() for row in target_connection.execute("PRAGMA database_list")
             if row[1] == "main" and row[2]),
            None,
        )
        if main_path != target.resolve():
            raise EvidenceSchemaError("retained target connection does not address the sealed target DB")
        observed_post_state = capture_sqlite_logical_state(target, connection=target_connection)
        if observed_post_state != locked_post_state:
            raise EvidenceSchemaError("retained target connection does not match locked POST state")
        post_state = observed_post_state
    computed_delta = build_promotion_logical_delta(pre_state, post_state, result["inserted"])
    if computed_delta != result["logical_delta"]:
        raise EvidenceSchemaError("promotion result logical delta does not match canonical SQLite states")
    if _hash_file(target, "promotion result target_db") != result["target_db"]["post_sha256"]:
        raise EvidenceSchemaError("promotion result target DB SHA-256 does not match live bytes")
    return result, manifest, _hash_file(source, "promotion result")


def _canonical_catalog_authority_records(
    manifest: Mapping[str, Any], result: Mapping[str, Any] | None, phase: str,
) -> list[dict[str, str]]:
    candidates = {candidate["name"]: candidate for candidate in manifest["candidate_set"]}
    if not candidates or len(candidates) != len(manifest["candidate_set"]):
        raise EvidenceSchemaError("catalog authority candidates must be unique and nonempty")
    if phase == "PRE":
        return [
            {
                "name": name, "buy_sha256": candidate["buy_sha256"],
                "sell_sha256": candidate["sell_sha256"], "phase": "PRE",
                "outcome": "authorized", "disposition": "pending_post",
            }
            for name, candidate in sorted(candidates.items())
        ]
    if phase != "POST" or result is None:
        raise EvidenceSchemaError("catalog authority phase does not match verified upstream")
    outcomes = {
        item["name"]: ("inserted", "published") for item in result["inserted"]
    }
    outcomes.update({
        item["name"]: ("conflict", item["reason"]) for item in result["conflicts"]
    })
    if set(outcomes) != set(candidates):
        raise EvidenceSchemaError("catalog authority outcomes do not account for every PRE candidate")
    return [
        {
            "name": name, "buy_sha256": candidate["buy_sha256"],
            "sell_sha256": candidate["sell_sha256"], "phase": "POST",
            "outcome": outcomes[name][0], "disposition": outcomes[name][1],
        }
        for name, candidate in sorted(candidates.items())
    ]


def _verify_catalog_authority_db(
    db_path: Path, expected_records: list[dict[str, str]],
) -> None:
    expected_sql = (
        "CREATE TABLE catalog_authority (name TEXT PRIMARY KEY, "
        "buy_sha256 TEXT NOT NULL, sell_sha256 TEXT NOT NULL, phase TEXT NOT NULL, "
        "outcome TEXT NOT NULL, disposition TEXT NOT NULL)"
    )
    try:
        con = sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True, isolation_level=None)
    except sqlite3.Error as exc:
        raise EvidenceSchemaError(f"catalog authority DB cannot be opened read-only: {exc}") from exc
    try:
        row = con.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'catalog_authority'"
        ).fetchone()
        columns = con.execute("PRAGMA table_info(catalog_authority)").fetchall()
        expected_columns = [
            ("name", "TEXT", 0, 1), ("buy_sha256", "TEXT", 1, 0),
            ("sell_sha256", "TEXT", 1, 0), ("phase", "TEXT", 1, 0),
            ("outcome", "TEXT", 1, 0), ("disposition", "TEXT", 1, 0),
        ]
        actual_columns = [(item[1], item[2], item[3], item[5]) for item in columns]
        if row is None or row[0] != expected_sql or actual_columns != expected_columns:
            raise EvidenceSchemaError("catalog authority DB schema is not canonical")
        rows = con.execute(
            "SELECT name, buy_sha256, sell_sha256, phase, outcome, disposition "
            "FROM catalog_authority ORDER BY name"
        ).fetchall()
    except sqlite3.Error as exc:
        raise EvidenceSchemaError(f"catalog authority DB cannot be read: {exc}") from exc
    finally:
        con.close()
    actual_records = [
        dict(zip(("name", "buy_sha256", "sell_sha256", "phase", "outcome", "disposition"), row))
        for row in rows
    ]
    if (
        len(actual_records) != len(expected_records)
        or sha256_canonical(actual_records) != sha256_canonical(expected_records)
        or actual_records != expected_records
    ):
        raise EvidenceSchemaError("catalog authority DB records are omitted, extra, or misstated")
def _verify_catalog_authority_db_from_retained_identity(
    root: Path,
    authority_paths: Mapping[str, str],
    db_path: Path,
    expected_sha256: str,
    expected_records: list[dict[str, str]],
) -> None:
    """Bind receipt bytes and SQLite reads to one held catalog authority identity."""
    from alpha_lab.discipline.prereg import authority_mutation_guard

    with authority_mutation_guard(root, dict(authority_paths), fields=("catalog_dir",)) as guard:
        guard.hold_path(db_path)
        observed_sha256 = _hash_retained_file(guard, db_path, "catalog receipt catalog_db")
        if observed_sha256 != expected_sha256:
            raise EvidenceSchemaError("catalog receipt catalog_db SHA-256 does not match retained authority bytes")
        _verify_catalog_authority_db(db_path, expected_records)
        guard.validate_file(db_path)
        if _hash_retained_file(guard, db_path, "catalog receipt catalog_db") != observed_sha256:
            raise EvidenceSchemaError(
                "catalog receipt catalog_db pathname identity changed during SQLite authority validation"
            )



def validate_catalog_promotion_receipt_v2(
    value: object, *, repo_root: Path | str,
) -> dict[str, Any]:
    """Validate the authoritative catalog receipt, including live catalog bytes."""
    root = Path(repo_root).resolve()
    keys = {
        "schema_version", "kind", "phase", "valid", "evidence_id", "upstream",
        "promotion_manifest", "catalog_db", "source_hashes",
    }
    receipt = _require_exact_keys(value, keys, "catalog promotion receipt")
    if receipt["schema_version"] != 2 or receipt["kind"] != "catalog_promotion_receipt":
        raise EvidenceSchemaError("catalog receipt must be schema v2 catalog_promotion_receipt")
    if receipt["phase"] not in {"PRE", "POST"} or receipt["valid"] is not True:
        raise EvidenceSchemaError("catalog receipt must be an authoritative PRE or POST receipt")
    evidence_id = require_full_sha256(receipt["evidence_id"], "catalog receipt evidence_id")
    manifest_ref = _validate_file_ref(
        receipt["promotion_manifest"], "catalog receipt promotion_manifest", root, verify_files=True)
    manifest, _ = verify_promotion_manifest_v2(
        root / Path(*PurePosixPath(manifest_ref["path"]).parts), repo_root=root)
    if manifest["evidence_id"] != evidence_id:
        raise EvidenceSchemaError("catalog receipt does not bind its exact PRE manifest")
    upstream = _require_exact_keys(receipt["upstream"], {"kind", "path", "sha256"}, "catalog receipt upstream")
    expected_kind = "promotion_manifest" if receipt["phase"] == "PRE" else "promotion_result"
    if upstream["kind"] != expected_kind:
        raise EvidenceSchemaError("catalog receipt upstream kind does not match phase")
    upstream_path, upstream_file = _repo_path(upstream["path"], "catalog receipt upstream.path", root)
    upstream_sha256 = require_full_sha256(upstream["sha256"], "catalog receipt upstream.sha256")
    try:
        json.loads(upstream_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("catalog receipt upstream must be readable JSON") from exc
    if _hash_file(upstream_file, "catalog receipt upstream") != upstream_sha256:
        raise EvidenceSchemaError("catalog receipt upstream SHA does not match exact authority bytes")
    upstream_ref = {"path": upstream_path, "sha256": upstream_sha256}
    verified_result: PromotionResultV2 | None = None
    if receipt["phase"] == "PRE":
        if upstream_path != manifest_ref["path"]:
            raise EvidenceSchemaError("catalog PRE receipt upstream must be the exact PRE manifest")
    else:
        verified_result, result_manifest, result_sha256 = verify_promotion_result_v2(
            upstream_file, repo_root=root)
        if result_sha256 != upstream_sha256 or result_manifest != manifest:
            raise EvidenceSchemaError("catalog POST receipt does not bind the exact POST/PRE chain")
    db_ref = _validate_file_ref(receipt["catalog_db"], "catalog receipt catalog_db", root, verify_files=False)
    catalog_dir = PurePosixPath(manifest["authority_paths"]["catalog_dir"])
    expected_db = (catalog_dir / f"{evidence_id}.{receipt['phase'].lower()}.db").as_posix()
    if db_ref["path"] != expected_db:
        raise EvidenceSchemaError("catalog receipt DB path is not a sealed authority destination")
    sources = _validate_manifest(receipt["source_hashes"], "catalog receipt source_hashes", root, verify_files=True)
    expected_sources = sorted(
        [*manifest["input_artifacts"], *manifest["result_artifacts"]],
        key=lambda item: item["path"],
    )
    if sources != expected_sources:
        raise EvidenceSchemaError(
            "catalog receipt source_hashes must exactly equal manifest input_artifacts and result_artifacts")
    _verify_catalog_authority_db_from_retained_identity(
        root,
        manifest["authority_paths"],
        root / Path(*PurePosixPath(db_ref["path"]).parts),
        db_ref["sha256"],
        _canonical_catalog_authority_records(manifest, verified_result, receipt["phase"]),
    )
    return {
        "schema_version": 2, "kind": "catalog_promotion_receipt", "phase": receipt["phase"],
        "valid": True, "evidence_id": evidence_id, "upstream": {
            "kind": expected_kind, **upstream_ref,
        }, "promotion_manifest": manifest_ref, "catalog_db": db_ref, "source_hashes": sources,
    }
def _promotion_authority_paths(
    root: Path, manifest: Mapping[str, Any], evidence_id: str,
) -> dict[str, str]:
    """Derive every mutable promotion destination from sealed authority paths."""
    authority = manifest["authority_paths"]
    journal = PurePosixPath(authority["journal_dir"])
    backup = PurePosixPath(authority["backup_dir"])
    catalog = PurePosixPath(authority["catalog_dir"])
    return {
        "target_db": authority["target_db"],
        "pre": (journal / f"{evidence_id}.pre.json").as_posix(),
        "anchor": (journal / f"{evidence_id}.pre.sha256").as_posix(),
        "post": (journal / f"{evidence_id}.post.json").as_posix(),
        "backup": (backup / f"{evidence_id}.pre.sqlite").as_posix(),
        "catalog_pre": (catalog / f"{evidence_id}.pre.receipt.json").as_posix(),
        "catalog_post": (catalog / f"{evidence_id}.post.receipt.json").as_posix(),
    }


def validate_promotion_journal_pre_v2(
    value: object, *, repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Validate the durable PRE intent before any target DB access."""
    root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    keys = {
        "schema_version", "kind", "status", "evidence_id", "prepared_at",
        "promotion_manifest", "catalog_receipt", "candidate_set",
        "candidate_set_sha256", "target_db", "backup_ref", "chronology",
    }
    pre = _require_exact_keys(value, keys, "promotion journal PRE")
    if (pre["schema_version"], pre["kind"], pre["status"]) != (2, "promotion_journal", "PRE"):
        raise EvidenceSchemaError("promotion journal PRE must be strict v2")
    manifest = _validate_file_ref(
        pre["promotion_manifest"], "promotion journal PRE manifest", root, verify_files=False)
    catalog = _validate_file_ref(
        pre["catalog_receipt"], "promotion journal PRE catalog receipt", root, verify_files=False)
    _, _, candidates, candidate_hash = validate_measurement_bindings(
        input_artifacts=[manifest], result_artifacts=[catalog], candidate_set=pre["candidate_set"],
        negative_or_kill=False, repo_root=root, verify_files=False,
    )
    if require_full_sha256(pre["candidate_set_sha256"], "promotion journal PRE candidate_set_sha256") != candidate_hash:
        raise EvidenceSchemaError("promotion journal PRE candidate_set_sha256 does not match candidate_set")
    target = _require_exact_keys(
        pre["target_db"], {"path", "pre_sha256"}, "promotion journal PRE target_db")
    target_path, _ = _repo_path(target["path"], "promotion journal PRE target_db.path", root)
    pre_sha256 = require_full_sha256(
        target["pre_sha256"], "promotion journal PRE target_db.pre_sha256")
    backup = _validate_file_ref(
        pre["backup_ref"], "promotion journal PRE backup_ref", root, verify_files=False)
    if backup["sha256"] != pre_sha256:
        raise EvidenceSchemaError("promotion journal PRE backup SHA-256 must equal target DB pre-state")
    manifest_value, _ = verify_promotion_manifest_v2(
        root / Path(*PurePosixPath(manifest["path"]).parts), repo_root=root)
    expected = _promotion_authority_paths(root, manifest_value, pre["evidence_id"])
    if target_path != expected["target_db"] or backup["path"] != expected["backup"]:
        raise EvidenceSchemaError("promotion journal PRE destinations are not sealed authority paths")
    chronology = _require_exact_keys(
        pre["chronology"], {"sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at"},
        "promotion journal PRE chronology",
    )
    require_timestamp_order(*[(name, chronology[name]) for name in (
        "sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at"
    )])
    if pre["prepared_at"] != chronology["pre_at"]:
        raise EvidenceSchemaError("promotion journal PRE prepared_at must equal chronology.pre_at")
    return {
        "schema_version": 2, "kind": "promotion_journal", "status": "PRE",
        "evidence_id": require_full_sha256(pre["evidence_id"], "promotion journal PRE evidence_id"),
        "prepared_at": _require_timestamp(pre["prepared_at"], "promotion journal PRE prepared_at"),
        "promotion_manifest": manifest, "catalog_receipt": catalog,
        "candidate_set": candidates, "candidate_set_sha256": candidate_hash,
        "target_db": {"path": target_path, "pre_sha256": pre_sha256},
        "backup_ref": backup, "chronology": dict(chronology),
    }


def validate_promotion_journal_post_v2(
    value: object, *, pre: Mapping[str, Any], repo_root: Path | str,
) -> PromotionResultV2:
    """Compatibility verifier for the canonical POST file against its PRE intent."""
    validated_pre = validate_promotion_journal_pre_v2(pre, repo_root=repo_root)
    post = validate_promotion_result_v2(value, repo_root=repo_root)
    if (
        post["evidence_id"] != validated_pre["evidence_id"]
        or post["promotion_manifest"] != validated_pre["promotion_manifest"]
        or post["catalog_receipt"] != validated_pre["catalog_receipt"]
        or post["candidate_set"] != validated_pre["candidate_set"]
        or post["candidate_set_sha256"] != validated_pre["candidate_set_sha256"]
        or post["target_db"]["path"] != validated_pre["target_db"]["path"]
        or post["target_db"]["pre_sha256"] != validated_pre["target_db"]["pre_sha256"]
        or post["chronology"] != {
            **validated_pre["chronology"], "post_at": post["chronology"]["post_at"],
        }
    ):
        raise EvidenceSchemaError("promotion result does not preserve its exact PRE intent")
    return post
