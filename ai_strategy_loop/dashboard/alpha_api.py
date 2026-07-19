"""alpha_lab 연구 산출물 read-only 대시보드 라우터 (/api/alpha/*).

데이터 루트: docs/research/condition_research/research_runs/alpha_lab_20260705
(환경변수 ALPHA_LAB_RUN_DIR로 재지정 — 테스트 주입용). 요청 시점마다 env를
다시 읽으므로 프로세스 재시작 없이 주입 가능하다.

계약: 파일이 없거나 깨져도 항상 HTTP 200 + {"available": false[, "error"]}.
이 모듈은 run dir의 어떤 파일도 생성/수정하지 않는다(완전 read-only).
alpha_lab 패키지에 의존하지 않고 영수증 파일만 읽는다 — 대시보드가
research-only 패키지 존재 여부와 무관하게 동작하도록 결합을 끊는다.

영수증 파일 계약(생산 레인과 공유):
  - preregistration_v1.json / preregistration_v1.sha256 (sha hex 사이드카)
  - n_trials_ledger.jsonl  : {"ts","program","batch","n","meta"} JSONL
  - dataset_build_receipt.json → GET /dataset 의 receipt 원문
  - mining_report.json     : {"rules":[...], "n_discovered"?, "n_fdr_survived"?}
  - translation_receipt.json: {"translations":[{"rule_id",...}], "n_translated"?}
  - event_cells_report.json → GET /events 의 report 원문
  - registration_receipt.json / engine_check_receipt.json / rho_gate_verdict.json
    → GET /funnel 후반 3단계(없으면 0)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Final

from fastapi import APIRouter

logger = logging.getLogger(__name__)

alpha_router = APIRouter(prefix="/api/alpha", tags=["alpha"])

_ENV_RUN_DIR: Final[str] = "ALPHA_LAB_RUN_DIR"
_DEFAULT_RUN_DIR_REL: Final[str] = (
    "docs/research/condition_research/research_runs/alpha_lab_20260705"
)
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

_PREREG_FILE: Final[str] = "preregistration_v1.json"
_PREREG_SHA_FILE: Final[str] = "preregistration_v1.sha256"
_LEDGER_FILE: Final[str] = "n_trials_ledger.jsonl"
_LEDGER_PROGRAMS: Final[tuple[str, ...]] = ("P1", "P2", "P3", "P5")

# stage 추론: 파이프라인 순서의 (stage 이름, 존재해야 할 파일). 뒤에서부터
# 가장 먼저 존재하는 파일의 stage를 채택한다. 아무것도 없으면 "idle".
_STAGE_LADDER: Final[tuple[tuple[str, str], ...]] = (
    ("sealed", _PREREG_FILE),
    ("dataset_built", "dataset_build_receipt.json"),
    ("rules_mined", "mining_report.json"),
    ("rules_translated", "translation_receipt.json"),
    ("events_analyzed", "event_cells_report.json"),
    ("registered", "rho_gate_registration_receipt.json"),
    ("engine_confirmed", "rho_gate_engine_runs.json"),
    ("rho_gate_verdict", "rho_gate_verdict.json"),
    ("retrial_finalized", "rho_retrial_verdict.json"),
)

# 등록/판정 authoritative 영수증(재판정 우선, 없으면 게이트) — §4.1 실제 파일명.
_REGISTRATION_FILES: Final[tuple[str, ...]] = (
    "rho_retrial_registration_receipt.json",
    "rho_gate_registration_receipt.json",
)
_VERDICT_FILES: Final[tuple[str, ...]] = (
    "rho_retrial_verdict.json",
    "rho_gate_verdict.json",
)

_RULE_LIST_KEYS: Final[tuple[str, ...]] = ("rules", "leaves", "leaderboard", "candidates")
_TRANSLATION_LIST_KEYS: Final[tuple[str, ...]] = ("translations", "rules", "entries")
_RULE_ID_KEYS: Final[tuple[str, ...]] = ("rule_id", "id", "name")


def _run_dir() -> Path:
    """요청 시점의 run dir — env 우선, 없으면 repo 기본 경로."""
    override = os.environ.get(_ENV_RUN_DIR, "").strip()
    if override:
        return Path(override)
    return _REPO_ROOT / _DEFAULT_RUN_DIR_REL


def _load_json(path: Path) -> tuple[Any, str | None]:
    """(payload, error). 파일 없음 → (None, None). 깨짐 → (None, 메시지)."""
    if not path.is_file():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("alpha_api: %s 읽기 실패: %s", path.name, exc)
        return None, f"{path.name}: {exc}"


# ── /status ──────────────────────────────────────────────────────────


def _sidecar_sha(run_dir: Path) -> str | None:
    """사이드카(.sha256) 내용의 첫 토큰(sha hex). 없으면 None."""
    path = run_dir / _PREREG_SHA_FILE
    if not path.is_file():
        return None
    try:
        tokens = path.read_text(encoding="utf-8").split()
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("alpha_api: sha 사이드카 읽기 실패: %s", exc)
        return None
    return tokens[0] if tokens else None


def _preregistration_status(run_dir: Path) -> dict[str, Any]:
    prereg_path = run_dir / _PREREG_FILE
    payload, error = _load_json(prereg_path)
    sidecar = _sidecar_sha(run_dir)
    sha_match: bool | None = None
    read_error: str | None = None
    if prereg_path.is_file() and sidecar is not None:
        # §1b(검토): 직접 read_bytes 를 soft-error 로 감싼다 — 권한/레이스 오류가 HTTP 500 으로
        #   전파되지 않게 하고, present-but-unreadable 을 sha_match=None + 오류로 노출한다.
        try:
            actual = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
            sha_match = actual == sidecar
        except OSError as exc:
            read_error = f"{_PREREG_FILE}: {exc}"
            logger.warning("alpha_api: prereg read 실패: %s", exc)
    valid_json = isinstance(payload, dict)
    # §4.3: 파일 존재만으로 sealed 판정 금지 — 정상 JSON + 사이드카 + SHA 일치 모두 요구.
    sealed = bool(prereg_path.is_file() and valid_json and sha_match is True)
    status: dict[str, Any] = {
        "present": prereg_path.is_file(),
        "available": prereg_path.is_file(),
        "valid_json": valid_json,
        "sidecar_present": sidecar is not None,
        "sealed": sealed,
        "sealed_date": payload.get("sealed_date") if isinstance(payload, dict) else None,
        "program": payload.get("program") if isinstance(payload, dict) else None,
        "sha256": sidecar,
        "sha256_match": sha_match,
    }
    if error:
        status["error"] = error
    elif read_error:
        status["error"] = read_error
    return status


def _ledger_status(run_dir: Path) -> dict[str, Any]:
    """원장 JSONL 단일 패스 합산 — 깨진 줄은 건너뛰되 개수로 보고한다."""
    path = run_dir / _LEDGER_FILE
    totals: dict[str, int] = {program: 0 for program in _LEDGER_PROGRAMS}
    entries = 0
    malformed = 0

    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            # §1b: 원장 직접 읽기 오류를 soft-error 로 노출(HTTP 500 금지·측정 0 위장 금지).
            logger.warning("alpha_api: ledger read 실패: %s", exc)
            return {
                "available": True, "totals": totals, "total": 0, "entries": 0,
                "malformed_lines": 0, "error": f"{_LEDGER_FILE}: {exc}",
            }
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            program = record.get("program") if isinstance(record, dict) else None
            n = record.get("n") if isinstance(record, dict) else None
            if not isinstance(program, str) or isinstance(n, bool) or not isinstance(n, int):
                malformed += 1
                continue
            totals[program] = totals.get(program, 0) + max(n, 0)
            entries += 1
    return {
        "available": path.is_file(),
        "totals": totals,
        "total": sum(totals.values()),
        "entries": entries,
        "malformed_lines": malformed,
    }


def _infer_stage(run_dir: Path) -> tuple[str, dict[str, bool]]:
    artifacts = {name: (run_dir / name).is_file() for _, name in _STAGE_LADDER}
    stage = "idle"
    for stage_name, file_name in _STAGE_LADDER:
        if artifacts[file_name]:
            stage = stage_name
    return stage, artifacts


@alpha_router.get("/status")
def alpha_status() -> dict[str, Any]:
    """사전등록 봉인 상태 + n_trials 원장 합계 + stage 추론."""
    run_dir = _run_dir()
    prereg = _preregistration_status(run_dir)
    stage, artifacts = _infer_stage(run_dir)
    return {
        "available": bool(prereg["available"]),
        "run_dir": run_dir.as_posix(),
        "preregistration": prereg,
        "ledger": _ledger_status(run_dir),
        "stage": stage,
        "artifacts": artifacts,
        "verdict": _authoritative_verdict(run_dir),
    }


# ── /dataset · /events (원문 passthrough) ───────────────────────────


def _passthrough(file_name: str, body_key: str) -> dict[str, Any]:
    payload, error = _load_json(_run_dir() / file_name)
    if payload is None:
        return {"available": False, "error": error} if error else {"available": False}
    return {"available": True, body_key: payload}


@alpha_router.get("/dataset")
def alpha_dataset() -> dict[str, Any]:
    """dataset_build_receipt.json 원문 — {"available", "receipt"}."""
    return _passthrough("dataset_build_receipt.json", "receipt")


@alpha_router.get("/events")
def alpha_events() -> dict[str, Any]:
    """event_cells_report.json 원문 — {"available", "report"}."""
    return _passthrough("event_cells_report.json", "report")


# ── /rules (mining + translation 병합 리더보드) ──────────────────────


def _extract_list(payload: Any, keys: tuple[str, ...]) -> tuple[list, dict[str, Any]]:
    """payload에서 규칙/번역 리스트와 나머지 메타를 분리한다."""
    if isinstance(payload, list):
        return list(payload), {}
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                meta = {k: v for k, v in payload.items() if k != key}
                return value, meta
        return [], dict(payload)
    return [], {}


def _entry_rule_id(entry: Any) -> str | None:
    if not isinstance(entry, dict):
        return None
    for key in _RULE_ID_KEYS:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _merge_translations(rules: list, translations: list) -> list:
    index = {
        rule_id: entry
        for entry in translations
        if (rule_id := _entry_rule_id(entry)) is not None
    }
    merged: list = []
    for rule in rules:
        if isinstance(rule, dict):
            merged.append({**rule, "translation": index.get(_entry_rule_id(rule))})
        else:
            merged.append(rule)
    return merged


@alpha_router.get("/rules")
def alpha_rules() -> dict[str, Any]:
    """규칙 리더보드 — mining_report + translation_receipt 병합."""
    run_dir = _run_dir()
    mining, mining_error = _load_json(run_dir / "mining_report.json")
    translation, translation_error = _load_json(run_dir / "translation_receipt.json")
    rules, mining_meta = _extract_list(mining, _RULE_LIST_KEYS)
    translations, translation_meta = _extract_list(translation, _TRANSLATION_LIST_KEYS)
    body: dict[str, Any] = {
        "available": mining is not None,
        "translation_available": translation is not None,
        "rules": _merge_translations(rules, translations),
        "mining_meta": mining_meta,
        "translation_meta": translation_meta,
    }
    error = mining_error or translation_error
    if error:
        body["error"] = error
    return body


# ── /funnel ──────────────────────────────────────────────────────────


def _count_in(payload: Any, count_keys: tuple[str, ...], list_keys: tuple[str, ...]) -> int:
    """명시 카운트 키 우선, 다음 리스트 길이, 마지막 bool 플래그 → int."""
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return 0
    for key in count_keys:
        value = payload.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return max(value, 0)
    for key in list_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    for key in count_keys + list_keys:
        value = payload.get(key)
        if isinstance(value, bool):
            return int(value)
    return 0


def _fdr_survived_count(mining: Any) -> int:
    # §4.4: authoritative n_fdr_survived 는 0 도 유효값 — truthiness 대신 타입 검사.
    if isinstance(mining, dict):
        explicit = mining.get("n_fdr_survived")
        if isinstance(explicit, int) and not isinstance(explicit, bool):
            return max(explicit, 0)
    rules, _ = _extract_list(mining, _RULE_LIST_KEYS)
    return sum(
        1
        for rule in rules
        if isinstance(rule, dict) and bool(rule.get("fdr_survived") or rule.get("fdr_pass"))
    )


def _registration_count(run_dir: Path) -> tuple[int, str | None]:
    """등재 수 — 재판정 우선, 없으면 게이트. registration.inserted 리스트 길이."""
    for name in _REGISTRATION_FILES:
        payload, _ = _load_json(run_dir / name)
        if isinstance(payload, dict):
            reg = payload.get("registration")
            if isinstance(reg, dict) and isinstance(reg.get("inserted"), list):
                return len(reg["inserted"]), name
    return 0, None


def _authoritative_verdict(run_dir: Path) -> dict[str, Any]:
    """권위 최종 판정 — 재판정 verdict 우선(final), 없으면 게이트 verdict.

    §4.1: 제네릭 이름(rho_gate_verdict) 고정 대신 실제 파일을 명시 선택하고,
    발견/FDR/번역 뒤 단계(등재·엔진·게이트)의 실제 결과를 노출한다.
    """
    for name in _VERDICT_FILES:
        payload, error = _load_json(run_dir / name)
        if isinstance(payload, dict):
            cov = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
            per_rule = payload.get("per_rule") if isinstance(payload.get("per_rule"), list) else []
            # §4(검토): measured_ok(측정 완료) 와 gate_passed(성능게이트 통과)는 다른 의미다.
            #   per_rule[].gate_passed(True) 만 실제 성능게이트 통과다(현 데이터는 전부 MDD 초과 → 0).
            gate_passed_n = sum(
                1 for r in per_rule if isinstance(r, dict) and r.get("gate_passed") is True
            )
            return {
                "available": True,
                "source": name,
                "final": bool(payload.get("final")),
                "status": payload.get("status"),
                "rho": payload.get("rho"),
                "verdict": payload.get("verdict"),
                "n_per_rule": len(per_rule),
                "performance_gate_passed": gate_passed_n,
                "coverage": {
                    "n_rules_sealed": cov.get("n_rules_sealed"),
                    "measured_ok": cov.get("measured_ok"),
                    "censored_timeout": cov.get("censored_timeout"),
                    "no_trades": cov.get("no_trades"),
                },
            }
        if error:
            # §1b: present-but-broken 영수증은 0/이전값으로 축소하지 않고 오류로 노출한다.
            return {"available": False, "source": name, "error": error}
    return {"available": False}


@alpha_router.get("/funnel")
def alpha_funnel() -> dict[str, Any]:
    """퍼널 6단계: 발견→FDR 생존→번역→등재→엔진 대상→성능게이트 통과. 판정·검열 동봉.

    §4(검토) 교정: gate_passed 는 measured_ok(측정 완료)가 아니라 per_rule[].gate_passed(True)
    로 집계한 **실제 성능게이트 통과 수**다(현 데이터는 전부 MDD>cap 로 0). measured_ok·censored
    는 별도 필드로 노출해 의미 혼합을 없앤다. 판정 카드의 rho(집합 상관 게이트)와도 구분한다.
    """
    run_dir = _run_dir()
    mining, _ = _load_json(run_dir / "mining_report.json")
    translation, _ = _load_json(run_dir / "translation_receipt.json")
    registered, reg_source = _registration_count(run_dir)
    verdict = _authoritative_verdict(run_dir)
    cov = verdict.get("coverage") if isinstance(verdict.get("coverage"), dict) else {}
    n_sealed = cov.get("n_rules_sealed")
    measured_ok = cov.get("measured_ok")
    censored = cov.get("censored_timeout")
    engine_checked = n_sealed if isinstance(n_sealed, int) else 0   # 봉인=엔진 대상 수
    perf_gate = verdict.get("performance_gate_passed")
    gate_passed = perf_gate if isinstance(perf_gate, int) else 0    # 개별 성능게이트 통과(실측 0)
    discovered = _count_in(mining, ("n_discovered",), _RULE_LIST_KEYS)
    return {
        "available": any(
            p is not None for p in (mining, translation)
        ) or registered > 0 or bool(verdict.get("available")),
        "discovered": discovered,
        "fdr_survived": _fdr_survived_count(mining),
        "translated": _count_in(translation, ("n_translated",), _TRANSLATION_LIST_KEYS),
        "registered": registered,
        "registration_source": reg_source,
        "engine_checked": engine_checked,
        "measured_ok": measured_ok if isinstance(measured_ok, int) else None,
        "censored": censored if isinstance(censored, int) else None,
        "gate_passed": gate_passed,
        "verdict": verdict,
    }
