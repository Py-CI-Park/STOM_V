# -*- coding: utf-8 -*-
"""전이율 원장 축 분리 계약 테스트 (W4-b 실측이 드러낸 결함).

실측 2026-08-06:
  진입까지 바꾼 후보 — 전이율 0.105 ~ 0.343 (지도가 **과대**평가)
  진입 고정·청산만 바꾼 후보 — 2.25 ~ 4.22 (지도가 **과소**평가)

방향이 반대인 두 무리의 중앙값 하나를 "보수 계수"라고 부르면 어느 쪽에도 맞지
않는다. 원장은 축을 나눠 답해야 한다.

계약:
  1. 진입 고정 러너 기록(`arm` 표식)은 exit_only 축으로 분류된다.
  2. 표식이 없는 기록은 entry_and_exit 축이다.
  3. 축별 계수는 그 축의 표본만으로 계산한다.
  4. 두 축이 모두 표본을 가지면 `axis_mixed=True` 로 알린다 — 조용히 섞지 않는다.
  5. 축 계수도 최소 표본 규칙을 그대로 지킨다.
  6. 모르는 축 이름은 거부한다.
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.dashboard import transfer_ledger_api as tl


def _outcome(name, rule, map_pct, engine_pct, *, arm=None):
    row = {
        "name": name, "rule": rule, "job_id": f"job-{name}",
        "predicted": {"expectancy_pct": map_pct, "rows": 344},
        "engine": {"trade_count": 157, "avg_profit_pct": engine_pct},
        "transfer_ratio": engine_pct / map_pct,
    }
    if arm:
        row["arm"] = arm
    return row


@pytest.fixture()
def ledger_root(tmp_path, monkeypatch):
    monkeypatch.setattr(tl, "_LABEL_ROOT", str(tmp_path))
    return tmp_path


def _write(root, folder, filename, outcomes):
    target = root / folder
    target.mkdir(parents=True, exist_ok=True)
    (target / filename).write_text(
        json.dumps({"lane": "tick", "outcomes": outcomes}, ensure_ascii=False),
        encoding="utf-8")


def test_arm_marker_routes_to_exit_only_axis(ledger_root):
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.2493, 0.56, arm="challenger_1"),
    ])
    row = tl.transfer_ledger()["records"][0]
    assert row["axis"] == tl.AXIS_EXIT_ONLY


def test_missing_marker_is_entry_and_exit(ledger_root):
    _write(ledger_root, "design_v2", "_p5_report.json", [
        _outcome("q1", "TP3.0/SL2.0", 0.3501, 0.12),
    ])
    row = tl.transfer_ledger()["records"][0]
    assert row["axis"] == tl.AXIS_ENTRY_AND_EXIT


def test_axis_coefficients_do_not_borrow_from_each_other(ledger_root):
    """★ 각 축의 계수는 그 축의 표본만으로 만든다."""
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.2493, 0.56, arm="c1"),
        _outcome("t2", "trailing(arm+3/give1)", 0.2320, 0.55, arm="c2"),
        _outcome("t3", "trailing(arm+5/give2)", 0.2182, 0.92, arm="c3"),
    ])
    _write(ledger_root, "design_v2", "_p5_report.json", [
        _outcome("q1", "TP3.0/SL2.0", 0.3501, 0.12),
        _outcome("q2", "TP3.0/SL1.0", 0.2867, 0.03),
    ])

    ledger = tl.transfer_ledger()
    exit_only = ledger["by_axis"][tl.AXIS_EXIT_ONLY]
    entry_exit = ledger["by_axis"][tl.AXIS_ENTRY_AND_EXIT]

    assert exit_only["record_count"] == 3 and exit_only["status"] == "ready"
    assert exit_only["coefficient"] > 1        # 지도가 과소평가한 쪽
    assert entry_exit["record_count"] == 2 and entry_exit["status"] == "accumulating"
    assert entry_exit["coefficient"] < 1       # 지도가 과대평가한 쪽
    assert ledger["axis_mixed"] is True


def test_single_axis_is_not_flagged_as_mixed(ledger_root):
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.2493, 0.56, arm="c1"),
    ])
    assert tl.transfer_ledger()["axis_mixed"] is False


def test_axis_estimate_uses_that_axis_only(ledger_root):
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.25, 0.50, arm="c1"),
        _outcome("t2", "trailing(arm+3/give1)", 0.25, 0.50, arm="c2"),
        _outcome("t3", "trailing(arm+5/give2)", 0.25, 0.50, arm="c3"),
    ])
    out = tl.transfer_estimate(0.25, axis=tl.AXIS_EXIT_ONLY)
    assert out["available"] is True
    assert out["coefficient"] == pytest.approx(2.0)
    assert out["engine_estimate_pct"] == pytest.approx(0.5)
    assert out["axis_mixed"] is False


def test_axis_estimate_respects_minimum_sample(ledger_root):
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.25, 0.50, arm="c1"),
    ])
    out = tl.transfer_estimate(0.25, axis=tl.AXIS_EXIT_ONLY)
    assert out["available"] is False
    assert out["reason"] == "insufficient_records"


def test_unknown_axis_is_refused(ledger_root):
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(arm+3/give1.5)", 0.25, 0.50, arm="c1"),
    ])
    out = tl.transfer_estimate(0.25, axis="whatever")
    assert out["available"] is False and out["reason"] == "unknown_axis"


def test_mixed_estimate_admits_it_is_mixed(ledger_root):
    """섞인 값을 내주더라도 섞였다는 사실을 숨기지 않는다."""
    _write(ledger_root, "design_v4", "_p5_engine_report.json", [
        _outcome("t1", "trailing(a)", 0.25, 0.55, arm="c1"),
        _outcome("t2", "trailing(b)", 0.25, 0.56, arm="c2"),
    ])
    _write(ledger_root, "design_v2", "_p5_report.json", [
        _outcome("q1", "TP3/SL2", 0.35, 0.12),
        _outcome("q2", "TP3/SL1", 0.29, 0.03),
    ])
    out = tl.transfer_estimate(0.25)
    assert out["available"] is True
    assert out["axis_mixed"] is True
    assert set(out["by_axis"]) == {tl.AXIS_EXIT_ONLY, tl.AXIS_ENTRY_AND_EXIT}
