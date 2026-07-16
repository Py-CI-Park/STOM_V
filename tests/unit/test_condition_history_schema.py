"""condition_history_v1 스키마 계약 테스트 (G002).

DB/네트워크 접근 없이 순수 stdlib만 사용하는 cli/condition_history_schema.py
모듈에 대한 계약 테스트: 영수증 결정론, 동결된 축 값의 바이트 정확성,
flat_rows 트리/테이블 정합성, 구조 검증, null-vs-zero 지표 시맨틱스를
검증한다.
"""

from __future__ import annotations

import copy

from cli.condition_history_schema import (
    CAP_BANDS,
    CHANGE_GUARD,
    COVERAGE_STATUSES,
    EVALUATION_STATUSES,
    GAP_BANDS,
    MIN_EXIT_PROFILE,
    MIN_WINDOWS,
    SCHEMA_VERSION,
    SIGNAL_PERIOD,
    TICK_EXIT_PROFILE,
    TICK_WINDOWS,
    UNVALIDATED_COMPARISON_CONTROL_LABEL,
    WARMUP_BARS,
    ExitProfileReceiptV1,
    SeedBoundaryIntentReceiptV1,
    canonical_sha256,
    flat_rows,
    validate_research_node,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _evaluation(eval_id: str, condition_id: str, status: str = "success", metrics=None) -> dict:
    return {
        "evaluation_id": eval_id,
        "condition_id": condition_id,
        "status": status,
        "metrics": metrics if metrics is not None else {"win_rate": 0.5},
    }


def _condition(condition_id: str, stage_id: str, evaluations=None) -> dict:
    return {
        "condition_id": condition_id,
        "stage_id": stage_id,
        "label": f"label-{condition_id}",
        "coverage_status": "success",
        "evaluations": evaluations if evaluations is not None else [],
    }


def _stage(stage_id: str, research_id: str, conditions=None) -> dict:
    return {
        "stage_id": stage_id,
        "research_id": research_id,
        "label": f"label-{stage_id}",
        "coverage_status": "success",
        "conditions": conditions if conditions is not None else [],
    }


def _research(research_id: str, stages=None) -> dict:
    return {
        "research_id": research_id,
        "label": f"label-{research_id}",
        "coverage_status": "success",
        "stages": stages if stages is not None else [],
    }


def _sample_tree() -> dict:
    ev1 = _evaluation("e1", "c1")
    ev2 = _evaluation("e2", "c1", status="no_trades", metrics={"win_rate": None})
    c1 = _condition("c1", "s1", [ev1, ev2])
    ev3 = _evaluation("e3", "c2")
    c2 = _condition("c2", "s1", [ev3])
    s1 = _stage("s1", "r1", [c1, c2])
    return _research("r1", [s1])


# ---------------------------------------------------------------------------
# canonical_sha256 / SeedBoundaryIntentReceiptV1 determinism
# ---------------------------------------------------------------------------


def test_canonical_sha256_same_input_same_hash():
    obj = {"b": 2, "a": 1}
    assert canonical_sha256(obj) == canonical_sha256({"a": 1, "b": 2})


def test_canonical_sha256_changed_value_differs():
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_seed_boundary_receipt_determinism():
    a = SeedBoundaryIntentReceiptV1.frozen_default()
    b = SeedBoundaryIntentReceiptV1.frozen_default()
    assert a.sha256 == b.sha256


def test_seed_boundary_receipt_changed_value_differs_hash():
    a = SeedBoundaryIntentReceiptV1.frozen_default()
    b = SeedBoundaryIntentReceiptV1(
        schema_version=a.schema_version,
        tick_windows=a.tick_windows,
        min_windows=a.min_windows,
        cap_bands=a.cap_bands,
        gap_bands=a.gap_bands,
        change_guard=a.change_guard,
        warmup_bars=a.warmup_bars + 1,
        signal_period=a.signal_period,
    )
    assert a.sha256 != b.sha256


def test_exit_profile_receipt_determinism():
    a = ExitProfileReceiptV1.frozen_default()
    b = ExitProfileReceiptV1.frozen_default()
    assert a.sha256 == b.sha256


def test_exit_profile_receipt_changed_value_differs_hash():
    a = ExitProfileReceiptV1.frozen_default()
    changed_tick_exit = dict(a.tick_exit)
    changed_tick_exit["stop"] = -99.0
    b = ExitProfileReceiptV1(
        schema_version=a.schema_version,
        tick_exit=changed_tick_exit,
        min_exit=a.min_exit,
        label=a.label,
    )
    assert a.sha256 != b.sha256


# ---------------------------------------------------------------------------
# frozen axis values -- byte-exact
# ---------------------------------------------------------------------------


def test_schema_version_value():
    assert SCHEMA_VERSION == "condition_history_v1"


def test_tick_windows_frozen_values():
    assert TICK_WINDOWS == ((90000, 90500), (90500, 91000), (91000, 92000))


def test_min_windows_frozen_values():
    assert MIN_WINDOWS == ((90000, 93000), (93000, 100000), (100000, 140000))


def test_cap_bands_frozen_values():
    assert CAP_BANDS == ((0, 3000), (3000, 6000), (6000, 10000), (10000, None))


def test_gap_bands_frozen_values():
    assert GAP_BANDS == ((-15, -5), (-5, 0), (0, 5), (5, 10), (10, 15))


def test_change_guard_frozen_values():
    assert CHANGE_GUARD == (-15, 29)


def test_warmup_and_signal_period_frozen_values():
    assert WARMUP_BARS == 20
    assert SIGNAL_PERIOD == 20


def test_tick_exit_profile_frozen_values():
    assert TICK_EXIT_PROFILE == {"stop": -3.0, "take": 5.0, "hold": 300, "close": 93000}


def test_min_exit_profile_frozen_values():
    assert MIN_EXIT_PROFILE == {"stop": -4.0, "take": 6.0, "hold": 60, "close": 145900}


def test_exit_profile_label_is_unvalidated_comparison_control():
    assert UNVALIDATED_COMPARISON_CONTROL_LABEL == "unvalidated_comparison_control"
    receipt = ExitProfileReceiptV1.frozen_default()
    assert receipt.label == "unvalidated_comparison_control"


def test_evaluation_statuses_frozen_values():
    assert EVALUATION_STATUSES == (
        "success",
        "no_trades",
        "missing",
        "unavailable",
        "failed",
        "timeout",
        "not_run",
    )


def test_coverage_statuses_frozen_values():
    assert COVERAGE_STATUSES == (
        "success",
        "no_trades",
        "missing",
        "unavailable",
        "failed",
        "timeout",
        "not_run",
    )


# ---------------------------------------------------------------------------
# flat_rows -- tree/table parity + ordering
# ---------------------------------------------------------------------------


def test_flat_rows_one_row_per_evaluation():
    tree = _sample_tree()
    rows = flat_rows(tree)
    assert len(rows) == 3


def test_flat_rows_deterministic_ordering():
    tree = _sample_tree()
    rows = flat_rows(tree)
    assert [r["evaluation_id"] for r in rows] == ["e1", "e2", "e3"]


def test_flat_rows_parity_with_tree_structure():
    tree = _sample_tree()
    rows = flat_rows(tree)
    row = rows[0]
    assert row["research_id"] == "r1"
    assert row["stage_id"] == "s1"
    assert row["condition_id"] == "c1"
    assert row["evaluation_id"] == "e1"
    assert row["evaluation_status"] == "success"


def test_flat_rows_same_input_same_output():
    tree = _sample_tree()
    rows_a = flat_rows(tree)
    rows_b = flat_rows(copy.deepcopy(tree))
    assert rows_a == rows_b


# ---------------------------------------------------------------------------
# validate_research_node -- structural validation
# ---------------------------------------------------------------------------


def test_validate_research_node_valid_tree_has_no_errors():
    tree = _sample_tree()
    assert validate_research_node(tree) == []


def test_validate_research_node_rejects_duplicate_condition_id():
    ev = _evaluation("e1", "c1")
    c1 = _condition("c1", "s1", [ev])
    c1_dup = _condition("c1", "s1", [])
    s1 = _stage("s1", "r1", [c1, c1_dup])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("duplicate condition_id" in e for e in errors)


def test_validate_research_node_rejects_duplicate_evaluation_id():
    ev1 = _evaluation("e1", "c1")
    ev1_dup = _evaluation("e1", "c1")
    c1 = _condition("c1", "s1", [ev1, ev1_dup])
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("duplicate evaluation_id" in e for e in errors)


def test_validate_research_node_rejects_orphan_condition_parent():
    ev = _evaluation("e1", "c1")
    c1 = _condition("c1", "wrong-stage-id", [ev])
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("orphan parent stage_id" in e for e in errors)


def test_validate_research_node_rejects_orphan_stage_parent():
    s1 = _stage("s1", "wrong-research-id", [])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("orphan parent research_id" in e for e in errors)


def test_validate_research_node_rejects_orphan_evaluation_parent():
    ev = _evaluation("e1", "wrong-condition-id")
    c1 = _condition("c1", "s1", [ev])
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("orphan parent condition_id" in e for e in errors)


def test_validate_research_node_rejects_unknown_evaluation_status():
    ev = _evaluation("e1", "c1", status="bogus_status")
    c1 = _condition("c1", "s1", [ev])
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("unknown status" in e for e in errors)


def test_validate_research_node_rejects_unknown_coverage_status():
    c1 = _condition("c1", "s1", [])
    c1["coverage_status"] = "bogus_coverage"
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    errors = validate_research_node(tree)
    assert any("unknown coverage_status" in e for e in errors)


# ---------------------------------------------------------------------------
# null-vs-zero metric semantics
# ---------------------------------------------------------------------------


def test_missing_metric_stays_none_not_zero():
    ev = _evaluation("e1", "c1", status="no_trades", metrics={"win_rate": None, "pnl": 0.0})
    c1 = _condition("c1", "s1", [ev])
    s1 = _stage("s1", "r1", [c1])
    tree = _research("r1", [s1])
    rows = flat_rows(tree)
    assert rows[0]["metrics"]["win_rate"] is None
    assert rows[0]["metrics"]["pnl"] == 0.0
    assert rows[0]["metrics"]["pnl"] is not None
