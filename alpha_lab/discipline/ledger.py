"""전역 n_trials 원장의 **단일 기입 API** (백로그 A1+A21 흡수).

원장 실물: `docs/research/condition_research/research_runs/alpha_restart_20260710/
n_trials_ledger.jsonl` — 1행 1시행, 스키마는 기존 전체 행과 왕복 호환
(키 순서 ts→series→window→trial_type→target→result→session,
json.dumps(ensure_ascii=False) 기본 구분자, 검증: 기존 53행 byte-identical 왕복).

설계 결정(백로그 중복 제거 기록 #2): **기입 경로는 프로그램 전체에서
append_trial 1개뿐이다.** A6 리포터(trials_report)는 소비 전용이고,
A21 헬퍼 역할(스키마 검증·known 창 오용 거부·fail-closed)은 본 API에
흡수됐다. 다른 곳에서 이 파일에 직접 쓰면 장부가 갈라진다.

규율: append-only(기존 행 수정·삭제 금지), 현재시각은 호출자가 ts로 주입
(내부 datetime.now() 금지 — registry.py 관례), known 창 접촉 행은
known_ok=True 명시 없이는 거부(fail-closed, 원장 §1 veto 전용).
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

from alpha_lab.discipline import windows
from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    build_evidence_identity,
    require_full_sha256,
    require_timestamp_order,
    sha256_canonical,
    validate_gate_receipt,
    validate_gate_usage,
    validate_measurement_bindings,
)

_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_PATH = (
    _ROOT
    / "docs"
    / "research"
    / "condition_research"
    / "research_runs"
    / "alpha_restart_20260710"
    / "n_trials_ledger.jsonl"
)

# 원장 규약 §3.3 스키마 — 순서까지 계약이다(기존 행 왕복 호환).
REQUIRED_KEYS: tuple[str, ...] = (
    "ts",
    "series",
    "window",
    "trial_type",
    "target",
    "result",
    "session",
)
V2_REQUIRED_KEYS = REQUIRED_KEYS + ("schema_version", "evidence_id", "evidence")

# 원장 규약 §3.1 — 시행 유형 a/b/c. type-d 신설은 규약 개정(원장 §5)으로만.
ALLOWED_TRIAL_PREFIXES: tuple[str, ...] = ("a", "b", "c")


class LedgerSchemaError(Exception):
    """원장 스키마 위반(필수 키·형식·파싱 불가) — fail-closed 거부."""


def _serialize(record: dict) -> str:
    """Serialize v1 byte-compatibly and v2 with its appended contract keys."""
    if record.get("schema_version", 1) in (None, 1):
        _validate_v1_record(record)
        ordered = {key: record[key] for key in REQUIRED_KEYS}
    elif record.get("schema_version") == 2:
        _validate_v2_record(record)
        ordered = {key: record[key] for key in V2_REQUIRED_KEYS}
    else:
        raise LedgerSchemaError(f"unsupported ledger schema_version: {record.get('schema_version')!r}")
    return json.dumps(ordered, ensure_ascii=False)


def _validate_schema(record: dict) -> None:
    """필수 7키가 전부 비어 있지 않은 문자열인지, ts·trial_type 형식 검증."""
    for key in REQUIRED_KEYS:
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LedgerSchemaError(
                f"필수 키 '{key}'가 비어 있거나 문자열이 아닙니다: {value!r}"
            )
    try:
        dt.datetime.fromisoformat(record["ts"])
    except ValueError as exc:
        raise LedgerSchemaError(
            f"ts는 ISO 형식이어야 합니다: {record['ts']!r} ({exc})"
        ) from exc
    prefix = record["trial_type"][:1].lower()
    if prefix not in ALLOWED_TRIAL_PREFIXES:
        raise LedgerSchemaError(
            f"trial_type은 a/b/c로 시작해야 합니다(예: 'b(오프라인 봉인 판정)'). "
            f"type-d 등 신설은 원장 §5 규약 개정으로만: {record['trial_type']!r}"
        )
def _validate_v1_record(record: object) -> None:
    if not isinstance(record, dict) or set(record) != set(REQUIRED_KEYS):
        raise LedgerSchemaError("필수 키 누락 또는 추가 키 존재: v1 ledger row must contain exactly the seven required keys")
    _validate_schema(record)
def _validate_v2_record(record: dict) -> None:
    if set(record) != set(V2_REQUIRED_KEYS):
        raise LedgerSchemaError(f"v2 ledger row has invalid keys: {sorted(record)!r}")
    _validate_schema(record)
    if record["schema_version"] != 2:
        raise LedgerSchemaError("v2 ledger row schema_version must be exactly 2")
    try:
        evidence_id = require_full_sha256(record["evidence_id"], "evidence_id")
    except EvidenceSchemaError as exc:
        raise LedgerSchemaError(str(exc)) from exc
    evidence = record["evidence"]
    identity_keys = {
        "prereg_sha256", "seal_manifest_sha256", "code_manifest_sha256",
        "gate_receipt_id", "gate_receipt_sha256", "gate_usage_sha256",
        "input_artifacts", "result_artifacts", "candidate_set", "candidate_set_sha256",
        "negative_or_kill",
    }
    if not isinstance(evidence, dict) or set(evidence) != identity_keys:
        raise LedgerSchemaError("v2 ledger evidence has invalid keys")
    try:
        for key in ("prereg_sha256", "seal_manifest_sha256", "code_manifest_sha256", "gate_receipt_id", "gate_receipt_sha256", "gate_usage_sha256", "candidate_set_sha256"):
            require_full_sha256(evidence[key], f"evidence.{key}")
        inputs, results, candidates, candidate_hash = validate_measurement_bindings(
            input_artifacts=evidence["input_artifacts"],
            result_artifacts=evidence["result_artifacts"],
            candidate_set=evidence["candidate_set"],
            negative_or_kill=evidence["negative_or_kill"],
            repo_root=_ROOT,
            verify_files=False,
        )
        if inputs != evidence["input_artifacts"] or results != evidence["result_artifacts"] or candidates != evidence["candidate_set"] or candidate_hash != evidence["candidate_set_sha256"]:
            raise LedgerSchemaError("v2 ledger measurement bindings are not canonical")
        if evidence_id != sha256_canonical(evidence):
            raise LedgerSchemaError("v2 ledger evidence_id does not match evidence")
    except EvidenceSchemaError as exc:
        raise LedgerSchemaError(str(exc)) from exc


def _append_record(target_path: Path, record: dict) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    line = _serialize(record)
    eol, prefix = b"\n", b""
    if target_path.exists():
        existing = target_path.read_bytes()
        if b"\r\n" in existing:
            eol = b"\r\n"
        if existing and not existing.endswith(b"\n"):
            prefix = eol
    with open(target_path, "ab") as handle:
        handle.write(prefix + line.encode("utf-8") + eol)


def _validate_append_fields(record: dict, known_ok: bool) -> None:
    _validate_schema(record)
    contact = _known_contact_zones(record["window"], record["series"])
    if contact and not known_ok:
        raise windows.WindowViolation(
            f"known 창 접촉 기입 거부(fail-closed): window={record['window']!r} 이(가) "
            f"{sorted(contact)} 에 접촉합니다. veto/감사 기록이 맞으면 "
            f'known_ok=True를 명시하십시오. 원장 §1: "{windows.LEDGER_QUOTE_KNOWN}"'
        )


def _known_contact_zones(window: str, series: str) -> set[str]:
    """window 문자열의 날짜 토큰에서 known 접촉 창 집합을 계산한다.

    날짜 토큰이 하나도 없으면 파싱 불가로 fail-closed 거부한다
    (A21 채택 조건: 파싱 불가 시 기본 거부).
    """
    tokens = windows.extract_date_tokens(window)
    if not tokens:
        raise LedgerSchemaError(
            f"window에서 날짜 토큰을 찾지 못했습니다(fail-closed 거부). "
            f"창-지위 원장 §3.3 형식(예: '2022-03-23~2023-12-31(발견 가용)')으로 "
            f"기입하십시오: {window!r}"
        )
    zones: set[str] = set()
    for token in tokens:
        zones |= windows.window_zones(token["start"], token["end"])
    contact: set[str] = set()
    if "KNOWN" in zones:
        contact.add("KNOWN")
    if "NONE" in zones:
        contact.add("NONE")
    if "CONDITIONAL_2024" in zones and windows.series_2024_is_known(series):
        contact.add("CONDITIONAL_2024(계열 known)")
    return contact


def append_trial(
    *,
    ts: str,
    series: str,
    window: str,
    trial_type: str,
    target: str,
    result: str,
    session: str,
    path=None,
    known_ok: bool = False,
) -> dict:
    """전역 n_trials 원장에 시행 1행을 append한다 — 유일한 기입 경로.

    known 창(2025-01-01~2026-02-27·부재 창·계열-known 2024) 접촉 window는
    known_ok=True를 명시해야만 기록된다(veto/감사 기록 용도 — 원장 §1).
    반환: 기록된 레코드 사본(dict).
    """
    record = {
        "ts": ts,
        "series": series,
        "window": window,
        "trial_type": trial_type,
        "target": target,
        "result": result,
        "session": session,
    }
    _validate_append_fields(record, known_ok)
    target_path = Path(path) if path is not None else DEFAULT_LEDGER_PATH
    _append_record(target_path, record)
    return dict(record)
def append_trial_v2(
    *,
    ts: str,
    series: str,
    window: str,
    trial_type: str,
    target: str,
    result: str,
    session: str,
    repo_root: Path | str,
    gate_receipt_path: Path | str,
    gate_usage_path: Path | str,
    input_artifacts: list[dict[str, str]],
    result_artifacts: list[dict[str, str]],
    candidate_set: list[dict[str, str]],
    negative_or_kill: bool = False,
    path: Path | str | None = None,
    known_ok: bool = False,
) -> dict:
    """Append a v2 evidence-bound trial after validating its immutable claim."""
    root = Path(repo_root).resolve()
    receipt_file = Path(gate_receipt_path).resolve()
    usage_file = Path(gate_usage_path).resolve()
    try:
        receipt_value = json.loads(receipt_file.read_text(encoding="utf-8"))
        usage_value = json.loads(usage_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerSchemaError(f"v2 gate receipt or usage cannot be read: {exc}") from exc
    try:
        receipt = validate_gate_receipt(receipt_value, repo_root=root)
        receipt_id = require_full_sha256(receipt["receipt_id"], "receipt_id")
        if receipt_file != root / "receipts" / f"{receipt_id}.json":
            raise EvidenceSchemaError("gate_receipt_path is not the canonical receipt path")
        if usage_file != root / "claims" / f"{receipt_id}.json":
            raise EvidenceSchemaError("gate_usage_path is not the canonical claim path")
        usage = validate_gate_usage(usage_value, receipt=receipt)
        evidence_id, evidence = build_evidence_identity(
            receipt,
            usage,
            input_artifacts=input_artifacts,
            result_artifacts=result_artifacts,
            candidate_set=candidate_set,
            negative_or_kill=negative_or_kill,
            repo_root=root,
        )
    except EvidenceSchemaError as exc:
        raise LedgerSchemaError(f"invalid v2 evidence chain: {exc}") from exc
    try:
        require_timestamp_order(
            ("sealed_at", json.loads(
                (root / Path(*receipt["seal_manifest"]["path"].split("/"))).read_text(
                    encoding="utf-8"))["sealed_at"]),
            ("issued_at", receipt["issued_at"]),
            ("consumed_at", usage["consumed_at"]),
            ("ledger.ts", ts),
        )
    except (OSError, json.JSONDecodeError, EvidenceSchemaError) as exc:
        raise LedgerSchemaError(f"invalid v2 evidence chronology: {exc}") from exc
    record = {
        "ts": ts,
        "series": series,
        "window": window,
        "trial_type": trial_type,
        "target": target,
        "result": result,
        "session": session,
        "schema_version": 2,
        "evidence_id": evidence_id,
        "evidence": evidence,
    }
    _validate_append_fields(record, known_ok)
    _validate_v2_record(record)
    target_path = Path(path) if path is not None else DEFAULT_LEDGER_PATH
    _append_record(target_path, record)
    return dict(record)




def read_all(path=None) -> list[dict]:
    """원장 전체를 파싱해 레코드 리스트로 반환한다(없으면 빈 리스트).

    파싱 불가 행·필수 키 누락 행은 행 번호와 함께 LedgerSchemaError
    (fail-closed — 조용히 건너뛰지 않는다).
    """
    target = Path(path) if path is not None else DEFAULT_LEDGER_PATH
    if not target.exists():
        return []
    entries: list[dict] = []
    text = target.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LedgerSchemaError(
                f"원장 {lineno}행 JSON 파싱 불가(fail-closed): {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise LedgerSchemaError(f"원장 {lineno}행 객체가 아닙니다")
        if record.get("schema_version", 1) == 2:
            try:
                _validate_v2_record(record)
            except LedgerSchemaError as exc:
                raise LedgerSchemaError(f"원장 {lineno}행 v2 스키마 위반: {exc}") from exc
        elif record.get("schema_version", 1) in (None, 1):
            try:
                _validate_v1_record(record)
            except LedgerSchemaError as exc:
                raise LedgerSchemaError(f"원장 {lineno}행 v1 스키마 위반: {exc}") from exc
        else:
            raise LedgerSchemaError(
                f"원장 {lineno}행 지원하지 않는 schema_version: {record.get('schema_version')!r}"
            )
        entries.append(record)
    return entries


def sqrt_2_ln(n: int) -> float:
    """sqrt(2·ln N) — 무효 후보 기대 최대 성과 스케일(원장 §3). N<=1이면 0.0."""
    if n <= 1:
        return 0.0
    return math.sqrt(2.0 * math.log(n))


def aggregate(path=None) -> dict:
    """계열별 누계·전역 누계와 sqrt(2·ln N) 병기값을 집계한다(읽기 전용).

    반환 키: total / sqrt_2_ln_total / known_window_contacts /
    window_unparsed / by_series({계열: {n, sqrt_2_ln_n}}) / by_trial_type.
    """
    entries = read_all(path)
    series_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    known_contacts = 0
    unparsed = 0
    for entry in entries:
        series = entry["series"]
        series_counts[series] = series_counts.get(series, 0) + 1
        prefix = str(entry["trial_type"])[:1].lower()
        type_counts[prefix] = type_counts.get(prefix, 0) + 1
        try:
            if _known_contact_zones(entry["window"], series):
                known_contacts += 1
        except (LedgerSchemaError, ValueError):
            unparsed += 1  # 과거 행 집계는 관대하게 — 계수만 하고 계속
    total = len(entries)
    return {
        "total": total,
        "sqrt_2_ln_total": sqrt_2_ln(total),
        "known_window_contacts": known_contacts,
        "window_unparsed": unparsed,
        "by_series": {
            series: {"n": count, "sqrt_2_ln_n": sqrt_2_ln(count)}
            for series, count in sorted(series_counts.items())
        },
        "by_trial_type": dict(sorted(type_counts.items())),
    }
