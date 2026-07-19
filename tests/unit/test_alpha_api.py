"""alpha_lab 대시보드 라우터(/api/alpha/*) 계약 테스트.

테스트 방식: create_app() 전체 기동은 무겁고(loop controller/bootstrap 체인)
이 레인 밖 상태에 의존하므로, 라우터 단독 FastAPI 앱 + TestClient로 5개
엔드포인트 계약을 검증하고, app.py 배선은 파일 문자열 검사로 확인한다
(기존 tests/unit/test_dashboard_route_parity.py 의 frontend 문자열 검사 관례).

데이터 주입: ALPHA_LAB_RUN_DIR 환경변수로 tmp run dir을 지정한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_strategy_loop.dashboard.alpha_api import alpha_router  # noqa: E402

APP_PY = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "app.py"


def _client(monkeypatch, run_dir: Path) -> TestClient:
    """라우터 단독 앱 — ALPHA_LAB_RUN_DIR로 tmp run dir 주입."""
    monkeypatch.setenv("ALPHA_LAB_RUN_DIR", str(run_dir))
    app = FastAPI()
    app.include_router(alpha_router)
    return TestClient(app)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _seal_preregistration(run_dir: Path) -> str:
    """견본 사전등록 봉인 + sha256 사이드카 작성. sha hex를 반환."""
    payload = {
        "program": "alpha_lab_v1",
        "sealed_date": "2026-07-05",
        "features": ["등락율", "체결강도"],
    }
    body = (json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "preregistration_v1.json").write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    (run_dir / "preregistration_v1.sha256").write_text(sha + "\n", encoding="utf-8")
    return sha


def _append_ledger(run_dir: Path, program: str, n: int) -> None:
    record = {"ts": "2026-07-05T09:00:00", "program": program, "batch": "b1", "n": n, "meta": None}
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / "n_trials_ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write(line)


# ── /api/alpha/status ────────────────────────────────────────────────


def test_alpha_status_empty_run_dir_reports_unavailable(monkeypatch, tmp_path: Path) -> None:
    """빈 run dir에서도 200 + available:false 스키마를 돌려준다."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/alpha/status")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["preregistration"]["available"] is False
    assert body["ledger"]["available"] is False
    assert body["ledger"]["totals"] == {"P1": 0, "P2": 0, "P3": 0, "P5": 0}
    assert body["ledger"]["total"] == 0
    assert body["stage"] == "idle"


def test_alpha_status_reports_seal_and_ledger_totals(monkeypatch, tmp_path: Path) -> None:
    """봉인 sha·sealed_date·프로그램별 n_trials 합계를 정확히 보고한다."""
    sha = _seal_preregistration(tmp_path)
    _append_ledger(tmp_path, "P1", 100)
    _append_ledger(tmp_path, "P1", 50)
    _append_ledger(tmp_path, "P2", 30)
    with open(tmp_path / "n_trials_ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write("not-json\n")
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/status").json()

    assert body["available"] is True
    prereg = body["preregistration"]
    assert prereg["available"] is True
    assert prereg["present"] is True
    assert prereg["valid_json"] is True
    assert prereg["sealed"] is True
    assert prereg["sealed_date"] == "2026-07-05"
    assert prereg["sha256"] == sha
    assert prereg["sha256_match"] is True
    ledger = body["ledger"]
    assert ledger["available"] is True
    assert ledger["totals"] == {"P1": 150, "P2": 30, "P3": 0, "P5": 0}
    assert ledger["total"] == 180
    assert ledger["entries"] == 3
    assert ledger["malformed_lines"] == 1
    assert body["stage"] == "sealed"


def test_alpha_status_present_but_sha_mismatch_is_not_sealed(monkeypatch, tmp_path: Path) -> None:
    """§4.3: 파일이 존재해도 SHA 불일치면 sealed=False, present=True 로 분리 표시한다."""
    _seal_preregistration(tmp_path)
    # 봉인 후 파일 바이트를 변조 → 사이드카 SHA와 불일치
    (tmp_path / "preregistration_v1.json").write_bytes(b'{"program": "tampered"}\n')
    client = _client(monkeypatch, tmp_path)

    prereg = client.get("/api/alpha/status").json()["preregistration"]
    assert prereg["present"] is True
    assert prereg["valid_json"] is True
    assert prereg["sha256_match"] is False
    assert prereg["sealed"] is False


def test_alpha_status_stage_progression(monkeypatch, tmp_path: Path) -> None:
    """영수증이 쌓일수록 stage가 파이프라인 순서대로 전진한다."""
    _seal_preregistration(tmp_path)
    client = _client(monkeypatch, tmp_path)

    _write_json(tmp_path / "dataset_build_receipt.json", {"days": 1})
    assert client.get("/api/alpha/status").json()["stage"] == "dataset_built"

    _write_json(tmp_path / "mining_report.json", {"rules": []})
    assert client.get("/api/alpha/status").json()["stage"] == "rules_mined"

    _write_json(tmp_path / "translation_receipt.json", {"translations": []})
    assert client.get("/api/alpha/status").json()["stage"] == "rules_translated"

    _write_json(tmp_path / "event_cells_report.json", {"cells": []})
    assert client.get("/api/alpha/status").json()["stage"] == "events_analyzed"


# ── /api/alpha/dataset ───────────────────────────────────────────────


def test_alpha_dataset_unavailable_then_passthrough(monkeypatch, tmp_path: Path) -> None:
    """영수증 없으면 available:false, 있으면 receipt 원문 그대로."""
    client = _client(monkeypatch, tmp_path)
    assert client.get("/api/alpha/dataset").json() == {"available": False}

    receipt = {"days": 3, "coverage": {"20240103": 62}, "label_pos_rate": {"h60": 0.04}}
    _write_json(tmp_path / "dataset_build_receipt.json", receipt)

    body = client.get("/api/alpha/dataset").json()
    assert body["available"] is True
    assert body["receipt"] == receipt


def test_alpha_dataset_invalid_json_reports_unavailable(monkeypatch, tmp_path: Path) -> None:
    """깨진 JSON 파일은 500이 아니라 available:false + error로 보고한다."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "dataset_build_receipt.json").write_text("{broken", encoding="utf-8")
    client = _client(monkeypatch, tmp_path)

    response = client.get("/api/alpha/dataset")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert "error" in body


# ── /api/alpha/rules ─────────────────────────────────────────────────


def test_alpha_rules_merges_translation_by_rule_id(monkeypatch, tmp_path: Path) -> None:
    """mining_report 규칙에 translation_receipt 항목을 rule_id로 붙인다."""
    _write_json(
        tmp_path / "mining_report.json",
        {
            "n_discovered": 2,
            "rules": [
                {"rule_id": "r1", "lift": 2.0, "fdr_survived": True},
                {"rule_id": "r2", "lift": 1.1, "fdr_survived": False},
            ],
        },
    )
    _write_json(
        tmp_path / "translation_receipt.json",
        {"translations": [{"rule_id": "r1", "expr": "등락율 > 3"}]},
    )
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/rules").json()

    assert body["available"] is True
    assert body["translation_available"] is True
    assert len(body["rules"]) == 2
    assert body["rules"][0]["rule_id"] == "r1"
    assert body["rules"][0]["translation"] == {"rule_id": "r1", "expr": "등락율 > 3"}
    assert body["rules"][1]["translation"] is None
    assert body["mining_meta"]["n_discovered"] == 2


def test_alpha_rules_without_translation_receipt(monkeypatch, tmp_path: Path) -> None:
    """번역 영수증이 없어도 규칙 리더보드는 제공한다."""
    _write_json(tmp_path / "mining_report.json", {"rules": [{"rule_id": "r1", "lift": 2.0}]})
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/rules").json()

    assert body["available"] is True
    assert body["translation_available"] is False
    assert body["rules"][0]["translation"] is None


def test_alpha_rules_unavailable_without_mining_report(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/rules").json()

    assert body["available"] is False
    assert body["rules"] == []


# ── /api/alpha/events ────────────────────────────────────────────────


def test_alpha_events_unavailable_then_passthrough(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    assert client.get("/api/alpha/events").json() == {"available": False}

    report = {"cells": [{"event": "VI해제", "stratum": "y2023", "ev": 0.002}]}
    _write_json(tmp_path / "event_cells_report.json", report)

    body = client.get("/api/alpha/events").json()
    assert body["available"] is True
    assert body["report"] == report


# ── /api/alpha/funnel ────────────────────────────────────────────────


def test_alpha_funnel_missing_receipts_all_zero(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/funnel").json()

    assert body["available"] is False
    for key in ("discovered", "fdr_survived", "translated", "registered", "engine_checked", "gate_passed"):
        assert body[key] == 0


def test_alpha_funnel_counts_registration_and_verdict(monkeypatch, tmp_path: Path) -> None:
    """§4.1: 등재=registration.inserted, 엔진/게이트=verdict.coverage, 판정 동봉."""
    _write_json(
        tmp_path / "mining_report.json",
        {"n_discovered": 80, "n_fdr_survived": 40, "rules": []},
    )
    _write_json(tmp_path / "translation_receipt.json", {"n_translated": 30, "translations": []})
    _write_json(
        tmp_path / "rho_gate_registration_receipt.json",
        {"registration": {"inserted": [{"name": "ALP_RM_01"}, {"name": "ALP_RM_02"}]}},
    )
    _write_json(
        tmp_path / "rho_retrial_verdict.json",
        {
            "final": True, "status": "finalized", "rho": 0.6687, "verdict": "본빌드 진행 권고",
            "coverage": {"n_rules_sealed": 10, "measured_ok": 8, "censored_timeout": 2, "no_trades": 0},
            # §4(검토): per_rule[].gate_passed 만 성능게이트 통과. 측정완료(8)와 구분(전부 MDD 초과 → 0).
            "per_rule": [
                {"name": f"R{i}", "gate_passed": False, "gate_reason": "mdd>cap"} for i in range(8)
            ] + [
                {"name": "R8", "gate_passed": None}, {"name": "R9", "gate_passed": None},
            ],
        },
    )
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/funnel").json()

    assert body["available"] is True
    assert body["discovered"] == 80
    assert body["fdr_survived"] == 40
    assert body["translated"] == 30
    assert body["registered"] == 2
    assert body["engine_checked"] == 10       # 봉인=엔진 대상
    assert body["measured_ok"] == 8           # 측정 완료(별도 필드)
    assert body["censored"] == 2
    assert body["gate_passed"] == 0           # §4 교정: 성능게이트 통과(per_rule)는 0
    verdict = body["verdict"]
    assert verdict["available"] is True and verdict["final"] is True
    assert verdict["source"] == "rho_retrial_verdict.json"
    assert verdict["verdict"] == "본빌드 진행 권고"
    assert verdict["performance_gate_passed"] == 0


def test_alpha_funnel_prefers_retrial_registration(monkeypatch, tmp_path: Path) -> None:
    """재판정 등록 영수증이 게이트 등록보다 우선한다."""
    _write_json(tmp_path / "mining_report.json", {"n_discovered": 1, "n_fdr_survived": 1})
    _write_json(
        tmp_path / "rho_gate_registration_receipt.json",
        {"registration": {"inserted": [{"name": "g1"}, {"name": "g2"}, {"name": "g3"}]}},
    )
    _write_json(
        tmp_path / "rho_retrial_registration_receipt.json",
        {"registration": {"inserted": [{"name": "r1"}]}},
    )
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/funnel").json()
    assert body["registered"] == 1
    assert body["registration_source"] == "rho_retrial_registration_receipt.json"


def test_alpha_funnel_fdr_survived_zero_is_kept(monkeypatch, tmp_path: Path) -> None:
    """§4.4: authoritative n_fdr_survived=0 을 rule-flag fallback(1)으로 덮지 않는다."""
    _write_json(
        tmp_path / "mining_report.json",
        {"n_discovered": 5, "n_fdr_survived": 0, "rules": [{"rule_id": "r1", "fdr_survived": True}]},
    )
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/funnel").json()
    assert body["fdr_survived"] == 0


def test_alpha_funnel_prefers_explicit_counts(monkeypatch, tmp_path: Path) -> None:
    """명시 n_* 카운트가 리스트 길이보다 우선한다."""
    _write_json(
        tmp_path / "mining_report.json",
        {"n_discovered": 10, "n_fdr_survived": 4, "rules": [{"rule_id": "r1"}]},
    )
    client = _client(monkeypatch, tmp_path)

    body = client.get("/api/alpha/funnel").json()

    assert body["discovered"] == 10
    assert body["fdr_survived"] == 4


# ── 읽기 전용 보증 + app.py 배선 ─────────────────────────────────────


def test_alpha_endpoints_do_not_write_run_dir(monkeypatch, tmp_path: Path) -> None:
    """5개 엔드포인트 호출 전후 run dir 파일 집합이 불변이다."""
    _seal_preregistration(tmp_path)
    _append_ledger(tmp_path, "P1", 10)
    _write_json(tmp_path / "dataset_build_receipt.json", {"days": 1})
    client = _client(monkeypatch, tmp_path)
    before = sorted(str(p) for p in tmp_path.rglob("*"))

    for endpoint in ("status", "dataset", "rules", "events", "funnel"):
        assert client.get(f"/api/alpha/{endpoint}").status_code == 200

    after = sorted(str(p) for p in tmp_path.rglob("*"))
    assert before == after


def test_app_py_wires_alpha_router() -> None:
    """app.py가 alpha_router를 import하고 include_router로 배선한다."""
    source = APP_PY.read_text(encoding="utf-8")

    assert "from ai_strategy_loop.dashboard.alpha_api import alpha_router" in source
    assert "app.include_router(alpha_router)" in source
