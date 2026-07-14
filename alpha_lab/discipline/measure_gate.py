# -*- coding: utf-8 -*-
"""측정 배치 기동 전 게이트 (백로그 A7 / WBS v3 P1-3).

목적: O-1G 에서 실제 발생한 "측정 코드 3파일 untracked 상태로 배치 진행" 유형의
재발 차단 — 배치 기동 직전에 다음 3검사를 통과해야 pass 를 준다.

  검사 1) 봉인 문서가 커밋 이력에 존재한다(tracked + 커밋 1건 이상).
  검사 2) 측정 코드 파일 전부가 tracked 이고 clean 이다(미커밋 diff·untracked 불허).
          → "측정 시점 코드가 무엇이었나"를 항상 커밋 해시로 답변 가능해진다.
  검사 3) (봉인 sha 기록이 주어진 경우) 측정 스크립트의 현재 sha256 이 봉인 기록과
          일치한다. 기록 미제공 시 이 검사는 '미실시'로 명시 기록되며,
          --require-sha(fail-closed) 로 강제할 수 있다.

git 사용 규율: **이 모듈 안에서만** 읽기 전용 git subprocess 를 허용한다.
허용 서브커맨드는 rev-parse / log / status(--porcelain 강제) / ls-files 뿐이며,
화이트리스트를 코드로 강제해 쓰기 git 이 끼어들 수 없게 한다.

본 게이트는 어떤 파일도 수정하지 않는다(결과 json 저장은 CLI 의 --json-out 선택).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    require_full_sha256,
    require_timestamp_order,
    sha256_canonical,
    validate_gate_receipt,
    validate_gate_usage,
    validate_prereg_seal,
)

# 읽기 전용 git 서브커맨드 화이트리스트 — 이 밖은 코드상 실행 불가.
_ALLOWED_GIT = frozenset({"rev-parse", "log", "status", "ls-files"})
_GIT_TIMEOUT_SEC = 30

# 봉인 sha 축약 표기(예: 8ef01e0e…) 관행을 수용하는 최소 접두 길이.
_MIN_SHA_PREFIX = 8


def _run_git(repo_root: Path | str, *args: str) -> tuple[int, str]:
    """읽기 전용 git 실행. 화이트리스트 밖 서브커맨드는 즉시 거부한다."""
    if not args or args[0] not in _ALLOWED_GIT:
        raise ValueError(f"읽기 전용 git 만 허용(rev-parse/log/status/ls-files): {args!r}")
    if args[0] == "status" and "--porcelain" not in args:
        raise ValueError("status 는 --porcelain 전용으로만 허용한다")
    cmd = ("git", "-C", str(repo_root)) + args
    try:
        cp = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                            errors="replace", timeout=_GIT_TIMEOUT_SEC,
                            shell=False, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, f"git 실행 실패: {exc}"
    return cp.returncode, (cp.stdout or "").strip()


def _rel_posix(repo_root: Path | str, file_path: Path | str) -> str | None:
    """repo 루트 기준 posix 상대경로. repo 밖 파일이면 None."""
    try:
        rel = Path(file_path).resolve().relative_to(Path(repo_root).resolve())
    except ValueError:
        return None
    return rel.as_posix()


def file_sha256(path: Path | str) -> str:
    """파일 sha256 (소문자 hex, 청크 읽기)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ── 개별 검사 ────────────────────────────────────────────────────────────────
def check_repo(repo_root: Path | str) -> dict[str, Any]:
    """대상 경로가 git 작업 트리인지 확인한다."""
    rc, out = _run_git(repo_root, "rev-parse", "--is-inside-work-tree")
    ok = rc == 0 and out == "true"
    return {"pass": ok, "detail": out,
            "reason": "" if ok else f"git 작업 트리 아님/접근 실패: {out}"}


def _file_git_state(repo_root: Path | str, rel: str) -> dict[str, Any]:
    """단일 파일의 tracked/clean/최종 커밋 상태를 조회한다."""
    rc_ls, out_ls = _run_git(repo_root, "ls-files", "--", rel)
    tracked = rc_ls == 0 and out_ls != ""
    rc_st, out_st = _run_git(repo_root, "status", "--porcelain", "--", rel)
    clean = rc_st == 0 and out_st == ""
    rc_lg, out_lg = _run_git(repo_root, "log", "-1", "--format=%H", "--", rel)
    last_commit = out_lg if rc_lg == 0 and out_lg else ""
    return {"tracked": tracked, "clean": clean, "status": out_st,
            "last_commit": last_commit}


def check_sealed_doc(repo_root: Path | str, doc_path: Path | str) -> dict[str, Any]:
    """검사 1 — 봉인 문서 존재 + tracked + 커밋 이력 1건 이상."""
    rel = _rel_posix(repo_root, doc_path)
    if rel is None:
        return {"pass": False, "path": str(doc_path), "rel": "", "last_commit": "",
                "reason": "봉인 문서가 repo 밖에 있음"}
    if not Path(doc_path).exists():
        return {"pass": False, "path": str(doc_path), "rel": rel, "last_commit": "",
                "reason": "봉인 문서 파일이 없음"}
    st = _file_git_state(repo_root, rel)
    ok = st["tracked"] and st["last_commit"] != ""
    reason = "" if ok else "봉인 문서가 커밋 이력에 없음(untracked 또는 미커밋)"
    # 커밋 뒤 로컬 수정된(dirty) 봉인 문서는 '디스크 봉인 변조 → 게이트 통과 →
    # prereg-diff가 변조 기준으로 MATCH'라는 우회 조합을 성립시킨다(검증 실증).
    if ok and not st["clean"]:
        ok = False
        reason = f"봉인 문서에 미커밋 변경 있음 — 변조 의심(status: {st['status']})"
    return {"pass": ok, "path": str(doc_path), "rel": rel,
            "last_commit": st["last_commit"], "reason": reason}


def check_code_files(repo_root: Path | str,
                     code_files: tuple[str, ...]) -> dict[str, Any]:
    """검사 2 — 측정 코드 전부 tracked ∧ clean. 파일별 상태·최종 커밋 기록."""
    files: dict[str, Any] = {}
    reasons: list[str] = []
    for fp in code_files:
        rel = _rel_posix(repo_root, fp)
        if rel is None:
            files[str(fp)] = {"tracked": False, "clean": False, "status": "",
                              "last_commit": "", "reason": "repo 밖 파일"}
            reasons.append(f"{fp}: repo 밖 파일")
            continue
        if not Path(fp).exists():
            files[str(fp)] = {"tracked": False, "clean": False, "status": "",
                              "last_commit": "", "reason": "파일 없음"}
            reasons.append(f"{fp}: 파일 없음")
            continue
        st = _file_git_state(repo_root, rel)
        reason = ""
        if not st["tracked"]:
            reason = "untracked — 측정 코드가 커밋되지 않음(O-1G 재발 유형)"
        elif not st["clean"]:
            reason = f"미커밋 변경 있음(status: {st['status']})"
        if reason:
            reasons.append(f"{fp}: {reason}")
        files[str(fp)] = {**st, "reason": reason}
    return {"pass": not reasons, "files": files, "reasons": reasons}


def check_sha_seals(expected: Mapping[str, str],
                    repo_root: Path | str) -> dict[str, Any]:
    """검사 3 — 파일 sha256 ↔ 봉인 기록 대조(축약 기록은 접두 일치, 최소 8자)."""
    files: dict[str, Any] = {}
    reasons: list[str] = []
    for fp, want in expected.items():
        path = Path(fp)
        if not path.is_absolute():
            path = Path(repo_root) / path
        want_norm = want.strip().lower()
        if len(want_norm) < _MIN_SHA_PREFIX:
            files[str(fp)] = {"expected": want, "actual": "", "match": False,
                              "reason": f"봉인 sha 가 너무 짧음(<{_MIN_SHA_PREFIX}자)"}
            reasons.append(f"{fp}: 봉인 sha 형식 불량")
            continue
        if not path.exists():
            files[str(fp)] = {"expected": want, "actual": "", "match": False,
                              "reason": "파일 없음"}
            reasons.append(f"{fp}: 파일 없음")
            continue
        actual = file_sha256(path)
        match = actual.startswith(want_norm)
        if not match:
            reasons.append(f"{fp}: sha256 불일치(봉인 {want_norm[:12]}… ↔ 현재 {actual[:12]}…)")
        files[str(fp)] = {"expected": want_norm, "actual": actual, "match": match,
                          "reason": "" if match else "sha256 불일치"}
    return {"checked": bool(expected), "pass": not reasons,
            "files": files, "reasons": reasons}


# ── 종합 게이트 ──────────────────────────────────────────────────────────────
def run_gate(repo_root: Path | str, sealed_doc: Path | str,
             code_files: tuple[str, ...],
             expected_shas: Mapping[str, str] | None = None,
             require_sha: bool = False) -> dict[str, Any]:
    """3검사를 종합해 pass/fail + 한국어 사유 목록 json(dict) 을 만든다."""
    expected_shas = dict(expected_shas or {})
    reasons: list[str] = []
    repo = check_repo(repo_root)
    if not repo["pass"]:
        return _gate_result(repo_root, False, [repo["reason"]],
                            {"repo": repo, "sealed_doc": None,
                             "code_clean": None, "sha_seal": None})
    doc = check_sealed_doc(repo_root, sealed_doc)
    if not doc["pass"]:
        reasons.append(f"봉인 문서: {doc['reason']}")
    code = check_code_files(repo_root, code_files)
    reasons.extend(f"측정 코드: {r}" for r in code["reasons"])
    sha = check_sha_seals(expected_shas, repo_root)
    if sha["checked"]:
        reasons.extend(f"sha 봉인: {r}" for r in sha["reasons"])
    elif require_sha:
        reasons.append("sha 봉인: 기록 미제공(--require-sha 지정됨 — fail-closed)")
    gate_pass = not reasons
    checks = {"repo": repo, "sealed_doc": doc, "code_clean": code, "sha_seal": sha}
    return _gate_result(repo_root, gate_pass, reasons, checks)


def _gate_result(repo_root: Path | str, gate_pass: bool, reasons: list[str],
                 checks: dict[str, Any]) -> dict[str, Any]:
    """게이트 결과 dict 조립(불변 원칙 — 입력을 변형하지 않는다)."""
    return {
        "kind": "measure_gate_result",
        "generated": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "gate_pass": gate_pass,
        "reasons": list(reasons),
        "checks": checks,
        "verdict": "기동 허용" if gate_pass else "기동 거부 — 사유 해소 후 재실행",
    }


def _relative_file_ref(path: Path | str, repo_root: Path) -> dict[str, str]:
    try:
        resolved = Path(path).resolve()
        relative = resolved.relative_to(repo_root)
    except ValueError as exc:
        raise EvidenceSchemaError("path must be inside repo_root") from exc
    if not resolved.is_file():
        raise EvidenceSchemaError(f"file does not exist: {path}")
    return {"path": relative.as_posix(), "sha256": file_sha256(resolved)}


def _current_head(repo_root: Path) -> str:
    rc, head = _run_git(repo_root, "rev-parse", "HEAD")
    if rc != 0 or len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        raise EvidenceSchemaError("repository HEAD must be a lowercase 40-character git SHA")
    return head


def issue_gate_receipt_v2(
    repo_root: Path | str,
    seal_manifest_path: Path | str,
    *,
    issued_at: str,
    nonce: str,
) -> dict[str, Any]:
    """Issue an immutable v2 receipt for the complete sealed code manifest."""
    root = Path(repo_root).resolve()
    require_timestamp_order(("issued_at", issued_at))
    if not isinstance(nonce, str) or not nonce:
        raise EvidenceSchemaError("nonce must be non-empty")
    seal_file_ref = _relative_file_ref(seal_manifest_path, root)
    try:
        seal_value = json.loads(Path(seal_manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("seal manifest must be readable JSON") from exc
    seal_ref = {"path": seal_file_ref["path"], "sha256": sha256_canonical(seal_value)}
    seal = validate_prereg_seal(seal_value, repo_root=root, verify_files=True)
    prereg_path = root / Path(*Path(seal["sealed_doc"]["path"]).parts)
    code_paths = tuple(str(root / Path(*Path(item["path"]).parts))
                       for item in seal["code_manifest"])
    expected = {path: item["sha256"] for path, item in zip(code_paths, seal["code_manifest"])}
    gate = run_gate(root, prereg_path, code_paths, expected, require_sha=True)
    if not gate["gate_pass"]:
        raise EvidenceSchemaError("v2 gate failed: " + "; ".join(gate["reasons"]))
    head = _current_head(root)
    code_manifest_sha256 = sha256_canonical(seal["code_manifest"])
    receipt_id = sha256_canonical({
        "issued_at": issued_at,
        "nonce": nonce,
        "repo_head": head,
        "seal_manifest": seal_ref,
        "prereg": seal["sealed_doc"],
        "code_manifest_sha256": code_manifest_sha256,
    })
    receipt = {
        "schema_version": 2,
        "kind": "measure_gate_receipt",
        "status": "PASS",
        "receipt_id": receipt_id,
        "issued_at": issued_at,
        "nonce": nonce,
        "repo_head": head,
        "seal_manifest": seal_ref,
        "prereg": seal["sealed_doc"],
        "code_manifest_sha256": code_manifest_sha256,
        "code_manifest": seal["code_manifest"],
        "checks": gate["checks"],
    }
    validate_gate_receipt(receipt, repo_root=root)
    out = root / "receipts" / f"{receipt_id}.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except FileExistsError as exc:
        raise EvidenceSchemaError("canonical receipt path already exists") from exc
    return receipt


def claim_gate_receipt_v2(
    receipt_path: Path | str,
    *,
    repo_root: Path | str,
    consumer: str,
    consumed_at: str,
) -> dict[str, Any]:
    """Atomically claim a valid v2 receipt at its sole canonical claim path."""
    root = Path(repo_root).resolve()
    require_timestamp_order(("consumed_at", consumed_at))
    if not isinstance(consumer, str) or not consumer:
        raise EvidenceSchemaError("consumer must be non-empty")
    receipt_file = Path(receipt_path).resolve()
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("receipt must be readable JSON") from exc
    receipt = validate_gate_receipt(receipt, repo_root=root)
    receipt_id = require_full_sha256(receipt["receipt_id"], "receipt_id")
    expected_receipt_path = root / "receipts" / f"{receipt_id}.json"
    if receipt_file != expected_receipt_path:
        raise EvidenceSchemaError("receipt_path is not the canonical receipt path")
    if _current_head(root) != receipt["repo_head"]:
        raise EvidenceSchemaError("receipt repo_head does not match current HEAD")
    require_timestamp_order(
        ("issued_at", receipt["issued_at"]), ("consumed_at", consumed_at))
    claim_path = root / "claims" / f"{receipt_id}.json"
    usage = {
        "schema_version": 2,
        "kind": "measure_gate_usage",
        "issuer": {
            "receipt_id": receipt_id,
            "receipt_sha256": sha256_canonical(receipt),
            "issued_at": receipt["issued_at"],
            "repo_head": receipt["repo_head"],
        },
        "claim": {
            "receipt_id": receipt_id,
            "path": f"claims/{receipt_id}.json",
        },
        "consumer": consumer,
        "consumed_at": consumed_at,
    }
    validate_gate_usage(usage, receipt=receipt)
    try:
        claim_path.parent.mkdir(parents=True, exist_ok=True)
        with claim_path.open("x", encoding="utf-8") as handle:
            json.dump(usage, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except FileExistsError as exc:
        raise EvidenceSchemaError("gate receipt has already been claimed") from exc
    return usage




# ── CLI ──────────────────────────────────────────────────────────────────────
def _parse_expected(expect_args: list[str],
                    manifest_path: str | None) -> dict[str, str]:
    """--expect path=sha 반복 인자와 --manifest json 을 병합한다."""
    expected: dict[str, str] = {}
    if manifest_path:
        raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        mapping = raw.get("files", raw) if isinstance(raw, dict) else {}
        if not isinstance(mapping, dict):
            raise ValueError("매니페스트 형식 오류: {경로: sha256} dict 필요")
        expected.update({str(k): str(v) for k, v in mapping.items()})
    for item in expect_args:
        path, sep, sha = item.rpartition("=")
        if not sep or not path or not sha:
            raise ValueError(f"--expect 형식 오류(경로=sha256 필요): {item!r}")
        expected[path] = sha
    return expected


def main(argv: list[str] | None = None) -> int:
    """게이트 CLI. stdout 에 결과 json 만 출력. exit 0=pass / 1=fail / 2=오류."""
    parser = argparse.ArgumentParser(
        prog="measure_gate",
        description="측정 배치 기동 전 게이트(봉인 커밋·코드 clean·sha 봉인 검사)")
    default_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--repo-root", default=str(default_root),
                        help=f"git repo 루트(기본: {default_root})")
    parser.add_argument("--sealed-doc", help="봉인 사전등록 md 경로(v1)")
    parser.add_argument("--code", action="append", default=[],
                        help="측정 코드 파일(v1, 반복 지정)")
    parser.add_argument("--expect", action="append", default=[],
                        help="sha 봉인 대조: <경로>=<sha256> (v1, 반복 지정)")
    parser.add_argument("--manifest", default=None,
                        help="sha 봉인 매니페스트 json(v1)")
    parser.add_argument("--require-sha", action="store_true",
                        help="sha 봉인 기록 미제공 시에도 fail 처리(v1)")
    parser.add_argument("--json-out", default=None, help="결과 json 저장 경로(v1)")
    parser.add_argument("--seal-manifest", default=None, help="v2 prereg seal manifest")
    parser.add_argument("--issued-at", default=None, help="v2 receipt issue timestamp")
    parser.add_argument("--nonce", default=None, help="v2 non-empty run nonce")
    args = parser.parse_args(argv)
    if args.seal_manifest:
        if (args.sealed_doc or args.code or args.expect or args.manifest
                or args.require_sha or args.json_out):
            parser.error("--seal-manifest cannot be combined with v1 gate options")
        if not (args.issued_at and args.nonce):
            parser.error("--seal-manifest requires --issued-at and --nonce")
        try:
            receipt = issue_gate_receipt_v2(
                args.repo_root, args.seal_manifest,
                issued_at=args.issued_at, nonce=args.nonce)
        except (OSError, ValueError, EvidenceSchemaError) as exc:
            print(f"[measure-gate] v2 receipt issue failed: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(receipt, ensure_ascii=False, indent=1))
        return 0
    if not args.sealed_doc or not args.code:
        parser.error("--sealed-doc and at least one --code are required for v1")
    try:
        expected = _parse_expected(args.expect, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[measure-gate] 봉인 sha 기록 해석 실패: {exc}", file=sys.stderr)
        return 2
    result = run_gate(args.repo_root, args.sealed_doc, tuple(args.code),
                      expected, require_sha=args.require_sha)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    print(text)
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    return 0 if result["gate_pass"] else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # 파이프/구형 스트림이면 무시
        pass
    sys.exit(main())
