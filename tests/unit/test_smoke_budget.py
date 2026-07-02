"""셀 단위 스모크 예산 + 부활 레지스트리 (T1.5) 단위 테스트.

검증:
  - 예산 경계: -2,000,000 정확히 → no_go (규약 3항 '<='), 그보다 크면 go.
  - 창 비례 축소: 45일 → -1,000,000, 9일 → -200,000; 기준(90일) 초과 창은
    확대 없이 기준 예산 유지 (축소 전용).
  - advisory 라벨 원칙: advisory_only/forbidden_uses 표식 + docstring 명시.
  - n_trials 정직성: attempt 필드 (counted_as_trial/run_id/trades).
  - fail-closed: 비유한수 profit → no_go.
  - 부활 레지스트리: JSONL append 왕복, 전수 재검증 대상 추출(선별 없음,
    같은 데이터 재선택 금지 경계), 날짜 형식 정규화.
  - CLI smoke-plan: 셀별 집계 + 배치 계획 JSON (백테스트 실행은 범위 밖).

실DB/백테 미사용: 순수 함수 + tmp_path 파일만 쓴다.
"""

import json
import math
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.seeds.revival_registry import (  # noqa: E402
    REGISTRY_SCHEMA,
    REVALIDATION_POLICY,
    load_registry,
    pending_revalidation,
    register_rejected,
)
from ai_strategy_loop.seeds.smoke_budget import (  # noqa: E402
    SMOKE_BASE_BUDGET_KRW,
    SMOKE_BASE_WINDOW_DAYS,
    SMOKE_FORBIDDEN_USES,
    SMOKE_GO,
    SMOKE_NO_GO,
    SMOKE_VERDICT_SCHEMA,
    evaluate_smoke_budget,
    smoke_budget_threshold,
)


# --------------------------------------------------------------------------
# 예산 경계 (-2,000,000 / '<=' 포함)
# --------------------------------------------------------------------------
def test_budget_boundary_at_minus_two_million():
    """기준 창(90일): -2,000,000 정확히 → no_go, -1,999,999 → go."""
    assert SMOKE_BASE_BUDGET_KRW == -2_000_000.0
    assert SMOKE_BASE_WINDOW_DAYS == 90  # 2025Q1 (20250101~20250331)
    no_go = evaluate_smoke_budget({"profit": -2_000_000}, lane="tick", window_days=90)
    assert no_go["verdict"] == SMOKE_NO_GO
    assert no_go["budget_threshold"] == -2_000_000.0
    go = evaluate_smoke_budget({"profit": -1_999_999}, lane="tick", window_days=90)
    assert go["verdict"] == SMOKE_GO
    assert evaluate_smoke_budget({"profit": 0}, lane="tick",
                                 window_days=90)["verdict"] == SMOKE_GO


def test_window_proportional_reduction():
    """창 비례 축소: 45일 → -1,000,000 경계, 9일 → -200,000. 확대는 없음."""
    assert smoke_budget_threshold(45) == -1_000_000.0
    assert smoke_budget_threshold(9) == -200_000.0
    # 기준(90일) 이상 창: 예산 유지 (축소 전용 — 확대 금지).
    assert smoke_budget_threshold(90) == -2_000_000.0
    assert smoke_budget_threshold(180) == -2_000_000.0
    # 45일 창의 경계 판정.
    v = evaluate_smoke_budget({"profit": -1_000_000}, lane="tick", window_days=45)
    assert v["verdict"] == SMOKE_NO_GO and v["budget_threshold"] == -1_000_000.0
    v = evaluate_smoke_budget({"profit": -999_999}, lane="tick", window_days=45)
    assert v["verdict"] == SMOKE_GO


def test_invalid_inputs_rejected():
    """비양수 창/미지 lane/profit 누락/비 Mapping 은 거부 (시스템 경계 검증)."""
    with pytest.raises(ValueError):
        smoke_budget_threshold(0)
    with pytest.raises(ValueError):
        smoke_budget_threshold(30, base_budget=2_000_000.0)  # 예산은 음수여야
    with pytest.raises(ValueError):
        evaluate_smoke_budget({"profit": 1.0}, lane="hour", window_days=90)
    with pytest.raises(ValueError):
        evaluate_smoke_budget({"trades": 10}, lane="tick", window_days=90)  # profit 없음
    with pytest.raises(ValueError):
        evaluate_smoke_budget({"profit": "abc"}, lane="tick", window_days=90)
    with pytest.raises(ValueError):
        evaluate_smoke_budget([1, 2], lane="tick", window_days=90)  # Mapping 아님


def test_non_finite_profit_fail_closed():
    """NaN/inf profit → no_go (fail-closed)."""
    for bad in (math.nan, math.inf, -math.inf):
        v = evaluate_smoke_budget({"profit": bad}, lane="tick", window_days=90)
        assert v["verdict"] == SMOKE_NO_GO
        assert v["reason"] == "non_finite_profit"


# --------------------------------------------------------------------------
# advisory 라벨 원칙 + n_trials 정직성
# --------------------------------------------------------------------------
def test_advisory_label_principle_markers():
    """판정은 자원 배분용 advisory — 선택·동결 사용 금지 표식이 payload 에 있다."""
    v = evaluate_smoke_budget({"cell_id": "tick_0900_small_low", "profit": 100.0},
                              lane="tick", window_days=90)
    assert v["schema"] == SMOKE_VERDICT_SCHEMA
    assert v["advisory_only"] is True
    assert v["forbidden_uses"] == list(SMOKE_FORBIDDEN_USES) == ["selection", "freeze"]
    assert v["verdict"] in (SMOKE_GO, SMOKE_NO_GO)
    assert "선택" in v["policy_note"] and "동결" in v["policy_note"]
    # advisory 원칙은 docstring 에도 명시돼야 한다 (임무 계약).
    doc = evaluate_smoke_budget.__doc__ or ""
    assert "advisory" in doc and "선택" in doc and "동결" in doc


def test_attempt_fields_for_n_trials_accounting():
    """스모크도 trial — attempt 기록 필드(run_id/trades/counted_as_trial)."""
    v = evaluate_smoke_budget(
        {"cell_id": "tick_0900_small_low", "profit": -3_000_000,
         "run_id": "smoke_t1_20260702", "trades": 42},
        lane="tick", window_days=90)
    att = v["attempt"]
    assert att["counted_as_trial"] is True
    assert att["run_id"] == "smoke_t1_20260702"
    assert att["trades"] == 42
    # run_id/trades 없는 결과도 attempt 골격은 유지된다.
    v2 = evaluate_smoke_budget({"profit": 1.0}, lane="min", window_days=90)
    assert v2["attempt"]["counted_as_trial"] is True
    assert v2["attempt"]["run_id"] is None and v2["attempt"]["trades"] is None


# --------------------------------------------------------------------------
# 부활 레지스트리 (JSONL 왕복 + 전수 재검증)
# --------------------------------------------------------------------------
def _register_three(path):
    """엔트리 3개 등재: data_end 06-10 / 06-12 / 미기록."""
    register_rejected(
        {"condition_id": "lattice_v1:tick_0900_small_low:momentum_breakout",
         "cell_id": "tick_0900_small_low", "buy_sha256": "aa", "sell_sha256": "bb"},
        {"rejected_at": "2026-06-10", "data_end": "2026-06-10",
         "reject_basis": "고정 OOS 열위"},
        path)
    register_rejected(
        {"label": "REVIVAL X", "buy": "X_B", "sell": "X_S"},
        {"rejected_at": 20260612, "data_end_date": 20260612,
         "reject_basis": "maxMDD 위배"},
        path)
    register_rejected(
        {"condition_id": "lattice_v1:min_09h_small_low:volume_surge"},
        {"reject_basis": "구 등재분 — 데이터 창 미기록"},
        path)


def test_registry_roundtrip_append_only(tmp_path):
    """등재 → 로드 왕복: append-only, 순서 보존, 날짜 정규화, 정책 표식."""
    path = tmp_path / "revival" / "rejected_registry.jsonl"
    assert load_registry(path) == []  # 파일 없음 = 빈 레지스트리
    _register_three(path)
    entries = load_registry(path)
    assert len(entries) == 3  # 덮어쓰기 아님 — 3줄 append
    assert [e["schema"] for e in entries] == [REGISTRY_SCHEMA] * 3
    assert all(e["revalidation_policy"] == REVALIDATION_POLICY == "all_no_selection"
               for e in entries)
    assert entries[0]["label"].endswith("momentum_breakout")
    assert entries[0]["cell_id"] == "tick_0900_small_low"
    assert entries[1]["data_end"] == "2026-06-12"  # int 20260612 정규화
    assert entries[1]["rejected_at"] == "2026-06-12"
    assert entries[2]["data_end"] is None
    assert entries[1]["verdict"]["reject_basis"] == "maxMDD 위배"  # 원본 판정 보존


def test_register_rejected_requires_identity(tmp_path):
    """신원(label/condition_id/buy+sell) 없는 seed_record 는 거부."""
    path = tmp_path / "r.jsonl"
    with pytest.raises(ValueError):
        register_rejected({}, {"reject_basis": "x"}, path)
    with pytest.raises(ValueError):
        register_rejected({"buy": "X_B"}, {"reject_basis": "x"}, path)  # sell 없음
    with pytest.raises(ValueError):
        register_rejected({"label": "L"}, {"data_end": "언젠가"}, path)  # 날짜 오류
    assert not path.exists()  # 거부 시 아무것도 쓰지 않는다


def test_load_registry_rejects_corrupt_lines(tmp_path):
    """파싱 불가/비 dict/schema 불일치 줄은 줄 번호와 함께 거부."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"schema": "seed_revival_registry_v1"}\nnot-json\n',
                    encoding="utf-8")
    with pytest.raises(ValueError, match=":2"):
        load_registry(path)
    path.write_text('{"schema": "wrong_v9"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        load_registry(path)


def test_pending_revalidation_all_no_selection(tmp_path):
    """신규 데이터 도착 → 미접촉 등재자 전원 추출 (선별 없음, 재선택 금지 경계)."""
    path = tmp_path / "r.jsonl"
    _register_three(path)
    registry = load_registry(path)

    # 신규 창 끝 2026-07-01: 셋 다 미접촉 → 전원 (선별 없음).
    pend = pending_revalidation(registry, "2026-07-01")
    assert len(pend) == 3
    assert {p["pending_reason"] for p in pend} == {
        "new_untouched_data_available", "no_data_end_recorded"}
    assert all(p["new_data_end"] == "2026-07-01" for p in pend)

    # 경계: 새 창 끝 == data_end(06-12) → 그 엔트리는 같은 데이터 재선택이라 제외.
    pend2 = pending_revalidation(registry, 20260612)  # int 형식도 허용
    labels = [p["label"] for p in pend2]
    assert len(pend2) == 2 and "REVIVAL X" not in labels

    # 원본 불변: 추출이 레지스트리 엔트리를 오염시키지 않는다.
    assert "pending_reason" not in registry[0]
    with pytest.raises(ValueError):
        pending_revalidation(registry, "07/01/2026")  # 형식 오류


# --------------------------------------------------------------------------
# CLI smoke-plan (main(argv) 직접 호출 — 백테스트 실행은 범위 밖)
# --------------------------------------------------------------------------
def _write_min_coverage_map(tmp_path):
    """동적 3셀(모두 gap: trades 0)짜리 최소 coverage map 을 만든다."""
    from ai_strategy_loop.seeds.coverage import build_coverage_map, save_coverage_map
    seeds = [
        {"cell_id": "tick_0900_small_low", "buy_sha256": "aa"},
        {"cell_id": "tick_0905_small_low", "buy_sha256": "bb"},
        {"cell_id": "tick_0910_small_low", "buy_sha256": "cc"},
    ]
    cov = build_coverage_map(seeds, [], cells=[])
    path = tmp_path / "coverage_map.json"
    save_coverage_map(cov, path)
    return path


def test_cli_smoke_plan_batches_and_accounting(tmp_path, capsys):
    """smoke-plan: 판정+원시 혼합 입력 → 배치 3분류 + n_trials 집계 + advisory."""
    from cli.seed_lattice import main
    cov_path = _write_min_coverage_map(tmp_path)

    # 셀1 = 기판정 go, 셀2 = 원시 결과(-3M → no_go 판정 위임), 셀3 = 스모크 없음.
    judged_go = evaluate_smoke_budget(
        {"cell_id": "tick_0900_small_low", "profit": 500_000,
         "run_id": "smoke_c1"}, lane="tick", window_days=90)
    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(json.dumps({"verdicts": [
        judged_go,
        {"cell_id": "tick_0905_small_low", "profit": -3_000_000,
         "run_id": "smoke_c2"},
    ]}, ensure_ascii=False), encoding="utf-8")

    plan_path = tmp_path / "plan" / "smoke_plan.json"
    rc = main(["smoke-plan", "--coverage", str(cov_path),
               "--smoke", str(smoke_path), "--out", str(plan_path)])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["command"] == "smoke-plan" and summary["advisory_only"] is True

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["schema"] == "seed_lattice_smoke_plan_v1"
    assert plan["advisory_only"] is True
    assert "선택" in plan["policy_note"] and "동결" in plan["policy_note"]
    assert plan["batches"]["full_sweep"] == ["tick_0900_small_low"]
    assert plan["batches"]["deprioritized"] == ["tick_0905_small_low"]
    assert plan["batches"]["smoke_first"] == ["tick_0910_small_low"]
    assert plan["cells"]["tick_0905_small_low"]["no_go"] == 1
    assert plan["cells"]["tick_0910_small_low"]["verdict_count"] == 0
    # n_trials 정직성: 스모크 시도 2건 전량 집계 + run_id 보존.
    acc = plan["n_trials_accounting"]
    assert acc["smoke_attempts"] == 2
    assert sorted(acc["run_ids"]) == ["smoke_c1", "smoke_c2"]


def test_cli_smoke_plan_covered_cell_and_unmatched(tmp_path, capsys):
    """충족 셀(gap 아님)은 covered, 지도 밖 cell_id 판정은 unmatched 로 남는다."""
    from ai_strategy_loop.seeds.coverage import build_coverage_map, save_coverage_map
    from cli.seed_lattice import main
    seeds = [{"cell_id": "tick_0900_small_low", "buy_sha256": "aa"}]
    results = [{"cell_id": "tick_0900_small_low", "trades": 300, "profit": 10.0}]
    cov_path = tmp_path / "cov.json"
    save_coverage_map(build_coverage_map(seeds, results, cells=[]), cov_path)

    smoke_path = tmp_path / "smoke.json"
    smoke_path.write_text(json.dumps([
        {"cell_id": "min_09h_large_high", "profit": 1.0},  # 지도 밖
    ]), encoding="utf-8")

    plan_path = tmp_path / "plan.json"
    rc = main(["smoke-plan", "--coverage", str(cov_path),
               "--smoke", str(smoke_path), "--out", str(plan_path)])
    assert rc == 0
    capsys.readouterr()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    cell = plan["cells"]["tick_0900_small_low"]
    assert cell["gap"] is False and cell["action"] == "covered"
    assert plan["batches"] == {"full_sweep": [], "smoke_first": [],
                               "deprioritized": []}
    assert len(plan["unmatched_verdicts"]) == 1
    assert plan["n_trials_accounting"]["smoke_attempts"] == 1  # 미귀속도 trial
