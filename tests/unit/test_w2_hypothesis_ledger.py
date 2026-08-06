# -*- coding: utf-8 -*-
"""W2 심판 규율 계약 테스트 — 가설 원장 · 표본 밖 판정 · 편의 차감.

계약:
  1. 원장은 append-only — 기록을 덮어쓰지 않는다(폐기된 가설도 남는다).
  2. 수정 예산(15)을 넘기면 조용히 넘어가지 않고 BudgetExhausted 를 던진다.
  3. 판정은 **표본 밖** 델타로 한다. 표본 밖 일수가 모자라면 채택하지 않는다
     (적은 표본의 우연을 채택으로 바꾸는 것이 과적합의 출발점).
  4. 경계 이후만 표본 밖이다(경계 포함 이전은 설계 구간).
  5. 설계 성적은 항상 0.6225%p 차감본과 함께 읽는다.
  6. 입력 가정 객체를 변형하지 않는다(불변성).
"""
from __future__ import annotations

import json

import pytest

from ai_strategy_loop.autopsy.hypothesis import (
    VERDICT_ACCEPTED,
    VERDICT_INCONCLUSIVE,
    VERDICT_REJECTED,
    Hypothesis,
)
from ai_strategy_loop.controller import hypothesis_ledger as hl


@pytest.fixture()
def ledger(tmp_path):
    return tmp_path / "hypothesis_ledger.jsonl"


def _hyp(metric="profit", direction=1, text="손절을 넓히면 수익이 오른다"):
    return Hypothesis(
        side="sell", text=text, target_metric=metric,
        expected_direction=direction, source="gate_profit", basis="손실 73%가 90초 이후",
    )


# ---------------------------------------------------------------------------
# 원장 · 예산
# ---------------------------------------------------------------------------

def test_ledger_is_append_only(ledger):
    hl.append_record(hl.RevisionRecord("run-A", 1, "가설1", "profit", 1), path=ledger)
    hl.append_record(hl.RevisionRecord("run-A", 2, "가설2", "mdd", -1), path=ledger)

    rows = hl.read_ledger(ledger)
    assert [r["revision_no"] for r in rows] == [1, 2]
    assert [r["hypothesis_text"] for r in rows] == ["가설1", "가설2"]
    # 파일이 실제로 두 줄(덮어쓰기 아님)
    assert len(ledger.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_budget_blocks_after_limit(ledger):
    for n in range(hl.DEFAULT_REVISION_BUDGET):
        no = hl.next_revision_no("run-A", path=ledger)
        hl.append_record(hl.RevisionRecord("run-A", no, f"가설{no}", "profit", 1), path=ledger)

    state = hl.budget_state("run-A", path=ledger)
    assert state["revisions_used"] == hl.DEFAULT_REVISION_BUDGET
    assert state["budget_remaining"] == 0
    assert state["exhausted"] is True

    with pytest.raises(hl.BudgetExhausted):
        hl.next_revision_no("run-A", path=ledger)


def test_budget_is_per_idea(ledger):
    hl.append_record(hl.RevisionRecord("run-A", 1, "가설", "profit", 1), path=ledger)
    assert hl.budget_state("run-A", path=ledger)["revisions_used"] == 1
    assert hl.budget_state("run-B", path=ledger)["revisions_used"] == 0


def test_corrupt_line_does_not_lose_ledger(ledger):
    hl.append_record(hl.RevisionRecord("run-A", 1, "가설", "profit", 1), path=ledger)
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    hl.append_record(hl.RevisionRecord("run-A", 2, "가설2", "profit", 1), path=ledger)

    rows = hl.read_ledger(ledger)
    assert len(rows) == 2      # 손상 줄만 건너뛴다


# ---------------------------------------------------------------------------
# 표본 밖 분할 · 판정
# ---------------------------------------------------------------------------

def test_split_uses_only_days_after_boundary():
    result = hl.split_out_of_sample(
        [20250101, 20250102, 20250103, 20250104],
        [1.0, 1.0, -2.0, -2.0],
        boundary=20250102,
    )
    assert result["design_n"] == 2 and result["oos_n"] == 2
    assert result["oos_days"] == 2
    assert result["design_mean"] == pytest.approx(1.0)
    assert result["oos_mean"] == pytest.approx(-2.0)


def test_split_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        hl.split_out_of_sample([20250101], [1.0, 2.0], boundary=20250101)


def test_adjudicate_accepts_when_oos_agrees():
    hyps = [_hyp(metric="profit", direction=1)]
    out = hl.adjudicate_out_of_sample(hyps, {"d_profit": 12000.0}, oos_days=40)
    assert out[0].verdict == VERDICT_ACCEPTED
    assert out[0].observed_delta == pytest.approx(12000.0)


def test_adjudicate_rejects_when_oos_disagrees():
    hyps = [_hyp(metric="profit", direction=1)]
    out = hl.adjudicate_out_of_sample(hyps, {"d_profit": -8000.0}, oos_days=40)
    assert out[0].verdict == VERDICT_REJECTED


def test_thin_oos_is_never_accepted():
    """★핵심 — 표본 밖 일수가 모자라면 좋아 보여도 채택하지 않는다."""
    hyps = [_hyp(metric="profit", direction=1)]
    out = hl.adjudicate_out_of_sample(
        hyps, {"d_profit": 999999.0}, oos_days=3, min_oos_days=20,
    )
    assert out[0].verdict == VERDICT_INCONCLUSIVE
    assert out[0].observed_delta is None


def test_missing_metric_is_inconclusive():
    hyps = [_hyp(metric="profit", direction=1)]
    out = hl.adjudicate_out_of_sample(hyps, {"d_mdd": 1.0}, oos_days=40)
    assert out[0].verdict == VERDICT_INCONCLUSIVE


def test_adjudicate_does_not_mutate_input():
    original = _hyp()
    out = hl.adjudicate_out_of_sample([original], {"d_profit": 5.0}, oos_days=40)
    assert original.verdict == "untested"      # 입력 불변
    assert out[0] is not original


# ---------------------------------------------------------------------------
# 편의 차감 · 요약
# ---------------------------------------------------------------------------

def test_bias_adjusted_subtracts_measured_coefficient():
    assert hl.SELECTION_BIAS_PCT == pytest.approx(0.6225)
    assert hl.bias_adjusted(0.43) == pytest.approx(0.43 - 0.6225)
    assert hl.bias_adjusted(None) is None


def test_record_carries_bias_adjusted_value(ledger):
    hl.append_record(
        hl.RevisionRecord("run-A", 1, "가설", "profit", 1, design_pct=0.43), path=ledger,
    )
    row = hl.read_ledger(ledger)[0]
    assert row["design_pct"] == pytest.approx(0.43)
    assert row["bias_adjusted_pct"] == pytest.approx(0.43 - 0.6225)


def test_record_hypotheses_writes_and_summarizes(ledger):
    judged = hl.adjudicate_out_of_sample(
        [_hyp(metric="profit", direction=1, text="A"),
         _hyp(metric="profit", direction=-1, text="B")],
        {"d_profit": 100.0}, oos_days=40,
    )
    hl.record_hypotheses(
        "run-A", judged, design_pct=0.5, boundary=20250825, oos_days=40, path=ledger,
    )

    summary = hl.run_summary("run-A", path=ledger)
    assert summary["records"] == 2
    assert summary["verdicts"][VERDICT_ACCEPTED] == 1
    assert summary["verdicts"][VERDICT_REJECTED] == 1
    assert summary["hit_rate"] == pytest.approx(0.5)
    assert summary["last_boundary"] == 20250825
    assert summary["budget_remaining"] == hl.DEFAULT_REVISION_BUDGET - 2


def test_record_hypotheses_respects_budget(ledger):
    for n in range(hl.DEFAULT_REVISION_BUDGET):
        hl.append_record(hl.RevisionRecord("run-A", n + 1, "채움", "profit", 1), path=ledger)
    with pytest.raises(hl.BudgetExhausted):
        hl.record_hypotheses("run-A", [_hyp()], path=ledger)


def test_ledger_path_env_override(tmp_path, monkeypatch):
    target = tmp_path / "custom.jsonl"
    monkeypatch.setenv("STOM_AILOOP_HYPOTHESIS_LEDGER", str(target))
    hl.append_record(hl.RevisionRecord("run-A", 1, "가설", "profit", 1))
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8").splitlines()[0])["run_id"] == "run-A"
