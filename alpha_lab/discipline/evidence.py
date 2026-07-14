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


def _require_timestamp(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceSchemaError(f"{field} must be a timezone-aware ISO-8601 timestamp")
    return value


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
        candidate = _require_exact_keys(item, {"name", "sha256"}, f"candidate_set[{index}]")
        name = candidate["name"]
        if not isinstance(name, str) or not name.strip():
            raise EvidenceSchemaError(f"candidate_set[{index}].name must be non-empty")
        candidates.append(
            {"name": name, "sha256": require_full_sha256(candidate["sha256"], f"candidate_set[{index}].sha256")}
        )
    names = [candidate["name"] for candidate in candidates]
    if names != sorted(names) or len(names) != len(set(names)):
        raise EvidenceSchemaError("candidate_set names must be sorted and unique")
    if not isinstance(negative_or_kill, bool):
        raise EvidenceSchemaError("negative_or_kill must be boolean")
    if not candidates and not negative_or_kill:
        raise EvidenceSchemaError("candidate_set may be empty only for a negative_or_kill measurement")
    return inputs, results, candidates, sha256_canonical(candidates)


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
    if dt.datetime.fromisoformat(consumed_at.replace("Z", "+00:00")) < dt.datetime.fromisoformat(issued_at.replace("Z", "+00:00")):
        raise EvidenceSchemaError("consumed_at must not precede receipt issued_at")
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
