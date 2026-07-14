"""Canonical schemas and validators for the discipline v2 evidence chain."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
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
    """Bind a live seal manifest to the sealed document's derived closure."""
    document = root / Path(*PurePosixPath(result["sealed_doc"]["path"]).parts)
    text = document.read_text(encoding="utf-8")
    if "> 지위: **SEALED**" not in text:
        raise EvidenceSchemaError("sealed_doc is not explicitly SEALED")
    if any(marker in text for marker in ("봉인 전 초안", "(기입)", "(미주입")):
        raise EvidenceSchemaError("sealed_doc retains draft marker")
    from alpha_lab.discipline.prereg import derive_prereg_code_manifest

    expected = sorted(derive_prereg_code_manifest(text, root))
    actual = [item["path"] for item in result["code_manifest"]]
    if actual != expected:
        raise EvidenceSchemaError("code_manifest must equal the sealed document's derived dependency closure")


def validate_prereg_seal(value: object, *, repo_root: Path | str, verify_files: bool = True) -> PreregSealV2:
    root = Path(repo_root).resolve()
    seal = _require_exact_keys(value, {"schema_version", "kind", "status", "sealed_at", "sealed_doc", "code_manifest"}, "prereg seal")
    if seal["schema_version"] != 2 or seal["kind"] != "prereg_seal" or seal["status"] != "SEALED":
        raise EvidenceSchemaError("prereg seal must be schema_version=2, kind=prereg_seal, status=SEALED")
    result: PreregSealV2 = {
        "schema_version": 2,
        "kind": "prereg_seal",
        "status": "SEALED",
        "sealed_at": _require_timestamp(seal["sealed_at"], "sealed_at"),
        "sealed_doc": _validate_file_ref(seal["sealed_doc"], "sealed_doc", root, verify_files=verify_files),
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
    ledger: dict[str, str]
    gate_receipt: dict[str, str]
    gate_claim: dict[str, str]
    input_artifacts: list[dict[str, str]]
    result_artifacts: list[dict[str, str]]
    candidate_set: list[dict[str, str]]
    candidate_set_sha256: str


class PromotionResultV2(TypedDict):
    schema_version: int
    kind: str
    status: str
    completed_at: str
    evidence_id: str
    promotion_manifest_path: str
    promotion_manifest_sha256: str
    inserted: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    backup_path: str | None




def validate_promotion_manifest_v2(
    value: object, *, repo_root: Path | str, verify_files: bool = True,
) -> PromotionManifestV2:
    """Validate a PRE promotion authority and its immutable direct bindings."""
    root = Path(repo_root).resolve()
    keys = {
        "schema_version", "kind", "status", "created_at", "evidence_id", "ledger",
        "gate_receipt", "gate_claim", "input_artifacts", "result_artifacts",
        "candidate_set", "candidate_set_sha256",
    }
    manifest = _require_exact_keys(value, keys, "promotion manifest")
    if (manifest["schema_version"], manifest["kind"], manifest["status"]) != (2, "promotion_manifest", "PRE"):
        raise EvidenceSchemaError("promotion manifest must be strict PRE v2")
    ledger = _require_exact_keys(manifest["ledger"], {"path", "sha256", "record_sha256"}, "ledger")
    result: PromotionManifestV2 = {
        "schema_version": 2, "kind": "promotion_manifest", "status": "PRE",
        "created_at": _require_timestamp(manifest["created_at"], "created_at"),
        "evidence_id": require_full_sha256(manifest["evidence_id"], "evidence_id"),
        "ledger": _validate_file_ref(
            {"path": ledger["path"], "sha256": ledger["sha256"]},
            "ledger", root, verify_files=verify_files),
        "gate_receipt": _validate_file_ref(manifest["gate_receipt"], "gate_receipt", root, verify_files=verify_files),
        "gate_claim": _validate_file_ref(manifest["gate_claim"], "gate_claim", root, verify_files=verify_files),
        "input_artifacts": _validate_manifest(manifest["input_artifacts"], "input_artifacts", root, verify_files=verify_files),
        "result_artifacts": _validate_manifest(manifest["result_artifacts"], "result_artifacts", root, verify_files=verify_files),
        "candidate_set": manifest["candidate_set"],
        "candidate_set_sha256": require_full_sha256(manifest["candidate_set_sha256"], "candidate_set_sha256"),
    }
    _, _, candidates, candidate_hash = validate_measurement_bindings(
        input_artifacts=result["input_artifacts"], result_artifacts=result["result_artifacts"],
        candidate_set=manifest["candidate_set"], negative_or_kill=False, repo_root=root,
        verify_files=verify_files,
    )
    result["ledger"]["record_sha256"] = require_full_sha256(
        ledger["record_sha256"], "ledger.record_sha256")
    result["candidate_set"] = candidates
    if result["candidate_set_sha256"] != candidate_hash:
        raise EvidenceSchemaError("candidate_set_sha256 does not match candidate_set")
    receipt_id = _load_json_file(root, result["gate_receipt"], "gate_receipt").get("receipt_id")
    receipt_id = require_full_sha256(receipt_id, "gate_receipt.receipt_id")
    if result["gate_receipt"]["path"] != f"receipts/{receipt_id}.json":
        raise EvidenceSchemaError("gate_receipt path is not canonical")
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
    try:
        authority_rows = authority_ledger.read_all(ledger_path)
    except authority_ledger.LedgerSchemaError as exc:
        raise EvidenceSchemaError(f"ledger authority validation failed: {exc}") from exc
    rows = [
        row for row in authority_rows
        if row.get("schema_version") == 2 and row.get("evidence_id") == evidence_id
    ]
    if len(rows) != 1 or sha256_canonical(rows[0]) != manifest["ledger"]["record_sha256"]:
        raise EvidenceSchemaError("promotion manifest does not bind exactly one ledger v2 row")
    if rows[0]["evidence"] != identity:
        raise EvidenceSchemaError("ledger evidence does not match promotion evidence")
    require_timestamp_order(("ledger.ts", rows[0]["ts"]), ("PRE.created_at", manifest["created_at"]))
    return manifest, _hash_file(manifest_file, "promotion manifest")


def validate_promotion_result_v2(
    value: object, *, repo_root: Path | str,
) -> PromotionResultV2:
    """Validate the POST envelope before its PRE authority is resolved."""
    keys = {
        "schema_version", "kind", "status", "completed_at", "evidence_id",
        "promotion_manifest_path", "promotion_manifest_sha256", "inserted",
        "conflicts", "backup_path",
    }
    result = _require_exact_keys(value, keys, "promotion result")
    if (result["schema_version"], result["kind"], result["status"]) != (2, "promotion_result", "POST"):
        raise EvidenceSchemaError("promotion result must be strict POST v2")
    manifest_path, _ = _repo_path(
        result["promotion_manifest_path"], "promotion_manifest_path", Path(repo_root).resolve())
    if not isinstance(result["inserted"], list) or not isinstance(result["conflicts"], list):
        raise EvidenceSchemaError("promotion result inserted and conflicts must be lists")
    if result["backup_path"] is not None and not isinstance(result["backup_path"], str):
        raise EvidenceSchemaError("promotion result backup_path must be a string or null")
    return {
        "schema_version": 2, "kind": "promotion_result", "status": "POST",
        "completed_at": _require_timestamp(result["completed_at"], "completed_at"),
        "evidence_id": require_full_sha256(result["evidence_id"], "evidence_id"),
        "promotion_manifest_path": manifest_path,
        "promotion_manifest_sha256": require_full_sha256(
            result["promotion_manifest_sha256"], "promotion_manifest_sha256"),
        "inserted": result["inserted"], "conflicts": result["conflicts"],
        "backup_path": result["backup_path"],
    }


def verify_promotion_result_v2(
    result_path: Path | str, *, repo_root: Path | str,
) -> tuple[PromotionResultV2, PromotionManifestV2, str]:
    """Verify POST against the exact PRE authority and every candidate outcome."""
    root = Path(repo_root).resolve()
    source = Path(result_path).resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("promotion result must be readable JSON") from exc
    result = validate_promotion_result_v2(raw, repo_root=root)
    manifest_path = root / Path(*PurePosixPath(result["promotion_manifest_path"]).parts)
    manifest, manifest_sha256 = verify_promotion_manifest_v2(manifest_path, repo_root=root)
    if result["evidence_id"] != manifest["evidence_id"]:
        raise EvidenceSchemaError("promotion result evidence_id does not match PRE manifest")
    if result["promotion_manifest_sha256"] != manifest_sha256:
        raise EvidenceSchemaError("promotion result does not bind the exact PRE manifest bytes")
    require_timestamp_order(
        ("PRE.created_at", manifest["created_at"]), ("POST.completed_at", result["completed_at"]))
    expected = {candidate["name"]: candidate for candidate in manifest["candidate_set"]}
    inserted_names: set[str] = set()
    for index, item in enumerate(result["inserted"]):
        item = _require_exact_keys(
            item, {"name", "tables", "buy_sha256", "sell_sha256", "meta"}, f"inserted[{index}]")
        name = item["name"]
        if not isinstance(name, str) or name not in expected or item["tables"] != ["stockbuy", "stocksell"]:
            raise EvidenceSchemaError("promotion result inserted structure is invalid")
        if name in inserted_names:
            raise EvidenceSchemaError("promotion result inserted names must be unique")
        candidate = expected[name]
        if (
            require_full_sha256(item["buy_sha256"], f"inserted[{index}].buy_sha256") != candidate["buy_sha256"]
            or require_full_sha256(item["sell_sha256"], f"inserted[{index}].sell_sha256") != candidate["sell_sha256"]
        ):
            raise EvidenceSchemaError("promotion result inserted hashes do not match PRE candidate")
        inserted_names.add(name)
    conflict_names: set[str] = set()
    for index, item in enumerate(result["conflicts"]):
        item = _require_exact_keys(item, {"name", "reason", "tables"}, f"conflicts[{index}]")
        name = item["name"]
        if (
            not isinstance(name, str) or name not in expected or item["reason"] != "name_exists"
            or item["tables"] != ["stockbuy", "stocksell"]
        ):
            raise EvidenceSchemaError("promotion result conflict does not bind a candidate")
        if name in conflict_names:
            raise EvidenceSchemaError("promotion result conflict names must be unique")
        conflict_names.add(name)
    if inserted_names & conflict_names or inserted_names | conflict_names != set(expected):
        raise EvidenceSchemaError("promotion result must account for every PRE candidate exactly once")
    return result, manifest, _hash_file(source, "promotion result")


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
    if receipt["phase"] == "PRE":
        if upstream_path != manifest_ref["path"]:
            raise EvidenceSchemaError("catalog PRE receipt upstream must be the exact PRE manifest")
    else:
        result, result_manifest, result_sha256 = verify_promotion_result_v2(
            upstream_file, repo_root=root)
        if result_sha256 != upstream_sha256 or result_manifest != manifest:
            raise EvidenceSchemaError("catalog POST receipt does not bind the exact POST/PRE chain")
    db_ref = _validate_file_ref(receipt["catalog_db"], "catalog receipt catalog_db", root, verify_files=True)
    sources = _validate_manifest(receipt["source_hashes"], "catalog receipt source_hashes", root, verify_files=True)
    if len({item["path"] for item in sources}) != len(sources):
        raise EvidenceSchemaError("catalog receipt source_hashes paths must be unique")
    return {
        "schema_version": 2, "kind": "catalog_promotion_receipt", "phase": receipt["phase"],
        "valid": True, "evidence_id": evidence_id, "upstream": {
            "kind": expected_kind, **upstream_ref,
        }, "promotion_manifest": manifest_ref, "catalog_db": db_ref, "source_hashes": sources,
    }
def validate_promotion_journal_pre_v2(value: object) -> dict[str, Any]:
    """Validate the durable, pre-mutation journal intent envelope."""
    keys = {
        "schema_version", "kind", "status", "evidence_id", "prepared_at",
        "promotion_manifest", "catalog_receipt", "candidate_set",
        "candidate_set_sha256", "chronology",
    }
    pre = _require_exact_keys(value, keys, "promotion journal PRE")
    if (pre["schema_version"], pre["kind"], pre["status"]) != (
        2, "promotion_journal", "PRE"
    ):
        raise EvidenceSchemaError("promotion journal PRE must be strict v2")
    candidates = pre["candidate_set"]
    if not isinstance(candidates, list):
        raise EvidenceSchemaError("promotion journal PRE candidate_set must be a list")
    normalized_candidates: list[dict[str, str]] = []
    for index, candidate in enumerate(candidates):
        item = _require_exact_keys(
            candidate, {"name", "buy_sha256", "sell_sha256"},
            f"promotion journal PRE candidate_set[{index}]",
        )
        if not isinstance(item["name"], str) or not item["name"]:
            raise EvidenceSchemaError("promotion journal PRE candidate name must be non-empty")
        normalized_candidates.append({
            "name": item["name"],
            "buy_sha256": require_full_sha256(item["buy_sha256"], "promotion journal PRE buy_sha256"),
            "sell_sha256": require_full_sha256(item["sell_sha256"], "promotion journal PRE sell_sha256"),
        })
    if normalized_candidates != sorted(normalized_candidates, key=lambda item: item["name"]):
        raise EvidenceSchemaError("promotion journal PRE candidate_set must be sorted")
    if len({item["name"] for item in normalized_candidates}) != len(normalized_candidates):
        raise EvidenceSchemaError("promotion journal PRE candidate_set names must be unique")
    chronology = _require_exact_keys(
        pre["chronology"],
        {"sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at"},
        "promotion journal PRE chronology",
    )
    require_timestamp_order(
        ("sealed_at", chronology["sealed_at"]),
        ("issued_at", chronology["issued_at"]),
        ("consumed_at", chronology["consumed_at"]),
        ("ledger_at", chronology["ledger_at"]),
        ("pre_at", chronology["pre_at"]),
    )
    if pre["prepared_at"] != chronology["pre_at"]:
        raise EvidenceSchemaError("promotion journal PRE prepared_at must equal chronology.pre_at")
    return {
        "schema_version": 2, "kind": "promotion_journal", "status": "PRE",
        "evidence_id": require_full_sha256(pre["evidence_id"], "promotion journal PRE evidence_id"),
        "prepared_at": _require_timestamp(pre["prepared_at"], "promotion journal PRE prepared_at"),
        "promotion_manifest": _require_exact_keys(
            pre["promotion_manifest"], {"path", "sha256"}, "promotion journal PRE manifest"),
        "catalog_receipt": _require_exact_keys(
            pre["catalog_receipt"], {"path", "sha256"}, "promotion journal PRE catalog receipt"),
        "candidate_set": normalized_candidates,
        "candidate_set_sha256": require_full_sha256(
            pre["candidate_set_sha256"], "promotion journal PRE candidate_set_sha256"),
        "chronology": dict(chronology),
    }


def validate_promotion_journal_post_v2(value: object, *, pre: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a durable POST outcome against its exact PRE intent."""
    keys = {
        "schema_version", "kind", "status", "evidence_id", "completed_at",
        "promotion_manifest", "catalog_receipt", "candidate_set_sha256",
        "inserted", "conflicts", "backup_ref", "db_pre_sha256", "db_post_sha256",
        "chronology",
    }
    post = _require_exact_keys(value, keys, "promotion journal POST")
    if (post["schema_version"], post["kind"], post["status"]) != (2, "promotion_journal", "POST"):
        raise EvidenceSchemaError("promotion journal POST must be strict v2")
    validated_pre = validate_promotion_journal_pre_v2(pre)
    if post["evidence_id"] != validated_pre["evidence_id"]:
        raise EvidenceSchemaError("promotion journal POST evidence_id does not match PRE")
    if post["promotion_manifest"] != validated_pre["promotion_manifest"]:
        raise EvidenceSchemaError("promotion journal POST manifest does not match PRE")
    if post["catalog_receipt"] != validated_pre["catalog_receipt"]:
        raise EvidenceSchemaError("promotion journal POST catalog receipt does not match PRE")
    if post["candidate_set_sha256"] != validated_pre["candidate_set_sha256"]:
        raise EvidenceSchemaError("promotion journal POST candidate set does not match PRE")
    chronology = _require_exact_keys(
        post["chronology"],
        {"sealed_at", "issued_at", "consumed_at", "ledger_at", "pre_at", "post_at"},
        "promotion journal POST chronology",
    )
    if {key: chronology[key] for key in validated_pre["chronology"]} != validated_pre["chronology"]:
        raise EvidenceSchemaError("promotion journal POST chronology does not preserve PRE")
    require_timestamp_order(
        ("sealed_at", chronology["sealed_at"]),
        ("issued_at", chronology["issued_at"]),
        ("consumed_at", chronology["consumed_at"]),
        ("ledger_at", chronology["ledger_at"]),
        ("pre_at", chronology["pre_at"]),
        ("post_at", chronology["post_at"]),
    )
    if post["completed_at"] != chronology["post_at"]:
        raise EvidenceSchemaError("promotion journal POST completed_at must equal chronology.post_at")
    if not isinstance(post["inserted"], list) or not isinstance(post["conflicts"], list):
        raise EvidenceSchemaError("promotion journal POST outcomes must be lists")
    expected = {candidate["name"]: candidate for candidate in validated_pre["candidate_set"]}
    accounted: set[str] = set()
    for index, item in enumerate(post["inserted"]):
        item = _require_exact_keys(
            item, {"name", "tables", "buy_sha256", "sell_sha256", "meta"},
            f"promotion journal POST inserted[{index}]",
        )
        candidate = expected.get(item["name"])
        if (candidate is None or item["tables"] != ["stockbuy", "stocksell"]
                or item["buy_sha256"] != candidate["buy_sha256"]
                or item["sell_sha256"] != candidate["sell_sha256"]
                or item["name"] in accounted):
            raise EvidenceSchemaError("promotion journal POST inserted does not bind PRE candidate")
        accounted.add(item["name"])
    for index, item in enumerate(post["conflicts"]):
        item = _require_exact_keys(
            item, {"name", "reason", "tables"}, f"promotion journal POST conflicts[{index}]")
        if (item["name"] not in expected or item["name"] in accounted
                or item["reason"] != "name_exists"
                or item["tables"] != ["stockbuy", "stocksell"]):
            raise EvidenceSchemaError("promotion journal POST conflict does not bind PRE candidate")
        accounted.add(item["name"])
    if accounted != set(expected):
        raise EvidenceSchemaError("promotion journal POST must account for every PRE candidate")
    require_full_sha256(post["db_pre_sha256"], "promotion journal POST db_pre_sha256")
    require_full_sha256(post["db_post_sha256"], "promotion journal POST db_post_sha256")
    backup_ref = post["backup_ref"]
    if backup_ref is not None:
        _require_exact_keys(backup_ref, {"path", "sha256"}, "promotion journal POST backup_ref")
        require_full_sha256(backup_ref["sha256"], "promotion journal POST backup_ref.sha256")
        if not isinstance(backup_ref["path"], str) or not backup_ref["path"]:
            raise EvidenceSchemaError("promotion journal POST backup_ref.path must be non-empty")
    return dict(post)
