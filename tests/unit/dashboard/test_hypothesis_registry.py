"""ANA-08 — finding→hypothesis→prereg 브리지 + 원장·큐 시험."""

from __future__ import annotations

import pytest

from ai_strategy_loop.dashboard import hypothesis_registry as hr


def _finding(role="train", n=50):
    return hr.FindingRecord(
        finding_id="f-1", bundle_sha256="b" * 64, axis="exit_timing",
        role=role, effect=0.4, ci=(0.1, 0.7), q=0.03, n=n,
    )


def _draft(**kw):
    base = dict(
        failure_explained="조기청산으로 꼬리 손실",
        falsifiable_prediction="연장 청산이 손실을 줄인다",
        entry_time_vars=("entry_price",),
        forbidden_vars=("exit_pnl",),
        data_requirement="n>=30",
        leakage_risk="매도 결과 변수 유입 가능성",
        negative_controls=("placebo_exit",),
        budget="2 runs",
        normal_stop="q>0.1",
    )
    base.update(kw)
    return hr.draft_hypothesis(_finding(), **base)


def test_deterministic_hypothesis_id():
    d1 = _draft()
    d2 = _draft()
    assert d1.hypothesis_id == d2.hypothesis_id
    # 같은 bundle → 동일 ID; 다른 예측 → 다른 ID.
    assert _draft(falsifiable_prediction="다른 예측").hypothesis_id != d1.hypothesis_id


def test_role_gate_blocks_oos_finding():
    with pytest.raises(hr.RegistryError) as ei:
        hr.draft_hypothesis(_finding(role="oos"), failure_explained="x",
                            falsifiable_prediction="y", entry_time_vars=("a",),
                            forbidden_vars=(), data_requirement="d",
                            leakage_risk="l", negative_controls=(),
                            budget="b", normal_stop="s")
    assert ei.value.code == "role_forbids_directive"


def test_insufficient_evidence_blocked():
    from dataclasses import replace
    f = replace(_finding(), n=None)
    with pytest.raises(hr.RegistryError) as ei:
        hr.draft_hypothesis(f, failure_explained="x", falsifiable_prediction="y",
                            entry_time_vars=("a",), forbidden_vars=(),
                            data_requirement="d", leakage_risk="l",
                            negative_controls=(), budget="b", normal_stop="s")
    assert ei.value.code == "insufficient_evidence"


def test_missing_required_fields_blocked():
    with pytest.raises(hr.RegistryError) as ei:
        _draft(leakage_risk="")
    assert ei.value.code == "hypothesis_missing_fields"


def test_review_transitions_and_reviewer_required():
    d = _draft()
    with pytest.raises(hr.RegistryError):
        hr.review_hypothesis(d, hr.S_ACCEPTED, reviewer="")
    accepted = hr.review_hypothesis(d, hr.S_ACCEPTED, reviewer="park", note="ok")
    assert accepted.status == hr.S_ACCEPTED
    # 이미 검토된 초안은 재검토 불가.
    with pytest.raises(hr.RegistryError) as ei:
        hr.review_hypothesis(accepted, hr.S_REJECTED, reviewer="park")
    assert ei.value.code == "invalid_transition"


def test_seal_never_without_approval():
    d = hr.review_hypothesis(_draft(), hr.S_ACCEPTED, reviewer="park")
    pre = hr.to_prereg_draft(d)
    assert pre["status"] == hr.S_PREREG_DRAFT
    with pytest.raises(hr.RegistryError) as ei:
        hr.seal_prereg(pre, approval_evidence="", approver="")
    assert ei.value.code == "seal_requires_human_approval"
    sealed = hr.seal_prereg(pre, approval_evidence="meeting-2026-09-13",
                            approver="park")
    assert sealed["status"] == hr.S_PREREG_SEALED
    assert sealed["sealed_sha256"]


def test_prereg_draft_requires_accepted():
    d = _draft()
    with pytest.raises(hr.RegistryError) as ei:
        hr.to_prereg_draft(d)
    assert ei.value.code == "prereg_requires_accepted"


def test_knowledge_ledger_falsification():
    led = hr.KnowledgeLedger()
    led.record(_finding())
    led.falsify("f-1", by="exp-9")
    assert led.open_findings() == []
    with pytest.raises(hr.RegistryError):
        led.falsify("f-9", by="x")


def test_queue_gating_and_cancel_receipt():
    q = hr.ResearchQueue()
    d = _draft()
    with pytest.raises(hr.RegistryError) as ei:
        q.enqueue(d, item_id="i1", deadline=9999999999.0)
    assert ei.value.code == "queue_requires_accepted_hypothesis"
    accepted = hr.review_hypothesis(d, hr.S_ACCEPTED, reviewer="park")
    item = q.enqueue(accepted, item_id="i1", deadline=9999999999.0)
    q.attempt("i1")
    assert item.attempts == 1
    receipt = q.cancel("i1", reason="예산 초과")
    assert receipt["event"] == "cancelled" and receipt["attempts"] == 1
    with pytest.raises(hr.RegistryError):
        q.attempt("i1")
